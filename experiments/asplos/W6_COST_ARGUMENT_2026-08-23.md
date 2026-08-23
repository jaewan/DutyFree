# W6 — the cost argument, sourced to the two diffs

Written 2026-08-23. `PLAN_B_REBUILD.md` W6: *"Nobody adds hardware for 6%.
People do add a PAT encoding for 6%."* That sentence is currently unsupported
in the paper. This document supplies the support, and it is deliberately built
out of **diffstats and measured numbers**, not architectural assertion, because
the referee's named reject reason (W4) is unsourced claims.

Nothing here is a new experiment. The hardware side is `~/DutyFree-Gem5`; the
OS side is `~/DutyFree/linux`; the CAT comparison is W5.3's measured table.

---

## W6.1 — hardware cost

Full derivation in `W1.2_H3_ATTRIBUTION_2026-08-23.md` §"Consequence for W6".
Summary, across `5bdfcd8e19` (H2), `44b7eb7470` + `0102eee441` (H3) and
`b49615b3c7` (prefetch propagation):

| | cost |
|---|---|
| new coherence states | **0** |
| new protocol events | **0** |
| new CHI request types | **0** |
| new structures | **0** |
| state added per line | **1 bit** (private `CacheEntry`), = 0.20% of a 64 B line's storage |
| state added per in-flight request | 1 bit on `CHIRequestMsg` and on the TBE |
| fill-path logic | 2 predicate edits: one disjunct in `needCacheEntry`, one conjunct in `CheckCacheFill`'s `need_fill` |
| H3 additional | 3 guards on HNF directory operations (allocate, final-state update, dir state machine) |
| x86 side | 1 PTE flag, 1 `TlbEntry::streaming` field, 1 `Request::STREAMING_BIT` |

The claim that carries the most weight is the last row of the x86 side:
`STREAMING_BIT` rides the **existing** `cacheCoherenceFlags` word, the same
path that already carries `GLC`/`SLC`. There is no new datapath from the page
walker to the cache controller — the wire exists and is already used by
shipped GPU bypass semantics. This is checkable in minutes against the diff,
which is the point.

**Three things W6.1 must not overclaim, and the paper currently would:**

1. **The gem5 implementation does not use PAT slot 6.** It uses a bespoke
   `EmulationPageTable::Streaming` flag in SE mode. The PAT encoding is
   demonstrated in the *Linux* tree (§W6.2), not in the simulator. Nothing has
   run both halves end to end; that is exactly what W8 is for.
2. **`5bdfcd8e19` bundles a baseline change** — it removed `is_prefetch ||`
   from `needCacheEntry` ("Intel NINE accurate"). Within-campaign arm
   comparisons are unaffected (both arms share the binary), but no number we
   report is "STREAMING vs. stock gem5."
3. **The measured H3 arm is not the described H3** (W1.2). The 1.061x is an
   upper bound until the separable arm runs.

## W6.2 — OS cost

`~/DutyFree/linux`, feature branch `037af838cf7a^..HEAD`, 14 commits,
24 files, **2,073 insertions, 2 deletions**. Split:

| | lines |
|---|---|
| mechanism | **787** |
| tests (kunit + 4 selftests) | 830 |
| documentation (`Documentation/arch/x86/pat-streaming.rst`, 208 of it) | 412 |
| Kconfig / Makefile | 44 |

The mechanism, in full:

```
mm/streaming.c                    575
mm/mprotect.c                      97   <- the entry/exit transition
arch/x86/lib/cache-smp.c           41
mm/internal.h                      30
mm/mmap.c                          13   <- pgprot_streaming() on VMA setup
include/linux/mm.h                 12
arch/x86/include/asm/pgtable.h      9
arch/x86/include/asm/smp.h          5
include/linux/pgtable.h             4
arch/x86/include/asm/mman.h         1   <- the PROT_ bit
```

787 lines is the honest number for "an OS-declared, page-granular memory type,
with enforcement." It is small, and more importantly its shape is the argument:
the PAT plumbing is ~30 lines (`mman.h` 1 + x86 `pgtable.h` 9 + generic
`pgtable.h` 4 + `mmap.c` 13). **Almost all of the 787 is enforcement, not
declaration.**

`mm/streaming.c`'s own structure shows where the cost actually is:

- **I0/I1 enforcement — the largest single block.** `streaming_validate_entry`
  (:203) gates entry on `streaming_single_mapper` (:163) or
  `streaming_sealed_memfd_ok` (:187). A region may become STREAMING only if
  nothing else can write it. This is the contract the paper's I0/I1 name, and
  it is the reason the hardware side is allowed to be as cheap as W6.1 says.
- **The transition — `streaming_apply_cache_bits` (:256)** plus the 97 lines in
  `mprotect.c` that detect `entering_streaming` / `leaving_streaming`.
- **The exit drain — `streaming_drain_range` (:363) and
  `streaming_writeback_all` (:386)**, with `arch/x86/lib/cache-smp.c`'s 41
  lines behind them. `eccecc49e0ff` replaced a machine-wide entry writeback
  with a ranged drain, which is itself a cost-reduction commit.
- A debugfs PTE-query path (:416-:566) that is diagnostic, not mechanism.

**The one OS cost that is not free, and is not measured.** The drain is a real
flush of a real range on real cores. Its cost scales with region size and is
paid at `mprotect`-out and at exit. No number for it exists anywhere in the
repo, and it cannot be produced on this host — mos181 runs `7.0.0-28-generic`,
a distro kernel, not the streaming tree. Measuring the streamer-side cost of
flush-behind is **not** covered by the §3 δ embargo, so this is a permitted and
cheap experiment the moment the kernel is booted somewhere: `mprotect` entry
latency and exit-drain latency as a function of region size, against a
`PROT_READ` control. Until it exists, W6 must say the OS cost is 787 lines
**and one unmeasured runtime cost**, not that the OS cost is free.

## W6.3 — the comparison, stated with our own measurements

The plan's phrasing was "CAT shipped for less benefit than this," which is a
literature claim we cannot source. The stronger version is a claim about *our
own data*, from `W5.3_L5_EVIDENCE_2026-08-23.md`:

- CAT is a shipped, silicon-resident partitioning mechanism with per-way masks,
  per-CLOS registers, and an MSR interface — far more hardware than one PTE
  bit and two predicates.
- On mos182 it recovers the Intel co-run tax **completely** (co-run residual
  1.00x under CAT12), and it charges **1.222x** for the privilege with no
  co-runner present. That partitioning price is intrinsic: a way mask makes
  the victim's own capacity smaller.
- On moscxl it leaves a **12.4x** residual, because AMD's harm is rate-class
  and a capacity knob cannot reach it. The same silicon investment buys nothing
  on the other vendor's machine.
- Neither knob can name a region. Both are core- or class-scoped. `tab:fused`
  is the experiment that makes this bite: fuse the streamer into the victim's
  own thread and CAT recovers **nothing** (214.6 -> 215.0 Mtuple/s).

So the comparison to make is not "CAT shipped for less benefit." It is:

> A way-mask partitioner is a substantially larger hardware investment than a
> PAT encoding, it charges 22% of the victim's own performance to use, it is
> vendor-specific in what class of harm it can reach, and it cannot be aimed at
> an object at all. One PTE bit and two fill-path predicates can be.

That sentence is entirely composed of measured, in-repo numbers, and it does
not require the benefit magnitude to be large. It is the argument the evidence
actually supports.

## What W6 still needs

1. **The drain measurement** (W6.2). Blocked on a booted streaming kernel; not
   embargoed; cheap once unblocked.
2. **The separable H3 arm** (W1.2), because W6.1's cost table describes a
   mechanism whose measured benefit is currently an upper bound.
3. A decision on whether to state the PAT/SE-mode gap in the text or close it
   with W8. Stating it costs two sentences; closing it costs a campaign.
   Recommend stating it — the OS tree already demonstrates the PAT half, and
   claiming an unrun end-to-end demonstration is precisely the W4 failure mode.
