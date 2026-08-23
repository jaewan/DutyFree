# W7 pre-registration — necessity and benefit at the same operating point

> **Amendment 1, 2026-08-24 — Knob B's `k` is set to 16, not 8.** §2 says
> "`k = 8`, tunable"; this is the tuning. It is recorded here, above the
> original, per §6, and the original text below is unchanged. Justification is
> a native measurement made **before any A1 or gem5 datum exists** and blind to
> the outcome: against a 512 MiB hot table on mos181 (LLC 320 MiB, so the probe
> misses for real) `active_cycles_per_access` falls 132.63 → 112.43 → 90.83 →
> 77.49 for k = 0, 8, 16, 32. k=8 buys 1.18×, k=16 buys 1.46×, and the gain
> saturates by 32. k=16 is also exactly the modelled core's L1d TBE budget, so
> §2's target of "≥8 of the 16 TBEs occupied" is centred rather than at the
> edge. **k=2 is worse than serial** and the knob must not be set below 4.
> Full data and the correctness gate: `W7.1_KNOB_B_2026-08-24.md`.
>
> **Amendment 2, same day — the `--check` clause in §2 is withdrawn.** §2 says
> the `matches_last_rep` equality check "remains a valid correctness gate across
> arms." The equality gate is valid and is what W7 uses. The `--check` *flag* is
> not: `c.check` is read only in `run_single`, and `run_morsel` ignores it
> entirely, so the flag has been inert in every morsel run ever made — including
> the ones `run_gem5_fused_null.py` passes it to. Ledger **F12**. The gate is
> the cross-arm comparison, performed explicitly, not a flag.


Written 2026-08-23, before any run. Design only; nothing here has been executed.
Per §6.6 the predictions and their falsifiers are fixed now, not after.

`PLAN_B_REBUILD.md` calls W7 "the experiment that would make the paper whole."
Today no single workload both *requires* Streaming and is *measurably fixed* by
it. The fused morsel hash join proves necessity — 1.47× same-core, and CAT
recovers nothing (214.6 → 215.0 Mtuple/s) because a same-thread stream and its
victim share one CLOS by construction — but it is not where H2 pays off.

## 1. The plan names one obstacle. There are two, and they are separable.

### O1 — memory-level parallelism (already on record)

`GATE1_FUSED_NULL_CORRECTION_2026-08-15.md` §4: the fused kernel burns ~59
cycles per 16 B tuple on hash plus a dependent probe load and keeps ~**1.3 lines
in flight against a 16-entry L1d TBE budget** — 8.1% occupancy. It reaches
0.52 GB/s where the same binary with the probe chain removed reaches 4.17 (WB)
and 4.78 (H2), against an MLP ceiling of 16 × 64 B / 203 ns = 5.04 GB/s. So the
fused kernel runs at 10% of the ceiling and an efficiency gain at the HNF has
nothing to convert into.

### O2 — the modelled hierarchy is compressed, and this is *new here*

|  | gem5 model | Xeon 8592+ | compression |
|---|---:|---:|---:|
| per-core L2 : LLC | 2 MiB : 5 MiB = **2.5×** | 2 MiB : 320 MiB = **160×** | **64×** |
| aggregate ΣL2 : LLC | 4 MiB : 5 MiB = **1.25×** | 128 MiB : 320 MiB = **2.5×** | **2×** |
| SF coverage of ΣL2 (W3.1) | 65,536 entries = 4 MiB = **1.0×** | provisioned at a multiple | — |

Geometry read from `/tmp/sf_wb_inf_s1/config.ini`, the `tab:h3sf` apparatus
itself: 2 CPUs, L1D 48 KiB/12-way, L2 2 MiB/16-way each, HNF 5 MiB/20-way.

Consequences the memo's §1.3 states for the first row and this document extends:
the H2-protectable window is `(2 MiB, 5 MiB]` — the victim must exceed the
private L2 or it never needs the LLC, and must fit the LLC or protecting LLC
capacity cannot make it resident. **One power of two lies strictly inside it.**
At that one point, 4 MiB, the victim occupies 80% of the LLC and leaves 1 MiB of
headroom for everything else.

### O2 is not a restatement of O1, and the counters say so

At the 4 MiB arm, WB → H2:

| counter | WB | H2 | change |
|---|---:|---:|---:|
| HNF fills | 1,340,360 | 542,011 | **−59.6%** |
| LLC hit rate | 53.6% | 53.9% | **+0.3 pts** |
| DRAM read | 12.09 MB | 10.05 MB | −16.9% |
| cyc/access | 72.428 | 71.993 | −0.6% |

H2 did exactly what H2 is for: it kept the stream out, cutting fills by 60%.
**The victim still did not become resident** — 53.6 → 53.9 is inside the noise.
Against a full-rescue floor of one compulsory 4 MiB load (4.19 MB), H2 realised
2.04 MB of an achievable 7.90 MB, or **25.8%** of the residency gain that was
there to take.

That is the separation. If O1 were the whole story, residency would have
improved and only *time* would have failed to follow. Residency barely moved.
The memo's conclusion — "H2 works and the fused kernel cannot express it" — is
right about the kernel and incomplete about the model: at 1 MiB of LLC headroom,
excluding the stream is not sufficient to make a 4 MiB victim resident, so
**the model could not deliver most of the benefit even to a workload that could
express it.**

## 2. Design — a 2×2 that separates the two obstacles

Both knobs move the experiment *toward the target hardware*, not toward a
desired answer. §6 below states what would make that false.

**Knob A — hierarchy.** Raise LLC : per-core L2 from 2.5× toward the part's
160×. Concretely: L2 512 KiB/core, LLC 32 MiB → 64×; victim 8 MiB (25% of LLC,
16× the private L2, comfortably inside both bounds, and a power of two so `F9`'s
`table_capacity` rounding is a no-op). Aggregate ΣL2 : LLC becomes 1 MiB : 32 MiB
= 32×, which over-shoots the part's 2.5× in the other direction — so a second
A-point with 8 cores (ΣL2 4 MiB : 32 MiB = 8×) is included, and the ratio itself
becomes a reported axis rather than a fixed assumption.

**Knob B — MLP.** Batch the probe. Issue `k` independent hashes and their probe
loads before consuming any result, so the dependent chains overlap instead of
serialising. Target ≥8 of the 16 L1d TBEs occupied (`k = 8`, tunable). This is a
software-pipelining change to `cxl_join_bench.cpp`'s fused loop only — same
tuples, same matches, same `--check` hash — so the `matches_last_rep` equality
check remains a valid correctness gate across arms.

Four cells, each WB vs H2 (8 runs), plus a `--mode stream-smoke` bandwidth
reference per hierarchy point (4 runs):

| | A0 = current hierarchy | A1 = realistic hierarchy |
|---|---|---|
| **B0 = serial probe** | reproduces the known null | isolates O2 |
| **B1 = batched probe** | isolates O1 | the convergence cell |

Per W1.3, three repeated identical runs per cell for a variance estimate; and
per §6.1 of the correction memo, repeated runs, **not** a `SEED` sweep.

## 3. Pre-registered predictions

Primary metric: `cyc/access`. Secondary: DRAM read bytes, LLC hit rate, achieved
stream GB/s, lines in flight.

- **P1 (O2 isolated, A1/B0).** Residency responds where it could not before:
  LLC hit rate rises by **≥15 points** WB→H2, and DRAM read falls by **≥50%**
  of the achievable saving (vs 25.8% today). *Falsified below 25.8%* — that
  would mean the hierarchy was never the constraint and O2 is withdrawn.
- **P2 (O1 isolated, A0/B1).** Lines in flight rise from ~1.3 to **≥6**, and
  achieved fused bandwidth from 0.52 to **≥2.0 GB/s**. *Falsified below 3 lines*
  — the batching did not take, and the cell says nothing.
- **P3 (convergence, A1/B1).** `cyc/access` falls WB→H2 by **≥5%**. This is the
  number W7 exists to produce. *Falsified below 2%.*
- **P4 (necessity survives the change).** CAT applied to the A1/B1 cell recovers
  **<2%** of the WB→H2 gap, because the stream and the victim remain the same
  thread and therefore the same CLOS. *If CAT recovers it, W7 has produced a
  benefit result and destroyed the necessity result*, and the paper is no better
  off. This is the prediction most likely to fail and it is the one that matters.
- **P5 (ordering).** P3's effect exceeds both P1-alone and P2-alone effects on
  `cyc/access`. If either single knob already delivers ≥5%, the 2×2 is
  unnecessary and the simpler experiment is the one to report.

## 4. What a negative result buys

If P3 fails at A1/B1 with P1 and P2 both confirmed, then a workload that both
requires object scope and runs in the protectable regime **still** shows no
time benefit, with both known obstacles removed. That is a much stronger
statement than today's null, and it argues for dropping the benefit claim
entirely and shipping the scope-and-cost paper. Either outcome is publishable;
the current state — a null with two unexcluded explanations — is not.

## 5. Cost

12 gem5 runs at the A0 scale (~1.5 h each, parallelisable across mos181's 256
cores) plus 12 at A1. A1 runs are larger: 32 MiB LLC and an 8 MiB victim will be
slower than the 5 MiB/2.65 MiB cells, and the A1/8-core point slower again.
Budget ~3 days wall clock with the campaign parallelised, one week with analysis.
This sits in phase 2 of `PLAN_B_REBUILD.md` and is **gated on W1**: if W1 returns
FAIL, H2 recovers nothing anywhere and W7 has nothing to converge.

## 6. Legitimacy under §6.6, stated explicitly

Changing the model until the answer appears is exactly what §6.6 forbids. The
defence is that Knob A is specified **before** any A1 datum exists, is justified
by a ratio mismatch against the target part that is measurable independently of
the outcome (64× and 2×, §1), and has a stated falsifier (P1 below 25.8%).

This becomes illegitimate the moment A1's geometry is tuned after seeing a
result. So: **A1 is fixed here at L2 512 KiB / LLC 32 MiB / victim 8 MiB, with a
second point at 8 cores.** If those numbers change, the change and its reason go
in this file, dated, above the original — and the original stays.

## 7. Relationship to the rest of the plan

O2 is the third instance of one defect: the model's cache ratios are not the
part's. W3.1 found it on the snoop filter (SF at 1.0× of ΣL2; shipping parts at
a multiple) and closed H3 to a capability claim. F9.1/F9.6 found the same shape
on the hash-table side — 53% of the LLC is *unreachable* on both the 320 MiB
part and the 5 MiB model, for the same power-of-two reason. Edit-queue row 19
already qualifies `tab:h3sf` on the SF axis; if W7 runs, an equivalent
qualification is owed on the LLC axis.

---

# Addendum, 2026-08-24 ~04:15 — how P2's falsification constrains P5, and a disclosure

The original text above is unchanged. This addendum is appended, not edited in,
per the practice A6.19 fixes for committed markdown.

## What I have seen, and what I have not

Written with 22 of 28 cells complete. Of P5's four cells I have seen **three**:

| gap (cyc/access, WB→H2) | value | seen? |
|---|---:|---|
| A0/B0 | +0.534% | yes, n=3 |
| A0/B1 | +1.234% | yes, n=3 |
| A1/B1 | +0.628% | yes, n=3 |
| A1/B0 | — | **no**, still running |

## Disclosure: P5's verdict is already determined, so this is NOT a blind
##            pre-registration of it

`w7_analyze.py` reports the 2×2 justified iff `gap(A1/B1) > max(gap(A0/B1),
gap(A1/B0))`. Two of those three are already known, and **0.628 < 1.234**, so
the condition is false *for every possible value of the unseen A1/B0 gap*.

**P5's binary outcome is therefore fixed before its last cells land: the 2×2
does not pass the ordering test.** A1/B1 is not the largest H2 effect; A0/B1 is,
and it is 2× larger.

I state this rather than presenting the rules below as blind, because they are
not blind with respect to P5 and it would be easy to imply otherwise. **P1 is
genuinely blind** — it is evaluated at A1/B0 alone and I have seen neither of
its arms.

## The reading rules, registered now

**(R1) The B axis did not reach strength, and a small B contribution may not be
read as evidence about O1.** P2 is falsified: batching reached 1.77 lines in
flight against a required ≥6, i.e. it moved ~26% of the bandwidth where roughly
340% was needed. Any P5 or P3 statement in which the B axis appears to
contribute little is therefore **confounded** — the knob barely moved, and a
null on a knob that barely moved is uninformative about that knob's target. This
is the exact analogue of `W7.2`'s rule for the mis-sized A1, registered here for
the same reason: before the affected data is in.

**(R2) A "2×2 justified" outcome could only have been stated at the realized
point.** Moot now, given the disclosure above, but recorded so the rule is not
invented later: it would have had to read "with the MLP axis relieved only to
1.77 lines, 12% of the machine's measured 14.62-line ceiling" (§5.1).

**(R3) The sufficiency escape clause is dead, and may not be invoked
selectively.** §3's P5 says "if either single knob already delivers ≥5%, the
2×2 is unnecessary and the simpler experiment is the one to report." Every H2
effect measured anywhere in W7 is **≤1.23%**. No single knob delivers ≥5%, so
this clause does not fire, and the correct statement is not "a single knob
suffices" but **"no knob tested suffices."** Registered now so that neither
reading can be selected after A1/B0 lands.

**(R4) F12 in my own analyzer, found and fixed.** `w7_analyze.py`'s P5
else-branch printed *"a single knob already suffices; report the simpler
experiment"*. That branch is a **dominance** test, not the **sufficiency** test
R3 describes, and on the measured data its string asserts the opposite of the
truth. Wording corrected 2026-08-24; **the computation is byte-identical** and
the change is annotated in place with its date and reason, because editing
analysis code after seeing data is precisely what §6.6 polices. Anyone auditing
should diff the function and confirm only strings moved.

## What §4 is still owed

§4's strong-negative story requires "P3 fails at A1/B1 with P1 and P2 both
confirmed." P2 is falsified, so **that story is unavailable** and §4 may not be
quoted as though it were still live. What replaces it depends on P1, which is
still blind, and is not decided here.

---

# Addendum, 2026-08-24 ~04:40 — P1 may be arithmetically unevaluable at A1

Appended, original unchanged. Written **blind to both A1/B0 arms**, which are
still running; the constraint below is derived from A1/B1, which I have seen.

**(R5) P1's hit-rate half may be outside the range of its own metric.** P1 reads:
"LLC hit rate rises by **≥15 points** WB→H2." At the one A1 cell visible, the WB
arm's LLC hit rate is **97.61%**, leaving **2.39 points** of headroom to a
perfect cache. If A1/B0's WB arm is similar — and it should be, since batching
does not change what is fetched — then **no policy whatever can produce +15
points**, and P1's hit-rate criterion is not a hypothesis about H2 but an
arithmetic impossibility.

Registered rule, conditional so it is decidable when the data arrives: **if
A1/B0's WB LLC hit rate is ≥85%, P1's hit-rate half is reported as NOT EVALUABLE,
not as falsified.** This is stronger than and distinct from `W7.2`'s protection.
`W7.2` says a falsified P1 at A1 is "a null at a different point"; R5 says the
threshold lies outside the metric's range, so there is no experiment at any
operating point of this machine that could have confirmed it.

P1's **DRAM half** ("≥50% of the achievable saving, falsified below 25.8%") has
range and stays evaluable, under `W7.2`'s existing rule. For reference, the same
computation at A1/B1 yields 14.5%.

**Why A1 did this.** A1 was chosen to relieve O2 so that H2 would have room to
work. It over-relieved it: an 8 MiB hot table in a 20 MiB effective LLC is 97.6%
resident, so there is almost nothing left for an admission policy to protect,
which is the obvious candidate for why H2 moves A1/B1 by only 0.63%. That
diagnosis is measurable independently of the outcome — the §6.6 standard — and
is registered here rather than offered later as an excuse. See also
`W7.4_PREFETCHERS_AND_THE_CXL_ANOMALY_2026-08-24.md` §2a: at A1 the fact array is
31.5% LLC-resident in the WB arm, so A1 is not the streaming regime either.
