# The m5op `%rax` clobber, audited across every campaign: r5 is clean, and no published claim moves

**2026-09-04.** Written against `DUCKDB_MMAP_SE_H2_HANDBACK_2026-09-04.md`
(commit `8da6499`), whose §6.4 identified a register-clobber defect in
`mmap_probe.gem5`'s m5op wrappers, observed that `cxl_join_bench.cpp` shares the
wrapper pattern, and handed back the question of whether any other campaign was
affected.

*Dating note: this host's clock is KST (UTC+9), so commit timestamps for this
pass read `2026-09-05`; records in this directory are dated by project-local
time (UTC−7) and so are dated `2026-09-04`.*

`A1_PROVENANCE_LEDGER_2026-08-28.md` and `INDEX.md` are **not edited here**;
proposed wording for both is handed back in §8. Nothing under
`/home/domin/STREAMING_Paper/` and nothing in `gem5/src/` was modified. **No arm
ran, no simulation was launched, and `gem5.opt` was not rebuilt.**

---

## 1. Verdict first

**`COMPLETE_JOIN` / r5 — the paper's headline, `fig:frontier`(a) — is CLEAN.
The range it claims to have marked is the range it actually marked.** The
evidence is in §3, and it is in-band evidence produced by the binary that
actually ran, not an inference from a substitute.

**No campaign in this repository mismarked its declared range.** The
`mmap_probe.gem5` defect is, so far as this audit can establish, confined to
`mmap_probe.gem5`, whose campaign had already VOIDed.

| # | campaign | declaration path | verdict | basis |
|---|---|---|---|---|
| 1 | **`COMPLETE_JOIN` / r5** | m5op `0x55` | **CLEAN** | in-band run evidence (§3.2) + counters (§5) + disassembly of nearest relatives (§3.3). Exact binary **gone** (§4) |
| 2 | **`FUSED_KNEE` / `fused.c`** | m5op `0x55` | **CLEAN, by construction** | the wrapper has declared `: "rax"` in *every* revision of `fused.c` that ever existed (§3.4). Schedule-independent. Exact binary **gone** (§4) |
| 3 | **`H1BW_SINGLECORE`** | m5op `0x55` | **CLEAN** | disassembly of the exact binary (`2b9d6732`, on disk, hash-matched to the archive) |
| 4 | **`H1BW_MULTICORE`**, **`H1BW_CXLBW`**, **`H1BW_SLICE_BRACKET`** | m5op `0x55` | **CLEAN** | disassembly of the exact binary (`cac9e27a`, on disk, hash-matched to the archive) |
| 5 | **`H2H_REALJOIN` / r3** | m5op `0x55` | **CLEAN on counters; INDETERMINATE on disassembly** | exact binary **gone** and never hashed (§4). Counter evidence in §5.4 |
| 6 | **`FS_COMPLETE_JOIN` / r6b–r6e** | real `mprotect` | **CLEAN** | disassembly of the exact binaries, **recovered from the committed disk images** and hash-matched to the run manifests (§3.5). All 14 sites safe in each |

One genuine defect was found, in a code path **no committed campaign executes**:
the flush-behind oracle (§6). It is fixed here.

---

## 2. Method, and why the source cannot answer the question

The defect is that gem5 decodes the magic instruction as `BasicOperate::gem5Op`
(`arch/x86/isa/decoder/two_byte_opcodes.isa:159-166`), whose body ends
`Rax = result;` — written **unconditionally** — and `pseudo_inst.hh:140` sets
`result = 0` before dispatch, so every *void* m5op leaves `%rax == 0`. A wrapper
that declares neither an `"rax"` clobber nor an output operand tells the
compiler `%rax` survives.

Whether that lie is *harmful* is a property of the schedule the optimiser
happened to pick, not of the source. So the audit disassembles binaries.

`experiments/asplos/audit_m5op_rax.py` is the instrument, committed with this
record. For each binary it enumerates every m5op site and decides whether a
value the program still needs is live in `%rax` across it.

Three things in it are worth stating because each was a real trap:

1. **Sites are enumerated by raw byte scan of the PROGBITS sections, not from
   objdump's instruction stream.** `0f 04` is an invalid opcode, so objdump
   renders it `(bad)` and desynchronizes. Where the source emits two m5ops back
   to back — `dump_stats()` immediately followed by `reset_stats()` — the second
   falls inside the first's desync shadow and **never appears as a decoded
   line**. An objdump-driven enumerator silently misses it. This was not
   hypothetical: it hid two real sites in `cxl_join_bench.gem5wbrk`
   (`0x411b57`, `0x411b86`), which the corrected enumerator found.
2. **The forward walk restarts objdump at each m5op + 4**, and consumes
   objdump's multi-line byte continuations in order rather than treating them
   as instruction boundaries.
3. **A `call` terminates the walk as SAFE.** `%rax` is caller-saved and the
   integer return register, so the compiler cannot expect a value to survive a
   call and never places a live value in `%rax` across one.

**Positive control.** Run against `mmap_probe.gem5` the tool independently
rediscovers the known defect at `0x5260` — `mov %rax,0x6049(%rip) # g_probe+0x20`
— matching the handback's §6.2 exactly. A tool that finds the one bug already
proven to exist, without being told where it is, is worth more than one that
only reports clean.

**Enumeration was cross-checked.** For `cxl_join_bench.gem5`, an independent
raw-byte scan written separately from the tool found the same 10 sites, at the
same addresses, with the same selectors.

### 2.1 The structural fact that bounds the whole defect

An m5op's own inputs (`%rdi`, `%rsi`, `%rdx`) are read *at* the instruction.
They cannot be corrupted by that instruction's own write to `%rax`. **A
`set_streaming` can therefore only receive a wrong address if some *earlier*
m5op corrupted the value that later feeds it.** In `mmap_probe` that earlier
m5op was `bind_pool`, whose `%rax` clobber landed on the store of `mmap`'s
return value into a global.

This is why the audit tracks value flow from `bind_pool` forward, not just the
`set_streaming` site in isolation.

---

## 3. Per-campaign evidence

### 3.1 r5: what the disassembly of the surviving relative shows

r5 ran `--mode single --policy stream`, so its path is
`alloc_bytes` → `run_single`. In `cxl_join_bench.gem5` (`cac9e27a`):

```
  40bbaf:	e8 fc 24 15 00       	call   55e0b0 <__mmap>      ; %rax = p
  40bbb4:	48 83 f8 ff          	cmp    $0xffffffffffffffff,%rax
  40bbc4:	48 89 c3             	mov    %rax,%rbx            ; SURVIVING COPY, callee-saved
  40bbc7:	48 89 c7             	mov    %rax,%rdi
  40bbce:	48 89 ee             	mov    %rbp,%rsi
  40bbd1:	4c 89 ea             	mov    %r13,%rdx
  40bbd4:	0f 04 56 00          	; M5OP_BIND_POOL -> gem5 sets Rax = 0
  40bbd8:	ba 0a 00 00 00       	mov    $0xa,%edx            ; %rax NOT read
  40bbeb:	e8 d0 55 06 00       	call   4711c0 <__ostream_insert>
  ...
  40bcce:	48 89 d8             	mov    %rbx,%rax            ; RETURNS the pre-m5op copy
  40bcd9:	c3                   	ret
```

This is the exact structural **inverse** of the `mmap_probe` failure. There the
pointer was stored to a global *after* the m5op, from `%rax`. Here the copy is
taken *before* the m5op into `%rbx`, and `%rbx` is what the function returns.

The caller captures it immediately, with no m5op in between:

```
  411ff3:	e8 88 9b ff ff       	call   40bb80 <alloc_bytes>
  411ffd:	49 89 c6             	mov    %rax,%r14            ; %r14 = fact pointer
  ...
  4120ab:	8b 05 df 2b 20 00    	mov    0x202bdf(%rip),%eax  # g_declare
  4120b5:	85 c0                	test   %eax,%eax
  4120b7:	0f 85 80 02 00 00    	jne    41233d               ; -> mprotect path
  4120bd:	4c 89 f7             	mov    %r14,%rdi            ; addr
  4120c0:	0f 04 55 00          	; M5OP_SET_STREAMING(fact, fact_bytes)
  4120c4:	48 8d bc 24 80 01 00 	lea    0x180(%rsp),%rdi
  4120cc:	48 8d 84 24 90 01 00 	lea    0x190(%rsp),%rax     ; %rax redefined, never read
```

`%rax` at the `set_streaming` held `g_declare`, already consumed by the
`test`/`jne`, and is overwritten by a `lea` two instructions later. The address
argument comes from `%r14`, a callee-saved register loaded directly from
`alloc_bytes`'s return.

All 10 sites in this binary, and the 3 on r5's executed path
(`0x4120c0` `set_streaming`, `0x412469` `reset_stats`, `0x412c59` `exit`), are
**SAFE**.

### 3.2 r5: the decisive evidence, produced by the binary that actually ran

§3.1 is disassembly of a **later** binary (§4). The following is not.

`alloc_bytes` prints the pointer to `stderr` **immediately after** the
`bind_pool` m5op, from the same variable `p` whose store is the thing at risk
(r5-era source, `cxl_join_bench.cpp:334-345`):

```c
    gem5_bind_pool(p, bytes, pool);
    std::cerr << "BIND_POOL " << name << " addr=0x" << std::hex
              << reinterpret_cast<uintptr_t>(p) << std::dec << ...
```

and `run_single` passes the *same* C variable to both the declaration and the
JSON report (`cxl_join_bench.cpp:1284-1300`, `:1420`):

```c
  Fact *fact = static_cast<Fact *>(alloc_bytes(c.fact_bytes, ...));
  ...
  if (c.policy == "stream") declare_streaming(fact, c.fact_bytes);   // -> m5op 0x55
  ...
  emit_json_prefix(c, fact, c.fact_bytes, cpus);                     // prints "fact_base"
```

So if the clobber had corrupted the pointer, the run's own log would say so.
The r5 run logs survive in `/tmp/r5` (45 launch logs, one per cell, each
carrying the launcher's `R5_GEM5` / `R5_JOIN` / `R5_VICTIM` hashes). Across
**all 42 cells that run the join** (the 3 `qui` cells run only the victim):

```
     42 addr=0x7ffff77ff000
     42 "fact_base":"0x7ffff77ff000","fact_end":"0x7ffff7fff000"
     42 "probe_accesses":131072
```

- `fact_end − fact_base` = `0x800000` = 8,388,608 B = exactly the requested
  `--fact-bytes 8388608`.
- `probe_accesses` = 131,072 = exactly 8 MiB / 64 B.
- **No cell reports a zero address anywhere.**
- Every cell reports `"correct":true` with 260,875 matches — the join read the
  full 8 MiB through that pointer.

This is direct, in-band evidence, emitted by the lost binary `401373ce` itself,
that the `bind_pool` `%rax` clobber did **not** corrupt the pointer, and that
the value handed to `SET_STREAMING` was the real mapping at `0x7ffff77ff000`
spanning exactly 8 MiB.

**Honest limit.** This shows the C variable `fact` was correct at the
declaration and at the report. It does not, by itself, exclude a compiler having
kept two copies and corrupted only the one feeding the m5op. Two things close
that gap: by §2.1 the m5op's own input register cannot be corrupted by its own
write, so corruption must arrive from the earlier `bind_pool` — and the
`BIND_POOL` line, printed after that op, shows it did not; and §3.1 shows the
compiler's actual strategy on this source is to keep the pointer in a
callee-saved register throughout.

### 3.3 r5: why the substitute disassembly is still worth something

`cac9e27a` is a different compilation and cannot *settle* the question. It is
reported because it is the nearest surviving relative built from the same
source file by the same compiler and flags, and because the *shape* it reveals —
pointer parked in a callee-saved register before the m5op, returned from there —
is a stable consequence of `alloc_bytes`'s structure rather than a scheduling
accident. `cxl_join_bench_w7.gem5` (`9dadce49`, built 2026-09-01 02:23, ~22 h
before r5 launched) shows the same shape and is **SAFE at all 7 of its sites**.

### 3.4 `FUSED_KNEE`: clean by construction, which is stronger than clean by schedule

`fused.c`'s declaration wrapper has, in **every revision that has ever
existed**, declared the clobber:

```c
static inline void gem5_set_streaming(void *addr, long size) {
    __asm__ volatile(".byte 0x0f, 0x04, 0x55, 0x00"
                     : : "D"((long)addr), "S"(size) : "rax");
}
```

Verified at `800b7f920e`, `71441822dc`, `d00caefd14` (all 2026-08-29) and
`f3c2c84949` (2026-09-04). `FUSED_KNEE` ran 2026-08-29 against `d00caefd14`.

This matters more than a disassembly would. **A declared clobber is
schedule-independent**: the compiler is contractually forbidden from keeping a
live value in `%rax` across the asm, at any optimization level, in any
surrounding code. So the fact that `FUSED_KNEE`'s exact binary no longer exists
(§4) does **not** leave its verdict open. The defect requires an *undeclared*
clobber, and this wrapper was never undeclared.

The same holds for `fig:recovery`, all three panels, which is backed by the same
harness.

Note the scope precisely: in the `FUSED_KNEE`-era `fused.c`, `set_streaming` was
the **only** m5op in the file. `gem5_reset_stats` was added later, by
`f3c2c84949` (2026-09-04), *without* an `"rax"` declaration — so the current
`fused` binary carries two undeclared sites. Both are SAFE by schedule in the
built binary, but that is luck, and §7 fixes them.

### 3.5 `FS_COMPLETE_JOIN` r6b–r6e: the exact binaries were recovered

The FS campaign's guest binary lives inside the disk image, and both images
survive. Each run's `manifest.txt` records `image_sha256` and
`guest_bench_sha256`; both were verified before anything was read out of them:

| | recorded `image_sha256` | recomputed | recorded `guest_bench_sha256` | extracted binary |
|---|---|---|---|---|
| r6b | `c4d3e2e1…` | **match** | `9bd3d1e3…` | **match** |
| r6e | `a66930ab…` | **match** | `db41495d…` | **match** |

The binaries were extracted read-only with `debugfs` (partition offset
1,048,576; the images were not mounted and not modified) and audited. **All 14
m5op sites are SAFE in each.** These are the actual bytes that ran, so this is
the strongest class of evidence available for any campaign in this audit.

As the brief anticipated, the declaration itself goes through real `mprotect`
here rather than an m5op, so the declaration path was never exposed. The point
of checking was the stats/exit ops, and they are clean too.

---

## 4. Binaries that no longer exist

Three campaigns cannot be audited by disassembling what they ran, because what
they ran is gone. This is `F13` — the `BUILD_PROVENANCE.md` defect — recurring
on the **tenant** side rather than the simulator side.

| campaign | binary that ran | status |
|---|---|---|
| **`COMPLETE_JOIN` / r5** | `cxl_join_bench.gem5` `401373ce94799ec6b00a814f310243e902f0118197cca2999506a51dbf25c864` | **gone.** Overwritten in place; the current file at that path is `cac9e27a…` |
| **`FUSED_KNEE`** | `gem5/testcase/dutyfree/fused`, hash **never recorded** | **gone.** The on-disk `fused` contains the post-`f3c2c84949` warmup string and so postdates the campaign |
| **`H2H_REALJOIN` / r3** | unrecorded | **gone.** Run directories deleted; only the 66 directory *names* survive, in `/tmp/rj3_dirs.txt` |

The r5 loss is documented rather than inferred: all 45 r5 launch logs in
`/tmp/r5` record `R5_JOIN 401373ce…`, and an exhaustive search of every regular
file on this host between 2.5 MB and 2.9 MB found no file with that hash. The
launcher recorded the hash — which is why we know what is missing — but nothing
preserved the bytes.

**Nothing was rebuilt to stand in for a lost binary.** A rebuild is a different
compilation and would not answer the question; where the exact bytes are gone,
this record says so and rests on §3.2 and §5 instead.

`run_complete_join.sh` deserves credit here: because it wrote
`R5_GEM5`/`R5_JOIN`/`R5_VICTIM` hashes into every run log, r5's tenant identity
is *known* to be lost rather than merely unknown. `run_fused_knee.sh` records no
hashes at all, which is why `FUSED_KNEE` would have been unanswerable had its
source not carried the declaration.

---

## 5. The counter cross-checks, and what they can and cannot exclude

The disassembly and the run-log evidence are the direct evidence. The counters
are the cross-check a reviewer can inspect without a disassembler.

### 5.1 The arithmetic for r5

r5 declares the whole 8 MiB fact table: 2,048 pages, **131,072 lines** of 64 B.
`--reps 1`, so one pass.

| arm | n | `hnf_streaming_bypasses` | as % of the 131,072 declared lines |
|---|--:|--:|--:|
| `r5_h2` | 3 | 129,545 / 129,613 / 129,571 | **98.83% / 98.89% / 98.85%** |
| `r5_wb`, `r5_qui`, `r5_wm01…wm20` | 42 | **0** in every cell | — |

Two independent instruments agree: the tenant's own `probe_accesses` (131,072)
and the simulator's bypass counter (129,545) differ by 1.2%, a residue
consistent with the un-bypassable clean evictions this project has already
characterised.

**The counterfactual is not close.** A mismark to a binary image is ~16 pages =
1,024 lines. Reaching 129,545 from 1,024 lines would need 126.5 LLC fills per
line, for a 64 KiB region that fits comfortably in L1.

And in r5's case the mismark could not even have marked the image:
`cxl_join_bench.gem5` is `Type: EXEC`, loaded at `0x400000`, **not a PIE**. The
`mmap_probe` failure marked the tenant's own text because that binary *is* a PIE
loaded at base 0. `pseudo_inst::setstreaming` (`sim/pseudo_inst.cc:641-652`)
*allocates* absent pages before marking them, so `addr=0` in a non-PIE would
have created 16 fresh anonymous pages at VA 0 that the program never touches —
yielding **0** bypasses, not 129,545.

### 5.2 The strongest counter argument: it scales with the declared range

Across the `H1BW` campaigns the bypass count tracks the *declared* size:

| cells | declared (two-pass) lines | `h2` bypasses | ratio |
|---|--:|--:|--:|
| 4-core (`total_bytes` 32 MiB) | 1,048,576 | 419,718 – 427,408 | 40.0 – 40.8% |
| 8-core (`total_bytes` 64 MiB) | 2,097,152 | 857,334 – 862,619 | 40.9 – 41.1% |
| 1-slice, post-`isStreaming`-fix | 1,048,576 | **853,853** | 81.4% |
| every `wb` cell (declares nothing) | — | **0** | — |

Doubling the declared bytes doubles the count (8c ≈ 2.01× 4c) while the
*fraction* stays pinned near 40%. **A mismark to the binary's own image is a
fixed ~16-page region independent of `--fact-bytes`, and so cannot produce a
count proportional to the declared size.** This is the cross-check that most
sharply separates "something was marked" from "the right thing was marked",
because it tests the *derivative*, not the level.

Single-core (`H1BW_SINGLECORE`) adds a realized-range check of a different
shape: `llc_fills_total_over_stream_lines` is **10.98** in every `wb` cell and
**1.09–1.10** in every `h2`/`pfoff` cell — a 10× suppression measured *per
declared stream line*.

### 5.3 Correcting an attribution the brief inherited

The brief, following the handback's §6.4, attributes **853,853** bypasses to
r5's `h2` arm. **That figure is not r5's.** It belongs to
`h1bw_mc_h2_4c_l3x1_bwdef_20260904fix`, the post-`isStreaming`-fix single-slice
cell of `H1BW_SLICE_BRACKET` (`H2_BYPASS_FIX_OUTCOME_2026-09-03.md` §184).
r5's `h2` arm recorded **129,545 / 129,613 / 129,571**.

This does not weaken the conclusion — it strengthens the method. 129,545 against
a *known* denominator of 131,072 is a far tighter constraint than 853,853
against no stated denominator. But the misattribution should not propagate, and
the handback's §6.4 sentence should be read as superseded on this point.

### 5.4 r3, where the counters are all there is

r3's binary is gone and unrecorded, so no disassembly is possible. What the
archive shows: of 66 cells, the **60** with `declared_streaming=false` record
**exactly 0** bypasses, and the **6** with `declared_streaming=true` record
1,274,276–1,277,320 (`r3_h2`) and 10,575,035–10,577,704 (`r3_fh2`). The
declaration flag and the counter agree perfectly on which cells marked
something, at magnitudes three to four orders above a 1,024-line image.

### 5.5 What these cross-checks cannot exclude

Stated plainly, because this project has been burned by treating a nonzero
counter as proof:

- **A nonzero count proves something was marked, never that the right thing
  was.** Every argument above is about *magnitude and scaling*, not identity.
- **A partial mismark is not excluded by the level alone.** If a declaration
  had covered, say, 90% of the intended range, the count would fall inside the
  spread seen across seeds. For r5 this is closed by §3.2 — the run prints
  `fact_base` and `fact_end` and they bracket exactly 8 MiB — but *for the
  H1BW cells the counters alone would not close it*, and there the disassembly
  of the exact binary does.
- **An offset mismark of the same size is not excluded by counters at all.** A
  correctly-sized range at the wrong base would produce a similar count. Only
  the disassembly (§3.1) and the printed `fact_base` (§3.2) exclude it.
- **The ~40% engagement fraction is not evidence of correct marking**; it is a
  property of the workload's reuse and the HNF's admission policy. Only its
  *proportionality to the declared size* (§5.2) carries weight here.
- **r3 rests on counters alone**, and by the above that is enough to say a
  large, correctly-scaled range was marked, and **not** enough to exclude an
  offset or partial mismark. r3 is therefore recorded as
  `CLEAN on counters, INDETERMINATE on disassembly`, not as CLEAN.

---

## 6. The one real defect: the flush-behind oracle, in a path nothing runs

`join_range_flushbehind` — reached only by `--policy fbo` — is genuinely
broken by this bug, in all three binaries that contain it
(`cxl_join_bench.gem5` `0x40ced1`, `.gem5wbrk` `0x40cf11`, `.gem5fs` `0x40d7b1`):

```
  40cec5:	49 8d bb 10 f0 ff ff 	lea    -0xff0(%r11),%rdi   ; addr
  40cecc:	be 00 10 00 00       	mov    $0x1000,%esi        ; size
  40ced1:	0f 04 57 00          	; M5OP_FLUSH_RANGE -> gem5 sets Rax = 0
  40ced5:	49 83 c3 10          	add    $0x10,%r11
  40cedd:	48 39 e8             	cmp    %rbp,%rax           ; <-- READS %rax
  40cee0:	0f 82 4b ff ff ff    	jb     40ce31              ; loop back
```

`%rax` is the **loop induction variable**, compared against the bound in `%rbp`.
The m5op zeroes it on every iteration, so the loop cannot terminate.

This sharpens `BUILD_PROVENANCE.md`'s standing note that the oracle opcode is
compiled in but sits behind a `policy == "fbo"` branch no cell takes. That note
argued the path was inert. It is stronger than inert: **had any cell taken it,
that cell would have hung rather than produced a wrong number.** A campaign
cannot have silently used this path and gone unnoticed. No committed campaign
passes `--policy fbo`; `FB_ORACLE_PREREG_2026-09-03.md` registers the arm and it
has not run.

---

## 7. The fix, and its verification

Declare `%rax` as an output. A register cannot be both an input constraint and
a clobber, so an output operand is the minimal correct form:

```c
static inline void gem5_reset_stats(void) {
    unsigned long m5_rax;
    __asm__ volatile(".byte 0x0f, 0x04, 0x40, 0x00"
                     : "=a"(m5_rax) : "D"(0ULL), "S"(0ULL));
    (void)m5_rax;
}
```

**Guest-side only. `gem5.opt` was not rebuilt and `gem5/src/` was not touched.**

**What was deliberately *not* changed: each wrapper's existing `"memory"`
clobber decision.** Adding a memory barrier where one was absent is a strictly
stronger ordering constraint that changes codegen for reasons unrelated to this
defect, and several of these harnesses back committed campaigns. Wrappers that
already declared `: "rax"` were converted to the output form, which is exactly
equivalent to the compiler — both mark `%rax` as written — and so cannot move a
generated instruction. Whether `fused.c`'s `set_streaming` *should* also carry
`"memory"`, as `cxl_join_bench.cpp`'s does, is a real question and is handed
back rather than decided here.

### 7.1 Coverage

31 wrappers across 14 files:

| tree | files | wrappers | committed here? |
|---|--:|--:|---|
| `gem5/testcase/dutyfree/`, `gem5/testcase/dirtax/` | 11 | 19 | **yes** — tree was clean |
| `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp` | 1 | 6 | **no** — see §7.3 |
| `benchmarks/e2e/duckdb_mmap_probe/src/mmap_probe.cpp` | 1 | 4 | **no** — see §7.3 |
| `benchmarks/e2e/hash_join/src/streaming_h3_dirty_owner.cpp` | 1 | 2 | **no** — see §7.3 |

### 7.2 Verification

Every fixed source was compiled **to a scratch directory** and audited. **No
campaign binary was overwritten**, so the `gem5.opt.pre-npot-guard.cb290444`
preservation convention was not invoked — the bytes were never at risk. This
matters concretely: `gem5/testcase/dutyfree/victim` is `1f6214b8…`, which is
exactly the `R5_VICTIM` hash in r5's own run logs, so that file is itself a
binary a committed campaign depends on.

| rebuilt (scratch) | sites | result |
|---|--:|---|
| `victim`, `npot_probe`, `fused`, `aggressor`, `aggressor_finite`, `aggressor_lowBW`, `aggressor_finite_lowBW`, `h1bw_stream`, `streaming_pf_probe` | 18 | **all SAFE** |
| `cxl_join_bench.gem5` | 14 | **all SAFE** (was 13 SAFE + 1 UNSAFE) |
| `streaming_h3_dirty_owner.gem5` | 2 | **all SAFE** |
| `mmap_probe.gem5` | 4 | **all SAFE** (was 3 SAFE + 1 UNSAFE) |

The two previously-UNSAFE sites are both repaired, and the repair is visible as
a single ModRM byte. In `mmap_probe`, at the identical address in the identical
instruction slot:

```
before:  5270:	48 89 05 49 60 00 00 	mov %rax,0x6049(%rip)  # g_probe+0x20   <- 0
after:   5270:	48 89 2d 49 60 00 00 	mov %rbp,0x6049(%rip)  # g_probe+0x20   <- p
```

Told that `%rax` is written, the compiler simply uses the surviving `%rbp` copy
it already had. In `cxl_join_bench`'s flush-behind loop the induction variable
moves out of `%rax` to `%r15` and the loop terminates.

### 7.3 Three files edited but not committed, and why

`cxl_join_bench.cpp` is modified in the working tree by another worker
(**+1,086 / −27** lines), and `duckdb_mmap_probe/` and
`streaming_h3_dirty_owner.cpp` are **untracked**. Committing any of them —
even with `git commit --only` and an explicit pathspec — would sweep another
worker's in-flight, unreviewed work into the history under this record's commit
message. That is a worse outcome than a deferred fix.

The wrapper edits **are applied in the working tree** so the fix is in place for
whoever owns those files, and the diffs are confined to the wrapper blocks: 6, 4
and 2 hunks respectively, no other line touched. Pre-edit copies are preserved
at `/tmp/m5audit/*.before`. Committing them is handed back to their owners.

**Consequence to declare before any future arm:** applying this fix changes
`mmap_probe.gem5`, so `DUCKDB_MMAP_SE_H2`'s registered tenant pin
`2139aa85…` moves and an apparatus deviation must be declared, exactly as the
handback's §6.5 said. That binary has **not** been rebuilt here; the pin is
still intact on disk.

---

## 8. Handed back, not applied

### 8.1 Proposed ledger entry — `F19`

`F19` is the next free number. This is proposed as a **new class**, not an
instance of `F18`.

> **`F19` — an inline-asm statement that under-declares what the instruction
> writes.** gem5's magic instruction writes `%rax` unconditionally
> (`two_byte_opcodes.isa:159-166`), and `pseudo_inst.hh:140` zeroes it for a
> void op, but the m5op wrappers in this tree declared only `"memory"`. The
> compiler therefore believed `%rax` survived, and **whether that belief cost
> anything depended on the schedule the optimiser happened to pick** — so the
> same source is safe in one binary and wrong in the next, and reading the
> source settles nothing. Realized in `mmap_probe.gem5`, where `SET_STREAMING`
> marked the tenant's own image at VA 0 instead of the probe
> (`DUCKDB_MMAP_SE_H2_HANDBACK_2026-09-04.md` §6).
> **Audited across every campaign** in
> `M5OP_RAX_CLOBBER_AUDIT_2026-09-04.md`: no campaign mismarked its declared
> range; one unexecuted path (the `--policy fbo` flush-behind oracle) was
> genuinely broken and is fixed. **Fixed** by declaring `%rax` as an output
> operand in all 31 wrappers across 14 files; 19 committed, 12 applied and
> handed back to the files' owners.
> *Distinct from `F9`* (requested-vs-realized): nothing here is recorded as
> configuration. *Distinct from `F18`* and from `F13`, though it **compounds**
> `F13`: r5's, `FUSED_KNEE`'s and r3's tenant binaries no longer exist, so two
> of the three had to be settled by in-band run evidence and by a
> schedule-independent source guarantee rather than by disassembly.
> **Prevention:** a declared clobber is schedule-independent and is therefore
> the only durable fix; and a harness runner that hashes the *tenant* binary,
> as `run_complete_join.sh` does and `run_fused_knee.sh` does not, is what makes
> the difference between "the binary is lost" and "we cannot even say what was
> lost".

### 8.2 Proposed `INDEX.md` row

> | `M5OP_RAX_CLOBBER_AUDIT_2026-09-04.md` | **`AUDIT`** — closes the question
> `DUCKDB_MMAP_SE_H2_HANDBACK_2026-09-04.md` §6.4 handed back. Every m5op call
> site in every binary a committed campaign used, audited for a live `%rax`
> across the instruction (`audit_m5op_rax.py`, committed). **r5 / `COMPLETE_JOIN`
> — the headline `fig:frontier`(a) — is CLEAN**, on in-band evidence from the
> run itself: all 42 join cells print `fact_base 0x7ffff77ff000` / `fact_end
> 0x7ffff7fff000`, exactly the declared 8 MiB, and `h2` records 129,545 bypasses
> = **98.8%** of that range's 131,072 lines against **0** in all 42 non-streaming
> cells. `FUSED_KNEE` is clean **by construction** — `fused.c` has declared
> `: "rax"` in every revision that ever existed, which is schedule-independent
> and so survives the loss of its binary. `H1BW_*` clean on the exact binaries;
> **`FS_COMPLETE_JOIN` r6b/r6e clean on binaries recovered from the committed
> disk images and hash-matched to their manifests**. `H2H_REALJOIN`/r3 is clean
> on counters but **INDETERMINATE on disassembly** — its binary is gone and was
> never hashed. **No published claim is in doubt.** One genuine defect found, in
> the `--policy fbo` flush-behind oracle, which no cell executes and which would
> have **hung** rather than produced a wrong number. Corrects the handback's
> §6.4 attribution of **853,853** bypasses to r5: that figure is
> `H1BW_SLICE_BRACKET`'s, not r5's. **`F19` proposed**; three files' wrapper
> fixes applied but handed back uncommitted, being other workers' in-flight
> paths |

Also worth a line: `H2H_REALJOIN_CLOSED_2026-09-04.md`'s "no paper claim
depends on this campaign" was re-checked here and holds — searching
`/home/domin/STREAMING_Paper/` for r3's characteristic magnitudes and for
`rj3`/`realjoin` returned nothing. The brief's premise that r3 feeds "the CAT
calibration the paper still cites" is **not supported** by anything found in
either tree.

---

## 9. Which published claims are in doubt

**None.**

Stated without softening, and without overclaiming:

- **`fig:frontier`(a) and every r5 number in `Sec7_Evaluation.tex`** — 22.6%
  recovery, +5.35% vs unprotected, +9.97% against the cheapest sufficient mask,
  +8.42% interpolated, and the abstract's headline — rest on a campaign whose
  declared range is confirmed correct by the run's own output (§3.2) and whose
  counters match the declared range's line count to 1.2% (§5.1). Not in doubt.
- **`fig:recovery`, all three panels** — rest on a harness whose declaration
  wrapper has always been correctly declared (§3.4). Not in doubt, and not
  contingent on the missing binary.
- **`tab:h1bw` and the §7 MSHR sweep**, and the multi-reader bandwidth figures
  — rest on binaries that still exist, are hash-matched to their archives, and
  are clean at every site. Not in doubt.
- **The full-system P1 claims** — rest on binaries recovered from their own
  committed disk images and hash-matched to their manifests. Not in doubt.

The one thing that *is* damaged is **provenance, not correctness**: three
tenant binaries a committed campaign depended on no longer exist (§4). For r5
that costs the ability to settle the question by disassembly, which is why §3.2
carries the weight; for `FUSED_KNEE` it costs nothing, because the source
guarantee is stronger than a disassembly would have been; for r3 it leaves a
genuine `INDETERMINATE` that counters alone cannot close (§5.5). That is an
`F13`/`F19` provenance debt, and it is stated here rather than papered over.

---

## 10. Provenance and hygiene

- **No arm ran, nothing was launched, `gem5.opt` was not rebuilt, and
  `gem5/src/` was not modified.** Nothing was written under `gem5/logs/` or
  `experiments/asplos/data/`.
- **No campaign binary was overwritten.** Every verification build went to
  `/tmp/m5audit/build/`. The r5 victim `1f6214b8…`, `cxl_join_bench.gem5`
  `cac9e27a…`, `.gem5wbrk` `2b9d6732…`, `.gem5fs` `6216571a…`, `fused`
  `7937d3b8…` and `mmap_probe.gem5` `2139aa85…` are all byte-identical to what
  they were before this pass.
- **The FS disk images were read, never mounted and never written.** Extraction
  used `debugfs` at the partition offset; both images re-hash to the values
  their run manifests record.
- **Host `c4` was not touched**, and no process was signalled. Work was done on
  `mos181`.
- **`A1_PROVENANCE_LEDGER_2026-08-28.md`, `INDEX.md` and
  `/home/domin/STREAMING_Paper/` were not edited.** The paper tree was read
  only, to check r3's dependency.
- **`/tmp/r5` is load-bearing for §3.2 and is not committed.** It is 45 launch
  logs in `/tmp`, which is exactly the fragility that lost r5's binary in the
  first place. Preserving them into the repository is the obvious follow-up and
  is **not** done here, because they are another campaign's artifacts and this
  record is not their owner. Flagged rather than silently relied on.
