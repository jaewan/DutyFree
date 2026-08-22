# E2E status

Updated 2026-08-22, third revision. The first revision of this file, written
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

- At ~18 GB/s, write-back taxes the victim **1.112x** and a less-allocating
  streamer at the same byte rate taxes it **1.049x**: paired difference
  **+0.058** [+0.047, +0.071].
- At ~10.8 GB/s, **1.113x** against **1.018x**: paired difference **+0.093**
  [+0.089, +0.097].

Both intervals exclude zero and victim occupancy tracks the tax rather than the
bandwidth (67 vs 126 MiB; 66 vs 93 MiB). Holding bytes fixed and changing how
much the streamer allocates changes the victim's slowdown. **A5.4 relabelled
this from a binary contrast to a dose-response and reproduced both differences;
see below.**

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
| recovery | **partially measured on Intel, and relabelled by A5.4.** 56% and 84% at matched bandwidth, 89.5% unmatched -- every recovery figure must say which it is, *and* that it is recovery by a partially-allocating streamer (A5.4: the Intel "non-allocating" arms hold 44--68% of the LLC under competition). **AMD is complete and yields no verdict**: A4.4 outcome 5 fired on CoV, and outcome 3 fired against the mechanism (see below) |
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
+0.276) while the interval swings across [+0.107, +0.483].

The cause is **between-invocation**, not within: in every arm the observed
CoV_rep is 4.5--12x what the standard error of a median of 300 queries predicts.
DuckDB's 1 ms CLI timer is a real floor -- all 27000 measured queries are exact
integer milliseconds, and the quiescent arm's 1.74% is indistinguishable from
its 1.75% half-quantum floor -- but at 1.2--1.4% it explains about a ninth of
the 5.7--13.1% in the matched arms. What tracks runtime is residency: within an
arm, the invocation's mean victim occupancy predicts its median runtime at
r = -0.82 (`NTA_sat`, `FB256_match`) and -0.61 (`FB0_match`). `FB256_match` inv5
holds 6.0 MiB for its whole duration against 7.0--7.4 elsewhere and runs 47 ms
against 31--35 -- a 15% shortfall in cache costing 38% in time, the signature of
an operating point on a cliff. A first-draft remedy (lengthen the query via
`probe_rows`) is **withdrawn**: A2 forbids it, P being sized to 12% of LLC
precisely to stop probe-scan pollution, and it targets the within-invocation
term that is already 9x too small to matter.

**Outcome 3 also fired, and it is a negative for the paper.** `NTA_sat` recovers
+2.897 [+2.845, +2.992] against `WB_sat` -- about 40% of the tax -- at the same
core count and 1.2% more bandwidth. A4.1 had declared NTA a negative control the
mechanism predicts will *not* recover, because a victimless sweep measured it
holding the whole 16 MiB CCX. The contrast is robust where the matched pair is
not: both arms are inside the CoV bar and all ten leave-one-out estimates are
+2.897 to three decimals. The one untested premise was that victimless occupancy
cannot distinguish MRU from LRU insertion -- both fill an idle cache.

**A5.3 tested it, and the premise holds: the reading is final.** Streamer-side
L3 occupancy during co-run, 10 repetitions, `duckdb_join/DUCKDB_JOIN_AMD_NTA_DISCRIMINATION.md`.
NTA holds **86.7% of the CCX**, a rep-paired **0.884 [0.880, 0.889]** of
`wb_load`'s, against a 0.50 threshold fixed in advance. It allocates and
recovered anyway, so **the mechanism as stated is wrong**, in the words A5.3
declared. The same artifact shows why a victimless sweep could never have seen
it: with no victim the two streamers are identical (15.80 MiB each), and
under competition `wb_load` yields 0.13 MiB while NTA yields 1.98. The operative
variable is insertion priority in a cache both streamers fill, not allocation
versus bypass, and the reverse-causation reading fails on the sign -- the
`WB_sat` victim drives 2.5x more DRAM traffic and retains 6.8x less cache.

Two consequences beyond the wording. The five-link chain's L2/L3 route harm
through a binary allocation predicate that does not predict it here. And L5 is
threatened on AMD: `PREFETCHNTA` is a deployed, unprivileged, single-instruction
hint that recovered 40% of the excess tax with no OS involvement. It does not
occupy the paper's corner -- per-instruction, unenforced, not object-scoped,
vendor-divergent -- but it erodes the magnitude argument for occupying it.
**Restating L5 is a §9 lead-only decision and has not been taken.**

What did pass: §5's per-repetition bandwidth assertion, cleanly, for the first
time on either host (every referenced arm within 2.1% of A4.5); the A4.5
cross-binary instrument check (+0.034, interval includes zero); and the
quiescent arm against the independent gate (0.0288 vs 0.0280 s, 8 vs 8.70 MiB).

## A5.4: the same blind spot on Intel, measured, and it fails there too

`mos181`, five arms x 10 repetitions, all valid,
`duckdb_join/DUCKDB_JOIN_INTEL_NTA_DISCRIMINATION.md`. `wb_prefetchnta` holds
**43.6%** of the 320 MiB LLC at ~18 GB/s and **68.2%** at ~10.8, against
`wb_load`'s 77.5% and 78.1%: rep-paired **0.637 [0.557, 0.754]** and **0.875
[0.852, 0.893]** against a 0.25 threshold fixed in advance. **Both fail.** The
Intel arms differ from the AMD ones in degree, not in kind.

So the headline de-confound is a **dose-response between two allocating
streamers**, not allocation against none. The causal result is untouched and
was independently reproduced by this run (+0.069 [+0.038, +0.079] and +0.102
[+0.094, +0.103] against the campaign's +0.058 and +0.093, quiescent 0.6050
against 0.6070 s). What changes is every label: `DUCKDB_JOIN_CORUN_OUTCOME.md`
is relabelled in place, and its 89.5/56/84% are recovery *delivered by a
partially-allocating streamer*, not estimates of what non-allocation would give.

**No host in this project now retains a demonstrated non-allocating arm except
AMD flush-behind**, whose co-run arms fail the CoV bar and yield no verdict. So
there is today no valid allocation-versus-none de-confound anywhere in the
campaign. Flush-behind's own status survives on an argument worth stating: its
5.5% is victimless, and victimless occupancy can only *over*-estimate what a
streamer holds under competition, so 5.5% is an upper bound.

**And occupancy does not predict harm, now on two vendors.** Excess tax
recovered per point of streamer occupancy given up:

| pair | occ drop | excess tax recovered | per point |
|---|---:|---:|---:|
| AMD, 24.3 GB/s | 11.3 pts | 40.3% | 3.6 %/pt |
| Intel, ~18 GB/s | 33.9 pts | 57.8% | 1.7 %/pt |
| Intel, ~10.8 GB/s | 9.9 pts | 85.6% | 8.6 %/pt |

Within one host, one victim, one artifact, the pair giving up **3.4x more**
streamer occupancy recovers **less** tax. That cannot be a vendor effect, and it
independently corroborates A5.3 without using the streamer-yield argument. It
also bars the tempting patch on the relabelling -- that a truly non-allocating
streamer would recover more, so the Intel figures are conservative. That needs
tax monotone in streamer occupancy, which is what these three rows refute. (The
*core-count* conservatism argued in the Intel outcome is a different argument
and still stands.)

Three instrument defects surfaced and are recorded rather than repaired in
place: `wait_for_streamer`'s three-samples-within-5% gate is satisfied by a slow
monotone ramp, and `WB_match_hi` is consequently bimodal in occupancy *and*
bandwidth across repetitions (verdict robust: 0.56 and 0.82 in the two states);
`WB_match_lo` fails §5's bandwidth assertion at +15.1%, with the bias direction
conservative for the threshold it failed anyway; and my own post-hoc idle
estimator was invalid on Intel and is fixed, leaving only `NTA_lo` with a
quotable idle reading there. AMD's numbers are unchanged by the fix.

A5.4 was pre-registered as unable to produce a positive result -- "a pass leaves
the Intel de-confound where it already was; a failure removes it" -- and it
failed. Whether the L5 restatement now owed on AMD extends to Intel, and what
either does to the paper's page-1 posture, are **§9 lead-only decisions and are
not taken here.**

## A5.2: hugepages do not control the spread, and the comparator did not reproduce

`moscxl`, two blocks of 10 x 2 arms, 40 records, all valid,
`duckdb_join/DUCKDB_JOIN_A52_OUTCOME.md`. Run under a shim
(`tools/thp_arena.c`) that marks the victim's arena `MADV_HUGEPAGE` and
pre-faults it, scoped to the victim process so the **frozen host state is not
touched**; every repetition obtained 24--28 MiB of `AnonHugePages` against 0
host-wide, which is the check that stops a silently no-op shim from producing a
null indistinguishable from a real one.

**The pass branch is ruled out on absolute thresholds**: spread **5.69%** and
CoV_rep **5.29%**, needing < 3% and < 5%. Against a contemporaneous control the
spread is unchanged (5.90%) and CoV_rep slightly worse (4.28%). So page
placement is not a controllable driver and **no hugepage re-run is licensed** --
that was the only thing a pass would have bought. The occupancy spread is in
fact the stable quantity: 5.95% historically, 5.90% today, 5.69% with
hugepages, three readings within 0.26 points across a day and across the
manipulation.

**The other branch is void, and that is the finding.** The declared validity
condition fired: the contemporaneous no-shim control -- same host, same frozen
state, same arm, no manipulation -- ran at **CoV_rep 4.28%** against the
campaign's **13.10%**. Not a state change (the campaign ran 22:11 on 08-21,
*after* the 21:23 freeze, and absolute medians agree to 3%). The 13.10% is
**one invocation**: dropping `FB256_match` inv5 gives 4.50%, and `WB_fbmatch`
falls to 3.56% on one removal too, though `FB0_match` stays at 6.98% and is
genuinely dispersed -- so **outcome 5 does not collapse and is not retracted.**

The decisive observation is in this run's own **quiescent** arm: CoV_rep
**13.40%**, best leave-one-out **1.59%**, one invocation at 0.0400 s against
0.0280 -- **with no streamer running at all.** A 1.4x excursion that happens on
an idle host with no aggressor cannot be the signature of a co-run operating
point on a cliff, which is how the AMD outcome document read it. The
occupancy-runtime correlation it rested on is real and reproduces (-0.856,
-0.605, -0.830); the attribution does not.

**A plain re-run of the AMD campaign is deliberately not taken.** If today's
control sits at 4.28%, a repetition might clear the bar and hand back the
+0.263 that outcome 5 voided -- which is exactly why A5.2 says "no conclusion,
and no re-run," and exactly the move §6.6 names: the target number is already
known, so a re-run chosen because a pilot suggested the bar would clear is
selected on its outcome. Legitimising it needs a pre-registration with the
repetition count and the outlier rule fixed in advance. **That decides whether
the AMD de-confound exists and is put to the lead.**

Unexcluded: time of day. The campaign ran late at night, this run in the
afternoon, on a host with other logged-in users. Nothing here tests it.

## A6: the re-run is pre-registered, and launched

The lead directed the re-run, so it is taken on that instruction rather than
because a diagnostic cleared it -- A5.2 clears nothing. **Amendment 6 of
`DUCKDB_JOIN_CORUN_PREREGISTRATION.md` fixes every rule before the first record
exists**, with `summarize_stability.py` committed alongside it.

The measured basis, from the 150 AMD invocations that already exist: the
anomaly runs at **1.3% incidence, 2 in 150** -- not the rate a 13.10% CoV
suggests -- one of the two events is a *quiescent* arm with no streamer, both
have a normal warm-up query and then a shifted and widened measured stream, and
**no field in the record distinguishes an anomalous invocation** except runtime
and occupancy. Occupancy is the mediator, so there is nothing to exclude on that
is not the outcome variable. Hence the fixed rule: **no repetition is excluded
for any reason relating to its runtime, its occupancy, or its effect on any
estimate.** n rises 10 -> 30, all nine arms, nothing else changes, 4.9 h.

**Launched 2026-08-22 14:50; started 20:45 on the lead's instruction, ahead of the declared 22:00 (A6.8)** (`run_a6_block.sh`,
detached on `moscxl`, ~4.9 h, artifacts `join_corun30_moscxl.jsonl` /
`corun30_moscxl.log`). The freeze was verified against `d8eda44` before launch
and is re-verified into the log before the first arm: performance governor on
all 512 CPUs, boost 0, `numa_balancing` 0, `perf_event_paranoid` -1, THP
madvise, cpu8 at 2.25 GHz, no reboot since 2026-08-19. `MODE=corun30` gives the
re-run its own artifact rather than appending to the campaign's; the interleave
RNG is unchanged at seed 20260821, so repetitions 0-9 reproduce the campaign's
exact arm ordering and 10-29 continue the stream. The runner has moved since the
campaign only by the A5.2 THP patch, which is inert with `VICTIM_PRELOAD` unset
(a `None` field and `env=dict(os.environ)`); a two-arm smoke test on the same
path reproduced the campaign to 0.0330 s at 15.39 GB/s against 0.0340 at 15.42.

Raising n is not a dispersion remedy and A6 forbids reporting it as one. The
original 5% CoV bar is retained unweakened; two stability checks are *added* and
can only license a weaker statement than it would. **`FB0_match` is forecast in
the document to fail the CoV bar again** -- its dispersion is broad, not
outlier-driven, 6.98% on its best leave-one-out -- so the realistic best outcome
is a bounded non-verdict, in wording already fixed. There is no third campaign.

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
- `duckdb_join/DUCKDB_JOIN_CORUN_OUTCOME.md` -- the Intel result, relabelled
  in place by A5.4
- `duckdb_join/DUCKDB_JOIN_AMD_NTA_DISCRIMINATION.md` -- A5.3: `PREFETCHNTA`
  allocates under competition on Zen4c and recovered anyway
- `duckdb_join/DUCKDB_JOIN_INTEL_NTA_DISCRIMINATION.md` -- A5.4: it allocates
  on Intel too, and occupancy does not order the harm within a single host
- `duckdb_join/DUCKDB_JOIN_A52_OUTCOME.md` and `..._A52_RUN_DECISIONS.md` --
  A5.2: hugepages do not control the spread, and the 13.10% that voided the AMD
  campaign did not reproduce
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
