# Plan B: skip Sep 9, rebuild the paper the evidence supports

> **AMENDED 2026-08-24 — W1 PASSED and two of the four founding premises below
> are overturned.** H2/infinite-SF = **1.0337x ± 0.0005**, removing **90.9%** of
> the capacity charge. Premise 1 ("H2 is inert in our own simulator") is false as
> stated: H2 is inert against the *finite-SF back-invalidation* charge and
> removes 90.9% of the *capacity* charge. Premise 3 ("the two instruments do not
> meet") is false: silicon's Intel charge is capacity-class and so is the one H2
> removes here. Premises 2 and 4 stand. **The `Why` section below is left
> verbatim, struck where wrong, because the reasoning that produced Plan B has to
> stay legible.** See `W1_OUTCOME_2026-08-24.md`.
>
> **Second amendment, same day: premise 1 was already falsified in writing before
> Plan B was written, and W1 is a replication rather than a first measurement.**
> `tab:sens` (`Appendix.tex:126-135`) has carried H2/infinite-SF at **1.041x /
> 88.8% recovered** across six cells on two axes since task #25's re-run, and
> `TAX_INCONSISTENCY_2026-08-20.md` states those numbers in this repo on
> **2026-08-20**, three days before Plan B. Nothing about the verdict changes --
> three measurements across two harnesses and two gem5 commits agree, WB to four
> digits and H2 to 0.7% -- but the overturn is not W1's to claim, and the reason
> premise 1 was ever written is a process failure worth more than the datapoint.
> See the appended correction in `W1_OUTCOME_2026-08-24.md`.
>
> Plan B's *conclusion* is unchanged. The rebuilt argument in the next section
> already said what was missing — "(a) evidence that H2 recovers the charge
> silicon actually levies, and (b) a cost argument" — and both now exist. The
> case for skipping Sep 9 rested on the seventeen-day runway, not only on the
> nulls; it is now a stronger paper to finish, not a weaker one to abandon.

Written 2026-08-23. Supersedes the ASPLOS'27 Sep 9 push. Lead decision.

## Why

Four facts, each measured in this repo, that jointly make the Sep 9 submission
a reject:

1. ~~**H2 is inert in our own simulator.**~~ **OVERTURNED 2026-08-24.** The
   observation is correct and its generalisation was not. `tab:h3sf` re-measured
   2026-08-20: WB/finite-SF 2.501x, H2/finite-SF 2.512x ("indistinguishable at
   +/-0.07"), H2+H3 1.061x — all true, and all in the finite-SF row. At an
   infinite SF, H2 reads **1.034x against WB's 1.369x**. The entire gem5 benefit
   is **not** H3.

   The clause "the only configuration it is reported in" was itself false, and
   checkable at the time: `tab:sens` reports the same arm at **1.041x / 88.8%**
   across six cells, and `TAX_INCONSISTENCY_2026-08-20.md` recorded it here
   2026-08-20. The defect was not a missing measurement. It was reading
   `tab:h3sf`'s finite-SF row as the mechanism's behaviour without consulting
   the adjacent table that measures the other arm -- Sec5.1's rule applied to
   figures but not to the diagnosis built from them.
2. **H3's charge is absent on shipping silicon.** Private-L2-resident victims
   read 1.000x on SPR and Bergamo; mos182's forced SF turnover reads 1.00x.
3. ~~**So the two instruments do not meet.**~~ **OVERTURNED 2026-08-24.** They
   meet. Silicon measures a *capacity* charge (CAT recovers it on mos182). H2 at
   an infinite SF removes a *capacity* charge — 90.9% of it — on a victim whose
   private-L2 miss count is invariant to 0.02% across arms, so the charge is
   levied entirely below L2. The back-invalidation charge is a *separate* charge
   that H3 addresses and that shipping snoop filters do not levy (W3.1). The
   division of labour the paper claimed is supported.
4. **The realised magnitudes are small.** DuckDB co-run, matched bandwidth:
   1.112x vs 1.049x, allocation-attributable difference +0.058. Six e2e
   workloads, same shape: direction confirmed, magnitude small.

The paper the evidence supports is a **scope-and-abstraction paper with a cheap
mechanism** -- which is what the title already says. The paper currently
written is a performance paper. Three months converts one into the other;
seventeen days does not.

## The rebuilt argument

> No deployed control can be aimed at an object. Fusion proves object scope is
> necessary (tab:fused, on silicon). The cross-vendor result proves the
> per-vendor knobs do not substitute: AMD's harm is rate-class and MBA recovers
> it, Intel's is capacity-class and CAT recovers it, each is useless on the
> other's machine, and neither can name a region. The mechanism that can is
> nearly free. The label is the only thing that ports.

Every clause is already measured. What is missing is (a) evidence that H2
recovers the charge silicon actually levies, and (b) a cost argument.

---

# Workstreams

## W1 -- The decisive cell. **PASSED 2026-08-24. Gate released.**

> **Outcome: `W1_OUTCOME_2026-08-24.md`. H2/infinite-SF = 1.0337x ± 0.0005
> (1 sd), inside the pre-registered PASS band by 136 sd, removing 90.9% of the
> WB/infinite-SF charge.** The pre-registered prediction (1.00-1.10x) is
> confirmed near the bottom of its band. The aggressor is not throttled: its
> L2-miss rate per cycle falls 3.9%, and under H2 the LLC is accessed 16% *more*
> per cycle while going off-chip 16% *less*.
>
> **W1.2's consistency prediction for H2+H3/infinite is now resolved --
> `W1.5_H3_INFINITE_SF_OUTCOME_2026-08-24.md`.** (H2+H3)/inf = 1.0694x, i.e.
> **1.0345x relative to H2/inf** -- 3.45% worse, inside the registered +/-5%
> "same" band and in the predicted direction. Neither escape clause fires:
> `tab:h3sf`'s H3 attribution is **not** withdrawn, and the no-retention traffic
> penalty is **not** large. With an infinite SF there is no enrolment charge to
> remove and H3 delivers no benefit at all, which is the control separating
> "H3 = SF-enrolment relief" from "H3 = something else." One number is owed to
> the text: H3 is not free; it costs 3.45% over H2 alone at an infinite SF.
> **No W1 prediction remains unevaluated.**
>
> **Re-scoped, same day: this is the third measurement of the cell, not the
> first** -- see the banner and the appended correction. What W1 alone supplies
> is the variance estimate (`tab:sens` is single runs per cell), agreement
> across the `b2c6499` -> `356e7b7d0e` commit change, and the mechanism counters
> and aggressor de-confound.
>
> Per the rule as written: proceed to W2, and H3 demotes to a bounded capability
> claim — which W3.1 had already forced independently.

### Original section, unchanged

`tab:h3sf` is a 2x3 design (SF in {infinite, finite} x arm in {WB, H2, H2+H3})
with **the load-bearing cell empty**. H2 has never been tested against the
capacity-only charge -- the one charge both hosts exhibit.

| | WB | H2 | H2+H3 |
|---|---|---|---|
| infinite SF | 1.369x | **MISSING** | **MISSING** |
| finite SF | 2.501x | 2.512x | 1.061x |

**Runs** -- `experiments/asplos/sf_inf_cells.sh` (written 2026-08-23, and
committed, unlike the original). **`b4run2.sh` is the wrong harness for this
table** and an earlier draft of this plan said otherwise: b4run2 runs
`testcase/dirtax/victim` with aggressor arg `10.0`, whereas tab:h3sf was
produced with `testcase/dutyfree/victim 2650 3000000` and
`testcase/dutyfree/aggressor 16.0 stream`. Reconstructed from
`/tmp/sf_h2_fin_s1/config.ini`.

The H2 declaration is **the aggressor's `stream` argv[2]**, gated by gem5
commit `356e7b7d0e`. SF finiteness is `HNF_SF_FINITE`, with a 4 MiB/16-way =
65,536-entry filter that only binds when finite. Six runs, seeds 1-3:

```
sf_h2_inf_s{1,2,3}   HNF_SF_FINITE=0 HNF_H3=0   # H2, infinite SF   <- decisive
sf_h3_inf_s{1,2,3}   HNF_SF_FINITE=0 HNF_H3=1   # H2+H3, infinite SF <- consistency
```

The WB/infinite comparator does **not** need re-running: `sf_wb_inf_s{1,2,3}`
exist from the same apparatus and give 1.369x.

Launched 2026-08-23 22:11 on mos181 (load 1.07 / 256 cores; the `ld_*` sims
last wrote 2026-08-11, so that host constraint has expired). Expect ~45 min per
cell, three seeds in parallel, ~1.5 h total.

### Provenance findings from reconstructing the apparatus

These are W4 items, found while setting up W1:

1. **The table is sound and fully reproducible.** Recomputing cyc/access as
   `system.cpu0.numCycles / 3e6` from the surviving `stats.txt` reproduces every
   published row on seed 1: 33.87 / 46.37 / 84.83 / 85.08 / 35.96 against
   published 33.88 / 46.38 / 84.75 / 85.10 / 35.95.
2. **The commit attribution is wrong.** `H3SF_REMEASURED_2026-08-20.md` names
   gem5 `0f37c28`. The runs used `356e7b7d0e`; `0f37c28` (2026-08-18) *predates*
   the argv[2] streaming gate those runs depend on, so the stated commit could
   not have produced them. Recorded, not reconciled (Sec6.6).
3. **The launcher was never committed.** It was typed at the shell. The runs are
   only reconstructible because `/tmp` survived 19 days of uptime. Every future
   campaign gets a committed launcher.
4. **H2's declaration is live, so its inertness is a real result, not a
   silent no-op.** Under finite SF, H2 cuts HNF demand misses 3,850,630 ->
   3,406,579 (-11.5%) while the tax does not move (84.83 -> 85.08). H2+H3 cuts
   them to 1,535,054 (-60%). A no-op declaration would also have disabled H3,
   and H3 plainly works.

**Pre-registered predictions and decision rules -- fixed before the run, per Sec6.6:**

- **Prediction:** H2/infinite-SF lands at 1.00-1.10x. Rationale: CAT, H2's
  real-silicon proxy, recovers the capacity tax completely on mos182.
- **PASS (H2/inf <= ~1.10x):** H2 removes the charge silicon levies. The
  instruments now meet. Proceed to W2. H3 demotes to a bounded capability claim.
- **PARTIAL (1.10 < H2/inf < 1.30x):** H2 recovers some capacity. Report the
  fraction; the paper survives but the benefit claim is weaker than CAT's.
- **FAIL (H2/inf >= ~1.30x):** H2 recovers nothing, anywhere. Hard stop. The
  paper has no working mechanism and the project needs a different design, not
  a different framing. Escalate to lead before any further work.
- **Consistency check:** H2+H3/inf should be indistinguishable from H2/inf --
  with an infinite SF there is no enrolment charge for H3 to remove. If they
  differ, H3 is doing something unmodelled and the H3 attribution in tab:h3sf
  is unsafe.

Seed mechanism (resolved): `SEED=<int>` is read by
`configs/deprecated/example/se.py` and passed to `_m5.core.seedRandom()`,
alongside `RUBY_RANDOMIZATION=1`. Seeds 1-3, matching the `_s1/_s2/_s3` naming
of the existing rows.

Effort: hours of compute, ~1 day with analysis. **Nothing else in this plan is
worth starting until this lands.**

## W2 -- Benefit under scrutiny. **W2.1 answered 2026-08-24; W2.2/W2.3 largely pre-existing. Off the critical path.**

- ~~**W2.1 P0-1 bandwidth-matched de-confound.**~~ **ANSWERED 2026-08-24, zero
  compute** -- `W2.1_DECONFOUND_2026-08-24.md`. The nine W1 runs already held a
  better discriminator than a matched point. The victim's L2 demand miss count
  is **invariant (714,210 -> 714,068, 0.02%)** while the fraction of those misses
  reaching DRAM goes **62.4% -> <=0.45%**. A throttle shortens queues and lowers
  miss *latency*; it cannot relocate a miss from DRAM to the LLC. The argument
  needs no assumption about the victim's response shape, which the matched-point
  design did. The throttle is real and small and is reported rather than denied:
  the stream loses **6.25% of delivered bandwidth (245 sd)** -- and that looks
  like a **cost of H2** (it also pays +1.70 MB of CXL writes, having lost its LLC
  writeback absorption), not the source of the victim's gain. **The MSHR band is
  downgraded to a robustness result** with a prediction registered in the memo.
- ~~**W2.2 Working-set sensitivity.**~~ **Largely already done** -- see the
  2026-08-24 correction. `tab:sens` sweeps WSS/LLC {24%, 53%, 97%} on the H2 arm
  and reads {--, 88.8%, 90.5%} recovered. The curve exists. What is still owed is
  repetition for variance and the de-confound at more than the 53% point.
- ~~**W2.3 LLC size / associativity sensitivity.**~~ **Largely already done.**
  `tab:sens` already covers the H2 arm at assoc {8, 12, 20} -> {90.8%, 91.9%,
  88.8%}. Recovery is 88.8-91.9% across both axes, so the result is not
  knife-edge and the paper can say so. Same residual owing: variance, and the
  de-confound at a second point.

Effort: **revised down again, 2026-08-24: ~1 week -> ~2 days -> under a day.**
W2.1 was the only genuinely unbuilt item and the existing runs answered it. What
remains in W2 is repetition for variance at the `tab:sens` points and, if
wanted, the MSHR band as robustness. **W2 is no longer on the critical path.**

## W3 -- Does *any* shipping machine levy H3's charge? New work, valuable either way.

You have measured "no" on SPR (non-inclusive + SF) and Bergamo (exclusive
victim L3). The hypothesis worth testing: **real snoop filters are provisioned
not to thrash**, in which case gem5's 4096x16 = 65,536 entries is
unrepresentative and the finite-SF story is a modelling artifact.

The obvious counter-candidate: **an inclusive-LLC Xeon back-invalidates private
caches by construction** (Broadwell-EP / Haswell-EP era, pre-Skylake-SP).
That is exactly H3's charge, in silicon, findable.

- ~~**W3.1** Try harder to make the SF thrash on mos182~~ -- **CLOSED
  2026-08-23, negative.** The experiment was already run and committed
  (`run_sfpressure.py`, `probe_mos182_sfpressure.jsonl`, `574f9fa`, analysed as
  `GPROBE_OUTCOME.md` S3.2). 62 MiB of streaming private footprint -- the whole
  socket's L2 -- leaves the victim at 1.020x, bounded at 1.0998x, with
  bandwidth flat across the ladder. The structural reason is S4.1: gem5's SF
  sits at 1.0x coverage of aggregate private L2, shipping parts at a multiple.
  Per this item's own stated consequence, **H3 is bounded to a capability
  claim.** See `W3.1_CLOSED_2026-08-23.md`.
- **W3.4** (new, 2026-08-24, no experiment) --
  `W3.4_H3_PERFORMANCE_CASE_2026-08-24.md` assembles H3's performance case from
  the committed campaigns so that **lead decision 4 can be made on numbers**.
  Headline: H3 is worth 2.512x -> 1.061x at a finite SF and **−3.45% at an
  infinite one**; no reachable silicon is in the paying regime (W3.1, bounded
  1.0998x); and, computed there for the first time, H2+H3 costs the *streamer*
  **33.3% of its instruction throughput** while pulling **2.51x the CXL bytes
  per retired instruction** (infinite SF, n=3). It also files an S5.1 defect:
  `H3_MODELCHECK.md`'s streamer-bandwidth caveat names no arm and moves the
  opposite direction to the labelled figure. **Three options are stated and
  none is chosen**; option 3 -- rebuild H3 as sound variant (b)/(c), which
  retains lines and so dissolves the entire measured cost -- is new to the plan
  as a *decision* rather than a build, and is the only one that makes H3
  stronger.
- **W3.2** Acquire an inclusive-LLC machine (Broadwell/Haswell Xeon) and repeat
  the L2-residency test. A positive here grounds H3 in silicon and repairs the
  gem5/hardware mismatch outright.
- **W3.3** Fold in the existing Sec9 "obtain an Arm server" question -- same
  experiment, different hierarchy.

Outcome is useful in both directions: either H3 gets silicon grounding, or the
paper gets simpler and more honest by dropping it.

## W4 -- Provenance audit. **W4.3 ledger built, W4.4 and W4.5 closed. W4.1/W4.2 are text edits, held on the lead's co-author decision.**

The panel referee's judgement on record: the unreproducible RocksDB 2.33x
sentence, *not* the nulls, is the decisive reject reason. One unsourced number
makes a referee assume the rest are unsourced too.

- **W4.1** Delete the RocksDB 2.33x sentence.
- **W4.2** Fix the superseded AMD figure: 6.92x was retired in-repo on
  2026-08-08 for 9.87x; an independent runner reads 9.97x. Five sites:
  `Sec1_Introduction.tex:111`, `Sec5_Evaluation.tex:353/354/388`,
  `Appendix.tex:163/168`, plus comment sites.
- **W4.3** Build a full provenance table: every number in the paper ->
  artifact file -> commit -> date -> runner. Any number that cannot be traced
  is deleted, not reconciled (Sec6.6).
- **W4.5** **CLOSED 2026-08-24** --
  `W4.5_SF_CAMPAIGN_PROVENANCE_2026-08-24.md`. The SF campaigns audited against
  their own artifacts, after `analyze_sf_fin.py` turned up a contradiction with
  provenance tables written hours earlier the same day. Three findings.
  (1) **`sf_inf_cells.sh` launched two of the four infinite-SF arms, not four.**
  `sf_qui_inf` and `sf_wb_inf` are from the uncommitted 2026-08-20 batch (F10),
  and the quiescent arm is the denominator of every tax in W1, W1.4, W1.5 and
  W3.4. Dated addenda correct W1.4, W1.5, W3.4, the `sf_inf_cells.sh` header and
  the W4.3 ledger; `analyze_sf_fin.py` now derives the provenance line from the
  `DONE_` sentinels on disk instead of asserting it.
  (2) **"Four days and one gem5 commit apart" is wrong toward over-caution.**
  There is no commit between the campaigns. One simulator binary (`gem5 compiled
  Aug 9 2026`, `src/` as of `56874f1d42`, no `src/` commit since), one `configs/`
  tree, workload binaries verified byte-identical to committed source, and a
  four-line `config.ini` delta. The hedge on the H2+H3 finite-vs-infinite
  agreement (151.06 vs 152.24 cyc per victim L2 demand miss, **-0.78%**) is
  withdrawn as stated. A bonus control fell out: `sf_qui_fin` and `sf_qui_inf`
  are distinct runs that agree **to the cycle** at all three seeds, because the
  quiescent workload never evicts from the SF.
  (3) **"gem5 `<hash>`" is not an apparatus.** A run is three artifacts with
  three vintages -- compiled binary, Python `configs/` read at run time, workload
  binaries. `0f37c28` names the config tree and `356e7b7d0e` the workload, which
  is why both attributions looked defensible and the error survived twice. Owed
  to edit-queue row 18: the provenance appendix reports the triple. Every
  "gem5 `<hash>`" cell in the W4.3 table is under-specified.
  One item stays gone under Sec6.6: the seed values for the 2026-08-20 batch.
- ~~**W4.4** Confirm no published number traces to the pre-D1/D2-fix binary.~~
  **CLOSED 2026-08-23, verdict "no"** --
  `benchmarks/e2e/oltp_index/patches/W4.4_AUDIT_2026-08-23.md`. Done the right
  way: the pre-fix binary was kept and the post-fix one rebuilt, then compared
  on the same host under the same sweep, rather than reasoning from the
  constants. The AMD codes read **identically zero** on both Intel hosts -- a
  signature, not noise -- so any run that used them is recognisable on sight,
  and the published Intel artifacts (clean capacity transitions,
  `cyc_per_access` present in all 245 mos182 and 423 moscxl rows, hit counts
  scaling exactly 2.5x with `DUR`) cannot have come from it. D2 never bit
  anywhere: every runner passes `-w` explicitly. All three hosts are now on the
  patched, self-reporting HEAD.

  **It found a worse defect than the one it was looking for.** The binary that
  produced the entire oltp_index campaign was built from a source state that is
  in no commit and no stash on either host -- a third state between `481115c`
  and the patched HEAD. Same class as the uncommitted `tab:h3sf` launcher
  (F10). Recorded as gone per §6.6, not reconciled. The numbers are sound; the
  apparatus is not pinned.

This is the highest-value non-experiment task in the plan.

## W5 -- Restructure around scope.

- **W5.1** Promote `tab:fused` from Sec3 to the headline. It is the paper's best
  experiment and it is immune to the MBA objection (MBA is core-scoped too):
  1.47x same-core, restructuring costs 36% of throughput, and CAT then recovers
  nothing (214.6 -> 215.0 Mtuple/s).
- **W5.2** Restate contribution (2) as "no deployed control can be *aimed* at
  the object." The current wording claims no alternative *helps*, which is
  false and which the MBA result falsifies.
- **W5.3** Disclose the L5 death and convert it to evidence. New table:

  | | dominant charge | CAT | MBA |
  |---|---|---|---|
  | Intel SPR | capacity | recovers | inert, costs 47% BW |
  | AMD Bergamo | rate | ~10x residual | recovers, costs 4% BW |

  Two vendors, two charges, two knobs, each useless on the other's machine,
  neither aimable at an object. This is a *better* argument for an abstraction
  than a residual number was.
- **W5.4** Promote the MLP result: on mos181 a 320 MiB LLC cuts HNSW's DRAM
  traffic 8.44x and returns 1.54x runtime; time-per-traffic falls monotonically
  (1.05 at 16 MiB -> 0.18 at 320 MiB). This defines *which* victims are harmable
  and pre-empts the reviewer's central objection about small magnitudes. It is
  currently buried as a "by-product" in a status document.
- **W5.5** Reconcile Sec2's concession with the H3 claim, pending W3.

## W6 -- The cost argument. **COMPLETE 2026-08-24.** W6.1/W6.2 measured, W6.3 sourced and overturned.

> **Primary outcome: `W6_COST_ARGUMENT_2026-08-23.md`**, written 2026-08-23 and
> covering W6.1, W6.2 and W6.3 together. **It was not read before the
> 2026-08-24 memos were written** -- F11, third instance, recorded in
> `W4.3_PROVENANCE_LEDGER_2026-08-23.md`. Read it first. It is the only place
> that records two facts nothing else does: `STREAMING_BIT` rides a
> `cacheCoherenceFlags` word already carrying `GLC`/`SLC` for shipped GPU bypass
> semantics, so that wire is in use rather than merely unextended; and
> `5bdfcd8e19` bundles a baseline change (it removed `is_prefetch ||` from
> `needCacheEntry`), so **no number we report is "\textsc{Streaming} vs. stock
> gem5"** -- within-campaign comparisons are unaffected. Its cost table's "1 PTE
> flag" and its summary sentence's "One PTE bit" are both **wrong** and are
> superseded below; queue row 32 stops the phrase reaching the paper.
>
> **Second outcome: `W6.1_IMPLEMENTATION_COST_AUDIT_2026-08-24.md`.** Static audit of
> both trees against their pre-STREAMING bases, zero compute. The assertions
> below were checkable and are now checked. Every structural claim holds -- and
> **one clause is wrong in our favour: there is no new PTE bit.** The decode
> reads the PAT selector, PCD and PWT, three bits the walker already reads on
> every walk, in two lines per leaf size. The paper's title is an implementation
> fact. Queue rows 26 and 27 carry it into the text.

Nobody adds hardware for 6%. People do add a PAT encoding for 6%.

- ~~**W6.1** Hardware cost: unused PAT slot 6, one PTE bit, TLB carry, one
  fill-path predicate.~~ **DONE, and the wording was too modest.** Measured:
  **zero** new coherence states, message types, SLICC structures or enumerations
  attributable to \textsc{Streaming} (the 1 event / 4 transitions / 2 actions in
  the diff are the finite-SF *model*, present in the WB arm too). **One bit
  through six structures** -- TLB entry, an unused encoding in `Request`'s
  existing coherence-flag bitfield, RubyRequest, one wire bit in
  `CHIRequestMsg`, TBE, one LLC tag bit -- plus **four lines of decision logic**
  and **no new PTE bit**. 43 attributable non-comment non-logging lines total.
  The "argue against datapaths that already exist for WC and MOVNTDQA" half is
  still owed as *prose*; the numbers it would cite now exist.
- ~~**W6.2** OS cost.~~ **DONE.** **564** non-comment kernel lines over Linux 6.8
  across 16 commits, **447** without the removable debugfs PTE-query facility,
  **one line** of new UAPI (`PROT_STREAMING`), no new syscall. I0/I1 enforcement
  is six rejection rules over VMA flags the kernel already maintains. There is
  more test (155 KUnit + 662 selftest lines) than implementation.
- ~~**W6.3** State the comparison honestly: CAT shipped for less benefit than
  this.~~ **DONE 2026-08-24, and the claim does not survive sourcing** --
  `W6.3_CAT_COMPARISON_2026-08-24.md`. Published CAT benefits are not small; the
  claim contradicts W5.3's own table, where CAT *recovers* the Intel capacity
  charge; and cache QoS shipped on a capability argument, not a throughput one,
  so there is no throughput promise to beat. **Do not write the sentence**
  (queue row 31).

  What replaces it is better. The SDM, read at source: CAT tags every request
  from a logical processor with its COS and consults that tag in the LLC
  **allocation** decision. That is H2's mechanism, in the same pipeline
  position, shipping since E5-2600 v3 -- so W6.1's proposed WC/MOVNTDQA analogy
  is the weaker one and should be dropped for CAT (queue row 30). The difference
  between the two is not the mechanism but what the label can name: CAT's is a
  *thread*, bound at context switch; ours is an *object*, bound at translation.
  **That is the paper's title as an architectural fact.** On footprint, CAT
  needs a CPUID leaf, a per-logical-processor association register, a file of
  mask MSRs per class, an architectural mask-contiguity rule, and a write on
  every context switch; \textsc{Streaming} needs no new architectural state at
  all.

**What W6 does not yet cover, and must say so.** (i) Lines bound *structural*
complexity, not silicon area, timing or verification effort; lead with the
structural zeros and cite the counts as context. (ii) **Only H2's cost is
established.** H3 as realized is variant (a) -- no-retention, `ReadOnce`, off by
default -- and the sound retention variants (b)/(c) are unbuilt, so nothing here
prices them. (iii) The kernel's exit drain (`WBNOINVD` to one CPU per core) is
counted in lines, not cycles; that is the §3 δ embargo's unresolved item, and
measuring the *streamer-side* cost of flush-behind -- which is **not** embargoed
-- is the obvious way to convert the largest unpriced item into a number. (iv)
The line counts must never be quoted without their counting rule, because three
correct ones disagree: **787** raw added lines over ten mechanism files from
base `037af838cf7a^` (which sits *after* the first three STREAMING commits and
so undercounts its own foundation by 89), **876** raw over the same files from
the true v6.8 base `e8f897f4afef` (17 commits, 32 files, 2,227 insertions), and
**564** non-comment non-blank kernel-wide excluding `tools/`/`Documentation/`/
tests, **447** of that without the removable debugfs facility. Comments and
blanks are ~36% of these files. This is §5.1's arm-identity rule relocated from
a figure to a cost table, and it is the reason two memos disagreed for a day.

**The comparison to make, with our own numbers** (`W5.3_L5_EVIDENCE_2026-08-23.md`,
folded into `W6.3_CAT_COMPARISON_2026-08-24.md`'s appended correction): CAT
recovers the mos182 co-run tax completely (1.00x under CAT12) and charges
**1.222x** for it with no co-runner present, because a way mask shrinks the
victim's own capacity; it leaves **12.4x** on moscxl, where the harm is
rate-class and a capacity knob cannot reach it; and on `tab:fused` it recovers
**nothing** (214.6 -> 215.0 Mtuple/s), because a core-scoped knob has no
boundary to draw when the streamer is the victim's own thread. That last row is
why the argument does not need the benefit magnitude to be large.

## W7 -- Necessity and benefit at the same operating point. The structural gap.

> **W7.1 done 2026-08-24, zero gem5 hours: `W7.1_KNOB_B_2026-08-24.md`.** Knob B
> (the batched probe) is built, correctness-gated on 30 configurations including
> odd `k` and prime morsel sizes, and tuned. `--probe-batch k` is new; at 0 or 1
> the binary takes the untouched `join_range` path. Against a 512 MiB hot table
> on mos181 it cuts `active_cycles_per_access` **132.63 → 77.49 (1.71x)** at
> k=32 and 1.46x at k=16 -- the MLP signature, confirmed before any gem5 time.
> **`k` amended 8 → 16** in the pre-registration, above the original, with the
> measurement that justifies it. Binaries build to `cxl_join_bench_w7{,.gem5}`;
> the pre-W7 binaries are hash-verified unchanged (F10). Also found: **F12**,
> `--check` is inert in `--mode morsel` and the fused-null runner passes it
> anyway.
>
> **No calibration run is needed -- the number already exists.** The completed
> 4 MiB arm of `GATE1_FUSED_NULL_CORRECTION_2026-08-15.md` is on disk at
> `/tmp/m22_mid_wb`: **hostSeconds 9,116.7 (2h32m)**, simInsts 178.6M,
> hostInstRate 19,590/s, at exactly the A0 geometry and options W7 needs. The
> T1 campaign that died at 1:11:28 was a *different* geometry (L2 256 KiB, not
> 2 MiB) and is not evidence about A0. 28 runs, independent, on a 256-core host
> at load 3.
>
> **Campaign script `w7_campaign.sh`, committed before it is run** -- W1's
> launcher was typed at the shell and never committed, and reconstructing it
> cost a session. A0 is reproduced exactly from `/tmp/m22_mid_wb/config.ini` and
> its logged command line, including `enable_DMT=true`, which the W1/`tab:h3sf`
> arms force off and this apparatus does not. Three deliberate differences are
> recorded in the script header: gem5 356e7b7d0e vs 3d0d1ca2, the `_w7` binary,
> and `RUBY_RANDOMIZATION` seeds 1-3 for variance. **A0/B0 is re-measured rather
> than compared across campaigns**, which is what makes the gem5 drift harmless.
>
> **Status: campaign launched 2026-08-24 01:04 KST**, 28 cells in parallel,
> driver pid 2029938, outdir `/tmp/w7`. Gated on two A0 smoke runs that came
> back clean: `matches_last_rep` 32,641 and `sum_last_rep` -700 identical
> across `--probe-batch 0` and `16`, so the batched path is bit-identical under
> O3CPU + CHI and not only on the host; and cycles per access 77.45 -> 55.44
> (-28.4%), so Knob B takes in simulation, which is P2's precondition. The
> smoke also says, directionally, that -28.4% may not be enough: lines in
> flight go 1.24 -> 1.72 against a P2 threshold of >= 6, and the campaign cells
> are colder than the smoke. A P2 falsification is a pre-registered outcome and
> gets reported as one. See `W7.1_KNOB_B_2026-08-24.md`, addendum.
>
> **Analysis script `w7_analyze.py`, committed before the data exists** and
> self-checked against the completed 2026-08-15 runs, whose numbers are already
> published. Every stat key it reads is verified to reproduce a published
> figure: LLC hit 53.58% (published 53.6), HNF fills 1,340,360 (the **last**
> column of `Cache_Controller.DataArrayWriteOnFill`, which is the HNF), DRAM
> read 12.09 MB, CXL read 66.76 MB. It computes P1/P2/P3/P5 and prints the
> cross-arm `matches_last_rep` gate, since `--check` is inert (F12). P4 is not
> computed -- it needs a resctrl arm SE mode cannot run.
>
> The self-check paid for itself twice. It rejected a first draft that defined
> fused bandwidth as CXL bytes / `simSeconds` (0.239) rather than the
> bench-reported `stream_bandwidth_gbps` (0.420) that the published table
> actually uses, which fixes what P2's ">= 2.0 GB/s" threshold is measured on
> *before* the data lands. And it surfaced queue row 33: the three figures in
> `GATE1_FUSED_NULL_CORRECTION_2026-08-15.md` section 4 -- 4.17 / 4.78 / 0.52
> GB/s -- are all the **2 MiB** hot table, the arm that same memo calls null by
> construction, while the 4 MiB "window" arm the section is otherwise about
> reads 0.42. The sentence is currently commented out in
> `Sec5_Evaluation.tex:336`, so nothing published is wrong; the row exists so it
> does not become wrong when someone uncomments it.
>
> **One pre-registered cell is deferred, with its reason.** The second A1 point
> at 8 cores exists to vary aggregate-L2 : LLC. At `--threads 1` the seven extra
> cores never fill their L2s, so 8 idle cores are indistinguishable from 2.
> Making it meaningful needs `--threads 8`, which changes the workload and not
> only the hierarchy -- a second knob, not a second A-point. Deferred, stated,
> not silently dropped.

Today the workload that proves necessity (fused) is explicitly *not* where H2
pays off: it runs at 0.52 GB/s against 4.17 achievable, MLP-limited by its own
dependent probe chain, so there is nothing for an admission fix to relieve. No
single workload both requires Streaming and is measurably fixed by it.

You now know the controlling property, from HNSW: the victim's misses must
serialise while the stream saturates. Build the fused variant that satisfies
both -- a genuinely serialising probe chain interleaved with a stream that
reaches the model's achievable bandwidth.

This is the experiment that would make the paper whole, and it is a principled
prediction rather than a fishing expedition, which matters under Sec6.6. Three
months is enough; seventeen days was not.

**Pre-registered 2026-08-23: `W7_PREREGISTRATION_2026-08-23.md`.** Designing it
changed the diagnosis. The paragraph above names MLP as the obstacle; the
fused-null correction memo's own counters show a **second, separable** one. At
its 4 MiB arm H2 cut HNF fills 59.6% and the victim's LLC hit rate moved
53.6% -> 53.9% -- H2 excluded the stream and the victim still did not become
resident, realising 25.8% of the available residency gain. The cause is
hierarchy compression: per-core L2:LLC is 2.5x in the model and 160x on the
8592+, so the protectable window `(2 MiB, 5 MiB]` holds exactly one power of
two and leaves 1 MiB of headroom at it. W7 is therefore a **2x2** (hierarchy x
probe batching), not a single workload rewrite, with five numeric falsifiers.
The one that matters is P4: raising MLP must not hand the recovery back to CAT,
because that would buy a benefit result by destroying the necessity result.

> **W7.2, 2026-08-24, written mid-campaign and before any morsel cell finished:
> `W7.2_A1_SIZING_2026-08-24.md`.** Two defects in Knob A, both found from the
> four completed `stream-smoke` references at zero compute cost.
>
> 1. **A1's LLC is 20 MiB, not 32 MiB.** gem5's `CacheMemory` indexes only
>    `2^floorLog2(num_sets)` sets; 32 MiB/20-way gives 26,214 sets, of which
>    16,384 are reachable. 37.5% of the array is allocated and never addressed.
>    A0 (4096 sets) and every L1/L2 in the campaign are exact. The
>    pre-registration's "64x" and "victim at 25% of LLC" are realized as **40x**
>    and **40%**. 32 MiB is unreachable at 20-way at all: the neighbours are
>    20 MiB and 40 MiB. This is **F9's defect class relocated to the LLC**.
> 2. **A1's bandwidth reference is LLC-resident.** Both A1 smoke arms read the
>    16 MiB fact array from CXL exactly once -- 16,777,216 bytes, identical to
>    the byte across wb and stream -- at 97.98% HNF hit rate. 9.27 GB/s is an
>    on-chip number and cannot be the denominator P2 calls "achieved fused
>    bandwidth." A0's reference is sound (5.03 passes against a 4-pass floor).
>
> **P2 is unaffected** -- it is evaluated at A0/B1. **P1 and P3 are both at the
> realized A1 point**, and W7.2 registers the reading in advance: a null there
> may not be reported as falsifying the pre-registered prediction, because the
> point measured is not the point registered; a positive is still a positive if
> labelled with the realized geometry per Sec5.1. The running campaign was **not
> touched** (apparatus rule); re-running A1 is a spending decision, and W7.2
> states the corrected-geometry and fact-size options without choosing.
>
> Also fixed and committed with it: `w7_analyze.py`'s comparability gate printed
> `PASS -- invariant` on an **empty** result set (`len(set()) <= 1`), an F12-class
> vacuous PASS caught by running the analyzer against partial data rather than
> waiting to trust it.
>
> **W7.2 addendum, same day.** The memo left A1's wb/stream indistinguishability
> unresolved between two readings; it is resolvable from a counter the memo did
> not read. `hnf.cntrl.cache.numDataArrayWrites` falls **1,475,801 -> 434,160
> (−70.6%)** at A1 under the stream policy, against −77.3% at A0. **H2 is active
> at A1**; the reading "the declaration is not reaching the HNF" is refuted. The
> difference is composition: 99.9% of A0's HNF data-array writes are fills, so
> removing them removes CXL refetches and buys 16.4% bandwidth; only 21.8% of
> A1's are, because a resident line is updated in place by the thrashing 512 KiB
> L2, so removing 1,041,641 of them changes no fill, no miss, no CXL byte and no
> bandwidth. H2's mechanism is hierarchy-invariant; its payoff is not — which is
> Knob A's thesis, arriving from the reference runs rather than the morsel cells.
> Filed as **edit-queue row 35** (eighth amendment): report H2's LLC effect on
> data-array writes, not fills, and never claim inertness without naming the
> counter. Nothing here rehabilitates A1 as a bandwidth point.

> **W4.6, 2026-08-24, zero compute and zero dependence on surviving runs:
> `W4.6_TAB_SENS_ASSOC_AXIS_2026-08-24.md`.** W7.2's `floorLog2` finding is not
> confined to W7 -- it lands on a **published table**. `b4run2.sh` holds
> `--l3_size=5MiB` while `p1batch.sh` sweeps `L3_ASSOC` over 8/12/20, so
> `tab:sens`'s three associativity rows ran at an effective **4, 3 and 5 MiB**,
> and its caption's "53% WSS" is right only for the 20-way row (the others are
> 64.7% and 86.3%). Sorted by WSS over effective LLC, all five non-trivial cells
> lie on **one monotonic curve** in both arms -- the published non-monotonicity
> (12-way worse than both neighbours) is not an associativity mechanism, it is
> the smallest cache. **The corrected table is stronger than the published one:**
> recovery flat at 88.8-91.9% across a 3-5 MiB effective LLC, a 1250-5000 KiB
> victim, 8-20 ways and a 52-98% WSS/LLC ratio. What must be dropped is the
> "across associativity" claim as an *independent* axis -- confounded, not false.
> Both launchers are committed, so the ledger's **VERIFIED** row stands; this is
> an F12, not an F10. Filed as **edit-queue row 36** (ninth amendment). Optional
> clean re-run: associativity over the exact set {5, 10, 20, 40}, 9 cells.

> **W4.6 addendum, same day: the sweep is closed.** Every cache geometry
> reachable from a committed launcher was enumerated. **Exactly three cells in
> the repository are affected, all LLC, all now documented** -- `tab:sens` 8-way
> (5 MiB -> 4), `tab:sens` 12-way (-> 3) and W7's A1 (32 -> 20 MiB). Every L1d,
> L1i and L2 in use is exact, as are 5 MiB/20-way, 2 MiB/16-way and 16 MiB/16-way
> LLCs and both snoop-filter geometries. The SF **cannot** be affected by
> construction: `CHI_config_8592.py` sets `size = sf_sets*sf_ways*64` with
> `assoc = sf_ways`, so `num_sets` is identically `sf_sets` -- set directly, not
> derived from a byte size. And the LLC is the only structure whose size *and*
> associativity are both swept, which is why one bad cell hid from each sweep.
> `--num-l3caches` is unaffected (it moves `start_index_bit`, not the set count),
> so W8's multi-slice restore arms are exact. Out of scope: the classic non-Ruby
> hierarchy used by W8's atomic boot. **No further campaign is at risk from this
> defect**; what remains is the paper edit already filed as row 36.

## W8 -- gem5 FS capability demonstration. Stretch, not critical path.

`GEM5_FS_OS_CONTRACT_PREREGISTRATION.md` is written and has never been run.
Closes the "is this implementable end to end" question: guest kernel encodes
PROT_STREAMING as PAT slot 6, the x86 walker classifies, CHI applies H2/H3.
Explicitly a capability demonstration, not a calibration claim.

**Opened 2026-08-24, while W7 occupies the simulator.** W3 is lead-blocked and
W4/W5 are held on the co-author decision, so W8 is the only unblocked item, and
it is the one that buys the sentence no other experiment can: every gem5
STREAMING number this project owns came from a pseudo-instruction
(`aggressor.c:24`, m5op 0x55), which validates the hardware half and says
nothing about I0/I1. Two artifacts existed that the plan did not name --
`GEM5_FS_OS_CONTRACT_SESSION_PROMPT.md` (410 lines, five gated tasks) and
`GEM5_FS_OS_CONTRACT_T2_AUDIT.md` -- and both were read before anything was
written, per F11's fifth fix.

**Gate T1 PASSED, on an existing build, with no new build time.** A prior
session already built `gem5/build_Intel_8592/gem5.opt` (25.1.0.1, compiled
2026-08-23), which the session prompt lists as absent. All three T1 checks
shown: `--build-info` runs; `enable_H3_streaming_bypass` is present in the
SLICC-emitted `params/CHI_Cache_Controller.hh` and in four other generated
files, so H3 survived the build rather than merely existing in the `.sm`; and
all 17 keys of the checked-in `build_opts/Intel_8592` resolve identically in
`build_Intel_8592/gem5.build/config`, including `PROTOCOL="CHI"`,
`NUMBER_BITS_PER_SET=256` and `USE_X86_ISA=y`.

**T2 is deliberately deferred, not skipped.** Its runner
(`intel_8592_4cpu_dirtax_streaming_supervised.sh`, the bounded serial trio the
T2 audit names as the next authorized measurement) launches concurrent O3+Ruby
arms, and 28 W7 cells plus three `sf_h3_inf_*` cells are already resident --
`hostguard.py` reads CONTENDED on my own load. T2 does not gate T3 or T4, so it
runs after W7 drains. That the supervised runner is **untracked** in the gem5
submodule is itself an F10-class defect and is fixed in the same commit.

**T3 apparatus committed before it is run:** `w8/streaming_gem5.fragment` (a
reasoned config fragment, not a dumped `.config`) and `w8/build_kernel_t3.sh`.
The fragment turns on `CONFIG_PAT_STREAMING` -- `default n`, and the single
highest-probability way this task produces a confidently-wrong null -- plus the
KUnit self-check, the PIIX4/8250 devices gem5's x86 platform actually has, and
KASLR off because gem5 loads the ELF `vmlinux` at its link address. The builder
gates on all three symbols surviving `olddefconfig` before it spends a minute
compiling. `CC=gcc-13`: the host default is gcc 15.2, newer than 6.8 accepts.

**T5(b) done and gated: the workload can now declare through the kernel.**
`cxl_join_bench` had no Streaming path at all -- every SE arm got its
declaration from the m5op, which is the whole reason W8 exists. `--declare
{m5op,mprotect}` now selects the channel; `mprotect` issues
`mprotect(base, len, PROT_READ|PROT_STREAMING)` (0x10, from the custom kernel's
`mman-common.h:14`) at all six declaration sites, page-aligned outward so no
part of the object is left unlabelled. Three gates, all shown:

1. On this host (kernel 7.0.0-28, no `CONFIG_PAT_STREAMING`) the run exits
   **12** with the reason printed. A silently-ignored `EINVAL` here would
   reproduce the T3 failure mode exactly -- a null that looks like a result.
2. An independent 20-line probe confirms `mprotect` **rejects** the unknown
   0x10 bit (`errno=22`) rather than ignoring it. This is what makes a
   *successful* mprotect in the guest evidence that the guest kernel accepted
   the declaration, instead of evidence that nothing checks.
3. The default arm is untouched: `--policy stream` with no `--declare` still
   aliases to wb natively and still calls the m5op under `-DGEM5`.

Ordering is contract, not detail, and holds at all six sites: allocate,
`build_table`, `fill_fact` (the writes), `prefault_region`, *then* declare.
Nothing writes `fact` after any declaration point -- checked, not assumed --
so dropping `PROT_WRITE` cannot turn a live path into a `SIGSEGV`. `declare` is
emitted into the JSON record, because an m5op row and an mprotect row are
different arms (Sec5.1). Built as a **new** binary,
`build/cxl_join_bench.gem5fs` (`make gem5fs`, sha256 `7a02cfc0`), so the W7
binaries and their recorded hashes stay untouched.

**Apparatus defect found, not yet fixed.** `w7_campaign.sh` writes its
completion marker after `wait` *unconditionally* -- including under `W7_DRY=1`,
which returns from `launch` before starting anything. The 01:03 dry run
therefore left a `w7.done` in the real output directory, and at 01:18 that
marker said the campaign was finished while all 28 cells were provably still
burning CPU. F12 again: an artifact that is read and believed and does not do
what it says. The marker was removed and the wait re-armed on the driver pid.
The script is **not** being edited while bash is still executing it -- an
in-place edit shifts the byte offsets of a running script. It gets a
`[ "$DRY" = 1 ] && exit 0` before the marker once the driver exits.

**T3 gate stated, T4 built, T5 armed.** `nm` on the linked `vmlinux` shows 53
streaming symbols, so the code is in the image and not merely in the `.config`
-- including a debugfs `pte_query` that resolves addresses in `current->mm`.
That relocated the T5 gate somewhere better than the simulator: the benchmark
now reads its own PTE back after `mprotect` and decodes `PAT<<2|PCD<<1|PWT`,
the same three bits `pagetable_walker.cc:360-390` reads, and prints `GATE=PASS`
only on slot 6. gem5 was rebuilt with two new counters --
`streamingTranslations` at the walker's `doTLBInsert` (once per classification,
so a hot TLB entry cannot inflate it) and `tlb.streamingAccesses` (once per
tagged access). Declaration and consumption are counted separately so the
second can never be quietly reported as the first.

The image is `w8-busybox-streaming-r1.img`: a busybox rootfs, 257 MiB, built
unprivileged with `mke2fs -d` under `fakeroot`, contents verified with
`debugfs` before any boot. It is **not** the v2 image -- that one is gone from
all three hosts and its binary had a `--line-stride` option no revision in this
repository contains -- and it says so in its own `/etc/W8-PROVENANCE`.

`w8/t5_analyze.py` was written before the first restore, and fixes four gates
in advance: G1 walker classifications (zero in wb, non-zero in mprotect), G2
the in-guest readback, G3 tagged accesses, G4 the run actually completed. It
states in its own docstring that **no performance comparison is licensed by
these arms** -- the FS geometry has never been calibrated against SE, the runs
are single-rep and cold, and W8 is a capability demonstration. A speedup here
would not be evidence for L3, and the script says so where a reader will hit
it before the numbers.

**T5's launcher, written while T4 boots, refuses a trap the committed one does
not see.** `w8/run_t5.sh` is a wrapper on `gem5/scripts/fs_restore_chi_8592.sh`
-- same principle as `boot_t4.sh`, the committed script is not edited. The
difference that matters is `DISK`: the restore launcher defaults to
`x86-ubuntu-18.04-img-hashjoin-v2`, and T4's checkpoint was taken on the
reconstructed busybox image. Restoring across that mismatch **does not
necessarily fail loudly** -- the guest's restored in-memory ext2 state would
simply address blocks belonging to a different filesystem -- so the wrapper
reads the boot image straight out of the checkpoint's own `config.json` and
refuses unless it is the image being attached. Three further gates: exactly one
`cpt.*` with a non-empty `m5.cpt`; no gem5 process still owning the checkpoint
directory (`m5.cpt` is written *after* the directory appears, which is the parse
race the committed script warns about in prose and does not enforce); and a
non-empty arm script, since an empty readfile is precisely how the boot pass
tells init "no benchmark" and would here produce a clean stats file with no
workload in it. Gate 1 and the image extractor were both exercised against the
in-flight boot. One arm per invocation, serially, so each arm's gate is read
before the next starts.

**W8.1, found while writing that launcher: the m5op is SE-only, and that is a
gift.** `W8.1_M5OP_IS_SE_ONLY_2026-08-24.md`. `pseudo_inst::setstreaming`
marks pages in `process->pTable`, the SE `EmulationPageTable`; in FS
`tc->getProcessPtr()` is null, so it warns and returns. **No FS branch exists.**
Every gem5 STREAMING number this project owns was declared through that
instruction -- which is fine, they are SE runs, but it is exactly the gap W8 was
opened to close. `t5_analyze.py` inferred each arm's expectation by substring
(`"stream" in arm`), so it would have scored the FS m5op arm **G1 FAIL, G3 FAIL**
for behaving exactly as the simulator is built to behave. Its own docstring
never claimed that -- G1 and G3 named only `wb` and `mprotect` -- and the
pre-registration mentions the m5op only for the T2 **SE** sweep. F12 again,
caught before the data existed. Corrected, the arm is a control that cannot be
faked: same guest, kernel, binary, flags and checkpoint, one different
`--declare`, and the harness path yields **zero** classifications while the OS
path yields them through a page table a real kernel wrote. Fixes: an explicit
`ARMS` table replacing substring inference (unknown dirs report `UNKNOWN ARM`
rather than being guessed at); a new **G5** requiring gem5's own
`"called outside SE mode"` warning in the m5op arm, so a documented no-op is
never confused with an unexplained zero; and `run_t5.sh` tees gem5's stderr to
`<outdir>/gem5.log`, since that warning goes nowhere else. **No published claim
changes** -- the SE results were produced in SE mode, where the m5op is the
intended mechanism. What changes is what the FS arm demonstrates, and it now
demonstrates more.

> **W8.1 addendum: SE and FS declare differently and then converge on one line.**
> `TLB::translate` has a single TLB-miss handler branching SE (`tlb.cc:477`,
> the m5op's `EmulationPageTable::Streaming` flag) against FS
> (`pagetable_walker.cc:364/:389`, PAT slot 6 decoded off a real PTE). Both fall
> through to the same tail, where streaming has exactly one consumer:
> `req->setCacheCoherenceFlags(Request::STREAMING_BIT); stats.streamingAccesses++`.
> **Everything downstream of the TLB is byte-identical between the SE corpus and
> the FS arms** -- the modes differ only in who writes the bit into the TLB
> entry. That is the substitution W8 exists to demonstrate, and it is a
> substitution of the declaration only. Two cautions fall out:
> `streamingTranslations` is **structurally zero in SE** (no walker), so an SE
> zero is not a failed declaration -- `streamingAccesses` is the cross-mode
> counter; and `streamingTranslations` also counts **functional** walks (the
> increment sits above the `if (!functional)` guard), which cannot affect a gate
> that asks only zero-versus-nonzero but means the magnitude may not be quoted as
> demand classifications. Filed as **edit-queue row 37** (tenth amendment): the
paper never answers "is a pseudo-instruction the same as an OS declaration?",
and now it can, in one sentence. The row is licensed by source reading alone,
but if the claim is to be stated as *demonstrated* rather than *argued* it
should wait for T5, which is what T5 produces.

> **W8.1 second addendum: the rest of T5's analyzer contract, checked before the
> run.** G2's `GATE=PASS(slot6=Streaming)` (`cxl_join_bench.cpp:293`, `cerr`),
> G4's `"status":"ok"` (`run_morsel`, `:1650`, `cout`) and its
> `W8-RCS-BENCH-EXIT` echo, and G5's gem5 warning all exist and all reach the
> console -- init is pid 1 with the console on fds 0/1/2 and `exec` inherits
> them. **Every flag the three arms pass is accepted by the guest binary**; an
> unrecognized one would abort the arm with `exit 2` before any output and would
> have surfaced only after a full restore. The image's `/etc/W8-PROVENANCE`,
> read with `debugfs` without booting, records the same sha256 as
> `build/cxl_join_bench.gem5fs`, so the binary checked is the binary in the
> guest. **Trap left in place:** the *host* build `build/cxl_join_bench` is dated
> 2026-08-11, predates `--probe-batch`, and exits 2 on it -- a failure that looks
> like an arm flag error and is not. Not fixed: the image is frozen and nothing
> here needs the host binary.

> **W7's analyzer now carries the [F9.4] marker at the lines that compute A1's
> numbers.** W7's A1 cell is one of the three floorLog2-affected cells repo-wide:
> it requests `--l3_size=32MiB --l3_assoc=20`, which is 26,214 sets, of which
> `floorLog2` leaves 16,384 reachable -- **20 MiB effective**. A0 is clean
> (5MiB/20 = 4,096 sets exactly) and so are both L2s. The consequence runs in the
> safe direction: A1's 8 MiB hot table occupies 40% of its LLC rather than the
> 25% the pre-registration reasoned about, so **A1 is a harder cell than
> intended, not a softer one** -- a positive result there is not inflated by the
> defect. The running campaign was not disturbed (apparatus rule); the analyzer
> instead prints a geometry-as-simulated banner above the cell table and tags
> P1, P3 and P5 inline, so the marker travels with the number to whoever reads
> the output. `w7_analyze.py` is not executed by `w7_campaign.sh`, which is why
> editing it mid-campaign is safe.

> **T5 gate 2 has now been exercised in the passing direction, not only the
> failing one.** Against T4's real `config.json` (written at boot start, so
> readable while the boot runs): exactly one `image_file` exists, at
> `/system/pc/south_bridge/ide/disks[0]/image/child`; it resolves to the busybox
> image so the gate passes, and substituting the Ubuntu image makes it refuse.
> This also retires a latent quirk -- the extractor's `return` does not unwind
> the recursion, so with several `image_file` entries `head -1` could have picked
> by traversal order; there is exactly one. A gate seen only to fail is not known
> to protect anything, and gate 2 is the one whose failure mode is silent
> corruption rather than an error.

> **T5 gate 1 was wrong, and T4's checkpoint proved it before a run was spent.**
> A stock gem5 FS checkpoint leaves *two* `cpt.*` directories: `simulate.py`'s
> `checkpoint()` runs `os.makedirs()` on the literal, unsubstituted `"cpt.%d"`
> that `Simulation.py` hands it, and only afterwards does C++
> `CheckpointIn::setDir` (`serialize.cc:142-147`) `csprintf` the tick in and
> create the real `cpt.<tick>`. The empty `cpt.%d` is upstream behaviour and
> appears on every FS checkpoint. Gate 1 tested "exactly one `cpt.*`", so it
> would have refused **every valid T4 checkpoint**. Corrected to "exactly one
> `cpt.*` holding a non-empty `m5.cpt`", which still refuses when two real
> checkpoints are present, and which prints the full directory inventory when it
> does refuse. Also recorded at the gate: a non-empty `m5.cpt` does **not** mean
> the checkpoint is complete -- T4 wrote `m5.cpt` at 03:02 and its second physmem
> store at 03:03, so completeness rests entirely on the process-ownership check.
> Verified live: against T4's still-writing checkpoint the count check passes
> (the `cpt.%d` is correctly ignored) and the ownership check correctly refuses.

> **W7's registered reading rule now prints with W7's numbers.** W7.2 had already
> recorded both the 20 MiB realization and the asymmetric reading it forces --
> a falsified P1/P3 at the realized point may not be reported as falsifying the
> registered prediction, while a confirmed one is a real positive that must be
> stated at the realized point. That rule lived only in the memo; the analyzer
> that computes and prints P1 and P3 said nothing. It now prints the rule, and
> the note that P2 is unaffected because it is evaluated at A0 against a
> reference that is sound (5.03 CXL passes against a 4-pass floor), while the A1
> smoke references are on-chip bandwidths and not streaming references. Nothing
> new was discovered here: F11 fix #5 (`ls experiments/asplos/ | grep -i X`
> first) caught that the finding was already recorded, and the work became
> carrying it to the point of use rather than restating it.

> **W8.2: the kernel's streaming kunit suite ran and passed inside the simulated
> machine** -- `pat_streaming`, 8 cases, `pass:8 fail:0 skip:0`, at guest t=4.82 s
> of T4's boot, free evidence produced on the way to the checkpoint. W6 counted
> these tests as 830 lines in the cost argument; nothing recorded that they had
> ever been *executed*. `pat_streaming_msr_test` reads `MSR_IA32_CR_PAT` on the
> live CPU and asserts slot 6 holds `PAT_WB_ENCODING`, and its `kunit_skip` for
> non-full-PAT layouts was not taken, so the assertion really ran -- which makes
> the fallback property concrete: the signal is the *slot index*, the byte in it
> is ordinary write-back, so a Streaming page is a WB page on silicon that does
> not implement the contract. Filed as **edit-queue row 38**, with a caution that
> must travel with it: the suite covers the encoding half only and never asserts
> that `PROT_STREAMING|PROT_WRITE` is refused. That is I1's immutability rule; it
> lives in `mm/mprotect.c` and is covered by userspace selftests **T4 did not
> run**, so immutability remains the one part of I1 with no live evidence.
> Also recorded: T4's console is ISO-8859, so plain `grep` calls it binary and
> prints nothing -- a search for a marker silently looks like an absent marker.
> Use `grep -a`. `t5_analyze.py`'s `stats.txt` reader hardened to match its
> console reader.

> **W8.3: T4's gate written down while the checkpoint was still being written.**
> T4's acceptance criterion existed nowhere -- T3's did, T5's did -- so it was
> stated before the outcome was known rather than inferred from it. Six criteria:
> guest reaches userspace, the mechanism is live in the *running* kernel, a clean
> boot with no fault of any kind, exactly one `cpt.<tick>` with a non-empty
> `m5.cpt` and gem5 exited, the checkpoint's recorded image is the one T5 will
> attach, and gem5 exits 0. Four met at the time of writing; the two checkpoint
> criteria left open. **If either fails, T5 does not start.** The boot-log audit
> found 23 warnings, all boilerplate, and one worth chasing: `wbinvd
> unimplemented`. Traced and cleared -- streaming's transition flush is
> `clflush_cache_range` (`mm/streaming.c:322`), not `wbinvd`, and `clflush` *is*
> modeled, expanding to a `clflushopt` microop that carries `Request::CLEAN |
> INVALIDATE | DST_POC` with Ruby's Sequencer branching on
> `isCleanInvalidateRequest()`. Limit kept explicit: that establishes the request
> is decoded and recognized, **not** that a guest `clflush` was traced through
> CHI to the HNF -- and T4 booted `--caches` while T5 restores into Ruby/CHI.
> Also flagged: gem5's own boot log is in `/tmp` and uncommitted, which is the
> F10 failure mode, and must be copied into the outdir.

---

# Stop-work list

Plan B fails if the existing campaign eats the runway. Stop:

- **The A6 DuckDB co-run re-run.** Forecast in its own document to produce "a
  bounded non-verdict." It cannot change the paper.
- **mos182 node-2 unblocking** (package-1 latency ladder, `latency_chase`
  GLIBC_2.38 rebuild). Not needed by anything above.
- **Further e2e workload hunting.** Six is enough, and the reason the magnitudes
  are small is now understood (W5.4), not mysterious.
- **GAPBS / HNSW gate work**, except harvesting the MLP number for W5.4.
- The queued `-n 4` parity defect and the A6.12 settle criterion -- both only
  matter if the co-run campaign continues.

---

# Sequencing

| phase | weeks | work |
|---|---|---|
| 0 | 1 | **W1** (decisive cell) + **W4** (provenance audit) in parallel |
| 1 | 2-4 | ~~W2~~ ~~W6~~ **W5 (restructure) only** -- W2.1 answered and W6 complete, both 2026-08-24 |
| 2 | 5-9 | W3 (H3 grounding), W7 (necessity+benefit convergence) |
| 3 | 10-12 | W8 if it fits; full rewrite; 18pp -> target length |

Phase 1 onward is conditional on W1 passing. **W1 passed 2026-08-24; phase 1 is live.**

---

# Lead decisions needed

1. **Venue and date.** Everything above is sized to roughly three months;
   confirm the actual target.
2. **W3.2:** acquire an inclusive-LLC machine? Folds into the existing Sec9
   Arm-server question.
3. **Co-author communication.** `~/STREAMING_Paper/` publishes on write, so any
   restructure is visible immediately. Deciding to skip Sep 9 should reach the
   co-authors from the lead, before the text starts moving.
4. **Does H3 survive?** Deferred pending W3, but flag it now -- it changes the
   paper's shape. **Equipped with numbers 2026-08-24:
   `W3.4_H3_PERFORMANCE_CASE_2026-08-24.md` states the three options -- keep
   variant (a) and disclose its price, cut H3, or rebuild it as sound variant
   (b)/(c) -- with the measured cost of each. The decision is unchanged and
   still the lead's; only the ignorance is removed.**
5. `EUNJI_QUESTION_DRAFT.md` still must be sent by the lead personally.

# Next 72 hours

1. Resolve the seed question in b4run2.sh, then launch the three W1 runs on
   mos181 (idle, no contention).
2. Start W4.1 and W4.2 -- both are pure deletions/corrections, needed under
   every outcome including a hypothetical return to Plan A.
3. ~~Rebuild the D1/D2-fixed binary on mos181, now unblocked.~~ **Done 2026-08-23; all three hosts patched.**

> **2026-08-24, T5 gate 1 hardened again — gem5 selects the checkpoint by a
> different rule than the gate validated it by.** `-r 1` does not mean "the
> checkpoint you just checked". `configs/common/Simulation.py:200-215` enumerates
> `cpt.*` with `re.compile(r"cpt\.([0-9]+)").match()`, sorts by `int(tick)`, and
> takes `cpts[0]` -- the **lowest** tick. Two findings. First, the reassuring one:
> the empty `cpt.%d` upstream leaves behind fails that regex, so it is invisible
> to gem5 and `-r 1` does land on the real checkpoint -- the two-dir situation is
> genuinely safe, not merely tolerated, and `-r 1` `fatal()`s rather than guessing
> if nothing matches. Second, the gap: a stale, interrupted `cpt.<lower-tick>`
> with an empty `m5.cpt` would pass the "exactly one non-empty `m5.cpt`" test and
> then be silently restored by gem5 in preference to the good one. The gate now
> additionally requires that the directory gem5 will pick is the directory it
> validated. Exercised over four synthetic shapes -- real T4 shape PASS, stale
> lower-tick REFUSE, two genuine checkpoints REFUSE, no checkpoint REFUSE -- and
> against the live T4 directory, read-only, PASS. No stale dir is present today;
> the hardening is for the re-runs, since T5 restores this checkpoint three times.
> Separately, `/tmp` on mos181 is **tmpfs**, so `/tmp/w7` (10 completed cells,
> ~20 host-hours) and `/tmp/w8_boot.log` live in RAM only; both are now mirrored
> to `~/tmpfs_backup/` on ext4. That is the F10 lesson applied before the loss
> rather than after.

> **2026-08-24, T5's liveness criterion, fixed before any arm runs.** W8's
> 90-minute zero-byte-`stats.txt` tripwire fired on T4 at 02:55 and is still true
> at 03:23. It does not apply: a boot-and-checkpoint pass dumps stats only at
> `simulate()` exit and `empty.rcS` issues no `m5 dumpstats`, so zero bytes for
> the whole boot is the expected state, not a symptom. T4 is demonstrably working
> — pid 2069959 `R` at 99.9% CPU, console at `W8-GUEST checkpointing...`,
> `store2.pmem` growing 13.0 → 85.7 MB between 03:16 and 03:22. T5's arms will
> trip the same wire for the same structural reason, so the replacement is
> registered now rather than chosen with a run in front of me (§6.6): process
> alive with advancing CPU time; Ruby's own deadlock detector as the real hang
> guard, since a CHI deadlock panics rather than spinning silently; and the
> wall-clock timebox treated as an escalation to the lead, not a liveness test.
> Stated in the memo as **weaker** than what it replaces — it cannot separate
> "simulating correctly" from "simulating something wrong quickly". The stronger
> fix (configure a periodic stats dump, restoring the original tripwire) is
> declined only because it would change the apparatus mid-campaign.
> Process note: this plan entry lands one commit after the memo it belongs to
> (38ae985), which is the F11 fix-#4 pairing rule slipping by one commit.

> **2026-08-24, T5 arm order fixed before data: `wb` → `stream_mprot` →
> `stream_m5op`.** Discovered on pre-flight that `fs_restore_chi_8592.sh` has
> never been executed — `logs/fs_restore_chi/` does not exist in either gem5 tree
> — and that no FS + Ruby/CHI run exists anywhere in the project. T5 arm 1 is
> therefore the first exercise of an untested launcher *and* a measurement, so a
> failure there is most likely apparatus, not science. Statically verified what
> could be: memory layout equals T4's boot (256 GiB / 128 GiB CXL), CPU count
> matches (the launcher infers `N=2` from the substring `2cpu` in the checkpoint
> *name* — fragile, noted), `--restore-with-cpu=O3CPU` against an Atomic
> checkpoint is the supported flow, and `-r 1` resolves to the real tick dir.
> `wb` runs first because it is the control and needs no streaming machinery, so
> a broken restore surfaces without being entangled with declaration or the
> walker; `stream_m5op` runs last because its expected result is zero, which is
> indistinguishable from a broken run until a positive arm has shown a non-zero
> count is reachable. See W8.1 third addendum.

> **2026-08-24, T5 arm scripts read directly.** Name→declaration mapping correct
> in all three — the one mapping whose inversion would invert every gate rather
> than fail visibly. Each arm brackets the benchmark with `m5 resetstats` /
> `m5 dumpstats`, so the gate counters exclude boot: the `wb` control's expected
> zero is a statement about the workload, not about when counting started. All
> three run `--probe-batch 0 --reps 1 --warmups 0`, so O1 is off and every arm is
> single-rep cold — a second, independent reason no performance comparison is
> licensed here.

> **2026-08-24 03:29, T4's gate PASSES; T5 is unblocked.** gem5 exited at 03:27
> after 1 h 59 m. Checkpoint complete (~524 MB: `m5.cpt` 20,339,682 B plus three
> physmem stores), sibling `cpt.%d` empty as predicted, directory released —
> verified by process *name*, because a `pgrep -f` on the outdir string matched
> my own shell wrapper, the ancestor-argv trap seen live a second time. Two
> things to carry forward. (1) `m5.cpt` is finalized **last**, growing 59× after
> it first becomes non-empty (344 KB at 03:02 → 20.3 MB at 03:27, after all three
> stores), so no sample of its existence or size before gem5 exits can tell a
> finished checkpoint from a partial one — the process-ownership check is the
> only thing in gate 1 that establishes completeness, not a belt-and-braces
> extra. The `run_t5.sh` comment, which had this backwards, is corrected with the
> measured timeline. (2) **G-T4-6 is not evaluable as written**: T4 was
> backgrounded and its exit status was never captured anywhere, so the number is
> gone and is reported as gone (§6.6). Clean termination is established by other
> means (`Exiting @ tick ... m5_exit`, 0 fatal/0 panic, final `stats.txt`
> written, guest at its designed terminal state, 0 kernel faults) and is
> explicitly weaker — this must not be cited as "gem5 exited 0". The gap does not
> recur: `run_t5.sh` already captures `PIPESTATUS[0]` and propagates it. Added
> `DRYRUN=1` to `run_t5.sh` so the gates can be exercised against the real
> checkpoint without spending a run; all three arms pass, no side effects.

> **2026-08-24 03:32, T5 geometry as instantiated.** Read from the running arm's
> `config.json`. Two findings. F9.4 does **not** touch T5 — every level's set
> count is an exact power of two (L1I 64, L1D 64, L2 2048, LLC 4096) — checked,
> not assumed, so T5 needs no `[F9.4]` marker and the affected set repo-wide
> stays at three LLC cells. But T5's **aggregate LLC is 10 MiB, not 5 MiB**:
> `--num-l3caches=N` with `N=2` builds two 5 MiB HNF slices, while W7's SE cells
> pass `--num-l3caches=1` at the same nominal `--l3_size=5MiB`. So T5's machine
> has twice W7 A0's last-level capacity at the same flag value. Registered before
> any T5 number exists: no T5 figure may be placed beside a W7 figure, and every
> T5 quantity must name "2 × 5 MiB HNF slices, 10 MiB aggregate" at its point of
> use (§5.1). Third independent reason no performance comparison is licensed out
> of T5, and a caution for any future FS↔SE calibration.

> **2026-08-24 04:00, W7 P2 is FALSIFIED — the campaign's first hard negative.**
> `W7.3_P2_FALSIFIED_2026-08-24.md`. Written with 22 of 28 cells complete and the
> A0 2×2 done at n=3, deliberately *before* the campaign drained, so the
> falsification cannot have been shaped by what the remaining cells say. At
> A0/B1 H2 (k=16, 5 MiB/20 LLC, 2 MiB/16 private L2, 4 MiB hot table, 203 ns CXL)
> the fused kernel holds **1.77 lines in flight** against a registered target of
> ≥6 and an explicit floor of <3, and **0.558 GB/s** against ≥2.0. Not marginal
> (seed sd ≤0.16%) and **not protected**: W7.2's asymmetric reading rule covers
> only P1 and P3 at the mis-sized A1, and says in terms that "P2 is unaffected …
> A0's reference is sound."
>
> The finding underneath the verdict is that the pre-registration's *explanation*
> of a sub-3 result — "the batching did not take" — is itself false. Batching
> took: **−20.7% cyc/access under H2 and −20.1% under WB** (so it is orthogonal
> to admission), **+26% bandwidth**, at **unchanged traffic** (CXL 61.53 → 61.54
> MB), which is the signature of a pure rescheduling knob that engaged. So the
> verdict is the third reading the pre-registration did not enumerate: the knob
> works and this kernel's expressible MLP is ~1.8 lines, not ≥6. The target was
> not unreachable — the A0 stream-smoke sustains **14.62 lines** on the same
> machine at 3.89 genuine CXL passes, so ≥6 was 41% of a measured ceiling and the
> join reaches 12% of it. **The limit is the kernel, not the memory system.**
> `k` is not retuned; W7.1's addendum pre-committed to that and its 1.72-line
> smoke predicted the falsified quantity to within 3% before launch.
>
> Three things recorded against my own report. (1) The registered `lines` metric
> is `GB/s × 3.1719` — a monotone rescaling — so **P2 is one test stated twice,
> not two independent halves**, and must not be presented as doubly falsified.
> (2) No MSHR-occupancy stat exists in this build and `lqAvgOccupancy` is
> forbidden as a substitute; both limits were registered before the data, so per
> §6.6 and row 35 the metric is not swapped after seeing the result. (3) The
> pre-registration's strong-negative story required "P3 fails with P1 and P2 both
> confirmed" — **that story is now unavailable**, and any W7 negative must be
> reported in the weaker form.
>
> What A0/B1 still buys, reported as an observation and not as a P2 outcome:
> H2 removes **59.8% of HNF fills** and **22.6% of DRAM reads** there while
> moving time by **1.23%**. §5.2 applied before believing that null — the 4 MiB
> hot table does not fit the 2 MiB private L2, so it is not an L2-residency
> artifact. That is the L3 problem stated quantitatively. P1/P4/P5 stay open;
> P3 completed at n=3 (+0.63%) and is not adjudicated in this memo.

> **2026-08-24 04:15, W7 P5 constrained, and a disclosure I would rather not
> make.** Addendum appended to `W7_PREREGISTRATION_2026-08-23.md`. With 22/28
> cells in, three of P5's four gaps are visible (A0/B0 +0.53%, A0/B1 +1.23%,
> A1/B1 +0.63%; A1/B0 unseen). Because the test is `gap(A1/B1) > max(singles)`
> and 0.628 < 1.234 already, **P5's binary verdict is fixed no matter what
> A1/B0 says: the 2×2 fails the ordering test**, and A0/B1 — not the convergence
> cell — carries the largest H2 effect in the campaign. So the addendum is
> explicitly *not* a blind pre-registration of P5 and says so; only P1 is still
> genuinely blind. Four rules registered before A1/B0 lands: (R1) the B axis
> reached 1.77 of ≥6 lines, so any small B contribution is **confounded** and
> may not be read as evidence about O1 — the direct analogue of W7.2's A1 rule;
> (R2) a "2×2 justified" outcome would have had to be stated at the realized
> point; (R3) the "either knob delivers ≥5%" escape clause is **dead** — every
> H2 effect in W7 is ≤1.23%, so the honest statement is "no knob tested
> suffices," registered now so neither reading can be picked later; (R4) **F12
> in my own analyzer** — its P5 else-branch printed "a single knob already
> suffices", which is a dominance branch asserting a sufficiency claim that the
> data contradicts. Wording fixed, computation byte-identical, annotated in
> place with date and reason. §4's strong-negative story ("P3 fails with P1 and
> P2 both confirmed") is **unavailable** now that P2 is falsified and may not be
> quoted as live.

> **2026-08-24 04:40, two facts about the W7 machine that were never on record.**
> `W7.4_PREFETCHERS_AND_THE_CXL_ANOMALY_2026-08-24.md`, plus an (R5) addendum to
> the pre-registration. Both from re-reading committed artifacts; no new runs.
>
> **(1) The W7 machine prefetches, hard, and this was undisclosed.** The
> instantiated `config.json` carries `MultiPrefetcher` at both L1D (Stride +
> DCPT) and L2 (Stride + Tagged) on both cores, running at **0.547 prefetches
> per demand access** at B0. §5.1 disclosure now owed on every W7 figure,
> `W7.3`'s included. It does not change P2's verdict and it cuts against the
> kernel: the "1.40 lines" serial baseline is what the loop sustains *with*
> aggressive prefetching, and knob B raises demand accesses 64% while cutting
> prefetches 43% (ratio 0.547 → 0.189) because k=16 scattered probes are less
> prefetchable than a strided scan. It also supplies a **measured** candidate for
> what `W7.3` §6 could only hypothesise: the 14.62-line smoke ceiling is
> substantially a *prefetcher's* achievement on a pure sequential scan, so the
> ≥6 target was calibrated against a mechanism the fused loop cannot invoke.
>
> **(2) H2 reads FEWER CXL bytes than WB, at every cell, and nothing predicts
> that.** 8.3% vs 0.5% of stream traffic absorbed on-chip at A0; 47.4% vs 31.5%
> at A1. Non-admission should cause *more* re-fetches. Prefetch differences are
> **ruled out by measurement** (ratios identical to three decimals within each
> cell). Leading untested candidate is **inclusion victims** — under WB an
> admitted fact line is evicted from the thrashed LLC, back-invalidating a live
> L2 copy and forcing a CXL re-fetch, which H2 avoids by never admitting it. If
> true that is a real, previously unarticulated benefit of non-allocation.
> Registered before P1 lands: **unresolved**, may not be reported as a benefit
> until tested (§6.6), may not be dismissed as noise (5.2 MB at A0, 10.6 MB at
> A1, stable over 3 seeds), and stands as a pending question against every W7
> traffic figure including `W7.3` §8's "22.6% of DRAM reads removed."
>
> **(2a) A1 is not the streaming regime, and this reaches P1's and P3's cells.**
> `W7.2` excluded the A1 *smokes* because the 16 MiB fact array fits the 20 MiB
> effective LLC; the same defect reaches the A1 **morsel** cells and was not
> propagated. A1's WB arm absorbs **31.5%** of the fact stream on-chip against
> A0's 0.5%.
>
> **(R5) P1's hit-rate half may be arithmetically unevaluable.** A1/B1's WB arm
> hits **97.61%**, leaving 2.39 points against a required **+15**. Registered
> blind to both A1/B0 arms: if A1/B0's WB hit rate is ≥85%, P1's hit-rate half is
> **NOT EVALUABLE**, not falsified — stronger than W7.2's protection, which says
> "a null at a different point"; R5 says the threshold is outside the metric's
> range. The DRAM half keeps its range and stays evaluable (14.5% at A1/B1).
> Diagnosis, registered rather than offered later as an excuse: **A1 over-relieved
> O2** — an 8 MiB hot table 97.6%-resident in a 20 MiB LLC leaves an admission
> policy almost nothing to protect, the obvious candidate for H2's 0.63% there.

> **2026-08-24 04:55, correcting my own framing an hour after committing it.**
> Correction appended to `W7.4`. I called the prefetchers "undisclosed"; they are
> not. `CHI_config_8592.py:660` documents them as a deliberate Intel-SPR model —
> DCU Streamer + DCU IP at L1D, MLC Streamer + MLC Spatial at L2, "all 4
> default-ON", `PF_DEGREE=4`, 4 KiB page annotated "faithful". I read the
> instantiated `config.json` and the stats but not the config source. The real
> gap survives and is narrower: the choice was never propagated into W7's
> pre-registration, memos, or P2's calibration — a gap in the analysis, not the
> apparatus — and the §5.1 line is still owed. Every measurement and both
> readings stand unchanged. Two things gained: **`PF_OFF_CORES` / `PF_DEGREE` /
> `PF_PAGE` are environment knobs**, so a prefetcher-off arm costs one env var
> and would decompose P2's shortfall into "cannot express MLP" vs "cannot be
> prefetched" — recorded as the cheapest follow-up, *not* run, W7's arms are
> fixed. And the disclosure is **repo-wide** for Ruby/CHI figures
> (`intel_8592_4cpu_dirtax_streaming` shows 17.6–20.9 M prefetch transactions),
> though not for the W8 FS boot, which measures 0.

> **2026-08-24 05:15, W7 COMPLETE — 28/28, and the designed corner does not
> exist.** `W7_OUTCOME_2026-08-24.md`. 66.2 host-hours, 3 h 42 m wall. **P1's
> hit-rate half: NOT EVALUABLE** — R5's registered ≥85% condition fires at a
> measured 97.685% WB hit rate, so the +15 points asked for exceed the metric's
> 2.315 points of headroom. **P1's DRAM half: 14.1% of achievable** against ≥50
> (falsified <25.8); the metric *has* range (≥50 needed 12.560 MB, floor 8.389),
> so this half is genuinely missed — but W7.2's rule holds, it is **a null at
> 20 MiB / 40× / 40%, and P1 as registered stays open**. **P3: +0.63%**, same
> protection, and doubly confounded (R1: B reached 1.77 of ≥6 lines; R5's
> diagnosis: A1 over-relieved O2 to 97.6% residency). **P5: dominance FAILS** as
> pre-disclosed at 22/28 — A0/B1's +1.23% is ~2× A1/B1's +0.63% — and R3's
> sufficiency clause is dead, no knob reaches 5%. P4 unevaluated, needs CAT.
>
> **New and unpredicted: H2 costs time at A1/B0, −1.00%, all three seeds
> negative** (−0.902 / −1.634 / −0.464 against arm sds ≤0.271 cycles), with Ruby
> LD latency +2.19% — *while reading fewer bytes from both pools and hitting the
> LLC more often*. The W7.4 CXL anomaly in the time domain. Mechanism NOT
> asserted: these are per-request means over a changed mix, and A1/B1 runs the
> other way (latency +0.65%, time −0.63%). What is safe to say and belongs in the
> paper: **H2 is not free, and at one measured point its cost exceeds its
> benefit.**
>
> The campaign-level result is not "H2 gives no benefit" — it is that **every
> cell W7 measured has at least one of the two obstacles still fully in place**,
> so the corner the 2×2 was built to reach was never occupied. §4's strong
> negative remains unavailable. Reaching it needs both axes fixed *together*: a
> probe that can express ≥6 independent misses (the 14.62-line smoke says the
> machine allows it; the kernel does not), and A-axis sizes that are exact powers
> of two after (size/assoc)/block so F9.4 cannot silently re-inflate the hot-set
> ratio. Sizing and spend are lead decisions.

> **2026-08-24 04:55, recalibrating a tripwire I set, six minutes before it would
> have fired on a healthy run.** `W8.4_T5_TRIPWIRE_RECALIBRATED_2026-08-24.md`.
> T5's `wb` arm dumps stats exactly once, at the end of `w8_wb.rcS`, so a
> zero-byte `stats.txt` and a static console are the *expected* state for the
> whole measured region — the 90-minute threshold was testing elapsed time when
> what it wanted was liveness. The run is live: state `R`, **99.9% CPU**, CPU time
> 1:22:25 against elapsed 1:22:26. And it is on schedule: W7's `A0_B0_wb_s1` has
> the identical workload shape (morsel, wb, 16 MiB fact, 4 MiB hot, probe-batch 0)
> on the same 2-core O3 + CHI machine and cost 9,037 host-seconds for 4 passes,
> so **~38 min/pass is the SE floor** for T5's single pass — and T5 additionally
> pays for a real kernel, page table, ext2 and device models. Setup took 53 min;
> the measured region is 30 min in; the earliest possible dump is ~05:05. Firing
> the tripwire would have killed a run with 53 minutes of restore already sunk.
> Replaced by liveness (CPU time advancing), a 4 h ceiling (~6× the derived
> estimate), and a console-regression check (`W8-RCS-BENCH-EXIT` must precede a
> non-zero `stats.txt`). **G0–G5 and `t5_analyze.py` untouched**, and the rule
> that `stream_mprot` waits for `wb`'s gate to be read *and stated in writing*
> stands unchanged.

> **2026-08-24 05:05, the "add `exit 0` on DRY" item was hiding a destructive
> defect.** `w7_campaign.sh`. The pending note said the dry path merely failed to
> stop cleanly. It was worse: `launch()` ran **`rm -rf "$OUT/$n"` above the DRY
> branch**, so `W7_DRY=1 ./w7_campaign.sh` — the one invocation whose entire
> purpose is to change nothing — would have **deleted all 28 completed cells**
> before printing its first DRY line, and the tail would then have stamped a
> fresh `w7.done` over the real one. Same shape as A6.19's `run_join_campaign.py
> --help`: an inspection command with a destructive body. Fixed by checking DRY
> before the first side effect and having the dry path *print* the command
> instead of writing it, so it is side-effect-free and safe against a live
> `$OUT`; the tail is guarded too. Verified in the only way that counts — patched
> first, then ran `W7_DRY=1 W7_OUT=/tmp/w7` against the live campaign: **28/28
> cells survive and `w7.done`'s mtime is unchanged.** `~/tmpfs_backup/w7/` was
> already refreshed to 28 cells / 60 MB on ext4 before this was attempted. No
> data or analysis is affected — the campaign ran on the old file and its results
> stand.

> **2026-08-24 05:30, T2's blocker cleared and I found that T2 already ran, was
> truncated on all three arms, and reported success.**
> `W8.5_T2_SUPERVISED_TRIO_WAS_TRUNCATED_2026-08-24.md`. **T2 was not launched.**
> The T2 audit names
> `intel_8592_4cpu_dirtax_streaming_supervised.sh` as the next authorized
> measurement; it ran on 2026-08-23 and **every arm was SIGINT'd at 5400 s**
> (`tripwire_reason=zero-byte_stats_after_5400s` in all three `provenance.txt`,
> `Exiting @ tick N because user interrupt received` at the end of all three
> `run.log`). **gem5 handles SIGINT by dumping a complete stats file and exiting
> 0**, so `[[ $status -eq 0 && -s stats.txt ]]` passed on all three, each with
> 1.8–2.0 MB of normal-looking statistics. The arms stopped at 193.1e9 / 48.7e9 /
> 51.9e9 ticks — **~4× different amounts of work in a "matched trio"**. F12, in
> the runner the audit points at.
>
> Root cause is not marginal: **5400 s is shorter than the known completion time
> of the fastest 53% arm.** `alone_53p` completed naturally at hostSeconds 6072
> in the historical sweep already in the repo. The contended arms need **≥12.1 h
> and ≥10.9 h** at their own measured tick rates (172.5e9 and 191.8e9 ticks at
> 17,400 s against `alone`'s 431.8e9), and those are *lower* bounds because
> contention raises the victim's per-iteration tick cost. **A serial 53% trio
> costs 25–30 host-hours, not 4.5 — the budget was off ~6×.**
>
> Fixed and committed in the submodule (`d4fe79a9dd`): a tripped arm returns
> failure via two independent detectors, the trio aborts at the first failure,
> `provenance.txt` gains `tripwire_fired`/`user_interrupt`/`completed`, and
> `TIMEOUT_S` defaults to 50400 with the derivation written in at the assignment.
> Verified the only way that counts — **old test PASS / new test FAIL on all
> three real truncated arms**. Both invalid run dirs carry
> `INVALID_DO_NOT_ANALYSE.md`.
>
> **F9.4 audit of T2's frozen geometry: clean.** L1I 64, L1D 64, L2 2048, L3
> slice 4096 sets — all exact powers of two. Fourth geometry audited, first
> outside W7/tab:sens; the affected set repo-wide is still exactly three cells.
>
> **Escalated, not decided** (W8: spend beyond the timebox is the lead's).
> Recommendation is option 1: **run the trio concurrently, ~12 h wall instead of
> 25–30.** Serialization was a response to the historical sweep *losing its
> children* — a supervision failure, not a contention one — and gem5's
> determinism in simulated time means host load moves wall clock, not
> `stats.txt`; the same argument already licensed W7 and T5 running together.
> Options 2 (serial at 14 h/arm) and 3 (drop 53%, since T2 gates neither T3 nor
> T4) are in the memo. **No published number moves**; the supervised trio's
> numbers have never been reported and this is their only appearance.

> **2026-08-24 — the watchdog sweep W8.5 §8 asked for is done; the F12 was
> confined to one runner.** Seven of our own runners carry a kill/timeout
> construct. `cat_mba.py` and `wss_sweep.py` check returncode and let
> `TimeoutExpired` propagate — clean. `exp35_smba_pareto.sh` and
> `exp36_localdram_ccx.sh` have no such construct. The three
> `e1_residual_decomp/run_e1_*` runners share a *different*, latent defect —
> the victim's `returncode` is never checked — but its failure mode is a
> **visible null** (`victim_line=""` → `parse_victim("")` → `{}` →
> `cyc_per_iter: None`), not a success report. Scanned all twelve e1 data
> files: **684 nested-schema records, 0 empty**; the other 96 use a flat schema
> and are all populated. It never fired. No fix applied — frozen phase-1
> runners, campaigns complete, and changing apparatus to guard a fault that did
> not occur buys nothing.
>
> **The structural reason the F12 was gem5-only, now named:** gem5 dumps a
> complete, plausible `stats.txt` and exits 0 on SIGINT, so a killed arm is
> indistinguishable from a finished one by exit status or file size. A killed
> silicon victim emits nothing, and nothing is loud. **F12 requires a child that
> lies convincingly.** That is the property to look for in future runners, not
> the presence of a watchdog.
>
> **Recorded against interest:** my first scan reported 96 bad records and was
> itself wrong — the condition `not r.get("victim")` fires on every record of a
> schema with no `victim` key. Caught by opening one flagged record. **Read one
> flagged record before believing a count**; an analyzer that invents a defect is
> F12 pointing the other way.
>
> Addendum appended to `W8.5_T2_SUPERVISED_TRIO_WAS_TRUNCATED_2026-08-24.md`,
> original text verbatim (A6.19). No published number moves. T5's `wb` arm was
> not touched during any of this (apparatus rule).

> **2026-08-24 (same day, strengthening the entry above) — T5 is structurally
> immune to the F12, and the sweep's real yield is a design rule.** My addendum
> first said only that `run_t5.sh` "has no watchdog"; that is incomplete. T5's
> G4 keys on `W8-RCS-BENCH-EXIT 0` plus a JSON `status=ok` — markers printed **by
> the guest workload**, which a killed run cannot emit. Verified with two
> synthetic arms carrying **byte-identical `stats.txt`**: they separate on G4
> alone, FAIL vs PASS. `t5_analyze.py` also correctly reports `NO DATA` on the
> live empty arm, so it does not carry `w7_analyze.py`'s pass-on-no-evidence bug.
>
> **Rule: gate on a completion marker the workload itself emits, never on the
> simulator's or harness's exit status.** The supervised runner tested
> `$status -eq 0 && -s stats.txt` — both properties of the *simulator*, both
> satisfied by a SIGINT'd gem5. This supersedes the weaker "child that lies
> convincingly" heuristic: that says where to worry, this says what to build.
>
> Also verified and recorded so they are not repeated: `DRYRUN=1` passes all
> three gates for both remaining T5 arms leaving nothing behind, and the three
> `.rcS` scripts differ **only** in arm name and `--declare` — the premise of
> G0's negative control, previously assumed. T5's `wb` arm untouched throughout.

> **2026-08-24 — W8 / T5 arm 1 (`wb`) GATE: PASS. Arm 2 authorized.** Full-system
> run of the real workload through a real kernel, restored from T4's checkpoint:
> `streamingTranslations = 0`, `streamingAccesses = 0`, `W8-RCS-BENCH-EXIT 0`,
> JSON `status=ok`. simSeconds 0.2337, 1 h 39 m host. Nothing other than a
> declaration sets the bit. `W8.6_T5_WB_GATE_2026-08-24.md`.
>
> **Four qualifications, none of which moves the gate, all of which bind reporting:**
>
> **(A)** The `wb` record says `"declare":"m5op"` although the arm passed no
> `--declare`: `g_declare` defaults to M5OP and is printed unconditionally, while
> `declare_streaming()` is only reached under `policy == "stream"`. The control is
> clean, the reporting is not — and `t5_analyze.py` prints `declare=m5op` directly
> above `G1 PASS (expected ==0)`, which reads as the negative-control claim that
> belongs to the *m5op* arm. **Reading rule: `declare` is meaningful only when
> `policy == stream`.**
>
> **(B) T5's FS runs have no CXL involvement — a new finding that extends W8.1.**
> `bindpool` is SE-only just as `setstreaming` is (`pseudo_inst.cc:674` warned);
> the bench took the m5op path and its own record says `"placement": "GEM5 no NUMA
> placement check"` — no `mbind` fallback, no verification. At the controllers:
> the 198 ns CXL range read **46 KB**, the 97 ns DRAM range read **45 MB**. The
> 16 MiB fact array was served from DRAM; `"fact_node": 2` was requested, not
> realized. No gate is touched (all gates concern the declaration reaching the
> walker, not placement), but this is a **fourth** independent reason no
> performance comparison is licensed out of T5.
>
> **(C)** `stats.txt` holds **two** cumulative dump sections (`m5 dumpstats` then
> `m5 exit`; two `simSeconds`, 0.233184 and 0.233720) and `stat_sum` sums both, so
> any non-zero count is ~2× inflated. Presence gates are unaffected; **no count may
> be quoted as measured** when arm 2 returns a non-zero classification count.
>
> **(D)** `run_t5.sh` exits 1 on a successful arm — `grep -c` returns 1 at zero
> matches, `pipefail` propagates, `set -e` aborts before `exit $rc`. Affects `wb`
> and `stream_mprot`; only `stream_m5op` exits 0. **Expect exit 1 from arm 2 and
> treat it as uninformative.** Not fixed (apparatus rule; a wrong exit code does
> not prevent running). Exact mirror of W8.5's F12 — success reported over a
> killed run there, failure over a completed one here — and a direct vindication
> of `f47d554`'s rule: gate on the workload's own markers, never the harness's
> exit status. `t5_analyze.py` did, and was right.

> **2026-08-24 — `t5_sections.py`, committed before arm 2's data existed.**
> W8.6 qualification C: each T5 arm's `stats.txt` holds two cumulative dump
> sections (`m5 dumpstats`, then `m5 exit`), and `t5_analyze.py`'s `stat_sum`
> adds them, so any non-zero count it prints is ~2× inflated. Its gates are
> presence tests and are unaffected, so **`t5_analyze.py` is deliberately not
> edited** — it is pre-registered apparatus and the campaign is mid-flight.
> This is a separate reader: it computes no gate, overrides no verdict, and
> reports each stat per section, naming the last section (resetstats → m5_exit)
> as the one to quote. Written and committed **while arm 2 was still running and
> before any non-zero classification count existed**, for the same reason
> `t5_analyze.py` was written before its data.
>
> Validated on arm 1, where the answer is known to be zero: 4 rows per section,
> not the 8 `t5_analyze.py` reports — the 2× is confirmed rather than inferred.
> Two defects in my own first draft were caught by that validation and fixed
> before commit: it formatted every value with `.0f`, rendering simSeconds
> 0.233184 as **"0"**, and it flagged 33 legitimate repeated Ruby rows
> (`avg_reserved`/`avg_size`/`avg_util`, one per cache partition) as anomalies
> while silently dropping all but the first. A reader that truncates the quantity
> it exists to report, or cries wolf loudly enough to hide a real duplicate, is
> the failure the file warns about.

> **2026-08-24 — arm 2's reading fixed before arm 2's data (W8.6 addendum).**
> Committed mid-run. Three things it buys: G2 acquires no innocent failure mode
> (the `pte_query` interface is verified present in the booted `vmlinux` by `nm`,
> not assumed from `.config`, which is newer than the binary), so a G2 FAIL is a
> real finding about the mprotect path; G1's `>0` gate is qualified by a
> magnitude expectation (4,096 declared pages → O(10^3)–O(10^4), a single-digit
> count is a stray page and must not be reported as the object being classified);
> and G3 >> G1 is registered as the coherence check. Also: qualification B moved
> from inferred to observed via a live `bindpool called outside SE mode` warning,
> which simultaneously proves G5's mechanism works for runtime warnings before
> arm 3 is spent on it.

> **2026-08-24 — T5 arm 2 livelocked in the guest; W8's capability arm has no
> result (W8.7).** Killed after 6 h 44 m. The guest console stops mid-word inside
> the `HOT_TABLE` print at `cxl_join_bench.cpp:1537`, **eleven lines before**
> `declare_streaming()` at `:1548`, so arm 2 never reached its declaration. Not a
> stalled simulator: gem5 serviced two `SIGUSR1` dumps in ~2 s each and committed
> 17.2 M instructions between them. It is a **livelock** — between the two dumps
> both cores' instruction-mix deltas were byte-identical (`IntAlu 7,657,333`,
> `MemRead 957,167`, no stores, exactly 8:1), i.e. two cores lockstepped in one
> store-free polling loop, having burned 23× arm 1's entire completed run.
>
> This implicates the declaration path in **neither** direction: the code that
> hung is byte-identical to arm 1's, which passed, but `CONFIG_PAT_STREAMING=y`
> means the STREAMING kernel's mm hooks were live on every fault, so the kernel
> is not exonerated either. **The cause is unknown and must not be asserted.**
>
> A naive retry is a 7-hour no-op: gem5 is deterministic and `RUBY_RANDOMIZATION`
> runs off fixed seed 5489, so an identical re-run reproduces the hang bit-for-bit
> — and that same determinism is the one asset here, since the hang lands 18 m 23 s
> in, making a diagnostic reproduction cost ~20 min rather than 7 h. `GEM5` is
> overridable and expands unquoted in the launcher's `exec`, so
> `--listener-mode=on` can restore the gdb socket (`remote_gdb.cc:418` reported it
> disabled) **without editing committed apparatus**. Escalated to the lead, not
> decided: arm 2 underpins L4, and the alternatives (editing the hardcoded
> `RUBY_RANDOMIZATION=1`, or perturbing the pre-registered rcS) are blind re-rolls
> that spend a 7-hour arm on a guess.
>
> Arm 3 is **not started** — arm 2's gate did not pass. The aborted directory was
> quarantined by exploiting `t5_analyze.py`'s suffix matching: `arm_spec()` uses
> `name.endswith(k)` so directories may be freely prefixed, and the dual is that
> **appending** a suffix yields `UNKNOWN ARM … not gated`. Verified. This matters
> because the artifact is F12-shaped — gem5 exits **0** on SIGINT and left a
> `stats.txt` with three plausible dump sections; nothing about it looks broken.

> **2026-08-24 — the stock-CHI control, pre-registered before it was built
> (W8.8).** Lead authorized "run the stock-protocol control" to settle whether
> our CHI edits cause arm 2's livelock. Our branch modifies
> `src/mem/ruby/protocol/chi/`, so "upstream's bug, not ours" is not free, and
> the question outruns W8: if our protocol edits can wedge atomics, every
> Ruby/CHI number this project owns is in question.
>
> Built in a **separate git worktree** (`~/DutyFree-stockchi`, branch
> `w8-control-stockchi`) with `chi/` reverted to the last upstream commit that
> touched it, `6386a580d1`, and everything else at `d4fe79a9dd`. The revert is
> exactly the inverse of our delta — ours is 221 insertions / 15 deletions over
> 6 files, the revert is 15 / 221 — so nothing rides along. `~/DutyFree/gem5` is
> **not touched** and stays byte-identical to the tree that produced arm 1's
> accepted data; `logs/` and `../linux` are symlinks so the control restores the
> identical checkpoint and kernel.
>
> The pre-registration's substance is a **gating audit** done before the run,
> which is what turns the control from suggestive into interpretable. Every
> functional change in the delta is gated on `is_streaming` or `sf_finite`, and
> both are off here — verified from the aborted run's own artifacts, not
> assumed: all 24 `streamingTranslations`/`streamingAccesses` lines are 0 (the
> stall precedes `declare_streaming()`), and `config.ini` reports
> `sf_finite=false`, `enable_H3_streaming_bypass=false` on every controller.
> Three ungated changes were checked and are provably inert, including the new
> `if (in_msg.isSFEvict)` arm that now runs first on **every** replacement
> trigger — an undefaulted bool there would have been exactly this class of bug;
> it is declared `default="false"`.
>
> That leaves **exactly one ungated functional line** in the whole delta:
> `tbe.dataValid := true` for `initial == State:UD_RU` in
> `Initiate_Replacement`, our "H3/B2 FIX" for SF-eviction dirty-data loss. It
> fires on every UD_RU replacement, and UD_RU is the state a contended lock line
> occupies while bouncing between two cores. Registered prediction: the control
> **stalls identically** unless that line is the cause.
>
> Outcome branches fixed in advance. B1 (reproduces) exonerates our edits and is
> decisive. B2 (completes) points at that one line, and the gating audit is what
> makes that inference strong — but it is semantic equivalence, not cycle-exact
> equivalence, so B2 still requires a one-line-revert confirmation before it may
> be reported as causation. B3 is anything else, reported as itself: W8.7's
> discriminator already produced a fourth unenumerated outcome and that must not
> be smoothed over twice. The control is named so `t5_analyze.py` refuses to gate
> it, and it licenses no performance comparison.

> **2026-08-24, W8.8 stock-protocol control: OUTCOME B1, our CHI edits are
> exonerated.** The T5 `stream_mprot` livelock reproduces **bit-identically** on
> a stock-CHI build (`src/mem/ruby/protocol/chi/` reverted to `6386a580d1`, a
> 15/221 inverse of our delta, in a throwaway worktree so the campaign tree was
> never touched). Console frozen at exactly 248 bytes with the same tail;
> `MemWrite` frozen at **64,200** / **3,162,502** -- not merely constant, the
> *same numbers* as the arm-2 reference -- while `numMemRefs`, `simTicks` and
> `simInsts` all advance. Three independent checks confirm the reverted protocol
> is what ran (0 vs 10 `1kB->1KiB` warns, 0 vs 20 `sf_finite`/`H3` config lines,
> 0 vs 7/3/6/5/3 generated-protocol files carrying our symbols), and upstream's
> own `UD_T`/`sc_lock` livelock machinery survived the revert identically in
> both builds. Attribution: **upstream gem5 CHI at v25.1.0.1**, consistent in
> every observable with issue #3075, which addendum 1 registered before any
> control datum existed. `W8.8_STOCKCHI_CONTROL_PREREG_2026-08-24.md` addendum 2.
>
> Consequence: the blocked arm cannot be unblocked by fixing our protocol,
> because there is nothing of ours in the failing path. Tuning `sc_lock_*` stays
> unauthorized. The one route left does not need Ruby at all -- both W8 gate
> counters are arch-side (`src/arch/x86/pagetable_walker.cc` ->
> `streamingTranslations`, `src/arch/x86/tlb.cc` -> `streamingAccesses`) and G2
> is an in-guest debugfs readback, so a **classic-memory FS restore** exercises
> G1/G2/G3 in full. W8 licenses no performance comparison, so dropping Ruby
> costs W8 nothing it claims. Recorded as a lead option, **not started**; arm 3
> stays barred and T2 stays unlaunched.

> **2026-08-24 — external-reviewer state memo written; three of our own numbers
> failed their own provenance check while writing it.**
> `REVIEWER_STATE_2026-08-24.md` states the case for and against submitting at
> all, for a reader outside the project. Its spine: the harm is measured on
> silicon and is large, the benefit is measured in simulation and is small, and
> **those are not the same experiment** -- W1 established the two meet in *kind*
> (both capacity-class) but never in *magnitude*. Six thought experiments; the
> load-bearing one is TE-3, which explains W7's failure structurally rather than
> as bad luck: **batching a probe is adding MLP, and adding MLP is what makes a
> victim immune.** The knob chosen to make the cell realistic is the knob that
> destroys the effect, so no re-tuning of that 2x2 recovers the number. W5.4
> then converts "small magnitude" into "correctly scoped": elasticity of runtime
> to cache traffic is 0.18 on mos181 -- 8.44x of a victim's DRAM traffic removed
> returns 1.54x in time -- because independent misses overlap. The harmable class
> is latency-bound, low-MLP, LLC-resident victims, which is exactly the
> pointer-chase victim the decisive cell uses.
>
> Verifying every cited figure against its committed source before committing
> caught three defects **in the memo's own first draft**, all F12 in miniature:
> (1) it quoted the paper's `tab:amdcat` **19.85 / 6.92 / 1.02**, which W4.2
> superseded -- the verified files read 19.886/7.225/0.989 (n=12) and
> 20.545/**9.867**/1.006 (n=6), so CAT removes 67% or 55% depending which you
> believe, not 69%; (2) it quoted a RocksDB "CAT recovers 54% [50,56]" that the
> provenance ledger marks **UNTRACEABLE**; (3) it attached an unsourced
> "20.9 GB/s" to E1's matched-bandwidth dissociation. All three corrected, and
> the memo now carries **N7** disclosing the provenance defects to the reviewer
> rather than hiding them. It also caveats the W5.4 three-host elasticity ladder
> as host-confounded, which W5.4 itself insists on.
>
> Consequence for the plan: **no new measurement is on the critical path, and
> the memo says so.** The decisive missing datum (TE-6) is a *silicon*
> experiment -- one real, named, economically important workload whose victim is
> demonstrably low-MLP and whose harm is large, with CAT failing on it. That
> would convert section 5's limitation into the paper's scoping contribution.
> Option (B) "submit as a scope-and-abstraction paper with a cheap mechanism" is
> what the evidence currently supports; option (C) is (B) plus TE-6. Lead
> decisions 1 (venue/date) and 3 (co-author communication) still gate the
> 39-row edit queue, and W4.2's superseded-number substitution is now also
> blocking, because a referee who pulls on N7 finds it in five places.

> **2026-08-24 (later) — three review rounds, and the spine changed twice. Net:
> the scissors, and an F11 I committed myself.**
> `REVIEWER_STATE_2026-08-24.md` addenda 1 and 2 carry the detail. Summary of
> what actually changed in the plan:
>
> **1. The memo's S4 was wrong and is retracted.** A same-silicon, same-victim,
> same-operating-point harm-recovery pair already existed and was already in the
> draft: flush-behind on AMD Bergamo, hash-join cross-process, n=12, frozen at
> `0628e0d`, recovers **76.3% [76.1,76.4]** of a **6.484x** tax -- victim
> **406.25 -> 144.21 cyc/access, 2.82x faster** -- at a measured, non-embargoed
> streamer cost of **31.34%**. The h1bw anomaly that blocked the companion
> sentence was resolved 2026-08-18, so the three-link chain (silicon harm,
> silicon single-knob cost, simulated type without the self-cost) is assemblable
> from committed data with no new measurement. Publish **2.82x**, never 2.33x.
>
> **2. The scissors.** W5.3 kills L5 for cross-process: CAT12 alone reaches
> **1.00x at 0.7%** streamer cost on Intel, CAT12+MBA192 **1.07x at 96%** of
> full bandwidth on AMD. Meanwhile `results/clos_split/` shows that in the
> same-thread case *every* deployed control makes the victim **worse,
> monotonically in how hard it is applied* (CAT 20/20 87.65 -> 12/20 105.12 ->
> 8/20 115.81 -> 4/20 126.86 cyc/access; `PREFETCHNTA` 98.37; splitting threads
> 95.69 at 0.6375x throughput). So: **the case where STREAMING is uniquely
> expressible is the case where its payoff is smallest, and the case where its
> payoff is large is the case shipping knobs already handle at <=4%.** Every
> unique claim now funnels through the OS thread. Options B and C as previously
> written are dead; the cross-process branch must not be reopened.
>
> **3. `resctrl` is task-granular.** CLOS is per-TID (`IA32_PQR_ASSOC` is
> context-switched). "Compaction and serving share a process, so CAT is
> inexpressible" is **false, and it was ours.** The expressibility boundary is
> the OS thread. LSM therefore sits in the *expressible* branch; its argument is
> operational fragility, not capability. Branch B's candidate population is
> thread-per-core runtimes (Seastar/ScyllaDB, Redpanda) plus fused engines --
> same-thread by design, unreachable by per-TID CLOS, and unable to split
> without re-imposing the measured 36.2%.
>
> **4. F11, by me.** Addendum 1 declared the fused-tax decomposition "the new
> critical path" and called the second blade an unearned inference. The
> decomposition **ran 2026-07-29** -- pre-registered, three instruments, n=30,
> committed report and three committed runners -- and its verdict is harsher
> than anything the reviewers proposed: `Delta_LLC_upper/Delta_total` is **at
> most 0.31 and 0.00 under the strict L2-fit reference**, i.e. the pre-registered
> **"H2 story in trouble"** band, with the fused tax essentially fully present at
> L2-fit scale and `Delta_M5` ~ 0. `FB_FULL` grows 3.84x/11.68x while mean
> outstanding depth stays flat, and the report declines to convert that into
> cycles for want of a causal model. So the second blade is **measured**, not
> inferred -- and `Sec5_Evaluation.tex:382-389` already scopes the fused kernel
> to necessity on this authority. The draft was more honest than the memo
> credited. What never propagated: the **strict 0% reading** beside the
> published `<=31%`, and the pre-registered **verdict**, which appears in no
> other file in the repo. Both are S5.1 obligations applied to a threshold.
>
> **5. Artifacts.** `results/mechanism_decomp/` (1,402 files) pinned with
> `git add -f` in this commit -- it was the stated authority for a paper claim
> and was unversioned. `results/clos_split/` needed no action: already pinned at
> `a41df38`, and the W4.3 ledger's F1 entry saying otherwise is **stale and
> should be amended**; I read it and repeated it. `results/` stays in
> `.gitignore`, so future runs remain unversioned by default.
>
> **6. Three reviewer citations failed verification** -- a 15.8/4.2 GB/s
> per-core WB/WC pair ("15.8" is nowhere in the repo; 4.17 is our *WB* SE
> figure), a "3.8 vs 2.5 GB/s" non-enrolling-stream claim, and an
> `AnonHugePages=0` note. The first came from the draft's own prose, so the
> intro's motivating single-core bandwidth contrast joins the W4.2 repair list.
> A review inherits provenance rot from the text it reviews.
>
> **Revised order:** (1) hygiene, now including the intro bandwidth pair;
> (2) propagate the decomposition's strict reading and verdict -- hours, and
> obligatory; (3) the hugepage/TLB arm, the one candidate the 2026-07-29
> decomposition did not cover; (4) assemble the chain in 1 re-scoped to
> mechanism attribution with W5.3 printed beside it; (5) fork on the
> `Delta_M3` cycles-per-access conversion, which decides whether a mechanism
> paper proposes a staging buffer or MSHR QoS -- and note that a buffer forfeits
> "zero new architectural state", so that and "uniquely needed in the same-thread
> case" cannot headline together. Deferred: census, SHiP, virtualization and
> security sections, standalone consume-in-place.
>
> **Process rule earned, four instances now** (the knob *combination*, the
> per-TID *scope check*, the *stale ledger entry*, and the *unread
> decomposition*): before adopting any spine, enumerate the cheapest
> configuration a hostile referee could run against its central sentence and run
> that first -- and before declaring any experiment the critical path, `ls` the
> results tree and read what is already there.
>
> **Not taken, still lead-only:** writing W5.3 into `~/STREAMING_Paper/` sets
> page-1 evidentiary posture. Three documents' spines die on it and the
> reviewers argue it can no longer wait; it remains the lead's call, and the
> co-author conversation should lead with it.

> **2026-08-24 (T2 executed) — the intro's WB/WC contrast is falsified on three
> hosts; delete it, do not re-source it.**
> Pre-registered at `d1a0c6b` before any measurement, analyzer at `76eeea3`
> written while the runs were in flight, outcome in
> `T2_WBWC_OUTCOME_2026-08-24.md`. n=5 per cell, 2 GB region, one pinned core,
> local DRAM, arms interleaved within each rep, CoV <= 1.31% everywhere and no
> bimodality.
>
> **A/C = 1.252 / 1.289 / 1.283** on EMR 8592+, SPR 8462Y+ and EPYC 9754 against
> the ~3.76 the introduction's numbers imply. The registered falsifier fired on
> all three. The **WB** half was roughly right (14.755 / 16.040 GB/s vs a claimed
> 15.8); the **WC** half was wrong by ~3x. The derived "five WC cores to match
> two WB cores" also falls -- it is ~2.6 cores measured, ~3.7 with the honest
> proxy. And no silicon arm reads anywhere near the claimed 4.2 GB/s: the lowest
> is 8.04. gem5's SE model reports **4.17 GB/s for its WB pure-stream ceiling**,
> which is almost certainly the source, mislabelled as silicon WC -- the A6
> misattribution hypothesis, now measured.
>
> **Two findings that hold regardless of the numbers.** (1) `stream_wc.c` is
> `MOVNTDQA`-on-WB *with the hardware prefetchers left ON* -- not the WC memory
> type and not prefetch-free -- and `stream_nt.c` is the same program plus an MSR
> warning (load loops md5-identical; C and D agree to three decimals on all three
> hosts). So `stream_nt.c`'s pre-registered "if D ~ C the NT hint is honored"
> reading is **circular and void**, and arm C is evidence about the taxonomy's
> *advisory* plane, not its *enforced* one. Registered replacement wording:
> "non-temporal (`MOVNTDQA`) loads on write-back pages". (2) A new additive arm
> `stream_wc_nopf` (same load loop, prefetchers off, read-back verified) gives
> **C'/C = 0.682 / 0.708**, so **every published "WC" bandwidth figure is an
> overestimate of WC by ~1.4x.**
>
> **One adverse result to scope rather than bury:** disabling all four hardware
> prefetchers costs only **~6%** of WB stream bandwidth on local DRAM
> (B/A = 0.944 / 0.940). The paper's "demand misses sustain only ~4-5 GB/s per
> core" is a *CXL-latency* claim and CXL was pre-registered out of scope here, so
> this does not refute it -- but the sentence must be explicitly scoped to far
> memory, because on local DRAM a sequential stream barely needs prefetching.
>
> **Platform state, newly documented.** mos182 runs with **MSR 0x1A4 = 0x20
> machine-wide** (an extra prefetcher disabled; cpu8 and cpu9 agree), and
> `stream_wb` *refused to measure* rather than report a non-default machine --
> correct instrument behaviour and an undocumented difference between our two
> Intel hosts that belongs in `tab:appplat`. moscxl had **zero** 2 MB hugepages,
> independently confirming the ledger's `tab:appplat` defect where the paper
> asserts pre-allocated hugepages there. Both were normalised for the run and
> **restored to as-found**, verified. `kill -9` defeats these binaries' `atexit`
> prefetcher restore -- use SIGTERM.
>
> Two contaminated windows were quarantined rather than used: a mos182 run where
> I relaunched the host while its first run was still live (two processes pinned
> to cpu8), and a mos181 partial killed mid-rep2 by a wrapper-shell timeout. The
> two `*_FAILED_nohugepages.jsonl` files are kept deliberately as evidence.
>
> **T2 status: the bandwidth-pair item is closed.** What remains on T2 is the
> rest of the hygiene batch (the five superseded AMD triples, the RocksDB prose,
> the 9.6x/19.85x arm identity, F9.4 labels), and those are paper-tree writes
> gated on T0.

> **2026-08-24 (T3 executed) — stream-side TLB excluded; the walk counters say
> the load-induced walks are the VICTIM's; and `tab:fused`'s quiescent
> denominator is bimodal with n=1.**
> Pre-registered at `5070dbe`, runner at `30e60fd`, both before the run. Outcome
> in `T3_HUGEPAGE_OUTCOME_2026-08-24.md`. mos181, 1 core, panel-verbatim
> operating point, n=5, arms interleaved.
>
> **R = -0.088, below the registered 0.10 threshold: stream-side TLB/walk
> pressure is excluded.** The paired A-arm comparison is far tighter and agrees:
> cyc/access **-0.38%**, page walks **-0.45%**. Guard 1 passed decisively --
> every A_2m rep consumed exactly **128** node-2 hugetlb pages (256 MB / 2 MiB)
> and every other arm consumed 0, so `MAP_HUGETLB` really succeeded. That had to
> be measured externally, because `alloc_bytes()` falls back from `MAP_HUGETLB`
> to `mmap`+`MADV_HUGEPAGE` **silently** and the JSON's `anon_huge_kb`/`table_*`
> fields describe the hot table, not the fact array.
>
> **The null is a mechanism, not just a null.** The stream's pages went from
> 65,536 to 128 -- a 512x smaller translation footprint -- yet its apparent walk
> contribution fell only **1.8%** (7.953M -> 7.811M), where the arithmetic
> predicts 99.8%. So the ~8M extra walks under load are **not the stream's
> translations; they are the victim's**, invariant to the stream's page size,
> driven by a 170 MB hot table on ~43,500 4 KiB pages. The motivated follow-up
> is therefore the **victim's** page size, which T3 could not touch (the hot
> table is a `std::vector` and the prereg barred editing the kernel). Cheap: an
> arena or an `LD_PRELOAD` like the existing `duckdb_join/tools/thp_arena.c`.
> This does not reopen the stream-side question; it opens the one the counters
> pointed at.
>
> **Incidental, and material to the paper's strongest exhibit.** The quiescent
> arm is **bimodal** -- per-rep cyc/access clusters near ~55.5 and ~63.5 (Q_4k:
> 55.62/61.17/63.28/64.05/64.09; Q_2m: 55.46/55.56/55.79/62.07/64.48). Which
> mode each arm sampled is the entire 2.97 cyc `Delta` difference and why R is
> negative rather than zero. `run_confirmatory_panel.py` passes `--reps 1` and
> runs each label **once**, so the published `tab:fused` quiescent **61.71 is a
> single sample from that distribution** -- and it is the denominator of the
> 1.4737x same-core tax the paper calls its decisive case, carrying ~+/-7% from
> the denominator alone. With the ledger's "18/18 cells reproduce exactly" being
> *recomputation*, not replication, `tab:fused` has **no n and no CoV and at
> least one bimodal load-bearing cell.** Establishing n/CoV is now a hygiene
> blocker, not a nicety. Note the walk counters are stable to 0.05-0.23% while
> cyc/access swings 2.6-6.5%, so the bistability is in timing, not in memory
> behaviour; cause unidentified and reported as such.
>
> **T3 closed. T4 (the `Delta_M3` cycles-per-access conversion) is next**, and
> Addendum 3 C2's objection stands: use thread count and hot-set size as the
> levers, not MBA, which is a pacing throttle barred by the standing rule and
> which W5.3 showed to be a step function rather than a clean rate knob.
> No system state was changed by T3 and no source file was edited.

> **2026-08-24 (code audit) — today's apparatus reviewed before trusting it: six
> defects of mine, one error in my own outcome doc, and F9's second instance in
> the paper.**
> `T3_CODE_AUDIT_2026-08-24.md`. Every figure was independently re-derived with
> code sharing nothing with my analyzers; T2's bandwidths reproduce from
> `total_bytes/elapsed_sec` to <=2e-3 GB/s, the new arm's load loop is
> md5-identical to its parent, and host validity (cpu8 on node0, local mbind,
> `performance` governor) holds on all three hosts.
>
> **T2 stands fully.** A/C = 1.252/1.289/1.283 vs a claimed 3.76, CoV <=1.31%;
> no defect found can move a ratio of 1.27 to >=2.0.
>
> **T3's headline stands; its `R` is withdrawn as a number.** `run_hot_probe()`
> never calls `alloc_bytes()`, so `--huge2m` is a **no-op in the Q arm** --
> Q_4k and Q_2m are the same execution -- and arm order was **fixed, not
> randomized**, so R's denominator is one bimodal configuration and a position
> effect is not separable. What survives untouched is the arithmetic: the fact
> array's pages went 65,536 -> 128 (512x, confirmed by 128 consumed hugetlb
> pages) while the stream's apparent walk contribution fell **1.8%** against a
> predicted ~99.8%. Measured-vs-predicted, so immune to arm order. **The
> load-induced walks are the victim's.** And because Q_2m == Q_4k, the pooled 10
> samples are a direct variance estimate of one configuration: 55.46-64.48,
> **16.3% spread**, bimodal -- so the `tab:fused` n=1 finding is stronger, not
> weaker.
>
> **F9, second instance, on silicon, unfixed.** `table_capacity()` rounds entries
> to a power of two, so the panel's `HOT_BYTES = 177838489` (169.6 MiB)
> instantiates **256 MiB** -- **80.0%** of the 8592+'s 320 MiB LLC, not the
> **53.0%** the paper states at `Sec3_Mitigation.tex:48` and uses for
> `tab:fused`, the CAT sweep and the split arms. The class was already found on
> 2026-08-15 in a gem5 arm and fixed at source (`fef3e5e` prints
> `HOT_TABLE_ROUNDED`), but the clos_split runs predate the warning so it never
> fired, and the lesson was never carried to the silicon panel. Checked and NOT
> affected: `Sec2:96` and `Sec5:201`, which describe the pointer-chase victim,
> and `pointer_chase.c:171` rounds only to a 2 MiB boundary. Note 80% is a
> *harder* point than 53%, so the tax is not flattered -- but the arm identity is
> misstated on the exhibit we were about to promote to Figure 1.
>
> **My own defects, recorded rather than smoothed:** fixed arm order in both
> runners (the consequential one); the T3 runner deleted stderr after parsing it,
> which is how `HOT_TABLE_ROUNDED` was thrown away; a latent F12 where a failed
> sysfs read would render `hugetlb_pages_used=0` and read as "the manipulation
> did not take"; `t2_analyze.py` printing "on ALL hosts" while evaluating only
> the hosts loaded; population sd reported unlabelled as "+/-"; and T3's analysis
> having been an uncommitted heredoc, now pinned as `t3_analyze.py` with a
> docstring recording that it postdates the run.
>
> **Hygiene list gains four items:** Sec3:48's 170 MB/53% -> 256 MiB/80% plus an
> audit of every `HOT_BYTES`-derived size; n and CoV for `tab:fused`; randomized
> arm order before either runner is reused; D2/D3 fixed first.

> **2026-08-24 (T3 run 2) — runner defects fixed, rerun under a balanced design:
> verdict CONFIRMED, and the position confound found, measured, and shown to
> explain run 1's sign.**
> Registered in the T3 prereg's Addendum 1 before running; analyzer committed at
> `722694e` before the data existed; outcome in the T3 outcome doc's Addendum 2.
> n=12, randomized Latin square, every arm in every position exactly 3 times,
> 48/48 records parseable, stderr archived.
>
> **R = +0.0897, inside the registered excluded band.** Stream-side TLB pressure
> is excluded under a design where position cannot confound it. Primary evidence
> agrees with run 1 and is tighter: A-arm cyc/access **-0.16%**, walks
> **-0.24%**, stream's apparent walk contribution **-1.0%** (run 1: -1.8%)
> against the ~99.8% its 512x page-count cut predicts. Guard 1 held (128 hugetlb
> pages in every A_2m rep, 0 elsewhere). **The load-induced walks are the
> victim's, in both runs.**
>
> **R's verdict is stable; R's value is noise.** Run 1 gave -0.0877, run 2 gives
> +0.0897 -- both inside the band, straddling zero, which is what a true-zero
> effect looks like through a noise-dominated denominator. Report the verdict,
> not the number, for run 2 as well as run 1.
>
> **The position confound was real and is now quantified.** It is confined to the
> quiescent arm and acts by **mode selection**, not as a slowdown: Q arms land in
> the slow (~64.1) mode 4/6, 3/6, 2/6, 1/6 of the time across positions 1-4,
> monotone, while the A arms are position-insensitive (means within 0.59 cyc,
> walks within 0.14%). That explains run 1's negative R exactly: Q_4k was always
> position 1 (mode-inflated) and Q_2m always position 3, so Delta_4k was
> understated and Delta_2m overstated. The audit predicted it, run 2 measured it,
> and it accounts for the sign.
>
> **Bimodality confirmed, and n=12 is not enough.** Pooled Q (n=24, the two
> labels being the same execution): 14 low (55.79) / 10 high (64.05), spread
> **16.8%** against run 1's 16.3%. The two Q labels still differ by 2.85 cyc
> because their mode splits differ (3/9 vs 7/5); the registered replicate check
> passes (2.849 <= pooled sd 3.817) but averaging a bimodal variable needs far
> more than 12 samples. This **sharpens** the `tab:fused` problem: the published
> quiescent **61.71 falls in the sparse region between** the two observed modes
> (55.4-56.2 and 62.9-64.7), matching neither, and with `--reps 1` there is no
> way to know which state it sampled -- it is the denominator of the 1.4737x tax.
>
> **F9 now recorded in-band:** `hot_table_instantiated_bytes = 268435456` =
> 256 MiB = **80.0%** of the 320 MiB LLC. Residual gap, visible only because
> stderr is archived now: `run_hot_probe()` emits no `HOT_TABLE` line, so the one
> mode that measures the victim alone is the one that does not record the
> victim's instantiated size.
>
> **Two further defects found by running the fix** (audit Addendum 1): a
> `grep -c` fallback that split every JSON record across two lines -- the same
> class as the known defect at `run_t5.sh:161-163`, which I had read the same day
> and then reproduced; that run was quarantined rather than hand-repaired, and
> records are now validated as JSON before being appended. And the built binary
> is dated Aug 11 while `fef3e5e` (which added `HOT_TABLE_ROUNDED`) landed Aug
> 15, so archiving stderr could never have caught F9 by itself. **Both T3 runs
> and the whole clos_split panel came from binaries that no longer match the
> source tree** -- a provenance item to sit beside `tab:fused`'s missing runner.

> **2026-08-24 (tab:fused n/CoV) — the item was never open. Retracting a claim I
> propagated into four documents today.**
> `TAB_FUSED_N_COV_2026-08-24.md`. `run_confirmatory_panel.py:41` sets
> `N_REPS = 30` and `run_sequence()` shuffles every `(label, rep)` pair under a
> fixed seed, so the panel invoked **each label 30 times in randomized order**;
> `results/clos_split/summary.csv` has carried `n`, `*_cov` and bootstrap
> `*_ci95` for both metrics since **2026-07-29**. The 660 raw files are 22 labels
> x 30, corroborating it independently of the code. So the published quiescent
> **61.71 is a median of 30, CoV 4.39%, CI95 [60.65, 62.05]** -- not a single
> sample, and the "+/-7% from the denominator" figure I quoted was wrong by ~6x.
> I misread the benchmark's internal `--reps 1` as the panel's rep count without
> reading the function that runs the sequence. **Third F11 of the day by me**,
> after the unread decomposition and the stale ledger F1, all the same shape.
>
> **What the exercise did contribute.** The three `bsweep_*` cells are in `raw/`
> but absent from `summary.csv` (theirs is the runner the ledger records as
> missing), so they had n but no published dispersion; computed from raw at n=30:
> CAT 20/20 **87.653, CoV 1.48%**; 12/20 **105.123, CoV 5.29%**; 8/20 **115.814,
> CoV 5.24%**. With those, the monotone-harm column is **statistically solid** --
> steps of +17.47, +10.69, +11.05 cyc against pooled SEs of ~1.05/1.50/1.31, i.e.
> **7-17 standard errors each**, and `PREFETCHNTA` vs unrestricted is ~27 SE.
> Figure 1 is sound on its statistics; its outstanding defects are the missing
> bsweep runner, the filename-carried way count, and the 53%->80% operating point.
>
> **And one real finding.** July's `panel_Q_1c` was **unimodal**, 58.0-62.0, CoV
> 1.64%. The same configuration today is **bimodal**, 55.4-64.7, 16.8% spread;
> July's `panel_Q16` already had a low cluster (8 of 30 at 55.1-57.4) beside a
> high one. So the two-state behaviour existed at 16 cores in July and has since
> appeared at 1 core -- a change in **mos181's state**, not in the benchmark.
> Consequences: T3's absolute values are not comparable to the panel's (its
> internal, same-session, balanced comparisons are unaffected, so its verdict
> stands), and any future re-run of the panel will measure different variance
> than the July CoV column and must say so rather than call it a replication.

> **2026-08-24 (paper edit, lead-authorized) — the 53%->80% operating point is
> corrected in the draft.** Three files in `~/STREAMING_Paper/ASPLOS27/Text/`
> modified, and therefore published to the co-authors:
>
> - `Sec3_Mitigation.tex:73` — "a pre-built open hash table of about 170~MB
>   (53\% of LLC)" -> "**256~MiB (80\% of LLC)**".
> - `Sec3_Mitigation.tex` sweep sentence — the clause "even 12 of 20, **more than
>   the hot table's own share**" is **removed**, because it inverts: at 80% of
>   LLC, 12/20 = 60% is *less* than the table's share. The conclusion it
>   supported -- that the only non-hurting allocation is the trivial one -- is
>   unchanged and still measured.
> - `tab:fused` caption — now states "$n{=}30$ randomized runs per cell, medians;
>   **CoV 1.3--5.3\%**", using the dispersion that has existed since 2026-07-29
>   plus the three bsweep CoVs computed today.
> - `Appendix.tex:76` — same size correction, plus a parameters-section sentence
>   giving the mechanism: `--hot-bytes` is requested as 177,838,489 B (169.6 MiB)
>   and the entry count is rounded up to a power of two, so the instantiated
>   table is 16,777,216 x 16 B = 256 MiB. States that the instantiated size is
>   reported throughout and that drafts before today reported the requested one.
>
> **Checked and deliberately NOT changed:** `Sec2_DirectoryTax.tex:96` and
> `Sec3_Mitigation.tex:24` both describe the **pointer-chase** victim, and
> `pointer_chase.c:171` aligns WSS only up to a 2 MiB boundary with no
> power-of-two rounding, so their "170~MB / 53%" is correct. `Sec5:189/201/239`
> and `Appendix.tex:129-152, 414` are gem5 `tab:sens`/`tab:gem5` rows at a
> different operating point. Brace balance verified unchanged (delta 0, matching
> HEAD) in both edited files.
>
> **One framing decision left to the lead, recorded as a `\jw{}` note in
> `Sec3_Mitigation.tex` rather than decided here.** The corrected figure permits
> a stronger sentence -- "the reused structure alone occupies 80% of the LLC, so
> no non-trivial mask can contain it" -- but it also opens a referee objection:
> an 80%-of-LLC victim makes CAT's failure less surprising. The *scope* failure
> does not depend on table size (the stream shares the CLOS and evicts the
> structure within whatever ways it is given) but the *magnitude* does. The note
> states both, points at the 512 KB sensitivity point already in the file, and
> leaves the choice open. Nothing was committed or pushed in the paper tree.

> **2026-08-24 (E1 arm-identity audit) — E1 is SOUND, and the audit retracts T2's
> headline.** `E1_ARM_IDENTITY_AUDIT_2026-08-24.md`.
>
> **E1 measures the enforced plane.** `Sec2:30` says the WC path uses
> `pgprot_writecombine` with `MOVNTDQA`; traced to
> `benchmarks/e2e/instrument/src/aggressor.c` mode `wc_ntdqa` ->
> `mmap("/dev/cxl_wc")`. The same aggressor implements **`wb_ntdqa` separately**,
> so its author drew the distinction I later collapsed. **Concern closed.**
> Byte-matching was by **thread count** (WB 2T packed vs WC 5T spread, n=12,
> rep-interleaved), not the barred `-R` throttle. Tax numbers reproduce tightly:
> 1.2877x [1.2790,1.3095] vs 1.28x, and 0.9996x [0.9879,1.0136] vs 1.003x.
>
> **T2's headline is RETRACTED.** T2's `C` arm was `MOVNTDQA`-on-WB -- the
> aggressor's `wb_ntdqa`, not `wc_ntdqa` -- so its falsifier fired against a
> claim it could not reach. T2's own prereg said "true WC is still not measured"
> in S3 while asserting in S2 that the paper's arm *was* the WB-page proxy. On the
> correct arms, from `e4_hygiene/RESULTS.md` (n=12, predating today): WB 12.43,
> WC 3.20, **ratio 3.882 vs the implied 3.762 -> CORROBORATED**, with the
> absolute scale ~21-24% low and its candidate causes already recorded. Also
> withdrawn: the claim that "4.2 GB/s" was gem5's 4.17 mislabelled.
>
> **Two real defects found.** (1) The paper never names E1's platform -- the pair
> is **AMD, diff-CCX**, while `Sec1:35`/`Sec2:61` state it bare and Sec2's
> preamble says "eight on Intel", inviting the wrong reading. (2) **F10: the
> `/dev/cxl_wc` driver is not committed** -- only the path `#define` exists, no
> module source, and the device is absent on both Intel hosts with no module
> loaded, so E1's WC arm is not reproducible from this repo.
>
> **Fourth F11 of the day and the worst**, because it produced a
> "delete-from-the-paper" recommendation against a claim that reproduces. Had I
> read `e4_hygiene/RESULTS.md` first, the entire T2 campaign was unnecessary --
> that document already carried the 15.8/4.2 audit with n=12 and CIs.
>
> **Hygiene list, revised by this audit:** REMOVE "delete the intro WB/WC pair".
> ADD: restate the absolutes at 12.43/3.20 or keep 15.8/4.2 with the documented
> ~21-24% scale caveat; name E1's platform at both use sites; commit the
> `/dev/cxl_wc` driver or declare it lost per S6.6; and **rename
> `benchmarks/bench/aggressor/stream_wc.c`**, whose name caused this error and
> will cause it again -- the `instrument` aggressor already uses the correct
> label `wb_ntdqa`.
