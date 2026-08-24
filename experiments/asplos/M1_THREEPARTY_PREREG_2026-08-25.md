# M1 pre-registration: does a *fused tenant* harm a neighbour at all?

Written **before any measurement**. This is the panel's own registered falsifier
for the three-party reframing, and it decides which paper exists.

## Why this first, before the 3–5 day joint campaign

The reframing's middle row — *"V vs. fused tenant: harm is Branch-A physics"* —
has one unmeasured premise: that a fused tenant's **self-paced** stream is fast
enough to harm a neighbour. Computed from committed data before registering
this, it is not obvious that it is:

| streamer | GB/s | lines/s | LLC turnovers/s (320 MiB) |
|---|--:|--:|--:|
| fused tenant, 1 worker | 0.34 | 5.3 M | 1.0 |
| fused tenant, 8 workers | 2.70 | 42.2 M | 8.0 |
| **fused tenant, 16 workers** | **5.40** | **84.4 M** | **16.1** |
| W5.3's aggressor (the one that harmed) | 23.70 | 370.3 M | 70.6 |

A fused worker streams **0.335–0.340 GB/s** (n=36, A4+A6 data), because its own
probe paces the loop. At the paper's 16-worker configuration that is **4.4×
below** the rate that produced W5.3's harm.

Directly relevant counter-evidence already in hand: on AMD at **0.94 GB/s** with
the streamer holding **15.9 of 16 MiB** of L3, the victim read **exactly
1.000×** — *"the harm disappears… levied on the rate and not on the footprint"*
(`W5.3_L5_EVIDENCE`). If Intel behaves similarly at low rate, the fused tenant
may be harmless to neighbours and the three-party scenario does not exist.

Running the 3–5 day joint campaign before settling this would be the mistake
this project keeps making. **Cheapest hostile configuration first.**

## Arms

Host mos181. Victim `pointer_chase` (dependent loads, MLP 1), **cpu 8**, node 0,
WSS 4 MiB. Fused tenant = `cxl_join_bench --mode morsel` at the campaign
operating point (fact 256 MiB on CXL node 2, hot table 256 MiB instantiated,
morsel 1 MiB), workers pinned in **32–47**. All on node 0, one L3 domain.

| arm | co-runner |
|---|---|
| **V** | none (baseline) |
| **V+F1** | fused tenant, 1 worker |
| **V+F8** | fused tenant, 8 workers |
| **V+F16** | fused tenant, 16 workers |
| **V+STREAM** | `stream_wb`, 8 threads — **positive control** |

n=6 per arm, arm order rotated per rep so each arm occupies each position an
equal number of times.

## Metric

Victim `cycles_per_load`, median over its trials. Harm = arm median / V median.

## Pre-registered readings

| outcome | verdict |
|---|---|
| **V+F16 harm < 1.15×** | **The three-party containment scenario is moot.** A fused tenant does not harm neighbours, so there is nothing for a label to protect them from, and the paper falls back to: knobs work, streams are free, the expressibility gap has software demand evidence but **no measured victim in any configuration**. |
| V+F16 harm ≥ 1.15× | the scenario exists; the joint campaign (masks swept, joint endpoints, flush-behind-on-F arm) is justified and becomes the paper's centrepiece |
| 1.05–1.15× | report the curve; do not claim the scenario without the joint campaign showing containment actually helps V |

**Instrument falsifier, and it is not optional.** If **V+STREAM** does not itself
show clear harm (≥1.5×), then this victim/host/geometry cannot detect neighbour
harm at all, and **every other arm here is void** — a null from V+F16 would then
say nothing about fused tenants. The positive control is checked first and the
fused arms are only read if it passes.

**Registered secondary:** the harm-vs-worker-count curve. F's stream rate scales
with workers, so if harm appears only at 16 the scenario is real but narrow, and
the paper must state the worker count at which it turns on.

## Out of scope

CAT masks (that is the joint campaign, and only justified if this passes);
H2/flush-behind arms; any change to either binary; AMD (broker is down).
