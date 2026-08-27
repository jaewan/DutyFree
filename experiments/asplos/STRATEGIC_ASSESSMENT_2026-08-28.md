# Strategic assessment: L5 is dead on *both* vendors, and the critical path is not the AMD host

Written 2026-08-28 after the red-team review, as a decision record. No new
measurements. Its purpose is to correct a strategic error I made on 08-26 and to
name the experiment that should run next.

## The correction

On 08-26 and again on 08-27 I told the lead that the unrun narrow-aggressor CAT
cell on the 9754 was *"the single experiment that decides what this paper
claims"* and *"the highest-value thing anyone can do for this paper right now."*

**That was wrong, and our own committed evidence says so.**
`W5.3_L5_EVIDENCE_2026-08-23.md` --- written five days before I said it ---
already establishes that a shipped mitigation returns the neighbour to baseline
on **both** vendors at negligible bandwidth cost:

| host | unmitigated | the working shipped mitigation | streamer BW cost |
|---|--:|---|--:|
| Intel SPR (8462Y+) | 1.62x | CAT12 alone -> co-run residual **1.00x** | **0.7%** |
| AMD Bergamo (9754) | 18.73x | CAT12 + MBA192 -> **1.07x** | **4%** |

So **L5 --- "no deployed alternative protects the neighbour" --- is dead on both
platforms**, not just on Intel as `M6_OUTCOME` and `CLAIM_REWRITE` framed it.

What the AMD narrow-mask cell can still settle is the narrower *mechanism*
question: whether a bitmask **alone** can shed AMD's fill-path harm. That is
worth knowing and it sharpens §5's cross-vendor argument. It **cannot** revive
L5, because CAT+MBA already reaches 1.07x at 96% of full bandwidth. The host is
therefore **downgraded from blocker to nice-to-have**, and no further work should
wait on it.

I should have caught this before advising the lead twice. The failure mode is
F11 from the W4.3 ledger --- a correct artifact committed in the repo that nobody
re-read --- and this time I was the one who did not re-read it.

## What the surviving case actually is

Not necessity. **Cost asymmetry.** Every shipped mitigation works by confining or
throttling the tenant, and its price depends on what the tenant itself keeps in
cache:

| the tenant | price of the shipped mitigation |
|---|--:|
| a **pure** streamer (nothing reused in cache) | 0.7% (Intel, W5.3) |
| a **fused** tenant whose reused structure fits its mask | ~2% (M10/M10b, hr 0.5) |
| a **fused** tenant whose reused structure exceeds its mask | **37--41%** (M10/M10b, hr 0.5) |

Non-allocation removes the stream's residency **completely** (M5: victim to
0.993x) without touching the tenant's own data, so its cost does not scale with
the tenant's working set. That is the whole remaining argument, and it is
measured in the regime where our instrument is good (independent M10/M10b runs
agree to 0.3--4.4%).

Two further legs, both already in hand:

- **No calibration.** On AMD the working MBA cap is a knife edge: nominal
  28 GB/s leaves the victim at 12.44x, 24 GB/s drops it to 1.08x, and being 4%
  too generous buys nothing. W5.3's own words: *"a property of this streamer,
  this victim, this core count and this machine, and an operator has to find
  it."* A declaration is correct on every fill by construction. This is §3.5's
  *certainty* axis, now with hard numbers behind it.
- **H3.** Coherence elision is licensed only by knowing no writer exists, which a
  predictor cannot establish. Untouched by everything measured this week.

## The experiment that should run next

**The iso-protection cost curve on the fused tenant.** Fix a victim-protection
target (say V <= 1.05x). For a fused tenant, find the widest mask that still
meets it, with and without the stream label, and price that mask to the tenant.

The hypothesis, stated so it can fail: without the label the mask must be narrow
enough to exclude the stream's churn, which costs the tenant 37--41% once its
reused structure exceeds the mask; with the label the mask need only hold the
tenant's own structure, which M10b prices at ~0--2%. **The difference is the
mechanism's value, in the geometry the paper cares about, on the platform we can
reach.**

Design notes that must go into its pre-registration:

- **The proxy cannot carry the cost axis.** `clflushopt` flush-behind costs
  13--19% (M3, M9, P4 checks), which exceeds the ~12--17% it would save at a wide
  mask. So silicon must establish the **mechanism** --- via LLC miss and
  occupancy counters showing the tenant's structure retains residency once the
  stream stops allocating --- and gem5 supplies the **cost** with a free H2,
  bounding it **from above** (S1-1 of the red-team review).
- **Hit rate 0.5 only.** M8's accidental duplicate cell and the M11/M11b pair
  both put hit-rate-1.0 resolution at 16--18% run-to-run at n<=10; hit rate 0.5
  reproduces to 0.3--4.4%.
- **State the measured CoV and the implied n in the registration.** Four
  thresholds this week were set finer than the instrument resolves. Per the
  red-team review's process finding, no threshold should be chosen as a round
  number near the expected effect again.

## Priorities

1. **Iso-protection cost curve** (above). ~1 day, mos181, no blocked host.
2. **Rewrite the claim from cost asymmetry rather than necessity.** The abstract
   still leads on the old framing; write it once, after (1).
3. **Venue decision.** This has become a measurement-and-mechanism paper --- what
   admission control can and cannot buy, plus a new ISA ask --- rather than "a new
   memory type is necessary." Lead-only, open a week, alongside the W5.3 write-in
   and co-author contact.
4. **e2e gather: NO-GO for now.** 5--8 engineer-days for a *second* instance of
   the fused claim, when (1) produces the first *sound* instance in about a day.
5. **AMD host when convenient.** Diagnosis in
   `BROKER_OUTAGE_DIAGNOSIS_2026-08-26.md` rules us out as the cause; needs a
   power cycle or BMC. No longer gating.

## Status of the chain, for the record

| link | claim | status |
|---|---|---|
| L1 | the demand exists in shipped software | **stands** (RocksDB two-layer source exhibit) |
| L2 | there is a missing admission cell | **stands** (taxonomy) |
| L3 | harm follows allocation, not bytes | **qualified** --- dissociation holds; only 27% of harm is residency (M3b) |
| L4 | OS-enforceable, HW-implementable | **stands** (prototype + gem5, the latter bounding from above) |
| L5 | no deployed alternative protects the neighbour | **dead, both vendors** (W5.3) |

The paper does not need L5. It needs the cost-asymmetry claim, and that claim
needs experiment (1).
