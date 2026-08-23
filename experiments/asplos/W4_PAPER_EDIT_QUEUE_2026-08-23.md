# The held paper-edit queue — one decision unblocks all of it

Written 2026-08-23. **Nothing in `~/STREAMING_Paper/` has been touched.** Every
write there publishes to the co-authors, so the whole queue is held behind one
S9 lead decision — *co-author communication* — not behind sixteen separate
ones.

This document exists so that decision can be made in one pass. 19 rows. Every row names
the site, quotes the current text, states the replacement, and cites the
evidence. Line numbers were verified against the working tree on 2026-08-23;
re-check them if the tree has moved.

**Two rows are deletions, twelve are corrections, four are additions.** None
requires a new experiment. Three are wrong-as-written on page 1 or in the
headline table.

---

## Tier 1 — wrong as written, and load-bearing

| # | site | current | replacement | evidence |
|---|---|---|---|---|
| 1 | `Sec5_Evaluation.tex:399` | "the SSTable workload of \S\ref{sec:intro}---slows 2.33$\times$ $[2.30,2.35]$" | **delete the sentence** | W4.1. Unreproducible; the panel referee's named reject reason. Comment at `:412` refers to it and should go with it. |
| 2 | `Appendix.tex:75-76` | "sized to approximately 170\,MB (53\% of the 8592+ LLC)" | "sized to 256\,MiB (80.0\% of the 8592+ LLC)" | F9.1. `table_capacity()` rounds the entry count to 2^24; 169.6 MiB requested, 256 MiB resident. 53% is unattainable by this kernel. |
| 3 | `Sec3_Mitigation.tex:93` | "even 12 of 20, more than the hot table's own share, leaves it 20\% worse" | **the clause inverts.** 12/20 of 320 MiB = 192 MiB = 75% *of* the 256 MiB table. Rewrite around "the table alone needs 16 of 20 ways, so a partition wide enough to hold it leaves 4 ways for everything else." | F9.2. The substantive claim survives and is sharpened. |
| 4 | `Sec1_Introduction.tex:111`, `Sec5_Evaluation.tex:354`, `:388`, `Appendix.tex:163`, `:168` | "6.92$\times$ residual" | "9.87$\times$" | W4.2. Retired in-repo 2026-08-08; an independent runner reads 9.97x. Comment sites `Abstract.tex:45`, `Sec2_DirectoryTax.tex:141`, `Sec5_Evaluation.tex:457`, `:462` carry it too. |
| 5 | *site unresolved* | the S1 premise that CAT cannot defend a private cache | mos182 exposes **L2 CAT** (`/sys/fs/resctrl/info/L2/` populated, `cbm_mask ffff`, `num_closids 8`, live `L2:` schemata line), so the sentence is false as written on this silicon. The argument survives — an invalidation is not an allocation, and no L2 way mask prevents back-invalidation — but the sentence does not. | W5.3 §page-1 correction, from GPROBE S5.7. **Site not located**: greps for `cannot defend`, `way mask`, and non-comment `private` across all `.tex` do not find it in `Sec1`/`Abstract`; the nearest live claim is `Sec4_Streaming.tex:50`. Locate before editing; it may already have been reworded. |
| 21 | `Sec5_Evaluation.tex:216-219` | "H2 pays down capacity and leaves that tax where write-back left it (2.51$\times$)" | **the two charges are not additive, and the sentence asserts they are.** If H2 paid down the 1.369x capacity charge and left the SF charge untouched, the finite-SF total would fall well below WB's 2.501x. It does not move (2.512x). The correct statement: *the back-invalidation charge subsumes the capacity charge* — the SF tracks private-cache contents, which H2 by construction does not touch, so once the victim is being back-invalidated out of its own L2 it no longer matters whether the aggressor also occupies the LLC. Same conclusion (only H3 removes it), sound reason. Also worth stating: 62–80% of the finite-SF charge is per-miss inflation, not the 213k extra misses, so "back-invalidation tax" as a count-of-invalidations story understates what is happening. | **`W1.4_CHARGE_DECOMPOSITION_2026-08-24.md`**, measured, n=3 on all six arms. Per-miss excess over a 142.4 cyc/miss quiescent baseline: WB/inf 52.4 → H2/inf 4.8 (**−90.9%**), WB/fin 131.9 → H2/fin 131.2 (**−0.5%**), → H2+H3/fin 8.7 (−93.4%). The victim alone hits the LLC **99.99%**; WB drops it to 20.8%; WB+finite-SF to **0.17%**, and aggregate hits (6,668) are fewer than victim L2 misses (927,002), so the victim's own LLC hit rate is bounded at 0.7%. H2 changes SF evictions by −0.2%. W1.4 §"The corrected sentence" supplies replacement prose. Load-bearing: this is the sentence that makes H3 necessary, and a referee who checks the addition finds it does not add. |

## Tier 2 — arm identity and provenance at the point of use

| # | site | change | evidence |
|---|---|---|---|
| 6 | wherever `tab:h3sf`'s 1.061x is quoted in `Sec5` | name the realization: it is measured under **ReadOnce / no-retention** (`H3_MODELCHECK.md` variant (a)), not the retain-and-skip mechanism the surrounding text implies | W1.2 + S5.1 arm-identity rule. The Appendix already discloses this correctly at `:422-424` and `:461-465`; the gap is only that Sec5's point of use does not. **Counter added 2026-08-24 (W1.4):** `ReadOnce` = 5,612,431 HNF inbound transitions in the H3 arm and **zero** in every other arm — the realization is variant (a) in the model, not an inference from the code. |
| 7 | `Sec5_Evaluation.tex:245-250` (`\jw{}`) | stale. Names 2026-08-03 / `0102eee441` and a "1.05x recovery"; the table now carries 1.061x from the 2026-08-20 remeasure. Also `H3SF_REMEASURED_2026-08-20.md` names gem5 `0f37c28`, which **predates** the argv[2] streaming gate those runs depend on and cannot have produced them (the runs used `356e7b7d0e`). | W1 provenance finding 2, S6.6 — record, do not reconcile. |
| 8 | `Appendix.tex:90-94` | "must agree on both the match count and a running hash of the result tuples" -> "…the match count, checked per run; a full per-tuple hash was verified in a separate pass whose timings were discarded because the hash itself perturbs them." | W4.3. `results/clos_split/raw_v1_contaminated_with_hash_overhead/` is that discarded pass, now committed. |
| 9 | `app:kernel` (`Appendix.tex`) | **add**: for the way-sweep rows the applied way count is carried by the filename, not recorded by the instrument — `bsweep_*` records have no `cmd` and no CAT field. | F1.2 / `results/clos_split/PROVENANCE.md`. |
| 10 | `tab:gem5cfg` memory row | wrong capacity | F6.1 |
| 11 | `tab:gem5cfg` prefetch row | `L1/L2 Stride(4) + DCPT` over-states DCPT | F6.2 |
| 12 | `tab:appplat` ways row | `16 | 20 (15 CLOSes)` is true of one of the Intel column's two hosts | F7.1 |
| 13 | `tab:appplat` CXL capacity | unit inconsistency | F7.2 |
| 14 | `tab:h1bw` | **add** a cycles column | F3 |
| 15 | `tab:gem5` | **name** the estimator | F5 |
| 20 | every gem5 table (`tab:gem5`, `tab:sens`, `tab:h1bw`, `tab:h3sf`) | **add** a variance statement, and make it the honest one. `tab:h3sf`'s infinite-SF cells now carry one — WB/inf tax **1.3689 ± 0.0015 (1 sd)**, from three repeated identical runs (CoV 0.042% quiescent, 0.100% WB). The other three tables have **none**, and the paper should say so rather than imply single-run numbers are exact. Do not describe the `_s1/_s2/_s3` spread as seed sensitivity: `SEED` enables divergence but does not control it, so these are repeated runs, not a seed sweep. | W1.3, closing the gap `GATE1_FUSED_NULL_CORRECTION` §6 named; estimator per its §6.1 amendment. **Extended 2026-08-24 (W1.4):** the *finite*-SF cells now have n=3 too — WB 84.7541 ± 0.0698, H2 85.0959 ± 0.0173, H2+H3 35.9474 ± 0.0123 — so all four `tab:h3sf` rows plus victim-alone (33.8814 ± 0.0140) and H2/inf (35.0247 ± 0.0074) can carry a real one. Only `tab:gem5` and `tab:h1bw` remain without. |
| 19 | anywhere `tab:h3sf`'s 2.501x (or the finite-SF charge generally) is presented as an expectable silicon quantity | qualify it as a mechanism study at 1.0x SF:L2 coverage. Shipping parts provision snoop filters at a multiple of aggregate private capacity; mos182 cannot be made to thrash even at 62 MiB of streaming private footprint (tax 1.020x, bounded at 1.0998x). | W3.1 closure + `GPROBE_OUTCOME.md` S3.2/S4.1, which states the requirement in as many words. |
| 22 | `tab:h3sf` (`Appendix.tex:205-229`) and `tab:sens` (`:126-135`) | **cross-reference them, and reconcile the 0.7%.** They share an arm. `tab:h3sf` has no H2/infinite-SF row; `tab:sens` publishes exactly that cell at **1.041x / 88.8% recovered**, and five more across assoc {8,12,20} and WSS {24,53,97}, all 88.8-91.9%. A reader of `tab:h3sf` alone concludes H2 does nothing. W1's three-run remeasure reads **1.0337 ± 0.0005**, which differs from the published 1.041 by ~14 sd — small, real, and spanning a commit (`b2c6499` -> `356e7b7d0e`) and a harness change. State it; do not smooth it. | W1 correction 2026-08-24 / W4.3 **F11**. This is the paper-side half of the failure that produced Plan B's premise 1. |
| 23 | `Appendix.tex:227` | "mean of three randomisation seeds, half-range $\le$0.07~cyc/access" | "mean of three repeated runs" — the exact wording row 20 forbids, now with a site. `SEED` enables divergence but does not control it (`GATE1_FUSED_NULL_CORRECTION` §6.1: a fixed-seed control did not reproduce, 562,510 vs 562,777 HNF fills). Three runs is a repeat, not a seed sweep, and calling it a seed sweep claims a robustness the design does not deliver. | W1.3 / row 20, site pinned. |
| 25 | `tab:h3sf` caption (`Appendix.tex:226`) and `Sec5_Evaluation.tex:217-219` | the finite-SF WB and H2 rows (2.501$\times$, 2.512$\times$) are presented as the same number, "indistinguishable at ±0.07". **With n=3 they are not:** 84.7541 ± 0.0698 vs 85.0959 ± 0.0173, a +0.3418 cyc/access difference at **4.8 sd**. H2 is reproducibly **0.40% worse** than write-back under a finite SF. Replace with "H2 costs a further 0.4%, consistent with paying the exclusion's own overhead while buying nothing." The published half-range was computed per cell and does not bound a difference *between* cells. | W1.4 §"A second, smaller correction". Magnitude negligible, conclusion untouched — but a claim of indistinguishability that the data does not support is exactly the kind of thing a referee checks. |

## Tier 3 — restructure, larger than a line edit

| # | change | evidence |
|---|---|---|
| 16 | Restate contribution (2) as *"no deployed control can be **aimed at** the object."* The current wording claims no alternative helps, which the MBA result falsifies. | W5.2, earned by W5.3's two-vendor table rather than conceded. |
| 17 | Promote `tab:fused` from Sec3 to the headline; add the L5 two-vendor table; promote the victim-MLP result out of a status file. | W5.1 / W5.3 / W5.4. Structural surgery — S9 lead decision in its own right. |
| 18 | Add a provenance appendix — and it must state what is **gone**, not only what is pinned. Three of the four major campaigns (`tab:h3sf`'s gem5 cells, `tab:fused`'s way sweep and its nine rows, oltp_index's 668 rows) have no recoverable apparatus; the fourth survived only because `/tmp` outlived it. The numbers reproduce, the launchers and binaries do not exist. | W4.3 **F10**. Upgraded from optional to load-bearing: the referee's inference from the RocksDB sentence — one unsourced number implies the rest — turns out to be partly correct, so silence is the worst available answer and disclosure is the only one, since the artifacts cannot be recovered. |
| 24 | **Place H2's benefit result.** It is currently one column of an appendix sensitivity table. H2 removes **88.8-91.9%** of the capacity charge across two axes and three independent measurements — this is the paper's benefit claim for the mechanism in its title, and `tab:h3sf`, the table a reader reaches from Sec5, omits it. Moving it forward is structural surgery and interacts with rows 17 and 22. | W1 + `tab:sens`. **S9 lead decision** in its own right: it changes what the paper's central experiment is. |

---

## What is *not* in this queue, deliberately

- **No number changes because of F9.** The measurements are correct; only their
  geometry description was wrong. Row 2 and row 3 are description fixes.
- **No re-run of `tab:fused`.** All nine rows reproduce exactly from the raw,
  which is now committed (`a41df38`). A re-run would have to pick 128 MiB or
  256 MiB — 53% is unattainable — and changing the geometry to match the prose
  would be fitting the experiment to the text, which S6.6 forbids. Fix the
  text.
- ~~**Nothing gated on W1.**~~ **No longer true, 2026-08-24.** Rows 1-20 are
  still unconditional. Rows 21-24 come from W1 and from discovering that
  `tab:sens` already carried the cell; they are conditional on nothing further,
  since W1 passed and the `tab:sens` rows were already published, but they did
  not exist when this bullet was written.
- **No attempt to reconstruct the three lost apparatus states (F10).** Two were
  tried and failed; the third is a source state present in neither commit nor
  stash on either host. Rebuilding *a* binary that reproduces the numbers would
  not establish that it is *the* binary, and presenting it as such is exactly
  the move S6.6 forbids. Row 18 discloses instead.

## Recommended order once unblocked

Rows 1 and 4 first: both are pure deletions/substitutions, both are needed
under every outcome including a return to Plan A, and row 1 is the single
sentence the referee named. Then Tier 1 rows 2, 3, 5. Then Tier 2, which is
mechanical. Tier 3 only after the lead has decided the paper's shape.

**Amended 2026-08-24: row 21 joins rows 1 and 4 at the front.** It is a Tier 1
correctness fix in the paragraph that motivates H3, it is checkable by a referee
with arithmetic alone, and it does not depend on any lead decision. Rows 22 and
23 follow with Tier 2. Row 24 is Tier 3 and waits.
