# Delta audit outcome

Dated 2026-08-10. Pre-registration:
`DELTA_AUDIT_PREREGISTRATION.md`. Runs executed on `broker`/`moscxl`,
AMD EPYC 9754, CCX1 (`victim=cpu8`, aggressors `cpus9-15`), resctrl
domain 1, via sudo. No files under `~/STREAMING_Paper/` were touched.

## T0: arm identity closed

The subtraction target is the clean-CCX1 ladder:

| figure | arm and operating point |
|---|---|
| 13.435x | WB CXL, clean CCX1, `PHASE2_CLEAN_CCX_OUTCOMES.md` |
| 9.736x | WB+CAT 8/8, clean CCX1, MSR-verified |
| 4.612x | `flush_d256kb`, clean CCX1 |
| 0.996x | WC CXL, clean CCX1 |
| 5.939x | older CCX0 Phase 2.4 `d_256kb`, not used for this subtraction |

Therefore `4.6x` is the clean-CCX1 `flush_d256kb` operating point
(4.612x [4.560, 4.700]), while `5.94x` is the older CCX0 Phase 2.4
sweep point. They are both real, but they are different CCX/session
operating points.

Clean-CCX1 raw flush-to-WC span before delta:

`4.612 - 0.996 = 3.616x`.

## Data

Raw files:

| file | contents |
|---|---|
| `delta_audit_raw_n12.jsonl` | n=12, rep-interleaved: quiescent, WB, flush1, flush1_matched, flush2_matched, WB+disjoint-flush |
| `delta_audit_wb_matched_n12.jsonl` | n=12, paired follow-up: quiescent, WB throttled to match WB+disjoint-flush stream rate |
| `delta_audit_event_registry.json` | host, CCX/domain, raw perf event registry |

The runner records both `mbm_total_bytes` and `mbm_local_bytes`.
No CXL PMU device was exposed by `perf list` on `broker`; CXL wire-byte
truth was therefore not available in this run.

## Tax results

Paired bootstrap except `wb_matched` vs `wb_plus_flush`, which uses the
separate paired follow-up for `wb_matched` and an independent bootstrap
for the difference.

| arm | tax | 95% CI | self BW | MBM total | MBM local | flush rate |
|---|---:|---:|---:|---:|---:|---:|
| WB | 13.474x | [13.349, 13.875] | 24.71 | 24.19 | 0.069 | - |
| flush1, D=256 KiB | 4.597x | [4.544, 4.732] | 17.25 | 33.60 | 0.018 | 268.49 Mops/s |
| flush1 matched | 2.434x | [2.264, 2.564] | 11.51 | 22.42 | 0.019 | 179.11 Mops/s |
| flush2 matched | 1.336x | [1.325, 1.379] | 11.50 | 33.60 | 0.020 | 357.99 Mops/s |
| WB+disjoint flush | 12.550x | [12.481, 12.840] | 22.39 | 52.05 | 30.21 | 241.30 Mops/s |
| WB matched | 8.179x | [7.838, 8.429] | 22.21 | 21.76 | 0.077 | - |

## T1: MBM doubling mechanism call

`flush1` reproduces the MBM/self gap: self BW 17.25 GB/s, MBM total
33.60 GB/s, ratio 1.95x. WB does not: self 24.71 GB/s, MBM total
24.19 GB/s, ratio 0.98x.

The usable AMD XI sampled-request counter does not show a matching 2x
request increase:

| arm | `l3_xi_sampled_latency_requests.ext_near` median |
|---|---:|
| WB | 70,333.5 |
| flush1 | 70,840.5 |

Ratio: 1.007x. The raw L3 lookup-state encodings (`rff04`, `rfe04`,
`r0104`) returned zero or near-zero in this post-victim sampling window
and are treated as unavailable for this run.

Mechanism call: the observed MBM doubling is most consistent with a
resctrl MBM accounting/selection artifact or with a byte-accounting path
not reflected in the sampled XI request counter. This run does **not**
confirm the maximal-severity "2x home transactions with 1x data" case.
Because no CXL PMU wire-byte counter was exposed, T1 is a strong
anti-2x-home signal but not a complete wire-truth proof.

## T2: double-flush bound

The rate-matched T2 arms held the fetch rate fixed at about 11.5 GB/s:

| contrast | delta |
|---|---:|
| `flush2_matched - flush1_matched` | -1.098x [-1.203, -0.926] |

This violates the pre-registered estimator assumption. Doubling the
flush operation rate increased MBM total (22.42 -> 33.60 GB/s) but
reduced victim tax (2.434x -> 1.336x). T2 is therefore not a valid
upper-bound estimator in this implementation and is not used as a point
estimate of delta.

## T3: additive disjoint-buffer estimator

The first WB comparator was full-rate WB, but WB+disjoint-flush streamed
more slowly. A follow-up matched WB arm was therefore run at the same
streaming rate:

| contrast | delta |
|---|---:|
| `WB+disjoint-flush - WB matched` | 4.371x [4.137, 4.843] |

This is the primary conservative estimator by the preregistration, but
its caveat is material: the disjoint-flush control introduced about
30.21 GB/s of local MBM traffic while keeping the disjoint lines valid
before flushing. That means the control is not a clean "flush messages
only" superposition. It is still the largest observed delta band and
therefore governs the conservative prose under the pre-registered
triangulation rule.

## Verdict

The three estimates disagree by band:

| source | delta band |
|---|---|
| T1 counter contrast | small / not 2x-home; no positive delta sized |
| T2 double-flush | estimator failed; negative delta, not usable |
| T3 matched additive control | delta > 1.8 |

Pre-registered rule: if the estimates disagree by band, the conservative
reading, the largest delta, governs until Build B or a cleaner hardware
discriminator settles it.

Conservative verdict: **delta > 1.8**, so H3 demotes to
"structurally unique but quantitatively secondary" for the clean-CCX1
flush-behind ladder.

Numerically, T3's conservative delta estimate (4.371x) exceeds the
entire clean-CCX1 flush-to-WC span (3.616x). This should not be read as
"negative H3"; it means this additive control is too conservative and
fully consumes the span for paper-prose purposes. The defensible
paper-facing H3 share from this rung is therefore not a settled 3.6x;
under the conservative audit rule it is bounded down to zero until a
cleaner discriminator supersedes T3.

## Embargo status

The old embargo wording, "upper bound, flush-overhead unresolved," is
superseded for this dataset, but the 3.6x number still must not be cited
as H3's quantitative contribution.

Replacement wording:

> Clean-CCX1 flush-behind leaves a 3.616x flush-to-WC span before
> subtracting emulation overhead. A conservative delta audit finds that
> the additive flush-control bound can consume the entire span, so the
> flush-behind rung does not currently support a settled positive
> quantitative H3 share; H3 remains structurally unique but
> quantitatively secondary pending Build B or a cleaner counter/control
> discriminator.
