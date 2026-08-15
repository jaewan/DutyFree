# Sealed-memfd admission: implemented, compile-tested, not boot-tested

Written 2026-08-16. Implements the one-day tier from
`SEALED_MEMFD_ESTIMATE_2026-08-16.md`. Branch `streaming-sealed-memfd`
(`f2f3a8b`) on `jaewan/DutyFree-Linux`, PR #2 against `claude-draft2`.

## What changed

`streaming_validate_entry()` rejected every shared file-backed VMA because
"writable file-backed mappings can have writeback I/O in flight against dirty
page-cache entries." A sealed memfd is the one shared carrier that objection
does not describe, so the exception is *narrower* than the rule rather than a
weakening of it:

- `F_SEAL_WRITE` cannot be applied while a writable mapping exists and forbids
  creating one afterwards -> no dirty page-cache entries to race.
- shmem pages to swap, not to a backing file -> no writeback path at all.
- `F_SEAL_GROW`/`F_SEAL_SHRINK` additionally required: a resize during an
  epoch would change the frame set under an already-recorded memory type.

**Restriction: single mapper only.** I0 requires all mappings of a frame to
agree on its type; there is no cross-`mm` mechanism here. The check is
point-in-time and does not prevent a later `mmap()` — a prototype restriction,
not a guarantee. This is the "multiple concurrent streaming users" item the
prototype already defers.

## An invariant this nearly broke

The hugetlb rewrite walk justifies a *read-mode* vma lock by asserting
`streaming_validate_entry()` "rejects all shared file-backed VMAs" — that is
what makes hugetlb PMD unsharing unreachable. Relaxing the rule invalidated
the stated reasoning. The hazard itself cannot occur, because `shmem_file()`
tests for shmem address-space ops so a `MFD_HUGETLB` memfd never takes the
sealed path, but the comment asserted something no longer true and was
corrected. Worth recording: the dangerous part of this change was not the
predicate, it was a comment three hundred lines away that depended on it.

## Testing status, stated plainly

- `mm/streaming.o` builds clean, x86_64 defconfig + `CONFIG_PAT_STREAMING`,
  **no warnings**.
- New `tools/testing/selftests/mm/streaming_memfd.c` covers all three
  outcomes: sealed single-mapper accepted, unsealed shared rejected, sealed
  multiply-mapped rejected. Compiles clean; skips gracefully on a kernel
  without `PROT_STREAMING` (verified by running it on `mos181`).
- **Not boot-tested.** No Streaming-capable kernel was available here; the
  only one is `6.8.0+` on `mos182`, built from a tree this account cannot
  write. The selftest must be run there before the claim is made anywhere.

Until it is boot-tested, **the paper must not claim sealed-memfd support.**
`Sec4_Streaming.tex` currently says the prototype admits private anonymous
mappings including hugetlb, which remains accurate for the merged tree.

## Why this was worth a day

It is the difference between "the prototype takes anonymous memory" and "the
prototype consumes a sealed shared object of exactly the kind Ray Plasma
produces". Plasma's lifecycle — create, write, seal, share read-only — *is* the
epoch at application level, so this makes the declaration chain (application
seal -> OS memory type -> hardware non-allocation) demonstrable end to end
rather than asserted. It is also the paper's own thesis in miniature: a seal is
a declaration no reuse predictor could infer.
