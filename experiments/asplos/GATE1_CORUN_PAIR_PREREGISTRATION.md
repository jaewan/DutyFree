# Pre-registration: co-run pair re-run (tab:gem5)

Dated 2026-08-09, before running. Per ruling: this is the sharpest,
weakest-provenance, most load-bearing gem5 number in the dataset
(demonstrates the enforced `setstreaming` path end-to-end) — re-run it
first, give it its own table, and settle the "1.34 vs 2.57" anomaly as
part of this run rather than as a separate Gate 2 arm.

## Operating point (documented explicitly, per ruling)

- Aggressor: `testcase/dirtax/aggressor` (the `wb` tag in `b4run.sh`), 1
  aggressor thread/core.
- Memory latency class: to be confirmed from this run's own
  `gate1_manifest.py` output — `b4run.sh`'s `COMMON` config instantiates
  two `SimpleMemory` controllers (98 ns local, 203 ns CXL per prior runs
  this session), but which one the aggressor's allocation actually lands
  in is not yet confirmed by direct inspection, only inferred from the
  paper's own framing ("a single CXL-latency aggressor"). This run's
  manifest will settle it, not assume it.
- Victim WSS: `2650` (KiB, per `b4run.sh`'s hardcoded `WSS=2650`) — the
  paper's stated "53% LLC" point (2650/5120 KiB $\approx$ 51.8%, close
  enough to 53% to be the same point modulo rounding/an old LLC-size
  assumption).
- LLC: confirmed genuinely 5 MiB shared (this session, `alone` config,
  same `COMMON` string).
- Achieved fill rate: to be read from this run's own aggressor-side
  bandwidth stat, not assumed.

## Prediction (falsifiable, stated before running)

At this operating point — 5 MiB shared LLC, single aggressor, victim at
~53% LLC — **the WB co-run tax should land near the old prose-cited
1.34x (a mild-pressure operating point), not near tab:gem5's tabulated
2.57x (the high-fill-rate, local-latency calibration point)**, *if* the
prose's 1.34x reflects this same CXL-latency-aggressor configuration and
the table's 2.57x reflects a different (e.g. local-DRAM-latency,
higher-fill-rate) calibration run.

## What would falsify this / what each outcome means

- **Lands near 1.34x**: the "1.34 vs 2.57" anomaly closes as two
  legitimate operating points on one pressure curve, not a bug — prose
  and table were both right, just about different configs, and
  `\cref{tab:gem5}` in the prose is simply the wrong cross-reference (it
  should point to a description of the mild-pressure point, not the
  table showing the high-fill-rate one). Paper fix: correct the
  cross-reference, add a one-line statement of each experiment's
  occupancy-pressure ratio (bandwidth achieved / LLC capacity or
  similar), and Gate 2's original "10 MiB explains 1.34x" hypothesis is
  retired as moot — no need to run it as a separate arm.
- **Lands near 2.57x**: the prose's 1.34x is unexplained by operating-
  point difference alone — something else changed (stale number from an
  earlile config, a real regression, or a config this session hasn't
  found). Do not write a text-fix in this case; escalate to a dedicated
  investigation before touching the paper.
- **Lands somewhere else entirely**: report exactly what and treat this
  finding as gates the whole tab:gem5 reconciliation, not just this one
  cross-reference.

## H2 recovery, secondary check

The `st` tag (same operating point, `PROT_STREAMING`-tagged /
`setstreaming`-tagged stream) should return the victim close to baseline
(the paper's own +H2 column claims 1.00x at every LLC-fraction row) —
already have both `st` runs from this session's Gate 0 follow-up
(`/tmp/st_postmerge/stats.txt`, `/tmp/st_premerge/stats.txt`, both
byte-identical to each other), so this doesn't need a fresh run, just
extraction of the actual tax number from the already-collected data.

## Method

Run `b4run.sh corun_wb_v2 wb 0 0` (WB baseline) at current `streaming`
HEAD (`23f27375e9`+`a309523389`), with `gate1_manifest.py` attached.
Extract the H2/`st` tax from already-collected data
(`/tmp/st_postmerge/stats.txt`). Tag the result `table-corun-v2` in the
gem5 repo once confirmed.
