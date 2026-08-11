# Pre-registration: GAPBS cross-vendor sizing gate

Dated 2026-08-11. Written before the first GAP Benchmark Suite measurement
in this campaign.

## Objective

Select a graph-analytics victim geometry that is demonstrably beyond the
private L2 on both hosts before measuring a co-run tax. This is a sizing gate,
not an attempt to select a favorable loaded result: all points below are run
quiescent only and the later co-run configuration is fixed from these records.

## Workload and hosts

- Suite: GAP Benchmark Suite (GAPBS), upstream `main`, source commit recorded
  in each run record.
- Applications: breadth-first search (`bfs`), PageRank (`pr`), and connected
  components (`cc`).
- Graph family: GAPBS Kronecker generator, scales 20, 22, 24, and 25; the
  default synthetic degree and seed are retained and recorded verbatim.
- `mos181` (Intel Xeon 8592+): one victim CPU on NUMA node 0, graph allocation
  local to node 0.
- `broker` / `moscxl` (AMD EPYC 9754): one victim CPU in a single CCX on NUMA
  node 0, graph allocation local to node 0.

## Measurement protocol

Each application/scale point is run three times after one untimed warm-up.
The runner captures wall time, the GAPBS-reported timing line, CPU placement,
NUMA allocation evidence (`numastat -p` when available), and the exact command.
No aggressor is started in this gate. A point is invalid if its process moves
off the requested CPU or its allocation cannot be observed on the intended
local node.

## Falsifiable predictions and decision rule

1. Scales 24--25 will exceed each host's private L2 (2 MiB on Intel; 1 MiB on
   AMD) and have materially higher standalone time than scale 20.
2. BFS and CC will show a more latency-sensitive shape than scan-heavy
   PageRank; this is an expectation, not a selection criterion.
3. A graph that is private-L2 resident, has unstable timing, or completes too
   quickly to sustain a concurrent stream is rejected for the co-run campaign.

The co-run victim will be the smallest scale satisfying all of: at least 10x
the host private-L2 size by graph-file footprint, median standalone runtime of
at least 2 seconds under a repeated-work wrapper, and CoV at most 5% across
the three sizing repetitions on both hosts. If no common scale qualifies, the
campaign records that failure and does not quote a co-run tax.

## Later campaign boundary

The subsequent co-run campaign, if the gate passes, will receive its own
pre-registration before any loaded arm. Its baseline and every loaded arm will
be interleaved, victim-first, and reported only against a matched quiescent
baseline from that same run.
