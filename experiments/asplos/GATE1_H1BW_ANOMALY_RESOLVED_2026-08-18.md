# The h1bw anomaly is resolved: two misreadings, no model defect

Written 2026-08-18, closing the open item in
`GATE1_H1BW_RERUN_OUTCOME.md` that `CANONICAL_CONFIG_PROPOSAL.md` made a
prerequisite for #28.

Reproduced both arms at the documented config (`num-cpus=1`, `l3_size=5MiB`
20-way, `--maxinsts=20000000`, `ALL_CXL=1`, `HNF_SF_FINITE=0 HNF_H3=0
HNF_DMT=0`, `L1_MSHR=16`) and matched the recorded numbers to within 1%:

| | measured here | recorded in the re-run |
|---|---:|---:|
| WB | 3.16 GB/s | 3.19 GB/s |
| +H2 | 2.73 GB/s | 2.76 GB/s |

So this is the same phenomenon, not a different one.

## Half 1 — the "impossible" hit rate is a base-rate effect, not miscounting

The anomaly: H2 reports a far higher HNF hit rate than WB despite being the
non-allocating arm. Reproduced (26.6% vs 0.15%). The leading hypothesis was that
`m_demand_hits` counts a tag/directory hit against a pure-R entry as a data hit.

**Refuted.** H2 performs *more* real data-array reads than WB:

| | WB | +H2 |
|---|---:|---:|
| HNF `numDataArrayReads` | 114,891 | **278,599** |
| HNF fills (`DataArrayWriteOnFill`) | 812,465 | **32,814** (−96%) |
| HNF `m_demand_hits` | 98 | 16,713 |
| HNF `m_demand_accesses` | 66,061 | 62,773 |

The hits are backed by actual data-array reads, so nothing is being
miscounted. The explanation is the *composition* of what the L3 holds. Under
WB the L3 takes 812k fills of dead stream lines that a sequential scan never
re-reads, so the hit rate is ~0 by construction. Under H2 the stream does not
fill the L3 at all (33k fills, −96%), so the L3 retains only the small
non-streaming working set — which *is* re-read. Demand accesses are nearly
identical (66,061 vs 62,773); ~17k that missed under WB now hit.

That is H2 doing exactly what it is for: protecting a resident working set from
stream pollution. The counter was never wrong; "the non-allocating arm should
have fewer copies to hit against" is true of *streaming* lines and irrelevant to
the lines that dominate the hit rate.

## Half 2 — the "backwards ordering" is a metric artifact

The re-run found WB > H2 in GB/s and flagged it as violating H1, since H2 is
not supposed to disturb prefetching. At matched work:

| | WB | +H2 | delta |
|---|---:|---:|---:|
| `simInsts` | 14,621,894 | 14,621,818 | **−0.0005%** |
| cycles | 31,284,372 | 25,259,240 | **−19.3%** |
| memory read | 52.0 MB | 36.3 MB | **−30.2%** |
| GB/s | 3.16 | 2.73 | −13.6% |

**H2 is 19.3% faster on identical work.** It reports lower GB/s only because it
needs 30% less traffic to do that work — WB's L3 thrash forces re-fetches that
H2 avoids. GB/s is bytes-moved per unit time, so on a fixed-work probe whose
arms differ in traffic volume it *penalises efficiency*. Nothing about H1 is
violated: the ordering that matters (H2 at least as fast as WB) holds, and
holds more strongly than the bandwidth figure suggests.

## Consequences

1. **#28's prerequisite is discharged.** The accounting is sound; `m_demand_hits`
   can be used, though `mem_ctrls` bytes and `DataArrayWriteOnFill` remain
   preferable because they are unambiguous.
2. **`tab:h1bw` should not report GB/s alone.** For a fixed-instruction probe
   whose arms differ in traffic, add cycles-to-complete (or normalise traffic by
   construction). The published ordering (H2 $\ge$ WB) is substantively correct;
   the re-run's inversion was the metric, not the model.
3. **The deferred contrast in `Sec3_Mitigation.tex` is unblocked.** The
   flush-behind paragraph deliberately omits a numeric
   "declared-Streaming-costs-the-streamer-nothing" contrast *pending resolution
   of this anomaly*. It is now resolved, and the direction is favourable: a
   declared type costs the streamer nothing here, against flush-behind's
   measured 31.3% streamer-bandwidth cost on AMD. **State that structurally,
   not with a gem5 magnitude** — mixing a gem5 delta with an AMD hardware delta
   would break the arm-identity rule, and quoting a gem5 magnitude would break
   the demotion decision.
