# Task: Implement the CXL streaming-vs-hot-set E2E benchmark kernel

## Role & context
You are a systems performance engineer building a benchmark for a computer-architecture
paper. Build a single, portable C++17 benchmark that models the paper's central
workload: a **same-thread (and many-thread) columnar hash join** where one relation is
streamed once from CXL memory (immutable, no reuse) while a smaller hash table is
repeatedly probed and must stay resident in the shared LLC.

The paper's thesis, stated precisely so you build the RIGHT experiment:
- The **load-bearing case is SAME-CORE (row C)**: on ONE thread, an immutable
  streaming scan and reuse of an LLC-resident hot table are interleaved in the same
  access stream. Core-scoped cache partitioning (CAT) structurally CANNOT separate
  them, because both live on the same core. This is the case that motivates a new
  memory type.
- The **cross-core case (morsel/multi-thread)** is a secondary amplification: many
  worker cores each stream while sharing one hot table; aggregate stream pressure
  scales with core count. CAT *can* help here (different cores → different classes),
  which is exactly why it is NOT the paper's unique-value case.

Keep these two cases methodologically distinct — they use different metrics and have
different expectations (below). Do not conflate their numbers.

This benchmark serves two consumers from ONE codebase:
1. **Real hardware** — measurement + correctness, using a CXL tier as a zero-core NUMA node.
2. **gem5 syscall-emulation (SE) mode** — the microarchitectural study, where the
   streamed region's address range is tagged "Streaming" (non-allocating) by a harness.

Correctness = the same source, compiled two ways, produces identical join results.

## CRITICAL SCIENTIFIC CONSTRAINTS (read before designing anything)
These prevent the four most likely ways this benchmark could silently measure the
wrong thing. Violating them invalidates the result.

1. **Interference magnitude is a MEASURED OUTPUT, not a validation target.** The
   same-core (row-C) interference has NO prior hardware number — measuring it is the
   point. Do NOT import the paper's cross-core numbers (e.g., "2.03×") as a PASS/FAIL
   band for the single-thread kernel. Only the *platform microbenchmark anchors*
   (bandwidths) and the *L2-resident negative control* are PASS/FAIL.

2. **CMT/`pqos` occupancy is per-RMID (per core/thread), so it CANNOT attribute LLC
   occupancy to the hot table vs. the stream when they share a thread.** Therefore:
   - `single` mode: measure hot-table pressure via **probe MPKI and probe
     cycles-per-access** (a periodically-timed probe-only micro-section), NOT CMT.
   - `morsel` / cross-core mode: CMT/CAT occupancy is valid because the hot structure
     and stream traffic can be attributed across cores/classes.

3. **`nta` (PREFETCHNTA) is a confounded proxy unless stream bandwidth is controlled.**
   PREFETCHNTA is a *software* prefetch and does NOT train the L2 hardware stream
   prefetcher, so the `nta` stream typically runs SLOWER than `wb`. Lower stream
   bandwidth reduces pressure independently of allocation, which would fake a benefit.
   Therefore: always report `wb` vs `nta` **stream bandwidth side-by-side**, and treat
   `nta` protection of the hot set as a **LOWER BOUND** valid only when interpreted
   at matched-or-lower stream BW. State this in the output.

4. **CAT's expected role is mode-dependent, and single-mode CAT "failure" is a RESULT,
   not a bug.**
   - `morsel`/cross-core: CAT is the success control (stream → few disjoint ways,
     hot set → the rest); expect the hot set protected at full stream BW.
   - `single`/same-core: CAT can only place the whole thread in one class, so it
     CANNOT protect the hot table from the thread's own stream. Expect it to FAIL to
     help. This is the on-silicon demonstration of CAT's inadequacy — record it, do
     not "fix" it.

## Definition of done (acceptance criteria)
Complete when ALL hold:
- [ ] One kernel builds natively (`-O3 -march=native`) and for gem5 (`-DGEM5`, static).
- [ ] Join aggregate is **bit-identical** across policies, thread counts, and
      native-vs-gem5, verified against a scalar reference. Use **integer** keys and
      **integer** measures with a deterministic reduction order so bit-identity is
      actually achievable under parallelism (no floating-point aggregation).
- [ ] A microbenchmark confirms the streamed region is physically on the CXL node and
      sustains CXL-class bandwidth (see Environment). ABORT with a clear error if the
      region is NOT on the CXL node or bandwidth is out of band (i.e., we accidentally
      hit local DRAM).
- [ ] The single-core (row-C) experiment produces a clean `wb` vs `nta` comparison:
      probe MPKI / probe cycles-per-access and overall join throughput, WITH stream
      bandwidth reported for both. (Magnitude is measured, not asserted.)
- [ ] The cross-core (morsel) experiment reproduces the DIRECTION of the interference:
      hot-set-bound slowdown under `wb`, recovered under `cat`, at full stream BW.
      (Direction + rough magnitude only; not a tight band.)
- [ ] The L2-resident negative control (~2 MB hot set) shows ~1.0× (pathway runs
      through shared LLC, not private caches). This IS a PASS/FAIL check.
- [ ] A validation harness prints a PASS/FAIL table for the *platform anchors + negative
      control only*, plus a separate MEASURED-RESULTS table for interference; exits
      non-zero on any anchor/control FAIL.
- [ ] Reproducible: pinned threads, fixed seeds, JSON per-run output, and a
      machine-readable config dump (every knob, plus the fact region's [base,base+len)).

## Environment (the dev machine)
- CPU: Intel Xeon (Sapphire Rapids / Emerald Rapids class), **non-inclusive LLC** +
  snoop filter. `performance` governor and turbo OFF for measurement; harness must
  check and WARN if not.
- **CXL memory = zero-core NUMA node, node 2** (memory-only). Compute cores on node 0.
  Verify with `numactl -H` at startup; assert node 2 has 0 CPUs and nonzero memory.
- Allocation:
  - Fact (stream) region MUST bind to node 2 (`numa_alloc_onnode(2)` or `mmap` +
    `mbind(MPOL_BIND, node 2)`). Bind THREADS to node 0.
  - Hot (hash table) + all working state on node 0.
  - Support 2 MB hugepages (preferred) and 4 KB pages for the fact region (flag).
- Tools (detect at runtime; if a required one is missing or needs privileges you lack,
  STOP and ask — do not silently skip a measurement):
  - `numactl`, `libnuma`.
  - `perf stat` (uncore CHA / offcore / `mem_load_l3_miss_retired`, `LLC-load-misses`).
  - Intel PCM and/or `pqos` (RDT). Use **CMT** for per-class LLC occupancy ONLY in
    cross-core mode (see constraint #2). Use **CAT** via `pqos`/resctrl as a policy.
- Phase-0 smoke test: a STREAM-like probe bound to node 2 (threads on node 0),
  reporting per-core and aggregate CXL bandwidth, BEFORE building the full workload.

## Platform anchors (PASS/FAIL bands; ±20% unless noted)
These are microbenchmark properties of the machine, independently trustworthy:
- Single-core sequential WB read from node 2 (CXL): ~15.8 GB/s (UPPER anchor).
- Single-core CXL read on the demand-miss-limited path: ~4.2 GB/s (LOWER anchor).
- Local DRAM (node 0) single-core WB read: markedly higher than CXL. If the "CXL"
  region reads at local-DRAM speed, binding failed → ABORT.
- Negative control: L2-resident hot set (~2 MB) → ~1.0× (PASS/FAIL).

## Measured outputs (NOT validation targets — report, do not tune to)
- Single-core (row-C): probe MPKI, probe cycles-per-access, join throughput, and
  stream BW, for `wb` vs `nta` (and `cat` as the negative demonstration).
- Cross-core (morsel): hot-set slowdown and hot-table CMT occupancy for `wb` vs `cat`,
  with stream BW.
- If any measurement disagrees with an anchor band, report the discrepancy and STOP —
  that is a finding, not a bug to paper over.

## Workload specification
### Data model (star-schema join)
- **Dimension → hash table (HOT set / victim).** Open-addressing (linear-probing)
  table of fixed-size **integer** entries (8-byte key + 8-byte integer payload). Size is
  a first-class knob `--hot-bytes`; support values in the "LLC band" (> L2 = >2 MB; and
  25% / 53% / 100% of LLC), plus the 2 MB L2-resident size for the negative control.
- **Fact relation → streamed probe side (stream/aggressor).** Large array of
  (foreign_key:int, measure:int) tuples, `--fact-bytes` (GB-scale), on node 2, read
  exactly ONCE sequentially. FKs drawn (fixed seed) so a controllable fraction hit the
  table (`--hit-rate`).
- Scalar reference join computes ground-truth aggregate (integer SUM(measure) over
  matches + match count) for bit-identical validation.

### Kernels
- **Inner loop (vectorized/pipelined):** iterate fact tuples in batches (`--vector`,
  e.g., 1024); per tuple: hash FK → probe → integer-aggregate. This interleaves the
  immutable stream with hot-table reuse on the SAME thread (row C).
- **Probe-timing micro-section:** periodically time a probe-only window (no new stream
  loads) to derive probe cycles-per-access and MPKI, so single-mode hot-table pressure
  is measurable without CMT.
- **Modes:**
  - `single`: one thread, scan+probe (headline same-core case).
  - `morsel`: N worker threads pinned to node 0, each pulls morsels of the fact array
    and probes the SHARED table (`--morsel`). Cross-core amplification.

### Allocation policies `--policy`
- `wb`     : plain cacheable loads of the fact stream (baseline; pollutes LLC).
- `nta`    : `_mm_prefetch(..., _MM_HINT_NTA)` issued `--pf-distance` ahead of the fact
             stream; normal loads follow. On this non-inclusive server LLC, PREFETCHNTA
             brings the line to the private cache and does NOT populate shared L3 — the
             real-hardware proxy for non-allocation. CONFIRM this by checking the
             stream's LLC occupancy is near-zero (cross-core) or via reduced probe MPKI
             (single). Report `nta` stream BW next to `wb` (constraint #3).
             Do NOT use MOVNTDQA/streaming loads on WB memory — the NT hint is a no-op
             on WB; the effect must come from PREFETCHNTA. A true WC path is a separate
             `wc` flag and is OUT OF SCOPE unless you ask first.
- `cat`    : partition LLC ways via `pqos`/resctrl. Role is mode-dependent (constraint
             #4): success control in `morsel`; negative demonstration in `single`.
- `stream` : gem5-only. Fact region tagged Streaming (non-allocating). On native builds
             this policy is compiled out or aliases `wb` with a loud warning.

## Portability: real HW + gem5 (single source)
Abstract three things behind a thin interface:
1. Fact-region allocation: native → `numa_alloc_onnode(2)`; gem5 → plain `mmap` of a
   region the harness tags.
2. ROI markers: native → `rdtscp`/`clock_gettime`; gem5 → `m5_work_begin/end` +
   `m5_dump_reset_stats` (guard with `#ifdef GEM5`, link the m5 op lib).
3. Policy application: `stream` only under gem5; `nta`/`cat`/`wb` on native.

**gem5 SE has no NUMA/RDT/perf syscalls.** The ENTIRE measurement/validation harness is
native-only; the gem5 build runs only the kernel under m5 stats and dumps the fact
region bounds. Guard every `numactl`/`libnuma`/`mbind`/`get_mempolicy`/`perf`/`pqos`
call behind `#ifndef GEM5` so the static gem5 binary links cleanly.

Build both from one `CMakeLists`/`Makefile`: `make native` and `make gem5`.

## Measurement & validation harness (critical deliverable)
For each (policy, mode, hot-size, fact-size, thread-count):
- Confirm fact-region NUMA placement (`get_mempolicy`/`move_pages`/`/proc/self/numa_maps`)
  → ABORT if not node 2.
- Measure: join throughput (fact-rows/s + derived stream GB/s), probe cycles-per-access
  and MPKI (single mode), hot-table + stream CMT occupancy (cross-core mode only),
  LLC-load-misses, achieved stream BW from node 2 (CHA/PCM), ROI time.
- Run N reps (default 30), report median + coefficient of variation; WARN if CoV > 2%.
- Emit TWO tables: (a) PASS/FAIL for platform anchors + negative control (exit non-zero
  on FAIL); (b) MEASURED interference results (no pass/fail). Fail examples for (a):
  stream BW ≈ local DRAM (binding broke); negative control not ~1.0×.
- Output JSON (one record per run) + human-readable summary.

## Process (follow in order; checkpoint at the marked steps)
1. **Plan first.** Write PLAN.md: file layout, the portability interface, the run
   matrix, and the exact perf/pcm/pqos commands. List every environment assumption you
   could NOT verify and surface it. **STOP and report before coding.**
2. Write tests FIRST for: (a) the scalar reference join, (b) the NUMA placement
   assertion. These must run in CI-like fashion after every later phase.
3. **Phase 0 smoke test:** parse `numactl -H` + STREAM-like read bound to node 2.
   Confirm CXL bandwidth in-band. **STOP and report the numbers; do not proceed on FAIL.**
4. Scalar reference join + bit-identical result validation (integer aggregation).
5. Hash table + vectorized probe + probe-timing micro-section (single mode, wb policy).
6. NUMA-node-2 fact allocation + placement assertion.
7. Policies `nta`, `cat`; then `morsel` mode. **Checkpoint: report wb-vs-nta (single)
   and wb-vs-cat (morsel) before continuing.**
8. gem5 build path + m5 ROI markers + region-bounds dump.
9. Measurement/validation harness (two tables).
10. RESULTS.md: the PASS/FAIL anchor table + the measured row-C (wb-vs-nta) and
    cross-core (wb-vs-cat) comparisons at 53% WSS.

## Guardrails / non-goals
- Do NOT implement the kernel `PROT_STREAMING` OS prototype — separate effort; `stream`
  is gem5-tag-only here.
- Do NOT invent bandwidth/latency numbers — measure and compare to anchor bands.
- Do NOT tune parameters to hit any number. If measurements disagree with anchors,
  report and STOP — a finding, not a bug.
- Do NOT use CMT to attribute occupancy within a single thread (constraint #2).
- Do NOT treat single-mode CAT's failure-to-help as a bug (constraint #4).
- Prefer clarity/reproducibility over micro-optimizing the join.
- Ask before: enabling any WC path, changing governor/turbo, or anything needing root
  beyond `perf`/`pqos` setup.

## What to return
- The code, PLAN.md, RESULTS.md (PASS/FAIL anchor table + measured comparisons), and the
  exact reproduction commands. Flag every place a measurement fell outside an anchor band
  or where a control behaved unexpectedly.
