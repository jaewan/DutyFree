# A one-slice home node reproduces the archive's magnitudes, in a regime where the archive's ordering is false. The bracket's magnitude half survives; its mechanistic half does not.

Outcome document for `H1BW_SLICE_BRACKET_PREREG_2026-09-03.md` (Campaign B),
judged against that pre-registration's own frozen gates, bands and
interpretation table. Six cells exist in two generations; **five certify and
one is void**. Reads only completed artifacts. **Nothing was launched, nothing
under `gem5/logs/` was written, `gem5/src/` was not modified, `gem5.opt` was
not rebuilt, and no `*_PREREG_*` document was edited.**

Campaign B's verdicts have until now lived inside
`H2_BYPASS_FIX_OUTCOME_2026-09-03.md` §5, which is a document about a protocol
defect rather than about this campaign. This document is Campaign B's own
record. Every figure below was recomputed here from the cells' `stats.txt`,
`config.ini`, `console.log` and `MANIFEST.json`, not inherited from that §5 or
from the pre-registration; where a recomputation disagreed with a circulated
figure, §9 says so.

## The answer

**Does a single shared home node reproduce the archived magnitudes? Yes, as a
band, and only as a band.** WB lands at 7.714 GB/s and H2 at 8.250 GB/s, both
inside the pre-declared 6–11 GB/s, against an archive that reported 6.23 /
7.73 / 5.62. Arm for arm the agreement is much weaker than the band suggests:
1.07× for H2, 1.24× for WB and 1.55× for prefetch-off.

**Is the archive's arm structure reproduced there? No, and it inverts.** With
H2 genuinely engaged the H2-over-WB ratio falls from 1.250× at four slices to
**1.070×**, and prefetch-off goes from the worst arm to the best. The
one-slice ordering is `pfoff > h2 > wb` against the archive's and the
four-slice campaign's `h2 > wb > pfoff`.

**So no configuration in this project reproduces the archive's §4 row.** Four
slices reproduce its *ratio* to 0.7% and miss its *magnitude* by 3.2×; one
slice reproduces its *magnitude* band and inverts its *ordering*. The
archive's row is not repairable by finding a nearby configuration, because
magnitude and ordering are reproducible only in different ones. §7 draws out
what that does to the paper, and it runs in the paper's favour.

**Is the HNF transaction-buffer pool the mechanism? Not established by this
bracket, and the bracket cannot establish it.** The pre-registration treats
the slice count as a clean buffer-budget knob on the strength of a claim —
"the LLC supplied none of the measured pass" — that
`AGGBW_VALIDITY_2026-09-03.md` has since withdrawn. Going from four slices to
one moves the transaction pool 128 → 32 **and** the LLC 20 MiB → 5 MiB
against a 32 MiB working set, i.e. the working-set-to-LLC ratio 1.6× → 6.4×.
Both moves are large and they are not separable in a one-variable bracket.
The prefetch-off arm is the proof that they matter differently: it lost 34.6%
of its bandwidth at an **11.3%** write-retry fraction with concurrency down
only 10.3%, which the buffer-pool hypothesis cannot explain and the residency
collapse can. §6 is the argument.

**The frozen interpretation table does not adjudicate, and is not rewritten to
fit.** Its row 1 requires occupancy to "approach 100%" and its row 2 requires
"well below budget"; the measurement is 82.3–83.8%, which is neither. §5
applies the table as written, reports the non-firing, and discloses that the
reading it does rest on comes from a measurement the table did not nominate —
and that the measurement the table *did* nominate turns out not to be an
independent instrument at all.

## 1. Certification of all six cells

Six cells exist at `--num-l3caches=1`, three per binary. `BUILD_PROVENANCE.md`
§2 is the authority for the binary attribution and its instruction — **never
pool a cell with its cross-binary twin** — is followed here.

Gates as frozen in the pre-registration §Gates: **G1** every instance
`status: "ok"`; **G2** realized instance count equals 4; **G3** realized LLC
equals `slices × 5 MiB` = 5,242,880 B with realized slice count 1; **G4**
realized CXL bandwidth equals 2 ticks/byte from `config.ini`. **G5** —
streaming engagement — is the fifth gate added by
`H2_BYPASS_COLLAPSE_2026-09-03.md` §6; §2 below records exactly how
pre-registered it is against each generation, because that differs.

### Pre-fix generation — `build-cfd37207`, `gem5/logs/se_chi/h1bw_mc_*_4c_l3x1_bwdef_20260904/`

| cell | G1 | G2 | G3 | G4 | G5 | verdict |
|---|:--|:--|:--|:--|:--|---|
| `h1bw_mc_wb_4c_l3x1_bwdef_20260904` | PASS | PASS | PASS | PASS | PASS (0 bypasses, exact) | **CERTIFIED** |
| `h1bw_mc_h2_4c_l3x1_bwdef_20260904` | PASS | PASS | PASS | PASS | **FAIL** | **VOID** |
| `h1bw_mc_pfoff_4c_l3x1_bwdef_20260904` | PASS | PASS | PASS | PASS | PASS | **CERTIFIED, qualified** |

**The `h2` cell is void and no bandwidth is reported for it.** Recomputed here
from its own transition histogram: 17,191 `WriteEvictFull.RU→I` against
944,540 clean fill decisions, i.e. `E_clean` = **1.82%**; bypass per write
allocation decision 1.1%; fill suppression against its own WB peer 1.2%. The
cause is established in `H2_BYPASS_COLLAPSE_2026-09-03.md`: `isStreaming` is
dropped in `prepareRequestRetry()`, and 64.8% of this cell's write requests
were retried, so the fabric and not the policy decided it. It is a writeback
measurement wearing an H2 label. Its 7.718 GB/s appears nowhere in this
document's results.

**The `pfoff` cell certifies but is a lower bound, not a clean arm.** Its
`E_clean` is **82.65%** against the 97.96% its post-fix twin achieves, because
10.3% of its writes retried and lost their tag. It passes G5 — it is
unambiguously engaged — but it is a partially-engaged measurement of the same
condition its twin measures fully, and its 8.369 GB/s is a floor. It is
reported in §3 as a provenance row and is not used in any ratio.

**The `wb` cell is sound and unaffected.** WB never sets `isStreaming`, so the
defect had nothing to strip; the exact-zero form of G5 is the check that no
tag leaked in, and it reads 0 bypasses against 1,560,892 decisions.

### Post-fix generation — `build-cb290444`, `.../h1bw_mc_*_4c_l3x1_bwdef_20260904fix/`

| cell | G1 | G2 | G3 | G4 | G5 | verdict |
|---|:--|:--|:--|:--|:--|---|
| `h1bw_mc_wb_4c_l3x1_bwdef_20260904fix` | PASS | PASS | PASS | PASS | PASS (0 bypasses, exact) | **CERTIFIED** |
| `h1bw_mc_h2_4c_l3x1_bwdef_20260904fix` | PASS | PASS | PASS | PASS | PASS (`E_clean` 97.57%) | **CERTIFIED** |
| `h1bw_mc_pfoff_4c_l3x1_bwdef_20260904fix` | PASS | PASS | PASS | PASS | PASS (`E_clean` 97.96%) | **CERTIFIED** |

`analyze_h1bw_bracket.py slice 20260904fix` returns **`COMPLETE: 3/3 cells
certified`**, pre-declared predictions confirmed 2/3. This is the citable
generation.

### Six cells are not six measurements

Worth stating plainly, because "six cells" invites a wrong reading of `n`:

- The two `wb` cells are **bit-identical on all 11,166 simulated quantities**
  (`H2_BYPASS_FIX_OUTCOME_2026-09-03.md` §3; five differing lines, all
  host-side). They are one measurement recorded twice. The pair's value is as
  a correctness control on the protocol fix, not as replication.
- The `h2` pre-fix cell is void.
- The two `pfoff` cells measure the same condition at two engagement levels,
  82.65% and 97.96%, and must not be pooled.

So the campaign holds **one** citable triple, the post-fix generation, at
**n = 1 per cell** with no seed replication — exactly the limit the
pre-registration declared in §"What this campaign cannot settle".

## 2. How pre-registered G5 is, stated exactly

The frozen pre-registration §Gates enumerates **G1–G4 only**. G5 was added to
`analyze_h1bw_bracket.py` on 2026-09-03 by
`H2_BYPASS_COLLAPSE_2026-09-03.md` §6, after the pre-fix cells were on disk
and in response to a defect found in them. Two different standings follow and
they should not be blurred:

- **Against the post-fix triple, G5 is genuinely pre-registered.** It was
  written and its two thresholds fixed as module constants on 09-03; those
  cells started at 12:52 on 09-04. The gate could not have been tuned to
  them.
- **Against the pre-fix triple, G5 is post-hoc**, and the honest description
  of the void `h2` cell is that a gate was written after seeing the data that
  the data then failed.

That the void survives anyway rests on something older than G5. `INDEX.md`'s
failure taxonomy carries **`S5.1` — "an arm's identity comes from its own
artifact, never the launcher's intent"** — as a standing project rule, and a
cell whose STREAMING tag was inert on 98.2% of its fill opportunities is not
the arm its launcher named under that rule, with or without a gate to
mechanize it. G5 is `S5.1` made executable for this quantity. The
pre-registration's own §Metrics also demands that the campaign report the case
where "the buffer pool is **not** the mechanism… as such", which is the same
discipline pointed at the mechanism rather than at the arm.

One cosmetic mismatch, recorded so it is not later read as a discrepancy: the
analyzer prints five gate lines per cell and then a verdict string reading
"certified against all four gates". The gate count in the string was not
updated when G5 landed. The gates themselves all ran.

## 3. Results

Post-fix triple, `build-cb290444`, one LLC slice, 4 cores. `agg_bw_sum` with
its window-overlap floor, as pre-registered; `agg_bw_wall` is retired and not
computed. Concurrency is Little's law on the HNF read path; occupancy is that
concurrency against the 32-buffer budget — see §5, which is about why those
are the same number.

| arm | `agg_bw_sum` | band | 4-slice baseline | 1s / 4s | HNF fills | `E_clean` | write retry | HNF read lat | concurrency | occupancy | overlap floor |
|---|--:|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| `wb` | **7.714** | 6–11 **PASS** | 20.087 | 0.384× | 1,604,202 | 0.0% | **64.7%** | 218.5 ns | 26.33 ln | 82.3% | 97.8% |
| `h2` | **8.250** | 6–11 **PASS** | 25.108 | 0.329× | 678,647 | **97.6%** | **65.0%** | 205.3 ns | 26.46 ln | 82.7% | 98.9% |
| `pfoff` | **8.688** | 10–15 **FAIL** | 13.274 | 0.655× | 702,091 | **98.0%** | **11.3%** | 197.5 ns | 26.81 ln | 83.8% | 98.7% |

All rates GB/s. Per-core spread 1.09% / 2.10% / 2.11%. Wall 1.40 / 1.41 /
1.32 h, inside the pre-registered 2–4 h budget for three concurrent arms.

For provenance only, and not used in any ratio below: the certified pre-fix
`wb` cell reads 7.714 GB/s (bit-identical) and the certified-but-depressed
pre-fix `pfoff` cell reads 8.369 GB/s at 82.65% engagement. The pre-fix `h2`
cell is void and has no entry.

### Ratios, and the inversion

| quantity | 1 slice | 4 slices | archive §4 |
|---|--:|--:|--:|
| H2 / WB | **1.070×** | 1.250× | 1.241× |
| pfoff / WB | **1.126×** | 0.661× | 0.902× |
| H2 / pfoff | **0.950×** | 1.892× | 1.375× |
| ordering | **`pfoff > h2 > wb`** | `h2 > wb > pfoff` | `h2 > wb > pfoff` |

The pre-registration declared an inverted ordering possible in advance
(§"The ordering may invert, and that is registered as informative") and
declared it informative rather than a failure. It is being read that way. But
note what actually inverted: the pre-registration anticipated
`wb > pfoff` breaking, with "a buffer-capped WB near 8 GB/s against a largely
unaffected prefetch-off near 13 GB/s". WB did land near 8. Prefetch-off did
not stay near 13 — it fell to 8.688 and **missed its band low by 1.3 GB/s**.
So the ordering broke in the predicted direction for an unpredicted reason,
and that reason is §6.

### Against the archive, arm for arm

The band statement and the arm-for-arm statement are different, and only the
first is favourable.

| arm | 1 slice | archive §4 | ratio |
|---|--:|--:|--:|
| `wb` | 7.714 | 6.23 | 1.238× |
| `h2` | 8.250 | 7.73 | **1.067×** |
| `pfoff` | 8.688 | 5.62 | 1.546× |

The one-slice triple spans 7.714–8.688 against the archive's 5.62–7.73, so the
two bands overlap only at the archive's top. The frequently-quoted coincidence
that "`wb` lands on 7.714 against the archive's ~7.7" is a **cross-arm**
coincidence: 7.73 is the archive's *H2* figure, and our WB arm happens to sit
on it. It should not be offered as an arm-for-arm reproduction, and this
document does not.

## 4. What binds at one slice, decomposed against the four-slice baseline

Throughput is exactly `concurrency × 64 B / HNF read latency` in every live
cell — the identity reproduces `agg_bw_sum` to three decimals in all five —
so the whole result is a statement about those two factors. Both are read back
from each run's own `stats.txt`.

| arm | | concurrency | HNF read lat | `agg_bw_sum` | HNF hit frac | write retry | occupancy |
|---|---|--:|--:|--:|--:|--:|--:|
| `wb` | 4 slices, 128 buf | 60.52 ln | 192.8 ns | 20.087 | 26.8% | 6.9% | 47.3% |
| | **1 slice, 32 buf** | **26.33** | **218.5** | **7.714** | **3.2%** | **64.7%** | **82.3%** |
| | change | **−56.5%** | +13.3% | −61.6% | | | |
| `h2` | 4 slices, 128 buf | 61.13 ln | 155.8 ns | 25.108 | 44.3% | 5.8% | 47.8% |
| | **1 slice, 32 buf** | **26.46** | **205.3** | **8.250** | **10.7%** | **65.0%** | **82.7%** |
| | change | **−56.7%** | **+31.8%** | −67.1% | | | |
| `pfoff` | 4 slices, 128 buf | 29.90 ln | 144.2 ns | 13.274 | 41.4% | 0.0% | 23.4% |
| | **1 slice, 32 buf** | **26.81** | **197.5** | **8.688** | **12.0%** | **11.3%** | **83.8%** |
| | change | **−10.3%** | **+37.0%** | −34.6% | | | |

Three things fall out, and the third is the one that decides §6.

**Concurrency pins, and it pins at the same place in all three arms.** 26.33,
26.46 and 26.81 lines — a 1.83% spread across arms whose policies differ as
much as policies can here, and whose four-slice concurrencies differed by
2.05× (61.13 against 29.90). Whatever sets 26.5 is indifferent to policy.
26.5 of a 32-buffer pool is the natural reading, and the 64.7–65.0%
write-retry fraction in the two arms that offer the most traffic says the pool
is visibly refusing work.

**H2's mechanism works essentially perfectly here and buys almost nothing.**
`E_clean` 97.6%, 57.7% of WB's HNF fills suppressed — 1,604,202 down to
678,647 — converted into 7.0% of bandwidth, against 25.0% at four slices. A
policy that removes fill traffic cannot help much when fill traffic is not
what binds. This is the campaign's cleanest single sentence and it is a
negative.

**Prefetch-off did not lose its bandwidth to the buffer pool.** Its
concurrency fell 10.3%, not 57%; its retry fraction is 11.3%, not 65%. By the
buffer-pool hypothesis it should have been "least affected", and on the
concurrency axis it *was* — the pre-registration's arithmetic about pfoff
needing only ~30 of 128 buffers was correct, and 32 nearly sufficed. Yet it
lost 34.6% of its bandwidth, and all of that loss is in the latency term:
+37.0%, the largest of the three. Its HNF hit fraction fell from 41.4% to
12.0%. **Prefetch-off at one slice is a residency measurement, not a buffer
measurement**, and it is sitting in the middle of a bracket that was designed
to vary buffers.

## 5. The frozen interpretation table, applied as written

The table has three rows. Taking them in order, against the post-fix triple:

| row | condition | met? |
|---|---|---|
| 1 | WB and H2 in 6–11 GB/s **and** HNF TBE occupancy approaches 100% | 7.714 and 8.250 — **yes**. Occupancy 82.3% and 82.7% — **no** |
| 2 | WB and H2 in 6–11 GB/s **but** occupancy stays well below budget | bandwidth yes; 82–83% of budget is **not** "well below" |
| 3 | WB and H2 stay well above 11 GB/s | **no** |

**No row fires.** 82.3–83.8% is not "approaches 100%" and is not "well below
budget"; it sits in a gap the table does not describe. The table is frozen and
is not being rewritten to close its own gap, and no row's reading is being
claimed on the strength of the row.

### The measurement the table nominated is not an independent instrument

This is worth more than the non-firing, because it explains it. The table's
discriminator is "HNF TBE occupancy". The number carrying that name is
computed at `analyze_h1bw_bracket.py:404-407` as

```
hnf_concurrency          = delivered_line_rate × hnf_read_latency_ns × 1e-9
hnf_tbe_occupancy_frac   = hnf_concurrency / (32 × slices)
```

so it is Little's law on the delivered rate, divided by the budget. Checked
arithmetically here: 26.33167/32 = 0.822865 and 26.45923/32 = 0.826851, which
are the reported figures to six places. **Occupancy and concurrency are one
measurement in two units, not two measurements.** Two consequences:

1. It is a **whole-run mean**, over a program that spends 97%+ of itself in
   `fill_fact` and setup (`AGGBW_VALIDITY_2026-09-03.md` §Q2), so it is
   diluted by phases in which nothing is streaming. It cannot approach 100%
   in such a run.
2. It **rises with throughput at fixed latency**. Row 1 asks the campaign to
   confirm saturation by observing occupancy near its budget, but the
   hypothesis's own prediction is that throughput *falls*. On this instrument
   row 1's stated signature is close to unreachable in the direction the
   hypothesis needs. That is a defect in the frozen table, not in the runs.

The only direct HNF utilization counter in `stats.txt` is `avg_util`, which is
also whole-run and also therefore uncomparable to a "100%" threshold: it reads
0.1427 / 0.1357 / 0.1221 at one slice against 0.0373 / 0.0314 at four. The
3.8× rise is directionally consistent with a pool that has begun to bind, and
that is all it can support.

### The reading this document does rest on, and what it costs

The sharper instrument is the **HNF write-request retry fraction**, a ratio of
two direct counters — retries over arrivals, 1,038,507 / 1,604,202 for WB —
which the pre-registration registered under §Metrics as a mechanistic quantity
to be read back, but **did not nominate in the interpretation table**. Saying
so explicitly, as the pre-registration's closing constraint requires:

> **For the two arms row 1 names, WB and H2, the pool demonstrably binds:
> 64.7% and 65.0% of write requests are refused and re-sent, and concurrency
> is cut 57% from the four-slice baseline. Row 1's *reading* — that the
> archive measured a buffer-capped single-home-node regime, and that its
> "CXL-path-limited" label named the wrong mechanism — is consistent with
> that. But it rests on a measurement the table did not nominate, and no
> paper sentence should rest on it alone.**

And a limit on that reading which has not previously been stated: the retry
fraction gives a **split verdict across arms**, 64.7% and 65.0% against
11.3%. The frozen table asks a single question about "WB and H2" and treats
occupancy as one per-campaign number, so it has no way to express that the
third arm's loss has a different cause. §6 is that finding, and it is why row
1's reading, even granted, does not license the mechanism claim the campaign
was built to test.

## 6. The withdrawn premise, the residency confound, and whether the bracket still discriminates

### What the pre-registration assumed, and what withdrew it

The pre-registration's §"Why the slice count is the discriminating variable"
rules out four non-structural causes to leave the buffer pool standing. Its
capacity bullet reads, verbatim and frozen:

> Capacity is not it. Every arm pulled at least the entire two-pass working
> set across the CXL controller (1.007x–1.356x), so **the LLC supplied none of
> the measured pass** and a smaller LLC simply thrashes harder.

`AGGBW_VALIDITY_2026-09-03.md` §Q1 withdrew exactly that sentence, and
`INDEX.md`'s "Withdrawn during 2026-09-03→04" table lists this
pre-registration as one of the four places it was stated or assumed. The
replacement wording, appended to `H1BW_MULTICORE_OUTCOME_2026-09-03.md` as its
Addendum 2, is:

> **The CXL controller supplied at most 42.9% of the read passes; the LLC
> supplied the rest.** … The same decomposition gives <= 43.6% for H2 and
> <= 77.7% for WB.

The pre-registration is frozen and is not edited. But the bullet's *function*
in the argument was to make the LLC change inert, so that the slice count
could be read as a buffer-budget knob and nothing else. With the premise
withdrawn, that function is gone and has to be re-established or abandoned.

### The confound, measured at both slice counts

Reproducing `AGGBW_VALIDITY`'s decomposition on these cells, from each run's
own transition histogram. Setup write-allocate fetches are calibrated by the
prefetch-off arm's `ReadUnique_PoC.I.RU`, which reads **607,974** at one slice
pre-fix and **607,939** post-fix against **607,930** at four slices — the same
151,983 lines per instance in every geometry, so the calibrator transfers.
Two-pass need at 4 cores is 2 × 8 MiB × 4 / 64 = 1,048,576 lines.

| arm | slices | CXL read lines | − setup | for the passes | of need | controller share `f ≤` | HNF hit frac |
|---|--:|--:|--:|--:|--:|--:|--:|
| `wb` | 4 | 1,422,102 | 607,930 | 814,172 | 77.6% | 0.776 | 26.8% |
| `h2` | 4 | 1,084,243 | 607,930 | 476,313 | 45.4% | 0.454 | 44.3% |
| `pfoff` | 4 | 1,056,228 | 607,930 | 448,298 | 42.8% | 0.428 | 41.4% |
| `wb` | **1** | 1,679,735 | 607,930 | 1,071,805 | 102.2% | **1.000** | **3.2%** |
| `h2` | **1** | 1,547,401 | 607,930 | 939,471 | 89.6% | **0.896** | **10.7%** |
| `pfoff` | **1** | 1,544,113 | 607,930 | 936,183 | 89.3% | **0.893** | **12.0%** |

The four-slice rows reproduce `AGGBW_VALIDITY` §Q1 exactly, which is the check
that the method is being applied the same way.

**The one-slice rows are the finding.** The withdrawn claim — that the LLC
supplies none of the measured pass — is **false in the configuration the
pre-registration argued from** (4 slices, ~55% LLC-supplied for H2 and
prefetch-off) and **approximately true in the configuration it created**
(1 slice, 89–100% controller-supplied). The bracket did not hold LLC supply
constant. It brought LLC supply from roughly half the read stream down to
roughly a tenth, in the same step that took the buffer pool from 128 to 32.

The geometry says the same thing without counters: four slices give
`4 × 5 MiB` = 20 MiB against a 32 MiB working set, a **1.6×** ratio; one slice
gives 5 MiB, a **6.4×** ratio. That is not a marginal change in residency, it
is most of the residency.

### So: does the bracket still discriminate?

**Its magnitude half survives intact.** The bands were declared in advance,
encoded as `SLICE_PREDICTION` and checked mechanically; WB and H2 landed in
6–11 GB/s and the check is untouched by anything above. The campaign's
headline question — *does a single shared home node produce archive-like
magnitudes?* — is answered yes, and the answer does not depend on the
withdrawn premise, because it is a claim about an output and not about a
mechanism. §7 is built on this half and only on this half.

**Its mechanistic half does not survive, and the prefetch-off arm is why.**
The buffer-pool hypothesis predicts that an arm which was not buffer-limited
at 128 stays roughly where it was at 32. Prefetch-off was not buffer-limited
at 128 — 29.90 lines, 23.4% occupancy, **zero** retries — and at 32 it is
still barely buffer-limited: concurrency down 10.3%, retry fraction 11.3%. The
hypothesis's prediction for its concurrency was right. Its prediction for its
bandwidth was wrong by 1.3 GB/s, and the entire error is in a latency term
that rose 37.0% while its HNF hit fraction fell from 41.4% to 12.0%. There is
no version of "the transaction pool binds" that produces a 37% latency rise in
an arm retrying 11% of its writes. There is an obvious version of "the LLC
stopped supplying half the read stream" that does.

Two mechanisms are therefore live at one slice, they act on different arms in
different proportions, and the bracket moved both knobs in one step. **The
one-slice cells cannot attribute the magnitude drop to the transaction pool**,
and this document does not. What they establish is weaker and still useful:
*some* combination of a 4× smaller transaction pool and a 4× smaller LLC
produces archive-like magnitudes, with direct evidence that the pool binds the
WB and H2 arms and direct evidence that residency binds the prefetch-off arm.

Separating them needs a bracket that moves one at a time, and both directions
are cheap and neither is launched here:

- **`HNF_MSHR=8` at four slices.** 32 total buffers, 20 MiB LLC. Isolates the
  pool at four-slice residency. If WB and H2 fall to ~7.7 GB/s here, the pool
  is the mechanism and the LLC change was incidental. `HNF_MSHR` is read at
  `CHI_config_8592.py:435` and is unset today, so this is a runner
  environment change and no rebuild.
- **`HNF_MSHR=128` at one slice.** 128 buffers, 5 MiB LLC. Isolates residency
  at four-slice buffering. If the arms stay near 8 GB/s here, residency is
  the mechanism.

The pair is a clean 2×2 with the two existing cells, and it is what the
pre-registration's §"Why the slice count is the discriminating variable" would
have specified had its capacity bullet not been available to it. Recorded as
the recommended follow-up; **not launched**, and it needs its own
pre-registration.

### One thing the confound gives back

The residency confound that `AGGBW_VALIDITY_2026-09-03.md` calls "the
highest-value follow-up in this document", and that the paper concedes at
`Sec7_Evaluation.tex:84-89`, is **largely absent at one slice**: 6.4×
working-set-to-LLC and a controller supplying 89–100% of the read passes, as
against 1.6× and ≤45% at four slices. That is close to the geometry a clean
far-memory streaming measurement wants.

These cells still cannot serve as it, because the transaction pool binds them
and pins all three arms at the same concurrency, which is precisely the
condition under which policy cannot express itself. The lesson for that
follow-up is directional and concrete: reach 6.4× by **growing the working
set at full slice count** — 32 MiB per instance, 128 MiB total, at four
slices and 128 buffers — not by shrinking the LLC. Shrinking the LLC delivers
the ratio and destroys the measurement in the same move.

## 7. What this does to the archive, and to the paper

**The archive's magnitudes are reproducible.** A 4-core, one-slice,
32-buffer configuration puts WB at 7.714 and H2 at 8.250 GB/s, inside a band
declared before the runs, overlapping the archive's 5.62–7.73. The archive's
platform line — a single "L3(HNF) 5MiB/20" — is consistent with
`--num-l3caches=1`, and if that is what it ran, this is roughly the
configuration. That much the campaign delivers.

**They are reproducible only in a regime where the archive's own ordering
claim is false.** In that regime `pfoff > h2 > wb`. The archive's §4 reports
`H2 >= WB > WC` with H2/WB = 1.241 and prefetch-off last, and it reports those
alongside the magnitudes as one coherent result. We now know of no
configuration that produces both halves:

| configuration | archive magnitude | archive ordering | archive H2/WB ratio |
|---|---|---|---|
| 4 slices, 128 buffers | missed by 3.2× | reproduced | reproduced to 0.7% (1.250 vs 1.241) |
| 1 slice, 32 buffers | reproduced as a band | **inverted** | **not reproduced (1.070)** |

**The consequence, and it runs in the paper's favour.** The choice already
made — to supersede the archive's §4 row with the certified multi-core
campaign rather than to repair it — is strengthened, not weakened, by this
result. Repair would have meant finding a configuration that reproduces the
archive's row and citing that instead. This campaign was the best candidate
for such a configuration, and it shows that reproducing the magnitude costs
you the ordering. An archive row whose magnitude is only recoverable in a
regime that falsifies its own ordering is not a row with a recoverable
provenance defect; it is a row that cannot be made to mean what it says. It
can only be replaced by a measurement with its own artifacts, which is what
`H1BW_MULTICORE_OUTCOME_2026-09-03.md` is, and which `INDEX.md` already
records as superseding `preserved/gem5_streaming.tar.gz` §4 for both core
counts. That decision stands and this campaign is now a positive argument for
it rather than a neutral one.

**The paper's claim is not damaged, and the reason must not be edited away.**
`Sec7_Evaluation.tex:73-75` states the transferable claim as
"H1--H2 $\geq$ WB $>$ prefetch-off **once concurrency is available**". At one
slice concurrency is emphatically *not* available: it is pinned at 26.5 lines,
83% of a 32-buffer pool, identically in all three arms, and the two
highest-traffic arms are having 65% of their writes refused. The one-slice
inversion falls outside the qualifier and does not contradict the sentence.
But the qualifier is now doing real load-bearing work rather than reading as a
hedge, and it should not be dropped or softened in any editing pass. If a
reviewer asks what happens when concurrency is *not* available, the honest
answer is this campaign: the ordering inverts, and prefetch-off wins.

**Nothing here licenses a paper sentence on its own**, per the
pre-registration's §"Interpretation table" closing constraint. This campaign
discriminates between two readings of an unrecoverable archive and supersedes
nothing. `H1BW_MULTICORE_OUTCOME_2026-09-03.md` remains the citable source for
4- and 8-core aggregates.

## 8. What this licenses, and what it does not

Licensed:

- **Five of six cells certify against G1–G5; one is void.** The citable
  generation is the post-fix triple, `COMPLETE: 3/3`.
- **WB 7.714 and H2 8.250 GB/s at one slice, both inside the pre-declared
  6–11 GB/s band.** Prefetch-off 8.688, which **misses** its 10–15 band low.
  Predictions confirmed 2/3.
- **H2/WB collapses from 1.250× to 1.070× and the ordering inverts to
  `pfoff > h2 > wb`.** Pre-declared as possible and informative.
- **H2's mechanism is near-perfect at one slice and buys ~7%.** `E_clean`
  97.6%, 57.7% of WB's fills suppressed, HNF fills 1,604,202 → 678,647.
- **Concurrency pins at 26.3–26.8 lines in all three arms**, a 1.83% spread,
  against 29.9–61.1 at four slices; and throughput is exactly
  `concurrency × 64 B / latency` in every cell.
- **The transaction pool binds the WB and H2 arms**, on the retry fraction:
  64.7% and 65.0% of write requests refused and re-sent.
- **The controller supplies 89–100% of the read passes at one slice**, against
  ≤45% for H2 and prefetch-off at four slices.

Not licensed, and to travel with any quotation:

- **Do not report the pre-fix `h2` cell's 7.718 GB/s as an H2 number under any
  qualification.** It is void at 1.82% engagement.
- **Do not attribute the magnitude drop to the HNF transaction-buffer pool.**
  §6. The bracket moves the pool and the LLC together; the prefetch-off arm
  lost 34.6% of its bandwidth at an 11.3% retry fraction, which the pool
  cannot explain.
- **Do not cite the frozen interpretation table as adjudicating this
  campaign.** No row fires. Row 1's reading is consistent with the retry
  fraction, which the table did not nominate, and only for two of three arms.
- **Do not cite "HNF TBE occupancy" as an independent measurement.** It is
  Little's-law concurrency divided by the budget, whole-run, and it rises with
  throughput.
- **Do not read "the magnitudes reproduce" as arm-for-arm agreement.** 1.07×
  for H2, 1.24× for WB, 1.55× for prefetch-off, with the ordering inverted.
  The often-repeated "7.714 against the archive's ~7.7" is a cross-arm
  coincidence: 7.73 is the archive's H2 figure.
- **Do not pool cells across binaries.** `BUILD_PROVENANCE.md` §2. The `wb`
  pair is one measurement; the `pfoff` pair is two engagement levels of one
  condition.
- **`n = 1` per cell**, no seed replication, no within-instance repetition,
  `cov` identically 0. Nothing below roughly 10% is interpretable.
- **The 4c/8c convergence test is not run**, as the pre-registration declared
  in §Scope. The saturation reading remains consistent-with, not confirmed.
- **Agreement in magnitude is not a reproduction.** The archive's harness is
  gone (`F10`, `S6.6`); this is a demonstration that a nearby configuration
  produces nearby numbers, and §3 shows even that is arm-dependent.
- **The pre-fix `pfoff` cell's 8.369 GB/s is a floor**, depressed by the
  retry-path defect to 82.65% engagement.
- **`agg_bw_sum` is high by 2.4–16.7%** at 4 cores generally
  (`AGGBW_VALIDITY_2026-09-03.md`); the overlap floors here are 97.8–98.9%,
  the tightest in the project, so these cells sit at the favourable end.

## 9. Recomputation notes

Every figure above was recomputed from artifacts. Three notes where that
mattered:

- **All post-fix figures circulated in `H2_BYPASS_FIX_OUTCOME_2026-09-03.md`
  §4–§5 reproduce exactly.** `E_clean` 97.57% and 97.96% recomputed from
  `WriteEvictFull.RU→{I,UC}` here (853,465/874,726 and 851,968/869,701);
  residues 5,315 and 4,433 per core; bandwidths to nine printed digits;
  occupancy 82.3/82.7/83.8%; retry 64.7/65.0/11.3%. No disagreement.
- **The "about 65% of writes retry … in all three arms" shorthand is wrong for
  the third arm** and is corrected here. It is 64.7% and 65.0% for WB and H2
  and **11.3%** for prefetch-off, a 5.8× difference that is load-bearing for
  §6 rather than incidental. The "concurrency pins at ~26.5 lines in all three
  arms" half of that shorthand is correct.
- **The occupancy figure is a derivation, not a counter.** Established from
  `analyze_h1bw_bracket.py:404-407` and confirmed arithmetically. Previously
  reported as a measurement.

## Provenance

- Artifacts: six completed run directories
  `gem5/logs/se_chi/h1bw_mc_{wb,h2,pfoff}_4c_l3x1_bwdef_20260904{,fix}/`, all
  with `DONE.json` and `"exit":0`, plus the three four-slice baseline cells
  `h1bw_mc_{wb,h2,pfoff}_4c_20260904/` for the comparison in §4 and §6.
  **Nothing under `gem5/logs/` was written and no process was signalled.**
- Analyzers re-run read-only: `analyze_h1bw_bracket.py slice 20260904`
  (`INCOMPLETE: 2/3`, `h2` void, exit 1) and
  `analyze_h1bw_bracket.py slice 20260904fix` (`COMPLETE: 3/3`). Records
  written to `experiments/asplos/data/gem5/h1bw_slice_bracket_20260904.jsonl`
  and `..._20260904fix.jsonl`; these coexist by the stamp fix recorded in
  `H2_BYPASS_FIX_OUTCOME_2026-09-03.md` §Provenance, so re-running clobbered
  nothing. `h2_engagement_table.py` re-run read-only for the pre-fix stamp.
- `E_clean`, the `WriteEvictFull` transition decomposition, the
  `ReadShared`/`ReadUnique_PoC` split and the `avg_util` figures were computed
  directly from each cell's `stats.txt` rather than taken from any analyzer,
  as an independent check on both.
- Binaries: pre-fix cells `build-cfd37207`
  (`gem5_sha256 cfd37207b9b7124a…`), post-fix cells `build-cb290444`
  (`cb2904444d5c5c4d…`), both confirmed against each cell's `MANIFEST.json`.
  Attribution and the five-commit delta are `BUILD_PROVENANCE.md` §2 and its
  2026-09-04 addendum; the delta is measured inert on this workload by the
  bit-identical `wb` control. Benchmark `bench_sha256 cac9e27a…` in all six.
- Realized configuration read back from `config.ini` in all six: one
  `system.ruby.hnf.cntrl.cache` section, `size=5242880`, `assoc=20`, four CPUs,
  CXL 203 ns at 2.000 ticks/byte, DRAM 98 ns, `latency_var=0`. G4 confirms
  Campaign A's `CXL_MEM_BW` did not leak in. `prefetcher_sections` 76 / 76 / 0,
  which is the prefetch-off arm's identity from its own artifact per `S5.1`.
- `gem5/src/` was not read for this document and not modified; `gem5.opt` was
  not rebuilt; no simulation was launched.
- No `*_PREREG_*.md` was edited. `H1BW_SLICE_BRACKET_PREREG_2026-09-03.md`
  stands as registered, including the capacity bullet §6 addresses.
- Paper read only, not edited: `Sec7_Evaluation.tex` in
  `/home/domin/STREAMING_Paper/ASPLOS27/Text/` (outside this repository —
  a prior audit that searched only within `DutyFree` wrongly concluded no
  `.tex` files existed).
- One incidental health note, consistent with what
  `AGGBW_VALIDITY_2026-09-03.md` §"Health findings" already logs: the post-fix
  `pfoff` cell records `free_invalid_size: 1`. It is the known teardown
  bookkeeping defect in `free_bytes`, after the measured window and after the
  JSON emit, and it affects no reported quantity. The other five cells read 0.
- Supersedes nothing. Cross-referenced from
  `H2_BYPASS_FIX_OUTCOME_2026-09-03.md`, whose §5 was Campaign B's only
  verdict record until now; that document's verdicts are unchanged and its
  §4–§5 figures all reproduce here.

<!-- CHAIN: H1BW_SLICE_BRACKET_PREREG_2026-09-03.md -> H2_BYPASS_COLLAPSE_2026-09-03.md -> H2_BYPASS_FIX_OUTCOME_2026-09-03.md -> H1BW_SLICE_BRACKET_OUTCOME_2026-09-04.md -->
