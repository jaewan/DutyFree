# Outcome: AMD cross-process hash-join victim

Dated 2026-08-10. Host: `broker` (`moscxl`, AMD EPYC 9754). This run swaps
the pointer-chase/RocksDB/DuckDB-style victim for the hash-join tenant and
keeps the stream pressure in separate aggressor processes.

## Setup

Victim:

- binary: native `cxl_join_bench`, compiled on `broker` with `-march=native`
- mode: `--mode morsel --no-stream --policy wb`
- placement: victim cpu 0, hot/fact-local buffer on NUMA node 0
- hot table: 8 MiB, intended to be LLC-resident in the 16 MiB CCX-local L3
- logical work: `--fact-bytes 512m --warmups 1 --reps 3`
- metric: `active_cycles_per_access`

Aggressors:

- binaries: `stream_wb` and `stream_wc` from
  `/home/domin/tmp_dutyfree_exp/intel_experiments/bench/aggressor/`
  on `broker`; their `stream_wb.c` and `stream_wc.c` sources were checked
  byte-identical to this repo's `benchmarks/bench/aggressor/` sources
- placement: cpus 1-7, NUMA node 2, one process per CPU
- footprint: 1 GiB per process
- lifetime: fresh launch per loaded arm, 2 s settle, 16 s duration
- resctrl: victim group `hj_v`, aggressor group `hj_a`, both unrestricted
  (`L3:0=ffff`, `SMBA:0=2048`)

Raw data:

- `results/amd/hash_join_cross_process/amd_hash_join_cross_process_n12.jsonl`
- aggregate summary: `results/amd/hash_join_cross_process/summary.json`
- smoke check: `results/amd/hash_join_cross_process/smoke.jsonl`

## Result

| arm | n | cycles/access mean | cycles/access median | sd | tax vs quiescent | self BW mean | MBM BW mean | victim LLC occ mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| quiescent | 12 | 65.74 | 65.72 | 0.60 | 1.000x | n/a | ~0.013 GB/s | 8.23 MiB |
| WB stream aggressors | 12 | 361.92 | 361.19 | 2.06 | 5.505x | 24.34 GB/s | 23.22 GB/s | 0.74 MiB |
| WC stream aggressors | 12 | 361.95 | 361.91 | 0.50 | 5.505x | 24.31 GB/s | 23.11 GB/s | 0.65 MiB |

The separate-process stream pressure produces a large, stable hash-join tenant
tax. The hot table is resident in the quiescent arm by CMT occupancy
(~8.23 MiB for an 8 MiB hot table) and is displaced under both loaded arms
(below 1 MiB mean occupancy).

## Interpretation

This directly tests the suggested structure: hash join as the tenant, stream as
separate aggressor processes on neighboring cores. It confirms that the null
seen in fused same-thread gem5 is not because the hash-join probe itself is
immune to LLC pressure. When stream pressure is supplied externally, the tenant
tax is large and reproducible.

The WC arm is not a no-tax control on this AMD host with this `stream_wc`
binary: it matches WB in both bandwidth and victim tax. Treat this run as a
cross-process tax demonstration, not as evidence that MOVNTDQA/WC semantics
recover the hash-join victim on AMD.
