# Closed: the knee campaign ran in full, and its verdict was published under another document's name

Date: 2026-09-04. **No new compute**: committed archives read only, nothing
written under `gem5/logs/`, nothing launched, no rebuild.

Pre-registration: `FUSED_KNEE_PREREG_2026-08-29.md`.
Runners: `run_fused_knee.sh` (2.0–4.0 MB), `run_fused_knee_big.sh` (6.0, 8.0 MB).
Archives: `data/gem5/kn_runs.jsonl` (45 records), `data/gem5/kb_runs.jsonl` (18).
Verdict record: `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md`.

**Disposition: ANSWERED ELSEWHERE.** The campaign executed completely, its
registered prediction was judged, and the judgement is published. What never
existed is a document carrying this campaign's name.

## Why this record exists

This pre-registration has looked open since 2026-08-29, and three things made it
look that way at once:

1. No `FUSED_KNEE_OUTCOME_*` was ever written. Its verdict went into
   `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md`, a document named after the
   probe-stride defect rather than after the campaign that measured it.
2. `INDEX.md` does not mention `FUSED_KNEE_PREREG` **at all** — not in the
   curated table, not in the "no outcome exists yet" list, nowhere. It is the
   only one of the open pre-registrations in that condition.
3. Its runs went to `/tmp/kn_*` and `/tmp/kb_*` rather than to `gem5/logs/`, so
   the usual place a reader looks for evidence of execution is empty.

None of that is a missing result. The result is load-bearing in the paper right
now (§"Paper dependency" below).

## What was registered

The 2026-08-29 table sweep found H2's recovery falling 90.6% → 51.9% between a
2 MB and a 4 MB tenant table while a four-way mask stayed flat, and could not say
*where*, because `fused.c` quantized the table to powers of two. With that
restriction removed, the knee pre-registration asked which of two mechanisms
governs the collapse:

| model | what competes for the LLC | predicted knee |
|---|---|---|
| **A — whole-table** | the entire table, continuously evicted from L2 by the 16 MB stream | **2.41 MB** |
| **B — spill-only** | only `table − L2` | **4.41 MB** |

2.5 MB discriminates. **Registered prediction: model A** — `R(h2)` at a 2.5 MB
table is **< 80%**; **> 85% refutes model A** and forces withdrawal of the
mechanism account stated in `FUSED_TABLESWEEP_PREREG` and repeated in its
outcome; 80–85% is inconclusive.

Secondary, registered: `R(cat4)` flat at 85–90% across all five sizes;
`cost(cat4)` ≥ 15% wherever protection is matched; `cost(h2)` ≤ 3% (one-sided).

Design: tables **2.0, 2.5, 3.0, 3.5, 4.0 MB** × arms `wb`, `h2`, `cat4` × 3
seeds = **45 runs**, with the 2.0 and 4.0 anchors deliberately re-run rather than
reused, so that the index change could not be confounded with the table size.

What it would have licensed: a statement of which regime the paper is claiming.
Left of the knee a page-scoped label and a way mask protect equally and only the
label is free; right of it, only the mask works. The paper needs to say which.

## What ran

Everything, plus an unregistered extension.

| batch | runner | sizes | runs | `completed` | archive |
|---|---|---|--:|---|---|
| knee | `run_fused_knee.sh` | 2.0, 2.5, 3.0, 3.5, 4.0 | 45 | 45/45 `ok` | `kn_runs.jsonl` |
| knee-big | `run_fused_knee_big.sh` | 6.0, 8.0 | 18 | 18/18 `ok` | `kb_runs.jsonl` |

The 6.0 and 8.0 MB batch is **not in this pre-registration's design** (it
registered five sizes, 2.0–4.0). `run_fused_knee_big.sh` carries this
pre-registration's header verbatim by copy-paste. See §"Provenance discrepancy".

### Liveness assertions, checked today against the archives

| # | assertion | result |
|---|---|---|
| 1 | all runs reach `Exiting @ tick`; dead runs reported, not dropped | **PASS** — 63/63 `completed=true`, `reason=ok`; none dropped |
| 2 | realized table size read from each run's own log line, not the directory name | **PASS** — `realized_table_mb` non-null in all 63 records, covering exactly {2.0, 2.5, 3.0, 3.5, 4.0, 6.0, 8.0} |
| 3 | arm identity from each run's own `config.ini` | **PASS** — `hnf_policy=LRURP` and `fwd_unique=false` throughout; `hnf_requestor_masks` is `0 0 0 0 0 15` on every `cat4` and empty on every `wb`/`h2` |
| 4 | tenant L2 misses non-zero; `streamingAccesses` > 0 on `h2` only | **PARTIAL** — misses non-zero in all 63, and `declared_streaming` is true on every `h2` and false on every other arm. The **positive counter does not exist in this build**: `hnf_streaming_bypasses` is absent from every fused record (absent, not zero). Engagement rests on the declaration flag, not on a counter |

Assertion 2 is worth naming as a pass. It is the `F9` failure this campaign was
built to stop repeating, and it is the reason these archives can be re-analysed
today at all — every record self-reports the size it actually ran.

Assertion 4's shortfall is the same weakness `H2H_REALJOIN_PREREG` records as its
`A5b` lesson: positive proof of engagement should come from a bypass counter,
never from a marker or flag that a code path may or may not emit. The fused build
predates that counter. This does not touch the verdict — the arms separate by
25–33 pp on the victim — but it means the fused arms cannot supply
counter-based engagement evidence, and it is why panel (c) of `fig:recovery` must
compute declared share by differencing allocations.

## The verdict

Recomputed today from `kn_runs.jsonl` + `kb_runs.jsonl`, with the quiescent
denominator from `fh_runs.jsonl` (`fh_qui`, n=3, 33.8814 cyc/access).
`R = (wb − arm) / (wb − qui)`; tenant column is L2 misses per kilocycle.

| table | `wb` tax | `R(h2)` | `R(cat4)` | h2 tenant vs wb | cat4 tenant vs wb |
|---|--:|--:|--:|--:|--:|
| 2.0 MB | 1.4679 | 89.44% | 89.26% | **+4.14%** | −15.84% |
| 2.5 MB | 1.5012 | **87.69%** | 88.20% | **+7.07%** | −23.54% |
| 3.0 MB | 1.5141 | 84.51% | 87.79% | **+11.92%** | −23.17% |
| 3.5 MB | 1.5186 | 81.95% | 87.45% | **+12.03%** | −24.22% |
| 4.0 MB | 1.5100 | 82.33% | 87.26% | **+7.81%** | −19.28% |
| 6.0 MB | 1.5223 | 67.14% | 86.25% | **+11.38%** | −18.95% |
| 8.0 MB | 1.5477 | 56.84% | 86.31% | **+10.42%** | −22.09% |

Every cell reproduces `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` and
`RECOVERY_CURVE_OUTCOME_2026-09-04.md` to the digits printed there.

| registered prediction | threshold | measured | verdict |
|---|---|---|---|
| **primary — model A (whole-table)** | `R(h2, 2.5 MB)` < 80%; > 85% refutes | **87.69%** | **REFUTED.** Model A withdrawn |
| `R(cat4)` flat | 85–90% at all five registered sizes | 87.26–89.26% | **HOLDS** |
| `cost(cat4)` where protection matched | ≥ 15% | 15.84–24.22% | **HOLDS** |
| `cost(h2)` | ≤ 3%, one-sided | no cost at any size; the tenant is 4.14–12.03% **faster** | **HOLDS** |

**And the question itself did not survive.** Recovery declines gradually from
89.44% to 56.84% across 2–8 MB with no sharp transition at 2.41 MB, at 4.41 MB,
or anywhere else. The campaign was built to locate a knee; there is no knee. The
registered discriminator did its job — it refuted the mechanism account cleanly
at the one point chosen in advance to separate the two models — and in doing so
established that the premise of the framing question was wrong.

That is why the verdict ended up in a `*_CORRECTION_*` document. The corrected
index landed at the same time and rewrote the magnitudes of two earlier
documents; the knee refutation was recorded as one section of that correction
(§"The registered prediction it was meant to test, refuted") rather than as a
campaign outcome of its own.

## Disposition: answered elsewhere

Not abandoned — it ran to completion. Not deferred — nothing is waiting.
Not superseded — no later campaign re-asked this question; its data has instead
been *re-used* on a better axis.

The verdict is `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md`. The current use
of the data is `RECOVERY_CURVE_OUTCOME_2026-09-04.md`, which keeps all seven
points and re-plots recovery against the declared range's share of shared-cache
fills — the axis that explains the decline the knee campaign could only exhibit.
Read in that order, the campaign's failure to find a knee is what made the
successful axis findable.

## Paper dependency — yes, and it is load-bearing

**`fig:recovery` in `Sec7_Evaluation.tex` is this campaign's data.** All three
panels: `make_recovery_curve.py` reads `kn_runs.jsonl` + `kb_runs.jsonl` and
emits `figures/recovery_curve.pdf`. The surrounding paragraph
(§"The tenant's own footprint") states, from these 63 runs:

- recovery falls **89.4% → 56.8%** while a four-way mask holds **86–89%**;
- the mask charges the tenant **15.8–24.2%** at every table size;
- \textsc{Streaming} leaves the tenant **4.1–12.0% faster** than unprotected WB;
- the wedge is **20–36 percentage points at every point on the curve**.

Panel (c)'s declared-share axis is also computed from these archives, and the
complete join's held-out point is checked against them.

Closing this campaign is therefore **not** bookkeeping. The paper's boundary
argument — where object scope stops helping, and why — rests entirely on a
campaign that had no outcome document and no index entry.

## Provenance discrepancy to route (does not change any number)

I did not act on this: it concerns a paper caption, and a full reconciliation of
paper claims against records is owned by someone else right now.

`RECOVERY_CURVE_OUTCOME_2026-09-04.md` addendum 1 defends panel selection with:

> The seven fused points are the whole of a registered sweep
> (`FUSED_TABLESWEEP_PREREG_2026-08-29.md`)

and the `fig:recovery` caption carries "Panels~(a) and~(b) report a registered
sweep." The defence is substantially right — no point was dropped, and 63/63
records are `completed` — but it names the wrong registration, and one point is
not registered anywhere:

| plotted size | registered in | plotted runs come from |
|---|---|---|
| 2.0, 2.5, 3.0, 3.5, 4.0 MB | **`FUSED_KNEE_PREREG`** (this record) | `kn_*`, `run_fused_knee.sh` |
| 6.0 MB | `FUSED_TABLESWEEP_PREREG` registers the *size*; its own runs are `ts_*` at the aliased index and are **not plotted** | `kb_*`, `run_fused_knee_big.sh` |
| 8.0 MB | **no pre-registration's design** | `kb_*`, `run_fused_knee_big.sh` |

`FUSED_TABLESWEEP_PREREG` registered sizes {1, 2, 4, 6} plus a reused 3 MB point,
and explicitly named 6 MB as its top end ("Explicitly NOT predicted — the shape
at the top end"). Its executed sweep (`ts_runs.jsonl`, 45 records) covers
{1, 2, 4, 6, 8} — itself one size beyond its registration — and **none of those
runs appears in the figure**, because they used the aliased power-of-two probe
stride. 36 of its 45 records carry a null `realized_table_mb`.

The consequence worth flagging: **8.0 MB is the endpoint of the paper's headline
range** ("falls from 89.4% to 56.8%") and is the least-registered point on the
curve. The honest attribution is that panels (a)/(b) report *this*
pre-registration's sweep, extended by two sizes that were not pre-registered, all
63 runs of which completed and none of which was dropped.

## What would be required to complete it

Nothing, for the question as registered — it is answered, and the answer is that
the question was malformed.

Two things would be required before the curve could carry more than it does:

1. **A registration covering 6.0 and 8.0 MB**, or an explicit statement in the
   record that the top two points are an unregistered extension of a registered
   sweep. This is a writing task, not a compute task; the data exists and is
   complete.
2. **Counter-based engagement evidence for the fused arms** (liveness assertion 4
   above). The fused binary predates `streamingHnfFillBypasses`. Obtaining it
   means a rebuild and a re-run of all 63 cells, and it would not change any
   value here — the arms already separate by 25–33 pp. It matters only if a
   reviewer refuses declaration-flag evidence of mechanism engagement.

Neither is a reason to hold the figure.
