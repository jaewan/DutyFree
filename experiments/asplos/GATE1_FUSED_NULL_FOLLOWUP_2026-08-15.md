# #22 follow-up — both candidates tested with a real fix, the null holds and is now well-verified

Written 2026-08-15, continuing `GATE1_FUSED_NULL_OUTCOME.md` (2026-08-13).
That document identified two candidate causes for the gem5 fused hash-join
null and recommended against spending further time without being asked.
The lead asked. This is the result.

## The fix

`gem5` already had the missing mechanism: `bindpool` (`M5OP_BIND_POOL=0x56`,
`pseudo_inst.cc:666`), which backs a not-yet-touched VA range from a named
memory pool (0=DRAM, 1=CXL) — the SE-mode analogue of `mbind`, already fully
wired into gem5's dispatch and M5OP tables but never called from the
benchmark. `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp`'s `alloc_bytes`
had an explicit `#ifdef GEM5` branch that skipped placement entirely
(`(void)node;` — a deliberate, acknowledged stub, not an oversight).

Patched `alloc_bytes` to call a new `gem5_bind_pool()` wrapper (same
`.byte 0x0f,0x04,...` pattern as the existing `gem5_set_streaming()`) before
first touch, mapping `node==0` to pool 0 and any other node (the bench's own
default `fact_node=2` for "the CXL one") to pool 1. Rebuilt via the existing
`make gem5` target — no gem5 source change needed. Full patch in DutyFree
commit (see `git log -- benchmarks/e2e/hash_join/src/cxl_join_bench.cpp`).

**One unrelated bug surfaced and fixed along the way:** the gem5 build
crashed (`std::system_error: Resource temporarily unavailable` from
`std::thread` construction) at `--num-cpus=1`. `run_morsel` always spawns at
least one worker via `std::thread` even for `--threads 1` (main + 1 worker =
2 OS-level contexts), and gem5 SE mode needs a hardware context available
for each. Fixed by using `--num-cpus=2`, not a benchmark change.

## Placement verified from instantiated state, not assumed

Per-controller `bytesRead` in `stats.txt` (Gate-1's own standard, not the
in-binary `check_pages_on_node` stub, which still just returns `true`
unconditionally under `GEM5` and was not fixed here — there is no
"which pool is this address in" pseudo-op to make that check real):

| hot\_bytes | `mem_ctrls0` (pool 0/DRAM) | `mem_ctrls1` (pool 1/CXL) |
|---|---:|---:|
| 2 MiB | 5.25 MB | 67.68 MB |
| 10 MiB | 945.18 MB | 67.89 MB |

The CXL controller's traffic is ~constant across both runs (same 16 MiB
fact array, same pass count) — confirming `fact` consistently lands on pool
1 regardless of `hot_bytes`. The DRAM controller's traffic jumps **180×**
between the two `hot_bytes` settings — confirming the hot table is
genuinely on pool 0 *and* genuinely dependent on the shared cache hierarchy
once resized (candidate 1 from the prior document): at 2 MiB it barely
touches DRAM at all (mostly resident somewhere above it); at 10 MiB it very
much does not fit and drives real traffic. Placement is real, and sizing
now spans "collapsed" to "genuinely shared-cache-dependent" within the same
verified setup.

## H2 engages at both sizes; the fused cost does not move at either

HNF `DataArrayWriteOnFill` (the LLC-fill count H2 targets; 7th/last bucket
of `Cache_Controller.DataArrayWriteOnFill`, confirmed via the same
`config.json` version-to-controller mapping used for `tab:h1bw`):

| hot\_bytes | policy | HNF fills | active\_cycles\_per\_access |
|---|---|---:|---:|
| 2 MiB | wb | 1,136,303 | 58.706 |
| 2 MiB | stream (H2) | 356,951 (−68.6%) | 58.374 (−0.6%) |
| 10 MiB | wb | 15,970,551 | 123.725 |
| 10 MiB | stream (H2) | 14,842,644 (−7.1%) | 122.553 (−0.9%) |

$n{=}3$ per cell (`--reps 3`), CoV 0.09–1.64% — tight, but short of this
project's usual $n{\ge}10$ rep-paired-bootstrap bar, so treat the exact
percentages as indicative, not paper-grade. The qualitative result does not
need more reps to read clearly: **H2 measurably reduces LLC-fill traffic at
both hot-table sizes, including the one (10 MiB) now independently
confirmed to depend on the shared cache — and the fused hot-table cost
does not move either time.** This is the same finding
`GATE1_FUSED_NULL_OUTCOME.md` reported, but that version could not
distinguish "the mechanism doesn't help" from "nothing was really being
tested." This version can, and the mechanism-doesn't-help reading survives.

## What this changes

Not a fix, in the sense of producing a positive recovery number — it is a
**stronger negative result**, which is what #22 asked for once the lead
opted in to spending the time: the gem5 fused null was previously
inconclusive-by-construction (candidate 2 meant nothing was really compared
apples-to-apples); it is now a verified null under a setup independently
confirmed to have both correct cross-pool placement and a genuinely
shared-cache-dependent hot table. This more rigorously **confirms** —
rather than merely "is consistent with" — the real-hardware mechanism
decomposition's finding that the same-thread fused tax lives mostly outside
the shared-LLC admission channel H2 addresses.

**Recommendation for the paper:** `Sec5_Evaluation.tex:281-294`'s existing
"necessity, not payoff" framing does not need to change in substance, but
its margin note could be upgraded from "gem5 shows ~0 fused tax, consistent
with hardware decomp" to "gem5, under a placement- and sizing-verified
setup, shows H2 reducing LLC fills without reducing fused cost at either a
collapsed or a genuinely shared-cache-dependent hot-table size" — a
strictly stronger and now well-grounded claim. Would need a proper
$n{\ge}10$ bootstrap pass first if it is going to carry any specific
percentage into the paper; the $n{=}3$ runs here support the qualitative
claim, not a citable number.
