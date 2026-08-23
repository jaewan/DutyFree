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

## Tier 2 — arm identity and provenance at the point of use

| # | site | change | evidence |
|---|---|---|---|
| 6 | wherever `tab:h3sf`'s 1.061x is quoted in `Sec5` | name the realization: it is measured under **ReadOnce / no-retention** (`H3_MODELCHECK.md` variant (a)), not the retain-and-skip mechanism the surrounding text implies | W1.2 + S5.1 arm-identity rule. The Appendix already discloses this correctly at `:422-424` and `:461-465`; the gap is only that Sec5's point of use does not. |
| 7 | `Sec5_Evaluation.tex:245-250` (`\jw{}`) | stale. Names 2026-08-03 / `0102eee441` and a "1.05x recovery"; the table now carries 1.061x from the 2026-08-20 remeasure. Also `H3SF_REMEASURED_2026-08-20.md` names gem5 `0f37c28`, which **predates** the argv[2] streaming gate those runs depend on and cannot have produced them (the runs used `356e7b7d0e`). | W1 provenance finding 2, S6.6 — record, do not reconcile. |
| 8 | `Appendix.tex:90-94` | "must agree on both the match count and a running hash of the result tuples" -> "…the match count, checked per run; a full per-tuple hash was verified in a separate pass whose timings were discarded because the hash itself perturbs them." | W4.3. `results/clos_split/raw_v1_contaminated_with_hash_overhead/` is that discarded pass, now committed. |
| 9 | `app:kernel` (`Appendix.tex`) | **add**: for the way-sweep rows the applied way count is carried by the filename, not recorded by the instrument — `bsweep_*` records have no `cmd` and no CAT field. | F1.2 / `results/clos_split/PROVENANCE.md`. |
| 10 | `tab:gem5cfg` memory row | wrong capacity | F6.1 |
| 11 | `tab:gem5cfg` prefetch row | `L1/L2 Stride(4) + DCPT` over-states DCPT | F6.2 |
| 12 | `tab:appplat` ways row | `16 | 20 (15 CLOSes)` is true of one of the Intel column's two hosts | F7.1 |
| 13 | `tab:appplat` CXL capacity | unit inconsistency | F7.2 |
| 14 | `tab:h1bw` | **add** a cycles column | F3 |
| 15 | `tab:gem5` | **name** the estimator | F5 |
| 19 | anywhere `tab:h3sf`'s 2.501x (or the finite-SF charge generally) is presented as an expectable silicon quantity | qualify it as a mechanism study at 1.0x SF:L2 coverage. Shipping parts provision snoop filters at a multiple of aggregate private capacity; mos182 cannot be made to thrash even at 62 MiB of streaming private footprint (tax 1.020x, bounded at 1.0998x). | W3.1 closure + `GPROBE_OUTCOME.md` S3.2/S4.1, which states the requirement in as many words. |

## Tier 3 — restructure, larger than a line edit

| # | change | evidence |
|---|---|---|
| 16 | Restate contribution (2) as *"no deployed control can be **aimed at** the object."* The current wording claims no alternative helps, which the MBA result falsifies. | W5.2, earned by W5.3's two-vendor table rather than conceded. |
| 17 | Promote `tab:fused` from Sec3 to the headline; add the L5 two-vendor table; promote the victim-MLP result out of a status file. | W5.1 / W5.3 / W5.4. Structural surgery — S9 lead decision in its own right. |
| 18 | Add a provenance appendix. | W4.3; the referee's reject reason is unsourced numbers, and a ledger now exists. |

---

## What is *not* in this queue, deliberately

- **No number changes because of F9.** The measurements are correct; only their
  geometry description was wrong. Row 2 and row 3 are description fixes.
- **No re-run of `tab:fused`.** All nine rows reproduce exactly from the raw,
  which is now committed (`a41df38`). A re-run would have to pick 128 MiB or
  256 MiB — 53% is unattainable — and changing the geometry to match the prose
  would be fitting the experiment to the text, which S6.6 forbids. Fix the
  text.
- **Nothing gated on W1.** These are all true regardless of how the
  H2/infinite-SF cell lands.

## Recommended order once unblocked

Rows 1 and 4 first: both are pure deletions/substitutions, both are needed
under every outcome including a return to Plan A, and row 1 is the single
sentence the referee named. Then Tier 1 rows 2, 3, 5. Then Tier 2, which is
mechanical. Tier 3 only after the lead has decided the paper's shape.
