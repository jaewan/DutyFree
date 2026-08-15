# Sealed-memfd admission: what it would take, and why the estimate is structural

Written 2026-08-16. The lead asked for an estimate after checking out the
prototype. The checkout changes the answer, so that comes first.

## 1. The prototype is not in version control

`git submodule update --init linux` succeeds and yields **one commit
(`1d8334d`, "Initial commit") containing `LICENSE` and `README.md` — 24 KB
total.** The README reads "Linux Patch for DutyFree". There is no patch.

Searched exhaustively across both repos:

- The only `PROT_STREAMING` code is `gem5/testcase/dirtax/aggressor.c`, which
  **defines the constant itself** (`#ifndef PROT_STREAMING / #define
  PROT_STREAMING 0x10 /* Linux 6.8 claude-draft2: PAT slot 6 */`) and is
  marked "FS mode only" — a guest program that expects a patched kernel.
- No `.patch` for Linux (only a gem5 CHI/H3 patch and an unrelated
  Kconfiglib makefile patch).
- No `pgprot` / `_PAGE_PAT` / `pat_enabled` code anywhere.

**The prototype does exist**, though: `RANGED_DRAIN_DOS_WRITEUP.md` reports the
epoch-entry cost as *"Measured ~48 ms, size-independent, scaling with
logical-CPU count (64 on the measurement host)"*. That is a real measurement
from a real kernel, on a 64-logical-CPU machine (`c4`/`mos182` is 2x32). So the
kernel lives on a host, not in git.

Two consequences, and the second is the serious one:

1. **I cannot ground an estimate in the code.** Everything below is structural
   — derived from the ABI as described in `Sec4_Streaming.tex` and from how
   Linux's mprotect/memfd/PAT paths work in general. Treat the numbers as
   design-level, not code-level.
2. **Artifact evaluation would fail on this today.** The paper's central
   systems claim is a kernel ABI; a reviewer cloning `DutyFree` gets an empty
   submodule. This needs fixing regardless of what is decided about sealed
   memfd, and it is cheaper to fix now than under a rebuttal clock.

## 2. A correction to my own earlier analysis

Yesterday I argued sealed memfd is the right carrier because `F_SEAL_WRITE`
gives a kernel-enforced, object-level I1. That still holds. But I overstated
what it buys:

**`F_SEAL_WRITE` gives I1. It does not give I0.**

- **I1** ("no CPU may write during the epoch") is *exactly* what the seal
  provides, and provides better than `mprotect` does: sealing fails if a
  writable mapping exists, no new writable mapping can be created, and seals
  are one-way — they cannot be removed for the object's lifetime. For a shared
  object this is strictly stronger than any per-mapping check.
- **I0** ("a physical frame has a uniform memory type within its coherence
  domain") is untouched by sealing. A sealed memfd can still be mapped WB by
  one process and `Streaming` by another; both are read-only, so the seal is
  satisfied while I0 is violated. Nothing about immutability implies type
  uniformity.

For anonymous private memory I0 is nearly free — the frames have one mapper.
**The moment the carrier is shared, I0 becomes the hard half**, and that is the
real content of the `MAP_SHARED` check. This sharpens rather than weakens the
recommendation: sealing is still the right way in, but the work is I0, not I1.

## 3. Structural estimate

Assuming a working prototype on the measurement host.

**(a) Carrier admission + seal validation — small, ~1-2 days.**
Relax the entry check from "anonymous or device-DAX" to additionally accept a
shmem/memfd VMA, and require the backing file's seals to include
`F_SEAL_WRITE`. Require `F_SEAL_GROW`/`F_SEAL_SHRINK` too, since a resize
during an epoch would change the frame set underneath a recorded type. This is
a predicate over the VMA's file plus a seals query; tens of lines.

**(b) I0 across address spaces — the real work, ~1-2 weeks.**
Entry must record type ownership over the *physical frames* and refuse a later
conflicting mapping from any process, not just the declaring one. Linux already
has the right shape of mechanism, and the paper already cites it: the x86 PAT
memtype reservation tree (`arch/x86/mm/pat/memtype.c`, the `track_pfn` family)
exists precisely to refuse conflicting type reservations over physical ranges.
Reserving at epoch entry and releasing at exit is the natural implementation.
The work is in wiring shmem's fault path to consult it and to fail a WB mapping
of frames currently under a `Streaming` reservation.

**(c) The risk item: shmem reclaim, swap, migration, THP split.**
Sealed memfd pages are still shmem pages — reclaimable, swappable, migratable,
subject to compaction and KSM. The paper already states the requirement
("migration, compaction, and KSM must preserve the type on the destination or
end the epoch, never silently alias it"), and for anonymous memory the
prototype presumably handles it. Shared shmem adds writeback and page-cache
paths. This is where an estimate can double.

**Defensible shortcut**: require the object's pages to be pinned for the epoch
(`mlock`/`FOLL_LONGTERM`-style), which removes reclaim and migration from the
picture entirely. That is an honest prototype restriction — say it in the paper
— and it likely collapses (c) to near zero, bringing the total to **under a
week**.

**Cheaper still, if the goal is only to demonstrate the argument**: admit a
sealed memfd only while it has a single mapper (verified by mapcount). That
sidesteps cross-address-space I0 completely and still exercises the whole
declaration chain end to end. It does *not* cover Plasma's real multi-reader
case, so it must be labelled as a demonstration, not a general implementation.

**Summary:**

| scope | estimate | what it demonstrates |
|---|---|---|
| single-mapper sealed memfd | ~2-3 days | the full declaration chain, honestly scoped |
| + pinned pages, multi-mapper | ~1 week | Plasma's real sharing pattern |
| + reclaim/migration correctness | 2-3 weeks | production-shaped |

## 4. Recommendation

The middle row is the target: **sealed memfd, multi-mapper, pages pinned for
the epoch**, with the pinning stated as a prototype restriction. It covers the
Ray plasma motivation, exercises I0's genuinely hard case, and is roughly a
week rather than a month.

But the ordering matters: **get the prototype into version control first.**
It is a prerequisite for anyone estimating this properly (including me), for
artifact evaluation, and for the sealed-memfd work itself being reviewable. An
empty submodule behind a paper whose contribution is an OS/hardware contract is
the single cheapest thing on this list to fix and the most expensive to be
caught on.
