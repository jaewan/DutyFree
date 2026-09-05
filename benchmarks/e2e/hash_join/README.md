# Hash-join — official STREAMING application benchmark

**This is the STREAMING application's unit.** One-pass fact stream vs a reused
hot hash table; the neighbour is a pointer-chase victim. Do not substitute HNSW,
GAPBS, DuckDB, or RocksDB for the STREAMING-vs-CAT cell.

| platform | campaign | metric | STREAMING? |
|---|---|---|---|
| gem5 SE m5op | **r5 complete join** | tuples/s + victim cyc/load | **yes** (H2) |
| silicon SPR (mos182) | silicon e2e | tuples/s + victim cyc/load | **no** (CAT / nta / flush-behind only) |

Recompute the STREAMING cell from committed data (`make official-bench` at the
repo root). That does **not** re-run 4.6 hours of gem5.

```bash
# from DutyFree/
make official-bench
# equivalent:
python3 experiments/asplos/analyze_complete_join.py \
    experiments/asplos/data/gem5/r5_runs.jsonl
```

r5 (45/45, P5 PASS): H2 R = **22.59%**, tenant **+5.35%** vs wb. Wedge
**+9.97%** vs cheapest CAT with R ≥ H2 (w=16); **+8.42%** interpolated at
matched R (post-hoc). Quote both. Victim/LLC is **0.345** (r3 and silicon are
~0.53) — disclose that. Do not write "~1.07×" model↔silicon calibration.

| document | role |
|---|---|
| `experiments/asplos/COMPLETE_JOIN_PREREG_2026-09-01.md` | thresholds, before data |
| `experiments/asplos/COMPLETE_JOIN_OUTCOME_2026-09-01.md` | verdict + **addendum 1** |
| `experiments/asplos/run_complete_join.sh` | gem5 launcher (`--l3_size=7680KiB`, never `7.5MiB`) |
| `experiments/asplos/data/gem5/r5_runs.jsonl` | 45 archived runs |
| `experiments/asplos/SILICON_E2E_OUTCOME_2026-09-01.md` | shipping knobs on SPR |
| `experiments/asplos/data/silicon_e2e_hashjoin.jsonl` | 105 silicon records |

`wm20` uses empty `requestor_masks` (same as wb). Bit-identity is tautological,
not a mask-path control. Do not quote `cyc_per_access` from r5 JSONL (stale
`ITERS=3e6`); use `cyc_per_load`. r12 `mprotect` is mechanism, not this cell.

The rest of this file is the binary's native/CXL characterization harness. Those
numbers are not the STREAMING application cell.

---

# CXL Streaming-vs-Hot-Set Hash-Join Benchmark

Portable C++17 benchmark for measuring cacheable one-pass stream interference against a reused hot hash table on real hardware, with a clean seam for later gem5 SE runs.

The benchmark was built for the CXL/hash-join experiment in this repository: native execution is the source of real-silicon measurements; gem5 support is limited to a static `-DGEM5` binary and fact-region bound reporting for the simulator harness.

## Native characterization (not the STREAMING cell)

The latest real-hardware findings are recorded in [docs/RESULTS.md](docs/RESULTS.md). Headline numbers on this host:

| Finding | Result |
|---|---:|
| CXL node-2 pointer-chase latency | 199.16 ns |
| Local node-0 pointer-chase latency | 111.49 ns |
| Single-core CXL WB stream anchor | 9.405 GB/s |
| Aggregate CXL WB stream ceiling | 23.643 GB/s |
| Morsel 53% LLC, 16-core quiescent -> loaded | 56.43 -> 87.05 cycles/access |
| Morsel 53% LLC, 16-core MPKI quiescent -> loaded | 32.53 -> 71.41 MPKI |
| PREFETCHNTA best offcore reduction | 81.2% at pf-distance 512, with 62.9% BW loss |

Interpretation: same-core row-C interference is small/null on this host, but morsel mode shows real many-core shared-LLC interference. Local-DRAM and CXL aggressors with matched bandwidth produce similar probe costs, so the observed tax is a generic cacheable-fill/shared-LLC effect rather than a CXL-link-specific contention effect.

## Repository Layout

```text
.
├── Makefile                  # native, gem5, test, clean targets
├── README.md                 # this guide
├── gem5_handoff.md           # execution contract for gem5 H1/H2 work
├── src/
│   └── cxl_join_bench.cpp    # single-source C++17 benchmark
├── scripts/
│   └── run_all.py            # resumable native measurement harness
├── docs/
│   ├── PLAN.md               # design and run plan
│   ├── PROGRESS.md           # timestamped run log and findings
│   ├── RESULTS.md            # summarized measurements and interpretation
│   └── workloads_prompts.md  # original workload specification trail
└── artifacts/
    ├── results.jsonl         # append-only raw run records
    ├── state.json            # resumability state
    └── logs/                 # per-run stdout/stderr/perf logs
```

Compatibility symlinks are kept at the repo root for `PLAN.md`, `PROGRESS.md`, `RESULTS.md`, `results.jsonl`, `state.json`, and `logs/`.

## Requirements

Native measurement assumes:

- Linux on Intel Xeon SPR/EMR-class hardware with a non-inclusive LLC.
- A memory-only NUMA node for CXL.mem. In the current dataset, node 2 is the CXL node.
- Compute threads pinned to physical cores on node 0, avoiding SMT siblings.
- `perf` usable by the current account for the selected events.
- `numactl` available for environment inspection. The benchmark uses direct syscalls for placement checks and does not require `libnuma` headers.
- Optional root/passwordless sudo for resctrl/CAT experiments. CAT/CMT are not required for the native WB/NTA benchmark path.

Generated data can be large. Keep raw logs under `artifacts/logs/`; commit only curated results when they are intentionally part of a paper artifact.

## Build And Test

```bash
make native
make test
```

`make test` runs:

- deterministic scalar-reference join self-test
- NUMA placement self-test for node-2 fact allocation

Build the gem5 seam binary without running gem5:

```bash
make gem5
./build/cxl_join_bench.gem5 --mode single --policy wb --fact-bytes 16m --hot-bytes 2m --reps 1 --warmups 0
```

## Benchmark Modes

The binary is intentionally single-file and mode-driven:

| Mode | Purpose |
|---|---|
| `stream-smoke` | Sequential WB stream bandwidth and placement sanity |
| `stream-nta` | Pure-stream WB/NTA prefetch-distance sweep |
| `latency` | Randomized pointer-chase latency |
| `single` | Same-core row-C stream+probe join |
| `breakdown` | Per-tuple cycle breakdown diagnostic |
| `probe-workload` | Quiescent/probe-only hot-set measurement |
| `hot-probe` | Shared hot-table probe baseline |
| `morsel` | Multi-core morsel scan+probe benchmark |

Common flags:

```bash
./build/cxl_join_bench \
  --mode morsel \
  --policy wb \
  --fact-node 2 \
  --hot-node 0 \
  --fact-bytes 1g \
  --hot-bytes 177838489 \
  --threads 16 \
  --cpu-list 32-47 \
  --morsel 1m \
  --warmups 3 \
  --reps 30
```

Policies:

- `wb`: normal cacheable loads.
- `nta`: `_mm_prefetch(..., _MM_HINT_NTA)` ahead of normal loads. Always report bandwidth beside probe metrics because software prefetch changes stream throughput.
- `t0`: software `prefetcht0` diagnostic for MLP experiments.
- `cat`: native stub unless resctrl setup is run externally with sufficient privilege.
- `stream`: gem5-only non-allocating stream tag; native aliases to WB with a warning.

## Reproducing The Native Matrix

The harness is resumable and writes records incrementally:

```bash
BENCH_FACT_BYTES=1g BENCH_REPS=30 BENCH_WARMUPS=3 BENCH_TIMEOUT=600 ./scripts/run_all.py
```

Outputs:

- raw JSONL: [artifacts/results.jsonl](artifacts/results.jsonl)
- resumability state: [artifacts/state.json](artifacts/state.json)
- per-run logs: [artifacts/logs](artifacts/logs)
- human summary: [docs/RESULTS.md](docs/RESULTS.md)
- progress heartbeat: [docs/PROGRESS.md](docs/PROGRESS.md)

Each run record includes configuration, measured throughput, placement metadata, fact-region `[base,end)` bounds, and perf counters when collected.

## Measurement Discipline

- Do not tune parameters to hit an expected number.
- Treat out-of-band anchors and null effects as findings.
- Pre-fault and verify NUMA placement before timed loops.
- Use regions larger than LLC for stream bandwidth and latency characterization.
- In same-thread row-C mode, do not use CMT to attribute occupancy between stream and hot table; use probe MPKI and probe cycles/access.
- Report WB and NTA stream bandwidth side by side.
- Pin one worker per physical core and record the CPU mapping.

## CAT And resctrl

CAT/CMT require resctrl control or monitor group creation. If the account cannot create groups under `/sys/fs/resctrl`, `--policy cat` exits clearly as deferred. When using sudo, clean up resctrl groups after the run and record the schemata mask in [docs/RESULTS.md](docs/RESULTS.md).

## Development Notes

- Keep benchmark logic in `src/cxl_join_bench.cpp` unless there is a strong reason to split it.
- Keep generated artifacts append-only where practical; `results.jsonl` is the audit trail.
- Preserve root-level symlinks because older notes and scripts refer to top-level result paths.
- Prefer adding focused benchmark modes over changing the semantics of existing modes.
