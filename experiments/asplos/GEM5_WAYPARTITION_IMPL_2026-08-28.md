# Way partitioning in gem5: design, and why three functions had to change

Written 2026-08-28 while the build runs. Implements the baseline the project has
never been able to compare against in-model --- `AGENDA` item 3 and the highest-value
remaining code change, because without it any simulated STREAMING speedup is
measured against *doing nothing* when the real alternative is one MSR write.

## What was already there, and why it was not enough

The CHI protocol already makes a per-request allocation decision at exactly the
right place: `needCacheEntry()` in `CHI-cache-funcs.sm` returns false for a
STREAMING line at the home node, which is H2. So the plumbing for "should this
fill allocate in the LLC?" exists.

**It is the wrong shape for CAT.** H2 is binary --- allocate or don't.
Way-partitioning is *placement*: allocate, but only in these ways. That decision
lives below SLICC, in `CacheMemory`, and nothing there knew about masks.

## Where the change had to go, and why all three

`CacheMemory` has three functions on the fill path, and constraining only one
would be wrong:

| function | what it does | why it must be mask-aware |
|---|---|---|
| `cacheAvail(addr)` | is there room in this set? | must report "full" when the *masked* ways are full, even if unmasked ways are free --- otherwise `allocate` is called and finds nothing |
| `allocate(addr, e)` | takes the **first open slot** in the set | must skip ways outside the mask, or a confined requestor places lines anywhere |
| `cacheProbe(addr)` | asks the replacement policy for a victim, over **all** ways | must offer only masked ways as candidates, **or a confined requestor evicts the party it is supposed to be isolated from** --- which is precisely the interference the mechanism exists to prevent |

That last row is the one that makes this a three-function change rather than a
one-liner. A mask that constrains placement but not eviction gives isolation on
paper and none in fact.

## Implementation

**C++** (`CacheMemory.hh/.cc`), additive --- the existing three functions are
untouched, so a run that never configures a mask is bit-identical to before:

- `setClosWayMask(clos, mask)` --- a CLOS is a numbered policy slot; its policy is
  a bitmask over ways. Rejects an all-zero mask (real CAT forbids it, and a
  requestor that may allocate nowhere would deadlock the fill path rather than
  degrade) and rejects bits beyond the associativity.
- `setRequestorClos(requestor, clos)` --- the context-to-policy map. This is the
  faithful part: **CAT keys on execution context, never on address**, and so does
  this.
- `wayMaskFor(requestor)` --- resolves the mask, defaulting to all ways for any
  requestor with no CLOS and for the case where no mask was ever set.
- `cacheAvailMasked`, `allocateMasked`, `cacheProbeMasked`.

One deliberate asymmetry, and it mirrors hardware: **a tag match counts as
available regardless of the mask.** CAT constrains allocation, not lookup --- a
confined requestor still *hits* on lines anywhere in the cache. This is the same
property our paper leans on when it says a bitmask cannot shed the tag-pipeline
walk.

**SLICC**: three declarations in `RubySlicc_Types.sm`, a `closRequestor(tbe)`
helper returning the CHI requestor's `NodeID`, and the three call sites in
`CheckCacheFill` (`CHI-cache-actions.sm`) threaded through it. The snoop-filter
call sites in the same action are **left alone** --- CAT partitions the data array,
not the directory, and partitioning the SF would be a different mechanism.

**Python**: `PyBindMethod` exports on `RubyCache`, so a config script does

    llc.setClosWayMask(1, 0x0ff)   # CLOS 1 may allocate in ways 0-7
    llc.setRequestorClos(rid, 1)   # requestor rid uses CLOS 1

## Two SLICC frictions worth recording

1. `NodeID` is `external_type(..., primitive="yes")` with **no int-literal
   conversion**, so `return 0` from a `NodeID` function does not compile, and
   `intToID` is not in the CHI protocol's scope. The fallback branch was dropped
   instead: `CheckCacheFill` already asserts `is_valid(tbe)` before the fill
   path, so it was dead code.
2. The first attempt declared the parameters as `int`. Tightened to `NodeID`,
   which is what `machineIDToNodeID` returns; the C++ side takes `int` and the
   conversion is implicit there.

## What this does and does not model

**Does:** capacity and associativity partitioning of the shared data array, keyed
on execution context, with eviction confined to the mask --- the three properties
that make CAT protect a neighbour completely.

**Does not:** the 15-CLOS hardware limit (a config-time property, better argued
from the ISA than simulated); MBA rate throttling; CDP (separate code/data
masks); or any partitioning of the snoop filter.

## Verification plan, before any measurement

1. **Null test.** A run with no mask configured must produce byte-identical stats
   to the pre-change binary. This is the check that the additive design actually
   is additive.
2. **Mask enforcement.** With a CLOS confined to *k* of *N* ways, that
   requestor's LLC occupancy must saturate at $k/N$ of capacity and not above.
   The equivalent of the `cpus_list`/bit-count assertions the silicon runners
   grew after E1a's defect.
3. **Sanity against silicon.** A victim confined to the complement should show
   the qualitative shape E1 measured: interference gone, a confinement cost that
   rises with occupancy. Magnitudes will differ --- gem5 reads 39% low against its
   one hardware anchor --- so only the shape is checked.

No performance claim is made from this until 1 and 2 pass.

---

# Verification log, 2026-08-28

## Passed

- **Builds and links.** SLICC accepts the interface; `nm` finds `allocateMasked`,
  `cacheProbeMasked`, `setClosWayMask`; `strings` finds `m_allocsByWay` and both
  guard messages.
- **Callable from a config script**, post-instantiation: `hasattr` true for both
  setters, and `setClosWayMask(1, 0x0ff)` / `setRequestorClos(3, 1)` succeed.
- **Guards fire.** An all-zero mask aborts with the intended message. Note that
  gem5's `fatal` terminates rather than raising a catchable Python exception, so a
  config error here stops the run --- which is the right behaviour and worth knowing
  when writing config scripts.
- **The audit stat works** and reports per-way allocations for L1D, L1I, L2 and
  the HNF.

## A workload obstacle, diagnosed rather than guessed

The first verification workload (a 512 KiB victim) produced **52 HNF accesses and
zero allocations**. The reason is not the working-set size alone --- it is the
HNF's allocation policy in `CHI_config_8592.py`:

    alloc_on_readshared = False
    alloc_on_readunique = False
    alloc_on_readonce   = False
    alloc_on_writeback  = True     # <-- the only path that fills the HNF

**This LLC is configured as a victim cache.** Lines enter it when L2 evicts them,
never on a read fill. That is faithful to a non-inclusive EMR-style LLC, and it has
a direct consequence for the verification:

> A read-only victim smaller than the 2 MiB L2 produces **no** L2 evictions,
> therefore no HNF writebacks, therefore no HNF allocations, and the mask has
> nothing to constrain. The check would have passed vacuously.

So the workload must exceed the L2 to generate writebacks. Re-running with a
4 MiB victim, which is above the 2 MiB L2 and below the 5 MiB L3.

**And it sharpens what check 2 actually verifies:** in this configuration the way
mask constrains **where L2 victims may land in the LLC**, not where read fills
land. That is the correct semantics for this cache and it is what CAT does on a
non-inclusive part --- but it means the audit must be read as "L2 victims confined
to the mask", and a future reader of the stat should not expect read fills to
appear there at all.

## Still open

- **Check 1, null test** --- a no-mask run identical to the pre-change binary.
  Requires stash, rebuild, re-run, diff. Blocked while the 4 MiB run holds the
  binary.
- **Check 2, mask enforcement** --- zero allocations in ways outside the mask,
  which needs the 4 MiB run first to establish that any allocations occur at all.

No performance claim from the model until both pass.


---

# Addendum 1 --- 2026-08-28: check 2's quantitative deltas are confounded by a replacement-policy swap. Withdrawn.

Found while auditing the diff for check 1, not by the check itself.

`configs/ruby/CHI_config_8592.py` installs `LRURP` **only when a mask is set**:

```python
    way_mask = int(os.environ.get("L1D_MASK", "0"), 0)
    if way_mask != 0:
        replacement_policy = LRURP()
```

The comment on those lines is deliberate and, for check 1, correct: the
unpartitioned baseline keeps TreePLRU so it stays comparable to every prior gem5
number in the repo. But it means check 2's two arms differed in **two** variables:

| arm | mask | replacement policy |
|---|---|---|
| unmasked | all 12 ways | TreePLRU (default) |
| masked | ways 0--3 | **LRURP** |

## What survives and what does not

**Survives.** The structural criteria are properties of the mask alone and are
policy-independent:

- zero allocations in ways 4--11 under mask `0xf`;
- allocations present in ways 0--3, 11,597 -> 24,258;
- `simInsts` identical at 504,234, normal exit in both arms.

**Withdrawn.** Both quantitative deltas I reported:

- total allocations **+6.4%**
- `simTicks` **+2.5%**

Neither is a way-partitioning effect. Each mixes partitioning with a policy
change, and on a 12-way cache the TreePLRU->LRU difference alone is easily of
that magnitude. They were reported without this caveat; that was an error of
interpretation, not of implementation.

## The fix

A third arm, **unmasked + `LRURP`**, gives a policy-matched baseline; the masked
number is then compared against it rather than against TreePLRU. This needs a
config hook to force the policy at mask 0 --- the current config cannot express
it. To be added as `L1D_RP` alongside the existing `HNF_RP` hook, which already
does exactly this for the HNF.

Until that arm exists, the only defensible statement from check 2 is the
structural one: **the mask is enforced.** No cost or benefit figure follows.

Standing commitment unchanged: no performance claim from the model until check 1
passes and the policy-matched arm is measured.


---

# Addendum 2 --- 2026-08-28: check 1 (null test) PASSES. The unmasked path is untouched.

## Method

Two runs of the same workload with `L1D_MASK=0`, differing only in binary:

| arm | source | binary verified by |
|---|---|---|
| **new** | HEAD (`3fdde426bf`) | contains `allocateMasked`/`cacheProbeMasked` |
| **old** | baseline `16c131693a`, 7 files reverted | `nm` finds **0** masked symbols |

Both binaries rebuilt from scratch in `build_Intel_8592`, one at a time. The
baseline run's process was checked against the binary mtime before trusting it:
build finished 14:29:30, gem5 started 14:29:45, `/proc/<pid>/exe` resolved to the
real path with no `(deleted)` marker. This check exists because an earlier
episode in this campaign launched runs against a binary caught mid-link.

## Result

Both runs exited normally on `m5_exit`; `simInsts` = **504,234** in both, matching
check 2's unmasked arm. **1,869 counters compared. 1,864 bit-identical.** The five
that differ are host wall-clock stats, which are non-deterministic by
construction:

| counter | old | new |
|---|--:|--:|
| `hostSeconds` | 14.82 | 15.01 |
| `hostInstRate` | 34,030 | 33,596 |
| `hostOpRate` | 61,283 | 60,501 |
| `hostTickRate` | 125,805,637 | 124,201,176 |
| `hostMemory` | 8,599,520 | 8,599,576 |

`hostMemory` differs by 56 KB --- the added stat vectors. **Zero simulated
counters differ.**

## The exclusion is audited, not assumed

`m_allocsByWay` was excluded from the diff. That is only legitimate if it is the
sole added counter, so the counter *name sets* were compared: 60 names appear
only in the new binary, **all** of them `m_allocsByWay` (12 ways x each
`CacheMemory` instance, plus a scalar for each snoop filter), and **nothing**
appears only in the old binary.

## Why the pass was predictable, and why it was still run

With mask 0, `wayMaskFor()` returns all-ways, `cacheAvailMasked()` reduces
line-for-line to `cacheAvail()`, and both `cacheProbe` variants iterate
`0..assoc-1` in the same order, so the replacement policy receives an identical
candidate vector. No divergence was predicted. But "identical by construction"
is exactly what was believed about `cacheProbeMasked` and TreePLRU before that
pairing crashed the simulator at 2,429 instructions while satisfying its own
success criterion. The argument is not the evidence.

Also note: mask 0 keeps TreePLRU, so this null test is genuinely policy-matched
--- unlike check 2, per addendum 1.

## Consequence

Every existing unmasked gem5 number in the repo --- including the H2 bound ---
stands without re-measurement. The way-partitioning code is inert unless a mask
is set.

## Status of the standing commitment

"No performance claim from the model until both pass." Check 2 passed
structurally (mask enforced); check 1 passes fully. **The remaining blocker on a
partitioning cost figure is not verification but the confound in addendum 1**: a
policy-matched unmasked arm is still needed. `L1D_RP` has been added to
`CHI_config_8592.py` for exactly that, and it refuses `L1D_RP=treeplru` together
with a mask rather than silently substituting LRU.


---

# Addendum 3 --- 2026-08-28: the addendum-1 confound is measured at 0.03%. The withdrawn figures are restored, now properly attributed.

Three arms, same workload, one variable changed at a time. `L1D_RP` (added for
this purpose) forces the policy independently of the mask.

| arm | mask | policy | simInsts | simTicks | L1D allocs | allocs in ways 4--11 |
|---|---|---|--:|--:|--:|--:|
| **A** | 0 | TreePLRU | 504,234 | 1,864,095,082 | 91,203 | 44,899 |
| **B** | 0 | **LRU** | 504,234 | 1,863,580,654 | 91,154 | 60,788 |
| **C** | `0xf` | LRU | 504,234 | 1,911,295,692 | 97,035 | **0** |

`simInsts` identical across all three; all exited normally.

## The decomposition

| effect | comparison | simTicks | allocations |
|---|---|--:|--:|
| policy alone | A -> B | **-0.028%** | -0.054% |
| **partitioning alone** | **B -> C** | **+2.560%** | **+6.452%** |
| as originally reported | A -> C | +2.532% | +6.395% |

**The policy swap contributes -0.028% of a +2.532% delta.** The confound was real
and had to be declared, but it is immaterial: the clean partitioning cost is
+2.560% simTicks / +6.452% allocations against +2.532% / +6.395% confounded.

Addendum 1's withdrawal was correct procedure on the information available --- the
arms genuinely differed in two variables and I had reported the delta as a
partitioning effect without checking. It is now measured rather than assumed, and
**the figures are restored with the attribution earned rather than presumed.**

## A second, independent confirmation of the TreePLRU bias

Arm B is unmasked LRU on the same 12-way cache. Its per-way distribution:

| ways | allocations per way | spread |
|---|--:|--:|
| 0--11 | 7,571 -- 7,636 | **0.9%** |

Uniform. So the 2.06x skew in arm A is a property of `TreePLRURP` at
associativity 12 and **not** of the workload, the indexing, or the new stat ---
which is exactly what `GEM5_TREEPLRU_NONPOW2_BIAS_2026-08-28.md` predicts from
the traversal arithmetic. Arm B was run to remove a confound and independently
confirmed a separate finding.

Note also arm A's `waysGE4` = 44,899 against arm B's 60,788: under a uniform
policy 8/12 = 66.7% of allocations land in ways 4--11 (measured 66.7%), while
TreePLRU puts only 49.2% there. The bias is visible in the aggregate too.

## What this run does and does not establish

**Does.** The implementation is verified end to end: the mask is enforced
(zero allocations outside it), the unmasked path is bit-identical to the
pre-change binary (check 1), and confining a requestor from 12 ways to 4 costs
+2.56% simTicks / +6.45% allocations in a policy-matched comparison.

**Does not.** This is the **L1D**, chosen because it demonstrably allocates in
this configuration. It is a mechanism demonstration, not the paper's shared-LLC
result --- the HNF is a victim cache here and allocated **zero** lines in this
workload. The LLC partitioning number the paper needs still requires a workload
that generates writeback pressure at the HNF.

The standing commitment is now discharged for the *mechanism*: both checks pass
and the cost figure is policy-matched. It remains undischarged for any
**shared-LLC** claim.
