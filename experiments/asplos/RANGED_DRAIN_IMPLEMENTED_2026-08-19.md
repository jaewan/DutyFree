# The 48 ms DoS primitive is mitigated in the prototype

**Forward pointer, 2026-09-04: the runtime knob this record describes has since
been withdrawn.** Kernel commit `888060f6a66e` removes
`/sys/kernel/debug/streaming/drain_at_exit` **and the exit-drain call site with
it**, so the two arms below are *not* recoverable by building two kernels: no
configuration reaches the ranged exit drain, and recovering that arm requires
reverting code. `streaming_drain_range()` still compiles
(`mm/streaming.c:383`) but has no caller anywhere in the tree. Entry now needs
no drain at all under baseline H2 — measured at ~124 µs, not ~48 ms — and the
machine-wide clean survives only as the default-off
`CONFIG_PAT_STREAMING_H3_SEAL_ORACLE`. **No measured quantity is lost**, because
this record already discloses that it carries no performance number (see "What
is still missing"); what is lost is the runtime selectability of the two
validated modes.

**Correction, 2026-09-04: the "~124 µs" in the pointer above is a
clock-quantisation artifact, not a measurement.** Per `A6.19` that pointer is
left verbatim and its superseded clause is quoted rather than deleted:

> Entry now needs no drain at all under baseline H2 — measured at ~124 µs, not
> ~48 ms

**Replacement:** entry now needs no drain at all under baseline H2 — **72–90 µs
on QEMU/KVM** (four committed guest boots, `data/kernel/`), not ~48 ms. The
gem5 full-system figure that produced "124 µs" is **resolution-limited**: that
guest marks its TSC unstable and runs on `refined-jiffies`, whose tick at
`CONFIG_HZ=1000` is 999 848 ns, so `enter_max` = one tick = 999 µs
(byte-identical across all four lifecycle logs) and `enter_avg` =
999 848 / 8 / 1000 = 124 µs. Seven of the eight samples returned a **0 ns
delta**. Cite gem5 as "below the guest clock's ~1 ms resolution", never as
"124 µs". **The direction of the pointer above is unchanged and if anything
understated** — both families put entry three orders of magnitude below
~48 ms — so this corrects a figure's *status*, not the withdrawal.

**And neither figure is comparable to this record's ~48 ms.** Neither family
measures a `WBNOINVD` broadcast; the ~48 ms came from a third platform, the
64-logical-CPU silicon host described in "What the primitive was" below. The
oracle build issues a machine-wide clean and the baseline issues none, so the
collapse is a **mechanism** change, not a platform difference. See
`KERNEL_TEST_AGGREGATE_OUTCOME_2026-09-03.md`, addendum 2026-09-04.

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
