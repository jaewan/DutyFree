# CLFLUSH is a silent no-op under gem5 Ruby/CHI

Date: 2026-09-01.  Found while reviewing the H2 cold-admission protocol, before
that campaign was run.

## Finding

`CLFLUSH` / `CLFLUSHOPT` retire as instructions under Ruby/CHI but generate **no
memory-system activity at all**.  They do not evict.  The same binary on gem5's
classic memory system evicts correctly.

A/B probe: touch 512 lines (32 KiB, resident in a 48 KiB L1D), optionally
`_mm_clflush` each, `mfence`, re-read all 512.

| | classic | Ruby/CHI |
| --- | --- | --- |
| L1D/dcache misses added by the 512 flushes | **+511** | **+4** (noise) |
| cache accesses added | -13 | **0** |
| `simInsts` added | +2057 | +2057 |

Identical instruction counts prove the flushes executed in both.  Only the
classic hierarchy acts on them.

## Why

`Clflushopt` is a store microop carrying
`Request::CLEAN | Request::INVALIDATE | Request::DST_POC`
(`src/arch/x86/isa/microops/ldstop.isa:667`).  `Packet::makeWriteCmd`
(`src/mem/packet.hh:1023`) turns that into `MemCmd::CleanInvalidReq`, whose
attributes are `{IsRequest, IsInvalidate, IsClean, NeedsResponse, FromCache}` --
notably **not** `IsWrite`.  `Sequencer::makeRequest` therefore reaches
`src/mem/ruby/system/Sequencer.cc:1052` and assigns
`RubyRequestType_FLUSH`.

CHI has no handler for it.  Grepping `src/mem/ruby/protocol/chi/*.sm` for
`FLUSH` returns nothing; the CPU-side dispatch in
`CHI-cache-actions.sm:166-180` accepts only LD/IFETCH/ST/ATOMIC_* and otherwise
calls `error("Invalid RubyRequestType")`.  Empirically no panic occurs, so the
request is retired before reaching the protocol -- the exact short-circuit was
not pinned down, and the observed `l1d.cache.m_demand_accesses` delta of **0**
shows it never reaches the L1 controller.

## Consequences

1. **The H2 cold-admission protocol's scrub does nothing.**  Its step
   `clflush_full_region` is inert, so the ROI is warm in *both* arms: `fill_fact`
   leaves the fact dirty in L2 and its writebacks populate the HNF.  No cold
   start is established, and `declare_streaming` runs *after* `fill_fact`, so
   both arms enter the ROI with HNF residency.
2. **Gate A3 certifies a step that never happened.**  It tests
   `cold_start_protocol == "...clflush_full_region..."` and
   `cold_scrub_complete is True`, both *self-declared by the guest* after calling
   the inert routine.  The gate passes while nothing is scrubbed -- the F11/F12
   pattern: a criterion satisfiable without the mechanism.
3. **Any gem5-measured flush-behind arm is invalid.**
   `join_range_flushbehind` (`cxl_join_bench.cpp:628`) is built on
   `_mm_clflushopt`.  The published flush-behind cost (14-17%) is from **real
   silicon** and stands; a gem5 flush-behind comparison must not be produced
   without fixing this.

## Required fix

CLFLUSH cannot be used to scrub under Ruby.  Scrub with ordinary loads/stores
instead: a disjoint cacheable eviction buffer sized comfortably beyond total HNF
capacity, traversed after the private caches, mapped across the same HNF slices.
Then *prove* the cold start rather than declaring it: require ~zero fact-range
HNF demand hits in the first ROI pass, in **both** arms, and reset statistics
only after that check passes.  Replace A3's protocol-string test with that
measurement.
