# Session prompt: δ fast-path counter audit

Paste everything below the rule into a fresh session. Written 2026-08-10.

Structured as **OSTA** — Objective / Scope / Task / Acceptance. (Stating the
expansion because the acronym is not universal; correct me if you meant a
different one and I will re-cut the same content.)

---

## O — Objective

**Decide whether the ~2× MBM self-report gap in the AMD flush-behind arm is
real coherence traffic or a counting artifact, and thereby bound δ.**

δ is the flush-operation coherence overhead sitting inside the flush-behind
rung of the AMD ladder. It is an artifact of the *emulation*: a real
`PROT_STREAMING` page pays no `clflushopt`, so whatever the flush ops
themselves cost must be subtracted before the rung's recovery can be credited
to H3.

The AMD ladder, as the project lead stated it:

| rung | tax | mechanism at that rung |
|---|---:|---|
| WB | 13.4× | full allocation, full coherence |
| CAT (way-restricted) | 9.7–10.0× | capacity bounded, allocation still happens |
| flush-behind | 4.6× | **non-allocating yet fully coherent** |
| WC | ~1.0× | non-allocating, non-coherent |

Recoverable span = 13.4 − 1.0 = **12.4**.

- CAT→flush isolates shared fill/insertion work → **H2's share ≈ 71%**
- flush→WC isolates coherent lookup + entry occupancy *at matched
  non-allocation* → **H3's share = 3.6 − δ**, i.e. ≤29% of span

Every downstream claim about H3's quantitative weight on real silicon
currently rests on that 3.6, and the 3.6 is an **upper bound** until δ lands.
This audit is the gate. **Nothing downstream starts ahead of it.**

### Standing embargo (in force until this audit completes)

> No document, internal or external, cites the 3.6 without the qualifier
> **"upper bound, flush-overhead unresolved."**

That includes the paper draft, slides, the positioning document, and any
summary written during this session.

---

## S — Scope

### In scope

- AMD EPYC 9754, the same host and frozen config as Phase 2.4.
- Counter reads and short confirmatory runs against the **existing**
  flush-behind arm. The heavy sweeps are already done; this is hours, not days.
- Small, additive modifications to `amd_flushbehind_aggressor.c` for the two
  control arms in T3 and T4.

### Explicitly out of scope — do not start these

- **§4.2 prose, the ReadOnce re-derivation, the H3 spec upgrade, the two-tier
  framing, the §5 mechanism rewrite (the four snoop-filter-language sites), or
  the `tab:h3sf` caption/supersession note.** All are embargoed on this result.
- **Build B validation** (gem5 finite-transaction-pool model). Its
  *construction* is unparked; its *validation criterion* is what this audit
  sets. Do not run validation.
- Re-running the D-sweep. It exists. See `phase2_AMD_flushbehind_OUTCOME.md`.
- Any Intel work. This is an AMD-attribution question.

### Hard boundary

Do not touch `~/STREAMING_Paper/`. That repo has an autosync process that
commits (`-m .`) and **pushes to Overleaf** on its own; anything written there
leaves the machine without review.

---

## T — Task

### T0 — Reconcile the arm identity before computing anything

There is a live inconsistency that must be closed first, and closing it is
itself a deliverable.

The ladder quotes the flush-behind rung at **4.6×**.
`phase2_AMD_flushbehind_OUTCOME.md` reports best-case recovery at **5.94×**
(D=256 KiB), with the full sweep:

| D | tax | 95% CI | agg bw self / MBM (GB/s) | victim occupancy (MB) |
|---|---:|---:|---:|---:|
| 32 KiB | 6.182× | [6.061, 6.230] | 16.38 / 31.90 | 2.87 |
| 256 KiB | 5.939× | [5.823, 5.985] | 17.04 / 33.05 | 2.93 |
| 2 MiB | 8.126× | [7.397, 9.158] | 12.64 / 24.12 | 2.50 |
| 16 MiB | 17.489× | [17.148, 17.612] | 22.30 / 38.03 | 0.14 |
| 64 MiB | 20.901× | [20.497, 21.054] | 24.69 / 24.09 | 0.16 |
| off | 20.843× | [20.434, 20.990] | 24.66 / 24.07 | 0.15 |

4.6 and 5.94 are not the same number. Either the ladder is drawn from a later
or differently-configured run, or the 4.6 is a different operating point, or
one of them is wrong. **Find which, name the operating point inline, and do not
compute δ against a rung whose identity is unsettled** — the whole point of
this audit is a subtraction, and a subtraction is only as good as its minuend.

Apply the arm-identity rule while you are here: every tax figure gets its arm
and operating point named at the point of use, not in a distant caption.

### T1 — The fast path: is the MBM doubling real? (primary, cheapest)

The finding to adjudicate, from `phase2_AMD_flushbehind_OUTCOME.md`:

> At D=32/256 KiB/2 MiB, resctrl MBM reads roughly double the aggressor's own
> self-reported bandwidth (D=256 KiB: self=17.04, MBM=33.05 GB/s); at
> D=64 MiB/off the two agree closely (24.69 vs 24.09).

Note the sweep table shows D=16 MiB at 22.30 / 38.03 — a 1.71× gap, so the
effect is **rate-dependent**, not a binary flushing-on/off switch. The outcome
doc's prose omits that row from its list; the numbers do not. That gradient is
useful signal, not noise.

The doc's own hypothesis, flagged there as unconfirmed:

> `clflushopt`-driven eviction of a CXL-sourced line may generate a coherence
> message (invalidate/notify-home) that MBM counts as bytes moved.

**The discriminating read.** Three quantities, same run, flush arm vs WB arm:

1. **Home / coherent-station request count** — the uncore's count of
   transactions presented to the coherence point.
2. **Bytes actually moved** — UMC/IMC for local, plus the CXL-side counter for
   the streamed buffer. This is the wire truth.
3. **The aggressor's own self-report** — bytes the program asked for.

Discover the exact events on the machine rather than trusting event names from
memory: `perf list | grep -iE 'amd_df|umc|l3|ccm'`, and check whether
`mbm_total_bytes` vs `mbm_local_bytes` already separates the two under resctrl
(the existing runner reads only `mbm_total_bytes`, via `read_mbm()` in
`run_p24_amd_flushbehind.py:47`).

**Decision rule, pre-registered:**

- **home requests ≈ 2× per byte, data moved ≈ 1×** → each flush raises a real
  home transaction carrying no data. Maximal-severity case confirmed; δ is
  potentially large. Proceed to T3/T4 to size it.
- **home requests ≈ 1.05×** → the doubling is a resctrl event-selection quirk
  (MBM counting evictions/flushes as traffic with no home transaction behind
  them). δ is small. T3/T4 become confirmatory rather than load-bearing.
- **anything in between** → the fast path has not resolved it; T3 and T4 are
  now primary, and say so explicitly rather than leaning on the closer endpoint.

### T2 — Double-flush intercept: run it, but as a *one-sided bound only*

Method: flush each line once (tax₁) vs twice (tax₂) at fixed fetch rate; fit
tax(n) = H2_true + n·c through n∈{1,2}; take δ̂ = tax₂ − tax₁ and read the
intercept at n=0 as H2_true.

**This estimator is biased, and the sign of the bias is knowable.** Flush #2
lands on a line that is already invalidated — the expensive case: a transaction
that still has to be presented to the coherence point but finds nothing to act
on. So the marginal cost is increasing, not constant:

> tax(2) − tax(1) > tax(1) − tax(0)

Consequences: the fitted intercept sits **too low**, true H2 is **understated**,
and **δ̂ overstates δ**.

That is not a reason to skip it — a bias with a known sign is a bound. δ̂ is a
**conservative upper bound on δ**, so:

- if **δ̂ ≤ 0.9**, the H3-decisive verdict holds *a fortiori* and the audit can
  stop early;
- if δ̂ lands in or above the middle band, T2 is **uninformative** and must not
  be reported as a point estimate of δ.

Do not use the batch-size lever as a substitute. Varying flush batch size holds
the total flush count constant (every line is flushed exactly once), so it
varies burstiness, not rate, and cannot isolate per-op cost. That approach was
raised and withdrawn.

### T3 — Additive disjoint-buffer control (primary estimator of δ)

Because T2 is one-sided, **this is the estimator the verdict should rest on.**

Run the plain WB arm (full residency, no flush-behind) and add a flush loop
issuing `clflushopt` at a **matched op-rate** against a **disjoint** buffer that
the victim never touches and that stays resident. The tax delta versus plain WB
is the cost of the flush operations alone, at matched rate, with the streaming
arm's allocation behavior unchanged. Subtract → δ, additively, with no
extrapolation.

State its own caveat in the write-up rather than presenting it as clean:
additivity may not hold (flush cost need not superpose with the streaming arm's
own uncore pressure), and the disjoint buffer's flushes hit *valid, resident*
lines while the real arm's hit lines mid-pipeline — a different coherence-state
distribution. T3 is not bias-free; its bias simply sits somewhere other than
T2's, which is exactly why running both is worth the hours.

### T4 — Triangulate

Three estimates of δ: T1 (counter contrast), T3 (additive control, primary),
T2 (one-sided upper bound). **Require agreement in *band*, not in value.** If
they disagree on band, the conservative reading — the largest δ — governs the
prose until Build B settles it, and the disagreement itself gets written down.

---

## A — Acceptance

### The pre-registered verdict table

| δ | H3's share of the 12.4 span | verdict |
|---|---|---|
| **δ ≤ 0.9** | ≥ 2.7, i.e. **≥22%** | H3 **decisive**; the promotion stands |
| **0.9 < δ ≤ 1.8** | 1.8–2.7, i.e. 14.5–22% | H2 and H3 **co-equal**; both tiers load-bearing |
| **δ > 1.8** | < 1.8, i.e. <14.5% | H3 **demotes** to "structurally unique but quantitatively secondary" |

### The inconclusive branch (missing from the table as originally drawn — add it)

**If the 95% CI on δ straddles a band boundary, declare INCONCLUSIVE.** Do not
round to the nearer band; do not report the point estimate as if the band were
settled. Escalate in this order: more reps → the remaining discriminator → if
it still straddles, report H3's share in the paper as an **interval** and hand
the resolution to Build B.

A straddling CI is a real outcome of this audit, not a failure of it. The
banded criterion exists precisely so that "we do not yet know which tier is
load-bearing" is a sayable result.

### Deliverables

1. **`DELTA_AUDIT_PREREGISTRATION.md`**, written **before** running — following
   the house format already set by `PHASE2_AMD_FLUSHBEHIND_PREREGISTRATION.md`
   and `GATE1_CORUN_PAIR_PREREGISTRATION.md`: operating point stated
   explicitly, falsifiable prediction, and what each outcome means.
2. Raw `.jsonl` per arm, n≥12, rep-interleaved, matched-warmup — the standard
   this campaign has held to throughout.
3. **`DELTA_AUDIT_OUTCOME.md`**: the T0 reconciliation, the three δ estimates
   with CIs, the band verdict (or INCONCLUSIVE), and the T1 mechanism call on
   whether the MBM doubling is real.
4. A **number-registry** line for each figure produced, with its arm identity
   and operating point attached.
5. An explicit statement of whether the embargo on the 3.6 lifts, and if it
   lifts, the exact replacement wording.

### Done means

The band is called (or INCONCLUSIVE is declared with the straddle shown), the
4.6-vs-5.94 identity is closed, everything is committed, and **no embargoed
downstream prose has been written.** Report the verdict; do not act on it in
this session.

---

## Context appendix

### File map

| what | where |
|---|---|
| AMD flush-behind streamer | `experiments/phase1/e1_residual_decomp/amd_flushbehind_aggressor.c` (`-f <flush_distance_KiB>`, 0=off; `kern_flushbehind()` at L38) |
| its runner | `.../run_p24_amd_flushbehind.py` (`read_mbm()` at L47) |
| raw sweep data | `.../p24_raw_n12.jsonl` |
| the finding under audit | `.../phase2_AMD_flushbehind_OUTCOME.md` §"Secondary finding" |
| pre-registration to imitate | `.../PHASE2_AMD_FLUSHBEHIND_PREREGISTRATION.md` |
| lookups-only arm (1.28×, independent corroboration) | `.../lookups_aggressor.c` |
| Intel-side sibling streamer | `benchmarks/bench/aggressor/stream_wb_flushbehind.c` |
| repo conventions | `experiments/asplos/REPO_DISCIPLINE.md` |

The AMD streamer is built by the hand-written `gcc` line in its own header
comment (L18–19), not by a Makefile. Its Intel sibling **is** now in
`benchmarks/bench/Makefile` — that rule was added 2026-08-10 (`REPO_DISCIPLINE
#9`) after the two flush-behind/sw-prefetch binaries were found to be
unbuildable from a clean tree. If you modify the AMD streamer for T3/T4,
consider giving it a Makefile rule too rather than repeating the pattern.

### Corroborating result

The lookups-only arm measures **1.28×** independently — a tax from coherent
lookup with no allocation and no flush ops at all. It is a floor on the
lookup component and a useful sanity check on any δ that would leave H3's
share implausibly small.

### Two errors already made on this material — do not repeat them

- **0.9915 / 0.9913 / 0.9905 (Intel, D≤2 MiB, 98.7% of unbounded bandwidth) is
  the corrected E2b flush-behind result.** It is *not* CAT-with-a-disjoint-mask.
  CAT-1-way separately lands at 0.99×. Two independent emulations coincidentally
  landing on the same value; conflating them has happened once already.
- **The Intel D-sweep does not stop at the 2 MiB L2 boundary.** It runs
  32 KiB → 64 MiB → off and shows the same inflection structure as AMD. Both
  vendors supply the positive control.
