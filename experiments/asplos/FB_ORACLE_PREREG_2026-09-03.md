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
