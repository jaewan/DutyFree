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

`flush_d256kb` sits at 5.86-5.90x, comfortably matching the previously
reported 5.94x — the convergent-floor claim holds there. **`wb_cat`
(CAT) does NOT comfortably match its previous number** — see below, this
is now a confirmed, real, and as-yet-unexplained drift, not a warmup
artifact.

## Secondary finding, unrelated to warmup: `wb_cat` session drift, investigated

The W=2 control-replica's `wb_cat` tax (9.92x) is notably higher than the
original gate's `A2_wb_cat` (7.23x) — a ~37% relative difference. This was
followed up rather than just flagged.

**Confirmed real, not a v2/warmup artifact.** Re-ran the *literal,
unmodified* `run_e1_gate.py` (byte-identical to the committed file, diffed
to confirm), fresh, n=6, right now. It crashed on a `perf stat` failure
(see below) before completing, but the victim/aggressor measurements
before the crash are fully valid — patched a copy
(`run_e1_gate_noperf.py`, only change: catch the now-missing perf output
file instead of crashing) and reran clean:

| arm | now (n=6) | original (n=12) | relative drift |
|---|---:|---:|---:|
| A1_wb | 20.545 | 19.886 | +3.3% |
| A2_wb_cat | **9.867** | **7.225** | **+36.6%** |
| A3_wc | 1.006 | 0.989 | +1.7% |

**The drift is specific to the CAT-partitioned arm.** `wb` and `wc` sit
well within normal session-to-session noise (1.7-3.3%); only `wb_cat`
shows a large, real shift. This rules out general thermal/hardware drift
(which would move all three) and points at something specific to CAT
enforcement.

**Investigated directly, several mechanisms ruled out:**
- **Not a schemata-write failure.** `last_cmd_status` reads `ok` both
  before and during a live run; schemata reads back exactly as written
  (`ff00`/`00ff`) and stays stable throughout.
- **Not a domain-mapping shift.** The box has 32 L3 domains (one per CCX;
  16 CCX × 2 sockets), and both scripts only ever write `L3:0=...`
  (domain 0). Verified directly: ran the victim alone in a fresh
  monitoring-only group and checked `llc_occupancy` across all 32
  `mon_L3_NN` domains — only `mon_L3_00` showed nonzero occupancy,
  confirming domain 0 is still correctly mapped to CCX0 (cores 0-7,
  matching `cpu0`'s `shared_cpu_list`). The partition is being applied to
  the right physical cache slice.
- **Not resctrl capability drift.** `cbm_mask=ffff`, `num_closids=16`,
  group `mode=shareable` all read as expected, matching a normal 16-way
  CAT-capable configuration.

**One timing-consistent but mechanistically-unconfirmed candidate found**:
`dpkg.log` shows `linux-tools-common` upgraded (6.8.0-136.136 →
6.8.0-137.137) at **2026-08-06 06:32:46** — about 4 hours *after* the
original gate data was collected (committed at 2026-08-06 02:31-02:40,
same day). This same package area plausibly explains a fully separate
observation made along the way: `perf list` no longer recognizes the
`l3_lookup_state.*` / `l3_xi_sampled_latency.*` AMD uncore PMU event
aliases that `run_e1_gate.py` depends on for its supplementary L3 counters
(confirmed missing; the gate script now crashes on this unless patched).
However, `linux-tools-common` is a **userspace perf-tooling package** —
it ships event-alias JSON definitions, not kernel code, and has no
obvious mechanism for changing real hardware CAT-partition enforcement
behavior. The timing match is suspicious enough to record, but this is
flagged as **correlation, not a confirmed cause**.

**Bottom line: real, isolated to CAT, several plausible mechanisms ruled
out by direct testing, true cause not identified.** Verifying the actual
QoS mask MSRs at the CLOSID level (bypassing resctrl's sysfs abstraction
entirely) would be the next step, but that's beyond what's practical to
pursue further here. Diagnostic script kept: `check_cat_live.py`.

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

- **[INVESTIGATED, NOT RESOLVED]** `wb_cat` drift: confirmed real (9.87-9.92x
  now vs 7.23x originally), isolated to the CAT-partitioned arm
  specifically (wb/wc drift only 1.7-3.3%), several mechanisms ruled out
  by direct testing (schemata write/readback, domain mapping, resctrl
  capability info), true physical cause not identified. A `linux-tools-common`
  package upgrade ~4 hours after the original data collection is a
  timing-consistent but mechanistically-unconfirmed candidate.
- **Next step if pursued further**: read the actual QoS mask MSRs for the
  assigned CLOSIDs directly (bypass resctrl's sysfs abstraction) to verify
  hardware-level enforcement, or open a case with AMD/kernel resctrl
  maintainers referencing the exact kernel version (`7.0.0-28-generic`)
  and the `linux-tools-common` version delta.
- **Do not fold `wb_cat`/CAT numbers into the paper's convergent-floor
  table until this is resolved** — a real 37% swing in one input, with an
  unidentified cause, shouldn't be silently averaged with the original
  number or silently replaced with the new one. The 6-7x floor's
  *qualitative* conclusion is safe either way (7.23x and 9.87x both land
  in the same "large, CAT-doesn't-fully-recover" bucket relative to WB's
  ~20x and WC's ~1.0x), but the *specific number* quoted needs a decision,
  not an assumption.
- Add a governor/boost/hugepage freeze-state check to the start of every
  AMD session, not just after known reboot events — this is the second
  time state has been found drifted without an intervening reboot being
  the obvious cause.
