# Bergamo back-invalidation outcome: the harm is L3-domain-local, not fabric --- and it is not back-invalidation at 512 KB

Pre-registration `BERGAMO_BACKINVAL_PREREG_2026-08-30.md` (`0ff6ca4`). 240/240
runs usable.

## Results

Medians, n=20 per cell. Aggressor bandwidth is ~24.2--24.8 GB/s in **every**
co-run cell, so placement is not confounded by rate.

| THP | victim WSS | place | cyc/access | IQR | L2 hit% | agg GB/s |
|---|--:|---|--:|--:|--:|--:|
| never | 512 KB | quiescent | 19.28 | 0.44 | 95.44 | --- |
| never | 512 KB | **same-CCX** | **53.18** | **32.31** | 93.51 | 24.76 |
| never | 512 KB | other-CCX | 19.37 | 1.82 | 95.87 | 24.80 |
| never | 4096 KB | quiescent | 54.96 | 0.96 | 14.41 | --- |
| never | 4096 KB | **same-CCX** | **1526.01** | 6.93 | **0.00** | 24.78 |
| never | 4096 KB | other-CCX | 71.82 | 0.17 | 0.00 | 24.81 |
| always | 512 KB | quiescent | 18.69 | 1.35 | 97.08 | --- |
| always | 512 KB | **same-CCX** | **30.18** | **22.60** | 97.51 | 24.24 |
| always | 512 KB | other-CCX | 19.19 | 2.81 | 96.97 | 24.24 |
| always | 4096 KB | quiescent | 47.63 | 0.57 | 14.12 | --- |
| always | 4096 KB | **same-CCX** | **1468.19** | 6.81 | **0.00** | 24.24 |
| always | 4096 KB | other-CCX | 62.16 | 0.08 | 0.00 | 24.23 |

## P2 --- the harm is L3-domain-local. Confirmed, and it is the strongest result here.

| THP | WSS | same | other | **ratio** |
|---|--:|--:|--:|--:|
| never | 512 | 2.76x | 1.00x | **2.75** |
| never | 4096 | 27.77x | 1.31x | **21.25** |
| always | 512 | 1.61x | 1.03x | **1.57** |
| always | 4096 | 30.82x | 1.30x | **23.62** |

Registered threshold was >= 1.3; every cell clears it, three of four by a wide
margin. **An aggressor on a different CCX, pulling the same ~24.8 GB/s from the
same CXL device, barely touches the victim (1.00--1.31x).** The same aggressor
moved onto the victim's own CCX costs it 1.6--31x.

**This rules out global fabric or CXL-link bandwidth as the mechanism.** The
bytes are identical; only the L3 domain changes. Whatever the AMD residual is, it
is produced inside the shared L3 domain.

That is a real strengthening of `E3`'s rate-class finding: rate-class did not
mean *fabric*-class.

## P1 --- mis-specified by me, and the corrected form is informative

I registered "median L2 hit rate < 99.0%" as the back-invalidation signal,
calibrating 99.8% from an earlier run taken under `THP=madvise`. Under the THP
settings actually swept, the **quiescent** hit rate is already 95.4--97.1%, so the
registered test passes trivially and means nothing. **Recorded as mis-specified;
the eighth threshold in this campaign calibrated in one configuration and applied
in another.**

The correct paired comparison, quiescent vs same-CCX within each condition:

| THP | WSS | quiescent hit% | same-CCX hit% | change |
|---|--:|--:|--:|---|
| never | 512 | 95.44 | 93.51 | -1.9 pp |
| always | 512 | 97.08 | **97.51** | **+0.4 pp** |
| never | 4096 | 14.41 | **0.00** | **-14.4 pp** |
| always | 4096 | 14.12 | **0.00** | **-14.1 pp** |

**At 512 KB the victim loses no L2 hits --- under `THP=always` it gains some --- yet
it is still slowed 1.6--2.8x.** So for an L2-resident victim the harm is **not**
back-invalidation: the hits survive and the few remaining misses become
expensive. **The back-invalidation reading of `AMD_NARROWMASK_OUTCOME` addendum 1
does not hold at 512 KB and is withdrawn for that case.**

At 4096 KB the hits do vanish completely. Whether that is back-invalidation or a
consequence of the victim's L3 residency being destroyed cannot be settled with
L2 counters, which is why `AMD_L3OCC_PREREG_2026-08-30.md` exists.

## P3 --- THP is not the mode selector. Reported as unidentified, as registered.

IQR of slowdown, 512 KB same-CCX: **32.31** (`never`) vs **22.60** (`always`) ---
a ratio of 0.70 against a registered <= 0.50. **P3 fails.** Per the
pre-registration the mode-selecting variable is reported as **unidentified**
rather than replaced with a fresh guess.

Two things are worth keeping from it. THP does halve the *median* harm
(2.76x -> 1.61x), so physical page backing matters to the magnitude even though
it does not explain the spread. And the spread is **specific to the same-CCX
co-run**: IQR 22.6--32.3 there against 0.44--1.35 quiescent and 1.82--2.81
other-CCX. The bimodality is caused by the co-runner, not intrinsic to the
victim, which is the opposite of what the first quiescent samples suggested.

## Consequence for `tab:h3sf`

The caption's "private-L2-resident victims read 1.000x on Bergamo" is not
reproduced. At 512 KB the median is **1.61x** (`THP=always`) to **2.76x**
(`THP=never`), with an IQR spanning roughly 1.0x to well above 2x. The published
value sits at the bottom of a wide, co-runner-induced distribution. **The claim
should carry the distribution, not the point** --- and since it is what makes H3 a
capability claim rather than a measured benefit, that matters.
