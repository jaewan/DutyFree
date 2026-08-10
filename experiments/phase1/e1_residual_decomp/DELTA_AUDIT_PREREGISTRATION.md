# Pre-registration: delta audit for AMD flush-behind overhead

Dated 2026-08-10. Written before any delta-audit hardware run. This
audit is scoped to AMD EPYC 9754, the frozen Phase 2 AMD configuration,
and the existing flush-behind arm. The current shell used to write this
file is `mos181`, an Intel Xeon Platinum 8592+ host, so no AMD hardware
measurements are run from this session state.

## Objective

Decide whether the MBM/self-report gap in the AMD flush-behind arm is
real coherence traffic or a counting artifact, then bound the
flush-operation overhead delta inside the flush-behind rung.

The paper-facing rule remains in force until this audit has an outcome:
do not cite the clean-CCX1 `flush_d256kb` 4.612x rung's recovery as a
settled H3 contribution without the qualifier "upper bound,
flush-overhead unresolved."

## T0: arm identity

The subtraction target is the clean-CCX1 co-measured ladder, not the
older CCX0 Phase 2.4 D-sweep.

Number registry for the operating point used by this audit:

| figure | arm and operating point | source |
|---|---|---|
| 13.435x | WB CXL, clean CCX1, victim cpu8, aggressors cpus9-15, n=12, same session | `PHASE2_CLEAN_CCX_OUTCOMES.md` |
| 9.736x | WB+CAT 8/8, clean CCX1, MSR-verified disjoint masks, n=12, same session | `PHASE2_CLEAN_CCX_OUTCOMES.md` |
| 4.612x | `flush_d256kb`, clean CCX1, same session, self BW 17.03 GB/s, MBM 33.14 GB/s | `PHASE2_CLEAN_CCX_OUTCOMES.md` |
| 0.996x | WC CXL, clean CCX1, same session | `PHASE2_CLEAN_CCX_OUTCOMES.md` |
| 5.939x | `d_256kb`, original Phase 2.4 CCX0 sweep, victim cpu0, aggressors cpus1-7 | `phase2_AMD_flushbehind_OUTCOME.md` |

Therefore the ladder's 4.6x value is reconciled as the later clean-CCX1
`flush_d256kb` operating point: 4.612x [4.560, 4.700]. The 5.939x value is
real but belongs to the older CCX0 Phase 2.4 sweep and must not be mixed
into the clean-CCX1 ladder subtraction.

For the clean-CCX1 ladder, the raw flush-to-WC span is:

`4.612 - 0.996 = 3.616x`, an upper bound until delta is subtracted.

## T1: counter contrast

Run `flush_d256kb` and matched plain WB on AMD, same clean-CCX operating
point, rep-interleaved with n>=12. Before running, discover the live event
surface on that AMD host with:

`perf list | grep -iE 'amd_df|umc|l3|ccm|cxl'`

Record the exact event names or raw encodings in the outcome. Do not
reuse event names from memory without checking the AMD host. Prior AMD
scripts used raw Zen4 L3/XI encodings (`rff04`, `rfe04`, `r0104`,
`r10ac`, `r10ad`, `r01ac`, `r01ad`) only after alias discovery failed;
that precedent is allowed only if the same failure is observed and logged.

Primary contrast:

| quantity | interpretation |
|---|---|
| home/coherent-station requests | transaction pressure presented to the coherence point |
| data moved | UMC/IMC local plus CXL-side read-data counters for the streamed buffer |
| aggressor self-report | bytes the program intentionally streamed |
| `mbm_total_bytes` and `mbm_local_bytes` | resctrl split, if available on the AMD host |

Prediction and decision rule:

| outcome | call |
|---|---|
| home requests near 2x per self byte, data moved near 1x | MBM doubling reflects real coherence transactions without matching data movement; delta may be large |
| home requests near 1.05x per self byte | MBM doubling is mainly a resctrl event-selection artifact; delta likely small |
| intermediate result | T1 is not decisive; T3/T2 govern the delta band |

## T2: double-flush bound

Run the flush-behind arm at the clean-CCX1 `D=256 KiB` operating point
with one flush per line and with two flushes per line. Keep fetch rate,
victim placement, warmup, resctrl domain, and rep interleaving matched.

Estimator:

`delta_T2 = tax(double_flush) - tax(single_flush)`

This is pre-registered as a one-sided conservative upper bound, not a
point estimate. The second flush lands on an already invalidated line, so
its marginal cost can exceed the first flush's marginal cost.

Decision use:

| result | interpretation |
|---|---|
| `delta_T2 <= 0.9` with CI not crossing 0.9 | H3-decisive verdict holds a fortiori |
| `delta_T2 > 0.9` or CI crosses a band boundary | T2 is only a loose upper bound; do not report it as delta |

## T3: additive disjoint-buffer estimator

Run clean-CCX1 plain WB and clean-CCX1 WB plus an added `clflushopt` loop
against a disjoint resident buffer that the victim never touches. Match
the flush operation rate to the `flush_d256kb` arm's measured line rate.

Estimator:

`delta_T3 = tax(WB + disjoint matched-rate flush loop) - tax(WB)`

This is the primary delta estimator. Its caveat is pre-registered:
additivity may fail, and the disjoint buffer's valid resident-line state
does not exactly match the streaming arm's transient line state.

## Verdict bands

For clean-CCX1:

`H3 share = 3.616 - delta`

Use paired bootstrap CIs. If the 95% CI for delta straddles a band
boundary, declare INCONCLUSIVE and do not round to the nearest band.

| delta | clean-CCX1 H3 share | verdict |
|---|---|---|
| `delta <= 0.9` | `>= 2.716x`, at least 21.9% of the 12.4x span | H3 decisive |
| `0.9 < delta <= 1.8` | 1.816x to 2.716x | H2 and H3 co-equal |
| `delta > 1.8` | `< 1.816x` | H3 demotes to structurally unique but quantitatively secondary |

If T1, T2, and T3 disagree by band, the conservative reading is the
largest delta band until Build B or a follow-up hardware discriminator
settles the mismatch.

## Deliverables

1. Raw JSONL, n>=12, rep-interleaved, with one record per arm and per rep.
2. Exact counter-event registry from the AMD host, including any raw
   encodings and any unavailable events.
3. `DELTA_AUDIT_OUTCOME.md`, containing T0 reconciliation, T1 mechanism
   call, T2 bound, T3 primary estimate, CI-aware band verdict, and an
   explicit statement on whether the embargo lifts.
