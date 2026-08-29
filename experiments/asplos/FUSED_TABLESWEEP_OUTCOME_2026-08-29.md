# Table sweep outcome: the wedge is real but bounded, and H2's protection collapses as the tenant's own footprint grows

Pre-registration `FUSED_TABLESWEEP_PREREG_2026-08-29.md` (`19a3cef`). 36 runs
plus a 9-run completion at 8 MB. **Two findings, one about the mechanism and one
about our own instrument.**

## Instrument first: the sweep was mislabelled (F9, fourth instance)

`fused.c` rounds the table down to a **power-of-two element count** --- my own
code, for the mask-based probe index. It is silent, and it collapsed the sweep:

| requested | realized |
|---|---|
| 1 MB | 1 MB |
| 2 MB | 2 MB |
| **3 MB** | **2 MB** |
| 4 MB | 4 MB |
| **6 MB** | **4 MB** |

Five requested sizes measured **three** distinct tables. Worse, **the headline
"36.53% at a 3 MB table" in `H2H_FUSED_OUTCOME_2026-08-29.md` was measured at a
2 MB table.** The number is correct; its label was not.

This is F9 a fourth time, after `--hot-bytes 177838489` -> 256 MiB. I wrote the
rounding, documented it in the source, then designed a sweep whose points
collapse under it --- and **liveness assertion 3 checked the *requested* size from
the command line**, which is precisely the value F9 says not to trust. Fixed
(`71441822dc`): the workload now prints its realized size before any work, so it
lands in every run's own log.

Curve below is on **realized** sizes, with 8 MB run to give four clean points.

## The curve

| realized table | `wb` tax | h2 R% | cat4 R% | h2 cost | cat4 cost | wedge |
|---|--:|--:|--:|--:|--:|--:|
| **1 MB** (L2-resident) | 1.3192 | 86.83 | 87.18 | -9.85% | **+1.01%** | 10.9 pp |
| **2 MB** | 1.5571 | **90.61** | **89.47** | **-1.16%** | **+36.53%** | **37.7 pp** |
| **4 MB** | 1.5848 | **51.92** | 85.31 | -26.47% | +17.35% | 43.8 pp |
| **8 MB** | 1.7555 | **27.95** | 88.68 | +0.13% | +31.18% | 31.1 pp |

As neighbour slowdown left behind:

| table | unprotected | **under H2** | **under partitioning** |
|---|--:|--:|--:|
| 1 MB | 1.319x | 1.042x | 1.041x |
| 2 MB | 1.557x | 1.052x | 1.059x |
| 4 MB | 1.585x | **1.281x** | 1.086x |
| 8 MB | 1.756x | **1.544x** | 1.086x |

## Verdicts

| | registered | result |
|---|---|---|
| **P1** onset | `cost(cat4,1MB)` <= 10% | **PASS** --- +1.01% |
| **P1** upper | `cost(cat4,4MB)` >= 25% | **FAIL** --- +17.35% (at a size P3 voids) |
| **P2** | two-sided `abs(cost(h2))` <= 3% everywhere | **FAIL** --- max 26.47% |
| P2, one-sided (the claim intended) | `cost(h2)` <= 3% everywhere | **PASS** --- max **+0.13%** |
| **P3** | `R` >= 80% at every size | **FAIL at 4 MB and 8 MB** |

**P2's failure is a specification defect, not a result.** I registered a
two-sided bound for a one-sided claim; the tenant *gaining* throughput was never
a failure mode I cared about. Recorded as a defect rather than reinterpreted
after the fact --- the seventh threshold in this campaign specified wrongly.

## The finding that matters: H2's protection is not flat

**H2 recovers 86.8% / 90.6% / 51.9% / 28.0% as the tenant's table grows.
Partitioning recovers 87.2% / 89.5% / 85.3% / 88.7% --- flat.**

This is not H2 failing. It is **M5's two-component account reproducing in the
model**: H2 removes the *stream's* residency, and as the tenant's own table
grows, a growing share of the neighbour's harm is not the stream's to remove. A
way mask confines the tenant's **whole footprint**, so it keeps protecting ---
and charges the tenant 17--37% for the privilege.

The two mechanisms are therefore **not ordered**. They do different things:

- **The label removes the stream's harm, completely and for free.**
- **The mask removes the tenant's entire harm, expensively.**

## What the paper may and may not claim

**May**, and this is the clean wedge, at matched protection:

> With a tenant whose reuse structure is 1--2 MB, a way mask and a page-scoped
> label protect the neighbour equally (87--90% recovery, both), and the mask
> charges the tenant **up to 36.5%** of its throughput while the label charges
> **nothing**.

**May not**: that STREAMING protects the neighbour as well as partitioning in
general. **It does not** once the tenant's own working set dominates --- at an 8 MB
table the neighbour is left at 1.54x under H2 against 1.09x under partitioning.
Any claim of equal protection must carry the regime.

This is a **boundary, not a refutation**. It is also arguably the honest form of
the contribution: a page-scoped label is the only mechanism that removes the
stream's harm at zero cost, and it is *only* the stream's harm that it removes.
A reviewer will find this boundary in an afternoon; the paper is far better
stating it first.

## Follow-on this implies

The 1--2 MB regime is where the paper's claim lives, and the curve has **two
points** there. Between 2 MB (equal protection, 37.7 pp wedge) and 4 MB (H2
already down to 51.9%) the mechanism's usefulness falls off a cliff, and the
sweep cannot say where. Because the workload quantizes to powers of two, mapping
that knee needs either a finer table (change the probe indexing to a modulo) or a
different stream/LLC ratio. **Not run; recorded as the open question this sweep
raises.**


---

# SUPERSEDED (numerically) --- 2026-08-30

The fused-tenant numbers in this document were produced with a probe index whose
stride was 512 bytes --- a power of two --- which aliased the table onto 1/8 of the
cache sets and made it behave as though it were eight times larger. See
`FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` for the diagnosis and the
superseding curve. The qualitative conclusions largely survive; **every magnitude
here is wrong** and must be cited from the correction instead.
