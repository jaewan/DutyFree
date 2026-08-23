# G-probe outcome: the kill switch fires, and the victim population inverts

**Date:** 2026-08-23 · **Hosts:** mos182 (Xeon 8462Y+, SPR), moscxl (EPYC 9754, Bergamo)
**Artifacts (moscxl):** `probe_moscxl.jsonl` (72), `probe_moscxl_cat12_control.jsonl` (36), `probe_moscxl_mba.jsonl` (99), `probe_moscxl_mba_knee.jsonl` (36), `probe_moscxl_mba_knee2.jsonl` (18), `probe_moscxl_mba_2x2.jsonl` (18), `probe_moscxl_mba_paperpoint.jsonl` (144), `moscxl_mba_calib.jsonl` (9)
**Artifacts (mos182):** `probe_mos182_matrix.jsonl` (60), `probe_mos182_cat_control.jsonl` (18), `probe_mos182_sfpressure.jsonl` (15), `mos182_wsext.jsonl` (75), `probe_mos182_mba.jsonl` (54), `probe_mos182_cat12_control.jsonl` (18), `mos182_mba_calib.jsonl` (10)
— 519 probe runs plus two MBA unit calibrations, all valid, all in `artifacts/`
**Runners:** `scripts/run_probe.py`, `run_cat_control.py`, `run_sfpressure.py`, `run_cat12_control_mos182.py`, `run_mba_mos182.py`, `mba_calib_mos182.py`, `run_probe_moscxl.py`, `run_cat12_control_moscxl.py`, `run_mba_moscxl.py`, `run_mba_knee_moscxl.py`, `run_mba_knee2_moscxl.py`, `run_mba_2x2_moscxl.py`, `mba_calib.py`

## Verdict

`OLTP_INDEX_DESIGN.md` pre-registered G-probe as a zero-code kill switch with
its interpretation fixed in advance:

> If the residual is small, the design's central claim is false on silicon and
> this document is abandoned before Masstree is written. That is the point of
> running it first.

**At the operating point the kill switch was written about — an L2-resident
victim — the residual is small on both hosts.** On mos182 the typical reading
there is 1.000× and nothing in the original matrix exceeds 1.065×.

That matrix stopped at a 16 MiB victim, and its scope was later stated here as
though it covered the host. It did not, and §5.7 corrects it: extending the
sweep to a victim sized to the full 60 MiB LLC finds a **1.60×** co-run tax on
mos182. The kill-switch verdict is untouched — it was always about the
L2-resident victim — but no sentence in this document may say "the largest tax
anywhere on mos182 is 1.065×". Read the null with its scope attached in both
directions: one working set out of L2, moscxl reads 18.8×, and at a
LLC-sized victim mos182 reads 1.60×. See "But do not read this as 'no harm'".

At the L2-resident point itself the typical mos182 reading is **1.000×**, with
the victim's L2 miss rate pinned at 0.00% while a co-resident streamer holds
41 MiB of the 60 MiB LLC and drives the victim's LLC occupancy to 0.1 MiB.

The null survives the strongest challenge available to it: scaling the
streaming cores' aggregate private-cache footprint from 16 MiB to 62 MiB —
essentially the whole socket's L2 — does **not** increase the tax (§3.2). If
snoop-filter capacity pressure were reaching the victim's private L2, that
sweep is where it would show, and it does not.

The null replicates on a second vendor. On moscxl — the harsher geometry, 7
streaming cores against a 16 MiB L3 — an L2-resident victim reads 1.011–1.026×
while the streamer holds **the entire L3** and drives the victim's occupancy to
zero (§5.1).

The design is abandoned as written. Masstree is not to be built for this
purpose.

This is a null on silicon, not a null from a broken instrument. §3 is the
evidence for that, and it is the part of this document that should be attacked
first if anyone wants to overturn the verdict.

### But do not read this as "no harm"

One working set further out, moscxl returns the opposite of a null, and it is
the most consequential number here. With the victim sized to 8 MiB — out of its
1 MiB L2, comfortably inside the 16 MiB L3 — the co-run tax is **18.8×**, and
way-partitioning does not recover it: granting the victim 12 of 16 ways and
boxing the streamer into 4 still leaves **12.4×**, against a measured 1.066×
cost for the partition itself (§5.3). It is not capacity — the victim loses
about a third of its L3 residency and runs 12.4× slower.

So the design got the *direction* wrong, not the existence of a CAT-resistant
residual. It predicted harm concentrated on L2-resident victims and defendable
capacity harm on LLC-resident ones. Measurement says: **nothing on L2-resident
victims, and a large tax on everything else that way-partitioning does not
recover — on AMD.** The same relative operating point on Intel reads 1.065×.

And that residual is a bandwidth problem that shipping hardware already
solves. The MBA arm has now been run (§5.6, on the lead's instruction).
**CAT and MBA together take the 18.7× tax to 1.07× while the streamer keeps
96% of its bandwidth** — both mechanisms ship in every current server part and
are set through the same kernel interface. So the AMD residual cannot carry an
L5 "unoccupied corner" claim, and that claim should not be written.

**§5.8 removes the last way to read that as an off-point result.** Re-run at
the paper's own published cell — 4 MiB victim, 8/8 split, CXL streamer, n=12 —
the same pair takes 9.97× to **0.985× [0.961, 1.008] of its own no-streamer
control** at 95.7% of streamer bandwidth, with the non-binding caps clean. The
same run also finds the paper is printing a **superseded number**: page 1's
6.92× was set aside in this repo on 2026-08-08 in favour of 9.87×, and an
independent runner reads 9.97× today. That correction is owed to the paper
whatever is decided about everything else.

What survives from the AMD leg is narrower but is the part the paper's
admission-gate argument actually needs: **CAT alone — way-partitioning, the
mechanism the gate is about — recovers almost nothing (18.73× → 13.05×)**, and
reaching 1.07× needs an operator to identify the aggressor and tune two
orthogonal knobs at core granularity, within a few percent of a saturation
knee.

**That is an AMD sentence, and §5.7 shows the Intel leg is the mirror image.**
The same arm on mos182: MBA is inert (1.221× → 1.229× while removing 47% of
the streamer's bandwidth), and CAT alone recovers the co-run tax *completely* —
measured against its own no-streamer control, the residual is **0.997×**.
mos182's harm is capacity and CAT is the right tool for it; moscxl's harm is
bandwidth and CAT is the wrong tool. One control separates them on both hosts:
MBA cuts the streamer's request rate without cutting its cache occupancy, so
the AMD tax dying and the Intel tax surviving under it is direct evidence of
which resource each is. Neither is the mechanism the design predicted.

## 1. What the design needed to be true

The OLTP-index victim was derived from the gem5 mechanism decomposition, in
which capacity displacement is the minority charge (1.369×) and
snoop-filter back-invalidation of the victim's **private** L1/L2 is the
majority (2.501× total). The whole point of choosing an index probe whose hot
set sits in the private L2 was that **no way mask defends against
back-invalidation**: a bitmask governs what a requester may allocate, and a
back-invalidation is an eviction performed on a line the victim already holds,
so no mask at any level is consulted — including the per-core L2 mask this
silicon does expose (§8). That is what would have made the residual
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

## 3. Why this is a real null and not a dead instrument (mos182)

An invariant reading across arms is equally consistent with an instrument that
cannot see co-run pressure. Three independent checks say it can — (a) and (b)
below, and, retrospectively, the strongest of the three: **the same runner and
the same counters read 18.8× on moscxl** one working set out of L2 (§5.2). An
instrument that cannot see a co-runner does not do that.

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

### 3.2 The strongest challenge to the null: snoop-filter footprint

The matrix used 8 streaming cores. Bandwidth saturates at 4 on this host, so
more threads buy no bandwidth — but **snoop-filter pressure does not scale with
bandwidth, it scales with the aggregate private-cache footprint of the
streaming cores.** 8 cores hold 16 MiB of L2 against a socket whose 32 cores
hold 64 MiB in total. If SPR's SF is provisioned at roughly 1–1.5× aggregate
private capacity, 16 MiB might genuinely not pressure it while 48 MiB would.
That is the one remaining way the null could have been an artifact of how the
stressor was sized, so it was closed directly (`run_sfpressure.py`, victim
fixed at ws=1024 KB, no CAT, 3 reps, 15/15 valid). Thread count is the honest
way to vary this; the `-R` pacing throttle carries a known confound and was not
used.

| threads | streaming L2 footprint | cyc/access | tax | L2 miss % | per-rep cyc |
|---:|---:|---:|---:|---:|---|
| 0 | — | 20.42 | 1.000 | 0.00 | 20.42 / 20.42 / 20.42 |
| 8 | 16 MiB | 21.93 | 1.074 | 2.51 | 22.69 / 20.42 / 22.70 |
| 16 | 32 MiB | 20.44 | 1.001 | 0.04 | 20.46 / 20.42 / 20.44 |
| 24 | 48 MiB | 21.22 | 1.039 | 1.25 | 20.42 / 22.83 / 20.42 |
| 31 | 62 MiB | 20.83 | 1.020 | 0.60 | 21.61 / 20.44 / 20.43 |

**Quadrupling the streaming private-cache footprint does not increase the tax.**
The largest mean is at the *smallest* footprint, and 62 MiB — essentially the
whole socket's L2 capacity streaming at once — reads 1.020×. If SF capacity
pressure were the mechanism, t31 would be dramatically worse than t8.

The per-rep column shows why the means move at all: the readings are **bimodal,
not noisy**. Eight of the twelve streamed arms sit at 20.43 cyc / 0.02% miss,
indistinguishable from quiescent; the other four sit at 22.46 cyc / 3.26% miss,
with almost no spread within either state (22.69, 22.70, 22.83, 21.61). The
elevated state occurs at t8, t8, t24 and t31 — **random with respect to
footprint** — and never at t0. A discrete two-state outcome that requires a
streamer but does not scale with it is not SF capacity pressure; the shape is
more consistent with per-run physical page placement producing L2 set conflicts
in some layouts. It was not chased further, because even taking the elevated
state as real and always-on puts the tax at **1.10×**, which does not change
any conclusion here.

Reported rather than smoothed over: the matrix's ws=1024 `WB_cxl` arm read
20.42 in all three reps, so the matrix happened to sample only the clean state.
That is an instability in the apparatus worth knowing about before anyone
quotes a 1.000× as though it were exact.

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
moved into the private L2. It does not, on either host.

§5.3 now goes further than reconciliation: it re-measures a residual of this
class directly, on the same part family, with the no-streamer control the
original lacked. At ws=8192 (8× the private L2) the co-run tax on a 12-way
partitioned victim is **12.43×**, against a 1.066× cost for the partition
itself. That is the same phenomenon as exp41's residual, measured with its
starvation component subtracted rather than assumed away, and it is larger.

(Per the standing δ embargo, no attribution of any of these residuals between
H2 and H3 is made or implied here. §5.3 is a magnitude and a CAT-recovery
fraction, nothing more.)

## 5. moscxl — the harsh-capacity replication, and the finding that inverts

*Host note: §5.1–§5.6 are moscxl. §5.7 returns to mos182 to run §5.6's arm
there; §5.8 returns to moscxl to run it at the paper's published operating
point. Both are kept in this section because neither means anything except read
against §5.6. Every figure below names its host.*

mos182 alone cannot distinguish "SPR does not back-invalidate" from "shipping
server LLCs do not back-invalidate," and those are very different claims.
moscxl is the harsher geometry (16:1 vs 30:1, 7 streaming cores against a
16 MiB L3 at 1 MiB/way) and is where the effect is most likely to appear. This
was not a rescue attempt, and it did not rescue the design — but it returned
more than a second null, and §5.2 is the most consequential result in this
document.

Full matrix: `artifacts/probe_moscxl.jsonl`, 72 rows, 3 reps, all valid.

### 5.1 At the pre-registered operating point: the null replicates

ws = 256 KB in a 1 MiB 8-way L2 — unambiguously L2-resident, 0.02% quiescent
L2 miss.

| arm | cyc/access | tax | L2 miss % | victim occ | streamer occ | GB/s |
|---|---:|---:|---:|---:|---:|---:|
| quiescent | 14.11 | 1.000 | 0.02 | 0.0 | 0.5 | — |
| WB_cxl | 14.44 | 1.023 | 0.03 | 0.0 | **16.0** | 24.7 |
| WB_local | 14.48 | 1.026 | 0.04 | 0.0 | **16.0** | 24.7 |
| WB_local_CAT12 | 14.26 | 1.011 | 0.02 | 0.1 | 4.1 | 24.5 |
| WB_local_CAT1 | 14.43 | 1.023 | 0.03 | 0.0 | 15.0 | 24.7 |
| CAT1_nostream | 14.11 | 1.000 | 0.02 | 0.0 | 0.5 | — |

The streamer holds **the entire 16 MiB L3**, drives the victim's L3 occupancy
to zero, and the victim moves by 2%. Its L2 miss rate does not move at all.
Two vendors, two microarchitectures, same answer: **an L2-resident victim is
not back-invalidated.** The kill switch fires on both.

(Zen's L3 is a victim cache, so an L2-resident victim has almost no L3
footprint to lose in the first place. The near-zero victim occupancy is
expected and is not the streamer evicting anything.)

### 5.2 One working set out, the tax is enormous — and CAT cannot recover it

The same six arms, swept out of L2. Quiescent L2 miss rises 0.02 → 26 → 93 →
99%, so only the first row is L2-resident.

| ws (KB) | quiescent | WB_local | WB_cxl | WB_local_CAT12 | WB_local_CAT1 | CAT1_nostream |
|---:|---:|---:|---:|---:|---:|---:|
| 256 | 14.11 | 1.026× | 1.023× | 1.011× | 1.023× | 1.000× |
| 1024 | 29.60 | 7.467× | 9.257× | 4.982× | 10.665× | 1.733× |
| 8192 | 60.67 | 18.756× | 18.767× | 13.248× | 18.753× | 4.056× |
| 65536 | 260.54 | 4.572× | 4.571× | 4.534× | 4.530× | 1.145× |

(The 65536 column reads 4.57× only because the quiescent baseline is already
260 cyc/access — a 256 MiB chase is DRAM-bound before anyone else runs. In
absolute terms it is the same ~1190 cyc/access wall as ws=8192.)

`WB_cxl` and `WB_local` agree at every working set. **CXL is not the variable
here; L3 and memory-path pressure is.** The one place they differ is ws=1024,
where the CXL arm's three reps are [166.8, 435.5, 219.8] against WB_local's
tight [229.3, 218.4, 215.5] — a 2.6× spread that makes the 9.257× mean
untrustworthy. ws=1024 KB is exactly the L2 size, i.e. a capacity knife-edge,
and it behaves like one. **The 8192 row is the reliable one**: [1137.5, 1136.8,
1139.8], a 0.3% spread.

### 5.3 The CAT12 control: the residual is not partition starvation

The matrix cannot interpret the `WB_local_CAT12` numbers on its own. That arm
gives the victim 12 of 16 ways and boxes the streamer into 4, so a tax there is
either real co-run residual or the cost of the partition itself. The matrix has
a no-streamer control only at the 1-way grant. `scripts/run_cat12_control_moscxl.py`
adds the missing cell (`artifacts/probe_moscxl_cat12_control.jsonl`, 36 rows,
3 reps, all valid); it imports the matrix runner rather than restating it, so
the control cannot drift from the arm it controls.

| ws (KB) | quiescent | CAT12_nostream | cost of the partition | WB_local_CAT12 | **co-run tax on the partitioned victim** |
|---:|---:|---:|---:|---:|---:|
| 256 | 14.11 | 14.11 | 1.000× | 14.26 | **1.011×** |
| 1024 | 29.54 | 29.92 | 1.013× | 147.50 | **4.93×** |
| 8192 | 60.65 | 64.65 | 1.066× | 803.84 | **12.43×** |
| 65536 | 260.42 | 269.60 | 1.035× | 1181.29 | **4.38×** |

A 12-way grant costs the victim between 0% and 6.6%. So the CAT12 taxes are
**almost entirely co-run residual**: with the streamer confined to a quarter of
the L3 and the victim holding three quarters of it, an 8 MiB victim still runs
**12.4× slower**. Way-partitioning recovers roughly a third of the no-CAT tax
(18.76× → 13.25×) and leaves the rest standing.

Nor is what remains explicable as capacity. At ws=8192 the victim's measured L3
occupancy is 7.9 MiB partitioned-and-quiescent versus 5.1 MiB
partitioned-and-co-run: it loses about a third of its L3 residency and gets
12.4× slower, at a working set that is already 93% L2-miss. A third of the L3
does not cost 12×.

### 5.4 What the L2 miss rate does and does not show here

At ws=1024 the victim's L2 miss rate moves under co-run (26.4% → 45.2%), and
that could be read as the back-invalidation signature the design predicted. It
is not, and the controls in this same table say so: **`CAT1_nostream` moves it
too** (26.2% → 35.4%), with no co-runner at all. An L3 way mask cannot
invalidate a private L2. So at ws=1024 the L2 miss rate is sensitive to
manipulations that cannot possibly be back-invalidation — a knife-edge working
set plus whatever prefetch and page-walk traffic the AMD L2 event counts — and
it does not isolate the mechanism.

At ws=256, where the victim is unambiguously L2-resident, the miss rate does
not move in any arm, under any partition, against a streamer holding the whole
L3. That is the measurement that carries the verdict, and it is the one with no
confound.

### 5.5 What this means

The design predicted harm **concentrated on L2-resident victims** — CAT-
undefendable because back-invalidation is not an allocation — and comparatively
little on LLC-resident ones, where the charge is capacity and CAT applies.

The measurement is the inverse of that on both counts:

- **L2-resident victim: no harm at all** (1.01–1.03×), on either vendor, even
  with the entire LLC taken.
- **Non-L2-resident victim on AMD: very large harm that CAT does not recover**
  (12.4× with a 12-way grant), and not from capacity.

CAT-irrecoverability survives, then — it is the *victim population* and the
*mechanism* that invert, not the existence of a CAT-resistant residual. But the
residual sits where a bandwidth-class explanation is the obvious one: 7 cores
saturating this CCX's egress at 24.7 GB/s, with every victim miss queueing
behind them. §5.6 tests that explanation and confirms it, which costs the L5
argument the corner: CAT-irrecoverable is not the same as irrecoverable, and
MBA — shipping on the same silicon, set through the same interface — recovers
it for 4% of the streamer's bandwidth. Read the rest of this subsection with
§5.6 attached.

The Intel/AMD gap at the same relative operating point is worth stating plainly
because it constrains any general claim: mos182 with a 16 MiB victim in a
60 MiB LLC against 8 streaming cores reads **1.065×**; moscxl with an 8 MiB
victim in a 16 MiB L3 against 7 streaming cores reads **18.8×**. Whatever the
mechanism is, it is not a property of "server LLCs."

### 5.6 The MBA arm: the corner is occupied, and cheaply

§7.5 asked whether the 12.4× CAT-irrecoverable residual is an unoccupied corner
or a known bandwidth problem. Run on the lead's instruction, the answer is
unambiguous and it is the bad one: **CAT and MBA together reduce an 18.7×
co-run tax to 1.07× while the streamer keeps 96% of its bandwidth.** Both
mechanisms ship in every current server CPU and are configured through the same
kernel interface.

Runners `scripts/run_mba_moscxl.py`, `run_mba_knee_moscxl.py`,
`run_mba_knee2_moscxl.py`, `run_mba_2x2_moscxl.py`; artifacts
`probe_moscxl_mba.jsonl` (99), `_knee` (36), `_knee2` (18), `_2x2` (18) —
171 rows, 3 reps each, all valid. Each runner monkeypatches the matrix runner's
`cat_setup` to write and verify an `MB` line alongside `L3` and then calls that
module's `run_arm` unchanged, so placement, victim-first arrival, occupancy
sampling, the foreign-load check and the D1 validity gate are the same code as
the matrix rather than a copy of it. Both resources are read back and compared
numerically before every arm.

**Units were calibrated on the host, not assumed** (`scripts/mba_calib.py`,
`artifacts/moscxl_mba_calib.jsonl`). The kernel reports
`MB: max 2048, gran 1, delay_linear 0`, and the documentation is ambiguous
between MB/s and 1/8 GB/s — the first reading would make the default 2 GB/s,
which cannot be right against a measured 24.7. A streamer-only ladder settles
it: the unit is 1/8 GB/s, and once the cap binds, delivery tracks it within 4%.

| MB setting | nominal GB/s | delivered GB/s |
|---:|---:|---:|
| 2048 / 1024 / 512 / 256 | ≥ 32 | 24.65 / 24.55 / 24.49 / 24.64 |
| 128 | 16 | 15.36 |
| 64 | 8 | 8.65 |
| 32 | 4 | 3.91 |
| 16 | 2 | 1.99 |
| 8 | 1 | 0.93 |

Anything ≥ 256 is above what 7 cores can pull here and does not bind — which is
what makes the non-binding controls below possible.

#### The 2×2 at ws = 8192 KB

Quiescent 60.89 cyc/access. `MBA192` is a nominal 24 GB/s cap — it costs the
streamer 4% of delivered bandwidth and nothing else.

| | **MBA off** (24.63 GB/s) | **MBA192** (23.60 GB/s, 96%) |
|---|---:|---:|
| **no L3 partition** | **18.73×** | 4.13× |
| **victim granted 12/16 ways** | 13.05× | **1.07×** |

Both knobs are needed and they attack different halves. Neither alone gets
below 4×; together, at a 4% throughput cost to the streamer, the victim is
within 7% of running alone.

#### The knee is the cap, not the machinery

A 13× collapse for 4% of bandwidth is the signature of a queue held at
saturation — but it is also what one would see if arming AMD's delay-injection
logic perturbed the streamer whether or not the cap bound. `_knee2` separates
them with settings that are above what 7 cores can pull, so they cost nothing:

| arm | streamer GB/s | victim tax |
|---|---:|---:|
| CAT12, no MBA | 24.54 | 13.28× |
| CAT12 + MBA256 (nominal 32 GB/s — does not bind) | 24.52 | **13.35×** |
| CAT12 + MBA224 (nominal 28 GB/s — does not bind) | 24.54 | **12.44×** |
| CAT12 + MBA192 (nominal 24 GB/s — barely binds) | 23.56 | **1.08×** |
| CAT12 + MBA176 (nominal 22 GB/s) | 20.95 | 1.08× |

Arming MBA without binding it does nothing. The recovery appears exactly where
the cap starts to bind, between 24.5 and 23.6 GB/s delivered, and does not
improve with further throttling — 1.08× at 96%, 1.08× at 85%, 1.078× at 35%,
1.084× at 8%. The 4% figure is the rate cap and it is real.

#### The harm is definitively not capacity

Throttling the request *rate* does not stop a streamer from occupying the L3 —
over an 8 s arm even 0.94 GB/s rewrites 16 MiB many times over — and the
occupancy column confirms it kept doing so. The cleanest cell is at ws=256:
under MBA8 the streamer holds **15.9 of the 16 MiB L3** and the victim reads
**exactly 1.000×**. At ws=8192, MBA16 leaves the streamer holding 7.8 MiB and
the victim at 1.018×. Same footprint, harm gone. §5.3 inferred this from
occupancy; it is now measured directly.

#### The full MBA-only Pareto curve at ws = 8192

For completeness, and because the shape matters: the tax falls smoothly with
throttling when CAT is not applied, and only the combination is cheap.

| streamer GB/s | % full | streamer L3 | victim tax |
|---:|---:|---:|---:|
| 24.69 | 100% | 16.0 | 18.667× |
| 23.70 | 96% | 15.4 | 4.13× |
| 15.38 | 63% | 14.9 | 3.943× |
| 12.68 | 52% | 12.8 | 3.298× |
| 8.66 | 35% | 10.9 | 2.154× |
| 3.91 | 16% | 8.9 | 1.284× |
| 1.99 | 8% | 7.8 | 1.018× |
| 0.94 | 4% | 8.1 | 1.010× |

The same pattern holds at ws=65536, where the victim is DRAM-bound:
4.552× → 1.036× with CAT12+MBA64, and CAT alone does nothing at all there
(4.537×), as expected when nothing fits.

#### What this does to L5

**"No deployed alternative occupies this corner" is false at this operating
point and must not be written.** It is not even expensive to occupy: 4% of the
streamer's throughput.

What survives is narrower, and none of it is a capability claim:

- **CAT alone — the mechanism the paper's admission-gate discussion is actually
  about — recovers almost nothing here: 18.73× → 13.05×.** This is untouched by
  the MBA result and is arguably the more useful finding, because it is a
  statement about the *admission* mechanism specifically rather than about
  interference control in general.
- Reaching 1.07× requires an operator to know which workload is the aggressor,
  place its cores in a class, and choose a cap within a few percent of the
  saturation point — where being slightly too generous (MBA224) buys nothing at
  all. Two orthogonal knobs, tuned per workload pair, at core/CLOSID
  granularity rather than at the granularity of the data.
- The Intel leg is untouched. mos182 reads 1.065× at the matching point, so
  there is no harm there for any mechanism to recover, and nothing in this
  section changes that.

Whether "the deployed alternative works, costs 4%, and needs per-pair tuning at
a granularity that is not the data's" is a paper or a paragraph in someone
else's related work is §9 item 6, and not a call I should make. What I can say
is that the L5 argument cannot be carried by the AMD residual, because the
residual is recoverable by shipping hardware at negligible cost.

### 5.7 The same MBA arm on Intel (mos182): the mirror image

Repeating §5.6 on mos182 required two things before any arm could run, and both
changed what the experiment is.

**The knob is not the same knob.** moscxl's MB is a group-level 1/8 GB/s cap
with 2048 steps. mos182 reports `bandwidth_gran 10, min_bandwidth 10,
delay_linear 1, thread_throttle_mode max` — ten coarse steps of a *per-core*
request delay scaled to one core's peak, not to the group's share of a shared
ceiling. Calibrated on the host (`scripts/mba_calib_mos182.py`,
`artifacts/mos182_mba_calib.jsonl`, 8 threads, the arms' own streamer):

| MB | 100 | 90 | 80 | 70 | 60 | 50 | 40 | 30 | 20 | 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GB/s | 23.82 | 23.95 | 23.98 | 23.96 | 23.97 | 23.93 | 23.96 | 23.88 | **22.57** | **12.57** |

Eight of the ten settings do nothing at all: capping each of 8 cores to 30% of
its individual peak still lets them saturate a ceiling that is already
saturated. Only MB=20 (94.7% of full) and MB=10 (52.8%) bind. So Intel offers
exactly one barely-binding setting and one deep one, and MB=30 is a free
non-binding control — the analogue of moscxl's MBA256/224. That MB=20 lands at
94.7% delivered, almost exactly moscxl's 96% knee, is an arithmetic coincidence
of core count and must not be read as the two knobs behaving alike.

**There was no known tax to recover, because the matrix stopped short.** §2's
largest reading is 1.065×, but §2 tops out at a 16 MiB victim — 27% of this
LLC — whereas moscxl blew up at 50% of its L3. The matching relative point had
never been probed on Intel. `scripts/run_probe.py` re-run with
`WS_LIST=16384,30720,61440,122880,245760` (`artifacts/mos182_wsext.jsonl`,
75 runs, all valid, 3 reps) finds the Intel tax is **non-monotone in working
set and peaks where the matrix was not looking**:

| ws | 16 MiB | 30 MiB | **60 MiB (= LLC)** | 120 MiB | 240 MiB |
|---|---:|---:|---:|---:|---:|
| quiescent cyc/acc | 95.04 | 100.73 | 132.38 | 275.35 | 310.13 |
| `WB_local` | 1.057× | 1.143× | **1.603×** | 1.182× | 1.065× |
| `WB_cxl` | 1.063× | 1.143× | 1.597× | 1.182× | 1.065× |

This corrects a claim in this document's own Verdict. "The largest mean co-run
tax at any working set, in any arm, is 1.065×" was true of the working sets
measured and is false of this host: at a victim sized to the LLC it is 1.60×.
The kill-switch verdict is unaffected — that was about the L2-resident victim,
which still reads 1.000× — but the scope sentence was an overreach and is
corrected in place. The curve falls back to 1.065× at 4× LLC for the ordinary
reason: a victim that already misses everything has no residency left to lose.

#### The 2×2 at ws = 61440 KB, the peak

`scripts/run_mba_mos182.py`, `artifacts/probe_mos182_mba.jsonl` — 54 runs, all
valid, 3 reps, same monkeypatch discipline as §5.6. Quiescent 131.22
cyc/access; streamer 8 threads on local DRAM.

| | **MBA off** (23.73 GB/s) | **MBA20** (22.51, 95%) | **MBA10** (12.63, 53%) |
|---|---:|---:|---:|
| **no L3 partition** | **1.621×** | 1.594× | 1.476× |
| **victim granted 12/15 ways** | **1.221×** | 1.224× | 1.229× |

**MBA is inert here.** Taking away 47% of the streamer's bandwidth removes 9%
of the excess in the unpartitioned arm and *none at all* from the partitioned
one. This is the opposite of moscxl, where 4% bought everything.

#### And after CAT there is nothing left for it to do

The 1.221× is not a residual. §5.3's rule applies with more force on Intel,
because at this working set the partition is not free: a 12-of-15-way grant
caps a 60 MiB victim at 48 MiB. The missing cell
(`scripts/run_cat12_control_mos182.py`,
`artifacts/probe_mos182_cat12_control.jsonl`, 18 runs, all valid) supplies the
denominator — quiescent drifted 0.2% between the two sessions, so they are
comparable:

| ws | CAT12_nostream / quiescent | CAT12 co-run / CAT12_nostream |
|---:|---:|---:|
| 30720 | 1.028× | **0.984×** |
| 61440 | 1.222× | **0.997×** |

**The co-run residual on Intel, after way-partitioning, is zero.** The entire
1.221× is the price of the partition itself. A 23.7 GB/s, 8-core,
LLC-thrashing co-runner costs a 12-way-granted victim nothing measurable, at
either working set, at any MBA setting. That is why MBA does nothing: not
because it is a weak knob, but because CAT already took the whole tax.

#### The two hosts are mirror images, and one control proves it

| | moscxl (Bergamo) | mos182 (SPR) |
|---|---|---|
| peak co-run tax | **18.73×** (victim = ½ L3) | **1.62×** (victim = 1× LLC) |
| CAT12 vs its own no-stream control | **12.4×** — CAT fails | **1.00×** — CAT complete |
| MBA against that residual | 13.05× → **1.07×** at 96% bw | 1.221× → 1.229× at 53% bw |
| harm class | bandwidth / queueing | capacity |

The discriminating control is the same one on both hosts, and it points in
opposite directions. MBA lowers the streamer's *request rate* without lowering
its *cache occupancy* — verified in the occupancy column on both machines
(moscxl: 15.9 of 16 MiB held under MBA8; mos182: 24.2 MiB held under MBA10,
statistically identical to the 25.4 MiB it holds unthrottled). So:

- moscxl's tax **vanishes** when rate falls and occupancy does not → the harm
  was never capacity.
- mos182's tax **survives** when rate falls and occupancy does not, and
  vanishes when occupancy is partitioned away → the harm is capacity, and
  only capacity.

Two vendors, one victim, one streamer, opposite mechanisms. Neither is the
mechanism the design predicted, which was back-invalidation of the private L2.

#### What this does to the paper

- **The L5 conclusion of §5.6 is unchanged and now two-sided.** There is no
  unoccupied corner on either host: on AMD the deployed pair costs 4%, on Intel
  a single deployed knob costs nothing beyond the partition and leaves no
  residual at all. The Intel leg is the weaker case for the paper, not the
  stronger one.
- **"CAT recovers almost nothing" is an AMD statement, not a general one.**
  §5.6's surviving finding (18.73× → 13.05×) must carry its host and operating
  point every time it is used, per §5.1. On Intel the same partition recovers
  100%.
- **The admission-gate inversion survives both legs, and is now the only thing
  that does.** A capacity-sensitivity gate mis-describes the AMD harm (which is
  bandwidth) and is redundant against the Intel harm (which CAT already fixes
  without any gate). It is wrong in one direction on one vendor and unnecessary
  in the other direction on the other.

#### Two incidental findings, both worth knowing

**mos182 exposes L2 CAT.** `/sys/fs/resctrl/info/L2/` is populated —
`cbm_mask ffff` (16 ways), `num_closids 8`, one domain per core — and the
schemata carries a live `L2:` line. §1's premise sentence, "CAT cannot defend a
private cache," is therefore false as written on this silicon: there is a
private-L2 way-allocation knob in the same kernel interface. The *argument*
survives, because an invalidation is not an allocation and no L2 mask prevents
back-invalidation — but the sentence would not survive a reviewer with an SPR
box, and should be rewritten to say what it means. Whether this interface
actually enforces was not tested.

**CAT12 is repeatedly faster than quiescent at large working sets** — 0.985×
at 16 MiB, 0.893× at 120 MiB, 0.967× at 240 MiB in the wsext sweep, and 0.984×
against its own no-stream control at 30 MiB — with the victim holding *more*
LLC under a 12-way cap (45.9 MiB) than with all 15 ways available (42.9 MiB).
Consistent across 3 reps, so not noise. One candidate: `shareable_bits=6000`
says L3 ways 13–14 are shared with other agents (DDIO), and the `0fff` victim
mask excludes exactly those two, so the partition may be buying isolation from
inbound DMA. **This is a guess and was not tested.** It does not affect
anything above — the peak operating point has CAT12 at 1.222×, well clear of
it — but any future use of a `0fff` mask on this host should establish what
this is first.

### 5.8 The paper's own operating point (moscxl): the published cell falls, and it was already the wrong cell

§5.6 measured an 8 MiB victim at a 12/4 split against a local-DDR streamer.
The paper's Sec5 portability paragraph measures something else: a **4 MiB**
victim at an **8/8** split against a **CXL** streamer, and reports 19.85×
unpartitioned with a **6.92× residual** after way-partitioning — the figure
page 1 cites for "capacity control is insufficient". Three deltas, so §5.6 did
not touch the published cell. `run_mba_paperpoint_moscxl.py` closes all three
at once and adds the MBA ladder. n=12 to match the paper, 144/144 rows valid,
95% rep-paired bootstrap over 20k resamples, seed 1.

| arm | cyc/access | tax | 95% CI | streamer GB/s | % BW | socc |
|---|---:|---:|---|---:|---:|---:|
| quiescent | 55.21 | 1.000× | — | — | — | 0.7 |
| CAT8_nostream | 57.79 | 1.047× | [1.029, 1.065] | — | — | 0.7 |
| WB_cxl | 1138.52 | **20.620×** | [20.435, 20.789] | 24.67 | 100.0% | 15.9 |
| CAT8_cxl | 550.51 | **9.971×** | [9.883, 10.057] | 24.69 | 100.1% | 8.0 |
| CAT8_cxl_MBA256 *(non-binding)* | 552.39 | 10.005× | [9.901, 10.105] | 24.71 | 100.1% | 8.0 |
| CAT8_cxl_MBA224 *(non-binding)* | 550.56 | 9.972× | [9.876, 10.069] | 24.70 | 100.1% | 8.0 |
| **CAT8_cxl_MBA192** | 56.92 | **1.031×** | [1.017, 1.047] | 23.62 | **95.7%** | 8.0 |
| CAT8_cxl_MBA176 | 56.90 | 1.031× | [1.020, 1.041] | 21.05 | 85.3% | 8.0 |
| MBA192_cxl *(no partition)* | 210.07 | 3.805× | [3.586, 3.978] | 23.71 | 96.1% | 15.2 |
| WB_local | 1138.85 | 20.626× | [20.433, 20.796] | 24.68 | 100.0% | 16.0 |
| CAT8_local | 549.59 | 9.954× | [9.864, 10.039] | 24.70 | 100.1% | 8.0 |
| CAT8_local_MBA192 | 57.41 | 1.040× | [1.029, 1.051] | 23.63 | 95.8% | 8.0 |

Against the §5.3 no-streamer control — the same victim under the same 8/8
partition with nothing co-running, which is the only denominator that separates
co-run harm from partition starvation:

| arm | vs CAT8_nostream | 95% CI |
|---|---:|---|
| CAT8_cxl | 9.526× | [9.359, 9.688] |
| **CAT8_cxl_MBA192** | **0.985×** | **[0.961, 1.008]** |
| CAT8_cxl_MBA176 | 0.985× | [0.968, 1.001] |
| CAT8_local_MBA192 | 0.993× | [0.975, 1.011] |

**The published residual does not reproduce, and the repo already knew.** The
unpartitioned arm does reproduce — 20.620× [20.435, 20.789] against a published
19.85×, +3.9%, so the apparatus is measuring the paper's phenomenon. The
partitioned arm is not: 9.971× [9.883, 10.057] against a published 6.92×.
That is not a new discovery. `experiments/phase1/e1_residual_decomp/RESULTS.md`
carries a **CORRECTION dated 2026-08-08**: a rerun of that campaign's own
unmodified script reproduced **9.87×**, the drift was verified all the way to
the hardware QoS mask MSRs (enforcement correct, physical cause unidentified),
and per explicit decision "**9.87× is now the campaign's standard number for
this arm**". Today's independent runner, different code, fifteen days later,
reads 9.97× — agreeing with the corrected number to 1%, not with the published
one. **The paper is printing a figure its own provenance record superseded.**
The derived quantity is wrong in the same direction: way-partitioning recovers
**54.3%** of the tax here, not the published 69%.

Per §6.6 this is reported, not reconciled. No configuration hunt was run and
none should be; two independent runners now agree on ~9.9× and the 6.92× has
a dated supersession notice against it.

**MBA closes the residual at the paper's point, whatever its value.** 9.971× →
1.031× at 95.7% of streamer bandwidth, and against its own no-streamer control
**0.985× [0.961, 1.008]** — statistically indistinguishable from the victim
running alone under the same partition. The two non-binding caps are the arm's
control and they are clean: 256 and 224 read 10.005× and 9.972× against the
uncapped 9.971×, so it is the cap doing the work, not the act of arming MBA.
That control was missing from §5.6's first pass and is present here.

**CAT is still necessary — this is the one result that goes the paper's way.**
MBA192 with no partition reads 3.805× [3.586, 3.978]. The deployed answer is
the *pair*, not MBA alone. "Capacity control is insufficient" survives as a
literal statement; what does not survive is "and nothing deployed closes the
gap."

**Capacity is again ruled out as the mechanism.** The streamer holds 8.0 MiB —
its full eight ways — in every CAT8 arm including the recovered ones. MBA
removes the tax without removing a single line of streamer occupancy, exactly
as on the §5.6 arm and the §5.7 Intel mirror.

**CXL contributes nothing at this operating point.** WB_local 20.626× against
WB_cxl 20.620×, at 24.68 vs 24.67 GB/s; CAT8_local 9.954× against CAT8_cxl
9.971×; the MBA192 cells 1.040× and 1.031×. Every pair is inside the other's
interval. At matched bandwidth the source node is undetectable, which supports
"the tax follows allocation, not the device" and withdraws support from any
CXL-specific framing of *this* cell.


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
- The **admission-gate inversion** finding is untouched and, after §5, much
  stronger than it was. The old CAT capacity-sensitivity gate selects for
  LLC-capacity-sensitive victims. This probe shows that on both hosts an
  L2-resident victim has essentially no co-run tax, and that on AMD the
  non-L2-resident victim has a 12.4× tax that CAT does **not** recover. The
  gate is not merely mis-aimed: it selects the only population where a tax
  exists, and then mis-describes that tax as capacity. §5.6 sharpens this
  further: the tax is a *bandwidth* charge, so a capacity knob is the wrong
  instrument for it in both directions.
- **A large co-run residual that way-partitioning does not recover, on
  shipping AMD silicon**, now measured with the no-streamer control the earlier
  result lacked (§5.3) — but read only as a statement about way-partitioning,
  and no longer as a statement about deployed mechanisms in general. It is
  18.73× → 13.05× for CAT alone at §5.6's point, and 20.62× → 9.97× at the
  paper's own point (§5.8). Those are what is alive; the word
  "CAT-irrecoverable" is not, because MBA recovers both.
- The measurement apparatus, now with D1/D2 fixed (`patches/`).
- **A bandwidth-matched control for free.** An 8-thread streamer delivers
  ~24 GB/s from local DRAM and ~24 GB/s from CXL on mos182, and ~24.7 GB/s
  either way on moscxl, so `WB_local` separates "CXL" from "bandwidth" at no
  extra cost. Two corrections to how this has been stated: on the CXL side it
  is a *link* ceiling, not a core-side one — the §3.2 sweep holds 23.6–23.9
  GB/s flat from 8 to 31 streaming threads, so 8 threads already saturate it —
  and on the local side no thread sweep was run, so "core-side limit" there is
  an inference, not a measurement. The operational claim the control needs (the
  two arms are bandwidth-matched at 8 threads) is measured; the mechanism
  behind the local number is not.

**Newly dead (§5.6, §5.7, §5.8):** the L5 "no deployed alternative occupies
this corner" claim, on both hosts, by two different routes, and — as of §5.8 —
at the exact operating point page 1 cites for it. On moscxl CAT+MBA
reaches 1.07× at a 4% cost to the streamer. On mos182 CAT alone reaches 0.997×
of its own no-streamer control — there is no residual there at all, at any MBA
setting, so the Intel leg never had a corner to occupy. The MBA arm was run
twice to test exactly this and came back the wrong way both times; reporting it
is not optional.

**Also newly dead:** any general form of "way-partitioning cannot recover this
tax." It cannot on Bergamo and it entirely can on Sapphire Rapids. Per §5.1
that claim now travels with its host and operating point or it does not travel.

**Newly corrected:** this document's own Verdict claimed 1.065× as the largest
mos182 tax at any working set. The matrix it rested on stopped at a 16 MiB
victim; at an LLC-sized victim mos182 reads 1.60× (§5.7). The kill switch is
unaffected, the scope sentence was wrong.

**Newly found, and the most urgent item in this document (§5.8):** the paper
prints **6.92×** for the AMD way-partitioned residual, and
`experiments/phase1/e1_residual_decomp/RESULTS.md` has carried a dated
supersession since **2026-08-08** setting the campaign's standard number for
that arm to **9.87×**. An independent runner reproduced 9.97× [9.88, 10.06]
today. The derived "recovers only 69%" is 54.3%. Both figures are on page 1.
This is a correctness defect in a live submission and is independent of
everything else here — it needs fixing even if no other conclusion in this
document is accepted.

**Cost:** 17 days to deadline, and roughly one day spent. The probe did exactly
what it was built to do — this is a cheap negative, not an expensive one, and
§5.2 was not on the menu when it was designed.

## 7. For the lead (§9)

These are decisions, not recommendations I should take myself.

0. **NOT a decision — a correction the paper needs regardless (§5.8).** Sec5
   and page-1 contribution (2) print **6.92$\times$** and "recovers only 69\%".
   The repo's own provenance record superseded that on 2026-08-08 (9.87×), and
   an independent runner read 9.97× [9.88, 10.06] today; recovery is 54.3%.
   Listed here only because it is on page 1 and someone has to actually do it.
   It is not contingent on any other item below. **I have not touched the
   paper's numbers** — changing a page-1 figure is a lead call even when the
   direction is not in doubt.

1. **The gem5 SF geometry disclosure.** §4.1 is the sharpest item here. If any
   paper text presents the 2.501× as a quantity expected on a current server
   part, it needs to change, and the SF-at-parity provisioning should be stated
   where the number appears. This is a page-1 evidentiary-posture call.
2. **Whether the OLTP-index line is dropped entirely** or retained as a
   documented negative result. A measured "an L2-resident victim takes no
   co-run tax from a 24 GB/s LLC-thrashing streamer, on either vendor" is a
   genuine contribution to the L5 argument, but it argues against the mechanism
   story as currently framed, not for it.
3. **Whether this displaces the Sec5 DuckDB rewrite** — now more pressing, since
   the OLTP index is no longer competing for that slot.
4. **Whether the headline becomes an H3 capability claim** (permitted under the
   embargo), given that the silicon-harm framing just lost its Intel leg.
5. **The MBA arm — ANSWERED, and answered against us (§5.6).** Run on the
   lead's instruction. It is a well-known bandwidth problem: CAT+MBA takes
   18.73× to 1.07× at a 4% streamer cost, and MBA does it without displacing
   the streamer from the L3, which also settles that the harm was never
   capacity. **The L5 "unoccupied corner" sentence cannot be written from the
   AMD number and should be struck wherever it appears.** No further
   experimental work is queued on this line. The residual figure that survives
   for the paper is the CAT-alone one — 18.73× → 13.05× at §5.6's point, and
   20.62× → 9.97× at the paper's own point (§5.8) — and it must be labelled as
   being about way-partitioning specifically, not about interference control.
   **§5.8 closes the last escape route**: the recovery is no longer at a
   nearby operating point, it is at the published one, with the non-binding
   controls clean and the recovered victim statistically indistinguishable from
   its own no-streamer control (0.985× [0.961, 1.008]) at 95.7% of streamer
   bandwidth. CAT is still necessary (MBA alone 3.805×), so the deployed answer
   is the pair — that much is still available to the paper. **And per §5.7 it must also carry its vendor**: on mos182 the same
   partition recovers 100% of the tax and MBA is inert, so "CAT recovers almost
   nothing" is a Bergamo sentence, not a server-CPU sentence.
6. **Whether the paper's harm claim relocates rather than dies.** §5.5 is
   written as a finding, not a rescue, but it does hand back a mechanism story:
   harm on non-L2-resident victims, CAT-resistant, AMD-specific at these
   geometries, Intel reads 1.065× at the matching point. That is a narrower and
   better-evidenced claim than the one being replaced, and it is also a
   different paper section. Whether to make that move is a structural call.

With 5 resolved and 0 pending, **item 6 is now the one that should not wait**, and it is a
narrower question than it was this morning: the relocated harm claim can no
longer be "shipping hardware cannot fix this," only "way-partitioning cannot
fix this, and the thing that can needs per-workload-pair tuning at core
granularity." Item 2 follows from it.

## 8. Defects found while running this

- **D1 / D2** — see `patches/README.md`. Every Intel L2 hit/miss number this
  binary has ever printed is void; mos182 and moscxl are fixed and rebuilt,
  **mos181 is not** (it was running twelve gem5 sims and was left alone).
- **Mask readback was host-dependent.** `cat_setup()` compared the resctrl
  schemata readback as a string. AMD's resctrl normalises `0fff` to `fff` while
  Intel's preserves the leading zero, so the check whose entire purpose is to
  catch a silently-unapplied CAT mask was itself vendor-dependent — it aborted
  a valid moscxl run. Now compared numerically in both runners.
- **The MB readback had the same bug in the other direction.** Intel pads MB
  values with a leading space (`MB:0= 100;1= 100`); AMD does not. The regex
  written for AMD (`{DOM}=(\d+)`) therefore matched nothing on Intel and the
  first mos182 calibration aborted with "MBA NOT APPLIED" against a schemata
  that had applied perfectly. Same class of defect as the one above, in the
  same check, found two hosts later. Now `=\s*(\d+)`, compared numerically.
  The lesson both times: a readback assertion written against one vendor's
  string formatting is an apparatus bug waiting for the second vendor.
- **§1's premise sentence was wrong on Intel silicon; fixed 2026-08-23.** It
  read "CAT cannot defend a private cache" — but mos182 exposes L2 CAT
  (`/sys/fs/resctrl/info/L2/`, `cbm_mask ffff`, 8 CLOSIDs, per-core domains),
  so as written a reviewer with an SPR box would have refuted it. The argument
  survives unchanged, because back-invalidation is not allocation and no way
  mask at any level is consulted for one. §1 here and the paper's two
  statements of the same claim (`Sec5_Evaluation.tex` H3 paragraph,
  `Appendix.tex` tab:h3sf caption) now say that instead. See §5.7. Whether the
  L2 interface actually enforces was not tested.
- **An unexplained sub-quiescent effect on mos182 at large working sets.** A
  12-way-granted victim is repeatedly *faster* than the same victim with all 15
  ways and no co-runner, and holds more LLC while doing it (§5.7). Consistent
  over 3 reps at three working sets. A DDIO-isolation candidate is named there
  and is untested. It does not touch any conclusion in this document, and it is
  a trap for anything that later uses a `0fff` mask on this host.
