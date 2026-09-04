# `tab:h1bw`'s third arm is prefetch-off, the model cannot express a WC arm at all, and the fidelity caveat's conservativeness claim does not survive

Settles the open question left by `H1BW_MULTICORE_OUTCOME_2026-09-03.md`
§"Two facts the campaign surfaced incidentally" and `STATE_2026-09-01.md`
Addendum 7: whether `Appendix.tex`'s `WC` column and the "model WB-versus-WC
ratio" derived from it are correct. Reads only committed source, the preserved
archive and the completed multi-core cells. **Nothing was launched, nothing
under `gem5/logs/` was written, `gem5/src/` was not modified, `gem5.opt` was
not rebuilt, no `*_PREREG_*` document was edited, and `INDEX.md` was not
touched.** Three `h1bw_mc_*_4c_l3x1_*` simulations were in flight throughout
and were not signalled.

## The answer

**The `WC` label is wrong, and it is wrong in a stronger way than the prior
audit claimed. The third arm is not merely "not write-combining" — the model
has no write-combining memory type, so no gem5 arm in this project could ever
have been WC. The arm is the \textsc{Streaming} (H2) policy with that core's
four prefetchers not instantiated.**

**The artifacts behind the table do not exist.** All twelve numbers survive
only as a hand-written markdown summary. There is no `stats.txt`, no
`config.ini`, no per-run JSON and no runner.

**The ratio is not stable, and it is not even stable in sign inside the
table's own sweep.** `1.18×` is the 48-MSHR point; the 16-MSHR point of the
same two rows is `0.92×`. The appendix cited the one of two points whose sign
its argument needed.

**The concluding conservativeness sentence must go.** Its premise is not
established by the comparison it rests on, and the only matched-quantity
silicon reading available points the other way.

## Question 1 — what was the third arm?

Five independent lines of evidence, three of them decisive on their own.

### 1. The model has no write-combining memory type (decisive, mechanism)

`gem5/src/arch/x86/pagetable_walker.cc` derives exactly two special types from
the PAT bits, at both the PMD leaf and the 4 K PTE:

```
:364   entry.streaming   = bits(pte, 12) && pte.pcd && !pte.pwt;   // PMD leaf
:365   entry.uncacheable = uncacheable && !entry.streaming;
:389   entry.streaming   = bits(pte, 7)  && pte.pcd && !pte.pwt;   // 4K PTE
:390   entry.uncacheable = uncacheable && !entry.streaming;
```

`streaming` is PAT slot 6. There is no third branch, and
`grep -rIl 'write.combin\|WriteCombin\|WRITE_COMBIN'` returns **nothing** in
`src/mem/ruby/`, in `configs/`, or in the walker. Write-combining is not a
memory type this model implements. **A WC arm was never constructible here**,
so the question is not whether this particular arm was WC but why anything was
ever labelled that way.

### 2. The committed runner builds the arm as `stream` + prefetch-off, and *names the directory* `wc` (decisive, and the origin of the mislabel)

`gem5/scripts/run_se.sh` is, per `H1BW_MULTICORE_PREREG_2026-09-03.md`, the
only committed definition of these three arms. Its `run_w1` launches:

```
:41  run_gem5 ${base}_wb_${N}c stream-smoke wb     "" "$ls" ALL_CXL=1 1 1 0 ""
:43  run_gem5 ${base}_h2_${N}c stream-smoke stream "" "$ls" ALL_CXL=1 1 1 0 ""
:45  run_gem5 ${base}_wc_${N}c stream-smoke stream "" "$ls" ALL_CXL=1 1 1 0 "0"
```

The tenth positional argument is `pf-off` (`:19`, `:21-22`), which becomes
`PF_OFF_CORES=$pfoff`. So the arm whose **output directory is named `wc`** is
`--policy stream` with `PF_OFF_CORES=0`. Its `--policy` is *identical to the H2
arm's*; the only difference from H2 is the prefetchers.

This is the whole causal chain of the defect, and it is worth stating plainly
because the same shape will recur: a runner named a directory `wc`, the
archived report inherited `WC` as a column head, and `Appendix.tex` then read
that column as a write-combining memory type and derived a hardware-fidelity
argument from it. Nothing between the runner and the appendix ever re-checked
what the arm was.

### 3. `PF_OFF_CORES` removes all four prefetchers, and removes them from the config rather than from the benchmark

`gem5/configs/ruby/CHI_config_8592.py`:

- `:723-728` parses `PF_OFF_CORES` into `_pfoff`;
- `:737-739` sets `l1Dprefetcher_type = None` for those cpu_ids;
- `:744-751` passes `pf_type = None` to `addPrivL2Cache` for the same cpu_ids.

So both the L1D pair (`StridePrefetcher(degree=_deg1)` + `DCPTPrefetcher()`,
`:703-711`) and the L2 pair (`StridePrefetcher(degree=_deg2)` +
`TaggedPrefetcher()`, `:713-721`) are **not instantiated at all** — not
disabled at runtime. This is independently confirmed in the surviving
multi-core artifacts, whose `config.ini` files contain **76 / 152 prefetcher
sections for `wb` and `h2` against exactly 0 for `pfoff`**
(`H1BW_MULTICORE_OUTCOME_2026-09-03.md` §"Realized configuration").

The prefetch-off arm is therefore realized through the gem5 config, exactly as
suspected, and not through any benchmark policy.

### 4. The benchmark has no write-combining policy to select

`benchmarks/e2e/hash_join/src/cxl_join_bench.cpp` parses `--policy` at `:2854`
into a free-form string and branches on it in six places. The realized set is:

| `--policy` | what it does | site |
|---|---|---|
| `wb` | nothing; the default path | `:72` |
| `stream` | `declare_streaming()` → m5op `0x55`, or `mprotect(PROT_READ\|PROT_STREAMING)` → PAT slot 6 | `:1174`, `:342-357` |
| `nta` | `_mm_prefetch(_MM_HINT_NTA)` — a software non-temporal **prefetch hint**, not a memory type | `:957-959` |
| `t0` | `_mm_prefetch(_MM_HINT_T0)` | `:959` |
| `fbo` | flush-behind **oracle**: m5op `0x57`, zero-latency LLC invalidate; explicitly "an UPPER BOUND on flush-behind, not a model of it" | `:238-247`, `:704-717` |
| `quiet` | no tenant | `:1467`, `:1725` |
| `cat` | refuses: "needs resctrl control-group privilege" | `:2595-2596` |

None of the three candidate mechanisms named as possibilities is what ran.
There is no PAT-WC policy. `nta`/`t0` exist but are advisory prefetch hints on
ordinary write-back pages, and `run_stream()` never selected them for this
family. The `clflushopt` flush-behind path exists but is `--policy fbo`, is a
*join* path (`join_range_flushbehind`), and the source records at `:241-242`
that "gem5's CHI has no handler for a real CLFLUSH, so clflushopt is a silent
no-op here" — so it could not have produced a distinct bandwidth arm even if
selected.

### 5. The counters corroborate, and the MSHR-insensitivity does not discriminate on its own

The suggestive detail — 4.60 GB/s at both MSHR depths, LLC writes matching to
3 parts in 290,000 — is *consistent* with prefetch-off but is not by itself
decisive, because a WC arm on real silicon is limited by fill/WC buffers
rather than by an L1 MSHR pool and would also be insensitive to `L1_MSHR`.
What discriminates is the **magnitude and the direction of movement** of the
LLC data-array writes:

| | WB | +H2 | third arm |
|---|--:|--:|--:|
| 16 MSHRs | 529,330 | 300,238 | 289,695 |
| 48 MSHRs | 529,309 | 353,739 | 289,698 |
| Δ across the sweep | −21 | **+53,501 (+17.8%)** | **+3 (+1.0e-5)** |

- **An uncached WC arm would write ~nothing into the LLC data array.** 289,695
  is not near zero; it is 55% of WB's count and within 3.5% of H2's. That is
  the footprint of a *cacheable but non-allocating* arm, which is what
  `--policy stream` produces.
- **The direction of movement is the mechanism.** Extra MSHR depth lets the
  prefetcher run further ahead, so H2's fills rise 17.8% (300,238 → 353,739)
  while WB's are already saturated. An arm with **no prefetcher has no
  prefetch fills to add**, so its count is fixed by demand traffic and
  writebacks alone and moves by 3 lines in 290,000. A memory-type change would
  not predict that the invariant arm is the one whose count sits just *below*
  H2's.
- The flat bandwidth has a measured mechanism under the prefetch-off reading:
  4.60 GB/s at 203 ns and 64 B/line is **14.6 lines in flight**, below the
  16-MSHR pool, so the pool never bound this arm. The multi-core campaign
  measured the same thing directly — prefetch-off reaches only 15% of the L1
  MSHR budget and "its throughput is set by how fast an O3 core can generate
  demand misses without a prefetcher"
  (`H1BW_MULTICORE_OUTCOME_2026-09-03.md` §"The transferable ratio").

### The archive said so itself, in prose

`results/gem5_streaming/REPORT.md` heads its §1 column `WC` but its own
verdict line reads "both > WC (**4.60, prefetch off**)", and its §4 heads the
arm "WC (prefetch off)". The paper body is likewise already correct:
`Sec7_Evaluation.tex:57-63` says "prefetch-off arm" four times. **Only the
appendix table's column head and the fidelity caveat carried the mislabel into
a claim.**

## Question 2 — do the artifacts behind `tab:h1bw` exist?

**No. The table traces to one 4,609-byte hand-written markdown file and
nothing else.**

- `experiments/asplos/preserved/README.md` records
  `gem5_streaming.tar.gz` as backing "`tab:h1bw` — all 12 numbers", contents
  "`results/gem5_streaming/REPORT.md`", runner "**gone** (`/tmp/run_arm.sh`,
  `/tmp/run_arm_mshr.sh`, dead session)".
- `tar tzvf` on that tarball lists exactly one file, `REPORT.md`.
  `sha256sum -c SHA256SUMS` passes, so the archive is intact — it is simply
  not an artifact set. `results/gem5_streaming/` on disk likewise contains
  only `REPORT.md`.
- The MSHR sweep's runner is named in `run_se.sh:16-17` — "The one-off
  MSHR/prefetcher knee sweep lives in a separate script (`knee_sweep.sh`), not
  here" — and **`knee_sweep.sh` does not exist anywhere on this host.**
- `gem5/logs/se_chi/` holds 24 directories, all `h1bw_mc_*` from the
  multi-core campaign. There is no single-core 16 MiB sweep cell, under any
  name, in either repository or under `~/DutyFree-Gem5/logs/` (empty).
- Grepping the whole tree for the distinctive LLC-write literals
  (`529330`/`529,330`, `289695`/`289,695`, `300238`/`300,238`) finds them in
  `results/gem5_streaming/REPORT.md` and nowhere else that is not an unrelated
  binary or kernel symbol file.

So none of the three independent checks the task proposed can be run:
`MANIFEST.json`, `config.ini` and the per-instance JSON in `console.log` all
do not exist for these runs. **The arm identity above is established from
committed source, not from the run.** That is a weaker footing than a
`config.ini` would give, but it is not a guess: the model cannot express a WC
arm, the benchmark cannot select one, and the only committed definition of
this arm family builds the third arm as `stream` + `PF_OFF_CORES`.

### The one attempted reproduction did not reproduce it

`GATE1_H1BW_RERUN_OUTCOME.md` (2026-08-13) reconstructed the sweep at gem5
`b2c6499` with a purpose-written probe (`testcase/dutyfree/h1bw_stream.c`),
and **it too built the third arm as prefetch-off** — "WC = `h1bw_stream 16.0`
with `PF_OFF_CORES=0`". It measured 3.19/2.76/2.41 and 5.12/4.04/2.41 against
the published 4.24/4.90/4.60 and 5.44/5.82/4.60: **no cell within 25%, and the
WB/H2 ordering inverted.** `GATE1_H1BW_ANOMALY_RESOLVED_2026-08-18.md`
resolves the inversion as a metric artifact — at `simInsts` matched to
0.0005%, H2 is 19.3% faster in cycles while moving 30.2% less traffic, so GB/s
penalises it — and that resolution is sound. But it rescues the *ordering*,
not the *magnitudes*, and it leaves `tab:h1bw`'s twelve figures with no
artifact behind them. `A1_PROVENANCE_LEDGER_2026-08-28.md:32,74` carries this
as **F3, open**.

Two things follow that are worth separating, because they have different
remedies. The published ordering is corroborated twice over — once by the
matched-work cycle comparison, once by the certified multi-core campaign — so
the *claim* is not in doubt. The *table* is, and the honest options are to
disclose that its figures are an unrecoverable summary or to replace it with a
certified single-core campaign. I have taken the first, minimally; see
§"The paper edit".

## Question 3 — the ratio, and its stability

The quantity the appendix calls "the model's own WB-versus-WC bandwidth ratio"
is, correctly named, WB over prefetch-off. Every artifact-backed reading:

| reading | source | value |
|---|---|--:|
| 4.24 / 4.60, 1 core, 16 MSHRs | archive REPORT §1 | **0.922** |
| 5.44 / 4.60, 1 core, 48 MSHRs | archive REPORT §1 | **1.183** |
| 6.23 / 5.62, 4 cores | archive REPORT §4 | 1.109 |
| 20.087 / 13.274, 4 cores | `h1bw_multicore.jsonl` | 1.513 |
| 30.997 / 26.983, 8 cores | `h1bw_multicore.jsonl` | 1.149 |

The prior audit logged four of these. **The fifth is the one that matters
most**: 0.922 is the 16-MSHR point of the very two rows the appendix quotes,
and at that point WB is *below* the third arm. The appendix quotes 1.18×
without saying that the sweep it cites contains a point of the opposite sign —
in a table whose own caption insists "the sweep is the claim, not a single
point."

These five are not replicates and must not be pooled into a range with an `n`:
they span two harnesses, three core counts and two LLC geometries, and
`H1BW_MULTICORE_OUTCOME_2026-09-03.md` §"The transferable ratio is narrower
than 'the ratios agree'" already records that WB-over-prefetch-off **does not
transfer** (1.513 against 1.109 at 4 cores, a 36% discrepancy) and
§"What this licenses" that it is a **ceiling** and must **not be quoted to
three digits**. The correct statement is that the quantity is
configuration-dependent over 0.92–1.51 and is not licensed as a point value at
all.

### The quantity that *is* licensed, and is the right one for this argument

Because the third arm shares H2's policy and differs from it only in
prefetcher instantiation, **H2 over prefetch-off is a clean
prefetcher-contribution measurement at fixed policy** — which is what a
prefetcher-fidelity argument actually needs. `AGGBW_VALIDITY_2026-09-03.md`
independently finds this the safest of the three ratios ("phase-invariant to
±1.5%", "the safest of the three ratios to quote as a point value").

| | value |
|---|--:|
| 4.90 / 4.60, 1 core, 16 MSHRs | **1.065** |
| 5.82 / 4.60, 1 core, 48 MSHRs | **1.265** |
| 7.73 / 5.62, 4 cores (archive) | 1.375 |
| 25.108 / 13.274, 4 cores | 1.892 |
| 43.140 / 26.983, 8 cores | 1.599 |

WB over prefetch-off is *not* a prefetcher measurement even in the model,
because the third arm also carries the \textsc{Streaming} declaration, whose
effect is positive (H2 beats WB at both depths). The appendix's ratio therefore
bundles the prefetcher's contribution with the declaration's, in opposite
directions — which is why it can come out below 1.0.

## Question 4 — does the conservativeness argument survive?

**No. It fails at the premise, and it would not follow even if the premise
held.**

The sentence was:

> The direction of the gap is conservative for our claim: a weaker modeled
> prefetcher understates how much bandwidth H2 preserves relative to WC.

Four failures, in descending order of consequence.

**1. The two ratios are not the same quantity, so their comparison establishes
nothing about prefetcher strength.** Silicon's 3.9× is `12.43 / 3.20` on a
**genuine WC memory type** — `pgprot_writecombine` via `/dev/cxl_wc` with
`MOVNTDQA`, arm identity certified in `E1_ARM_IDENTITY_AUDIT_2026-08-24.md`.
A WC mapping withdraws cacheable allocation *and* the prefetch path together.
The model's 1.18× withdraws prefetchers only, at a fixed cacheable policy. One
number is a memory-type effect and the other a prefetcher effect; the ratio of
the two is not a fidelity measure of anything. `T2_WBWC_OUTCOME_2026-08-24.md`
R5/R6 decompose the silicon side directly and neither component is 3.9×: the
non-temporal path costs ~21% at equal prefetch state, and turning prefetch off
underneath it costs a further ~1.4×.

**2. It is a cross-vendor comparison, stated without saying so.** The 12.4/3.2
pair is **AMD EPYC 9754** (`Sec3_Measurement.tex:130-143`; `E1_ARM_IDENTITY_
AUDIT` defect 2 requires naming the platform at every use site). The model is
Intel Emerald Rapids 8592+, and its prefetchers are configured as one-for-one
stand-ins for *Intel's* DCU and MLC streamers
(`CHI_config_8592.py:691-694`). The caveat compared a model of Intel's
prefetchers against an AMD part's memory-type behaviour.

**3. The only matched-quantity silicon reading available points the other
way.** `T2_WBWC_OUTCOME_2026-08-24.md` R7 measures prefetch on against
prefetch off at a fixed WB memory type: `B/A` = 0.944 (mos181 EMR 8592+) and
0.940 (mos182 SPR 8462Y+), i.e. **all four hardware prefetchers are worth only
~6%** — a 1.06× contribution, `n=5`, CoV ≤ 1.31%. This reading survived T2's
retraction intact (`E1_ARM_IDENTITY_AUDIT`: "New, and it stands"). Against it,
the model's own matched contribution is **1.065× at 16 MSHRs and 1.265× at
48**. If anything the modelled prefetcher looks *stronger*, not weaker.

   **This does not establish the reverse, and must not be reported as if it
   did.** R7 is local DRAM over a 2 GB region, and `T2_WBWC_OUTCOME` §6 is
   explicit that it does not transfer to far memory: "on local DRAM a
   sequential stream needs almost no prefetching to reach full rate", and the
   paper's demand-miss claim "is a *CXL-latency* claim". No artifact in this
   project measures silicon's prefetch contribution at CXL latency. **The
   honest position is that the direction of the gap is unknown**, which is
   what the paper now says.

**4. Even granting a weaker modelled prefetcher, the conclusion does not
follow.** "How much bandwidth H2 preserves" is measured against WB, not
against the no-prefetch floor, and that margin is +7.0% at 48 MSHRs and +15.6%
at 16. A stronger prefetcher raises WB and H2 together; nothing offered shows
the *difference* would widen. The inference from "the prefetcher is weaker" to
"the margin is understated" was never made, only asserted.

The underlying qualitative point does survive, and it survives from
configuration rather than from any measurement: the instantiated prefetchers
are gem5's `StridePrefetcher` + `DCPTPrefetcher` at the L1D and
`StridePrefetcher` + `TaggedPrefetcher` at the L2, standing in for four named
Intel engines. That is a substitution, and disclosing it needs no ratio. What
cannot be salvaged is the pricing of the substitution and the safety argument
built on its sign.

Two notes for whoever revisits this. First, the paper does not need this
caveat to be conservative: `tab:gem5cfg`'s caption already carries the model's
one anchored operating point and its 39% under-prediction, and
`Sec7_Evaluation.tex:74-77` already states the multi-core margins as lower
bounds on two independent grounds (`H2_BYPASS_COLLAPSE_2026-09-03.md`'s
83.5–90.4% engagement, and `AGGBW_VALIDITY_2026-09-03.md`'s windowed
denominator). Removing a conservativeness claim that does not hold costs the
paper nothing it does not already have from sources that do hold. Second,
those two lower-bound arguments are **not** available for `tab:h1bw` itself:
its runs predate both campaigns, the binary that produced them is gone, and
its engagement cannot be measured. Do not extend them to it.

## The paper edit

`STREAMING_Paper/ASPLOS27/Text/Appendix.tex`. Compiles clean at **22 pages**,
unchanged from before the edit; no new overfull boxes (the pre-existing
overfull `\vbox` at the `app:gem5` page break in fact disappears).

### `tab:h1bw` column head

**Before:** `& \textbf{WB} & \textbf{+H2} & \textbf{WC} \\`
**After:** `& \textbf{WB} & \textbf{+H2} & \textbf{pf-off} \\`

### `tab:h1bw` caption

**Before:**

> Once MSHR depth clears the concurrency ceiling, H2 tracks WB and beats
> prefetch-off WC while holding a WC-like LLC footprint---prefetch survives
> non-allocation. The verdict is MSHR-depth-sensitive, so the sweep is the
> claim, not a single point.

**After:**

> The third arm is prefetch-off---the same non-allocating policy with that
> core's prefetchers not instantiated---so its columns are floors rather than a
> second memory type: no prefetch fills to add, hence a bandwidth and a
> footprint that do not move with MSHR depth. Once MSHR depth clears the
> concurrency ceiling, H2 tracks WB while staying near the footprint
> floor---prefetch survives non-allocation. The verdict is
> MSHR-depth-sensitive, so the sweep is the claim, not a single point. Single
> runs, no interval; these twelve figures survive only as an archived summary
> report, its per-run counters and its harness having been lost, so the
> multi-reader rows of \S\ref{sec:eval} are the artifact-backed statement of
> the same ordering.

"WC-like LLC footprint" had to go independently of the relabelling: the
reference footprint is *the same \textsc{Streaming} policy's* footprint, so the
comparison was circular. The provenance clause is a judgement call and is
flagged as such in the handback — it discloses F3 rather than resolving it.

### Fidelity caveat

**Before:**

> The modeled prefetchers (stride-4 $+$ DCPT) are not the silicon's stream
> class. The model's own WB-versus-WC bandwidth ratio is 1.18$\times$ (5.44
> vs.\ 4.60~GB/s, \cref{tab:h1bw}) against silicon's 3.9$\times$ (12.4 vs.\
> 3.2~GB/s, \S\ref{sec:measurement}), a gap that partly explains the model's
> more muted prefetch-survival margin. The direction of the gap is conservative
> for our claim: a weaker modeled prefetcher understates how much bandwidth H2
> preserves relative to WC.

**After:**

> The modeled prefetchers are not the silicon's stream class: a strided and a
> delta-correlating prefetcher at the L1D, and a strided and a next-line
> prefetcher at the L2, stand in for this part's DCU and MLC streamers---a
> substitution, not a model of those engines. We previously priced that gap as
> a ``model WB-versus-WC'' bandwidth ratio of 1.18$\times$ against silicon's
> 3.9$\times$, and we withdraw the comparison. The third arm of \cref{tab:h1bw}
> is prefetch-off, not write-combining: it runs the \textsc{Streaming} policy
> with that core's four prefetchers not instantiated, and the model has no
> write-combining memory type from which a WC arm could be built. Its
> 4.60~GB/s is a demand-miss floor under a non-allocating policy, so it is not
> comparable with the AMD memory-type measurement of \S\ref{sec:measurement},
> which withdraws cacheable fills as well as prefetch; and the model ratio is
> not stable in sign across the sweep it is drawn from (0.92$\times$ at 16
> MSHRs against 1.18$\times$ at 48). Changing only the prefetchers, the model's
> own prefetch contribution is 1.07$\times$ at 16 MSHRs and 1.27$\times$ at 48,
> against the 6\% ($n{=}5$) that disabling all four hardware prefetchers costs
> on our Intel hosts---but that is a local-DRAM figure over a 2~GB region and
> does not transfer to a far-memory stream. **We therefore assign no direction
> to this gap and do not claim it is conservative**: nothing we have measured
> bounds the modeled prefetcher against silicon's at CXL latency. H1
> accordingly rests on the ordering and on the MSHR sweep, not on any single
> margin.

Every figure in the replacement traces to a named record: 0.92/1.18/1.07/1.27
to `results/gem5_streaming/REPORT.md` §1 (the same table the text cites);
6\% and `n=5` to `T2_WBWC_OUTCOME_2026-08-24.md` R7 and
`benchmarks/data/t2_bandwidth/t2_mos18{1,2}_*.jsonl`; the prefetcher classes to
`CHI_config_8592.py:691-721`; the absent WC type to
`src/arch/x86/pagetable_walker.cc:359-390`.

`tab:gem5cfg`'s `Prefetch` row ("not stream-class (see caveat)") stays correct
and was not touched — though note for a separate pass that it reads
"L1/L2 Stride(4) + DCPT" while the L2 pair is in fact Stride + Tagged, and
`run_se.sh` sets `PF_DEGREE_L2=8`.

## Index changes handed back, not applied

`INDEX.md` was not edited (a concurrent worker owns it). Three changes are
needed:

1. **New row for this document.** `H1BW_ARM_IDENTITY_2026-09-04.md` — settles
   `tab:h1bw`'s third-arm identity (prefetch-off; the model has no WC memory
   type at all), records that the table's artifacts do not exist beyond an
   archived summary, and withdraws the appendix fidelity caveat's
   conservativeness claim.
2. **`A1_PROVENANCE_LEDGER_2026-08-28.md` F3 row** currently reads
   "`tab:h1bw` ordering not reproduced; harness gone — **open**". It should
   additionally record that the *arm identity* is now settled and the paper
   relabelled, and that the ordering is corroborated by
   `GATE1_H1BW_ANOMALY_RESOLVED_2026-08-18.md` at matched work and by the
   certified multi-core campaign, so what remains open is the twelve
   magnitudes and not the claim. F3 stays open.
3. **The `H1BW_MULTICORE_OUTCOME` row's paper-edit note**, if it repeats the
   prescription "the direction of the caveat survives the relabelling", is
   superseded by Addendum 4 of that document and should point at it.

Separately, and outside `INDEX.md`: `preserved/README.md` describes
`gem5_streaming.tar.gz` as backing "`tab:h1bw` — all 12 numbers". That is
accurate about intent but reads as provenance. It would be worth one clause
recording that the tarball contains a summary report and no per-run artifacts,
so the next reader does not open it expecting counters. Not applied here.

## Provenance

- Read: `results/gem5_streaming/REPORT.md`;
  `experiments/asplos/preserved/{README.md,SHA256SUMS,gem5_streaming.tar.gz}`
  (listed and checksum-verified, not extracted over anything);
  `gem5/scripts/run_se.sh`; `gem5/configs/ruby/CHI_config_8592.py`;
  `gem5/src/arch/x86/pagetable_walker.cc`;
  `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp`;
  `benchmarks/data/t2_bandwidth/`; and the certified documents cited inline.
- `gem5/logs/se_chi/` was enumerated only. **Nothing under `gem5/logs/` was
  written and no process was signalled.** The three in-flight
  `h1bw_mc_*_4c_l3x1_*` runs were not touched.
- `gem5/src/` was read only and not modified; `gem5.opt` was not rebuilt.
- No `*_PREREG_*.md` was edited. `INDEX.md` was not edited.
- Corrects `H1BW_MULTICORE_OUTCOME_2026-09-03.md` by Addendum 4; that
  document's verdict and licensed ordering are unaffected.
