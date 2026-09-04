# Pre-registration — window-scoped aggregate bandwidth, 2026-09-03

## Why this campaign exists

`AGGBW_VALIDITY_2026-09-03.md` re-audited the headline metric of the
multi-core H1 bandwidth campaign, `agg_bw_sum` (the sum over instances of each
instance's own 8 MiB divided by its own self-timed window). It found three
things, all from the completed artifacts and none of them requiring a new run:

1. The `h2_8c` cell's 132.9% of its realized CXL ceiling is **not** evidence
   of window stagger. It is what a metric reports when only ~44% of the bytes
   it counts cross the capped controller, the rest being served out of a
   40 MiB LLC that is ~94–100% occupied by dirty fact-array lines deposited
   during `fill_fact` and never evicted, because the STREAMING policy bypasses
   the read stream's own clean fills.
2. Window phase **is** reconstructable from the completed artifacts, to within
   a few microseconds, via per-CPU `numCycles` plus each instance's own
   `seconds`. The eight measured windows overlap for 84–99% of the narrowest
   window and the all-N-concurrent intersection is non-empty in every one of
   fifteen cells. `agg_bw_sum` is high by 2.4–16.7%, not by "at least 1.329x".
3. The reconstruction rests on one assumption — that the post-window epilogue
   costs each instance the same simulated time — which is validated but not
   proven, and it cannot be extended to in-window *traffic*, because
   `stats.txt` carries exactly one section per run.

**The question this campaign answers: do the published H2-over-WB ratios and
the `H2 >= WB > pfoff` ordering hold when the aggregate is computed over a
measured, timestamped concurrent window rather than over a sum of
unsynchronised per-instance windows?**

It is registered as a *confirmation* campaign. The prior document's answer is
that the ratios are floors and that no re-run is required to protect them.
This campaign exists to remove the one assumption that answer rests on, and to
deliver the windowed traffic counters that two prior campaigns asked for and
neither had.

## The barrier both prior documents specify cannot be built

`H1BW_MULTICORE_OUTCOME_2026-09-03.md` and `H1BW_CXLBW_OUTCOME_2026-09-03.md`
both prescribe the same fix:

> a cross-process barrier immediately before the measured pass — a shared
> anonymous mapping with an atomic arrival counter, spinning on
> `__builtin_ia32_pause()` and **not** `sched_yield()`

**That construct does not work in gem5 SE multi-program mode, and this
document is the first to say so.** Read from the source that is compiled into
the binary in use:

| mechanism | status in this SE build | source |
|---|---|---|
| `mmap(MAP_SHARED\|MAP_ANONYMOUS, PROT_WRITE)` | mapped, but **writes are not propagated to other mappings** | `src/sim/syscall_emul.hh:2055`, `warn_once("mmap: writing to shared mmap region is currently unsupported…")`; the comment above it states "there's no structure which maintains information about which virtual memory areas are shared" |
| `shmget` (29), `shmat` (30), `shmdt` (67) | **no handler** -> `unimplementedFunc` | `src/arch/x86/linux/syscall_tbl64.cc:82,83,120`; `SyscallDescABI(num, name)` defaults to `unimplementedFunc` (`src/sim/syscall_desc.hh:180`) |
| `memfd_create` (319) | **no handler** -> `unimplementedFunc` | `src/arch/x86/linux/syscall_tbl64.cc:376` |
| `unimplementedFunc` behaviour | `fatal("syscall %s (#%d) unimplemented.")` | `src/sim/syscall_emul.cc:77` |

The N instances in this harness are not forked; they are N independent
`Process` objects that `se.py` builds from `--cmd=a;b;c` and assigns one per
CPU, each with its own page table. An arrival counter written by instance 0
into a `MAP_SHARED|MAP_ANONYMOUS` page is **invisible** to instances 1..N-1, so
every instance would spin forever on a counter that never advances — the exact
livelock class the prescription was written to avoid, arrived at by a
different route. Making it work is a change to `src/sim/syscall_emul.hh`,
which requires the `gem5.opt` rebuild this work is forbidden to perform.

The barrier that *does* exist in the benchmark is not a counter-example.
`run_fs_e2e_calibrate()` (`cxl_join_bench.cpp:1435`) does exactly what the
prescription describes — `MAP_SHARED|MAP_ANONYMOUS`, `std::atomic<int> ready/go`,
`wait_for_go()` spinning on `__builtin_ia32_pause()` — and it works because it
is `#ifdef GEM5_FS`, `fork()`s, and runs under a real guest kernel. It cannot
be lifted into SE multi-program mode.

**What replaces the barrier here is not a weaker version of it. It is a
different and, for this question, stronger instrument:**

- **Window bracketing timestamps every boundary.** A stats dump/reset pair at
  each end of the measured loop makes each instance's window start and end
  available as an absolute simulated tick, read out of `stats.txt`. Overlap
  stops being assumed, bounded or reconstructed, and becomes *measured*. A
  barrier would have forced the windows to coincide; bracketing tells you
  whether they did, which is the question actually being asked.
- **`--reps 8` shrinks the stagger by construction.** The start skew is set by
  the setup phase and is 36–353 us across the six baseline cells. It does not
  grow with the number of reps, while the window does. At `--reps 1` the
  measured window is 1.32–2.64 ms and the overlap floor is 84–99%; at
  `--reps 8` the window is ~8x longer against the same skew and the overlap
  floor is >=97% arithmetically, before any synchronisation. It also retires
  the `cov == 0` / `n = 1` limitation that both prior campaigns listed as not
  licensed.

A host-file barrier **is** implementable — `openat` (257), `pread64` (17),
`pwrite64` (18) and `ftruncate` (77) all carry real handlers against the host
filesystem — and it is registered below as an **optional** arm, not a primary
one, because a spin loop across emulated syscalls is precisely the construct
that cost five arms in r6b/r6e. `flock` (73) and `fsync` (74) have no handler
and must not appear in it.

## What changes, and where

Three files. None of them is under `gem5/src/`, and **no gem5 rebuild is
required**: the two m5 ops involved are already decoded by the binary in use.

### 1. `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp` — `run_stream()`

The measured loop is `cxl_join_bench.cpp:1190-1196`. Bracket it, and emit a
marker on stderr on each side so the analyzer can pair stats sections with
instances:

```
  getrusage(RUSAGE_SELF, &ru_before);
  std::vector<double> samples;
  samples.reserve(c.reps);
  double total_sec = 0.0;
+ // Window-scoped counters.  The k-th AGGBW_WINDOW_* marker in console.log is
+ // the k-th stats section boundary in stats.txt: stderr and the stats dumps
+ // are both ordered by simulated time, and the OPEN marker precedes its op
+ // while the CLOSE marker follows its op.
+ std::cerr << "AGGBW_WINDOW_OPEN cpu=" << cpus[0] << " reps=" << c.reps << "\n";
+ gem5_dump_stats_now();
+ gem5_reset_stats_now();
  for (int r = 0; r < c.reps; ++r) {
    ...
  }
+ gem5_dump_stats_now();
+ gem5_reset_stats_now();
+ std::cerr << "AGGBW_WINDOW_CLOSE cpu=" << cpus[0] << " seconds="
+           << std::setprecision(9) << total_sec << "\n";
  getrusage(RUSAGE_SELF, &ru_after);
```

**`gem5_dump_stats_now()` and `gem5_reset_stats_now()` already exist in this
file** (`cxl_join_bench.cpp:218` and `:211`), are already used by
`run_join()`/`run_morsel()`/`run_fs_e2e_join()`, and encode `M5OP_DUMP_STATS`
= 0x41 and `M5OP_RESET_STATS` = 0x40. Both are handled in the binary:
`include/gem5/asm/generic/m5ops.h:59-60`, dispatched at
`src/sim/pseudo_inst.hh` `case M5OP_RESET_STATS` / `case M5OP_DUMP_STATS`, and
implemented at `src/sim/pseudo_inst.cc:318` / `:332`. **No new op byte
sequence is introduced.** `M5OP_DUMP_RESET_STATS` = 0x42 is also present
(`m5ops.h:61`, `pseudo_inst.cc:346`) and is an exact equivalent as a single
op; the existing pair is specified instead purely because it is already
exercised by this binary.

The bracketing works because `simTicks` is reset by the dump/reset pair:
`Root::RootStats::resetStats()` sets `startTick = curTick()`
(`src/sim/root.cc:107-110`) and `simTicks` is the functor
`curTick() - startTick` (`root.cc:83`). Each section's `simTicks` is therefore
the length of the interval since the previous reset, and a cumulative sum over
sections recovers the absolute tick of every boundary.

Nothing else in `run_stream()` moves. `bytes`, `total_sec`,
`bandwidth_gbps` and the emitted JSON keep their present definitions, so
`agg_bw_sum` remains computable and directly comparable to the published
figures. Two further additions to the JSON, for the same reason:

```
+ std::cout << "\"window_reps\":" << c.reps << ",";
+ std::cout << "\"window_seconds_each\":"; emit_samples(samples);   // already emitted
```

### 2. `experiments/asplos/run_h1bw_multicore.sh`

- `REPS=1` (line 51) becomes `REPS=${REPS:-1}`.
- The output directory gains the reps tag so no bracket can collide:
  `h1bw_mc_${arm}_${n}c_l3x${slices}_bw${BW_TAG}_r${REPS}_$STAMP` (line 89).
- `"prereg"` (line 117) becomes
  `"experiments/asplos/${PREREG:-H1BW_MULTICORE_PREREG_2026-09-03.md}"` and
  this campaign sets `PREREG=AGGBW_WINDOW_PREREG_2026-09-03.md`. The CXLBW
  outcome flagged the hard-coded path as a provenance hazard; this fixes it.
- `MANIFEST.json` already records `"reps": $REPS`; nothing to add.

With `REPS` unset the generated `config.ini` is unchanged, so
`prove_default_unchanged.sh` still passes byte-for-byte. `--reps` is a guest
program argument and does not appear in `config.ini` at all.

### 3. `experiments/asplos/analyze_aggbw_window.py` (new)

`analyze_h1bw_bracket.py` and `analyze_h1bw_multicore.py` are **left
untouched** so they continue to certify the completed campaigns. The new
analyzer:

- splits `stats.txt` on `Begin Simulation Statistics`, requires exactly
  `2N + 1` sections, and cumulative-sums each section's `simTicks` to absolute
  boundary ticks;
- pairs boundary k with the k-th `AGGBW_WINDOW_{OPEN,CLOSE}` marker in
  `console.log`, giving each instance's window as an absolute
  `[start_tick, end_tick]`;
- reports, per cell: `agg_bw_sum` (unchanged definition, for comparability),
  `agg_bw_union` = total bytes / (max end - min start), `agg_bw_isect` = bytes
  delivered inside the all-N intersection / intersection length, the
  intersection length as a fraction of the narrowest window, and the
  reconstruction residual against the `numCycles` method of
  `AGGBW_VALIDITY_2026-09-03.md`;
- reports in-window `mem_ctrls1.bytesRead`/`bytesWritten`, HNF
  `ReadShared.I.RU` / `ReadShared.{UC,UD}.*` and `ReadUnique_PoC.I.RU`,
  summed over the sections that lie inside the intersection, so the
  CXL-served share of the stream and the controller traffic per useful byte
  become **windowed** quantities for the first time;
- asserts `mem_ctrls0` still carries no non-zero counter other than
  `power_state.pwrStateResidencyTicks`.

Nothing under `gem5/logs/` is written. `gem5/configs/` is not touched —
this campaign needs no config change at all, capped arms excepted, where
`CXL_MEM_BW` uses the already-merged `configs/ruby/Ruby.py` path registered in
`H1BW_CXLBW_PREREG_2026-09-03.md`.

## Frozen configuration

Identical to `H1BW_MULTICORE_PREREG_2026-09-03.md` in every respect except
`reps`. Restated so this document stands alone.

| parameter | value |
|---|---|
| CPU | O3CPU, requested 1.9 GHz, realized 1.9011407 GHz (526 ticks) |
| L1d / L1i | 48 KiB 12-way / 32 KiB 8-way |
| L2 | 2 MiB / 16-way |
| L3 (HNF) | 5 MiB / 20-way per slice, `--num-l3caches=N` (20 MiB at 4c, 40 MiB at 8c) |
| directories | `--num-dirs=1` |
| memory | `SimpleMemory`, DRAM 98 ns, CXL 203 ns, `latency_var=0` |
| DRAM range bandwidth | untouched: 2 ticks/byte = 500 GB/s |
| CXL range bandwidth | 2 ticks/byte (uncapped arms) / 31 ticks/byte = 32.2581 GB/s (capped arms) |
| `L1_MSHR` | 48 |
| `L1_REPL` | 16 (default, left unset; a live confound, recorded not endorsed) |
| stream size | 8 MiB per instance, `--fact-node 1` |
| `ALL_CXL` | 1 |
| warmups | 1 |
| **reps** | **8** (was 1) |
| `--threads` | 1 (parsed and not applied; recorded, see F9 note below) |
| `--hot-node` | 0 (parsed and **not applied** in `stream-smoke`; see below) |

Two requested-versus-realized traps are recorded here so they are not
re-inherited. Neither affects this campaign, because neither knob is used.

- **`--threads` is parsed and never applied** in `run_stream()`
  (`cxl_join_bench.cpp:1154` pins one CPU and spawns no threads). Already
  logged in `H1BW_MULTICORE_OUTCOME_2026-09-03.md`.
- **`--hot-node` is parsed and never applied** in `run_stream()`. `hot_node`
  is read at `cxl_join_bench.cpp:2859`, echoed into the JSON at `:1106`, and
  used by no allocation on the `stream-smoke` path: the hot table and key
  vector are `std::vector`s on the ordinary heap and never pass through
  `alloc_bytes`/`gem5_bind_pool`. With `ALL_CXL=1` every process's default
  pool is 1, so **there is no local-DRAM traffic in this harness at all** —
  confirmed in all 21 completed cells, where `system.mem_ctrls0` emits exactly
  one non-zero counter and it is `power_state.pwrStateResidencyTicks`. First
  recorded in `AGGBW_VALIDITY_2026-09-03.md`.

## Arms

| arm | policy | prefetch | CXL bandwidth |
|---|---|---|---|
| `wb` | `wb` | on | 2 ticks/byte |
| `h2` | `stream` | on | 2 ticks/byte |
| `pfoff` | `stream` | **off** (`PF_OFF_CORES=0..N-1`) | 2 ticks/byte |

Three arms x two core counts (4, 8) = **six primary cells**.

**Optional arm set A — capped confirmation, 8 cores only, three cells.**
`CXL_MEM_BW=32258064516B/s` (31 ticks/byte, 32.2581 GB/s). This is the cell
set in which the metric contradiction appeared, and windowed counters are what
turn `AGGBW_VALIDITY`'s one-sided bound on the CXL-served share into a
measurement. Run it if host capacity allows; it is the highest-value optional
addition. Nine concurrent single-threaded gem5 processes on a 256-core,
1.1 TiB host is not a resource constraint.

**Optional arm set B — host-file barrier, NOT registered as a primary arm.**
A `--barrier-file <path>` option in which each instance `pwrite64`s one byte
at offset `cpu`, then `pread64`s the whole array until all N bytes are
non-zero, bounded at a fixed iteration count and calling `m5_fail` on timeout
rather than spinning. Registered so that, if it is built, it is built to a
committed shape. **It must not be added to the primary arms**, because it
changes the instruction stream of the setup phase and would make the primary
cells non-comparable to the six published ones. If arm set B runs, it runs as
a separate cell triple and is compared against the primary cells, not
substituted for them.

`pfoff` **is not write-combining.** It is `policy=stream` with the L1D/L2
prefetchers disabled. Restated so the `Appendix.tex:568-572` mislabel is not
re-inherited.

## Metrics

Four aggregate rates per cell. The first is unchanged from the published
campaigns so the comparison is direct; the other three are new and are the
reason for the campaign.

| metric | definition | role |
|---|---|---|
| `agg_bw_sum` | sum of per-instance `bandwidth_gbps` | the published metric, recomputed unchanged; the **upper** end of the interval |
| `agg_bw_isect` | bytes delivered inside the all-N intersection / intersection length | the **windowed concurrent rate**; the headline of this campaign |
| `agg_bw_union` | total bytes / (max window end - min window start) | the episode average; the **lower** end of the defensible interval |
| `agg_bw_disjoint` | total bytes / sum of window lengths | the rigorous floor under arbitrary stagger; reported for completeness only |

`agg_bw_wall` remains **retired** and is not computed.

Additionally recorded per cell, all read back from `config.ini` or from the
bracketed `stats.txt` sections, never from `MANIFEST.json`:

- absolute window start and end tick for every instance, and the pairwise
  overlap matrix;
- the intersection length as a fraction of the narrowest window;
- **in-window** `mem_ctrls1.bytesRead` and `bytesWritten`, and controller
  bytes per useful byte — the quantity `H1BW_CXLBW_OUTCOME_2026-09-03.md`
  could only bound one-sidedly;
- **in-window** CXL-served share of the stream, from HNF `ReadShared.I.RU`
  against `ReadShared.{UC.UC_RU, UD.UD_RU}`;
- in-window HNF read transaction latency and TBE / L1-MSHR occupancy, so the
  `concurrency x 64 B / latency` decomposition is finally computed on windowed
  rather than whole-program counters;
- `cov` per instance across the 8 reps, and the across-instance spread, so a
  3% effect finally has an error bar;
- realized CXL and DRAM ticks/byte, realized slice count and LLC bytes,
  `E_clean` engagement per arm.

## Pre-declared outcomes

Encoded as `AGGBW_PREDICTION` in `analyze_aggbw_window.py` and checked
mechanically, so the result confirms or refutes them rather than being
narrated afterwards. The predictions are derived from the window
reconstruction in `AGGBW_VALIDITY_2026-09-03.md` scaled to `--reps 8`.

| quantity | 4 cores | 8 cores |
|---|---|---|
| intersection / narrowest window | **>= 0.97** | **>= 0.96** |
| `agg_bw_isect` / `agg_bw_sum` | **0.97–1.03** | **0.95–1.03** |
| `agg_bw_union` / `agg_bw_sum` | **0.96–1.00** | **0.95–1.00** |
| `h2/wb` on `agg_bw_isect` | **1.24–1.36** | **1.38–1.48** |
| `wb/pfoff` on `agg_bw_isect` | **1.38–1.55** | **1.10–1.16** |
| in-window CXL bytes read per useful byte, `h2` | 0.35–0.55 | **0.35–0.55** |
| in-window CXL bytes read per useful byte, `pfoff` | 0.35–0.55 | **0.35–0.55** |
| in-window CXL bytes read per useful byte, `wb` | 0.65–1.10 | **0.65–1.10** |

The last three rows are the sharpest test in the campaign, because they are a
direct measurement of a quantity that has so far only been bounded. If the
in-window CXL read share for `h2_8c` comes in near 1.0 rather than near 0.44,
then `AGGBW_VALIDITY`'s resolution of the 132.9% reading is wrong, the
stagger inference of `H1BW_CXLBW_OUTCOME_2026-09-03.md` is reinstated, and
every 8-core magnitude is unpublishable. That is the outcome this campaign is
run to expose, and it is stated with the same weight as the expected one.

### What confirms that the published ratios are safe

**CONFIRMED — the published ratios stand as floors, and the +25% / +39%
margins may be published as written** if all four hold:

1. the ordering `H2 >= WB > pfoff` holds on `agg_bw_isect` in every cell;
2. `h2/wb` on `agg_bw_isect` is **>= 0.98x** the published `agg_bw_sum` ratio
   (1.2500 at 4c, 1.3917 at 8c) — i.e. the windowed metric does not reduce the
   H2 advantage;
3. `agg_bw_isect / agg_bw_sum >= 0.95` in every cell, so the published
   magnitudes are within 5% of a measured concurrent rate;
4. the reconstruction residual — `AGGBW_VALIDITY`'s `numCycles`-derived window
   boundaries against the bracketed ground truth — is **< 2% of the window**
   in every instance, which retroactively certifies the reconstruction and
   with it the interval already published for the completed cells.

### What refutes it

**REFUTED — the published ratios must be restated on the windowed metric
before submission** if any of:

- `h2/wb` on `agg_bw_isect` falls **below 0.95x** the published value in any
  cell, or inverts below 1.0;
- the ordering `H2 >= WB > pfoff` fails on `agg_bw_isect` in any cell;
- `agg_bw_isect / agg_bw_sum < 0.85` in any cell, i.e. `agg_bw_sum` is high by
  more than 15% even at `--reps 8`;
- the N open-boundaries do **not** all precede the N close-boundaries in any
  cell, i.e. the windows genuinely failed to overlap. This is a *result*, not
  a void: the analyzer reports the measured non-overlap and the cell's
  `agg_bw_sum` is then known to be inflated by a measured factor.

A refutation is publishable and is the reason the campaign is worth ~4 h. It
would mean the paper quotes `agg_bw_isect`, not `agg_bw_sum`, and restates the
margins accordingly.

## Gates

Fail-closed. A cell failing any gate is printed VOID and contributes no
number. Enforced by `analyze_aggbw_window.py`; the two existing analyzers are
untouched.

- **G1** — every instance reports `status: "ok"`.
- **G2** — realized instance count equals N.
- **G3** — realized LLC equals `slices x 5 MiB` and the realized slice count
  equals the declared bracket, both counted from `config.ini`.
- **G4** — realized `mem_ctrls1.bandwidth` equals the pre-registered integer
  ticks/byte for the cell (2 for the primary arms, 31 for optional set A), and
  realized `mem_ctrls0.bandwidth` equals 2. Read back from `config.ini`, never
  from `MANIFEST.json`.
- **G5** — declared policy measurably engaged: `wb` exactly 0
  `streamingHnfFillBypasses`; `h2` `E_clean` in 80–95%; `pfoff` `E_clean` in
  94–98%. Bands from the twenty-one completed cells. A cell outside its band
  is VOID, as at one slice.
- **G6 (new)** — `stats.txt` contains exactly `2N + 1` sections, and
  `console.log` contains exactly N `AGGBW_WINDOW_OPEN` and N
  `AGGBW_WINDOW_CLOSE` markers. Any other count means the bracketing did not
  fire on every instance and the cell is VOID. This is the gate the campaign
  exists to satisfy and it must not be relaxed.
- **G7 (new)** — reconstructed boundary ticks strictly increasing, and every
  instance's bracketed window length agrees with its own reported `seconds`
  to within **0.5%**. A disagreement means the ops did not land where the
  source puts them.
- **G8 (new)** — `--reps` realized: every instance's `samples` array has
  exactly 8 entries and its `cov` is finite. `cov == 0` at `--reps 8` means
  the reps did not run.
- **G9 (new)** — placement unchanged: `system.mem_ctrls0` carries no non-zero
  counter other than `power_state.pwrStateResidencyTicks`. Any local-DRAM
  traffic means the pool assignment moved and the cell is not comparable to
  the published ones. VOID.
- **G10 (new)** — useful bytes identical across arms: every instance in every
  cell reports `fact_bytes == 8388608` and `warmups == 1`. The ratio argument
  requires that all three arms move the same number of bytes through their
  measured windows, and this gate is what makes that a checked fact rather
  than an assumption.

## Expected runtime and cost

Observed on `mos181`, from each cell's own `MANIFEST.json` `started` and
`DONE.json` `ended`: **4-core cells 1.322–1.432 h** (mean 1.37), **8-core
cells 2.953–3.225 h** (mean 3.11), with three to twelve arms running
concurrently and no measurable interference between them.

`--reps 8` adds seven extra measured passes. The measured pass is 1.6–2.8% of
simulated time at `--reps 1`, so seven more of them add 9.4–17.7 ms of
simulated time to an 83–91 ms program, i.e. **+11% to +20% of simulated
ticks**. The measured pass is also the highest-miss-rate phase, so host
seconds per simulated tick there is above the program average; budget **+25%**
rather than +20%.

| set | cells | per-cell estimate | wall (concurrent) |
|---|---|---|---|
| primary 4c | 3 | 1.37 x 1.25 = **1.7 h** | 1.7–2.0 h |
| primary 8c | 3 | 3.11 x 1.25 = **3.9 h** | 3.9–4.4 h |
| **primary total, six cells concurrent** | **6** | — | **3.9–4.4 h** |
| optional set A (capped 8c) | 3 | **3.9 h** | absorbed, wall unchanged |
| **all nine cells concurrent** | **9** | — | **4.0–4.5 h** |

**Budget 5 h wall for all nine cells**, launched in one batch. Nothing here
requires serialisation.

Storage: `stats.txt` is 4.9 MB / 33,978 lines for a single-section 8-core
cell. At `2N + 1 = 17` sections it becomes **~83 MB / ~578k lines** per 8-core
cell and ~43 MB per 4-core cell, so **~0.7 GB** for nine cells. This is the
one real cost of the bracketing and it is accepted; the analyzer streams
`stats.txt` rather than loading it.

## What this campaign cannot settle

- **It does not synchronise the windows.** No cross-process barrier exists in
  gem5 SE and none can be added without a `src/` change. The campaign measures
  the overlap instead of imposing it, and shrinks it with `--reps`. If a
  future campaign needs imposed synchronisation it needs either FS mode or the
  `syscall_emul.hh` shared-mapping work, and both are larger than this.
- **It does not make `SimpleMemory` a CXL link model.** `latency_var` remains
  0; no flit protocol, no retry, no per-direction asymmetry.
- **It does not fix the LLC-residency confound.** The 40 MiB LLC will still be
  ~94–100% occupied by `fill_fact`'s dirty lines and will still supply roughly
  half of the `h2` and `pfoff` read stream. The campaign *measures* that share
  in-window instead of bounding it; removing it needs a different benchmark
  geometry (a scrub between `fill_fact` and the passes, or a working set
  several times the LLC), which is a separate pre-registration and is the
  single highest-value follow-up. Nothing in this campaign should be read as
  establishing that these runs measure far-memory streaming bandwidth.
- **The sibling rebuild has already landed, and this is a blocking condition
  on G5.** At the time of writing, `gem5/build_Intel_8592/gem5.opt` has
  mtime `2026-09-04 12:51:05` and `sha256 = cb2904444d5c5c4d…`, against the
  twenty-one completed cells' `cfd37207b9b7124a…`. **The binary that produced
  every published magnitude no longer exists on disk.** Two consequences,
  both of which must be resolved *before* launch and not narrated afterwards:
  1. `H2_BYPASS_COLLAPSE_2026-09-03.md`'s `prepareRequestRetry()` defect —
     `h2` partially engaged at 83–91% of a 96.0% ceiling — is presumably
     fixed, so `h2` will bypass more, suppress more fills, pay less home-node
     latency and **measure faster**. **G5's `h2` band of 80–95% is derived
     from pre-fix cells and would void every `h2` cell if the fix works.** It
     must be re-derived from the patched protocol before launch. The
     conservative pre-launch action is to set the `h2` band to 80–98% and
     record the realized `E_clean` as the primary observable rather than a
     gate. Do not launch against the 80–95% band.
  2. Post-fix cells are **not** comparable cell-for-cell to the published
     magnitudes, so the "windowed against published" comparison this campaign
     is registered to make becomes a comparison across two binaries. The
     campaign's *internal* comparisons — `agg_bw_isect` against `agg_bw_sum`
     within the same cell, and `h2/wb` on both metrics — are unaffected,
     because both come from the same run. **Those are the confirm/refute
     tests, so the campaign survives the binary change**; but the prediction
     bands on absolute `h2` magnitude do not, and any `h2` band in
     §"Pre-declared outcomes" that is quoted against 43.14 GB/s must be
     dropped rather than adjusted after the fact. The `h2/wb` and
     `wb/pfoff` bands stand, because a fix moves H2 upward and those bands
     are open at the top.
  Additionally, `src/python/m5/ticks.py` now has mtime `2026-09-04 09:49:19`,
  so the `QUANTIZATION_AUDIT_2026-09-03.md` rounding-warning fix — which that
  document recorded as "needs a gem5 rebuild to take effect" — **is live in
  this binary**. Expect `grep -ci 'rounding error'` to return non-zero for the
  first time in this campaign family. It does not affect G4: 2, 31 and 16
  ticks/byte are exactly realizable and the warning is diagnostic only. A
  non-zero count is **not** a gate failure and the analyzer must not treat it
  as one.
- **Nine of 120 completed instances reported a non-zero `checksum`** where the
  warm and measured passes over identical unmodified data must XOR to zero,
  and all nine were the `cpu0` instance. This campaign records the same field
  and the analyzer prints the count, but it does not diagnose it. See
  `AGGBW_VALIDITY_2026-09-03.md`.

## Provenance of the numbers in this document

Window reconstruction, LLC-supply decomposition, overlap fractions and the
runtime observations are all from `AGGBW_VALIDITY_2026-09-03.md`, which reads
only the twenty-one completed `gem5/logs/se_chi/h1bw_mc_*_20260904` cells.
Source citations are to the working tree at the time of writing:
`benchmarks/e2e/hash_join/src/cxl_join_bench.cpp`,
`experiments/asplos/run_h1bw_multicore.sh`, `gem5/configs/deprecated/example/se.py`,
and — read only, not modified — `gem5/src/sim/syscall_emul.{hh,cc}`,
`gem5/src/sim/syscall_desc.hh`, `gem5/src/sim/pseudo_inst.{hh,cc}`,
`gem5/src/sim/root.cc`, `gem5/src/arch/x86/linux/syscall_tbl64.cc` and
`gem5/include/gem5/asm/generic/m5ops.h`. **`gem5/src/` was not modified, no
run was launched, and nothing under `gem5/logs/` was written.**
