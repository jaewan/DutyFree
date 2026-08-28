# Pre-registration: the remaining tab:h3sf cells under an unbiased LLC policy

Registered **before** the run. Continuation of the SENSITIVE verdict in
`HNFRP_ROBUSTNESS_OUTCOME_2026-08-28.md` (`6d59635`), whose registered action was
"re-run the gem5 figures that quote a magnitude". That verdict covered only the
infinite-SF `wb` and `h2` cells. This covers the rest.

## What is missing, and what is reused

`tab:h3sf` is 2 (SF) x 3 (mechanism), plus the quiescent denominator per SF
setting. Measured under both policies already (previous batch, absolute paths,
same host): `qui_inf`, `wb_inf`, `h2_inf`. **Those are reused rather than
re-run** --- they are my own runs, from one batch, and gem5 is deterministic under
a fixed seed, so host contention cannot move a simulated counter. What is missing:

| cell | SF | runs |
|---|---|--:|
| `h3_inf` (H2+H3) | infinite | 2 policies x 3 seeds = 6 |
| `qui_fin` | finite | 6 |
| `wb_fin` | finite | 6 |
| `h2_fin` | finite | 6 |
| `h3_fin` | finite | 6 |

**30 runs.** `qui_fin` is measured rather than assumed equal to `qui_inf`, even
though the archive shows them bit-identical, because it is the denominator of the
entire finite row.

## Apparatus

Identical to `HNFRP_ROBUSTNESS_PREREG_2026-08-28.md`: `~/DutyFree-Gem5` at
`356e7b7d0e`, binary built 2026-08-09, `configs/` unchanged since 2026-08-19,
`HNF_RP` read at run time so no rebuild. Arms, from `sf_fin_cells.sh`:

| arm | second workload | `HNF_H3` |
|---|---|--:|
| `qui` | `dummy` | 0 |
| `wb` | `aggressor 16.0` | 0 |
| `h2` | `aggressor 16.0 stream` | 0 |
| `h3` | `aggressor 16.0 stream` | **1** |

`HNF_SF_FINITE` = 0 (infinite) or 1 (finite); `HNF_SF_SETS=4096 HNF_SF_WAYS=16`
(4 MiB / 16-way = 65,536 entries) bind only when finite. `HNF_DMT=0`,
`RUBY_RANDOMIZATION=1`, seeds 1..3. **All workload paths absolute**, matching the
previous batch.

## The three registered quantities

Archived / re-run TreePLRU values, for reference:

| | `wb` | `h2` | `h3` |
|---|--:|--:|--:|
| infinite SF | 1.3689 | 1.0341 | 1.0694 |
| finite SF | 2.5015 | 2.5116 | 1.0610 |

**Q1 --- is H2 inert under a finite SF?** `I = tax_h2_fin - tax_wb_fin`.
TreePLRU: **+0.0101** (H2 very slightly *worse* than WB, i.e. inert). The paper
claims H2 cannot touch the back-invalidation charge.

**Q2 --- does H3 remove the SF charge?**
`R3 = (tax_wb_fin - tax_h3_fin) / (tax_wb_fin - 1)`. TreePLRU: **95.94%**.

**Q3 --- what does H3 cost when there is no SF charge to remove?**
`C3 = tax_h3_inf / tax_h2_inf - 1`. TreePLRU: **3.42%**. This is the source of
the "3.45% at modelled SF" figure the paper attributes to H3.

## Thresholds, and their margin over instrument resolution

Propagated 1-sd at n=3 from the archived per-arm sds:

| quantity | 1-sd | threshold | margin |
|---|--:|--:|--:|
| `I` | 0.00123 | sign change beyond -0.05 | **41 sd** |
| `R3` | 0.0209 pp | 2 pp / 10 pp | **96 sd / 478 sd** |
| `C3` | 0.0382 pp | 1 pp / 3 pp | **26 sd / 79 sd** |

Decision rules, on the change from TreePLRU to LRU:

- **Q1.** If `I_lru < -0.05` --- H2 becomes materially *helpful* under a finite SF ---
  then "H2 is inert against the SF charge" is policy-dependent and must be
  re-stated in the paper. Otherwise the claim stands.
- **Q2.** `abs(dR3) <= 2 pp` ROBUST; `2-10 pp` SENSITIVE (report the LRU figure);
  `> 10 pp` MATERIAL (H3's headline recovery is policy-dependent; escalate).
- **Q3.** `abs(dC3) <= 1 pp` ROBUST; `1-3 pp` SENSITIVE; `> 3 pp` MATERIAL. The
  band is tighter than Q2's because `C3` is itself only 3.42%, so a 2 pp move
  would be a ~60% relative change in a number the paper quotes to three digits.

`C3`'s thresholds are relative to a quantity whose absolute size is small; this
is stated so that a "small" absolute change is not later dismissed as immaterial.

## Predicted direction

**Q1 and Q2: no direction registered.** The finite-SF charge is
back-invalidation from a bounded snoop filter, a different mechanism from LLC
capacity, and I have no sound basis for predicting how a replacement-policy bias
interacts with it.

**Q3: a direction is registered.** The previous batch found that TreePLRU's
protected way group shelters aggressor lines and so *inflates* the infinite-SF WB
tax. `C3` is a ratio of two arms that both decline to allocate the stream
(`h2_inf`, `h3_inf`), so neither benefits from that sheltering, and I expect
`C3` to be **substantially less policy-sensitive than the WB tax was**:
`abs(dC3) < 1 pp`, i.e. ROBUST. **If `C3` moves more than that, this reasoning is
wrong and must be reported as refuted.**

## Instrument check: a per-arm bit-identity prediction

The archived batches split on workload path convention, and the previous batch
established that argv string length shifts the simulated stack and moves
`cyc/access` by ~0.04% (confirmed exactly: a relative-path control reproduced
35.0293 against 35.0160 absolute). Mapping the archive:

| archived arm | convention | source |
|---|---|---|
| `qui_inf`, `wb_inf`, `qui_fin`, `wb_fin`, `h2_fin`, `h3_fin` | **absolute** | uncommitted 2026-08-20 batch (F10) |
| `h2_inf`, `h3_inf` | **relative** | committed `sf_inf_cells.sh` |

This runner uses absolute paths throughout, so:

- **Predicted bit-identical to the archive:** `qui_fin`, `wb_fin`, `h2_fin`,
  `h3_fin` (TreePLRU arms).
- **Predicted NOT bit-identical, by ~0.04%:** `h3_inf`.

A miss on the first group, or a match on the second, falsifies the path-length
explanation and means something else moved --- report it as apparatus drift.
Loose band as a backstop, as before: `max(4 sd, 0.5% of mean)`.

## Liveness assertions

1. All 30 runs must reach `Exiting @ tick`; dead runs are reported, not dropped.
2. Every run's identity is read from its **own** `config.ini` (S5.1): HNF
   replacement policy, presence of the streaming declaration, `HNF_H3`, and the
   snoop-filter geometry (finite vs infinite).
3. The `h3` arms must differ from the `h2` arms **only** in `HNF_H3`, and the
   finite arms from the infinite arms **only** in the snoop-filter bound.
4. `qui_fin` must show `cpu1.numCycles = 0` --- the dummy does no work. The
   archived script's own comment notes this; a nonzero value means the second
   program ran and the denominator is not quiescent.

## Cost

Archived runtimes: `h2_fin` ~4720 s, `wb_fin` ~4460 s, `h3_inf` ~2100 s,
`h3_fin` ~2030 s, `qui_fin` ~740 s. 84,300 s of uncontended CPU. The previous
batch measured throughput at 9-way concurrency as ~4.9 uncontended-equivalent
streams (1.85x per-run slowdown), and the workload is memory-bandwidth bound, so
more concurrency is not expected to raise throughput much. Run at 16-way,
**longest job first** to minimise the tail. Expected wall clock **~5 h**. No
silicon time.
