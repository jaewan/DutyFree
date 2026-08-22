# Outcome: DuckDB join co-run, `mos181`, N = 2M

Dated 2026-08-21. Implements `DUCKDB_JOIN_CORUN_PREREGISTRATION.md` and its
three amendments. Seven arms x 10 repetitions, fixed seeded interleave, 12
measured queries per invocation, host exclusivity enforced per arm, streamer
settle gated on its own occupancy. All 70 arms valid. **Supersedes**
`DUCKDB_JOIN_FINDING_2026-08-21.md`, whose numbers are withdrawn.

## Amendment, 2026-08-22: "non-allocating" is withdrawn as a label for these arms

A5.4 measured streamer-side L3 occupancy for the two `wb_prefetchnta` arms
below, under competition, on this host. They hold **43.6% and 68.2% of the
320 MiB LLC** while the victim runs, against `wb_load`'s 77.5% and 78.1%, and
against 5.5% for the only arm this project has ever shown to be non-allocating
(AMD flush-behind). Rep-paired ratios 0.637 [0.557, 0.754] and 0.875 [0.852,
0.893], against a 0.25 threshold fixed in advance: **both fail.**

Per A5.4's declared consequence, every de-confound and recovery figure in this
document is relabelled. `NTA_sat` and `NTA_lo` are **less-allocating** arms, not
non-allocating ones. The contrast is a **dose-response between two allocating
streamers**, and the causal result -- that at matched bandwidth the streamer's
allocation behaviour changes the victim's slowdown, with intervals excluding
zero -- is unaffected. The relabelling is applied in place below; the numbers
are unchanged, and A5.4 independently reproduced them (+0.069 and +0.102
against the +0.058 and +0.093 here). See
`DUCKDB_JOIN_INTEL_NTA_DISCRIMINATION.md`.

**One reading is now barred.** That NTA still allocates 44--68% does not license
"a truly non-allocating streamer would recover more, so these figures are
conservative." That requires tax to be monotone in streamer occupancy, which
A5.3 disproved on AMD and which A5.4 disproves again here: across the two levels
below, the pair giving up 33.9 points of streamer occupancy recovers *less*
excess tax (57.8%) than the pair giving up 9.9 points (85.6%). The core-count
conservatism argued further down is a separate argument and still stands.

## Result

Victim: DuckDB v1.1.3, chain8 many-to-many join, N = 2M build rows over 250K
distinct keys, probe 4M rows, `threads=1`, pinned cpu40, all tables on CXL node
2. Reused set R = 76 MiB; quiescent occupancy 142 MiB of a 320 MiB LLC.

| arm | streamer | GB/s | cores | victim occ | median s | **tax** | 95% CI | CoV |
|---|---|---:|---:|---:|---:|---:|---|---:|
| quiescent | none | -- | -- | 142 MiB | 0.6070 | 1.000 | -- | 1.33% |
| `WB_sat` | `wb_load` CXL | 24.95 | 8 | 70 MiB | 0.8920 | **1.467** | [1.451, 1.492] | 2.66% |
| `WB_local` | `wb_load` DRAM | 24.93 | 8 | 70 MiB | 0.8830 | 1.454 | [1.444, 1.465] | 2.39% |
| `WB_match_hi` | `wb_load` CXL | 18.02 | 2 | 67 MiB | 0.6750 | 1.112 | [1.097, 1.121] | 1.96% |
| `NTA_sat` | `prefetchnta` CXL | 17.81 | 8 | **126 MiB** | 0.6380 | 1.049 | [1.048, 1.055] | 1.90% |
| `WB_match_lo` | `wb_load` CXL | 10.71 | 1 | 66 MiB | 0.6750 | 1.113 | [1.104, 1.118] | 1.09% |
| `NTA_lo` | `prefetchnta` CXL | 10.78 | 2 | **93 MiB** | 0.6180 | 1.018 | [1.016, 1.021] | 1.50% |

Rep-paired percentile bootstrap, B = 20000, over 10 paired repetitions. The
quiescent arm reproduces the independent gate sweep to 0.3% (0.6070 vs 0.6050 s;
occupancy 142 vs 138 MiB).

## The de-confound: allocation is implicated, and the effect is small

The control this campaign existed to run. At each of two bandwidth levels, a
write-back streamer is compared against a *less-allocating* one at the same
achieved bandwidth (streamer-occupancy percentages from A5.4, measured on the
same arms at the same operating point):

| level | write-back | less-allocating | paired difference | 95% CI |
|---|---|---|---:|---|
| ~18 GB/s | 1.112x (18.02, occ 67 MiB, streamer 77.5%) | 1.049x (17.81, occ 126 MiB, streamer 43.6%) | **+0.058** | [+0.047, +0.071] |
| ~10.8 GB/s | 1.113x (10.71, occ 66 MiB, streamer 78.1%) | 1.018x (10.78, occ 93 MiB, streamer 68.2%) | **+0.093** | [+0.089, +0.097] |

Both intervals exclude zero, and the victim-occupancy column moves with the tax
rather than with the bandwidth. **Holding the byte rate fixed and changing how
much the streamer allocates changes the victim's slowdown.** That is the
abstract's central de-confound, on a real application, with an interval. It is
a dose-response, not a binary contrast: read the two streamer-occupancy columns
together and note that they do not order the effect -- 33.9 points buys +0.058
and 9.9 points buys +0.093.

**Neither pre-registered outcome fired, and this must be said plainly.**
Outcome 1 required `WB_match_hi >= 1.5x` with `NTA_sat <= 1.2x`; the measured
write-back tax at matched bandwidth is **1.112x**, not >= 1.5x. Outcome 2
required the two arms to be indistinguishable; they are clearly distinguishable.
The result is a third thing the pre-registration did not enumerate: **the
causal direction is confirmed and the magnitude is small.**

## Pollution scales with filling cores, not with bytes

An unplanned finding, and the most useful mechanism in the data. The write-back
tax is **flat** across a 68% change in bandwidth -- 1.113x at 10.71 GB/s and
1.112x at 18.02 GB/s -- and then jumps to 1.467x at 24.95 GB/s. What changes
across those three points is not principally bandwidth but **core count: 1, 2,
and 8**. Eight streams filling from eight cores displace far more of the victim
than two streams carrying nearly the same bytes.

This independently replicates a control already in the repository and never
cited: exp40's pointer-chase victim measured 2.042x at 24.82 GB/s and 2.025x at
11.52 GB/s -- a 1% change in tax for a halving of bandwidth.

It also means **this campaign's headline control is conservative by
construction, and now measurably so.** The matched-bandwidth write-back arms use
1 and 2 cores against less-allocating arms on 2 and 8, and an 8-core write-back
streamer taxes 1.467x where a 2-core one at the same bandwidth taxes 1.112x. So
the +0.058 and +0.093 figures **understate** allocation's contribution.
That argument is about core count and survives A5.4 untouched; the separate
argument from residual NTA allocation does not, and is barred above.

## What the campaign can and cannot bracket

The largest tax observed, `WB_sat` at 1.467x, **cannot be decomposed**, because
`PREFETCHNTA` saturates this CXL link at ~18 GB/s and no less-allocating arm
reaches 25 GB/s. There is no bandwidth-matched partner for it, and `-R` pacing
is barred. So allocation's contribution is bracketed rather than pinned:

- **at least +0.058 to +0.093** in tax units -- bandwidth-matched, core-count
  conservative;
- **at most +0.418** -- the core-count-matched comparison `WB_sat` (8 cores,
  24.95 GB/s) against `NTA_sat` (8 cores, 17.81 GB/s), which is unmatched in
  bandwidth by 40%.

Expressed as recovery, the distinction matters: the bandwidth-unmatched
comparison gives **89.5%** recovery, and the bandwidth-matched ones give
**56%** and **84%**. Any recovery figure quoted from this victim must say which
it is. The orphaned run's 84-91% was of the unmatched kind.

Post-A5.4, each of those is **recovery delivered by a partially-allocating
streamer**, not an estimate of what non-allocation would deliver, and must be
quoted that way. There is no non-allocating arm on this host to estimate it
with.

## The gap between capacity headroom and realised tax

The quiescent CAT gate at this operating point measured a **2.354x** ceiling,
forcing the victim from 138 MiB of occupancy to 15 MiB. The strongest real
streamer realises **1.467x**, leaving the victim **70 MiB**. A write-back
streamer at 25 GB/s across 8 cores cannot displace this victim below half of
what a one-way mask forces.

The mechanism is reuse density: DuckDB's pointer table is touched on the order
of a hundred times per line per query while the streamer's lines are touched
once, and this part's LLC insertion policy rewards that. **A high-reuse victim
partially defends itself**, so a CAT gate is an upper bound on the
capacity-mediated tax and not an estimate of it. That is a useful correction to
how the gate has been used in this project, including by me.

## Section 5's bandwidth assertion, discharged late and not cleanly

Section 5 requires that "aggressor achieved bandwidth [be] recorded per
repetition and asserted within 10% of section 3." The runner records it but
never asserted it, so the assertion went undischarged until now
(`check_bandwidth_assertion.py`). Checked per repetition rather than per
median — a median can sit inside the band while individual repetitions do not,
and it is the repetitions that enter the paired bootstrap:

| arm | section 3 | campaign min / median / max | worst deviation | verdict |
|---|---:|---|---:|---|
| `WB_sat` | 25.019 | 24.58 / 24.95 / 24.99 | -1.7% | pass |
| `WB_match_hi` | 18.484 | 17.02 / 18.02 / 19.02 | -7.9% | pass |
| `WB_match_lo` | 10.308 | 10.11 / 10.71 / 11.39 | **+10.5%** | **fail, 1 rep** |
| `NTA_sat` | 17.969 | 17.55 / 17.81 / 17.88 | -2.3% | pass |
| `NTA_lo` | 10.751 | 10.76 / 10.78 / 10.78 | +0.3% | pass |

`WB_local` is excluded by construction: it streams from local DRAM while every
section 3 arm streamed from node 2, so no declared value predicts it, and
asserting it against a node-2 reference would be the arm-identity error section
5.1 exists to prevent.

**One repetition of one arm is out of band**, `WB_match_lo` inv2 at 11.39 GB/s,
+10.5% against a 10% tolerance. Two things must be said about it rather than
one. First, it is not an isolated excursion: *every* `WB_match_lo` repetition
runs hot, min 10.11 and median 10.71 against a declared 10.308, and the control
run does the same (min 10.52, worst +9.6%, passing only just). The single-core
`wb_load` point is reproducibly ~4% faster in the campaign than in
characterisation. Section 3 measured 6 s runs; the campaign uses a 25 s settle
and a longer window, so the likeliest explanation is that the two measure
different steady states — but that is a hypothesis, not a measurement, and it
is not tested here.

Second, the failing repetition does not carry the result. Dropping inv2, the
10.8 GB/s de-confound moves from **+0.0930 [+0.0887, +0.0967]** to **+0.0905
[+0.0883, +0.0968]** — a shift of 0.0025 against an interval roughly 0.008
wide — and `WB_match_lo`'s tax *rises* slightly, 1.1133 to 1.1152, so the extra
bandwidth in that repetition did not buy extra tax. The finding stands with the
deviation disclosed; it is not repaired by widening the tolerance to fit, and
the tolerance has not been widened.

## Honest position

1. **The causal claim is supported on a real application, cross-checked two
   ways** (bandwidth-matched pairs, plus occupancy moving with tax rather than
   bandwidth), with intervals. This is the first time this project has
   established that on production-shaped software rather than a microbenchmark
   or a hand-rolled kernel.
2. **The magnitude claim is not supported on Intel.** 1.467x is the largest tax
   from a real streamer here, against a 2x bar. The withdrawn 3.847x came from
   an out-of-window build size with a 3 s streamer settle and no matched
   control.
3. **`WB_local` at 1.454x versus `WB_sat` at 1.467x** says placement of the
   *streamer* barely matters at fixed core count -- the tax is an allocation
   effect in the shared cache, not a CXL-link effect. Worth having: it removes
   an obvious reviewer objection that these results are about CXL queueing.

## Not yet done

AMD, where the panel expects the effect to be larger because Zen's L3 is a
victim cache with no reuse-aware insertion to defend the victim -- and where
`PREFETCHNTA` appears not to change insertion at all, so flush-behind is the
only viable non-allocating arm. `moscxl` must be frozen and captured first.
`mos182` node-2 arms remain gated behind the latency-ladder check.

*Done as of 2026-08-21; see `DUCKDB_JOIN_AMD_CORUN_OUTCOME.md`. The conjecture
in the paragraph above turned out to be right and is now the project's only
demonstrated non-allocating arm -- A5.3 and A5.4 disqualified `PREFETCHNTA` as
one on both vendors.*
