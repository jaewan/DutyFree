# Pre-registration: GAPBS PageRank x DuckDB scan co-run

Dated 2026-08-11. Written before any co-run arm in this campaign.

## Objective

Test whether an immutable, scan-heavy **real application** streamer (DuckDB)
causes a substantial tax to a real graph-analytics tenant with dependent and
reused accesses, and measure the streamer's own end-to-end cost for deployed
alternatives.

## Fixed victim configuration

The sizing gate fixes the victim to GAPBS PageRank: `pr -g 22 -n 4 -r 1 -l`,
one OpenMP thread, pinned to CPU 32/node 0 on `mos181` and CPU 8/node 0 on
`moscxl`. The first GAPBS trial is warm-up; the reported victim metric is the
median of the remaining three `Trial Time` values. This configuration was
chosen solely by the standalone gate: both hosts have a measured trial time
over two seconds and a graph footprint far above private L2.

## Fixed streamer configuration

DuckDB will scan a generated, CXL-node-2-resident Parquet table using a single
scan-and-aggregate query. Eight pinned streamer threads will be used on each
host (Intel CPUs 40-47; AMD CPUs 9-16), with no `-R` pacing. The runner will
record DuckDB's query wall time and achieved memory-controller traffic; a run
is invalid if the streamer has zero traffic, exits before the victim's final
measured trial, or cannot demonstrate node-2 placement.

The initial silicon rows are WB/default DuckDB scan and the available
flush-behind process control. A true non-allocating DuckDB load arm is only
reported if instruction inspection verifies it; otherwise it is explicitly
marked unmeasured, never substituted with a synthetic bandwidth result.

## Protocol and arms

All arms use victim-first arrival order. GAPBS builds its graph and completes
its first trial, emits a ready marker, then the runner starts the streamer
after 0.1 seconds. For each loaded repetition, the matching quiescent
repetition uses the same victim command and is interleaved in a fixed seeded
random order. The arms are:

| arm | streamer | prediction |
|---|---|---|
| quiescent | none | baseline PageRank time |
| WB | default DuckDB scan | PageRank slows by at least 2x if LLC allocation is the limiting tax |
| flush-behind | DuckDB scan plus available flush process control | PageRank moves substantially toward its matched baseline, while DuckDB pays a query-time cost |
| NT | verified non-allocating DuckDB scan only | low tenant tax but streamer query time worse than WB; otherwise unmeasured |

Each host gets n=10 valid repetitions per arm. The runner asserts no orphan
streamer process, full streamer-window coverage of the victim's measured
trials, and nonzero/in-range streamer traffic for every loaded repetition.

## Falsifiable outcomes

1. If WB tax is below 2x on either host, GAPBS PageRank fails the magnitude or
   cross-vendor bar and will be reported as such.
2. If WB tax is at least 2x but the loaded distributions are bimodal or CoV is
   over 5%, the result is not a publishable operating point until a declared
   cause is resolved and the campaign is re-run.
3. If flush-behind does not recover a substantial share of the matched WB tax,
   the recovery bar fails; no H2/H3 attribution will be made.
4. If no deployed DuckDB alternative has a measured own-query cost, the
   frontier bar remains open even if tenant tax and recovery succeed.

Every tax is `loaded / matched quiescent` within its own host/run; no tax is
computed from a baseline belonging to another arm or host.
