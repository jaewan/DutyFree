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
