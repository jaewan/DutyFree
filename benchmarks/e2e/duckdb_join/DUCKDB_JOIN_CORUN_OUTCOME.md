# Outcome: DuckDB join co-run, `mos181`, N = 2M

Dated 2026-08-21. Implements `DUCKDB_JOIN_CORUN_PREREGISTRATION.md` and its
three amendments. Seven arms x 10 repetitions, fixed seeded interleave, 12
measured queries per invocation, host exclusivity enforced per arm, streamer
settle gated on its own occupancy. All 70 arms valid. **Supersedes**
`DUCKDB_JOIN_FINDING_2026-08-21.md`, whose numbers are withdrawn.

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
write-back streamer is compared against a non-allocating one at the same
achieved bandwidth:

| level | write-back | non-allocating | paired difference | 95% CI |
|---|---|---|---:|---|
| ~18 GB/s | 1.112x (18.02, occ 67 MiB) | 1.049x (17.81, occ 126 MiB) | **+0.058** | [+0.047, +0.071] |
| ~10.8 GB/s | 1.113x (10.71, occ 66 MiB) | 1.018x (10.78, occ 93 MiB) | **+0.093** | [+0.089, +0.097] |

Both intervals exclude zero, and the occupancy column moves with the tax rather
than with the bandwidth. **Holding the byte rate fixed and changing only
whether the streamer allocates changes the victim's slowdown.** That is the
abstract's central de-confound, on a real application, with an interval.

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
1 and 2 cores against non-allocating arms on 2 and 8, and an 8-core write-back
streamer taxes 1.467x where a 2-core one at the same bandwidth taxes 1.112x. So
the +0.058 and +0.093 figures **understate** allocation's contribution.

## What the campaign can and cannot bracket

The largest tax observed, `WB_sat` at 1.467x, **cannot be decomposed**, because
`PREFETCHNTA` saturates this CXL link at ~18 GB/s and no non-allocating arm
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
