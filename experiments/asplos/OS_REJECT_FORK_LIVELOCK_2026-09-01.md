# `fork()` during a STREAMING epoch livelocks the kernel prototype

Date: 2026-09-01.  Found by the OS-contract enforcement suite, which is the
point of having one.

## Observation

`streaming_reject` (TAP plan `1..17`) passes tests 1-11 and then stops
producing output.  The gem5 process burns **99.9% CPU for 14,610 s** while the
guest console has been unmodified for **239 minutes**.  Spinning, not blocked:
a stalled `waitpid` would idle.

Last output:

    ok  9 MADV_DONTNEED during STREAMING epoch -> EINVAL
    ok 10 FOLL_FORCE write during STREAMING epoch is rejected (errno=5)
    ok 11 MADV_DONTFORK omits STREAMING VMA from child

## The test that hangs

Test 12, `linux/tools/testing/selftests/mm/streaming_reject.c` ~line 231:

```c
if (madvise(epoch, REGION_SIZE, MADV_DOFORK))     /* re-enable inheritance */
        ksft_exit_fail_msg(...);
child = fork();                                    /* expected: -1 / EBUSY */
if (child == -1 && errno == EBUSY) { pass; }
else { if (!child) _exit(mincore(...) == 0 ? 98 : 97); ... fail; }
```

Test 11 -- fork *with* `MADV_DONTFORK` -- passes.  Test 12 re-enables
inheritance with `MADV_DOFORK` and forks, which the design intends to reject
with `EBUSY` because a COW alias would break the I1 read-only epoch.  It does
not return; it spins.

## Root cause: an unbalanced `mmap_write_unlock()` in `dup_mmap()`

Found by reading `kernel/fork.c`; none of the three candidates first listed
(kernel COW livelock, child spinning in `mincore`, wedged `waitpid`) was right.

    637   if (mmap_write_lock_killable(oldmm)) { ... }      <- oldmm LOCKED
    647   if (IS_ENABLED(CONFIG_PAT_STREAMING)) {
    648       for_each_vma(old_vmi, mpnt) {
    649           if ((vm_flags & VM_STREAMING) && !(vm_flags & VM_DONTCOPY)) {
    651               retval = -EBUSY;
    652               goto out;                              <- exits HERE
    ...
    661   mmap_write_lock_nested(mm, SINGLE_DEPTH_NESTING);  <- mm locked only HERE
    ...
    788 out:
    789       mmap_write_unlock(mm);                         <- releases an unheld rwsem
    790       flush_tlb_mm(oldmm);
    791       mmap_write_unlock(oldmm);

The `VM_STREAMING` refusal jumps to `out:` from a point **before** `mm`'s
`mmap_lock` is ever acquired, so `out:` performs `up_write()` on an rwsem that
path never took.  That corrupts the new `mm`'s lock state, and the teardown of
the half-built `mm` spins -- matching the observation exactly: 99.9% CPU, no
forward progress, no output.

It also explains the pass/hang split.  Test 11 forks *with* `MADV_DONTFORK`,
never enters the EBUSY branch, so `mmap_write_lock_nested(mm)` is taken normally
and `out:` is balanced.  Test 12 re-enables inheritance with `MADV_DOFORK`, the
branch fires, and the imbalance occurs.

The comment above the check records that it was deliberately moved earlier so
allocation pressure could not turn a deterministic ABI refusal into `ENOMEM`.
Moving it above the second lock acquisition is what introduced the imbalance --
a correct intent with an unnoticed side effect.

## Fix (applied 2026-09-01)

A separate exit label that unlocks only `oldmm`; `out:` falls through into it so
every other path is unchanged:

    out:
        mmap_write_unlock(mm);
    out_oldmm_only:
        flush_tlb_mm(oldmm);
        mmap_write_unlock(oldmm);
        dup_userfaultfd_complete(&uf);
    fail_uprobe_end:

`kernel/fork.o` compiles clean; `vmlinux` rebuilt (`3039d245...`, was
`09c23ea0...`).  The `IS_ENABLED()` guard keeps the `goto` syntactically present
when `CONFIG_PAT_STREAMING=n`, so no unused-label warning.

## Verification status: NOT yet re-run

Three checkpoints are provenance-bound to the old kernel
(`atomic_2cpu_w8_fs_e2e_r12_16g`, `atomic_2cpu_w8_os_contract_r12_16g`,
`atomic_2cpu_w8_h2_admission_r2_16g`).  A checkpoint captures the booted
kernel's memory image, so restoring any of them under the new `vmlinux` is
invalid, and `run_fs_e2e_gate.sh` would refuse it -- `kernel_sha256` is a gated
provenance key.  Confirming the fix needs a fresh boot checkpoint.

**Nothing already measured is invalidated.**  Every completed run used the old
kernel consistently and none forks a STREAMING VMA: the wedge campaign is SE
mode, the H2 admission arms are single-process, and the four passing OS tests
never reach test 12.

## Consequence for the paper

**I1 must not be described as fully enforced until this resolves.**  Ten of the
suite's checks demonstrate rejection working -- `MADV_MERGEABLE`,
`MADV_DONTNEED`, `FOLL_FORCE` writes, `MADV_DONTFORK` inheritance -- but the
fork-during-epoch path, which is exactly the case where a COW alias could
silently violate immutability, does not return at all.  A reviewer running the
artifact would hit this.

The honest framing: the enforcement suite found a defect in the prototype.  That
is evidence the suite is worth having, and it is also an open bug.

## Disposition

The hung run was killed after 4 h to unblock `hugetlb` and `memfd`, which then
completed clean (7/13 with 6 skips, and 3/3).  Its outdir
is preserved as evidence:
`gem5/logs/fs_restore_chi/atomic_2cpu_w8_os_contract_r12_reject`.
