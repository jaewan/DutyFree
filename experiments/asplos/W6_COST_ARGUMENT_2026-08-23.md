# W6 — the cost argument, with the implementation as the evidence

Per `PLAN_B_REBUILD.md` W6: *"Nobody adds hardware for 6%. People do add a PAT
encoding for 6%."* That sentence is the paper's load-bearing rebuttal to the
reviewer who reads a modest benefit number and stops. It is currently absent
from the paper, and where the surrounding text gestures at it, it asserts.

This document replaces the assertion with counts a referee can reproduce with
`git show`. Nothing here is new measurement; it is an audit of what building
`Streaming` actually cost, in the two trees where it was built.

Written 2026-08-23. Not applied to the paper — W5/W6 text edits are held with
W4.1/W4.2 pending the lead's decision on co-author communication.

---

## W6.1 — hardware cost

### The claim, stated precisely

Three claims are worth separating, because they have different strengths:

1. **No new coherence states.** Strong, and now verified.
2. **No new structures.** Strong for H2. For H3 it needs the qualifier below.
3. **The request-side datapath already exists.** Strong, and verifiable from
   what the flag joins rather than from what it adds.

### 1. Zero new coherence states

Counted directly out of the SLICC protocol definition, from the last commit
before this project's work (`6386a580d1`, upstream, 2025-11-25) to HEAD
(`356e7b7d0e`):

| enumeration | before | after | added |
|---|---|---|---|
| `state_declaration(State, ...)` in `CHI-cache.sm` | 33 | 33 | **none** |
| `enumeration(Event)` in `CHI-cache.sm` | 209 | 211 | `CheckSFFill`, `SF_Eviction` |

The state space is untouched. That is the expensive thing to add to a coherence
protocol and the thing a reviewer will look for first, and the answer is zero.

The two added *events* are worth being honest about rather than hiding: neither
belongs to the contract.

```
CheckSFFill, desc="Ensure the finite SF has room for this dir entry;
                   evict an SF victim if full";
SF_Eviction, in_trans="yes",
             desc="Finite-SF capacity eviction: back-invalidate all upstream
                   sharers of a directory-tracked victim";
```

Both model a **finite snoop filter** — a property of the baseline machine we
are simulating, which stock gem5 does not model (its directory is a
`PerfectCacheMemory`). They exist so the model can exhibit the back-invalidation
charge H3 addresses; they would be present in any faithful model of a modern
non-inclusive LLC whether or not `Streaming` existed. H2 and H3 themselves add
**zero events**.

Reproduce:

```
git -C ~/DutyFree-Gem5 show 6386a580d1:src/mem/ruby/protocol/chi/CHI-cache.sm
git -C ~/DutyFree-Gem5 show HEAD:src/mem/ruby/protocol/chi/CHI-cache.sm
```

### 2. The fill-path change is one disjunct

The entire H2 + H3 admission decision, in
`src/mem/ruby/protocol/chi/CHI-cache-funcs.sm:823`:

```slicc
bool needCacheEntry(CHIRequestType req_type,
                    CacheEntry cache_entry, DirEntry dir_entry,
                    bool is_prefetch, bool is_streaming) {
  if (is_valid(cache_entry) ||
      ((is_HN || enable_H3_streaming_bypass) && is_streaming) ||   // <-- all of it
      (enable_DMT && is_invalid(dir_entry) && ...)) {
    return false;
```

One added disjunct in an early-return that already existed, inside a predicate
that already existed and already took `is_prefetch` for the same *kind* of
reason. `is_HN && is_streaming` is H2 (the HNF never fills the LLC for a
Streaming line). `enable_H3_streaming_bypass && is_streaming` is H3 (private
levels do not retain it either, so the read goes out as `ReadOnce` and no
sharer is ever recorded, hence nothing to back-invalidate).

This is the whole mechanism in the fill path. It is a predicate, evaluated at a
point where a predicate is already evaluated.

### 3. The carry from OS to protocol rides an existing channel

The end-to-end path added by `5bdfcd8e19`, hop by hop:

| hop | what was added | file |
|---|---|---|
| page table | `Streaming = 16`, one flag value | `mem/page_table.hh` |
| TLB entry | `bool streaming` | `arch/x86/pagetable.hh` |
| translate | one `if (entry->streaming) req->setCacheCoherenceFlags(...)` | `arch/x86/tlb.cc:510` |
| request | `STREAMING_BIT = 0x00002000` | `mem/request.hh` |
| ruby | `bool m_isStreaming` | `slicc_interface/RubyRequest.hh` |
| CHI msg / TBE / entry | `bool isStreaming, default="false"` | `CHI-msg.sm`, `CHI-cache.sm` |

Six hops, one boolean each. The point is not that six is small — it is **what
the flag joins**. `STREAMING_BIT` is added to `_cacheCoherenceFlags`, whose
existing members are

```
CACHED = 0x400, READ_WRITE = 0x800, SHARED = 0x1000, STREAMING_BIT = 0x2000
```

The group `STREAMING_BIT` joins is literally commented `/** mtype flags */`
— memory-type flags — and its neighbours `GLC_BIT` / `SLC_BIT` / `DLC_BIT`
arrived upstream in `66d4a15820` (2022-12-26), whose title is **"gpu-compute,
mem-ruby: Add support for GPU cache bypassing"**. `CACHED` / `SHARED` /
`READ_WRITE` are set from a *per-mapping* memory type: `gpu_compute_driver.cc`
builds a `CacheCoherenceFlags mtype` and hands it to `allocateGpuVma()`, from
where it rides every request into Ruby and is consumed as allocation policy.

So the shape — *a memory type attached to a mapping, carried per-request into
the coherence protocol, and read there as a cache-allocation decision* — is not
something this work invents. It is a datapath gem5 already had, for exactly the
purpose of bypassing a cache level. Be precise about what `Streaming` does add:
the **TLB → `Request` hop**. The GPU flags are attached at VMA allocation time,
not read out of a PTE by a page walker; `arch/x86/tlb.cc:510` is the one genuinely
new link, and it is three lines.

That is the concrete form of the "argue against datapaths that already exist"
instruction, and it is stronger than the WC / `MOVNTDQA` analogy, because it is
the same field and the same consumer rather than an analogous one.

### 4. Where the cost is *not* zero — state this, do not hide it

H3 is not free and the paper should not imply it is. H3's obligation is that a
Streaming line is not enrolled in the snoop filter. In the model that is a
skipped allocation, which costs nothing. In silicon it means the fill path must
distinguish enrolling from not-enrolling per request, and the *coherence
argument* for why that is safe rests entirely on the read being issued as
`ReadOnce` — no upstream copy is retained, so there is nothing to
back-invalidate and nothing to go stale. The implementation history says this
plainly: `0102eee441` exists precisely because the first H3 attempt retained
lines upstream and tripped a staleness assert.

Two further items on the honest side of the ledger:

- `00fca787bd` is titled **"H3 review fixes (UNBUILT/UNVALIDATED)"** and fixes a
  *silent dirty-data-loss* on the `UD_RU` SF-eviction path. Its own message says
  it "needs rebuild + writer-victim + combined-state validation before trusting
  non-pure-R paths". The validated envelope for H3 is read-only sharers. Any
  cost claim for H3 must be scoped to that envelope, and the paper should say
  so rather than let the reader assume generality.
- H3 forfeits DCT forwarding for multi-reader Streaming lines
  (`CHI-cache.sm`, the `enable_H3_streaming_bypass` comment says so). That is a
  real functional cost, not just an implementation one.

None of this touches H2, whose envelope is clean.

---

## W6.2 — OS cost

Measured against the mainline base the series was developed on, Linux 6.8
(`e8f897f4afef`), through `b9f60fafda72`:

| scope | files | insertions | deletions |
|---|---|---|---|
| **modifications to pre-existing kernel code** | 18 | **409** | 13 |
| new kernel files (`mm/streaming.c`, `mm/streaming_kunit.c`) | 2 | 730 | — |
| kernel proper, total | 20 | 1,139 | 13 |
| selftests + KUnit configs + documentation | 10 | 885 | 1 |
| **everything** | 30 | 2,024 | 14 |

Reproduce: `git -C ~/DutyFree/linux diff --stat e8f897f4afef..HEAD`.

The 409-line figure is the one to quote. It is the amount of *existing kernel*
that had to change; the rest is a new self-contained file plus its tests. For
comparison of order-of-magnitude only, this is a small-feature-sized change, not
a subsystem-sized one, and 44% of the whole series by line count is tests and
documentation.

### The PAT slot is nearly free, and it is inert on shipping silicon

`eb342571ead0` — the entire claim on the x86 memory-type architecture — is
**42 insertions and 4 deletions across 6 files.** The substantive line is one
field in the PAT MSR initialiser:

```c
- pat_msr_val = PAT(WB, WC, UC_MINUS, UC, WB, WP, UC_MINUS, WT);
+ pat_msr_val = PAT(WB, WC, UC_MINUS, UC, WB, WP, WB,       WT);
```

Two properties of this that the paper should be making much more of than it
does:

1. **Slot 6 was already redundant.** In Linux's full-PAT layout it held a
   *duplicate* `UC-`, present only for errata recovery; the errata and pre-PAT
   layouts use slots 0–3 and are untouched. Nothing is displaced.
2. **The encoding is architecturally inert on every deployed x86 CPU.** Slot 6
   is programmed to `WB`, so a Streaming-marked page is bit-for-bit a WB page to
   current silicon. The mark is visible to a page walker that looks for it and
   invisible to one that does not.

Property 2 is a deployment argument, not just a cost argument, and it is
strictly stronger than "cheap to add": **the OS half can ship first, alone, and
correctly.** A kernel that sets `PROT_STREAMING` runs at exactly WB performance
on today's machines and gains the benefit on a machine that implements H2 —
with no `#ifdef`, no feature negotiation at the page level, and no correctness
divergence. The contract degrades to a no-op instead of degrading to a bug.
That is the property `MOVNTDQA` and `WC` do **not** have: they change the memory
model, so software written for them is written differently and cannot be
un-adopted.

### Where the OS cost actually sits

Not in the PAT slot. It sits in I0/I1 — enforcing that a Streaming region is
immutable and single-mapper — and the commit history shows that is where the
iteration went: `f2f3a8b7bca3` (admit single-mapper sealed memfds),
`eccecc49e0ff` (ranged exit drain, *replacing* a machine-wide writeback),
`7836f7b123ce` (hugetlb), `8d947c88c8db` (broadcast `WBNOINVD` to one CPU per
core). `mm/mprotect.c` is the most-modified pre-existing file at 99 insertions.
The transition in and out of the type is the hard part, and the honest framing
is "the enforcement is the cost, the encoding is free," not "it's all free."

---

## W6.3 — the honest comparison

The plan's phrasing is *"CAT shipped for less benefit than this."* As a claim
about Intel's internal justification that is unsourceable and should not be
written. There is a version of it this paper can actually support, from its own
measurements, and it is a better argument:

**The deployed mechanisms were considered worth their silicon, and on the
workloads measured here each of them is inert on the other vendor's machine.**

From `tab:catmba`, the AMD MBA campaign, and the SPR CAT work (W5.3's table):

| | dominant charge | CAT | MBA |
|---|---|---|---|
| Intel SPR | capacity | recovers | inert, costs 47% of streamer BW |
| AMD Bergamo | rate | ~10× residual remains | recovers, costs 4% of streamer BW |

Neither knob is aimable at an object; each is core- or class-scoped, and each is
the wrong instrument on the other machine. Both shipped. Both consume MSR
space, resctrl surface, and validation effort well beyond one PAT slot and one
fill-path predicate.

So the comparison to make is not about benefit magnitude at all. It is:

> The mechanisms already in silicon for exactly this problem cost more, are not
> portable across the two vendors that ship them, and cannot be pointed at the
> object that is causing the harm. The contract costs 42 lines of memory-type
> plumbing and one predicate, is inert where unimplemented, and is aimable by
> construction.

That argument survives a small benefit number. "6% is worth it" does not.

---

## What this does not do

- It does not measure area, power, or timing. gem5 line counts are a proxy for
  design complexity, not for silicon cost, and the document should say so
  wherever it is cited. The defensible claim is *no new coherence states and no
  new structures on the H2 path*, which is a complexity statement.
- It does not establish that H3 is cheap. It establishes that H3 is cheap
  **within a read-only-sharer envelope that has been validated**, and flags the
  unvalidated paths explicitly (`00fca787bd`).
- W6.3's table depends on the AMD/Intel knob results being final. If the δ
  embargo moves, the table moves with it.
