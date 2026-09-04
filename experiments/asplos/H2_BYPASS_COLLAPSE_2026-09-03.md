# The STREAMING attribute is dropped on the CHI retry path. The baseline H2 arm survives; the one-slice H2 cell does not.

Found 2026-09-03 while chasing a 24.5x collapse in `streamingHnfFillBypasses`
between the four-slice and one-slice H2 cells. The counter is not broken and
the H2 mechanism is not misconfigured. `prepareRequestRetry()` in
`gem5/src/mem/ruby/protocol/chi/CHI-cache-funcs.sm` omits one field
assignment, so every CHI request that receives a `RetryAck` is re-sent with
`isStreaming` reset to its field default of `false`. At one LLC slice, 65% of
the private L2s' writeback traffic is retried, and H2 stops existing.

Six baseline runs, six certified cap cells and three slice-bracket runs were
read; nothing was launched, nothing under `gem5/logs/` was written, and
`gem5/src/` was not modified. Six 8-core cap runs were in flight throughout
and were not touched.

## 1. Is the baseline H2 arm sound?

**Yes, with one qualification that must be written into the outcome document.**
The baseline H2 arm engaged on **83.5% of its LLC fill opportunities at 4
cores and 90.4% at 8 cores**, against a **96.0% ceiling** established by the
prefetch-off control. It is partially, not fully, engaged.

The direction of the bias is what makes this survivable: the defect *removes*
bypasses that should have occurred. A fully-engaged H2 would suppress more LLC
fills, pay less home-node transaction latency, and measure faster. The
licensed claim — the ordering `H2 >= WB > pfoff`, with H2 ahead by 25% at 4
cores and 39% at 8 — is therefore a **conservative** statement of a
fully-engaged mechanism, and does not need re-running.

Two sentences in `H1BW_MULTICORE_OUTCOME_2026-09-03.md` describe the arm more
strongly than the artifacts support. §5 gives replacement wording.

The one-slice H2 cell is a different matter. At 1.8% engagement it is not a
weakened H2 measurement; it is a **writeback measurement wearing an H2 label**,
and its 7.72 GB/s must not be reported as an H2 number under any
qualification. §6 covers the analyzer change that now catches this.

## 2. Where the counter is incremented, and what it therefore counts

The counter does not live in the SLICC protocol's accounting; it lives in
`CacheMemory` and is called from exactly one site,
`CHI-cache-actions.sm:291-294` inside `Initiate_Request`:

```
  bool would_alloc_without_streaming := needCacheEntry(tbe.reqType,
                                                       cache_entry, dir_entry,
                                                       tbe.is_local_pf, false);
  if (is_HN && tbe.isStreaming && is_invalid(cache_entry) &&
      would_alloc_without_streaming) {
    cache.profileStreamingHnfFillBypass();
  }
```

Three consequences follow, and all three are confirmed in the artifacts.

**The `l1d` / `l1i` / `l2` / `*.sf` instances of the counter are structural
noise, not a counter-location artifact.** `ADD_STAT` registers the counter on
every `CacheMemory`, so it appears everywhere; the `is_HN` guard means only
HNF slices can increment it. Across all fifteen completed runs, the sum of
every non-HNF instance is **exactly 0**. The alternative is closed.

**Reads can never be bypassed in this configuration, so the counter is purely
an eviction-path counter.** `would_alloc_without_streaming` calls
`needCacheEntry` with `is_streaming=false`; at the HNF,
`alloc_on_readshared`, `alloc_on_readunique`, `alloc_on_readonce` and
`alloc_on_seq_acc` are all `False` and only `alloc_on_writeback` and
`alloc_on_atomic` are `True` (`CHI_config_8592.py:396-402`). This HNF is a
non-inclusive victim cache: a read never presents an allocation opportunity,
so there is nothing for H2 to veto on a read. Only `WriteEvictFull`,
`WriteBackFull` and `WriteCleanFull` do, and only when the LLC data entry is
invalid.

**That makes the counter exactly identifiable in the transition histogram.**
An LLC-miss write request is one arriving in a directory state with no local
data; in these runs that is always `RU`. A bypass is such a request leaving in
state `I`. Summed over slices, in all fifteen runs:

`streamingHnfFillBypasses == WriteEvictFull.RU->I + WriteBackFull.RU->I`

with **zero residual in every run** — 421,432 = 393,154 + 28,278 at
`h2_4c`; 17,197 = 17,191 + 6 at `h2_4c_l3x1`; 0 = 0 + 0 in all five WB cells.
The counter is trustworthy and its denominator is measurable.

The per-level breakdown the investigation asked for is therefore degenerate,
and that is itself the answer to the prefetch-path alternative: **all bypasses
occur at the HNF, on clean evictions, and 93–100% of them are
`WriteEvictFull`.** A prefetch-specific explanation — prefetched lines never
carrying the attribute — would require the prefetch-off arm to bypass *less*
than H2. It bypasses *more*, in every cell. It is also wrong at source:
`queued.cc:69-71` copies `Request::STREAMING_BIT` onto every generated
prefetch packet, and `CHI-cache-actions.sm:252` copies it onto the outgoing
CHI request. Closed.

## 3. The mechanism: one missing field assignment on the retry path

`isStreaming` has exactly six writers in the protocol. Five are correct. The
sixth is a hole:

| site | what it does |
|---|---|
| `actions.sm:161` | sequencer request -> CHI request (load/ifetch only; a tagged store is a hard `error()`) |
| `actions.sm:252` | prefetch request -> CHI request |
| `actions.sm:273` | incoming CHI request -> `tbe.isStreaming` |
| `actions.sm:3470` | `tbe.isStreaming` -> `cache_entry.isStreaming` on fill |
| `actions.sm:430` | `cache_entry.isStreaming` -> `tbe.isStreaming` on eviction |
| `funcs.sm:700` | `tbe.isStreaming` -> outgoing request, in `prepareRequest()` |

`funcs.sm:726-746`, `prepareRequestRetry()`, is the function that rebuilds a
request after a `RetryAck`. It copies fourteen fields out of the TBE —
`addr`, `requestor`, `fwdRequestor`, `accAddr`, `accSize`, `type`,
`Destination`, `dataToFwdRequestor`, `retToSrc`, `seqReq`, `isSeqReqValid`,
`is_local_pf`, `is_remote_pf`, `atomic_op` — and does **not** copy
`isStreaming`. `CHI-msg.sm:121` declares the field `default="false"`, so the
re-sent request is not merely unmarked, it is affirmatively marked
non-streaming. At the HNF, `tbe.isStreaming` becomes `false`,
`needCacheEntry` returns `true`, the victim line is allocated into the LLC,
and the counter does not fire.

The TBE is still live at `Send_Retry` (`actions.sm:2791-2798`) and still holds
the correct value, so the repair is a one-line addition and needs no new
state:

```diff
--- a/src/mem/ruby/protocol/chi/CHI-cache-funcs.sm
+++ b/src/mem/ruby/protocol/chi/CHI-cache-funcs.sm
@@ prepareRequestRetry
   out_msg.is_local_pf := false;
   out_msg.is_remote_pf := tbe.is_local_pf || tbe.is_remote_pf;
+  out_msg.isStreaming := tbe.isStreaming;
   out_msg.atomic_op.clear();
   out_msg.atomic_op.orMask(tbe.atomic_op);
```

**Not applied.** Applying it requires rebuilding `gem5.opt`, and six runs are
in flight against the current binary. It is also not the only field
`prepareRequestRetry` drops relative to `prepareRequest`: `txnId` is copied by
the latter and not the former. `usesTxnId` is `false` for all memory
transactions here so `addr` is the key and the effect is probably nil, but
that has not been checked and is not claimed.

### What triggers it at one slice

The HNF sends `RetryAck` from one place: `AllocateTBE_Request`
(`actions.sm:43-70`) when `storTBEs.areNSlotsAvailable(1)` is false. Going
from four slices to one takes the HNF transaction-buffer pool from 4 x 32 =
128 entries to 32 while leaving the offered request rate unchanged, so the
pool saturates and the fabric starts rejecting requests.

The requester-side and home-side counters agree to the unit in all fifteen
runs — `L2 SendWriteBackOrWriteEvict.retries == HNF (WriteEvictFull +
WriteBackFull).retries` — which is what lets the retry rate be read as a
single number:

| cell | slices | HNF TBEs | HNF write-request retry fraction |
|---|--:|--:|--:|
| `pfoff` 4c, 4 slices | 4 | 128 | **0.0%** (0 of 1,669,759) |
| `h2` 8c, 8 slices | 8 | 256 | 1.7% |
| `h2` 4c, 4 slices | 4 | 128 | 5.8% |
| `pfoff` 4c, **1 slice** | 1 | 32 | 10.3% |
| `h2` 4c, **1 slice** | 1 | 32 | **64.8%** (1,038,329 of 1,601,829) |

That single column reorders the whole finding. `h2` and `pfoff` are both
`policy=stream` and differ only in prefetcher instantiation; the prefetchers
do not touch the attribute, they raise the offered rate, which raises the
retry rate, which destroys the attribute. At one slice `pfoff`'s lower traffic
keeps it at 10.3% retries and 82.7% engagement, while `h2` hits 64.8% retries
and 1.8% engagement. One collapsed and the other grew for the same reason.

### The falsifiable signature, and it holds

If the attribute survives only the first send, then a bypass can only come
from a request that was never retried:

> `WriteEvictFull.RU->I  <=  WriteEvictFull arrivals - WriteEvictFull retries`

and, symmetrically, every retried clean eviction must have allocated:

> `WriteEvictFull.RU->{UC,UD}  >=  WriteEvictFull retries`

**Both inequalities hold in all fifteen runs.** They are not close to
violation at the interesting end: at `h2_4c_l3x1` there were 36,726
non-retried clean-eviction arrivals and 17,191 bypasses, and 927,349 retried
allocations against 907,921 retries.

The residual is quantified rather than waved at. The four `pfoff` cells with
**zero** retries report `E_clean` of **96.0%** — 96.0, 96.0, 96.0, 96.0 —
which fixes the non-streaming clean-eviction background of this workload
(instruction lines, the neighbour's read-only region) at exactly 4.0% of the
denominator. Against that calibration:

| cell | clean fill decisions | bypassed | shortfall vs 96% | clean-evict retries | share explained | L1D->L2 retries |
|---|--:|--:|--:|--:|--:|--:|
| `h2` 4c | 470,978 | 393,154 | 58,985 | 47,465 | 80% | 39,361 |
| `h2` 8c | 908,645 | 820,963 | 51,336 | 26,535 | 52% | 53,292 |
| `h2` 4c t31 | 472,662 | 400,971 | 52,785 | 40,853 | 77% | 37,623 |
| `h2` 4c t16 | 467,521 | 392,310 | 56,510 | 44,331 | 78% | 38,318 |
| `h2` 4c 1 slice | 944,540 | 17,191 | 889,567 | 907,921 | **102%** | 18,813 |
| `pfoff` 4c 1 slice | 888,484 | 734,358 | 118,587 | 141,469 | 119% | 0 |

The over-explanation at one slice is expected: a small number of retried
evictions arrive in `UC_RU` rather than `RU` and are not in the denominator.
The under-explanation at four and eight slices is the **second hop**: the same
omission fires on L1D->L2 requests, and a retried L1D read or eviction leaves
`cache_entry.isStreaming` false at the L2, so that line's later
`WriteEvictFull` is unmarked even though it was never itself retried. The
L1D->L2 retry counts in the last column are the right size to close each gap,
and the `pfoff` arms — which have zero retries at either hop in the four-slice
cells — have a shortfall of **-168**, i.e. none.

### The three alternatives, ruled out

**HNF buffer saturation as an independent cause of attribute loss.** There is
no such path. Saturation acts only by producing `RetryAck`s, and the
attribute is lost in `prepareRequestRetry`, not in the HNF. The occupancy
figures the investigation cited (47% -> 82.5% of a budget that fell 128 -> 32)
are the *cause of the retries*, and they are the same in the WB arm (82.3%) as
in H2 (82.5%) — so occupancy alone cannot distinguish an engaged from a
disengaged cell, and the retry fraction can (10.3% for `pfoff` vs 64.8% for
`h2` at identical occupancy).

**Replacement-TBE starvation (`L1_MSHR=48` with `L1_REPL=16`).** Refuted twice
over, and this was the leading hypothesis going in. Structurally: every
eviction transition in `CHI-cache-transitions.sm` (lines 818, 827, 836, 845,
854, 863, 872, 882, 905, 917) carries the `{ReplTBEAvailable}` resource guard,
which makes exhaustion a SLICC **resource stall** — the eviction waits. There
is no path that allocates a replacement TBE without running
`Initiate_Replacement`, and `actions.sm:429-431` copies
`cache_entry.isStreaming` into it unconditionally whenever the entry is valid.
Starvation delays evictions; it cannot strip the attribute. Empirically:
`l2.replTriggerQueue.m_stall_count` is 0 in every run, its message count
equals the outgoing write count exactly (1,601,829 == 1,601,829 at
`h2_4c_l3x1`), so no eviction was dropped; and the back-pressure it does show
is arm-independent — `m_stall_time` is 19.29e9 ticks in `h2_4c_l3x1` and
19.50e9 in `wb_4c_l3x1`, +1.1% apart, while their bypass counts differ by
17,197 to 0. The comment at `CHI_config_8592.py:315-322` flagged a real
asymmetry, but it is not this bug.

**A prefetch-specific attribute-loss path.** Closed in §2.

**`dealloc_backinv_*` / `WriteEvictFull`.** `WriteEvictFull` is not an
interaction, it is the main line: 93.3% of bypasses at `h2_4c` and 99.97% at
`h2_4c_l3x1`. Both `dealloc_backinv_unique` and `dealloc_backinv_shared` are
`False` at the HNF, so it issues no back-invalidations; `Global_Eviction` at
the L2 is 3,077-5,442 events per run against ~1.6-1.8M `Local_Eviction`s.
Not a factor.

### Confidence

**High** for the mechanism. The defect is a visible omission in a
seventeen-line function; the counter's identity to a transition pair is exact
in fifteen runs; both directions of the retry inequality hold in fifteen runs;
the requester-side and home-side retry counters agree to the unit; the
zero-retry cells sit at a constant 96.0%; and the two competing explanations
are each refuted structurally as well as numerically.

**Not proven**: per-line causality. These are aggregate counters, so "this
specific eviction lost its tag because it was retried" is an inference from
five independent aggregate agreements, not a traced event. The run in §7 would
convert it to a direct observation.

## 4. Engagement across every completed cell

`engagement` is defined as

> **`E_clean`** = `WriteEvictFull.RU->I` / `WriteEvictFull.RU->{I,UC,UD}`
>
> the share of clean-eviction LLC fill opportunities that the HNF actually
> declined. Numerator and denominator are the same population, from the same
> histogram, at the same place; no cross-arm normalisation is involved.

**What it can mean.** It is the fraction of the fill decisions the LLC
presented to the policy that the policy took. A cell at 96% is doing what H2
is specified to do; a cell at 1.8% is not running H2.

**What it cannot mean.** (i) It is *not* the fraction of streaming lines
bypassed: the denominator includes clean evictions of lines that were never
tagged, which measure to 4.0% here, so 96.0% and not 100% is this workload's
ceiling. (ii) It says nothing about capacity benefit — a declined fill only
helps if what it would have evicted mattered. (iii) It is a whole-run count
over the warm and measured passes together, not the measured pass alone.
(iv) n = 1 per cell, no seed replication.

`fills avoided` is `wb_fills - arm_fills` in the **same** cell. Comparing a
four-slice H2 against a one-slice WB, as the opening framing did, mixes two
geometries and gives 599,592 where the matched figure is 808,014.

| campaign | cell | arm | slices | bypasses | HNF fills | fills avoided | suppr | clean fill decisions | `E_clean` | write retry | verdict |
|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|---|
| baseline | 4c | `wb` | 4 | 0 | 1,812,624 | — | — | 736,938 | 0.0% | 6.9% | correct |
| baseline | 4c | `h2` | 4 | 421,432 | 1,004,610 | 808,014 | 44.6% | 470,978 | **83.5%** | 5.8% | partial |
| baseline | 4c | `pfoff` | 4 | 427,363 | 748,713 | 1,063,911 | 58.7% | 444,945 | **96.0%** | 0.0% | full |
| baseline | 8c | `wb` | 8 | 0 | 4,065,739 | — | — | 1,490,355 | 0.0% | 2.5% | correct |
| baseline | 8c | `h2` | 8 | 857,334 | 2,257,656 | 1,808,083 | 44.5% | 908,645 | **90.4%** | 1.7% | partial |
| baseline | 8c | `pfoff` | 8 | 850,083 | 1,921,270 | 2,144,469 | 52.7% | 885,053 | **96.0%** | 0.0% | full |
| cxlbw t31 | 4c | `wb` | 4 | 0 | 1,827,384 | — | — | 740,199 | 0.0% | 4.9% | correct |
| cxlbw t31 | 4c | `h2` | 4 | 427,408 | 984,234 | 843,150 | 46.1% | 472,662 | **84.8%** | 4.6% | partial |
| cxlbw t31 | 4c | `pfoff` | 4 | 427,581 | 748,928 | 1,078,456 | 59.0% | 445,170 | **96.0%** | 0.0% | full |
| cxlbw t16 | 4c | `wb` | 4 | 0 | 1,802,490 | — | — | 734,674 | 0.0% | 6.5% | correct |
| cxlbw t16 | 4c | `h2` | 4 | 419,718 | 1,001,070 | 801,420 | 44.5% | 467,521 | **83.9%** | 5.2% | partial |
| cxlbw t16 | 4c | `pfoff` | 4 | 427,611 | 748,598 | 1,053,892 | 58.5% | 445,205 | **96.0%** | 0.0% | full |
| slice x1 | 4c | `wb` | 1 | 0 | 1,604,202 | — | — | 940,973 | 0.0% | 64.7% | correct |
| slice x1 | 4c | `h2` | 1 | 17,197 | 1,584,632 | 19,570 | **1.2%** | 944,540 | **1.8%** | 64.8% | **VOID** |
| slice x1 | 4c | `pfoff` | 1 | 734,590 | 845,215 | 758,987 | 47.3% | 888,484 | **82.7%** | 10.3% | engaged |

Reproduce with `experiments/asplos/h2_engagement_table.py` (read-only; also
prints the four identity checks of §2 and §3).

The three answers the investigation asked for, stated plainly:

- The **baseline H2 arm is partially engaged**, at 83.5% (4c) and 90.4% (8c)
  of a 96.0% ceiling. Not indeterminate — the counters bound it tightly — and
  not full.
- The **six certified 4-core cap cells are sound**: 83.9-84.8% for H2,
  96.0% for `pfoff`, all three WB arms at exactly 0. The bandwidth cap did not
  change engagement, which is itself worth stating.
- The **one-slice H2 cell is void**. At 1.8% engagement and 1.2% fill
  suppression it measured the writeback policy.

The six in-flight 8-core cap cells run at eight slices, so their HNF pool is
256 entries and their retry fraction should land near the 1.7-2.5% of the
8-core baseline. **Prediction, recorded before they finish:** `h2` engagement
88-92%, `pfoff` 96.0%, `wb` exactly 0 bypasses, all six passing the new gate.
If any 8-core `h2` cell comes in below 20% engagement, this prediction is
wrong and that cell is void.

### One correction to the fill accounting

`hnf_fills` is `numDataArrayWrites`, and `suppr` is not a capacity measure,
because H2 has a **second** suppression site. `CheckCacheFill`
(`actions.sm:3541-3542`) gates the data-array write on
`!(is_HN && tbe.isStreaming)`, which also skips the write when the line is
**already resident** — an LLC hit, no allocation, no capacity effect. The
accounting closes exactly:

> `write arrivals - fills = bypasses + suppressed rewrites of resident lines`

| run | write arrivals | fills | deficit | bypasses (capacity) | rewrite-suppressed | LLC hit rate |
|---|--:|--:|--:|--:|--:|--:|
| `h2_4c` | 1,816,224 | 1,004,610 | 811,614 | 421,432 | 390,182 | 44.3% |
| `h2_8c` | 4,012,721 | 2,257,656 | 1,755,065 | 857,334 | 897,731 | 50.1% |
| `h2_4c_l3x1` | 1,601,829 | 1,584,632 | 17,197 | 17,197 | **0** | 2.9% |
| `pfoff_4c_l3x1` | 1,623,274 | 845,215 | 778,059 | 734,590 | 43,469 | 8.0% |
| all five `wb` | = fills | | **0** | 0 | 0 | |

So H2's headline "44.6% fewer fills" is **23.3% avoided allocations plus 21.5%
suppressed rewrites of lines that were already in the LLC**. The second half
is a data-array bandwidth and energy effect, not a footprint effect, and
should not be described as capacity. The `h2_4c_l3x1` row is a bonus
corroboration of §3: with the attribute destroyed, *both* H2 sites go inert
and the rewrite-suppression term is exactly zero.

## 5. Wording that `H1BW_MULTICORE_OUTCOME_2026-09-03.md` needs

`H1BW_MULTICORE_PREREG_2026-09-03.md` is frozen and untouched. An addendum has
been appended to the outcome document pointing here. Two claims need
qualifying.

**Current** (outcome doc, §"The feared WB/H2 asymmetry does not exist"):

> H2's mechanism is separately confirmed engaged — 421,432 and 857,334 fill
> bypasses against exactly 0 in both WB runs, cutting fills 44.6% — which
> reproduces the archive's −45%.

**Defensible:**

> H2's mechanism is confirmed engaged, and partially so. It recorded 421,432
> and 857,334 fill bypasses against exactly 0 in both WB runs, declining
> **83.5% (4c) and 90.4% (8c)** of the clean-eviction fill opportunities the
> HNF presented — against 96.0% for the prefetch-off arm, which is this
> workload's ceiling. The shortfall is a model defect, not a policy effect:
> `prepareRequestRetry()` drops `isStreaming`, so a `RetryAck`'d request loses
> its STREAMING attribute (`H2_BYPASS_COLLAPSE_2026-09-03.md`). It removes
> bypasses that should have happened, so every H2 figure here is a lower bound
> on a fully-engaged mechanism and the ordering claim is unaffected. The 44.6%
> fill reduction is **23.3% avoided LLC allocations and 21.5% suppressed
> data-array rewrites of already-resident lines**; only the first is a
> footprint effect, so this is not a like-for-like match to the archive's
> −45% and should not be reported as reproducing it.

The `H1BW_SLICE_BRACKET` result also needs re-reading. Its H2 cell measured
7.72 GB/s against WB's 7.71 — `h2/wb = 1.0013` where the baseline is 1.25 —
and the analyzer's "ORDERING INVERTED ... evidence the archive was not
buffer-capped" reads that as a statement about H2 under buffer pressure. It
is not. H2 was not running. On real CHI a retried request keeps its
attributes, so **the disappearance of H2's advantage at one slice is a model
artifact of the omitted field assignment, and no claim about H2 under
home-node buffer pressure is licensed from that cell.** The WB and `pfoff`
cells stand.

## 6. Analyzer fixes, `experiments/asplos/analyze_h1bw_bracket.py`

**Defect 1 — the alarm line printed a ratio as a change.** It formatted
`got/base` where it meant `got/base - 1`, rendering a +0.5% change as
`+100.5% relative` on the one line in the script written to be read carefully.
The predicate `got < base * ALARM_SHRINK_FRAC` was correct and is untouched;
only the printed figure changed. It now reads:

```
  4c @  32.26 GB/s cap:  h2/wb = 1.2560 (uncapped 1.2500, +0.5% relative)
  4c @  62.50 GB/s cap:  h2/wb = 1.2557 (uncapped 1.2500, +0.5% relative)
```

**Defect 2 — the A1 identity check was vacuous.** It tested
`(bypasses > 0) == (policy == "stream")`, which is why it certified
`h2_4c_l3x1`: 17,197 is greater than zero. It is replaced by a fifth
pre-registered gate, **G5**, with the same fail-closed discipline as G1-G4 —
a cell that fails is voided in place and contributes no number to the verdict.

G5 uses two measures, both of which must pass:

| measure | definition | engaged cells observed | collapsed cell | threshold |
|---|---|--:|--:|--:|
| fill suppression | `1 - arm_fills / wb_fills`, WB arm of the **same** cell | 44.5-59.0% | 1.2% | 0.20 |
| bypass / decision | `bypasses` / HNF write allocation decisions | 37.5-48.6% | 1.1% | 0.20 |

A `wb` arm must record **exactly zero** bypasses — an exact test, not a
threshold, because one bypass in the control arm would mean a STREAMING tag
had leaked into it.

Justification for the pair rather than either alone. Fill suppression is the
measure the finding was framed around and is directly meaningful, but it needs
a WB partner and is confounded by traffic differences between arms.
Bypass-per-decision is self-contained — numerator and denominator from the
same histogram, so a campaign with no WB arm is still checked — and it is the
quantity the mechanism acts on. Requiring both is strictly fail-closed. The
threshold of 0.20 sits under half the smallest engaged observation and roughly
twenty times the collapsed one; nothing in the gap is close to either
boundary, so the result does not depend on where in it the line is drawn. Both
constants are module-level, so moving them after seeing data is visible in
git.

The failure mode is loud rather than silent. G5 prints `FAIL` in the gate
block, the run appears under `VOID RUNS` with the reason, and a banner block
names the cell, its bypass count, its fill suppression, its retry fraction and
the one-line cause. The ordering comparison then refuses to run at all rather
than comparing against a void cell:

```
  !! STREAMING POLICY DID NOT ENGAGE -- these cells are VOID
  !!   h1bw_mc_h2_4c_l3x1_bwdef_20260904
  !!     bypasses 17197 over 1567662 HNF write allocation decisions (1.1%)
  !!     HNF fills 1584632 vs WB peer h1bw_mc_wb_4c_l3x1_bwdef_20260904 -- suppression 1.2%
  !!     HNF write-request retry fraction 64.8% -- a retried CHI request arrives with isStreaming reset
  !!     to its field default, so the fabric, not the policy, decided this cell.
  !! This cell measured the WRITEBACK policy with an inert STREAMING tag.
  !! Do not report its bandwidth as an H2 number under any qualification.
```

The same check was added to `analyze_h1bw_multicore.py`, with the same two
thresholds, keyed on core count since that campaign's slice count tracks it.
That script still runs on its own campaign and still returns `PASS`: all six
baseline arms clear G5 (H2 at 37.5%/39.5% bypass-per-decision and
44.6%/44.5% fill suppression). A `MISMATCH` there withholds the verdict via a
non-zero exit, as `ident_ok` already did.

Both analyzers were re-run against both campaigns:

| invocation | before | after |
|---|---|---|
| `analyze_h1bw_bracket.py slice 20260904` | `COMPLETE: 3/3 certified`, A1 `PASS` | `INCOMPLETE: 2/3`, A1 `FAIL`, `h2` void, exit 1 |
| `analyze_h1bw_bracket.py cxlbw 20260904` | `6/12`, `+100.5% relative` | `6/12`, `+0.5% relative`, all six G5 `PASS` |
| `analyze_h1bw_multicore.py 20260904` | `PASS`, A1 on `bypasses > 0` | `PASS`, A1 on engagement, all six pass |

The six 8-core cap cells still show as `not analyzed -- missing DONE.json`,
which is correct while they are in flight, and no in-flight directory is read
beyond an `os.path.exists` check.

## 7. Recommendation, nothing launched

**`L1_REPL=48` at one slice would not settle the mechanism, and is no longer
the run to make.** It is a clean discriminator for the hypothesis it was
designed to test, and that hypothesis is already refuted from source and from
counters (§3). Its predictions:

| hypothesis | predicted `h2_4c_l3x1` with `L1_REPL=48` |
|---|---|
| retry drops `isStreaming` (concluded) | bypasses unchanged within a few percent, ~17-18k; `E_clean` ~1.8%; HNF write-retry fraction still ~65%, because the saturating pool is the HNF's 32 TBEs and `L1_REPL` cannot touch it |
| replacement-TBE starvation (refuted) | bypasses recover toward ~780k, `E_clean` toward `pfoff`'s 82.7%, HNF fills fall from 1,584,632 toward ~870k |
| HNF saturation as an independent cause | indistinguishable from the first row — which is why this run cannot separate the two surviving accounts |

At ~1.4 h it is cheap enough to run as a pre-registered falsification if a
reviewer demands the negative, and if it is run then a matching `L1_REPL=48`
at four slices is needed as a control — it should change nothing (`E_clean`
83.5%, retries 5.8%), and if it *does*, `L1_REPL` perturbs something
unmodelled and the four-slice baseline needs re-examining for that reason
instead. Both cells would also need a runner change: `run_h1bw_multicore.sh`
hard-codes `MSHR=48` at line 48 and does not pass `L1_REPL` through the `env`
at line 142, and the output directory needs a distinguishing tag or the
analyzer's `outdir_for()` will collide with the existing cells.

**The run that does settle it** is the one-line patch of §3, a rebuild, and a
re-run of the three one-slice cells. Predicted outcome: `h2_4c_l3x1`
bypasses rise from 17,197 to 750-820k, `E_clean` from 1.8% to 83-90%, HNF
fills fall from 1,584,632 toward ~850k, and H2's bandwidth advantage over WB
reappears at one slice. `wb_4c_l3x1` must be **bit-identical** to the existing
run — it has 906,830 retried clean evictions and zero streaming tags, so a
correct patch cannot perturb it, which makes it a free correctness check on
the patch itself. About 1.4 h per cell, three cells, plus a `gem5.opt` rebuild
— **and the rebuild cannot start until the six in-flight runs finish, because
`src/python/` is marshalled into the binary and `src/python/m5/ticks.py`
carries an uncommitted fix that must stay dormant until then.**

**Does the baseline campaign need re-running?** No, to protect its licensed
claim; yes, if H2's magnitude is to be stated at face value. The defect
deflates H2 by 12.5 pp of engagement at 4 cores and 5.6 pp at 8, so
`H2 >= WB` and the +25%/+39% margins are conservative and stand as published
with the §5 wording. A post-fix re-run would move them **up**, which is a
strengthening rather than a correction, and at 1.38 h x 3 (4-core) + 3.1 h x 3
(8-core) it is affordable — but it is not on the critical path and should not
displace the one-slice re-run, which is repairing a void cell rather than
improving a sound one.

**Order of work, once the host is free:** patch and rebuild; re-run the three
one-slice cells and confirm `wb_4c_l3x1` is bit-identical; then decide on the
baseline re-run with the fixed binary in hand. The six 8-core cap cells now
finishing were launched against the current binary and remain valid as
partially-engaged H2 measurements under the §5 wording, provided they clear
G5 — which §4 predicts they will.

## Provenance

- Artifacts: fifteen completed run directories `gem5/logs/se_chi/h1bw_mc_*_20260904`,
  all with `DONE.json`; nothing under `gem5/logs/` was written.
- Source read at `gem5/src/mem/ruby/protocol/chi/{CHI-cache-actions,CHI-cache-funcs,CHI-cache-transitions,CHI-msg}.sm`,
  `gem5/src/mem/ruby/structures/CacheMemory.{cc,hh}`,
  `gem5/src/mem/cache/prefetch/queued.cc`, `gem5/configs/ruby/CHI_config_8592.py`.
  **`gem5/src/` was not modified**; the patch in §3 is proposed, not applied.
- Scripts added: `experiments/asplos/h2_engagement_table.py` (the tables in
  §2-§4), `experiments/asplos/probe_h2_bypass.py` (the exploratory dump the
  finding came out of). Both read-only.
- Scripts changed: `experiments/asplos/analyze_h1bw_bracket.py` (G5, alarm
  line), `experiments/asplos/analyze_h1bw_multicore.py` (A1 engagement).
- Six runs `h1bw_mc_*_8c_l3x8_*_20260904` were in flight for the whole
  investigation and were not signalled, killed or read beyond an existence
  check; `gem5.opt` was not rebuilt.

<!-- CHAIN: H2_BYPASS_COLLAPSE_2026-09-03.md -> H2_BYPASS_FIX_OUTCOME_2026-09-03.md -->

---

**Superseded in part — see [`H2_BYPASS_FIX_OUTCOME_2026-09-03.md`](H2_BYPASS_FIX_OUTCOME_2026-09-03.md).**
The §3 patch was applied (commit `b9c8714c93`), `gem5.opt` rebuilt as
`build-cb290444`, and the three one-slice cells re-run. Outcome: the `wb`
control is bit-identical on all 11,166 simulated quantities, one-slice H2 goes
from 17,197 bypasses / 1.8% engagement to 853,853 / 97.6%, and the slice bracket
certifies 3/3. Two findings above are amended there: the §4 "96.0% ceiling" is a
constant per-core *count* (~4,408 un-bypassable clean evictions), not a
fraction, so the achievable ceiling at one slice is 98.0%; and the §5 embargo on
the one-slice H2 number is moot, that cell having been replaced by one that
clears G5. The full-system P1 claims are confirmed unaffected — those runs
retried exactly zero times.
