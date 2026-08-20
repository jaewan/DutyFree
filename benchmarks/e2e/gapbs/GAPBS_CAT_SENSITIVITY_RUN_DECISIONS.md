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
