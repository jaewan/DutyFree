# A2 --- the quantity index: for every number the paper cites, the document that owns it

Built 2026-08-28. **This document is the answer to a specific, repeated failure**,
not general hygiene.

## Why it exists

Three times this week an argument was built on a committed number whose
interpretation a later committed document had already replaced:

| # | the number quoted | superseded by | cost |
|---|---|---|---|
| 1 | "no deployed alternative protects the neighbour" (L5) | `W5.3_L5_EVIDENCE_2026-08-23` --- five days earlier | told the lead twice that the AMD host was the critical path when it was not |
| 2 | "residency is 27% of harm, 73% is transport" (`M3B_OUTCOME_2026-08-25`) | `M5_OUTCOME_2026-08-26` --- the next day | produced red-team finding S1-1, which reversed a correct statement in five places before being retracted |
| 3 | "the label has no winning cell" (`M6_OUTCOME`) | `M11_OUTCOME_2026-08-28` | overshot the panel's own branch on the strength of an n=3 arm |

The mechanical cause is the same each time and is visible in one measurement:
searching the corpus for a load-bearing quantity returns **between 3 and 22
documents**, most of which cite it and one of which measured it. Picking wrong is
not a lapse of care, it is the default outcome of 133 files with no index.

**The rule this enforces:** before a cross-document number enters an argument,
look it up here. If it is not here, add it here first.

## How to read the table

- **Owner** = the document that most recently *measured* the quantity. Not the
  most recent to *mention* it.
- **Superseded** = earlier owners whose value or interpretation no longer holds.
  Citing one of these is the failure above.
- **In paper?** = whether the live `.tex` currently carries it.

---

## Neighbour-side quantities (the paper's spine)

| quantity | current value | owner | superseded | in paper? |
|---|---|---|---|:--|
| unmitigated neighbour harm, fused tenant, 128 MiB table, 1 GiB stream | **2.258x** | `M12_OUTCOME_2026-08-28` (n=10) | --- | yes |
| harm with the stream non-allocating | **1.311x** (75% removed) | `M12_OUTCOME_2026-08-28` | --- | yes |
| harm under an 8-way mask | **1.122x** | `M12_OUTCOME_2026-08-28`, reproduced `E1_OUTCOME_2026-08-28` | --- | yes |
| harm with mask **and** label | **1.120x** (composition = 1%) | `M12_OUTCOME_2026-08-28` | --- | yes |
| neighbour's own confinement cost, 12 ways, 170 MB | **13.1%** | `E1_OUTCOME_2026-08-28` pass B (n=6), reproduces M12's exactly | --- | yes |
| neighbour harm *given* an enforced partition, any split | **0.988--0.994x** (undetectable) | `E1_OUTCOME_2026-08-28` pass B | --- | **no --- should be** |
| confinement cost vs partition occupancy | **~0% below 2/3 full; 10.8% at 75%; 13.1% at 89%; 65% at 133%** | `E1_OUTCOME_2026-08-28` pass B, 15 cells | --- | **no --- should be** |
| Intel victim tax, pure streamer, EMR | **2.03x** | `benchmarks/data/catmba_s*.csv` via `W4.3_PROVENANCE_LEDGER_2026-08-23` (VERIFIED 14/14) | --- | yes |
| Intel CAT sufficiency, pure streamer | **1.00x at 0.7% streamer BW** | `W5.3_L5_EVIDENCE_2026-08-23` | --- | yes (§controls) |

## Tenant-side quantities

| quantity | current value | owner | superseded | in paper? |
|---|---|---|---|:--|
| tenant cost at 8 of 20 ways, 128 MiB table | **+16.9%** (median of 10 pairs) | `E1_OUTCOME_2026-08-28` addendum (pass A2) | `M12_OUTCOME` +16.7% and `E2` +17.1% agree; **`E1a`'s +8.7% is VOID** (amendment 1) | yes (16.7%) |
| tenant cost across widths 2/4/8/12/16 | **+43.2 / +41.5 / +16.9 / +2.1 / +0.3%** | `E1_OUTCOME_2026-08-28` addendum | **`E1a`'s +32.7/+24.7/+8.7/+1.3/+0.0% VOID**; M10/M10b's sweep used `--reps 1` and a different statistic | partly (17--41%) |
| **bimodality of the masked arm** | two stable modes at widths 2--8; spreads 19.0 / 15.4 / 7.9%; unimodal at 12--16 | `E1_OUTCOME_2026-08-28` addendum | --- | **no --- must be disclosed** |
| tenant's own table: what the label recovers | **0.9 of 16.7 points** | `M12_OUTCOME_2026-08-28` pass A (CoV 0.28%) | supersedes M9's unresolvable difference-of-differences | yes |
| split-restructuring cost | **36% of throughput** | `results/clos_split/` --- **in git** (`a41df38`), 8/8 cells recomputed by `A1_PROVENANCE_LEDGER_2026-08-28` | --- | yes |
| **tenant's confinement cost vs occupancy** | 0% at 57--67%, **15--17% at 100%**, 41--57% beyond --- **host-invariant** | `E4_OUTCOME_2026-08-28` (mos182) + `E1_OUTCOME_2026-08-28` addendum (mos181) | --- | **no --- this is the claim the paper should carry** |
| victim's confinement cost vs occupancy | agrees below 60% and above 120%; **diverges in the 75--90% band** (13.1% mos181 vs 0.3% mos182) | `E3_OUTCOME_2026-08-28` + `E1_OUTCOME` pass B | --- | **no --- must name its host wherever used** |
| ~~the 2/3 occupancy knee as one curve~~ | **WITHDRAWN** --- two curves, two access patterns | `E4_OUTCOME_2026-08-28` | E1's "one curve from both sides"; E3's "platform-specific coefficient" | no |
| free-split condition | **no split on either host** --- tenant needs 1.5x its table on both, victim 1.6x / 1.15x | `E4_OUTCOME_2026-08-28` | E1's "<= 2/3 x LLC" **as a law** | **no --- should be** |

## AMD quantities (one unreachable host)

| quantity | current value | owner | superseded | in paper? |
|---|---|---|---|:--|
| same-CCX WB tax | **19.89x** (n=12) / **20.55x** (n=6 rerun) | `experiments/phase1/e1_residual_decomp/e1gate_raw_n12.jsonl`, `_rerun_n6.jsonl` | **19.85x** (untraceable `/tmp/task1_raw.jsonl`) | yes |
| CAT 8/8 residual | **9.87x** (n=6) / **7.23x** (n=12) --- both disclosed | same artifacts | **6.92x** | yes |
| tax removed by CAT | **55%** (within n=6) / **67%** (within n=12) | recomputed in `REDTEAM_REVIEW_2026-08-28` S1-4 | **53%** --- a cross-run pairing, and the value least favourable to CAT | yes (55%) |
| WC arm | **0.99x, but at 13.84 GB/s vs WB's 24.13** | `e1gate_raw_n12.jsonl`; rate gap found in `REDTEAM_REVIEW_2026-08-28` S1-3 | the undisclosed-rate version | yes, now disclosed |
| **`n=6` rerun's WC arm** | **VOID** --- moved 0.0108 GB/s | `REDTEAM_REVIEW_2026-08-28` S1-4 | --- | no |
| single-core WB / WC bandwidth | **12.43 / 3.20 GB/s** (n=12) | `experiments/phase1/e4_hygiene/RESULTS.md` | **15.8 / 4.2 GB/s** --- was live in five places until 08-28 | yes |
| E1 dissociation | **+28% (20.4 GB/s WB) vs +0.3% (15.1 GB/s WC)** | `E1_ARM_IDENTITY_AUDIT_2026-08-24` | *"the CXL traffic is identical"* --- **WITHDRAWN**, arms are thread-matched not rate-matched | yes, disclosed |
| MBA knife edge | **12.44x at a 28 GB/s cap -> 1.08x at 24 GB/s**, i.e. 96% of full BW | `W5.3_L5_EVIDENCE_2026-08-23` | --- | **no --- should be; it is leg two of the case** |

## gem5 quantities

| quantity | current value | owner | superseded | in paper? |
|---|---|---|---|:--|
| model WB tax vs hardware | **1.60x vs 2.61x --- 39% low** | `GATE1_LOCALDRAM_COLUMN_OUTCOME` | --- | yes |
| H2 recovery at infinite SF | **90.9%** of the charge | `W1.5_H3_INFINITE_SF_OUTCOME_2026-08-24` (also `W1.4`, `W1_OUTCOME`) | --- | yes |
| H3 cost over H2 alone | **3.45%** (a cost, not a gain) | `W1.5_H3_INFINITE_SF_OUTCOME_2026-08-24`; case in `W3.4` | --- | yes |
| direction of the model's bound | **lower bound on both tax and recovery** | `REDTEAM_S1-1_RETRACTION_2026-08-28` | **"upper bound"** --- S1-1, retracted; it rested on the superseded 27% | yes, corrected |
| what the model structurally cannot represent | congestion latency (`SimpleMemory`, `latency_var=0`) | `GEM5_TRANSPORT_CHECK_2026-08-26` | --- | yes, as a caveat |
| `tab:gem5` +H2 column | **DECLARED GAP** --- never re-instantiated at the WB column's commit | `W4.3_PROVENANCE_LEDGER_2026-08-23` | --- | yes, with the gap disclosed |

## The victim decomposition --- **one stream size as of E2B**

Owner for the whole table: **`E2B_OUTCOME_2026-08-28`** (n=8, 1 GiB stream, hit
rate 0.5, no mask, instrument check passed).

| tenant's own table | harm removed | superseded value |
|---|--:|---|
| 4 MiB | **100.7%** | M5's 100.5% --- reproduces across a 4x stream change *and* a hit-rate change |
| 16 MiB | **100.7%** | new point |
| 64 MiB | **96.6%** | new point |
| 128 MiB | **74.1%** | M12's 75.3% --- matched conditions, reproduces |
| 256 MiB | **14.3%** | M3b's 28.0% --- **does not reproduce**; two variables differ (stream *and* hit rate), so the gap is recorded unattributed |

**Interpretation owner is `M5`, and the data owner is now `E2B`, not `M3b`.** M3b's own title claims the residue is
"bytes in flight and no admission-control mechanism can reach it"; M5 shrank the
tenant's table and the residue vanished, so the residue is **the tenant's own
resident data**. Citing M3b's framing is failure #2 above. E2 on the agenda would
put all three rows on one stream size.

## Withdrawn outright --- cite none of these

| withdrawn | why | recorded in |
|---|---|---|
| 1.47x fused-versus-quiescent tax | two different loops (hit rate 0.5 vs 1.0, plus a hardware `div`) | `Sec3_Mitigation` + `A4_HITRATE_FINDING_2026-08-24` |
| the split's "negative recovery" | inherits the same mismatch | same |
| RocksDB 2.33x / 54% | untraceable; nearest survivor disagreed | `W4.3_PROVENANCE_LEDGER_2026-08-23` |
| "the way sweep measures label scope" | it measures a 256 MiB table against a 64 MiB mask | `M8`, `M9`, confirmed `M10_OUTCOME_2026-08-28` |
| "the hit-rate caveat" (penalty specific to hr 0.5) | swept; penalty is *largest* at hr 1.0 | `M7_OUTCOME_2026-08-26` |
| M6 pass A's +2.9% / +7.5% | n=3 at an operating point with +/-15% resolution | `M11_OUTCOME`, `M11B_OUTCOME_2026-08-28` |
| "169.6 MiB" as the fused table | requested size; **256 MiB** is instantiated | `Appendix` + `T3_CODE_AUDIT_2026-08-24` |
| "the Intel side has no quantitative result in the label's favour" | estimator confounded 6.5x over its signal | `REDTEAM_REVIEW_2026-08-28` S3-8 |
| S1-1 (gem5 bound reversed) | rested on M3b's superseded 27% | `REDTEAM_S1-1_RETRACTION_2026-08-28` |
| E1a's tenant column | bimodal; low at every width | `E1_FRONTIER_PREREG` amendment 1 |

## Gaps this index exposes

Compiling it surfaced five things, which is the point of compiling it:

1. **Four of E1's strongest results are not in the paper at all** --- the
   undetectable harm under any enforced partition, the occupancy curve, the 2/3
   knee, and the free-split condition. These are the newest and best-supported
   numbers we have.
2. **The masked arm's bimodality is in no paper text**, and it must be, because
   individual runs of a published cell do not reproduce even though medians do.
3. **MBA's knife edge is not in the paper**, though it is one of the three legs
   the surviving case rests on.
4. ~~**`tab:fused`'s raw data is still not in git**~~ --- **WRONG WHEN WRITTEN.**
   F1 was closed on 2026-08-23 by commit `a41df38`, hours after W4.3 opened it:
   660 raw records plus a `PROVENANCE.md` stating four defects at the data. I read
   W4.3's finding and did not check for a later commit closing it --- **the exact
   failure this index exists to prevent, committed inside this index.** Corrected
   by `A1_PROVENANCE_LEDGER_2026-08-28`, which also recomputes all eight of
   `tab:fused`'s quantitative cells from that data and finds them exact. What
   remains open there is the *runner* and *binaries*, not the numbers.
5. ~~**The victim decomposition mixes two stream sizes**~~ --- **CLOSED** by
   `E2B_OUTCOME_2026-08-28`: five points, one stream size, one hit rate, all four
   registered predictions held. The paper's dagger can come out.
