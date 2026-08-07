# Phase 2.4 — AMD flush-behind: OUTCOME vs pre-registration

Dated 2026-08-07. Pre-registration in
`PHASE2_AMD_FLUSHBEHIND_PREREGISTRATION.md`, written and committed before
any AMD flush-behind measurement of any kind. n=12, rep-interleaved, same
victim/aggressor placement as A0-A6. One mid-run interruption: `broker`
rebooted (apparent external cause, unrelated to this work -- clean boot
sequence in dmesg, no panic/crash) during the first n=12 attempt at ~92%
completion; machine state (governor, resctrl mount, boost) was fully
re-frozen and the run redone from scratch. This file reports the completed
re-run.

## Results

| D | tax | 95% CI | agg bw (self/mbm, GB/s) | victim occupancy (MB) |
|---|---:|---:|---:|---:|
| 32 KiB | 6.182x | [6.061,6.230] | 16.38 / 31.90 | 2.87 |
| 256 KiB | 5.939x | [5.823,5.985] | 17.04 / 33.05 | 2.93 |
| 2 MiB | 8.126x | [7.397,9.158] | 12.64 / 24.12 | 2.50 |
| 16 MiB | 17.489x | [17.148,17.612] | 22.30 / 38.03 | 0.14 |
| 64 MiB | 20.901x | [20.497,21.054] | 24.69 / 24.09 | 0.16 |
| off | 20.843x | [20.434,20.990] | 24.66 / 24.07 | 0.15 |

(D=off's 20.84x is a fresh independent measurement of the same condition as
A1's original 19.89x gate -- 4.8% apart, consistent with this campaign's
established run-to-run variance, not a new discrepancy.)

## Outcome: OCCUPANCY MODEL CONFIRMED, CAPACITY MODEL REFUTED

**Best-case recovery (D=256 KiB): tax = 5.94x.** The pre-registered
occupancy-model prediction was "residual >=5x at small D, should look
qualitatively like A2 (CAT recovers 69%, residual 7.2x)." That is exactly
what happened: flush-behind recovers 20.84x down to 5.94x -- a **71.5%
reduction**, essentially the same magnitude as CAT's 69% reduction from the
original AMD data (19.85x -> 6.92x), landing at a comparable residual
(5.94-6.18x here vs. 6.92-7.23x for CAT in this campaign's own A2). The
capacity-model prediction (tax -> ~0.9-1.0x, matching Intel's E2b) is
**cleanly refuted** -- nothing in this sweep gets remotely close to
baseline at any D.

**This is the cross-vendor discriminator result the mission needed.**
Flush-behind and CAT produce near-identical partial recovery on AMD,
consistent with both leaving the same underlying resource (the coherent
transaction pool) untouched: CAT frees LLC *ways* but not lookup/enrollment
entries; flush-behind frees LLC *residency* but not the same entries either
-- both address capacity-adjacent symptoms, neither touches the actual
binding resource. Intel's near-total recovery under the identical
flush-behind mechanism (E2b, tax->~0.90-0.905x) shows the SAME mechanism
means something structurally different on the two platforms: on Intel, LLC
capacity really is close to the whole story (bounding residency ~solves
it); on AMD, it demonstrably is not.

**Consequence for H2's cross-vendor story**: H2's non-allocation contract
does NOT port to AMD by analogy from the Intel result. A gem5 model that
implements H2 as "bound residency, matching Intel" and expects similar
recovery on an AMD-analog config would be **wrong** -- this is now
measurement-backed, not a guess. An AMD-analog gem5 model needs a
transaction-pool/queue mechanism that H2 does not touch; only a
type-licensed lookup/enrollment skip (H3-class) would be expected to
recover the AMD residual, consistent with A4's independent finding
(lookups-only tax is real) earlier in this campaign.

## Secondary finding: MBM shows ~2x self-report specifically when flushing is active

At D=32/256KiB/2MiB, resctrl MBM reads roughly double the aggressor's own
self-reported bandwidth (e.g. D=256KiB: self=17.04, mbm=33.05 GB/s); at
D=64MiB/off, the two agree closely (24.69 vs 24.09, 24.66 vs 24.07).
Plausible mechanism, not confirmed: `clflushopt`-driven eviction of a
CXL-sourced line may generate a coherence message (invalidate/notify-home)
that MBM counts as bytes moved, roughly comparable in size to the original
fetch -- this would appear only when eviction is frequent (small D) and
fade out as D grows (less frequent flushing). Flagged as an observation,
not asserted as fact; would need direct verification (e.g., a controlled
clean-vs-dirty-line eviction comparison) to confirm the causal mechanism.
