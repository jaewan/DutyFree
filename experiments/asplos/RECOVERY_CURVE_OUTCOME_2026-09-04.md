# Outcome: recovery is bounded by the declared range's share of shared-cache fills

Dated 2026-09-04. No new compute: re-analysis of committed archives.
Figure: `make_recovery_curve.py` -> `figures/recovery_curve.pdf` (paper `fig:recovery`).

## The question

The paper reports H2 recovering **89%** of a neighbour's charge in one
experiment and **22.4%** in its headline frontier. Presented as two numbers
that is an inconsistency, and it is the paper's most exploitable seam. This
asks whether one variable explains both.

## Axis that does NOT work, and was already refuted in-repo

`table/LLC`. `COMPLETE_JOIN_OUTCOME_2026-09-01.md` tested it: r3 at
table/LLC=0.80 gave R=24.11%, r5 at 0.53 gave R=22.59%, while fused.c at 0.80
gives R=82.33%. Growing the HNF 5 -> 7.5 MiB did not raise the ceiling. The
tenant, not the geometry, sets R. That axis is not used.

## Axis that works

**The fraction of shared-cache fills the declared range accounts for**,
measured as the reduction in home-node line allocations when the range is
declared: `(sum(m_allocsByWay) under wb - under h2) / under wb`.

Fused tenant, 5 MiB HNF / 2 MiB L2 / 2650 KiB neighbour chase, n=3 per point
(`data/gem5/{kn,kb}_runs.jsonl`, quiescent arm from `fh_runs.jsonl`):

| table | wb tax | R(h2) | R(cat4) | tenant vs wb, h2 | tenant vs wb, cat4 | declared share |
|---|--:|--:|--:|--:|--:|--:|
| 2.0 MB | 1.4679 | 89.44% | 89.26% | +4.14% | −15.84% | 98.95% |
| 2.5 MB | 1.5012 | 87.69% | 88.20% | +7.07% | −23.54% | 97.43% |
| 3.0 MB | 1.5141 | 84.51% | 87.79% | +11.92% | −23.17% | 89.80% |
| 3.5 MB | 1.5186 | 81.95% | 87.45% | +12.03% | −24.22% | 83.76% |
| 4.0 MB | 1.5100 | 82.33% | 87.26% | +7.81% | −19.28% | 81.37% |
| 6.0 MB | 1.5223 | 67.14% | 86.25% | +11.38% | −18.95% | 71.73% |
| 8.0 MB | 1.5477 | 56.84% | 86.31% | +10.42% | −22.09% | 65.23% |

Every cell reproduces `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` to 0.01.

**Held-out test.** The complete join (`data/gem5/r5_runs.jsonl`, a different
tenant, different HNF size, different victim ratio, played no part in
establishing the relation):

| | declared share | R measured |
|---|--:|--:|
| complete join, r5 | **32.32%** | **22.59%** |

It lands on the relation. Recovery sits at or just below the declared share in
**7 of 8** points; the exception is table=4.0 MB, which exceeds it by 0.96 pp
(that table size is also a mild outlier in the sweep's own wb tax, 1.5100
against 1.5186 at 3.5 MB, so the excess is inside run-to-run spread).

## Why this is the mechanism, not a curve fit

`W1.4_CHARGE_DECOMPOSITION_2026-08-24.md` shows the same thing from the other
side. H2 returns the neighbour's shared-cache residency: at an infinite SF it
lifts the LLC demand hit rate 20.8% -> 43.7% and removes 90.9% of the per-miss
excess; under a finite SF the hit rate is 0.17%, there is no residency left to
defend, and H2 removes 0.5%. Recovery is bounded by how much displaced
residency the declared object is responsible for. Nothing else is the type's to
remove.

No regression is quoted. The claim is a ceiling that recovery tracks, not a
slope. A least-squares fit over the fused range (65-99%) extrapolates to 31.8%
at share=32.3% against 22.6% measured, i.e. the fit does not transfer; the
ceiling statement does.

## Deliberately not on the figure

- **FS r6e.** R is ~100% at a 69.4% declared share, which breaks the ceiling.
  Its counters are whole-run rather than ROI-scoped (guest-OS traffic is in the
  denominator) and its `qui` arm is n=1 with R reported as 101.92%, so the
  point is not commensurable with the SE arms. Excluded and stated.
- **Bypass-counter numerator.** The fused build predates
  `streamingHnfFillBypasses` (it reads 0 in those runs). In r5, where both
  exist, differencing gives 32.3% and the bypass counter 17.4%; differencing
  also captures the secondary fills H2 removes, which is what the victim
  experiences. Differencing is used throughout, and said so in the caption.
- **Tenant metric.** Panels (a)/(b) use L2 misses per kilocycle, this kernel's
  progress proxy, not the completed-tuple throughput of `fig:frontier`(a).
  Labelled in the caption; the two are not mixed.

## Paper edits made

- `Sec7_Evaluation.tex`: the 22.4% headline now carries its explanation at
  first statement; the one-sentence "separate modeled sensitivity" is replaced
  by the curve, the wedge, and the mechanism; `fig:recovery` added as a
  `figure*`. Page count 21 -> 22.

---

# Addendum 1 — 2026-09-04: post-hoc status audited; the held-out test is metric-dependent; the r6e exclusion is sound but was reasoned from the wrong defect

Audit of this document against its own artifacts, prompted by the observation
that it is the one recent case where a paper figure rests on a post-hoc
relation. **Nothing in the body is retracted.** Every number above reproduces
exactly (see §"Reproduction" below). What changes is the strength the relation
is allowed to carry in the paper, the disclosure attached to it, and the
*stated reason* for excluding FS r6e. No new compute; committed archives and
`gem5/logs/fs_restore_chi/` read only, nothing written, nothing launched.

## Reproduction

All seven fused rows, the wb tax column, the held-out complete-join point and
the r6e share were recomputed independently from
`data/gem5/{kn,kb,fh,r5}_runs.jsonl` and the r6e `stats.txt` files. Every value
matches the body to the digits printed there: 89.44/87.69/84.51/81.95/82.33/
67.14/56.84 for `R(h2)`, 98.95/97.43/89.80/83.76/81.37/71.73/65.23 for share,
32.32% and 22.59% for the complete join, and 69.37% for r6e.

**Point selection is clean, and this is worth recording because it is the first
thing a reviewer will suspect.** `kn_runs.jsonl` and `kb_runs.jsonl` contain
exactly 63 records covering 7 table sizes x 3 arms x 3 seeds. Every record has
`completed: true`. **No point in the sweep was dropped, and there is no table
size in either archive that the figure omits.** The seven fused points are the
whole of a registered sweep (`FUSED_TABLESWEEP_PREREG_2026-08-29.md`); what is
post-hoc is the *choice of x-axis*, not the selection of data.

## The held-out test is weaker than the body presents it, in two specific ways

The body says the complete join "played no part in establishing the relation"
and "lands on the relation." Both are literally true, and neither is the whole
picture.

**1. The target value was known in advance.** `r5`'s `R = 22.59%` is the
paper's own headline and is the explicit motivation stated in §"The question"
("why 89% in one experiment and 22.4% in the headline"). So the quantity the
test had to predict was not blind: only the *share* (32.32%) was newly
computed. This is a one-degree-of-freedom check that the share lands above a
known recovery, not a blind prediction of an unknown outcome.

**2. Its verdict depends on which share metric is used, and the alternative
metric fails it.** Recomputed from `r5_runs.jsonl`:

| share definition | value | vs `R = 22.59%` |
|---|--:|---|
| differencing allocations `(wb-h2)/wb` | **32.32%** | ceiling holds, 9.7 pp slack |
| `hnf_streaming_bypasses / wb allocs` | **17.43%** | **ceiling violated by 5.2 pp** |
| `hnf_streaming_bypasses / (h2 allocs + bypasses)` | **20.48%** | **ceiling violated by 2.1 pp** |

The body records the 17.4% figure and its justification, and that
justification is **sound and forced, not chosen**: the key
`hnf_streaming_bypasses` is *absent entirely* from every fused record (verified
— it is not zero, it is not present), so differencing is the only definition
that exists across all eight points. Differencing is also the quantity the
victim experiences, since it captures the refills H2 prevents and the bypass
counter does not. But the honest statement is that **the single external test
of this relation is metric-dependent, the metric was fixed by an unavoidable
constraint rather than by a pre-registration, and the constraint became visible
only after the alternative was computed.** That is a real researcher degree of
freedom, it is now disclosed in the paper caption, and it should not be
described again as the relation being "confirmed" by a held-out instrument.

## What the relation can and cannot carry

In its favour, and this is not nothing: **there is no fitted parameter.** The
line in panel (c) is `y = x`, not a regression. The body already declines to
quote a least-squares fit and shows that one does not transfer (31.8%
extrapolated against 22.6% measured). The reviewer objection this document was
written to anticipate — "a curve fitted to eight points" — therefore misfires
on its own terms: nothing was fitted, and a one-sided bound with zero free
parameters is a far weaker thing to ask eight points to support than a slope.
The mechanism is independently corroborated from the other side by
`W1.4_CHARGE_DECOMPOSITION_2026-08-24.md`.

Against it: the axis was identified after the data existed; the sole external
point is metric-dependent as above; and the one commensurable-looking third
tenant (r6e) violates the bound and is excluded.

**Licensed:** recovery is bounded by the declared range's share of shared-cache
fills, as a bound these measurements exhibit and a mechanism they share.
**Not licensed:** "two tenants, a 3x range of declared share, and one relation"
— the phrasing the paper carried, which presents a two-tenant post-hoc bound as
an established law.

## The r6e exclusion is correct, but the stated reason does not do the work

The body excludes r6e because "its counters are whole-run rather than
ROI-scoped (guest-OS traffic is in the denominator)" and its `qui` arm is n=1.
The first reason is real but **points the wrong way**, and on its own would
argue for *including* the point after a correction rather than excluding it.

Share is `(W - H)/W`. Contamination common to both arms cancels in the
numerator and inflates the denominator, so whole-run counters **understate**
the share. Removing common traffic `C` gives `(W - H)/(W - C)`, which is
strictly larger. The measured 69.37% is therefore a *floor* on the ROI-scoped
share, and correcting the defect moves r6e **toward** the ceiling, not away.

That correction cannot succeed, for a reason that needs no new measurement:

- `share = (W - H)/W <= 100%` for any `H >= 0`, with equality only if the
  declared arm allocates **nothing** at the home node.
- r6e's `R` is **101.92%**, reported by `FS_COMPLETE_JOIN_OUTCOME_2026-09-04.md`
  as "R ~= 100%".
- So `R <= share` requires `H ~= 0` over the ROI. That is impossible here: the
  tenant's own 4 MiB table and the victim's 6 MiB line-granular chase are
  **undeclared**, and both must allocate at the HNF.

Quantitatively, from the r6e `stats.txt` files (HNF slices 0 and 1,
`m_allocsByWay`): `wb` mean 1,667,374 over three seeds, `h2` mean 510,797 over
two, giving 69.37%. Even subtracting from **both** arms an amount equal to the
*entire* quiet arm's home-node allocation traffic (325,238 — a deliberately
generous over-estimate of everything that is not the tenant's stream or table)
lifts the share only to **86.1%**, still ~14 pp below `R ~= 100%` and ~16 pp
below the 101.92% actually measured. **No ROI scoping brings r6e onto the
curve.**

**The reason r6e is off the curve is the second one, and it should be stated
first: `R > 100%` is not an admissible value.** A mechanism that can only
decline fills belonging to the declared range cannot leave the neighbour
*faster* than it runs with no stream present at all. `FS_COMPLETE_JOIN_OUTCOME`
says so itself ("Do NOT quote 101.92%") and attributes the overshoot to the
n=1 quiescent baseline. Two further non-commensurabilities compound it, both
already recorded in `FS_COMPLETE_JOIN_PREREG_2026-09-02.md`: the victim does
**different amounts of work** across the arms being compared (1,200,000 loads
in `qui` against 1,994,240 in `h2`, windows 116.9M against 193.6M cycles,
ratio 1.66x), which addendum 3 item 2 of that pre-registration identifies as
biasing exactly this comparison; and the ROI section's teardown is present in
`wb`/`h2` and absent in `qui`, so the contamination is not even common across
the three arms.

### An ROI-scoped recomputation is not possible from existing artifacts

Checked directly rather than assumed. Each r6e `stats.txt` contains **exactly
two** statistics sections, and the counters are **cumulative** — section 2
minus section 1 is only ~0.5e9 ticks (~0.5 ms) and a few thousand HNF
allocations in every arm, against section 1's ~109e9 ticks. Section 1 already
runs from the ROI reset **through the teardown** to the rcS's `m5 dumpstats`;
section 2 is the trailing dump at exit. There is **no counter snapshot at the
true end of the ROI**, so the teardown cannot be subtracted from anything.

This is precisely the defect `FS_COMPLETE_JOIN_PREREG_2026-09-02.md` addendum 5
item 3 records and addendum 6 leaves under "Still deferred, and it needs a
rebuild": `run_fs_e2e_join` calls `gem5_reset_stats_now()` but never
`gem5_dump_stats_now()`. Fixing it requires a source change, a rebuild, a
re-derivation of `BYPASS_COVERAGE_MIN`, and new runs — and addendum 7 of that
pre-registration closed the campaign ("no r6f, no r7"). **The recomputation
would need new simulations, and it would not change the conclusion anyway,
per the bound above.**

## Superseded wording

The paper text carried, and no longer carries:

> The complete join of \cref{fig:frontier}(a) is a different tenant that was
> not used to establish the relation, and it lands on it: its declared range is
> 32.3% of the fills, and it recovers 22.6%. **Two tenants, a $3\times$ range
> of declared share, and one relation.**

Replaced by:

> The complete join of \cref{fig:frontier}(a) is a different tenant and is
> consistent with the same bound: its declared range is 32.3% of the fills, and
> it recovers 22.6%. **We report this as a bound these measurements exhibit and
> a mechanism they share, not as a fitted law.**

The `fig:recovery` caption carried, and no longer carries:

> The complete-join tenant of \cref{fig:frontier}(a) **played no part in
> establishing the relation and lands on it**, which is why its headline
> protection is 22.4\% rather than 89\%: only 32\% of its shared-cache fills
> carry the declared type.

Replaced by:

> The complete-join tenant of \cref{fig:frontier}(a) **is consistent with the
> same bound**, which is why its headline protection is 22.4\% rather than
> 89\%: only 32\% of its shared-cache fills carry the declared type.
> **Panels~(a) and~(b) report a registered sweep; panel~(c)'s axis was chosen
> afterwards and nothing is fitted---the line is $y{=}x$. Share is by
> differencing allocations, the only definition the fused build supports; the
> later fill-bypass counter, which sees declined fills but not the refills they
> prevent, puts the complete join at 17.4\%.**

`Sec7_Evaluation.tex` compiles at **22 pages**, unchanged, with the overfull-box
count unchanged from before the edit (7, none of them in `Sec7`).

## What this addendum does not change

- the relation, the mechanism, or any of the eight plotted points;
- the decision to publish `fig:recovery`, which stands;
- the exclusion of r6e, which stands on a corrected reason;
- panels (a) and (b), which rest on a registered sweep and are untouched by
  anything here.

---

# Addendum 2 — 2026-09-04: panels (a)/(b) cite the wrong pre-registration, two of their seven points are registered nowhere, and the "run-to-run spread" excuse for the 4.0 MB point is wrong by an order of magnitude

Written in response to `FUSED_KNEE_CLOSED_2026-09-04.md` §"Provenance
discrepancy to route", which flagged the citation defect and correctly declined
to act on it. **No new compute**: committed archives read only, nothing written
under `gem5/logs/`, nothing launched, no rebuild. Reproduction script:
`analyze_registered_scope.py`.

**This is a registration-scope and attribution problem, not a data-integrity
one.** All 63 fused runs carry `completed=true` and `reason=ok`, every record
self-reports a `realized_table_mb` equal to its requested size, no point was
dropped, no table size in either archive is omitted from the figure, and every
value in the body table above and in Addendum 1's reproduction re-derives
exactly today. Nothing here suggests any number is wrong. What is wrong is the
claim about *which of them were registered in advance*, and the strength the
paper draws from the two that were not.

Addendum 1's last line — "panels (a) and (b), which rest on a registered sweep
and are untouched by anything here" — is the sentence this addendum retracts.

## Superseded wording

Addendum 1 §"Reproduction" carried, and no longer carries:

> The seven fused points are the whole of a registered sweep
> (`FUSED_TABLESWEEP_PREREG_2026-08-29.md`); what is post-hoc is the *choice of
> x-axis*, not the selection of data.

Replaced by:

> The five points from 2.0 to 4.0 MB are the whole of the sweep registered in
> `FUSED_KNEE_PREREG_2026-08-29.md` (45 runs, `run_fused_knee.sh`, `kn_*`); the
> 6.0 and 8.0 MB points are an unregistered extension (18 runs,
> `run_fused_knee_big.sh`, `kb_*`) that appears in no pre-registration's
> design. What is post-hoc is the choice of x-axis *and* the top two sizes of
> the x-range; what is not post-hoc is the selection of data, since all 63 runs
> completed and none was dropped.

And Addendum 1 §"What this addendum does not change" carried, and no longer
carries:

> panels (a) and (b), which rest on a registered sweep and are untouched by
> anything here.

Replaced by:

> panels (a) and (b), whose five registered sizes are untouched by anything
> here; their 6.0 and 8.0 MB points are unregistered and are addressed in
> Addendum 2.

## The correct citation, and why the old one is worse than it looks

`FUSED_TABLESWEEP_PREREG_2026-08-29.md` is the wrong record on three
independent grounds, not one:

1. **Its design does not contain three of the five plotted registered sizes.**
   It registers tables {1, 2, 4, 6} MB plus a reused 3 MB point. 2.5 and 3.5 MB
   — the two intermediate sizes that exist precisely because the knee campaign
   added them — are not in it, and neither is 8.0.
2. **None of its runs is plotted.** Its executed sweep is `ts_runs.jsonl`, 45
   records at the aliased power-of-two probe stride, superseded by
   `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` and not comparable to the
   plotted runs.
3. **It never produced a distinct measurement at 6 MB at all.** This is new and
   was not visible in the discrepancy as routed. In `ts_runs.jsonl` the `t6.0`
   and `t4.0` cells are **bit-identical in all nine arm × seed pairs** — same
   `simTicks`, same `cyc_per_access` to every printed digit, giving the same
   51.92% recovery and the same 1.5848 `wb` tax. 36 of its 45 records carry a
   null `realized_table_mb`, so nothing in the archive contradicts the natural
   reading: `fused.c`'s pre-fix table-size rounding quantized 6 MB down onto
   4 MB, which is the fourth of the five power-of-two pathologies the correction
   document enumerates. A duplicated harvest of one run directory cannot be
   excluded from the archive alone, since the `/tmp/ts_*` trees are gone; both
   readings have the same consequence, which is that **the pre-fix sweep has
   four distinct table sizes, not five.**

   Worth recording against that pre-registration's own text: its liveness
   assertion 3 anticipated exactly this — "a sweep that silently ran one size
   four times would produce a flat curve and look like a finding" — and
   required each size to be read back from the run's own `cmd=` line. In
   execution the read-back is null in 80% of records and the assertion did not
   hold. (Its `*_PREREG_*.md` is frozen and is not edited; this belongs in the
   index.)

So citing it as the registration that covers 6.0 MB credits a registration
whose only execution at that size was a copy of another size. The honest
attribution, which is also `FUSED_KNEE_CLOSED`'s:

| plotted size | registered in | plotted runs |
|---|---|---|
| 2.0, 2.5, 3.0, 3.5, 4.0 MB | **`FUSED_KNEE_PREREG_2026-08-29.md`**, exactly its design | `kn_*`, `run_fused_knee.sh`, 45 runs |
| 6.0 MB | **no design.** `FUSED_TABLESWEEP_PREREG` names the size but produced no distinct run at it, and named 6 MB as the point it "explicitly [does] NOT predict" | `kb_*`, `run_fused_knee_big.sh` |
| 8.0 MB | **no pre-registration, anywhere** | `kb_*`, `run_fused_knee_big.sh` |

`run_fused_knee_big.sh` carries `FUSED_KNEE_PREREG`'s header verbatim by
copy-paste, which is how an 18-run extension came to look like part of a 45-run
registered design.

## What the registered range actually shows

Recomputed per seed, which the figure script does not do — the question "is a
7 pp decline across five sizes a trend?" cannot be answered from means. Both
decompositions in `analyze_registered_scope.py` (each seed against its own `wb`
baseline; and the arm's seeds against the fixed mean `wb` tax, i.e. exactly the
plotted quantity) agree to two decimals.

**The seed spread is very small.** Pooled within-size SD is **0.075 pp** for
`R(h2)` and **0.062 pp** for `R(cat4)` over the five registered sizes, and at no
registered size do the three seeds span more than **0.22 pp**.

| | registered 2.0–4.0 MB | published 2.0–8.0 MB |
|---|---|---|
| `R(h2)` | 89.44% → 82.33%, **7.11 pp** | 89.44% → 56.84%, **32.60 pp** |
| `R(h2)` OLS slope | **−3.99 pp/MB** (SE 0.33), t(13) = −11.9, R² = 0.92 | −5.59 pp/MB, t(19) = −37.7, R² = 0.99 |
| `R(cat4)` | 89.26% → 87.26%, **1.99 pp** | 89.26% → 86.31%, 2.95 pp |
| `R(cat4)` OLS slope | **−0.95 pp/MB** (SE 0.09), t(13) = −10.2, R² = 0.89 | −0.44 pp/MB, t(19) = −8.6, R² = 0.80 |

**A trend exists in the registered range and it is not close.** The 7.11 pp
decline is **95×** the pooled within-size SD; 2.0 against 4.0 MB is a 7.11 pp
difference at a standard error of 0.09 pp. Nothing about this range is
noise-limited, and the small seed spread is what makes a 7 pp decline
interpretable at n=3.

**The non-monotonicity at the top is also real, not noise.** 3.5 MB (81.95%)
sits **below** 4.0 MB (82.33%). Per seed, 3.5 MB gives {81.93, 81.97, 81.94} and
4.0 MB gives {82.42, 82.20, 82.37} — **no overlap**, in either decomposition.
The reversal reproduces in every seed and is ~5σ. So the registered curve is
not "a decline with a wobble"; it is a decline over 2.0–3.5 MB that has
**stopped declining** by 4.0 MB. `PAPER_RECONCILIATION_2026-09-04.md` row 63
already removed "monotonically" from the paper on the strength of the means;
the per-seed data is stronger than that row needed and the word must not come
back.

**What that costs the boundary argument.** The registered range establishes the
*direction* and the *mechanism* and does **not** reach a boundary. At the top of
the registered range \textsc{Streaming} still recovers **82.33%** of the
neighbour's charge — that is strong protection, not a place where object scope
stops helping — and the decline has flattened rather than accelerated. The
sentence the campaign was built to license ("the paper needs to state which
regime it is claiming") is **not** licensable from the registered sweep: within
2.0–4.0 MB the paper is in one regime throughout. The two unregistered sizes
supply **78.2%** of the published 32.60 pp decline; the registered range supplies
**21.8%**.

## The CAT comparison on the same basis

Over the registered range `R(cat4)` runs **89.26% → 87.26%**, i.e. the range is
**87–89%**, not 86–89%; the 86% floor comes only from 6.0 and 8.0 MB.

**"Flat" is not defensible on either basis.** CAT's registered decline is
1.99 pp, monotone across all five sizes, at a pooled within-size SD of
0.062 pp — **32×** the spread, t(13) = −10.2. It is a shallow decline measured
far outside noise, not flatness. On the published range it declines 2.95 pp and
is itself non-monotonic at the top (86.25% at 6.0, 86.31% at 8.0). The
comparison that survives is a **ratio of slopes**: −3.99 against −0.95 pp/MB,
so \textsc{Streaming}'s protection declines about **four times as fast** as the
mask's over the registered range. The mask's protection advantage grows from
**−0.19 pp at 2.0 MB** (\textsc{Streaming} is very slightly *ahead*) to
**+4.93 pp at 4.0 MB**, reaching +29.47 pp only at the unregistered 8.0 MB point.

**Panel (b) needs no narrowing at all, and this is the load-bearing finding for
the paper.** Every quantitative range in the surrounding paragraph other than
the recovery endpoint has **both** of its endpoints at a registered size, with
the 6.0 and 8.0 MB points falling strictly inside:

| published range | min at | max at | registered range |
|---|---|---|---|
| mask charges the tenant 15.8–24.2% | 2.0 MB | 3.5 MB | **identical** |
| \textsc{Streaming} leaves the tenant 4.1–12.0% faster | 2.0 MB | 3.5 MB | **identical** |
| the wedge is 20–36 pp at every point | 2.0 MB | 3.5 MB | **identical** |

So the paragraph's actual argument — that the mask buys flat protection out of
the tenant while the label charges nothing — is carried in full by the 45
registered runs. Only the recovery endpoint, and the word "flat", have to move.

## The 4.0 MB excess over the `y=x` bound is not "run-to-run spread"

Found while computing the per-seed spread; it corrects this document's body and
a clause of the paper caption, and it is independent of the registration
question.

The body §"Axis that works" carried, and no longer carries:

> the exception is table=4.0 MB, which exceeds it by 0.96 pp (that table size is
> also a mild outlier in the sweep's own wb tax, 1.5100 against 1.5186 at
> 3.5 MB, so the excess is inside run-to-run spread).

Replaced by:

> the exception is table=4.0 MB, which exceeds it by 0.96 pp. That excess is
> **not** run-to-run spread: it reproduces in all three seeds individually
> (+1.041, +0.863, +0.984 pp) at a seed SD of 0.091 pp, so it is ~10σ. The
> 4.0 MB cell's low `wb` tax (1.5100 against 1.5186 at 3.5 MB) is likewise
> systematic, not spread — 19× that cell's own seed SD, Welch t = +18.7 — so it
> cannot be invoked as a source of noise, and if it is the cause then the cause
> is a real property of that configuration. The bound is therefore violated at
> one of eight points by a small, reproducible margin, and is reported as a
> bound these measurements *nearly* exhibit rather than one they satisfy.

Recomputed at every size, `R − share` per seed:

| table | per-seed `R − share` (pp) | mean | SD | \|mean\|/SD |
|---|---|--:|--:|--:|
| 2.0 | −9.605, −9.407, −9.513 | −9.509 | 0.099 | 96× |
| 2.5 | −9.720, −9.730, −9.769 | −9.740 | 0.026 | 376× |
| 3.0 | −5.281, −5.369, −5.213 | −5.288 | 0.078 | 68× |
| 3.5 | −1.829, −1.791, −1.810 | −1.810 | 0.019 | 96× |
| **4.0** | **+1.041, +0.863, +0.984** | **+0.963** | **0.091** | **11×** |
| 6.0 | −4.537, −4.673, −4.580 | −4.597 | 0.070 | 66× |
| 8.0 | −8.290, −8.550, −8.335 | −8.391 | 0.139 | 61× |

This does **not** overturn the relation, and it makes the case *against* the
strong reading that Addendum 1 already withdrew. A one-sided bound with zero
free parameters that is exceeded at one of eight points by ~1 pp is still a
bound worth reporting; describing the exception as noise when it is 10σ is not.
The paper caption's clause "inside the sweep's own run-to-run spread" carries
the same defect and is routed below.

## The pre-fix 90.6% → 51.9% collapse was substantially an index artifact

`FUSED_KNEE_PREREG` line 8 motivates the whole campaign with a prior
observation of recovery falling "90.6% -> 51.9% between a 2 MB and a 4 MB tenant
table". Both figures reproduce exactly from `ts_runs.jsonl` today (90.61%,
51.92%). Against the post-fix runs at the same two sizes:

| | pre-fix (aliased stride) | post-fix | moved |
|---|--:|--:|--:|
| `R(h2)`, 2.0 MB | 90.61% | 89.44% | **1.17 pp** |
| `R(h2)`, 4.0 MB | 51.92% | 82.33% | **30.41 pp** |
| decline over 2.0 → 4.0 MB | **38.69 pp** | **7.11 pp** | — |

**81.6% of the original decline over that interval was the aliased index.**
`FUSED_KNEE_PREREG` §"Design" registered precisely this diagnostic in advance —
"the new 2 MB and 4 MB points should reproduce the old ones closely, and any
large deviation is the code change, not the table size" — and it discriminated:
the 2 MB anchor reproduced within 1.2 pp while the 4 MB anchor moved 30 pp. By
the pre-registration's own stated criterion the 4 MB deviation is attributed to
the code change. The artifact grew with table size, so it inflated the *slope*
rather than shifting the level, which is why re-running the anchors was the
right call and why the intermediate points could not have been compared against
the old ones.

**Only the magnitude is affected; the mechanism claim the paper now makes is
not.** Two mechanism claims must be kept apart:

- The **whole-table** account (model A) — that the 16 MB stream evicts the
  entire table from L2 continuously so the whole table competes for the LLC —
  was asserted in `FUSED_TABLESWEEP_PREREG`, registered as the primary
  prediction of `FUSED_KNEE_PREREG` (`R(h2, 2.5 MB) < 80%`, `> 85%` refutes),
  and **refuted at 87.69%**. It is already withdrawn. It was refuted at a
  discriminator chosen in advance, on post-fix data, at a size inside the
  registered range — so the refutation owes nothing to the artifact and nothing
  to the unregistered points.
- The **declared-share ceiling** — this document's relation — was established
  entirely on post-fix data and is corroborated from the other side by
  `W1.4_CHARGE_DECOMPOSITION_2026-08-24.md`. The artifact does not touch it.

What the artifact history *does* establish is that **the dramatic decline has
relocated twice**: once from the aliased index (38.69 pp over 2–4 MB becomes
7.11 pp) and once onto table sizes no pre-registration covers (7.11 pp over the
registered range becomes 32.60 pp only by extending to 8 MB). On registered,
post-fix data the decline has never been dramatic. That is the reason to narrow
the claim rather than to look for a framing that keeps it: the strong form of
the claim has, on each occasion, been supported by data that later turned out
not to support it.

This is **not** a suggestion that the 6.0 and 8.0 MB points are artifacts. They
are post-fix, their realized sizes are self-reported and correct, all 18 runs
completed, and their values reproduce. They are good measurements at
unregistered sizes.

## What the figure licenses

**Licensed by the 45 registered runs (2.0–4.0 MB):**

- \textsc{Streaming}'s protection of the neighbour declines as the tenant's own
  hot table grows — direction established at ~95× the seed spread;
- the decline is **7.1 pp** over a 2× range of table size (89.4% → 82.3%), it
  is concentrated in 2.0–3.5 MB, and it has stopped by 4.0 MB;
- a four-way CAT mask declines too, by **2.0 pp**, i.e. about **four times more
  slowly**, and its protection advantage over \textsc{Streaming} grows from
  nothing at 2.0 MB to ~5 pp at 4.0 MB;
- the mask charges the tenant **15.8–24.2%** and \textsc{Streaming} charges
  nothing (**4.1–12.0% faster**), with the wedge **20–36 pp** at every size —
  all three ranges complete, both endpoints registered;
- recovery tracks the declared range's share of shared-cache fills across the
  range (share 98.95% → 81.37% against recovery 89.44% → 82.33%), exceeding it
  at one size by 0.96 pp;
- the whole-table mechanism is refuted, at a registered discriminator.

**Not licensed by the registered runs:**

- "falls to 56.8%" — needs 8.0 MB, which no pre-registration covers;
- any located boundary, knee or regime change, and any phrasing on which object
  scope "stops helping" within the registered range: at its top end recovery is
  still 82.3% and flattening;
- CAT as **flat**, or the range **86–89%**;
- the sweep as a registered design spanning 2–8 MB.

**Licensed as exploratory, clearly labelled:** the 6.0 and 8.0 MB extension,
reported as an unregistered extension of a registered sweep, showing that the
decline resumes and steepens past 4 MB (67.14%, 56.84%) while the mask holds
86–87%. This is the same treatment Addendum 1 gave panel (c)'s post-hoc axis —
publish the data, disclose the status in the caption, and let the registered
part carry the claim — and it is adequate here for the reason it was adequate
there: the defect is in what was promised in advance, not in what was measured.
Dropping the two points would be the wrong correction. Neither is a reason to
hold the figure.

## Routed to the paper, not applied here

`Sec7_Evaluation.tex` is owned by another worker and was **not edited**. Two
sites, both quoted verbatim with recommended replacements, plus one defect found
in passing.

**1. `fig:recovery` caption, the registered-sweep clause.** Replace

> fills carry the declared type.  Panels~(a) and~(b) report a registered sweep;
> panel~(c)'s axis was chosen afterwards and nothing is fitted---the line is
> $y{=}x$.

with

> fills carry the declared type.  In panels~(a) and~(b) the five table sizes
> from 2.0 to 4.0~MB were registered before the runs ($45$ runs) and are what
> the text quantifies; the 6.0 and 8.0~MB points are an unregistered
> exploratory extension ($18$ runs).  All $63$ runs completed, none was
> dropped, and each reports the table size it actually ran.  Panel~(c)'s axis
> was chosen afterwards and nothing is fitted---the line is $y{=}x$.

**2. `fig:recovery` caption, the run-to-run-spread clause** (§"The 4.0 MB
excess" above; independent of registration scope). Replace

> Recovery tracks that fraction and does not
> materially exceed it---one of the eight points sits 1.0~pp above the line,
> inside the sweep's own run-to-run spread.

with

> Recovery tracks that fraction and does not
> materially exceed it---one of the eight points sits 1.0~pp above the line, a
> small excess that reproduces across seeds rather than a scatter effect.

**3. The claim in §"The tenant's own footprint".** Replace

> quantitative rather than anecdotal.  Sweeping a fused tenant's own hot table
> from 2 to 8~MB against a fixed 5~MiB shared cache ($n{=}3$ per point), the
> neighbour's recovery under \textsc{Streaming} falls from
> 89.4% to 56.8%, while a four-way CAT mask holds a flat 86--89%.  Read alone,

with

> quantitative rather than anecdotal.  Sweeping a fused tenant's own hot table
> against a fixed 5~MiB shared cache ($n{=}3$ per point), the neighbour's
> recovery under \textsc{Streaming} falls from 89.4\% to 82.0\% between 2.0 and
> 3.5~MB and falls no further by 4.0~MB (82.3\%), across the five sizes
> registered in advance; a four-way CAT mask declines about four times more
> slowly over the same range, 89.3\% to 87.3\%.  Seed-to-seed spread is below
> 0.25~pp at every registered size, so both declines are far outside run-to-run
> noise and so is the difference between them.  An unregistered extension to
> 6.0 and 8.0~MB shows the decline resuming and steepening, to 56.8\% against
> the mask's 86--87\%; we report it as exploratory and rest the claim on the
> registered range.  Read alone,

Three notes for whoever applies this. The paragraph's remaining figures —
15.8--24.2\%, 4.1--12.0\%, 20--36 percentage points — are **fully carried by the
registered five sizes** and need no change; that is the finding, not a
concession. The replacement drops "from 2 to 8~MB" from the opening clause
because the caption now states the range and its scope. And the word "flat" is
withdrawn for CAT wherever it appears in this paragraph: line 272's "the mask
buys its flat protection" should read "its far flatter protection".

**Found in passing, and material: the claim under review does not currently
render.** `Sec7_Evaluation.tex` uses **unescaped `%`** in body text at 20+
lines, including all four numbers in this paragraph. LaTeX treats each as a
comment, so `main.pdf` (rebuilt two minutes after the current source, so it does
reflect it) prints:

> the neighbour's recovery under Streaming falls from 89.4that is a weakness.

The 56.8\% endpoint, the CAT contrast and the "Read alone" clause are all
commented out, and the same defect truncates "15.8--24.2whereas",
"4.1--12.0points", "22.65.35reason", "32.3generates", "9.97mask" and
"8.42introduction" elsewhere in the section. The `fig:recovery` caption is
**not** affected — it uses `\%` correctly and renders in full. This compiles
without error and without an overfull box, which is why the 22-page count
recorded in Addendum 1 §"Superseded wording" did not catch it. It is an escaping
regression, not a scope or provenance problem, and it is not this document's to
fix; but the narrowing recommended above should be applied to a paragraph whose
percent signs are escaped, or the narrowed claim will not render either. The
replacements above use `\%` throughout.

## Handed back — index and ledger wording

`INDEX.md` and `A1_PROVENANCE_LEDGER_2026-08-28.md` were **not edited**, per the
standing split. `FUSED_TABLESWEEP_PREREG_2026-08-29.md` and
`FUSED_KNEE_PREREG_2026-08-29.md` were not edited; they are frozen.

**Rebased on the state of both documents as of 00:44 today**, because they were
edited concurrently while this analysis ran and the attribution half of it has
already landed independently. Specifically: `INDEX.md` line 93 now carries a
`FUSED_KNEE_PREREG` row naming it "the registration behind `fig:recovery` panels
(a) and (b)"; the ledger has a new `fig:recovery` row (**VERIFIED — 63/63**)
which explicitly declines to certify the attribution; and ledger **`F15`** logs
the attribution defect **open**, with the note that "a separate worker is
analyzing what the headline claim should be narrowed to". That narrowing is what
this addendum supplies. So the handback below **adds to** that work rather than
restating it, and the two items it would have duplicated — a `FUSED_KNEE_PREREG`
index row and a `fig:recovery` ledger row — are **withdrawn as already done**.

**For the ledger, to close `F15`** — it is open pending exactly this:

> **Resolved 2026-09-04 by `RECOVERY_CURVE_OUTCOME_2026-09-04.md` add. 2, which
> supplies the narrowing this row was held open for.** Restricted to
> `FUSED_KNEE_PREREG`'s five registered sizes the claim is **89.4% → 82.3%, a
> 7.11 pp decline**, against 32.60 pp over the published range: the two
> unregistered sizes supply **78.2%** of the published decline. The decline over
> the registered range is real and not noise-limited — pooled within-size SD
> **0.075 pp**, so 7.11 pp is **95×** the spread, OLS slope −3.99 pp/MB,
> t(13) = −11.9 — but it **does not reach a boundary**: at the top of the
> registered range recovery is still 82.3% and has stopped falling (3.5 MB at
> 81.95% sits *below* 4.0 MB at 82.33%, non-overlapping across all three seeds,
> ~5σ). `R(cat4)` over the same range is **87–89%**, not the "flat 86–89%" the
> paper carries, and declines 1.99 pp monotonically at 32× its own spread; the
> surviving contrast is a **ratio of slopes**, −3.99 against −0.95 pp/MB.
> **Panel (b) needs no narrowing**: 15.8–24.2%, 4.1–12.0% and the 20–36 pp wedge
> each have **both** endpoints at a registered size (2.0 and 3.5 MB), with 6.0
> and 8.0 MB strictly inside, so the paragraph's argument survives intact.
> One correction to this row's own account of `FUSED_TABLESWEEP_PREREG`: it
> produced **no distinct measurement at 6 MB at all** — its `t6.0` cells are
> **bit-identical to its `t4.0` cells in all nine arm × seed pairs** — so its
> executed sweep has four distinct sizes, not five, and it registers no plotted
> size that `FUSED_KNEE_PREREG` does not register better. Recommended paper
> wording for both sites is in add. 2 §"Routed to the paper"; `F15` closes on
> that wording being applied, not on this row.

**For `INDEX.md`, "Withdrawn during 2026-09-03→04"** — two rows. The attribution
withdrawal is not among them: ledger `F15` and the new `FUSED_KNEE_PREREG` index
row already carry it. These two are new findings:

> | **`R(cat4)` as "flat"** across the fused sweep — in `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` §"What survives", `RECOVERY_CURVE_OUTCOME_2026-09-04.md`, and `Sec7_Evaluation.tex` | `RECOVERY_CURVE_OUTCOME_2026-09-04.md` add. 2 | CAT declines **1.99 pp monotonically** across the five registered sizes at a pooled within-size SD of **0.062 pp** — 32× the spread, t(13) = −10.2 — and 2.95 pp across all seven, non-monotonically (86.25% at 6.0, 86.31% at 8.0). It is a shallow decline measured far outside noise, not flatness. **The comparison that survives is a ratio of slopes**: −3.99 against −0.95 pp/MB over the registered range, so \textsc{Streaming}'s protection declines about **four times as fast** as the mask's. The mask's advantage grows from **−0.19 pp at 2.0 MB** to **+4.93 pp at 4.0 MB**, reaching +29.47 pp only at the unregistered 8.0 MB point |
> | **"the excess is inside run-to-run spread"** as the account of the 4.0 MB point exceeding the `y = x` bound — in `RECOVERY_CURVE_OUTCOME_2026-09-04.md` §"Axis that works" and, as "inside the sweep's own run-to-run spread", in the `fig:recovery` caption | `RECOVERY_CURVE_OUTCOME_2026-09-04.md` add. 2 | the excess is **~10σ**, not spread: `R − share` at 4.0 MB is **+1.041, +0.863, +0.984 pp** per seed at a seed SD of 0.091 pp, positive in every seed. The 4.0 MB cell's low `wb` tax invoked as its cause (1.5100 against 1.5186 at 3.5 MB) is itself **19×** that cell's seed SD, Welch t = +18.7 — systematic, so it cannot supply noise. **The relation is not overturned and Addendum 1's withdrawal of the strong reading already covers it**: a zero-parameter one-sided bound exceeded at one of eight points by ~1 pp is still worth reporting; calling a 10σ exception noise is not. Report as a bound these measurements *nearly* exhibit |

**For `INDEX.md`, curated table — amend the `RECOVERY_CURVE_OUTCOME_2026-09-04.md` row.** Its
present text asserts "**Point selection is verified clean** — 63 records, 7 table
sizes x 3 arms x 3 seeds, every record `completed: true`, no point dropped and no
table size omitted; what is post-hoc is the choice of x-axis, not the selection
of data." That is all true and should stay. Append:

> **`AMENDED` again by add. 2** — point selection is clean but **registration
> scope is not**: only the five sizes 2.0–4.0 MB are registered
> (`FUSED_KNEE_PREREG`, not `FUSED_TABLESWEEP_PREREG` as add. 1 states), and
> 6.0/8.0 MB are an unregistered extension supplying **78.2%** of the published
> decline. Narrowed, the claim is 89.4% → 82.3% (7.1 pp) with CAT at 87–89%;
> "flat" is withdrawn for CAT and the 4.0 MB excess over `y = x` is **10σ**, not
> run-to-run spread. Panel (b)'s three ranges (15.8–24.2%, 4.1–12.0%, 20–36 pp)
> are **carried in full by the registered sweep** — both endpoints of each fall
> at 2.0 or 3.5 MB — so the paragraph's argument survives narrowing intact.

**For `INDEX.md`, `FUSED_TABLESWEEP_PREREG_2026-08-29.md`'s row** — the
pre-registration is frozen and was not edited, so this belongs in the index:

> Its **liveness assertion 3 did not hold in execution.** The assertion required
> each run's table size to be read back from its own `cmd=` line and warned in
> terms that "a sweep that silently ran one size four times would produce a flat
> curve and look like a finding". In `ts_runs.jsonl`, **36 of 45 records carry a
> null `realized_table_mb`** and the `t6.0` cells are **bit-identical to the
> `t4.0` cells in all nine arm × seed pairs**, consistent with `fused.c`'s
> pre-fix table-size rounding quantizing 6 MB onto 4 MB. A duplicated harvest
> cannot be excluded, since `/tmp/ts_*` is gone; either way **the executed sweep
> has four distinct table sizes, not five**, and it registers no size the current
> figure plots that `FUSED_KNEE_PREREG` does not register better. This is the
> `F9` family and it is the failure `FUSED_KNEE_PREREG`'s assertion 2 was written
> to stop — that one **passed**, in all 63 records.

**For the existing `fig:recovery` ledger row** — no new row is needed; it landed
today and verifies 63/63. One sentence to append to its "recomputed" cell, since
the per-seed decomposition is what licenses reading its `R(h2)` column as a
trend:

> Per-seed spread added by `analyze_registered_scope.py`: pooled within-size SD
> **0.075 pp** for `R(h2)` and **0.062 pp** for `R(cat4)` over the five
> registered sizes, no size's three seeds spanning more than 0.22 pp. The
> 3.5/4.0 MB reversal is therefore a property of the curve, not scatter — the
> two triples do not overlap.

**Withdrawn as already done.** Two items this analysis would otherwise have
handed back are now redundant and are **not** re-proposed: a curated
`FUSED_KNEE_PREREG_2026-08-29.md` row for `INDEX.md` (added today at line 93,
and it already names the document as the registration behind panels (a) and (b))
and a `fig:recovery` row for the ledger (added today, **VERIFIED — 63/63**,
correctly declining to certify the attribution and pointing at `F15`).

**For `PAPER_RECONCILIATION_2026-09-04.md` §3.6** (owned by another worker; not
edited) — two rows, and an amendment to its row 63:

> | 63a | `Sec7:271` | recovery "falls from 89.4% to 56.8%" attributed to a sweep the caption calls registered | `RECOVERY_CURVE_OUTCOME_2026-09-04` add. 2: only 2.0–4.0 MB is registered; narrowed the decline is **7.1 pp**, to 82.3% | **X** |
> | 63b | `Sec7:271` | "a four-way CAT mask holds a **flat** 86--89%" | same: CAT declines 1.99 pp monotonically over the registered range at 32× the seed spread, and its registered range is **87–89%** | **X** |
> | 66a | `fig:recovery` caption | "one of the eight points sits 1.0 pp above the line, **inside the sweep's own run-to-run spread**" | same §"The 4.0 MB excess": the excess is ~10σ and positive in every seed | **X** |

Row 63 of that document ("falls **monotonically**", already applied) should also
carry that the per-seed data is stronger than the means it cited: 3.5 MB
{81.93, 81.97, 81.94} against 4.0 MB {82.42, 82.20, 82.37} do **not overlap**,
so the reversal is a ~5σ property of the curve and "monotonically" must not
return.

Separately, that document's **U-list** should gain the unescaped-`%` defect
described above; it is a rendering fault across 20+ lines of
`Sec7_Evaluation.tex`, it silently deletes four numbers from this paragraph
alone, and it is invisible to a page-count or overfull-box check.

## What this addendum does not change

- any of the 63 runs, any plotted point, or any value in the body table — every
  one re-derives exactly;
- the relation, the mechanism, or panel (c)'s `y = x` line;
- the decision to publish `fig:recovery`, which stands, with all seven points;
- the exclusion of r6e, and Addendum 1's corrected reason for it;
- the withdrawal of the whole-table mechanism, which was refuted on a
  registered discriminator inside the registered range and owes nothing to
  either the artifact or the unregistered points.
