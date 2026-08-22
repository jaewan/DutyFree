# A5.3: `PREFETCHNTA` allocates under competition, and the mechanism as stated is wrong

`moscxl` (EPYC 9754, Zen4c), 2026-08-22. Implements `A5.3` of
`DUCKDB_JOIN_CORUN_PREREGISTRATION.md`, whose threshold was fixed before the
measurement. Two arms x 10 repetitions, `MODE=nta`, `QUERIES=301`, N = 100000,
the same operating point and the same frozen host as the AMD co-run campaign.
All 20 arms valid.

## The declared result

A5.3 asked one question: A4.1 concluded `wb_prefetchnta` allocates on Zen4c
from a sweep run **with no victim present**, and an idle cache fills to
capacity under any insertion policy, so that sweep could not distinguish a
stream inserted at MRU from one inserted at LRU. Only occupancy under
competition can.

| arm | GB/s | victim s | victim L3 occ | **streamer L3 occ** | % of CCX | CoV_rep |
|---|---:|---:|---:|---:|---:|---:|
| `WB_sat` | 24.27 | 0.2590 | 0.30 MiB | 15.69 MiB | 98.0% | 0.37% |
| `NTA_sat` | 24.52 | 0.1615 | 2.05 MiB | **13.88 MiB** | **86.7%** | 2.22% |

NTA streamer occupancy as a fraction of `wb_load`'s, rep-paired percentile
bootstrap, B = 20000: **0.884, 95% CI [0.880, 0.889]**. Per-repetition ratios
span 0.877 to 0.893. The declared threshold was 0.50 and nothing in this
artifact comes near it.

Both arms sit inside the 5% CoV bar, so unlike the rest of the AMD campaign
this measurement is not governed by outcome 5. The victim runs **1.604x
[1.587, 1.621]** faster under NTA at 1.0% *more* streamer bandwidth.

Per A5.3, reported in the words fixed in advance:

> A4.1's premise holds under competition. NTA allocates and recovered anyway.
> **The mechanism as stated is wrong**, this is a serious negative for the
> paper.

`PREFETCHNTA` holds 86.7% of the shared cache -- 13.88 MiB of a 16 MiB CCX --
and is by no honest reading a non-allocating arm. It nonetheless recovered
+2.897 [+2.845, +2.992] of `WB_sat`'s 8.175x tax in the main campaign, 40% of
the excess, at equal cores and equal bandwidth. A streamer that allocates
almost as much as `wb_load` does most of what non-allocation was supposed to
do. Harm is therefore not a function of whether the streamer allocates, which
is how this project has been stating it.

## A4.1 was right about what it measured and wrong about what it meant

Unplanned, and the cleanest thing in the artifact. Every invocation carries its
own victimless reading: the sampler's first sample is taken while the victim is
still starting up and its last after the queries have finished, with the
streamer running at steady state throughout both. So A4.1's measurement is
reproduced inside every repetition of this run, beside the competed one.

| arm | streamer, victim absent | streamer, victim competing | **yield** | 95% CI |
|---|---:|---:|---:|---|
| `WB_sat` | 15.89 MiB | 15.69 MiB | **0.21 MiB** | [0.13, 0.23] |
| `NTA_sat` | 15.84 MiB | 13.85 MiB | **2.02 MiB** | [1.91, 2.09] |

With no victim the two streamers are indistinguishable at 15.84 and 15.89 MiB,
which is A4.1's 15.99/16.00 reproduced to within a rounding difference. **A4.1
measured correctly.** Put a victim in the cache and `wb_load` gives up 0.21 MiB
while NTA gives up 2.02 -- a tenfold asymmetry that is invisible by
construction to any victimless sweep, because both streamers fill an idle cache
to capacity.

This is the failure mode A5.3 was written to test, and it is confirmed. The
inference "occupancy is 100%, therefore the arm allocates, therefore it is a
negative control" was wrong at the third step, not the first.

## The reverse-causation reading dies on the sign

The obvious objection: the NTA victim runs 1.6x faster, so perhaps it simply
demands harder and takes the cache, and the streamer's lower occupancy is the
consequence rather than the cause.

That reading predicts the arm with the higher victim demand holds the most
cache. The artifact says the opposite:

| arm | victim DRAM traffic during measured queries | victim L3 occ |
|---|---:|---:|
| `WB_sat` | **0.75 GB/s** | 0.30 MiB |
| `NTA_sat` | 0.31 GB/s | 2.05 MiB |

The `WB_sat` victim drives **2.5x more** DRAM traffic and retains **6.8x
less** cache. The arm whose victim pushes hardest is the arm whose streamer
yields least. The sign is wrong for reverse causation, and it is wrong by a
wide margin rather than marginally, so the asymmetry is a property of the
streamer's insertion, not of the victim's demand rate.

## What the mechanism appears to be instead

Post-hoc; the verdict above is fixed by the declared threshold and does not
depend on this section.

The victim's reused set is `R(N) = 40N` = 3.81 MiB. Zen's L3 is a victim cache,
so victim L2 and victim L3 contents are disjoint and may be added -- the
private-L2 discipline section 5.2 requires, applied here in the direction it
actually matters:

| arm | victim L3 | + private L2 | of R = 3.81 MiB | resident |
|---|---:|---:|---:|---:|
| `WB_sat` | 0.30 MiB | <= 1.30 MiB | 3.81 MiB | **<= 34%** |
| `NTA_sat` | 2.05 MiB | <= 3.05 MiB | 3.81 MiB | **<= 80%** |

The CCX is saturated in both arms -- streamer plus victim sums to ~16 MiB
either way -- so this is a pure partition question. Near saturation the last
12 points of streamer occupancy are the victim's entire working set, and the
transition from 34% to 80% resident is worth 1.6x in runtime. That is the
whole effect.

So the operative variable is **insertion priority in a cache both streamers
fill**, not allocation versus bypass. This artifact cannot separate the two
mechanisms that would produce it -- lines inserted at LRU, or lines allocated
normally and demoted early -- because both yield under pressure and neither is
distinguishable from a stock measurement. The distinction matters for what
hardware is implied, and it is left open.

## What this costs the paper, stated plainly

1. **The five-link chain's L2/L3 are mis-stated, not merely mis-worded.** They
   route harm through whether the streamer allocates. Here two streamers whose
   occupancy differs by 11 points, both filling ~90%+ of the cache, differ by
   2.9x in the tax they impose. A binary allocation predicate does not predict
   the harm on this microarchitecture.
2. **L5 is directly threatened on AMD.** `PREFETCHNTA` is a deployed,
   unprivileged, single-instruction hint. On this host it recovered 40% of the
   excess tax with no OS involvement, no page-granular declaration, no object
   scoping and no enforcement. It does not *occupy* the corner the paper
   claims is empty -- it is per-instruction rather than per-object, unenforced,
   and vendor-divergent -- but it substantially erodes the magnitude argument
   for why that corner is worth occupying. **Whether and how to restate L5 is a
   section 9 lead-only decision and is not taken here.**
3. **A4.1's consequence still stands, for its own reason.** `NTA_sat` and
   `NTA_lo` remain arms that yield no verdict as recovery results on AMD,
   because an arm holding 86.7% of the cache cannot be reported as
   non-allocating. What changes is that they are no longer a *negative
   control*: the mechanism's prediction that they would not recover was wrong,
   and that is the finding.

## What it does not do

**It does not convert into a positive result**, as A5.3 declared in advance.
The AMD de-confound remains governed by outcome 5 and by A5.1: the primary
matched pair still fails the CoV bar and there is still no AMD verdict. Nothing
here rescues it, and the recovery reported above is not a de-confound because
its two arms are not an allocating/non-allocating contrast -- they are two
allocating arms with different insertion behaviour.

## The threshold was miscalibrated, and that is my drafting error

A5.3 set the line at 50%, framed as "does NTA allocate at all." The informative
range turned out to be 86 against 98 percent, and the entire result lives in an
11-point difference the threshold was far too coarse to express. Had NTA come
in at 60% the declared rule would have returned the same branch and the same
words, while meaning something quite different.

The rule is not being reinterpreted after the fact -- the branch that fired is
the branch the numbers select, and its conclusion is correct. But the threshold
was chosen to discriminate 0 from 100 when it should have been chosen to
discriminate *yield under pressure*, which is the quantity that matters and
which I did not name until after seeing the series. A5.4's threshold is set on
the same statistic and inherits the same weakness; it is stated there.

## The same blind spot is unmeasured on Intel

Nothing in the criticism A5.3 levelled at A4.1 was AMD-specific. `mos181`'s
streamer occupancy was never measured under co-run either, so the project's
headline de-confound -- +0.058 and +0.093, the abstract's central result --
rests on an arm that has never been shown to be non-allocating while anything
was competing with it. Intel's indirect evidence (the hint costs 28--41%
bandwidth there; victim occupancy is 126 MiB against 67) is consistent with a
hint being honoured, and equally consistent with a streamer that allocates and
yields, which is what Zen4c does. Pre-registered as **A5.4** and running.

## Provenance

- `artifacts/join_nta_moscxl.jsonl` -- 20 records, this measurement
- `artifacts/nta_moscxl.log` -- runner log
- `summarize_nta.py` -- declared decision rule, threshold 0.50, B = 20000,
  seed 20260822; the yield decomposition below the rule is marked post-hoc
- `run_join_campaign.py` -- streamer-side sampler on the aggressor's own
  monitoring group; `agg_group/cpus_list` is cores 9-15 and `group/cpus_list`
  is cpu8, disjoint, no SMT siblings recruited

Reproduce with `python3 summarize_nta.py artifacts/join_nta_moscxl.jsonl`.
