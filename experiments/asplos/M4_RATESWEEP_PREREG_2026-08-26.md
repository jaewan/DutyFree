# M4 pre-registration: is the non-residency component rate-dependent?

Written before measurement. **This is the last measurement before writing**, and
it must reconcile two results that currently contradict each other.

## The contradiction it has to resolve

| datum | harm | what a pure residency control achieved |
|---|--:|---|
| W5.3, Intel SPR, 1.62× harm | 1.62× | **CAT12 alone → 1.00×** — residency was ~everything |
| M3b, Intel EMR, 2.77× harm | 2.77× | flush-behind → 2.28× — residency was **28%** |
| AMD Bergamo, 6.48× harm | 6.48× | flush-behind → 2.30× — residency was **76%** |

All three used a residency-only intervention. The residency share reads ~100%,
28% and 76%. Either the model is wrong, or **the non-residency component depends
on rate** and these are three points on one curve. Invoking that is not showing
it, and selective retrodiction is the failure this project has caught in itself
repeatedly.

## The lever, and why this one

Worker count. The standing rule is explicit — *"thread count is the honest way to
vary this; the `-R` pacing throttle carries a known confound and was not used"* —
and MBA is the same class of intervention, which is why it was rejected for T4.

Calibrated before registering, F standalone at hit rate 1.0:

| workers | stream GB/s | F's own cyc/access |
|--:|--:|--:|
| 1 | 0.702 | 43.23 |
| 2 | 1.394 | 43.36 |
| 4 | 2.748 | 43.46 |
| 8 | 5.403 | 43.94 |
| 16 | 10.157 | 44.61 |

A **14.5× rate range** with F's per-access cost changing 3%. Clean.

**Registered confound:** worker count changes active core count as well as rate.
Both move together and cannot be separated with this lever. Stated rather than
hidden; a pacing lever would separate them but is barred for distorting the
arrival distribution, which is worse for a queueing question specifically.

## Arms

Victim `pointer_chase` 170 MB on cpu8, unchanged. F = morsel, hit rate 1.0, fact
256 MiB on CXL node 2, hot table 256 MiB, workers pinned from core 32 up.
**11 arms, n=11** so rotation puts each arm in each position exactly once.

`V` · for w ∈ {1, 2, 4, 8, 16}: `F{w}_retain` (D=0) and `F{w}_flush` (D=256 KiB).

## Quantities

For each rate:

    harm(w)      = victim cyc/load with F / victim alone
    floor(w)     = harm_flush(w) - 1        # the non-residency component
    residency(w) = harm_retain(w) - harm_flush(w)
    share(w)     = residency(w) / (harm_retain(w) - 1)

## Pre-registered readings

**Primary — how does the floor scale?** Rate rises 14.5× from 1 to 16 workers.

| outcome | verdict |
|---|---|
| `floor(16)/floor(1)` **> 20** (superlinear in rate) | **queueing near saturation.** The non-residency component is a congestion effect, the residency share is a curve, and W5.3's Intel row, M3b and AMD plausibly lie on one axis. The model becomes predictive. |
| ratio **7–20** (≈ linear, i.e. ∝ bytes) | proportional to traffic — fill-path or far-from-saturation queueing. Model holds but is not a saturation story, and W5.3's Intel row needs a different explanation. |
| ratio **< 3** (flat across 14.5×) | **the rate-dependence rescue FAILS.** The non-residency component is fixed per-stream, W5.3's Intel counter-point stays unexplained, and the two-component model is reported as a hypothesis with an outstanding contradiction. |

**Secondary — does the residency share move the way the rescue requires?**
The rescue predicts `share(w)` **falls as rate rises**, approaching ~100% at the
lowest rate (matching W5.3's Intel CAT-complete result at a small harm) and ~28%
at 16 workers (matching M3b). Registered: if `share` is **flat within ±15 points**
across the 14.5× range, the rescue fails regardless of what the floor does, and
that is reported as the headline.

**Instrument check, not optional.** `harm_retain(16)` must reproduce M3b's 2.77×
and `harm_flush(16)` its 2.28× within 0.1×; the victim-alone arm must land at
78.05–78.20 as it has in four prior campaigns. If any of those miss, the run is
void.

## Out of scope

AMD (unreachable for three days); any pacing lever; any change to either binary;
hit rates other than 1.0 (M2 established 0.5 masks the stream entirely).
