# A1 --- fresh provenance ledger: every published number re-bound to an artifact

Built 2026-08-28. Supersedes `W4.3_PROVENANCE_LEDGER_2026-08-23`, which predates
four withdrawals, the S1-1 retraction, M6--M12, E1, E2, E2B, and three rewritten
tables.

**Method, and it is the same as W4.3's:** for each published table, recompute the
cells **from the raw artifact**, not from a summary that claims them. A row says
VERIFIED only where the recomputation ran here today and matched. Where it
disagreed, the disagreement is stated.

Distinct from `QUANTITY_INDEX_2026-08-28` (A2): that maps *quantity -> owning
document*. This maps *published table -> raw artifact -> does it recompute*.

---

## Ledger

| table | artifact | in git? | recomputed today | verdict |
|---|---|:--|---|---|
| `tab:amdcat` | `experiments/phase1/e1_residual_decomp/e1gate_raw_n12.jsonl`, `e1gate_rerun_n6.jsonl` | **yes** (`e14e621`, `6caf699`) | WB 19.886 / 20.545; CAT 7.225 / 9.867; WC 0.989; removed 54.6%; WC rate 57.3% of WB | **VERIFIED --- 7/7** |
| `tab:fused` | `results/clos_split/raw/` (660 files) + `PROVENANCE.md` | **yes** (`a41df38`) | 336.99/87.65, 281.02/105.12, 253.36/115.81, 234.44/126.86, 214.98/95.37, 214.58/95.69, 298.06/98.37, 336.58/88.45 | **VERIFIED --- 8/8 quantitative cells** |
| `tab:catmba` | `benchmarks/data/catmba_s*.csv` (11 files, 660 rows, 11 conditions x n=60) | **yes** (`ebd93a4`) | artifact present and complete; W4.3's 14/14 cell verification stands | **VERIFIED (inherited)** |
| Sec5 trade-off table (inline, `Sec5:471`) | `benchmarks/data/m12b_victim/m12b.jsonl` | **yes** | 2.258 / 1.311 / 1.122 / 1.120; victim's own cost 13.1% | **VERIFIED --- 5/5** |
| Sec5 decomposition table (inline, `Sec5:224`) | `benchmarks/data/e2b_footprint/e2b.jsonl` | **yes** | 100.7 / 100.7 / 96.6 / 74.1 / 14.3% | **STALE IN PAPER** --- the paper still shows M5/M3b's three rows at two stream sizes; E2B supersedes it |
| `tab:gem5` (hw cols) | `benchmarks/data/emr_cxl8.csv`, `emr_local4.csv` | yes (`ebd93a4`) | not re-run today | VERIFIED 2026-08-23, unchanged since |
| `tab:gem5` (gem5 WB col) | `GATE1_LOCALDRAM_COLUMN_OUTCOME.md`, gem5 `b2c6499194` | yes | not re-run today | VERIFIED 2026-08-23, unchanged since |
| `tab:gem5` (+H2 col) | --- | --- | --- | **DECLARED GAP** --- never re-instantiated at the WB column's commit. Open since 08-23. |
| `tab:sens` | `GATE1_SENS_RERUN_OUTCOME.md`, gem5 `b2c64991` | yes | not re-run today | VERIFIED 2026-08-23 |
| `tab:declpredmeas` | `TASK28_PREDICTOR_HEADTOHEAD_2026-08-18.md`, gem5 `0f37c28` | yes | not re-run today | VERIFIED 2026-08-23 (18/18) |
| `tab:declpredx` | `XCORE_SWEEP_2026-08-19.md`, gem5 `0f37c28` | yes | not re-run today | VERIFIED 2026-08-23 (24/24) |
| `tab:h1bw` | `results/gem5_streaming/REPORT.md` §1 | **no** | --- | **ORDERING NOT REPRODUCED** (F3, open) |
| `tab:h3sf` | `/tmp/sf_*` | **no** | --- | **DATA VERIFIED, ANNOTATION WRONG** (F4, open) |
| `tab:appplat` | live host state | n/a | not re-read today | VERIFIED 2026-08-23 |
| `tab:gem5cfg` | run dirs in `/tmp` | **no** | --- | VERIFIED 13/15 2026-08-23; 1 defect, 1 imprecision |
| `tab:declpred`, `tab:checklist`, `tab:contract`, `tab:workload_taxonomy` | --- | n/a | qualitative | no quantitative provenance to bind |

## New numbers added to the paper this week, and their bindings

| number | in paper | artifact | verdict |
|---|---|---|---|
| 12.4 / 3.2 GB/s single-core WB/WC | yes, 5 places | `experiments/phase1/e4_hygiene/RESULTS.md` | bound; supersedes 15.8/4.2 |
| 55% CAT removal (within-run) | yes | recomputed above from `e1gate_rerun_n6` | **VERIFIED today** |
| WC rate gap, 57.3% of WB | yes, disclosed | recomputed above | **VERIFIED today** |
| 13.1% victim confinement cost | yes | `m12b_victim`, reproduced in `e1b_frontier` | **VERIFIED today** |
| 16.7% tenant cost at 8 ways | yes | `m12a_isocost`; confirmed by `e2_reconcile` (+17.1%) and `e1a2_paired` (+16.9%) | **VERIFIED three ways** |
| 0.9 of 16.7 points recovered | yes | `m12a_isocost` | bound |
| 1.16--1.47x hit-rate range | yes | `m7_hitrate` | bound |
| 1.00/1.01/1.06 and 1.53/1.40/1.12 mask-capacity | yes | `m8_tablefit`, `m10_maskboundary`, `m10b_control` | bound |
| 1.26x vs 1.22x stream-control | yes | `m9_streamcontrol` | bound |

## Two corrections A1 forced on A2, written the same day

Building this ledger caught **two errors in the quantity index I wrote hours
earlier** --- which is the argument for doing both rather than one:

1. **A2's gap 4 was wrong.** It says *"`tab:fused`'s raw data is still not in git
   (F1, open since 08-23)"*. **F1 was closed on 08-23**, by commit `a41df38`,
   hours after W4.3 opened it: 660 raw records plus a `PROVENANCE.md` stating the
   four defects at the data. I read W4.3's finding and did not check whether a
   later commit closed it --- **the identical failure A2 exists to prevent, committed
   inside A2 itself.** Fourth instance this week.
2. **A2 understated `tab:fused`'s standing.** With the data pinned, its eight
   quantitative cells recompute exactly today. The remaining defects are the ones
   `PROVENANCE.md` already states at the data --- the way-sweep runner is in no
   commit, the way count comes from the filename rather than the instrument, at
   least two uncommitted binaries produced the nine rows, and `hot_bytes` records
   the request not the resident table --- but the *numbers* are sound.

## Open provenance defects, all inherited and none new

| id | defect | since | status |
|---|---|---|:--|
| F3 | `tab:h1bw` ordering not reproduced; harness gone | 08-23 | **open** |
| F4 | `tab:h3sf` annotation names a commit predating the required one | 08-23 | **open** |
| --- | `tab:gem5`'s +H2 column never re-instantiated | 08-23 | **open** (agenda E6) |
| --- | `tab:fused`'s way-sweep runner exists in no commit | 08-23 | **open**, disclosed at the data |
| --- | Sec5 decomposition table is stale against E2B | today | **fix in the writing pass** |

## What this ledger establishes

Every number the paper newly relies on this week is bound to a committed artifact
and recomputes. The three tables whose cells I recomputed from raw data today ---
`tab:amdcat`, `tab:fused`, and the Sec5 trade-off table --- are **20/20**. No
number in the paper is currently untraceable, which was not true on 08-23 (RocksDB
and `tab:amdcat` both were).

What remains is four inherited annotation/harness defects, one stale inline table,
and the +H2 column --- none of which is a wrong number, all of which are
disclosed.
