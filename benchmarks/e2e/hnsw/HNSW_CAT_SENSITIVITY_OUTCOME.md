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
| `mos181` (8592+) | 320 MB / 20 | 320 MiB | 16 MiB | 1.620751 s | 2.502836 s | **1.544** | fail |

CoV was 0.098--1.19%, inside the 5% bound, and the even measured count showed
no alternation of the kind PageRank exhibits on `moscxl`.

**The host ordering inverts against PageRank.** For PageRank `mos181` was the
least sensitive host of the three (1.311x at best) and here it is the most
(1.544x); `moscxl` was the only host to pass with PageRank (2.580x) and is the
least sensitive here (1.257x). Sensitivity is a property of the victim paired
with the host, not of either alone, which is worth stating because the
convenient summary -- "Intel absorbs it" -- is wrong.

**This is pre-registered falsifiable outcome 3: HNSW fails everywhere,
including AMD.** PageRank at g21 on `moscxl` remains the only victim
configuration that has passed a capacity-sensitivity gate.

## Why it fails, and why that is not a null

The gate worked. CMT occupancy tracked the granted mask exactly -- 59 MiB of
60, 3 of 4, 14--15 of 16, 1 of 1 -- and denying the cache moved real traffic:

| host | granted | occupancy | local traffic over six trials | traffic ratio | runtime ratio | time per traffic |
|---|---:|---:|---:|---:|---:|---:|
| `mos181` | 320 MiB | 305 MiB | 14.5 GB | 1.00 | 1.000 | -- |
| `mos181` | 16 MiB | 15 MiB | 122.7 GB | **8.44** | **1.543** | **0.18** |
| `mos182` | 60 MiB | 59 MiB | 77.2 GB | 1.00 | 1.000 | -- |
| `mos182` | 4 MiB | 3 MiB | 142.1 GB | 1.84 | 1.325 | 0.72 |
| `moscxl` | 16 MiB | 14 MiB | 166.7 GB | 1.00 | 1.000 | -- |
| `moscxl` | 1 MiB | 1 MiB | 200.4 GB | 1.20 | 1.257 | 1.05 |

The last column is the headline. `mos181`'s 320 MiB LLC holds essentially the
whole hot footprint -- 305 MiB of occupancy -- and cuts HNSW's DRAM traffic by
**8.44x**, from 122.7 GB to 14.5 GB. That enormous saving returns **1.54x** in
runtime. The ladder is monotone in LLC size: the larger the cache, the more
traffic it saves and the smaller the fraction of that saving which becomes
time, from 1.05 on a 16 MiB LLC to 0.18 on a 320 MiB one.

**Stated as a claim: capacity can remove 8.4x of a victim's DRAM traffic and
return 1.5x in time.** The victim is not insensitive to cache because the cache
does nothing for it -- it demonstrably does a great deal -- but because its
misses overlap. HNSW issues
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

This is also a caution the paper should absorb about its own tax figures rather
than only about victim choice: a large shared-cache tax requires a victim whose
misses serialise. Bandwidth saved is not time saved.

## Two disclosures

**The index is not byte-identical across hosts, contrary to the
pre-registration.** The pre-registration required one index built once and
copied. Rebuilding on each host was tried first and produced two distinct digests, not
three: `0a7759aa` on **both** `mos182` and `mos181`, and `c816b629` on
`moscxl`. Copying the canonical index was deferred rather than done, to avoid
pushing 630 MB across `mos181` while a gate was measuring on it, so each host
queried its own locally built index of identical size and parameters.

**A correction to this file's own first reasoning.** The divergence was
initially attributed partly to the three hosts carrying gcc 15.2, 11.4 and
13.3, with the inference that a common ISA "would not have fixed it either".
That inference is wrong, and `mos181`'s digest is what refutes it: gcc 15.2 on
the 8592+ produced a bit-identical index to gcc 11.4 on the 8462Y+. Compiler
version is not the variable. The variable is the SIMD path -- `-march=native`
selects different AVX-512 forms on Zen 4 than on Sapphire/Emerald Rapids,
perturbing distance results, neighbour choice and hence the graph. Compiling to
a common baseline such as `-march=x86-64-v3`, so that all three hosts take
hnswlib's AVX2 path, would very likely have produced one digest everywhere.
Byte-identity was cheaply achievable and this deviation was avoidable.

It is still disclosed rather than repaired, because it cannot carry the
verdict: the three hosts miss a 2x bar by 0.46x, 0.67x and 0.74x, and no
plausible difference in construction order moves a 1.26x ratio to 2.0x. The
two hosts that *do* share an index differ from each other by more (1.325x vs
1.544x) than any index effect could account for, which is itself evidence that
the graph's construction detail is not what these ratios turn on. The summariser
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
