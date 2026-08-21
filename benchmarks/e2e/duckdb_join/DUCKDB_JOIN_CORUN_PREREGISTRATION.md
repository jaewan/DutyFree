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
