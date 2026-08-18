# Answering Reviewer #2's four questions

Written 2026-08-19. Q1's experiment is running; Q2–Q4 are below.

---

## Q2 — Price the 17.8x data-array-write gap

**First, the gap is larger than reported, and the earlier number understated
it.** `TASK28_PREDICTOR_HEADTOHEAD_2026-08-18.md` quoted the
`DataArrayWriteOnFill` bucket (584k vs 33k, 17.8x). The *total* LLC data-array
write count is the right quantity, and it says something stronger:

| L1_MSHR=16 | data-array writes | tag-array writes | cycles |
|---|---:|---:|---:|
| WB + TreePLRU | 812,501 | 2,437,715 | 31,284,372 |
| WB + BRRIP | **806,306** | 2,209,494 | 25,047,407 |
| \textsc{Streaming} (H2) | **32,854** | 1,658,065 | 25,259,240 |

**BRRIP does not reduce data-array writes at all** — 806,306 against
TreePLRU's 812,501, a 0.8% difference. It is a pure *retention* policy: it
changes which line is evicted, never whether a line is written. H2 is
**24.5x** lower. That is not a tuning gap; it is what "after admission" means.

Priced as bandwidth, which is the unit the fill path is actually contended in:

| | vs BRRIP | array writes avoided | per-core LLC write bandwidth avoided |
|---|---:|---:|---:|
| L1_MSHR=16 | 24.5x | 49.5 MB / 13.18 ms | **3.75 GB/s** |
| L1_MSHR=48 | 12.9x | 47.6 MB / 9.02 ms | **5.28 GB/s** |

Plus a 24–25% reduction in tag-array writes (551k and 529k fewer).

Two things to note. The saving **grows with MLP** (3.75 → 5.28 GB/s as MSHRs
go 16 → 48), because deeper concurrency means more fills per unit time — so it
grows exactly as cores get more aggressive, not less. And it is per core: at
eight streaming cores this is 30–42 GB/s of LLC fill-path write bandwidth not
spent. That is the same resource the paper's own multi-core result already
fingers ("write-back's own fills contend for the LLC fill path"), now with a
number attached.

**Not priced in joules, deliberately.** Converting array writes to energy needs
a CACTI-class array model this project does not have, and inventing a pJ/write
figure would be exactly the kind of unsourced number the rest of this
repository refuses. The honest form is bandwidth and occupancy, above.

---

## Q3 — The multi-mapper I0 story

I0 requires every mapping of a frame to agree on its memory type. The prototype
admits a sealed memfd only while it has one mapper, which does not cover
Plasma's multi-reader case — the reviewer is right that this is the gap.

**The design that closes it is object-scoped type, and the ordering the
application already uses removes the hard part.**

Today the type is a property of a *mapping*, set by `mprotect`. For a shared
object that is the wrong scope: N mappers means N page tables to rewrite, which
needs a cross-`mm` rmap walk under lock — the expensive thing, and the reason
this looked like weeks of work.

But the type belongs to the *data*, which is the paper's own framing, and a
sealed object already has an object-scoped immutability property. So:

1. Producer creates a memfd, writes it, seals it
   (`F_SEAL_WRITE|F_SEAL_GROW|F_SEAL_SHRINK`).
2. Producer marks **the object** `Streaming` — an operation on the fd, allowed
   only when sealed and not currently mapped. A per-inode flag in
   `shmem_inode_info`, next to `seals`.
3. Consumers `mmap(PROT_READ, MAP_SHARED)`. The type comes from the object, so
   they get slot-6 PTEs on first map. The prototype's existing
   `vma_set_page_prot()` override already installs the right pgprot for faults,
   COW and swap-in — so no new fault-path plumbing is needed.
4. Reclaim, not exit, carries the drain — which is where the paper already
   argues it belongs under H2-only semantics.

**I0 then holds by construction**: one object, one type, every mapping
inherits it, and no mapping can disagree because none of them chose it. There
is no cross-`mm` rewrite in the common case, because the type is set *before*
sharing.

That ordering is not a convenient assumption — it is exactly what Plasma does:
create, write, **seal**, then share read-only. The application already
establishes immutability before publishing.

**Residual hazard, and the honest restriction:** a consumer that maps before
the type is set. Two options: refuse the type change while any mapping exists
(enforceable, and precisely how `F_SEAL_WRITE` itself behaves — it fails with
`EBUSY` against an existing writable mapping), or fall back to the cross-`mm`
walk. The prototype should refuse, and say so.

**Cost:** a per-inode flag, one fd operation, a hook where shmem computes
`vm_page_prot`, and reuse of the PTE machinery that already exists. That is the
same order of work as the single-mapper change already merged — **days, not the
1–2 weeks I estimated before**, and the reason is entirely that object scope
plus seal-before-share deletes the cross-address-space rewrite rather than
solving it.

---

## Q4 — Is `Streaming` defensible without H3?

> **Revised 2026-08-19 after Q1 landed.** The recommendation below originally
> said to move H2's case *off* victim protection, because a predictor tied it.
> That rested on the single-core measurement and is **wrong**. Cross-core, a
> tuned predictor recovers *none* of a co-runner's tax (1.67x against
> write-back's 1.65x, where H2 reaches 1.01x) — see
> `Q1_CROSSCORE_PREDICTOR_2026-08-19.md`. Victim protection is exactly where
> H2's case belongs. The revised answer is at the end of this section.

**Yes, but it becomes a different paper, and a narrower one.**

What survives H3's removal:

- The **taxonomy** — enforced⊗context versus advisory⊗address, one enforced
  address-scoped plane whose encodings bundle the two properties. This is the
  paper's most durable contribution and does not depend on H3 at all.
- **Enforcement.** H2 is enforced; `PREFETCHNTA`, Arm Transient and `NTL.S1`
  are advisory. A hint a core may ignore cannot be the basis of a co-runner's
  sizing decision.
- **The admission axis**, now measured: 12.9–24.5x fewer LLC data-array writes
  than a tuned predictor achieves, because a replacement policy cannot decline
  a write. Prediction cannot reach this at any accuracy.
- **The guarantee.** A co-runner can size its working set against a declaration
  and cannot against a predictor's future behaviour.

What is lost:

- The **surplus**. H3 is the part only a declaration can license, and it is the
  answer to "CAT already does enforced non-allocation — you have made it
  address-scoped." Without H3 that objection lands, and the paper reads as
  better plumbing for a known mechanism.
- **Snoop-filter relief.** H2 explicitly does *not* relieve SF pressure; a line
  in a private cache but absent from the LLC still consumes an SF entry. Only
  H3 does. Cutting H3 cuts the only answer to directory pressure.

**Recommendation:** keep H3, and stop asking it to carry a performance number
it cannot have. Its evidence is a correctness argument plus the TLA+ model
check, which is the right species for a claim about the *absence* of a race.
What should change is H2's case: it should rest on **admission cost and the
guarantee**, both of which a predictor structurally cannot provide, rather than
on victim hit rate, where a predictor now demonstrably ties. That reframing
costs the paper a headline number and buys it a claim that survives the
comparison the reviewer asked for.

### Revised answer (2026-08-19)

**Yes, and less narrowly than I first judged.** With Q1 in hand, H2 has a
measured, exclusive benefit on the axis the paper actually claims: it returns a
co-runner from a 1.655x tax to 1.012x, cutting the victim's misses to memory by
99%, where a tuned reuse predictor delivers **-2.4%** of the available benefit.
That is not an accuracy gap a better predictor closes — a replacement policy
admits before it retains, so the eviction that displaces the neighbour has
already happened. Prediction is self-serving; declaration is other-serving.

So H2 stands on its own without H3, and it stands on victim protection rather
than only on admission counts and the guarantee. What H3 still uniquely
provides is snoop-filter relief, which H2 explicitly does not, and the
coherence exemption no load-side observation can license. Keep H3 as the
architectural surplus, evidenced by argument and the TLA+ check; stop asking it
for a performance number. Nothing about the paper's structure now depends on
H3 carrying weight it cannot.