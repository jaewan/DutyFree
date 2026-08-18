# The 48 ms DoS primitive is mitigated in the prototype

Written 2026-08-19, answering reviewer item 4. Merged to `DutyFree-Linux` `main`
via PR #3 (`b9f60fa`).

## What the primitive was

Epoch entry broadcast WBNOINVD to every core: **~48 ms, size-independent,
scaling with logical-CPU count** rather than object size. Since declaring an
epoch is by design unprivileged, any process on a shared host could impose a
machine-wide serialisation stall on every other tenant by declaring a
single-page epoch in a loop, at near-zero cost to itself. For a mechanism whose
premise is large objects on shared machines, the cost was billed by exactly the
wrong quantity — and the paper reported the un-relocated number.

## Why the entry drain was unnecessary, not just expensive

Under H2-only semantics WB and Streaming are both **coherent cacheable** types.
A dirty line left in a cache at entry is still findable by coherence, and a
later Streaming read snoops it — there is no data hazard on the read path. The
real hazard is at the other end: stale clean Streaming lines must not survive
into a differently-typed reuse of the frame. That is an exit/reclaim concern,
and unlike a writeback of every cache it can be **ranged over the object**.

## What was implemented

- `streaming_drain_range()` — a page walk over `[start,end)` flushing only
  present PTEs (holes cost nothing), via the **kernel direct map** rather than
  the user VA, because a supervisor-mode access to a user page would trip SMAP.
  hugetlb leaves flushed at their own granularity.
- `mprotect` gates the entry writeback off and records the span leaving the
  epoch, draining it after the type flip and TLB shootdown, still under
  `mmap_write_lock` as the walk requires.
- `/sys/kernel/debug/streaming/drain_at_exit` selects the mode at runtime;
  unset reproduces prior behaviour exactly.

**Deliberately default-off, because it is not sound with H3.** H3 declines
coherence enrolment, so a dirty line left behind at entry could no longer be
located — H3 requires the entry drain. The knob makes that a documented
configuration choice rather than a silent assumption.

## Validation

Boot-tested under QEMU in **both** modes, full suite green in each:

| mode | `streaming_basic` | `streaming_reject` | `streaming_memfd` |
|---|---|---|---|
| entry drain (default) | 7/7 | 3 + 1 skip | 3/3 |
| `drain_at_exit=1` | 7/7 | 3 + 1 skip | 3/3 |

`streaming_basic` walks the whole WB→Streaming→WB cycle including the write
fault and the post-exit write, so phase 2 exercises the new drain path end to
end.

## What is still missing, stated plainly

**No performance number.** The ~48 ms came from real hardware with 64 logical
CPUs; QEMU cannot reproduce WBNOINVD cost, so nothing here measures the
mitigation's benefit. The claims the paper would want — entry becomes O(1) in
machine size, exit scales with object size, break-even falls well below
realistic CXL object sizes — all need the patched kernel booted on the
measurement host. That is also exactly the figure deleted from
`Sec5_Evaluation.tex` as a TBD, and it stays deleted until measured.

So the honest status is: **the primitive has a mitigation, the mitigation is
correct, and its benefit is unmeasured.** That is a better position than
reporting the primitive with no answer, and worse than the figure the paper
originally wanted.
