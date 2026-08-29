# AMD outcome: the way-partitioning refutation survives an aimed mask --- and the residual is a *latency* residual, not a capacity one

Pre-registration `AMD_NARROWMASK_PREREG_2026-08-30.md` (`24664e4`). `broker`
(moscxl) returned after nine days down. n=6, 36/36 records mask-enforced.

## Result

Victim on core 0, aggressor 7 threads on cores 1--7, same CCX (16 MiB L3, 16 CAT
ways), aggressor streaming from the CXL node.

| arm | agg ways | victim L2 miss | cyc/access | tax | removed | agg GB/s |
|---|--:|--:|--:|--:|--:|--:|
| quiescent | --- | 86.51% | 55.39 | 1.00x | --- | --- |
| `wb` | 16 | **100.00%** | 1530.05 | 27.62x | --- | 24.81 |
| `cat8` (**published split**) | 8 | **100.00%** | 710.33 | 12.82x | 55.6% | 24.79 |
| `cat4` | 4 | 89.41% | 570.56 | 10.30x | 65.1% | 24.65 |
| `cat2` | 2 | 89.36% | 566.94 | 10.23x | 65.3% | 24.66 |
| `cat1` | **1** | 89.19% | 569.74 | 10.28x | **65.1%** | 24.67 |

**Registered verdict: 65.1% removed --- the 50--80% "partial" band.** The caption is
restated quantitatively rather than kept or withdrawn.

## The finding: aiming the mask does not help, and now we know why

Narrowing the aggressor from 8 ways to 4 buys 10 points. From 4 to 2 to 1 buys
**nothing** (65.1 / 65.3 / 65.1%). A capacity mask that could reach this harm
would keep improving as it tightened.

The victim's L2 miss rate explains the plateau:

| | miss rate | cyc per **miss** |
|---|--:|--:|
| quiescent | 86.51% | **64.0** |
| `wb` | 100.00% | 1530.0 |
| `cat1` | 89.19% | **638.8** |

**CAT restores the victim's residency to within 2.7 points of quiescent and the
victim is still 10.3x slower, because each surviving miss costs 10.0x more to
service.** Once the mask has restored residency --- which it has, by 4 ways ---
there is nothing left for a *capacity* mechanism to fix. The residual lives
entirely in the miss path: the fabric carrying the aggressor's 24.7 GB/s.

This is a direct decomposition of `E3`'s "AMD's harm is rate-class, not
capacity-class", which until now was an inference from CAT under-performing.

Aggressor bandwidth is flat to **0.63%** across every arm, so the mask constrains
residency and not rate --- the failure mode that would have produced the right
answer for the wrong reason.

## What the caption may now say --- stronger than the current text

> On the AMD part a way mask cannot reach the harm, and not for want of aiming:
> confining the streaming aggressor from 8 of 16 ways down to **1** moves the
> residual only from 12.8x to 10.3x and is flat below four ways. The mask does
> restore the victim's cache residency (L2 miss 89.2% against 86.5% quiescent);
> what it cannot restore is miss *latency*, which remains 10.0x inflated at every
> mask width.

## Reproduction: the ratio holds, the magnitude does not

| | published | re-measured |
|---|--:|--:|
| `wb` slowdown | 19.89x / 20.55x | **27.62x** |
| removed at 8/8 | 55% | **55.6%** |

The **fraction removed reproduces almost exactly**; the **absolute tax does
not**. The mechanism ratio survived a host rebuild; the magnitude did not. This
is consistent with `AMD_PLATFORM_STATE_PROVENANCE_2026-08-21.md`: the published
runs were taken on an unfrozen platform, and this host is in that same unfrozen
state (`schedutil`, boost on) after being rebuilt. **Per S6.6 the paper should
say the absolute AMD magnitudes are not reproducible while its argument is.**

A second reason the published 8/8 figure was a weak place to rest the claim:
`wb` and `cat8` both pin the victim at **exactly 100.00%** L2 miss --- a saturated
instrument. Any comparison between those two arms measures the cost of misses,
not their number.

## Two follow-ons attempted, one answered and one blocked

**(a) Module-free non-allocation at matched rate --- ANSWERED, negative.** The
published WC row is not rate-matched (13.8 vs 24.1 GB/s), so its 0.99x cannot
separate non-allocation from moving 43% fewer bytes. Three write-back-memory
modes all sustain ~25 GB/s:

| mode | victim L2 miss | tax | GB/s |
|---|--:|--:|--:|
| `wb_load` | 100.00% | 27.6x | 24.8 |
| `wb_prefetchnta` | **100.00%** | 27.4x | 24.7 |
| `wb_ntdqa` | **100.00%** | 27.4x | 25.2 |

`prefetchnta` does **not** avoid L3 allocation on Zen 4c, and `wb_ntdqa` behaves
as the architecture requires (`movntdqa` on write-back memory is an ordinary
load) --- included as a null control so that a null would look like one.
**There is no module-free non-allocating arm on this hardware.**

**(b) The real WC path --- BLOCKED by machine configuration.** `wc_ntdqa` mmaps
`/dev/cxl_wc` from a kernel module that is itself a documented reconstruction.
Two independent blockers:

1. The CXL window `[0x18400000000, 0x1c3ffffffff)` is **online System RAM** on
   this rebuilt host. **37 of 129 memory blocks refuse to offline** (unmovable
   kernel pages).
2. More fundamentally, **offlining does not remove a block from the iomem
   resource tree**. `/proc/iomem` still reports the window as System RAM, so the
   module's `region_intersects` guard can never be satisfied by offlining alone.

The module refused to load, twice, exactly as designed --- its guard requires the
range be *provably disjoint* from System RAM, because a WC alias of
kernel-write-back memory is an architectural hazard, not merely a bad
measurement. **Defence in depth worked: the guard was the backstop that made the
attempt safe to make at all.**

Freeing the window needs the memory taken out of system-ram mode: `daxctl` is not
installed, `cxl list -R` reports no regions, and there is no dax device, so the
remaining route is a **boot-time** `memmap=`/soft-reserve change. That is a
reboot of a shared machine and was not done.

**Consequence for the paper: the WC row cannot currently be rate-matched on
available hardware, so the AMD data refutes way partitioning without yet
demonstrating that non-allocation succeeds where it fails.** That distinction
should be stated rather than left for a referee.

## Machine state

Fully restored and verified: node2 back to 264,213,200 kB, **0** offline blocks,
module not loaded, no resctrl groups, no stray aggressors, load ~0.3. The only
persistent change is `perf_event_paranoid` 4 -> -1, required for the victim's PMU
and matching the frozen protocol the paper already claims. Governor and boost
were deliberately left as found so the reproduction matched the published
conditions.


---

# Addendum 1 --- 2026-08-30: my "the residual is latency" reading is incomplete, and one paper claim looks unstable

Written after stress-testing my own interpretation. **Two corrections and one
open question, none of which the main text above anticipated.**

## 1. The dominant effect under `wb` is that the victim's private-L2 hits *vanish*

Raw counts, victim 4 MB:

| | L2 hits | L2 misses | hit rate |
|---|--:|--:|--:|
| quiescent | 25,643,357 | 140,591,463 | 15.4% |
| under `wb` | **155** | 6,030,663 | **0.003%** |

Not degraded --- **gone**. The victim runs on core 0; its L2 is **private** (1 MiB)
and the aggressor runs on cores 1--7. **A co-runner on other cores cannot evict a
private L2 by capacity.** The only cross-core mechanisms that can are
back-invalidation from L3 shadow tags / probe filter, or coherence probes. Zen's
L3 is a victim cache with shadow tags tracking L2 contents, so shadow-tag
pressure forcing L2 back-invalidation is the leading explanation.

**That is the H3 charge --- snoop-filter enrolment --- and this is a machine we can
reach.**

## 2. Consequences for two things I asserted earlier today

**"CAT restores the victim's residency" was loose.** It rests on an **L2** counter
while CAT partitions **L3**. What CAT restores is the private-L2 hit rate, which
is a back-invalidation signal, not an L3-residency one. The better-supported
reading is **two components** --- back-invalidation (largely mitigated by CAT) and
miss-service latency (not mitigated at any mask width) --- but I have only L2
counters, so the attribution is **suggestive, not established**.

**My recommendation to cut H3 is withdrawn.** I argued H3 "removes a charge no
reachable machine levies." Bergamo may levy exactly that charge. That
recommendation should not be acted on until this is tested properly.

## 3. The L2-resident control is bimodal, which unsettles a paper claim

`tab:h3sf`'s caption states private-L2-resident victims read **1.000x** on
Bergamo --- load-bearing, because it is what makes H3 a capability claim rather
than a measured benefit. Re-measured with a 512 KB victim in a 1 MiB private L2:

| rep | slowdown | L2 hit rate |
|---|--:|--:|
| (single earlier run) | **3.04x** | 93.49% |
| 1 | 2.03x | 96.84% |
| 2 | 1.73x | 96.83% |
| 3 | 1.72x | 96.84% |
| 4 | **0.94x** | 99.83% |
| 5 | **1.09x** | 99.79% |

**Bimodal**: an unharmed mode at ~1.0x with hits intact (99.8%), and a harmed
mode at 1.7--3.0x with hits partly lost (96.8%). The published **1.000x is one
mode of a bimodal distribution**, not a stable result --- and in the harmed mode an
L2-resident victim loses private-L2 hits to a co-runner on other cores, which
capacity cannot explain.

**I am not claiming the paper is wrong.** I am claiming the measurement is
unstable and that a single value does not characterise it. This project has been
bitten by bimodality before (`E1a`'s tenant column was voided for it), and the
correct response is a designed experiment, not a louder number.

## What this calls for

1. **Do not cut H3** on the current argument.
2. A proper Bergamo back-invalidation experiment: L2-resident victim, n>=12,
   frozen platform, with the mode-selecting variable identified (physical page
   placement is the first suspect). L3/probe-filter counters if obtainable.
3. Until then `tab:h3sf`'s "1.000x on Bergamo" should carry the spread, not the
   point.
