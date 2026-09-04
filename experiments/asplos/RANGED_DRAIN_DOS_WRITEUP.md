# The transition-storm DoS, and why the ranged-drain relocation actually closes it (#32)

> **Forward pointer, 2026-09-04: this analysis is sound, and the entry path it
> analyses is no longer baseline.** Everything below was true of the revision it
> was written against (2026-08-13). The mitigation it argues for has since
> **shipped**: at the kernel tip (`linux` `pr4-work`, tip `ae43f80e67`) baseline
> H2 entry performs no writeback and no machine-wide clean, and is measured in
> **microseconds** — 72–90 µs across four committed QEMU/KVM guest boots
> (`data/kernel/`), 124 µs in gem5 r12. The ~48 ms `WBNOINVD` survives only as
> `CONFIG_PAT_STREAMING_H3_SEAL_ORACLE` (`arch/x86/Kconfig:1848`, **`default n`**),
> reached solely through `IS_ENABLED(...)` at `mm/mprotect.c:900`.
>
> **Read every present tense below as "as of 2026-08-13".** In particular the
> primitive of §"The primitive, stated plainly" (lines 21–39) **does not exist in
> baseline H2 today**: a 72–90 µs operation confined to the declarer is not a
> denial-of-service vector. The primitive is now a property of a **default-off
> oracle** that the Kconfig help text tells you not to enable, not a property of
> the mechanism the paper proposes. This is a change of *scope*, not a retraction
> of the reasoning: the coherence argument in §"Why the broadcast is machine-wide
> today" and the sharer-set precision argument are exactly why the entry drain
> could be removed, and they remain the live justification for H3's bounded seal
> and retire.
>
> **Two clauses are now out of date as statements about the paper, and both are
> good news.** First, lines 13–15 report that "the words 'DoS,' 'unprivileged,'
> and 'storm' appear nowhere in `~/STREAMING_Paper/`" and treat that as a gap.
> Re-checked across all eleven `Text/*.tex` today: `DoS`, `storm`, `denial`,
> `attack`, `adversar`, `malicious` and `threat` still appear **nowhere**, and
> `unprivileged` now appears exactly once — `Appendix.tex:669`, correctly scoped.
> **That absence is the correct end state, not a gap**; see
> `PAPER_SESSION_PROMPT.md` "Correction — 2026-09-04". Second, the closing line
> "This has not been landed in `~/STREAMING_Paper/` yet" is superseded: §"Recommendation
> for the paper" items 2 and 3 **were** landed, at `Appendix.tex:674-681`
> ("The fix needs precision in \emph{who}, which the snoop filter already
> records"), and item 1 was landed **rescoped** — `Appendix.tex:660` attributes
> the cost to the "H3-oracle" and line 674 states that "Removing the broadcast
> from H2 closes it for the portable path." Whoever drafted it dropped the
> security framing and kept the coherence argument. That was the right call and
> it is why the paper needs no correction today.
>
> One code note, since this document turns on the exit-side drain: commit
> `888060f6a66e` removed the `drain_at_exit` debugfs knob **and the
> `streaming_drain_range()` call site**. The function is still defined
> (`mm/streaming.c:383`) and declared (`mm/internal.h`) with **no caller anywhere
> in the tree**, so the ranged exit drain this document designs is present as code
> and unreachable as behaviour. See
> `RANGED_DRAIN_IMPLEMENTED_2026-08-19.md`'s forward pointer of the same date.

Written 2026-08-13. Per `PAPER_SESSION_PROMPT.md` #32: *"The 48 ms
machine-scoped IPI broadcast at epoch entry is an unprivileged DoS primitive
if any process can trigger it in a loop... A reviewer who finds this before
we do will find it in the worst possible way."*

**The ranged-drain relocation argument itself is already written** —
`Appendix.tex` ("Epoch-exit ordering," "Why the entry broadcast is
conservative") and `Sec5_Evaluation.tex`'s cost paragraph already state that
`Streaming` and WB are both coherent cacheable types, so no stale-alias
hazard exists at entry, and that the drain belongs at exit/reclaim, ranged
over the VMA. **What is not written anywhere in the paper is the security
framing** — the words "DoS," "unprivileged," and "storm" appear nowhere in
`~/STREAMING_Paper/`. This document supplies that, and goes one step past
"ranged over the VMA" to what "ranged" needs to mean for the fix to actually
hold, not just relocate the problem.

## The primitive, stated plainly

Today's entry path (`Sec5_Evaluation.tex:18-30`): `mprotect`-style call →
PTE rewrite → clear writable bit → **broadcast a machine-wide writeback
IPI**. Measured cost: ~48 ms, *size-independent*, scaling with logical-CPU
count (64 on the measurement host), not object size — a 4 KB epoch costs
the same as a 256 MB one.

Declaring an epoch is, by design, an ordinary unprivileged operation — the
entire point of `Streaming` is that an application declares its own
immutable read epoch without special privilege. Put those two facts
together: **any unprivileged process, on any multi-tenant host, can impose
a ~48 ms machine-wide serialization stall on every logical CPU by declaring
a trivial (single-page) streaming epoch, and can repeat this at whatever
rate a tight `mprotect`+`munprotect` loop achieves.** The attacker's own
cost is near zero (a 4 KB mapping); the victim set is every other tenant on
the machine, including ones sharing nothing with the attacker. This is
precisely the shape CXL pooled memory's own threat model should worry
about most: a primitive whose cost the *declarer* does not pay, in a
setting the paper's own motivation section already frames as multi-tenant.

## Why the broadcast is machine-wide today, and why "ranged over the VMA" is not by itself the full fix

The paper's existing argument establishes *that* entry needs no drain. It
is worth being precise about *why* the SDM-mandated procedure is
machine-wide in the first place, because the answer determines what
"ranged" has to mean for the exit-side drain to not just be a smaller
version of the same problem.

TLB shootdowns are already cheap and precise in Linux: `flush_tlb_mm_range`
targets exactly the cores in a mapping's cpumask, because a *virtual*
translation is process-scoped. The writeback IPI is a different animal: **a
physical cache line is coherent, and therefore visible to, every core in
the coherence domain regardless of which process mapped it** — any core
could hold a cached copy of a given physical address from an unrelated
mapping (a shared library page, a page-cache-backed file, a prior tenant of
a reused physical frame). The x86 SDM's documented procedure for a general
memory-type change is conservative for exactly this reason: it is an
ISA-level operation that cannot assume any particular coherence-tracking
precision is available, so it broadcasts to everyone.

**This project's own gem5/CHI model already has the precision the ISA-level
procedure lacks.** The directory (`dir_sharers` in `H3_IMPL_SPEC.md`,
`CHI-cache.sm`) tracks *exactly* which cores currently hold a cached copy
of a given line — it is the same structure `Initiate_SF_Eviction` already
targets with `SendSnpCleanInvalid` for an ordinary capacity eviction. If
the exit/reclaim-time drain is expressed as an invalidation against the
directory's recorded sharer set for the range — not a VMA-size-bounded but
still all-core broadcast — then:

- A typical single-reader (or few-reader) epoch drains against a **sharer
  set of size 1 (or a handful)**, not 64+ logical CPUs. The blast radius
  shrinks to cores that actually cached something from this object, which
  for an attacker's own trivial epoch is the attacker's own core(s).
- **Ranged by VMA size alone does not get you this.** A VMA-bounded but
  still machine-broadcast drain still interrupts every core, just to do
  less work once there — the interrupt-handling overhead of an all-core IPI
  does not vanish just because the flush loop inside the handler got
  shorter. The sharer-set precision is what removes the *machine-wide
  interrupt*, not just the *work per interrupt*.

This is not a new mechanism to build: it is the existing H2/H3 directory
already doing, for the drain, what it already does for capacity eviction.
The paper does not currently make this connection explicit, and should —
it is the difference between "ranged" as a size bound and "ranged" as the
actual fix.

## Does relocating to exit actually kill the loop, or just move it?

The honest version of this question, worked through rather than asserted:

**Can an attacker still loop entry+exit rapidly against the relocated
design?** Yes — nothing stops a process from declaring and immediately
ending its own epoch in a tight loop. What changes is what that loop now
costs, and to whom:

1. **Entry costs nothing extra** (no hazard, no drain, per the paper's
   existing argument) — there is no machine-wide operation left on the
   entry side to loop against, at any rate.
2. **Exit's drain, done sharer-set-precise, costs the attacker their own
   cores, not everyone's.** A freshly-mapped, never-shared, single-page
   object has a directory sharer set of size 1 (or 0, if the attacker never
   even read it) — the drain has nothing to invalidate anywhere but the
   attacker's own cache hierarchy. A self-inflicted cost paid entirely by
   the triggering process is not a cross-tenant denial of service; it is
   just that process wasting its own cycles, which it could already do a
   thousand other ways.
3. **Reclaim-time drains are not attacker-triggered at all.** When the
   *kernel* reclaims a physical frame (as opposed to the *application*
   ending its own epoch), the trigger is memory-pressure-gated allocator
   behavior, not a raw syscall an unprivileged process controls the rate
   of. This path was already outside attacker control before this
   analysis; it stays that way.

So the relocation does not merely make the storm smaller — it moves the
expensive operation off a trigger the attacker fully controls (an
arbitrary unprivileged syscall, repeatable at whatever rate they choose)
and onto triggers that are either (a) gated by the attacker's own real
resource footprint, so any remaining cost is self-inflicted, or (b)
kernel-mediated and already rate-limited by existing memory-management
policy. That is a categorical change, not a size reduction, and it is
the argument that actually earns the word "closes" rather than "relocates."

## What to say if a reviewer asks about a shared-object epoch

The one case worth naming explicitly, because it is the one where the
sharer set is *not* trivially small: a legitimately multi-reader epoch
(the paper's own motivating case — several tenants scanning the same
immutable object) has a real, possibly large sharer set by design, and its
exit-time drain genuinely does need to reach all of them. This is not a
DoS gap, though — reaching N legitimate, currently-caching readers at exit
is proportional to *real, declared sharing*, not to an attacker's ability
to manufacture cost against strangers. The distinguishing question a
reviewer should be pointed at is not "can the drain ever be expensive" (it
can, honestly, for a genuinely widely-shared epoch) but "can an
unprivileged party make it expensive *against victims who never touched
their object*" — and the sharer-set-precise design answers no to the
second question while still doing the necessary work for the first.

## Recommendation for the paper

Add a short, explicitly-named subsection or paragraph — near
`Appendix.tex`'s "Why the entry broadcast is conservative" is the natural
site, since the coherence argument it needs is already established there —
stating:

1. The primitive plainly: unprivileged, size-independent, machine-wide,
   loop-able at entry today.
2. That the fix is not merely "ranged over the VMA" but **ranged over the
   directory's recorded sharer set**, reusing the same structure H3's
   eviction path already targets — naming this explicitly forecloses a
   reviewer's obvious follow-up ("ranged by what, and does that reintroduce
   an all-core IPI with a shorter handler?").
3. The self-scoping argument in miniature: a trivial, unshared epoch drains
   against a trivial sharer set, so the worst a looping attacker can do is
   waste their own cycles.

This has not been landed in `~/STREAMING_Paper/` yet — draft only, pending
review of the exact placement and whether the lead wants it as prose or as
a short numbered list matching the existing "Epoch-exit ordering" style.
