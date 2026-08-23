# Plan B: skip Sep 9, rebuild the paper the evidence supports

Written 2026-08-23. Supersedes the ASPLOS'27 Sep 9 push. Lead decision.

## Why

Four facts, each measured in this repo, that jointly make the Sep 9 submission
a reject:

1. **H2 is inert in our own simulator.** `tab:h3sf` re-measured 2026-08-20 at a
   documented geometry: WB/finite-SF 2.501x, H2/finite-SF 2.512x
   ("indistinguishable at +/-0.07"), H2+H3 1.061x. The entire gem5 benefit is
   H3. The mechanism in the paper's title recovers nothing in the only
   configuration it is reported in.
2. **H3's charge is absent on shipping silicon.** Private-L2-resident victims
   read 1.000x on SPR and Bergamo; mos182's forced SF turnover reads 1.00x.
3. **So the two instruments do not meet.** Silicon measures a *capacity*
   charge. gem5's benefit removes a *back-invalidation* charge. The
   gem5-shows-benefit / silicon-shows-harm division of labour requires them to
   be the same charge at different fidelity. They are not.
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

## W1 -- The decisive cell. Gates everything. Start immediately.

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

## W2 -- Benefit under scrutiny. Only if W1 passes.

- **W2.1 P0-1 bandwidth-matched de-confound.** Already designed. Show H2's
  recovery is not "the aggressor got slower." Without this, the first reviewer
  kills the result.
- **W2.2 Working-set sensitivity.** The whole benefit claim currently sits at
  one point (2650 KiB victim = 53% of a 5 MiB LLC). Sweep victim WSS so it is a
  curve. Establishes where H2 helps and where it does not -- which is a
  scope result, not a weakness.
- **W2.3 LLC size / associativity sensitivity.** `tab:sens` exists; extend to
  the H2 arm.

Effort: ~1 week compute + analysis.

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
- **W3.2** Acquire an inclusive-LLC machine (Broadwell/Haswell Xeon) and repeat
  the L2-residency test. A positive here grounds H3 in silicon and repairs the
  gem5/hardware mismatch outright.
- **W3.3** Fold in the existing Sec9 "obtain an Arm server" question -- same
  experiment, different hierarchy.

Outcome is useful in both directions: either H3 gets silicon grounding, or the
paper gets simpler and more honest by dropping it.

## W4 -- Provenance audit. Start now, in parallel with W1. Referee's named reject reason.

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
- **W4.4** Confirm no published number traces to the pre-D1/D2-fix binary.
  Rebuild that binary on mos181 -- now unblocked, the `ld_*` sims are done.

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

## W6 -- The cost argument. Currently absent; it is what makes modest benefit sufficient.

Nobody adds hardware for 6%. People do add a PAT encoding for 6%.

- **W6.1** Hardware cost: unused PAT slot 6, one PTE bit, TLB carry, one
  fill-path predicate. Argue explicitly against datapaths that already exist for
  WC and MOVNTDQA -- no new coherence states, no new structures.
- **W6.2** OS cost: the mmap/mprotect flag, PAT setup, immutability enforcement
  (I0/I1). Partly written already.
- **W6.3** State the comparison honestly: CAT shipped for less benefit than this.

## W7 -- Necessity and benefit at the same operating point. The structural gap.

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

## W8 -- gem5 FS capability demonstration. Stretch, not critical path.

`GEM5_FS_OS_CONTRACT_PREREGISTRATION.md` is written and has never been run.
Closes the "is this implementable end to end" question: guest kernel encodes
PROT_STREAMING as PAT slot 6, the x86 walker classifies, CHI applies H2/H3.
Explicitly a capability demonstration, not a calibration claim.

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
| 1 | 2-4 | W2 (benefit under scrutiny), W5 (restructure), W6 (cost argument) |
| 2 | 5-9 | W3 (H3 grounding), W7 (necessity+benefit convergence) |
| 3 | 10-12 | W8 if it fits; full rewrite; 18pp -> target length |

Phase 1 onward is conditional on W1 passing.

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
   paper's shape.
5. `EUNJI_QUESTION_DRAFT.md` still must be sent by the lead personally.

# Next 72 hours

1. Resolve the seed question in b4run2.sh, then launch the three W1 runs on
   mos181 (idle, no contention).
2. Start W4.1 and W4.2 -- both are pure deletions/corrections, needed under
   every outcome including a hypothetical return to Plan A.
3. Rebuild the D1/D2-fixed binary on mos181, now unblocked.
