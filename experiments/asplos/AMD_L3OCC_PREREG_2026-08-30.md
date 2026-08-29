# Pre-registration: a proper instrument for the AMD question --- L3 occupancy, not L2 counters

Registered **before** the run.

## Why this exists

Every AMD conclusion this campaign has drawn about the **L3** has been measured
with **L2** counters. That is the recurring root cause behind today's
corrections, stated plainly in the assessment: *the instrument does not measure
the quantity in the claim.* Two live examples:

- `AMD_NARROWMASK_OUTCOME` addendum 1 argued back-invalidation from the victim's
  private-L2 hits collapsing (25,643,357 -> 155). Suggestive, but an L2 counter
  cannot say whether the line left L3.
- The `512`\,KB control turned out to have a **quiescent** L2 hit rate ranging
  92.3--99.8\% with no aggressor at all, so at that size the L2 hit rate is
  placement noise and cannot carry the argument.

`resctrl` on this part exposes **`llc_occupancy`**, verified working (a probe
group on core 0 read 491,520 B). It measures the question directly.

## The discrimination

Sampling the victim's L3 occupancy *during* its run:

| observation | conclusion |
|---|---|
| occupancy **collapses** under the aggressor | the victim is **evicted from L3** --- capacity or rate harm |
| occupancy **holds** while L2 hits vanish | the victim is **back-invalidated from L2** while still L3-resident |
| occupancy holds **and** L2 hits hold, yet the victim is slow | the harm is **miss latency** on the path, neither eviction nor invalidation |

These are mutually exclusive and jointly cover the candidates, which is what the
L2-only instrument could not do.

## Design

Victim on core 0; aggressor 7 threads, `wb_load`, CXL node 2. Arms `quiescent` /
`same`-CCX (cores 1--7) / `other`-CCX (cores 9--15), at victim WSS **512 KB**
(fits the 1 MiB private L2) and **4096 KB** (does not). n=10, 60 runs.

Occupancy is sampled every 250 ms **during** the victim's run, warmup excluded,
and the **median** of in-run samples is the statistic. A before/after reading
would miss the transient the victim actually experiences, which is the whole
phenomenon.

## Registered predictions

**P1 --- the 4 MB case.** Victim L3 occupancy under `same` falls to <= **50%** of
its quiescent median. If it does, the 4 MB harm is L3 eviction and the
back-invalidation reading of addendum 1 is **withdrawn**. If occupancy holds
above 80% while L2 hits stay collapsed, back-invalidation is **supported**.

**P2 --- the 512 KB case.** For an L2-resident victim, quiescent L3 occupancy
should be small (the working set lives in L2). The registered question is whether
`same` still slows it: if it does **while** L3 occupancy is already near zero in
both arms, then neither L3 eviction nor L2 capacity explains it, and the residual
is on the **path**.

**P3 --- placement.** Occupancy loss under `same` exceeds that under `other`. If
`other`-CCX harms occupancy equally, the mechanism is not L3-local at all.

**No prediction is registered for which of the three outcomes P1 selects.** I
have argued both sides of this within one day --- first "the residual is latency",
then "it is back-invalidation" --- and a third guess would be worth nothing. The
instrument is the contribution here, not another hypothesis.

## Liveness assertions

1. `llc_occupancy` must be non-zero and vary across arms; a counter that reads a
   constant is broken, and a constant reading voids the run rather than becoming
   a finding.
2. Occupancy sample count recorded per run; a run with fewer than 4 in-run
   samples is reported, not averaged in.
3. The aggressor's core list is written into the monitoring group before each
   arm and its bandwidth recorded, so a placement change cannot silently become
   a rate change.
4. Quiescent arms must record zero aggressor bandwidth.
