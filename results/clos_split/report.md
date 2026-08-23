# CLOS-split falsification experiment: report

## Verdict, first

**`T_best_split/T_A = 0.68` (95% CI [0.68, 0.69]) and `R = 0.055` (95% CI [0.041, 0.069]) against the fused baseline — both conditions of the pre-registered "paper's claim holds" branch are satisfied independently and by a wide margin: restructuring the join into CAT-separable scan/probe threads costs about a third of end-to-end throughput and recovers under 6% of the hot-table cycle gap, so context-scoped CAT cannot rescue the split even when the split itself is tuned to its best-known configuration.**

Recomputed against the split-only baseline (no CAT) rather than the fused baseline — the comparison the reviewer insisted on, to avoid crediting CAT for the architectural decoupling that splitting buys for free — CAT's recovery is statistically indistinguishable from zero: `R_vs_D = -0.021` (95% CI [-0.057, 0.001]).

This is not a marginal call in either direction. `T_best_split/T_A` (0.68) is nowhere close to the 0.90 threshold, and `R` (0.055) is nowhere close to even the 0.50 "partial" threshold, let alone the 0.90 falsification bar.

---

## What changed since the last checkpoint (the A-vs-D gate)

The initial decisive gate (untuned D: 8 scan/8 probe threads, queue-depth=8) reported `T_D/T_A = 0.476`. The adversarial sweep below found a materially better split configuration (4 scan/12 probe, queue-depth≥16), which recovers to `T_D/T_A ≈ 0.69`. **This matters and is reported honestly rather than kept as the more dramatic first number**: the untuned gate understated best-case split throughput by about 20 points. The corrected number is what's used in the verdict above. Both the untuned gate's raw data (`gate_A_untuned_16c`, `gate_D_8x8_qd8_16c`) and the tuned sweep are preserved in `raw/` and `summary.csv` for audit.

---

## Core-count scaling: `H` (active cycles/access) per configuration

Two core counts measured, per the pre-registered flat-gap finding (Phase 0 correction): the quiescent-vs-loaded gap does not grow with core count in cycles/access, so the informative comparison is 1 core (confound-free) vs 16 cores (realistic, full matrix), not a 5-point sweep.

| Config | 1 core `H` (median, 95% CI) | 16 cores `H` (median, 95% CI) |
|---|---:|---:|
| Q (quiescent) | 60.47 [60.18, 60.75] | 60.15 [55.95, 61.28] |
| A (fused, CAT off) | 100.59 [99.87, 101.16] | 99.23 [98.91, 99.37] *(seq2 ref)* / 96.34 [95.77, 99.14] *(seq1 ref)* |
| B (fused, CAT on, 4/20 ways) | 141.38 [140.46, 142.06] | 145.05 [144.80, 145.74] |
| D (split, best ratio, CAT off) | not applicable — split needs ≥2 threads | 96.25 [95.10, 96.82] |
| C (split, best ratio, CAT on) | not applicable | 96.97 [96.57, 97.38] (1-way) / 99.37 [98.37, 99.80] (2-way) |
| E (fused, PREFETCHNTA) | not measured (16-core only, per approved scope) | 107.80 [106.97, 108.79] |

**Same-context tax, confound-free (1 core, no cross-core contention possible):** `H_A/H_Q = 1.663×` (95% CI [1.649, 1.676]). This is the cleanest number in the whole experiment — one thread, one core, and restructuring nothing: the tax is already fully present.

**CAT on fused mode makes it worse, at both core counts, and the effect is *stronger* with a tighter restriction than the historical 16-of-20-way test:** `H_B/H_A = 1.462×` at 16 cores (CI [1.458, 1.471]), `1.384×` at 1 core (CI [1.368, 1.400]), both with a 4-of-20-way CLOS. Throughput drops in lockstep: `T_B16/T_A16 = 0.682` (CI [0.678, 0.688]).

---

## The throughput cost of splitting (D vs A) — the number that decides whether fusion is load-bearing

| Comparison | Throughput ratio (median, 95% CI) |
|---|---:|
| First-pass gate: `T_D(8:8,qd8)/T_A` | 0.476 |
| Best-tuned: `T_D(4:12,qd16)/T_A` | **0.693** [0.687, 0.702] |
| Best-tuned split + CAT: `T_C(best)/T_A` | **0.684** [0.680, 0.691] |

Splitting costs 31% of throughput at best, before CAT is even applied, and CAT on top of the split does not recover any of it (compare the last two rows — they agree within noise).

**Why the best split ratio is 1:3 (scan-light), not the naively-expected balanced 1:1**, checked against the per-stage costs rather than assumed: at 8:8 the per-tuple cost of scan (90.9 cyc) and probe (94.1 cyc) look nearly balanced, which would predict 1:1 is near-optimal. It measured decisively worse than 1:3 (152.4 Mt/s vs 204.9 Mt/s). The reason is that aggregate CXL bandwidth from concurrent streamers saturates early on this platform — 4 threads already reach 23.1 GB/s versus 23.6 GB/s for 8 threads (from this repo's existing CXL characterization) — so moving 4 threads off scan costs almost nothing in scan throughput while adding 50% more probe parallelism. This is a real, reproducible, mechanistically-explained effect (tight non-overlapping CIs across all three ratios: 79.1 / 152.4 / 204.9 Mt/s for 3:1 / 1:1 / 1:3), not noise.

**Why the copy is structural, not a fixable inefficiency**: swapped the scan-side element-wise copy for an explicit `memcpy` and re-measured (5 runs each) — no meaningful difference (148.6–149.6 Mt/s loop vs 148.2–149.3 Mt/s memcpy). The compiler was already emitting an efficient copy; the cost is the memory movement itself, which is unavoidable if scan and probe are to run on CPUs a context-scoped mechanism can tell apart.

**Queue depth was checked and ruled out as a confound, per the original task's explicit warning that an undersized queue would manufacture a false negative in our favor**: throughput at queue-depth 1/2/4/8/16/32/64/128 was 40.2 / 38.5 / 80.1 / ~149 / 166.9 / ~159 / 166.3 / 166.5 Mt/s. It plateaus at depth≥16; the main sweep uses depth=16, comfortably past the knee, so the reported D/C numbers are not queue-starved.

---

## Full sweep table: split ratio and CAT way allocation (config D/C)

| Config | Scan:Probe threads | Queue depth | CAT ways (scan/probe) | Throughput Mt/s (median, CoV, 95% CI) | `H` cyc/access (median, CoV, 95% CI) |
|---|---|---:|---|---:|---:|
| D | 4:12 (1:3) | 16 | off | 204.89, 2.67%, [203.08, 206.21] | 96.83, 2.48%, [96.38, 97.87] |
| D | 8:8 (1:1) | 16 | off | 152.44, 2.60%, [152.13, 155.60] | 96.64, 2.61%, [94.25, 97.03] |
| D | 12:4 (3:1) | 16 | off | 79.14, 2.08%, [77.61, 80.06] | 94.03, 2.11%, [92.74, 95.80] |
| D (ref, paired w/ C) | 4:12 | 16 | off | 206.62, 1.98%, [205.49, 208.73] | 96.25, 1.81%, [95.10, 96.82] |
| C | 4:12 | 16 | 1 / 19 | 204.20, 1.58%, [203.60, 206.05] | 96.97, 1.50%, [96.57, 97.38] |
| C | 4:12 | 16 | 2 / 18 | 199.88, 2.09%, [198.28, 201.21] | 99.37, 1.83%, [98.37, 99.80] |

**Sweep points skipped for time, disclosed explicitly per the truncation rule**: the original design called for scan-CLOS ways ∈ {1, 2, 4} at all three ratios × two queue depths (18 points). This panel measured 3 ratios × 1 queue depth for D, and 2 way-points × 1 ratio (the winning one) for C — 5 of the original 18 C/D combinations, chosen adversarially (best ratio found empirically, not assumed) rather than arbitrarily. The 4-way scan CLOS point for C, and the 1:3/3:1 ratios for C, were not measured; given C already shows no recovery at 1 and 2 ways relative to D, and a coarser CAT class (more ways, less restriction) can only move C's occupancy closer to D's unrestricted case, there is no mechanistic reason to expect a 4-way point to look different — but it was not measured, and this is stated rather than assumed.

---

## Environment capture

| Item | Value |
|---|---|
| CPU | Intel Xeon Platinum 8592+, stepping 2, microcode `0x210002d3` |
| Kernel | Linux 7.0.0-22-generic (Ubuntu), `PREEMPT_DYNAMIC` |
| Governor / turbo | `performance`, turbo disabled (`no_turbo=1`) |
| Hugepages | Static hugetlbfs pool, 2 MB pages, 34288 pages reserved; THP (`AnonHugePages`) not used by this workload |
| `resctrl` | Mounted; L3: 15 CLOSes, 20 ways/domain, 2 domains (`mon_L3_00`=socket 0, `mon_L3_01`=socket 1); CDP off; `min_cbm_bits=1`; MB: 15 CLOSes |
| Compute CPUs used | 32–47 (physical cores, no SMT siblings — confirmed all map to L3 domain 0 via `/sys/devices/system/cpu/cpu*/cache/index3/id`) |
| NUMA topology | node 0: 128 logical CPUs (64 physical + SMT), 515 GB; node 1: same, other socket; node 2: 0 CPUs, 254 GB, CXL-only |
| CXL device | Micron Technology Device 6400 (CXL 2.0), PCI `0000:27:00.0`, `region0` 274,877,906,944 B, interleave ways=1 |
| Prefetcher MSR `0x1a4` | `0x0` on sampled cores (all hardware prefetchers enabled, none disabled) |
| Compiler | g++ (Ubuntu 15.2.0-16ubuntu1) 15.2.0, `-O3 -std=c++17 -march=native -pthread` |
| Benchmark commit | `f6e15c1e0bdea9412c51dfe41ef3ecc218ef083a` (working tree modified, uncommitted — see `git diff` for the split-mode addition) |
| Frequency stability | `cycles/ref-cycles` median ≈ 0.999 across all measured configs — actual core frequency tracked the invariant-TSC-implied rate throughout, consistent with turbo off; no evidence of frequency drift confounding the TSC-based cycle counts |

---

## What surprised me, what I couldn't measure, and what a reviewer would attack

**Surprised me:**
- The optimal split ratio (1:3, scan-light) is the opposite of what a naive per-tuple-cost balance calculation predicts at 8:8. It's explained by CXL bandwidth saturating with only ~4 concurrent streamers on this platform, not by anything about the probe side. Worth stating explicitly in the paper so a reviewer doesn't assume the ratio choice was arbitrary or cherry-picked.
- Splitting is *this* expensive (31% throughput loss at best) even with the ratio and queue depth tuned. I expected the untuned gate's 0.476 to close substantially under tuning; it closed to 0.69, not further.
- `R_vs_D`'s point estimate is slightly *negative* (median -0.021). CAT applied after splitting isn't just "no better," its central estimate is marginally worse, though the CI [-0.057, 0.001] can't rule out exactly zero.

**Could not measure / explicitly out of scope:**
- E (PREFETCHNTA) was only measured at 16 cores, not 1 core, and not under the split configurations — it's a fused-mode-only comparison per the original scope.
- The full 3-ratio × 3-way × 2-queue-depth (18-point) C/D grid was not run; 5 adversarially-chosen points were, as disclosed above.
- A joint, fully-propagated bootstrap CI for `R` uses the actual paired raw samples (not a plug-in from each component's marginal CI), so the reported `R` CIs are the rigorous ones; the per-component `H`/`T` CIs in the tables above are marginal (computed independently per label) and will look slightly wider than what a reader might back out from combining them naively — this is expected and not an error.
- Whether the `cpu-migrations` perf counter's baseline (~16–18 per 16-thread run) reflects *only* the one-time affinity-correction at thread creation, versus some additional unpinned-main-thread noise, was not fully isolated (see the A-vs-D gate report). The pinning guarantee that actually matters — a single-CPU affinity mask, set once, never changed — is architectural, not measured indirectly via this counter.

**What I'd expect a skeptical reviewer to attack:**
- "You only tried one queue implementation (mutex/condvar)." Addressed: queue depth was swept 1–128 and plateaus at 16; a lock-free queue wouldn't change the copy cost, which is what the memcpy-vs-loop check isolated as the actual bottleneck.
- "Zero-copy range handoff (scan publishes `[start,end)`, probe reads CXL) would avoid the copy tax." Addressed in the discussion the reviewer and I converged on: that design just relocates the identical fused-context problem to whichever thread ends up issuing both the CXL read and the hot-table probe — it isn't a way around the paper's thesis, it's a restatement of it one hop downstream.
- "Why is `B` (CAT on fused) so much worse here — 46% cycle penalty — than the historical 16-way test showed?" Answer: this run used a tighter 4-of-20-way restriction, not the historical 16-of-20; the two aren't the same measurement, and the direction (CAT hurts fused, monotonically worse with a tighter class) is consistent across both.
- Both `A2_16`/`A3_16` (298.7 vs 304.8 Mt/s, seq1 vs seq2 references) and `D_1_3`/`Dref` (204.9 vs 206.6 Mt/s) differ by 1–2% across independently-randomized batches run at different points in the ~30-minute panel. This is normal run-to-run variance, not drift, but is disclosed rather than silently averaged away — the report uses the specific paired reference for each comparison (seq2's `A3_16`/`Dref` for the C/B verdict) rather than mixing batches.

---

## Deliverables

- `results/clos_split/raw/` — all 510 individual run records (gate + panel), nothing aggregated away.
- `results/clos_split/summary.csv` — one row per labeled configuration, median/CoV/95% CI for throughput and cycles/access, regenerated from raw JSON with a single consistent schema (the two driver scripts' incremental writes used incompatible column sets; this was caught and fixed before finalizing).
- This report.
