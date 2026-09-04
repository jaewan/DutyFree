# Closed: the real-join campaign reached a certified verdict, wrote it into its own pre-registration, and was superseded before anyone lifted it out

Date: 2026-09-04. **No new compute**: committed archives read only, nothing
written under `gem5/logs/`, nothing launched, no rebuild.

Pre-registration: `H2H_REALJOIN_PREREG_2026-09-01.md` (24 KB; four addenda, one
five-part amendment, and two embedded outcome sections).
Archive: `data/gem5/rj3_runs.jsonl` — **66/66 `completed=true`**, 22 arms × 3 seeds.
Analyzers: `analyze_realjoin_frontier.py`, `analyze_realjoin_wedge.py`.
Regression pin: `tests/test_dutyfree.py::TestRealJoinArchiveReproduces`.

**Disposition: SUPERSEDED**, by `COMPLETE_JOIN_OUTCOME_2026-09-01.md` (campaign
r5), with one **deferred** residual described below (addendum 4 / P7).

**No paper claim depends on this campaign.** Verified in §"Paper dependency".

## Why this record exists

The campaign is not unrun and not unjudged. It ran four generations, the last of
which completed 66/66 and was certified by a committed analyzer. Three things
hid that:

1. **The verdict was written into the pre-registration itself.** Two sections of
   `H2H_REALJOIN_PREREG_2026-09-01.md` — "Outcome of the superseded 51" and
   "Final outcome at 66/66" — are outcome documents living inside a `*_PREREG_*`
   file. `INDEX.md`'s own reading guide splits those roles ("`*_PREREG_*`:
   thresholds and action-on-miss, committed **before** the data existed"), so a
   reader scanning for `H2H_REALJOIN_OUTCOME_*` finds nothing and concludes
   nothing was measured.
2. **`INDEX.md` says so, and is wrong.** Line 111 groups
   `H2H_REALJOIN_PREREG` with four others as "registered and unlaunched, or
   launched and not yet judged." This one was launched *and* judged. Handback
   wording below.
3. **It was overtaken four days later by a campaign with a better instrument**,
   which took over the paper figure, so nobody needed r3's numbers again.

For the record, and contrary to report, the pre-registration *is* mentioned in
`INDEX.md` — but only in that "no outcome exists yet" list, and it has no row in
the curated table. The file is untracked in git; so are 42 other `experiments/asplos/*.md`
from 2026-08-31 onward, so that is the repo's general state, not this campaign's.

## What was registered, and how four addenda moved it

A pre-registration with four addenda has a history, and here the history is the
point: **the addenda are three successive apparatus repairs, not a change of
question.** Each was registered blind, and each was forced by a defect that would
have biased the result in the paper's own favour.

| # | registered | what changed | fate |
|---|---|---|---|
| body | 2026-09-01 | The wedge on a real hash join rather than `fused.c`. Victim `2650 3000000`, tenant `cxl_join_bench --mode single`, arms `qui`/`wb`/`cat4`/`cat10`/`h2`, 3 seeds = 15 runs. **P1** wedge ≥ 8% at matched protection (all arms ≥ 85%, within 5 pp); **P2** WB tax ≥ 1.30×; **P3** h2 within ±3% of wb; **P4** direction vs the fused +17.1%, exploratory | — | superseded by add. 2 |
| add. 1 | same day, with **0 of 15 runs finished** | The way-mask frontier: 12 widths × 3 seeds = 36 runs. **P5** dominance — no width matches H2 on both axes; **P6** monotonicity as an apparatus check. Registered because a single operating point cannot answer "why not just use CAT?" for every CAT tuning | **scope expansion**; the frontier becomes the primary instrument | **this is the one that survived** |
| add. 2 | after `qui` only (carries no wedge information) | Corrected tenant lifetime. The join *terminates* and front-loads setup, so STREAMING was inactive for the first ~20–26M cycles **and the setup share was arm-dependent** — both pushing CAT to look better-protecting and costlier, which is the shape of the paper's own claim | supersedes the body's sizing; the 51 runs already in flight are kept as a quantification of the confound | superseded by add. 3 |
| add. 3 | before any metric-B arm produced a number | Setup excluded by a **tenant-side stats reset** rather than diluted by a longer window; victim metric becomes `cyc_per_load`; victim raised to `2650 12000000`; new gate **A6** on `victim_loads` | add. 2 was not enough — setup measured at ~79% of tenant work, ~87% of a 6e6 window | **executed as campaign r3** |
| add. 4 | before any r4 arm produced a number | Phase-aligned fused reference (campaign r4): `fused.c` gains `argv[4]` warmup passes so the *tenant's* reset lands last in both workloads. **P7**: with `warm=25`, fused `victim_loads` falls into the real-join band | repairs the withdrawal in A1.3 rather than working around it | **never ran** |

`Amendment 1` then records five corrections made **after data existed** — a
run-name parser that made analysis impossible (A1.1), a gate cap that rejected
the two arms the campaign exists to measure (A1.2), the withdrawal of a
fused-vs-real "4.2×" ratio (A1.3), a gate that was unimplementable by
construction (A1.4), and a suppression rule for mismatched windows (A1.5). Each
is stated with whether it could have favoured the paper. That disclosure is the
document working as intended.

**So the addenda do not record the campaign being overtaken, and they do not
narrow its scope.** They record it being repaired three times and then answered.
What overtook it came from outside: `COMPLETE_JOIN_PREREG_2026-09-01.md`,
registered the same day as addendum 4.

## What ran

Four generations. The analyzers' run-name pattern still accepts all three
executed prefixes (`r(?:j|[0-9])_`), which is the surviving trace of the first two.

| gen | design | runs | outcome |
|---|---|--:|---|
| `rj_` | body + add. 1 | 51 | Completed. **Void by its own gate**: WB tax **1.0060×** against a registered 1.30× floor. The tenant retired 20.9M instructions against a setup cost of 43.4M — it never reached `declare_streaming()` and never executed one join pass. `h2` and `wb` agree to 0.005%. Recorded in the prereg rather than discarded |
| `r2_` | add. 2 | 66 | **Stopped, not reported.** Setup measured at ~79% of tenant work; widening the window could not fix a confound that large |
| `r3_` | add. 3 (metric B) | **66** | **Completed 66/66 and certified.** Archived as `data/gem5/rj3_runs.jsonl` |
| `r4_` | add. 4 | **0** | Never launched. No archive, no `/tmp` remnant, no committed runner |

The void of the 51 is worth keeping visible: had its gates been trusted it would
have supported *"way partitioning protects the victim by 72–80%; STREAMING
provides none (0.76%); the fused wedge does not reproduce on a real hash join"* —
thesis-destroying, and entirely an artifact of tenant lifetime and phase
alignment. The registered P2 floor caught it.

## The verdict r3 reached

From "Final outcome at 66/66" in the pre-registration, independently pinned by
`TestRealJoinArchiveReproduces` against the committed archive:

    reference  quiet 33.890 | wb 44.628 (tax 1.3168x, tenant IPC 0.3604)
    STREAMING  victim 42.040, protection 24.11%, tenant IPC 0.3814

| prediction | verdict |
|---|---|
| **P5** dominance (primary instrument) | **PASS** — no way width matches H2 on both axes, 12 widths tested |
| **P2** WB tax ≥ 1.30× | **PASS** — 1.3168× |
| **P6a** w=20 reproduces `wb` | **PASS** — to +0.000% on victim and IPC |
| **P6b** protection monotone in width | **FAIL, and not an apparatus fault** — non-monotone, rising to w=8 then falling, because way-starvation at narrow masks raises tenant miss traffic more than occupancy costs. Registered as a pure apparatus check; that framing was too narrow and was corrected |
| **P6c** tenant IPC monotone in width | **PASS** |
| **P1** wedge ≥ 8% at matched protection | **REFUTED on its precondition** — protection 24.11–95.33%, not matched within 5 pp |
| **P3** h2 within ±3% of `wb` | **REFUTED in the paper's favour** — H2 leaves the tenant **+5.82% faster** than unprotected |
| **P7** phase-aligned fused reference | **NEVER TESTED** — see below |

**Wedge at equal-or-better protection: +11.76%.** The cheapest CAT width
protecting ≥ H2's 24.11% is w=16 (24.84%), costing the tenant −5.32%; STREAMING
costs +5.82%. The `+33.52%` printed beside P1 is not a wedge and must not be
quoted: it compares `h2` against `cat10`, which protects ~4× better.

## Why it is being closed, and the disposition

**Superseded by `COMPLETE_JOIN_OUTCOME_2026-09-01.md` (r5).** r5 asks r3's
question — does object scope move the protection/cost frontier for a real hash
join — with a strictly better instrument on three axes r3 itself named as
limitations:

| | r3 | r5 |
|---|---|---|
| tenant lifetime | `--reps 100`, truncated by the victim's `m5_exit` | `--reps 1`, **complete** pass; tenant emits JSON and exits |
| tenant metric | **IPC** (a proxy) | **`join_mtuples_per_s`** (application units) |
| table/LLC | 0.80 | **0.533**, matched to silicon's 32/60 MiB |
| P1-style matched-protection precondition | required ≥ 85%, which the campaign could not satisfy | dropped by design — H2's ceiling is the quantity the geometry exists to move |

The two agree on the substance, which is why supersession is the right word and
not retraction: r3 measured R = 24.11% with a +11.76% wedge; r5 measured
R = 22.59% with a +9.97% wedge (+8.42% interpolated to matched protection).
`COMPLETE_JOIN_OUTCOME` compares itself against r3 explicitly and concludes that
growing the HNF from 5 to 7.5 MiB **did not** raise H2's ceiling — "the
comparability defect in r3 is real; it is not why H2 recovers only ~23%."

`INDEX.md`'s "Start here" already names r5 as the official model cell, and
`make_eval_frontiers.py` builds `fig:frontier`(a) from `r5_runs.jsonl`. The
supersession is a fact of the repo; this record states it.

### Deferred residual: campaign r4 and P7

One registered item is genuinely unanswered, and it is deferred rather than
closed:

- The **source change exists**: `gem5/testcase/dutyfree/fused.c` carries the
  `argv[4]` warmup-pass parameter with a comment citing amendment A1.3, and `0`
  reproduces the previous behaviour exactly.
- **No runner was committed, no r4 arm ever ran**, and no r4 archive exists.

Consequence, which should be treated as standing: **A1.3's withdrawal of the
fused-vs-real ratio is permanent until P7 is tested.** The fused arms' measured
window (`victim_loads` = 12,001,060, the victim's own reset landing last) and the
real-join arms' (10.8e6, the tenant's reset landing last) are 9.9% apart, so any
statement of the form "a synthetic stream pollutes N× harder than a real join" is
unsupported. `analyze_realjoin_frontier.py` enforces the suppression (A1.5) and
`TestRealJoinArchiveReproduces::test_fused_and_realjoin_windows_differ` pins the
reason. **I confirmed no such ratio appears in the paper.**

What it is waiting on: nothing external. r4 is ~15 runs of already-built
apparatus. It was not run because r5 made the fused-vs-real comparison
unnecessary to the argument — the paper's boundary claim is now carried by
`fig:recovery`, which compares fused table sizes *against each other* rather than
against the join.

## Paper dependency: none

Checked directly against `/home/domin/STREAMING_Paper/ASPLOS27/Text/`, not
assumed.

- **No r3 number appears in the paper.** Searched for `24.11`, `11.76`, `1.3168`,
  `33.52`, `0.3814`, and the words `IPC` and `truncated`: **zero matches in any
  `.tex` file.** The one `1.64` hit is `1.648×` in an unrelated appendix
  cross-core slowdown table.
- **Every frontier number in `Sec7_Evaluation.tex` is r5's**: 22.6% recovery,
  +5.35% vs unprotected, +9.97% against the cheapest sufficient mask, +8.42%
  interpolated (the value carried in the abstract and introduction).
- **No paper artifact reads `rj3_runs.jsonl`.** The only file in either tree that
  touches it is `tests/test_dutyfree.py`, which pins it as a regression guard.
- The `1.64×` r3-IPC-vs-silicon-tuples/s calibration that
  `COMPLETE_JOIN_OUTCOME` addendum 1 says to keep "labelled as such" is **not in
  the paper**, so nothing needs to be done about it.

So closing this campaign is bookkeeping, not a problem. The archive stays
committed and pinned because it is the only measurement of this tenant at
table/LLC = 0.80, and `COMPLETE_JOIN_OUTCOME` uses that contrast to argue that
geometry is not what caps H2's recovery.

## What would be required to complete it

Two separate things, neither urgent:

1. **To close P7 / r4** (~15 runs, no rebuild — the `fused.c` warmup parameter is
   already in the tree): commit a runner that passes `warm=25` to the fused arms,
   run 5 arms × 3 seeds under r3's metric-B apparatus, and check that fused
   `victim_loads` lands below 0.97 × 12e6 and inside the real-join band. Only
   then may a fused-vs-real ratio be quoted. **Do not** run this to obtain a
   headline; it repairs a withdrawn comparison that the paper does not currently
   make.
2. **To make r3 quotable as a paper cell** — nothing measurement-side; it is
   certified and pinned. It would need its verdict lifted out of the
   pre-registration into a normal `*_OUTCOME_*` document, since the current
   arrangement puts post-hoc analysis corrections inside a file whose suffix
   promises they were committed beforehand. That is a filing task, and this
   record is the pointer in the meantime.

Neither is a reason to keep the campaign open.
