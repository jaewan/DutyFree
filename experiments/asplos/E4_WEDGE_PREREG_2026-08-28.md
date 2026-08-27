# E4 pre-registration: does the tenant's confinement cost — the wedge — travel?

Written 2026-08-28, **before any E4 data exists**.

## Why this is the kill-risk test

The paper's entire remaining case is one number: way-partitioning charges a
**fused** tenant **16.9%** at 8 of 20 ways, where it charges a *pure* streamer
0.7%. That is the wedge, and it is measured on **one machine**.

E3 then showed the *victim's* confinement cost collapses across geometries ---
**13.1% on mos181, 0.2% on mos182** --- because the knee moves from ~2/3 to ~100%
occupancy. If the tenant's cost collapses the same way, then on mos182-class parts
CAT is cheap for **both** parties, and the wedge is a property of one machine
rather than of context-scoped partitioning. **The case would largely evaporate.**

This is the cheapest test that can invalidate the paper, so it runs before any of
the expensive gem5 work.

## Matched on occupancy, not on absolute size

E3's pass B mis-scaled the tenant (53% of LLC against mos181's 40%) and I set a
threshold for a configuration the design did not deliver --- the eighth
specification defect of this campaign. So E4 matches the variable E3 showed
actually governs: **the tenant's table as a fraction of its own partition.**

mos182 has 4 MiB per way against mos181's 16 MiB. A **32 MiB** table
(`33554432`, an exact power of two) reproduces mos181's occupancy ladder:

| tenant ways (mos182) | partition | occupancy | mos181's matched point | mos181 measured |
|--:|--:|--:|---|--:|
| 2 | 8 MiB | 400% | 2 of 20 ways | +43.2% |
| 4 | 16 MiB | 200% | 4 of 20 | +41.5% |
| **8** | **32 MiB** | **100%** | **8 of 20** | **+16.9%** |
| 12 | 48 MiB | 67% | 12 of 20 | +2.1% |
| 14 | 56 MiB | 57% | (16 of 20 = 40%) | +0.3% |

## Design

Identical in method to E1 pass A2, which is the run that produced the 16.9%:

- **Paired ratios.** Every masked run is paired with an unmasked run taken
  immediately beside it, pair order alternating by rep parity, and the statistic
  is the **median of per-pair ratios**. This is the design that survived E1a's
  unexplained bimodality.
- Fixed: `--mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g
  --hot-bytes 33554432 --cpu-list 16-31 --morsel 1m --warmups 2 --reps 20
  --threads 16 --hit-rate 0.5`, stream retained, no victim.
- Widths $\{2,4,8,12,14\}$ of 15, via `setup_c` so the complement is enforced.
- **n=12.** `cpus_list` asserted `16-31` and the mask bit-counted on every run;
  aborts on either mismatch or on silent table rounding.
- Preflight exercises every flag before measuring --- the guard added after
  mos182's stale binary voided E3's first pass B.

## Variance basis and resolution

From the matching arm --- E1a2's 8-way paired cell on mos181, same statistic ---
**per-pair ratio CoV 3.46%**. At n=12 the two-sample resolution is **~3.9%**.
**Both thresholds below are 8 points, i.e. ~2x resolution.**

Bimodality guard, as in E1a2: if any width's per-pair ratio CoV exceeds **4%**,
that width's pairs are printed individually rather than summarised.

## Instrument check (registered, action on miss stated)

The unmasked half of the pairs must reproduce mos182's own unconfined tenant
throughput consistently: **per-pair `cyc_none` CoV <= 2%** across all 60 pairs.

- **On miss:** E4 is void; the tenant baseline on this host is not stable enough
  to support a ratio and the comparison cannot be made at this n.

## Registered predictions

- **P1 (the wedge collapses --- the kill outcome).** At 8 of 15 ways (100%
  occupancy) the tenant's cost is **<= 8%**, i.e. at least 8 points below
  mos181's 16.9%.
- **P2 (the wedge travels).** At 8 of 15 ways the cost is **within 8 points** of
  16.9%.
- **P3 (the knee tracks the victim's).** The tenant's cost is <= 3% at 67%
  occupancy **and** >= 8% at 200% occupancy --- i.e. its knee, like the victim's on
  this host, sits nearer 100% than 2/3.

P1 and P2 are exhaustive and mutually exclusive at the 8-point threshold; one
fires.

## Registered consequences

- **P1 fires** --- **the wedge is mos181-specific.** On this geometry CAT is cheap
  for the tenant *and* (from E3) cheap for the victim, so a shipping bitmask
  solves the whole problem at low cost and STREAMING has no measured advantage on
  this class of part. The paper cannot claim a general trade-off; it can claim one
  bounded by a platform condition we would then have to state, and the mechanism
  case becomes very weak. **Stop the gem5 and e2e work until the boundary is
  characterised**, because a mechanism evaluated in simulation against a baseline
  that is nearly free on real hardware is not publishable.
- **P2 fires** --- the wedge travels across a 5.3x cache-size and 4x way-size
  change. That is the strongest single result the project would have, because it
  means the tenant-side cost of context-scoped partitioning is a property of the
  *mechanism* and not of one machine. Proceed with gem5 way-partitioning and the
  e2e.
- **P3 fires with P1** --- coherent picture: both parties' knees move together with
  geometry, and the whole trade-off is a function of one platform coefficient.
- **P3 fires with P2** --- incoherent, and the most interesting outcome: the
  victim's knee moves between hosts but the tenant's does not. That would mean the
  two costs have different mechanisms, and the frontier's single-curve account is
  wrong. Investigate before writing anything.

## What this cannot show

mos182 only, one table size, one hit rate, one stream size, no victim. It prices
the tenant's own confinement and says nothing about protection. Both hosts are
Intel and way-partitioned; AMD is untested and its harm is rate-class.
