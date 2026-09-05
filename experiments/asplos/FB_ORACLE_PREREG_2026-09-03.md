# H2 vs a flush-behind ORACLE — pre-registration

Registered 2026-09-03, before the first arm runs. Machine, geometry, arms,
metrics, predictions and the void condition are fixed here.

## The cell this fills

`Sec5_Evaluation.tex` states, in our own voice, that *"the paper's competitive
claim must be made against flush-behind, not against CAT"* -- and the appendix's
"Platform split" concedes that *"the strongest shipping alternative therefore
has no controlled comparison against the label on either platform."* The paper
names its decisive comparison and admits it is missing. A reviewer only has to
quote us.

The cell is empty for a structural reason, not an oversight:

| | flush-behind | STREAMING H2 |
|---|---|---|
| silicon | measured (45.7% recovery / 5.9% cost, capped) | does not exist |
| gem5 | `CLFLUSH` is a **silent no-op** under Ruby/CHI | measured |

r6e does not fill it: it compares H2 against an *unprotected* neighbour, not
against flush-behind.

## Why an oracle, and what it is

Implementing a real `CLFLUSH` in CHI means new SLICC transitions across many
states in a ~4000-line protocol; a wrong transition deadlocks or asserts, which
is how the r6 generation died. That is the right long-term fix and the wrong
critical path.

Instead: `M5OP_FLUSH_RANGE` (0x57) -> `pseudo_inst::flushrange`. It sweeps
`SimObject::getSimObjectList()` for `CacheMemory` objects whose name contains
`.hnf`, translates VA->PA through the SE page table, and functionally
deallocates every present line in the range. **Zero latency, zero fabric
traffic, no protocol transition.** The guest side (`--policy fbo`) issues one
m5op per 4 KiB of trailing data instead of one `clflushopt` per 64 B line, so
the software cost is ~1 instruction per 64 lines rather than one per line.

This is an **UPPER BOUND on flush-behind, not a model of it.** Every
idealisation errs *against* our own thesis, which is the direction an oracle
must err in:

- no instruction cost for the flush itself
- no latency, no queueing, no fabric occupancy
- no `sfence` serialisation
- perfect timing: the line leaves exactly when asked

Two scope decisions, stated so they cannot be discovered later:

1. **LLC only.** Private L1/L2 copies are untouched. Real `CLFLUSH` invalidates
   those too, but H2 governs only the shared LLC, so invalidating private
   copies would give the oracle *more reach than the mechanism under test* --
   and would risk tearing down a line with an in-flight transaction.
2. **No AbstractController or SLICC change.** A public `getSimObjectList()`
   accessor on `SimObject` is the only simulator-core addition, so there is no
   new protocol surface and no deadlock risk.

Built into **`build_Intel_8592_FBO/gem5.opt`**, a separate variant, so
`build_Intel_8592/gem5.opt` is never relinked while r6e's arms execute it.

## Machine — r5's, exactly

`--num-l3caches=1 --l3_size=7680KiB --l3_assoc=20`, `--cpu-type=O3CPU
--num-cpus=2 --cpu-clock=1.9GHz`, `--l1d_size=48KiB --l1d_assoc=12
--l2_size=2MiB --l2_assoc=16`, `--mem-type=SimpleMemory --dram-latency=98ns
--cxl-latency=203ns`, and `HNF_RP=lru HNF_SF_FINITE=0 HNF_SF_SETS=4096
HNF_SF_WAYS=16 HNF_H3=0 HNF_DMT=0 HNF_FWD_UNIQUE=0 SEQ_OUT=1024
RUBY_RANDOMIZATION=1`.

Every one of those is pinned because r6b silently took `CHI_config_8592.py`
defaults (TreePLRU at 20 ways, DMT on, forward-unique on) and was therefore
**not the same machine as any other number in the paper**.

## Geometry — r5's, exactly

Tenant `--mode single --fact-bytes 8388608 --hot-bytes 4194304 --reps 1
--warmups 0 --hit-rate 0.5`; victim `testcase/dutyfree/victim 2650 12000000`
(2650 KiB Sattolo chase, `int` elements, `srand(42)`); `qui` pairs the victim
with `dummy`. Three seeds. This is r5's launch verbatim, so `qui`/`wb`/`h2`
must reproduce r5 within noise -- which is itself a check on the new binary.

Flush distance for `fbo`: **65536 B**, matching silicon's best-performing
`fb64k` arm.

## Arms

`qui` / `wb` / `h2` / `fbo`, three seeds each, 12 runs.

## Metrics

Victim cyc/load (recovery R) and tenant tuples/s, both as r5 measured them.
`R(x) = (wb - x) / (wb - qui)`.

## Registered predictions

- **P-O1 (the oracle works).** `fbo` must show a materially lower HNF
  occupancy/insertion count than `wb`. If it does not, the m5op is a silent
  no-op and the campaign is **VOID** -- this is the `CLFLUSH` failure repeated
  one layer up, and it is the first thing to check, before any ratio is read.
- **P-O2 (reproduction).** `qui`/`wb`/`h2` reproduce r5 within noise. A
  deviation means the new binary or the pinned config differs from r5's.
- **P-O3 (the comparison).** `R(h2) > R(fbo)`. Directional, with the same
  evidential bar as r6e's P3: the gap must exceed the cross-seed spread.
- **P-O4 (cost).** Tenant tuples/s under `h2` >= under `fbo`, to within the
  resolvable spread.

## Falsification, stated in advance

If **`R(fbo) >= R(h2)`** at comparable tenant cost, then an idealised
flush-behind matches or beats the declaration on this workload, and the paper
must say so before submission. That is a publishable negative and it is the
reason this experiment is worth running: it is the one measurement that can
still change a reviewer's mind in either direction.

## How the result may and may not be used

- Label every `fbo` number an **oracle**. Never call it flush-behind.
- **Never plot it on the same axes as the silicon CAT/flush-behind table.**
  Different platform, different LLC (7.5 MiB vs 320 MiB per socket), different
  victim tax (r5 ~6 cyc/load vs silicon ~94).
- The silicon result stands on its own and is already stronger than expected:
  flush-behind's recovery **peaks at 45.7% and falls to 31.7%** as the flush
  distance grows, because the line has already displaced a neighbour before the
  flush lands. The oracle tests whether removing flush-behind's *cost* lifts
  that ceiling. Our expectation is that it does not, because the ceiling is
  set by retroactivity, not by cost -- but that expectation is what is under
  test, not an assumption.

## Context: what r6e established (2026-09-03)

Seven of nine arms, full system, declaration via real `mprotect`:
`qui` 97.443, `wb` 115.224 (half-range 0.157), `h2` 97.102 (half-range 0.053)
cyc/load. Victim tax +18.25%; **R(h2) = ~100%** with a gap of 18.12 cyc/load
against a 0.157 spread (115x); tenant cost -0.01%, i.e. none measurable; HNF
bypasses 524,076 and 524,211 of 524,288 stream lines with all four controls at
exactly 0. So H2's recovery on a properly exposed victim is near-total. The
open question is whether an idealised flush-behind can also reach it.

---

## Amendment 1 — 2026-09-04, before any arm of this campaign has run

Registered geometry change, made **while this campaign has produced no number
of any kind**: no `fbo`, `qui`, `wb` or `h2` cell exists under `gem5/logs/`, and
`data/gem5/` carries no file for it. (The `/tmp/fbo_validate` pair of
2026-09-03 is this registration's own `P-O1` plumbing check at the wrong
geometry — one run per arm, `--fact-bytes 2097152 --hot-bytes 1048576 --reps 2`,
no victim process — and is not a campaign cell; see `F16`.) Amending a
registration before its data exists is what pre-registration is for. Superseded
wording is quoted rather than deleted, per `A6.19`.

### What changes

**§"Machine — r5's, exactly" as registered:**

> `--num-l3caches=1 --l3_size=7680KiB --l3_assoc=20`

**as amended:**

> `--num-l3caches=1 --l3_size=5MiB --l3_assoc=20`

**§"How the result may and may not be used", third bullet, as registered:**

> Different platform, different LLC (7.5 MiB vs 320 MiB per socket), different
> victim tax (r5 ~6 cyc/load vs silicon ~94).

**as amended:** "different LLC (**5.0 MiB** vs 320 MiB per socket)".

---

## Amendment 2 — 2026-09-04, still before any arm has run: as registered, the `fbo` arm would have hung, and three of the four predictions were unreachable

Appended by the ledger/index pass, not by this campaign's worker, against
`M5OP_RAX_CLOBBER_AUDIT_2026-09-04.md` (commit `964fbf1`). **Appended, not
applied**: this is a sealed registration, so nothing above this line is edited
and the superseded reading is quoted, per `A6.19`. Every figure below was
re-derived in this pass rather than accepted from the handback that raised it.

**The defect.** gem5 decodes the magic instruction with a body ending
`Rax = result;` — written **unconditionally**
(`arch/x86/isa/decoder/two_byte_opcodes.isa:163`) — and `pseudo_inst.hh:140`
sets `result = 0` before dispatch, so **every void m5op leaves `%rax == 0`**.
The guest wrappers in this tree declared only `"memory"`, so the compiler
believed `%rax` survived. This is registered as **`F19`** in
`A1_PROVENANCE_LEDGER_2026-08-28.md`.

**What that does to this registration specifically.** In
`join_range_flushbehind` — the function `--policy fbo` exists to reach — the
compiler placed the **loop induction variable in `%rax`**, compared against its
bound in `%rbp`, across the `FLUSH_RANGE` m5op. Re-verified here by running the
committed instrument `audit_m5op_rax.py` against all three binaries that contain
the function:

| binary | m5op site | reads `%rax` at | verdict |
|---|---|---|---|
| `cxl_join_bench.gem5` | `0x40ced1` | `0x40cedd`, `cmp %rbp,%rax` | **UNSAFE** |
| `cxl_join_bench.gem5wbrk` | `0x40cf11` | `0x40cf1d`, `cmp %rbp,%rax` | **UNSAFE** |
| `cxl_join_bench.gem5fs` | `0x40d7b1` | `0x40d7bd`, `cmp %rbp,%rax` | **UNSAFE** |

The m5op zeroes the induction variable on every iteration, so **the loop cannot
terminate**. This is the only UNSAFE site in any of the three binaries; every
other site in each is SAFE.

**The consequence for this document, stated plainly: it could not have run as
written.** Not "would have produced a suspect number" — the primary arm would
have **hung**. And the campaign's predictions do not degrade gracefully around
that, because three of the four are defined on `fbo` cells:

- **`P-O1`** ("the oracle works") is measured *on* `fbo`. Unreachable.
- **`P-O3`** (`R(h2) > R(fbo)`) needs an `R(fbo)`. Unreachable.
- **`P-O4`** (tenant tuples/s under `h2` ≥ under `fbo`) needs an `fbo` cell.
  Unreachable.

Only `P-O2`, the `qui`/`wb`/`h2` reproduction of r5 that Amendment 1 above
strengthened, is unaffected — it does not touch the `fbo` path.

So the §"12 runs" design — `qui`/`wb`/`h2`/`fbo` at three seeds — would have
delivered **9 completed cells and 3 hangs**, and the registered headline
comparison is the part that would not have arrived.

**The reading this replaces, quoted rather than deleted.** The `M5OP_FLUSH_RANGE`
section above presents the mechanism as settled and costed:

> The guest side (`--policy fbo`) issues one m5op per 4 KiB of trailing data
> instead of one `clflushopt` per 64 B line, so the software cost is
> ~1 instruction per 64 lines rather than one per line.

That arithmetic is correct and is **not** what is amended. What is amended is the
unstated premise that the loop issuing those m5ops terminates. It does not, in
any binary currently on disk.

**Why this is good news rather than bad, and it is worth being explicit.** The
failure mode is a **hang, not a wrong number**. This registration was never run,
so nothing is retracted — but the same code path is present in three committed
binaries, and had any campaign taken it, the operator would have seen a
simulation that never finished rather than a plausible flush-behind result that
survived reading. **`BUILD_PROVENANCE.md`'s standing note that this opcode is
"compiled in but inert" is therefore superseded in the campaign's favour: it is
stronger than inert.** A silent wrong answer is the outcome this project has been
burned by repeatedly; this defect could not produce one.

**Launch precondition, registered here rather than left to be discovered.**
Before any `fbo` cell is launched:

1. The guest-side fix must be **built and pinned**. The correct form is to
   declare `%rax` as an output operand — a register cannot be both an input
   constraint and a clobber — and with that declared, the compiler moves the
   induction variable out of `%rax` and the loop terminates. **The fix is applied
   in the working tree but is *not committed*, because `cxl_join_bench.cpp` is
   another worker's in-flight path**; so at the time of writing, no committed
   binary can run this arm.
2. The rebuilt tenant's hash must be recorded in this document and in the run
   logs, per `F13`/`F19`. This campaign's own audit trail is what makes the
   difference between "the binary is lost" and "we cannot even say what was
   lost", and `run_complete_join.sh` is the model to copy — it writes the tenant
   hash into every run log.
3. `P-O1`'s threshold should be re-read once a *terminating* `fbo` cell exists.
   It was set against a mechanism nobody had observed complete.

**Nothing else in this registration moves.** The geometry as amended in
Amendment 1, the UPPER-BOUND framing, the idealisation list and `P-O2` all stand
exactly as written.

### Why — and why it costs this registration nothing

`--l3_size=7680KiB --l3_assoc=20` at 64 B lines gives
`(7864320 / 20) / 64 = 6144` sets. `CacheMemory::init()` takes
`floorLog2(6144) = 12` and `addressToCacheSet()` selects 12 index bits, so
4,096 of 6,144 sets are reachable and the HNF realizes
`4096 x 20 x 64 = 5,242,880 B = 5.00 MiB`, 66.7% of what was asked for. Record:
`NONPOW2_SETS_MEASURED_2026-09-04.md`; `[F9.4]` class, proposed as `F18`.

**The amendment changes the description of the machine and not the machine.**
Measured, on the campaign binary `cb290444` unmodified: `--l3_size=7680KiB
--l3_assoc=20` and `--l3_size=5MiB --l3_assoc=20` are **bit-identical on all
2,014 simulated quantities** — same HNF demand hits (166,595), same misses
(128,498), same `simTicks` (26,881,767,046), same per-way allocation histogram;
5 differing lines, all five host-side. So:

- **`P-O2` is preserved exactly, and strengthened.** Its requirement is that
  `qui`/`wb`/`h2` reproduce r5 within noise. r5's realized machine is
  5,242,880 B, so after this amendment the registration names the geometry r5
  actually ran. Before it, `P-O2` asked for reproduction of r5 on a machine
  described as 1.5× r5's realized size — a description that would have made a
  successful reproduction look like a coincidence.
- **No other registered quantity moves.** `P-O1`, `P-O3`, `P-O4`, the
  falsification condition, the arms, the seeds, the flush distance (65,536 B),
  every pin in §"Machine", and the r6e context figures are untouched. The
  geometry section's remaining lines — `--cpu-type=O3CPU --num-cpus=2
  --cpu-clock=1.9GHz`, `--l1d_size=48KiB --l1d_assoc=12`, `--l2_size=2MiB
  --l2_assoc=16`, and the tenant/victim options — are all confirmed clean:
  48 KiB/12 = 64 sets, 32 KiB/8 = 64, 2 MiB/16 = 2048, every one a power of two.

### Do not "fix" this by respelling 7,864,320

Added to §"Do not". No `--l3_size` value gives 7.5 MiB at 20 ways: the
attainable capacities are `2^k x 20 x 64`, i.e. 5 MiB then 10 MiB. A genuine
7.50 MiB needs `--l3_size=7680KiB --l3_assoc=15` (8,192 sets, exact), which
breaks this campaign's requirement to be r5's machine and would void `P-O2`.
**5 MiB at 20 ways is the correct amendment precisely because it is r5's
machine.**

### Recurrence

From `gem5.opt` `d4e798601e7205c526868c8bdefbb75c4dde4f05f2b6b6a54a802df0b9c74a83`
onward, `CacheMemory::init()` warns with the realized capacity whenever a set
count is not a power of two, so this cannot recur silently. The guard is
warning-only and proved inert on power-of-two geometries (four cells, pre and
post, byte-identical on every simulated quantity). Whichever binary runs this
campaign, its console log should contain **no** such warning; if it does, the
geometry is not the amended one.
