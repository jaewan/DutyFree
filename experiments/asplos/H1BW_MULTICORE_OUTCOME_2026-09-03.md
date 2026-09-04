# Multi-core H1 bandwidth survival (4c / 8c) — outcome

Registered in `H1BW_MULTICORE_PREREG_2026-09-03.md`. Six runs, all
`exit: 0`, all 36 instances `status: "ok"`, all three pre-registered gates
passed on all six. Analyzer `analyze_h1bw_multicore.py`; machine-readable
record `data/gem5/h1bw_multicore.jsonl`.

Runs are stamped `20260904` rather than `20260903`: the runner takes
`STAMP=$(date +%Y%m%d)` in host-local time (`+09:00`) and the campaign was
launched at 04:13 JST. Same campaign, one calendar day later in the directory
name.

## Verdict against the pre-registered outcome table

**PASS.** The ordering H2 >= WB > prefetch-off holds at both core counts.

| | 4 cores | 8 cores |
|---|---|---|
| H2 >= WB | 25.11 >= 20.09 | 43.14 >= 31.00 |
| WB > prefetch-off | 20.09 > 13.27 | 31.00 > 26.98 |

Per the pre-registration this supersedes `preserved/gem5_streaming.tar.gz` as
the citable source for both core counts, and it supplies the 8-core row that
the archive announced (`8-core repeat launched for robustness`) and never
recorded. It is not a reproduction: the archive's runner is gone, so where this
campaign disagrees with the archive the difference cannot be attributed to the
archive versus the harness. That limitation was accepted going in and is
restated in every section below that compares the two.

## Results

`agg_bw_sum` is the sum of the per-instance `bandwidth_gbps` fields, each of
which is one instance's own 8 MiB divided by its own measured pass.

| run | `agg_bw_sum` | per core | inter-instance spread | window overlap floor | wall |
|---|---|---|---|---|---|
| `wb_4c` | 20.09 GB/s | 5.02 | 9.99% | 84.4% | 1.38 h |
| `h2_4c` | 25.11 GB/s | 6.28 | 1.82% | 98.2% | 1.38 h |
| `pfoff_4c` | 13.27 GB/s | 3.32 | 1.83% | 96.7% | 1.32 h |
| `wb_8c` | 31.00 GB/s | 3.87 | 6.25% | 80.7% | 3.12 h |
| `h2_8c` | 43.14 GB/s | 5.39 | 2.80% | 88.3% | 3.16 h |
| `pfoff_8c` | 26.98 GB/s | 3.37 | 9.89% | 81.9% | 2.95 h |

All six aggregates reproduce the previously circulated values exactly
(20.0866, 25.1083, 13.2741, 30.9972, 43.1402, 26.9832 GB/s), as do the wall
times. Scaling is sublinear for the two prefetch-on arms and linear for
prefetch-off:

| arm | 4c -> 8c | per-core retention |
|---|---|---|
| `wb` | 1.543x (ideal 2.000) | −22.8% |
| `h2` | 1.718x | −14.1% |
| `pfoff` | 2.033x | +1.6% |

Do **not** describe this campaign as scaling linearly. Two of three arms lose
14–23% of their per-core throughput when the core count doubles. The
contention is real; §"Where the contention is" localizes it.

## Realized configuration, read back from `config.ini`

Every value here is from the run's own `config.ini` or `stats.txt`, not from
`MANIFEST.json` and not from the runner (F9, S5.1).

| parameter | realized 4c | realized 8c | source |
|---|---|---|---|
| HNF (L3) slices | 4 | 8 | `system.ruby.hnf{i}.cntrl.cache` sections |
| per-slice size / assoc | 5,242,880 B / 20 | same | `size=`, `assoc=` |
| **total LLC** | **20 MiB** | **40 MiB** | sum over slices |
| HNF address interleave | 4-way, bits 6–7 | 8-way | `addr_ranges=0:274877906944:i:64:128` |
| HNF transaction buffers | 32 per slice (128 total) | 32 per slice (256 total) | `number_of_TBEs=32`, `CHI_config_8592.py:435` |
| directories (SNF) | 1 | 1 | `--num-dirs=1`, `system.ruby.snf` |
| SNF transaction buffers | 256 | 256 | `number_of_TBEs=256`, `CHI_config_8592.py:961` |
| CXL controller latency | 203 ns, `latency_var=0` | same | `system.mem_ctrls1.latency=203000` |
| DRAM controller latency | 98 ns | same | `system.mem_ctrls0.latency=98000` |
| memory type | `SimpleMemory` | same | `type=` |
| **memory bandwidth ceiling** | **500.00 GB/s per controller** | same | `bandwidth=2.000000` ticks/byte, `simFreq=1e12`; requested 512 GiB/s, see below |
| CPU clock | requested 1.9 GHz, **realized 1.9011407 GHz** | same | `system.cpu_clk_domain.clock=526` ticks; 1.9 GHz is 526.3158 ps, quantized to 526 (+0.060%) |
| L1 MSHRs | 48 | 48 | `L1_MSHR=48`, `CHI_config_8592.py:314` |
| L1 replacement-path depth | 16 (default) | 16 | `L1_REPL` unset, `CHI_config_8592.py:322` |
| prefetcher sections instantiated | 76 (`wb`,`h2`) / **0** (`pfoff`) | 152 / **0** | count of `*prefetcher*` sections |

Two of these deserve emphasis because they drive everything downstream.

**`bandwidth=2.000000` is ticks per byte, not GB/s.** `SimpleMemory.bandwidth`
is a `MemoryBandwidth` parameter whose `getValue()` returns
`ticks.fromSeconds(1/bytes_per_sec)`, and `simple_mem.hh:130` documents the
field as "Bandwidth in ticks per byte". Two ticks per byte at
`simFreq = 1e12` is 5.0e11 B/s, i.e. exactly 500 GB/s per controller.
Combined with `latency_var=0`, the CXL device in this model is a
**fixed-latency memory with no realistic link bandwidth limit**. The measured
aggregates consume 2.65–8.63% of it.

**Why it is exactly 500 and not 549.76, and why nobody saw it.** The
configured default is `512GiB/s` = 5.4976e11 B/s = 1.8190 ticks/byte, but
`ticks.fromSeconds()` (`gem5/src/python/m5/ticks.py:80`) returns an *integer*
tick count via `decimal.ROUND_HALF_UP`, so 1.8190 becomes 2 and the realized
ceiling is 500.00 GB/s — a silent 9.1% reduction from the requested value.
The guard that should have reported this cannot: it computes
`err = (value - int_value) / value` and tests `err > frequency_tolerance`, and
rounding *up* makes `err` negative. `grep -ci 'rounding error'` returns 0 on
every run in this campaign and on all six of the superseded ones.

Integer ticks-per-byte is a fine grid at low bandwidth and a coarse one at
high bandwidth: the representable neighbours of 500 GB/s are 1000 (1 tick) and
333 (3 ticks). This is why the problem only appeared recently. gem5 commit
`44b7eb7470` ("mem-ruby,configs,tests: calibrate latency; add STREAMING H3",
2026-06-05) raised the `SimpleMemory.bandwidth` default from `12.8GiB/s` to
`512GiB/s` as a `[minor]` line item, moving the parameter from a region where
quantization costs 0.3% (72.76 rounds to 73, giving 13.70 GB/s) into one where
it costs 9.1%. The comment directly above the changed line still reads "The
memory bandwidth limit default is set to 12.8GiB/s which is representative of
a x64 DDR3-1600 channel."

**Consequence for the archive.** The preserved REPORT's own explanation of its
section 4 numbers — "Aggregate is CXL-path-limited (~6-8 GB/s regardless of
cores)" — is mechanically impossible for any run after 2026-06-05, because
there was no CXL path limit to bind against. That invalidates the archive's
stated mechanism independently of its harness being unrecoverable.

Two campaigns were pre-registered to bound what this costs the paper:
`H1BW_CXLBW_PREREG_2026-09-03.md` (a realistic cap at 32.26 and 62.50 GB/s,
the nearest representable points to 32 and 64) and
`H1BW_SLICE_BRACKET_PREREG_2026-09-03.md`.

**The prefetch-off arm has zero prefetcher sections**, confirming
`PF_OFF_CORES` took effect on every core rather than being requested and
dropped.

## The regime discrepancy, and its resolution

The new absolute magnitudes are 3.22x (WB), 3.25x (H2) and 2.36x
(prefetch-off) the archive's 4-core section-4 figures of 6.23 / 7.73 / 5.62
GB/s, while the H2/WB ratio agrees to within 0.7% (1.2500 new against 1.2408
archived). A ratio that reproduces under a magnitude that does not is the
signature of two different regimes, and the write-up must say which.

### There is no saturated shared resource in the new runs

Every candidate shared structure was checked in `stats.txt` and none is close
to its limit. Occupancies marked *window* are Little's-law estimates scoped to
the measured pass; the raw `stats.txt` counters average over the whole
simulated program, of which the measured pass is only 1.6–2.8%, so the raw
whole-run numbers understate the streaming phase and are given separately.

| shared structure | 4c | 8c | limit |
|---|---|---|---|
| CXL controller bandwidth | 4.0 / 5.0 / 2.7% | 6.2 / 8.6 / 5.4% | ~500 GB/s |
| single SNF, whole-run occupancy | 1.63 / 1.20 / 0.99% | 3.85 / 2.66 / 1.99% | 256 TBEs |
| single SNF, *window* occupancy | 24.9 / 31.1 / 16.4% | 38.4 / 53.5 / 33.4% | 256 TBEs |
| HNF transaction buffers, *window* | 47.3 / 47.8 / 23.4% | 42.5 / 43.0 / 22.1% | 32 x N |
| L1 MSHRs aggregated, *window* | 31.5 / 31.8 / 15.6% | 28.3 / 28.7 / 14.7% | 48 x N |
| per-slice HNF request balance | 1.003–1.004x | 1.003–1.010x | 1.000x is perfect |
| network link utilization | <0.51% | <0.28% | — |

(Triples are `wb / h2 / pfoff`.)

Nothing exceeds 54% of any budget. The HNF slices are balanced to within 1%,
so no slice is a hot spot. No link reports meaningful bandwidth saturation.
The first half of the leading hypothesis is therefore **confirmed: the new
runs contain no shared bottleneck.**

One caution for anyone re-deriving this: the HNF *demand*-only access counters
are imbalanced by up to 2.04x across slices at 8c. That imbalance lives
entirely in a small non-stream subset (649k demand accesses against 4.33M
total). Counting demand plus prefetch accesses, which is what the stream
actually generates, the slices are balanced to 1.010x. Do not quote the
demand-only imbalance as evidence of a hot slice.

### But the mechanism is not the one that was hypothesised

The pre-registration and the archive both frame the ceiling as "the CXL path".
There is no CXL path to saturate. `SimpleMemory` is a fixed-latency device at
~500 GB/s, so in this model aggregate throughput is *identically*
concurrency x 64 B / latency, and it must scale with core count and with any
concurrency budget until some buffer pool binds. That is why this campaign
scales and it is why no amount of core count would have produced the archive's
"~6–8 GB/s regardless of cores" from a *memory* limit. Whatever capped the
archive, if anything capped it, was a Ruby transaction-buffer pool, not a link.

The slice count does matter, but for a specific structural reason rather than
for capacity or for data-array throughput. `HNF_MSHR` defaults to 32
(`CHI_config_8592.py:435`), so the home-node transaction-buffer budget is
32 x N — 128 at 4c, 256 at 8c, and **32 at one slice**. The measured window
occupied roughly 60 of those buffers at 4c and 109 at 8c, so a single slice
would supply less than the 4-core runs demonstrably needed. Capacity is not
the mechanism (a 5 MiB LLC would simply thrash harder, and §"LLC residency"
shows the LLC supplies none of the stream anyway), and neither is array
throughput: the HNF cache is configured `dataArrayBanks=1` with
`resourceStalls=false`, so bank conflicts are counted but never enforced. The
single-slice bracket in §"Recommended bracketing run" is designed around the
TBE pool for exactly this reason.

### Where the contention is

The sublinearity of `wb` and `h2` is latency inflation at the shared home node
and single directory, not saturation:

| quantity | `wb` 4c -> 8c | `h2` 4c -> 8c | `pfoff` 4c -> 8c |
|---|---|---|---|
| HNF read transaction latency | 192.8 -> 224.7 ns (+16.5%) | 155.8 -> 163.5 ns (+4.9%) | 144.2 -> 134.3 ns (−6.9%) |
| SNF `datOut` mean stall | 5.77 -> 24.91 ticks | 2.76 -> 11.60 ticks | 0.00 -> 0.02 ticks |
| SNF `requestToMemory` mean stall | 519 -> 787 ticks | 345 -> 461 ticks | 156 -> 213 ticks |
| per-core throughput | −22.8% | −14.1% | +1.6% |

The ordering of the latency inflation matches the ordering of the throughput
loss, and the prefetch-off arm — which never gets above 23% of any budget —
shows neither. The absolute queueing delays are small (25 ticks is 0.025 ns
against a 203 ns memory latency), so the SNF queues are a *marker* of the
contention rather than its full magnitude; most of the per-transaction latency
growth is in the home node's own transaction lifetime. Report the effect as
measured, and do not describe the single directory as a bottleneck: at 3.85%
whole-run occupancy it is not one.

### Why the ratio transfers and the magnitude does not

Because throughput in this model is concurrency x 64 B / latency, the two
factors can be read off separately. They separate cleanly, and the result is
the mechanistic core of this document:

| run | home-node concurrency (lines in flight) | HNF read latency | `agg_bw_sum` |
|---|---|---|---|
| `wb_4c` | 60.5 | 192.8 ns | 20.09 GB/s |
| `h2_4c` | 61.1 | 155.8 ns | 25.11 GB/s |
| `wb_8c` | 108.9 | 224.7 ns | 31.00 GB/s |
| `h2_8c` | 110.2 | 163.5 ns | 43.14 GB/s |

**WB and H2 run at the same concurrency** — 60.5 against 61.1 at 4c and 108.9
against 110.2 at 8c, within 1.2% in both cases — and differ only in latency
per transaction. The bandwidth ratio is therefore just the inverse latency
ratio, and it is:

| | predicted from latency | measured `agg_bw_sum` |
|---|---|---|
| H2/WB at 4c | 1.2375 | 1.2500 |
| H2/WB at 8c | 1.3743 | 1.3917 |

Concurrency is a fabric-budget quantity: it scales with slice count, core
count and MSHR budget. Latency per transaction is a policy quantity: WB pays
for writing 1.81M lines into the LLC and 41 MiB back out to CXL, H2 bypasses
1.00M of those fills and writes back 23 MiB. **Change the slice count and the
concurrency budget changes; the latency ratio does not.** That is why the
archive and this campaign agree on H2/WB and disagree by 3.2x on magnitude,
and it is the reason the ratio is the transferable quantity.

### Which regime the archive measured cannot be determined

The archive's own numbers are consistent with two readings, and its artifact
cannot separate them.

*Saturation*, which is what section 4 asserts ("CXL-path-limited (~6–8 GB/s
regardless of cores) -> this is the ratio/survival result, not absolute
scaling"). Its 4-core aggregates are only 1.145x, 1.328x and 1.222x its own
single-core section-1 figures (5.44 / 5.82 / 4.60 GB/s at MSHR=48), which is
the signature of four cores sharing something that one core already nearly
filled.

*Denominator*, i.e. that "aggregate BW = 32MiB/total_sec" divided by a span
wider than the concurrent window — the same defect that makes this campaign's
own `agg_bw_wall` 36–62x too low. Applying "total bytes / sum of per-instance
windows" to the new 4-core runs gives 5.01 / 6.28 / 3.32 GB/s, which is
1.24x, 1.23x and 1.69x *below* the archive's 6.23 / 7.73 / 5.62. On that
reading the archive's "aggregate" is numerically a per-core-scale quantity and
its four instances were never concurrently accounted for.

One piece of positive evidence leans toward the second reading. The archive's
LLC fill counts are 0.5868x and 0.5872x the new campaign's for WB and H2 —
the same factor to four significant figures — while the fill *reduction*
reproduces almost exactly (−44.5% archived, −44.6% new: 1,063,653 -> 589,928
against 1,812,624 -> 1,004,610). A uniform rescaling of both arms is what a
shorter or narrower accounting window produces. Saturation compresses arms
toward each other; it does not scale them by a common factor. This is
suggestive and not decisive, because 0.587 corresponds to no configuration we
can name, and the prefetch-off arm does not share the factor (0.7428x).

**Record this as: the archive and this campaign measured different regimes.
The archive measured a configuration in which aggregate bandwidth was
insensitive to core count, whether because a shared structure saturated or
because its metric never counted concurrency; this campaign measured a
configuration in which no shared structure is above 54% of its budget and
throughput scales with cores at 1.54–2.03x per doubling. The transferable
quantity is the H2/WB ratio, not the absolute magnitude.**

### The transferable ratio is narrower than "the ratios agree"

Only H2/WB transfers. The prefetch-off arm's ratio does not, at either core
count:

| ratio | archive 1c | archive 4c | new 4c | new 8c |
|---|---|---|---|---|
| H2 / WB | 1.070 | **1.241** | **1.250** | 1.392 |
| WB / prefetch-off | 1.183 | 1.109 | 1.513 | 1.149 |
| H2 / prefetch-off | 1.265 | 1.375 | 1.892 | 1.599 |

WB/prefetch-off is 1.513 new against 1.109 archived at 4 cores, a 36%
discrepancy, and it moves to 1.149 at 8 cores. Quote H2/WB as reproducing.
Do **not** claim the arm structure as a whole reproduces.

The reason is visible in the concurrency decomposition: prefetch-off is not
fabric-limited at all. It reaches only 23% of the HNF buffer budget and 15% of
the L1 MSHR budget, so its throughput is set by how fast an O3 core can
generate demand misses without a prefetcher. That is a core-side limit, which
is why prefetch-off is the one arm that scales linearly (2.033x) and why its
ratio to the other two is a function of the configuration rather than of the
LLC policy under test.

## LLC residency of the measured pass — the validity threat, refuted

The concern was serious and worth quantifying. Total working set is 32 MiB at
4c against 20 MiB of LLC and 64 MiB at 8c against 40 MiB — about 1.6x in both
cases, against the 3.2x (16 MiB stream, 5 MiB LLC) of the archive's
single-core section 1, which the paper describes as "larger than the 5 MiB
LLC". At 1.6x the warm pass could plausibly leave much of the data resident
and the measured pass could be reading from the LLC rather than from CXL.

It does not. The decisive counter is what the CXL memory controller actually
delivered, against the two-pass demand of 2 x 8 MiB x N:

| run | CXL bytes read | two-pass demand | ratio | HNF fills | HNF bypasses |
|---|---|---|---|---|---|
| `wb_4c` | 86.8 MiB | 64.0 MiB | 1.356x | 1,812,624 | 0 |
| `h2_4c` | 66.2 MiB | 64.0 MiB | 1.034x | 1,004,610 | 421,432 |
| `pfoff_4c` | 64.5 MiB | 64.0 MiB | **1.007x** | 748,713 | 427,363 |
| `wb_8c` | 172.8 MiB | 128.0 MiB | 1.350x | 4,065,739 | 0 |
| `h2_8c` | 130.2 MiB | 128.0 MiB | 1.018x | 2,257,656 | 857,334 |
| `pfoff_8c` | 129.1 MiB | 128.0 MiB | **1.009x** | 1,921,270 | 850,083 |

Every arm pulled at least the entire two-pass working set across the CXL
controller. **The LLC supplied none of the measured pass.** The prefetch-off
arm is the clean control: with no prefetcher instantiated its CXL reads are
exactly its demand fetches, and it reads 1.007x and 1.009x the two-pass
demand — the residual sub-1% being the program's non-stream traffic. WB's
1.35x excess is prefetch over-fetch plus re-fetch of lines its own fill
traffic evicted (it writes 116 MiB of fills into a 20 MiB LLC).

The reason 1.6x sufficed is that a cyclic sequential scan gets essentially
zero reuse under LRU-family replacement once its footprint exceeds the cache:
the warm pass evicts its own early lines before the measured pass reaches
them. For this access pattern 1.6x is as complete a thrash as 3.2x. The
concern was correct in principle and is refuted in fact; the geometry
difference against the archive's section 1 does not create a residency
confound.

### The feared WB/H2 asymmetry does not exist, and runs the other way

The specific worry was that WB, which allocates in the LLC, would collect
hits that H2, which is designed not to allocate, could not — putting the two
arms on unequal footing. The measured HNF hit fractions are the opposite:

| run | HNF accesses | HNF hit fraction |
|---|---|---|
| `wb_4c` | 1,943,697 | 26.84% |
| `h2_4c` | 1,947,298 | **44.32%** |
| `wb_8c` | 4,327,885 | 34.58% |
| `h2_8c` | 4,274,867 | **50.08%** |

H2 has the *higher* home-node hit rate. Neither hit stream is the fact stream.
This HNF is configured `alloc_on_readonce=false`, `alloc_on_readshared=false`,
`alloc_on_readunique=false`, `alloc_on_seq_acc=false` and
`alloc_on_writeback=true`: it allocates only on writeback, so its hits come
from non-stream traffic and from lines the private L2s wrote back, not from
demand reads of the stream. H2's mechanism is separately confirmed engaged —
421,432 and 857,334 fill bypasses against exactly 0 in both WB runs, cutting
fills 44.6% — which reproduces the archive's −45%.

Since both arms read the whole stream from CXL, **WB and H2 are on equal
footing with respect to the measured pass, and no directional bias needs to be
declared.** H2 measuring faster than WB is consequently not an LLC-hit
artifact. It is the latency effect established above: at identical concurrency,
WB pays for its own fill and writeback traffic in home-node transaction
latency (192.8 ns against 155.8 ns at 4c) and loses 20% of its throughput to it.

## The MSHR-implied ceiling, and what H1 is actually about here

48 outstanding misses of 64 B at 203 ns is 15.13 GB/s per core.

| run | per core | fraction of ceiling | per-core lines in flight (of 48) |
|---|---|---|---|
| `wb_4c` | 5.02 GB/s | 33.2% | 15.1 |
| `h2_4c` | 6.28 GB/s | 41.5% | 15.3 |
| `pfoff_4c` | 3.32 GB/s | 21.9% | 7.5 |
| `wb_8c` | 3.87 GB/s | 25.6% | 13.6 |
| `h2_8c` | 5.39 GB/s | 35.6% | 13.8 |
| `pfoff_8c` | 3.37 GB/s | 22.3% | 7.1 |

No arm gets within a factor of 2.4 of the MSHR ceiling; the closest is `h2_4c`
at 41.5%. The MSHR pool is not what binds these runs.

The arms do differ in memory-level parallelism, but not in the pairing that
matters for the H1 claim. **Prefetch-off achieves half the MLP of the other
two** (7.5 against 15.1 lines per core at 4c), which is the prefetcher's whole
contribution and the reason it loses. **WB and H2 are indistinguishable in
MLP** (15.1 against 15.3; 13.6 against 13.8). So in this configuration H2's
advantage over WB is *not* more MLP — it is lower latency at equal MLP.

This is consistent with the archive's section-1 verdict that "non-allocation
preserves prefetch MLP", and it sharpens it: H2 preserves MLP exactly, and
then wins on latency because it is not paying for its own LLC fills. Anywhere
the paper describes H2's multi-core bandwidth advantage as recovered
memory-level parallelism, restate it as preserved MLP plus reduced fill-path
latency. The MLP is preserved, not increased.

## `agg_bw_sum` and the missing barrier

The N instances are separate processes in separate address spaces. Nothing
synchronizes their measured windows, so summing per-instance `bandwidth_gbps`
reports a concurrency that in principle may never have existed. This is a real
weakness of the harness and it should be disclosed wherever the aggregates
appear. It is, however, bounded, and the bound is tight enough to publish.

Three facts constrain the skew. Every instance starts at simulated t = 0.
Every instance runs the same program on the same inputs: `simInsts / N` is
34.887M at 4c and 34.888M at 8c, and per-CPU `numCycles` differ by 0.03–0.48%
within a run. And `run_stream()` (`cxl_join_bench.cpp:1153`) emits its JSON
line and frees the fact buffer immediately after the measured pass, so each
window ends a near-constant offset before that instance's own program end.
Program-end skew therefore bounds window skew:

| run | narrowest window | program-end skew | skew as % of window | guaranteed pairwise overlap |
|---|---|---|---|---|
| `wb_4c` | 1.5874 ms | 0.2472 ms | 15.6% | ≥ 84.4% |
| `h2_4c` | 1.3218 ms | 0.0234 ms | 1.8% | ≥ 98.2% |
| `pfoff_4c` | 2.5120 ms | 0.0828 ms | 3.3% | ≥ 96.7% |
| `wb_8c` | 2.0977 ms | 0.4043 ms | 19.3% | ≥ 80.7% |
| `h2_8c` | 1.5395 ms | 0.1795 ms | 11.7% | ≥ 88.3% |
| `pfoff_8c` | 2.3887 ms | 0.4317 ms | 18.1% | ≥ 81.9% |

In the worst of the six runs any two instances' measured windows overlap for at
least 80.7% of the narrower window; in the best, 98.2%. A corroborating
consistency check: total bytes divided by the single widest instance window —
a denominator that ignores per-instance width variation entirely — gives
94.2–99.3% of `agg_bw_sum`.

**Judgement: `agg_bw_sum` is defensible and publishable, provided the overlap
floor is reported with it.** The honest phrasing is that the aggregate is
taken over windows that overlap for at least 81% of their width, and that
`agg_bw_sum` is therefore biased high by at most about 19% in the worst run
and about 2% in the best. That bias is far smaller than the effects being
claimed (a 25% H2/WB gap at 4c, 39% at 8c) and it is common to all three arms
at a given core count, so it cannot manufacture the ordering.

What would make it airtight, and what any successor campaign should build: a
cross-process barrier immediately before the measured pass — a shared
anonymous mapping with an atomic arrival counter, spinning on
`__builtin_ia32_pause()` and **not** `sched_yield()`, which is the W8.7
two-core CHI queued-spinlock livelock that cost five arms in r6b/r6e — paired
with `m5_dump_reset_stats` around the measured pass so that `stats.txt`
counters are window-scoped rather than whole-program. That single change would
convert the overlap floor from a bound into a guarantee and would also repair
the second metric, below.

A separate limitation of the same shape: `--reps 1` means each instance's
`samples` array has one entry and its reported `cov` is identically 0. **There
is no within-instance variance estimate anywhere in this campaign.** The
1.8–9.99% spreads in the results table are across instances within one run,
not repeat measurements, and there is no seed replication either. Treat every
number here as n = 1 per cell.

## `agg_bw_wall` is unusable and is not published

The second pre-registered metric — total bytes divided by `simSeconds` — comes
out at 0.37–0.80 GB/s. The arithmetic is confirmed from the artifacts:

| run | `simSeconds` | mean measured window | window as % of `simSeconds` | `agg_bw_wall` | shortfall vs `agg_bw_sum` |
|---|---|---|---|---|---|
| `wb_4c` | 0.084133 s | 1.6732 ms | 1.99% | 0.40 GB/s | 50x |
| `h2_4c` | 0.083229 s | 1.3365 ms | 1.61% | 0.40 GB/s | 62x |
| `pfoff_4c` | 0.090423 s | 2.5279 ms | 2.80% | 0.37 GB/s | 36x |
| `wb_8c` | 0.085570 s | 2.1663 ms | 2.53% | 0.78 GB/s | 40x |
| `h2_8c` | 0.083896 s | 1.5557 ms | 1.85% | 0.80 GB/s | 54x |
| `pfoff_8c` | 0.090757 s | 2.4890 ms | 2.74% | 0.74 GB/s | 36x |

The shortfall is **36–62x**, not the 25–50x that had been circulated. The
cause is that `simSeconds` spans the entire simulated program — process
startup, the 8 MiB allocation, `build_table`, `fill_fact` over every tuple,
the streaming declaration, the placement check and the whole warm pass —
while the measured pass is 1.6–2.8% of it. The metric divides the measured
pass's bytes by the whole program's time. It is not a bandwidth of anything,
and its variation across arms tracks total program length rather than
streaming rate.

**Recommendation: drop `agg_bw_wall` as defined.** Do not publish it, do not
report it as a conservative bound, and do not reconcile it against
`agg_bw_sum`. The correct replacement is total bytes divided by the span of
the measured windows, from the first instance entering its measured pass to
the last leaving it — and that span is **not reconstructable from these
artifacts**, because the JSON lines carry only durations and no start
timestamps, and `stats.txt` is whole-program. The best available substitute
today is total bytes over the widest single instance window, which gives
13.11–42.38 GB/s, within 0.7–5.8% of `agg_bw_sum`; report that as
corroboration of `agg_bw_sum`, not as a second metric. A genuine windowed
aggregate requires the barrier and the `m5_dump_reset_stats` bracketing
described above, and should be pre-registered as such if a successor campaign
runs.

This deviates from the pre-registration, which registered two metrics. The
pre-registration is frozen and has not been edited; the deviation is recorded
here. Metric 1 stands and carries the verdict; metric 2 is retired as vacuous.

## Two facts the campaign surfaced incidentally

**`run_stream()` accepts `--threads` and does not apply it (F9).**
`cxl_join_bench.cpp:1153` calls `pin_cpu(cpus[0])` and spawns no threads;
`stream-smoke` is single-threaded by construction. `--threads` is parsed and
echoed into the emitted JSON — every one of the 36 instance lines in this
campaign carries `"threads":1` — but never acted on. This campaign passed
`--threads 1`, so nothing here is affected. It is recorded because it is a
live requested-versus-realized trap: any future `stream-smoke` invocation with
`--threads k > 1` would report `k` in its artifact and run one thread. This is
the same defect class already logged in the pre-registration and is the
mechanical reason the archive's "4-core stream-smoke" could not have been a
threaded run.

**The third arm is prefetch-off, not write-combining.** Both this campaign and
the archive build it as `policy=stream` with the L1D/L2 prefetchers disabled;
the archive labels it "WC (prefetch off)" and the paper body calls it
"prefetch-off", which is accurate. No arm in either campaign uses a
write-combining memory type. `Appendix.tex:568-572` nonetheless derives a
model fidelity caveat from it:

> The model's own WB-versus-WC bandwidth ratio is 1.18x (5.44 vs. 4.60 GB/s,
> `\cref{tab:h1bw}`) against silicon's 3.9x (12.4 vs. 3.2 GB/s ...)

Those two numbers are the archive's section-1 single-core WB and prefetch-off
figures at MSHR=48. **The derivation therefore rests on an arm that is not
WC**, and the appendix's "WB-versus-WC" label is wrong at the source. It is
also not a stable quantity: the same WB-over-third-arm ratio is 1.183x
(archive, 1 core), 1.109x (archive, 4 cores), 1.513x (this campaign, 4 cores)
and 1.149x (this campaign, 8 cores). Restate the caveat as WB versus
prefetch-off, cite one specific artifact for whichever value is used, and note
the spread. The direction of the caveat — that a weaker modelled prefetcher
understates how much bandwidth H2 preserves — survives the relabelling; the
single figure 1.18x does not.

## Corrections to previously circulated numbers

All six `agg_bw_sum` values, the six wall times, and the realized LLC geometry
(4 and 8 slices of 5,242,880 B, so 20 and 40 MiB) reproduce exactly from the
artifacts. Two circulated statements are wrong:

1. **`free(): invalid size` did not occur in all six runs.** Five runs emitted
   it exactly once; `h1bw_mc_wb_8c_20260904` emitted it **zero** times.
   Source: `grep -c 'free(): invalid size' console.log` across the six
   `console.log` files. All six reached `Exiting @ tick` with `exit: 0`.
2. **The `agg_bw_wall` shortfall is 36–62x, not 25–50x.** See the table above.

## Latent defect: heap corruption in the benchmark's teardown

Five of six runs printed `free(): invalid size` once, after the last instance's
measured JSON line and before a clean `Exiting @ tick` with `exit: 0`. The
message originates in glibc's allocator, and the only allocation freed at that
point is `free_bytes(fact, c.fact_bytes, c.huge2m)` at the end of
`run_stream()`. Because it fires strictly after every reported number is
computed and printed, and because all 36 instances reported `status: "ok"`,
it cannot have affected any figure in this document.

It is nonetheless heap corruption, and the fact that `wb_8c` did not reproduce
it makes it **non-deterministic**, which strengthens rather than weakens that
reading — a size-mismatched free would fire every time. Flagged for separate
investigation of `alloc_bytes`/`free_bytes` size bookkeeping under the
`huge2m=false` path. It is not a reason to void or re-run this campaign.

## Recommended bracketing run — NOT LAUNCHED

**Recommendation: yes, run the single-slice bracket, at 4 cores only.** It is
the only measurement that can settle whether the archive's 6–8 GB/s was
saturation, and the campaign above cannot settle it from artifacts alone.

*Why it discriminates.* At `--num-l3caches=1` the home-node transaction-buffer
budget falls from 128 to 32 while the 4-core runs measurably occupied ~60. The
pool becomes binding, and it is the only structure that does become binding
(memory stays at ~500 GB/s, the SNF keeps 256 buffers, capacity is already
irrelevant because the LLC supplies none of the stream). If the archive's
platform line — a single "L3(HNF) 5MiB/20" — describes `--num-l3caches=1`,
this is the configuration it ran.

*What would change in the runner.* `run_h1bw_multicore.sh` hard-codes the
slice count in two places: `--num-l3caches=$n` on the gem5 command line
(line 88) and `"num_l3caches": $n` in the manifest (line 71). Introduce one
parameter, e.g. `L3_SLICES=${L3_SLICES:-$n}` inside `run_arm`, use it in both
places, and include it in the outdir name (`h1bw_mc_${arm}_${n}c_l3x${L3_SLICES}_$STAMP`)
so the two configurations cannot collide in `logs/se_chi`. Nothing else in the
runner needs to move; `--num-dirs=1`, the per-slice `--l3_size=5MiB`, `L1_MSHR`
and `PF_OFF_CORES` all stay frozen, which is what makes it a clean bracket.

The analyzer needs a matching change and will otherwise do the right thing for
the wrong reason: gate G3 is written as `realized LLC == N x 5 MiB`, so a
single-slice run would be marked VOID. That is correct fail-closed behaviour
for an accidental slice-count change and wrong for a deliberate one. Replace
the expectation with `slices x 5 MiB`, where `slices` is counted from
`config.ini`, and add a separate assertion that the realized slice count
matches the run's declared bracket — keeping the F9 protection while allowing
the intended geometry.

*Expected outcome under the hypothesis.* Little's law at the measured
per-transaction latencies puts the 32-buffer ceiling at 10.6 GB/s for WB,
13.2 for H2 and 14.2 for prefetch-off. Those are optimistic in two ways: a
binding buffer pool inflates the very latency in the denominator, and a 5 MiB
LLC raises the miss share above what the 20 MiB configuration saw. Predict
aggregates in roughly the **6–11 GB/s band for WB and H2, overlapping the
archive's 6.23 and 7.73**, with prefetch-off least affected because it needs
only ~30 buffers and might come through near its present 13.27 GB/s. Two
falsifiable consequences worth registering in advance:

- **The 4-core and 8-core aggregates should converge**, both capped by the same
  32 buffers, reproducing the archive's "~6–8 GB/s regardless of cores". If
  they do not converge, the slice count is not the explanation and the archive's
  number is a metric-definition artifact rather than a saturation result.
- **The ordering may invert.** A buffer-capped WB near 8 GB/s against an
  unaffected prefetch-off near 13 GB/s would break WB > prefetch-off. That
  would be an informative negative: it would show the archive's ordering was
  not itself measured in a buffer-capped regime, and it would mean neither
  configuration reproduces the archive's full arm structure — consistent with
  the WB/prefetch-off ratio already failing to transfer (1.513 against 1.109).

*Expected runtime.* The 4-core arms took 1.32–1.38 h each with three arms
running concurrently on mos181; the 8-core arms took 2.95–3.16 h. A 4-core
single-slice bracket of three concurrent arms should be budgeted at **2–4 h**,
longer than the 1.4 h baseline because a buffer-capped configuration burns
more simulated cycles for the same 34.9M instructions per instance. Do not
include 8 cores: the archive has no artifact-backed 8-core row to bracket
against, and adding it roughly triples the cost for no comparison.

This is a recommendation. Nothing was launched, and nothing under
`gem5/logs/` was modified.

## What this licenses, and what it does not

Licensed: the ordering H2 >= WB > prefetch-off in aggregate read bandwidth at
4 and 8 independent single-threaded CXL stream readers, with H2 ahead of WB by
25% at 4 cores and 39% at 8 cores, in the SE CHI model, on a configuration
whose LLC scales with core count. The mechanism is preserved MLP plus reduced
home-node latency, not increased MLP. The H2/WB ratio agrees with the archive
to 0.7%.

Not licensed, and to be stated wherever these numbers appear:

- **Absolute magnitudes are not comparable to the archive's** and are not a
  CXL link measurement. `SimpleMemory` at ~500 GB/s with `latency_var=0`
  models no link. Do not present 20–43 GB/s as CXL bandwidth.
- **This is not a reproduction.** The archive's runner is gone (`S6.6`); the
  magnitude difference cannot be attributed to archive versus harness.
- **The arm structure does not reproduce as a whole** — only H2/WB.
- **n = 1 per cell**, no seed replication, no within-instance repetition.
- **`agg_bw_wall` is retired.** Do not publish it.
- **The third arm is not WC.** Fix `Appendix.tex:568-572` before citing 1.18x.

---

# Addendum 1 — 2026-09-03: the H2 arm here is partially engaged, and the fill reduction is half capacity

Added after `H2_BYPASS_COLLAPSE_2026-09-03.md`. The pre-registration
`H1BW_MULTICORE_PREREG_2026-09-03.md` is frozen and unchanged; the body of
this document above is unchanged. **Nothing above is retracted** — the
licensed ordering claim is unaffected — but two figures in
§"The feared WB/H2 asymmetry does not exist" describe the H2 arm more
strongly than the artifacts support, and this addendum supersedes them.

`prepareRequestRetry()` in `src/mem/ruby/protocol/chi/CHI-cache-funcs.sm`
rebuilds a CHI request after a `RetryAck` and does not copy `isStreaming`,
which `CHI-msg.sm:121` declares `default="false"`. Every retried request
therefore reaches the HNF affirmatively marked non-streaming, the victim line
is allocated into the LLC, and the bypass does not happen. The defect is
confirmed from source and from five independent exact counter identities
across fifteen runs; see the linked document.

## What this changes about the two figures

**"H2's mechanism is separately confirmed engaged"** — engaged, and partially
so. Measured on the population where a bypass is possible at all (clean
evictions arriving at the HNF with the LLC entry invalid), H2 declined
**83.5% at 4 cores and 90.4% at 8 cores**. The prefetch-off arm, which has
**zero** retries at either cache hop, declined **96.0%** in both — that is
this workload's ceiling, the residual 4.0% being clean evictions of lines that
were never tagged. H2's shortfall of 12.5 and 5.6 percentage points is
accounted for by its retried requests: 47,465 and 26,535 retried clean
evictions at the home node, plus 39,361 and 53,292 retried L1D→L2 requests
that leave the L2's `cache_entry.isStreaming` false.

| arm | 4c bypasses | 4c engagement | 8c bypasses | 8c engagement | HNF write-retry fraction |
|---|--:|--:|--:|--:|--:|
| `wb` | 0 | 0.0% (correct) | 0 | 0.0% (correct) | 6.9% / 2.5% |
| `h2` | 421,432 | **83.5%** | 857,334 | **90.4%** | 5.8% / 1.7% |
| `pfoff` | 427,363 | **96.0%** | 850,083 | **96.0%** | 0.0% / 0.0% |

**"cutting fills 44.6% — which reproduces the archive's −45%"** — the 44.6% is
not all capacity. H2 has a second suppression site: `CheckCacheFill`
(`CHI-cache-actions.sm:3541-3542`) also skips the data-array write when the
line is **already resident**, which is an LLC hit and has no footprint effect.
The accounting closes exactly — `write arrivals − fills = bypasses +
suppressed rewrites` — and splits as:

| | avoided LLC allocations | suppressed rewrites of resident lines | total |
|---|--:|--:|--:|
| 4c | 421,432 (**23.3%** of WB's fills) | 390,182 (21.5%) | 44.6% |
| 8c | 857,334 (**21.1%**) | 897,731 (22.1%) | 44.5% |

Only the first column is a capacity claim. The 44.6% should therefore **not**
be reported as reproducing the archive's −45% without establishing that the
archive's figure was measured the same way. Cite 23.3% / 21.1% for footprint
and describe the remainder as an LLC data-array bandwidth and energy effect.

## What this does not change

The defect **removes** bypasses that should have occurred, so it biases H2
against itself. A fully-engaged H2 would suppress more fills, pay less
home-node transaction latency, and measure faster. Everything licensed in
§"What this licenses, and what it does not" stands as written:

- the ordering `H2 >= WB > pfoff` at both core counts;
- the +25% (4c) and +39% (8c) H2-over-WB margins, now readable as **lower
  bounds** on a fully-engaged mechanism;
- the LLC-residency refutation, which turns on CXL bytes delivered and does
  not depend on the bypass counter;
- the higher H2 home-node hit fraction, which is measured directly.

This campaign therefore does **not** need re-running to protect any claim it
makes. Re-running it against a patched binary would move the H2 numbers up,
which is a strengthening and not a correction, and is lower priority than
re-running the slice bracket — whose H2 cell is **void** at 1.8% engagement
and measured the writeback policy with an inert STREAMING tag.

`analyze_h1bw_multicore.py` now gates on engagement rather than on
`bypasses > 0`; all six arms here clear it. Re-running the analyzer reproduces
every number above and still returns `PASS`.

---

# Addendum 2 — 2026-09-03: the LLC supplies roughly half the read stream, and the overlap floors are confirmed

Added after `AGGBW_VALIDITY_2026-09-03.md`, which re-audited this campaign's
headline metric from the same artifacts. The pre-registration
`H1BW_MULTICORE_PREREG_2026-09-03.md` is frozen and unchanged; the body of
this document and Addendum 1 are unchanged. **The verdict, the licensed
ordering and the H2-over-WB ratios all stand** — the ratios are in fact
*strengthened*, because the correction runs against H2. Two claims in
§"LLC residency of the measured pass — the validity threat, refuted" are
withdrawn, and one claim in §"`agg_bw_sum` and the missing barrier" is
confirmed against an attack made on it elsewhere.

## Withdrawn: "The LLC supplied none of the measured pass"

**Current wording:**

> Every arm pulled at least the entire two-pass working set across the CXL
> controller. **The LLC supplied none of the measured pass.** The prefetch-off
> arm is the clean control: with no prefetcher instantiated its CXL reads are
> exactly its demand fetches, and it reads 1.007x and 1.009x the two-pass
> demand — the residual sub-1% being the program's non-stream traffic.

**Replacement:**

> Every arm pulled at least the entire two-pass working set across the CXL
> controller in *aggregate byte count*, but that aggregate is not the measured
> pass and the agreement is a composition coincidence. Decomposed by request
> type at the home node, `pfoff_8c`'s 2,114,960 CXL read lines are
> **1,215,867 `ReadUnique_PoC` write-allocate fetches from the setup phase**
> (`fill_fact` writing 8 MiB of fact plus `build_table`'s 1 MiB table and
> 0.5 MiB key vector, 151,983 lines per instance against a structural
> 155,648) plus **899,092 `ReadShared` read fetches**. Only the second group
> can have served the two read passes, which need 2,097,152 lines. **The CXL
> controller supplied at most 42.9% of the read passes and the cache hierarchy
> supplied the rest.** The 1.007x/1.009x agreement is the near-coincidence of
> `1,215,867 + 899,092` with `2 x 1,048,576`.

The same subtraction, using the cross-arm identity
`h2 ReadShared.I.RU − pfoff ReadShared.I.RU = 1,211,903 ≈ pfoff
ReadUnique_PoC.I.RU = 1,215,867` (0.33%) to establish that the prefetcher
merely reclassifies the setup fetches, gives per-arm CXL-served shares of the
read passes:

| arm | 4 cores | 8 cores |
|---|--:|--:|
| `wb` | <= 77.6% | <= 77.7% |
| `h2` | <= 45.4% | <= 43.6% |
| `pfoff` | <= 42.8% | <= 42.9% |

The mechanism is the opposite of the LRU-reuse argument this section makes.
`fill_fact` **writes** the entire working set immediately before the passes
read it; the dirty lines land in the LLC on eviction from the private L2s; and
because the HNF is `alloc_on_read* = false` and the STREAMING bypass suppresses
90.4–96.0% of the read stream's clean fills, the passes never displace them.
Net dirty residency at end of run is 615,836 lines (`h2_8c`) and 671,940
(`pfoff_8c`) against a 655,360-line LLC — **94% and ~100% full**. The
`ReadShared` hits are correspondingly almost all on dirty lines: 1,985,051
`UD` against 22,050 `UC` in `h2_8c`.

**"The concern was correct in principle and is refuted in fact"** is therefore
withdrawn. The residency confound is real. At a 1.6x
working-set-to-LLC ratio with the working set written immediately before it is
read, this campaign does not isolate far-memory streaming, and **20–43 GB/s
must not be described as CXL or far-memory bandwidth.**

## Withdrawn: "WB and H2 are on equal footing"

**Current wording:**

> Since both arms read the whole stream from CXL, **WB and H2 are on equal
> footing with respect to the measured pass, and no directional bias needs to
> be declared.** H2 measuring faster than WB is consequently not an LLC-hit
> artifact.

**Replacement:**

> WB and H2 are **not** on equal footing with respect to where the measured
> pass's bytes come from: WB sources <= 77.7% of its read stream from the CXL
> controller against H2's <= 43.6%, because WB's clean-eviction fills
> (1,495,749 against H2's 78,955, a factor of 19) evict the LLC-resident dirty
> lines that H2's bypass preserves. H2's higher home-node hit fraction —
> 44.32% against 26.84% at 4c and 50.08% against 34.58% at 8c — **is** stream
> traffic. The claim in this section that "neither hit stream is the fact
> stream" is wrong: the HNF allocates on writeback, and the writebacks in
> question are `fill_fact`'s. A directional bias must therefore be declared:
> **part of H2's measured advantage over WB is an LLC-hit advantage.**

This is the policy under test operating as designed — non-allocation preserves
resident data — so it strengthens rather than weakens the mechanism story. But
the mechanism sentence in §"The MSHR-implied ceiling" must be extended.
"Preserved MLP plus reduced fill-path latency" should read **"preserved MLP,
reduced fill-path latency, and fewer far-memory fetches per useful byte
(1.78x fewer CXL read lines than WB for the same delivered bytes)"**.

## Confirmed: the window-overlap floors

`H1BW_CXLBW_OUTCOME_2026-09-03.md` declared this document's overlap floor
"refuted directly". It is not. Reconstructing each instance's window from
per-CPU `numCycles` (each CPU halts at process exit, so `numCycles x 526 ps`
is that instance's program-end time) minus its own reported `seconds` — an
assignment in which the epilogue length cancels — gives the actual minimum
pairwise overlap:

| run | floor published here | reconstructed actual |
|---|--:|--:|
| `wb_4c` | >= 84.4% | 94.9% |
| `h2_4c` | >= 98.2% | 98.4% |
| `pfoff_4c` | >= 96.7% | 98.6% |
| `wb_8c` | >= 80.7% | 83.7% |
| `h2_8c` | >= 88.3% | 89.3% |
| `pfoff_8c` | >= 81.9% | 92.4% |

**Every floor holds**, in these six and in nine further capped and bracketed
cells, including the `h2_8c` @32.26 GB/s cell cited as the refutation, which
reconstructs to 90.84% against a published floor of 90.7%. The reconstruction
is validated against an independent signal — the order in which instances'
JSON lines reach `console.log` — reproducing it exactly in nine of fifteen
cells with every inversion an adjacent pair separated by 0.11–9.84 us.

This also quantifies what this section could only bound. **`agg_bw_sum` is
high by 2.4–9.8% at 4 cores and 11.8–16.3% at 8** in these six runs, against
the "at most about 19%" estimated here — so the judgement "`agg_bw_sum` is defensible and
publishable, provided the overlap floor is reported with it" is correct and
was, if anything, conservative. Recomputed on the union-span denominator the
H2-over-WB ratio *rises*, from 1.2500 to 1.3411 at 4c and from 1.3917 to
1.4479 at 8c, because WB is the most staggered arm and H2 the least.
**The published +25% and +39% margins are floors.**

## Correction to the barrier prescription

§"`agg_bw_sum` and the missing barrier" prescribes "a shared anonymous mapping
with an atomic arrival counter, spinning on `__builtin_ia32_pause()`".
**That construct cannot work in gem5 SE multi-program mode.** `mmapFunc`
(`src/sim/syscall_emul.hh:2055`) warns that writes to a shared mapping are not
propagated, and `shmget`/`shmat`/`shmdt`/`memfd_create` carry no handler in
`src/arch/x86/linux/syscall_tbl64.cc` and so `fatal()` via
`unimplementedFunc`. The N instances are independent `Process` objects with
independent page tables, not forks, so the arrival counter is invisible across
them and every instance would deadlock. Implementing it is a `src/sim/` change
and needs a rebuild.

The `m5_dump_reset_stats` half of the prescription is sound and needs no
rebuild — 0x40/0x41/0x42 are all already decoded by this binary and 0x40/0x41
are already used by `run_join()`. `AGGBW_WINDOW_PREREG_2026-09-03.md`
registers the bracketing plus `--reps 8` in place of the barrier, and a
host-file rendezvous as an optional arm.

## What this addendum does not change

- the verdict **PASS** and the ordering `H2 >= WB > pfoff` at both core
  counts, which hold on `agg_bw_sum`, on the union-span rate and even on the
  fully-disjoint floor;
- the +25% (4c) and +39% (8c) H2-over-WB margins, now readable as **floors**
  for a second independent reason (Addendum 1 gave the first);
- the realized configuration, the 500 GB/s quantisation finding, the
  contention decomposition, the MSHR-ceiling analysis, or the retirement of
  `agg_bw_wall`;
- the conclusion that this campaign does not need re-running to protect any
  claim it makes. It does not. What needs a new campaign is the residency
  confound above, which is a benchmark-geometry question and not a defect in
  this campaign's execution.

---

# Addendum 3 — 2026-09-03: two remaining repetitions of the withdrawn residency claim

Added after `AGGBW_VALIDITY_2026-09-03.md` and Addendum 2 above. The
pre-registration `H1BW_MULTICORE_PREREG_2026-09-03.md` is frozen and
unchanged; the body of this document and Addenda 1–2 are unchanged.

Addendum 2 withdrew "the LLC supplied none of the measured pass" by quoting
and replacing the passage in §"LLC residency of the measured pass". The claim
is **repeated in two further sections** as a settled premise for a different
argument, and a reader who follows the slice-bracket recommendation reaches it
without passing through Addendum 2. This addendum closes both. It also
records what does and does not follow for the recommendation itself.

## §"But the mechanism is not the one that was hypothesised"

**Current wording:**

> Capacity is not the mechanism (a 5 MiB LLC would simply thrash harder, and
> §"LLC residency" shows the LLC supplies none of the stream anyway), and
> neither is array throughput: the HNF cache is configured `dataArrayBanks=1`
> with `resourceStalls=false`, so bank conflicts are counted but never
> enforced.

**Replacement:**

> Capacity is not the mechanism *for the sublinearity of `wb` and `h2` between
> 4 and 8 cores*, because the LLC scales with the core count in this campaign
> — 4 slices at 4c and 8 at 8c, so 1.6x working set to LLC at both — and the
> parenthetical reason given here is withdrawn: §"LLC residency" is corrected
> by Addendum 2 and the LLC in fact supplies **at least ~57%** of the `h2` and
> `pfoff` read stream — the controller-served share is bounded *above* at
> 43.6% and 42.9%, so the cache-served share is bounded *below* at 56.4% and
> 57.1% (`AGGBW_VALIDITY_2026-09-03.md` §Q1). Array throughput
> is separately not the mechanism: the HNF cache is configured
> `dataArrayBanks=1` with `resourceStalls=false`, so bank conflicts are
> counted but never enforced.

The corrected reasoning reaches the same conclusion about *this* campaign, by
a geometry argument rather than a residency one, and the sublinearity
decomposition in §"Where the contention is" — which is measured from HNF
transaction latencies and SNF stalls — is untouched.

## §"Recommended bracketing run — NOT LAUNCHED"

**Current wording:**

> The pool becomes binding, and it is the only structure that does become
> binding (memory stays at ~500 GB/s, the SNF keeps 256 buffers, capacity is
> already irrelevant because the LLC supplies none of the stream).

**Replacement:**

> The pool becomes binding, and it is the only *fabric* structure that does
> (memory stays at ~500 GB/s and the SNF keeps 256 buffers). **Capacity is
> not irrelevant, and the clause asserting it is withdrawn.** At
> `--num-l3caches=1` the LLC falls from 20 MiB to 5 MiB against a 32 MiB
> 4-core working set, i.e. from 1.6x to 6.4x — and Addendum 2 establishes
> that at 1.6x the LLC was supplying at least 56% of the `h2` read stream from
> `fill_fact`'s resident dirty lines. A 6.4x geometry removes most of that
> residency. **The bracket therefore moves two variables at once**, the
> transaction-buffer budget and the residency, and it cannot attribute its
> result to the buffer pool alone.

### What this costs the recommendation

The bracket is still worth running and its *discriminating* value survives,
because the two variables push the same way — both a binding buffer pool and a
lost ~57% LLC supply reduce the aggregate — so a result in the predicted
**6–11 GB/s band would still overlap the archive's 6.23 and 7.73** and a
result well above the band would still refute the saturation reading. What it
can no longer do is *attribute* the drop to the TBE pool, which was the
mechanistic half of its purpose. Two consequences to register before it runs:

- **The predicted band is now optimistic for a second reason.** The document
  already notes that a binding pool inflates the latency in Little's law and
  that a 5 MiB LLC raises the miss share. The second of those is exactly the
  residency effect, and Addendum 2 quantifies it at no less than 56% of the read
  stream rather than the "above what the 20 MiB configuration saw" the body
  assumed on the strength of the withdrawn claim.
- **Separating the two needs a third cell**, one slice at 5 MiB against a
  working set already several times the LLC — which is the same
  benchmark-geometry change Addendum 2 and
  `AGGBW_VALIDITY_2026-09-03.md` §"What this licenses" name as the highest-
  value follow-up. Running that geometry at both slice counts would separate
  buffer budget from residency in one campaign. It is not pre-registered.

The predicted ordering inversion, the runner and analyzer changes
(`L3_SLICES`, gate G3 on `slices x 5 MiB`), and the 2–4 h budget are
unaffected.

## What this addendum does not change

- the verdict **PASS**, the ordering `H2 >= WB > pfoff` at both core counts,
  and the +25% / +39% H2-over-WB margins, which Addenda 1 and 2 establish as
  floors for two independent reasons;
- the realized configuration and the 500 GB/s quantisation finding;
- the contention decomposition of §"Where the contention is", the MSHR-ceiling
  analysis, or the retirement of `agg_bw_wall`;
- the conclusion that this campaign does not need re-running to protect any
  claim it makes.

---

# Addendum 4 — 2026-09-04: the arm identity is settled, and this document's prescription for the appendix caveat was wrong in its second half

Added after `H1BW_ARM_IDENTITY_2026-09-04.md`, which resolved the `tab:h1bw`
arm question this document raised. The pre-registration
`H1BW_MULTICORE_PREREG_2026-09-03.md` is frozen and unchanged; the body of this
document and Addenda 1-3 are unchanged. **The verdict, the licensed ordering
and every ratio here are unaffected** — this addendum concerns only the paper
edit §"Two facts the campaign surfaced incidentally" prescribed.

## Confirmed, and strengthened: "The third arm is prefetch-off, not write-combining"

This document's finding is correct and can be stated more strongly.
`gem5/src/arch/x86/pagetable_walker.cc:359-390` derives exactly two special
memory types from the PAT bits — `streaming` (slot 6) and `uncacheable` — and
`write-combining` appears nowhere in `src/mem/ruby/`, in `configs/`, or in the
walker. **The model has no write-combining memory type, so no gem5 arm in this
project could ever have been WC**, in this campaign, in the archive, or in any
future one on this binary. The claim is not "this arm happened not to be WC"
but "the arm was not constructible".

The mislabel's origin is also now identified, and it is worth recording
because the same shape will recur: `gem5/scripts/run_se.sh:45` builds the arm
as `--policy stream` with `PF_OFF_CORES=0` while **naming its output directory
`_wc_`**. The archived REPORT inherited `WC` as a column head; `Appendix.tex`
then read that column as a memory type and derived a hardware-fidelity
argument from it. No step between the runner and the appendix re-checked the
arm.

## Withdrawn: the second half of the prescribed appendix fix

**Current wording**, §"Two facts the campaign surfaced incidentally", final
sentences:

> Restate the caveat as WB versus prefetch-off, cite one specific artifact for
> whichever value is used, and note the spread. The direction of the caveat —
> that a weaker modelled prefetcher understates how much bandwidth H2
> preserves — survives the relabelling; the single figure 1.18x does not.

**Replacement:**

> Restate the caveat as WB versus prefetch-off, and do not quote a value at
> all: WB-over-prefetch-off is a *ceiling* that this document separately
> records as not transferring and not quotable to three digits, and it is not
> even a prefetcher measurement, because the third arm carries the STREAMING
> declaration as well as the missing prefetchers, in the opposite direction.
> **The direction of the caveat does *not* survive the relabelling, and this
> prescription is withdrawn.** Three reasons. (i) Silicon's 3.9x is a genuine
> WC *memory type* on **AMD** (`E1_ARM_IDENTITY_AUDIT_2026-08-24.md`), which
> withdraws cacheable allocation and prefetch together, against a model ratio
> that withdraws prefetchers alone on an **Intel** model — the two are not the
> same quantity and their comparison bounds nothing. (ii) The only
> matched-quantity silicon reading available runs the other way:
> `T2_WBWC_OUTCOME_2026-08-24.md` R7 measures all four hardware prefetchers at
> only ~6% of WB stream bandwidth (`B/A` = 0.944 / 0.940, `n=5`), i.e. 1.06x,
> against the model's own matched prefetch contribution of **1.065x at 16
> MSHRs and 1.265x at 48** — so if anything the modelled prefetcher is
> *stronger*. R7 is local DRAM over 2 GB and does not transfer to far memory,
> so it does not establish the reverse either; the direction is simply
> **unknown**. (iii) Even granting a weaker modelled prefetcher, "understates
> how much bandwidth H2 preserves" does not follow: H2's preservation is
> measured against WB (+7.0% at 48 MSHRs, +15.6% at 16), and a stronger
> prefetcher raises both arms. The appendix caveat is now a qualitative
> disclosure with no direction assigned.

## Also worth adding to the spread this document logged

§"The transferable ratio is narrower than 'the ratios agree'" tabulates
WB/prefetch-off as 1.183 (archive 1c), 1.109 (archive 4c), 1.513 (new 4c) and
1.149 (new 8c). **There is a fifth reading, and it is the most damaging one:**
the archive's *16-MSHR* single-core point is `4.24 / 4.60` = **0.922**, i.e.
WB *below* the third arm, in the same two rows the appendix quoted 1.183 from.
The published caveat cited the one of two points in that sweep whose sign its
argument required, in a table whose caption insists the sweep is the claim.
Range across all five artifact-backed readings: **0.92-1.51**.

## What this addendum does not change

- the verdict **PASS** and the ordering `H2 >= WB > pfoff` at both core counts;
- the +25% (4c) and +39% (8c) H2-over-WB margins, or their status as floors;
- any figure, table or mechanism claim in the body or in Addenda 1-3;
- the finding that the third arm is prefetch-off, which is confirmed;
- `H2 / pfoff` as the safest ratio to quote, which this addendum leans on.
