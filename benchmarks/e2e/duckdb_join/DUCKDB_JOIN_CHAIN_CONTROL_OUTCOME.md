# The duplicate chain is not the mechanism, and the de-confound does not need it

`mos181`, 2026-08-21. Within-engine control declared in
`DUCKDB_JOIN_CORUN_PREREGISTRATION.md` §1 and §6 outcome 3, run to its
pre-registered decision rule. 70 arms, all valid, no aborts.

## What was held fixed

`joinuniq` is the same query, the same build size, the same host, the same
seven arms, the same seeded interleave. `K = N` instead of `K = N/8`, so build
keys are unique and each probe row matches exactly one build row. The reused
set is **identical** — `R(N) = 8N + 32N = 40N` does not mention `K` — so the
hash table the victim rereads is byte-for-byte the same size. What changes is
the chain walk: nine dependent rounds per tuple become one, and the output
falls from `8 x probe` rows to `probe` rows.

`QUERIES` was raised from 13 to 31 for the control, because its query is 2.3x
shorter and an unmatched query count would have given the occupancy sampler a
third of the samples. The tax is a within-configuration ratio of medians, so
the count cannot bias it; only measurement quality changes.

## Result

Tax against the adjacent quiescent repetition, 10 repetitions, rep-paired
percentile bootstrap:

| arm | GB/s | `chain8` tax | `joinuniq` tax | chain contribution |
|---|---:|---:|---:|---:|
| `WB_sat` | 24.9 | 1.467 | 1.378 | +0.089 |
| `WB_local` | 24.9 | 1.454 | 1.377 | +0.077 |
| `WB_match_hi` | 18.0 | 1.112 | 1.102 | +0.010 |
| `WB_match_lo` | 10.7 | 1.113 | 1.093 | +0.020 |
| `NTA_sat` | 17.8 | 1.049 | 1.036 | +0.013 |
| `NTA_lo` | 10.8 | 1.018 | 1.011 | +0.007 |

`chain8` exceeds `joinuniq` at every arm, so §6 outcome 3 does **not** fire and
the chain claim is not withdrawn. But the size of the effect is the finding:
at saturation the chain contributes **0.089 of a 0.467 tax, 19%**. The
remaining 81% is hash-table reuse alone, with no duplicate chain involved. The
chain is a contributor, not the mechanism, and the paper should say so.

## The part that matters more

The campaign's central de-confound is not the tax, it is the *difference*
between an allocating and a non-allocating streamer at matched bandwidth. That
difference is unchanged by removing the chain:

| operating point | `chain8` | `joinuniq` |
|---|---|---|
| ~18 GB/s, `WB_match_hi` - `NTA_sat` | +0.058 [+0.047, +0.071] | +0.068 [+0.065, +0.073] |
| ~10.8 GB/s, `WB_match_lo` - `NTA_lo` | +0.093 [+0.089, +0.097] | +0.079 [+0.074, +0.084] |

The two configurations disagree in **opposite directions** at the two operating
points, by margins comparable to the interval widths — `joinuniq` larger at
18 GB/s, `chain8` larger at 10.8 GB/s. There is no consistent chain effect on
the de-confound. Both intervals exclude zero in both configurations.

This strengthens the central claim rather than weakening it. The allocation
result is not an artifact of an unusual many-to-many join: it survives in a
plain one-to-one hash join, which is the shape of join most real queries have.
It also narrows what the paper may say about the chain, which had been carrying
more weight in the argument than it earns.

## A supporting observation, unchanged across both configurations

Victim DRAM traffic tracks allocation, not the streamer's byte rate.
Under `NTA_sat` the victim moves 0.28 GB, the same as quiescent, while holding
90 MiB. Under `WB_match_hi` at *less* streamer bandwidth it moves 2.52 GB — 9x
more — while holding 66 MiB. A streamer that does not allocate does not evict
the victim, and a victim that is not evicted does not go to memory. This is the
mechanism stated in counters rather than in runtimes.

## Provenance

- `artifacts/join_corun_mos181_chain1.jsonl` — 70 records, this control
- `artifacts/join_corun_mos181.jsonl` — 70 records, the `chain8` campaign
- `summarize_corun.py` — rep-paired percentile bootstrap, B = 20000, seed
  20260821; resamples repetitions, not queries

Reproduce with `python3 summarize_corun.py artifacts/join_corun_mos181_chain1.jsonl`.
