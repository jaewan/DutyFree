# Sealed-memfd admission: code-grounded estimate

**Forward pointer, 2026-09-04: the carrier this estimate scopes has since been
withdrawn.** The one-day tier below was built
(`SEALED_MEMFD_IMPLEMENTED_2026-08-16.md`) and then removed by kernel commit
`888060f6a66e`, which narrows admission to private anonymous and private
hugetlb; the tip asserts `EINVAL` for a sealed single-mapper memfd. The reason
is the one §3 below already names — a point-in-time mapper count does not
establish I0 — so the estimate's own analysis stands; the capability does not.

Written 2026-08-16. **Supersedes the first version of this file**, which was
structural because the prototype appeared to be outside version control. It
was not — the submodule pointed at an empty default branch (see
`PROTOTYPE_LOCATION_2026-08-16.md`). The prototype is
`DutyFree-Linux` `claude-draft2` = `63dab9b`, `v6.8-10-g63dab9b1239c`, now
wired into the submodule. Everything below is read from that code.

## 1. What the prototype actually admits

`mm/streaming.c:streaming_validate_entry()` (415-line file) rejects, in order:

| check | reason given in-tree |
|---|---|
| `xen_pv_domain()` | Xen PV overrides `ptep_modify_prot_transaction()` |
| `vma->vm_flags & VM_PAT` | "`track_pfn_remap()` already owns the cache bits ... typically device-DAX" |
| `VM_PFNMAP \| VM_MIXEDMAP` | "**Device-DAX / PFN-only mappings are out of prototype scope**" |
| `(VM_SHARED && vm_file)` | "Writable file-backed mappings can have writeback I/O in flight against dirty page-cache entries" |
| `userfaultfd_wp(vma)` | PTE markers race the post-pass cache-bit rewrite |

So the admitted set is **private anonymous mappings, including hugetlb**
(commit `7836f7b`). The rejection set is codified as a test in
`tools/testing/selftests/mm/streaming_reject.c`.

`Documentation/arch/x86/pat-streaming.rst`'s own "Out of scope" list confirms:
device-DAX/PFNMAP, KSM/autoNUMA/compaction, KVM memslot fences, and
"**multiple concurrent streaming users contending on the same physical
pages**."

**This corrected a false claim in the paper** — `Sec4_Streaming.tex` said "the
prototype admits anonymous and device-DAX mappings" and "records frame-type
ownership". Device-DAX is explicitly rejected, and there is no ownership record
anywhere in `mm/streaming.c`. Fixed 2026-08-16 with a margin note carrying this
evidence.

## 2. Why sealed memfd is a small change — the existing rationale supports it

The blocker is one predicate: `(VM_SHARED && vm_file) -> -EINVAL`. Its stated
reason is *writable* file-backed mappings with dirty page-cache writeback in
flight.

**A sealed memfd is exactly not that.** `F_SEAL_WRITE` cannot be applied while
a writable mapping exists, no writable mapping can be created afterwards, and
seals are one-way for the object's lifetime. And shmem has no writeback to a
backing file — it pages to swap. So admitting sealed shmem is *consistent with*
the reason the check exists rather than a weakening of it. That is the
strongest possible position for a patch: it narrows the exception to precisely
the case the original rationale does not cover.

The machinery downstream already works carrier-independently:

- `streaming_apply_cache_bits()` walks the VMA and rewrites PTE cache bits
  under each PTE lock, then invalidates TLBs.
- `vma_set_page_prot()` is overridden so that "page faults, COW and swap-in all
  install slot-6 PTEs without any extra plumbing in the fault path"
  (`pat-streaming.rst:142`).
- hugetlb leaves are rewritten in place via `streaming_hugetlb_entry()`.

None of that is anonymous-specific.

## 3. What is genuinely missing: I0 across address spaces

Confirmed by reading, not inferred: there is **no frame-type ownership record**
in `mm/streaming.c` (the only `owner` is a debugfs `.owner = THIS_MODULE`). The
prototype does not arbitrate conflicting types — it *avoids* the problem by
rejecting every carrier where two mappers could disagree.

The moment a sealed memfd is shared by N processes, I0 ("a physical frame has a
uniform memory type within its coherence domain") requires all N sets of PTEs
to agree, and there is no cross-`mm` mechanism to make them. This is the
prototype's own "multiple concurrent streaming users contending on the same
physical pages", tracked as Steps B–F.

Note this is the **same** design question the paper's §4 now names. Sealing
solves I1 and does nothing for I0. That split is the real content.

## 4. Estimate

| scope | estimate | basis |
|---|---|---|
| **single-mapper sealed memfd** | **~1 day** | relax one predicate + `F_SEAL_WRITE`/`GROW`/`SHRINK` query; downstream PTE path unchanged; test harness (`streaming_basic.c`, `streaming_reject.c`, KUnit) already exists |
| **multi-mapper, pages pinned** | **~1–2 weeks** | needs cross-`mm` type agreement, which does not exist today; pinning avoids the swap/reclaim half |
| **+ swap/reclaim/migration correct** | beyond that | explicitly Steps B–F; the prototype currently *refuses* swap-paged pages rather than integrating |

Requiring `F_SEAL_GROW`/`F_SEAL_SHRINK` as well as `F_SEAL_WRITE` matters: a
resize under an epoch would change the frame set beneath a recorded type.

## 5. Recommendation

**Do the one-day version first**, even if the multi-mapper case is later
dropped for schedule. It is the difference between "our prototype takes
anonymous memory" and "our prototype consumes a sealed, shared object of
exactly the kind Ray Plasma produces" — and it exercises the full declaration
chain (application seal → OS memory type → hardware non-allocation) end to end
for a single reader. That is the paper's thesis demonstrated rather than
asserted, for roughly a day of work against a codebase that already has KUnit
and kselftest scaffolding to hang it on.

Whether to then spend 1–2 weeks on multi-mapper I0 is a schedule call against
#28, and I would not make it before #28 has run.
