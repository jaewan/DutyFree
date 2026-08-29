# L3-occupancy outcome: the AMD harm is **L3 eviction**. Back-invalidation is withdrawn.

Pre-registration `AMD_L3OCC_PREREG_2026-08-30.md` (`065dd38`). 60 runs.
`llc_occupancy` sampled every 250 ms during each victim run, warmup excluded.

## Result

| victim WSS | arm | cyc/access | L2 hit% | **victim L3 occupancy** | agg GB/s |
|---|---|--:|--:|--:|--:|
| 512 KB | quiescent | 19.47 | 94.87 | **180 KB** | --- |
| 512 KB | same-CCX | 28.81 | **98.20** | **8 KB (4.4%)** | 24.78 |
| 512 KB | other-CCX | 19.12 | 97.01 | 16 KB | 24.81 |
| 4096 KB | quiescent | 54.87 | 14.12 | **3568 KB** | --- |
| 4096 KB | same-CCX | 1530.12 | **0.00** | **196 KB (5.5%)** | 22.44 |
| 4096 KB | other-CCX | 618.72 | 0.00 | 128 KB | 18.37 |

**Liveness 1 passes:** occupancy spans 8--3568 KB across cells, so the counter is
live rather than stuck.

## P1 --- answered, and it withdraws my own hypothesis

Registered: occupancy under `same` falling to **<= 50%** of quiescent means L3
eviction and the back-invalidation reading is withdrawn; **>= 80%** with hits
still collapsed would support back-invalidation.

**Measured: 5.5%** at 4 MB and **4.4%** at 512 KB. Not close to the boundary.

> **The victim is evicted from L3. It is not back-invalidated from L2 while
> remaining L3-resident. The reading in `AMD_NARROWMASK_OUTCOME` addendum 1 is
> withdrawn in full.**

The 4 MB L2-hit collapse (14.12% -> 0.00%) that prompted the back-invalidation
idea is a *consequence* of losing L3 residency, not evidence of probe-filter
activity: with its L3 copy gone, every L2 miss goes to memory and the chase's
effective reuse window collapses.

At 512 KB the picture is equally clear and simpler than anything proposed so far:
the victim keeps **all** its L2 hits (94.87% -> 98.20%, *higher* under load), its
small L3 spill is evicted (180 KB -> 8 KB), and it slows 1.48x. No
back-invalidation, no capacity loss in L2 --- just the spill losing its L3 home.

## What this means for H3

H3 removes a **snoop-filter enrolment** charge. This experiment finds no evidence
of one on Bergamo: the mechanism is ordinary L3 eviction, which H2 addresses and
H3 does not. **The case for reinstating H3 on the strength of AMD evidence is
withdrawn.** H3's standing returns to what it was before yesterday: a bounded
capability claim with no demonstrated charge on reachable hardware.

I argued the opposite yesterday, from L2 counters, and recorded then that the
attribution was "suggestive, not established". It is now established, and against
me.

## An unresolved discrepancy, recorded rather than smoothed

The **4 MB other-CCX** cell disagrees with the factorial:

| | `BERGAMO_BACKINVAL` (n=20) | this run (n=10) |
|---|--:|--:|
| 4 MB other-CCX cyc/access | 71.82 / 62.16 | **618.72** |
| aggressor bandwidth there | 24.81 | **18.37** |

An 8.6x difference in one cell, with the aggressor moving 26% fewer bytes. The
`same`-CCX and `quiescent` cells reproduce closely (1530 vs 1526; 54.87 vs
54.96), so this is not a global shift. THP differed (`madvise` here, `never`/
`always` there), and node-2 memory had been heavily exercised by the preceding
experiments.

**Consequence: the P2 "harm is L3-domain-local" conclusion rests on the
factorial, and this run does not corroborate it in the 4 MB cell.** P2 should be
treated as **provisional** until the other-CCX arm is re-measured under a
controlled THP setting on a quiesced machine. The 512 KB other-CCX cell *does*
agree (19.12 here vs 19.19/19.37), so the disagreement is confined to 4 MB.

I am not choosing the reading I prefer. The L3-eviction result (P1) is internal
to this run and is unaffected; the locality result (P2) is not, and is flagged.
