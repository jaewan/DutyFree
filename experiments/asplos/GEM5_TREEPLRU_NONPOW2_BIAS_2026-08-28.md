# gem5's TreePLRU is 2x-biased at non-power-of-two associativity --- including the HNF, where H2 acts

Found incidentally on 2026-08-28 while auditing the way-partitioning null test.
The new `m_allocsByWay` stat, added to verify mask enforcement, made it visible;
nothing else in the repo would have shown it.

## The observation

L1D, associativity **12**, `TreePLRURP` (the config default), unmasked, 91,203
allocations:

| ways | allocations per way | share |
|---|--:|--:|
| 0--3 | ~11,576 | 12.7% each |
| 4--11 | ~5,612 | 6.2% each |

A **2.06x** skew. A replacement policy should not prefer some ways over others;
way index carries no meaning.

## The mechanism

`tree_plru_rp.cc` builds `PLRUTree(numLeaves - 1)` --- a flat array of `L-1`
internal nodes at indices `0..L-2` --- and descends from the root while
`tree_index < L-1`, mapping the stopping index to `candidates.at(tree_index -
(L-1))`. For `L = 2^k` this is a perfect tree and every leaf sits at depth `k`.
For `L` **not** a power of two the array is not a perfect tree, leaves land at
**two different depths**, and a leaf at depth `d` is selected with probability
`2^-d`. Shallower leaves are therefore chosen twice as often.

Computed from the actual traversal:

| assoc | uniform? | max/min | structure |
|---|---|--:|---|
| 8 | yes | 1.00 | depth 3: ways 0--7 |
| **12** | **no** | **2.00** | depth 3: ways 0--3; depth 4: ways 4--11 |
| 16 | yes | 1.00 | depth 4: ways 0--15 |
| **20** | **no** | **2.00** | depth 4: ways 0--11; depth 5: ways 12--19 |

Prediction against measurement, L1D, 91,203 allocations:

| ways | predicted/way | measured/way | measured/predicted |
|---|--:|--:|--:|
| 0--3 | 11,400 | 11,576 | **1.015** |
| 4--11 | 5,700 | 5,612 | **0.985** |

Within 1.5%. The mechanism is confirmed, not conjectured.

There is **no guard**: `num_leaves = Param.Int(Parent.assoc, ...)` and the only
check in the constructor is `fatal_if(numLeaves < 1)`. Any non-power-of-two
associativity silently gets a biased policy.

## Why this reaches the paper

The configuration's caches:

| cache | assoc | affected |
|---|--:|---|
| l1i | 8 | no |
| l1d | 12 | **yes** |
| l2 | 16 | no |
| **hnf (LLC)** | **20** | **yes** |

**The HNF is where H2 acts.** Its 20 ways split into 12 evicted at `p=1/16` and 8
at `p=1/32`, so the LLC in every gem5 run we have reported behaves as a PLRU with
a structurally protected way group rather than as a uniform 20-way PLRU.

## What this does and does not invalidate

**Does not.** Both arms of any within-model comparison share the policy, so the
bias is common-mode. `simInsts` and all functional results are unaffected --- this
is a policy-quality issue, not a correctness bug.

**Does, potentially.** The *magnitude* of any result sensitive to LLC replacement
quality --- the H2 bound above all --- is measured under a degraded policy. A tree
with a protected way group is not the same cache as a uniform 20-way PLRU, and
whether that inflates or deflates the measured value of declining to allocate is
**not determinable a priori**. I am not asserting a direction; asserting one
without measuring it is the error this campaign has already made more than once.

## The check this calls for

`configs/ruby/CHI_config_8592.py` already exposes `HNF_RP` (`ship|brrip|lru|
treeplru`), so the robustness run costs one rebuild-free invocation: **re-measure
the H2 bound with `HNF_RP=lru`** and compare against the TreePLRU value.

- If the bound moves little, the existing numbers stand and gain a robustness
  citation.
- If it moves materially, `HNF_RP=lru` becomes the reporting configuration and
  the TreePLRU numbers are superseded --- and every gem5 figure needs re-running.

To be pre-registered before the run, with the threshold and the action-on-miss
fixed in advance, per the procedure adopted in `M5_OUTCOME` addendum 1.

## Provenance note

This is the second time an instrument added for one purpose has exposed a defect
invisible to every prior run --- the pattern argues for keeping `m_allocsByWay`
enabled rather than treating it as verification scaffolding to be removed.
