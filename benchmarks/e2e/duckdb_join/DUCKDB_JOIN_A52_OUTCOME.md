# A5.2 outcome: hugepages do not control the spread, and the comparator did not reproduce

`moscxl`, 2026-08-22. Implements A5.2 of `DUCKDB_JOIN_CORUN_PREREGISTRATION.md`
under `DUCKDB_JOIN_A52_RUN_DECISIONS.md`, both committed before the data
existed. Two blocks of 10 repetitions x 2 arms, 40 records, all valid, no
aborts. Control block first, hugepage block second.

## Verdict

**The pass branch is ruled out on its own absolute thresholds.** A5.2 required
spread < 3% *and* CoV_rep < 5%. With a hugepage-backed victim arena the spread
is **5.69%** and CoV_rep is **5.29%**. Neither clears, and the spread misses by
nearly a factor of two. Against the contemporaneous control the spread is
**unchanged** (5.69% against 5.90%, 3.6% relative, inside the 15% bar declared
in advance) and CoV_rep is slightly **worse** (5.29% against 4.28%).

So the actionable half of A5.2 has a clean answer: **page placement is not a
controllable driver of the between-invocation spread, and no hugepage re-run of
the AMD campaign is licensed.** A pass was the only thing that would have
bought one.

**The remaining half cannot be settled, and the reason is the finding.** A5.2's
"unchanged -> report the instability as physical" branch is stated against the
historical comparator, and **the historical comparator did not reproduce.** The
contemporaneous no-shim control -- same host, same frozen state, same arm, same
operating point, no manipulation at all -- ran at **CoV_rep 4.28%**, under the
5% bar, against the campaign's **13.10%**.

That validity condition was declared before the run for exactly this
possibility. It fires, so A5.2 does not conclude that the instability is
physical. It does not conclude the opposite either.

## The two blocks

| block | arm | spread (CoV of mean occ) | CoV_rep | occ range | median range | AnonHugePages |
|---|---|---:|---:|---|---|---|
| control | `quiescent` | 3.74% | 2.80% | 8.18--9.10 MiB | 0.0270--0.0290 s | none |
| control | `FB256_match` | **5.90%** | **4.28%** | 6.39--7.59 MiB | 0.0310--0.0360 s | none |
| hugepage | `quiescent` | 3.86% | 13.40% | 7.90--8.95 MiB | 0.0270--0.0400 s | 26--28 MiB |
| hugepage | `FB256_match` | **5.69%** | **5.29%** | 6.18--7.41 MiB | 0.0300--0.0360 s | 24--26 MiB |

Historical comparators: spread 5.95%, CoV_rep 13.10%.

**The manipulation demonstrably took.** Every one of the 20 hugepage
repetitions obtained 24--28 MiB of `AnonHugePages`, against 0 kB host-wide
before and 0 in all 20 control repetitions. This is the check that stops the
diagnostic from lying: a shim that silently failed would produce a null
identical in every respect to a real one. It did not fail, so the null is real.

**The occupancy spread is the stable quantity here, and it is completely
insensitive to page backing.** 5.95% historically, 5.90% in today's control,
5.69% with hugepages -- three measurements within 0.26 points across a day and
across the manipulation. Whatever fixes how much cache an invocation keeps, it
is not the page size it is faulted with.

## Why the comparator did not reproduce: the 13.10% is one invocation

| arm | campaign CoV_rep | best leave-one-out | the dropped repetition |
|---|---:|---:|---|
| `FB256_match` | 13.10% | **4.50%** | inv5, median 0.0470 s against a 0.0340 pool |
| `WB_fbmatch` | 5.68% | **3.56%** | inv2, 0.0370 against 0.0430 |
| `FB0_match` | 7.83% | 6.98% | inv5, 0.0370 against 0.0415 -- **still over the bar** |

Two of the three arms that voided the AMD campaign fall under the 5% bar on the
removal of a single repetition. `FB0_match` does not: its dispersion is broad
rather than driven by one point, so **outcome 5 does not collapse entirely**,
and nothing here retracts it.

**The decisive observation is in this run's own quiescent arm.** The hugepage
block's `quiescent` arm reads CoV_rep **13.40%** -- the campaign's figure, near
enough to be uncanny -- with a best leave-one-out of **1.59%**: one invocation
at 0.0400 s against a 0.0280 s pool, 1.43x. That arm has **no streamer running
at all.** A solo DuckDB process on an idle frozen host, with no aggressor, no
contention and no cache pressure, produced the same signature that was
attributed to an unstable co-run operating point.

So the anomaly is at the level of the *invocation*, not of the contention. It
appears at a rate of roughly one in twenty to forty invocations across every
arm, and its magnitude is about 1.4x. `FB256_match` inv5 was one draw of it.

The AMD outcome document reads that repetition as "the signature of an
operating point on a cliff -- a 15% shortfall in cache costing 38% in time."
The cache correlation it rests on is real and reproduces (r = -0.856 campaign,
-0.605 control, -0.830 hugepage). What does not survive is the attribution to
the *operating point*: the same 1.4x excursion happens with the streamer absent.

## What was excluded

- **Not a host-state change.** The campaign ran 2026-08-21 22:11--23:49, after
  the 21:23 freeze at `d8eda44`, so both campaigns are on identical frozen
  state. Absolute medians agree: quiescent 0.0288 s then against 0.0280 s now,
  `FB256_match` 0.0340 against 0.0330. Same host, same operating point.
- **Not a failed manipulation.** 24--28 MiB of huge pages in every repetition.
- **Not the estimator.** The spread comparator reproduces to 1% relative
  (5.90% against 5.95%). Only the runtime statistic moved, which is what makes
  the dissociation interpretable at all.
- **Not excluded: time of day.** The campaign ran late at night and this run
  in the afternoon on a host with other logged-in users. Nothing here tests
  that, and it is the most obvious remaining candidate for what varies the
  outlier rate.

## What this licenses, and the one thing it conspicuously does not

Licensed:

1. **No hugepage re-run.** The pass branch failed on absolute thresholds.
2. **A5.1 clause 4 is not yet triggered.** The instability may not be reported
   as physical, because the diagnostic that would have said so is void.
3. `tools/thp_arena.c` and the `VICTIM_PRELOAD` plumbing are available for any
   future page-backing question, with a working per-invocation proof of effect.

**Not licensed, and deliberately not taken: a plain re-run of the AMD
campaign.** The temptation is obvious and should be written down rather than
acted on. If today's un-manipulated control runs at 4.28% where the campaign ran
at 13.10%, a straight repetition of the AMD arms might clear the CoV bar and
hand back the +0.263 de-confound that outcome 5 voided.

A5.2 forecloses it in terms: *"Anything between -> no conclusion, **and no
re-run**."* This run is at best that branch. And §6.6 describes precisely this
move -- re-running until the dispersion cooperates, with the target number
already known, is selection, not replication. The +0.263 is known. A re-run
chosen because a pilot suggested the bar would clear is a re-run selected on its
outcome.

What would make it legitimate is a pre-registration written before it: a fixed
repetition count chosen in advance, a declared rule for outlier repetitions
written before any are seen, and the result reported whether or not the bar
clears. That is a decision about whether the AMD de-confound exists, so it is
put to the lead rather than taken here.

## Provenance

- `artifacts/join_thpctl_moscxl.jsonl` -- 20 records, control block
- `artifacts/join_thp_moscxl.jsonl` -- 20 records, hugepage block
- `artifacts/a52_ctl_moscxl.log`, `artifacts/a52_thp_moscxl.log` -- run logs
- `tools/thp_arena.c` -- the shim; `run_join_campaign.py` `VICTIM_PRELOAD`
- `summarize_thp.py` -- the decision rule, written before the data was readable
- `DUCKDB_JOIN_A52_RUN_DECISIONS.md` -- estimators and validity conditions,
  committed before the measurement

Reproduce with `python3 summarize_thp.py artifacts/join_thpctl_moscxl.jsonl
artifacts/join_thp_moscxl.jsonl`.
