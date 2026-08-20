# CAT capacity-sensitivity gate: run decisions

Written 2026-08-21, **while the gate was running and before any result was
read**, so that the four departures below cannot be mistaken for post-hoc
rationalisation. The pre-registration
(`GAPBS_CAT_SENSITIVITY_PREREGISTRATION.md`, 2026-08-11) is unchanged; its
objective, method and decision rule are implemented verbatim in
`scripts/run_cat_sensitivity_gate.py` and
`scripts/summarize_cat_sensitivity_gate.py`, both new — the gate had no runner.

## 1. AMD reports `min_cbm_bits=0`, and the driver accepts a zero mask

`moscxl` (EPYC 9754) reports `min_cbm_bits=0`, against `1` on `mos181`. Taking
the reported floor literally yields the mask `0`, and the AMD resctrl driver
**accepts it**: a plumbing check measured `effective = 0 MiB` and PageRank at
scale 18 slowing 0.0647 s -> 0.1388 s.

That is not the quantity this gate is about. A zero mask grants no L3
allocation at all, which is a *different configuration*, not the minimum
capacity point; the pre-registration says "the minimum legal **contiguous** way
mask", and no-allocation is not a way count. The runner therefore floors the
mask at one way on every host, recording `min_cbm_bits_reported` alongside
`min_cbm_bits_used` in every record. Probed points are consequently 320 -> 16
MiB on `mos181` (20 ways x 16 MiB) and 16 -> 1 MiB on `moscxl` (16 ways x 1
MiB).

Had this gone unnoticed it would have inflated the AMD ratio with a
configuration the paper could not describe.

## 2. `moscxl`'s L3 domain is 1, not 0

The superseded `run_llc_occupancy_gate.py` hardcoded `l3_domain = 0` for both
hosts. On EPYC 9754 the L3 is per-CCX: `cpu8` reports `id = 1`, sharing with
`8-15,264-271`, and the schemata line carries 32 domains. The gate would have
constrained a CCX the victim does not run on, measuring nothing. The
pre-registration's own requirement -- "the CPU's actual L3 domain is read from
sysfs" -- is what catches this, and the new runner reads `id`, `size` and
`ways_of_associativity` per host rather than carrying a table.

## 3. `moscxl` is measured unfrozen, and this is disclosed rather than fixed

`mos181` is frozen (`performance`, `no_turbo=1`). `moscxl` is not
(`schedutil`, `boost=1`) and carries a live desktop login by another user.
The gate runs it as-is, for three reasons: these are the same conditions under
which the 2026-08-11 sizing gate measured CoV 1.387% on this host, comfortably
inside the rule's 5% bound; the rule is a *ratio* between two arms measured
back to back, which a shared frequency policy perturbs in the same direction;
and freezing would degrade another user's live session. `freeze_state`
-- governor, turbo/boost, loadavg -- is recorded in every record. If either
`moscxl` arm exceeds CoV 5%, the run is repeated frozen, by request, rather
than reported.

AMD's per-CCX L3 helps here: the desktop occupies other CCXs, hence other L3
domains entirely, so it cannot contend for the victim's ways.

## 4. Scales 21--23 first; 24--25 only if none passes

The rule selects the **smallest** passing scale, so a pass at g21, g22 or g23
settles the gate and makes g24/g25 unselectable. With `OMP_NUM_THREADS=1` the
Kronecker build, not the trial, dominates wall clock at high scales (the
2026-08-11 gate abandoned its g25 PageRank endpoint for this reason). Scales
are therefore run ascending, 21--23 first, extending to 24--25 only if all
three fail. A failure of all five is the pre-registered kill condition: PageRank
fails the magnitude pre-gate and the campaign moves to HNSW **without building
a DuckDB streamer**.

## What this gate does not claim

No co-run tax, recovery, or frontier result. No streamer and no aggressor is
launched. CMT occupancy is recorded per trial as a diagnostic only and is
explicitly not attributed to `outgoing_contrib` nor used in the selection.

## 5. Prediction recorded before the g24--g25 extension (2026-08-21)

Scales 21--23 have landed. `moscxl` passes at g21 (2.574x) and g22 (2.124x)
and fails at g23 (1.670x); `mos181` fails all three (1.312x, 1.123x, 1.098x).
Per decision 4, `moscxl` stops -- it has passed, and the rule takes the
*smallest* passing scale, so g24/g25 cannot change its selection -- while
`mos181` extends to g24--g25.

**Predicted outcome of that extension: `mos181` fails both, and PageRank has no
passing scale on the 320 MiB host.** The ratio is monotonically decreasing in
scale on both hosts, and the mechanism accounts for it: the full-mask arm loses
its advantage as soon as the graph outgrows the full mask. At g21 the CSR is
about 268 MB and fits inside 320 MiB, which is why the Intel full-mask arm is
unusually fast there and the ratio is at its highest; from g22 (about 537 MB)
the full-mask arm is already DRAM-bound, and further scale can only shrink the
gap. The Intel g22 -> g23 full-mask time rises 4.2x (2.748 s -> 11.485 s)
against a 2x increase in work, which is that transition showing up directly.

This is recorded as a prediction and not as a reason to skip the runs. The
pre-registration names g21--g25, and a monotone trend across three points plus
a mechanism is an argument, not a measurement.

## 6. What a failure on `mos181` would and would not license

The minimum-way arm confines the victim to one way, which is **harsher than any
co-runner can be through the capacity channel**: a co-runner competes for ways,
it cannot confine. So a ceiling measured this way is a ceiling on the
capacity-mediated tax -- and the capacity-mediated tax is exactly the quantity
non-allocation could recover. If PageRank on `mos181` moves only 1.10--1.31x
across the entire CAT range, then no aggressor can hand H2 more than that to
recover on this victim and host, and the pre-gate has done its job: it stops a
multi-day co-run campaign whose headroom was capped at 1.31x before it starts.

Two limits on that reading, stated so it is not over-claimed. The bound is on
the capacity channel only: a co-runner also adds memory-bandwidth and
DRAM/CXL queueing pressure, which way-confinement does not, so total
interference is not bounded by this gate. And a CAT way mask is shared rather
than isolated -- the default group retains the full mask -- so the victim's one
way is not private to it.

Finally, the arithmetic behind the Intel failure is worth naming on its own:
20 ways over a 320 MB LLC makes one way 16 MiB, which is larger than the
*entire* LLC of the AMD host in the same table. On this platform CAT cannot
express a small allocation at all. That is a granularity limit, independent of
the context-scoping argument in \S2, and it is why the same workload is
capacity-sensitive on the smaller-LLC host and not on the larger one.
