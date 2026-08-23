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
