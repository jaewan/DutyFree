# Config-fidelity audit: every geometry and default in the gem5 apparatus, checked for silent degradation

Motivated by two accidental discoveries. `CacheMemory::init()`'s set truncation
was found on 2026-08-24 while sizing a different experiment (W7.2); `TreePLRURP`'s
associativity bias was found on 2026-08-28 by a per-way stat added to verify way
partitioning. Neither was found by looking. **Two accidents justify one
deliberate pass.** Zero compute cost; static analysis of config artifacts and
gem5 source only, so it ran alongside the live batch without touching it.

Geometry read from `/tmp/rq_h2_fin_treeplru_s1/config.ini` --- a run from the
batch in flight, i.e. the apparatus actually in use.

## 1. Cache geometry: the two power-of-two traps, per cache

| cache | size | assoc | sets | indexed | effective | set trunc? | assoc pow2? |
|---|--:|--:|--:|--:|--:|---|---|
| l1i | 32K | 8 | 64 | 64 | 32K | no | **yes** |
| **l1d** | 48K | **12** | 64 | 64 | 48K | no | **NO** |
| l2 | 2048K | 16 | 2048 | 2048 | 2048K | no | **yes** |
| **hnf (LLC)** | 5120K | **20** | 4096 | 4096 | 5120K | no | **NO** |
| hnf.sf (finite) | 4096K | 16 | 4096 | 4096 | 4096K | no | yes |
| l1d/l1i/l2 `.sf` | 1K | 1 | 16 | 16 | 1K | no | yes (trivially) |

**Set truncation is not triggered anywhere in this configuration** --- every
`num_sets` is already a power of two. The 5 MiB/20-way LLC lands on exactly 4096
sets, which is luck, not design.

**Associativity is non-power-of-two in exactly two caches: l1d (12) and the HNF
(20)** --- both on `TreePLRURP`, both therefore 2x biased. Already established and
measured; the HNF instance costs the H2 bound 2.25 pp
(`HNFRP_ROBUSTNESS_OUTCOME_2026-08-28.md`).

**Net new from this pass on #1: nothing broken that was not already known.** The
value is knowing the truncation trap is *not* firing, which had never been
checked at the geometry actually in use.

## 2. Live paper defect: `tab:sens`'s associativity axis is confounded and undisclosed

The truncation *does* fire in a **published table**. `tab:sens` sweeps LLC
associativity at a fixed *requested* 5 MiB:

| row | assoc | sets | indexed | **effective LLC** | of 5 MiB |
|---|--:|--:|--:|---|--:|
| 1 | 8-way | 10,240 | 8,192 | **4 MiB** | 80% |
| 2 | 12-way | 6,826 | 4,096 | **3 MiB** | 60% |
| 3 | 20-way | 4,096 | 4,096 | 5 MiB | 100% |

So the axis moves associativity **and** capacity together, over a 1.67x capacity
range. The caption says the recovery "holds (89--92\%) **across LLC
associativity**" and says nothing about effective capacity.

`W4.6_TAB_SENS_ASSOC_AXIS_2026-08-24.md` established this five days ago. The
paper's reader-visible text discloses the *benchmark-side* quantization
(`--hot-bytes` -> 256 MiB, Appendix) but **not** either gem5-side instance. The
gem5 instance survives only as a LaTeX comment in `Sec5_Evaluation.tex:61`, which
says the realized size "must be labelled at the point of use" --- and it is not.

**This is an F11: a correct artifact, committed, that nobody read back into the
deliverable.** A referee who computes `(5 MiB / 12) / 64 = 6826` finds it in one
line of arithmetic.

**Note the direction: disclosure makes the claim stronger, not weaker.** If the
three rows are really (4 MiB, 8-way), (3 MiB, 12-way) and (5 MiB, 20-way), then
H2 recovery holding at 89--92% spans a joint capacity *and* associativity change
--- broader evidence of robustness than the caption currently claims. The defect is
the mislabelling, not the result.

Proposed caption insert, not applied (paper writes publish to co-authors):

> Ruby quantizes LLC sets to a power of two, so at a requested 5 MiB the 8- and
> 12-way rows realize 4 MiB and 3 MiB respectively; the axis therefore spans a
> joint associativity and capacity change, and the recovery is stable across
> both. The 20-way row realizes the full 5 MiB.

The stale sibling: `Sec5_Evaluation.tex:61`'s comment warns about a 32 MiB/20-way
LLC realizing 20 MiB. **That geometry no longer appears in reader-visible text**
(the paper uses 5 MiB throughout), so the warning is stale rather than live.

## 3. Why the truncation is a gem5 defect and not a modelling choice

gem5 enforces this invariant --- in the other cache path:

    src/mem/cache/tags/indexing_policies/base.hh:120
        fatal_if(!isPowerOf2(numSets), ...)

The **classic** cache refuses a non-power-of-two set count outright. The **Ruby**
path (`CacheMemory.cc:108`) computes `m_cache_num_set_bits =
floorLog2(m_cache_num_sets)` and silently indexes a truncated array. Same
project, same invariant, two enforcement policies. `TreePLRURP` has no
power-of-two guard in *either* path.

That asymmetry is worth one sentence in the paper's threats section and, if the
work is upstreamed, one issue.

## 4. Infinite-SF integrity: PASS

Load-bearing, because H3's entire claim is a finite-vs-infinite contrast. In
"infinite" mode the config still instantiates `SFDirectory(size="1kB", assoc=1)`,
because the controller cannot take a NULL. If any path touched it, the "infinite"
arm would be running a 16-entry snoop filter and the H3 result would be
meaningless.

Verified: every `sf.` access in the CHI protocol is either inside an
`if (sf_finite)` guard (`CHI-cache-funcs.sm:84,103,111`) or inside `CheckSFFill`,
whose **only** entry point is `Allocate_DirEntry`'s `else if (sf_finite)` branch
(`CHI-cache-actions.sm:3489-3493`). Single gated caller. The dummy is never
consulted.

## 5. Fragile defaults: two knobs whose unset value is not the campaign's value

| knob | code default | campaign always sets | consequence if forgotten |
|---|---|---|---|
| `HNF_DMT` | **1 (ON)** | `0` | DMT on. The config's own comment says DMT is **incompatible** with the finite-SF deferral and "could silently exercise that untested combination". |
| `HNF_SF_SETS` | **`1 << 16` = 65,536 sets** | `4096` | 65,536 x 16 ways = **1,048,576** SF entries instead of 65,536 --- a **16x** larger snoop filter. |

Every committed runner sets both, and the runs in flight have `enable_DMT=false`
and 4096 sets, verified from their own `config.ini`. But these are the two places
where a hand-typed invocation --- which is how the F10 arms were launched --- would
silently produce a different experiment. **Recommendation: make both fatal if
unset when `sf_finite` is on, rather than defaulting.**

## 6. Fidelity gaps that are real, off by default, and documented

| setting | value | meaning |
|---|---|---|
| `fwd_unique_on_readshared` | false | model grants SC where real x86 grants E to a sole reader |
| `dealloc_backinv_unique/shared` | false at HNF, true at L1/L2 | HNF does not back-invalidate; matches intent |
| `SimpleMemory latency_var` | 0 | no congestion latency, by construction --- already a stated limit |

`fwd_unique_on_readshared` is immaterial to our arms specifically, because the
streaming epoch is read-only by contract (I1) and the victim is a read-only
pointer chase, so no write ever needs the upgrade the model declines to grant.
Worth one clause in the threats section, not an experiment.

Prefetching **is** modelled (`MultiPrefetcher` = `StridePrefetcher` + DCPT on the
l1d, `use_prefetcher=true` on 4 controllers), which matters because H1 is a
contract clause.

## Summary

| # | finding | status |
|---|---|---|
| 1 | set truncation at the geometry in use | **not triggered** --- newly verified |
| 2 | `tab:sens` associativity axis confounded, undisclosed | **live paper defect (F11)** |
| 3 | Ruby silently truncates where classic `fatal_if`s | gem5 defect; threats-section sentence |
| 4 | infinite-SF never touches the dummy | **PASS** |
| 5 | `HNF_DMT` / `HNF_SF_SETS` defaults != campaign values | fragility; make fatal |
| 6 | `fwd_unique_on_readshared`, `latency_var=0` | known, immaterial or already stated |

**One live paper defect, one gem5 defect worth reporting upstream, two
fragilities, one clean pass on the check that most needed one.** No finding
invalidates a measured result beyond the 2.25 pp already recorded.

## What this audit did not cover

- O3CPU microarchitectural parameters (width, ROB, LSQ) against the real 8592+.
- Whether the CHI topology (`Pt2Pt`, 1 HNF, 1 directory) is representative of a
  60-core mesh; single-slice LLC is a known simplification.
- The workload binaries' own numerics.
- Anything about the AMD/`moscxl` apparatus, unreachable since 2026-08-22.

These are scope statements, not clean bills of health.
