# Head-to-head outcome: the wedge does NOT reproduce against a pure stream. Partitioning and STREAMING are equivalent here.

Pre-registration `H2H_PARTITION_VS_H2_PREREG_2026-08-29.md` (`7b69cc7`); harness
`451e5cf`, both committed before the data. 15/15 runs reached `Exiting @ tick`.
**This is the experiment that tests the paper's central claim, and the claim came
out narrower than the paper states it.**

## The data

| arm | neighbour cyc/access | tax | **recovery** | tenant misses/kcyc | tenant IPC | tenant misses/**instruction** |
|---|--:|--:|--:|--:|--:|--:|
| `qui` | 33.8814 | 1.0000 | --- | --- | --- | --- |
| `wb` | 45.2764 | 1.3363 | 0.00% | 27.085 | 0.1625 | 0.166684 |
| `h2` (STREAMING) | 35.1905 | 1.0386 | **88.51%** | **29.891 (+10.36%)** | 0.1793 | 0.166685 |
| `cat4` (stream in 4/20 ways) | 35.0809 | 1.0354 | **89.47%** | **26.935 (-0.55%)** | 0.1616 | 0.166684 |
| `cat10` (stream in 10/20 ways) | 35.1784 | 1.0383 | **88.62%** | **26.947 (-0.51%)** | 0.1617 | 0.166684 |

n=3 seeds, tenant throughput sd $\le$0.010.

## Verdicts

| | registered | result |
|---|---|---|
| **P1** | partitioning protects, `R` $\ge$ 80% | **HOLDS** --- 89.47% and 88.62% |
| **P2** | wedge $\ge$ 5% on tenant misses/instruction | **FAILS --- 0.00% at both splits** |
| **P3** | H2's tenant cost reproduces, $\le$1% | **REPRODUCES --- +0.00%** |
| **P4** | mask enforced | **HOLDS** --- see below |
| instrument | `wb`/`h2` within 0.5% of W1-under-LRU | **PASS --- bit-identical** (45.2764, 35.1905) |

`P4`: per-way HNF allocations, `cat4` **708,682/way inside** the mask against
**2,046/way outside** --- a **346x** ratio; `cat10` 284,515 vs 11,368, **25x**. The
outside traffic is the victim's, which is deliberately unmasked. The unmasked
`wb` arm is uniform to 0.5% across all 20 ways, as LRU should be, and the `h2`
arm allocates 921--3,447 per way --- near-nothing, the 99.3% eviction collapse
reproduced in this tree.

## P2 failed for two reasons, and both are mine

### 1. I registered the wrong metric

Tenant misses **per instruction** is **0.16668 in every arm, identical to five
decimals**. It is invariant to cache policy for a no-reuse stream: the loop
touches the same lines wherever they are cached. The metric detects whether a
mechanism forces **re-fetching** --- which is why it caught H3 at **+163%** --- and
is structurally blind to whether a mechanism **slows the tenant down**.

I chose it because it is invariant to how long the tenant was allowed to run.
That was the wrong invariance to want. For a bandwidth-bound streaming tenant the
figure of merit is **rate**, and on rate there is a difference.

### 2. On throughput there *is* an ~11 pp wedge --- but not the one the paper claims

| | tenant throughput vs `wb` |
|---|--:|
| `h2` | **+10.36%** |
| `cat4` | **-0.55%** |
| `cat10` | **-0.51%** |

Wedge = **+10.97%** (`h2` vs `cat4`), **+10.93%** (`h2` vs `cat10`).

The wedge exists. **Its composition is not what the paper says.** The paper
claims partitioning *charges the tenant 15--17%* while STREAMING charges nothing.
Here partitioning charges **0.55%** and STREAMING **gains 10.4%**. The 11 pp gap
is almost entirely H2's gain, not partitioning's loss.

## Why partitioning is nearly free here, and why that is not a modelling artifact

**The tenant is a pure stream with no reuse.** Confining a no-reuse stream to 4 of
20 ways costs it almost nothing, because it had no residency benefit to lose.
E1/E4's 15--17% was measured against a **fused** tenant carrying its own hot
table, and what confinement destroyed there was the tenant's *own* reuse.

This is M5's two-component account, arriving from the other direction: the
stream's residency is free to remove; the tenant's own working set is not. And
the model **agrees with silicon** on the pure-stream case --- `W5.3` found Intel
CAT against a table-less streamer reaches 1.00x at **0.7%** cost, against 0.55%
here. Two platforms, same answer, which is why this is a real result and not a
`SimpleMemory` artifact.

## What this means for the paper

**As run, this experiment does not support the wedge.** It supports a different
and narrower claim:

> Against a **pure** immutable read stream, way partitioning and an OS-declared
> memory type are **equivalent**: both return the neighbour ~89% of its charge,
> and both cost the stream essentially nothing. STREAMING's advantage does not lie
> in the pure-stream case at all. It appears only when the streaming tenant
> **also holds resident reuse state** that a way mask would confine along with the
> stream --- because a mask cannot separate the two and a page-scoped label can.

That is still the paper's thesis, but it is a **conditional** thesis, and §1
currently states it unconditionally. Two honest routes:

1. **Scope the claim.** State that against a pure stream shipped knobs suffice ---
   which W5.3 already showed on silicon and this now shows in the model --- and
   that the mechanism's value is confined to mixed tenants. Cheap; weakens the
   headline; is what the evidence supports today.
2. **Demonstrate the wedge in the model with a fused tenant.** Requires a gem5
   workload that streams *and* keeps a hot table, which does not exist --- the
   gem5 aggressor is a pure stream by construction. New workload development.

**Route 1 is what the evidence supports now. Route 2 is what would restore the
unconditional claim.** This is a lead-and-co-author decision, not an editing one.

## What went right

The pre-registration did its job. A 5% threshold on a named metric, fixed in
advance, turned "the wedge is obvious" into a falsifiable statement and then
falsified it. Had the metric been chosen after seeing the data, the throughput
numbers would have been reported as an 11% wedge confirming the paper, and the
0.55% partitioning charge --- the number that actually matters --- would never have
been looked at.
