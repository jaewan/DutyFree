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

## 7. A third host was added, and the hypothesis behind adding it was falsified

`mos181` failed g21--g23, which would have cost the campaign its cross-vendor
victim. Before extending scales, note that the failure is a property of a
320 MB LLC: 20 ways over 320 MB makes one way 16 MiB, and PageRank's reused
structures at g21 (a `scores` and an `outgoing_contrib` array, about 8.4 MB
each) largely fit inside that. `tab:appplat` already lists a second Intel host
-- the 8462Y+, 60 MB LLC over 15 ways, one way = 4 MiB -- so `mos182` was
added to `CFG` and gated on the same pinned GAPBS commit.

**Hypothesis, recorded before that run: `mos182` passes**, because the
full/min *ratios* are near-identical across all three hosts (20x, 15x, 16x),
so a ratio cannot be what distinguishes them; what differs is the minimum
mask in absolute terms against the hot set, and 4 MiB sits below it where
16 MiB sits above.

**Falsified.** `mos182` gives 1.435x at g21 and 1.347x at g22, with CoV under
0.1%. Dropping the minimum from 16 MiB to 4 MiB moved the Intel ratio from
1.311x to 1.435x -- not to anything near AMD's 2.580x at 1 MiB.

So absolute minimum capacity is not the discriminator either. Adding each
host's private L2 to its minimum mask gives the capacity the victim actually
retains: 18 MiB on `mos181`, 6 MiB on `mos182`, 2 MiB on `moscxl` (Intel
carries a 2 MiB L2 per core against AMD's 1 MiB). `mos182` therefore retains
about a third of a roughly 17 MB hot set and still slows by only 1.35--1.44x,
where AMD retains an eighth and slows by 2.13--2.58x. Something beyond
capacity -- most plausibly Intel's more aggressive prefetch and greater
memory-level parallelism covering the added misses -- is absorbing the
difference. This gate does not measure that, and no claim about it is made
here beyond ruling out the capacity explanation.

The measured outcome is what stands: **PageRank is capacity-sensitive enough
to pass on the AMD host and on neither Intel host.**

## 8. The bar is not moving

`mos182`'s 1.44x and `mos181`'s 1.31x are real taxes, and a real-application
arm reporting a 1.4x tax with a high recovery fraction would not be a weak
result. It is nonetheless not what was pre-registered. The 2x bar was fixed
on 2026-08-11 before any arm ran, and lowering it now, having seen three
hosts fail it, is the move §6.6 of the session prompt exists to forbid. If a
sub-2x operating point is wanted, it needs a fresh pre-registration that
states its bar before the data is looked at again -- not an amendment to this
one.

## 9. A defect in the trial count, affecting the co-run pre-registration too

On `moscxl` at g22 the four trials of every invocation **alternate**, by about
9%, in both arms:

    g22 full inv0: 1.9041  1.7492  1.9123  1.7447
    g22 min  inv0: 3.7797  3.7184  3.7819  3.7214

`mos181` and `mos182` show no such pattern -- only a warm-up decay. The
mechanism is consistent with PageRank double-buffering `scores` and
`outgoing_contrib`: on a 16 MiB L3 with a roughly 16 MB hot set, one buffer's
placement fits and the other's does not, while on 320 MiB and 60 MiB LLCs both
fit.

The defect is in the sampling, not the workload. `pr -n 4` with the first
trial discarded leaves **three** measured trials -- an odd sample of a
two-phase signal -- so the median is phase-biased, and which phase wins can
differ between arms. Phase-matched, g22 on `moscxl` is 2.126x on the low phase
and 1.983x on the high one: it straddles the bar depending on a sampling
parity. g21, the selected scale, is 2.561--2.794x across every reading and is
unaffected, so the selection stands.

`GAPBS_DUCKDB_CORUN_PREREGISTRATION.md` specifies the same `pr -g SCALE -n 4
-r 1 -l`, and computes each tax as loaded over matched quiescent. Both sides of
that ratio would carry the same parity bias. **The co-run runner should use an
even number of measured trials (`-n 5` or `-n 7`) before any arm is taken.**
That is a correction to a pre-registered command, so it is recorded here for
the lead rather than applied silently.

## 10. Three explanations for the AMD variance were tested and eliminated

`moscxl`'s g21 full-mask arm varies about 8% *between* invocations (per-
invocation medians 0.4892, 0.4518, 0.4887 s), against 0.1% on the frozen Intel
hosts. Each hypothesis was tested by re-running g21 with one knob changed and
the artifact kept separately (`cat_freqdiag_*_moscxl.jsonl`):

| hypothesis | test | result |
|---|---|---|
| DVFS, since the host is unfrozen | `performance` governor on cpu8 and its SMT sibling only, leaving every other core alone | **falsified** -- still 0.4433 / 0.4468 / 0.4895 |
| co-tenants on the victim's CCX sharing its 16 MiB L3 | 20 s `/proc/stat` sample of all 16 threads of cpu8's L3 domain | **falsified** -- 7 busy jiffies out of ~32,000, i.e. 0.02% |
| AutoNUMA, which is on here and off on `mos181` | `numa_balancing=0`, restored afterwards | **falsified** -- still 0.4450 / 0.4895 / 0.4475 |

The values recur at two discrete levels, about 0.445 s and 0.489 s, rather
than scattering, which is the signature of per-invocation physical page
placement against a 16 MiB L3 -- not something freezing the host would fix.
Decision 3's claim that per-CCX L3 keeps the desktop from contending was an
assumption when written; the second row above is now the measurement, and it
happens to support it. The AMD selection at g21 holds across the full
0.4509--0.4919 s span (2.561--2.794x), so no arm needs repeating for it.
