# Outcome: DuckDB join co-run, `moscxl` (EPYC 9754), N = 100K

Dated 2026-08-21. Implements `DUCKDB_JOIN_CORUN_PREREGISTRATION.md` as amended
by A4.1--A4.7. Nine arms x 10 repetitions, 90 arms, **all valid, no aborts**,
host exclusivity enforced per arm, streamer settle gated on the streamer's own
occupancy, fixed seeded interleave, 300 measured queries per invocation.

## Verdict: A4.4 outcome 5 fires. This host yields no verdict.

**A4.4 outcome 5** — *"No build size satisfies §2 on this host, or CoV > 5%, or
bimodal loaded distributions. No AMD verdict; not a vendor null."*

The CoV trigger fires unambiguously, on three arms, including **both members of
the primary de-confound pair**:

| arm | CoV across rep medians | CoV pooled over 3000 queries |
|---|---:|---:|
| `FB256_match` | **13.10%** | 19.50% |
| `FB0_match` | **7.83%** | 11.92% |
| `WB_fbmatch` | **5.68%** | 7.96% |

So **no number below is a verdict**, the +0.263 de-confound included, and per
A4.4 and §6 outcome 4 this host may not be cited as a vendor null either. What
follows is recorded so the operating point can be repaired, not so the result
can be quoted with a caveat attached.

## The measurements

| arm | streamer | GB/s | cores | victim occ | victim MBM | median s | tax | 95% CI | CoV_rep |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|
| `quiescent` | none | -- | -- | 8 MiB | 1.40 GB | 0.0288 | 1.000 | -- | 1.74% |
| `WB_sat` | `wb_load` CXL | 24.24 | 7 | 0 MiB | 56.48 GB | 0.2340 | 8.175 | [8.069, 8.357] | 0.37% |
| `FB0_sat` | `flushbehind -f 0` | 24.22 | 7 | 0 MiB | 56.18 GB | 0.2340 | 8.157 | [8.034, 8.393] | 0.74% |
| `WB_local` | `wb_load` DRAM | 24.26 | 7 | 0 MiB | 56.11 GB | 0.2338 | 8.140 | [8.034, 8.339] | 0.36% |
| `NTA_sat` | `prefetchnta` CXL | 24.54 | 7 | 2 MiB | 14.80 GB | 0.1515 | 5.281 | [5.207, 5.429] | 4.69% |
| `FB256_sat` | `flushbehind -f 256` | 16.96 | 7 | 5 MiB | 6.37 GB | 0.0747 | 2.586 | [2.569, 2.667] | 1.56% |
| `WB_fbmatch` | `wb_load` CXL | 12.70 | 1 | 2 MiB | 9.38 GB | 0.0430 | 1.509 | [1.431, 1.557] | 5.68% |
| `FB0_match` | `flushbehind -f 0` | 12.73 | 1 | 2 MiB | 8.96 GB | 0.0415 | 1.456 | [1.393, 1.552] | 7.83% |
| `FB256_match` | `flushbehind -f 256` | 15.42 | 3 | 7 MiB | 3.27 GB | 0.0340 | 1.172 | [1.138, 1.250] | 13.10% |

Declared pairs, rep-paired percentile bootstrap, B = 20000:

| pair | difference | 95% CI | status |
|---|---:|---|---|
| `FB0_match` - `FB256_match` (within-binary, matched) | +0.263 | [+0.179, +0.420] | **no verdict** (outcome 5) |
| `WB_fbmatch` - `FB256_match` (cross-binary, matched) | +0.298 | [+0.174, +0.369] | **no verdict** (outcome 5) |
| `WB_fbmatch` - `FB0_match` (instrument check, expect 0) | +0.034 | [-0.069, +0.071] | **passes** |
| `FB0_sat` - `FB256_sat` (NOT bandwidth-matched) | +5.531 | [+5.474, +5.714] | anti-conservative, not quotable alone |
| `WB_sat` - `NTA_sat` (declared negative control) | +2.897 | [+2.845, +2.992] | **outcome 3 fires — see below** |

## A4.4 outcome 3 also fires, and it is the serious finding

A4.1 established from a victimless sweep that `wb_prefetchnta` holds the entire
16 MiB CCX L3 on Zen4c and is therefore **not** a non-allocating arm. A4.4
declared the consequence in advance: *"`NTA_sat` recovers anything at all. The
mechanism is wrong, because A4.1 measured that arm holding the entire CCX L3."*

`NTA_sat` recovers a great deal. Against `WB_sat` at the same core count and a
bandwidth 1.2% higher, it taxes **5.281 against 8.175** — a paired difference
of **+2.897 [+2.845, +2.992]**, about 40% of the tax recovered.

This contrast is not an artifact of the dispersion that voids the matched pair.
`WB_sat` is the tightest arm in the campaign (CoV_rep 0.37%) and `NTA_sat` is
under the bar at 4.69%, and the difference is **exactly insensitive to dropping
any single repetition**: all ten leave-one-out point estimates are +2.897 to
three decimals. (`NTA_sat` does sit marginally over the bar on the *pooled*
figure, 5.25%, carried by one repetition whose median is 0.172 s against
0.147--0.154 for the other nine. Dropping it changes the difference by nothing.)

Taken at the pre-registration's word, an arm that allocates has recovered 40% of
the tax, and allocation is therefore not what the recovery mechanism turns on.
That is a serious negative and is reported as one.

**One premise in that chain is worth testing before it is accepted, and the test
has not been run.** A4.1 measured streamer occupancy *with no victim present*.
Occupancy in an uncontended cache cannot distinguish a stream inserted at MRU
from one inserted at LRU: both fill an idle L3 to 16.00 MiB. They behave
completely differently under competition, where LRU-inserted lines are the first
to go. This run's victim-side counters are consistent with that reading — at
equal bandwidth and equal cores the victim keeps 2 MiB against 0 MiB and moves
14.80 GB against 56.48 GB — but victim-side evidence cannot settle a question
about the streamer.

The discriminating measurement is **streamer-side L3 occupancy during the
co-run**, `NTA_sat` against `WB_sat`. If NTA's streamer occupancy collapses
under competition while `wb_load`'s holds near 16 MiB, A4.1's premise fails and
outcome 3's inference does not go through; if both hold, the mechanism is wrong
as declared.

**It has since been made, and both hold.** A5.3, 2026-08-22, 10 repetitions:
NTA's streamer occupancy under co-run is **86.7% of the CCX** and **0.884
[0.880, 0.889]** of `wb_load`'s, against a threshold of 0.50 fixed before the
measurement. NTA allocates under competition, and the declared reading above
therefore stands as the final one rather than the provisional one: **the
mechanism as stated is wrong.**

The same artifact also shows what A4.1 could not have seen and what the
victim-side counters above were groping towards. With no victim competing the
two streamers are identical (15.80 MiB each); under competition `wb_load`
yields 0.13 MiB and NTA yields 1.98. The operative variable is insertion
priority in a cache both streamers fill, not allocation versus bypass. Full
result, including why the reverse-causation reading fails on the sign, in
`DUCKDB_JOIN_AMD_NTA_DISCRIMINATION.md`.

## What did work

- **§5's bandwidth assertion passes cleanly**, per repetition, for the first
  time on either host: every referenced arm within 2.1% of its A4.5 declared
  value, most within 1%. (The Intel campaign fails it on one repetition; see
  `DUCKDB_JOIN_CORUN_OUTCOME.md`.)
- **The A4.5 instrument check passes.** `WB_fbmatch` and `FB0_match` — two
  allocating arms at 12.70 and 12.73 GB/s from *different binaries* — differ by
  +0.034 with an interval spanning zero. The two binaries do not differ in
  anything but flushing, so the cross-binary pairing is not contaminated. This
  was declared as an instrument check and no result is drawn from it.
- **The quiescent arm reproduces the independent gate sweep**: 0.0288 s here
  against the gate's 0.0280 s full-mask median (2.9%), occupancy 8 MiB against
  8.70 MiB.
- **All 90 arms valid**, no hostguard aborts, no invalid records.

## Why the dispersion, declared as §6 outcome 5 requires

**The variance is between invocations, not within them.** This is the first
thing to establish, because it decides which remedies are even relevant. If
every invocation sampled the same underlying distribution, the CoV across
repetition medians would be the standard error of a median of 300 draws,
`1.253 sigma / sqrt(300)`. It is not, in any arm:

| arm | CoV_rep observed | predicted from within-invocation sampling | ratio | half-quantum floor |
|---|---:|---:|---:|---:|
| `FB256_match` | 13.10% | 1.41% | 9.3x | 1.44% |
| `FB0_match` | 7.83% | 0.86% | 9.1x | 1.19% |
| `WB_fbmatch` | 5.68% | 0.58% | 9.9x | 1.18% |
| `NTA_sat` | 4.69% | 0.38% | 12.4x | 0.33% |
| `quiescent` | 1.74% | 0.25% | 7.1x | 1.75% |
| `WB_sat` | 0.37% | 0.08% | 4.5x | 0.21% |

Every arm carries real invocation-to-invocation structure, 4.5x to 12x more
than sampling explains.

**The timer is a floor, not the driver.** DuckDB's CLI `.timer` has 1 ms
resolution — all 27000 measured queries in this artifact are exact integer
milliseconds, so the quantum is the instrument and not a coincidence of the
workload — and against a 28 ms query that is 3.6% per query. But each
repetition reports a median of 300 queries, which averages the quantum down to
the half-quantum column above: **1.2--1.4% for the matched arms against
5.7--13.1% observed.** The timer explains roughly a ninth of the dispersion in
the arms that matter. It does bound the quiescent arm, whose 1.74% is
indistinguishable from its 1.75% floor, and it does set the pooled CoV.

**What does move with runtime is the victim's residency.** Within an arm,
across its ten repetitions, the invocation's mean victim occupancy predicts its
median runtime:

| arm | correlation of rep median with rep mean occupancy |
|---|---:|
| `NTA_sat` | **-0.818** |
| `FB256_match` | **-0.815** |
| `FB0_match` | -0.605 |
| `WB_fbmatch` | +0.299 |
| `FB256_sat` | -0.034 |

Less cache retained, slower — in the three arms with the largest CoV, and not
in the two where the correlation is absent. `FB256_match` inv5 is the clean
case: its occupancy runs low for the *entire* invocation, mean 6.0 MiB against
7.0--7.4 for the other nine, and its median is 47 ms against 31--35.

**A5.2 has since qualified this paragraph, 2026-08-22.** The correlation is real
and reproduces (r = -0.856 here, -0.605 and -0.830 in two fresh blocks). The
*attribution to the operating point* does not. Removing inv5 alone takes this
arm from 13.10% to 4.50%, under the bar; `WB_fbmatch` likewise falls to 3.56% on
one removal, though `FB0_match` stays at 6.98% and is genuinely broadly
dispersed. And a fresh **quiescent** arm -- no streamer, no contention, idle
frozen host -- produced CoV_rep 13.40% with a best leave-one-out of 1.59%, one
invocation at 0.0400 s against 0.0280. The 1.4x excursion is an invocation-level
anomaly that occurs with the aggressor absent, so it cannot be the signature of
a co-run operating point on a cliff. See `DUCKDB_JOIN_A52_OUTCOME.md`. There is
no warm-up transient to blame — occupancy reaches its level by the first 0.25 s
sample and stays there. A 15% shortfall in retained cache costs 38% in runtime,
which is what operating near a cliff looks like: at 7 filling cores the victim
is deterministically crushed to 0 MiB (`WB_sat` CoV 0.37%), quiescent it
deterministically keeps its table (1.74%, at the timer floor), and the matched
pair sits in between at 2--7 MiB of 16, where the outcome is not determined.

Sarle's bimodality coefficient is reported for completeness and carries nothing.
Pooled over the arm, `FB256_match` reads 0.754 against the 0.556 uniform
threshold, the highest in the campaign. But per invocation the statistic is too
noisy at n = 300 against a 1 ms quantum to separate anything: only 1 of
`FB256_match`'s 10 invocations exceeds the threshold, 3 of `FB0_match`'s do
despite a pooled 0.330, and one *quiescent* invocation reaches 0.677 with no
streamer running at all. The evidence that this operating point is unstable is
the variance decomposition and the occupancy correlation above, not the
coefficient.

Consistent with all of it, the matched pair's **intervals** are what the
dispersion destroys, not its point estimate: leave-one-out moves the difference
only between +0.250 and +0.276, while the 95% interval swings across
[+0.107, +0.483] depending on which repetition is dropped. The effect is
probably real and this campaign cannot say so.

## What must happen before this host can be quoted

**A remedy proposed in the first draft of this document is withdrawn here, and
the reason matters.** That draft proposed lengthening the query by raising
`probe_rows`, on the grounds that `R(N) = 40N` is build-side only so the
validity conditions would be untouched. It is wrong twice. **A2 forbids it
explicitly** — "timing resolution lost to the shorter probe is recovered by
raising the in-invocation query count, not by lengthening the probe" — because
P was sized to ~12% of LLC precisely so the victim would stop competing with
its own scan for the cache it is being measured on; on this host P = 250K is
2 MB against a 16 MiB CCX, and 10x-ing it would reinstate the exact defect A2
was written to remove. And independently of A2 it would not work: it attacks
the within-invocation term, which the table above shows is already 9x too small
to account for the dispersion. Recorded rather than quietly dropped, because
the reasoning error — fixing the cause that was easiest to measure rather than
the one that dominates — is the kind that survives into a paper.

What follows is therefore declared *before* any re-run, with the +0.263 already
known, so that no subsequent number can be selected against it (§6.6).

**Status 2026-08-22: item 1 has run and item 4 is complete; see A5.2 and A5.3.**
Item 1's declared measurement was made and **hugepages do not control the
spread** (5.69% against a contemporaneous 5.90%, needing < 3%), so item 3's
re-run is *not* licensed by it. A5.2 could not reach its second branch either,
because the 13.10% comparator failed to reproduce on the same frozen host.
Whether a plain re-run may be taken on that basis is put to the lead in
`DUCKDB_JOIN_A52_OUTCOME.md`; it is not taken here, because the target number is
already known and A5.2 says "no conclusion, and no re-run."

1. **Establish what differs between invocations.** Each repetition is a fresh
   DuckDB process building a fresh hash table, and the L3 is physically
   indexed, so one candidate is that the physical pages a given invocation
   receives determine how well its reused set coexists with the streamer, fixed
   for that invocation's lifetime. That is a hypothesis and nothing here tests
   it. The measurement that would: repeat one arm with the victim's build
   arena pre-faulted from hugepages, and compare between-invocation occupancy
   spread against the 6.2% measured for `FB256_match` here. If the spread
   collapses, page placement is the driver and is controllable; if it does not,
   it is not.
2. **Do not lengthen the query, by either route.** Not the probe (A2), and not
   the query count, which also attacks only the within-invocation term.
3. **Re-run only after 1 has a declared answer**, at the same N = 100K, same
   arms, and report whatever comes out. If the between-invocation spread is
   controllable and CoV falls under 5%, a verdict may be drawn. **If it is not
   controllable, the finding is that a 16 MiB CCX cannot host this victim at a
   stable operating point, and that is a publishable result** — it is reported
   as such and not re-tuned around. A re-run that lowers CoV must say which
   change did it.
4. **Measure streamer-side occupancy during co-run** for `NTA_sat` and
   `WB_sat`, to settle outcome 3. Independent of the above and worth doing
   first, being cheaper and more consequential.

## The asymmetry that must accompany any AMD number

Per A4.4, stated wherever an AMD figure is quoted. On Intel the matched pairs
held bandwidth fixed and let core count differ, with the write-back arm using
*fewer* cores, so its excess tax was understated. Here it runs the other way:
`FB256_match` carries 1.21x the bandwidth, 3x the filling cores and more
attributed controller traffic than `FB0_match`, and is smaller only in the
quantity the paper is about. Any recovery measured under those handicaps is a
**lower bound**. Both campaigns are conservative, by different mechanisms, and
neither may be quoted as a point estimate of allocation's contribution.

`FB0_sat` / `FB256_sat` are not bandwidth-matched (24.22 vs 16.96 GB/s, in the
non-allocating arm's favour). Per A4.5 that pair is anti-conservative and may
not be quoted on its own; it appears here only alongside the matched pair.

## Provenance

- `artifacts/join_corun_moscxl.jsonl` — 90 records
- `artifacts/corun_moscxl.log` — run log, including hostguard lines
- `artifacts/join_gate_moscxl.jsonl` — the §2 gate that selected N = 100K
- `summarize_corun.py` — rep-paired percentile bootstrap, B = 20000, seed
  20260821; resamples repetitions, not queries
- `check_bandwidth_assertion.py` — §5's per-repetition bandwidth assertion

Reproduce with `python3 summarize_corun.py artifacts/join_corun_moscxl.jsonl`
and `python3 check_bandwidth_assertion.py artifacts/join_corun_moscxl.jsonl`.
