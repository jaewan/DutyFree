# T4 rescoped: is the fused tax memory-side at all? (read-first outcome)

Registered **before any measurement**. T4 was specified as a `Δ_M3`
cycles-per-access conversion — fit an arrival × residence occupancy model, and
let it decide between a staging buffer and MSHR QoS. **Reading the existing
decomposition first says that is the wrong next step.**

## Why the original T4 is premature

`results/mechanism_decomp/MECHANISM_DECOMPOSITION_REPORT.md` §7, on what it
could not measure:

> "A validated cycles-per-access conversion for `Δ_M3` — the raw signals
> (`FB_FULL`, `PENDING_CYCLES`) are real but **not convertible to an additive
> cycle-cost term without a causal model this experiment does not have**."

And §3, on the per-load latency histogram:

> the histogram "accounts for roughly **12%** of the real tax. **Most of it is
> not explained**" by per-load memory latency.

§7's own most-defensible reading:

> "most of the tax is an **execution-level effect** (front-end/pipeline/
> dependency-chain interaction, or the same OoO-overlap phenomenon found while
> building the quiescent baseline), **not a per-load memory latency effect at
> all** — which is itself informative: it means the tax lives somewhere neither a
> pure cache-residency story nor H2 specifically was designed to reach."

An arrival × residence model presumes the contended resource is a **memory-side
occupancy**. If ~88% of the tax is not a per-load latency effect, that model
would be fitted to a term accounting for at most 31% — and possibly 0% — of the
thing being explained. Worse, **neither candidate mechanism it adjudicates
addresses an execution-level interaction**: a staging buffer relocates fills, and
MSHR reservation partitions miss slots; neither touches OoO overlap or a
dependency-chain interaction. The fork T4 was meant to settle may be a false
dichotomy.

Corroborating datum already in hand: the decomposition found that **removing the
stream made the probe slower** (91.5 vs 84.4 cyc/access), which it flagged as an
OoO-overlap hypothesis "not confirmed against outstanding-load counters". T3 run
2 then found the load-induced page walks are the victim's and invariant to the
stream's page size. Both point away from a simple memory-occupancy story.

## The prior question, and the instrument for it

**Split the fused tax into memory-bound, core-bound, front-end and bad-speculation
components.** Intel Top-Down does this directly and the events are present on
mos181 (verified: `topdown-retiring`, `topdown-bad-spec`, `topdown-fe-bound`,
`topdown-be-bound`, `topdown-mem-bound`).

## Arms and design

Two arms at the panel's 1-core operating point, identical to T3's:
`Q` = `--mode hot-probe` (no stream), `A` = `--mode morsel` (fused), with
`--fact-bytes 256m --hot-bytes 177838489 --morsel 1m --threads 1 --cpu-list 32`.
Note the hot table instantiates at **256 MiB (80% of LLC)**, not the requested
169.6 MiB.

n=12 per arm, **order balanced**: odd reps run `Q,A`, even reps run `A,Q`, so each
arm occupies each position exactly 6 times. Per-rep values, CoV, and archived
stderr, using the T3 v2 runner's fixed idioms (records validated as JSON before
being appended; no `grep -c` fallback; guards emit `NA` not `0`).

Metric: Top-Down slot fractions plus `active_cycles_per_access`. Multiplexing
percentage is recorded per event; **any arm whose events multiplex below 100% is
reported as such and not silently averaged.**

## Pre-registered readings

Let `Δ = A − Q` in cycles/access, and let each Top-Down category's contribution
be its slot-fraction change scaled by cycles.

| outcome | verdict |
|---|---|
| **memory-bound accounts for ≥60% of Δ** | the tax **is** memory-side. The original T4 occupancy fit becomes the right experiment, and the buffer-vs-MSHR-QoS fork is real. |
| **memory-bound accounts for ≤30% of Δ** | the tax is **not** memory-side. No memory-side mechanism — H2, staging buffer, or MSHR QoS — can address the fused case, and the paper's fused section must say so. The original T4 is **cancelled**, not deferred. |
| 30–60% | mixed; report the split and treat the fork as open on the memory-side share only. |

Registered independently of the above: **whichever category dominates Δ is
reported by name**, even if it is one this project has no mechanism for
(front-end, bad-speculation, core-bound). A dominant core-bound or
bad-speculation term would be the most informative possible outcome and must not
be buried as "unattributed".

**Falsifier for the instrument itself:** `topdown-retiring + bad-spec + fe-bound
+ be-bound` must sum to ≈1.0 slots in both arms. If it does not, the reading is
void rather than interpreted.

## Out of scope

The 16-core arms; any change to `cxl_join_bench.cpp`; the `Δ_M3` conversion
itself (this experiment decides whether to attempt it); and any mechanism design
study. No system state is changed and no hugepage pool is resized.
