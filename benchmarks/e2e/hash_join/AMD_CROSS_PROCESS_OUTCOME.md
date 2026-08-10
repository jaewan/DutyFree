# Outcome: AMD cross-process hash-join victim

Dated 2026-08-10; amended 2026-08-11. Host: `broker` (`moscxl`,
AMD EPYC 9754). This run swaps the pointer-chase/RocksDB/DuckDB-style
victim for the hash-join tenant and keeps the stream pressure in separate
aggressor processes.

## 2026-08-11 Amendment

The original 2026-08-10 run remains useful as a tax demonstration, but its
`WC` arm is invalid as a control:

- `stream_wc.c` is MOVNTDQA-on-WB memory; on AMD it behaved like WB, not a
  true WC/non-coherent condition.
- WB and `stream_wc` matched almost exactly: 361.92 vs 361.95 cycles/access.
- The loaded victim call could overrun the fixed 16 s aggressor lifetime
  (`wall_dur_s` 16.49 s in WB rep 1), contaminating the accumulated metric.
- The runner documented `--fact-bytes 512m`, but `--no-stream` intentionally
  caps the resident local fact buffer to 1 MiB; the records correctly show
  `actual_fact_bytes=1048576`.

The repaired 2026-08-11 run supersedes the old WC comparison. It uses the AMD
`aggressor -m wb_load` and `amd_flushbehind_aggressor -f 256` controls on
clean-CCX1 placement (`victim=cpu8`, aggressors `cpus9-15`) and terminates the
aggressor only after the victim exits, so the aggressor window strictly covers
the victim window.

True-WC rerun status: blocked. `/dev/cxl_wc` was absent; rebuilding
`cxl_memtype.ko` succeeded, but the kernel refused to offline even one CXL
memory block, so the device could not be recreated safely. The historical
clean-CCX1 WC arm remains 0.996x, but no new hash-join true-WC arm was
collected in this amendment.

## Setup

Victim:

- binary: native `cxl_join_bench`, compiled on `broker` with `-march=native`
- mode: `--mode morsel --no-stream --policy wb`
- original placement: victim cpu 0, hot/fact-local buffer on NUMA node 0
- repaired placement: victim cpu 8, hot/fact-local buffer on NUMA node 0
- hot table: 8 MiB, intended to be LLC-resident in the 16 MiB CCX-local L3
- logical work: `--fact-bytes 512m --warmups 1 --reps 3`
  (`--no-stream` caps the actual resident fact buffer to 1 MiB)
- metric: `active_cycles_per_access`

Original 2026-08-10 aggressors:

- binaries: `stream_wb` and `stream_wc` from
  `/home/domin/tmp_dutyfree_exp/intel_experiments/bench/aggressor/`
  on `broker`; their `stream_wb.c` and `stream_wc.c` sources were checked
  byte-identical to this repo's `benchmarks/bench/aggressor/` sources
- placement: cpus 1-7, NUMA node 2, one process per CPU
- footprint: 1 GiB per process
- lifetime: fresh launch per loaded arm, 2 s settle, 16 s duration
- resctrl: victim group `hj_v`, aggressor group `hj_a`, both unrestricted
  (`L3:0=ffff`, `SMBA:0=2048`)

Repaired 2026-08-11 aggressors:

- binaries: `/home/domin/tmp_dutyfree_exp/bin/aggressor -m wb_load` and
  `/home/domin/tmp_dutyfree_exp/bin/amd_flushbehind_aggressor -f 256`
- placement: cpus 9-15, NUMA node 2, one process with seven pinned threads
- footprint: 64 MiB per thread
- lifetime: fresh launch per loaded arm; terminated after victim exit
- resctrl: victim group `hj_v`, aggressor group `hj_a`, both unrestricted

Raw data:

- `results/amd/hash_join_cross_process/amd_hash_join_cross_process_n12.jsonl`
- aggregate summary: `results/amd/hash_join_cross_process/summary.json`
- smoke check: `results/amd/hash_join_cross_process/smoke.jsonl`
- repaired flush run:
  `results/amd/hash_join_cross_process/amd_hash_join_cross_process_flush_n12.jsonl`
- repaired summary:
  `results/amd/hash_join_cross_process/summary_flush.json`
- repaired cluster summary:
  `results/amd/hash_join_cross_process/cluster_summary_flush.json`
- repaired smoke:
  `results/amd/hash_join_cross_process/smoke_v2b.jsonl`
- smaps diagnostic run:
  `results/amd/hash_join_cross_process/amd_hash_join_cross_process_smaps_n12.jsonl`
- smaps diagnostic summary:
  `results/amd/hash_join_cross_process/smaps_cluster_summary.json`
- frequency-check run:
  `results/amd/hash_join_cross_process/amd_hash_join_cross_process_freq_n12.jsonl`
- frequency-check summary:
  `results/amd/hash_join_cross_process/freq_summary.json`
- pagemap + frequency run:
  `results/amd/hash_join_cross_process/amd_hash_join_cross_process_pagemap_n12.jsonl`
- pagemap + frequency summary:
  `results/amd/hash_join_cross_process/pagemap_summary.json`

## Original Result, Superseded Control

| arm | n | cycles/access mean | cycles/access median | sd | tax vs quiescent | self BW mean | MBM BW mean | victim LLC occ mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| quiescent | 12 | 65.74 | 65.72 | 0.60 | 1.000x | n/a | ~0.013 GB/s | 8.23 MiB |
| WB stream aggressors | 12 | 361.92 | 361.19 | 2.06 | 5.505x | 24.34 GB/s | 23.22 GB/s | 0.74 MiB |
| WC stream aggressors | 12 | 361.95 | 361.91 | 0.50 | 5.505x | 24.31 GB/s | 23.11 GB/s | 0.65 MiB |

The separate-process stream pressure produces a large, stable hash-join tenant
tax. The hot table is resident in the quiescent arm by CMT occupancy
(~8.23 MiB for an 8 MiB hot table) and is displaced under both loaded arms
(below 1 MiB mean occupancy).

## Repaired Flush-Behind Result

The loaded arms are bimodal. The pooled means are useful for rough orientation
but do not correspond to a single operating point on this machine.

| arm | n | cycles/access mean | cycles/access median | sd | tax mean | tax median | self BW mean | MBM BW mean | victim LLC occ mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| quiescent | 12 | 65.56 | 65.71 | 0.70 | 1.000x | 1.000x | n/a | ~0.0004 GB/s | 7.84 MiB |
| WB CXL aggressor | 12 | 438.43 | 480.41 | 70.72 | 6.688x | 7.311x | 24.71 GB/s | 24.31 GB/s | 0.72 MiB |
| flush_d256kb | 12 | 147.28 | 161.62 | 18.58 | 2.247x | 2.460x | 16.97 GB/s | 32.06 GB/s | 7.99 MiB |

Per-mode split:

| arm | cluster | n | cycles/access mean | tax vs quiescent mean | victim LLC occ mean | wall mean |
|---|---|---:|---:|---:|---:|---:|
| WB | low | 3 | 322.66 | 4.92x | 1.97 MiB | 14.46 s |
| WB | high | 9 | 477.02 | 7.28x | 0.31 MiB | 21.36 s |
| flush_d256kb | low | 5 | 126.67 | 1.93x | 8.10 MiB | 5.69 s |
| flush_d256kb | high | 7 | 161.99 | 2.47x | 7.91 MiB | 7.27 s |

Recovery is stable across the split:

| mode | recovery of WB tax by flush_d256kb |
|---|---:|
| low | 76.2% |
| high | 76.6% |

The repaired run keeps the core result and fixes the control structure:
external WB stream pressure gives the hash-join tenant a large tax, while
flush-behind recovers about 76.5% of that tax and preserves hot-table
occupancy near the 8 MiB resident set. The mixed WB mean should not be used as
a single headline operating point.

## Interpretation

This directly tests the suggested structure: hash join as the tenant, stream as
separate aggressor processes on neighboring cores. It confirms that the null
seen in fused same-thread gem5 is not because the hash-join probe itself is
immune to LLC pressure. When stream pressure is supplied externally, the tenant
tax is large and reproducible.

The 2026-08-10 WC arm is not a no-tax control on this AMD host with the
Intel `stream_wc` binary. The repaired result should be read against the
flush-behind rung and the historical clean-CCX1 true-WC result, not against
MOVNTDQA-on-WB.

The leading hypothesis for the loaded-arm bimodality is per-process variation
in hot-table backing/index spread, for example THP success versus 4 KiB fallback.
The repaired runner now drops the first CMT sample for future runs; the
existing repaired raw retained only aggregate CMT statistics, so the spurious
initial zero samples cannot be de-biased post hoc without rerunning.

## Smaps Diagnostic

A follow-up n=12 diagnostic added victim-side table backing fields and reran
the same quiescent/WB/flush_d256kb arms with first-sample CMT dropping enabled.
The two loaded modes reproduced, and the initial-zero CMT artifact disappeared.

The THP-success-versus-4 KiB-fallback hypothesis is refuted for the current
vector-backed hot table:

| cluster | table AnonHugePages | KernelPageSize | MMUPageSize |
|---|---:|---:|---:|
| WB low | 0 KiB | 4 KiB | 4 KiB |
| WB high | 0 KiB | 4 KiB | 4 KiB |
| flush low | 0 KiB | 4 KiB | 4 KiB |
| flush high | 0 KiB | 4 KiB | 4 KiB |

The bimodality is still real and load-only, but it is not explained by THP
success versus fallback in this allocation path. The next placement-control
test, if needed, is to back the hot table explicitly rather than relying on
`std::vector` heap placement.

## Frequency Check

A narrow n=12 follow-up wrapped the loaded victim process on cpu8 with
`perf stat -C 8 -e cycles,ref-cycles`. It refutes DVFS/clock-rate as the
loaded-arm mode split:

| cluster | n | cycles/access mean | cycles/ref-cycles mean | victim LLC occ mean |
|---|---:|---:|---:|---:|
| WB low | 8 | 322.08 | 1.00000004 | 2.01 MiB |
| WB high | 4 | 444.66 | 0.99999969 | 0.57 MiB |
| flush low | 7 | 125.06 | 0.99999976 | 8.33 MiB |
| flush high | 5 | 161.03 | 0.99999979 | 7.97 MiB |

WB high/low cycles/access differs by 1.381x, while cycles/ref-cycles differs
by less than one part per million in the opposite direction. Flush high/low
cycles/access differs by 1.288x with no meaningful frequency movement. The
clock component of the bimodality is therefore effectively zero; the remaining
explanation is memory/cache placement or retention state under load.

## Pagemap Placement Check

A second n=12 follow-up dumped `/proc/<victim>/pagemap` for the hot table in
each rep, while also collecting cpu8 `cycles,ref-cycles` for quiescent and both
loaded arms. The victim emits a `HOT_TABLE` line with pid/base/bytes before the
measured loop; the runner samples pagemap immediately, stores the raw PFN list,
and derives LLC-set and low-physical-bit interleave proxies from those PFNs.

The run reproduced the loaded split, but the static PFN/set placement features
do not predict it:

| cluster | n | cycles/access mean | cycles/ref-cycles mean | victim LLC occ mean | LLC sets covered | set-count COV | max set lines | AnonHugePages |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| quiescent | 12 | 64.45 | 1.00000015 | 8.18 MiB | 16384 | 0.337 | 16.4 | 0 KiB |
| WB low | 8 | 323.04 | 0.99999983 | 1.96 MiB | 16384 | 0.352 | 16.4 | 0 KiB |
| WB high | 4 | 455.06 | 1.00000024 | 0.46 MiB | 16368 | 0.356 | 17.0 | 0 KiB |
| flush low | 9 | 123.96 | 0.99999962 | 8.27 MiB | 16384 | 0.353 | 17.3 | 0 KiB |
| flush high | 3 | 160.87 | 0.99999974 | 8.05 MiB | 16363 | 0.351 | 16.7 | 0 KiB |

All records are 4 KiB-backed; `AnonHugePages` is zero throughout. The hot-table
PFNs cover the full 16,384-set LLC index space in every low/quiescent record
and almost all sets in the high records. PFN mod-16/mod-64/mod-512 and
2 MiB-frame mod-32 histograms overlap across high and low states; these are
only userspace physical-bit proxies for channel/CCD interleave, but they give
no separable signature. Occupancy remains the only strong correlate of the
state.

This closes the two cheap explanations. DVFS is refuted by cycles/ref-cycles,
and static hot-table PFN/index placement, as visible from pagemap at measurement
start, does not explain the mode. The remaining mechanism is a load-dependent
retention state or a lower-level physical-address hash effect not captured by
these simple PFN-derived proxies. Hugetlbfs pinning may still be useful as a
control, but the current evidence does not justify claiming page placement as
the mechanism.
