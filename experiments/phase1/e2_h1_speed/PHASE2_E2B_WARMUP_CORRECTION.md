# E2b quiescent-baseline correction: the reported 0.90x small-D tax was a measurement artifact

Dated 2026-08-07. Supersedes the verdict in `phase2_pmqos_ticker_RESULTS.md`
("do not use this result to revise E2b's original 0.90-0.905x finding") and
partially falsifies `PHASE2_TICKER_NORMALIZED_E2B_PREREGISTRATION.md`'s
proposed fix mechanism, while confirming its underlying prediction via a
different mechanism.

## What was pre-registered, and what happened

The ticker-normalized re-run (`run_e2b_flushbehind_ticker.py`, n=12, busy-spin
ticker on cpu20 present for the whole script including the quiescent arm)
predicted: if idle-package-activity-mode explains E2b's ~0.90x small-D tax,
adding a keep-awake ticker to every arm should collapse quiescent's mode to
match the loaded arms', moving tax toward ~1.00x.

**Result: it did not.** Quiescent stayed at median 89.22 (all 12 reps in
88.7-89.7, still 100% slow-mode) despite the ticker running continuously and
verified alive (99.9% CPU pinned to cpu20). The pre-registered falsification
condition was met for *this specific mechanism*.

## Diagnosis: bandwidth threshold, not "any concurrent activity"

Five direct, cheap tests (not written up as formal experiments, run to
localize the failure before committing to another full n=12):

1. Three standalone back-to-back single-trial victim calls (no aggressor, no
   resctrl group): first call slow (89.85), next two fast (81.83, 81.88) —
   recovery happens *within* a process boundary, not across it.
2. Heavy 8-thread aggressor for 10s, killed, then victim `--trials 3`
   immediately: trial 0 (right after aggressor stops) still slow (90.78);
   trials 1-2 (same process, ~4s later) fast (81.59, 81.66). The aggressor's
   *prior* traffic does not carry over across the kill/relaunch gap.
3. Same aggressor-then-victim test with a 3s wall-clock gap before
   measuring: still slow (89.22) — rules out simple time-based dissipation.
4. Fresh victim process, no aggressor, `--trials 4`: trial 0 mildly slow
   (85.64), trials 1-3 fast (81.51, 81.55, 81.79) — the victim's *own*
   accumulated in-process runtime is sufficient on its own.
5. `run_quiescent_corrected.py`, n=12 independent fresh processes each doing
   `--trials 4` and discarding trial 0: trial 0 was *already* fast in 9/12
   reps (81.5-82.1) and only slow in 1/12 (86.92) — showing that once the
   *sequence* of repeated invocations gets going (this script loops with
   essentially no gap between reps), even a fresh process's first trial
   tends to already be warm. Median of trial 1 across all 12: 81.605.

Taken together, these localize the effect to the **memory subsystem's own
power state** (consistent with uncore/IMC clock-gating on sustained idle),
not cpu0's C-state and not "any activity in the system": what appears to
matter is *recent, substantial* memory bandwidth on the path the victim
uses. A trivial ~64 MB/s busy-spin ticker on a different core is far below
whatever bandwidth threshold matters, which is exactly why the
pre-registered ticker fix failed.

> **⚠️ Mechanism status: open, not settled.** The paragraph above (and
> earlier drafts of this file) stated the fix as "self-generated or
> externally-generated bandwidth is sufficient" without being precise about
> *dose*, and a panel review correctly flagged an apparent contradiction:
> the victim's own ~1.5-2 GB/s of pointer-chase traffic can't be "enough to
> stay warm" if 16.4 GB/s of concurrent aggressor traffic (d_16mb) was
> *insufficient* to fully warm the same victim's single trial. Two follow-up
> checks below narrow this, but the mechanism itself — power-state,
> something else, or a mix — is **not confirmed** and should not be quoted
> in the paper beyond the one mechanism-agnostic methodology sentence in
> the Verdict section.

**Harness archaeology (code-read, not inference)**: `run_e2b_flushbehind.py`
(the pre-correction original) calls the identical `run_victim_once()` —
one `subprocess.run()`, one fresh process, `--trials 1` — from the same
`run_one()` code path for *every* arm, `is_quiescent` or not. There is no
persistent-victim-for-loaded-arms branch. **The lifecycle-asymmetry
hypothesis (loaded arms reusing a warm process, quiescent always cold) is
refuted by direct inspection — the code path is provably identical.**

**Reconciling the dose contradiction**: pulling the actual retained
per-rep values resolves it differently than "the victim's own bandwidth is
enough." `run_quiescent_corrected.py`'s own **trial 0** (self-generated
traffic only, no external aggressor) was itself only *partially* warm —
median 82.22, individual reps as high as 88.85 — not fully warm; only
**trial 1** (after ~4s of trial 0's own accumulated traffic) reaches the
fully-warm ~81.6-81.7 floor. That partial-warm trial-0 value (82.22, or
85.64 in an earlier single run of the same test) sits almost exactly where
`d_16mb`'s original single-trial reading landed (median 85.5) under 16.4
GB/s of *concurrent* aggressor traffic. Read this way, both observations
say the same thing: **a ~4-second window carrying a moderate cumulative
dose (whether self-generated over the window or externally concurrent
during it) produces partial warming, and only a higher dose (23.5 GB/s
concurrent, or waiting through a second full 4s window) reaches full
warming.** This is a graded, cumulative, concurrent-dose response, not a
binary "any activity" switch — consistent with diag 2/3 showing zero
carryover from bandwidth that ends *before* the measurement window starts.
This narrows the candidate mechanisms but does not identify one; "memory
subsystem power state" remains a plausible but unconfirmed label for
whatever integrates dose over the measurement window.

**Floor characterization (per panel request)**: `run_quiescent_4trial_floor.py`,
n=12, all 4 trials recorded per fresh process. Trial 1/2/3 medians:
81.681 / 81.685 / 81.698 — **flat, no further convergence**. The ~0.7-1%
sub-baseline residual seen in the small-D taxes (0.9905-0.9915) is a
**stable plateau relative to trial 1, not a still-converging protocol
floor**. Per the panel's own stated contingency: quote "baseline within
~1%" and stop chasing it.

This also explains the original bimodal pattern end-to-end at the level of
*measurement protocol*, independent of which specific mechanism turns out
to be responsible: E2b's quiescent arm is *always* a single cold-process
trial (zero window dose) → always slow; small-D loaded arms are *always*
accompanied by a concurrent heavy 8-thread aggressor at ~23.5 GB/s (high
window dose) → always fast; `d_16mb`/`d_64mb` sit at a lower concurrent
dose (~16.4/14.8 GB/s) → partially warmed, which is why their originally
reported taxes were the two points that moved the most under correction.
The asymmetry was built into the measurement protocol's *sensitivity to
window dose*, not into flush-behind's mechanism — but the physical reason
dose matters (uncore power state vs. something else) remains open.

## Corrected measurement: matched discard-cold-trial protocol, n=12

`run_e2b_matched_warmup.py`: quiescent and `d_32kb` measured with the
*identical* protocol (`--trials 2 --run-sec 4`, discard trial 0, report
trial 1), interleaved rep-by-rep, same victim placement/WSS as every other
E2b measurement. Full raw data: `/tmp/e2b_matched_warmup_n12.jsonl` (not
yet committed — see below).

| arm | median | range | n |
|---|---:|---:|---:|
| quiescent (warmed) | 81.643 | 81.57-81.89 | 12 |
| d_32kb (warmed) | 81.047 | 80.92-81.15 | 12 |

Distributions are **completely non-overlapping** at n=12.

**tax = d_32kb / quiescent = 0.9927**
**95% paired bootstrap CI (10,000 resamples, seed 12345): [0.9913, 0.9937]**

## Verdict

The panel's core prediction is **confirmed, via a different fix than the
one pre-registered**. The originally reported small-D tax of ~0.90-0.905x
is **retracted as a baseline-measurement artifact**: E2b's quiescent arm was
systematically measured cold (single fresh-process trial, no accumulated
warm-up, no concurrent bandwidth) while every loaded arm was systematically
measured warm (concurrent heavy aggressor), so the "tax" was contaminated by
this fixed ~9-10% asymmetry in baseline state, not a real effect of
flush-behind's mechanism.

The corrected small-D tax is **~0.99x** — a small, real, and now
tightly-bounded residual (CI excludes 1.0), but two orders of magnitude
smaller than the retracted number and consistent with "recovers to baseline
within noise" in the sense the panel used that phrase, not with any genuine
"faster than quiescent" physical effect. The floor characterization above
confirms this ~1% residual is stable (trials 1-3 plateau, not still
converging) — quote "baseline within ~1%," this is not worth further
chasing.

**Paper methodology language (mechanism-agnostic, use this and nothing
stronger)**: "Quiescent baselines are sensitive to idle-state and warm-up
asymmetries relative to co-run measurements; all arms in this sweep use a
matched discard-first-trial protocol to remove this asymmetry." Do not cite
a specific physical mechanism (uncore power state, IMC clock-gating, etc.)
in the paper — see the mechanism-status warning above; it is a plausible,
unconfirmed label, not a validated finding, and the fix's validity does not
depend on it: the matched protocol is correct because it makes measurement
procedure arm-invariant, whether the underlying cause is memory-subsystem
power state, process-local warm-up, or both.

**The claim originally made here — that D=16MiB/64MiB/off taxes "are not
affected by this correction" — is itself retracted below.** That was an
untested extrapolation ("their magnitude already swamps a ~1% baseline
correction"), and the full sweep re-run shows it was wrong for two of the
three points. See the next section.

## Full D-sweep re-run under the matched protocol, n=12

`run_e2b_full_sweep_warmup.py`: every arm (quiescent + all 6 D points)
measured with the identical `--trials 2 --run-sec 4`, discard-trial-0,
report-trial-1 protocol, rep-interleaved, same victim/aggressor placement
and bandwidth/occupancy sampling as `run_e2b_flushbehind.py`. Raw data:
`e2b_full_sweep_warmup_n12.jsonl`.

| config | median (cyc/load) | tax | 95% CI | agg BW (GB/s) | occupancy (MiB) |
|---|---:|---:|---:|---:|---:|
| quiescent | 81.66 | 1.000 | — | — | — |
| d_32kb | 80.97 | 0.9915 | [0.9901, 0.9928] | 23.55 | 6.16 |
| d_256kb | 80.95 | 0.9913 | [0.9901, 0.9921] | 23.55 | 9.88 |
| d_2mb | 80.88 | 0.9905 | [0.9894, 0.9910] | 22.48 | 23.68 |
| d_16mb | 83.12 | 1.0178 | [1.0167, 1.0190] | 16.38 | 53.89 |
| d_64mb | 99.06 | 1.2130 | [1.1982, 1.2363] | 14.83 | 114.34 |
| d_off | 191.18 | 2.3410 | [2.3056, 2.3623] | 23.85 | 233.98 |

Against the originally reported (confounded-baseline) taxes:

| config | original tax | corrected tax | Δ | CIs overlap? |
|---|---:|---:|---:|---|
| d_32kb / d_256kb / d_2mb | 0.902 | ~0.991 | +0.089 | no |
| d_16mb | 0.951 | 1.0178 | +0.067 | **no — sign flip** |
| d_64mb | 1.335 | 1.2130 | −0.122 | no |
| d_off | 2.307 | 2.3410 | +0.034 | yes (barely) |

**Two new, real findings, not just a re-confirmation of the small-D fix:**

1. **D=16MiB flips sign.** Originally reported as *below* quiescent
   (0.951x, "recovering better than baseline"); corrected, it is a small
   but statistically real tax *above* baseline (1.018x, CI tightly
   excludes 1.0). The original number wasn't just imprecise, it pointed
   the wrong way.
2. **D=64MiB's tax shrinks by ~9% relative (1.335x → 1.213x), a materially
   larger correction than quiescent's own ~9% shift alone would produce
   by simple division.** Working the arithmetic backward: the original
   d_64mb raw value must have been ~120.4 cyc/load; the corrected value is
   99.06 — an ~18% drop in the *loaded-arm* reading itself, not just the
   baseline. So the loaded-arm measurement was *also* contaminated by a
   cold-start artifact at this D, not only quiescent.

**Mechanistic explanation for why loaded arms weren't uniformly immune**:
per the bandwidth-threshold hypothesis above, what keeps the victim's
single trial "warm" is *ambient memory bandwidth*, which at small D and at
`d_off` is high (22.5-23.9 GB/s — plenty). At D=16MiB/64MiB, the aggressor's
own bandwidth is markedly lower (16.4 / 14.8 GB/s — this is the same
already-documented non-monotonic dip from clflushopt+sfence overhead
competing with the aggressor's own memory traffic at large D). Lower
ambient bandwidth from the aggressor leaves the victim's own single-trial
measurement more exposed to the same cold-start contamination diagnosed
for quiescent — hence a *disproportionately* large correction exactly at
the two points where aggressor bandwidth itself is lowest. `d_off`'s
aggressor bandwidth (23.85 GB/s) is back in the "high" range, which is
consistent with its correction being the smallest (+0.034, CIs nearly
overlapping) of the three large-D points.

**Updated headline numbers for the paper**: small-D recovery is ~0.99x
(not ~0.90x); D=16MiB shows a small *real* tax (~1.02x, not a sub-baseline
0.95x); D=64MiB's tax is ~1.21x (not 1.335x); full-residency tax (~2.34x)
is essentially unchanged. The aggressor-side non-monotonic bandwidth dip at
16-64MiB (16.4-14.8 GB/s vs ~23.5-23.9 GB/s elsewhere) is untouched by this
correction (aggressor-side measurement, not victim-side) and stands as
previously reported.

## What still needs doing

- **[RESOLVED]** Harness lifecycle archaeology — refuted by direct code
  read, see above.
- **[RESOLVED]** Floor characterization — plateaus at trial 1, see above.
- **[SUPERSEDED — do not rely on this]** "AMD's retained quiescent data
  showed no bimodality on inspection, arguing against the same artifact."
  This reasoning is invalid by construction: on Intel, the confound was
  *never* visible as within-arm bimodality either — quiescent was 100%
  slow, unimodal, and tight across every retained run; loaded arms were
  100% fast, unimodal, and tight. Per-arm distributional inspection is
  exactly the check that passed while Intel's number was wrong by ~10%.
  AMD needs the same matched-warmup re-measurement Intel got, not a
  bimodality look. This is now the top open item — see below.
- **AMD matched-warmup re-measurement (broker), not yet done.** Quiescent,
  WC, best-D flush-behind, and CAT all used the same single-cold-trial
  convention as Intel's original E2b. The highest-stakes number is **WC at
  0.989x** — the quadrilateration anchor claiming type-exempt traffic
  reaches baseline outright. If broker's quiescent baseline carries even a
  few percent of cold inflation, WC's true tax could drift to ~1.05-1.1x,
  softening exactly the claim the paper leans hardest on. (The 6-7x
  convergent floor itself is insensitive to this — a 10% baseline shift
  moves 5.94x to ~6.5x, no qualitative change.) One combined run should
  cover quiescent + WC + best-D flush-behind + CAT + WB under the matched
  protocol, and fold in the still-open Phase 2.4 items in the same pass:
  per-arm aggressor bandwidth from non-MBM counters, victim-side occupancy
  on flush arms, and the 2T-anchor comparison.
- **[RESOLVED] Intel `cat_mba.py` gate delta-check under the matched
  protocol.** Checked directly against the retained raw trial-by-trial CSV
  (`s2_cxl8_baseline.csv`): `cat_mba.py` already runs `--trials 30` within
  *one* continuous victim process per phase (Q or A), not 12 independent
  single-trial fresh processes like E2b's broken design, and reduces to a
  median across all 30. Q-phase trial 0 (82.03) is only mildly elevated
  above the tight 81.56-81.65 plateau of trials 1-29 (~0.5%, nothing like
  E2b's ~10% jump); A-phase shows a real multi-trial ramp-down (195.56 →
  174.95 → 167.42 → ... → ~156-160 plateau by trial ~8) but with 30 trials
  to draw from, the median absorbs it completely: **tax = 1.9458 (all 30
  trials) vs 1.9457 (excluding trial 0)** — a 0.006% difference. The
  4.1% gap to the paper's 2.03x is **not** explained by a cold-baseline
  artifact; `cat_mba.py`'s many-trials-per-process design was already
  structurally immune to the failure mode that broke E2b's single-trial
  design. No revision needed to this gate's numbers.
- **Build the occupancy-vs-tax dose-response plot** from the full-sweep
  data (6.2 / 9.9 / 23.7 / 53.9 / 114.3 / 234.0 MiB occupancy vs. 0.991 /
  0.991 / 0.991 / 1.018 / 1.213 / 2.341 tax) — this is the Intel silicon
  H2 calibration curve for gem5, strictly stronger than any single point
  target.
- Add a baseline-stationarity preflight (standalone vs. warmed quiescent
  comparison) to the campaign's standard methodology before any future
  co-run tax measurement.
- Eventually: a single-protocol regeneration pass over every table
  destined for the paper (matched warmup, baseline-stationarity preflight,
  ticker retired), all measured under one stated, documented convention,
  with provenance manifests — not urgent today, but should happen before
  any of these numbers are finalized for submission.
- Commit `run_quiescent_4trial_floor.py` and its raw data
  (`/tmp/quiescent_4trial_floor_n12.log`) to the repo.
- Update the correction banners in `phase2_pmqos_ticker_RESULTS.md`,
  `e2b_RESULTS.md`, `PHASE2_FINDINGS.md`, `PHASE1_FINDINGS.md`, and
  `OUTCOMES.md` — they currently say only the small-D tax was corrected;
  they need to reflect the d_16mb sign-flip and d_64mb magnitude change too.
