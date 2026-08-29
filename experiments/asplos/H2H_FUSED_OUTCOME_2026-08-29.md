# The wedge reproduces. Partitioning charges the fused tenant 36.5%; the label charges it nothing.

Pre-registration `H2H_FUSED_PREREG_2026-08-29.md` (`9a30dd2`); workload
`800b7f920e`. 15/15 runs reached `Exiting @ tick`. **This is the result the
paper's central claim needed and did not have.**

## The data

Tenant = 16 MB stream + **3 MB hot table**, only the stream declared. n=3 seeds.

| arm | neighbour cyc/access | tax | **recovery** | tenant misses/kcyc | tenant IPC | **tenant cost** |
|---|--:|--:|--:|--:|--:|--:|
| `qui` | 33.8814 | 1.0000 | --- | --- | --- | --- |
| `wb` | 52.7563 | 1.5571 | 0.00% | 47.950 | 0.3503 | --- |
| `h2` (STREAMING) | 35.6530 | 1.0523 | **90.61%** | 48.506 | 0.3543 | **-1.16%** |
| `cat4` (4/20 ways) | 35.8691 | 1.0587 | **89.47%** | 30.435 | 0.2223 | **+36.53%** |
| `cat10` (10/20 ways) | 35.5726 | 1.0499 | **91.04%** | 41.406 | 0.3025 | **+13.65%** |

## Verdicts

| | registered | result |
|---|---|---|
| **P1** | all three protect, `R` >= 80% | **HOLDS** --- 90.61 / 89.47 / 91.04% |
| **P2** | `cost(cat4)` >= 5%, `cost(cat4)` > `cost(cat10)`, `cost(h2)` <= 1% | **ALL THREE PASS** |
| **P4** | mask enforced | **HOLDS** --- 400x per-way ratio at `cat4` |
| liveness 4 | tenant really uses its table | **PASS** --- non-zero L2 misses in every arm; `streamingAccesses` > 0 on `h2` only |

**The wedge is 37.7 pp at a 4/20 mask and 14.8 pp at 10/20**, and it has the
registered ordering: a tighter mask hurts the tenant more.

## What this establishes

All three mechanisms return the neighbour ~90% of its charge. They are **not**
interchangeable, because of what they cost the tenant:

- **Way partitioning** confines the stream *and* the tenant's table together,
  because a mask is indexed by **agent**. The table's LLC spill is evicted
  continuously and the tenant loses **36.5%** of its throughput (IPC
  0.3503 -> 0.2223).
- **The page-scoped label** declines to admit the stream and leaves the table
  alone, because a label is indexed by **address**. The tenant loses **nothing**
  --- it gains 1.16%.

That is the paper's thesis, measured in one apparatus, one workload, one variable
changed.

## The pure-stream null was right, and is now explained rather than explained away

`H2H_PARTITION_VS_H2_OUTCOME_2026-08-29.md` found partitioning charged **0.55%**
and the wedge failed at 0.00%. That result stands. It was a property of the
**workload**, not the mechanism: a pure stream has no reuse for a mask to
destroy. Both experiments together say something sharper than either alone:

> Against a pure stream, a way mask and a page-scoped label are equivalent, and
> the shipped knob is sufficient. The label's advantage appears exactly when the
> streaming tenant also holds resident reuse state --- and then it is large.

The scope condition is not a weakening. **It is the paper's contribution stated
precisely**, and it now has a measurement on both sides of the boundary.

## An unregistered convergence worth noting as such

`cat10` costs the tenant **13.65%**, against silicon's **15.0--16.9%** (E1, E4).
I explicitly declined to predict the magnitude --- `SimpleMemory` has no
congestion latency and the table is 3 MB rather than 256 MB --- so this is an
**observation, not a confirmation**, and it is recorded that way. But two
platforms, two workloads and two mechanisms landing within ~2 pp is a stronger
coincidence than the model had any right to produce.

## A sub-prediction I got wrong

The prereg said misses **per instruction** "should now move, because a destroyed
table *does* force re-fetching". **It did not**: 0.136900 in every arm, invariant
to five decimals again.

The reasoning was wrong for a clear reason. An L2 miss is counted when the access
misses L2, regardless of whether the LLC or DRAM serves it. Confinement changes
*where the miss is served* --- and therefore its latency --- not *whether it
occurs*. Misses per instruction is fixed by the access pattern and is blind to
the LLC by construction, for a fused tenant exactly as for a pure stream. It
detects only mechanisms that change what is *retained* (H3, +163%).

The metric was correctly demoted to secondary before the run, so nothing depends
on this; but the expectation stated alongside it was wrong and is recorded as
wrong.

## What the paper should now say

Sec1 currently states the wedge unconditionally. It can keep the claim, with the
scope made explicit and both measurements cited:

> A way mask is indexed by agent and cannot separate a tenant's stream from its
> working set; a page-granular label is indexed by address and can. Where the
> tenant is a pure stream the two are equivalent (partitioning costs it 0.55% in
> simulation, 0.7% on silicon). Where the tenant also keeps a hot structure ---
> the common case for scans, decoders and loaders --- partitioning costs it
> **36.5%** at a 4/20 mask and **13.7%** at 10/20, while the label costs it
> nothing, at equal protection for the neighbour (89--91%).

That is a **stronger** claim than the current text, because it is bounded, it
names the regime where shipped knobs suffice, and every number in it is measured.


---

# SUPERSEDED (numerically) --- 2026-08-30

The fused-tenant numbers in this document were produced with a probe index whose
stride was 512 bytes --- a power of two --- which aliased the table onto 1/8 of the
cache sets and made it behave as though it were eight times larger. See
`FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` for the diagnosis and the
superseding curve. The qualitative conclusions largely survive; **every magnitude
here is wrong** and must be cited from the correction instead.
