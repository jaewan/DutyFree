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
as declared. No artifact in this repository contains that measurement — the
runner monitors the victim's group only. Until it is made, **the declared
reading stands**, and this is the most important open item on the AMD host.

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

Two causes, one instrumental and one physical.

**The query is too short for the timer.** Times come from DuckDB's CLI `.timer`,
which prints `Run Time (s): real 0.028` — **1 ms resolution**. All 27000
measured queries in this artifact are exact integer milliseconds, confirming the
quantum is the instrument and not a coincidence of the workload. On Intel's
607 ms query 1 ms is 0.16%; on this 28 ms query it is 3.6%. The quiescent arm
puts **2326 of its 3000 queries into two adjacent bins** (0.028 and 0.029), and
its ten repetition medians take only the values 0.028, 0.0285 and 0.029 — one
quantum wide end to end. Its 3.4% pooled CoV is therefore the *floor* here
before any real variation.

The short query is not a free choice. `R(N) = 40N` and §2 caps full-mask
occupancy at 60% of a 16 MiB CCX, which caps N at 100K, which caps the query at
28 ms. The Intel host has 320 MiB and no such squeeze.

**The victim is bistable in exactly the arms that matter.** Dispersion is not
uniform: `WB_sat` reads 0.37% and `quiescent` 1.74%, while the three
low-filling-core arms read 5.68--13.10%. At 7 filling cores the victim is
deterministically crushed to 0 MiB; quiescent it deterministically keeps its
table. The matched pair operates in between, at 2--7 MiB of 16, where the victim
either retains its hash table or loses it, and small perturbations flip the
outcome.

`FB256_match` inv5 shows the flipping directly, without needing a statistic:
its median is **0.047 s against 0.031--0.035 for the other nine repetitions**,
and within that single invocation the queries span 0.029 to 0.072 s in three
visibly separated groups (~0.029--0.043, ~0.044--0.055, ~0.061--0.072). A whole
repetition displaced by 40%, and a 2.5x spread inside it, is what a bistable
residency looks like.

**Sarle's bimodality coefficient corroborates this but cannot carry it.** Pooled
over the arm, `FB256_match` reads 0.754 against the 0.556 uniform threshold,
the highest in the campaign. But computed per invocation the statistic is noisy
at n = 300 against a 1 ms quantum: only 1 of `FB256_match`'s 10 invocations
exceeds the threshold, while 3 of `FB0_match`'s do despite a pooled 0.330, and
one *quiescent* invocation reaches 0.677 with no streamer running at all. BC is
reported here for completeness and as corroboration; the evidence that the
loaded distributions are multimodal is the inv5 structure above and the CoV
table, not the coefficient.

Consistent with all of this, the matched pair's **intervals** are what the
dispersion destroys, not its point estimate: leave-one-out moves the difference
only between +0.250 and +0.276, while the 95% interval swings across
[+0.107, +0.483] depending on which repetition is dropped. The effect is
probably real and the campaign cannot say so.

## What must happen before this host can be quoted

1. **Lengthen the measurement window without touching §2.** `R(N) = 8N + 32N` is
   build-side only, so raising `probe_rows` (currently 250K against a 100K
   build) lengthens the query without changing the reused set or any validity
   condition *by construction*. Condition 2 must still be re-verified
   empirically — full-mask occupancy is 54.4% with only 5.6 points of headroom,
   and the probe's own streaming footprint is not nothing.
2. **Re-run and re-check dispersion.** If CoV falls under 5% and the
   multimodality goes with it, the operating point is repaired and a verdict may
   be drawn. If the multimodality survives a 10x longer query, it is physical,
   and the finding is that a 16 MiB CCX cannot host this victim at a stable
   operating point — which is a legitimate result and must be reported as one
   rather than re-tuned around.
3. **Measure streamer-side occupancy during co-run** for `NTA_sat` and `WB_sat`,
   to settle outcome 3.

These are declared here, before the re-run, so that a subsequent number cannot
be selected against the one above. §6.6 governs: fishing for a configuration
that produces a preferred result is not repair.

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
