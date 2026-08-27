# E3 pre-registration: does the 2/3 occupancy knee travel to a different cache geometry?

Written 2026-08-28, **before any E3 data exists**. Agenda item E3.

## Why this rather than a second victim

The agenda offered two options: a second victim type on mos181, or the same victim
on a second machine. **The second machine tests the more load-bearing claim.**

E1's strongest output is not a measured point, it is a *rule*: each party is free
while its own partition is $\lesssim 2/3$ full, from which follows

$$\text{a free static split exists} \iff \text{tenant WS} + \text{neighbour WS} \lesssim \tfrac{2}{3}\times\text{LLC}$$

That rule was derived twice on mos181 --- once from a 16-thread hash-join tenant,
once from a single-threaded pointer chase --- but **both derivations share one cache
geometry**: 320 MiB in 20 ways, 16 MiB per way. A coefficient measured on one
geometry and stated as a rule is exactly the kind of claim this campaign has
learned to distrust.

mos182 is a genuinely different geometry:

| | mos181 (EMR 8592+) | mos182 (SPR 8462Y+) |
|---|---|---|
| LLC per socket | **320 MiB** | **60 MiB** |
| ways | 20 (`fffff`) | **15** (`7fff`) |
| **per way** | 16 MiB | **4 MiB** |
| L3 domain 0 cpus | 0-63,128-191 | 0-31,64-95 |
| private L2 | 2 MiB | 2 MiB |

A 5.3x smaller cache and a 4x smaller way. If the knee is still at ~2/3
occupancy there, the rule is a property of way-partitioned caches. If it moves,
it is a property of mos181 and the paper must say so.

## Apparatus

`pointer_chase` was not on mos182. Built there from source md5-identical to
mos181's (`f69462f92ef0d8590bb38e9f1f224a0f`), same compiler flags, linked against
the same `lib/` sources. Smoke test: 16 MiB unconfined reads 79.43 cyc/load
(mos181 reads 73.4 at the same size), so the two are in the same regime without
being identical --- which is expected and is the point.

`cxl_join_bench` was already present on mos182. CXL is node 2, 256 GiB.

## Design

**Pass A --- the occupancy knee, victim alone.** This is the decisive pass.

- Victim confined to $k_v$ ways via `resctrl_clos.sh setup_c` with the complement
  on the tenant's cores; **no tenant runs**.
- $k_v \in \{5, 10, 15\}$ ways $= 20, 40, 60$ MiB.
- WSS $\in \{8, 16, 24, 32, 48\}$ MiB, giving partition occupancies from **13% to
  240%** --- straddling the predicted knee at every way count.
- Plus one unconfined baseline per WSS.
- 15 confined cells + 5 baselines = **20 cells, n=6, 120 runs**.

**Pass B --- does the trade-off itself travel.**

- Tenant: `cxl_join_bench --mode morsel --policy wb --fact-node 2 --hot-node 0
  --fact-bytes 1g --hot-bytes 33554432` (32 MiB table, an exact power of two;
  53% of this LLC, against 128 MiB = 40% on mos181), 16 threads on cpus 16-31
  (L3 domain 0), hit rate 0.5.
- Victim: 32 MiB WSS on cpu 8 (same domain).
- Arms: victim alone; victim + tenant unmasked retained; unmasked non-allocating;
  and tenant confined to 5 of 15 ways with the victim holding 10.
- **5 cells, n=6, 30 runs.**

Both passes: per-rep rotation, schemata captured per record, tenant liveness
asserted in co-run records, aborts on silent table rounding, A6.19, resctrl torn
down on every exit path. **Domain 1 must keep the full mask** --- mos182 has two L3
domains and restricting the idle one would be a silent no-op that could
manufacture a null (the `resctrl_clos.sh` header records this rule).

## Variance basis and the resolution it gives

There is **no matching mos182 victim cell** to calibrate against --- the honest
consequence of running on a new host --- so the basis is the smoke test just taken:
three trials at 79.430 / 79.416 / 79.430, i.e. **CoV 0.01%**, consistent with
mos181's victim CoV of 0.03--0.66%.

Taking mos181's *worst* victim CoV (0.66%) as the conservative estimate, $n{=}6$
gives a two-sample resolution of **~1.1%**. **Every threshold below is at least
3 points.** If pass A's observed CoV exceeds 0.66% at any cell, that cell's
thresholds are reported as unresolved rather than evaluated --- the rule E1's
sixth defect earned.

## Instrument check (registered, action on miss stated)

The unconfined victim at 16 MiB must reproduce the smoke test within **+/-3%**,
i.e. **[77.05, 81.81]**.

- **On miss:** E3 is void for cross-host comparison; the within-E3 sweep may still
  be reported.

## Registered predictions

- **P1 (the knee travels).** Across all 15 confined cells, the victim's
  confinement cost is $\le 3\%$ wherever its partition is $\le 60\%$ full and
  $\ge 8\%$ wherever it is $\ge 85\%$ full. This is the same shape E1 pass B found
  on mos181, tested on a 5.3x smaller cache with a 4x smaller way.
- **P2 (occupancy, not absolute size, is the variable).** Cells at similar
  occupancy but different way counts agree within **5 points** of cost. On mos181
  this is what let 15 cells collapse onto one curve.
- **P3 (the trade-off travels).** In pass B, non-allocating the tenant's stream
  removes $\ge 50\%$ of the victim's harm, and confining the tenant to 5 of 15
  ways returns the victim to within **5%** of its own confined baseline.
- **P4 (no free split, again).** At pass B's sizes --- tenant 32 MiB, victim
  32 MiB, LLC 60 MiB --- the 2/3 rule predicts a combined demand of
  $32/0.66 + 32/0.66 = 97$ MiB against 60 MiB available, so **no split should be
  cheap for both**. Pass A supplies the per-party costs to check this without a
  separate sweep.

## Registered consequences

- **P1 and P2 hold** --- the 2/3 rule is a property of way-partitioned caches, not
  of mos181, and the free-split condition can be stated as a rule in the paper
  with two geometries behind it.
- **P1 fails with the knee at a different occupancy** --- the rule is
  geometry-dependent. The paper must state the coefficient as measured per
  platform and **may not** present the inequality as general. This is the outcome
  that costs the most and it is why E3 runs before the writing.
- **P2 fails** --- occupancy is not the right variable even on mos181's own terms,
  and E1's collapse onto one curve was a coincidence of the sizes chosen. Both
  hosts' curves must then be re-expressed against whatever variable does work.
- **P3 fails** --- the trade-off is mos181-specific and the paper's central table
  needs a platform qualifier.
- **P4 fails** (some split is cheap for both) --- the free-split condition is
  wrong as stated, on the platform where the cache is small enough to test it
  cheaply.

## What this cannot show

Two Intel server geometries, both way-partitioned, both with a 2 MiB private L2 ---
so E3 tests transfer across cache size and way size, **not** across
microarchitecture family, replacement policy, or a non-inclusive/inclusive
difference. AMD remains untested and its harm is rate-class rather than
capacity-class, so nothing here transfers there. One victim type on both hosts:
E3 buys geometry generality at the cost of leaving victim-type generality still
open, which was the other option on the agenda and remains unaddressed.
