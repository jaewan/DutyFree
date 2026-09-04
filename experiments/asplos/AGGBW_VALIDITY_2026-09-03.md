# Is `agg_bw_sum` physically valid? — validity audit of the multi-core H1 bandwidth metric

Audit of the headline metric of `H1BW_MULTICORE_OUTCOME_2026-09-03.md` and
`H1BW_CXLBW_OUTCOME_2026-09-03.md`. Reads only the twenty-one completed
`gem5/logs/se_chi/h1bw_mc_*_20260904` cells, the benchmark source, the runner
and the gem5 source that is already compiled into `gem5.opt`. **No run was
launched, `gem5/src/` was not modified, nothing under `gem5/logs/` was
written, and no `*_PREREG_*` document was edited.** The successor campaign is
pre-registered in `AGGBW_WINDOW_PREREG_2026-09-03.md` and was **not** run.

## The answer

**The published multi-core ratios can stand as written, and the H2-over-WB
figures are conservative — but for reasons that are not the ones the certified
documents give, and one certified mechanism claim has to be withdrawn.**

Four findings, in descending order of consequence.

1. **The 132.9% reading does not prove stagger.** It is explained by LLC
   supply, and the arithmetic is not close: for `agg_bw_sum` to be infeasible,
   at least 75.8% of the measured pass would have to cross the capped
   controller, and the counters bound that share at **43.6%**. The
   local-DRAM hypothesis is separately dead — `ALL_CXL=1` puts every process
   on the CXL pool and `system.mem_ctrls0` carries **zero** traffic in all 21
   cells — so the LLC is the whole explanation, and it suffices with a factor
   of 1.9 in hand. `H1BW_CXLBW_OUTCOME_2026-09-03.md`'s "inflated by at least
   1.329x" is **not established** and its supporting inequality has a false
   premise.

2. **Window phase is reconstructable from the completed artifacts, and the
   stagger is small.** Per-CPU `numCycles` gives each instance's program-end
   time in absolute simulated time; subtracting its own `seconds` gives its
   window. The reconstruction is validated against an independent signal (the
   order in which the instances' JSON lines reach `console.log`) and is
   accurate to ~10 us. **`agg_bw_sum` is high by 2.4–16.7%**, the all-N
   concurrent intersection is non-empty in every one of fifteen cells, and it
   covers 83.9–98.8% of the narrowest window.

3. **The published ratios are floors, not ceilings.** WB is the most staggered
   arm and H2 the least, so recomputing on a windowed denominator *widens*
   H2-over-WB: 1.2500 -> **1.3411** at 4 cores and 1.3917 -> **1.4479** at 8.
   The ordering `H2 >= WB > pfoff` holds on every metric in every cell. Every
   instance in every arm moves exactly 8,388,608 bytes through its measured
   window, from an identical seed and an identical instruction stream, so a
   shorter window means a genuinely faster arm and not a different amount of
   work.

4. **A certified mechanism claim must be withdrawn: the LLC supplies roughly
   half of the `h2` and `pfoff` read stream, not none of it.** The 40 MiB LLC
   finishes these runs 94–107% occupied by dirty fact-array lines that
   `fill_fact` deposited and that the read passes never evict, because the
   STREAMING policy bypasses their clean fills. This does not disturb any
   ratio, but it means **"aggregate CXL read bandwidth" is the wrong name for
   20–43 GB/s**, and it means H2 and WB are *not* on equal footing with
   respect to where their bytes come from — which is the exact asymmetry
   `H1BW_MULTICORE_OUTCOME_2026-09-03.md` declared absent. This is the one
   finding here that changes what the paper may say about mechanism.

**A re-run is not required to protect the published ratios.** It is worth ~4 h
to remove the one assumption finding 2 rests on and to deliver the windowed
traffic counters that two prior campaigns asked for and neither had;
`AGGBW_WINDOW_PREREG_2026-09-03.md` registers it. The re-run that *is*
scientifically necessary before the paper claims to measure far-memory
streaming bandwidth is a different one — a benchmark-geometry change that
removes the residency confound of finding 4 — and it is out of scope here.

## What the metric counts, from the source

`run_stream()` (`cxl_join_bench.cpp:1153-1214`) is the whole of `stream-smoke`:

| step | line | notes |
|---|---|---|
| `alloc_bytes(fact_bytes, fact_node=1)` | 1158 | `mmap` + `gem5_bind_pool(p, bytes, 1)` -> CXL pool |
| `build_table(table, keys, 1 MiB, seed)` | 1166 | `std::vector<Entry>` / `std::vector<int64_t>`, **ordinary heap** |
| `fill_fact(fact, n, keys, hit_rate, seed)` | 1167 | writes every one of 524,288 tuples |
| `declare_streaming(fact, fact_bytes)` | 1174 | `policy=stream` only; m5op 0x55 |
| `check_pages_on_node` | 1176 | a `return true` stub under GEM5 |
| warm pass | 1183 | `warmups=1` |
| **measured loop** | **1190-1196** | `reps=1`; `t0`/`seconds_since` per rep |
| JSON emit, `free_bytes` | 1200-1213 | the epilogue |

The numerator is `bytes = c.fact_bytes * c.reps` (line 1198) and the reported
rate is `bytes / total_sec / 1e9` (line 1210), where `total_sec` is the sum of
the rep durations from `std::chrono::steady_clock`. So **`agg_bw_sum` counts
exactly `N x 8,388,608` bytes of fact-array reads, and nothing else** — no
table traffic, no writebacks, no over-fetch. Confirmed in the artifacts: all
120 instances across the 21 cells report `fact_bytes: 8388608`, `reps: 1`,
`warmups: 1`, `seed: 13835551735702238294`, `hit_rate: 0.5`,
`hot_bytes: 1048576` and `fact_base: 0x7ffff77ff000`. The instances are
bit-identical programs on bit-identical data in separate address spaces.

The gem5 binary takes the **scalar** path in `stream_read()`
(`cxl_join_bench.cpp:1055-1076`), not the AVX2 path: the `gem5` Makefile
target compiles with `-O3 -mclflushopt -DGEM5 -static` and **no
`-march=native`** (`benchmarks/e2e/hash_join/Makefile:44`), so `__AVX2__` is
undefined. The measured window is a dense sequential 8-byte-load scan over
8 MiB with an unroll of 32, eight register accumulator chains.

### Two knobs are parsed and never applied

`--threads` was already logged. `--hot-node` is the new one, and it is the
knob the premise of Question 1 rested on.

**`--hot-node 0` has no effect in `stream-smoke`.** `hot_node` is parsed
(`:2859`), echoed into the JSON (`:1106`), and used by no allocation on this
path: the hot table and its key vector are `std::vector`s and never pass
through `alloc_bytes`/`gem5_bind_pool`. With `ALL_CXL=1` (runner line 142) the
process default pool is 1 for every instance (`se.py:344,374`), so the table,
the keys, the stack and libc are all on the CXL range too.

**There is therefore no local-DRAM traffic anywhere in this harness**, and the
artifacts say so unambiguously: in all 21 cells, `system.mem_ctrls0` emits
**exactly one** non-zero counter in the whole of `stats.txt`, and it is
`power_state.pwrStateResidencyTicks::UNDEFINED`. Zero reads, zero writes.

This closes one branch of Question 1 outright. Nothing in `agg_bw_sum` can
have been served from an uncapped local range, because no byte in the run
was.

## Question 1 — the 132.9% reading does not prove stagger

### The inequality that has to be settled

`H1BW_CXLBW_OUTCOME_2026-09-03.md` §"The cap as an audit of `agg_bw_sum`"
argues: the measured pass delivers 67,108,864 useful bytes; every byte crossed
`mem_ctrls1`; at 31 ticks/byte that costs 2.0804 ms of controller time; the
widest single window is 1.5772 ms; therefore the windows cannot be concurrent
and 42.87 GB/s is high by at least 1.329x.

Step 2 is the load-bearing one, and its justification —
`cxl_read_over_demand = 1.016x` — is a whole-program aggregate, not a
statement about the measured pass. Restate the argument as a threshold on the
fraction `f` of the measured pass's useful bytes that cross the controller:

- all eight windows inside the **widest** window (1.5772 ms) requires
  `f <= 1.5772 / 2.0804 = 0.758`;
- all eight windows inside their **reconstructed union** (1.7210 ms, §Q2)
  requires `f <= 0.827`.

So the stagger inference stands only if `f > 0.758`. The certified document
assumes `f = 1`.

### `f` measured: the CXL read stream decomposes, and the read passes are a minority of it

Every HNF read miss becomes exactly one 64 B CXL read. The identity is exact,
not approximate, in all nine cells checked:

| cell | HNF `ReadMissPipe` (8 slices) | `mem_ctrls1.numReads::total` |
|---|--:|--:|
| `wb_8c` @32.26 | 2,844,406 | 2,844,406 |
| `h2_8c` @32.26 | 2,131,136 | 2,131,136 |
| `pfoff_8c` @32.26 | 2,114,960 | 2,114,960 |

Those misses split by request type, and the split differs enormously by arm:

| cell | `ReadShared.I.RU` | `ReadUnique_PoC.I.RU` | total |
|---|--:|--:|--:|
| `wb_8c` @32.26 | 2,824,204 | 20,200 | 2,844,404 |
| `h2_8c` @32.26 | 2,110,995 | 20,139 | 2,131,134 |
| `pfoff_8c` @32.26 | 899,092 | 1,215,867 | 2,114,959 |
| `wb_8c` uncapped | 2,810,895 | 20,189 | 2,831,084 |
| `h2_8c` uncapped | 2,113,813 | 20,148 | 2,133,961 |
| `pfoff_8c` uncapped | 899,525 | 1,215,868 | 2,115,393 |

**`pfoff` is the clean calibrator and it is the one that gives the game away.**
With no prefetcher, its 1,215,867 `ReadUnique_PoC` misses are the
write-allocate fetches of the setup phase: `fill_fact` writing 8 MiB of fact
plus `build_table` writing a 1 MiB table and a 0.5 MiB key vector, once per
instance. Divide by 8: **151,983 lines per instance**, against
131,072 (fact) + 16,384 (table) + 8,192 (keys) = 155,648 — 97.6% accounted, the
remainder being stack, libc and loader pages that were never written. At 4
cores the same counter gives 607,930 lines, i.e. **151,983 per instance
again**, to the line.

Those fetches cannot come from anywhere but memory. They are the first touch
of freshly `mmap`'d anonymous pages, `fill_fact` writes each line exactly once
in one sequential sweep, so no line is fetched twice, and the LLC is empty at
those addresses. **1,215,867 lines is both a floor and a near-exact count of
setup fetches, and it is the same in every arm because every arm runs the
identical setup.**

In `h2` and `wb` the same fetches arrive at the home node as `ReadShared`
rather than `ReadUnique`, because the L1D/L2 prefetcher runs ahead of the
store stream. The reclassification is confirmed by a five-significant-figure
identity:

```
h2_8c ReadShared.I.RU  -  pfoff_8c ReadShared.I.RU  =  2,110,995 - 899,092 = 1,211,903
pfoff_8c ReadUnique_PoC.I.RU                        =                        1,215,867
                                                       agree to 0.33%
```

Subtract the setup and what remains is the CXL read supply available to the
two read passes, which between them touch `2 x 8 MiB x N / 64` = 2,097,152
lines at 8 cores:

| cell | CXL read lines | - setup | = for the two read passes | of 2,097,152 needed | **`f` <=** |
|---|--:|--:|--:|--:|--:|
| `wb_8c` @32.26 | 2,844,406 | 1,215,867 | 1,628,539 | 77.7% | **0.777** |
| `h2_8c` @32.26 | 2,131,136 | 1,215,867 | 915,269 | 43.6% | **0.436** |
| `pfoff_8c` @32.26 | 2,114,960 | 1,215,867 | 899,093 | 42.9% | **0.429** |
| `wb_8c` uncapped | 2,831,086 | 1,215,868 | 1,615,218 | 77.0% | 0.770 |
| `h2_8c` uncapped | 2,133,963 | 1,215,868 | 918,095 | 43.8% | 0.438 |
| `pfoff_8c` uncapped | 2,115,394 | 1,215,868 | 899,526 | 42.9% | 0.429 |
| `wb_4c` uncapped | 1,422,102 | 607,930 | 814,172 | 77.6% | 0.776 |
| `h2_4c` uncapped | 1,084,243 | 607,930 | 476,313 | 45.4% | 0.454 |
| `pfoff_4c` uncapped | 1,056,228 | 607,930 | 448,298 | 42.8% | 0.428 |

These are upper bounds on `f`, one-sided in the safe direction: any
prefetch over-fetch consumes CXL reads without delivering a consumed byte, so
the true `f` is lower still. For `pfoff` the bound is tight by construction —
with no prefetcher, "CXL read lines minus setup" *is* its `ReadShared` miss
count, 899,093 against 899,092.

**`f <= 0.436` against a requirement of `f > 0.758`. The inequality fails by a
factor of 1.74 on the widest-window denominator and 1.90 on the union. The
132.9% reading is not evidence of stagger.**

Charging the writebacks as well does not rescue it. During the read passes
`h2`'s LLC allocation pressure is `WriteEvictFull.RU.UC` = 78,955 plus
`UC_RU.UC` = 19,153, so at most 98,108 resident lines can be displaced and at
most 6,278,912 B of writes can be attributed to the window — 0.094 per useful
byte. Total in-window controller traffic is then `<= 0.530` bytes per useful
byte, costing 1.1024 ms of controller time against a 1.7210 ms union span.
**Feasible with 36% headroom.**

Turned around: with 43.6% of the useful bytes crossing a 32.2581 GB/s
controller, the largest *useful* aggregate rate the cell could sustain is
`32.2581 / 0.530 = 60.9 GB/s`. The reported 42.87 GB/s is **70% of that**, not
133% of anything. 132.9% of the raw ceiling is exactly what you get when you
compare a rate of delivered-to-core bytes against a ceiling on a path that
carries fewer than half of them.

### Why the LLC can do this: it is full of `fill_fact`'s dirty lines and the stream never evicts them

The mechanism is not cache reuse by the stream, which is why the certified
"cyclic sequential scan gets zero reuse under LRU" argument missed it. The
mechanism is that `fill_fact` **writes** the entire working set immediately
before the passes read it, the dirty lines land in the LLC on eviction from
the private L2s, and the STREAMING policy then prevents the read passes from
allocating anything that could displace them. The HNF is configured
`alloc_on_readonce/readshared/readunique/seq_acc = false`,
`alloc_on_writeback = true`, so read misses never allocate at all.

Net dirty residency, from the home-node transition counters, against a 40 MiB
/ 655,360-line LLC:

| cell | new dirty allocs (`WriteBackFull.RU.UD`) | dirty evictions (`LocalHN_Eviction.UD.I` + `UD_RU.RU`) | net resident | of capacity |
|---|--:|--:|--:|--:|
| `h2_8c` @32.26 | 1,229,220 | 565,898 + 47,486 | 615,836 | **94.0%** |
| `pfoff_8c` @32.26 | 1,236,803 | 562,519 + 2,344 | 671,940 | **102.5%** |
| `wb_8c` @32.26 | 1,427,836 (+1,544,235 clean) | 2,267,956 (all states) | 704,115 | **107.4%** |

The `pfoff` and `wb` figures exceed capacity by 2.5% and 7.4%, which bounds
the residual of this transition accounting — the counters do not capture every
invalidation path. Within that residual the conclusion is unambiguous:
**the LLC ends these runs essentially full, and for the two STREAMING arms it
is full of dirty fact lines.**

The read passes confirm they are hitting them. `ReadShared` hits are almost
entirely on dirty lines, not clean ones:

| cell | `ReadShared.UD.UD_RU` (hit, dirty) | `ReadShared.UC.UC_RU` (hit, clean) | clean fills during the passes |
|---|--:|--:|--:|
| `h2_8c` @32.26 | 1,985,051 | 22,050 | 78,955 |
| `pfoff_8c` @32.26 | 1,897,088 | 1,755 | 35,285 |
| `wb_8c` @32.26 | 1,276,390 | 148,945 | **1,495,749** |

WB is the contrast that proves the mechanism: it allocates on clean eviction,
so its read passes push **19x** more allocation pressure through the LLC than
`h2` does, evict the resident dirty lines, and re-fetch them — which is
exactly why WB's `f` is 0.777 against `h2`'s 0.436 and why WB pulls 1.78x more
CXL read lines to deliver the same bytes.

### Verdict on Question 1

**The 132.9% reading is explained by LLC traffic. It is not evidence of
stagger and it does not establish a lower bound on inflation.** The
local-DRAM branch of the hypothesis is refuted outright (zero `mem_ctrls0`
traffic, `--hot-node` inert, `ALL_CXL=1`); the LLC branch is confirmed and is
more than sufficient. `H1BW_CXLBW_OUTCOME_2026-09-03.md` needs the corrections
in §"Corrections" and Addendum 2 of that file.

## Question 2 — window phase, bounded directly

### Nothing in the harness constrains phase, and there is no barrier

Confirmed by reading both: `run_h1bw_multicore.sh` launches N instances as one
`--cmd=a;b;c` list and contains no synchronisation of any kind;
`run_stream()` contains none either. The benchmark *does* contain a
cross-process barrier — `run_fs_e2e_calibrate()` at `cxl_join_bench.cpp:1435`,
with `MAP_SHARED|MAP_ANONYMOUS`, `std::atomic<int> ready/go` and
`wait_for_go()` spinning on `__builtin_ia32_pause()` — but it is `#ifdef
GEM5_FS`, it `fork()`s, and it is unreachable from `stream-smoke`. §Q4
establishes that it is also not portable to SE mode.

`declare_streaming` is eliminated as a source of arm-dependent phase: the
`declare_seconds` field is **0.51–3.98 us** in all 120 instances, five orders of
magnitude below the setup phase.

### The phase *is* reconstructable, and the certified documents left this on the table

Two facts combine into an exact reconstruction.

**Per-CPU `numCycles` is each instance's program-end time.** In SE mode a
CPU halts when its process exits and stops accumulating cycles. So
`numCycles_i x 526 ps` is instance `i`'s end time measured from `t = 0`. The
check is that the maximum equals `simSeconds` exactly: in `wb_4c`, cpu0 gives
84.1330 ms and `simSeconds` is 0.084133 s, ratio 1.000000, while the other
three CPUs give 84.0501, 83.9370 and 83.8859 ms. If halted CPUs kept ticking,
all four would be equal. They are not.

**The epilogue length cancels.** Instance `i`'s window is
`[T_i - eps_i - d_i, T_i - eps_i]` where `d_i` is its reported `seconds` and
`eps_i` is the time from window close to process exit — `getrusage`,
`smaps_info`, the JSON write, `free_bytes`. If `eps` is the same for every
instance in a run, then

```
union span = max(T_i - eps) - min(T_i - eps - d_i) = max(T_i) - min(T_i - d_i)
```

and `eps` **drops out**. The reconstruction needs no start timestamps and no
knowledge of `eps` — only that it is common. Every instance runs the identical
epilogue on identical sizes, so this is the natural assumption, and it is
testable.

### The reconstruction validates against an independent signal

The order in which instances' JSON lines land in `console.log` is set by the
simulated time at which each executes its `write`, i.e. by window close plus a
*different* constant. The two orderings are independent evidence about the
same thing.

| cell | stdout order matches `numCycles` order | largest program-end gap involved in any inversion |
|---|---|---|
| `wb_4c` | **4/4** | — |
| `h2_4c` | 2/4 | 7.73 us |
| `pfoff_4c` | **4/4** | — |
| `wb_8c` | **8/8** | — |
| `h2_8c` | 6/8 | **0.11 us** |
| `pfoff_8c` | **8/8** | — |
| `wb_8c` @32.26 | **8/8** | — |
| `h2_8c` @32.26 | 6/8 | 2.34 us |
| `pfoff_8c` @32.26 | 6/8 | **0.11 us** |
| `wb_8c` @62.50 | **8/8** | — |
| `h2_8c` @62.50 | 5/8 | 8.10 us |
| `pfoff_8c` @62.50 | **8/8** | — |
| `wb_4c` @32.26 | **4/4** | — |
| `h2_4c` @32.26 | **4/4** | — |
| `pfoff_4c` @32.26 | 2/4 | 9.84 us |

**Nine of fifteen cells reproduce the ordering exactly, and every inversion in
the other six is an adjacent pair separated by 0.11–9.84 us.** The
constant-epilogue model is therefore accurate to **~10 us**, which is
0.4–0.8% of a 1.3–2.6 ms window. A second self-consistency check: the
reconstructed window *starts* cluster to within 36–353 us across an 82–88 ms
setup phase (0.04–0.42%), which is what N identical programs launched together
must do and is not what a randomly varying epilogue would produce.

### Reconstructed windows and the interval

| cell | `agg_bw_sum` | `R_disjoint` | `R_union` | union / widest | intersection / narrowest | `R_union` / `agg_bw_sum` |
|---|--:|--:|--:|--:|--:|--:|
| `wb_4c` | 20.087 | 5.013 | **18.291** | 1.046 | 94.9% | 0.911 |
| `h2_4c` | 25.108 | 6.277 | **24.530** | 1.016 | 98.8% | 0.977 |
| `pfoff_4c` | 13.274 | 3.318 | **12.932** | 1.014 | 98.6% | 0.974 |
| `wb_8c` | 30.997 | 3.872 | **26.655** | 1.128 | 83.9% | 0.860 |
| `h2_8c` | 43.140 | 5.392 | **38.595** | 1.098 | 89.7% | 0.895 |
| `pfoff_8c` | 26.983 | 3.370 | **23.797** | 1.068 | 92.4% | 0.882 |
| `wb_8c` @32.26 | 29.967 | 3.740 | **26.442** | 1.079 | 88.2% | 0.882 |
| `h2_8c` @32.26 | 42.873 | 5.359 | **38.994** | 1.091 | 91.9% | 0.910 |
| `pfoff_8c` @32.26 | 26.890 | 3.358 | **23.818** | 1.073 | 92.6% | 0.886 |
| `wb_8c` @62.50 | 31.050 | 3.878 | **26.601** | 1.124 | 86.0% | 0.857 |
| `h2_8c` @62.50 | 42.537 | 5.317 | **40.686** | 1.036 | 96.8% | 0.957 |
| `pfoff_8c` @62.50 | 26.944 | 3.365 | **23.668** | 1.071 | 92.1% | 0.878 |

All rates GB/s. `R_disjoint` = total bytes / sum of window lengths (the
rigorous floor under arbitrary stagger); `R_union` = total bytes / union span;
"intersection" is the interval in which all N instances are simultaneously
inside their measured windows.

**The defensible interval for the true concurrent aggregate rate is
`[R_union, agg_bw_sum]`.** `R_union` is the average rate over the whole
measured episode and is a lower bound because part of the union has fewer than
N instances active; `agg_bw_sum` is the rate over the intersection, where all
N are active, and is an upper bound because at the edges of the union the
surviving instances face less contention and run faster than their
window-average.

- **4 cores: `agg_bw_sum` is high by 2.4–12.1%.**
- **8 cores: `agg_bw_sum` is high by 4.6–16.7%.**

The three quoted bounds, for the `h2_8c` @32.26 cell that generated the
question:

| bound | value | source |
|---|--:|---|
| no phase information at all (fully disjoint) | 5.359 GB/s | rigorous, useless |
| reconstructed union average | **38.994 GB/s** | this document |
| reported `agg_bw_sum` | 42.873 GB/s | published |
| certified claim ("high by at least 1.329x") | <= 32.258 GB/s | **not established** |

### The certified overlap floors are correct, and the claim that they were refuted is not

`H1BW_MULTICORE_OUTCOME_2026-09-03.md` published a "guaranteed pairwise
overlap" floor per cell, derived from program-end skew.
`H1BW_CXLBW_OUTCOME_2026-09-03.md` then declared that floor "refuted
directly". The reconstruction settles it: the floors hold everywhere.

| cell | published floor | reconstructed actual minimum pairwise overlap |
|---|--:|--:|
| `wb_4c` | >= 84.4% | 94.9% |
| `h2_4c` | >= 98.2% | 98.4% |
| `pfoff_4c` | >= 96.7% | 98.6% |
| `wb_8c` | >= 80.7% | 83.7% |
| `h2_8c` | >= 88.3% | 89.3% |
| `pfoff_8c` | >= 81.9% | 92.4% |
| `wb_8c` @32.26 | >= 79.2% | 88.2% |
| `h2_8c` @32.26 | >= 90.7% | **90.8%** |

Every reconstructed value is above its published floor, and the `h2_8c`
@32.26 cell — the one cited as the refutation — comes in at 90.84% against a
published floor of 90.7%, a **0.14 percentage-point** agreement. The floors
were sound; what was unsound was the premise that forced them to be doubted.

### Why the stagger is small without a barrier

Because the setup phase is the same instruction stream in every instance and
consumes 97.2–98.4% of the program. `simInsts / N` is 34.888M at 8 cores with
an across-arm spread below 0.001%, and the seed, sizes and virtual addresses
are identical. Eight identical programs started at simulated `t = 0` arrive at
their measured windows within 36–353 us of each other out of 82–88 ms of
prologue. The stagger is not zero and it is not arm-independent, but it is a
sub-percent phase error, not the order-unity effect the certified metric
audit inferred.

## Question 3 — the published ratios survive, and H2-over-WB is a floor

### Same bytes, same work: a shorter window means a faster arm

The subtlety is settled affirmatively and mechanically. Every one of the 120
instances reports `fact_bytes: 8388608`, `reps: 1`, `warmups: 1` and the same
`seed`, `hit_rate`, `hot_bytes` and `fact_base`. The numerator of
`bandwidth_gbps` is `fact_bytes * reps` — a **compile-time-identical
constant** across all arms, not a measured quantity. `simInsts / N` agrees
across arms to better than 0.001%. `h2`'s 1.55 ms window against `pfoff`'s
2.39 ms is therefore the same 8,388,608 bytes moved faster, not less work
measured.

**One qualification, and it is finding 4 rather than a measurement artifact:**
the arms move the same *useful* bytes but do not source them the same way.
`h2` gets <= 43.6% of its stream from the controller and `wb` <= 77.7%. That is
the policy under test operating as designed — non-allocation preserves the
resident data — but it means the arms are not on equal footing with respect to
where the bytes come from, and the certified claim that they are must be
withdrawn (§Corrections).

### The stagger is arm-dependent, and the direction is favourable

The window durations are not arm-independent, and neither is the skew. What
matters for a ratio is the *relative* skew, i.e. `R_union / agg_bw_sum`:

| arm | 4c | 8c | 8c @32.26 | 8c @62.50 | rank |
|---|--:|--:|--:|--:|---|
| `wb` | 0.911 | 0.860 | 0.882 | 0.857 | **most staggered** |
| `pfoff` | 0.974 | 0.882 | 0.886 | 0.878 | middle |
| `h2` | 0.977 | 0.895 | 0.910 | 0.957 | **least staggered** |

`wb` is the most staggered arm in all four cell groups. Its inter-instance
window spread is 6.4–12.1% against `h2`'s 2.0–2.9% — WB's LLC thrashing makes
the instances interfere unequally, which is a real arm-dependent effect and
not noise. Since `h2` is the least inflated and `wb` the most, **`agg_bw_sum`
understates H2-over-WB.**

### Each published ratio: floor, ceiling, or invariant

| ratio | published (`agg_bw_sum`) | windowed (`R_union`) | change | status |
|---|--:|--:|--:|---|
| H2 / WB, 4c | **1.2500** | 1.3411 | **+7.3%** | **FLOOR** |
| H2 / WB, 8c | **1.3917** | 1.4479 | **+4.0%** | **FLOOR** |
| WB / pfoff, 4c | 1.5132 | 1.4144 | −6.5% | **CEILING** |
| WB / pfoff, 8c | 1.1488 | 1.1201 | −2.5% | **CEILING** |
| H2 / pfoff, 4c | 1.8915 | 1.8969 | +0.3% | **INVARIANT** |
| H2 / pfoff, 8c | 1.5988 | 1.6219 | +1.4% | **INVARIANT** |
| ordering `H2 >= WB > pfoff` | holds | **holds** | — | **SAFE** |

The published +25% (4c) and +39% (8c) H2-over-WB margins are therefore
**conservative**: recomputed on a windowed denominator they are +34% and +45%.
They may be published as written, with the stronger figures available if
wanted.

WB-over-pfoff is a ceiling and loses 2.5–6.5% on the windowed metric, but it
survives with margin (1.12 at worst) so `WB > pfoff` is not at risk. It should
not be quoted to three digits — it was already flagged as the ratio that does
not transfer to the archive (1.513 new against 1.109 archived).

### How much of this depends on the reconstruction

Everything above uses the reconstruction for both arms, which is the correct
reading: the same instrument and the same assumption applies to both, so the
comparison is like-for-like. Two weaker readings, for completeness:

- **Each arm independently anywhere in its own `[R_union, agg_bw_sum]`
  interval:** H2/WB in **[1.221, 1.373]** at 4c and **[1.245, 1.618]** at 8c.
  Still strictly above 1.0, still H2-favourable, but the 8-core lower end is
  +24.5% rather than +39%. If a single number robust to *decorrelated* phase
  error is wanted for 8 cores, it is **"at least +24%"**.
- **No phase information at all**, each arm anywhere between fully disjoint
  and fully concurrent: H2/WB in [0.313, 5.00] at 4c and [0.174, 11.13] at 8c.
  **Unbounded in both directions for practical purposes.** This is the state
  the artifacts would be in without the reconstruction, and it is why the
  reconstruction is the substantive contribution of this document.

## Question 4 — the fix, specified and not run

Registered in full in **`AGGBW_WINDOW_PREREG_2026-09-03.md`**. Summary of what
changes and why, plus the one finding that contradicts the prior
prescriptions.

### The barrier both certified documents specify cannot be built in SE mode

Both prescribe "a shared anonymous mapping with an atomic arrival counter,
spinning on `__builtin_ia32_pause()`". Read from the gem5 source that is
already compiled into the binary:

- `mmapFunc` (`src/sim/syscall_emul.hh:2055`) emits
  `warn_once("mmap: writing to shared mmap region is currently unsupported.
  The write succeeds on the target, but it will not be propagated to the host
  or shared mappings")`, and the comment above it states there is "no
  structure which maintains information about which virtual memory areas are
  shared";
- `shmget` (29), `shmat` (30), `shmdt` (67) and `memfd_create` (319) carry no
  handler in `src/arch/x86/linux/syscall_tbl64.cc`, so they resolve to
  `unimplementedFunc`, which `fatal()`s (`src/sim/syscall_emul.cc:77`).

The N instances are separate `Process` objects with separate page tables, not
forks. An arrival counter written by one is invisible to the others, so the
prescribed barrier would deadlock every instance — the same livelock class it
was written to avoid. Making it work is a `src/sim/syscall_emul.hh` change and
needs the rebuild this work must not perform. The FS-mode barrier already in
the benchmark is not a counter-example: it works because it `fork()`s under a
real guest kernel.

### What to build instead

**1. Window bracketing — the primary fix, and it needs no rebuild.** Wrap the
measured loop (`cxl_join_bench.cpp:1190-1196`) in
`gem5_dump_stats_now(); gem5_reset_stats_now();` on both sides, with an
`AGGBW_WINDOW_{OPEN,CLOSE}` stderr marker each side for pairing. Both
wrappers **already exist in the file** (`:218` and `:211`), are already used
by `run_join()`/`run_morsel()`, and encode `M5OP_DUMP_STATS` = 0x41 and
`M5OP_RESET_STATS` = 0x40 — present in the binary at
`include/gem5/asm/generic/m5ops.h:59-60`, dispatched at `src/sim/pseudo_inst.hh`,
implemented at `src/sim/pseudo_inst.cc:318,332`. No new op byte sequence.
`M5OP_DUMP_RESET_STATS` = 0x42 is also compiled in and is an exact single-op
equivalent.

This works because `Root::RootStats::resetStats()` sets
`startTick = curTick()` (`src/sim/root.cc:107-110`) and `simTicks` is the
functor `curTick() - startTick` (`:83`), so each section's `simTicks` is the
interval since the previous reset and a cumulative sum recovers the absolute
tick of every boundary. With N instances there are `2N + 1` sections, every
window boundary is timestamped in absolute simulated time, and **the overlap
stops being reconstructed and becomes measured**. It also delivers the
window-scoped `mem_ctrls1` and HNF counters that both certified documents
named as "what would settle it".

**2. `--reps 8` — shrinks the stagger without a barrier.** The start skew is
set by the setup phase (36–353 us) and does not grow with reps; the window
does. At `--reps 1` the overlap floor is 83.9–98.8%; at `--reps 8` the window
is ~8x longer against the same skew and the floor exceeds 97% arithmetically.
It also retires the `cov == 0` / `n = 1` limitation both campaigns listed as
not licensed. This is one character in `run_h1bw_multicore.sh` line 51
(`REPS=1` -> `REPS=${REPS:-1}`) plus a reps tag in the output directory name.

**3. A host-file barrier is possible but is registered as optional, not
primary.** `openat` (257), `pread64` (17), `pwrite64` (18) and `ftruncate`
(77) all carry real handlers against the host filesystem, so a byte-array
rendezvous file would work; `flock` (73) and `fsync` (74) do not and must not
appear in it. It is optional because a spin loop across emulated syscalls is
the construct that cost five arms in r6b/r6e, and because it changes the setup
instruction stream and would make the cells non-comparable to the six
published ones.

Files touched: `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp`,
`experiments/asplos/run_h1bw_multicore.sh`, and a **new**
`experiments/asplos/analyze_aggbw_window.py`. `gem5/configs/` needs no change.
`gem5/src/` needs no change. The two existing analyzers are left untouched so
they keep certifying the completed campaigns.

**Cost, from the cells' own `MANIFEST.json`/`DONE.json` timestamps:** 4-core
cells took 1.322–1.432 h and 8-core cells 2.953–3.225 h. `--reps 8` adds
+11–20% of simulated ticks in the highest-miss-rate phase; budget +25%, giving
1.7 h per 4-core cell and 3.9 h per 8-core cell. Six primary cells launched
concurrently: **3.9–4.4 h wall.** Adding the three capped 8-core confirmation
cells leaves the wall unchanged at 4.0–4.5 h. **Budget 5 h for all nine
cells**, plus ~0.7 GB of `stats.txt`.

### Is a re-run necessary before publication?

**No, for the ratios.** They are floors, the ordering is safe on every metric
in every cell, and the reconstruction is validated. **Yes, before any 8-core
magnitude is quoted as a rate**, if the reviewer is expected to accept it
without the reconstruction's constant-epilogue assumption. **And separately
yes, before the paper describes these runs as measuring far-memory streaming
bandwidth** — that requires the geometry change of finding 4, which is a
different campaign and is not pre-registered here.

## Corrections to certified documents

Appended to the source documents as clearly-marked addenda, not edited in
place (rule A6.19). Quoted wording is verbatim from the certified text.

### `H1BW_MULTICORE_OUTCOME_2026-09-03.md`, §"LLC residency of the measured pass — the validity threat, refuted"

**Current:**

> Every arm pulled at least the entire two-pass working set across the CXL
> controller. **The LLC supplied none of the measured pass.** The prefetch-off
> arm is the clean control: with no prefetcher instantiated its CXL reads are
> exactly its demand fetches, and it reads 1.007x and 1.009x the two-pass
> demand — the residual sub-1% being the program's non-stream traffic.

**Replacement:**

> Every arm pulled at least the entire two-pass working set across the CXL
> controller in *aggregate byte count*, but that aggregate is not the measured
> pass and the agreement is a composition coincidence. Decomposed by request
> type at the home node, the prefetch-off arm's 2,114,960 CXL read lines are
> **1,215,867 `ReadUnique_PoC` write-allocate fetches from the setup phase**
> plus **899,092 `ReadShared` read fetches**, and only the second group can
> have served the two read passes, which need 2,097,152 lines. **The CXL
> controller supplied at most 42.9% of the read passes; the LLC supplied the
> rest.** The 1.007x/1.009x agreement is the near-coincidence of
> `1,215,867 + 899,092` with `2 x 1,048,576` and is not evidence of anything.
> The same decomposition gives <= 43.6% for H2 and <= 77.7% for WB. The
> mechanism is that `fill_fact` writes the whole working set immediately
> before the passes read it and the STREAMING bypass then prevents the read
> stream from displacing those dirty lines: the LLC finishes the run 94–107%
> full. See `AGGBW_VALIDITY_2026-09-03.md` §Q1.

### Same document, §"The feared WB/H2 asymmetry does not exist, and runs the other way"

**Current:**

> Since both arms read the whole stream from CXL, **WB and H2 are on equal
> footing with respect to the measured pass, and no directional bias needs to
> be declared.** H2 measuring faster than WB is consequently not an LLC-hit
> artifact.

**Replacement:**

> WB and H2 are **not** on equal footing with respect to where the measured
> pass's bytes come from: WB sources <= 77.7% of its read stream from the CXL
> controller against H2's <= 43.6%, because WB's clean-eviction fills
> (1,495,749 against H2's 78,955, a factor of 19) evict the LLC-resident
> dirty lines that H2's bypass preserves. H2's higher home-node hit fraction
> (50.08% against 34.58%) **is** stream traffic, not non-stream traffic. A
> directional bias must therefore be declared: **part of H2's measured
> advantage over WB is an LLC-hit advantage, and it is the policy under test
> producing it.** This strengthens the mechanism story — non-allocation
> preserves resident data — but it invalidates the claim that the arms are on
> equal footing, and it means the runs are not a clean far-memory streaming
> measurement at a 1.6x working-set-to-LLC ratio. The licensed ordering and
> the H2/WB ratio are unaffected; the *mechanism* statement "preserved MLP
> plus reduced fill-path latency" is incomplete and should read "preserved MLP,
> reduced fill-path latency, and fewer far-memory fetches per useful byte".

### `H1BW_CXLBW_OUTCOME_2026-09-03.md`, §"The cap as an audit of `agg_bw_sum`", step 2

**Current:**

> 2. Every one of those bytes crossed `mem_ctrls1`. The baseline campaign's
>    LLC-residency result establishes this and it reproduces here:
>    `cxl_read_over_demand` is **1.016x** for `h2_8c` @ 32.26, so CXL reads are
>    the two-pass demand plus 1.6%, and the 40 MiB LLC supplied none of it.

**Replacement:**

> 2. **This step is false.** At most 43.6% of those bytes crossed
>    `mem_ctrls1`. `cxl_read_over_demand = 1.016x` is a whole-program ratio
>    whose numerator is 1,211,903 setup write-allocate fetches plus 919,233
>    read-pass fetches, and it says nothing about the measured pass. The
>    inequality that follows therefore does not hold, and the conclusion drawn
>    from it is withdrawn. See `AGGBW_VALIDITY_2026-09-03.md` §Q1.

### Same document, §"The cap as an audit of `agg_bw_sum`", conclusion

**Current:**

> **`agg_bw_sum` = 42.87 GB/s is consequently not a concurrent delivered rate
> in this cell.** The rate averaged over the union of the windows is at most
> 32.2581 GB/s, so the reported figure is high by at least **1.329x**.

**Replacement:**

> `agg_bw_sum` = 42.87 GB/s is **not** shown to be non-concurrent by this
> cell. With <= 43.6% of the useful bytes crossing the controller and <= 0.094
> controller write bytes per useful byte attributable to the window, the eight
> measured passes require <= 1.1024 ms of controller time against a
> reconstructed union span of 1.7210 ms — feasible with 36% headroom. The
> reconstructed union average is **38.994 GB/s**, so `agg_bw_sum` is high by
> **10.0%**, not by at least 32.9%. The largest useful aggregate the cell could
> physically sustain is 60.9 GB/s. 132.9% of the raw ceiling is what a
> delivered-to-core rate reads when fewer than half its bytes cross the capped
> path.

### Same document, §"The cap as an audit of `agg_bw_sum`" and §"What this licenses"

**Current:**

> And the reported window overlap floor of 90.7% is refuted directly: that
> bound is derived from per-CPU `numCycles` skew, which measures *program-end*
> alignment, and this cell shows program-end alignment does not bound
> measured-pass alignment as tightly as was assumed.

**Replacement:**

> The reported window overlap floor of 90.7% is **confirmed**, not refuted.
> Reconstructing the windows from per-CPU `numCycles` and each instance's own
> `seconds` — an assignment in which the epilogue length cancels — gives an
> actual minimum pairwise overlap of **90.84%** in this cell, and every one of
> the fifteen cells checked lands at or above its published floor. The
> reconstruction is validated against an independent ordering signal to within
> ~10 us. Program-end alignment **does** bound measured-pass alignment, for
> the reason the baseline campaign gave: the setup phase is the same
> instruction stream in every instance and consumes 97%+ of the program.

### Also requiring correction, not appended here

- **`experiments/asplos/INDEX.md`**, the `H1BW_MULTICORE_OUTCOME` row: "LLC
  supplies **none** of the measured pass (prefetch-free control reads 1.007x
  the two-pass demand)". This is the summary line the next reader will see
  first and it is the claim withdrawn above. It should read "LLC supplies
  **~57%** of the prefetch-free and H2 read stream; the 1.007x figure is a
  composition coincidence (`AGGBW_VALIDITY_2026-09-03.md`)". Not edited here
  because `INDEX.md` is not this document's to rewrite.
- **`experiments/asplos/data/gem5/h1bw_multicore.jsonl`** and
  **`h1bw_cxlbw.jsonl`** carry `cxl_read_over_demand` and the overlap floors
  as record fields. The floors are sound. `cxl_read_over_demand` should be
  accompanied by the request-type decomposition before it is used again as a
  residency argument.

## Health findings, incidental

**Nine of 120 instances reported a non-zero `checksum`, and all nine were the
`cpu0` instance.** With `warmups=1, reps=1` the field is
`warm_pass ^ measured_pass` over identical, unmodified data and must be
exactly 0; it is 0 for 111 instances. The nine exceptions are in
`h2_4c_l3x4_bwt16`, `h2_8c`, `h2_8c_l3x8_bwt31`, `pfoff_8c`,
`pfoff_8c_l3x8_bwt16`, `pfoff_8c_l3x8_bwt31`, `wb_4c`, `wb_4c_l3x4_bwt16` and
`wb_8c_l3x8_bwt16`, spread across all three arms and both core counts,
never more than one per cell, and **always cpu0**.

This is functional-correctness evidence, not a timing artifact: both passes
still read 8,388,608 bytes and both still took the reported time, so no
bandwidth figure in any campaign changes. But a scan of unmodified memory
returning two different sums is either memory corruption or a functional bug,
it is non-deterministic in occurrence and deterministic in location, and it
sits in the same runs as the already-logged `free(): invalid size`. Flagged
for the same investigation as `alloc_bytes`/`free_bytes` size bookkeeping, and
recorded as a gate-worthy field: **`checksum != 0` in `stream-smoke` with
`warmups + reps == 2` should be a fail-closed condition** in any successor
analyzer. It is not one today.

## What this licenses, and what it does not

Licensed:

- **The published H2-over-WB ratios stand and are floors.** 1.2500 at 4 cores
  and 1.3917 at 8 cores on `agg_bw_sum`; 1.3411 and 1.4479 recomputed on a
  windowed denominator. The +25% and +39% margins may be published as
  written. If a figure robust to decorrelated phase error is wanted at 8
  cores, use **"at least +24%"**.
- **The ordering `H2 >= WB > pfoff` is safe**, on `agg_bw_sum`, on `R_union`
  and on `R_disjoint`, at both core counts, capped and uncapped.
- **`agg_bw_sum` is high by 2.4–16.7%**, cell-specific, with the correction
  running against H2 in every cell group.
- **The certified window-overlap floors are correct as floors** and are
  confirmed to within 0.14 pp in the cell where they were doubted.
- **There is no local-DRAM traffic in this harness.** `ALL_CXL=1`,
  `--hot-node` inert, `mem_ctrls0` at exactly zero in all 21 cells.
- **`H2 / pfoff` is phase-invariant to ±1.5%** and is the safest of the three
  ratios to quote as a point value.

Not licensed, and to be stated wherever these numbers appear:

- **Do not describe 20–43 GB/s as CXL or far-memory bandwidth.** At most 43.6%
  (`h2`), 42.9% (`pfoff`) and 77.7% (`wb`) of it crosses the CXL controller.
  It is aggregate read bandwidth delivered to the cores, and the LLC supplies
  a large and **arm-dependent** share.
- **Do not cite "the LLC supplied none of the measured pass."** Withdrawn
  above. Do not cite the 1.007x/1.009x `cxl_read_over_demand` figures as a
  residency refutation.
- **Do not cite "`agg_bw_sum` is inflated by at least 1.329x"** or the
  `h2_8c` "< 1.0, impossible" in-window traffic verdict. Both rest on the
  withdrawn premise.
- **Do not cite "WB and H2 are on equal footing with respect to the measured
  pass."** Withdrawn above.
- **`WB / pfoff` is a ceiling**, over-stated by 2.5–6.5%, and already known
  not to transfer to the archive. Do not quote it to three digits.
- **Absolute magnitudes carry a reconstruction assumption.** The interval
  `[R_union, agg_bw_sum]` depends on the epilogue costing each instance the
  same simulated time. Validated to ~10 us against an independent ordering
  signal, not proven. `AGGBW_WINDOW_PREREG_2026-09-03.md` removes it.
- **No in-window traffic rate is measured here.** The `f <= 0.436 / 0.777 /
  0.429` figures are whole-program bounds on a windowed quantity, one-sided in
  the safe direction. Windowed counters need the bracketing.
- **n = 1 per cell**, `cov` identically 0, no seed replication. No effect
  below roughly 10% is interpretable.
- **H2 is partially engaged** at 83–91% of a 96.0% ceiling on the pre-fix
  binary (`H2_BYPASS_COLLAPSE_2026-09-03.md`). Every H2 figure is a lower
  bound; a fix widens the H2 advantage and does not overturn anything here.
- **The residency confound is real and unresolved.** At a 1.6x
  working-set-to-LLC ratio with `fill_fact` writing the whole set immediately
  before the passes read it, these cells do not isolate far-memory streaming.
  Fixing it needs a benchmark-geometry change (a scrub between `fill_fact` and
  the passes, or a working set several times the LLC), separately
  pre-registered. **This is the highest-value follow-up in this document and
  it is larger than the window campaign.**

## Provenance

- Artifacts read: all twenty-one
  `gem5/logs/se_chi/h1bw_mc_*_20260904` cells (`console.log`, `stats.txt`,
  `config.ini`, `MANIFEST.json`, `DONE.json`). **Nothing under `gem5/logs/`
  was written and no process was signalled.**
- Per-instance records parsed from `console.log`; all six uncapped
  `agg_bw_sum` values reproduce the published figures exactly (20.0866,
  25.1083, 13.2741, 30.9972, 43.1402, 26.9832 GB/s), as do the twelve capped
  ones and all 21 wall times.
- Counters read from each run's own `stats.txt`. The
  `HNF ReadMissPipe == mem_ctrls1.numReads::total` identity holds exactly in
  every cell checked and is what licenses the request-type decomposition.
- Benchmark source: `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp`
  (unmodified), `benchmarks/e2e/hash_join/Makefile`. Runner:
  `experiments/asplos/run_h1bw_multicore.sh` (unmodified). Config:
  `gem5/configs/deprecated/example/se.py` (unmodified, read only).
- gem5 source read only, to establish what the compiled binary supports:
  `src/sim/syscall_emul.{hh,cc}`, `src/sim/syscall_desc.hh`,
  `src/sim/pseudo_inst.{hh,cc}`, `src/sim/root.cc`,
  `src/arch/x86/linux/syscall_tbl64.cc`,
  `include/gem5/asm/generic/m5ops.h`. **`gem5/src/` was not modified and
  `gem5.opt` was not rebuilt.**
- **The sibling worker's rebuild has landed during this audit.**
  `gem5/build_Intel_8592/gem5.opt` now has mtime `2026-09-04 12:51:05` and
  `sha256 = cb2904444d5c5c4d…`, against `cfd37207b9b7124a…` recorded in all
  twenty-one cells' manifests. **The binary that produced every published
  magnitude is no longer on disk.** Nothing in this document is affected: it
  reads only completed artifacts, and the four gem5 source files it cites for
  m5-op availability and SE shared-memory support
  (`syscall_emul.{hh,cc}`, `syscall_desc.hh`, `pseudo_inst.{hh,cc}`,
  `root.cc`, `syscall_tbl64.cc`, `m5ops.h`) are untouched by the CHI protocol
  fix, whose only working-tree edits are
  `src/mem/ruby/protocol/chi/CHI-cache-funcs.sm`, `src/python/m5/ticks.py`
  and `src/python/m5/SimObject.py`. It **is** a blocking condition on the
  successor campaign's G5 band; see
  `AGGBW_WINDOW_PREREG_2026-09-03.md` §"What this campaign cannot settle".
- Successor campaign: `AGGBW_WINDOW_PREREG_2026-09-03.md`, **not launched**.
- Supersedes nothing. Corrects `H1BW_MULTICORE_OUTCOME_2026-09-03.md` and
  `H1BW_CXLBW_OUTCOME_2026-09-03.md` by addendum; both retain their verdicts.
