# M5 pre-registration: is the rate-invariant floor F's own hot table?

Written before measurement. M4 established the non-residency floor is
rate-invariant (1.20× over a 14.5× rate range), so it is not congestion. The
leading candidate is the one thing held constant across that sweep: **F's 256 MiB
hot table**, which flush-behind never touches because F is actively using it.

## Arms

Identical to M4's 16-worker point except for `--hot-bytes`. Victim
`pointer_chase` 170 MB on cpu8; F = 16 workers, hit rate 1.0, fact 256 MiB on
CXL node 2. n=7, order rotated.

| arm | F's hot table | F's stream |
|---|---|---|
| **V** | — | — |
| **Fbig_retain** | 256 MiB | retain (M4's F16_retain, reproduced) |
| **Fbig_flush** | 256 MiB | flush 256 KiB |
| **Fsmall_retain** | **4 MiB** | retain |
| **Fsmall_flush** | **4 MiB** | flush 256 KiB |

## Pre-registered reading

    floor(table) = harm_flush(table) - 1

| outcome | verdict |
|---|---|
| `floor(4 MiB)` ≤ **0.15** (i.e. harm_flush ≤ 1.15×) | **the floor is F's hot table.** The non-residency component is a *second resident working set*, not transport. This reconciles W5.3-Intel without rate-dependence, and it means the residency share depends on how much *other* cache-resident state the tenant has — a covariate, not a constant. |
| `floor(4 MiB)` ≥ **0.80** (i.e. ≥ 60% of the 1.279 big-table floor survives) | **the floor is not the table.** It is something intrinsic to reading 256 MiB from CXL that flushing does not remove, and the AMD point's 2.30× floor is the same phenomenon. The component stays unidentified. |
| between | partial; report the fraction, claim neither |

**Registered confound:** shrinking the table also makes F's probes cheaper, so F
runs faster and streams *more* per unit time. That biases **toward** a surviving
floor, so a collapse is conservative. F's stream rate is recorded per arm.

**Registered check:** `Fbig_retain` and `Fbig_flush` must reproduce M4's 2.7677
and 2.2793 within 0.1×, and V must land in [78.05, 78.20], or the run is void.

## Why this matters beyond bookkeeping

If the floor is a second resident working set, the paper's claim sharpens
considerably: a page-scoped stream label removes stream residency **completely**,
and what remains is the tenant's *own* data — which no admission-control
mechanism should remove, because the tenant needs it. The 28% would then not be a
ceiling on the mechanism; it would be the mechanism working fully on the part it
addresses, in a configuration where the tenant happens to carry a large working
set of its own.

That is a materially better result than "the mechanism buys 28%", and it is
falsifiable by this experiment.
