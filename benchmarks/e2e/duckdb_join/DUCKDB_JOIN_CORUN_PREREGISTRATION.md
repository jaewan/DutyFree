# Pre-registration: DuckDB many-to-many join co-run campaign

Written 2026-08-21, **before any arm of this campaign**. The aggressor
bandwidth calibration in §3 was taken before this file existed; it is
instrument characterisation, not an arm, and it involved no victim.

Supersedes nothing. The orphaned panel measurements in
`DUCKDB_JOIN_FINDING_2026-08-21.md` are **not** part of this campaign and are
not cited by it: they were taken without exclusivity, without
pre-registration, and without the control in §4. This campaign re-establishes
the result from zero and may contradict them.

## 1. Why this victim

DuckDB has been a null in this project since exp40 (0.99x, Intel) and again at
matched 16 MiB geometry (1.00x). Those runs measured a **scan**, and the
project's own §3.2 diagnosis is that a scan has no reuse, so stealing its LLC
capacity costs it nothing. A **many-to-many equi-join** is the opposite shape
in the same engine: the build side is a hash table that is reused across the
whole probe, and when several build rows share a key the probe walks a
duplicate chain, which is a dependent load chain rather than a batched gather.

The victim is therefore DuckDB v1.1.3 (`19864453f7`) running:

```sql
CREATE TABLE b AS SELECT (i % K)::BIGINT AS k, (i*7)::BIGINT AS payload
                 FROM range(N) t(i);
CREATE TABLE p AS SELECT (hash(i) % K)::BIGINT AS k FROM range(10000000) t(i);
SELECT count(*), sum(b.payload) FROM p JOIN b ON p.k = b.k;
```

with `K = N/8`, so every probe key matches about eight build rows. `SET
threads=1` for the measured query; tables bound to the CXL node.

**The within-engine control is part of the design, not an afterthought.** The
same query with `K = N` (unique build keys, no duplicate chain) is run at the
same build size on the same host. If the chain is the mechanism, `chain8` must
exceed `joinuniq`. If they are equal, the reuse alone explains everything and
the chain claim is withdrawn.

## 2. Sizing, declared per host in advance

A gate whose minimum expressible mask exceeds the victim's reused set measures
granularity, not capacity. Minimum masks and LLCs differ by an order of
magnitude across these hosts, so **one build size cannot be used everywhere**,
and per-host sizing is declared here rather than chosen later:

| host | LLC | ways | min mask | build sizes to sweep |
|---|---:|---:|---:|---|
| `mos181` (8592+) | 320 MiB | 20 | 16 MiB | N = 1M, 2M, 4M, 6M, 8M |
| `mos182` (8462Y+) | 60 MiB | 15 | 4 MiB | N = 250K, 500K, 1M, 2M |
| `moscxl` (EPYC 9754) | 16 MiB/CCX | 16 | 1 MiB | N = 64K, 128K, 256K, 512K |

**Validity condition for a cell to count** (all three required, checked from
CMT and recorded per record):
1. full-mask victim occupancy **>= 2x the minimum mask** — otherwise the gate
   has no dynamic range on this victim and the cell yields *no verdict*, not a
   null;
2. full-mask victim occupancy **<= 60% of the LLC** — above that the full-mask
   arm is not holding the reused set either, and the contrast is not clean.
   60% rather than 50%: the panel referee proposed 50%, and `mos181`'s
   available build sizes bracket it awkwardly, so the looser bound is declared
   now with the tighter one reported alongside;
3. min-arm/full-arm DRAM traffic ratio **>= 1.5**, so the manipulation
   demonstrably changed the victim's memory behaviour.

**Selection rule:** among build sizes satisfying all three, take the
**smallest** that clears the gate, as the GAPBS campaign did. Smallest rather
than largest so the result cannot be accused of being the one point tuned to
the cache.

## 3. Instrument characterisation (already measured, `mos181`, node 2)

`~/tmp_dutyfree_exp/bin/aggressor`, 512 MB/thread, 6 s, cores 8-15:

| threads | `wb_load` GB/s | `wb_prefetchnta` GB/s |
|---:|---:|---:|
| 1 | 10.308 | 6.063 |
| 2 | 18.484 | 10.751 |
| 3 | 24.928 | 15.334 |
| 4 | 24.140 | 17.257 |
| 8 | 25.019 | 17.969 |

The CXL link saturates at 3-4 threads for `wb_load` and 4 for
`wb_prefetchnta`, so **thread count cannot vary bandwidth above 4 threads**.
`-R` pacing is not used: the E2E prompt records it as carrying a known
confound.

## 4. The control that decides the campaign

Every recovery arm in the orphaned data moved **less bandwidth** than the
write-back arm it was compared against, so its recovery was not attributable
to non-allocation rather than to reduced bandwidth. This campaign fixes that
with two matched-bandwidth pairs at two bandwidth levels:

| pair | write-back arm | non-allocating arm | bandwidth | mismatch |
|---|---|---|---:|---:|
| **high** | `wb_load -t 2` | `wb_prefetchnta -t 8` | 18.48 vs 17.97 GB/s | 2.8% |
| **low** | `wb_load -t 1` | `wb_prefetchnta -t 2` | 10.31 vs 10.75 GB/s | 4.3% |

In both pairs the write-back arm uses **fewer cores** (2 vs 8; 1 vs 2), so it
spreads less fill pressure across the LLC. Any excess tax it still shows is
therefore attributable to allocation and is **understated**, not flattered, by
the residual asymmetry. Two levels rather than one so the finding cannot be a
single-point coincidence.

## 5. Arms

Per host, per selected build size, in a fixed seeded interleave with a matched
quiescent repetition adjacent to every loaded repetition:

| arm | aggressor | purpose |
|---|---|---|
| `quiescent` | none | baseline, re-measured within the same run |
| `WB_sat` | `wb_load -t 8 -N 2` | the polluting reference at link saturation |
| `WB_match_hi` | `wb_load -t 2 -N 2` | **control** for `NTA_sat` |
| `NTA_sat` | `wb_prefetchnta -t 8 -N 2` | non-allocating, matched to `WB_match_hi` |
| `WB_match_lo` | `wb_load -t 1 -N 2` | **control** for `NTA_lo` |
| `NTA_lo` | `wb_prefetchnta -t 2 -N 2` | non-allocating, matched to `WB_match_lo` |
| `WB_local` | `wb_load -t 8 -N 0` | local-DRAM streamer, for the placement row |
| `flushbehind` | `amd_flushbehind_aggressor -f 256` | AMD only; the coherent proxy |

n >= 10 valid repetitions per arm, first repetition of each invocation
discarded, **even** measured count per the GAPBS parity defect. Victim LLC
occupancy and DRAM traffic recorded per repetition. Aggressor achieved
bandwidth recorded per repetition and asserted within 10% of §3.

## 6. Falsifiable outcomes, declared now

1. **`WB_match_hi` tax >= 1.5x while `NTA_sat` tax <= 1.2x, at equal
   bandwidth.** Allocation is the cause; the paper's central de-confound holds
   on a real application. This is the result the campaign is built to test.
2. **`WB_match_hi` and `NTA_sat` taxes within measurement error of each
   other.** The tax is bandwidth-mediated, the orphaned recovery numbers are
   void, and the campaign reports that the effect is not allocation. This
   would be a serious negative for the paper and must be reported as such.
3. **`chain8` and `joinuniq` equal at the same build size.** The duplicate
   chain is not the mechanism; the claim narrows to hash-table reuse alone.
4. **No build size satisfies §2 on a host.** That host yields no verdict and
   may not be cited as a vendor null.
5. **CoV > 5% or bimodal loaded distributions.** Not a publishable operating
   point until a cause is declared, per the standing bar.

## 7. Hygiene, because the last attempt failed on it

- **Host exclusivity is enforced in code**, not by convention:
  `../lib/hostguard.py` takes a lock and asserts quiescence immediately before
  every arm, aborting the arm on a foreign resctrl group, a competing
  experiment process, or excess load. The 2026-08-21 panel ran four
  investigations concurrently on `mos181` and destroyed at least one member's
  gate without either operator noticing.
- `moscxl` must be frozen and captured (`bergamo_freeze.sh`) before its first
  arm. It has run `schedutil` with boost enabled since a 2026-08-19 reboot and
  no AMD platform state has ever been recorded, so no AMD number taken before
  that is re-measurable under the protocol the paper states.
- Every tax is `loaded / matched quiescent` from within its own run and host.
- DuckDB is pinned to v1.1.3 by `scripts_setup_duckdb.sh`, because the
  hash-table layout this campaign depends on is an internal detail upstream is
  free to change.

---

# Amendment 1, 2026-08-21 — sizing, probe scaling, and an outcome-blind selection rule

Made **before any result of this campaign was read.** A gate sweep was launched
under §2 as originally written, then killed; its 10 records are quarantined
unread at `artifacts/SUPERSEDED_join_gate_mos181_wrong_sizing.jsonl` and are
not used anywhere, including in this amendment. The amendment comes from a
source-level analysis of DuckDB v1.1.3 by the panel's columnar-engine member,
not from data.

## A1. The reused set is analytic, and my declared sweep included invalid points

DuckDB's own sizing rules give the reused set in closed form. The pointer table
is `PointerTableCapacity(count) = MaxValue(NextPowerOfTwo(count*2), 1024)`
entries of 8 B (`join_hashtable.hpp:384`), keyed on build **rows**; at a load
factor of 6% the occupied entries are 16-32 slots apart, so each occupies its
own line and the *touched* pointer-table footprint is `8N` bytes. Row blocks in
`TupleDataCollection` measure ~32 B/row, all touched, because every probe walks
all eight rows of its chain. So

    R(N) = 8N + 32N = 40N bytes

which cross-checks against measured occupancy to ~15% at three build sizes.
Requiring `max(4 x private L2, minimum expressible mask) < R(N) < 0.5 x LLC`:

| host | admissible R | **admissible N** | my original sweep |
|---|---|---|---|
| `mos181` | 16 - 160 MiB | **500K - 4M** | 1M, 2M, 4M, ~~6M~~, ~~8M~~ |
| `mos182` | 8 - 30 MiB | **250K - 750K** | 250K, 500K, ~~1M~~, ~~2M~~ |
| `moscxl` | 4 - 8 MiB | **100K - 200K** | ~~64K~~, 128K, ~~256K~~, ~~512K~~ |

Revised sweeps: `mos181` 500K/1M/2M/3M/4M; `mos182` 250K/400K/500K/625K/750K;
`moscxl` 100K/125K/150K/175K/200K. `moscxl` 64K is dropped as only 2.4x the
private L2, which is the trap that produced three earlier nulls in this
project.

## A2. The probe side was unaccounted pollution, and it was worst where it mattered most

The probe table is streamed, never reused, and my §1 query fixed it at
P = 10M rows = **80 MB**. That is 25% of `mos181`'s LLC of pure non-reused
traffic and **five times the entire 16 MiB CCX on `moscxl`** — the victim was
competing with its own scan for the cache it was being measured on. P is now
scaled per host to about 12% of LLC:

| host | P | scan bytes |
|---|---:|---:|
| `mos181` | 4M | 32 MB |
| `mos182` | 1M | 8 MB |
| `moscxl` | 250K | 2 MB |

Timing resolution lost to the shorter probe is recovered by raising the
in-invocation query count from 7 to 13 (12 measured, still even), not by
lengthening the probe. Occupancy is reported against `R + 8P` so the reused and
streamed components stay separable.

## A3. The selection rule is replaced, because mine was outcome-conditioned

"Smallest passing" was borrowed from the GAPBS gate, where the dial changed
*work* and the criterion was a pass/fail on a gate ratio. Here the dial changes
the reused-set-to-cache ratio, the gate ratio is monotone in it inside the
window, so "smallest passing" deliberately selects the point closest to the
bar — maximum noise sensitivity — and it reads the outcome to make the
selection. Replaced with a rule that never looks at a masked or loaded arm:

> 1. Admit `N` by the analytic window in A1.
> 2. Run **quiescent, full-mask arms only**. Compute per-**output**-row time
>    (chain8 emits ~8 output rows per probe row).
> 3. Select the **largest** admitted `N` whose per-output-row cost is within 5%
>    of the minimum over admitted `N` — the largest reused set the full mask
>    still genuinely holds.
> 4. Freeze `N`. Only then take masked and loaded arms.

This independently rejects oversized points without reference to any tax.

## A4. Three measurement defects to fix before the first arm

- **Streamer settle time.** §5 as written let the aggressor run 3 s before the
  victim. A ramp of 123.7 -> 162.4 -> 190.7 -> 222.6 -> 252.0 ns across
  repetitions shows the streamer needs **more than 20 s** to reach steady-state
  LLC occupancy, so a short settle understates the loaded arm. The runner now
  waits for the aggressor's own CMT occupancy to stabilise (three consecutive
  samples within 5%), with a 25 s floor and a 60 s cap.
- **Table generation inside the measured process.** Every invocation
  regenerating its tables means allocator state and physical page placement
  differ run to run, and the first query is always contaminated. Worse, the
  orphaned runs used `SET threads=8` for generation on `mos181` and
  `threads=1` on `moscxl`, so those hosts were not comparable. Tables are now
  built **once per (host, N, chain)** into a persistent database, opened
  read-only for measurement, with one generation-threading policy everywhere.
- **`mbm_total_bytes` is now recorded**, not just `mbm_local_bytes`. This is
  not bookkeeping: the hand-rolled campaign recorded flush-behind at 16.97 GB/s
  self-reported against **32.06 GB/s on MBM**, versus write-back's 24.71/24.31
  — a recovery arm that moves *more* total controller traffic than write-back
  and still taxes the victim far less. That cannot be a bandwidth artifact, and
  it is a stronger de-confound than any thread-matched arm. It was not captured
  for the orphaned DuckDB flush arm.

## A5. `mos182` node 2 is gated behind a sanity check

On `mos181`, a 128 MiB dependent chase reads 54.41 ns on node 0 and 54.32 ns on
node 2 while quiescent — placement is invisible while the set is
LLC-resident, which is the control that makes a capacity result a capacity
result. `mos182` fails that check in the orphaned data: full-mask node-2 time
is 2-4x the node-0 time at the same `N`. No `mos182` node-2 arm is taken until
`cxl_join_bench --mode latency` reproduces the `mos181` invariance there.

## A6. A pre-existing control that partly pre-answers §4

exp40's pointer-chase victim on `mos181` measured **2.042x at 24.82 GB/s** and
**2.025x at 11.52 GB/s** — halving the aggressor's bandwidth moved the tax by
1%. That is already a bandwidth-insensitivity control for the Intel allocation
channel, it is committed, and it should be cited alongside the new
matched-bandwidth arms rather than re-earned.

## A7. Correction to a claim already committed

`DUCKDB_JOIN_FINDING_2026-08-21.md` says the join "clears the 2x CAT gate on
all three hosts". Under A1 that is **wrong for `mos182`**: its only >=2x row
(2.035x) is at b1M, which is 64% of that host's LLC and outside the window. The
best admissible `mos182` point in the orphaned data is 1.998x at b500K node 0 —
at the bar, not over it. The finding document is corrected accordingly.

---

# Amendment 2, 2026-08-21 — the A3 selection rule degenerated; what replaces it

Recorded **after the quiescent selection sweep and before any masked or loaded
arm**. The selection sweep is outcome-blind by construction (quiescent,
full-mask only), so amending the rule on its evidence does not read a tax.

## Observed

`mos181`, chain8, probe 4M, n=3 per point, CoV ~0.2%:

| N | R = 40N | measured occupancy | ns per output row |
|---:|---:|---:|---:|
| 500K | 19 MiB | 55-60 MiB | 14.69 |
| 1M | 38 MiB | 91-96 MiB | 16.22 |
| 2M | 76 MiB | 135-150 MiB | 18.97 |
| 3M | 114 MiB | 206-231 MiB | 21.76 |
| 4M | 152 MiB | 186-200 MiB | 25.76 |

The `R + 8P` model predicts occupancy well at four of five points (b500K
19+30=49 vs 55-60; b1M 68 vs 91-96; b2M 106 vs 135-150; b4M 182 vs 186-200).
**b3M is anomalous**: predicted 144 MiB, measured 206-231, which is both above
its neighbours' trend and above b4M's. Unexplained; flagged rather than
smoothed.

## Why A3's rule fails here

A3 selected "the largest admitted `N` whose per-output cost is within 5% of the
minimum", intending to find the largest reused set the full mask still holds.
That presumes a flat region followed by a rise. **There is no flat region** --
cost rises monotonically from the smallest admitted size, because in this range
the curve is driven by the hash table outgrowing the **2 MiB private L2**, not
the 320 MiB LLC. So the rule reduces to "smallest admitted `N`", the opposite
of its intent, and lands on b500K whose R of 19 MiB is only 1.19x the 16 MiB
minimum mask -- the one point where the gate would have almost no dynamic range
on the reused set.

The rule was mis-specified, not the data. LLC residency is simply not
identifiable from a quiescent cost curve on this host.

## What replaces it

1. **No single operating point is selected for the gate.** The gate is run at
   **every admitted build size** and the whole curve is reported, per the
   referee's instruction to print the sweep rather than a chosen row. A curve
   that is monotone in R is itself the evidence; a single row is not.
2. **For the co-run**, where n>=10 per arm makes a full sweep impractical, the
   operating point is the **largest build size satisfying the occupancy bound
   already declared in §2 condition 2** (occupancy <= 60% of LLC = 192 MiB
   here). That admits b500K, b1M, b2M and b4M, and excludes b3M at 206-231
   MiB. The largest admissible is therefore **N = 4M**, R = 152 MiB,
   occupancy 186-200 MiB.

This is outcome-blind: the 60% bound was declared before any measurement, and
occupancy is measured quiescently. It is worth stating plainly that N = 4M is
also the point the orphaned, discarded run found strongest (2.432x). That is a
coincidence of the bound, not an inheritance -- b4M is selected here because it
is the largest size under a pre-declared occupancy ceiling, and the orphaned
b6M and b10M points that scored *higher* are the ones the same ceiling rejects.

3. **b4M sits at 59.7% of the 60% ceiling.** Reported as borderline. If the
   co-run at b4M shows any instability, b2M (141 MiB, 44%) is the pre-declared
   fallback, and switching to it must be disclosed as a deviation.

---

# Amendment 3, 2026-08-21 — gate result, and the co-run operating point

Recorded after the quiescent gate sweep and **before any loaded arm**. The gate
is a quiescent capacity manipulation; it reads no aggressor and no tax.

## Gate curve, `mos181`, chain8, probe 4M, n=3 per cell, CoV ~0.3%

| N | R = 40N | occupancy full | % LLC | occupancy min | full s | min s | **ratio** |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 500K | 19 MiB | 59 MiB | 19% | 14 MiB | 0.4710 | 1.0360 | **2.200** |
| 1M | 38 MiB | 95 MiB | 30% | 15 MiB | 0.5210 | 1.2175 | **2.337** |
| 2M | 76 MiB | 138 MiB | 43% | 15 MiB | 0.6050 | 1.4240 | **2.354** |
| 3M | 114 MiB | 205 MiB | 64% | 15 MiB | 0.6920 | 1.5900 | 2.298 |
| 4M | 152 MiB | 193 MiB | 61% | 15 MiB | 0.8230 | 1.4555 | 1.769 |

Four of five admitted sizes clear 2x, so this is a **window, not a point** --
which is what makes it hard to dismiss as a tuned configuration. It is also
consistent in shape with an independent panel measurement: a bare dependent
chase on this host peaks at 32-128 MiB and collapses above ~256 MiB.

The manipulation is verified rather than assumed. At full mask the victim is
effectively LLC-resident, moving **0.03-0.22 GB** of DRAM traffic across 13
queries; confined to one way it moves **12-41 GB**. Occupancy tracks the
granted mask exactly (14-15 MiB of a 16 MiB mask). Validity condition 3
(traffic ratio >= 1.5) is met by a wide margin at every size; the ratio's
absolute value is uninformative because the denominator is near zero.

Note `mbm_total` and `mbm_local` are nearly identical here even though the
victim's tables are on CXL node 2, so MBM on this part is not separating
expander traffic. Recorded as an instrument limitation, not used for any claim.

## Operating point: N = 2M, not 4M

Amendment 2 named b4M as the largest size under the 60%-of-LLC occupancy
ceiling declared in §2, computed from the **predicted** occupancy of 182 MiB
(57%). The **measured** occupancy is 193 MiB (61%), which the same ceiling
excludes. Applying the unchanged rule to the measured value gives:

- admissible under the ceiling: b500K (19%), b1M (30%), b2M (43%);
- all three clear the gate;
- **largest admissible: N = 2M**, R = 76 MiB, occupancy 138 MiB, gate 2.354x.

This is the pre-declared rule applied to a measured input, not a new rule. It
is worth recording that b4M -- the point Amendment 2 would have used -- is also
the **only admitted size that fails the gate** (1.769x), so had the predicted
occupancy been used the co-run would have been sited at the one operating point
where a capacity-mediated tax was near-impossible. Predicting occupancy instead
of measuring it would have wasted the campaign.

b3M and b4M are excluded by the ceiling and are reported in the curve but not
carried forward. Their exclusion is not outcome-driven: b3M *passes* the gate at
2.298x and is still excluded.

## What the co-run now tests

At N = 2M the capacity-mediated ceiling is 2.354x, measured quiescently. The
co-run asks whether a **real streamer** realises any of it, and specifically
whether the matched-bandwidth pairs of §4 separate allocation from bandwidth.
`flushbehind` is dropped on Intel: `amd_flushbehind_aggressor` is AMD-only.
Seven arms x 10 repetitions, fixed seeded interleave.

---

# Amendment 4, 2026-08-21 — the AMD arms, rewritten around a measured fact about PREFETCHNTA

Made **before any AMD arm of this campaign.** `moscxl` was frozen first
(`bergamo_freeze.sh`, commit `d8eda44`): all 512 CPUs on the `performance`
governor, `cpufreq/boost=0`, `numa_balancing=0`, THP `madvise`. The host was
clocking 3.0999 GHz as found and holds 2.2486 GHz frozen.

Everything below comes from aggressor characterisation with **no victim
present**, which §3 already establishes as instrument characterisation rather
than an arm.

## A4.1 `PREFETCHNTA` does not avoid L3 allocation on Zen4c, and this is measured, not assumed

§4's whole de-confound rests on `wb_prefetchnta` being a non-allocating arm.
That is true on the Intel hosts and **false here.** Four threads on cores
9--12, streaming from CXL node 2, with the streamer's own CCX-L3 occupancy read
from CMT after a 20 s settle:

| aggressor | streamer L3 occupancy | fraction of the 16 MiB CCX | self-reported BW |
|---|---:|---:|---:|
| `wb_load -t 4` | 15.98 MiB | 99.9% | 23.31 GB/s |
| `wb_prefetchnta -t 4` | **16.00 MiB** | **100%** | 23.98 GB/s |
| `amd_flushbehind_aggressor -t 4 -f 0` | 16.00 MiB | 100% | 22.92 GB/s |
| `amd_flushbehind_aggressor -t 4 -f 256` | **0.88 MiB** | **5.5%** | 16.14 GB/s |

All four rows are from the one sweep in `~/amd_char.jsonl` so that nothing in
this amendment mixes artifacts. An earlier exploratory run of the same
configuration read 1.47 MiB for the `-f 256` row rather than 0.88 MiB; the
flushing arm's occupancy is small and correspondingly noisy (0.24--0.88 MiB
across t = 1..7, with no monotone trend), which is expected of a quantity near
zero and is not a discrepancy that matters at this resolution. The allocating
rows do not move at all.

The full thread sweep sharpens this rather than simply confirming it, and one
detail must be stated because the four-thread row above hides it. **NTA is not
completely inert on Zen4c at one thread**: it holds 9.94 MiB, 62% of the CCX,
against `wb_load`'s 16.00 MiB. From two threads up the reduction is gone —
15.80, 15.86, 16.00, 15.80, 15.96, 15.99 MiB at t = 2..7. So the hint does
something at the lowest possible pressure and nothing at the pressure every arm
in this campaign actually runs at, and even at its most effective it leaves the
streamer holding **62%** of the shared cache against flush-behind's 1.5--5.5%.
It is not a non-allocating arm at any thread count, and certainly not at the
saturated one.

The bandwidth curves say the same thing independently. On `mos181`,
`wb_prefetchnta` moves 41% less than `wb_load` at one thread (6.06 vs
10.31 GB/s) and 28% less at saturation — the cost of honouring the hint. On
`moscxl` NTA is *faster* than `wb_load` at every thread count (13.63 vs 12.85
at t = 1; 24.68 vs 24.72 at t = 7, within noise) — the signature of a hint
being dropped rather than paid for.

**Consequence, declared now.** `NTA_sat` and `NTA_lo` are not non-allocating
arms on this host. They **yield no verdict** on AMD and may not be reported as
a recovery result, and outcome 2 of §6 **cannot fire from them here**: two arms
that both allocate being indistinguishable is not evidence that the tax is
bandwidth-mediated. They are retained, at 10 repetitions each, as a *declared
negative control* — an arm the mechanism predicts will not recover on this
microarchitecture. If they nevertheless recover, the mechanism is wrong, and
that is worth the cost of running them.

## A4.2 Flush-behind is the only non-allocating arm on AMD, and it comes with a better control than any Intel arm had

`amd_flushbehind_aggressor -f 256` cuts the streamer's footprint from 16.00 to
1.47 MiB while running the same code over the same buffers. Setting `-f 0`
disables the flushing and restores full occupancy. That gives a **within-binary
pair** — same binary, same access pattern, same allocation of threads to cores,
one bit of behaviour changed — which is a tighter control than the cross-mode
`wb_load` / `wb_prefetchnta` pairing the Intel campaign had to use. `f0` and
`f256` are therefore both first-class arms here, not just `f256`.

## A4.3 The CCX has eight cores, so `-t 8` is not expressible

`mos181`'s aggressor set is eight cores in one L3 domain and the victim sits in
another. On `moscxl` the L3 domain **is** the CCX: cpus 8--15 (plus SMT
siblings 264--271) share L3 id 1, and cpu8 is the victim. Seven cores remain.
Every arm specified at `-t 8` becomes `-t 7` here. SMT siblings are not
recruited to reach eight: they share the victim's 1 MiB private L2, which would
convert a shared-cache experiment into an L2 experiment.

## A4.4 Outcomes for the AMD arms, declared now

§6's outcomes are written around the `wb_load` / `wb_prefetchnta` pair and do
not transfer unchanged. For AMD:

1. **`FB256` tax materially below its bandwidth-matched `wb_load` partner, with
   a paired interval excluding zero.** Allocation is implicated on AMD as it is
   on Intel, and on a microarchitecture whose L3 is a victim cache with no
   reuse-aware insertion.
2. **`FB256` and its bandwidth-matched partner within measurement error.** On
   this host the tax is bandwidth-mediated, not allocation-mediated. Reported as
   such, and the Intel result would then be vendor-specific rather than general.
3. **`NTA_sat` recovers anything at all.** The mechanism is wrong, because A4.1
   measured that arm holding the entire CCX L3.
4. **`FB0` and `FB256` indistinguishable.** The within-binary control fails,
   and no AMD verdict may be drawn from either.
5. **No build size satisfies §2 on this host**, or CoV > 5%, or bimodal loaded
   distributions. No AMD verdict; not a vendor null.

One asymmetry with the Intel campaign must be stated wherever an AMD number is
quoted. On Intel the matched pairs held bandwidth fixed and let core count
differ, with the write-back arm using *fewer* cores, so its excess tax was
understated. Here the same conservatism runs the other way: the recovery arm
will need *more* cores than its write-back partner to reach the same bandwidth,
which if anything overstates the recovery arm's tax and so **understates its
recovery.** Both campaigns are conservative; they are conservative by different
mechanisms, and neither may be quoted as a point estimate of allocation's
contribution.

## A4.5 The bandwidth-matched pair, and why it is built backwards on this host

Full victimless sweep, cores 9--15 of the victim's CCX, streaming from CXL
node 2, 40 s runs with a 22 s settle and a 12 s window (`~/amd_char.jsonl`).
Self-reported bandwidth (GB/s) above, streamer CCX-L3 occupancy (MiB) below:

| threads | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `wb_load` | 12.85 | 21.80 | 23.99 | 23.31 | 24.12 | 24.39 | 24.72 |
| | 16.00 | 15.98 | 16.00 | 15.98 | 15.92 | 15.99 | 16.00 |
| `wb_prefetchnta` | 13.63 | 22.45 | 24.57 | 23.98 | 24.11 | 24.35 | 24.68 |
| | 9.94 | 15.80 | 15.86 | 16.00 | 15.80 | 15.96 | 15.99 |
| `flushbehind -f 0` | 12.88 | 21.52 | 23.66 | 22.92 | 23.98 | 24.32 | 24.69 |
| | 16.00 | 16.00 | 16.00 | 16.00 | 15.99 | 15.99 | 16.00 |
| `flushbehind -f 256` | 5.64 | 11.13 | 15.39 | 16.14 | 15.77 | 16.71 | 17.01 |
| | 0.35 | 0.69 | 0.87 | 0.88 | 0.73 | 0.45 | 0.24 |

Two facts in this table decide the pair, and neither was known when §5 was
written.

**Flush-behind cannot be brought up to write-back's rate.** It saturates near
16--17 GB/s, because the flush costs it roughly half its throughput per core,
while `wb_load` reaches 21.8 GB/s on *two* cores and 24.7 GB/s at seven. There
is no thread count at which the allocating arm can be held down to meet the
non-allocating one at its own saturated rate. The Intel campaign had the
opposite problem and solved it by giving the write-back arm fewer cores.

**`wb_load` has no expressible operating point between 12.85 and 21.80 GB/s.**
The CXL link saturates by three threads, so the whole usable range of the
allocating arm is two points: 12.85 (t = 1) and everything at or above 21.8.

So the pair is built backwards from the Intel construction. Rather than holding
bandwidth equal, the **non-allocating arm is deliberately given more of every
quantity that could plausibly mediate a tax**, and the question becomes whether
it still taxes the victim less:

| | `FB0_match` | `FB256_match` | ratio |
|---|---:|---:|---:|
| binary, access pattern | identical | identical | — |
| flag | `-f 0` | `-f 256` | one bit |
| threads / filling cores | 1 | 3 | **3.0x** |
| self bandwidth | 12.88 GB/s | 15.39 GB/s | **1.20x** |
| MBM total attributed | 12.92 GB/s | 30.84 GB/s | **2.39x** |
| streamer L3 occupancy | 16.00 MiB | 0.87 MiB | **0.054x** |

`FB256_match` carries more bandwidth, more attributed controller traffic, and
three times the filling cores. The only quantity on which it is *smaller* is
the one the paper is about. If it taxes the victim less under those handicaps,
no bandwidth or core-count account is available, and the measured recovery is a
**lower bound** on allocation's contribution.

`WB_fbmatch` (`wb_load -t 1`, 12.85 GB/s) is added as a cross-binary check: it
sits within 0.3% of `FB0_match`'s 12.88 GB/s and allocates identically, so the
two should be indistinguishable. If they are not, the two binaries differ in
something other than flushing and the cross-binary pair must be discarded. This
is an instrument check and is declared as one; it is not a de-confound and no
result may be drawn from it.

`FB0_sat` / `FB256_sat` (both `-t 7`) are retained as the saturated
within-binary pair, but their bandwidths are **not** matched (24.69 vs
17.01 GB/s, in the non-allocating arm's favour). That pair is therefore
anti-conservative and may not be quoted on its own; it is reported only
alongside `FB0_match` / `FB256_match`, which is the primary AMD de-confound.

## A4.6 An unresolved ambiguity in what MBM counts under `clflushopt`

`flushbehind -f 256` reports memory-controller traffic **exactly 2.00x** its
own read rate at every thread count (2.002, 2.003, 2.003, 2.001, 2.062, 2.003,
2.004 at t = 1..7; the same ratio for `-f 0` is 1.003--1.004 throughout). Six
of the seven sit within 0.2% of exactly 2, which is too tight to be
statistical, and it is not
write traffic: the kernel is a pure `_mm256_load_si256` sweep, so `clflushopt`
retires against clean lines and produces no writeback. `-f 0` shows no such
factor (12.92 against 12.88 at t = 1).

Two readings are available and this campaign cannot separate them.

- **It is real.** Every line crosses the fabric twice, and flush-behind
  genuinely costs twice the DRAM traffic per useful byte. This is consistent
  with its halved per-core throughput.
- **It is attribution.** MBM charges the RMID one 64-byte unit per
  `clflushopt`-generated fabric transaction — an invalidate probe carrying no
  data. There is exactly one `clflushopt` per line, which is exactly the one
  extra unit per line observed, and this coincidence is what makes the reading
  hard to dismiss.

`moscxl` exposes no Data Fabric or UMC PMU (`/sys/bus/event_source/devices`
has no `amd_df*` or `amd_umc*`), so there is no independent counter on this
host to adjudicate against. **The question is left open and no claim is built
on the 2.00x figure.** In particular, the Intel finding that flush-behind moves
*more* total controller traffic than write-back while taxing the victim far
less may not be restated on AMD from this number.

It does not affect A4.5. Under the "real" reading `FB256_match` has 2.39x its
partner's controller traffic; under the "attribution" reading it has 1.20x, the
self-bandwidth ratio. The pair is conservative under both, which is why the
arm selection stands while the mechanism question does not.

## A4.7 `mos182`'s node-2 failure is a socket-affinity error, not a device defect

A5 gated every `mos182` node-2 arm behind a latency ladder that host fails,
its node-2 times running 2--4x node-0. The cause is now identified and it is
in the campaign's own configuration, not in the hardware.

| host | CXL node 2 distance from node 0 | from node 1 | victim cpu | victim package |
|---|---:|---:|---|---|
| `mos181` | **14** | 24 | 40 | 0 |
| `mos182` | 24 | **14** | 16 | 0 |

The two hosts hang their CXL memory off *opposite* sockets. On `mos181` the
victim and all eight aggressor cores sit in package 0, which is the near
socket, and the ladder reads 54.41 ns against 54.32 ns. On `mos182` the victim
(cpu16) and the aggressors (cpus 4--11) are also all in package 0 — which
there is the **far** socket. Every `mos182` node-2 access in the orphaned data
crossed the inter-socket link before reaching the CXL device.

The near socket on `mos182` is package 1, L3 domain 1 (cpus 32--63, 96--127).
Moving the victim and aggressors there is the fix. **No arm is unblocked by
this finding.** A5 stands as written: the ladder must actually be re-run and
must actually pass from package 1 before any `mos182` node-2 arm is taken. Two
things are needed first and neither is done — the host config in
`run_join_campaign.py` must move to package 1, and `latency_chase` on `mos182`
is built against a newer libc than that host provides (`GLIBC_2.38 not found`)
and must be rebuilt there. Recorded now so the gate is understood rather than
attributed to the device.

# Amendment 5, 2026-08-22 — what the AMD campaign is allowed to do next

The AMD co-run is complete and reduced in
`DUCKDB_JOIN_AMD_CORUN_OUTCOME.md`. Outcome 5 fired on CoV, so there is no AMD
verdict; outcome 3 fired against the mechanism. Both of the follow-ups this
implies are experiments whose result I can partly anticipate, and the
within-binary difference (+0.263) is already known. Everything below is
therefore declared before the measurements, per §6.6.

*(Numbering note: Amendment 1 contains a bare `A5` about `mos182`. It is
unrelated to the `A5.x` items here, and still stands as written.)*

## A5.1 The re-run may not lengthen the query, and a first-draft remedy is withdrawn

The first draft of the outcome document proposed recovering timing resolution
by raising `probe_rows`, reasoning that `R(N) = 40N` is build-side only so no
validity condition would move. **Withdrawn, on two independent grounds.**

**A2 forbids it in terms** — "timing resolution lost to the shorter probe is
recovered by raising the in-invocation query count, not by lengthening the
probe" — because P was sized to about 12% of LLC precisely so the victim would
stop competing with its own scan for the cache it is being measured on. On
`moscxl`, P = 250K is 2 MB against a 16 MiB CCX. Raising it tenfold reinstates
the exact defect A2 was written to remove.

**And it targets the wrong variance component.** The dispersion is
between-invocation. In every arm the observed CoV across repetition medians is
4.5x to 12x the standard error of a median of 300 draws — `FB256_match` 13.10%
against 1.41% predicted, `FB0_match` 7.83% against 0.86%, `WB_fbmatch` 5.68%
against 0.58%. Averaged over 300 queries the 1 ms timer leaves a half-quantum
floor of 1.2--1.4% in those arms, about a ninth of what is observed. Lengthening
the query — by probe *or* by query count — shrinks a term that is already
negligible.

**Binding for any re-run at this operating point:**

1. `probe_rows` stays at the A2 value. `QUERIES` may not be raised as a
   dispersion remedy either.
2. No re-run until A5.2's diagnostic has a declared answer.
3. The re-run keeps N = 100K, the nine arms, and the interleave. If a verdict
   is drawn it must name which change produced the lower CoV.
4. **If the between-invocation spread proves uncontrollable, that is the
   result.** "A 16 MiB CCX cannot host this victim at a stable operating point"
   is reported as a finding, not treated as a failed run to be retuned. This is
   declared now so that the option of continuing to tune is closed.

## A5.2 Diagnostic for the between-invocation spread, with its decision rule

Each repetition is a fresh DuckDB process building a fresh hash table, and the
L3 is physically indexed, so one candidate is that the physical pages an
invocation receives fix how well its reused set coexists with the streamer for
that invocation's lifetime. Consistent with this, occupancy reaches its level
by the first 0.25 s sample and holds — `FB256_match` inv5 sits at 6.0 MiB mean
for the whole invocation against 7.0--7.4 for the other nine — so there is no
warm-up transient to gate on. **This is a hypothesis and nothing measured so far
tests it.**

Measurement: repeat one arm (`FB256_match`, the worst) with the victim's build
arena pre-faulted from hugepages, 10 repetitions, everything else identical.

Declared in advance:

- **Between-invocation occupancy spread falls below 3%** (against 6.2% measured
  here) **and CoV_rep falls below 5%** → page placement is the driver and is
  controllable. The re-run of A5.1 proceeds with hugepages declared as part of
  the operating point, and the change is named in the result.
- **Spread and CoV both essentially unchanged** → page placement is not the
  driver. No further tuning; A5.1 clause 4 applies and the instability is
  reported as physical.
- **Anything between** → no conclusion, and no re-run. An ambiguous diagnostic
  does not license proceeding.

Hugepages change the victim's TLB behaviour as well as its page colouring, so a
pass here identifies a *controllable* cause, not specifically colouring. That
distinction must survive into whatever is written.

## A5.3 The NTA discrimination, and what each result obliges

Outcome 3 fired: `NTA_sat` recovered +2.897 [+2.845, +2.992] against `WB_sat`
at equal cores and 1.2% more bandwidth, where A4.1 declared it a negative
control that must not recover. Per A4.1 the consequence is that the mechanism is
wrong. Before accepting that, one premise is testable: A4.1 measured streamer
occupancy **with no victim present**, and occupancy in an uncontended cache
cannot distinguish MRU from LRU insertion — both fill an idle L3 to 16.00 MiB.

Measurement: CMT on the *streamer's* monitoring group during co-run, `NTA_sat`
and `WB_sat`, same cores, same bandwidths, 10 repetitions. Cheap, does not touch
the victim campaign, does not disturb the frozen host state, and should be done
before A5.2.

Declared in advance, with the threshold fixed now:

- **NTA streamer occupancy under co-run is ≥ 50% of `wb_load`'s** → A4.1's
  premise holds under competition. NTA allocates and recovered anyway. **The
  mechanism as stated is wrong**, this is a serious negative for the paper, and
  it is reported in those words.
- **NTA streamer occupancy is < 50% of `wb_load`'s** → A4.1's victimless sweep
  did not measure what it was taken to measure. Outcome 3's inference does not
  go through. Two things follow, and the second is not optional: NTA is
  partially non-allocating *under competition* on this host, **and every other
  conclusion in this project drawn from a victimless occupancy sweep must be
  re-examined**, A4.1 included.
- Either way this **does not convert into a positive result.** The best
  available outcome is that a declared negative does not fire. The AMD
  de-confound remains governed by outcome 5 and by A5.1.

## A5.4 The same blind spot exists on Intel, and the headline de-confound rests on it

A5.3 exists because A4.1 measured `wb_prefetchnta`'s occupancy with no victim
present, and an idle cache fills to capacity under any insertion policy. That
criticism is not specific to AMD. **No streamer-side occupancy was ever
measured under co-run on `mos181` either.** The Intel de-confound reported in
`DUCKDB_JOIN_CORUN_OUTCOME.md` -- +0.058 [+0.047, +0.071] at ~18 GB/s and
+0.093 [+0.089, +0.097] at ~10.8 GB/s -- is the project's headline causal
result, and its non-allocating arm has never been shown to be non-allocating
while something was competing with it.

The Intel evidence for the hint being honoured is real but indirect: on
`mos181` `wb_prefetchnta` moves 41% less than `wb_load` at one thread and 28%
less at saturation, which is the signature of a hint being paid for rather than
dropped, and victim occupancy is far higher under the NTA arms (126 MiB against
67 MiB). Neither is a measurement of what the streamer holds. Both are
consistent with a streamer that allocates and yields, which is exactly what
Zen4c turned out to do.

Measurement: identical instrument to A5.3, on `mos181`, arms `WB_match_hi`,
`NTA_sat`, `WB_match_lo`, `NTA_lo`, plus `quiescent` so the artifact reproduces
the taxes it is being read against. 10 repetitions, `MODE=ntaintel` so nothing
appends to `join_corun_mos181.jsonl`.

**The ratio is taken within a declared pair, and this is the trap.** On AMD,
`WB_sat` and `NTA_sat` are a matched pair at 24.3 against 24.5 GB/s, so the
A5.3 ratio was `NTA_sat / WB_sat`. On Intel those same two arm names are 17.8
against 24.9 GB/s across 8 and 8 cores and are **not** a matched pair. The
Intel ratios are `NTA_sat / WB_match_hi` and `NTA_lo / WB_match_lo`. Computing
`NTA_sat / WB_sat` here would be the section 5.1 arm-identity error committed
in the reducer rather than in prose.

Declared in advance, with the threshold fixed now, applied to **both** pairs:

- **NTA streamer occupancy under co-run is < 25% of its matched `wb_load`
  partner's, in both pairs** -> the Intel non-allocating arm is non-allocating
  under competition. The Intel de-confound stands exactly as reported, and
  A5.3's result is a Zen4c insertion-policy divergence rather than a defect in
  the de-confound design. This is the only outcome under which the paper may
  keep describing `wb_prefetchnta` as a non-allocating arm, and then only on
  Intel.
- **>= 25% in either pair** -> the Intel arms differ from the AMD ones in
  degree and not in kind. The de-confound then contrasts *less* allocation
  against *more*, not allocation against none. Every recovery and de-confound
  figure in `DUCKDB_JOIN_CORUN_OUTCOME.md` must be relabelled on that basis,
  and no host in this project retains a demonstrated non-allocating arm except
  AMD flush-behind.

The threshold is 25% because the project already has both reference points.
Flush-behind on AMD reads 5.5% of its CCX and is what this project means by
non-allocating; A4.1 rejected 62% as "not a non-allocating arm at any thread
count." 25% is four times the flush-behind reference and well under the level
already rejected, so it does not sit near either anchor.

**This cannot convert into a positive result.** A pass leaves the Intel
de-confound where it already was; a failure removes it. As in A5.3, the best
available outcome is that a declared negative does not fire. `mos181` is frozen
and this measurement does not change it: it adds a monitoring group read, and
runs the same arms at the same operating point that campaign already used.

# Amendment 6, 2026-08-22 — the AMD re-run, with the outlier rule fixed before any repetition exists

## A6.0 What licenses this, stated accurately

**A5.2 does not license it.** A5.2's declared rule was "anything between -> no
conclusion, **and no re-run**," and its own validity condition fired: the
contemporaneous control read CoV_rep 4.28% against the historical 13.10% it was
supposed to reproduce, 67% relative, so the "unchanged -> physical" branch is
void. Nothing in `DUCKDB_JOIN_A52_OUTCOME.md` clears a re-run and this amendment
does not pretend otherwise.

The re-run is taken **on the lead's instruction**, as a decision about whether
the AMD de-confound exists, which `DUCKDB_JOIN_A52_OUTCOME.md` put to the lead
rather than taking. It is therefore constrained more tightly than a
diagnostic-cleared re-run would be, and this amendment is the constraint. The
within-binary difference **+0.263 [+0.179, +0.420] is already known**, which is
precisely the §6.6 hazard — "fishing for a config that reproduces a published
number is not reconciliation" — so every rule below is fixed here, before the
first record exists, and the commit hash of this text is quoted in the outcome
document.

## A6.1 What the anomaly is, measured on the 150 AMD invocations that exist

Declared as the empirical basis for the design, from
`join_corun_moscxl.jsonl` (90), `join_nta_moscxl.jsonl` (20),
`join_thpctl_moscxl.jsonl` (20), `join_thp_moscxl.jsonl` (20).

**Incidence is 1.3%, not 5%.** Counting invocations whose median exceeds their
arm's median by >= 25%: exactly **2 of 150**, one in seventy-five.

| block | n | hits | which |
|---|---:|---:|---|
| campaign, night | 90 | 1 | `FB256_match` inv5, 1.38x |
| A5.3, day | 20 | 0 | -- |
| A5.2 control, day | 20 | 0 | -- |
| A5.2 hugepage, day | 20 | 1 | `quiescent` inv5, 1.43x |

Four properties, all of which the design below depends on:

1. **It occurs with no streamer running.** One of the two events is a quiescent
   arm on an idle frozen host. It is not a co-run operating point on a cliff.
2. **It is a whole-invocation state, not a transient.** In both events the
   warm-up query is *normal* — 0.0400 s against a 0.037--0.048 pool, and
   0.0340 s against 0.034--0.036 — and the 300 measured queries that follow are
   both shifted and widened (`FB256_match` inv5 p10/p90 = 0.0320/0.0690 against
   a normal 0.028--0.033 / 0.034--0.038). The invocation starts normal and does
   not recover.
3. **It is not what makes `FB0_match` disperse.** That arm's ten repetitions
   span 0.037--0.047 with no member over 1.13x, and its best leave-one-out CoV
   is 6.98%. Its dispersion is broad and intrinsic. **A6 forecasts that
   `FB0_match` fails the 5% CoV bar again, outliers or not**, and that forecast
   is recorded here so that an S3 pass cannot later be presented as a surprise.
4. **No independent marker distinguishes an anomalous invocation.** This was
   searched for before the rule was written, over every field in the record:
   warm-up time, wall-clock overhead outside the query stream, first-sample
   (victimless) occupancy, sample count, MBM totals, return code, stderr. The
   anomalous invocations are ordinary in all of them. They are visible **only**
   in runtime and in mean occupancy — and occupancy is the mediator of the
   effect being measured (r = -0.86, -0.61, -0.83 across three blocks), so
   keying an exclusion on it would bias the de-confound more directly than
   keying on runtime would. **There is nothing to exclude on that is not the
   outcome variable.** That fact, not a preference, determines A6.3.

## A6.2 The design, fixed

- **n = 30 repetitions**, up from 10. The only change from the campaign.
- **All nine arms**, unchanged: `quiescent`, `WB_sat`, `FB0_sat`, `WB_local`,
  `NTA_sat`, `FB256_sat`, `WB_fbmatch`, `FB0_match`, `FB256_match`. No arm is
  dropped, so no arm is selected. Cost at the campaign's measured 65.1 s per
  arm is **4.9 h** for 270 arms, which is affordable and is why nothing is
  trimmed for time.
- **N = 100K, chain8, `probe_rows` at the A2 value, `QUERIES` unchanged.**
  A5.1 clauses 1 and 3 are binding and are not touched.
- **No THP shim.** A5.2 showed page placement is not a controllable driver
  (5.69% against a contemporaneous 5.90%, needing < 3%). Running stock keeps
  the re-run comparable to the campaign.
- **Same fixed seeded interleave**, same hostguard, same per-arm exclusivity,
  same streamer settle gated on the streamer's own occupancy.
- **One contiguous night block beginning at 22:00 local**, the campaign's start
  hour. Time-of-day is the one confound A5.2 could not exclude; it is held at
  the campaign's value rather than varied. Incidence is additionally reported
  split by first and second half of the block, so drift within the night is
  visible at no extra cost, and against A5.2's 40 daytime invocations.
- **`moscxl` stays frozen at `d8eda44`.** The freeze is verified and its hash
  recorded in the log before the first arm.
- **Exactly one attempt.** If the block aborts, it is restarted from scratch at
  most once and the partial artifact is retained and reported. Completed
  repetitions from an aborted block are never merged into a later one.

**Raising n is not a dispersion remedy and may not be reported as one.** CoV_rep
is a property of the arm's per-invocation distribution, not of the sample size;
n changes only how precisely it is estimated. Declared now so that a lower
number at n = 30 cannot be narrated as a repair. Under A5.1 clause 3 — "a re-run
that lowers CoV must say which change did it" — the answer is fixed in advance:
**nothing was changed except n, so the only available explanation is that the
n = 10 estimate was imprecise.** With a tail at 1.3% incidence the n = 10
estimate is imprecise in both directions, and that is the whole of what a
movement means.

## A6.3 Rule O, the outlier rule, fixed here

**No repetition is excluded from the primary analysis for any reason relating
to its runtime, its occupancy, or its effect on any estimate. There is no
exclusion path that a slow repetition can take.** All 30 enter every declared
figure.

This is not conservatism for its own sake. Per A6.1 item 4 there is no marker to
exclude on except the outcome variable itself, and a rule that removes slow
repetitions from both arms of a *difference* still selects on the dependent
variable — it would shrink whichever arm happens to draw more anomalies, and the
de-confound is exactly a difference between two arms.

Three subordinate clauses, each fixed now:

1. **Voiding is unchanged and is not exclusion.** A repetition is void, and
   re-run, only on grounds already in the protocol and detectable without
   looking at the timing: hostguard abort, `valid: false`, a failed
   per-repetition bandwidth assertion (§5), or a missing counter series. Voids
   are counted and reported.
2. **One secondary, symmetric, fixed-count trim.** Drop the single fastest and
   the single slowest repetition of each arm — 2 of 30, one from each end,
   every arm identically. For a paired *difference* the same one-from-each-end
   trim is taken on the per-repetition difference series instead, so that
   pairing is never broken. The trimmed figures are reported **beside** the
   untrimmed ones, never in place of them. It is symmetric, so it cannot
   preferentially remove slow repetitions; it bounds any single repetition's
   leverage and nothing more. **No verdict may rest on it**, and the CoV bar is
   applied to the untrimmed figure only.
3. **Anomaly incidence is a reported quantity, not a filter.** Count of
   repetitions whose median is >= 1.25x their arm's median, per arm and per
   half-block. The 1.25 threshold is set from the 150 existing invocations,
   where the normal maximum is 1.13x and the two events are 1.38x and 1.43x;
   it is descriptive, it separates nothing that is close, and no verdict
   rests on it either.

## A6.4 The bars, and what each outcome obliges

Three checks. **S3 is the original bar and is not weakened, replaced, or
reinterpreted.** S1 and S2 are additional and can only ever license a *weaker*
statement than S3 would.

- **S3 (the §6 outcome-5 bar, unchanged).** CoV across repetition medians
  < 5%, untrimmed, on both members of the primary pair (`FB0_match`,
  `FB256_match`).
- **S1 (sign stability).** The sign of both matched-pair differences is the
  same in all 30 leave-one-out estimates.
- **S2 (point stability).** The leave-one-out range of each matched-pair
  difference is <= 20% of its point estimate. **The campaign already meets
  this** — +0.250 to +0.276 on +0.263 is 9.9% — which is why the outcome
  document called the effect "probably real." Declaring a bar the existing data
  already passes is stated plainly rather than presented as a hurdle.

**S3 passes.** Outcome 5 is lifted for this host and a verdict may be drawn. It
must be reported together with A6.2's fixed sentence: nothing changed but n, so
the n = 10 CoV estimate was imprecise and the operating point was not repaired.

**S3 fails, S1 and S2 both pass.** The declared result, in these words fixed in
advance:

> The AMD host remains under §6 outcome 5 and yields **no verdict**. It may not
> be quoted as a vendor null either. What 30 repetitions add is that the
> within-binary difference is *stable* under resampling at this operating point
> while its interval is not trustworthy: the point estimate is D with a
> leave-one-out range of R, and the sign does not turn. That is a bounded
> observation about a host that fails its stability bar, it is not a
> de-confound, and it does not enter the paper as a result.

**S1 or S2 fails.** The difference is not stable and the campaign's +0.263 does
not survive replication. Reported as such, prominently, and
`DUCKDB_JOIN_AMD_CORUN_OUTCOME.md` is amended at the point of use.

**In every branch the result is reported whether or not any bar clears, and the
outcome document is written before any figure is quoted elsewhere.** Per A5.1
clause 4, if the spread is again uncontrollable that *is* the finding — "a
16 MiB CCX cannot host this victim at a stable operating point" — reported as a
result and not retuned around. **There is no third campaign at this operating
point.**

## A6.5 What this cannot do

It cannot resurrect the AMD de-confound to full standing, and it is not designed
to. The best available outcome above S3 is a bounded non-verdict. It also does
not disturb two things already settled: A5.3's finding that `PREFETCHNTA`
allocates under competition (0.884, threshold 0.50) stands whatever this
returns, and **A5.2 did not retract outcome 5** — `FB0_match` sits at 6.98% on
its best leave-one-out and is broadly dispersed, so the CoV trigger was never
carried by one repetition alone.

Any consequence for **L5**, for the paper's page-1 evidentiary posture, or for
whether an AMD number appears at all remains a **§9 lead-only decision** and is
not taken here.

## A6.6 Reduction, committed before the data

`summarize_corun.py` is used **unchanged**, at its existing seed. Stability is
computed by `summarize_stability.py`, committed in the same commit as this
amendment and before the first record exists. It implements S1, S2, S3, the
Rule O clause 2 trim, and the Rule O clause 3 incidence count, and it prints the
branch of A6.4 that fires rather than leaving the mapping to the reader.
