# Pre-registration: ticker-normalized E2b re-run

Dated 2026-08-07, before running. Per the panel's adjudication from retained
raw data (confirmed directly against `e2b_raw_n12.jsonl` and
`e2b_pinned_n12.jsonl`): the original E2b's quiescent arm was **100%
slow-mode** across all 12 reps in both the original and uncore-pinned runs
(89.7-91.8 cyc/load), while `d_32kb` was **100% fast-mode** across all 12
reps in both runs (81.0-81.3 cyc/load). This is a total, systematic
confound, not a rare outlier a median would already absorb -- the backward
arithmetic (81.1 / 0.902 = 89.9) reproduces the reported tax almost exactly
from the two modes' typical values.

## Prediction

If the idle-package-activity-mode story is the explanation: placing a
keep-awake ticker (busy-spin on a spare core, present identically in every
arm including quiescent -- the mechanism already validated in the PM-QoS/
ticker test, `phase2_pmqos_ticker_RESULTS.md`) into **every** arm should
collapse quiescent's mode to match the loaded arms' fast mode, moving
small-D tax from ~0.90x toward **~1.00x** (recovers to baseline within
noise, not "faster than baseline"). D=16MiB/64MiB/off, which already show a
real, large tax overwhelming any ~90-vs-81 mode difference, should be
essentially unaffected by the ticker.

## What would falsify this

If quiescent-with-ticker still shows values distinctly different from
loaded-with-ticker (i.e. the tax ratio stays near 0.90x even with the
ticker present in both arms), the mode-prevalence story is insufficient and
something else specific to flush-behind's mechanism (not just package
activity level) would need to be invoked instead.

## Method

`run_e2b_flushbehind_ticker.py`, ticker on cpu20 for the whole run's
duration (not per-arm -- present continuously, matching "every arm
including baseline" exactly), same D sweep and victim/aggressor placement
as every other E2b run, n=12.
