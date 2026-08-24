# Mechanism decomposition: does H2 address the fused same-thread tax?

**Purpose:** the CLOS-split experiment established that no context-scoped mechanism
(CAT, in any way allocation, at either core count) helps the fused same-thread tax,
and that this tax is scale-invariant — present at 1 core with no cross-core confound.
The paper has made this its decisive case. This experiment asks the question that
follows: **is the tax the kind of tax H2 (non-allocation into the shared LLC) can
actually remove, or does it live somewhere H2 doesn't reach?**

---

## Verdict

> **`Δ_LLC_upper/Δ_total` is at most ≈0.31 and could be as low as 0, depending on
> which L2-resident reference point is used — both readings fall at or below the
> pre-registered "H2 story in trouble" threshold (≤0.30), and neither approaches
> the "sound" threshold (≥0.60). Three independent instruments (the L2-fit-size
> floor, a bandwidth-matched remote-socket queueing control, and a direct
> per-load latency histogram) agree: most of the fused tax does not live in the
> shared-LLC-residency channel H2 addresses.**

| | 1 core | 16 cores |
|---|---:|---:|
| `Δ_total` (170MB operating point) | 27.31 cyc | 27.63 cyc |
| `Δ_LLC_upper` (strict L2-fit reference, 256K) | 0.00 cyc (0%) | 0.00 cyc (0%) |
| `Δ_LLC_upper` (generous L2-fit reference, 1M) | 8.51 cyc (31%) | 7.52 cyc (27%) |

Per the pre-registered rule, this is **"H2 story in trouble,"** not "sound," and not
even a clean "partial." Section 8 discusses what this means for the paper.

---

## 1. The pre-registered decomposition

```
Δ_total = H_loaded − H_quiescent
Δ_LLC_upper ≈ max(0, Δ_total − Δ_L2fit − Δ_M5 − Δ_M3)
```

`Δ_L2fit`, `Δ_M5`, `Δ_M3` are each named and reported separately below; nothing is
inferred that wasn't measured (Section 7 on M3/M4 explains why `Δ_M3` is set to `0`
in the primary arithmetic rather than estimated).

### Decomposition table (absolute cycles per hot-table access, 170MB operating point)

| Component | 1 core | 16 cores | H2 addresses it? |
|---|---:|---:|---|
| `Δ_total` (measured, no PEBS) | 27.31 | 27.63 | — |
| `Δ_L2fit` — strict reference (256K, unambiguously L2-resident) | 27.80 | 27.32 | No — this floor exists with no LLC involvement at all |
| `Δ_L2fit` — generous reference (1M, the minimum point on the whole M2 curve) | 19.25 | 19.31 | No |
| `Δ_M5` — bandwidth-matched remote-socket residual (component d proxy) | −0.44 | +0.80 | No — both ≈0, memory-path queueing alone explains ~nothing |
| `Δ_M3` — outstanding-miss/MSHR contention (component c) | **unattributed** (qualitative only, see Section 6) | unattributed | No — real signal (FB_FULL grows 3.8–11.7×), not convertible to clean cycles here |
| **`Δ_LLC_upper` (strict)** | **0.00 (0%)** | **0.00 (0%)** | Upper bound on what's left for H2 |
| **`Δ_LLC_upper` (generous)** | **8.51 (31%)** | **7.52 (27%)** | Upper bound on what's left for H2 |

Components do not sum exactly to `Δ_total` by construction (`Δ_LLC_upper` is defined
as the *residual* after subtracting everything else, clamped at 0) — this is the
pre-registered arithmetic, not a discrepancy to explain away. What the residual
represents, honestly: whatever is left after removing (i) the tax already present at
L2-fit scale and (ii) the bandwidth-matched non-local-cache-touching queueing
control. It is an **upper bound** on H2's addressable share, not a clean isolation of
component (a) alone — some of it could still be private L1/L2 displacement
(component b, which H2 explicitly does not touch) or unattributed MSHR contention
(component c).

---

## 2. M2: the hot-set size sweep — absolute cycles, not just ratios

Full curve at both core counts, n=30 per point, `--no-stream`-free (real Q vs A),
no PEBS:

| Size | `H_Q` (1c) | `H_A` (1c) | `Δ_total` (1c) | `H_Q` (16c) | `H_A` (16c) | `Δ_total` (16c) |
|---|---:|---:|---:|---:|---:|---:|
| 256K | 24.53 | 52.32 | **27.80** | 25.24 | 52.56 | **27.32** |
| 512K | 32.89 | 53.80 | 20.90 | 33.23 | 54.04 | 20.81 |
| 1M | 36.66 | 55.90 | **19.25** | 36.85 | 56.16 | **19.31** |
| 2M | 39.74 | 60.35 | 20.61 | 39.68 | 60.55 | 20.88 |
| 4M | 43.01 | 64.54 | 21.53 | 42.86 | 65.07 | 22.21 |
| 16M | 46.34 | 69.86 | 23.52 | 46.60 | 69.58 | 22.98 |
| 64M | 47.87 | 73.58 | 25.71 | 48.95 | 72.93 | 23.98 |
| 170M | 58.06 | 85.38 | 27.31 | 59.50 | 87.13 | 27.63 |

**`Δ_total` is non-monotonic and U-shaped**, not increasing with hot-set size as a
pure LLC-capacity story would predict: large at 256K, a minimum around 1M, rising
back to nearly the 256K level by 170M. This is the same shape at both core counts —
not a fluke.

**This directly falsifies the earlier report's ratio-only framing.** The CLOS-split
report's "512KB tax is larger (1.60×) than the 170MB tax (1.47×)" was a genuine ratio
artifact: `H_Q` at 512K is much smaller than at 170M, inflating the ratio even though
the absolute penalty (20.9 cyc) is *smaller* than at 170M (27.3 cyc). The 256K point,
not 512K, actually carries the highest ratio (≈2.1×) *and* is close to the highest
absolute delta in the whole curve — a case the earlier report never examined,
because it only looked at 512K.

**Why this matters for `Δ_L2fit`:** every point from 256K to 2M is comfortably inside
the 2MB private L2, and yet `Δ_total` in that whole range (19.2–27.8 cyc) already
covers essentially the *entire* range spanned by the full curve up to 170M
(19.2–27.6 cyc). A tax that's already this large before the LLC can possibly be
involved cannot be attributed to LLC residency.

---

## 3. Hot-table load-latency histograms, quiescent vs loaded (M1, corroborating)

PEBS `mem-loads,ldlat=4/pp -W` (weight/latency only — no per-sample address, per the
Phase 0/1 hardware limitation), at the 170MB operating point:

| Band | 1c quiescent | 1c fused | 16c quiescent | 16c fused |
|---|---:|---:|---:|---:|
| L1 (<12 cyc) | 17.44% | 16.51% | 14.58% | 13.02% |
| L2 (12–30 cyc) | 16.12% | 14.73% | 16.65% | 16.37% |
| LLC (30–100 cyc) | 62.65% | 63.53% | 64.96% | 65.57% |
| memory (100–400 cyc) | 3.70% | 5.09% | 3.73% | 4.95% |
| slow/remote (≥400 cyc) | 0.09% | 0.13% | 0.08% | 0.10% |

There is a small, consistent, qualitatively-expected shift: mass moves out of L1/L2
and into the memory band under load (roughly 1–1.5 percentage points at each core
count), while the LLC band itself barely moves (+0.6 to +0.9pp) — some private-cache
residency is lost, and a modest fraction of what's lost falls all the way to memory
rather than being absorbed by the LLC. This is the qualitatively-expected direction.

**But the magnitude does not explain the tax.** Converting the histogram to a
weighted-average latency (band midpoints 6/21/65/250/600 cycles) gives an implied
delta of only **3.9 cycles at 1 core and 3.4 cycles at 16 cores** — against an actual
measured `Δ_total` (at this same 256MB/1GB fact-bytes scale, not the 1GB/170MB scale
used elsewhere) of **32.8 and 31.8 cycles respectively**. The direct per-load latency
instrument accounts for roughly **12%** of the real tax. Most of it is not explained
by individual loads taking longer, as directly measured — it lives somewhere this
instrument cannot see at all (execution-level interaction, not per-load memory
latency). This is independent, corroborating evidence for the same conclusion M2 and
M5 point to, from a completely different measurement channel.

---

## 4. M5: bandwidth-matched remote-socket residual (component d)

A single stream-smoke process on a remote-socket (node 1) core, duty-cycled via
`SIGSTOP`/`SIGCONT` (not process restart — see Section 6 for why) to approximate the
fused case's own achieved aggregate bandwidth, running concurrently with the local
hot-table probe:

| | Target BW | Achieved BW | `H_quiescent` | `H_with_remote` | `Δ_M5` |
|---|---:|---:|---:|---:|---:|
| 1 core | 0.339 GB/s | 0.340 GB/s | 57.35 cyc | 56.91 cyc | **−0.44 cyc** |
| 16 cores | 5.376 GB/s | 5.220 GB/s | 54.09 cyc | 54.88 cyc | **+0.80 cyc** |

Bandwidth matched closely at 1 core (0.340 vs 0.339 target). At 16 cores, the
achieved rate (5.22 GB/s) is the best available, not the exact target — node 1's own
single-thread CXL ceiling is 5.22 GB/s (measured fresh, `--huge2m`, continuous), and
this is genuinely lower than node 0's (node distance to the CXL device: node1→node2
is 24 vs node0→node2's 14, from `numactl -H` — a real topology fact, not a
measurement artifact), so 5.376 GB/s was not achievable from node 1 even running the
remote thread flat out. Both arms' achieved bandwidth are reported as measured, not
adjusted to make the match look better than it is.

**Both deltas are indistinguishable from zero relative to `Δ_total` (~27 cyc).**
Memory-path queueing — CXL link, mesh, CHA/TOR, memory controller — consuming
comparable bandwidth but never touching this core's local caches, produces
essentially no residual tax on the local probe. This is treated as an **upper
bound** on component (d), not a pure isolation (the remote stream still loads part
of the mesh), and even as an upper bound it is close to zero.

---

## 5. M3/M4: outstanding-miss occupancy and CHA TOR latency (qualitative)

Small perf-stat groups only (≤2 offcore-response-class events per invocation,
confirmed necessary in Phase 0 recon), n=30, quiescent vs loaded, at the 170MB
operating point. All groups showed 100% coverage (no multiplexing) except where
noted.

**M3 (component c proxy):**

| Metric | 1c ratio (loaded/quiescent) | 16c ratio |
|---|---:|---:|
| `L1D_PEND_MISS.FB_FULL` (fill-buffer-full events) | **3.84×** | **11.68×** |
| Average outstanding depth (`offcore_requests_outstanding.data_rd / offcore_requests.data_rd`) | 1.01× (flat) | 0.90× (slightly down, high CoV at 16c: 14.9%) |

These two proxies for the same underlying mechanism disagree in magnitude and, at 16
cores, in direction. `FB_FULL` (a saturation/tail signal — how often the fill buffer
was completely exhausted) grows sharply under load. Average outstanding depth (a mean
signal) does not. This is reported as-is rather than reconciled into one story: real
saturation events are clearly more frequent under load, but that does not
mechanically translate into a validated per-access cycle cost without a causal model
this experiment does not have. **`Δ_M3` is therefore reported as `0` (unattributed)
in the primary arithmetic** — a conservative choice: crediting it with a nonzero
value would only *lower* `Δ_LLC_upper` further (strengthen "in trouble"), so setting
it to zero does not shade the verdict toward the paper's preferred answer; if
anything it is the more generous-to-H2 choice.

**M4 (component d corroboration, CHA TOR average latency, uncore cycles):**

| Destination | 1c quiescent | 1c fused | Δ% | 16c quiescent | 16c fused | Δ% |
|---|---:|---:|---:|---:|---:|---:|
| All IA misses | 322.1 | 346.3 | +7.5% | 365.0 | 425.7 | +16.6% |
| Local DDR (hot-table-destined) | 263.2 | 300.5 | **+14.2%** | 261.3 | 343.2 | **+31.4%** |
| CXL-destined | 491.5 | 468.8 | −4.6%* | 562.5 | 481.2 | −14.5%* |

\* **The CXL-destined branch during quiescent is not meaningful as this workload's own
signal.** These are system-wide (`-a`) uncore counters on a shared 256-CPU host, and
the quiescent condition generates essentially zero CXL traffic of its own (hot-probe
mode never touches the fact stream) — a nonzero reading there is other users'
background CXL activity, not this experiment's. The CXL branch is reported as
single-arm (loaded-only) context, not a quiescent-vs-loaded delta.

The local-DDR branch (both arms genuinely reflect this workload, modulo the same
shared-host background-noise caveat, mitigated by randomized/back-to-back timing)
shows real, substantial growth in average LLC-miss latency under load — misses to the
hot table's own destination become measurably *more expensive*, not just more
frequent. This corroborates that queueing/contention is a real, present effect —
consistent with M5's small-but-nonzero and mixed-sign deltas — while still not adding
up, on its own, to most of `Δ_total`.

---

## 6. Phase 1 validation and instrumentation notes, carried forward

**Instrument validated against known cases** (Phase 1, reconfirmed here): L1-fit
(16K, 86.4% mass in L1 band), L2-fit (512K, 86.4% in L2 band), LLC-fit (32M, 61.2% in
LLC band), beyond-LLC (400M, mass visibly shifts into the memory band). The
weight-only PEBS histogram recovers the correct answer at every boundary.

**Instrumentation overhead measured, corrected from an earlier mislabeling.** An
initial overhead check accidentally compared two *fused* configurations at different
scale (a mode-selection mistake, not a real "flat tax" finding) — caught and
corrected before Phase 2 by rerunning with the exact `--mode hot-probe` / `--mode
morsel` configuration matching CLOS-split's `A_1c`/`Q_1c`. Corrected overhead: **2.11%
(quiescent) / 3.36% (fused)** for the PEBS-active histogram runs — real, roughly
uniform, confined entirely to Section 3's corroborating histograms and never used in
`Δ_total`, `Δ_M5`, or any other decision-rule quantity.

**A genuine, checked microarchitectural finding, not asserted from a bug.** Building
a same-code-path quiescent diagnostic (`--no-stream`, added to `run_morsel`) first
hit a real implementation bug (an un-strength-reduced runtime modulo dominating the
measurement) — fixed by masking instead of computing `%`. After the fix, the
no-stream variant was *still* slower than the real fused case (91.5 vs 84.4
cycles/access), which is the opposite of what a "code-path overhead inflates the
tax" story predicts. The most likely explanation: the real CXL load's latency
partially overlaps with the hot-table probe's own latency via out-of-order
execution, and removing that load removes the overlap opportunity, exposing more of
the probe's own latency serially. This is reported as a hypothesis, not confirmed
against outstanding-load counters — flagged as exactly that, not resolved into a
number it doesn't support.

**M5's engineering required two real fixes, both kept in the record rather than
smoothed over.** The first `DutyCycleStreamer` design restarted a fresh process per
burst; measuring true wall-clock (not the binary's own self-reported in-stream
"seconds," which excludes setup) showed mmap+mbind+prefault of a fresh region
dominates burst cost, capping the achievable duty-cycled rate at ~0.5–2 GB/s —
*below* the 16-core target. Switching to `SIGSTOP`/`SIGCONT` on one continuously-running,
already-prefaulted process fixed this. A second issue (Python's `threading.Thread` +
concurrent `subprocess.run` serializing on `fork()` from a large parent process,
~10× slower than shell `&` backgrounding) was diagnosed and made moot by the same
single-process redesign.

---

## 7. What could not be measured, and what a skeptical reviewer would attack

**Could not measure:**
- A true joint (address × latency) PEBS histogram — confirmed structurally
  unavailable on this kernel/hardware combination (Phase 0), not attempted as a fake
  substitute here.
- A validated cycles-per-access conversion for `Δ_M3` — the raw signals (`FB_FULL`,
  `PENDING_CYCLES`) are real but not convertible to an additive cycle-cost term
  without a causal model this experiment does not have. Reported as unattributed,
  set to 0 in the primary arithmetic (the more H2-generous choice, not the one that
  makes "in trouble" look worse).
- A background-noise-free CXL-destined CHA TOR reading — the quiescent arm's CXL
  branch is dominated by other users' traffic on this shared host; only the
  loaded-arm reading is treated as this workload's own signal.

**What a skeptical reviewer would attack:**
- *"You used two different L2-fit reference points (256K and 1M) and got 0% or 31% —
  which is it?"* Both are reported, deliberately, because the curve is genuinely
  non-monotonic and picking one silently would hide that. The honest statement is:
  the ratio is somewhere in [0%, 31%], and neither end reaches "sound" (≥60%).
- *"M5's bandwidth match wasn't exact at 16 cores."* Correct, and disclosed:
  achieved 5.22 vs target 5.376 GB/s, capped by node 1's own lower CXL ceiling (a
  real topology fact, checked via `numactl -H` node distances, not asserted). The
  residual is reported as an upper bound given the actual achieved bandwidth, not
  compared against an unmet target.
- *"M4's CHA events are system-wide on a shared host — how do you know the delta is
  yours?"* Randomized/back-to-back timing (as elsewhere in this project) is the
  mitigation, not a claim of a noise-free signal; the CXL-destined quiescent branch
  is explicitly called out as *not* usable for exactly this reason, rather than
  quietly included.
- *"Why does the histogram only explain 12% of the tax — is the PEBS instrument
  broken?"* No — it passed the L1/L2/LLC/>LLC validation cleanly (Section 6). The
  most defensible reading is that most of the tax is an execution-level effect
  (front-end/pipeline/dependency-chain interaction, or the same OoO-overlap
  phenomenon found while building the quiescent baseline), not a per-load memory
  latency effect at all — which is itself informative: it means the tax lives
  somewhere neither a pure cache-residency story nor H2 specifically was designed to
  reach.
- *"Isn't 'H2 story in trouble' just what CLOS-split already implied?"* CLOS-split
  showed context-scoped CAT doesn't help. This experiment asks a different, harder
  question — whether the *thing CAT was failing to fix* is even the thing H2 is
  built to fix — and answers it independently, via three different instruments that
  converge on the same answer rather than one number asserted from one method.

---

## Deliverables

- `results/mechanism_decomp/raw/` — all M2 (960 files), M3/M4 (300 files), and M5
  (120 files, block-structured) run records, nothing aggregated away. M1's final
  histogram runs are in `results/mechanism_decomp/m1_histograms/` alongside their
  raw per-sample weight arrays; Phase 1's known-size validation runs are in
  `results/mechanism_decomp/phase1/`.
- `results/mechanism_decomp/m2_summary.csv`, `m3_m4_summary.csv`, `m5_summary.json` —
  one row per (configuration, core count, size point) with medians, CoV, 95% CI.
- This report.
