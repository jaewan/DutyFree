# E4 hygiene — RESULTS

Dated 2026-08-06.

## Config

- Host: `broker` (AMD EPYC 9754), governor=performance, turbo=off, n=12
  rep-interleaved per experiment, resctrl groups cleaned up after each run.
- Scripts: `run_wc_reconciliation.py`, `run_matched_bw_pair.py`.

## AMD per-core WC/WB bandwidth reconciliation

Question from the mission: why does WC per-core bandwidth show ~4.2 GB/s in
one context and ~1.8 GB/s in another? Measured {WB,WC} x {1T,7T} x
{same-CCX, spread-across-7-different-CCXs}, n=12:

| config | median bw (self-report) | 95% CI | median bw (MBM) | per-core (self) |
|---|---:|---:|---:|---:|
| wb_1t_same | 12.434 | [12.434,12.438] | 12.431 | 12.434 |
| wb_7t_same | 24.136 | [24.118,24.163] | 23.786 | 3.448 |
| wc_1t_same | 3.203 | [3.202,3.203] | 3.273 | 3.203 |
| wc_7t_same | 13.846 | [13.845,13.849] | 14.270 | 1.978 |
| wb_1t_spread | 12.413 | [12.410,12.415] | 12.381 | 12.413 |
| wb_7t_spread | 24.424 | [24.395,24.437] | (see caveat) | 3.489 |
| wc_1t_spread | 3.204 | [3.203,3.204] | 3.262 | 3.204 |
| wc_7t_spread | 20.511 | [20.489,20.529] | (see caveat) | 2.930 |

**Caveat on the "spread" MBM column**: summing `mbm_total_bytes` across all 7
domains simultaneously under-reports by roughly half relative to
self-report (e.g. wb_7t_spread MBM=10.67 GB/s vs self-report 24.42 GB/s) --
this reproduces cleanly and is not a script bug (single-thread-per-domain
reads agree with self-report to <1%; only the *simultaneous multi-domain
sum for one RMID* is affected). Treated as a platform/kernel limitation on
this AMD box, not silently corrected -- self-reported aggregate bandwidth is
the trusted metric for the spread configs.

**Answer to the reconciliation question**: WC per-core bandwidth is heavily
sensitive to CCX placement -- packing 7 WC threads into one CCX drops
per-core bandwidth from 3.20 (1T) to 1.98 GB/s/core (-38%), while spreading
those same 7 threads across 7 different CCXs only drops it to 2.93 GB/s/core
(-8.5%). **WB shows no such sensitivity**: 7T-same (24.14 GB/s) and 7T-spread
(24.42 GB/s) are within noise of each other. This is itself a finding: WB's
aggregate ceiling looks bound by something link/device-side that doesn't
care about core placement, while WC hits a CCX-local bottleneck (plausibly
the local crossbar/fabric port from one CCX toward the CXL-facing fabric
endpoint, or shared non-temporal-store-buffer/WC-buffer resources) that only
binds when multiple WC streams share a CCX.

## Single-core WB/WC bandwidth vs the paper's 15.8/4.2 GB/s

Measured (n=12, same machine as the E1 gate that reproduced within
0.2-4.4%): **WB 12.43 GB/s [12.43,12.44], WC 3.20 GB/s [3.20,3.20]** — both
placements (same-CCX, spread) agree with each other to within 0.2%, so this
isn't a placement artifact. **This is a genuine ~21-24% gap from the paper's
stated 15.8/4.2 GB/s, on the exact machine where the co-run tax numbers
(19.85x/6.92x/1.02x) reproduced almost exactly.** Not one of the mission's
explicitly-designated repro gates, and E4's own purpose here is to report
these numbers with CI — the mismatch itself is the reportable finding, not
grounds to halt. Plausible explanations not disambiguated here: measurement
context (buffer size/duration not specified in the paper for this claim),
thermal/background-load drift on a 79-day-uptime shared machine, or a
genuine hardware/firmware change since the original measurement. Flagged
for `PHASE1_FINDINGS.md`, not resolved.

## Matched-bandwidth AMD pair (+28%/+0.3%), diff-CCX placement

`Sec2_DirectoryTax.tex:43-49`: aggressor on a neighbor CCX, WB imposes +28%,
WC imposes +0.3%, at a matched ~20.9 GB/s. Pilot found WB is insensitive to
same-CCX packing (2 threads packed into one neighbor CCX already hit the
target) but WC is not (packing WC threads into one CCX caps well below
20.9 GB/s per the reconciliation finding above) -- so WB uses 2 threads
packed into CCX1 (cores 8,9), WC uses 5 threads spread one-per-CCX (cores
8,16,24,32,40) to avoid that packing penalty, per the same-CCX-vs-spread
mechanism found above. n=12, rep-interleaved with quiescent baseline.

| arm | median tax | 95% CI | paper | agg bandwidth (median) |
|---|---:|---:|---:|---:|
| WB, 2T, diff-CCX | 1.2877x | [1.2790,1.3095] | 1.28x (+28%) | 20.363 GB/s |
| WC, 5T, spread | 0.9996x | [0.9879,1.0136] | 1.003x (+0.3%) | 15.137 GB/s |

**The tax numbers reproduce almost exactly** (1.288x vs 1.28x; 0.9996x vs
1.003x, both well inside CI of the paper's figures). **The bandwidths do
not fully match each other or the paper's implied ~20.9 GB/s target**: WB
reaches 20.36 GB/s (close, -2.6%), but WC only reaches 15.14 GB/s (-27.6%
short of WB's rate) -- consistent with the same ~21-24% single-thread WC
gap found above (measured single-core WC here is ~3.20 GB/s vs the paper's
implied ~4.2 GB/s; 5 threads at ~3.0 GB/s/core lands at ~15 GB/s, not ~21).

**Overall pattern across E4**: every AMD *tax/ratio* number reproduces
tightly (E1's 19.89x/7.23x/0.99x gate, and this pair's 1.288x/0.9996x). Every
AMD *absolute single-core bandwidth* number runs ~21-27% below the paper's
figures (WB 12.43 vs 15.8, WC 3.20 vs 4.2, and the derived 5T-spread WC rate
here). This is a coherent, systematic pattern worth carrying into
`PHASE1_FINDINGS.md` as its own finding: the mechanism/physics the paper
argues from is robustly reproducible on this hardware; the absolute
bandwidth scale is not, for reasons not disambiguated in this pass
(candidates: unspecified buffer-size/duration in the paper's original
single-core measurement, thermal/background-load drift on this 79-day-uptime
shared machine, or a genuine change in the CXL path since then -- this
machine's own CXL device has *not* been found swapped, unlike the EMR host,
but that does not rule out other drift).
