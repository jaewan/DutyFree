# G-probe outcome: the kill switch fires on Intel SPR

**Date:** 2026-08-23 · **Hosts:** mos182 (Xeon 8462Y+, SPR), moscxl (EPYC 9754, Bergamo)
**Artifacts:** `artifacts/probe_mos182_matrix.jsonl`, `artifacts/probe_mos182_cat_control.jsonl`, `artifacts/probe_moscxl.jsonl`
**Runners:** `scripts/run_probe.py`, `scripts/run_cat_control.py`, `scripts/run_probe_moscxl.py`

## Verdict

`OLTP_INDEX_DESIGN.md` pre-registered G-probe as a zero-code kill switch with
its interpretation fixed in advance:

> If the residual is small, the design's central claim is false on silicon and
> this document is abandoned before Masstree is written. That is the point of
> running it first.

**The residual is small. On mos182 the largest co-run tax observed at any
working set, in any arm, is 1.065×.** At the operating point the design
actually depends on — an L2-resident victim — it is **1.000×**, with the
victim's L2 miss rate pinned at 0.00% while a co-resident streamer holds
41 MiB of the 60 MiB LLC and drives the victim's LLC occupancy to 0.1 MiB.

The design is abandoned as written. Masstree is not to be built for this
purpose. What survives, and what this costs the paper, is in §6.

This is a null on silicon, not a null from a broken instrument. §3 is the
evidence for that, and it is the part of this document that should be attacked
first if anyone wants to overturn the verdict.

## 1. What the design needed to be true

The OLTP-index victim was derived from the gem5 mechanism decomposition, in
which capacity displacement is the minority charge (1.369×) and
snoop-filter back-invalidation of the victim's **private** L1/L2 is the
majority (2.501× total). The whole point of choosing an index probe whose hot
set sits in the private L2 was that **CAT cannot defend a private cache**: a
back-invalidation is an invalidation, not an allocation, so no way-partitioning
at any level prevents it. That is what would have made the residual
CAT-irrecoverable and the corner unoccupied (L5).

That argument requires back-invalidation of the private L2 to actually happen
on the target silicon. It is the single load-bearing assumption, and it is
directly measurable without writing an index at all — which is why the probe
was placed ahead of everything else.

## 2. mos182 — the arm matrix

`victim -P` (random pointer chase, 64 B nodes on a Fisher–Yates Hamiltonian
cycle) on core 32; streamer `aggressor -m wb_load -t 8` on cores 33–40 (+SMT),
same socket, same L3 domain. 3 reps, all 60 arm-runs valid, `l2_counters=ok`
throughout. Tax is rep-paired against the `quiescent` arm **at the same working
set**, because the quiescent cost of a chase changes with footprint.

| ws (KB) | arm | cyc/access | tax | L2 miss % | victim LLC occ | streamer LLC occ | GB/s |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1024 | quiescent | 20.43 | 1.000 | 0.01 | 4.8 | 0.9 | — |
| 1024 | WB_cxl | 20.42 | **1.000** | 0.01 | 0.1 | 39.2 | 23.9 |
| 1024 | WB_local | 20.73 | 1.015 | 0.51 | 0.1 | 39.4 | 23.9 |
| 1024 | WB_cxl_CAT12 | 20.73 | 1.015 | 0.51 | 1.9 | 8.2 | 23.6 |
| 1024 | WB_cxl_CAT1 | 20.42 | 1.000 | 0.00 | 1.4 | 34.9 | 23.9 |
| 2048 | quiescent | 41.51 | 1.000 | 31.94 | 4.9 | 1.0 | — |
| 2048 | WB_cxl | 38.33 | 0.923 | 27.43 | 0.3 | 43.0 | 23.9 |
| 2048 | WB_local | 41.40 | 0.997 | 32.49 | 0.2 | 42.7 | 23.9 |
| 4096 | quiescent | 83.90 | 1.000 | 98.69 | 11.7 | 1.5 | — |
| 4096 | WB_cxl | 82.62 | 0.985 | 98.81 | 2.3 | 49.4 | 23.8 |
| 4096 | WB_local | 82.29 | 0.981 | 98.28 | 2.1 | 50.2 | 23.8 |
| 16384 | quiescent | 95.01 | 1.000 | 100.00 | 26.2 | 0.7 | — |
| 16384 | WB_cxl | 101.18 | **1.065** | 100.00 | 14.4 | 41.0 | 23.7 |
| 16384 | WB_local | 100.49 | 1.058 | 100.00 | 14.7 | 41.3 | 23.7 |

Reps are extremely tight (e.g. ws=16384 `WB_cxl`: 101.2 / 101.2 / 101.2).

The decisive cell is **ws=1024**. The victim is L2-resident. The streamer takes
its LLC occupancy from 4.8 MiB to 0.1 MiB — its L3 lines are being evicted
essentially completely — and the victim's L2 miss rate stays at **0.00%** with
`cyc_per_access` bit-identical at 20.42. **The victim's L3 lines are destroyed
and its private L2 copies survive untouched.** That is a direct measurement of
the absence of back-invalidation, not an inference from a small ratio.

`WB_local` matters as a control: on this host 8 cores pull ~24 GB/s from node 1
and node 2 alike, so bandwidth is matched and "CXL" is separated from
"bandwidth." Both are null. The effect is absent for reasons that have nothing
to do with where the stream came from.

## 3. Why this is a real null and not a dead instrument

An invariant reading across arms is equally consistent with an instrument that
cannot see co-run pressure. Two independent checks say it can.

**(a) The working-set sweep.** The same binary, same counters, produces a
textbook L2 capacity curve — 0.00% miss at 128–1024 KB, 4.27% at 1536, 30.17%
at 2048, 99.29% at 4096, 100% at 32768 KB, with cyc/access rising 16.0 → 101.9.
An instrument blind to the memory system does not produce that.

**(b) The CAT arms move, hugely.** `WB_cxl_CAT1` confines the victim to 1 of 15
ways (4 MiB) and reads 1.117× / 1.900× / 2.823× at ws=2048/4096/16384. The
victim is strongly capacity-sensitive and `cyc_per_access` tracks it cleanly:
95 cyc ≈ 34 ns (LLC hit) → 268 cyc ≈ 96 ns (DRAM), against a measured node-1
DRAM latency of 121.6 ns. The instrument has ample dynamic range; the streamer
simply does not use it.

### 3.1 The CAT control — and a number that must not be misquoted

`WB_cxl_CAT1`'s 2.823× is **not** a co-run tax and must never be quoted as one.
That arm holds a 1-way mask while the `quiescent` baseline holds all 15, so the
ratio folds CAT capacity starvation together with whatever the streamer does.
`run_cat_control.py` runs the missing cell — victim on the 1-way mask with **no
streamer** — to separate them (3 reps, all valid):

| ws (KB) | quiescent | CAT1, no streamer | CAT1 + streamer | CAT alone | **co-run on the starved victim** |
|---:|---:|---:|---:|---:|---:|
| 4096 | 83.37 | 159.79 | 157.41 | 1.917× | **0.985×** |
| 16384 | 95.00 | 308.44 | 270.65 | 3.247× | **0.878×** |

The entire CAT1 effect is CAT starvation. Adding a 23.9 GB/s streamer to an
already-starved victim makes it **faster** — most plausibly uncore-frequency
scaling under load, which is a known effect at this magnitude. Either way it is
the opposite sign from the one the design needed.

So across every condition tested on mos182: L2-resident + streamer = 1.000×,
LLC-resident + streamer = 1.065×, CAT-starved + streamer = 0.878×. **No arm
shows a co-run tax above 1.065×.**

## 4. Reconciliation

### 4.1 With gem5

The gem5 back-invalidation charge is real *for the configuration it was
measured in*, and that configuration was deliberately chosen to make the
mechanism visible. `H3_IMPL_SPEC.md:384` says so in as many words: the pressure
arm is sized "**deliberately far smaller than the victim's read-shared
footprint so SF capacity pressure and back-invalidation are visible**." That is
legitimate mechanism work and it is not the error.

The error would be transferring that number to silicon as a prediction. The
geometry does not survive the trip:

| | SF entries | aggregate private L2 | SF : L2 coverage | LLC : L2 |
|---|---:|---:|---:|---:|
| gem5 H2+H3 runs (`SETS=8192 WAYS=8`) | 65,536 | 2 × 2 MiB = 65,536 lines | **1.0×** | 5 MiB : 4 MiB = **1.25 : 1** |
| mos182 (SPR) | — | 32 × 2 MiB | — | 60 MiB : 2 MiB = **30 : 1** |
| moscxl (Bergamo) | — | 8 × 1 MiB | — | 16 MiB : 1 MiB = **16 : 1** |

At exactly 1.0× coverage and 8-way associativity, set conflicts force
back-invalidation continuously even when total occupancy would fit. Shipping
parts size snoop filters at a multiple of aggregate private capacity precisely
so that does not happen. The gem5 result is the response of a snoop filter
provisioned at parity; mos182 is a part where the LLC alone is 30× the victim's
private L2.

**This does not invalidate the gem5 decomposition as a mechanism study.** It
does mean the 2.501× may not be presented as a quantity a reader should expect
on a current Intel server part, and any text that implies otherwise needs to
change.

### 4.2 With the existing AMD CAT-residual

The probe does **not** contradict the project's AMD CAT-residual. That result
was measured with the victim sized to 4× the private L2 (exp41) — i.e.
deliberately *out* of L2, an LLC-resident victim in a 16 MiB CCX. This probe's
null is specifically about **L2-resident** victims. The two measure different
operating points and both can hold.

What the probe removes is the assumption that the residual would *survive* being
moved into the private L2. It does not, on SPR. (Per the standing δ embargo, no
attribution of that residual between H2 and H3 is made or implied here.)

## 5. moscxl — the harsh-capacity replication

*(In flight at time of writing; this section is completed when
`artifacts/probe_moscxl.jsonl` lands. Preliminary single-rep smoke below.)*

mos182 alone cannot distinguish "SPR does not back-invalidate" from "shipping
server LLCs do not back-invalidate," and those are very different claims.
moscxl is the harsher geometry (16:1 vs 30:1, 7 streaming cores against a
16 MiB L3 at 1 MiB/way) and is the place the effect is most likely to appear.
This is not a rescue attempt: the mos182 verdict above stands unconditionally
regardless of what moscxl returns.

Single-rep smoke at ws=256 KB (L2-resident), all six arms:

| arm | cyc/access | L2 miss % | victim occ | streamer occ | GB/s |
|---|---:|---:|---:|---:|---:|
| quiescent | 14.11 | 0.02 | 0.0 | 0.7 | — |
| WB_local | 14.45 | 0.03 | 0.0 | **16.0** | 24.7 |
| WB_cxl | 14.48 | 0.04 | 0.0 | **16.0** | 24.7 |
| WB_local_CAT12 | 14.25 | 0.02 | 0.1 | 4.1 | 24.5 |
| WB_local_CAT1 | 14.35 | 0.02 | 0.1 | 15.0 | 24.7 |
| CAT1_nostream | 14.11 | 0.02 | 0.0 | 0.8 | — |

The streamer holds **the entire 16 MiB L3** and the L2-resident victim moves by
2%. Note that Zen's L3 is a victim cache, so an L2-resident victim has almost
no L3 footprint to lose in the first place — the near-zero victim occupancy is
expected here and is not the streamer evicting anything.

## 6. Consequences

**Dead:** the OLTP-index headline as specified. The victim was chosen precisely
because its hot set is private-L2-resident and therefore CAT-undefendable; that
property is worth nothing if the co-runner cannot reach the private L2. G1, G2,
G3, G4, G5 and G6 are all moot — they were gates on a victim that has no tax to
gate. Masstree is not built.

**Also dead:** G6, which was the strongest discriminator in the design. It
predicted the private-cache charge would survive iso-absolute capacity
neutralization and be *larger* on mos182's smaller snoop filter. There is no
charge to neutralize.

**Alive:**
- The **admission-gate inversion** finding is untouched and arguably
  strengthened. The old CAT capacity-sensitivity gate selects for
  LLC-capacity-sensitive victims; this probe shows an L2-resident victim on SPR
  has *no* co-run tax at all, so the gate is not merely mis-aimed, it is
  selecting the only population where a tax exists.
- The measurement apparatus, now with D1/D2 fixed (`patches/`).
- The observation that ~24 GB/s is a core-side limit on both hosts, which makes
  a local-DRAM streamer a free bandwidth-matched control.

**Cost:** 17 days to deadline, and roughly one day spent. The probe did exactly
what it was built to do — this is a cheap negative, not an expensive one.

## 7. For the lead (§9)

These are decisions, not recommendations I should take myself.

1. **The gem5 SF geometry disclosure.** §4.1 is the sharpest item here. If any
   paper text presents the 2.501× as a quantity expected on a current server
   part, it needs to change, and the SF-at-parity provisioning should be stated
   where the number appears. This is a page-1 evidentiary-posture call.
2. **Whether the OLTP-index line is dropped entirely** or retained as a
   documented negative result. A measured "an L2-resident victim on SPR takes
   no co-run tax from a 24 GB/s LLC-thrashing streamer" is a genuine
   contribution to the L5 argument, but it argues against the mechanism story
   as currently framed, not for it.
3. **Whether this displaces the Sec5 DuckDB rewrite** — now more pressing, since
   the OLTP index is no longer competing for that slot.
4. **Whether the headline becomes an H3 capability claim** (permitted under the
   embargo), given that the silicon-harm framing just lost its Intel leg.

Item 2 in particular should not wait: it determines whether anything further is
spent here at all.

## 8. Defects found while running this

- **D1 / D2** — see `patches/README.md`. Every Intel L2 hit/miss number this
  binary has ever printed is void; mos182 and moscxl are fixed and rebuilt,
  **mos181 is not** (it was running twelve gem5 sims and was left alone).
- **Mask readback was host-dependent.** `cat_setup()` compared the resctrl
  schemata readback as a string. AMD's resctrl normalises `0fff` to `fff` while
  Intel's preserves the leading zero, so the check whose entire purpose is to
  catch a silently-unapplied CAT mask was itself vendor-dependent — it aborted
  a valid moscxl run. Now compared numerically in both runners.
