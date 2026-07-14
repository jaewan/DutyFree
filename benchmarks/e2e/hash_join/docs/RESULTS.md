# RESULTS
## SUMMARY
- Node-2 WB stream bandwidth: 6.16991533 GB/s; local node-0: 7.97389109 GB/s.
- Row-C 53% LLC `wb`: 17.8485909 MT/s, probe cycles/access 24.8593731, stream BW 0.285577454 GB/s.
- Row-C 53% LLC `nta`: 17.1735929 MT/s, probe cycles/access 25.0389843, stream BW 0.274777486 GB/s.
- Best PREFETCHNTA LLC-load-miss reduction vs WB: 45.6% at pf-distance 256; BW 4.6877687 GB/s.
- Deferred: `cat` policy and CMT occupancy pending resctrl group creation privilege.

## Findings
- node-2 WB read 6.17 GB/s outside 15.8±20% anchor
- hot_probe:2MB_t1 was rerun after fixing per-probe atomic scheduling; original record remains earlier in artifacts/results.jsonl, latest record is used in docs/RESULTS.md

## Anchor Table
| Check | Result | Status |
|---|---:|---|
| Node-2 WB read 15.8 GB/s ±20% | 6.170 GB/s | OUT_OF_BAND |
| Local read higher than node-2 | local 7.974, node2 6.170 GB/s | PASS |
| L2 negative control 2MB | wb cycles/access 42.8856506, nta 42.8658752 | MEASURED |

## PREFETCHNTA Sweep
| Policy | pf-distance | BW GB/s | LLC-loads | LLC-load-misses | remote L3 miss retired |
|---|---:|---:|---:|---:|---:|
| wb | 0 | 6.30286216 | 154426620 | 49807 | 3752 |
| nta | 0 | 4.73641483 | 2308423 | 56062 | 4843 |
| nta | 1 | 4.67194323 | 1581944 | 43170 | 3191 |
| nta | 2 | 4.63760865 | 1576555 | 39278 | 3491 |
| nta | 4 | 4.55505613 | 1596582 | 42773 | 4662 |
| nta | 8 | 2.02190182 | 547859 | 37121 | 864 |
| nta | 16 | 2.47522818 | 768655 | 33912 | 495 |
| nta | 32 | 3.44350817 | 876980 | 33438 | 536 |
| nta | 64 | 4.57917207 | 793326 | 31476 | 450 |
| nta | 128 | 4.72665055 | 744525 | 30139 | 369 |
| nta | 256 | 4.6877687 | 766987 | 27106 | 678 |
| nta | 512 | 4.74099637 | 804385 | 42300 | 428 |

## Row-C Single Join
| Hot size | Policy | MT/s | Stream BW GB/s | Probe cyc/access | CoV | LLC misses |
|---|---|---:|---:|---:|---:|---:|
| 2MB | wb | 24.3979166 | 0.390366666 | 42.8856506 | 0.00379880352 | 929944 |
| 2MB | nta | 23.8768959 | 0.382030334 | 42.8658752 | 0.00299654962 | 215297 |
| 25pct | wb | 19.335128 | 0.309362048 | 30.1560268 | 0.0082677394 | 2755169 |
| 25pct | nta | 18.5710485 | 0.297136775 | 30.2882938 | 0.00939706784 | 584592 |
| 53pct | wb | 17.8485909 | 0.285577454 | 24.8593731 | 0.00834711059 | 27071205 |
| 53pct | nta | 17.1735929 | 0.274777486 | 25.0389843 | 0.00806296285 | 18571847 |
| 100pct | wb | 15.3380279 | 0.245408447 | 31.5146618 | 0.0101391248 | 1662835374 |
| 100pct | nta | 15.3066623 | 0.244906596 | 32.5855789 | 0.00294940175 | 1376727262 |

## Morsel WB
| Hot size | Threads | Join MT/s | Stream BW GB/s | Hot-probe Mops/s | Slowdown proxy | CoV |
|---|---:|---:|---:|---:|---:|---:|
| 2MB | 1 | 24.8540169 | 0.397664271 | 44.8018904 | 1.8026015907311947 | 0.00358129633 |
| 2MB | 2 | 51.2595252 | 0.820152403 | 89.8877079 | 1.7535805794002945 | 0.00194879658 |
| 2MB | 4 | 102.503523 | 1.64005637 | 180.021344 | 1.7562454316814067 | 0.00420681152 |
| 2MB | 8 | 204.016099 | 3.26425758 | 358.299886 | 1.7562333941107267 | 0.00714778502 |
| 2MB | 16 | 403.943549 | 6.46309678 | 709.833642 | 1.757259507565499 | 0.00589150336 |
| 25pct | 1 | 19.8569602 | 0.317711362 | 36.3960104 | 1.8329094702017885 | 0.00339690668 |
| 25pct | 2 | 39.9929097 | 0.639886554 | 72.2435189 | 1.80640817189653 | 0.00345150236 |
| 25pct | 4 | 79.7543138 | 1.27606902 | 142.214747 | 1.7831605617801702 | 0.00526266616 |
| 25pct | 8 | 158.485727 | 2.53577164 | 270.814319 | 1.7087615656392832 | 0.00584877882 |
| 25pct | 16 | 315.0462 | 5.0407392 | 493.110091 | 1.5651992977537899 | 0.00802793908 |
| 53pct | 1 | 18.4309207 | 0.294894731 | 34.6639149 | 1.8807478727853242 | 0.00439012671 |
| 53pct | 2 | 36.933988 | 0.590943807 | 68.6888742 | 1.8597740975060695 | 0.00635772637 |
| 53pct | 4 | 73.3522655 | 1.17363625 | 134.190242 | 1.8293946490309834 | 0.0106364501 |
| 53pct | 8 | 145.933417 | 2.33493468 | 250.477204 | 1.7163800392613298 | 0.00781943862 |
| 53pct | 16 | 291.673303 | 4.66677286 | 443.181703 | 1.5194455524097112 | 0.0112489632 |
| 100pct | 1 | 14.8695446 | 0.237912714 | 26.6386721 | 1.7914921281449334 | 0.00355121147 |
| 100pct | 2 | 29.7086945 | 0.475339111 | 52.8191493 | 1.7779020649998605 | 0.00544276426 |
| 100pct | 4 | 59.9228009 | 0.958764814 | 102.880126 | 1.716877790337067 | 0.00557871438 |
| 100pct | 8 | 118.637675 | 1.89820281 | 193.475025 | 1.6308059391757297 | 0.00745283296 |
| 100pct | 16 | 237.650021 | 3.80240033 | 344.078302 | 1.4478361943843463 | 0.0068782131 |

## Reproduction Commands

```bash
make clean && make native test
./scripts/run_all.py
make gem5
./build/cxl_join_bench.gem5 --mode single --policy wb --fact-bytes 16m --hot-bytes 2m --reps 1 --warmups 0
```

For a larger fact region, set `BENCH_FACT_BYTES`, for example:

```bash
BENCH_FACT_BYTES=4g BENCH_TIMEOUT=1200 ./scripts/run_all.py
```

## Config Dump
- Fact bytes for unattended run: 1g
- Reps: 30; warmups: 3; timeout: 600s
- CPU list: 0-15; SMT siblings avoided by using CPUs 0-15 for max 16 workers.
- Fact region bounds are present per run in `artifacts/results.jsonl` as `fact_base` and `fact_end`.
- `cat`/CMT: deferred because `/sys/fs/resctrl` group creation returned permission denied.

## Platform-Measured CXL Anchors, 2026-07-02

The original 15.8 GB/s single-core CXL anchor is superseded for this host. Local DRAM reaches 16.4 GB/s with the repaired loop, zero timed faults, and 2 MB pages, while node-2 CXL is stable around 8.8-9.4 GB/s. This indicates the prior 6.17 GB/s result was a benchmark bug, but this CXL device's single-core ceiling is lower than the paper's Samsung Type-3 platform.

### Step 1 Characterization

| Node-2 workers | CPUs | Aggregate GB/s | Per-core GB/s |
|---:|---|---:|---:|
| 1 | 32 | 9.405 | 9.405 |
| 2 | 32,33 | 16.722 | 8.361 |
| 4 | 32,33,34,35 | 23.069 | 5.767 |
| 8 | 32,33,34,35,36,37,38,39 | 23.643 | 2.955 |
| 16 | 32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47 | 23.295 | 1.456 |

Measured aggregate CXL ceiling: **23.643 GB/s**.

Pointer-chase latency, 1 GiB region, 2 MB pages, CPU 48:

| Node | Latency ns | Page size | Placement |
|---:|---:|---|---|
| 2 | 61.12 | 2048 KiB | sampled_pages=4096 node2=4096 |
| 0 | 49.57 | 2048 KiB | sampled_pages=4096 node0=4096 |

Little's-Law check using 64 B cache lines:

- Measured single-core CXL BW 9.405 GB/s at 61.12 ns implies about **9.0 outstanding cache lines**.
- Reaching 15.8 GB/s at the same latency would require about **15.1 outstanding cache lines**.
- The multi-core curve saturates near 23.643 GB/s, so the single-core point is consistent with an MLP-limited CXL path rather than a placement failure.

### Step 2 Bounded MLP Attempt

| Variant | BW GB/s | Median GB/s | CoV |
|---|---:|---:|---:|
| Baseline 4 streams | 8.801 | 8.803 | 0.0011 |
| Best prefetcht0 (t0_pf64) | 8.874 | 8.875 | 0.0006 |
| 8 independent streams | 7.298 | 7.298 | 0.0002 |

`prefetcht0` did not materially improve single-core CXL bandwidth; 8 streams made it worse. The accepted platform anchors for this host are therefore:

- Single-core node-2 WB stream anchor: **9.405 GB/s**.
- Aggregate node-2 WB stream ceiling: **23.643 GB/s**.

Gate A is recalibrated as PASSED for this machine because local DRAM is notably higher than CXL, timed-loop faults are zero, 2 MB pages are confirmed, and the single-core result lies on the measured scaling curve for this CXL device.

## Pre-Gate-B Verification, 2026-07-02

MLC is not installed (`mlc: command not found`), so latency was re-measured with the benchmark pointer-chase mode using a deterministic Feistel-randomized dependent chain over a 2 GiB buffer, 2 MB pages, CPU 48.

| Node | Buffer | Chain | Latency ns | Page size | Placement |
|---:|---:|---|---:|---:|---|
| 2 | 2 GiB | randomized dependent | 199.16 | 2048 KiB | sampled_pages=4096 node2=4096 |
| 0 | 2 GiB | randomized dependent | 111.49 | 2048 KiB | sampled_pages=4096 node0=4096 |

The earlier 61 ns node-2 latency was understated because it used a regular stride pattern that hardware prefetch could help. The randomized dependent chain puts node 2 in the expected real-CXL latency range.

### Node-2 Physical Identity

`cxl list` reports a CXL root (`root0`, provider `ACPI.CXL`), endpoint `endpoint1`, memdev `mem0` on PCI host `0000:27:00.0`, and committed volatile RAM `region0`:

- `region0` resource: `0x10080000000`
- `region0` end: `0x14080000000`
- `region0` size: `274877906944` bytes
- interleave ways: `1`
- interleave granularity: `4096`
- mapping: `mem0` / `decoder1.0`

Node-2 memory blocks have phys_index `0x201-0x280`; with memory block size `0x80000000`, node 2 spans exactly `0x10080000000-0x14080000000`, matching `region0`. `numactl -H` shows node 2 has 0 CPUs and 253888 MB memory, with node distances row `14 24 10`.

Plain statement: **node 2 is a real CXL.mem-backed memory-only NUMA node**, not merely an anonymous low-latency memory node. `dmesg` access is blocked for this user (`Operation not permitted`), and deeper `cxl list -vvv` media-error queries hit `/dev/cxl/mem0` permission denials, but the visible CXL region and physical memory range match is decisive for this benchmark.

Paused here before row-C join overhead work and Gate B, per instruction.

## Gate B Row-C Interference, 2026-07-02

The row-C join was rerun after fixing the hot table entry layout from 24 bytes to the required 16 bytes (`key,payload`, with `key=0` as empty). This reduced inflated working-set size and made the reported hot-size sweep meaningful. The join remains probe-gated, which is expected: full-BW CXL is 9.4 GB/s, but a one-probe-per-tuple join can only stream about 16 B per completed probe.

### Per-Tuple Breakdown

Measured with node-2 fact stream, 1 GiB fact region, 2 MB pages, CPU 48. Cycles are TSC cycles per tuple.

| Hot set | Stream load | Hash | Probe | Aggregate | Full join | Residual full-probe |
|---|---:|---:|---:|---:|---:|---:|
| 53pct | 4.40 | 4.46 | 88.09 | 3.94 | 86.66 | -1.42 |
| 100pct | 4.25 | 4.30 | 107.94 | 4.03 | 103.75 | -4.19 |
| 125pct | 4.25 | 4.30 | 108.40 | 4.03 | 106.11 | -2.29 |

Interpretation: the earlier apparent ~80 cycles/tuple non-probe overhead was an artifact of comparing full join throughput to an unrepresentative sequential-key probe microsection. With randomized fact keys, probe cost is the dominant cost: about 88 cycles at 53% LLC and about 108 cycles at 100-125% LLC. Stream-load, hash, and aggregate micro-loops are each about 4-4.5 cycles/tuple.

### Quiescent vs WB-Stream Probe Workload

Mandatory Gate-B comparison. `quiescent` uses the same generated fact-key stream allocated on node 0; `WB-stream` uses the fact-key stream allocated on CXL node 2. MPKI is LLC-load-misses per thousand tuples from `perf stat` over the probe workload.

| Hot set | Condition | Probe MT/s | Cycles/access | Probe MPKI | Offcore L3-miss demand reads |
|---|---|---:|---:|---:|---:|
| 53pct | quiescent | 21.69 | 87.61 | 108.25 | 58985402 |
| 53pct | WB-stream | 21.32 | 89.14 | 105.34 | 57842788 |
| 100pct | quiescent | 17.86 | 106.38 | 1162.91 | 626673578 |
| 100pct | WB-stream | 17.66 | 107.60 | 1106.55 | 596858948 |
| 125pct | quiescent | 17.65 | 107.65 | 1110.34 | 598506410 |
| 125pct | WB-stream | 17.64 | 107.69 | 1155.95 | 623773476 |

Gate-B finding: the WB CXL fact stream does **not** materially worsen same-thread probe cost in this configuration. At 53% LLC, cycles/access rises only from 87.61 to 89.14 and MPKI is slightly lower. At 100% LLC, cycles/access rises from 106.38 to 107.60 and MPKI is lower. At 125% LLC, cycles/access is essentially unchanged and MPKI is higher. This is a small/null row-C interference result on this host, not a tuning failure.

Investigation notes: the hot table is explicitly warmed before measurements, fact placement is asserted on node 2 for WB-stream runs, and stream/L3 activity is present. Full join WB offcore L3-miss demand reads were 49.8M at 53%, 564.6M at 100%, and 561.6M at 125%, so the stream/probe workload is reaching the uncore; the same-core stream rate is simply probe-gated at roughly 0.29-0.36 GB/s.

### WB vs NTA Row-C Join

| Hot set | Policy | Join MT/s | Stream BW GB/s | LLC miss / kTuple | Offcore L3-miss demand reads |
|---|---|---:|---:|---:|---:|
| 53pct | wb | 22.25 | 0.356 | 90.08 | 49826446 |
| 53pct | nta | 19.85 | 0.318 | 66.14 | 36074738 |
| 100pct | wb | 18.36 | 0.294 | 1043.64 | 564576337 |
| 100pct | nta | 16.40 | 0.262 | 954.02 | 515781313 |
| 125pct | wb | 18.37 | 0.294 | 1038.14 | 561621234 |
| 125pct | nta | 16.32 | 0.261 | 946.37 | 511519368 |

`nta` reduces LLC/offcore activity but also reduces join throughput and stream bandwidth. Since Gate B did not establish a strong quiescent-vs-WB degradation, the wb-vs-nta row-C gap should be interpreted as a small/probe-gated effect with the expected bandwidth confound, not as evidence of strong hot-set protection.

### Full-Bandwidth PREFETCHNTA Stream Finding

Pure stream microbench, 4 GiB fact region on node 2, 2 MB pages, CPU 48, 4 independent streams. Counts are absolute `perf` counts for the run; this reports L3/offcore fill behavior side by side with bandwidth rather than relying on a load-miss ratio.

| Policy | pf distance | BW GB/s | LLC loads | LLC misses | Offcore L3-miss demand reads | SW NTA prefetches |
|---|---:|---:|---:|---:|---:|---:|
| wb | 0 | 8.844 | 585575292 | 97351 | 583751286 | 0 |
| nta | 16 | 3.966 | 250721637 | 81570 | 244463767 | 469738316 |
| nta | 32 | 3.331 | 232153257 | 70852 | 219223037 | 469489386 |
| nta | 64 | 3.331 | 294832953 | 84117 | 278842124 | 469845521 |
| nta | 128 | 3.252 | 216980584 | 83556 | 205858164 | 469945562 |
| nta | 256 | 3.208 | 127245829 | 90541 | 114625287 | 470154820 |
| nta | 512 | 3.285 | 121912244 | 84045 | 110023984 | 469873026 |

Best absolute offcore L3-miss demand-read reduction was 81.2% at pf-distance 512, but bandwidth fell from 8.844 GB/s (`wb`) to 3.285 GB/s (`nta`). This is the required confound: NTA reduces fill pressure while also lowering stream bandwidth.

Raw records are appended in `artifacts/results.jsonl`; per-run logs are under `artifacts/logs/`.

## Morsel Interference Sweep, 2026-07-02

### Probe-Cost vs Core-Count Table

One worker per physical core, SMT siblings avoided. CPUs are listed in the mapping column. `QUIESCENT` repeatedly probes the shared hot table with no CXL fact stream. `LOADED` runs morsel scan+probe with the fact region on CXL node 2. MPKI is LLC-load-misses per thousand tuples/probes from `perf stat`.

| Hot set | Cores | Condition | Active cyc/access | MPKI | Aggregate stream BW GB/s | Throughput MT/s | CPU mapping |
|---|---:|---|---:|---:|---:|---:|---|
| 53pct | 1 | QUIESCENT | 57.59 | 55.30 | - | 32.98 | 32 |
| 53pct | 1 | LOADED | 89.08 | 70.49 | 0.341195438 | 21.32 | 32 |
| 53pct | 2 | QUIESCENT | 55.51 | 51.31 | - | 67.52 | 32,33 |
| 53pct | 2 | LOADED | 87.24 | 61.99 | 0.693366428 | 43.34 | 32,33 |
| 53pct | 4 | QUIESCENT | 55.55 | 45.04 | - | 130.09 | 32,33,34,35 |
| 53pct | 4 | LOADED | 87.98 | 69.90 | 1.36404209 | 85.25 | 32,33,34,35 |
| 53pct | 8 | QUIESCENT | 57.41 | 51.40 | - | 233.48 | 32,33,34,35,36,37,38,39 |
| 53pct | 8 | LOADED | 86.96 | 46.47 | 2.74272895 | 171.42 | 32,33,34,35,36,37,38,39 |
| 53pct | 16 | QUIESCENT | 56.43 | 32.53 | - | 416.21 | 32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47 |
| 53pct | 16 | LOADED | 87.05 | 71.41 | 5.42211841 | 338.88 | 32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47 |
| 100pct | 1 | QUIESCENT | 70.04 | 615.50 | - | 27.12 | 32 |
| 100pct | 1 | LOADED | 121.50 | 1047.55 | 0.25016273 | 15.64 | 32 |
| 100pct | 2 | QUIESCENT | 82.73 | 605.43 | - | 45.14 | 32,33 |
| 100pct | 2 | LOADED | 120.53 | 1023.77 | 0.502387403 | 31.40 | 32,33 |
| 100pct | 4 | QUIESCENT | 82.48 | 564.14 | - | 87.74 | 32,33,34,35 |
| 100pct | 4 | LOADED | 106.41 | 1060.79 | 1.1283519 | 70.52 | 32,33,34,35 |
| 100pct | 8 | QUIESCENT | 68.00 | 475.08 | - | 198.62 | 32,33,34,35,36,37,38,39 |
| 100pct | 8 | LOADED | 120.44 | 984.12 | 1.97855817 | 123.66 | 32,33,34,35,36,37,38,39 |
| 100pct | 16 | QUIESCENT | 81.87 | 495.99 | - | 290.90 | 32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47 |
| 100pct | 16 | LOADED | 120.07 | 931.02 | 3.9350527 | 245.94 | 32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47 |
| 125pct | 1 | QUIESCENT | 82.82 | 621.53 | - | 22.94 | 32 |
| 125pct | 1 | LOADED | 107.06 | 1098.60 | 0.283913231 | 17.74 | 32 |
| 125pct | 2 | QUIESCENT | 69.76 | 589.43 | - | 53.57 | 32,33 |
| 125pct | 2 | LOADED | 106.68 | 1090.86 | 0.56652833 | 35.41 | 32,33 |
| 125pct | 4 | QUIESCENT | 82.47 | 565.89 | - | 87.84 | 32,33,34,35 |
| 125pct | 4 | LOADED | 120.30 | 997.06 | 0.995998739 | 62.25 | 32,33,34,35 |
| 125pct | 8 | QUIESCENT | 81.79 | 517.87 | - | 165.48 | 32,33,34,35,36,37,38,39 |
| 125pct | 8 | LOADED | 119.69 | 965.98 | 2.01017371 | 125.64 | 32,33,34,35,36,37,38,39 |
| 125pct | 16 | QUIESCENT | 82.26 | 504.70 | - | 289.09 | 32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47 |
| 125pct | 16 | LOADED | 106.34 | 980.24 | 4.44117522 | 277.57 | 32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47 |

### Interpretation

Unlike the single-thread row-C case, morsel mode shows clear loaded-vs-quiescent interference on the shared hot table. The effect is visible even though the loaded morsel stream is probe-gated and does not reach the 23.6 GB/s full-stream aggregate CXL ceiling.

At 53% LLC, loaded active cycles/access are roughly 87-89 cycles across core counts versus 55-58 cycles quiescent. At 100% LLC, loaded is about 106-121 cycles/access versus 68-83 quiescent. At 125% LLC, loaded is about 106-120 cycles/access versus 70-83 quiescent. MPKI also rises strongly in the loaded condition for 100% and 125% hot sets, consistent with aggregate one-pass fills and probe traffic stressing the shared LLC at scale.

Aggregate loaded stream bandwidth scales with cores but remains probe-gated: about 0.34 GB/s at 1 core and up to 5.42 GB/s at 16 cores for 53%, 3.94 GB/s at 16 cores for 100%, and 4.44 GB/s at 16 cores for 125%. This is still enough to expose cross-core interference that the same-core row-C experiment did not show on this host.

## Morsel WB vs NTA and CAT Attempt, 2026-07-02

### WB vs NTA Table, 53% LLC

Shared hot table, fact stream on CXL node 2, one worker per physical core on CPUs 32-47. This table is presented before interpretation.

| Cores | Policy | Active cyc/access | MPKI | Aggregate stream BW GB/s | Join MT/s | SW NTA prefetches | CPU mapping |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | wb | 88.55 | 116.69 | 0.343 | 21.45 | 0 | 32 |
| 1 | nta | 94.46 | 81.34 | 0.322 | 20.11 | 1235190847 | 32 |
| 2 | wb | 89.24 | 88.62 | 0.679 | 42.41 | 0 | 32,33 |
| 2 | nta | 94.30 | 56.68 | 0.640 | 40.02 | 1246683387 | 32,33 |
| 4 | wb | 87.71 | 96.31 | 1.374 | 85.88 | 0 | 32,33,34,35 |
| 4 | nta | 92.87 | 75.91 | 1.290 | 80.64 | 1233588002 | 32,33,34,35 |
| 8 | wb | 86.55 | 58.68 | 2.755 | 172.19 | 0 | 32,33,34,35,36,37,38,39 |
| 8 | nta | 95.19 | 79.67 | 2.464 | 154.03 | 1254913293 | 32,33,34,35,36,37,38,39 |
| 16 | wb | 88.32 | 67.02 | 5.373 | 335.82 | 0 | 32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47 |
| 16 | nta | 92.67 | 37.87 | 5.096 | 318.51 | 1245233790 | 32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47 |

### 53% LLC Interference Curve: Quiescent vs Loaded WB

This repeats the full 1->16 core interference curve at 53% LLC.

| Cores | Quiescent cyc/access | Loaded WB cyc/access | Quiescent MPKI | Loaded WB MPKI | Loaded stream BW GB/s |
|---:|---:|---:|---:|---:|---:|
| 1 | 57.59 | 89.08 | 55.30 | 70.49 | 0.341 |
| 2 | 55.51 | 87.24 | 51.31 | 61.99 | 0.693 |
| 4 | 55.55 | 87.98 | 45.04 | 69.90 | 1.364 |
| 8 | 57.41 | 86.96 | 51.40 | 46.47 | 2.743 |
| 16 | 56.43 | 87.05 | 32.53 | 71.41 | 5.422 |

### Interpretation

NTA reduces MPKI relative to WB at 1, 2, 4, and 16 cores, but does not return active probe cost toward the quiescent baseline. Active cycles/access are consistently higher with NTA than WB in this sweep. The stream-bandwidth confound is visible: NTA aggregate stream bandwidth is lower than WB at every core count.

At 16 cores, WB is 88.32 cycles/access and 67.02 MPKI at 5.373 GB/s; NTA is 92.67 cycles/access and 37.87 MPKI at 5.096 GB/s. So NTA reduces measured LLC misses but does not improve observed hot-table probe cost here.

### CAT Attempt

Attempted direct resctrl group creation for CAT:

```text
mkdir /sys/fs/resctrl/_cat_probe_$$
mkdir: Permission denied
```

CAT cannot be run at the current privilege level. This was not skipped silently; the CAT-cannot-protect experiment is deferred until the process has root or `CAP_SYS_ADMIN` for resctrl control group creation.

## Morsel CAT Same-Core Test, 2026-07-02

Resctrl group creation now succeeds with sudo. The CAT test assigns the benchmark process and its worker threads to one CAT class with L3 mask `0ffff` on both LLC IDs, i.e. 16 contiguous ways out of 20. This is the relevant same-core/morsel CAT test because every worker core both streams the CXL fact region and probes the shared hot table; CAT can constrain the whole worker class, but cannot assign the stream and hot-table accesses from the same cores to different classes.

| Cores | Unpartitioned cyc/access | CAT cyc/access | Unpartitioned MPKI | CAT MPKI | Unpartitioned BW GB/s | CAT BW GB/s |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 88.55 | 93.07 | 116.69 | 358.08 | 0.343 | 0.327 |
| 2 | 89.24 | 93.40 | 88.62 | 342.46 | 0.679 | 0.645 |
| 4 | 87.71 | 92.26 | 96.31 | 311.31 | 1.374 | 1.299 |
| 8 | 86.55 | 97.24 | 58.68 | 281.70 | 2.755 | 2.463 |
| 16 | 88.32 | 95.18 | 67.02 | 222.73 | 5.373 | 5.008 |

CAT does not protect the shared hot table in this same-core morsel configuration. It makes active probe cost worse at every core count and substantially raises MPKI, while also lowering stream bandwidth. This supports the claim that CAT cannot separate a core's own stream accesses from its hot-table accesses when both originate from the same worker threads.

No resctrl groups were left behind after the run. Raw CAT records are in `artifacts/results.jsonl` under phase `morsel_cat_53pct`, and per-run logs are under `artifacts/logs/cat16ways_53pct_*`.

## Real-Hardware Handoff Findings, 2026-07-02

### Capacity vs Contention Diagnostic

Diagnostic uses the accepted 53% LLC morsel interference curve: quiescent shared-table probes versus loaded WB stream+probe across 1,2,4,8,16 cores.

| Cores | Quiescent cyc | Loaded cyc | Extra cyc | Quiescent MPKI | Loaded MPKI | Extra MPKI | Extra cyc predicted by local miss cost |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 57.59 | 89.08 | 31.49 | 55.30 | 70.49 | 15.19 | 3.22 |
| 2 | 55.51 | 87.24 | 31.74 | 51.31 | 61.99 | 10.68 | 2.26 |
| 4 | 55.55 | 87.98 | 32.42 | 45.04 | 69.90 | 24.86 | 5.27 |
| 8 | 57.41 | 86.96 | 29.55 | 51.40 | 46.47 | -4.93 | -1.04 |
| 16 | 56.43 | 87.05 | 30.62 | 32.53 | 71.41 | 38.88 | 8.24 |

Correlation results:

- Loaded cycles/access vs loaded MPKI: **r = 0.525**.
- Extra cycles/access vs extra MPKI: **r = 0.403**.
- Local randomized pointer-chase miss cost assumption: **211.8 cycles**.

Conclusion: the morsel interference is **not purely capacity-driven** by the measured MPKI increase. MPKI rises in important points, and NTA can reduce MPKI, so allocation-driven pollution is real. But the extra cycles are roughly 30 cycles/access across all core counts, while extra MPKI predicts only about -1 to 8 cycles/access on the accepted curve. This flags a memory-contention/overlap component that non-allocation alone may not remove. The morsel benefit claim should therefore be scoped as: non-allocation removes a measurable LLC-fill/MPKI component; cycle recovery depends on eliminating software-prefetch overhead and on how much of the remaining penalty is contention rather than capacity.

### Real-Silicon Findings to Hand Off

- **Platform identity:** node 2 is a real CXL.mem-backed memory-only NUMA node. Randomized 2 GiB pointer-chase latency is 199.16 ns on node 2 versus 111.49 ns on node 0.
- **Platform anchors:** single-core CXL WB stream is 9.405 GB/s; aggregate CXL ceiling is 23.643 GB/s. This host differs from the paper's 15.8 GB/s Samsung Type-3 platform.
- **Same-core row-C:** null/small interference on this host. Replacement policy protects the 1:1 case well enough that WB-stream does not materially worsen probe cost.
- **Morsel interference:** exists and scales in the many-core case. At 53% LLC and 16 cores, quiescent vs loaded is 56.43 -> 87.05 cycles/access and 32.53 -> 71.41 MPKI.
- **NTA morsel:** at 53%/16-core, NTA reduces MPKI from 67.02 to 37.87, but cycles worsen from 88.32 to 92.67 and stream BW falls from 5.373 to 5.096 GB/s. This supports the proxy-overhead/confound: software PREFETCHNTA can reduce allocation/fill pressure, but does not show a cycle win on this host.
- **PREFETCHNTA full-stream:** best observed offcore L3-miss demand-read reduction is 81.2% at pf-distance 512, but stream bandwidth drops from 8.844 GB/s to 3.285 GB/s, a 62.9% loss.
- **Local-vs-CXL matched-aggressor:** at 53% LLC, local-DRAM and CXL fact streams have matched bandwidth within ~3% and nearly identical probe cycles. The morsel tax is generic cacheable-fill/shared-LLC interference, not a CXL-path-specific contention effect.
- **CAT cannot bind same-core stream vs hot table:** with a 16-way CAT class at 53% LLC, CAT worsens probe cost and MPKI versus unpartitioned because every worker core both streams and probes. CAT constrains both access classes together.
- **CAT works-but-wrong-scope:** resctrl/CAT control groups and L3 schemata writes are functional under sudo. A separate-victim setup is the scope where CAT can isolate cores/classes, but that success control was not rerun in this final no-more-benefit-runs pass, so no numerical separate-victim CAT benefit is claimed here.

### gem5 Handoff

The gem5 H2 target should model an overhead-free non-allocating stream path, not software PREFETCHNTA. Based on real silicon, H2 is expected to reduce LLC-fill/MPKI pressure in morsel mode. Whether cycles recover depends on gem5's modeled contention and MLP behavior: if the extra cycles are primarily contention/queueing, cycle recovery may be smaller than MPKI recovery; if software-prefetch overhead was masking the benefit, H2 should show the missing cycle win.

## Local-DRAM vs CXL Morsel Aggressor, 2026-07-02

This diagnostic compares morsel interference with the fact stream allocated on local DRAM node 0 versus CXL node 2 at 53% LLC. Core counts and CPU mappings match the accepted morsel sweep. The goal is to distinguish generic cacheable-fill/LLC interference from a CXL-path-specific contention effect. The measured aggregate stream bandwidths are naturally matched because the join is probe-gated.

| Cores | Local-stream cyc/access | CXL-stream cyc/access | Local MPKI | CXL MPKI | Local BW GB/s | CXL BW GB/s | Local/CXL BW |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 87.87 | 88.55 | 117.95 | 116.69 | 0.346 | 0.343 | 1.008 |
| 2 | 87.66 | 89.24 | 104.88 | 88.62 | 0.690 | 0.679 | 1.017 |
| 4 | 87.25 | 87.71 | 96.53 | 96.31 | 1.369 | 1.374 | 0.996 |
| 8 | 89.09 | 86.55 | 104.83 | 58.68 | 2.674 | 2.755 | 0.971 |
| 16 | 87.64 | 88.32 | 74.75 | 67.02 | 5.391 | 5.373 | 1.003 |

The local and CXL aggressor bandwidths are matched within about 3% at all core counts. Probe cycles/access are also effectively the same: differences are under roughly 3 cycles/access. MPKI varies by core count, but there is no systematic CXL >> local cycle penalty.

Conclusion: the observed morsel tax is a generic cacheable-fill/shared-LLC phenomenon, not a CXL-link-specific contention effect. This is reassuring for gem5 H2: an overhead-free non-allocating stream mechanism targets the right class of problem. The remaining caveat from the capacity-vs-contention diagnostic still stands: cycle recovery depends on how much of the penalty is allocation-driven versus generic overlap/queueing, but that component is not specific to the CXL path on this host.
