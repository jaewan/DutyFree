# The harm is L3 admission work: why partitioning is the wrong tool

Date: 2026-09-01.  A synthesis of measurements already in this repository.  It
introduces no new experiment; it states what three existing results imply when
read together, because that implication is the strongest argument the project
has and it was not written down anywhere.

## The syllogism

**1. The harm is not capacity.**  `AMD_CATOCC_OUTCOME_2026-08-30.md`, EPYC 9754.
Victim quiescent: 55.34 cyc/access, 3292 KB resident in L3.

| arm | aggressor ways | victim L3 occupancy | % of quiescent | slowdown |
| --- | --- | --- | --- | --- |
| `cat4` | 4 | 2920 KB | 88.7% | **9.20x** |
| `cat1` | 1 | 3008 KB | **91.4%** | **9.24x** |

A way mask gives the victim back 91% of its cache residency and the victim is
still 9.2x slower.  `AMD_NARROWMASK_OUTCOME` adds that *aiming* the mask changes
nothing (65.1 / 65.3 / 65.1% of harm removed).  Capacity is restored; performance
is not.  Whatever the residual is, a capacity tool cannot reach it.

**2. The harm is not global bandwidth or fabric.**
`BERGAMO_BACKINVAL_OUTCOME_2026-08-30.md`, 4096 KB victim:

| victim placement | slowdown | aggressor bandwidth |
| --- | --- | --- |
| same-CCX | **27.77x** / **30.82x** | 24.78 / 24.24 GB/s |
| other-CCX | **1.31x** / **1.30x** | 24.81 / 24.24 GB/s |

The aggressor pushes the *same* bandwidth in both rows.  Moving the victim to
another CCX -- same memory controllers, same fabric, same DRAM pressure --
removes ~95% of the harm.  So the harm is local to the L3 domain, not global.

**3. Therefore the harm is a shared resource that is L3-domain-local and is not
capacity.**  That narrows the space sharply, but it does **not** uniquely
identify admission work.  Fill buffers, MSHR occupancy, L3 bank and queue
contention, CCX-internal interconnect arbitration, and coherence traffic are all
L3-domain-local, all non-capacity, and all remain plausible.  The evidence is
*consistent with* admission-path contention; it does not isolate it.

Isolating it needs an experiment this repository does not yet have -- e.g.
varying the aggressor's miss *rate* at fixed footprint, or instrumenting L3 fill
queue occupancy directly.  Until then the claim must be stated as elimination
("not capacity, not global bandwidth") plus a consistent hypothesis, never as a
demonstrated cause.

## Why CAT cannot fix it and H2 can

A way mask constrains *where* a line may land.  The streamer still misses, the
line still arrives, the L3 still writes it into a permitted way, still updates
tags, still runs replacement.  **All of the admission work still happens; only
placement is restricted.**  That is exactly why occupancy comes back while
performance does not.

H2 suppresses *admission*.  The work is never performed.  Measured in
`atomic_2cpu_w8_fs_e2e_r12_16g_gate_stream_mprot`: **118,260** allocations
declined against 0 in both controls, HNF data-array writes **682,901 ->
436,911**.

H2 is therefore *aimed at* the admission path, which the evidence above is
consistent with but does not prove is the binding resource.  Stated carefully:
CAT demonstrably fails, and H2 targets a mechanism in the surviving candidate
set.

On the alternatives -- scoped to x86 server parts examined here (EMR, SPR,
EPYC 9754 Zen 4c), not to all hardware ever built:
write-combining is non-allocating but costs 3.9x bandwidth; `prefetchnta` does
not avoid allocation on Zen 4c (100% L2 miss, `AMD_NARROWMASK_OUTCOME`); CAT is
per-requestor and cannot separate a stream from a working set inside one
process; flush-behind is per-access-site software.

## What this does NOT establish

- **The magnitude does not transfer.**  gem5 uses `SimpleMemory` and abstract HNF
  latencies; it does not faithfully model L3 fill-port contention.  Silicon shows
  the harm is admission-shaped; the model shows H2 removes admission.  Connecting
  them *quantitatively* is future work and must be stated as such.
- **The gem5 regime is mild.**  In the metric-B campaign a real hash join costs
  its neighbour only ~1-2%, versus 9.2x on Bergamo.  These are different regimes,
  and the paper must not silently blend them.
- **The fused-vs-real comparison is WITHDRAWN.**  It was stated as "+6.21% vs
  +1.48%, hence 4.2x".  The two arms do not share a measurement window: the
  fused arms report `victim_loads` = 12,001,060, identical to the tenant-free
  `qui` arm, because fused's initialisation is short enough that the *victim's*
  own reset lands last and defines the window; the real-join arms report
  10.5-10.8M because the *tenant's* reset lands last.  Both windows are
  plausibly steady-state, but that was argued after the fact, not verified, and
  the ratio must not be quoted until the fused reference is re-run with a
  phase-aligned barrier and the same A6 window gate.

## Consequence for the paper

Lead with the characterisation and the diagnosis, not with a cost wedge.  The
claim "way partitioning is aimed at the wrong resource" is supported by silicon,
is non-obvious, contradicts the premise of a large body of LLC-partitioning work,
and survives regardless of how large the wedge turns out to be.
