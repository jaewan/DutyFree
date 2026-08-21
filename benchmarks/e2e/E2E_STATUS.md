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
| magnitude | **DuckDB join clears the quiescent 2x gate on Intel at every valid size (2.200--2.354x) and on AMD at the one valid size (3.607x)**; the realised Intel co-run tax at the same operating point is 1.467x. GAPBS PageRank and HNSW do not clear it on Intel; PageRank clears it on AMD at g21 (2.580x) |
| reproducibility | DuckDB corun CoV 1.09--2.66% over 10 reps, quiescent arm reproducing the independent gate sweep to 0.3%; gate CoV 0.02--0.25% on GAPBS/HNSW Intel arms |
| recovery | **partially measured on Intel.** 56% and 84% at matched bandwidth, 89.5% unmatched -- every recovery figure must say which it is. **AMD is complete and yields no verdict**: A4.4 outcome 5 fired on CoV, and outcome 3 fired against the mechanism (see below) |
| frontier | preregistered; unmeasured |

A quantitative by-product worth carrying into the paper: on `mos181` a 320 MiB
LLC cuts HNSW's DRAM traffic **8.44x** (122.7 GB to 14.5 GB, occupancy verified
at 305 MiB) and returns only **1.54x** in runtime. The time-per-traffic ratio
falls monotonically with LLC size -- 1.05 at 16 MiB, 0.72 at 60 MiB, 0.18 at
320 MiB. A shared-cache tax requires a victim whose misses serialise; bandwidth
saved is not time saved. This is the gem5 task #22 MLP explanation reproduced
on silicon with traffic measured.

## The duplicate chain is a contributor, not the mechanism

The within-engine control declared in §1 and §6 outcome 3 has run: `joinuniq`,
`K = N`, identical `R(N)`, same seven arms, 70 arms all valid. `chain8` exceeds
`joinuniq` at every arm, so **outcome 3 did not fire** and the chain claim is
not withdrawn. But at saturation the chain contributes only **0.089 of a 0.467
tax, 19%** — the other 81% is hash-table reuse with no duplicate chain
involved. More usefully, the *de-confound* is chain-independent: +0.058 against
+0.068 at 18 GB/s and +0.093 against +0.079 at 10.8 GB/s, disagreeing in
opposite directions by about the interval width. The allocation result is not
an artifact of an unusual many-to-many join; it survives a plain one-to-one
hash join. See `duckdb_join/DUCKDB_JOIN_CHAIN_CONTROL_OUTCOME.md`, which also
records a counterexample forbidding any reading in which victim DRAM traffic or
occupancy *predicts* the tax.

## AMD: the gate clears, at exactly one build size

`moscxl`, victim cpu8 in L3 domain 1, 16 MiB/CCX, tables on CXL node 2:

| N | R = 40N | full-mask | min-mask | **gate ratio** | full occ | occ / LLC | valid? |
|---:|---:|---:|---:|---:|---:|---:|---|
| 100K | 3.8 MiB | 0.0280 s | 0.1010 s | **3.607** | 8.70 MiB | 54.4% | yes |
| 125K | 4.8 MiB | 0.0300 s | 0.1070 s | 3.567 | 9.66 MiB | 60.4% | **no** (occ > 60%) |

N = 100K satisfies all three §2 conditions (full/min occupancy 10.7x; 54.4% of
the LLC; traffic ratio 40.6 on `mbm_total`, 14.3 on `mbm_local`) and is the
**smallest** admitted size that clears, per the §2 selection rule. Amendment 1
excluded 64K and 80K: at 2.4x the 1 MiB private L2 they sit under the 4x-L2
floor, which is the trap that produced three earlier nulls in this project, and
that floor was not relaxed to gain a data point. So the AMD host admits one
build size only. (The *gate* clears there; the *co-run* at that size does not
yield a verdict -- next section.)

Two instrument notes. The AMD query is ~23x shorter than the Intel one, which
gave the 0.25 s occupancy sampler about two usable samples per arm and read
occupancy ~2 MiB high; `QUERIES` was raised to 301 and is now recorded per
record. And unlike `mos181` — where §3 records that `mbm_total` and
`mbm_local` are nearly identical despite CXL-resident tables, so MBM does not
separate expander traffic on that part — on `moscxl` they diverge about 10x
(0.115 against 1.188 GB at full mask), consistent with MBM there attributing
expander traffic to total but not local. Condition 3 passes on either counter
and its absolute value remains uninformative, the denominator being near zero.

## AMD co-run: no verdict, and one result that cuts against the mechanism

Complete, 90 arms, all valid. Full reduction in
`duckdb_join/DUCKDB_JOIN_AMD_CORUN_OUTCOME.md`. Two pre-registered outcomes
fired.

**Outcome 5 governs: no AMD verdict, and not a vendor null.** Three arms exceed
the 5% CoV bar across repetition medians -- `FB256_match` 13.10%, `FB0_match`
7.83%, `WB_fbmatch` 5.68% -- including both members of the primary de-confound
pair. The within-binary matched difference is +0.263 [+0.179, +0.420] and the
cross-binary +0.298 [+0.174, +0.369], and **neither may be reported as a
result**. Leave-one-out shows why: the point estimate barely moves (+0.250 to
+0.276) while the interval swings across [+0.107, +0.483]. Two declared causes
-- DuckDB's CLI `.timer` has 1 ms resolution against a 28 ms query (all 27000
measured queries are exact integer milliseconds; the quiescent arm puts 2326 of
3000 into two adjacent bins), and the victim is bistable at the 2--7 MiB
occupancy where the matched arms operate, deterministic only at 0 and 8 MiB.
Remedy declared before re-running: raise `probe_rows`, which lengthens the query
without touching `R(N) = 40N`, then re-verify condition 2 from its 54.4% start.

**Outcome 3 also fired, and it is a negative for the paper.** `NTA_sat` recovers
+2.897 [+2.845, +2.992] against `WB_sat` -- about 40% of the tax -- at the same
core count and 1.2% more bandwidth. A4.1 had declared NTA a negative control the
mechanism predicts will *not* recover, because a victimless sweep measured it
holding the whole 16 MiB CCX. The contrast is robust where the matched pair is
not: both arms are inside the CoV bar and all ten leave-one-out estimates are
+2.897 to three decimals. The one untested premise is that victimless occupancy
cannot distinguish MRU from LRU insertion -- both fill an idle cache. The
discriminating measurement, **streamer-side L3 occupancy during co-run**, has
not been made; the runner monitors the victim only. Until it is, the declared
reading stands.

What did pass: §5's per-repetition bandwidth assertion, cleanly, for the first
time on either host (every referenced arm within 2.1% of A4.5); the A4.5
cross-binary instrument check (+0.034, interval includes zero); and the
quiescent arm against the independent gate (0.0288 vs 0.0280 s, 8 vs 8.70 MiB).

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
`mos182` currently fails (node-2 times 2--4x node-0). **The cause is now
identified and it is ours, not the device's:** the two hosts hang CXL off
opposite sockets. `mos181`'s node 2 is distance 14 from node 0 and its victim
and aggressors are all in package 0, the near socket. `mos182`'s node 2 is
distance 24 from node 0 and 14 from node 1, while its configured victim
(cpu16) and aggressors (cpus 4--11) are also all in package 0 — there the
*far* socket, so every node-2 access crossed the inter-socket link first.
**This unblocks nothing.** A5 stands: the ladder must be re-run and must pass
from package 1 before any `mos182` node-2 arm is taken, and two prerequisites
are outstanding — `HOSTS["mos182"]` in `run_join_campaign.py` still names
package 0, and `latency_chase` there fails `GLIBC_2.38 not found` and must be
rebuilt on the host. Detail in the preregistration's A4.7.

## Still open before any further co-run arm

1. **Use an even measured trial count.** `pr -n 4` less a warm-up leaves three
   trials, an odd sample of a two-phase signal that alternates ~9% on
   `moscxl`. `-n 5` or `-n 7`. This is a change to a pre-registered command and
   is left for the lead.
2. **Verify the MBM counter is live before invalidating an arm for zero
   streamer traffic.** On AMD under resctrl group churn the counter returns
   stale values -- PageRank's traffic samples in the GAPBS gate are unusable
   for exactly this reason, while HNSW's are sound. *Partly closed:* the
   DuckDB runner no longer trusts field position. Every `mbm_local_first` in
   the moscxl gate was the string `Unavailable` (the RMID is not programmed at
   group-creation time) while every `_last` was numeric, which a naive
   `int()` turned into a crash and a naive first/last difference would have
   turned into a wrong ratio. `mbm_span()` now takes the first and last
   *numeric* samples and records how many were not, per record. The general
   liveness check for GAPBS/HNSW is still owed.
3. **Delete the unreproducible RocksDB 2.33x sentence** and add a provenance
   appendix. The panel referee's judgement is that this, and not the nulls, is
   the decisive reject reason.

## Documents

- `duckdb_join/DUCKDB_JOIN_CORUN_PREREGISTRATION.md` -- the campaign and its
  four amendments; Amendment 4 rewrites the AMD arms around a measured fact
  about `PREFETCHNTA` on Zen4c
- `duckdb_join/DUCKDB_JOIN_CORUN_OUTCOME.md` -- the Intel result
- `duckdb_join/DUCKDB_JOIN_CHAIN_CONTROL_OUTCOME.md` -- the `joinuniq`
  within-engine control, and what the counters may and may not be cited for
- `gapbs/GAPBS_CAT_SENSITIVITY_OUTCOME.md` -- result, both falsified
  predictions, the three eliminated variance causes, and the consequences
- `gapbs/GAPBS_CAT_SENSITIVITY_RUN_DECISIONS.md` -- every departure, written
  before results were read
- `hnsw/HNSW_CAT_SENSITIVITY_OUTCOME.md` -- why HNSW fails, and why halving a
  victim's DRAM traffic bought only a third more runtime
- `gapbs/GAPBS_SIZING_OUTCOME.md` -- the earlier, superseded `-g 22` selection
- `../../experiments/asplos/AMD_PLATFORM_STATE_PROVENANCE_2026-08-21.md` -- the
  provenance gap the freeze closes
