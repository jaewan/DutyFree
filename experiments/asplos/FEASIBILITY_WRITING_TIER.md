# Feasibility writing tier (#31) — four artifacts, no new experiments

Written 2026-08-13. Per `PAPER_SESSION_PROMPT.md` #31: "no experiments,
data in hand," except one explicitly-flagged gap (the full-system gem5 run
in the evidence ladder, §3 below), which is named as missing rather than
faked. Draft only — nothing here has been landed in `~/STREAMING_Paper/`.
Citations to vendor architecture manuals are given by document/section, not
as fabricated `\cite{}` keys — `reference.bib` does not yet have entries for
POWER, MIPS, or resctrl pseudo-locking, and inventing bib keys without
verifying them against the real source is exactly the kind of integrity risk
this project's rules exist to prevent. Whoever lands this should verify and
add the citations properly rather than copy the keys below.

---

## 1. Parts list for a minimal H2 realization

Converts "a label path, not an enforcement engine" (the paper's own
framing) from an assertion into an accounting: four components, each
already-shipped in kind, none novel in isolation.

| # | Part | Where it lives | What it does | Shipped precedent for this *kind* of part |
|---|---|---|---|---|
| 1 | **One PTE bit** | Page table entry, OS-managed | Marks a page `STREAMING` for the current epoch. Sourced once at declaration (`mprotect`/equivalent), read on every translation. | Every memory-type bit already there (PAT index, MPAM PARTID field, Arm's shareability/cacheability attribute bits) — this is one more field in an existing structure, not a new page-table format. |
| 2 | **One TLB field** | TLB entry (or the walk cache, if separate) | Carries the PTE bit through translation so it is available at the point a fill request is issued, without a page-table walk on every access. | Every existing memory-type attribute already rides the TLB this way (cacheability, shareability, MPAM PARTID after ARM's PE-to-TLB propagation). No new TLB port or comparison logic — same field width class as an existing attribute bit. |
| 3 | **One attribute bit on the fill request, inherited by the prefetcher** | The core's L2/L3 fill-request format (already carries a requester id, address, and coherence-state ask) | The demand miss that trains the prefetcher, and every fill request the prefetcher subsequently issues for that page, carries the bit forward. This is H1's entire hardware ask: *do not silently drop the tag when the requester is the prefetcher instead of the core.* | Structurally identical to how a QoS/PARTID tag already survives a prefetch-generated request in shipped designs (MPAM ties the tag to the requesting agent's context, which persists across a prefetcher trained by that context); the delta here is tying it to the *address* instead, which changes where the bit is read from, not what propagates it. |
| 4 | **One gate on the private-cache victim path (the L2→L3 fill/writeback decision)** | Wherever the cache currently decides "victim goes to the next level as a fill" vs "victim is silently dropped" | If the incoming (or evicted) line's tag says `STREAMING` and the destination is the *shared* level, skip the allocation; below the shared level, do nothing different. | This is exactly Intel CAT's/Arm MPAM's/RISC-V CBQRI's existing "do not allocate for context X" decision point, reused with an address-derived condition instead of a context-derived one (`Sec5_5_RelatedWork.tex`, "Enforced non-allocation already ships"). |

**What is deliberately NOT on this list, and why that is the point:** no new
coherence-directory structure, no new request type, no new cache-tag width
beyond one bit, no OS/hardware handshake beyond the existing page-fault and
TLB-shootdown machinery an epoch's entry/exit already needs. H3 (coherence
enrollment skip) is a *further* gate on the same bit at the directory
allocation point (`Allocate_DirEntry` in the gem5 model, `H3_IMPL_SPEC.md`)
— it is additional, not a prerequisite; a H1+H2-only implementation never
touches the directory.

**Honest gap this list does not close:** it says nothing about *verification*
of parts 3 and 4 against a real fill pipeline's timing budget — that is
exactly the risk named in §4 below.

---

## 2. Precedent table

Every row below already has prose treatment in `Sec5_5_RelatedWork.tex`;
this condenses it into one scannable comparison, because the paper is
"still nearly figure-free" (`PAPER_REVISIONS_2026-08-11.md`, "Not done, and
why") and a table carries this argument better than four more paragraphs
would.

| Mechanism | Enforced? | Object-scoped (not context-scoped)? | Preserves prefetch (H1)? | Carries an epoch/immutability declaration (I1)? | Governs coherence enrollment (H3)? | What's missing vs. `Streaming` |
|---|---|---|---|---|---|---|
| Intel CAT / MPAM PARTID / RISC-V CBQRI | ✔ | ✘ (per-core/PE/hart context) | n/a (doesn't touch fill decision, only capacity) | ✘ | ✘ | Right *mechanism* (non-allocation), wrong *scope* — the label rides the requester, not the address (`Sec5_5_RelatedWork.tex`, "Enforced non-allocation already ships"). |
| x86 `PREFETCHNTA`/`MOVNTDQA` | ✘ (hint) | ✔ (per-instruction address) | n/a (bypasses caching outright rather than choosing where) | ✘ | ✘ | Rides *instructions*, so it cannot label prefetcher-generated fills — the majority of traffic in a CXL stream. Measured on this project's own hardware: NTA's best observed LLC-miss reduction (81.2% at pf-distance 512) costs 62.9% of stream bandwidth (`benchmarks/e2e/hash_join/docs/RESULTS.md:370`) — it trades away exactly the thing H1 is supposed to preserve. |
| Arm `PRFM PLDL1/2/3STRM` | ✘ (hint) | ✔ (per-instruction address) | n/a (same bypass-not-choice shape as NTA) | ✘ | ✘ | Same instruction-scope objection as NTA; Arm's own hint, not an enforced admission decision. |
| Arm Normal Inner-WB/Outer-NC shareability attribute | ✔ (architected, page-granular) | ✔ | Implementation-defined (not guaranteed) | ✘ (static config, no epoch) | ✘ | Closest shipped precedent overall (`Sec5_5_RelatedWork.tex`'s own verdict). Cacheability axis, not shareability; no epoch, no revocation, no H3 — spelled out already in four numbered points there. |
| Cuesta et al. (deactivate coherence tracking for OS-private pages) | ✔ | ✔ | n/a | ✘ (private, not immutable-shared) | ✔ (for the *private* case) | H3's nearest precedent, but for privacy, not shared immutability — `Streaming`'s H3 is "the immutable-shared analogue" (already stated in `Sec5_5_RelatedWork.tex`). |
| DDIO (Direct Data I/O, request-type-based constrained-way allocation) | ✔ | ✘ (allocates by *request type* — DMA-in traffic — not by object) | n/a | ✘ | ✘ | Shipped a decade; proves way-constrained allocation-by-classification is production-grade silicon, but the classification axis is the requester/request-type, not the object — same scope objection as CAT, from the opposite direction (I/O-in vs. compute-out). |
| 4 KB prefetch-boundary conventions (stride/adjacent-line prefetchers stopping at page boundaries) | n/a — a design convention, not a control | n/a | n/a | n/a | n/a | Not a mitigation at all; included because it is the reason a page-granular label is a *natural* fit for the prefetcher's own operating unit — the prefetcher already reasons in page-sized windows, so a page-table bit is legible to it for free, unlike an instruction-scoped hint. |

---

## 3. Evidence ladder

Ordered weakest-to-strongest-already-in-hand, per the session prompt's own
ordering, with the one gap named rather than filled with a proxy number.

1. **CAT-at-1-way on Intel (EMR/8592+).** Confining the aggressor to a
   single disjoint LLC way (~20× capacity cut, 20-way LLC) still sustains
   32–33 GB/s aggregate stream bandwidth (measured: 31.34 GB/s vs. a 33 GB/s
   paper reference point, `experiments/phase1/e2_h1_speed/intel_repro_gate_RESULTS.md:52`,
   raw data `benchmarks/data/catmba_s3_cat_1way.csv`). Establishes that
   bandwidth survival does not need LLC capacity at all — the necessary
   condition for H1 to be plausible, on real silicon, at the extreme end of
   an existing shipped knob.
2. **Flush-behind on AMD (EPYC 9754).** Software-emulated non-allocation
   recovers 76.3% [76.1,76.4] of a real application's (hash-join) tax at
   full prefetch bandwidth, at a real, measured, non-embargoed streamer
   cost of 31.34% [31.28,31.39] of its own bandwidth
   (`GATE1_STREAMER_COST_OUTCOME.md`, now landed in `Sec3_Mitigation.tex`).
   Establishes the *magnitude* is worth having and is achievable without
   new hardware — at a real, quantified software cost `Streaming` does not
   pay.
3. **NTA / hint-scoped mitigation.** Trades LLC-fill pressure for
   bandwidth rather than removing the tradeoff: best observed 81.2%
   LLC-miss reduction costs 62.9% of stream bandwidth
   (`benchmarks/e2e/hash_join/docs/RESULTS.md:370`). Establishes that the
   *instruction-scoped* axis cannot reach this problem even when pushed to
   its most aggressive setting — reinforcing the precedent table's verdict
   with a number rather than an architectural argument alone.
4. **gem5.** `tab:gem5`, `tab:h3sf`, `tab:sens` (this session's re-run,
   `GATE1_SENS_RERUN_OUTCOME.md`) — the model, at a named commit, showing
   H2 recovery robust across LLC associativity and victim footprint, and
   H3 additionally removing the finite-SF back-invalidation tax neither CAT
   nor H2 touches. Treated throughout as a **lower bound** per the
   hardware-anchored posture (§4.3 of `PAPER_SESSION_PROMPT.md`), not a
   hardware prediction.

**Rung 5, explicitly not done — full-system existence proof.** The session
prompt asks for "one full-system gem5 FS run (custom OS + a real
application kernel, from a post-boot checkpoint) as an integration
existence proof." This is **not attempted here.** It requires FS-mode gem5
(a bootable kernel image, a checkpoint infrastructure, and OS-side
M5ops/PTE-bit plumbing exercised through a real page-fault/mmap path rather
than SE-mode's direct pseudo-instruction call) — a materially different and
larger undertaking than anything in this writing tier, and different in
kind from the SE-mode harness the rest of this project's gem5 work uses.
Per this project's own rule against silent caps: **this rung is missing,
not weak** — do not let a future pass quietly imply it exists because the
other four are checked off.

---

## 4. Near-miss matrix

Mechanisms that are close in spirit to a page-granular admission label but
fail on a specific, nameable axis — included because, per the session
prompt, "a taxonomy that only lists the sound options reads as marketing."

| Mechanism | What it gets right | What forecloses it |
|---|---|---|
| **POWER WIMG bits (Write-through, caching-Inhibited, Memory-coherence, Guarded), specifically the `I`-bit** | Page-granular, carried in the page table and TLB, architected (not a hint) — structurally the closest thing to "a memory-type bit that changes fill behavior" this survey found outside Arm. | The `I` (caching-inhibited) bit is a binary cache/no-cache switch, not an allocate/don't-allocate-but-still-prefetch distinction — setting it kills caching *and* prefetching together, which is exactly the H1+H2 bundling this paper's whole argument is about. It is the bundled-interface problem the paper diagnoses, not an exception to it. |
| **MIPS cache coherency attributes (CCA) field in the TLB entry** | Same shape as WIMG: a small enumerated field per TLB entry selecting a cache/coherence policy, page-granular, architected. | The CCA enumeration (cacheable-coherent, cacheable-noncoherent, uncached, etc.) is a fixed vendor-defined menu of *whole-hierarchy* policies, not an independently-settable {prefetch, allocate-in-shared} pair — the same missing-admission-cell problem, in a different encoding. |
| **resctrl cache pseudo-locking (Intel CAT's `cachepseudo_locksetup`, and Arm's equivalent MPAM-based locking)** | Object-scoped in practice (you lock a specific data region into specific ways) and enforced by hardware once set up. | It is the *opposite* mechanism from what `Streaming` wants: pseudo-locking *pins a region into* the cache so it is never evicted, aimed at latency-sensitive resident structures — not at *keeping a one-pass stream out* of the cache. It also consumes a static way allocation for the life of the lock (capacity partitioning's scope problem again: it acts after a lookup it cannot prevent for anyone not holding the lock), and is a system/root-privileged setup operation, not a per-object, per-epoch declaration an application makes at its own rate. |

---

## 5. The honest risk, named plainly

**On Intel, part of the MLP a stream depends on lives outside the core.**
LLC-directed streamer prefetches are tracked at the CHA (Caching and Home
Agent) and staged *in the LLC itself* while in flight. H2 removes that
staging ground by construction — a clean streaming line is never supposed
to occupy LLC data-array capacity, fill or victim. That means the bandwidth
claim (H1: prefetching survives non-allocation) does not get to lean on
CHA-staged in-flight capacity; it rests entirely on **private MSHR/superqueue
depth** (on the order of 32–64 entries per core in current Intel designs) or
on **a dedicated non-allocating stream/fill buffer** (on the order of 32–64
entries per L3 domain) that a real implementation would need to add if
private structures alone prove insufficient at scale. **This project has not
measured which of those two regimes a real implementation would land in** —
the gem5 model's MSHR sweep (`tab:h1bw`, itself unresolved this session per
`GATE1_H1BW_RERUN_OUTCOME.md`) is the only instrument aimed at this question
and does not currently settle it.

**The risk asymmetry, which is the reason this risk is survivable to name
plainly:** every H1/H2 failure mode is a **performance** failure, never a
**correctness** one. If private MSHR depth is insufficient and no dedicated
fill buffer exists, a `Streaming` line simply degrades toward the
demand-miss floor — the same floor write-combining already sits at today.
It never gets *worse* than WC (there is no mechanism by which removing LLC
allocation could reduce achieved bandwidth below the no-caching-at-all
baseline), and it never becomes *incorrect* — H1's failure mode is "the
prefetcher doesn't get to hide as much latency as hoped," not "the wrong
data is returned." That asymmetry is what licenses treating this as a named
open risk rather than a blocking one: the downside is bounded by a mechanism
already deployed and accepted (WC), and the upside is bounded above by what
gem5 already shows. Contrast this explicitly with H3's risk shape, which is
categorically different — a coherence-enrollment skip that goes wrong is a
*correctness* failure (a stale read), which is exactly why #29's model
checking (`H3_MODELCHECK.md`) exists as a separate, harder burden of proof
than anything in this section.
