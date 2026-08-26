# Rewriting the claim from M6's outcome

Ordered by the panel: "register and run the 2x2xmask campaign; rewrite the claim
from its outcome." M6 is run (`M6_OUTCOME_2026-08-26.md`, `bb7396f`). This is the
rewrite, and the list of paper edits it forces.

## The claim as it stands

Sec1, contribution (2), verbatim:

> **Neither bypass nor enforcement is the missing piece---the *label* is**:
> fusion shows object scope is *necessary*, since one thread interleaving a
> stream with a reused structure gives both access classes a single context
> label, and way-partitioning shows capacity control is *insufficient*, leaving a
> 9.87x residual at full bandwidth on AMD silicon.

The word *necessary* is carrying two different jobs, and M6 separates them.

| | job | status after M6 |
|---|---|---|
| (a) | protect a **neighbour** from a streaming tenant | **fails on Intel** |
| (b) | let a **fused tenant** keep its own reused structure resident while streaming | **survives** |

## (a) Neighbour protection: the shipped knob wins on Intel

M6 gave F a 2-of-20-way mask on its own cores and V the complement. V returns to
0.9924x (4 MiB table) and 0.9899x (256 MiB table), stream retained or flushed,
at a cost to F of +2.9% and +7.5%. The label's proxy reaches 0.9928x at 4 MiB for
+18.7%, and at 256 MiB does not protect V at all (2.2776x).

This is not a surprise result hiding in a new corner. `tab:catmba` has said since
W5.3 that on EMR a 1-way or 3-way aggressor mask returns the victim to 0.99x at
full bandwidth. What M6 removes is the **escape hatch**: the reply had been that
those arms used a pure streamer, and a *fused* tenant cannot be masked that way
because the mask would take its hot table too. M6 ran exactly that geometry --- F
holding a 256 MiB reused table *and* streaming --- and core-scoped confinement
still returns V to 0.99x for +7.5%. You do not have to separate F's two access
classes to protect V. You confine F wholesale and let V hold the complement.

**So we cannot claim the mechanism is needed for the multi-tenant story on
Intel.** Any sentence in the paper that reads "no deployed mechanism protects the
neighbour" must be scoped to the platform, or deleted.

## (a'), AMD: the one number that still refutes partitioning was taken at the wrong mask width

`tab:amdcat` is now the paper's *only* surviving hardware CAT-insufficiency
result: 19.89x -> 9.87x under an **8/8 equal way split** on EPYC 9754, a 53%
removal with the victim's 4 MiB fitting inside its 8 MiB of ways.

Intel's answer is that an equal split is not the configuration that works ---
**narrow** is. On EMR, 3 ways to the aggressor gives 0.99x; 8 of 20 would not.
And a narrow-aggressor mask on AMD **has never been run.** The AMD arm sweep in
`tab:amdcat` moves ways *toward the victim* (15/16 -> 5.89x), which is the same
direction, but it is the victim's allocation that grows, not the aggressor's that
is squeezed to 1--2 ways with the rest held by the victim as an enforced
complement.

This promotes the queued AMD reconciliation from "portability check" to **the
single most load-bearing missing experiment in the paper.** If a 1-of-16-way
aggressor mask on the 9754 leaves a large residual, the abstraction claim is
alive and is now *precisely* stated: on AMD the harm is lookup/fill-path and no
bitmask can shed it, on Intel it is capacity and a bitmask can, and an OS-level
type is the only thing that covers both. If instead the narrow AMD mask also
returns the victim to ~0.99x, then no platform in this paper needs the mechanism
for neighbour protection and (b) is the whole case.

Blocked: broker (moscxl) has refused SSH handshake for four days. Nothing else
in the paper is gated on it. This is.

## (b) Self-protection under fusion: survives, with its magnitude rescoped

The surviving claim is about **expressibility, not magnitude**:

> A context-scoped mask cannot let one thread keep its reused structure resident
> while denying residency to the stream that thread is also issuing, because both
> arrive under one label. Every mask narrow enough to constrain the stream
> constrains the structure with it. An object-scoped label is the only mechanism
> in the taxonomy that separates them.

Every measured fact behind that still holds: monotonicity in ways at fixed hit
rate, harm surviving at a single core and flat 1--16 cores, and the split
restructuring costing 36% of throughput while recovering none of the hot-table
tax. Those are same-workload comparisons and M6 does not touch them.

What M6 does touch is **how big the penalty is**, and the answer is hit-rate
specific:

| restriction on the fused class | hit rate | hot-table cost |
|---|--:|--:|
| `tab:fused`, 4 of 20 ways | 0.5 | 88.5 -> 126.9, **+43%** |
| M6 pass A, 2 of 20 ways, 256 MiB | 1.0 | 52.00 -> 55.90, **+7.5%** |

The tighter mask at the higher hit rate hurts *less*, by a factor of six. At
hr 0.5 the probe misses half the time and walks linear-probe chains across the
whole table, so any mask starves it; at hr 1.0 it does not. `tab:fused`'s
+19--44% column therefore describes a miss-heavy probe, not fused joins in
general, and must say so. This is the third time this benchmark's hit rate has
silently set a headline (it withdrew the 1.47x tax and the split's negative
recovery); it gets a standing caveat now.

## The rewritten contribution (2)

> **The missing piece is the label, and its scope is the tenant's own object, not
> its neighbour's protection.** Where the harm is shared-cache capacity and the
> streaming tenant runs on its own cores, a deployed allocation bitmask already
> returns the neighbour to baseline at full bandwidth, and we measure its price
> to the streaming tenant at 2.9--7.5% (\S\ref{sec:controls}) --- including in the
> fused geometry, where the tenant holds a 256 MiB reused table and streams from
> the same thread. What no context-scoped mechanism can do, at any width, is let
> that thread keep its own reused structure resident while denying residency to
> its own stream: both arrive under one label, the sweep is monotone in ways at
> fixed hit rate, and restructuring the application so a mask *can* apply costs
> 36% of throughput and recovers none of the tax (\S\ref{sec:declpred}). Where
> the harm is instead on the local fill path, a bitmask sheds none of it: on
> EPYC 9754 an equal way split leaves a 9.87x residual at full bandwidth
> (\S\ref{sec:eval}). Object scope is what those two have in common.

Contribution (2) no longer promises that the mechanism is the only way to protect
a neighbour. It promises that it is the only way to name an object --- which is
what the taxonomy actually establishes, and what the fused evidence actually
measures.

## Edit list

1. **Sec1 contribution (2)** --- replace with the paragraph above. (done)
2. **Sec1 closing "portable lesson"** --- unchanged; it is a statement about
   labeling, and M6 strengthens it.
3. **Sec5 fused-necessity paragraph** ("On the *fused single thread*,
   \textsc{Streaming} is *necessary*") --- scope "necessary" to
   self-protection, and state the neighbour result against it. (done)
4. **Sec5 AMD portability heading** --- add that the AMD residual is measured at
   an equal split, that Intel's working configuration is a narrow aggressor mask,
   and that the narrow AMD cell is unrun. (done)
5. **`tab:fused` caption** --- add the hit-rate scope on the +19--44% column.
   (done)
6. **`tab:amdcat` caption** --- add the mask-width gap. (done)
7. **`tab:catmba` caption** --- add M6's F-side cost and the fused cell, so the
   cost of the shipped knob is on the record next to its effect. (done)
8. **Abstract** --- deferred. It currently leads on CAT-insufficiency; it should
   lead on object scope. Not touched today because the abstract should be written
   once, after the AMD narrow cell resolves.

## Standing

This is a narrowing, not a retraction. The two-component account, the taxonomy,
RocksDB's demand evidence, W5.3's boundary map, H3's capability claim and the
gem5 bounds are all untouched. What is gone is the multi-tenant necessity
framing on Intel, and what is newly exposed is that the surviving cross-vendor
refutation rests on one mask width we did not vary.
