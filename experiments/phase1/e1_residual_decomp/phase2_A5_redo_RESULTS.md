# Phase 2.2 — A5 redo (thread-matched, unthrottled) + occupancy-collapse test: RESULTS

Dated 2026-08-07. n=12, rep-interleaved, 15 arms/rep (quiescent + cxl_1..7t +
local_1..7t), same victim/CCX0 placement as A0-A6. `-R` throttle removed
entirely (the panel's identified hole in the original A5_local_bwm result);
the earlier draft's real bug (both arms literally using CXL due to a wrong
mode string) was caught in smoke-test review and fixed before this run --
see the file's own inline comment for the record.

## Bandwidth and tax vs thread count

| threads | CXL bw (GB/s) | CXL tax | local bw (GB/s) | local tax |
|---:|---:|---:|---:|---:|
| 1 | 12.431 | 2.963 | 43.401 | 4.149 |
| 2 | 20.288 | 6.109 | 44.514 | 9.645 |
| 3 | 20.651 | 18.261 | 45.789 | 12.878 |
| 4 | 23.053 | 21.497 | 45.323 | 15.024 |
| 5 | 23.910 | 22.083 | 45.437 | 15.442 |
| 6 | 23.985 | 21.166 | 45.489 | 15.580 |
| 7 | 24.135 | 20.251 | 45.602 | 17.137 |

**Cross-run validation**: these CXL numbers closely reproduce A6's original
independent sweep (t=1: 2.96 vs 2.92; t=2: 6.11 vs 6.40; t=3: 18.26 vs
18.04; t=5: 22.08 vs 21.82; t=7: 20.25 vs 20.01) -- different day, same
machine, same superlinear knee between 2 and 3 threads. The mechanism
finding is robust to re-measurement.

**New finding, not previously measured**: local DRAM single-thread
bandwidth is already 43.2-44.4 GB/s and stays **flat** through 7 threads
(45.6-45.6 GB/s at 7T -- only ~3% higher than 1T). Something on the local
path (plausibly the memory controller/channel) is already at or near its
throughput ceiling from a single AVX2-unrolled thread on this platform.
**Despite flat bandwidth, local's tax still climbs substantially with
thread count** (4.15x at 1T to 17.14x at 7T) -- bandwidth alone does not
predict local's tax any better than it predicts CXL's.

## The occupancy-collapse test: inconclusive, and the reason is itself informative

Per the panel's request: computed occupancy_est = BW x measured_idle_latency
/ 64B for every arm (CXL idle latency 401.8 ns, local idle latency 145.7 ns,
both directly measured this session via dependent pointer-chase, n=5,
tight and consistent -- see `PHASE2_AMD_FLUSHBEHIND_PREREGISTRATION.md`'s
sibling measurement). **The points do not collapse onto one curve.** At
occupancy ~100-104 (all seven local arms cluster here, since local's flat
bandwidth means occupancy barely moves with thread count under this
formula), tax ranges from 4.15 to 17.14 -- a huge spread at *matched*
occupancy by this measure. Comparing across memory types: `local_7t`
(occupancy=103.8, tax=17.14) sits at *lower* estimated occupancy than
`cxl_3t` (occupancy=129.7, tax=18.26) yet reaches comparable tax -- backwards
from what one universal occupancy-tax curve would predict.

**This is very likely a bad-proxy problem, not a refutation of the
occupancy hypothesis.** Local DRAM bandwidth being flat from 1 to 7 threads
is itself evidence that *something* on the local path is already queued/
saturated at 1 thread -- meaning true loaded service time for local is
almost certainly far higher than the 145.7 ns *idle* (unloaded,
single-thread, no contention) latency used here. Idle latency is a
defensible floor for CXL (whose bandwidth clearly keeps scaling with thread
count, so per-request contention is more gradual), but it is very likely a
severe underestimate for local specifically, precisely because local
saturates so fast. Correcting this would need a genuine loaded-latency
probe for local DRAM under contention -- not attempted here (the natural
approach, a same-CCX dependent-chase probe on a spare core, doesn't exist
at n=7 threads, since all 8 CCX0 cores are already occupied by victim+
aggressor).

## What this does and does not settle

**Settled, reinforced**: this is now the third independent measurement
(A2 occupancy-intact, A4 lookups-only tax, A6/this-redo's superlinear knee)
arguing that CXL-side tax is a queueing/occupancy phenomenon, not a raw-
bandwidth or LLC-capacity one. **Newly extended, not previously known**:
the *same qualitative pattern* -- tax climbing while bandwidth is flat --
now also appears on the **local** path, suggesting queueing/occupancy
(as opposed to raw bytes moved) may be the right general framing for *both*
memory types, not a CXL-specific story.

**Not settled**: whether CXL and local share literally the *same* bottleneck
resource (one universal occupancy curve) or two *different* queueing
structures with different capacities that both happen to produce
occupancy-like tax curves. The idle-latency-based test in this pass cannot
distinguish these -- it is inconclusive, not a refutation, for the specific
reason given above. **This changes the sentence the paper can write**: not
"CXL is mechanistically special" (the panel's alternative to reject) and
not "one universal occupancy curve, CXL's role is just to force deployments
into the saturating regime" (the panel's preferred collapse) -- the honest
current answer is "both paths show occupancy-like behavior; whether they
share one mechanism or two is open pending a loaded-latency measurement this
pass could not obtain."
