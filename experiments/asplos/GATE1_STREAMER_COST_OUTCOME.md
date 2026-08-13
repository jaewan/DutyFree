# [STREAMER COST] — the streamer-side cost of AMD flush-behind (#30)

Written 2026-08-13. Answers the bracketed slot `PAPER_REVISIONS_2026-08-11.md`
R6 left open: *"It is per-core work: every recovered line costs the streamer
instructions and issue slots on the critical path, `[STREAMER COST]`."* Per
`PAPER_SESSION_PROMPT.md` §3.3, quantifying flush-behind's streamer-side cost
is explicitly **not embargoed** — only attributing the victim-side residual
between H2 and H3 is. This document does not attribute anything; it reports
one arm's own achieved bandwidth against another arm's own achieved
bandwidth, both self-reported by the aggressor process itself.

## No new hardware run was needed

The number was already sitting in data frozen for the 76.3%-recovery result
and never extracted. Same provenance as that number, exactly:

- `~/DutyFree-Gem5`... no — **AMD broker** (`ssh broker`, EPYC 9754), hash-join
  cross-process campaign, victim-first protocol, `flush_d256kb` = 256 KiB
  flush distance, n=12, frozen 2026-08-10 at DutyFree commit `0628e0d`.
- Raw file:
  `results/amd/hash_join_cross_process/amd_hash_join_victim_first_triple_n12.jsonl`
  (already committed).
- Each record's `aggressor_records[0].bw_gbps` (mirrored into
  `agg_bw_self_gbps_sum`) is the aggressor's **own self-reported achieved
  bandwidth** for that rep — the same field `AMD_CROSS_PROCESS_OUTCOME.md`'s
  "Frozen Victim-First Protocol" table already prints as "aggressor self BW"
  (24.72 GB/s for `wb`, 16.97 GB/s for `flush_d256kb`) but never turned into
  a cost figure or a CI.

## The number

Per-rep self-reported aggressor bandwidth (GB/s), n=12 each, same campaign:

- `wb`: 24.717, 24.662, 24.717, 24.747, 24.686, 24.723, 24.723, 24.746,
  24.740, 24.715, 24.717, 24.755 — mean 24.721, CoV 0.11%.
- `flush_d256kb`: 16.978, 16.983, 16.949, 16.974, 16.992, 16.953, 16.982,
  16.988, 16.981, 16.974, 16.972, 16.963 — mean 16.974, CoV 0.07%.

Per-rep paired cost fraction `(wb - flush) / wb`, 20,000-resample rep-paired
bootstrap, seed 1 (same method the 76.3% figure uses):

> **Flush-behind costs the streamer 31.34% [31.28, 31.39] of its own
> bandwidth** relative to plain write-back, at the 256 KiB flush distance
> used for the paper's 76.3% victim-recovery figure. Equivalently, the
> streamer retains 68.66% of its WB throughput.

Both distributions are extremely tight (CoV well under 1%), so this is not a
noisy estimate straining a wide CI — it is a clean, repeatable cost, measured
on the identical hardware, run, and flush-distance configuration as the
victim-side number it accompanies.

## What this is not

This is the **synthetic aggressor's** self-cost (the same `wb_load` /
`flushbehind` C microbenchmark used throughout the hash-join campaign), not a
**real application's** end-to-end query-time cost. `benchmarks/e2e/
E2E_SESSION_PROMPT.md` §4.4 wants the latter explicitly — its frontier table
is framed around "the streamer's own query time," not a raw bandwidth ratio,
precisely because "a reviewer discounts" a microbenchmark bandwidth number
for exactly this argument. That larger campaign (GAP-BS victim + DuckDB
streamer) is separately tracked and **not complete** —
`benchmarks/e2e/E2E_STATUS.md` currently reads "frontier: preregistered;
unmeasured." This document fills the bracket the paper currently has with a
real, clean, already-collected number; it does not substitute for that
fuller campaign, and should not be cited as if it does.

## The "declared Streaming costs nothing" contrast — deliberately left unfilled

R6's paragraph implicitly wants a contrast: flush-behind's real software
cost against what a genuine hardware declaration (H2) would cost the
streamer. The obvious source is gem5's own H2-vs-WB aggressor bandwidth
(`streaming-gem5-results` memory records an old H2 ≥ WB streamer-bandwidth
result). **This document deliberately does not cite that number.** This
session's `tab:h1bw` reconstruction (`GATE1_H1BW_RERUN_OUTCOME.md`) found an
unresolved anomaly in exactly this class of measurement on the current tree
— the HNF's hit-rate accounting behaves inconsistently with H2's own
non-allocating definition, and the WB-vs-H2 streamer-bandwidth ordering did
not reproduce. Citing an old, unverified number here to complete a tidy
contrast would repeat the mistake `GATE1_H1BW_RERUN_OUTCOME.md` was written
to stop. Until that `.sm`-level trace happens, the honest version of this
contrast is the **structural** one already available without a number: a
declared page attribute costs nothing per line touched, because it is
consulted, not executed — no instructions run on the streamer's critical
path — whereas flush-behind's cost above is a real per-line `clflushopt`
that competes with the streamer's own loads for issue slots. That is a
qualitative, defensible claim; the gem5 quantitative version of it is not,
right now.

## Suggested paragraph completion (draft — not yet in `~/STREAMING_Paper/`)

Per `REPO_DISCIPLINE.md`/`PAPER_SESSION_PROMPT.md` §2, this stays in
`~/DutyFree` as a draft. Filling `PAPER_REVISIONS_2026-08-11.md`'s R6
brackets:

> On AMD (`broker`, EPYC 9754), a hash-join tenant, victim-first arrival,
> 256 KiB flush distance, n=12, recovers 76.3% [76.1, 76.4] of its tax. It is
> **per-core work**: every recovered line costs the streamer instructions and
> issue slots on the critical path — the same aggressor's own achieved
> bandwidth drops 31.3% [31.28, 31.39] relative to plain write-back on this
> hardware, at this flush distance. [...] It offers the neighbour no
> guarantee [...] And it cannot reach the lines that matter most [...].

This fills `[RECOVERY]`/`[ARM IDENTITY]` (76.3% [76.1,76.4], AMD broker,
hash-join, victim-first, 256 KiB, n=12) and `[STREAMER COST]` (31.34%
[31.28,31.39], same arm) with numbers that share one provenance record. It
does **not** add the H2-cost contrast sentence — leave that out, or state it
structurally without a number, until the h1bw anomaly is resolved.

## Recommendation

1. Land the paragraph above (or the lead's edit of it) in
   `Sec3_Mitigation.tex` after the MBA paragraph, per R6's original
   placement instruction.
2. Do **not** add a numeric H2-streamer-cost contrast until
   `GATE1_H1BW_RERUN_OUTCOME.md`'s open anomaly is resolved.
3. Treat this as *not* satisfying `E2E_SESSION_PROMPT.md`'s frontier bar —
   that campaign is still open and is the more defensible, real-application
   version of this same argument.
