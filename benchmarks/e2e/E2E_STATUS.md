# E2E status

Updated 2026-08-21. The CAT capacity-sensitivity gate that had blocked this
campaign since 2026-08-11 has run on three hosts and two victims.

**Victim: GAPBS PageRank at `-g 21` on `moscxl` (AMD EPYC 9754) only.** It is
the sole configuration to pass a capacity-sensitivity gate: 2.580x, against a
2x bar, at CoV within bounds and robust across the whole observed spread
(2.561--2.794x). Both Intel hosts fail at every scale measured -- `mos181`
1.10--1.31x, `mos182` 1.34--1.43x, at CoV under 0.25%. The pre-registered
alternative victim, HNSW, was built and gated rather than assumed and fails on
every host including AMD (1.257--1.325x).

So the real-application arm is single-vendor whichever candidate victim is
chosen. That is now a measured statement, not a fallback. It does not touch the
paper's cross-vendor claim, which §2 rests on CAT/MBA on Intel plus a way sweep
and a non-allocating aggressor on AMD.

| bar | status |
|---|---|
| magnitude | **capacity-mediated tax ceilinged below 2x on both Intel hosts; passes on AMD at g21** |
| reproducibility | gate CoV 0.02--0.25% on Intel; `mos181` g22/g24 reproduce the 2026-08-11 sizing gate to ~0.1%; `moscxl` full-mask arm bimodal, three causes eliminated, selection unaffected |
| recovery | unmeasured |
| frontier | preregistered; unmeasured |

## Before any co-run arm is taken

1. **Use an even measured trial count.** `pr -n 4` less a warm-up leaves three
   trials, an odd sample of a two-phase signal that alternates ~9% on
   `moscxl`; the tax ratio would carry the bias on both sides. `-n 5` or `-n 7`.
2. **Verify the MBM counter is live before invalidating an arm for zero
   streamer traffic.** On AMD under resctrl group churn the counter returns
   stale values -- PageRank's traffic samples in the gate are unusable for
   exactly this reason, while HNSW's are sound.
3. **Re-freeze `moscxl`, or disclose that it is not frozen.** It has run
   `schedutil` with boost on since a 2026-08-19 reboot, and no AMD platform
   state has ever been captured. See
   `../../experiments/asplos/AMD_PLATFORM_STATE_PROVENANCE_2026-08-21.md` and
   the new `../setup/bergamo_freeze.sh`.

## Documents

- `gapbs/GAPBS_CAT_SENSITIVITY_OUTCOME.md` -- result, both falsified
  predictions, the three eliminated variance causes, and the consequences
- `gapbs/GAPBS_CAT_SENSITIVITY_RUN_DECISIONS.md` -- every departure, written
  before results were read
- `hnsw/HNSW_CAT_SENSITIVITY_OUTCOME.md` -- why HNSW fails, and why halving a
  victim's DRAM traffic bought only a third more runtime
- `gapbs/GAPBS_SIZING_OUTCOME.md` -- the earlier, superseded `-g 22` selection
- `gapbs/GAPBS_DUCKDB_CORUN_PREREGISTRATION.md` -- the campaign itself,
  unstarted
