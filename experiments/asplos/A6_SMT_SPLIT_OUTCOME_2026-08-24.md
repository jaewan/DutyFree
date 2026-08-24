# A6 outcome: the SMT-sibling split fails — the last cheap hostile configuration is closed

Registered in `T4_SCOPING_PREREG_2026-08-24.md` Addendum 1 (A6) and Addendum 3
(concrete arms), both committed before the run (`82b0af1`, `a895a40`). Runner
`run_a6_smt.sh`, data `benchmarks/e2e/hash_join/artifacts/a6_smt/`, 48/48 records,
stderr archived. mos181, n=12 per arm, randomized Latin square — **every arm in
every position exactly 3×** (verified).

## Verdict

> **Splitting the fused kernel across SMT siblings does not recover the fused
> cost. At equal physical resources it is 7.3% worse in hot-table cycles/access
> and 6.8% worse in throughput.** The registered threshold required a ≥10%
> cyc/access *improvement*; the measurement is in the opposite direction.
>
> **The last cheap hostile configuration against Branch B's inexpressibility
> claim is closed — by us, not by a referee.**

## The data

| arm | n | cyc/access | sd | CoV | throughput (Mt/s) | sd | CoV | physical cores |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Q (`morsel --no-stream`) | 12 | 92.461 | 0.526 | 0.57% | 20.530 | 0.117 | 0.57% | 1 |
| **F** (fused, 1 thread) | 12 | **90.850** | 2.766 | 3.05% | **20.912** | 0.628 | 3.00% | **1** |
| **Ssmt** (split on cpu32,160) | 12 | **97.523** | 4.074 | 4.18% | **19.500** | 0.815 | 4.18% | **1** |
| Score (split on cpu32,33) | 12 | 92.705 | 2.858 | 3.08% | 20.493 | 0.611 | 2.98% | 2 |

The arm is self-evidencing: the binary reports `thread_mapping` with
`{cpu: 32, physical_core: 32, role: scan}` and
`{cpu: 160, physical_core: 32, role: probe}` — one physical core, two logical
CPUs, roles labelled.

## Primary, resource-matched (F and Ssmt both occupy one physical core)

| | F | Ssmt | change | registered requirement |
|---|--:|--:|--:|---|
| hot-table cyc/access | 90.850 | 97.523 | **+7.3%** | needed ≤ −10% |
| throughput | 20.912 | 19.500 | **−6.8%** (93.2% of F) | floor was 90% |

Throughput stays above the registered 80% floor, so this is not a collapse — but
there is no recovery, and the "cyc/access no better than F" clause fires.
**Verdict: fails.**

## Secondary: SMT's shared L1/L2 buys nothing

Ssmt vs Score: **+5.2%** worse in cyc/access and **−4.8%** in throughput — and
Score has **twice** the physical cores. So keeping the SPSC ring inside a shared
L1/L2 does not rescue the split organization; the ring's locality is not what
made the cross-core split expensive. Whatever the split costs, it is not
cache-locality on the queue.

## An independent corroboration of the split's cost

Per-physical-core throughput: Score delivers **10.247** Mt/s/core against F's
**20.912** — the cross-core split costs **51.0%** of per-core throughput at 1+1
scan:probe. The paper reports 36% at 8+8. Different scale and configuration, so
not the same number, but the same direction and magnitude class, arrived at
independently. Note the standing requirement: Score's *absolute* throughput
(20.493, essentially matching F's 20.912) must never be quoted without stating
that it used two physical cores to get there.

## What this is worth to the paper

This is the first result today that **closes an attack instead of opening one.**
The argument it protects is `Sec3`'s: restructuring so that a context-scoped
control *can* apply costs more than the control recovers.

The panel identified SMT-sibling split as the cheapest remaining hostile
configuration, and the reasoning was sound — it creates two TIDs, so per-TID CLOS
genuinely *does* become expressible, and it keeps the locality that the
cross-core split forfeits. The measurement says the reorganization still does not
pay: **the cost of becoming expressible exceeds anything the expressed control
could recover, even in the cheapest form of the split available on the machine.**

That extends `Sec3`'s split argument from "restructuring costs 36% of throughput"
to "and it costs that even at the shared-L1/L2 limit", which is the strongest
form of the claim the hardware permits.

One honest note in the other direction: Ssmt also has the **highest variance** of
any arm (CoV 4.18% vs 3.05% for F), consistent with SMT contention adding
run-to-run noise. The effect is well outside that spread (+7.3% against a 4.18%
CoV at n=12), but the arm is the noisiest one measured.

## Scope

This measures whether the SMT split is *viable*. It does **not** measure whether
CAT applied to the resulting two TIDs helps — deliberately out of scope, and now
moot: since the split does not pay, what a control could do with its TIDs does
not arise. Registered as such before the run.
