# M12 pre-registration: the positive case. Does the label buy the tenant anything at a mask that already protects the neighbour?

Written 2026-08-28, **before any M12 data exists**. This is the first experiment
in the campaign designed to find something *for* the mechanism, so it is
registered with the same hostility as the ones that went against it, and the
outcome that kills the positive case is written down first.

## The claim being tested

`STRATEGIC_ASSESSMENT_2026-08-28.md` reduced the surviving case to **cost
asymmetry**: shipped QoS protects a neighbour by confining the tenant, so its
price scales with what the tenant keeps in cache, while non-allocation removes
the stream's residency without touching the tenant's own data.

That has never been measured in the one configuration where it matters: **a mask
wide enough to protect the neighbour, where the tenant's own stream is still
evicting the tenant's own table.** M9 looked at 20 ways (no mask) and 4 ways
(64 MiB, 256 MiB table) and found no benefit --- but at both of those points the
table's fate was already decided: at 20 ways nothing was squeezed, and at 4 ways
the table could not fit no matter what the stream did. **The predicted sweet spot
is table ~ mask**, and M10 puts it there: at an 8-way (128 MiB) mask the penalty
is 1.02x with a 64 MiB table and 1.12--1.16x with a 128 MiB one.

## Why 8 ways is the right mask

Eight of twenty ways leaves the victim **twelve ways = 192 MiB**, and the victim's
working set is 170 MB (~162 MiB). So an 8-way mask on the tenant is a mask that
*can* protect the neighbour --- pass B tests that it does. That makes the
comparison an **iso-protection** one: at a mask that meets the neighbour's
target, what does the label buy the tenant?

## Design

Two passes. mos181. `--hit-rate 0.5` **only** --- `tab:fused`'s operating point and
the regime where our instrument is good (below).

### Pass A --- the tenant's own cost and residency, no victim

- Fixed: `--mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g
  --cpu-list 32-47 --morsel 1m --warmups 2 --reps 1 --threads 16 --hit-rate 0.5`.
- `mask` in {`none` (20 ways), `b8` (8 ways = 128 MiB, `setup_b 8 32-47`)}.
- `table` in {33554432 (32 MiB), 67108864 (64), 134217728 (128)} --- ratios
  0.25 / 0.5 / **1.0** against the mask. All exact powers of two x 16 B, so
  `HOT_TABLE_ROUNDED` must never fire and the runner aborts if it does.
- `stream` in {`retain` (`--flush-distance 0`), `flush` (`--flush-distance
  262144`)}.
- 12 cells, **n=10**, 120 runs. Interleaved with a per-rep rotation, schemata and
  instantiated table size captured per record, per-record JSON validation, A6.19,
  resctrl torn down on every exit path.
- **Second metric, and the primary one: `llc_occupancy`.** CMT is available on
  this host (`/sys/fs/resctrl/info/L3_MON/mon_features` lists `llc_occupancy`,
  512 RMIDs). For every `b8` run we sample F's group occupancy at the end of the
  measured window. This is the mechanism instrument, and it exists because the
  cost axis cannot carry the claim (next section).

### Pass B --- the neighbour, to establish the iso-protection premise

- V = `pointer_chase --cpu 8 --node 0 --wss 178257920 --run-sec 1 --trials 6`.
- Arms: `Vnone`, `Vwide` (V alone under the mask, for the partitioning-cost
  control), and V co-running with F at {`none`, `b8`} x {`retain`, `flush`},
  F at the 128 MiB table.
- `b8` here uses `setup_c 8 32-47 8`, which gives F eight ways and **enforces the
  complementary twelve to V**. M11b found `setup_b`/`setup_c` indistinguishable
  (p=0.443), so the asymmetry with pass A is noted rather than treated as free.
- 6 arms, **n=10**, 60 runs, exact position balance across reps.
- **F's liveness is recorded per run** --- its stderr is kept and the `HOT_TABLE`
  and `HOT_TABLE_WARMED` lines are asserted present. M6b did not do this, and the
  AMD `n=6` WC arm (which moved 0.0108 GB/s while reporting no harm) is why it
  now matters.

## Variance basis and the sample size it implies

Recorded because four of this week's thresholds were set finer than the
instrument resolves, and the red-team review made stating this mandatory.

Across all 32 M10/M10b cells at hit rate 0.5: **CoV median 0.90%, p90 6.9%,
worst 8.0%**. Two-sample, alpha 0.05, power 0.80, at the worst-case 8.0%:

| effect to detect | n required per cell |
|--:|--:|
| 5% | 40 |
| 8% | 16 |
| **12%** | **7** |
| 20% | 3 |

**n=10 resolves an 8% difference at the worst cell's variance.** The predicted
effect (M10's 12--16% at table = mask) is comfortably above that. No threshold
below 8% is registered anywhere in this document.

## The cost axis cannot carry this claim, and that is registered up front

The flush-behind proxy costs the tenant 13--19% by itself (M3, and M9's P4 check
measured +12.9% and +13.5% at 20 ways). The effect we are looking for is
12--16%. **So even a perfectly working label would show roughly zero net benefit
in cyc/access through this proxy**, and a null on cost is uninformative.

Hence:
- **Primary metric: `llc_occupancy`.** A working label should show F's occupancy
  fall toward its table size while F's cost does not rise by more than the
  proxy's own charge. Occupancy down *and* cost flat is the signature of useless
  residency removed; occupancy down *and* cost up by more than the proxy is the
  signature of the label removing residency the tenant actually wanted.
- **Cost is secondary and interpreted only as a difference of differences** ---
  the proxy's charge at table 32 MiB (where there is nothing to win) subtracted
  from its charge at table 128 MiB. M9 showed this estimator is confounded by how
  much slack the workload leaves to hide flush work, so it is reported with that
  caveat and is not the basis of any conclusion.
- **A zero-cost H2 is a gem5 question**, and gem5 bounds it **from above**
  (red-team S1-1).

## Registered predictions

Let `Occ(mask, table, stream)` be F's LLC occupancy and `C(...)` its cyc/access.

- **P1 (mechanism, primary).** Under `b8`, `Occ(retain)` is close to the mask's
  128 MiB at every table size, and `Occ(flush)` is at least **25% lower** at the
  32 MiB table. Rationale: with a small table almost all of F's residency is
  stream, so removing the stream's allocation must be visible as occupancy.
- **P2 (the sweet spot).** The label's cost benefit, measured as the
  difference-of-differences `[C(b8,128,retain) − C(b8,128,flush)] −
  [C(b8,32,retain) − C(b8,32,flush)]`, is **>= +8%** of the 128 MiB retain
  baseline. This is the actual positive claim: the label helps most where the
  table just fails to coexist with the stream.
- **P3 (the honest null, expected).** Net cost `C(b8,128,flush)` is **not** lower
  than `C(b8,128,retain)`, because the proxy's 13% charge cancels the 12--16%
  it recovers. Registering this as *expected* so that its occurrence is not
  later reported as a discovery.
- **P4 (iso-protection premise, pass B).** V under `b8` co-running with F reaches
  **<= 1.05x** at the 128 MiB table, with both stream conditions. If this fails,
  8 ways does not protect the neighbour and the whole iso-protection framing
  needs a different mask width.
- **P5 (partitioning's cost to V).** `Vwide` (V alone, confined to twelve ways) is
  within **5%** of `Vnone`. V's 162 MiB fits 192 MiB, so confinement should cost
  V nothing; if it does not, pass B's V numbers are measuring V's own confinement
  rather than F's interference.

## Registered consequences

- **P1 and P2 hold** --- the positive case has its first sound instance on
  silicon. §3 gains a real exhibit: at a mask that protects the neighbour, the
  tenant's own stream costs it 12--16% and only an object-scoped label removes
  that without widening the mask. This is what the paper should be built on.
- **P1 holds, P2 fails** --- the label demonstrably removes stream residency but
  that residency was not costing the tenant anything at this mask. The
  cost-asymmetry claim then has **no silicon instance**, and the paper must rest
  it on gem5 (bounding from above) and say so plainly. This is a real possible
  outcome and it is the one I would bet on second.
- **P1 fails** --- the proxy is not removing residency the way we believe, which
  invalidates M3, M5, M9 and M6's flush arms as well. That would be the largest
  single finding of the campaign and it gets its own investigation before
  anything else proceeds.
- **P4 fails** --- re-run pass A at the widest mask that does protect V, and
  report that the iso-protection window is narrower than we thought.
- **P5 fails** --- pass B is void for attributing V's harm to F.

## What this cannot show

Intel EMR only, one benchmark, one fact size (1 GiB), one hit rate, one victim
working set, one mask width in the pass that matters. The label is a software
proxy with a known charge, so **no net-cost claim for the real memory type can
come out of this experiment** --- only the mechanism, and the size of the harm the
type would be removing. It also says nothing about AMD, whose harm is fill-path
rather than capacity.
