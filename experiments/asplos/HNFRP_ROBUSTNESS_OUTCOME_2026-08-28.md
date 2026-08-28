# HNF_RP robustness outcome: SENSITIVE, on the boundary. TreePLRU's bias overstated H2's benefit by 2.25 pp.

Pre-registration `HNFRP_ROBUSTNESS_PREREG_2026-08-28.md` (`e626e15`), runner and
analyzer `6328035`, both committed before any data existed. 18/18 runs reached
`Exiting @ tick`. Analyzer output is reproduced verbatim below the tables.

## The data

`cyc/access = system.cpu0.numCycles / 3,000,000`, n=3 seeds per cell.

| policy | arm | mean | sd | s1 | s2 | s3 |
|---|---|--:|--:|--:|--:|--:|
| TreePLRU | qui | 33.8814 | 0.0140 | 33.8654 | 33.8912 | 33.8877 |
| TreePLRU | wb | 46.3800 | 0.0460 | 46.3651 | 46.3434 | 46.4316 |
| TreePLRU | h2 | 35.0358 | 0.0193 | 35.0160 | 35.0367 | 35.0546 |
| **LRU** | qui | 33.8814 | 0.0140 | 33.8654 | 33.8912 | 33.8877 |
| **LRU** | wb | 45.2764 | 0.0302 | 45.2440 | 45.2810 | 45.3040 |
| **LRU** | h2 | 35.1905 | 0.0104 | 35.1790 | 35.1932 | 35.1993 |

## Verdict: SENSITIVE --- and the call sits on the registered boundary

| policy | `tax_wb` | `tax_h2` | **R** |
|---|--:|--:|--:|
| TreePLRU | 1.3689 | 1.0341 | **90.76%** |
| LRU | 1.3363 | 1.0386 | **88.51%** |

**`dR = -2.25 pp`.** The registered rule keys on the point estimate, so the
verdict is **SENSITIVE**: `HNF_RP=lru` becomes the reporting configuration, the
qualitative claim survives, magnitudes must be re-run.

**The boundary is disclosed, not smoothed.** Propagated 1-sd on `dR` is
**0.137 pp**, so the 95% CI is **[-2.52, -1.98] pp** --- it crosses the 2.0 pp
ROBUST threshold by 0.02 pp, and the point estimate is only **1.8 sd** past the
line. I am applying the registered rule rather than re-arguing toward ROBUST;
that is the entire purpose of fixing the rule in advance, and the registered
action is also the conservative one. **More seeds would settle it, and should be
run before the paper quotes either figure.**

## Direction: the prereg's mechanism 2 wins. TreePLRU *overstated* H2.

No direction was registered, because two opposing mechanisms were identified.
The data selects one:

| arm | TreePLRU -> LRU | reading |
|---|--:|---|
| qui | +0.000% | policy never consulted (see sanity check) |
| **wb** | **-2.380%** | the aggressor does **less** damage under LRU |
| h2 | +0.442% | nearly unchanged |

Under TreePLRU the protected way group (8 of 20 ways evicted at half rate)
**sheltered aggressor lines**, inflating the WB tax and therefore inflating the
charge H2 appeared to remove. With an unbiased policy, **H2 removes 88.5% of the
capacity charge, not 90.8%.**

This is the direction that costs us something, and it is the one the data shows.

## Internal sanity check that fell out

The quiescent arm is **bit-identical under both policies**, per seed. That is
what should happen: the victim's 2650 KiB = 2.59 MiB footprint fits inside the
5 MiB HNF, so no HNF evictions occur and the replacement policy is never
consulted. A policy change that moved the quiescent arm would have indicated the
knob was doing something other than advertised.

## Instrument check: PASS, and two arms reproduce bit-identically

| arm | re-run | archived | window | verdict |
|---|--:|--:|---|---|
| qui | 33.8814 | 33.8814 | [33.712, 34.051] | **PASS** (bit-identical, per seed) |
| wb | 46.3800 | 46.3800 | [46.148, 46.612] | **PASS** (bit-identical, per seed) |
| h2 | 35.0358 | 35.0247 | [34.850, 35.200] | PASS (not identical --- see below) |

The archived W1 figures are validated. No apparatus drift; the registered
action-on-miss is not triggered.

## Why one arm did not reproduce: argv path length. Confirmed, not conjectured.

`qui` and `wb` reproduced bit-identically; `h2` did not (per-seed deltas -0.013,
+0.021, +0.026). The cause is visible in the artifacts and is a consequence of
the F10 provenance split: the archived `qui`/`wb` launcher used **absolute**
workload paths, the archived `h2` launcher (`sf_inf_cells.sh`) used **relative**
ones, and this runner used absolute for all three.

Tested directly with one control run --- `h2`, TreePLRU, seed 1, identical in
every respect except relative paths:

| run | cyc/access |
|---|--:|
| archived h2 s1 | **35.0293** |
| **control, relative paths** | **35.0293** |
| this batch, absolute paths | 35.0160 |

**Exact to four decimals.** argv string length shifts the simulated stack layout
and hence the address alignment of the workload's allocations, moving
`cyc/access` by **0.038%**.

### Why this matters beyond bookkeeping

Immaterial in magnitude, sharp in consequence: **had the TreePLRU arms been
reused from the archive instead of re-run, a 0.038% apparatus artifact would have
been folded into a 2.25 pp result whose decision boundary is 2.00 pp.** The
prereg's stated reason for re-running --- "reusing them would assume the archived
batch and this one share an environment, and that assumption is exactly what
F10/F11 punished this project for" --- was correct for a reason more concrete than
the one given.

It also means **an absolute vs relative path is part of a gem5 run's apparatus**,
not a cosmetic detail, and belongs in the pinned triple.

## Analyzer output, verbatim

    INSTRUMENT CHECK (treeplru re-run vs archived W1 means)
      qui : got  33.8814  archived  33.8814  window [33.712, 34.051]  -> PASS
      wb  : got  46.3800  archived  46.3800  window [46.148, 46.612]  -> PASS
      h2  : got  35.0358  archived  35.0247  window [34.850, 35.200]  -> PASS
      all three reproduce -- the archived W1 figures are validated.

    PRIMARY TEST
      treeplru  tax_wb=1.3689  tax_h2=1.0341  R=90.76%
      lru       tax_wb=1.3363  tax_h2=1.0386  R=88.51%

      dR = R_lru - R_treeplru = -2.25 percentage points
      VERDICT: SENSITIVE

## What SENSITIVE obliges, and what is not yet done

This batch measured **only the infinite-SF `wb` and `h2` cells**. The registered
action extends to every gem5 magnitude, so the following are now **unverified
under an unbiased policy**:

- **H2+H3 at infinite SF** (the `h3` arm) --- W1.5's outcome;
- **the entire finite-SF row** (WB, H2, H2+H3) --- the source of `tab:h3sf` and of
  H3's 3.45% charge;
- `tab:gem5` and any other cell quoting a gem5 magnitude.

Estimated 9--12 runs, ~3 h. **Not launched:** it is beyond the registered scope
of this test, and whether H3's cells are worth the machine time depends on a
pending decision about H3's standing in the paper.

## Standing of the paper's gem5 numbers, as of now

| claim | status |
|---|---|
| H2 removes ~90% of the infinite-SF capacity charge | **holds qualitatively**; the figure is **88.5%**, not 90.9% |
| gem5 is a conservative lower bound vs silicon | **unaffected** --- silicon recovers 100.5%, and 88.5% is further below it than 90.9% was, so the bound is *stronger* |
| `tab:h3sf` finite-SF cells, H3's 3.45% | **unverified** under an unbiased policy |
| the archived W1 apparatus and figures | **validated**, bit-identically on 2 of 3 arms |

Note the second row: the correction moves the number **away** from silicon's
100.5%, which widens the margin by which the model under-claims. The retraction
`REDTEAM_S1-1_RETRACTION_2026-08-28.md` argued the model is conservative; this
result makes that argument slightly stronger, not weaker.
