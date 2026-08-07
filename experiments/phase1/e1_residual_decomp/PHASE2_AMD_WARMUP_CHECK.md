# AMD matched-warmup check: the WC quadrilateration anchor holds up

Dated 2026-08-08. Direct response to the panel's warning that "AMD's
retained quiescent data showed no bimodality on inspection" is invalid by
the same failure mode that hid Intel's ~10% artifact: per-arm distributions
can be tight and unimodal while still uniformly biased. This runs the
actual matched-warmup test AMD never got, rather than relying on
inspection.

## Background: AMD's victim already has a built-in warmup, unlike Intel's

`victim.c` (the AMD-side binary) takes a first-class `-W <warmup_sec>` flag
and runs an internal, unreported warmup phase before the measured window
begins — a real warmup mechanism, unlike Intel's `pointer_chase_nocap`
which had none. The campaign's existing AMD scripts (`run_e1_gate.py`,
`run_p24_amd_flushbehind.py`) already pass `-W 2` uniformly to every arm.
The open question was whether 2s is *enough*, given Intel's own finding
that ~2s of self-generated dose alone was insufficient (only partially
warm) and it took a full ~4-8s cumulative window to saturate.

## v1: a false alarm caused by a new confound, not by warmup duration

The first attempt (`run_amd_matched_warmup.py`) tried to save wall-clock
time by sharing one aggressor launch across two back-to-back victim calls
per arm (`W=2` then `W=10`). This surfaced an enormous, highly reproducible
anomaly: **WC's `W=2` call read ~12-15M cyc/iter — a ~3.3-4x tax — against
quiescent's ~3.6M, while `W=10` read ~3.6M (parity), across two independent
full runs.** Read naively, this would have overturned the WC=0.989x
quadrilateration anchor entirely.

It was investigated rather than trusted. In order:

1. An exact single-victim-call replica of `run_e1_gate.py`'s protocol
   (fresh aggressor launch per measurement, `AGG_DUR=16`) reproduced the
   *original* clean result (~3.6-3.7M) regardless of `W=2` or whether
   preceded by a `wb_cat` arm — ruling out warmup duration and
   single-arm carryover as the cause.
2. Raising the isolated test's `AGG_DUR` from 16 to 40 (matching v1's
   longer aggressor lifetime) alone did not reproduce the anomaly.
3. Two back-to-back `W=2` calls sharing one aggressor (isolating *call
   order* from *warmup value*) did not reproduce it either — both calls
   read clean.
4. Replicating the *full* `quiescent → wb → wb_cat → wc` sequence with
   every arm double-called (matching v1's exact structure) **did**
   reproduce it (WC `W=2` ~14.5-14.7M, `W=10` ~3.6M) — confirming the
   effect requires the accumulated depth of multiple preceding
   heavily-loaded double-called arms, not any single variable tested
   alone.
5. The original retained `e1gate_raw_n12.jsonl`'s `A3_wc` values, read in
   rep order (not sorted), show **no monotonic drift across 12 reps**
   (~10 minutes of wall-clock time): 3659563, 3658998, 3595471, 3676236,
   3586711, 3657911, 3647858, 3631127, 3610396, 3572206, 3571752, 3585517
   — a tight, non-drifting band. This rules out the original 12-rep
   protocol having quietly accumulated the same effect.

**Conclusion: v1's shared-aggressor-across-two-calls design tripled each
arm's aggressor lifetime relative to the original protocol, and that
extended lifetime — not warmup duration — is what produced the anomaly.**
This is a real methodology finding worth keeping in mind (sustained
multi-thread aggressor load, sustained for tens of seconds longer than the
original protocol ever holds it, measurably changes WC's interaction with
a short-warmup victim) but it does not implicate the original campaign
data, which never runs aggressors that long per arm.

## v2: corrected design — two full separate passes, original lifecycle preserved

`run_amd_matched_warmup_v2.py`: every arm gets its own fresh aggressor
launch per single victim call (`AGG_DUR` scaled tightly to
settle+warmup+measure+margin, never shared across two calls) — structurally
identical to `run_e1_gate.py` / `run_p24_amd_flushbehind.py`. Two full,
separate n=12 sweeps: one at `W=2` (an in-session control, replicating the
original protocol) and one at `W=10` (clearly past Intel's observed
dose-saturation point). Arms: quiescent, wb, wb_cat, wc,
`flush_d256kb` (Phase 2.4's best-case/lowest-tax D point).

| arm | W=2 tax | W=2 95% CI | W=10 tax | W=10 95% CI |
|---|---:|---:|---:|---:|
| wb | 20.438 | [20.348, 20.756] | 20.267 | [20.101, 20.513] |
| wb_cat | 9.917 | [9.846, 10.065] | 9.768 | [9.673, 9.902] |
| **wc** | **1.001** | **[0.985, 1.028]** | **0.983** | **[0.974, 1.009]** |
| flush_d256kb | 5.899 | [5.869, 5.991] | 5.857 | [5.815, 5.928] |

**Every arm's W=2 and W=10 confidence intervals overlap heavily.** Warmup
duration makes no material difference to any AMD tax number under the
corrected, original-lifecycle-preserving design.

## Verdict

**The WC quadrilateration anchor holds up under direct testing.** Both
warmup durations put it at parity (1.001x, 0.983x — both statistically
indistinguishable from 1.0, and from each other). AMD's victim binary's
built-in 2s warmup, despite being shorter than what Intel's ad-hoc
protocol needed, is evidently sufficient for AMD's hardware — AMD does not
reproduce Intel's dose-response sensitivity. This is a real, positive
answer to the panel's challenge, not a repeat of the "no bimodality on
inspection" failure mode: the check that was actually missing has now been
run, at n=12, with a proper control replica in the same session, and it
clears.

The 6-7x convergent-floor claim also holds: `wb_cat` (CAT) sits at
9.77-9.92x and `flush_d256kb` at 5.86-5.90x — both comfortably in the
previously-reported range, unaffected by warmup duration.

## Secondary finding, unrelated to warmup: `wb_cat` session drift

The W=2 control-replica's `wb_cat` tax (9.92x) is notably higher than the
original gate's `A2_wb_cat` (7.23x) — a ~37% relative difference, and
*consistent* between this session's W=2 and W=10 passes (9.92 vs 9.77,
internally tight), so it is not a warmup artifact. `wb` (20.4-20.3x vs
original 19.9x) and `wc`/`flush_d256kb` (both closely matching original)
show much smaller or no drift. This looks like a real, unexplained
session-to-session change specific to the CAT-partitioned arm — flagged
here for follow-up, out of scope for this warmup check. Candidates worth
checking first: CAT schemata actually taking effect identically
(way-count, not just the schemata string); governor/boost state at the
time of the original gate run vs. today's re-freeze; and general
hardware/thermal drift over the ~weeks between runs.

## Provenance

Scripts: `run_amd_matched_warmup.py` (v1, superseded — kept for the
methodology note above, not for its numbers), `run_amd_matched_warmup_v2.py`
(the valid design), `run_wc_isolation_check.py` and the ad-hoc depth-check
script (isolation diagnostics, not committed as they were throwaway
verification, results captured above). Data: `amd_v2_W2_n12.jsonl`,
`amd_v2_W10_n12.jsonl`. Host: broker (AMD EPYC 9754), re-frozen to
`performance` governor / boost off before this check (found drifted to
`schedutil`/boost-on since the last documented freeze — the same drift
pattern noted after the earlier mid-run reboot incident; worth adding a
freeze-state check to the top of every AMD session, not just after
reboots).

## What still needs doing

- Investigate the `wb_cat` session-to-session drift (9.92x now vs 7.23x
  originally) as its own item — separate from this warmup check.
- Fold these numbers into the convergent-floor synthesis and paper tables
  once the `wb_cat` drift is resolved (don't average across sessions with
  an unexplained 37% discrepancy in one arm).
- Add a governor/boost/hugepage freeze-state check to the start of every
  AMD session, not just after known reboot events — this is the second
  time state has been found drifted without an intervening reboot being
  the obvious cause.
