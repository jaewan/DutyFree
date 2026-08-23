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
| 27 | `tab:gem5cfg` (`Appendix.tex:385-408`) | **add an inclusivity row.** The table gives sets, ways, latencies, SF size and prefetchers but never says the modelled LLC is **non-inclusive / victim-fill**. `CHI_config_8592.py:350-405` sets `alloc_on_readshared=False`, `alloc_on_readunique=False`, `alloc_on_readonce=False`, `alloc_on_writeback=True`, commented "Non-inclusive (victim cache): L2 evictions fill LLC, reads do not." This is correct Intel-NINE modelling **and it is load-bearing**: H2's gate acts on the `WriteEvictFull` fill path, so a reader who assumes an allocating LLC cannot follow why H2 works, why `needCacheEntry` is the site, or why the victim's LLC hit rate collapses to 0.17% under a finite SF (W1.4). Joins rows 10 and 11 against the same table. | `W6.1_IMPLEMENTATION_COST_AUDIT_2026-08-24.md`, apparatus fact 1 |
| 28 | wherever H2's benefit is claimed (`Sec5_Evaluation.tex`, `tab:h3sf`, `tab:sens`) | **price H2 on the streamer's side. The paper prices nothing there.** Measured, n=3, infinite SF: the declared stream's delivered CXL read bandwidth falls **3.2929 → 3.0872 GB/s, −6.25%** (sd 0.00084 / 0.00020, ~245 sd — real, not noise), and its CXL write traffic rises **1,877 → 1,698,091 bytes** because H2 denies it the LLC writeback absorption `alloc_on_writeback=True` was giving it. This is a cost of the mechanism, not a confound in the benefit (see row 29), and reporting it is what makes the benefit credible. | `W2.1_DECONFOUND_2026-08-24.md` |
| 29 | same sites | **add the two numbers that answer the first reviewer's objection.** "The victim got faster because the aggressor got slower" is refuted by: the victim's L2 demand miss count is **invariant, 714,210 → 714,068, 0.02%**, while the fraction of those misses reaching DRAM goes **62.4% → ≤0.45%** (LLC-served 37.6% → 99.55%; `LocalHN_Eviction` fills −99.3%). A throttle shortens queues and lowers miss *latency*; it cannot relocate a miss from DRAM to the LLC. Neither number is currently in any table. | `W2.1_DECONFOUND_2026-08-24.md`; corroborated by `W1.4_CHARGE_DECOMPOSITION_2026-08-24.md` |
| 30 | wherever the cost argument lands (new, see row 26) | **argue from CAT, not from WC/MOVNTDQA.** `PLAN_B_REBUILD.md` W6.1 proposes arguing against "datapaths that already exist for WC and MOVNTDQA"; those are instruction-scoped hierarchy bypass and are the weaker analogy. The SDM (Vol. 3B §17, read at source) says CAT tags every request from a logical processor with its COS and consults that tag in the LLC **allocation** decision — H2's mechanism, in the same pipeline position, shipping since E5-2600 v3. The difference is what the label names: CAT's is a *thread*, bound at context switch; ours is an *object*, bound at translation. **That is the paper's title as an architectural fact and it is the sharpest form of contribution (2) we have.** | `W6.3_CAT_COMPARISON_2026-08-24.md` |
| 31 | **do not write** "CAT shipped for less benefit than this" | The sentence sits in `PLAN_B_REBUILD.md` W6.3 and would otherwise be drafted straight into the cost section. It is unsupported (published CAT benefits are not small), it contradicts W5.3's own table (CAT *recovers* the Intel capacity charge on mos182), and it argues the wrong axis (cache QoS shipped on a capability argument, not a throughput one). Replace with the footprint comparison: CAT needs a CPUID leaf, a per-logical-processor association register, a file of mask MSRs per class, an architectural mask-contiguity rule, and a write on every context switch; \textsc{Streaming} needs no new architectural state at all. **Negative row — recorded so the claim is not made, not so it is fixed later.** | `W6.3_CAT_COMPARISON_2026-08-24.md` |
| 32 | **do not write** "one PTE bit" (or "a new PTE bit", "1 PTE flag") anywhere in the paper | The mechanism adds **no new PTE bit**. `pagetable_walker.cc` decodes `bits(pte,12) && pte.pcd && !pte.pwt` for a PMD leaf and `bits(pte,7) && pte.pcd && !pte.pwt` for a 4K PTE — that is the existing PAT selector triple, architecturally defined since the PAT was introduced, selecting slot 6. The phrase appears in `W6_COST_ARGUMENT_2026-08-23.md` twice (its cost table says "1 PTE flag"; its summary sentence says "One PTE bit and two fill-path predicates can be") and would be drafted straight from there. Correct phrasing: **"A PAT encoding and two fill-path predicates can be."** Same rhetorical shape, strictly stronger claim — the paper is currently understating its own cheapness. **Negative row.** | `W6.1_IMPLEMENTATION_COST_AUDIT_2026-08-24.md`, four decision lines quoted; correction appended same day |
| 33 | `Sec5_Evaluation.tex:336-337` (currently commented out) | **if this MLP sentence is ever uncommented, name the arm.** It reads "stream-smoke reaches 4.17 GB/s (WB) / 4.78 GB/s (H2) while the fused kernel reaches 0.52 GB/s -- ~8x below". All three figures are the **2 MiB** hot-table configuration, and 2 MiB is the arm `GATE1_FUSED_NULL_CORRECTION_2026-08-15.md` section 3 itself calls null by construction ("the hot table never leaves the cache hierarchy"). The arm section 5 is otherwise about -- 4 MiB, "the window" -- reads **0.4199** (WB) / **0.4224** (H2), so the honest sentence is either "0.42 GB/s at the 4 MiB window arm, ~10x below the 2 MiB pure-stream ceiling" or the 2 MiB triple with "2 MiB hot table" stated once. Note also that the memo's neighbouring "~1.3 lines in flight" is the **4 MiB** number (0.42 x 203ns / 64B = 1.33); 0.52 gives 1.65. The conclusion (~10% of the 5.04 GB/s MLP ceiling) holds either way. | Bench JSON re-read 2026-08-24: `m22_small_wb` 0.5180 / `m22_small_st` 0.5209 (hot 2 MiB), `m22_mid_wb` 0.4199 / `m22_mid_st` 0.4224 (hot 4 MiB), `m22_bw_wb` 4.172 / `m22_bw_st` 4.777 (stream-smoke, hot 2 MiB). Key is `stream_bandwidth_gbps` / `bandwidth_gbps`, not CXL bytes / simSeconds -- the latter reads 0.239 and 0.483 for the same two runs. [S5.1] |

## Tier 3 — restructure, larger than a line edit

| # | change | evidence |
|---|---|---|
| 16 | Restate contribution (2) as *"no deployed control can be **aimed at** the object."* The current wording claims no alternative helps, which the MBA result falsifies. | W5.2, earned by W5.3's two-vendor table rather than conceded. |
| 17 | Promote `tab:fused` from Sec3 to the headline; add the L5 two-vendor table; promote the victim-MLP result out of a status file. | W5.1 / W5.3 / W5.4. Structural surgery — S9 lead decision in its own right. |
| 18 | Add a provenance appendix — and it must state what is **gone**, not only what is pinned. Three of the four major campaigns (`tab:h3sf`'s gem5 cells, `tab:fused`'s way sweep and its nine rows, oltp_index's 668 rows) have no recoverable apparatus; the fourth survived only because `/tmp` outlived it. The numbers reproduce, the launchers and binaries do not exist. | W4.3 **F10**. Upgraded from optional to load-bearing: the referee's inference from the RocksDB sentence — one unsourced number implies the rest — turns out to be partly correct, so silence is the worst available answer and disclosure is the only one, since the artifacts cannot be recovered. |
| 24 | **Place H2's benefit result.** It is currently one column of an appendix sensitivity table. H2 removes **88.8-91.9%** of the capacity charge across two axes and three independent measurements — this is the paper's benefit claim for the mechanism in its title, and `tab:h3sf`, the table a reader reaches from Sec5, omits it. Moving it forward is structural surgery and interacts with rows 17 and 22. | W1 + `tab:sens`. **S9 lead decision** in its own right: it changes what the paper's central experiment is. |
| 26 | **Add the cost argument. The paper does not have one.** A grep for `PAT slot` / `PTE bit` / `no new coherence state` / `hardware cost` across all of `Text/` returns four hits, none of which price the mechanism; `Sec4_Streaming.tex:99` explicitly declines to price the *optional* stream buffer (correctly — that sentence is well scoped and needs no edit). The audit supplies the numbers: **zero new coherence states, zero new message types, zero new SLICC structures, zero new enumerations**; the 1 event / 4 transitions / 2 actions in the protocol diff belong to the finite-SF *model*, not to \textsc{Streaming}. The mechanism is **one bit through six structures** (TLB entry, an unused encoding in `Request`'s existing coherence-flag bitfield, RubyRequest, one wire bit in `CHIRequestMsg`, TBE, one LLC tag bit) plus **four lines of decision logic**. **There is no new PTE bit** — the decode reads the PAT selector, PCD and PWT, three bits the walker already reads on every walk, in two lines per leaf size. That is the paper's title as an implementation fact and it is stronger than the claim `PLAN_B_REBUILD.md` W6.1 makes. OS side: **564** non-comment kernel lines, **447** without the removable debugfs facility, **one line** of new UAPI, no new syscall, I0/I1 enforcement as six rejection rules over VMA flags the kernel already maintains — against 155 KUnit and 662 selftest lines, i.e. more test than implementation. **Constraint:** any cost sentence about H3 must name the variant it is costing; only H2's cost is established (limit 2 of the audit). | `W6.1_IMPLEMENTATION_COST_AUDIT_2026-08-24.md`; W6.1/W6.2 of the plan |

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

**Second amendment, same day: row 26 is Tier 3 but does not wait on the lead.**
It adds a subsection the paper does not have, so it is structural — but unlike
rows 16-18 and 24 it changes nothing already written, contradicts nothing
already claimed, and is not contingent on whether H3 survives. Its content is a
static audit of two committed trees, so it can be drafted before any lead
decision and dropped in wherever §4 or §6 ends up. Row 27 is mechanical and
joins Tier 2.

**Third amendment, same day: rows 28 and 29 are Tier 2 but belong with row 21 at
the front.** Row 29 is the answer to the objection a referee raises first, and
row 28 is the disclosure that makes row 29 believable -- a benefit reported with
no cost on the other side reads as an incomplete accounting whether or not it is
one. Both are pure additions of measured numbers, neither depends on a lead
decision, and both come from runs that already exist.

**On row 31 and negative rows generally.** This queue has until now listed things
to change in the text. Row 31 lists something to *not write* that no draft
contains yet, because the plan tells a future drafter to write it. F11 in the
W4.3 ledger is the same failure in the other direction — a correct artifact
nobody read. A queue that only tracks existing text cannot catch either. Any
future memo that overturns a planned claim gets a negative row here.

**Fourth amendment, 2026-08-24: row 30 carries measurements, and row 32 is the
second negative row.** Row 30 as written argues only mechanism — that CAT's
per-request COS label consulted in the LLC allocation decision *is* H2's
mechanism. It should also carry the four measured rows from
`W5.3_L5_EVIDENCE_2026-08-23.md`: CAT recovers the mos182 co-run tax completely
(1.00x residual under CAT12), charges **1.222x with no co-runner present**
because a way mask shrinks the victim's own capacity, leaves a **12.4x**
residual on moscxl where the harm is rate-class rather than capacity, and
recovers **nothing** on `tab:fused` (214.6 -> 215.0 Mtuple/s) because a
core-scoped knob has no boundary to draw when the streamer is the victim's own
thread. The fused null is the row a referee cannot answer, and it is why the
argument does not require the benefit magnitude to be large.

Row 32 is a negative row of a kind row 31 is not: row 31 stops a claim the
*plan* proposes, row 32 stops a claim one of our own **outcome memos** already
makes twice. A negative row is cheaper than a correction only if it is filed
before the sentence is drafted; this one nearly was not, because the memo
carrying the error is the same memo that was itself never read (F11, third
instance). Both failures had the same cause and one fix.


**Fifth amendment, 2026-08-24: row 33, and a metric that is not the metric.**
Row 33 came out of writing `w7_analyze.py` against the completed 2026-08-15
runs before the W7 data existed. The script's first draft defined fused
bandwidth as CXL bytes / `simSeconds`, which is a defensible quantity and is
not the published one: it reads 0.239 where the bench reports 0.420 at the same
run, because `simSeconds` spans SE startup, table build and warmup while the
bench times only the measured region. The published table is bench-reported
throughout. Two things follow. First, the pre-registered P2 threshold
(">= 2.0 GB/s" fused) is on the **bench-reported** figure -- on the
simSeconds-derived one it would be a different and much harder test, and
choosing between them after seeing the data would be exactly the move S6.6
forbids, so it is fixed here in writing before the campaign returns. Second,
checking a new analysis script against a completed run whose numbers are
already published is cheap and catches this class immediately; it also
surfaced row 33, which reading the memo alone did not.

**Sixth amendment, 2026-08-24: row 34, and H3 stops being free.**

| # | site | change | evidence |
|---|---|---|---|
| 34 | wherever the paper describes H3 as costless, or prices H2+H3 as equal to H2 (audit `Sec4_Streaming.tex`, `Sec5_Evaluation.tex` around `tab:h3sf`, and `Appendix.tex:422-424`/`:461-465` before drafting) | **state H3's price.** At an **infinite** snoop filter — where H3 has no enrolment charge to remove — H2+H3 costs **1.0345x relative to H2 alone (+3.45%)**, n=3, sd 0.0117 cyc/access, ~3 sd of separation. Per S5.1 the sentence must carry its arm and operating point: *"H2+H3 costs 3.45% over H2 alone at an infinite snoop filter (2-core CHI, 5 MiB HNF, CXL-resident aggressor), where H3 has no enrolment charge to remove."* The mechanism is on the record too and is worth one clause: under H2+H3 the declared stream's L1D hit rate is **0.3%** and its private-L2 hit rate **11.7%** — no-retention observed, not inferred — so it puts **+61.7%** more traffic per cycle onto the shared fabric than under H2. **This is an addition, not a correction:** no current sentence is wrong, but the omission is the kind a referee reads as concealment once they notice the control exists. | `W1.5_H3_INFINITE_SF_OUTCOME_2026-08-24.md` |

Row 34 also **strengthens row 6 rather than competing with it.** Row 6 asks
Sec5 to name H3's realization as ReadOnce/no-retention at the point of use.
W1.5 supplies the direct consequence of that realization as a measured number,
so the two edits should be drafted together: the realization and its price in
the same paragraph, or the reader gets the disclosure without the reason.

And it retires a standing worry rather than adding one. W1.2 Correction 3
argued on traffic grounds that the H3 confound runs *against* `tab:h3sf` — H3
wins its finite-SF result while pushing more traffic, not less. That was an
inference from finite-SF counters. The infinite-SF control now measures the same
effect independently (+61.7% here against Correction 3's +58% there), and, more
decisively, shows H3 delivering **no benefit at all** when there is no enrolment
charge in play. `tab:h3sf`'s H3 attribution is confirmed by its own control, not
merely left unfalsified. If a referee asks "how do you know H3's benefit is
enrolment relief and not something else you happened to bundle with it," this
is the answer, and it should be in the paper as one sentence with a pointer.

**No row is withdrawn by W1.5.** The registered withdrawal trigger — H2+H3
coming in >10% *better* than H2 at an infinite SF — did not fire.

## Seventh amendment, 2026-08-24: row 18 gains a shape

Row 18 (provenance appendix) currently asks for artifact -> commit -> date ->
runner per number. `W4.5_SF_CAMPAIGN_PROVENANCE_2026-08-24.md` shows the
"commit" column cannot be one hash for a gem5 number, and that this is what
produced the `0f37c28` vs `356e7b7d0e` confusion the W4.3 ledger records twice.
A gem5 run is three artifacts with three vintages:

- the **simulator binary** — fixed by the build, not by HEAD;
- the **Python `configs/` tree** — read at run time, so *not* frozen by the
  build;
- the **workload binaries** — fixed by whenever they were last compiled.

For the SF campaigns these are 2026-08-09 (`src/` as of `56874f1d42`),
`fa103c5b7b`, and a verified byte-identical rebuild of committed source at
`356e7b7d0e`. `0f37c28` is a correct name for the second and a wrong name for
the third, which is why it is right for `tab:declpredmeas`/`tab:declpredx` and
wrong for `tab:h3sf`.

**Edit:** the appendix reports the triple for every gem5 number. Silicon numbers
keep the single-hash form; they have one binary.

This is an addition, not a correction — row 18 is not wrong, it is
under-specified in the same way the numbers it audits are.

Also owed here, from the same memo: every "gem5 `<hash>`" cell in the W4.3
ledger's main table is under-specified and should be re-emitted in the triple
form when the appendix is written. Not a defect in any number.

## Eighth amendment, 2026-08-24: row 35, and the counter that should have been reported all along

**Row 35 — Tier 2.** *Sites: wherever H2's effect is quantified
(`Sec5_Evaluation.tex`, `tab:h3sf`, `tab:sens`), and the metric definitions in
the appendix.*

**Report H2's LLC effect as data-array writes, not fills.** Fills answer "did the
line allocate"; they do not answer "did the declaration take effect", and at a
hierarchy where the stream is resident the two diverge completely. Measured, W7
stream-smoke references, one run each:

| point | HNF data-array writes, wb -> stream | fills, wb -> stream | CXL read | bench GB/s |
|---|---|---|---:|---|
| A0, 5 MiB LLC | 1,315,975 -> 298,625 (**−77.3%**) | 1,314,720 -> 298,569 (−77.3%) | 84.40 -> 65.21 MB | 3.960 -> 4.609 |
| A1, 20 MiB effective LLC | 1,475,801 -> 434,160 (**−70.6%**) | 321,818 -> 321,815 (**−0.001%**) | 16.78 -> 16.78 MB | 9.273 -> 9.270 |

Read on fills alone, A1 says H2 does nothing. Read on array writes, A1 says H2
does **the same proportional work as at A0** and none of it reaches memory,
because a resident line is updated in place by the thrashing L2 rather than
re-allocated. At A0, 99.9% of the HNF's data-array writes are fills; at A1,
21.8%.

Two consequences for the text.

1. **A claim that H2 is inert at some operating point must say which counter it
   is inert on.** This is §5.1's arm-identity rule applied to metrics rather than
   to arms, and it is the same failure mode as row 25's "indistinguishable":
   a null that is a property of the column read, not of the machine.
2. **It supplies a clean statement of what \textsc{Streaming} is for.** H2's
   mechanism is hierarchy-invariant; its *payoff* is not. Where the stream
   overflows the LLC the excluded fills are refetches, and removing them buys
   16.4% bandwidth and 19.2 MB of CXL traffic. Where the stream fits, the same
   exclusion buys array-write traffic and write-port pressure that neither this
   campaign nor the paper prices. That is an argument for the mechanism being
   correctly targeted, and the paper currently makes it nowhere.

**Constraint, inherited from W7.2.** The A1 numbers above are from a hierarchy
that is **20 MiB, not the 32 MiB configured** — gem5's `CacheMemory` indexes only
`2^floorLog2(sets)`. Any use of them must name 20 MiB. They may be cited for the
*mechanism* contrast, which does not depend on the exact capacity, and may not be
cited as a bandwidth result: 9.27 GB/s is on-chip.

Source: `W7.2_A1_SIZING_2026-08-24.md` and its 2026-08-24 addendum.
