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
