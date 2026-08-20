# Outcome: GAPBS PageRank CAT capacity-sensitivity gate

Dated 2026-08-21. Implements `GAPBS_CAT_SENSITIVITY_PREREGISTRATION.md`
(2026-08-11), which had been the campaign's blocking gate for ten days with no
runner. Every run-time departure is recorded in
`GAPBS_CAT_SENSITIVITY_RUN_DECISIONS.md`, written before results were read.
No streamer and no aggressor was launched.

## Result

GAPBS pinned to `2972aeb`, the commit the sizing gate recorded. `pr -g SCALE
-n 4 -r 1 -l`, one pinned OpenMP thread, first trial as warm-up, three
invocations per scale and mask, on the victim CPU each host used for the sizing
gate.

| host | LLC / ways | full | min | scale | full median | min median | ratio | pass |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `mos181` (8592+) | 320 MB / 20 | 320 MiB | 16 MiB | g21 | 0.724330 s | 0.949830 s | 1.311 | fail |
| | | | | g22 | 2.748220 s | 3.085530 s | 1.123 | fail |
| | | | | g23 | 11.484790 s | 12.612240 s | 1.098 | fail |
| | | | | g24 | 15.565260 s | 17.431470 s | 1.120 | fail |
| | | | | g25 | -- | -- | -- | running |
| `mos182` (8462Y+) | 60 MB / 15 | 60 MiB | 4 MiB | g21 | 0.594890 s | 0.852770 s | 1.433 | fail |
| | | | | g22 | 2.003310 s | 2.698410 s | 1.347 | fail |
| | | | | g23 | 8.052090 s | 10.817980 s | 1.343 | fail |
| `moscxl` (EPYC 9754) | 16 MB / CCX, 16 | 16 MiB | 1 MiB | g21 | 0.488290 s | 1.259800 s | **2.580** | **PASS** |
| | | | | g22 | 1.749400 s | 3.718370 s | **2.126** | **PASS** |
| | | | | g23 | 7.533790 s | 12.578820 s | 1.670 | fail |

**Selected: `moscxl` at g21.** The rule takes the smallest passing scale, so
g22's pass is not the selection and higher scales could not change it, which is
why `moscxl` stopped at g23. Neither Intel host has a passing scale.

Reproducibility against the independent 2026-08-11 sizing gate, ten days and a
different runner apart: `mos181` g22 full 2.748220 s against 2.748790 s, and
g24 full 15.565260 s against 15.541270 s. `moscxl` g22 full 1.749400 s against
2.140120 s -- see the variance note below.

CoV was 0.023--0.248% on the Intel hosts. On `moscxl` it reached 3.905% and
4.477% on the full-mask arm, inside the 5% bound but two orders of magnitude
worse, discussed below.

## What the failures mean, and what they do not

The minimum-way arm **confines** the victim to one way. A co-runner competes for
ways and cannot confine, so through the capacity channel this arm is harsher
than any co-runner -- and the capacity channel is exactly what non-allocation
recovers. A victim that moves only 1.10--1.43x across the entire CAT range
therefore cannot hand H2 more than that to recover, whatever aggressor is
placed beside it. The pre-gate has done its job: it stopped a multi-day co-run
campaign whose headroom was capped at 1.43x before the campaign began.

Two limits, so this is not over-read. The bound is on the capacity channel
only; a co-runner also adds bandwidth and DRAM/CXL queueing pressure that
way-confinement does not. And the masked way is shared with the default group
rather than private to the victim.

## Why the Intel hosts fail, with one explanation ruled out

Two predictions were recorded before the runs and **both were falsified**,
which is why the explanation below is offered narrowly.

The first predicted the ratio would rise with scale on `mos181` as PageRank's
hot arrays outgrew one 16 MiB way. It fell instead, 1.311 -> 1.123, because the
full-mask arm loses its advantage once the *graph* outgrows the full mask: at
g21 the CSR is about 268 MB and fits inside 320 MiB, and the g22 -> g23
full-mask time rises 4.2x against 2x more work, which is that transition.

The second added `mos182` predicting it would pass, on the reasoning that the
full/min ratios are near-identical across all three hosts (20x, 15x, 16x) so
the discriminator had to be the minimum mask in absolute terms against the hot
set -- 4 MiB below it where 16 MiB is above. `mos182` gave 1.433x. Counting
each host's private L2 alongside its minimum mask, the retained capacity is
18 MiB, 6 MiB and 2 MiB; `mos182` keeps about a third of a roughly 17 MB hot
set and slows 1.35--1.43x where AMD keeps an eighth and slows 2.13--2.58x.
**Capacity alone is therefore ruled out as the explanation, and nothing is
claimed in its place by this gate.** The HNSW gate that followed supplies the
missing half independently: there, cache denial that *halved* DRAM traffic
bought only a third more runtime, because the misses overlapped. Whether
Intel's larger L2 and more aggressive prefetch do the same for PageRank is
consistent with these numbers and is not measured here.

One arithmetic observation stands on its own: 20 ways over a 320 MB LLC makes
one way 16 MiB, larger than the *entire* LLC of the AMD host in the same
platform table. On `mos181`, CAT cannot express a small allocation at all.
That is a granularity limit independent of the context-scoping argument the
paper makes in §2.

## The `moscxl` variance, and three eliminated causes

`moscxl`'s g21 full-mask arm sits at two discrete levels across invocations
(medians 0.4892, 0.4518, 0.4887 s) rather than scattering. Each candidate cause
was tested by re-running g21 with one knob changed, artifacts kept separately
as `cat_freqdiag_*_moscxl.jsonl`:

| hypothesis | test | result |
|---|---|---|
| DVFS -- the host is unfrozen, `schedutil` with boost on | `performance` on cpu8 and its SMT sibling only | **falsified**, 0.4433 / 0.4468 / 0.4895 |
| co-tenants sharing the victim's 16 MiB CCX L3 | 20 s `/proc/stat` sample of all 16 threads of that L3 domain | **falsified**, 7 busy jiffies of ~32,000 |
| AutoNUMA, on here and off on `mos181` | `numa_balancing=0`, restored after | **falsified**, 0.4450 / 0.4895 / 0.4475 |

Two reproducible levels rather than a spread points at per-invocation physical
page placement against a 16 MiB L3, which freezing would not fix. Separately at
g22 the four trials *alternate* by about 9% within every invocation, in both
arms, consistent with PageRank double-buffering `scores` and
`outgoing_contrib` where one buffer's placement fits a 16 MiB L3 and the
other's does not; neither Intel host shows it. HNSW on the same host shows
neither effect (CoV 0.205%), which supports both explanations being specific to
PageRank's large contiguous arrays.

**The selection survives all of it.** At g21 the min-arm median divided by the
extremes of the full arm spans 2.561--2.794x, entirely above the bar.

## A defect in the trial count, which the co-run pre-registration inherits

`pr -n 4` with the first trial discarded leaves **three** measured trials -- an
odd sample of the two-phase signal above -- so the median is phase-biased.
Phase-matched, g22 on `moscxl` is 2.126x on one phase and 1.983x on the other:
its verdict straddles the bar on a sampling parity. g21 is unaffected.

`GAPBS_DUCKDB_CORUN_PREREGISTRATION.md` specifies the same `pr -g SCALE -n 4
-r 1 -l` and computes each tax as loaded over matched quiescent, so both sides
of that ratio would carry the same bias. **The co-run runner should use an even
measured count (`-n 5` or `-n 7`).** The HNSW gate already does.

Also inherited: PageRank's `mbm_local_bytes` samples in this gate are not
usable -- absolute values decrease across freshly created groups with ~1 KB
per-trial deltas against 14.8 MiB of occupancy, consistent with RMID recycling
under 18 groups against 16 CLOSIDs. No verdict here depends on them; trial
times come from the victim's own output. But the co-run pre-registration
invalidates an arm when "the streamer has zero traffic", and on AMD under group
churn that can be an artifact. The runner should confirm the counter is live
against a known-busy control before discarding an arm.

## Consequence for the campaign

Under `GAPBS_DUCKDB_CORUN_PREREGISTRATION.md`'s falsifiable outcome 1, a WB tax
below 2x on either host fails "the magnitude or cross-vendor bar", and this
gate ceilings the Intel capacity-mediated tax below that bar on both Intel
hosts. PageRank is a viable co-run victim on `moscxl` at g21 and on neither
Intel host.

The pre-registered alternative, HNSW, was then built and gated rather than
assumed: it fails on every host including AMD
(`../hnsw/HNSW_CAT_SENSITIVITY_OUTCOME.md`). So the real-application arm is
single-vendor whichever of the two candidate victims is chosen, and that is now
a measured statement rather than a fallback.

**What this does not cost.** The paper's cross-vendor claim does not rest on
this campaign. §2 rests it on CAT/MBA on Intel plus a way sweep and a
non-allocating aggressor on AMD, and says explicitly that "only the gem5 H2/H3
model is Intel-only". What is single-vendor here is the *real-application*
frontier arm.

**The bar is not moving.** `mos182`'s 1.43x and `mos181`'s 1.31x are real
taxes, and a real-application arm reporting 1.4x with a high recovery fraction
would not be a weak result -- but the 2x bar was fixed before any arm ran, and
lowering it now that three hosts have failed it is what §6.6 exists to forbid.
A sub-2x operating point needs a fresh pre-registration stating its bar in
advance.
