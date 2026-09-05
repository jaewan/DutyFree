# Handback — the STREAMING panic is a guest register-clobber bug, and SE `mprotect` cannot fix it

**2026-09-04.** Written against §7 of `DUCKDB_MMAP_SE_H2_OUTCOME_2026-09-04.md`
(the VOID outcome, commit `5f29346`), whose §7 offered three continuations for
the campaign owner and left the offending store unidentified. **This memo
retracts nothing and edits nothing.** It reports two results:

1. **§2–§5:** §7's option 2 (seal the mapping before marking it) does not work
   as written, because x86-64 SE implements `mprotect` as `ignoreFunc`. The
   proposed fix is inert. A related writeback hypothesis is also dead, on
   inspection rather than on evidence.
2. **§6:** the store has now been **localized**, and the cause is neither the
   seal nor a drain. `mmap_probe.gem5`'s m5op inline-asm wrappers do not declare
   `%rax` clobbered, gem5's m5op instruction unconditionally writes `%rax`, and
   the resulting corruption makes `SET_STREAMING` mark **the tenant's own image
   at VA 0 instead of the probe**. The fix is four characters of asm constraint
   per wrapper, guest-side, with no `gem5.opt` rebuild.

The second result also means the campaign would have VOIDed on `P1` even if the
panic had never fired, because the probe was never marked at all.

`A1_PROVENANCE_LEDGER_2026-08-28.md` and `INDEX.md` are not edited here.
No arm ran. No archive was written. `A6.19` holds: this is an append, and the
documents it refers to are quoted rather than changed. The run in §6 is a
**diagnostic run and not an arm** of `DUCKDB_MMAP_SE_H2`; its output is in
`gem5/logs/diag_duckdb_store_localize/` and
`experiments/asplos/artifacts/diag_streaming_store_localize/`, and nothing was
written under `data/`.

---

## 1. What was proposed, quoted not paraphrased

`DUCKDB_MMAP_SE_H2_OUTCOME_2026-09-04.md` §7, option 2:

> 2. **Mark the probe read-only before the m5op** (`mprotect(PROT_READ)` after
>    fill, then `SET_STREAMING`), which reproduces the invariant Linux enforces
>    and which the protocol comment says the model must not depend on. This is a
>    tenant change and changes what the campaign measures.

A brief dated 2026-09-04 proposed to take that option, treating it as a
minimal reorder of the tenant harness, and to relaunch the smoke and the nine
arms behind it.

## 2. The finding: x86-64 SE does not implement `mprotect` at all

`gem5/src/arch/x86/linux/syscall_tbl64.cc:63` binds syscall 10 to `ignoreFunc`:

```
    {10, "mprotect", ignoreFunc},
```

and `gem5/src/sim/syscall_emul.cc:84-88` is:

```
ignoreFunc(SyscallDesc *desc, ThreadContext *tc)
{
    warn("ignoring syscall %s(...)", desc->name());
    return 0;
}
```

It emits a warning and returns success. It never touches the page table. This
is stock upstream gem5, not a DutyFree change: `git log -L` on that line
reaches only `0261b18ee4` (2025-11-21, "sim-se: reformat syscall tables"),
which moved the entry without altering it.

Three consequences, each independently fatal to option 2 as written:

1. **It cannot clear the streaming bit.** The brief asked specifically whether
   SE `mprotect` clears `EmulationPageTable::Streaming`, since a later
   `mprotect` clobbering the marks would have been a second, independent defect.
   It does not, because it does nothing. That second defect does not exist.
2. **It cannot seal.** The pages stay writable. The offending access still
   translates through a `Streaming`-marked PTE, `arch/x86/tlb.cc:511` still
   stamps `Request::STREAMING_BIT`, and `CHI-cache-actions.sm:159` still fires.
   Sealing before marking is therefore **not sufficient**; and because the seal
   is inert in either position, it is **not necessary** either. Ordering it
   before the mark changes nothing observable in SE.
3. **It returns 0, not `EINVAL`.** See §3 — this is the part worth carrying
   past this campaign.

There is no other route to a read-only page in SE. `EmulationPageTable::ReadOnly`
exists (`mem/page_table.hh:100`) and `arch/x86/tlb.cc:476` honours it when
building a TLB entry, but across all of `gem5/src` nothing on the x86 SE path
ever sets it: `mmapFunc` consults `prot` only to decide file writeback
(`sim/syscall_emul.hh:2055`), and no m5op seals. In SE the m5op is the only
thing in the system that can change a PTE.

This is not inference from source alone. The VOIDed smoke run's own log
(`artifacts/duckdb_mmap_se_h2_smoke/h2_s1.log`) already carries ten
`warn: ignoring syscall mprotect(...)` lines from `syscall_emul.cc:86`, which is
`ignoreFunc`, emitted by DuckDB's loader and allocator during the run that
panicked. The evidence was in hand before the fix was proposed.

## 3. The reusable lesson: a vacuous success would have fabricated a seal

This is the part that generalises past this campaign, and it is the reason this
memo exists rather than a chat message.

`mmap_probe.cpp:268-276` decides what to record from `mprotect`'s return value:

```
  errno = 0;
  if (mprotect(g_probe.keys, g_probe.bytes, prot) != 0) return errno;
  return 0;
```

and `mmap_probe.cpp:399-410` records `mprotect_errno = 0` and
`mprotect_note = "ok"` on that zero, falling back to `PROT_READ` only when the
call reports failure. Natively that logic is sound: stock SPR returns `EINVAL`
for `PROT_STREAMING`, the fallback fires, and the JSON honestly records
`"fell back to PROT_READ"`.

Under SE the same code would have emitted, into
`data/gem5/duckdb_mmap_se_h2.jsonl`, for all nine arms:

```
"mprotect_kind":"streaming", "mprotect_errno":0, "mprotect_note":"ok"
```

That is a recorded `PROT_READ|PROT_STREAMING` seal, reported as having
succeeded, on a range that is still writable — and it would have been *more*
misleading than the native record, because the absent `EINVAL` also suppresses
the honest "fell back to `PROT_READ`" note. A reader of the archive would have
concluded that SE honoured `PROT_STREAMING`.

The general form: **a stub that returns success is more dangerous than one that
returns an error, because the caller's error path is the only place the caller
was going to tell the truth.** Any harness that infers realized state from a
syscall's return value is, under SE, inferring it from `ignoreFunc`. This is the
`F9` requested-for-realized class arriving through a new door — not a flag
recorded as configuration, but a *syscall return* recorded as an effect. The
existing F9 discipline of reading realized values from `config.ini` does not
cover it, because there is no `config.ini` field for a page's protection bits.

Practical rule for this repo: in an SE harness, do not record a protection or
placement change from its syscall return. Either assert the effect through a
channel that actually observes it, or record the request and label it as a
request. The SE-only syscalls currently bound to `ignoreFunc` or
`ignoreWarnOnceFunc` on the x86-64 table include `mprotect`, `madvise`,
`set_robust_list`, `rseq`, `rt_sigaction` and `rt_sigprocmask`; all six appear
in this campaign's own smoke log.

## 4. Two premises of the proposed diagnosis, corrected

Both were offered in good faith and both are wrong on inspection. Recorded
because they are easy to re-derive from a linear read of the file.

**There is no mark-then-seal inversion to reorder.** The two cited line numbers
are real, but `mmap_probe.cpp:391` (`gem5_set_streaming`) and
`mmap_probe.cpp:399` (`try_mprotect`) are in **mutually exclusive preprocessor
branches** of the `#ifdef GEM5` / `#else` at lines 388 and 398, and
`try_mprotect` is itself wrapped in `#ifndef GEM5` at line 267. The `-DGEM5`
binary therefore contains a mark and no seal; the native binary contains a seal
and no mark, `gem5_set_streaming` being an empty stub there
(`mmap_probe.cpp:51`). Neither binary contains both. The proposed change is
not a reorder but the *addition* of a seal to the gem5 path, and per §2 that
addition is inert.

**The "clobber" at `mmap_probe.cpp:33-34` is the inline-asm memory clobber.**
The comment reads "The `"memory"` clobber is load-bearing: set_streaming
re-marks PTEs; bind_pool must land before first touch." It is telling the
compiler not to cache or reorder memory accesses across the m5op. It is not a
statement that `mprotect` can clobber PTE marks.

## 5. A writeback hypothesis, killed on inspection

It was proposed that the guard is tripped not by a guest store but by a **dirty
writeback** from L1D of lines left dirty by the fill — which would make the
missing SE step a drain rather than a seal, and would make the fix a
`clflushopt` or the `0x57` flush-behind oracle over the range before the m5op.
The hypothesis is attractive: it would explain the r5 contrast, the FS path's
immunity, and the invisibility of the store in the tenant source.

It is nonetheless false, and it is false on inspection rather than on evidence,
so no run was spent on it. Three legs, all in
`gem5/src/mem/ruby/protocol/chi/CHI-cache-actions.sm`:

1. **The guard is inside `peek(seqInPort, RubyRequest)`.** It sits at lines
   156-160 within `action(AllocateTBE_SeqRequest)` (opens line 128), whose body
   is a single peek on the **sequencer input port**. That port carries only
   demand requests originating at the CPU sequencer.
2. **Writebacks and evictions do not use that port.** `Send_Evict` (1758),
   `Send_WriteCleanFull` (1807), `Send_WriteNoSnp` (1826) and the rest of the
   replacement family build their messages with `prepareRequest(tbe, ...)` from
   the TBE and enqueue on `reqOutPort`. They never traverse
   `AllocateTBE_SeqRequest`, so they can never reach line 159.
3. **The reachable type set is closed and does not include a writeback.**
   Immediately below the guard, lines 166-181 dispatch exhaustively on
   `in_msg.Type` over `LD`, `IFETCH`, `ST`, `ATOMIC_RETURN`, `ATOMIC_NO_RETURN`
   and `error("Invalid RubyRequestType")` on anything else. Since the guard
   excludes `LD` and `IFETCH` by construction, **the only request types that can
   trip it are `ST`, `ATOMIC_RETURN` and `ATOMIC_NO_RETURN`** — all three of
   them demand accesses issued by the guest and translated through the TLB.

Corroborating: `isStreaming` is a field on `RubyRequest`
(`RubySlicc_Types.sm:193`, default `false`) set from `Request::STREAMING_BIT` at
translation time. An eviction has no `RubyRequest` and no translation, so it
carries no streaming tag to be caught by.

**So the panic is a genuine guest-issued store or atomic, and a drain would not
prevent it.** The `clflushopt`-or-oracle fix that would have followed from the
hypothesis is not licensed, and the question of whether `CLFLUSH` is a silent
no-op under Ruby/CHI (`FB_ORACLE_PREREG_2026-09-03.md`) does not arise here.

## 6. The store, localized: `SET_STREAMING` marked VA 0, not the probe

One diagnostic run reproduced the panic and identified the cause. It was
`--preset gem5-smoke --policy stream`, seed 1, on the registered machine and the
registered binaries, with `--debug-flags=PseudoInst,TLB,ProtocolTrace` and
`--debug-start=34000000000`. It is **not an arm**; it reproduced the panic at
tick `35428746306` against the VOIDed run's `35423497878`, a 5.2 µs difference
with the identical message and machine.

### 6.1 What the m5ops actually received

```
34743860642: pseudo_inst::bindpool(addr=0x7ffff2e84000, size=0x10000, pool=1)
34743860642: bindpool: ... -> 16 allocated, 0 skipped
35355920028: pseudo_inst::setstreaming(addr=0, size=0x10000)
35355920028: setstreaming: addr=0 size=0x10000 -> 16/16 pages marked
```

`bindpool` received the probe's real address. **`setstreaming` received
`addr=0`** with a correct size, and marked 16 pages at VA `0x0`–`0x10000`. The
probe at `0x7ffff2e84000` was **never marked**.

In this SE image the tenant is a PIE loaded at base 0, so `0x0`–`0x10000` is
`mmap_probe.gem5`'s own text, `.data` and `.bss`. All 412 streaming-tagged
accesses in the run fall in it — instruction fetches at `0x3800`, data at
`0xadf8`–`0xb130` — and `nm` places `std::cout` at `0xb040`, `std::cerr` at
`0xb160` and `g_probe` itself at `0xb2a0`. The m5op marked the tenant's own
iostream objects as coherence-bypass memory.

### 6.2 Why `addr` was zero: `%rax` is clobbered and not declared

`mmap_probe.cpp:36-49` writes every m5op as, e.g.:

```
  __asm__ volatile(".byte 0x0f, 0x04, 0x56, 0x00"
                   : : "D"(addr), "S"(size), "d"(pool) : "memory");
```

There is **no output operand and no `"rax"` in the clobber list**, so the
compiler assumes `%rax` survives the instruction. It does not.
`gem5/src/arch/x86/isa/decoder/two_byte_opcodes.isa:159-166` decodes the magic
instruction as:

```
0x4: BasicOperate::gem5Op({{
    uint64_t result;
    bool recognized = pseudo_inst::pseudoInst<X86PseudoInstABI>(
            xc->tcBase(), IMMEDIATE, result);
    Rax = result;
```

`Rax` is written unconditionally, and `pseudo_inst.hh:140` sets `result = 0`
before dispatch, so a void m5op such as `bindpool` or `setstreaming` leaves
**`%rax = 0`**. In `map_probe()` the compiler had scheduled the assignment
`g_probe.keys = p` *after* the `bind_pool` op, still reading `%rax`:

```
    523f:	call   39f0 <mmap@plt>          ; %rax = p
    5244:	mov    %rax,%rbp                ; surviving copy of p
    525d:	mov    %rax,%rdi
    5260:	0f 04 56 00                     ; M5OP_BIND_POOL -> gem5 sets Rax = 0
    5270:	mov    %rax,0x6049(%rip)        ; g_probe.keys = 0
```

so `g_probe.keys` was set to **0** rather than to the mapping. The fill still
worked, and this is why nothing failed earlier: the compiler used the surviving
`%rbp` copy, so the probe was filled correctly and `fill_probe_mod`'s null check
never saw the corrupted global. At the marking site the compiler reloaded the
global across the intervening DuckDB calls, and got the zero:

```
    53f4:	mov    0x5ec5(%rip),%rdi        # b2c0 <g_probe+0x20>  -> 0
    53fb:	mov    0x5ece(%rip),%rsi        # b2d0 <g_probe+0x30>  -> 0x10000
    5402:	0f 04 55 00                     ; M5OP_SET_STREAMING(0, 0x10000)
```

The native binary is immune because its m5ops are empty stubs
(`mmap_probe.cpp:51-55`), which is exactly why the native evidence looked clean.

### 6.3 The failing store

The guard can only see `ST`, `ATOMIC_RETURN` or `ATOMIC_NO_RETURN` (§5), and the
only marked pages are `0x0`–`0x10000`, so the failing access is necessarily a
guest store into the tenant's own image. That much is proven.

**Which** store is strongly indicated but not proven: the debug log's final
gzip block was lost when the process aborted, truncating it 117 ns before the
panic. The last recorded tagged accesses are loads at `0xb061`/`0xb068` inside
`std::cout`, and the last TLB miss in the marked range is `0xb160` — the
`std::cerr` object — from `pc 0x7ffff4d83de0` in libstdc++/libduckdb, with the
final instruction fetches before truncation `0x20`–`0x60` bytes further into
that same routine. The next statement in the tenant after the m5op region is
`std::cerr << "JOIN_MEASURE_BEGIN ..."` (`mmap_probe.cpp:415-417`), whose
ostream bookkeeping stores into the `std::cerr` object at `0xb160`.

This **sharpens** the VOID outcome's §1 reading rather than contradicting it.
That document inferred from the absence of `JOIN_MEASURE_BEGIN` in the log that
the failing store "landed after `gem5_set_streaming()` and before the measured
join began". The evidence now says the failure is not *before* that line but
*inside* it: the line is missing because the store that emits it is the store
that trips the guard.

### 6.4 Two consequences

- **`P1` could never have passed.** `streamingHnfFillBypasses` counts HNF fills
  declined for STREAMING-tagged requests on the probe. The probe was never
  marked, so the count would have been 0 and the campaign would have VOIDed on
  `P1` even had the panic not fired. The `P1` VOID would have been read as "the
  m5op did not reach the HNF", which would have been true and completely
  misleading about why.
- **The wrapper defect is shared with r5's harness.** `cxl_join_bench.cpp:212-252`
  declares its `set_streaming`, `bind_pool`, `flush_range`, `reset_stats`,
  `dump_stats` and `exit` wrappers with the identical `: "memory"`-only clobber
  list. Whether any r5 call site actually kept a live value in `%rax` across an
  m5op is **not audited here and is not asserted** — r5's `h2` arm did report
  853,853 bypasses, which is hard to reconcile with a mismarked range, so the
  likely answer is that its call sites happened to be safe. It is a cheap check
  (disassemble each m5op site in `cxl_join_bench.gem5` and look for a live
  `%rax`) and it is handed back rather than performed, because that binary
  belongs to another campaign.

### 6.5 The fix, priced

Declare `%rax` in each wrapper. Adding an output operand is the minimal correct
form, since a register cannot be both an input constraint and a clobber:

```
  uint64_t ret;
  __asm__ volatile(".byte 0x0f, 0x04, 0x55, 0x00"
                   : "=a"(ret) : "D"(addr), "S"(size) : "memory");
```

- **Guest-side only. No `gem5.opt` rebuild, no simulator digest change.**
- It changes `mmap_probe.gem5`, so the registration's tenant pin
  `2139aa85…` moves and an apparatus deviation must be declared before any arm,
  exactly as Addendum 1 did for the simulator.
- The native binary's behaviour is unchanged, its m5ops being stubs — so the
  native `mmap_count`/`mmap_sum` identity is preserved by construction rather
  than by re-measurement, though re-measuring it is nearly free.
- It should be applied to `cxl_join_bench.cpp`'s wrappers too, but that file is
  another worker's and is currently modified in the working tree; handed back.

Neither of §7's simulator-side options is needed for this. If a `gem5.opt`
rebuild happens anyway for other reasons, the `EmulationPageTable::ReadOnly`
idea in §7 below remains worth folding in as defence in depth, because it would
have converted this silent mismarking into a page fault naming the address.

## 7. Where this leaves §7

§7's three options, re-priced against §2 and §5. Each still needs its own
registration; none is started by this memo.

- **Option 1 (a `wb`/`qui` smoke)** — unaffected by this memo and still the
  cheapest thing that separates "DuckDB is not SE-viable" from "DuckDB cannot
  run on a STREAMING-marked writable mapping". ~35 min.
- **Option 2 (seal before marking, in the tenant)** — **dead as written.** §2.
  A tenant-side seal cannot exist in SE. What survives of its intent is not a
  tenant change at all: the invariant Linux enforces can only be reproduced
  inside the m5op, which is option 3's territory and needs a rebuild.
- **Option 3 (extend the protocol)** — unchanged, and still far outside a
  kill-gate. A narrower simulator-side variant now looks more useful than
  extending the protocol: have `setstreaming` set `EmulationPageTable::ReadOnly`
  alongside `Streaming` in the same loop (`sim/pseudo_inst.cc:641-652`). That is
  where the OS invariant actually belongs in SE, it is atomic from the guest's
  point of view because it happens inside one instruction, and it converts the
  panic into a page fault that **names the faulting address**. It requires a
  `gem5.opt` rebuild and a fresh apparatus declaration, and it should be
  sequenced into the same rebuild as any other pending simulator change rather
  than producing a second digest of its own.

A fourth item now supersedes all three as the actual continuation: **fix the
`%rax` clobber in the tenant's m5op wrappers** (§6.5), declare the new tenant
digest, and re-run the registered smoke. None of §7's three options is on the
critical path any more, because none of them addresses the cause.

## 8. Provenance and hygiene

- **Nothing was applied.** No source file was edited, no binary rebuilt, no
  amendment committed, no arm launched. The §6.5 fix is reported, not applied.
  The registration's tenant pin
  `mmap_probe.gem5` `2139aa85efb386692b14c561df27eeb6ac257d89c9acb5b6c60aa8dc636fd84b`
  is intact and verified by `sha256sum`; the native `mmap_probe` is
  `8a77be743ffcd0520e7749f5e6fa24cfcb31c4ceeaa8e3f1c2c90b994ec97276`.
- **`gem5.opt` was not rebuilt and `gem5/src/` was not modified.**
  `gem5/src/mem/ruby/structures/CacheMemory.cc`, under concurrent audit, was
  not read for edit and not touched.
- **The `A6.19` amendment was deliberately not written.** Committing an
  addendum to `DUCKDB_MMAP_SE_H2_PREREG_2026-09-02.md` asserting that
  seal-before-mark makes the SE path more faithful would have sealed a
  disproved rationale into the registration. A pre-registration that is amended
  with a false mechanism is worse than one that records a VOID, because the
  VOID is recoverable and the amendment is on the record forever.
- **The `G-lock` self-match trap fired again, and the §8 workaround held.**
  A `grep` for `build_Intel_8592/gem5.opt` over a `ps` snapshot returned one
  match, which was the searching shell's own command line. Writing the snapshot
  in one command and searching it in a separate one, as
  `DUCKDB_MMAP_SE_H2_OUTCOME_2026-09-04.md` §8 recommends, made the false
  positive obvious rather than convincing. No `gem5.opt` was running and no
  process matched `atomic_2cpu_w8_fs_e2e_r6b_16g_join`.
- **Diagnostic run, labelled.** One cell, 47 min wall including debug overhead,
  aborting at the same panic. It ran under
  `gem5/logs/diag_duckdb_store_localize/`, not under
  `gem5/logs/fs_restore_chi/` and not under the campaign's own
  `se_duckdb_mmap_h2*` paths, so it cannot be mistaken for an arm. `stats.txt`
  is 0 bytes; no counters exist and none are quoted. Evidence excerpts, with a
  `SHA256SUMS`, are in
  `experiments/asplos/artifacts/diag_streaming_store_localize/`: the m5op
  DPRINTF lines, all 412 streaming-tagged accesses, the panic excerpt, the two
  disassembled m5op sites and the `.bss` symbol map. The 1.8 GB raw trace is
  not committed.
- **Cost.** One diagnostic run. The five-to-six hours of smoke plus nine arms
  that option 2 would have consumed, to reproduce the identical panic at
  35.42 ms simulated with the probe still unmarked, were not spent.
