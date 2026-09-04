# The dropped STREAMING attribute is fixed. The one-slice H2 cell is recovered; no published number needs revising.

One line was added to `prepareRequestRetry()` in
`gem5/src/mem/ruby/protocol/chi/CHI-cache-funcs.sm`. The one-slice H2 cell went
from 17,197 HNF fill bypasses and 1.8% engagement to **853,853 bypasses and
97.6% engagement** — a 49.7x increase — and is now certified against all four
gates of `H1BW_SLICE_BRACKET_PREREG_2026-09-03.md` where before it was VOID.
The `wb` control came back **bit-identical on every one of 11,166 simulated
quantities**, which is what licenses reading the other two cells at all.

Nothing already published moves. The full-system r6b/r6e campaigns behind the
P1 result ran at **exactly zero retries** — not "few", zero, established below
against gem5's `nozero` stat suppression — so the defect could not fire there,
and 130,864 bypasses / ~99.8% coverage stand unchanged. The 4- and 8-slice SE
H2 figures were depressed by the defect and are therefore lower bounds; the
ordering claim they support is unaffected in direction.

Two things came out that were not asked for and matter more than the fix. The
"96.0% engagement ceiling" from `H2_BYPASS_COLLAPSE_2026-09-03.md` §4 is **not
a fraction** — it is a constant ~4,408 un-bypassable clean evictions per core,
which reads 96.0% only at the denominator the 4- and 8-slice cells happen to
have (§4). And the slice bracket's answer is a **negative**: a buffer-capped
home node reproduces the archived magnitudes, but with H2 fully engaged the
H2-over-WB ratio *collapses* from 1.250x to 1.070x, and the arm ordering
inverts (§5). H2's mechanism works essentially perfectly at one slice and buys
almost nothing, because the binding constraint there is not LLC fills.

## 1. The diff

Committed as `b9c8714c93`, "CHI: carry isStreaming across the request retry path".

```diff
--- a/src/mem/ruby/protocol/chi/CHI-cache-funcs.sm
+++ b/src/mem/ruby/protocol/chi/CHI-cache-funcs.sm
@@ -741,6 +741,10 @@ void prepareRequestRetry(TBE tbe, CHIRequestMsg & out_msg) {
   out_msg.seqReq := tbe.seqReq;
   out_msg.is_local_pf := false;
   out_msg.is_remote_pf := tbe.is_local_pf || tbe.is_remote_pf;
+  // Must be copied here as well as in prepareRequest: the field defaults to
+  // false, so a retried request that omits it is affirmatively marked
+  // non-streaming and the HNF allocates a line H2 would have declined.
+  out_msg.isStreaming := tbe.isStreaming;
   out_msg.atomic_op.clear();
   out_msg.atomic_op.orMask(tbe.atomic_op);
 }
```

That is the whole protocol change. The comment states the constraint — that the
field defaults, so omission is not neutral — and not the history, which lives in
the commit message and in `H2_BYPASS_COLLAPSE_2026-09-03.md`.

### `prepareRequestRetryDVM()`: correctly absent, left unchanged

Decision: **do not add the field.** Not "harmless either way" — it is
unreachable, and the reason is checkable rather than plausible.

`tbe.isStreaming` has exactly two writers in the entire protocol directory:

| site | action | source of the value |
|---|---|---|
| `CHI-cache-actions.sm:273` | `Initiate_Request` | `in_msg.isStreaming` |
| `CHI-cache-actions.sm:430` | `Initiate_Replacement` | `cache_entry.isStreaming` |

Neither is on a DVM path: DVM transactions are initiated through the separate
`Initiate_*DVM` actions, which never touch the field, so a DVM TBE carries
`isStreaming` at its `false` default for its whole lifetime. Copying `false`
into a field that already defaults to `false` would be a no-op.

The three readers confirm it from the other end — all are guarded by `is_HN` on
the data/allocation path, which DVM never enters:

- `:291` `is_HN && tbe.isStreaming && is_invalid(cache_entry)` — the bypass counter
- `:3517` `enable_H3_streaming_bypass && is_HN && tbe.isStreaming`
- `:3542` `tbe.doCacheFill && !(is_HN && tbe.isStreaming)` — the allocation decision itself

So the omission is not an oversight of the same class; it is the field being
meaningless in that function. Adding it would have implied a DVM/streaming
interaction that does not exist. This rests on there being no DVM writer, which
is a fact about today's source rather than a structural guarantee, so it is
pinned by a test (§6) that fails if anyone adds one.

### Audit of the other reconstruction sites

Every site that builds a `CHIRequestMsg` from a TBE or forwards the attribute:

| site | carries `isStreaming` | correct? |
|---|---|---|
| `funcs:700` `prepareRequest` | yes | — |
| `funcs:747` `prepareRequestRetry` | **yes, after this fix** | was the defect |
| `funcs` `prepareRequestDVM` / `prepareRequestRetryDVM` | no | yes, per above |
| `actions:161`, `actions:252` sequencer -> `reqRdy` staging | yes, from `in_msg.isStreamingSet()` | — |
| `actions:3470` `cache_entry.isStreaming := tbe.isStreaming` | yes | the persistence hop `:430` reads back |

No other omission of this class exists. `prepareRequestRetry()` does still drop
`txnId` relative to `prepareRequest()`, and that is left alone deliberately:
`usesTxnId` is false for every memory transaction in this configuration, so port
lookup keys on address. It is recorded as a permitted omission in the test
rather than silently ignored, and it was not "fixed" because touching it would
have contaminated the `wb` bit-identity check in §3, which was worth more.

## 2. Build

Waited for all six `h1bw_mc_*_8c_l3x8_bwt{16,31}_20260904` runs to exit before
building; they were not signalled, read, or otherwise touched, and nothing under
`gem5/logs/` was modified.

Invocation taken from the campaign's own build record, not invented:
`scons build_Intel_8592/gem5.opt -j 192` (192 of 256 host threads, chosen after
the six runs freed their cores).

- `build_Intel_8592/gem5.opt` mtime **2026-09-04 12:51:05**, 984,361,288 bytes,
  tagged `build-cb290444`.
- SLICC re-ran: all 39 generated `.cc` under
  `build_Intel_8592/mem/ruby/protocol/CHI/` carry mtimes 12:44:04–12:44:08, one
  clean pass seven minutes before the link. The campaign binary was
  `build-cfd37207`.

### Provenance: the binary delta is larger than expected, and is measured inert

The brief anticipated one incidental difference (`ticks.py`). There are in fact
**five** commits between the campaign binary and this one:

| commit | subject | compiled in? |
|---|---|---|
| `b9c8714c93` | CHI: carry isStreaming across the request retry path | yes — the fix |
| `a5f366456e` | ticks: compare the magnitude of the rounding error | yes — the flagged one |
| `1bb6418e01` | m5 op 0x57 `flush_range`: an idealised flush-behind oracle | yes |
| `3bd36a0061` | fs checkpoint: bind a checkpoint to kernel/image/simulator | yes (`sim_object.{cc,hh}`) |
| `f3c2c84949` | fused: reset stats after the tenant's own init | no (`testcase/`, not this benchmark) |

`BUILD_PROVENANCE.md` had flagged the flush-behind oracle as *argued*
unreachable but not measured. It is now measured, and the reachability question
was not vacuous: the benchmark source does contain `gem5_flush_range()`, and the
`0f 04 57 00` opcode **is** present in the compiled
`cxl_join_bench.gem5` — it sits behind a runtime `policy == "fbo"` branch. None
of the three cells passes `--policy fbo` (no `--policy` flag at all, and the
string `fbo` appears nowhere in their manifests), so the byte never executes.
The benchmark binary is byte-identical across old and new runs
(`bench_sha256 cac9e27a...`).

The `wb` bit-identity in §3 closes this empirically for the whole delta at once:
every commit above except the `isStreaming` fix affects code paths the `wb` arm
exercises identically, so if any of them perturbed this workload, `wb` could not
have come back identical. It did. **The entire five-commit delta is inert on
these cells except through `isStreaming` on retried requests.**

On the `ticks.py` guard specifically — warning-only, as required. The change is
`err = (value - int_value) / value` to `err = abs(...) / value`; it feeds only a
`warn()` and no computed value. Confirmed two ways: `config.ini` is
byte-identical across old and new for every affected parameter, and `wb` is
bit-identical. It emits **six new `rounding error > tolerance` lines** in each
re-run cell's `console.log`, all from the `SimpleMemory.bandwidth` tick
quantization. The earlier certified cells do not have them. **This is expected
and is not a regression.**

## 3. The `wb` control is bit-identical

Comparing `h1bw_mc_wb_4c_l3x1_bwdef_20260904/stats.txt` against
`..._20260904fix/stats.txt`: 11,171 stat lines each, **5 differing lines, all
five host-side** — `hostSeconds`, `hostTickRate`, `hostMemory`, `hostInstRate`,
`hostOpRate`. Every one of the 11,166 simulated quantities is identical,
including `agg_bw_sum` to all nine printed digits (7.71428005 both times), all
1,604,202 HNF fills, and the 64.7% write-retry fraction.

No nondeterminism question arises, so no appeal to prior run-to-run variance
evidence was needed — the comparison came back exact rather than close. This is
the expected result for the right reason: `wb` never sets `isStreaming`, so
`tbe.isStreaming` is false on every retry, so the added line copies `false` over
a field already defaulting to `false`. A fix that changed `wb` would have been a
fix with a side effect.

## 4. What the fix bought

One-slice, 4-core cells. Retry fraction is the HNF write-retry fraction; the
engagement fraction is `E_clean` as defined in
`H2_BYPASS_COLLAPSE_2026-09-03.md` §4 (`WriteEvictFull` RU->I over RU-state
arrivals).

| cell | bypasses | HNF fills | retry | agg BW | `E_clean` |
|---|---|---|---|---|---|
| `wb` pre-fix | 0 | 1,604,202 | 64.7% | 7.714 GB/s | 0.0% |
| `wb` **fixed** | 0 | 1,604,202 | 64.7% | 7.714 GB/s | 0.0% |
| `h2` pre-fix (VOID) | 17,197 | 1,584,632 | 64.8% | 7.718 GB/s | 1.8% |
| `h2` **fixed** | **853,853** | **678,647** | 65.0% | **8.250 GB/s** | **97.6%** |
| `pfoff` pre-fix | 734,590 | 845,215 | 10.3% | 8.369 GB/s | 82.7% |
| `pfoff` **fixed** | 852,228 | 702,091 | 11.3% | 8.688 GB/s | 98.0% |

H2 now suppresses 57.7% of the `wb` arm's HNF fills, against 1.2% before. The
retry fraction is essentially unchanged (64.8% to 65.0%) — as it must be, since
retries are a transaction-buffer property and the fix changes what a retried
request *says*, not whether it is retried. `pfoff` also gained: it was already
mostly engaged at 82.7% because only 10.3% of its traffic retried, and the fix
recovered the rest.

The pre-registered falsification check inverted exactly as designed. The defect
signature — bypasses cannot exceed *non-retried* clean-evict arrivals, which
held in all fifteen pre-fix runs — now reads `VIOL` for both `h2` and `pfoff`
(853,465 and 851,968 bypasses against 32,453 and 726,075 non-retried arrivals)
and `ok` for `wb`, which has no streaming tags to carry. Reading `ok` on `h2`
here would have meant the fix did not take.

### The 96.0% ceiling is a count, not a fraction

The fixed H2 cell reads 97.6%, which is *above* the 96.0% "ceiling"
`H2_BYPASS_COLLAPSE_2026-09-03.md` §4 inferred from zero-retry cells. The
ceiling was misread there, and this is the correction: what is constant is the
absolute number of clean evictions that cannot be bypassed, at ~4,408 per core.

| cell | clean decisions | RU->I | residue | per core | `E_clean` |
|---|---|---|---|---|---|
| 4-slice 4c `pfoff` | 444,945 | 427,315 | 17,630 | **4,408** | 96.04% |
| 8-slice 8c `pfoff` | 885,053 | 849,785 | 35,268 | **4,408** | 96.02% |
| 1-slice 4c `pfoff` fixed | 869,701 | 851,968 | 17,733 | **4,433** | 97.96% |
| 1-slice 4c `h2` fixed | 874,726 | 853,465 | 21,261 | 5,315 | 97.57% |

Two cells with different core counts and different slice counts agree on
4,408/core to four significant figures. It reads as 96.0% there because those
cells see ~111k clean decisions per core; the one-slice cells see ~217k, so the
same residue is only 2.0% and the achievable ceiling rises to 97.96%.

So the honest statement is: **the achievable ceiling for this configuration is
98.0%, and the fixed H2 cell reaches 97.6% of arrivals, i.e. 99.6% of what is
achievable.** The remaining 0.39 pp gap against `pfoff` is 3,528 evictions, 882
per core, and is the prefetch-tagged tail — `h2` runs with the L2 prefetcher
enabled and `pfoff` does not, and a prefetched line arrives without the
STREAMING tag the demand path would have given it. That is a property of the
prefetcher's interaction with H2, not a residual defect.

## 5. The slice-bracket verdict, with H2 working

The campaign is now **COMPLETE: 3/3 cells certified** against all four gates
(pre-fix: 2/3, no claim licensed, because `h2` failed G5 — H2 did not engage).
Pre-declared predictions confirmed 2/3.

| prediction | result | 1 slice | 4 slices |
|---|---|---|---|
| `wb_4c` in 6.0–11.0 GB/s | **PASS** | 7.714 | 20.087 |
| `h2_4c` in 6.0–11.0 GB/s | **PASS** | 8.250 | 25.108 |
| `pfoff_4c` in 10.0–15.0 GB/s | **FAIL** | 8.688 | 13.274 |

**Does a single-slice, buffer-capped home node reproduce the archived ~7.7 GB/s
magnitudes with H2 working? Yes for `wb` and `h2`, both inside the pre-declared
band, and `wb` lands on 7.714 GB/s against the archive's ~7.7.** `pfoff` misses
its band low by 1.3 GB/s.

**What happens to the H2-over-WB ratio once H2 actually engages? It collapses.**

| | 1 slice | 4 slices |
|---|---|---|
| H2 / WB | **1.070x** | 1.250x |
| pfoff / WB | 1.127x | 0.661x |
| ordering | pfoff > h2 > wb | h2 > wb > pfoff |

This is the result worth carrying forward, and it is a negative. H2's *mechanism*
is near-perfect at one slice — 97.6% engagement, 57.7% of fills suppressed — and
it converts that into 7.0% of bandwidth, down from 25.0% at four slices. The
arm ordering inverts outright: `pfoff` goes from worst arm to best. The
pre-registration declared an inverted ordering possible in advance and reads it
as an informative negative and as evidence the archive was not buffer-capped.
Applying it as written: **at one slice the binding constraint is the HNF
transaction-buffer pool, not LLC fill traffic, so suppressing fills cannot buy
much.** 65% of writes retry; HNF occupancy is 82.7%; concurrency is pinned at
~26.5 lines in all three arms regardless of arm, and throughput follows
concurrency.

On the frozen interpretation table, honestly: WB and H2 do land in 6–11 GB/s,
but HNF TBE occupancy is 82.3–83.8%, which is neither "approaches 100%" (row 1)
nor "well below budget" (row 2). **The table does not cleanly adjudicate**, and
it is frozen, so it is not being rewritten to fit. The tiebreaker is the
write-retry fraction, which the pre-registration registered as a supplementary
measurement: at 64.7–65.0% for the two capped arms, the pool demonstrably binds,
which is row 1's mechanism arriving without row 1's stated signature. Mean
occupancy cannot approach 100% in a run with drain phases; the retry fraction is
the sharper instrument, and it is unambiguous. Row 1's *reading* therefore
holds — the archive measured a buffer-capped single-home-node regime and its
"CXL-path-limited" label named the wrong mechanism — but this rests on a
measurement the table did not nominate, and no paper sentence should rest on it
alone, per the pre-registration's own closing constraint.

## 6. Blast radius on published claims

### The full-system P1 result is unaffected. The retry fraction was zero.

`COMPLETE_JOIN_OUTCOME_2026-09-01.md` and the r6b/r6e records report ~130,864
HNF bypass events on H2 arms against exactly zero on WB, covering ~99.8% of an
8 MiB stream's lines. Checked all 19 `r6b`/`r6e` run directories under
`gem5/logs/fs_restore_chi/`: **`retryTriggerQueue` does not appear in any of
their `stats.txt` files.**

That absence had to be distinguished from a stat-name mismatch, because gem5
suppresses zero-valued counters. In the r6e H2 run, 488 `m_msg_count` lines are
printed and **all 488 are nonzero** — zero zero-valued lines — so `nozero`
suppression is active. The CHI protocol instantiates `retryTriggerQueue`
unconditionally, and the comparison SE cell that did retry shows it plainly
(`l2.retryTriggerQueue.m_msg_count = 528,731`). An instantiated counter, absent
under active `nozero`, is exactly zero.

So the defect **could not have fired** in the full-system campaigns: no request
was ever retried, so no request ever lost its tag. The 130,864 figure is not
under-counted and needs no revision.

The ~99.8% coverage figure remains a **floor**, but for the independent reason
already documented rather than because of this defect: the bypass counter cannot
observe dirty writebacks, which STREAMING cannot tag. The defect adds nothing to
that floor.

### The SE 4- and 8-slice H2 figures are lower bounds; direction is safe

The bias reasoning holds, and was verified rather than assumed. The defect only
ever *removed* bypasses that should have occurred, so a defect-affected H2 arm
suppresses fewer fills and measures slower than a correct one. Those cells ran
at 5.8% and 1.7% write-retry, so the loss was small (4-slice H2 engagement 83.5%
against the achievable 96.0% at that denominator). The published H2 figures are
therefore lower bounds and the ordering claim `H2 >= WB > pfoff` stands as
published in direction; a re-run would move H2's margins up, not down. The one
exception is the one-slice H2 cell, which was void and is superseded by §4–§5
here.

### Regression test

Added `TestChiRetryPathDropsNoField` to `tests/test_dutyfree.py`, alongside the
existing source-level protocol checks. Three tests, all passing on the patched
source; the first two fail on the pre-fix source.

1. `test_retry_path_carries_every_field_the_primary_path_takes_from_the_tbe` —
   parses both functions and asserts `prepareRequestRetry()` copies every
   TBE-derived field `prepareRequest()` does, against an explicit
   `PERMITTED_OMISSIONS` allowlist (currently `txnId`, with its reason).
   **This is the test that would have caught the defect**, and it will catch the
   next dropped field without anyone knowing which field to look for.
2. `test_isStreaming_omission_would_be_silent_so_it_is_pinned_explicitly` —
   pins both halves of what made this silent: `default="false"` in `CHI-msg.sm`
   and the presence of the copy in the retry path.
3. `test_dvm_retry_omission_rests_on_isStreaming_having_no_dvm_writer` — asserts
   `tbe.isStreaming` has exactly two writers and both are non-DVM, so the §1 DVM
   decision fails loudly if a future DVM path ever writes the field.

The allowlist design is the point: a test that re-measured the fixed cells would
pass forever and detect nothing, whereas this one treats any new divergence
between the two paths as a defect until a human writes down why it is not.

## Provenance

- Three new run directories `gem5/logs/se_chi/h1bw_mc_{wb,h2,pfoff}_4c_l3x1_bwdef_20260904fix/`,
  all with `DONE.json`. The `_20260904` originals were not touched.
- Configuration reproduced from the originals' `MANIFEST.json` and
  `run_h1bw_multicore.sh`; only the binary differs. Benchmark
  `bench_sha256 cac9e27a...` unchanged. `config.ini` byte-identical for all
  affected parameters.
- Binary `build_Intel_8592/gem5.opt`, tag `build-cb290444`, mtime
  2026-09-04 12:51:05. Campaign binary was `build-cfd37207`. Full five-commit
  delta enumerated and measured inert in §2.
- Source changed: `gem5/src/mem/ruby/protocol/chi/CHI-cache-funcs.sm` (§1, four
  lines). `prepareRequestRetryDVM()` deliberately unchanged.
- Tests added: `tests/test_dutyfree.py::TestChiRetryPathDropsNoField`.
- Scripts changed: `experiments/asplos/h2_engagement_table.py` (stamp
  overridable; defect-signature header now states the post-fix expectation),
  `experiments/asplos/analyze_h1bw_bracket.py` (output `.jsonl` carries the
  stamp, so re-running no longer clobbers the original campaign's records —
  `h1bw_slice_bracket_20260904.jsonl` and `..._20260904fix.jsonl` now coexist).
- Six `h1bw_mc_*_8c_l3x8_*_20260904` runs completed on their own before the
  build; not signalled, killed or strace'd.
- The re-run cells' `console.log` files each contain six
  `rounding error > tolerance` warnings absent from the earlier cells. Expected;
  see §2.

<!-- CHAIN: H2_BYPASS_COLLAPSE_2026-09-03.md -> H2_BYPASS_FIX_OUTCOME_2026-09-03.md -->

---

**Cross-reference.** This document is the second half of the chain begun in
[`H2_BYPASS_COLLAPSE_2026-09-03.md`](H2_BYPASS_COLLAPSE_2026-09-03.md), which
diagnosed the defect, established it against five aggregate counter identities,
and ruled out three alternatives including `L1_REPL` starvation. That document
proposed the patch in its §3 without applying it; this one applies it, rebuilds,
and re-runs the three affected cells. Two of its findings are amended here:

- Its §4 "96.0% engagement ceiling" is a constant per-core **count** of
  un-bypassable clean evictions (~4,408/core), not a constant fraction. See §4
  above. Its per-cell engagement numbers are unaffected; only the inferred
  ceiling was over-generalized.
- Its §5 wording for `H1BW_MULTICORE_OUTCOME_2026-09-03.md` remains correct for
  the 4- and 8-slice cells, which stay lower bounds. Its instruction that the
  one-slice H2 cell's 7.72 GB/s "must not be reported as an H2 number under any
  qualification" is now moot: that cell is superseded by the 8.250 GB/s cell in
  §4, which does clear G5.

---

# Addendum 1 — 2026-09-04: §5's mechanism attribution holds for two arms of three, and the occupancy it cites is not an independent measurement

Campaign B now has its own outcome document,
[`H1BW_SLICE_BRACKET_OUTCOME_2026-09-04.md`](H1BW_SLICE_BRACKET_OUTCOME_2026-09-04.md),
which certifies all six one-slice cells against the frozen gates (5 certified,
1 void) and re-derives every figure in §4–§5 above from the artifacts. **All of
them reproduce exactly** — `E_clean` 97.57% and 97.96%, residues 5,315 and
4,433 per core, the bandwidths to nine printed digits, occupancy
82.3/82.7/83.8%, retry 64.7/65.0/11.3%. The verdict of this document does not
move and neither does the fix.

Two readings in §5 need narrowing, and they are narrowed there rather than
here because §5 is certified text.

**Current** (§5, "The slice-bracket verdict, with H2 working"):

> Applying it as written: **at one slice the binding constraint is the HNF
> transaction-buffer pool, not LLC fill traffic, so suppressing fills cannot
> buy much.** 65% of writes retry; HNF occupancy is 82.7%; concurrency is
> pinned at ~26.5 lines in all three arms regardless of arm, and throughput
> follows concurrency.

**Defensible:**

> At one slice the pool demonstrably binds the **WB and H2** arms: 64.7% and
> 65.0% of their write requests are refused and re-sent, and their concurrency
> is cut 57% from the four-slice baseline. For H2 the conclusion stands
> unchanged — suppressing fills cannot buy much when fill traffic is not what
> binds. **It does not generalize to the campaign.** The `pfoff` arm retried
> **11.3%** of its writes, not 65%, and its concurrency fell only 10.3%; it
> nonetheless lost 34.6% of its bandwidth, entirely in a latency term that rose
> 37.0% while its HNF hit fraction fell from 41.4% to 12.0%. Its loss is
> **residency, not buffers**. Going from four slices to one moves the
> transaction pool 128 → 32 **and** the LLC 20 MiB → 5 MiB against a 32 MiB
> working set, so the two mechanisms are not separable in this bracket, and the
> magnitude drop **cannot be attributed to the pool** from these cells. The
> licence to treat the LLC change as inert was the "LLC supplied none of the
> measured pass" claim that `AGGBW_VALIDITY_2026-09-03.md` withdrew: measured
> here, the controller supplies 89–100% of the read passes at one slice against
> ≤45% at four. `H1BW_SLICE_BRACKET_OUTCOME_2026-09-04.md` §6 specifies the two
> one-variable follow-ups that would separate them (`HNF_MSHR=8` at four
> slices, `HNF_MSHR=128` at one); neither is launched.

The "concurrency is pinned at ~26.5 lines in all three arms" half of the
sentence is **confirmed**: 26.33 / 26.46 / 26.81, a 1.83% spread against 29.90
– 61.13 at four slices. It is the retry figure, not the concurrency figure,
that does not hold across arms.

**Second, and it is why the interpretation table could not fire.** §5 says
"Mean occupancy cannot approach 100% in a run with drain phases", which is
true but understates the problem. `hnf_tbe_occupancy_frac` is not a counter at
all: `analyze_h1bw_bracket.py:404-407` computes Little's-law concurrency from
the delivered line rate and the HNF read latency, then divides by the budget.
Occupancy and concurrency are **one measurement in two units** — 26.33167/32 =
0.822865 to six places. So it is whole-run, and it *rises* with throughput at
fixed latency, whereas the hypothesis predicts throughput falling. Row 1's
stated signature was close to unreachable on this instrument in the direction
the hypothesis needed. The retry fraction remains the sharper instrument, as
§5 says, and it remains a measurement the frozen table did not nominate.

Nothing else in this document changes. The fix, the bit-identical `wb` control,
the five-commit inert delta, the 4,408-per-core ceiling correction, the P1
zero-retry finding and the regression test all stand as written.

<!-- CHAIN: H2_BYPASS_FIX_OUTCOME_2026-09-03.md -> H1BW_SLICE_BRACKET_OUTCOME_2026-09-04.md -->

---

# Addendum 2 — 2026-09-04: the ceiling is a count, confirmed and strengthened; the ~4,408-per-core constant does **not** transfer across core count

Handed back by `H1BW_SINGLECORE_OUTCOME_2026-09-04.md` §9, whose author does not
own this document, and applied here as an addendum under `A6.19` rather than
written back into §4. **The fix, the patch, every per-cell engagement figure and
every cell in §4's table are unaffected and nothing in the body is retracted.**
No new compute; the single-core campaign's own artifacts are the evidence.

## Superseded wording

§4 ("The 96.0% ceiling is a count, not a fraction") carried, and still carries
in the body:

> The ceiling was misread there, and this is the correction: what is constant is
> the absolute number of clean evictions that cannot be bypassed, at ~4,408 per
> core.

and the "Cross-reference" section states the same generalization:

> Its §4 "96.0% engagement ceiling" is a constant per-core **count** of
> un-bypassable clean evictions (~4,408/core), not a constant fraction.

## Replacement

> The correction stands and is the durable half: the engagement ceiling is an
> absolute **count** of un-bypassable clean evictions, not a fraction. What does
> not hold is the *value* of that count as a per-core constant across core
> counts. The ~4,408/core figure is measured at 4 cores / 4 slices and 8 cores /
> 8 slices, and 4,433–5,315/core at 4 cores / 1 slice; at **one** core
> `H1BW_SINGLECORE_OUTCOME_2026-09-04.md` §2 measures the residue at **229 per
> core** (`h2` at both `L1_MSHR` 16 and 48) and **125 per core** (`pf-off` at
> both) — 19x and 35x below it. Scope the ~4,408/core constant to the multi-core
> cells it was measured on; do not extrapolate it down to one core.

## What established this

`H1BW_SINGLECORE_OUTCOME_2026-09-04.md` re-derived its G5 engagement gate from
this document's finding, replacing the inherited fraction-based threshold with a
residue **count** per core (`A1_MAX_UNBYPASSABLE_PER_CORE = 8000`). That gate
passed on all nine cells with a 35x–64x margin, and the campaign records the
count as "the sharper instrument" against a `bypass/decision` fraction whose
useful range moves with the configuration. **So the central correction is not
merely confirmed here, it is what the next campaign's primary gate was built
on.**

The transferability defect surfaced as a **pre-declared prediction failure, and
is reported there as a failure rather than reinterpreted**: four of that
campaign's nineteen predictions — the windowed-footprint bands for `+H2` and
`pf-off` at both MSHR depths — failed below their floors, and those floors of
0.02x were set by extrapolating this document's 4,433–5,315/core down to one
core. They failed because suppression is roughly 40x *more* complete than
predicted, which does not make them passes.

## Scope

- §4's four-cell table, `E_clean` 96.04/96.02/97.96/97.57%, the 98.0% achievable
  ceiling at one slice and the 882/core prefetch-tagged tail are all unchanged.
- Addendum 1's closing sentence — "the 4,408-per-core ceiling correction …
  stand[s] as written" — stands as a correction of the *fraction* reading. Its
  per-core constant is scoped by this addendum to the 4- and 8-core cells.
- Nothing here bears on `H2_BYPASS_COLLAPSE_2026-09-03.md`'s diagnosis, the
  regression test, or the P1 zero-retry finding.

<!-- CHAIN: H1BW_SINGLECORE_OUTCOME_2026-09-04.md -> H2_BYPASS_FIX_OUTCOME_2026-09-03.md add. 2 -->
