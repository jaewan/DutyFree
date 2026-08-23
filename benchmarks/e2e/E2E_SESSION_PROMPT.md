# Session prompt: build the e2e benchmark that carries the paper

Written 2026-08-11. Standalone — you should not need the originating
conversation. Read this whole file before running anything.

---

## 0. Your mission, and when you are allowed to stop

**Produce one end-to-end benchmark where \textsc{Streaming}'s value is
large, real, and reproducible — and where the deployed alternatives are
visibly worse.**

You have standing authorization to run experiments, write code, build
workloads, install/compile third-party benchmarks, create files, and
commit to `~/DutyFree` without asking. Do not stop to request permission
for measurement work. Keep going across as many candidate workloads as it
takes.

**You may stop when one candidate clears all four bars:**

1. **Magnitude** — WB co-run tax ≥ 2× on a *real* application victim
   (not a hand-rolled microbenchmark).
2. **Reproducibility** — n ≥ 10, CoV ≤ 5%, with a 95% rep-paired
   bootstrap CI, and the tax present on **both** AMD (`broker`) and Intel
   (`mos181`). Cross-vendor is a hard bar, not a nice-to-have: §3 explains
   why.
3. **Recovery** — a non-allocating arm returns the victim substantially
   toward baseline, measured against its own matched quiescent baseline
   from the same run.
4. **Frontier** — the deployed alternatives are shown to *cost something*,
   measured on the streamer's own end-to-end metric, not on a
   microbenchmark bandwidth number. See §4; this is the bar that actually
   matters and the one most likely to be skipped.

**If no candidate clears the bars, say so plainly and report what you
learned.** A documented negative result is a real deliverable here — this
project already has several, and they are load-bearing. What you must not
do is manufacture a number: see §6 on the difference between searching
the workload space (legitimate, and the whole point of this session) and
tuning a chosen configuration until it yields a big number (not).

---

## 1. Why this session exists

The paper (`~/STREAMING_Paper/ASPLOS27/`) proposes `PROT_STREAMING`: a
page-granular memory type for immutable read epochs. Pages fetch at
write-back aggressiveness (prefetchers train normally) but clean lines
never allocate in the shared LLC.

**The mechanism is not novel and the paper cannot win on it.**
Non-temporal hints, cache-bypass predictors, CAT, and NUMA placement all
exist. The contribution has to be carried by evidence that (a) the tax is
large in production-shaped software, and (b) *every* deployed way of
avoiding it forces a loss somewhere that \textsc{Streaming} does not.

Today the paper cannot support (a) or (b) with real applications. §3 has
the data.

---

## 2. Machines

Re-read from `/sys` and `numactl -H` on each host, 2026-08-23. The previous
version of this table recorded `mos182` as having no CXL. It has 256 GiB of it,
and that error propagated into a design document before it was caught.

| alias | hostname | CPU | private L2 | shared cache | ways | MiB/way | CXL | notes |
|---|---|---|---|---|---:|---:|---|---|
| *local* | `mos181` | Intel Xeon 8592+ (Emerald Rapids), 2×64 | 2 MiB, 16-way | 320 MiB LLC | 20 | 16.0 | node 2, cpuless, 258033 MB, **near socket 0** | resctrl ✔. **Also the gem5 testbed.** |
| `ssh broker` | `moscxl` | AMD EPYC 9754 (Bergamo), 2×128 | 1 MiB, 8-way | **16 MiB L3 per CCX** (8 cores) | 16 | 1.0 | node 2, cpuless, 258020 MB | resctrl ✔ (CAT + SMBA) |
| `ssh c4` | `mos182` | Intel Xeon 8462Y+ (Sapphire Rapids), 2×32 | 2 MiB, 16-way | 60 MiB LLC | 15 | 4.0 | **node 2, cpuless, 262144 MB, near socket 1** | resctrl ✔ |

Private L2: **EMR/SPR 2 MiB/core**, **Zen 4c 1 MiB/core**. Memorize this. It
has caused three separate nulls in this project (§6).

**All three hosts have a cpuless CXL node 2.** Two things about it are traps:

1. **The Intel hosts are mirrored.** `mos181`'s CXL is near socket 0
   (0→2 = 14, 1→2 = 24); **`mos182`'s is near socket 1** (1→2 = 14,
   0→2 = 24), so work there belongs on cpus 32–63, 96–127 with memory on
   node 1. Socket 0 adds a UPI hop to every CXL access and puts the
   streamer's LLC footprint in the wrong socket, silently.
2. **SLIT and HMAT are not measurements and may not be cited as any.**
   `moscxl` declares node 2 at distance **255** (unreachable) with HMAT
   bandwidth 5 GB/s; this project has repeatedly measured ~24 GB/s from it.
   The Intel hosts declare node-2 read latency 150 and 100 ns, a difference
   that is almost certainly firmware convention. Measure per host.

`mos181` and `mos182` have **identical private L2** (2 MiB, 16-way) and a
**5.3× difference in LLC**, which makes them a controlled LLC-size sweep at
constant private-cache geometry — see `oltp_index/OLTP_INDEX_DESIGN.md` G6.

Existing harness on both silicon hosts: `~/tmp_dutyfree_exp/bin/`
- `aggressor -m <wb_load|wc_ntdqa|uc_load|wb_ntdqa|wb_prefetchnta|wb_local> -t N -c <corelist> [-s MB] [-d sec] [-N node] [-R MBps]`
- `victim -c <core> [-n node] [-w ws_KB] [-d sec] [-W warmup] [-P]`
- `amd_flushbehind_aggressor -f <KiB>` (AMD only)

**`-R` pacing throttle carries a known confound. Do not use it.**
Thread count is the honest way to vary bandwidth.

`mos181` is currently running twelve gem5 simulations in tmux sessions
named `ld_*`, writing to `/tmp/ld_*`. **Leave them alone**; they are a
different workstream. You have ~256 cores, they are using ~12.

---

## 3. What is already known — read before proposing anything

### 3.1 Real applications do not respond, and it is not cache geometry

`~/tmp_dutyfree_exp/results/exp40_fourvictim_intel/exp40_tables.md`
(Intel, aggressor 8 threads × ~24 GB/s from CXL):

| victim | WB tax |
|---|---:|
| ptr (synthetic pointer chase) | 2.04× |
| rocksdb `readrandom` | 1.00× |
| duckdb | 0.99× |
| ivf (ANN) | 1.00× |

`~/tmp_dutyfree_exp/results/exp41_llcgeom_intel/exp41_report.md` tested
whether that null is geometry, by way-confining victim and aggressor to N
ways. At **1 way = 16 MiB = exactly one AMD CCX L3**, matching AMD's
victim-to-cache ratio, with victims resized to 4× private L2:

| victim | 16 MiB shared | AMD reference |
|---|---:|---:|
| ptr | 1.55× | 19.85× |
| duckdb | 1.00× | 2.32× |
| rocksdb | 1.00× | 2.33× |
| ivf | 1.04× | 1.63× |

**The geometry hypothesis was tested and rejected.** Every real engine is
a null on Intel even at matched cache ratio. The AMD numbers in the right
column are what the paper prints; I could find **no surviving raw
dataset, runner script, or `db_bench` invocation** for them anywhere on
either host. `exp40b_engines_scaled/` (larger working sets) confirms the
Intel null: duckdb 1.010×, ivf 1.002×, rocksdb 1.042×.

So the paper's only "real application" sentence
(`Sec5_Evaluation.tex:340`, RocksDB 2.33× / CAT recovers 54%) is
AMD-only, unreproducible on the other vendor at matched geometry, and
has no recoverable provenance. **That is why cross-vendor is a hard bar
in §0.** Do not hand back another AMD-only result.

### 3.2 The diagnosis

Group the four victims by what they actually do:

- **DuckDB** scans. A scan has no reuse, so stealing its LLC capacity
  costs it nothing.
- **RocksDB `readrandom`** spends ~3 µs/op ≈ 7000 cycles of software per
  lookup. A few hundred cycles of extra miss latency dissolves into it.
- **IVF** scans posting lists — streaming again, not reuse.
- **ptr** is the only one with a **dependent-load critical path and
  near-zero software work between hops**, and it is the only one that
  responds.

The paper half-concedes this (*"the tax bites in proportion to how much
of the critical path is latency-bound, tight reuse"*), but as written a
reviewer reads it as a scope confession. **You need a real application
with the pointer chase's access shape.**

### 3.3 What does work today

`benchmarks/e2e/hash_join/AMD_CROSS_PROCESS_OUTCOME.md` — hash-join
tenant, AMD, victim-first protocol, n=12:

| arm | cycles/access | tax | victim LLC occupancy |
|---|---:|---:|---:|
| quiescent | 62.66 | 1.000× | 8.29 MiB |
| WB | 406.25 | 6.484× | 0.39 MiB |
| flush-behind (256 KiB) | 144.21 | 2.302× | 7.92 MiB |

76.3% recovery. This is the best e2e the project has, and its weaknesses
are exactly the ones you are fixing: the victim is hand-rolled
(`cxl_join_bench`), the aggressor is synthetic, it is AMD-only, and the
loaded arms were bimodal in an earlier run.

---

## 4. The target

### 4.1 Primary candidate: graph analytics (GAP-BS)

Get **GAP Benchmark Suite** (`https://github.com/sbeamer/gapbs`, C++,
`make`, no exotic deps). Run **BFS**, **PageRank**, and **Connected
Components**.

Why this and not another engine:
- Random dependent access into a vertex-property array with genuine
  reuse across iterations — the pointer chase's shape, in software the
  architecture community already accepts as a real workload.
- Almost no software work per edge, so the latency is not diluted the way
  RocksDB's is.
- Scale is a dial (`-g <scale>` Kronecker, `-u` uniform). A Kron-25
  vertex array is ~100–130 MB — you can hit meaningful fractions of a
  320 MiB LLC *without* way-confinement tricks, and the same generator
  sizes down cleanly onto AMD's 16 MiB CCX. That is what makes the
  cross-vendor bar reachable.

**Sizing gate, run this first, before any co-run arm:** sweep graph scale
alone (no aggressor) and confirm the working set is *not* private-L2
resident and that runtime is genuinely memory-bound. Record the sweep.
Skipping this gate is what produced three of the nulls in §6.

### 4.2 Secondary, cheap: swap IVF → HNSW

IVF was structurally the wrong ANN algorithm: it scans posting lists.
HNSW traverses a proximity graph with dependent hops and reuses its upper
layers heavily. Same application domain, small change, plausibly converts
an existing null into a signal. `hnswlib` is header-only. Worth an hour
before committing to a long GAP-BS campaign, and vector search on CXL is
a topic reviewers care about.

### 4.3 Also viable if both above disappoint

In-memory OLTP index (Masstree / Silo TPC-C) — the paper's own §2 margin
note asks for it. Heavier setup; treat as third.

### 4.4 The deliverable shape — make the streamer a real application too

This is the part that answers *"this is obvious, just use NT stores."*

Right now the streamer is **always synthetic**, so the cost of the
obvious alternative is only ever a microbenchmark bandwidth ratio (15.8 →
4.2 GB/s), which a reviewer discounts. Make the streamer a real
application and you can report **its own end-to-end cost**:

| streamer mode | streamer's own query time | co-tenant tax |
|---|---|---|
| WB (default) | 1.00× (best) | large |
| NT / `movntdqa` | ? | ~1.00× |
| flush-behind | ? | small |
| \textsc{Streaming} | 1.00× | ~1.00× |

Three of four rows are measurable on silicon **today**; only the last
needs gem5. That table is the contribution — *no deployed knob occupies
this corner* — argued with two real applications instead of two
microbenchmarks.

**Use DuckDB as the streamer.** It is a scan engine over columnar data,
which is precisely the immutable-read-epoch shape the paper is about, and
it already failed as a victim for exactly the reason it will succeed as
an aggressor. Point it at a CXL-resident table (node 2), run a scan-heavy
query, and measure DuckDB's own query latency in each row while the
GAP-BS tenant's tax is measured in the same run.

If you cannot get DuckDB to issue NT loads without patching it, say so
and fall back to a real-format scan you control (e.g. a Parquet/columnar
reader you can compile both ways) — but keep the streamer's *own*
end-to-end metric in the table either way. A missing row is fine; an
unmeasured row silently replaced by a microbenchmark number is not.

---

## 5. Method — non-negotiable

This project has a written discipline file: **read
`experiments/asplos/REPO_DISCIPLINE.md` before your first measurement.**
Condensed:

1. **Pre-register.** Before the first measurement arm of each campaign,
   write `<CAMPAIGN>_PREREGISTRATION.md` stating the operating point and
   **falsifiable predictions**, and commit it. Then measure. Follow the
   shape of `experiments/asplos/GATE1_LOCALDRAM_COLUMN_PREREGISTRATION.md`.
2. **Matched baselines.** Every loaded arm gets its own quiescent
   baseline **from the same run and the same configuration**. A tax is
   `loaded ÷ its own matched baseline`, never a ratio across configs.
   Omitting this has already caused one misread in this project.
3. **Instantiated, not intended.** Record what the run *did*, not what
   the script meant. Verify placement from wire truth (per-controller
   traffic, CMT/MBM occupancy, `numastat`), not from the flag you passed.
4. **Arm identity.** Every number gets its operating point named at the
   point of use: victim size, aggressor thread count, placement,
   bandwidth achieved, arrival order. Absolute taxes on `broker` are
   **arrival-order dependent** — the frozen protocol is *victim-first*
   (victim warms, emits a ready marker, runner then starts the aggressor
   after a 0.1 s gap). Use it and name it.
5. **Statistics.** n ≥ 10, report median + 95% rep-paired bootstrap CI +
   CoV. Interleave repetitions across arms; do not run all of arm A then
   all of arm B. Check for bimodality before quoting a mean — the AMD
   hash-join run was bimodal and the pooled mean was meaningless.
6. **Integrity checks each rep.** Aggressor self-reports achieved
   bandwidth and you assert it is nonzero and in range; assert no orphan
   aggressor processes; confirm the aggressor window strictly covers the
   victim window (an aggressor that dies early silently deflates the
   tax — this happened); read CAT masks back through resctrl after
   setting them.
7. **`cmd | tee log; echo $?` reports `tee`'s status, not `cmd`'s.** Use
   `PIPESTATUS[0]`.

---

## 6. Traps this project has already fallen into

- **hot ÷ private-L2 collapse — three times.** gem5's fused hash-join
  null; exp41's first 4 MiB Intel attempt (EMR's 2 MiB private L2
  swallowed it); and `tab:gem5`'s 25% row, measured 2026-08-11 at
  **1.00002×** against a printed 1.79× — even with the aggressor pushing
  1.59× more traffic. **Always size the victim hot set against private L2
  first, shared LLC second.**
- **Provenance evaporation.** The AMD headline raw datasets and the
  exp40/exp41 runners are gone; only result JSON survives. **Commit your
  runner with your results, every time.**
- **`stream_wc.c` is MOVNTDQA-on-WB.** On AMD it behaved exactly like WB
  (361.95 vs 361.92 cycles/access) and is *not* a no-tax control. A true
  WC arm needs `/dev/cxl_wc`, which was last seen absent with the kernel
  refusing to offline a CXL memory block. Verify the device exists before
  planning a WC arm.
- **`-R` throttle confound** (§2). Vary threads instead.
- **Env-var footgun.** Tooling that reads the *invoking* shell's
  environment will silently mislabel a run. Generate manifests inside the
  run's own environment, and prefer fields derived from the run's own
  counters.
- **Two gem5 checkouts** exist (`~/DutyFree/gem5` submodule and
  `~/DutyFree-Gem5` build clone). The scripts `cd ~/DutyFree-Gem5`, so
  that is the copy that executes. Edit the wrong one and your change has
  no effect.

---

## 7. Out of bounds

- **Do not edit `~/STREAMING_Paper/`.** It has an autosync watcher that
  commits and pushes to Overleaf unattended, so an edit there is an
  unreviewed publication. Write findings into `~/DutyFree` and let the
  lead move them.
- **Do not `git push`** either repo.
- **δ embargo.** The flush-op coherence overhead is INCONCLUSIVE. The
  flush-behind arm may be reported as an operating point, but its
  residual **may not be attributed** between H2 and H3, and the 3.6
  figure may not be cited without *"upper bound, flush-overhead
  unresolved."*
- **Do not disturb the `ld_*` tmux sessions or `/tmp/ld_*`** on `mos181`.
- Do not spawn subagents or workflows unless the lead asks.

---

## 8. Deliverables

Commit to `~/DutyFree`, as you go rather than at the end:

1. `benchmarks/e2e/<workload>/` — runner, build recipe, and workload
   generation, reproducible from a clean checkout.
2. `<CAMPAIGN>_PREREGISTRATION.md`, committed *before* the first arm.
3. Raw per-rep JSONL + an aggregate summary, both committed.
4. `<CAMPAIGN>_OUTCOME.md` — which predictions held, which failed, the
   frontier table of §4.4 with every cell either measured or explicitly
   marked unmeasured, and the arm identity for every number.
5. A short `E2E_STATUS.md` at `benchmarks/e2e/` naming the current best
   candidate and the four bars it does or does not clear.

Report negative results with the same care as positive ones. The fastest
way to waste this session is to find a big number and not be able to
defend where it came from.
