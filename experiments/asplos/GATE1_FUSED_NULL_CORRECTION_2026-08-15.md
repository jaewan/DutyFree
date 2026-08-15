# #22 correction — the null is real, its stated cause is not; H2 works, the fused kernel cannot express it

Written 2026-08-15, correcting `GATE1_FUSED_NULL_FOLLOWUP_2026-08-15.md`
(commit `88d8edf`) after a red-team review of that commit and three new arms.

**The headline changes.** The follow-up concluded the fused null was "a
verified null: not an artifact of broken placement or under-sizing," and that
it "more rigorously CONFIRMS ... the same-thread fused tax lives mostly
outside the shared-LLC channel H2 addresses." The first half of that (the
placement fix) is correct and confirmed. The second half is not supported by
the data, and one arm it rests on was mis-sized and mislabelled.

What the new data shows: **H2 does protect a shared-cache-dependent hot table
— by 16.9% of its DRAM misses, at the one hot-table size where it can — and
that protection still does not move fused latency, because the fused kernel
runs 8x below the model's own bandwidth ceiling.** The null is a property of
the workload's memory-level parallelism, not evidence about where the tax
lives.

## 1. What was wrong in the previous document

### 1.1 The "10 MiB" arm was instantiated at 16 MiB

`table_capacity()` rounds up to the next power of two (`probe()` masks rather
than divides). `--hot-bytes 10485760` -> 655,360 entries -> rounded to
1,048,576 entries = **16,777,216 bytes**. The run log says so directly:

```
HOT_TABLE ... bytes=16777216 entries=1048576
```

So the arm recorded as "10 MiB, >=4x private L2" was 16 MiB — **3.2x the
modelled 5 MiB L3**, not a resize within the shared cache. This is a §5.1
arm-identity defect: the requested size was recorded, the instantiated size
was not. Fixed at the source in `fef3e5e` (prints `HOT_TABLE_ROUNDED`).

### 1.2 The 180x DRAM jump was read backwards

The follow-up cites it as "confirming the hot table is ... genuinely
dependent on the shared cache." High DRAM traffic means the hot table is
**overflowing** the shared cache. For this test those are opposites: a
working set that misses the L3 regardless cannot be rescued by protecting L3
capacity. The arm's own **-7.1%** HNF-fill number corroborates that H2
barely engages there — at 16 MiB the hot table's own fills swamp the
stream's.

### 1.3 Neither tested size was in the window where H2 can pay off

Instantiated geometry (`config.json`, not the command line): private L2 =
2 MiB/core, shared L3 (HNF) = 5 MiB. The H2-protectable window is therefore
**(2 MiB, 5 MiB]** — the hot table must be too big for the private L2 (or it
never needs the L3) and small enough for the L3 (or protecting L3 capacity
cannot make it resident). 2 MiB sits *at* the lower bound; 16 MiB is 3.2x
above the upper. The matrix went from under-sized to over-sized, skipping the
window. **4 MiB is the only power of two strictly inside it.**

Note the window is narrow *because the modelled L3 is only 2.5x the private
L2*. On the real 8592+ that ratio is 160x (320 MiB / 2 MiB). §5.2's
"resize to >=4x private L2" heuristic — which the follow-up followed — is
self-defeating in this config: 4x private L2 = 8 MiB already exceeds the L3.
The heuristic was written for the cross-core case and does not transfer to
this model's compressed hierarchy.

## 2. The new arm, pre-registered

Predictions were recorded before the runs landed (primary metric
`mem_ctrls0.bytesRead`, since the hot table is the only large object on pool
0, while `active_cycles_per_access` averages the whole fused loop). All three
resolved:

| prediction | threshold | result | outcome |
|---|---|---|---|
| P1 H2 cuts DRAM reads at 4 MiB | >15% (falsified <5%) | **-16.9%** | confirmed |
| P2 HNF fill cut lands well above the 16 MiB value | >-20% | **-59.6%** | confirmed |
| P3 cyc/acc moves less than DRAM-read % | — | -0.6% vs -16.9% | confirmed |

P1 cleared its threshold by only 1.9 points. See §5 on why that margin is
not well bounded.

## 3. The full matrix, from instantiated state

All six arms: gem5 `3d0d1ca2` (clean), DutyFree `88d8edf`, bench binary
sha256 `917413d5...`, `--reps 3 --warmups 1`, fact = 16 MiB on pool 1 (CXL,
203 ns), hot table on pool 0 (DRAM, 98 ns), single fused thread.

| hot (instantiated) | policy | DRAM read MB | CXL read MB | HNF fills | L3 hit% | cyc/acc | mem reqs |
|---|---|---:|---:|---:|---:|---:|---:|
| 2 MiB | wb | 5.25 | 67.68 | 1,136,303 | 6.3 | 58.706 | 1,473,446 |
| 2 MiB | stream | 5.20 | 53.97 | 356,951 | 7.0 | 58.374 | 1,181,163 |
| 4 MiB | wb | 12.09 | 66.76 | 1,340,360 | 53.6 | 72.428 | 1,698,024 |
| 4 MiB | stream | 10.05 | 61.52 | 542,011 | 53.9 | 71.993 | 1,540,396 |
| 16 MiB | wb | 945.18 | 67.89 | 15,970,551 | 33.9 | 123.725 | 16,992,524 |
| 16 MiB | stream | 923.23 | 67.89 | 14,842,644 | 35.1 | 122.553 | 16,649,534 |

Normalised to DRAM bytes per probe (3 reps x 1,048,576 probes), the three
sizes are three different physical situations, not three points on one curve:

- **2 MiB — 1.67 B/probe.** Essentially zero misses: the hot table never
  leaves the cache hierarchy (L2+L3 = 7 MiB). Nothing for H2 to protect.
  §5.2's collapse, now measured rather than hypothesised.
- **4 MiB — 3.84 B/probe, L3 hit rate 53.6%.** The hot table is genuinely
  L3-resident and L3-dependent. **This is the window**, and H2 protects it:
  DRAM misses -16.9%, HNF fills -59.6%.
- **16 MiB — 300 B/probe (~4.7 lines).** Misses everywhere; the L2
  prefetcher issues 2.3M prefetches (vs 95K at 2 MiB), amplifying a random
  probe pattern into useless traffic. Unprotectable by construction.

So both previously-tested sizes were null **by construction, for opposite
reasons**, and neither tested the mechanism.

## 4. Why protection still does not become latency

It is not that H2 fails. It is that this workload cannot express it.

**Measured bandwidth ceiling.** Same binary, same config, `--mode
stream-smoke` (the probe chain removed):

| config | bandwidth |
|---|---|
| pure stream, WB | 4.17 GB/s |
| pure stream, H2 | **4.78 GB/s (+14.5%)** |
| fused hash-join | 0.52 GB/s |

The model reaches 4-5 GB/s — exactly the regime `Sec1`/`Sec2` argue about —
when the dependent probe chain is removed. The fused kernel gets **8x less**,
because it burns ~59 cycles per 16-byte tuple on hash + dependent probe
loads and therefore keeps only ~1.3 lines in flight against a 16-entry L1d
TBE budget. The MLP ceiling is 16 x 64 B / 203 ns = **5.04 GB/s**; the pure
stream reaches 83% (WB) and 95% (H2) of it, the fused kernel ~10%.

`SimpleMemory.bandwidth` is 2.0 ticks/byte (~500 GB/s) — effectively
unlimited — so neither arm is link-limited. The ceiling is MLP, not the link.
(An earlier version of this analysis argued from `avg_util` being <4%; that
was wrong — `avg_util` is message-buffer occupancy, and it stays under 1%
even at 4.17 GB/s. The MLP argument above replaces it.)

**Therefore:** an efficiency gain at the HNF has nothing to convert into for
a thread that never approaches the ceiling. The fused null follows from the
workload's own MLP and would reproduce at *any* hot-table size. Re-running
the fused matrix is the one option with no payoff.

## 5. What this means for the claims

**Retract:** "the mechanism doesn't help" / the null "more rigorously
CONFIRMS ... the fused tax lives mostly outside the shared-LLC channel."
The experiment cannot distinguish that hypothesis from "this configuration
was never in the regime where LLC admission matters," and the 4 MiB arm shows
the mechanism *does* help where it is able to.

**Keep:** the placement fix (`88d8edf`) is correct and independently
verified — `bindpool 4096/4096, 0 skipped`, `setstreaming 4096/4096 marked`,
fact 100% on the 203 ns controller. Pre-fix single-process runs are confirmed
to have had **zero** CXL traffic (`mem_ctrls1` carries only a power-state
line; gem5 suppresses zero-valued stats), while the two-process harness
(`h1bw3_m48_wb`: 52 MB entirely on `mem_ctrls1`) always placed correctly.

**Strengthen, but not yet in the paper:** H2 raises achieved stream bandwidth
**+14.5%** at a deliberately hostile 16-MSHR budget. This speaks directly to
the risk §31 of `PAPER_SESSION_PROMPT.md` names — that removing LLC staging
leaves the bandwidth claim resting on private MSHR/superqueue depth. Here it
does not degrade toward the demand-miss floor; it improves. That is a
reviewer-facing result, and it needs the provenance of §6 before it is cited.

**Do not act on** the previous document's recommendation to upgrade
`Sec5_Evaluation.tex:281-294`'s margin note. Its proposed wording ("shows H2
reducing LLC fills without reducing fused cost at either a collapsed or a
genuinely shared-cache-dependent hot-table size") rests on the mis-sized arm
and on the reversed reading in §1.2. The paper's existing "necessity, not
payoff" framing survives intact — and is now better supported, for a
different reason than the one currently given. Any rewrite is the lead's
call (§9).

## 6. A systemic gap this surfaced: no gem5 number has a variance estimate

`RUBY_RANDOMIZATION=1` enables message-buffer randomisation, but gem5's RNG
is re-seeded only when `SEED` is set (`se.py:312-318`), and no batch in this
project sets it. Consequence, verified empirically: **a re-run is
bit-identical.** RUN2 of the 2 MiB and 16 MiB arms reproduced RUN1 exactly
(1,136,303 / 356,951 / 15,970,551 / 14,842,644 HNF fills; 58.706 / 58.374 /
123.725 / 122.553 cyc/acc), at a cost of ~1.5 h x 4 cores for zero new
information.

So the follow-up's "n=3 per cell, CoV 0.09-1.64%" is three `--reps` sharing
one stochastic trajectory and one evolving cache state — not independent
samples. This is not specific to #22: **no gem5 number in this project
currently has a variance estimate**, including `tab:gem5`, `tab:sens` and
`tab:h1bw`.

### 6.1 Amendment (same day): `SEED` is not the variance lever

The paragraph above originally closed by recommending a `SEED` sweep. A
later control run falsifies that recommendation, and the correction matters
more than the original point.

An 18-run `SEED` sweep did produce differing results (CoV 0.023-0.34%), which
looked like a working variance mechanism. But a **control run at a fixed
seed, with byte-identical instantiated config** (l1d TBEs 64/16, l2 48/32,
verified from `config.json`), did **not** reproduce its counterpart: 562,510
vs 562,777 HNF fills, a 0.047% drift — the *same magnitude* as the cross-seed
spread at that cell (0.043%). So the variation is run-to-run
nondeterminism, not a seed-controlled quantity, and `SEED` cannot be shown to
be doing the work.

Reconciling this with the bit-identical RUN1/RUN2 above: those runs left
`SEED` unset, so `seedRandom()` was never called and the randomised paths
took a fixed trajectory. Setting `SEED` *enables* divergence but does not
make it reproducible.

Practical consequence, unchanged in direction and stronger in force: a
variance estimate is still obtainable, but by **repeated identical runs**,
not by a seed sweep — and any future claim of reproducibility for a gem5
number in this project must be demonstrated, not assumed from determinism.
Runs with randomisation enabled are not bit-reproducible even at a fixed
seed.

## 7. Hypotheses tested and refuted (recorded so they are not re-run)

While explaining a 21% CXL-traffic gap between the 2 MiB arms (WB moves more
data than H2 for provably identical work — identical `local_n`,
`matches_last_rep`):

- **Placement drift** (`setstreaming` self-allocates unmapped pages from the
  *default DRAM pool*, and is called only in the stream arm) — refuted:
  `4096/4096 pages marked`, `0 skipped`.
- **Back-invalidation** — refuted: `SnpCleanInvalid` 235 vs 220, three orders
  of magnitude too small for a 214K-line gap.
- **Prefetcher throttling under the STREAMING bit** — refuted: issue counts
  identical (8,314,929 vs 8,318,529); `queued.cc` only *propagates* the bit,
  never suppresses. H1 is honoured.
- **L2-path asymmetry** — refuted: L2 `reqOut` 820,079 vs 819,418, `datIn`
  3,006,422 vs 3,006,506.

**Actual cause**, with accounting that closes to the byte: the divergence is
entirely below the L2. Under WB the L3 fills with dead stream victims, which
(a) evicts lines that are then re-requested (+214,993 reads) and (b) forces
dirty-victim writebacks (+77,290 writes) = +292,283 memory requests. H2
removes both. `1,139,548 reads x 64 B` = 72,931,072 B = measured
DRAM+CXL bytes exactly.

Two incidental defects, both real: `--stream-count` is **silently inert**
under gem5 (the 4-8 independent-stream loop is inside `#ifdef __AVX2__` and
the gem5 target compiles without `-march=native`, so every gem5 stream
experiment runs one sequential stream); and `pfUseful` reads 0 in all arms
against millions of prefetches issued — the counter is not wired through the
Ruby path and must not be cited in either direction.

## 7.1 Resolved: H2's fill-suppression gap is prefetch-mediated

An MSHR sweep found H2's HNF fill suppression degrading with concurrency
(77.3% at `L1_MSHR`=16 -> 57.2% at 64), which would matter for every gem5 H2
claim if it were a protocol defect. It is not, and it is now localised.

Three hypotheses were refuted from instantiated state before the right one:
replacement-TBE starvation (raising `L1_REPL` 16->64 and `L2_REPL` 32->48
left suppression at 57.0-57.2%), prefetch *inheritance*, and prefetch
*volume* (L2 `pfIssued` **falls** 87% at depth 64 while the leak grows, so
volume is the wrong variable).

Decisive test — prefetchers disabled via `PF_OFF_CORES=0`, matched controls,
`--reps 1`, fact 16 MiB:

| prefetch | `L1_MSHR` | wb fills | stream fills | suppression |
|---|---:|---:|---:|---:|
| on | 16 | 528,103 | 298,486 | 43.5% |
| on | 64 | 528,243 | 356,235 | **32.6%** |
| off | 16 | 517,542 | 289,660 | **44.0%** |
| off | 64 | 517,542 | 289,659 | **44.0%** |

With prefetching off the depth-dependence disappears completely — stream
fills differ by **one line** across a 4x MSHR change. So the gap is entirely
prefetch-mediated: some prefetch-filled lines are not carrying the STREAMING
attribute into their private-cache entry, so their later clean victims arrive
at the HNF unmarked and allocate. The candidate site is the attribute chain
`tbe.isStreaming := in_msg.isStreaming` (`CHI-cache-actions.sm` ~263) ->
`cache_entry.isStreaming := tbe.isStreaming` (~3440) -> recovered on
replacement (~409): a locally generated prefetch does not arrive as an
incoming CHI request on `reqRdyPort`, and `tbe.is_local_pf` exists precisely
to distinguish that path. Confirming the exact line needs a protocol trace
and was not done.

**Direction of the error is conservative, which is why this does not
invalidate anything.** Under-enforcement means streaming lines that *should*
have bypassed the L3 instead filled it, so the model reports **less** H2
benefit than a correct implementation would. Every gem5 H2 magnitude in this
project is therefore a lower bound on this axis too, consistent with the
posture Gate 1 already established. All existing paper numbers also run at
the default `L1_MSHR`=16, the better-behaved end.

## 8. What would be worth doing next, in order

1. **MSHR-depth sweep of the pure-stream H2-vs-WB bandwidth** (16/32/64).
   The +14.5% result is currently a single point at 16 MSHRs; §31's risk note
   cites 32-64. This converts a byproduct into the direct answer to a named
   reviewer objection, in the regime the paper actually argues about. Cheap:
   ~37 min/run, embarrassingly parallel.
2. **`SEED` sweep** for a real variance estimate (§6) — paper-wide, not
   #22-specific.
3. **Not** more fused sizings. The window is now measured end to end
   (2 / 4 / 16 MiB) and the limiter is the workload's MLP.
