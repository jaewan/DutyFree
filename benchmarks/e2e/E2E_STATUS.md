# E2E status

Updated 2026-08-21, second revision. The first revision of this file, written
after the GAPBS and HNSW capacity gates and before the DuckDB campaign,
contained a claim this revision **retracts**; see the box below.

## Retraction: "no Intel configuration reaches 2x"

The previous revision said, of two victims across three hosts and five scales,
that **no Intel configuration reaches 2x**. That sentence is withdrawn. It was
wrong in two independent ways.

**It is falsified by measurement.** The DuckDB v1.1.3 many-to-many join clears
the same style of quiescent capacity gate on `mos181`, an Intel host, at every
build size that satisfies the validity conditions:

| N | R = 40N | full-mask median | min-mask median | **gate ratio** | full occ | occ / LLC | valid? |
|---:|---:|---:|---:|---:|---:|---:|---|
| 500K | 19 MiB | 0.4710 s | 1.0360 s | **2.200** | 59 MiB | 18.6% | yes |
| 1M | 38 MiB | 0.5210 s | 1.2175 s | **2.337** | 96 MiB | 29.8% | yes |
| 2M | 76 MiB | 0.6050 s | 1.4240 s | **2.354** | 138 MiB | 43.1% | yes |
| 3M | 114 MiB | 0.6920 s | 1.5900 s | 2.298 | 206 MiB | 64.3% | **no** (occ > 60%) |
| 4M | 152 MiB | 0.8230 s | 1.4555 s | 1.769 | 194 MiB | 60.5% | **no** (occ > 60%) |

Three of five admitted sizes are valid and **all three pass**; a fourth passes
but is outside the occupancy ceiling. So the earlier sentence was not merely
unsupported, it was false: what the GAPBS and HNSW gates had established was
that *those two victims* do not reach 2x on Intel, which is a statement about
the victims, not about the vendor.

**It also over-read the gates it did rest on.** The DuckDB pre-registration's
§2 states a validity condition the GAPBS and HNSW gates were never checked
against: *a gate whose minimum expressible mask exceeds the victim's reused set
measures granularity, not capacity, and yields no verdict rather than a null.*
Applied backwards, two of the three rungs the sentence rested on fail it, in
opposite directions:

- **`mos181` PageRank.** Its minimum mask is 16 MiB, and its 2 MiB private L2
  sits behind that mask, so the min arm still leaves the victim 18 MiB against
  a hot set the GAPBS outcome puts at roughly 17 MB. The gate never denied
  PageRank its reused set on this host. Its 1.311x is a granularity floor, not
  a capacity null.
- **`moscxl` HNSW.** Going from a 16 MiB mask to a 1 MiB mask moved the
  victim's local DRAM traffic from 166.7 GB to 200.4 GB, a ratio of **1.20**
  against the 1.5 the same validity condition requires. The manipulation
  barely changed the victim's memory behaviour, so its 1.257x is not evidence
  about capacity either.

Neither yields a null. Both were counted as one. Note that both numbers were
already printed in the outcome documents; what was missing was the condition
that makes them disqualifying.

The GAPBS and HNSW outcome documents state their own results correctly. What
was wrong was the generalisation across them in this file.

## Where the campaign actually stands

**The real-application victim is the DuckDB join, and the paper's central
de-confound now holds on it with an interval.** `mos181`, N = 2M, seven arms x
10 repetitions, host exclusivity enforced per arm, streamer settle gated on the
streamer's own occupancy, all 70 arms valid:

- At ~18 GB/s, write-back taxes the victim **1.112x** and a non-allocating
  streamer at the same byte rate taxes it **1.049x**: paired difference
  **+0.058** [+0.047, +0.071].
- At ~10.8 GB/s, **1.113x** against **1.018x**: paired difference **+0.093**
  [+0.089, +0.097].

Both intervals exclude zero and victim occupancy tracks the tax rather than the
bandwidth (67 vs 126 MiB; 66 vs 93 MiB). Holding bytes fixed and changing only
whether the streamer allocates changes the victim's slowdown.

**Neither pre-registered outcome fired.** Outcome 1 wanted >= 1.5x at matched
bandwidth and got 1.112x; outcome 2 wanted the arms indistinguishable and they
are not. The truth was a third thing: direction confirmed, magnitude small.
Details, including the finding that pollution scales with *filling core count*
rather than with bytes, are in `duckdb_join/DUCKDB_JOIN_CORUN_OUTCOME.md`.

**A CAT gate is an upper bound, not an estimate.** The quiescent ceiling at
N = 2M is 2.354x, with the victim forced to 15 MiB. The strongest real streamer
realises 1.467x and leaves the victim 70 MiB. A high-reuse victim partially
defends itself against a streamer in a way it cannot against a mask.

| bar | status |
|---|---|
| magnitude | **DuckDB join clears the quiescent 2x gate on Intel at every valid size (2.200--2.354x); the realised co-run tax at the same operating point is 1.467x**. GAPBS PageRank and HNSW do not clear it on Intel; PageRank clears it on AMD at g21 (2.580x) |
| reproducibility | DuckDB corun CoV 1.09--2.66% over 10 reps, quiescent arm reproducing the independent gate sweep to 0.3%; gate CoV 0.02--0.25% on GAPBS/HNSW Intel arms |
| recovery | **partially measured on Intel.** 56% and 84% at matched bandwidth, 89.5% unmatched -- every recovery figure must say which it is. Non-allocating arm on AMD is flush-behind, not `PREFETCHNTA` (see below); campaign in flight |
| frontier | preregistered; unmeasured |

A quantitative by-product worth carrying into the paper: on `mos181` a 320 MiB
LLC cuts HNSW's DRAM traffic **8.44x** (122.7 GB to 14.5 GB, occupancy verified
at 305 MiB) and returns only **1.54x** in runtime. The time-per-traffic ratio
falls monotonically with LLC size -- 1.05 at 16 MiB, 0.72 at 60 MiB, 0.18 at
320 MiB. A shared-cache tax requires a victim whose misses serialise; bandwidth
saved is not time saved. This is the gem5 task #22 MLP explanation reproduced
on silicon with traffic measured.

## Host state

`moscxl` is **frozen** as of commit `d8eda44`: all 512 CPUs on the
`performance` governor, `cpufreq/boost=0`, `numa_balancing=0`, THP `madvise`,
captured to `../setup/state/bergamo_system_state.txt`. The as-found capture is
kept beside it because the host was clocking 3.0999 GHz unfrozen and holds
2.2486 GHz frozen. Every AMD number taken between the 2026-08-19 reboot and
that commit -- including today's GAPBS and HNSW gates, which disclosed it --
was taken at boost clocks. Those gates are ratios between back-to-back arms, so
the clock largely cancels.

`mos182` node-2 arms remain gated behind a `cxl_join_bench --mode latency`
ladder that `mos181` passes (54.41 ns node 0 against 54.32 ns node 2) and
`mos182` currently fails (node-2 times 2--4x node-0).

## Still open before any further co-run arm

1. **Use an even measured trial count.** `pr -n 4` less a warm-up leaves three
   trials, an odd sample of a two-phase signal that alternates ~9% on
   `moscxl`. `-n 5` or `-n 7`. This is a change to a pre-registered command and
   is left for the lead.
2. **Verify the MBM counter is live before invalidating an arm for zero
   streamer traffic.** On AMD under resctrl group churn the counter returns
   stale values -- PageRank's traffic samples in the GAPBS gate are unusable
   for exactly this reason, while HNSW's are sound.
3. **Delete the unreproducible RocksDB 2.33x sentence** and add a provenance
   appendix. The panel referee's judgement is that this, and not the nulls, is
   the decisive reject reason.

## Documents

- `duckdb_join/DUCKDB_JOIN_CORUN_PREREGISTRATION.md` -- the campaign and its
  four amendments; Amendment 4 rewrites the AMD arms around a measured fact
  about `PREFETCHNTA` on Zen4c
- `duckdb_join/DUCKDB_JOIN_CORUN_OUTCOME.md` -- the Intel result
- `gapbs/GAPBS_CAT_SENSITIVITY_OUTCOME.md` -- result, both falsified
  predictions, the three eliminated variance causes, and the consequences
- `gapbs/GAPBS_CAT_SENSITIVITY_RUN_DECISIONS.md` -- every departure, written
  before results were read
- `hnsw/HNSW_CAT_SENSITIVITY_OUTCOME.md` -- why HNSW fails, and why halving a
  victim's DRAM traffic bought only a third more runtime
- `gapbs/GAPBS_SIZING_OUTCOME.md` -- the earlier, superseded `-g 22` selection
- `../../experiments/asplos/AMD_PLATFORM_STATE_PROVENANCE_2026-08-21.md` -- the
  provenance gap the freeze closes
