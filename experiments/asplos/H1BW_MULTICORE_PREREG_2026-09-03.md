# Pre-registration — multi-core H1 bandwidth survival (4c / 8c), 2026-09-03

## Why this campaign exists

`Sec7_Evaluation.tex:67-69` states:

> The ordering persists with multiple readers. At four cores, aggregate
> bandwidth is 6.2/7.7/5.6~GB/s for WB/H1--H2/prefetch-off; at eight it is
> 6.1/7.6/5.8~GB/s.

Audit of both repos on 2026-09-03 found:

- **4-core (6.2/7.7/5.6).** Traceable to exactly one artifact:
  `experiments/asplos/preserved/gem5_streaming.tar.gz`, whose entire content is a
  single 2,513-byte `REPORT.md`. Section 4 of that report gives WB 6.23, H2 7.73,
  WC 5.62. There is no `stats.txt`, no `config.ini`, no JSON, and no runner: the
  `preserved/README.md` records that the scripts (`/tmp/run_arm.sh`,
  `/tmp/run_arm_mshr.sh`) are gone.
- **8-core (6.1/7.6/5.8).** No artifact. The same REPORT section ends
  `8-core repeat launched for robustness.` and records no result. The literals
  do not appear anywhere in either repository.

**The harness does not exist either.** `run_stream()` — the `stream-smoke` mode —
calls `pin_cpu(cpus[0])` and spawns no threads, in both
`benchmarks/e2e/hash_join/src/cxl_join_bench.cpp` (HEAD) and the retired
`benchmarks/e2e/hash_join_gem5se` fork on `origin/gem5-hashjoin-forks`. `--threads`
is parsed and echoed in that mode but never applied (an F9 requested-vs-realized
case). `gem5/scripts/run_se.sh` points `BIN` at the deleted fork path, and runs
`stream-smoke` only at `--num-cpus=1`.

So no committed code, on any branch, can produce a "4-core stream-smoke"
measurement as the REPORT describes it.

**This campaign is therefore not a reproduction.** It is a new measurement with a
newly written harness, pre-registered here, intended to supersede the archived
REPORT as the citable source for both core counts. If it disagrees with
6.23/7.73/5.62 we will not be able to attribute the difference to the archive
versus the harness, because the archive's harness is unrecoverable. That
limitation is accepted going in and must be stated wherever these numbers appear.

## Harness

`se.py` multi-program mode: N independent single-threaded instances of
`stream-smoke`, one per simulated CPU, each streaming its own private
`--fact-bytes`. This is the only construction consistent with the REPORT's
"32MiB total (8MiB/core), aggregate BW = 32MiB/total_sec" given a single-threaded
`run_stream()`. It is a reconstruction of intent, not of procedure.

Runner: `experiments/asplos/run_h1bw_multicore.sh`.

## Frozen configuration

Taken from the REPORT's platform line and section 4 where stated; every value the
REPORT left ambiguous is fixed here and recorded in each run's `MANIFEST.json`.

| parameter | value | source |
|---|---|---|
| CPU | O3CPU, 1.9 GHz | REPORT platform line |
| L1d | 48 KiB / 12-way | REPORT |
| L1i | 32 KiB / 8-way | `run_se.sh` |
| L2 | 2 MiB / 16-way | REPORT |
| L3 (HNF) | 5 MiB / 20-way **per slice**, `--num-l3caches=N` | REPORT gives per-HNF geometry only; slice count follows `run_se.sh`'s `--num-l3caches=$N` convention. **Total LLC therefore scales: 20 MiB at 4c, 40 MiB at 8c.** |
| memory | SimpleMemory, DRAM 98 ns, CXL 203 ns | REPORT |
| `L1_MSHR` | 48 | REPORT section 4 |
| `L1_REPL` | 16 (default, left unset) | Not stated by the REPORT. `CHI_config_8592.py:315-321` warns that sweeping `L1_MSHR` alone starves the replacement path and is "a candidate cause of H2 fill-suppression degrading at high L1_MSHR". Left at the default so this matches whatever the archive did; **recorded because it is a live confound, not because it is correct.** |
| stream size | 8 MiB per instance | REPORT |
| `ALL_CXL` | 1 | `run_se.sh` w1 path |
| warmups / reps | 1 / 1 | Not stated by the REPORT. One warm pass then one measured pass; runtime-bound. |

## Arms

Reproduced from `run_se.sh`'s w1 arm definitions, which are the only committed
definition of these three arms.

| arm | policy | prefetch | note |
|---|---|---|---|
| `wb` | `wb` | on | |
| `h2` | `stream` | on | |
| `pfoff` | `stream` | **off** (`PF_OFF_CORES=0..N-1`) | |

**The third arm is not write-combining.** `run_se.sh` builds it as
`policy=stream` with the prefetchers disabled, and the REPORT labels the same arm
"WC (prefetch off)". The paper calls it "prefetch-off", which is accurate; the
appendix's derivation of a "model WB-vs-WC ratio" from it is not, since no arm in
this campaign or the archive uses the WC memory type. Recorded here so the
mislabel is not re-inherited.

## Metrics

Two aggregates, both recorded, because the REPORT's "aggregate BW =
32MiB/total_sec" does not say which:

1. `agg_bw_sum` — sum of the per-instance `bandwidth_gbps`.
2. `agg_bw_wall` — total bytes / simulated seconds (`simSeconds` from `stats.txt`).

Also recorded per run: every instance's JSON line, `stats.txt`, `config.ini`, the
full argv, the environment, the benchmark binary SHA-256, and the gem5 binary
SHA-256.

## Pre-declared outcomes

- **PASS** — ordering H2 >= WB > prefetch-off holds at both 4c and 8c.
- **PARTIAL** — ordering holds at one core count only.
- **NULL** — ordering does not hold. This is a publishable result and supersedes
  the archive; the paper sentence comes out.

Any outcome supersedes the archived REPORT as the cited source. The archive is
retained as provenance for what was previously claimed, not as evidence.

## Gates

- Fail-closed: a run whose `status` is not `ok` on every instance is void.
- A run whose realized instance count != N is void (guards against se.py silently
  dropping a workload).
- Realized LLC bytes are recorded from `config.ini` and must equal
  `N * 5 MiB`; a mismatch voids the run rather than being reported as requested.
