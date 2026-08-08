# Clean-CCX co-measured session: outcomes

Dated 2026-08-09. Predictions pre-registered in
`PHASE2_CLEAN_CCX_PREREGISTRATION.md` before running. This file records
what happened, per the campaign's convention of never editing the
pre-registration after the fact.

## Session

`run_clean_ccx_session.py`, CCX1 (`victim=cpu8`, `aggressors=cpus 9-15`),
n=12, rep-interleaved: quiescent, wb, wb_cat, wc, flush_d256kb, and a
1T/2T/3T concurrency sweep. MSR-verified disjoint CAT enforcement
confirmed on every `wb_cat` rep (CLOSID 1→0xff00, CLOSID 2→0x00ff).

| arm | tax | 95% CI | agg BW self (GB/s) | agg BW MBM | occupancy (MiB) |
|---|---:|---:|---:|---:|---:|
| wb | 13.435 | [13.335, 13.714] | 24.69 | 24.19 | 0.20 |
| wb_cat | 9.736 | [9.673, 9.926] | 24.68 | 24.21 | 2.28 |
| wc | 0.996 | [0.984, 1.011] | — | — | 3.59 |
| flush_d256kb | **4.612** | [4.560, 4.700] | 17.03 | 33.14 | 2.64 |
| t1 | 2.828 | [2.004, 3.002] | 12.76 | 12.75 | 1.61 |
| t2 | 4.495 | [4.450, 4.575] | 21.59 | 21.44 | 0.38 |
| t3 | 9.954 | [8.702, 11.748] | 24.16 | 23.92 | 0.16 |

## Prediction 1 (flush-behind converges to CAT's invariant band): **FALSIFIED**

Flush-behind on CCX1 (4.612x) sits well below CAT's residual on the same
CCX (9.736x) — not in the same band at all, and below even CCX0's
original flush-behind number (5.94x). This is the pre-registration's
explicitly stated falsification condition, met cleanly: **residency
bounding removes something way-partitioning cannot.** The "single
un-partitionable floor" framing is wrong; flush-behind and CAT are not
in the same mechanism-equivalence class. Flush-behind is a genuinely
*stronger* control than CAT on a representative CCX, not merely riding
the same floor CCX0 happened to expose.

This is good news for the paper, not bad: it means residency-bounding
(the paper's own contribution) has a real, measured advantage over
simple capacity partitioning, rather than being indistinguishable from
it once measured cleanly.

## Prediction 2 (WC stays at parity): **CONFIRMED**

0.996x [0.984, 1.011] — parity, matching CCX0's already-adversarially-
confirmed result. WC's exemption is not a CCX0 property.

## Prediction 3 (WB ceiling reflects CCX1's own ~13.4x, not CCX0's ~20.8x): **CONFIRMED**, with a richer finding attached

WB tax on CCX1 (13.435x) matches CCX1's own uncontended ceiling from the
earlier cross-CCX comparison (13.339x) closely, not CCX0's 20.8x, as
predicted.

**The concurrency-knee sub-claim needs a caveat, and turned into the
session's most important side-finding.** The knee's bandwidth ratio
(t2/t3 = 0.894) does not match the paper's cited ~0.98 "2T captures 98%
of 3T's bandwidth" on CCX1. Comparing directly against CCX0's original,
retained A6 data (`e1a6_raw_n12.jsonl`) rather than assuming a mismatch
or a bug:

| thread count | CCX0 tax (original A6) | CCX1 tax (this session) | CCX0 excess |
|---|---:|---:|---:|
| t=1 | 2.917 | 2.828 | +3% |
| t=2 | 6.403 | 4.495 | +42% |
| t=3 | 18.038 | 9.954 | +81% |

**CCX0's excess over CCX1 grows monotonically with contention
intensity**: negligible at 1 thread, +42% at 2 threads, +81% at 3
threads. This is not noise or a script mismatch — it is a clean, graded
relationship between load intensity and CCX0's penalty, and it is
exactly the signature a queueing-theory mechanism predicts (queueing
delay grows super-linearly with utilization). It directly corroborates
the loaded-XI-latency finding from `probe_ccx0_mechanism.py` (CCX0 ~15-18%
worse specifically under load, flat at idle) with a second, independent,
now-graded measurement: the anomaly is not just "on vs off" under load,
it *scales with how much load*.

**This strengthens the queueing/arbitration-asymmetry hypothesis
considerably** — a static topology/distance difference would not
naturally produce a scaling relationship with contention intensity; an
arbitration or priority asymmetry that only bites under contention would.
Still requires AMD documentation/vendor engagement to identify the exact
mechanism, but the phenomenon itself is now characterized with much more
precision than "CCX0 is different."

## What this means for the floor table and the paper

- **CAT's residual (9.7-10.0x) and the concurrency-cap's residual
  (10-18x at t=3, chip-wide picture still forming) are in a similar
  "large, way/concurrency-bound floor" bucket.**
- **Flush-behind (4.6x on a clean CCX) is not in that bucket — it is
  measurably better.** The paper's mechanism story should distinguish
  "controls that leave a large chip-wide-ish floor" (CAT, raw
  concurrency limits) from "controls that reduce residency directly"
  (flush-behind), rather than treating all three as hitting one shared
  invariant.
- **The concurrency knee's specific numeric claim (2T ≈ 98% of 3T's
  bandwidth) does not replicate on CCX1** and needs to be re-quoted
  per-CCX or re-derived from a full, dedicated thread sweep (this
  session only sampled t=1,2,3) before appearing in the paper as a
  cross-platform-general number.
- The CCX0-topology mechanism question is now better characterized
  (queueing/arbitration under load, scaling with intensity) but not
  resolved — gem5 remains on hold per the standing decision, now with a
  sharper description of what it's waiting on.

## Provenance

Raw data: `clean_ccx1_n12.jsonl`. Analysis: `analyze_clean_ccx_session.py`.
Comparison data: `e1a6_raw_n12.jsonl` (original CCX0 A6 sweep, retained,
not re-measured for this comparison — read only).
