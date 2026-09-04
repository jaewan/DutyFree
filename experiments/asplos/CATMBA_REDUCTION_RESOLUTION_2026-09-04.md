# Resolution: the "two reductions disagree" open item in tab:catmba

Dated 2026-09-04. Closes the `OPEN ITEM before submission` comment that stood
in `Text/Sec3_Measurement.tex` above the MBA paragraph.

## What the open item alleged

That one campaign reduced two ways gave two different tax families
(1.946x vs 2.03x baseline, and so on down the sweep), and that "one
reduction should win."

## What is actually true

**It is two campaigns, not two reductions, and both have extant raw data.**

| | campaign A | campaign B |
|---|---|---|
| data | `benchmarks/data/catmba_*.csv` | `benchmarks/experiments/results/*/` |
| provenance | committed 2026-06-26 | run 2026-08-06 |
| kernel | 7.0.0-22-generic | 7.0.0-28-generic |
| host | Xeon 8592+ | Xeon 8592+ |
| n | 30 Q + 30 A per arm | 30 Q + 30 A per arm |

Reduced **identically** with `benchmarks/analysis/plot_cat_mba.py`
(`median(A)/median(Q)`, its own formula):

| arm | A tax | A BW | B tax | B BW | paper |
|---|---:|---:|---:|---:|---:|
| s2_quiescent | 1.001 | — | 1.001 | — | — |
| s2_cxl8_baseline | 2.076 | 30.41 | 1.946 | 30.82 | — |
| s3_cat_full | 2.026 | 33.93 | 1.928 | 30.61 | 2.03x @ 34 |
| s3_cat_3ways | 0.994 | 31.89 | 0.993 | 34.22 | 0.99x @ 32 |
| s3_cat_1way | 0.994 | 32.69 | 0.993 | 31.34 | 0.99x @ 33 |
| s4_mba_100 | 2.032 | 28.66 | 1.903 | 34.31 | 2.03x @ 29 |
| s4_mba_30 | 2.038 | 23.95 | 1.889 | 23.20 | 2.04x @ 24 |
| s4_mba_20 | 1.819 | 15.54 | 1.672 | 15.45 | 1.82x @ 16 |
| s4_mba_10 | 1.459 | 8.67 | 1.368 | 8.74 | 1.46x @ 8.7 |
| s5_neg_l2fit | 0.982 | 30.92 | 0.983 | 30.80 | 0.98x @ 31 |
| s5_neg_turnover | 0.995 | 67.41 | 0.995 | 67.50 | 1.00x |

**Every figure printed in the paper is a faithful reduction of campaign A.**
There is no reduction error and nothing to choose between. Campaign B is an
independent replication six weeks later: every ratio within 8.1%, every
bandwidth within 10% except `mba_100` (+19.7%). It is now reported in
`Sec3_Measurement.tex` as a replication result, which strengthens the section.

`experiments/phase1/e2_h1_speed/intel_repro_gate_RESULTS.md` already recorded
campaign B as a **passing** reproduction gate (all 11 conditions, <=15% gate).
The open item's error was reading a passing replication as a self-contradiction.

## The one real defect it half-found — fixed

`tab:catmba` printed **"CAT off, 34 GB/s"** and **"MBA 100%, 29 GB/s"** as if
they were different settings. They are the same physical condition: no mask,
no throttle. Campaign A's three nominally unprotected arms
(`s2_cxl8_baseline`, `s3_cat_full`, `s4_mba_100`) span **2.026-2.076x at
28.7-33.9 GB/s** — that arm-to-arm envelope, not the throttle, separates the
two printed cells.

Checked as a consequence: no comparison in Sec3 crosses that envelope. The
"17% of the stream's bandwidth" MBA claim is 28.66 -> 23.95 GB/s **inside the
MBA sweep**, so it stands as written. The table caption now states the
envelope explicitly.

## Actions taken

- `Sec3_Measurement.tex`: open-item comment replaced with this resolution;
  one body sentence added reporting campaign B as a replication.
- `Appendix.tex` (`tab:catmba`): caption states that the two unprotected rows
  are one condition measured twice, gives the 2.026-2.076x / 28.7-33.9 GB/s
  envelope, and notes that each Sec3 comparison is made within one arm family.
- No printed number changed.
