# Remaining tab:h3sf cells: Q1 holds, Q2 ROBUST, Q3 SENSITIVE and my registered prediction is refuted

Pre-registration `HNFRP_REMAINING_CELLS_PREREG_2026-08-28.md` (`5036cec`); runner
and analyzer `b7686ff`, both committed before the data. 30/30 runs reached
`Exiting @ tick`.

## The completed 2x3 design, both policies

`cyc/access`, n=3 seeds per cell, sd in the analyzer output.

| policy | SF | qui | wb | h2 | h3 |
|---|---|--:|--:|--:|--:|
| TreePLRU | infinite | 33.8814 | 46.3800 | 35.0358 | 36.2510 |
| TreePLRU | finite | 33.8814 | 84.7541 | 85.0959 | 35.9474 |
| **LRU** | infinite | 33.8814 | 45.2764 | 35.1905 | 36.7850 |
| **LRU** | finite | 33.8814 | 84.7410 | 85.1286 | 36.1946 |

As taxes:

| policy | SF | wb | h2 | h2+h3 |
|---|---|--:|--:|--:|
| TreePLRU | infinite | 1.3689 | 1.0341 | 1.0699 |
| **LRU** | infinite | **1.3363** | **1.0386** | **1.0857** |
| TreePLRU | finite | 2.5015 | 2.5116 | 1.0610 |
| **LRU** | finite | **2.5011** | **2.5125** | **1.0683** |

The quiescent arm is **identical across all four rows** --- both policies and both
SF settings, bit-identically per seed. It should be: a 2.59 MiB victim fits the
5 MiB HNF, so nothing is evicted and neither the policy nor the SF bound is ever
consulted.

## Verdicts against the registered thresholds

| | quantity | TreePLRU | LRU | delta | verdict |
|---|---|--:|--:|--:|---|
| **Q1** | `I = tax_h2_fin - tax_wb_fin` | +0.0101 | +0.0114 | --- | **H2 stays inert under a finite SF; the paper's claim holds** |
| **Q2** | `R3`, H3's recovery of the SF charge | 95.94% | 95.45% | **-0.49 pp** | **ROBUST** |
| **Q3** | `C3`, H3's cost with no SF charge | 3.47% | **4.53%** | **+1.06 pp** | **SENSITIVE --- registered prediction REFUTED** |

### Q3: the prediction I registered was wrong

I registered `abs(dC3) < 1 pp` with an explicit rationale: `C3` is a ratio of two
arms (`h2_inf`, `h3_inf`) that **both** decline to allocate the stream, so
neither benefits from the way-sheltering that inflated the WB tax, and the ratio
should therefore be insensitive to the policy. Observed **+1.06 pp** --- past the
threshold by 0.06 pp. **The reasoning is refuted and is recorded as refuted.**

Why it failed, stated as a hypothesis rather than a finding: the two arms decline
to allocate at *different levels*. H2 declines at the HNF only; H2$+$H3 also
declines at L1/L2, so the H3 arm's traffic reaches the HNF in a different pattern
and its **victim's** lines are exposed to the biased policy differently. The
arms are not symmetric with respect to the LLC after all. Not tested.

The practical consequence is small and specific: **H3's cost is 4.53%, not
3.45%** --- 31% larger than the paper stated.

### Q1 and Q2: the finite-SF row barely moves

`wb_fin` 2.5015 -> 2.5011 and `h2_fin` 2.5116 -> 2.5125 under a policy change
that moves the infinite-SF WB tax by 2.4%. Mechanically sensible: when a bounded
snoop filter is the binding constraint, LLC replacement quality is nearly
irrelevant. **The finite-SF conclusions are policy-independent; the infinite-SF
magnitudes are not.**

## Instrument check: 5/5, and the path-length explanation is confirmed

The registered per-arm bit-identity prediction, derived from the archive's
absolute-vs-relative workload-path split:

| arm | archived convention | predicted bit-identical | observed | verdict |
|---|---|---|---|---|
| `qui_fin` | absolute | yes | **yes** | PASS |
| `wb_fin` | absolute | yes | **yes** | PASS |
| `h2_fin` | absolute | yes | **yes** | PASS |
| `h3_fin` | absolute | yes | **yes** | PASS |
| `h3_inf` | **relative** | **no** | **no** | PASS |

Five for five. `argv` string length shifts the simulated stack and therefore
`cyc/access` by ~0.04%, and it is now a **predictive** model of this apparatus,
not a post-hoc explanation.

## An analyzer defect found and fixed

On partial data the bit-identity check printed `** PREDICTION FALSIFIED **` for
`qui_fin`, because it requires the full seed triple and only two had landed --- a
2-seed mean legitimately differs from a 3-seed archived mean. It now reports
`bit-identity NOT EVALUABLE yet`. **A false alarm in a verification harness is the
same defect class as a criterion a crashed run can satisfy**, and this campaign
has now produced one of each.

## Host-runtime anomaly, recorded and unexplained

The first 16 runs took **exactly** their archived host time (factor 1.00x, n=18)
at 16-way concurrency, so concurrency is not the constraint. The remaining 12 ran
**1.3--2.5x** longer, at 100% CPU with verified forward progress. Not contention,
not NUMA placement (slow runs appeared on both nodes). Partly legitimate --- the
LRU `h3` arms have a higher tax and so simulate more cycles --- but **seed-
dependent in a way nothing here explains**: `qui_fin_treeplru` s1 and s2 finished
in 12 min while s3 took over 34, same binary, same configuration, seed the only
difference. Results are unaffected (gem5 is deterministic under a fixed seed);
only wall clock is. Worth a look given this project has a documented CHI
arbitration livelock, but these runs terminated normally.
