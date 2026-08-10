# gem5 Handoff: Streaming H1/H2 Benefit Evaluation

**Audience:** the gem5 team taking over the microarchitectural benefit claims for the
ASPLOS'27 `Streaming` paper.

**Move target:** this directory is intended to live at:

```text
~/tmp_dutyfree_exp/DutyFree/benchmarks/e2e/hash_join/
```

All paths below are relative to that directory unless explicitly marked as a DutyFree
repository path.

**Status of upstream work:** real-hardware characterization and native hash-join
benchmarking on EMR 8592+ are complete. Real silicon cannot implement true, overhead-free
non-allocation, so H2's clean benefit must be measured in gem5.

This document is the execution contract for the gem5 handoff. It tells you what is
already established, what the C++ workload provides, what gem5 must implement, which
experiments gate the paper, and what artifacts to return.

---

## 0. Immediate Checklist

Before running sweeps:

1. Build the static workload binary:

   ```bash
   cd ~/tmp_dutyfree_exp/DutyFree/benchmarks/e2e/hash_join
   make gem5
   ```

2. Sanity-run the binary outside gem5:

   ```bash
   ./build/cxl_join_bench.gem5 \
     --mode single --policy wb \
     --fact-bytes 16m --hot-bytes 2m \
     --threads 1 --cpu-list 0 \
     --warmups 0 --reps 1 --check
   ```

3. Confirm the last stdout line is one JSON object with:

   - `status:"ok"`
   - `fact_base:"0x..."`
   - `fact_end:"0x..."`
   - `thread_mapping:[...]`
   - `correct:true` when `--check` is present

4. In gem5, parse `fact_base` and `fact_end` and tag exactly that byte range as
   `Streaming` when the experiment requests H2.

5. Do not treat the C++ `--policy stream` flag as a complete implementation of H2. The
   benchmark supplies the access stream and region bounds; gem5 must implement the
   non-allocating behavior in the memory hierarchy.

---

## 1. What Real Hardware Already Established

These measurements are settled on EMR 8592+ with performance governor, turbo off,
physical cores 32-47, 2 MB hugepages, and fact region on CXL node 2 unless noted. Source:
[docs/RESULTS.md](docs/RESULTS.md) and raw records in
[artifacts/results.jsonl](artifacts/results.jsonl).

| Finding | Result | Consequence for gem5 |
|---|---:|---|
| CXL identity | Real CXL.mem NUMA node 2 | Model a real CXL memory path, not generic remote DRAM |
| CXL pointer-chase latency | 199.16 ns | CXL latency anchor |
| Local pointer-chase latency | 111.49 ns | Local latency anchor |
| Single-core CXL WB stream | 9.405 GB/s | This host's single-core CXL anchor |
| Aggregate CXL WB stream | 23.643 GB/s | This host's CXL aggregate ceiling |
| Same-core row-C | Small/null interference | Do not anchor the single-thread capacity claim on native HW |
| Morsel 53% LLC, 16-core | 56.43 -> 87.05 cycles/access | Many-core fused stream+probe interference exists |
| Morsel 53% LLC, 16-core MPKI | 32.53 -> 71.41 MPKI | Pollution component exists |
| Local-vs-CXL matched aggressor | Similar probe cycles within about 3 cycles/access | Tax is generic cacheable-fill/shared-LLC, not CXL-link-specific |
| NTA morsel 53%, 16-core | MPKI 67.02 -> 37.87; cycles 88.32 -> 92.67 | Software NTA reduces misses but its overhead hides cycle benefit |
| PREFETCHNTA pure stream | 81.2% offcore L3-miss demand-read reduction at -62.9% BW | Vendor hint is a confounded proxy, not the target mechanism |
| CAT same-core morsel | CAT worsens probe cost/MPKI | CAT cannot bind stream and hot table when both come from same workers |

**Net:** the problem is real, source-agnostic, and CAT-unfixable in the fused worker
regime. What is unproven, and assigned to gem5, is whether overhead-free
non-allocation recovers the tax without collapsing stream bandwidth.

---

## 2. What This Directory Provides

### Source And Build

```text
src/cxl_join_bench.cpp      single-source C++17 workload
Makefile                    native/gem5/test targets
docs/RESULTS.md             real-HW findings
artifacts/results.jsonl     append-only native records
```

Build targets:

```bash
make native       # native Linux binary
make test         # native correctness + NUMA self-tests
make gem5         # static -DGEM5 binary for gem5 SE
```

The gem5 target emits:

```text
build/cxl_join_bench.gem5
```

### Important Limitation

The C++ code does **not** implement non-allocation by itself. For gem5:

- `--policy wb` is the baseline workload.
- `--policy nta` models software PREFETCHNTA behavior in the binary.
- `--policy stream` is a gem5-facing semantic label only. It is not sufficient unless the
  simulator uses the fact-region ABI below to apply non-allocating fills.

If gem5 runs the binary with no simulator-side H2 support, `stream` must be considered a
WB-equivalent control, not an H2 result.

### Workload Modes Relevant To gem5

| Mode | Use |
|---|---|
| `stream-smoke` | Pure sequential stream, useful for H1 bandwidth checks |
| `stream-nta` | Software-prefetch proxy; not the H2 result |
| `single` | Same-core row-C stream+hot-table join |
| `morsel` | Multi-core fused stream+shared-hot-table join |
| `probe-workload` | Quiescent hot-table probe baseline |
| `breakdown` | Per-tuple cycle breakdown diagnostic |

---

## 3. Fact-Region ABI

Every run prints one JSON object on stdout. The gem5 harness must parse the last JSON
object emitted by the workload and consume these fields:

| Field | Type | Meaning |
|---|---|---|
| `fact_base` | hex string | Inclusive start address of the fact stream region |
| `fact_end` | hex string | Exclusive end address of the fact stream region |
| `fact_bytes` | integer | Byte length of `[fact_base,fact_end)` |
| `mode` | string | Workload mode |
| `policy` | string | Requested software/simulator policy |
| `hot_bytes` | integer | Hot hash-table target size |
| `threads` | integer | Worker count |
| `thread_mapping` | array | Worker-to-CPU/core mapping requested by the workload |
| `status` | string | Must be `ok` for usable runs |
| `correct` | bool | Present when `--check` is used; must be `true` |

Example shape:

```json
{
  "mode": "morsel",
  "policy": "wb",
  "fact_bytes": 1073741824,
  "hot_bytes": 177838489,
  "threads": 16,
  "fact_base": "0x7f1000000000",
  "fact_end": "0x7f1040000000",
  "thread_mapping": [{"thread":0,"cpu":0,"physical_core":0}],
  "status": "ok"
}
```

For H2 experiments, gem5 must tag exactly:

```text
[parse_hex(fact_base), parse_hex(fact_end))
```

as `Streaming`. Do not tag the hot table, stack, heap metadata, or result buffers. The hot
table must remain WB/cacheable.

### Required H2 Semantics

The intended H2 realization is:

1. A clean `Streaming` demand or prefetch fill may enter the requesting core's private
   L1/L2.
2. On L2 eviction, a clean `Streaming` line is dropped at the L2-to-LLC boundary.
3. It is never inserted into the LLC data array.
4. It never displaces a resident WB line.
5. The streaming type is inherited by prefetches triggered by a streaming access.
6. The prefetcher re-resolves type at page boundaries.

This is realization (a), "drop silently." Only evaluate realization (b), a small
non-allocating stream/fill buffer, if Experiment 1 fails.

---

## 4. Frozen gem5 Configuration Contract

Freeze the config before sweeps and do not silently change it. The paper must disclose
the following as a table:

| Knob | Required disclosure |
|---|---|
| CPU model | O3/timing core model and frequency assumption |
| LLC | Size, associativity, replacement policy, inclusivity |
| Scaling | Proportional scaling factor for LLC, victim WSS, stream size |
| Private-cache ratios | L2:LLC ratio, hot-set-to-L2 ratio, and hardware-reference hot-set-to-L2 ratio |
| Snoop filter | Size/capacity; if unbounded, state that H3/SF-capacity claims are out of scope |
| L1/L2 prefetchers | Type, degree, distance; whether inherited streaming type is implemented |
| LLC prefetcher | Disabled unless explicitly justified |
| Local memory | Latency and bandwidth anchor |
| CXL memory | Latency and bandwidth anchor |
| MSHR/TBE counts | Every level; load-bearing for H1 |
| Network/mesh | Latency/bandwidth assumptions relevant to queueing decomposition |
| Validation status | Which points are real-HW validated versus scaled/interpolated |

Baseline model target: SPR/EMR-class non-inclusive LLC with snoop filter, Ruby/CHI if
available in the DutyFree gem5 tree.

---

## 5. Calibration Anchors

The real-HW calibration anchor for this repository is the local-DRAM high-fill-rate
operating point. Existing paper tables may cite `tab:gem5` and `tab:catmba`; when using
this repo alone, use [docs/RESULTS.md](docs/RESULTS.md) for raw real-HW context and the
following calibration rule for gem5.

| Victim WSS | HW CXL-8 | HW local-4 | gem5 WB target | gem5 +H2 target |
|---|---:|---:|---:|---:|
| 25% LLC | 1.27x | 2.36x | 1.79x | 1.00x |
| 53% LLC | 2.03x | 2.61x | 2.57x | 1.00x |
| 100% LLC | 2.11x | 2.48x | 2.82x | 1.00x |

Hard calibration gate:

- Simulated WB tax at 53% WSS must be within 2% of 2.57x.
- Acceptable range: `2.52x <= WB_tax_53pct <= 2.62x`.
- If it misses, fix the config before reporting H2 benefit.
- Do not tune the 25% and 100% points independently to force a match. Report mismatch as
  model limitation.

Define tax consistently:

```text
tax = loaded_probe_cycles_per_access / quiescent_probe_cycles_per_access
```

---

## 6. Required Run Recipes

Use small smoke sizes first, then paper sizes. The native host used a 320 MiB LLC-domain
reference, so:

```text
25% LLC  =  83,886,080 bytes
53% LLC  = 177,838,489 bytes
100% LLC = 335,544,320 bytes
125% LLC = 419,430,400 bytes
```

### Smoke: static binary and correctness

```bash
./build/cxl_join_bench.gem5 \
  --mode single --policy wb \
  --fact-bytes 16m --hot-bytes 2m \
  --threads 1 --cpu-list 0 \
  --warmups 0 --reps 1 --check
```

### H1 pure-stream input

Use this binary mode if you do not have a separate H1 microbenchmark:

```bash
./build/cxl_join_bench.gem5 \
  --mode stream-smoke --policy wb \
  --fact-bytes 1g \
  --threads 1 --cpu-list 0 \
  --warmups 1 --reps 3
```

For H2, run the same command with simulator-side tagging of `[fact_base,fact_end)` as
`Streaming`. Do not rely on software `nta` for H2.

### Quiescent hot-table baseline

```bash
./build/cxl_join_bench.gem5 \
  --mode probe-workload --policy wb \
  --fact-bytes 1g \
  --hot-bytes 177838489 \
  --threads 16 --cpu-list 0-15 \
  --warmups 1 --reps 3
```

### Loaded morsel baseline

```bash
./build/cxl_join_bench.gem5 \
  --mode morsel --policy wb \
  --fact-bytes 1g \
  --hot-bytes 177838489 \
  --threads 16 --cpu-list 0-15 \
  --morsel 1m \
  --warmups 1 --reps 3 --check
```

### Loaded morsel H2

Run the same morsel command, but tag `[fact_base,fact_end)` as `Streaming` in gem5 and
record the policy as `h2` or `stream` in your output artifact. The hot table must remain
WB/cacheable.

### Suggested final sweep

| Dimension | Values |
|---|---|
| Hot WSS | 25%, 53%, 100%, 125% LLC |
| Cores | 1, 2, 4, 8, 16 |
| Policy | WB, WC, CAT model, H2 |
| Stream memory | local-equivalent and CXL-equivalent if both are modeled |
| Reps | At least 3 for gem5; more if run-to-run variance is visible |

For paper-critical rows, always include the quiescent baseline and loaded WB/H2 in the
same configuration.

---

## 7. The Four Experiments

### Experiment 1: H1 / MLP Kill-Switch

Question: does WB-like streaming bandwidth survive true, overhead-free non-allocation at
realistic MSHR depth, with no LLC as a staging buffer?

Setup:

- Pure stream workload or the dedicated H1 microbenchmark if the gem5 team already has
  one.
- Policies: WB, WC, H2.
- Sweep MSHR depth and L1/L2 prefetcher distance.
- Report sustained per-core read bandwidth and peak MSHR/TBE occupancy.

Pass:

- `H2_BW >= 0.90 * WB_BW` at the frozen realistic MSHR/prefetcher point.
- `H2_BW >= 0.85 * WB_BW` across the sensitivity sweep.
- `H2_BW >= 2.0 * WC_BW` across the sweep.
- H2 must not trend toward the known demand-miss/WC floor around 4.2 GB/s.

Fail/contingency:

- If realization (a) throttles MLP toward WC, test realization (b): a small
  non-allocating stream/fill buffer probed before re-fetch.
- Report the minimum buffer depth that restores `H2_BW >= 0.90 * WB_BW`.
- Do not proceed to Experiments 2-4 until this is resolved.

### Experiment 2: Reproduce And Decompose Morsel Tax

Question: of the morsel tax reproduced from HW, how much is capacity versus contention?

Setup:

- Fused morsel pattern: each worker both streams fact and probes the shared hot table.
- Core counts: 1, 2, 4, 8, 16.
- Hot WSS: at minimum 53% LLC; include 100% and 125% if time permits.

Required gem5 stats:

- Hot-set LLC occupancy over time.
- Stream-line LLC insertions/fills.
- Hot-table LLC misses.
- Per-structure queueing latency for L2, LLC banks, memory controller, and network/mesh.
- Snoop-filter insertion, eviction, lookup count, and peak occupancy.

Report:

```text
extra_cycles = loaded_cycles_per_access - quiescent_cycles_per_access
capacity_cycles = extra_hot_misses_per_access * modeled_miss_cost
contention_cycles = extra_cycles - capacity_cycles
```

This is report-only unless the 53% WB calibration gate fails.

### Experiment 3: H2 Recovery

Question: does overhead-free H2 recover both MPKI and cycles?

Setup:

- Same morsel configurations as Experiment 2.
- Policies: WB, WC, CAT model, H2.

Pass:

- H2 hot-table MPKI is within 10% of quiescent MPKI, or recovers at least 80% of the
  WB-loaded MPKI increase.
- H2 cycles/access are within 10% of quiescent cycles/access, or recover at least 80% of
  the WB-loaded cycle increase.
- H2 stream bandwidth satisfies the Experiment 1 bandwidth gate.

Report any remaining contention honestly. If MPKI recovers but cycles do not, that is a
paper-scope limitation, not a result to hide.

### Experiment 4: Predictor, Portability, Sensitivity

4a. Declaration vs predictor:

- Add a well-tuned RRIP/SHiP bypass-on-dead policy for the aggressor.
- State predictor config and warm-up.
- Compare residual victim tax against H2 on:
  - a phase-changing pattern that defeats warm-up;
  - the fused same-thread/morsel pattern where core-scoped prediction cannot separate
    stream and hot-table accesses.
- Do not use a steady-state pure scan as the only comparison.

4b. Portability:

- Either add an AMD-like per-CCX L3-domain config and show H1/H2 behavior there, or
  explicitly scope the paper to Intel-demonstrated and AMD-argued-by-analogy.

4c. Sensitivity:

- Sweep prefetcher aggressiveness +/-20%.
- Sweep LLC associativity.
- Show Experiment 1 bandwidth and Experiment 3 recovery are not knife-edge.

---

## 8. Output Artifact Contract

Return a directory under the DutyFree repo, for example:

```text
results/gem5/hash_join_h2/
```

with:

```text
config_frozen.md
exp1_h1_mlp.csv
exp2_morsel_decomposition.csv
exp3_h2_recovery.csv
exp4_predictor_sensitivity.csv
run_manifest.json
stats/
```

Required `run_manifest.json` fields:

```json
{
  "git_commit": "<DutyFree commit>",
  "hash_join_path": "benchmarks/e2e/hash_join",
  "gem5_commit": "<gem5 commit>",
  "binary": "build/cxl_join_bench.gem5",
  "frozen_config": "config_frozen.md",
  "runs": [
    {
      "name": "exp3_morsel_53pct_16c_h2",
      "command": "...",
      "policy": "h2",
      "hot_bytes": 177838489,
      "threads": 16,
      "fact_base": "0x...",
      "fact_end": "0x...",
      "stats_path": "stats/exp3_morsel_53pct_16c_h2/stats.txt",
      "stdout_json": "{...}",
      "status": "ok"
    }
  ]
}
```

Required CSV columns:

```text
experiment,config_name,policy,hot_bytes,hot_wss_pct,threads,
stream_memory,quiescent_cycles_per_access,loaded_cycles_per_access,
tax,mpki,stream_bw_gbps,hot_llc_occupancy_bytes,
stream_llc_insertions,sf_insertions,sf_evictions,sf_peak_occupancy,
peak_mshr,peak_tbe,notes
```

Use empty fields for metrics that do not apply to an experiment. Do not silently omit a
required column.

---

## 9. Paper Deliverables

| Deliverable | Paper slot |
|---|---|
| Frozen config + scaling-factor table with validated/scaled points marked | Section 5 gem5 configuration table |
| Per-core BW + peak MSHR/TBE for WB/WC/H2 across MSHR-depth x prefetcher-distance sweep | H1/MLP headline table and Section 4 MLP text |
| Victim recovery table for WB/WC/CAT/H2 | Section 5 hash-join benefit table |
| SF insertion/eviction rate + peak SF occupancy, H2 vs WB | Section 4 snoop-filter discussion |
| Capacity-vs-contention decomposition | Section 5 explanation of morsel tax |
| Predictor head-to-head | Section 5 declaration-vs-predictor comparison |
| AMD-like config or explicit scope statement | Section 5 portability/sensitivity |

Priority:

1. Experiment 1 gates everything.
2. Experiment 2 explains the real-HW tax.
3. Experiment 3 provides the H2 benefit number.
4. Experiment 4 hardens the paper against predictor and portability objections.

---

## 10. Non-Goals

Do not spend gem5 time on:

- Re-running native CXL characterization.
- OS `PROT_STREAMING` implementation cost.
- Linux ranged-exit-drain prototype.
- RocksDB real-silicon magnitude checks.
- Treating software PREFETCHNTA as H2.
- Using CMT/RMID-style occupancy to attribute hot-table versus stream occupancy inside
  one fused worker thread.

---

## 11. Escalation Conditions

Escalate before continuing if:

- H2 stream bandwidth is below 90% of WB at the frozen realistic point.
- The WB 53% calibration tax misses `2.52x..2.62x`.
- The simulator cannot tag `[fact_base,fact_end)` without also tagging the hot table.
- The snoop-filter model is unbounded but the paper text wants an H3/SF-capacity claim.
- H2 recovers MPKI but not cycles after software-prefetch overhead has been removed.
- The scaled geometry has `hot_bytes / private_L2_size < 10x` while the hardware
  reference is much larger than 10x; either rescale L2/LLC/hot together or report the
  fused result as a private-cache-ratio model limitation.

These are not bookkeeping failures; they change the paper claim.
