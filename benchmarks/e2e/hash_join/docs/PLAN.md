# CXL Streaming-vs-Hot-Set Hash Join Benchmark Plan

## Scope and Gates

Native implementation proceeds first. `cat` policy and CMT occupancy are deferred because
`mkdir /sys/fs/resctrl/_probe` failed with `Permission denied`; root or `CAP_SYS_ADMIN`
is required for resctrl control/monitor group creation on this host. The benchmark will
still build with `--policy cat`, but native execution will exit clearly:

```text
deferred: --policy cat needs resctrl control-group privilege
```

Gem5 execution is not in scope here. The source will keep compile-time seams for
`-DGEM5`, fact-region allocation, ROI markers, and config dumping of `[base, base+len)`.

Stop gates:

1. This plan.
2. Phase-0 node-2 STREAM-like bandwidth smoke result.
3. Policy results after `nta` sweep and `morsel wb` baseline.

## Confirmed Environment

- CPU: Intel Xeon Platinum 8592+ / Emerald Rapids class, non-inclusive LLC.
- NUMA: node 0 compute CPUs `0-63,128-191`; node 2 has 0 CPUs and ~254 GB memory.
- SMT: enabled. Worker selection will use one logical CPU per physical core on node 0,
  avoiding sibling CPUs `128-191` unless explicitly requested.
- Governor and turbo: `performance`, turbo disabled.
- `perf stat` usable by current user; `perf_event_paranoid = -1`.
- `numactl` and `libnuma.so.1` available.
- `resctrl` mounted and metadata readable:
  - L3 `cbm_mask = fffff`
  - L3 minimum CBM bits = `1`
  - monitor features include `llc_occupancy`, `mbm_total_bytes`, `mbm_local_bytes`
- `pqos`, Intel PCM, and gem5 are not available on PATH.

## File Layout

```text
Makefile
README.md
PLAN.md
RESULTS.md
include/
  benchmark.hpp         shared types, config, metrics, policy enums
  platform.hpp          native/GEM5 allocation, pinning, timing, ROI hooks
  hash_join.hpp         data model, hash table, join entry points
  perf_events.hpp       perf_event_open helper and event group definitions
  resctrl.hpp           privilege probe and deferred CAT/CMT hooks
src/
  main.cpp              CLI, config dump, mode dispatch
  platform_native.cpp   NUMA allocation/assertions, CPU topology, pinning
  platform_gem5.cpp     GEM5-compatible mmap allocation and ROI no/syscall hooks
  datagen.cpp           deterministic portable fact/table generator
  hash_join.cpp         scalar reference, open-address table, single/morsel kernels
  stream_bench.cpp      node-local/node-2 bandwidth and PREFETCHNTA sweep
  perf_events.cpp       per-thread perf measurements
  resctrl.cpp           resctrl privilege detection, cat stub
  stats.cpp             median/CoV, JSON/human table emitters
tests/
  test_reference.cpp    scalar-reference correctness and bit-identical data-gen
  test_numa.cpp         node-2 placement assertion test
scripts/
  run_phase0.sh
  run_nta_sweep.sh
  run_single.sh
  run_morsel.sh
```

The implementation may collapse small translation units if that keeps the first version
clear, but the interfaces above are the ownership boundaries.

## Portability Interface

`platform.hpp` exposes:

- `alloc_fact_region(bytes, node, hugepage_mode)`:
  - native: `numa_alloc_onnode(2)` or `mmap` plus `mbind(MPOL_BIND, node 2)`, with a
    placement assertion using `move_pages` and `/proc/self/numa_maps` as fallback.
  - `GEM5`: plain anonymous `mmap`, no NUMA syscalls.
- `alloc_hot_region(bytes, node 0)`: native node-0 allocation for hot table and state;
  `GEM5`: plain allocation.
- `pin_thread(cpu)`: native `pthread_setaffinity_np`; `GEM5`: no-op.
- `roi_begin(name)` / `roi_end(name)`: native `rdtscp` and `clock_gettime`; `GEM5`:
  guarded m5 hooks when available, otherwise no-op.
- `dump_config()`: always prints fact `[base, base+len)`, policy, mode, sizes, seed,
  pf-distance, warmups/reps, hugepage mode, CPU mapping, and build flags.

All NUMA, perf, and resctrl paths are guarded out under `#ifdef GEM5`.

## Workload Design

Data model:

- Hot hash table entry: `int64_t key`, `int64_t payload`, open addressing with linear
  probing and an explicit occupied marker.
- Fact tuple: `int64_t fk`, `int64_t measure`.
- Data generation: deterministic SplitMix64-based generator, fixed seed, no libc or
  platform RNG. Hit-rate controls whether `fk` is selected from generated hot keys or
  generated as a guaranteed miss key.
- Validation: scalar reference computes integer `match_count` and `sum(measure)` in
  deterministic order; optimized kernels must match exactly.

Kernels:

- `single`: one pinned node-0 thread streams node-2 fact once and probes shared hot
  table. This is row-C: stream and hot reuse interleaved in one access stream.
- `morsel`: N node-0 physical cores pull non-overlapping fact morsels and probe the
  shared hot table. First version reports `wb` only; `cat` is a privilege-gated stub.
- Probe timing micro-section: periodically run a probe-only window over deterministic
  keys and measure cycles/access with `rdtscp`; perf event group measures probe MPKI
  (`LLC-load-misses` per thousand probe loads where available).
- Pure stream microbench: sequential read over node-2 fact region for `wb` and `nta`
  with `--pf-distance` sweep. This is the required PREFETCHNTA finding path.

Policies:

- `wb`: ordinary cacheable loads.
- `nta`: `_mm_prefetch(addr + distance, _MM_HINT_NTA)` followed by ordinary loads.
  Build will include disassembly guidance and/or a runtime `objdump` check in scripts
  to confirm `prefetchnta` is emitted.
- `cat`: native stub until resctrl group creation privilege is available.
- `stream`: GEM5-only; native aliases `wb` with a loud warning.

## Measurement Protocol

For each run:

1. Build config dump.
2. Verify CPU pinning and node-2 fact placement before ROI.
3. Pre-warm hot table to LLC residency before streaming runs.
4. Run K warm-up iterations, discarded.
5. Run N measured iterations, default `N=30`.
6. Report median and CoV. If CoV exceeds 2%, retry with larger N up to a fixed cap, then
   emit the elevated CoV as a flagged result.
7. Emit per-run JSON plus human summary.

Anchor/control handling:

- PASS/FAIL: node-2 single-core WB sequential read target 15.8 GB/s ±20%.
- PASS/FAIL: local node-0 single-core WB read must be markedly higher than node-2; if
  node-2 reads at local speed, abort as failed placement.
- PASS/FAIL: L2-resident hot set around 2 MB should be ~1.0x slowdown as negative
  control.
- Informational only: 4.2 GB/s demand-miss floor is omitted because WC mapping and
  prefetcher disabling are out of scope.

## Perf and System Commands

Build and tests:

```bash
make native
make test
./build/test_reference
./build/test_numa --fact-bytes 268435456 --fact-node 2
```

Phase-0 smoke:

```bash
numactl --cpunodebind=0 ./build/cxl_join_bench \
  --mode stream-smoke --policy wb --fact-node 2 --local-node 0 \
  --fact-bytes 4294967296 --threads 1 --cpu-list 0 --reps 30

numactl --cpunodebind=0 ./build/cxl_join_bench \
  --mode stream-smoke --policy wb --fact-node 0 --local-node 0 \
  --fact-bytes 4294967296 --threads 1 --cpu-list 0 --reps 30
```

PREFETCHNTA sweep:

```bash
for d in 0 1 2 4 8 16 32 64 128 256 512; do
  perf stat -C 0 -e cycles,instructions,LLC-loads,LLC-load-misses,mem_load_l3_miss_retired.local_dram,mem_load_l3_miss_retired.remote_dram,offcore_requests.l3_miss_demand_data_rd \
    ./build/cxl_join_bench --mode stream-nta --policy nta \
      --pf-distance "$d" --fact-node 2 --fact-bytes 4294967296 \
      --threads 1 --cpu-list 0 --reps 30
done
```

The exact event list will be validated with `perf list` and adjusted only to available
architectural/PMU names. The human output will still report the same logical fields:
bandwidth, LLC loads, LLC misses, L3-miss retired counts, and offcore/CHA fill proxies.

Disassembly sanity check:

```bash
objdump -d ./build/cxl_join_bench | grep -i prefetchnta
```

Single row-C join:

```bash
perf stat -C 0 -e cycles,instructions,LLC-loads,LLC-load-misses,mem_load_l3_miss_retired.local_dram,mem_load_l3_miss_retired.remote_dram \
  ./build/cxl_join_bench --mode single --policy wb \
    --hot-bytes <53pct_llc_bytes> --fact-bytes 4294967296 \
    --fact-node 2 --hot-node 0 --threads 1 --cpu-list 0 \
    --vector 1024 --warmups 3 --reps 30

perf stat -C 0 -e cycles,instructions,LLC-loads,LLC-load-misses,mem_load_l3_miss_retired.local_dram,mem_load_l3_miss_retired.remote_dram \
  ./build/cxl_join_bench --mode single --policy nta \
    --pf-distance <best_from_sweep> --hot-bytes <53pct_llc_bytes> \
    --fact-bytes 4294967296 --fact-node 2 --hot-node 0 \
    --threads 1 --cpu-list 0 --vector 1024 --warmups 3 --reps 30
```

Morsel `wb` baseline:

```bash
./build/cxl_join_bench --mode morsel --policy wb \
  --threads 1,2,4,8,16 --cpu-list 0-15 \
  --hot-bytes <53pct_llc_bytes> --fact-bytes 4294967296 \
  --fact-node 2 --hot-node 0 --morsel 1048576 \
  --warmups 3 --reps 30
```

Deferred CAT/CMT privilege check:

```bash
mkdir /sys/fs/resctrl/_probe && rmdir /sys/fs/resctrl/_probe
```

When this succeeds, `resctrl.hpp` hooks will create control/monitor groups, write L3
CBMs to `schemata`, assign PIDs/TIDs to `tasks`, and read
`mon_data/mon_L3_*/llc_occupancy`. Until then, `cat` and CMT rows are marked deferred.

## Run Matrix

Initial correctness:

- small hot/fact sizes, hit rates `0.0`, `0.5`, `1.0`
- `single wb`, scalar reference, optimized result exact match
- NUMA placement test on node 2

Phase-0 anchors:

- stream-smoke `wb`, node-2 fact, one node-0 physical core
- stream-smoke `wb`, node-0 local allocation, same core

Main native measurements:

- hot sizes:
  - 2 MB negative control
  - 25%, 53%, 100% of per-socket LLC where 53% is the required reporting point
- policies:
  - `single`: `wb`, `nta`
  - `morsel`: `wb`
  - `cat`: deferred stub
- `nta` pf-distance sweep:
  - `0,1,2,4,8,16,32,64,128,256,512` cache lines unless early data shows the useful
    range needs one adjacent extension
- threads:
  - `single`: 1
  - `morsel`: `1,2,4,8,16` node-0 physical cores, avoiding SMT siblings

## Output Format

Human output contains two tables:

1. PASS/FAIL platform anchors and controls. Failures exit non-zero and stop subsequent
   scripted phases.
2. Measured interference results with no pass/fail labels:
   - `single`: probe MPKI, probe cycles/access, join throughput, stream BW
   - `morsel`: hot-set slowdown vs quiescent baseline and stream BW
   - `cat`/CMT fields: `deferred: needs resctrl privilege`

JSON records include:

- build ID, command line, date/time, host CPU model
- NUMA nodes and fact-region placement proof
- fact-region `[base, base+len)`
- thread to logical CPU and physical core mapping
- LLC size assumptions used for hot-size presets
- all benchmark knobs and metric samples
- median, CoV, retry count, and flags

## Remaining Assumptions

- The per-socket LLC for node 0 is treated as 320 MiB, based on `lscpu` reporting
  640 MiB L3 across 2 instances. Hot-size percentages use the node-0/socket-local LLC
  unless a later CPUID/sysfs check provides a more precise per-LLC mapping.
- CPU IDs `0-63` are first SMT threads for node 0 physical cores and `128-191` are their
  siblings, based on `lscpu` topology. Implementation will confirm via
  `/sys/devices/system/cpu/cpu*/topology/thread_siblings_list`.
- `mem_load_l3_miss_retired.remote_dram` is the closest perf proxy for node-2 CXL read
  misses on this platform; final event naming will be recorded in JSON.
- Hugepage availability is not yet confirmed. The benchmark will support explicit
  `--page-size 2m` and `--page-size 4k`; if 2 MB hugepages cannot be obtained it will
  report and fall back only when the user requested fallback.
- Static `-DGEM5` link may need m5 headers/libs supplied later. The code will compile a
  no-m5 fallback path so a static sanity binary can still be produced without simulator
  dependencies.
