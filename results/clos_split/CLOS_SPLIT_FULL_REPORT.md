# The CLOS-split falsification experiment: full report (corrected)

**Purpose of this document:** this is the single, self-contained artifact for external
review. It contains the claim under test, the pre-registered decision rule, the
environment, the implementation, the instrumentation proof, both experiments' full
results (inlined, not by reference), a documented mid-flight correction of a real
measurement bug, and an explicit list of what a skeptical reviewer would attack. No
other file is required to evaluate this experiment.

**Platform:** Intel Xeon Platinum 8592+ (Emerald Rapids), 320 MB non-inclusive LLC,
CXL Type-3 memory device (Micron 6400) on a cpuless NUMA node. Real hardware, not
simulation.

**Note on revision history:** an earlier version of this report used contaminated
timing data (a correctness-check flag was left enabled during every timed run,
adding non-uniform overhead) and an inconsistent cycles/access definition between
fused and split modes. Both are described and fixed in Section 4. All numbers below
are from the corrected methodology; the superseded numbers are not quoted here except
where explicitly labeled as historical context. The archived contaminated raw data is
preserved at `raw_v1_contaminated_with_hash_overhead/` for anyone who wants to audit
the correction itself.

---

## 1. The claim under test

The paper argues that shared-cache admission control must be **object-scoped** (bound
to a memory region) rather than **context-scoped** (bound to a core or thread). Intel
CAT, Arm MPAM, and RISC-V CBQRI all enforce non-allocation, but derive their label from
execution context, swapped at context switch. The paper's evidence rests on: in a
morsel-driven (fused) many-core kernel, streaming and reusing accesses issue from the
*same thread*, so no context-scoped mechanism can separate them.

**The threat to that claim:** restructure the application — put scan (streaming) and
probe (reusing) in separate threads, assign them to separate CAT classes (CLOSes), and
shipped hardware solves the problem with no architectural change. If that works, the
paper's central claim is false.

This experiment tries, as hard as possible, to make that threat work.

### Pre-registered decision rule (committed to before any result was seen)

Let `T` = end-to-end join throughput (tuples/s), `H` = hot-table cycles/access,
`H_quiescent` = single-thread, no-streaming-co-runner baseline. Subscripts are the
configuration letters defined below. Recovery fraction:

```
R = (H_A − H_best_split) / (H_A − H_quiescent)
```

- **Paper is falsified** if `R ≥ 0.90` **and** `T_best_split ≥ 0.95·T_A`.
- **Paper's claim holds** if `T_best_split < 0.90·T_A` **or** `R < 0.50`.
- **Partial / re-aim** for anything in between.

### Configurations

| ID | Structure | CAT | Purpose |
|----|-----------|-----|---------|
| A | Fused: each worker scans CXL fact + probes hot table | off | Baseline / measured interference regime |
| B | Fused | on: all workers, one restricted CLOS | Shows context-scoped CAT starves the hot table along with the stream |
| C | Split: N_s scan threads + N_p probe threads via queue | on: scan CLOS restricted, probe CLOS generous | **The threat** — the configuration that could kill the paper |
| D | Split, same N_s/N_p as best C | off | **Essential control** — isolates the cost of splitting from the benefit of CAT |
| E | Fused, stream read via `PREFETCHNTA` | off | Software proxy for object-scoped non-allocation |
| Q | Single thread, no streaming co-runner | off | Yields `H_quiescent` |

All configurations at a given core count use the same total core count and the same
total input.

---

## 2. Verdict

> **`T_best_split/T_A = 0.64` (95% CI [0.63, 0.65]) and `R = −0.25` (95% CI [−0.29,
> −0.21]) against the fused baseline. Both conditions of the "paper's claim holds"
> branch are satisfied, and by more than a comfortable margin: splitting the join into
> CAT-separable scan/probe threads costs 36% of end-to-end throughput, and the
> resulting hot-table access cost is not merely unrecovered — it is measurably** worse
> **than the fused baseline it was supposed to fix.**

Recomputed against the split-only (no-CAT) baseline `D` — the more conservative
comparison, isolating CAT's own marginal contribution from the architectural cost of
splitting itself — CAT's effect is statistically indistinguishable from zero:
`R_vs_D = 0.009` (95% CI [−0.009, 0.033]).

This is the corrected version of a result that, before a measurement bug was found and
fixed (Section 4), looked like a small, ambiguous, barely-recovering effect. It isn't.
Splitting doesn't trade throughput for a cleaner hot-table access pattern — it costs
throughput **and** makes the hot-table access pattern worse, and CAT applied on top of
the split adds nothing further.

---

## 3. Ground truth reproduced, and one discrepancy caught and corrected

Before trusting any new measurement, the platform's prior documented findings were
cross-checked (`benchmarks/e2e/hash_join/docs/RESULTS.md`,
`benchmarks/e2e/hash_join/gem5_handoff.md`):

- Real Xeon 8592+ hardware confirmed: `resctrl` mounted, node 2 is a genuine CXL.mem
  NUMA node (0 CPUs, backed by a Micron CXL 2.0 Device 6400 — confirmed via `lspci`
  and `cxl list`, not inferred), turbo off, performance governor.
- Prior "separate-victim CAT" result (a different, simpler pointer-chase-vs-stream
  microbenchmark, not the hash join) reproduced from existing repo data: 0.99× victim
  slowdown at ~32 GB/s aggressor bandwidth with disjoint CAT ways — confirms CAT *can*
  isolate cleanly when streaming and reuse genuinely originate from different
  threads/cores from the start.
- The paper's draft references a "Samsung Type-3" CXL device in its platform
  description; this is a pre-existing, already-documented mismatch (see
  `docs/RESULTS.md`: "this CXL device's single-core ceiling is lower than the paper's
  Samsung Type-3 platform") between an earlier reference platform and the actual host
  used for every hardware number in this repository, including this experiment's. The
  paper's platform table should say Micron CXL 2.0 Device 6400.

**Discrepancy found:** the task brief described the morsel-mode interference
("56 → 87 cycles/access, 32 → 71 MPKI") as a **1→16 core scaling trend**. The
underlying data shows this is actually the **quiescent-vs-loaded gap at a fixed core
count**, and that gap is flat across 1, 2, 4, 8, and 16 cores. There is no cycles/access
scaling trend to exploit. This matters for the paper's framing: the interference is a
**structural, same-thread** effect present already at 1 core, not a many-core
contention effect — a cleaner and stronger claim than a scaling law, since the 1-core
case has no cross-core confound at all. The experiment is designed around this
corrected framing (1 core and 16 cores, not a 5-point core sweep).

---

## 4. A measurement bug found and fixed mid-experiment — documented in full

An earlier pass through this experiment reported `T_best_split/T_A ≈ 0.68` and
`R ≈ +0.055`. Both numbers were wrong, for a reason worth stating plainly rather than
quietly correcting.

**The bug:** every timed run in both experiments was launched with `--result-hash`, a
flag meant only for a one-time correctness cross-check (an order-independent hash over
matched tuples, confirming fused and split modes compute the same join). It was assumed
to be free when enabled, because it had only been verified to be a no-op *when
disabled*. It is not free, and — critically — its cost is not uniform:

| Config | Throughput with `--result-hash` | without | Overhead |
|---|---:|---:|---:|
| Fused (A) | ~299 Mt/s | ~341 Mt/s | **12.4%** |
| Split (D, 4:12) | ~209 Mt/s | ~216 Mt/s | **3.1%** |

Because fused mode pays roughly four times the overhead split mode does, every
throughput ratio and cycles/access comparison between fused and split configurations
was biased — specifically, biased in the *direction that made the split look better
than it is* (contaminated fused numbers were suppressed further than split numbers).
This was caught by re-checking one of the reviewer's side questions (whether E's
`PREFETCHNTA` result used a fairly-tuned parameter) and noticing the throughput number
for a quick sanity re-run didn't match the panel's reported number at all.

**Fix:** `--result-hash` removed from both driver scripts' timed argument builders.
Correctness is validated once, separately, at small scale (Section 5) — this never
needed to run on every timed repetition. The old contaminated raw data (510 files) is
preserved at `raw_v1_contaminated_with_hash_overhead/` rather than deleted, so the
correction itself is auditable.

**A second, related gap, also fixed:** split mode's `active_cycles_per_access`
originally timed only the probe loop itself, excluding any time a probe thread spent
blocked waiting for a scan thread to fill a queue slot. Fused mode has no equivalent
blocking (`join_range` never waits on anything internal), so it was implicitly always
"wall-clock inclusive." This made the two modes' `H` values not comparable. Fixed:
`active_cycles_per_access` for split mode now wraps the entire queue-consume call,
including wait time; a second field, `probe_compute_cycles_per_access`, preserves the
original compute-only metric for diagnostic purposes. Both are in the raw JSON.

**Net effect of both fixes on the substantive conclusion:** it got stronger, not
weaker. The corrected throughput ratio (0.64) is further from the 0.90 threshold than
the contaminated one (0.68) was. The corrected `H` comparison flips from "CAT barely
underperforms a small recovery" to "split, even with CAT, leaves the hot table worse
off than plain fusion" (Section 7).

---

## 5. Implementation (Phase 1)

Added an additive `--mode split` to the existing single-file C++17 benchmark
(`benchmarks/e2e/hash_join/src/cxl_join_bench.cpp`), without modifying the fused path
(`join_range`, `run_morsel`'s core loop) at all:

- **N_s scan threads** pull morsels from an atomic counter (same mechanism as fused
  mode), copy the fact tuples (the actual CXL read) into a slot in a bounded
  mutex/condvar MPMC queue (`MorselQueue`).
- **N_p probe threads** pop filled slots and run the hash-table probe against the local
  copy. Probe threads never touch CXL memory directly — that is the entire point of the
  split, and the entire reason it can be CAT-separated at all.
- `--scan-threads`, `--probe-threads`, `--queue-depth` control the split.
- `join_range_hashed` (a sibling function, not a modification of `join_range`) plus
  `--result-hash`, used only for the one-time correctness check below.

**Correctness validation:** fused and split runs at identical seed/fact-bytes/hot-bytes
produced **identical `matches`, `sum`, and order-independent `result_hash`** across
three scan:probe ratios (1:3, 1:1, 3:1) and multiple queue depths, both before and
after the timing-metric fixes in Section 4 — the split computes the same join result
as the fused path, just via a different thread structure. This was re-verified after
the H-definition fix (Section 4) with no change: `33427603` matches, `-369203` sum,
`7700551460813443366` hash, identical between fused and split.

**Two robustness checks run before trusting any split-mode number**, both mechanical
follow-ups from the task's own warnings about false negatives:

1. *Copy-implementation check:* the scan-side copy uses a plain element-wise loop
   (`buf[i-begin] = fact[i]`), trusting the compiler to vectorize it. Swapped it for an
   explicit `memcpy` and re-measured: no meaningful difference. The copy cost is
   genuine memory movement, not a fixable instruction-count inefficiency.
2. *Queue-depth check* (the task explicitly warned an undersized queue would
   manufacture a false negative in the paper's favor): throughput plateaus at
   queue-depth ≥ 16. The main sweep uses depth=16, comfortably past the knee.

---

## 6. Instrumentation proof (Phase 2)

**CAT is actually binding, not a no-op.** All compute CPUs (32–47) were confirmed to
map to a single resctrl L3 domain (`mon_L3_00`, socket 0) via
`/sys/devices/system/cpu/cpu*/cache/index3/id` before any CAT run — this matters
because writing a restrictive mask to the *wrong* domain index would silently restrict
nothing and manufacture a false null result in the paper's favor. The harness
(`scripts/resctrl_clos.sh`) asserts this domain match programmatically before every
setup and always leaves the other domain's mask full. Live verification during a real
run: a 4-way scan CLOS's LLC occupancy (`mon_data/mon_L3_00/llc_occupancy`) capped near
62.6 MB (≈4 × 16 MB/way), while the paired 16-way probe CLOS grew to 207.7 MB.

**The fact array is really on CXL, the hot table is really local — checked via
`numa_maps`, not just the binary's internal placement check.** A live process's
`/proc/<pid>/numa_maps` showed the fact region as `bind:2 ... N2=250037` (100% of
sampled pages on node 2) and the hot-table+keys region as `N0=81922` (100% on node 0).

**CXL bandwidth ceiling independently reproduced fresh, not taken from historical data
on faith.** `stream-smoke` mode is single-threaded (confirmed by reading the source —
`run_stream` only pins `cpus[0]` and ignores `--threads`); the aggregate-bandwidth
characterization requires concurrent *processes*, not a `--threads` flag. Launched
1/4/8 concurrent single-threaded processes directly: 8.88 / 23.63 / 23.80 GB/s —
closely matching the historical characterization (9.41 / 23.07 / 23.64 GB/s) and
confirming aggregate CXL bandwidth saturates by ~4 concurrent streamers on this
platform, which is the mechanism behind Section 7's ratio finding. (A different,
higher figure — ~32-34 GB/s — appears elsewhere in this repo's data; that comes from a
separate hand-written aggressor microbenchmark, `bench/aggressor/stream_wb.c`, not
from `cxl_join_bench`'s own AVX2-unrolled stream implementation. Different code,
plausibly different achievable bandwidth on the same hardware — not a contradiction
requiring the same number, but worth stating explicitly rather than leaving unexplained.)

**Frequency stability:** `cycles/ref-cycles` (hardware counters, not TSC) measured
≈0.999 across every configuration in both experiments — actual core frequency tracked
the invariant-TSC-implied rate throughout, consistent with turbo disabled and the
performance governor.

**Thread pinning:** every worker thread calls `pthread_setaffinity_np` with a
single-CPU mask before entering its timed loop (or the process exits with an error) —
an architectural guarantee that a pinned thread cannot be migrated mid-measurement.
The `cpu-migrations` perf counter (~16–20 per 16-thread run) is corroborating, not
primary, evidence — it is a coarse, whole-process counter that also picks up the
unpinned main thread's setup-phase scheduling and cannot cleanly isolate steady-state
drift from the one-time affinity-correction migration expected per thread.

---

## 7. Results

### 7.1 The A-vs-D decisive gate (untuned, first pass)

Config A (fused) and a naive D (8 scan / 8 probe threads, queue-depth=8) at 16 cores,
n=30 reps each, single rep per process invocation, order fully randomized across the 60
runs.

| | Throughput Mt/s (median, 95% CI) | H cyc/access (median, 95% CI) |
|---|---:|---:|
| A (fused) | 335.4 [334.6, 336.3] | 88.67 [88.39, 88.86] |
| D (untuned 8:8, qd8) | 148.0 [147.7, 148.3] | 101.56 [101.34, 101.69] |

`T_D/T_A = 0.441` (95% CI [0.440, 0.443]) — splitting alone, untuned, already costs
over half the throughput. `H_D/H_A = 1.145` (95% CI [1.142, 1.149]) — the untuned
split is already **worse**, not neutral, on cycles/access. Both decisively past the
threshold for treating fusion as load-bearing, before any adversarial tuning of the
split or any CAT configuration is even introduced.

### 7.2 The confirmatory panel (adversarially tuned)

Three sequences, n=30 per point, CAT profiles re-applied before every single run so
CAT-on and CAT-off points could be fully randomized together:

- **Sequence 1** (16 cores, CAT off): `Q16`, `A2_16`, three split ratios (4:12, 8:8,
  12:4, queue-depth=16), `E16` (NTA).
- **Sequence 2** (16 cores, CAT toggled per run): `A3_16` vs `B16` (fused + 4-of-20-way
  CLOS); `Dref` vs `C_1way` vs `C_2way` (split at the best ratio from sequence 1, CAT
  scan-CLOS at 1 or 2 ways).
- **Sequence 3** (1 core, smaller fact size for wall-clock): `A_1c`/`Q_1c`, then
  `A2_1c`/`B_1c` (CAT toggle).

**Best split ratio is 1:3 (scan-light), confirmed a second time after the
methodology fix — this finding is robust to the correction, as expected since it's a
CXL-bandwidth-saturation effect unrelated to the hash-overhead bug:**

| Ratio (scan:probe) | Throughput Mt/s (median, 95% CI) |
|---|---:|
| 12:4 (3:1) | 80.5 [80.1, 80.8] |
| 8:8 (1:1) | 159.2 [158.7, 159.6] |
| 4:12 (1:3) | **213.3** [212.6, 213.8] |

Mechanism (Section 6): aggregate CXL bandwidth from concurrent streamers saturates by
~4 threads on this platform (independently reproduced: 23.6–23.8 GB/s at both 4 and 8
concurrent streamers). Cutting scan from 8 to 4 threads costs almost nothing in
aggregate scan throughput; the freed threads add 50% more probe parallelism.

**Splitting, corrected for the measurement bug, does not trade throughput for a better
hot-table access pattern — it costs both:**

| | Throughput Mt/s (median, 95% CI) | H cyc/access (median, 95% CI) |
|---|---:|---:|
| A (fused, seq2 ref) | 336.6 [334.5, 338.0] | 88.45 [88.18, 88.92] |
| D (split, best ratio, seq2 ref) | 214.6 [213.5, 215.5] | 95.69 [95.45, 96.13] |
| C (split, best ratio, CAT 1-way) | 215.0 [214.0, 216.6] | 95.37 [94.65, 95.96] |
| C (split, best ratio, CAT 2-way) | 209.0 [208.4, 211.0] | 97.88 [97.02, 98.22] |
| Q (quiescent) | 391.9 [387.6, 397.4] | 61.71 [60.65, 62.05] |

`T_best_split/T_A = 0.639` (95% CI [0.635, 0.645]), consistent whether measured as
`Dref` vs `A3_16` (same batch) or `Dref` vs `A2_16` (cross-batch, seq1) — the two
agree to three significant figures now that the confound is removed, which is itself
evidence the fix worked (before the fix, same-batch vs cross-batch pairings disagreed
in sign; see the note in Section 8).

`R = −0.257` (95% CI [−0.286, −0.222]) using the seq2 batch reference, `−0.249`
(95% CI [−0.279, −0.214]) using the seq1 batch reference. **Both batches now agree in
sign and are close in magnitude.** Splitting plus CAT does not recover any of the
fused-mode hot-table tax — it adds to it, by about a quarter of the total
quiescent-to-loaded gap.

`R_vs_D = 0.009` (95% CI [−0.009, 0.033]) — CAT's own marginal contribution, once
splitting's cost is already priced in, is statistically indistinguishable from zero.

**Why H gets worse, not just throughput — the mechanism, corrected from the earlier
report's wrong explanation.** The earlier version of this report said "the separation
itself did the real work" — implying splitting improved `H`. It didn't; the data now
shows the opposite. The right mechanism, which a reviewer of the earlier draft pointed
out and which checks out against the actual `run_split` code: **splitting relocates
the stream, it does not eliminate the interleaving.** A probe thread's loop is
`for i in buf: probe(table, buf[i].fk)` — still a one-pass read (now of the local
queue buffer instead of the CXL fact array) interleaved with hot-table reuse, in the
same thread. CAT, being purely context-scoped, cannot separate those two access classes
inside the probe thread any more than it could when the stream was CXL-sourced. On top
of that, the split adds real synchronization cost (queue wait, visible now that
probe-side `H` is wall-clock inclusive — Section 4), which is why `H` for split comes
out *worse* than fused rather than merely "no better." This is a stronger, more
general form of the paper's thesis: it is not specifically "CXL streaming vs.
hot-table reuse" that is inseparable when fused — **any interleaved one-pass-plus-reuse
access pattern in a single thread is inseparable by a context-scoped mechanism,
regardless of where the streamed data physically lives.**

**Decomposing `H` to check this isn't just a synchronization artifact — MPKI and a
compute-only cycle count, both already captured by the existing instrumentation and
requiring no rerun.** The wall-clock-inclusive `H` fix in Section 4 is the right
convention for comparability, but it means split-mode `H` bundles queue-wait cost
together with cache-miss cost, and a careful reader shouldn't take "H is worse" as
automatically meaning "the access pattern itself is worse" — the two are different
claims. Both decompositions were checked directly rather than asserted:

| | MPKI (median) | Compute-only probe `H` (median, excludes queue-wait) | Wall-inclusive `H` (median) |
|---|---:|---:|---:|
| Q (quiescent) | 178.5 | — | 61.71 |
| A (fused) | 194.5–200.0 | — (no queue, always wall-equivalent) | 88.45–88.62 |
| D (split, best ratio) | 249.8–259.3 | 92.5–93.3 | 95.7–96.4 |
| C (split, CAT 1-way) | 233.3 | 92.3 | 95.4 |
| C (split, CAT 2-way) | 290.0 | 94.9 | 97.9 |

Two things follow from this. First, MPKI is **higher** for split than for fused
(≈250–290 vs ≈195–200), not lower — splitting does not reduce the rate of LLC misses
against the hot table, which is consistent with the "relocated stream, not eliminated
interleaving" mechanism above, not merely an artifact of it. Second, even the
compute-only probe cost (92.3–94.9), which entirely excludes queue-wait time and gives
the split configuration its most generous possible reading, is still higher than
fused's wall-clock cost (88.45–88.62). This directly checks (and does not support) the
natural guess that "the probe's cache behavior is genuinely better under splitting,
synchronization just eats more than the gain" — the data says the access pattern
itself is worse, not only the synchronization layered on top of it. `H` is not
over-claiming here; the decomposition confirms rather than contradicts the headline
finding, and both numbers are reported explicitly rather than one being asserted from
the other.

**CAT on fused mode makes it actively worse — confirmed at both core counts:**

| | H_B/H_A (median, 95% CI) | T_B/T_A (median, 95% CI) |
|---|---:|---:|
| 16 cores (4-of-20-way CLOS) | 1.434× [1.426, 1.440] | 0.697× [0.693, 0.701] |
| 1 core (4-of-20-way CLOS) | 1.345× [1.338, 1.355] | 0.744× [0.738, 0.748] |

The 1-core version is the cleanest demonstration in this experiment: one thread, one
core, no cross-core contention possible, and restricting its cache ways still makes
the fused workload worse on both axes.

**The claim the paper actually needs is stronger than "one restrictive allocation
hurts" — it's that *no* allocation helps. Checked with a way sweep, not asserted:**

| Ways given to the single fused CLOS | H cyc/access (median) | Throughput Mt/s (median) |
|---:|---:|---:|
| 4 of 20 | 126.86 | 234.4 |
| 8 of 20 | 115.81 | 253.4 |
| 12 of 20 | 105.12 | 281.0 |
| 20 of 20 (unrestricted, fresh reference) | 87.65 | 337.0 |

Monotonic in ways, as expected — but even at 12 of 20 ways (60% of the entire LLC,
comfortably more than the hot table's own 53%-of-LLC footprint), `H` is still 20%
worse than giving the fused class no restriction at all. There is no way count in this
sweep, including a generous one, that recovers unrestricted performance. The
mechanism is precise, not just empirical: any restriction narrow enough to matter
constrains both the streaming and the reused access classes together, because CAT
cannot address them separately within one context — so the only "allocation" that
doesn't hurt is the trivial one of not restricting at all, which is not a form of
cache admission control.

**The confound-free same-context tax (1 core, no CAT, no split — just the fused
kernel against quiescent):** `H_A_1c/H_Q_1c = 1.475×` (95% CI [1.470, 1.483]). The tax
is fully present with a single thread on a single core doing nothing but interleaving
its own stream and probe accesses.

**Checked whether this number is inflated by comparing two different code paths
(`run_morsel` for A, `run_hot_probe` for Q) rather than real interference — the check
surfaced something more interesting than a simple artifact, and is reported honestly
rather than resolved into a clean number it doesn't support.** Added a same-code-path
quiescent variant (`--no-stream`): identical threading and loop structure to `run_morsel`,
but the "fact" data is a small buffer that stays cache-resident, so there is no real
CXL stream. First attempt used `fact[i % local_n]`; since `local_n` is a runtime value
even though it is always a power of 2, the compiler could not strength-reduce the
modulo to a shift, and the resulting per-tuple integer division swamped the
measurement (the no-stream variant came out slower than the real streaming case,
which is not a sensible result — fixed by masking explicitly once `local_n`'s
power-of-2 invariant is enforced). After that fix: **the no-stream, same-code-path
variant is still measurably slower than the real fused case with a live CXL stream**
(91.5 vs 84.4 cycles/access in a 1-core check), which is the opposite of "code-path
overhead inflates the tax." The most likely explanation is that the CXL load's long,
independent latency in the real case overlaps with the hot-table probe's own latency
via out-of-order execution (both are memory-level-parallelism-eligible, long-latency,
mutually independent accesses per iteration), so the two costs partially hide each
other — removing the CXL load removes that overlap opportunity and exposes more of
the probe's own latency serially. This is a plausible mechanism, not a confirmed one:
it was not verified against direct microarchitectural counters (outstanding-load or
MLP-specific counters), and is flagged as exactly that — a hypothesis — rather than
asserted as settled. What this check does establish, regardless of which mechanism is
right: **the same-context tax number (1.475×) is not an overstatement caused by
comparing mismatched code paths.** If anything, a cleaner quiescent baseline appears
harder to construct than "just use the same loop," not easier, and the true isolated
interference effect could be argued either larger or smaller than 1.475× depending on
how the overlap effect is accounted for — this is flagged as an open methodological
question for anyone building on this number, not closed by this report.

**A cheap preview of the radix-partitioning question: does the tax survive when the
reused structure unambiguously fits in one core's private cache?** Before committing
to building a full radix-partitioned join (which also pays a separate, real cost —
the partitioning pass is itself a streaming write, a different potential source of
interference not tested here), checked the simpler question directly: shrink
`--hot-bytes` to 512 KB (comfortably inside this chip's 2 MB private L2, confirmed via
`/sys/devices/system/cpu/cpu32/cache/index2/size`) and re-run the same 1-core
fused-vs-quiescent comparison.

| Hot table size | H_A/H_Q (median) |
|---|---:|
| 512 KB (fits in private L2 with margin) | 1.604 |
| 177 MB (53% of LLC, the main experiment's size) | 1.475 |

The tax does not shrink at L2 scale — it is, if anything, slightly larger. This is
evidence against the naive version of "just partition the build side and the problem
goes away": even a build-side partition small enough to live entirely in one core's
private cache still shows the same-thread interleaving tax, because (per the mechanism
above) the tax appears to come from interleaving a one-pass stream with random-access
reuse in one thread, not from LLC-capacity contention specifically — shrinking the
reused structure changes where it lives, not whether it's interleaved with a stream in
the same thread. This is a genuine preview, not a full test: it does not include the
partitioning pass's own streaming-write cost, does not test multiple partitions across
threads, and used only one size point. A full radix-partitioned join mode is the
correct next experiment to make this airtight, and is scoped as future work, not
delivered here.

**E (`PREFETCHNTA`, real hardware's only proxy for object-scoped non-allocation) does
not help either — this experiment establishes a "nothing works" result on real
silicon:**

| | Throughput ratio vs A (median) | H vs A |
|---|---:|---:|
| E16 (NTA) | 298.1/335.5 = 0.889 | 98.37 vs 88.62 — **11.5% worse** |

Checked whether this is a fixable parameter choice rather than a real effect: swept
`--pf-distance` ∈ {0, 8, 32, 128, 512}; cycles/access ranged 94.5–98.4 with no
monotonic improvement, consistent with the platform's own historical NTA
characterization (software prefetch hints disable the hardware prefetcher's automatic
action, and the lost hardware-prefetch benefit outweighs the reduced pollution on this
platform). **The panel therefore shows CAT-on-fused fails, splitting fails, CAT-on-split
adds nothing, and the real-hardware NTA proxy fails — every mechanism tested on actual
silicon either does nothing or hurts.** The positive case for the paper's proposed
mechanism (true, overhead-free object-scoped non-allocation) rests entirely on the
gem5 side of this project, not on any measurement in this report. A reviewer should be
told this plainly rather than left to infer it.

---

## 8. Full data table (all 17 measured configurations, n=30 each, corrected data)

| Label | n | Mode | Threads (scan/probe) | Queue depth | Policy | Throughput Mt/s or Mops/s (median) | CoV | 95% CI | H cyc/access (median) | CoV | 95% CI |
|---|---:|---|---|---:|---|---:|---:|---|---:|---:|---|
| A2_16 | 30 | morsel | - | - | wb | 335.463 | 0.93% | [334.776, 337.145] | 88.624 | 0.96% | [88.275, 89.061] |
| A2_1c | 30 | morsel | - | - | wb | 21.277 | 1.73% | [21.185, 21.384] | 89.192 | 1.70% | [88.747, 89.586] |
| A3_16 | 30 | morsel | - | - | wb | 336.582 | 1.53% | [334.468, 338.024] | 88.454 | 1.48% | [88.178, 88.918] |
| A_1c | 30 | morsel | - | - | wb | 21.210 | 0.89% | [21.121, 21.253] | 89.468 | 0.89% | [89.295, 89.850] |
| B16 | 30 | morsel | - | - | wb | 234.443 | 3.60% | [233.890, 234.979] | 126.861 | 2.99% | [126.498, 127.073] |
| B_1c | 30 | morsel | - | - | wb | 15.818 | 5.27% | [15.757, 15.885] | 120.009 | 4.76% | [119.511, 120.477] |
| C_1way | 30 | split | 4/12 | 16 | wb | 214.983 | 1.94% | [213.957, 216.642] | 95.369 | 2.03% | [94.652, 95.963] |
| C_2way | 30 | split | 4/12 | 16 | wb | 208.963 | 2.05% | [208.384, 210.951] | 97.875 | 2.03% | [97.017, 98.216] |
| D_1_1 | 30 | split | 8/8 | 16 | wb | 159.217 | 0.74% | [158.690, 159.621] | 94.104 | 0.70% | [93.834, 94.485] |
| D_1_3 | 30 | split | 4/12 | 16 | wb | 213.330 | 0.77% | [212.589, 213.790] | 96.390 | 0.65% | [96.043, 96.599] |
| D_3_1 | 30 | split | 12/4 | 16 | wb | 80.511 | 0.87% | [80.135, 80.848] | 93.111 | 0.80% | [92.982, 93.610] |
| Dref | 30 | split | 4/12 | 16 | wb | 214.577 | 2.03% | [213.489, 215.488] | 95.688 | 2.11% | [95.453, 96.127] |
| E16 | 30 | morsel | - | - | nta | 298.065 | 1.75% | [294.928, 300.453] | 98.365 | 1.31% | [97.618, 98.832] |
| Q16 | 30 | hot-probe | - | - | wb | 391.925 | 3.97% | [387.559, 397.429] | 61.711 | 4.39% | [60.651, 62.048] |
| Q_1c | 30 | hot-probe | - | - | wb | 31.245 | 1.67% | [31.209, 31.440] | 60.710 | 1.64% | [60.334, 60.774] |
| gate_A_untuned_16c | 30 | morsel | - | - | wb | 335.385 | 1.00% | [334.595, 336.329] | 88.673 | 1.01% | [88.385, 88.863] |
| gate_D_8x8_qd8_16c | 30 | split | 8/8 | 8 | wb | 147.962 | 0.45% | [147.708, 148.259] | 101.559 | 0.41% | [101.339, 101.687] |

**On batch consistency, now versus before the fix:** `A2_16`/`A3_16` (independent
randomized batches, seq1 and seq2) agree to within 0.3% (335.5 vs 336.6 Mt/s). Before
the result-hash fix, the same-batch `H` deltas for "does splitting change H" disagreed
in *sign* between seq1 (+0.488) and seq2 (−2.983); after the fix, both batches agree
in sign and are close in magnitude for `R` (−0.249 vs −0.257). This convergence is
itself evidence the earlier disagreement was the hash-overhead artifact, not
irreducible noise.

**Sweep points skipped for time, disclosed explicitly:** the original design called for
scan-CLOS ways ∈ {1, 2, 4} at all three ratios × two queue depths (18 points). This
panel measured 3 ratios × 1 queue depth for D, and 2 way-points × 1 ratio (the
empirically-best one) for C — 5 of 18 combinations, chosen adversarially rather than
arbitrarily. The 4-way scan-CLOS point, and the 1:3/3:1 ratios for C specifically, were
not measured. Given C already shows no recovery (indeed slightly worse `H`) at 1 and 2
ways relative to D, and a coarser CAT allocation can only move C's behavior closer to
D's fully unrestricted case, there is no mechanistic reason to expect a 4-way point to
look qualitatively different — but this is stated as an expectation, not a measured
fact.

---

## 9. Environment capture

| Item | Value |
|---|---|
| CPU | Intel Xeon Platinum 8592+, stepping 2, microcode `0x210002d3` |
| Kernel | Linux 7.0.0-22-generic (Ubuntu), `PREEMPT_DYNAMIC` |
| Governor / turbo | `performance`, turbo disabled (`no_turbo=1`) |
| Hugepages | Static hugetlbfs pool, 2 MB pages, 34288 pages reserved; THP not used by this workload |
| `resctrl` | Mounted; L3: 15 CLOSes, 20 ways/domain, 2 domains (`mon_L3_00`=socket 0, `mon_L3_01`=socket 1); CDP off; `min_cbm_bits=1`; MB: 15 CLOSes |
| Compute CPUs used | 32–47 (physical cores, no SMT siblings; SMT sibling of 32 is 160, confirmed unused) — all confirmed L3 domain 0 |
| NUMA topology | node 0: 128 logical CPUs (64 physical + SMT), 515 GB; node 1: same, other socket; node 2: 0 CPUs, 254 GB, CXL-only |
| CXL device | Micron Technology Device 6400 (CXL 2.0), PCI `0000:27:00.0`, `region0` 274,877,906,944 B, interleave ways=1 (**not** Samsung Type-3 — see Section 3) |
| Prefetcher MSR `0x1a4` | `0x0` on sampled cores (all hardware prefetchers enabled, none disabled) |
| Compiler / flags | g++ (Ubuntu 15.2.0-16ubuntu1) 15.2.0, `-O3 -std=c++17 -Wall -Wextra -Wpedantic -march=native -pthread` |
| Benchmark commit | `f6e15c1e0bdea9412c51dfe41ef3ecc218ef083a` (working tree modified for this experiment — `--mode split`, `--scan-memcpy` added; correctness-check hooks added and then removed from the timed path per Section 4; fused path `join_range` byte-for-byte unchanged throughout) |
| Frequency stability | `cycles/ref-cycles` median ≈ 0.999 across every configuration measured |

---

## 10. What surprised us, what couldn't be measured, and what a reviewer would attack

**Surprised us:**
- The optimal split ratio (1:3) is the opposite of what per-tuple cost balance at 8:8
  predicts — driven by CXL bandwidth saturating at ~4 concurrent streamers on this
  platform, independently reproduced, not by the probe side at all.
- Splitting is not merely expensive in throughput — once measured comparably, it makes
  `H` *worse* than fusion, not better. The paper's strongest hardware evidence for
  fusion being load-bearing is arguably this, not the throughput number.
- A self-inflicted one: a "free" correctness-checking flag turned out to cost 12% on
  one configuration and 3% on another, and the discrepancy was large enough to flip
  the sign of a reported effect. Caught by re-checking a side question from review, not
  by a planned check — worth remembering that "this flag is off by default and adding
  it shouldn't matter" needs verifying in the *enabled* state too, not just the
  disabled one.
- A second self-inflicted one, caught while trying to *fix* the first: a same-code-path
  quiescent diagnostic came out slower than the real fused case, which made no sense
  until an unreduced runtime modulo in the diagnostic's own hot loop was found and
  fixed. After the fix, the diagnostic *still* came out slower than the real fused
  case — which turned out not to be another bug, but a genuine and interesting
  micro-architectural finding (Section 7): the real CXL stream's latency appears to
  overlap with the hot-table probe's own latency rather than simply adding to it.
- MPKI is *higher*, not lower, for the split configuration than for fused (Section 7)
  — checked directly rather than assumed, and it rules out the natural guess that
  splitting's `H` cost is "just" synchronization overhead on top of an improved access
  pattern.
- The same-context tax does not shrink when the hot table is shrunk to fit in private
  L2 — if anything it is slightly larger. Not what a pure LLC-capacity-contention
  story would predict.

**Could not measure / explicitly out of scope:**
- No real-hardware measurement in this experiment shows the paper's proposed mechanism
  (true, overhead-free object-scoped non-allocation) working — that evidence is
  entirely in the gem5 side of this project. This report only establishes that the
  alternatives (CAT-on-fused, split, CAT-on-split, NTA-as-proxy) all fail or hurt on
  real silicon.
- The full 18-point ratio × way × queue-depth grid for C/D was not run; 5
  adversarially-chosen points were (Section 8). The CAT-way sweep for B (4/8/12/20 ways)
  was completed and shows a monotonic trend with no way count recovering unrestricted
  performance (Section 7).
- **A full radix-partitioned join was not built.** A cheap, targeted preview (Section
  7: shrink the hot table to L2 size, re-run the 1-core tax comparison) found the tax
  does not disappear and is not smaller at that scale — evidence against the naive
  version of the partitioning defense, but not a substitute for the real experiment.
  A true radix-partitioned join also pays a separate cost this preview does not
  measure at all: the partitioning pass itself is a streaming write, potentially its
  own source of interference. This experiment's 53%-of-LLC hot table remains an
  explicit premise (a non-partitioned build side) that the paper needs to argue,
  not assume — the preview narrows the risk but does not close it.
- The same-code-path quiescent check (Section 7) opened a question it did not close:
  whether the 1.475× same-context tax is inflated, deflated, or roughly accurate
  relative to a true code-path-matched, interference-only baseline is now an open
  question, not a resolved one, pending direct microarchitectural (MLP/outstanding-load)
  instrumentation this report does not have.
- Whether the `cpu-migrations` perf counter's baseline reflects only the one-time
  affinity-correction at thread creation, or some additional unpinned-main-thread
  noise, was not fully isolated. The pinning guarantee that actually matters (a
  single-CPU affinity mask, set once, never changed) is architectural, established
  from source, not inferred from this counter.
- This report can audit only what it directly measures. It cannot audit prose in a
  paper draft it was not given access to (e.g., which platform a given bandwidth
  figure like "15.8 GB/s" or "4.2 GB/s WC" is attributed to in the introduction) —
  that check has to happen against the actual draft text, not against this report.

**What we'd expect a skeptical reviewer to attack, and the pre-empt:**
- *"You only tried one queue implementation."* Queue depth was swept and plateaus at
  16; a lock-free queue wouldn't change the copy cost, which a memcpy-vs-loop check
  isolated as the actual bottleneck, not synchronization overhead.
- *"Zero-copy range handoff (scan publishes `[start,end)`, probe reads CXL directly)
  would avoid the copy tax."* This just relocates the identical fused-context problem
  to whichever thread ends up issuing both the CXL read and the hot-table probe — it
  is not an escape from the paper's thesis, it is a restatement of it one hop
  downstream.
- *"You only configured CAT badly — a 170 MB working set in 4 of 20 ways is an unfair
  test."* Addressed with a sweep, not just the 4-way point: 8 and 12 ways were also
  measured (Section 7), and the degradation shrinks monotonically but never reaches
  parity with no restriction, even at 12 of 20 ways (60% of the entire LLC). There is
  no way count in the sweep that helps.
- *"What about a partitioned join?"* Addressed above as an explicit, unaddressed scope
  gap — not dismissed.
- *"Did you check your own instrumentation for overhead?"* Yes, twice — the compiler's
  handling of the scan-side copy, and (after this report's own correction) the
  correctness-check flag's cost in its enabled state. The second one wasn't caught
  until a fairly late stage, and that fact is reported rather than hidden.

---

## 11. Reproducibility

```
# Build
cd benchmarks/e2e/hash_join && make native test

# Correctness cross-check (fused vs split, same seed) -- run once, not per timed rep
./build/cxl_join_bench --mode morsel --policy wb --fact-node 2 --hot-node 0 \
  --fact-bytes 1g --hot-bytes 177838489 --cpu-list 32-47 --morsel 1m \
  --threads 16 --reps 1 --result-hash
./build/cxl_join_bench --mode split --policy wb --fact-node 2 --hot-node 0 \
  --fact-bytes 1g --hot-bytes 177838489 --cpu-list 32-47 --morsel 1m \
  --scan-threads 4 --probe-threads 12 --queue-depth 16 --reps 1 --result-hash
# matches/sum/result_hash must be identical between the two

# CAT harness (requires passwordless sudo; asserts L3 domain match before writing)
sudo bash scripts/resctrl_clos.sh setup_c 1 "32-35" "36-47"
sudo bash scripts/resctrl_clos.sh verify
sudo bash scripts/resctrl_clos.sh teardown

# CXL aggregate bandwidth (stream-smoke is single-threaded; launch N processes)
for cpu in 32 33 34 35; do
  ./build/cxl_join_bench --mode stream-smoke --policy wb --fact-node 2 \
    --fact-bytes 1g --cpu-list $cpu --reps 3 > /tmp/bw_$cpu.json &
done
wait

# Full experiment drivers (timed paths do NOT use --result-hash -- see Section 4)
python3 scripts/run_gate_a_vs_d.py            # Experiment 1
python3 scripts/run_confirmatory_panel.py     # Experiment 2
python3 scripts/regen_summary.py              # rebuild summary.csv from raw/

# Same-code-path quiescent diagnostic (Section 7) and L2-sized hot-table preview
./build/cxl_join_bench --mode morsel --policy wb --fact-node 2 --hot-node 0 \
  --fact-bytes 256m --hot-bytes 177838489 --cpu-list 32 --morsel 1m \
  --threads 1 --reps 1 --no-stream
./build/cxl_join_bench --mode morsel --policy wb --fact-node 2 --hot-node 0 \
  --fact-bytes 256m --hot-bytes 512k --cpu-list 32 --morsel 1m --threads 1 --reps 1
```

All individual run records (raw JSON, one per invocation, nothing aggregated away) are
preserved in `results/clos_split/raw/` (660 files: 60 gate + 450 panel + 90 CAT-way-sweep
+ 60 L2-preview) alongside this report. The superseded, contaminated first-pass data is
preserved separately at `results/clos_split/raw_v1_contaminated_with_hash_overhead/` for
anyone auditing the correction in Section 4. **One gap, disclosed rather than hidden:**
the same-code-path quiescent diagnostic (the NS-vs-A-vs-Q check in Section 7) was run
as an ad hoc script during review and its per-run JSON was not persisted to disk — only
the summary statistics quoted in Section 7 exist. Anyone wanting to re-verify that
specific finding should re-run the command above rather than look for raw files that
don't exist for it.
