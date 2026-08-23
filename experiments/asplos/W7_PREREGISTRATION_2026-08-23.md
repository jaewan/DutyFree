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
