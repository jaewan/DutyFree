# Pre-registration: is the AMD L2-resident harm back-invalidation, and what selects its two modes?

Registered **before** the run.

## Why

`AMD_NARROWMASK_OUTCOME_2026-08-30.md` addendum 1 found two things that the
campaign's model does not currently explain:

1. Under a co-running streamer the victim's **private** L2 hits go
   **25,643,357 -> 155**. The victim is on core 0 with a private 1 MiB L2; the
   aggressor is on cores 1--7. **Capacity cannot evict a private L2 from another
   core.**
2. An **L2-resident** victim (512 KB in 1 MiB) is harmed **bimodally**:
   0.94--1.09x with hits intact (99.8%), or 1.72--3.04x with hits partly lost
   (96.8%). `tab:h3sf`'s published **1.000x** is one mode of that distribution.

If the harm is back-invalidation from L3 shadow tags, it is **the H3 charge on a
machine we can reach** --- which is the opposite of the paper's current position
that no reachable snoop filter levies it. That is too important to leave resting
on six observations and a plausible story.

## Design: 2 x 2 x 2 factorial, n=20

| factor | levels | what it discriminates |
|---|---|---|
| **aggressor placement** | same-CCX (cores 1--7) vs **other-CCX** (cores 9--15) | L3-mediated vs global (fabric/memory) |
| **victim WSS** | **512 KB** (L2-resident) vs 4096 KB (exceeds L2) | back-invalidation is only unambiguous when the victim fits |
| **THP** | `never` vs `always` | the hypothesised mode selector: physical placement |

Plus a quiescent cell per (WSS, THP) = **12 conditions x 20 reps = 240 runs**,
~10 s each, about 40 minutes.

The victim binary has no hugepage flag, so THP is the only placement lever
available; a 512 KB victim under `THP=always` should sit inside a single 2 MiB
page and therefore have a *deterministic* L3 set mapping, where under `never` it
is 128 scattered 4 KB pages.

Fixed: victim `-c 0 -P -d 3 -W 1`, aggressor `-m wb_load -t 7 -N 2 -s 64`
(7 threads in both placements, so load is matched), platform **as found**
(`schedutil`, boost on) with `perf_event_paranoid=-1`. Core-0 frequency is
**recorded per run** rather than pinned, so frequency variation can be tested as
a confound instead of assumed away --- changing the governor would alter a shared
machine and would also change conditions relative to the published 1.000x.

## Registered predictions

**P1 --- back-invalidation exists.** For the L2-resident victim with a same-CCX
aggressor, median L2 hit rate **< 99.0%** (quiescent ~99.8%). Any *systematic*
loss of hits in a private L2 caused by a co-runner on other cores cannot be
capacity and is therefore back-invalidation or coherence probing.

**P2 --- it is L3-mediated.** median slowdown(same-CCX) >= **1.3x**
median slowdown(other-CCX), for the L2-resident victim.
**If the two placements are equal, the harm is global --- fabric or memory --- the
shadow-tag account is refuted, and H3 has no claim on it.** This is the
prediction that can most cleanly go against us.

**P3 --- THP selects the mode.** For the L2-resident same-CCX cell, the
interquartile range of slowdown under `THP=always` <= **50%** of the IQR under
`THP=never`. If not, **placement-via-THP is not the selector and the
mode-selecting variable remains unidentified** --- to be reported as unidentified,
not replaced with a new guess after the fact.

**Reported without a threshold:** the fraction of runs in each mode, classified
by hit rate (harmed if < 99.0%), per cell.

## Liveness assertions

1. Every run emits a `VICTIM` line; runs that do not are reported, not dropped.
2. **THP state is read back from sysfs into every record**, not assumed from the
   loop variable.
3. **The aggressor's cores are verified to be in the intended L3 domain** by
   reading `/sys/devices/system/cpu/cpuN/cache/index3/shared_cpu_list`, not
   inferred from core numbers.
4. Quiescent cells must record zero aggressor bandwidth.
5. Aggressor bandwidth must be comparable across placements; if the other-CCX
   aggressor cannot sustain the same rate, P2 is confounded by rate and is
   reported as such rather than as a placement effect.
6. Core-0 frequency recorded per run.

## What is deliberately not done

The platform is **not** frozen and the governor is **not** changed: this is a
shared host, and freezing would also move conditions away from the published
figure this experiment is trying to explain. Frequency is instead measured.
