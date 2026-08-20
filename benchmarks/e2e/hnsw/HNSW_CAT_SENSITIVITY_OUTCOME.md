# Outcome: HNSW CAT capacity-sensitivity gate

Dated 2026-08-21. Ran after `../gapbs/GAPBS_CAT_SENSITIVITY_OUTCOME.md`, against
the rule and the four outcomes declared in
`HNSW_CAT_SENSITIVITY_PREREGISTRATION.md` before any HNSW measurement existed.
No streamer and no aggressor was launched.

## Result

`hnswlib` d9b3608 (v0.9.0). One million float32 vectors of dimension 128,
`M=16`, `efC=100`; a 660,565,344-byte index; 10,000 `searchKnn` queries at
`ef=64`, `k=10` per trial; seven trials, first discarded, six measured; three
invocations per mask.

| host | LLC / ways | full | min | full median | min median | ratio | pass |
|---|---|---:|---:|---:|---:|---:|---|
| `mos182` (8462Y+) | 60 MiB / 15 | 60 MiB | 4 MiB | 1.712451 s | 2.269547 s | **1.325** | fail |
| `moscxl` (EPYC 9754) | 16 MiB / 16 | 16 MiB | 1 MiB | 2.069736 s | 2.601822 s | **1.257** | fail |
| `mos181` (8592+) | 320 MiB / 20 | 320 MiB | 16 MiB | -- | -- | -- | pending |

CoV was 0.098--0.230%, two orders of magnitude inside the 5% bound, and the
even measured count showed no alternation of the kind PageRank exhibits on
`moscxl`.

**This is pre-registered falsifiable outcome 3: HNSW fails everywhere,
including AMD.** PageRank at g21 on `moscxl` remains the only victim
configuration that has passed a capacity-sensitivity gate.

## Why it fails, and why that is not a null

The gate worked. CMT occupancy tracked the granted mask exactly -- 59 MiB of
60, 3 of 4, 14--15 of 16, 1 of 1 -- and denying the cache moved real traffic:

| host | mask | occupancy | local traffic over six trials | runtime |
|---|---|---:|---:|---:|
| `mos182` | 60 MiB | 59 MiB | 77.2 GB | 1.712 s |
| `mos182` | 4 MiB | 3 MiB | 142.1 GB (1.84x) | 2.270 s (1.33x) |
| `moscxl` | 16 MiB | 14 MiB | 166.7 GB | 2.070 s |
| `moscxl` | 1 MiB | 1 MiB | 200.4 GB (1.20x) | 2.602 s (1.26x) |

So on `mos182` a 60 MiB LLC **halves** HNSW's DRAM traffic and buys only a
third more runtime. The victim is not insensitive to cache because the cache
does nothing for it; it is insensitive because its misses overlap. HNSW issues
many independent proximity-graph hops, and the extra misses are absorbed by
memory-level parallelism rather than paid for in time. That is the same
mechanism that explained the gem5 fused null (task #22), observed here on
silicon and with the traffic measured rather than inferred.

The expectation this refutes is on the record: `../E2E_SESSION_PROMPT.md` §4.2
chose HNSW because it "reuses its upper layers heavily." It does -- but those
layers are a few hundred KB, so they survive even a 1 MiB mask, while the
630 MB of vector data below them is traversed too sparsely for LLC capacity to
matter. The reuse is real and in the wrong size range for CAT to act on it.

**The consequence for victim selection is general.** A capacity-sensitive
victim needs reuse in the size range the mechanism can act on *and* limited
ability to overlap the misses that removing it creates. HNSW has the first and
not the second. PageRank on a 16 MiB-per-CCX LLC has both.

## Two disclosures

**The index is not byte-identical across hosts, contrary to the
pre-registration.** The pre-registration required one index built once and
copied. Rebuilding on each host was tried first and produced different digests
-- `0a7759aa` on `mos182`, `c816b629` on `moscxl` -- because `-march=native`
selects different AVX-512 forms, which perturbs distance results, neighbour
choice, and hence the graph. A common ISA would not have fixed it either: the
three hosts carry gcc 15.2, 11.4 and 13.3. Copying the canonical index was
deferred rather than done, to avoid pushing 630 MB across `mos181` while a
gate was measuring on it, so each host queried its own locally built index of
identical size and parameters.

This is disclosed rather than repaired because it cannot carry the verdict:
both hosts miss a 2x bar by margins of 0.67x and 0.74x, and no plausible
difference in construction order moves a 1.26x ratio to 2.0x. The summariser
prints `index identical across hosts: False` rather than hiding it.

**PageRank's memory-traffic diagnostic is unusable; HNSW's is sound.** In the
GAPBS gate the `mbm_local_bytes` absolute values *decrease* across freshly
created groups (12,039,104,512 then 11,953,625,984) with per-trial deltas
around 1 KB against 14.8 MiB of occupancy. HNSW's are monotone, rise by a
regular ~27.8 GB per trial, and restart near zero for each new group. The
GAPBS gate created 18 groups back to back against 16 CLOSIDs where the HNSW
gate created 6, which is consistent with RMID recycling returning stale
counters. Only the diagnostic is affected: every trial time comes from the
victim's own output, so no verdict in either gate depends on MBM.

A hypothesis worth recording as *falsified*: block-buffered stdout was the
first suspected cause, and a timestamped pipe test refuted it -- GAPBS's lines
arrive in real time with or without `stdbuf -oL` (t+15.384, 15.978, 16.573 s
for 0.597 s trials). That test also confirms GAPBS's ready marker is not
delayed, so the co-run campaign's victim-first arrival ordering is safe.

**For the co-run campaign:** its pre-registration invalidates a run when "the
streamer has zero traffic." On AMD, under group churn, a zero or absurd MBM
delta can be an artifact rather than a real absence of traffic. The runner
should confirm the counter is live against a known-busy control before
declaring a run invalid, or it will discard good arms.
