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
- repaired smoke:
  `results/amd/hash_join_cross_process/smoke_v2b.jsonl`

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

| arm | n | cycles/access mean | cycles/access median | sd | tax mean | tax median | self BW mean | MBM BW mean | victim LLC occ mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| quiescent | 12 | 65.56 | 65.71 | 0.70 | 1.000x | 1.000x | n/a | ~0.0004 GB/s | 7.84 MiB |
| WB CXL aggressor | 12 | 438.43 | 480.41 | 70.72 | 6.688x | 7.311x | 24.71 GB/s | 24.31 GB/s | 0.72 MiB |
| flush_d256kb | 12 | 147.28 | 161.62 | 18.58 | 2.247x | 2.460x | 16.97 GB/s | 32.06 GB/s | 7.99 MiB |

The repaired run keeps the core result and fixes the control structure:
external WB stream pressure gives the hash-join tenant a large tax, while
flush-behind greatly reduces the tax and preserves hot-table occupancy near
the 8 MiB resident set. WB is bimodal in this run, so medians are the safer
summary for the loaded WB severity.

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
