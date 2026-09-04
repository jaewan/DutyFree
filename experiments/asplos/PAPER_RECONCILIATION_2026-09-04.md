# Draft-wide claim reconciliation, `ASPLOS27/Text/` against `experiments/asplos/`

**Date:** 2026-09-04 (complete version; supersedes the partial version of the
same filename written earlier the same day, whose `tab:h1bw` rows predate the
single-core certification and whose claim U7 is now resolved)
**Scope:** every quantitative claim, named result and attributed mechanism in
`STREAMING_Paper/ASPLOS27/Text/` — `Abstract.tex`, `Sec1_Introduction.tex`,
`Sec2_DirectoryTax.tex`, `Sec3_Measurement.tex`, `Sec4_Knobs.tex`,
`Sec5_Streaming.tex`, `Sec5_5_RelatedWork.tex`, `Sec6_Implementation.tex`,
`Sec6_Conclusion.tex`, `Sec7_Evaluation.tex`, `Appendix.tex`.

**Nothing is excluded.** `tab:h1bw` and the adjacent fidelity caveat were
out of scope in the earlier pass; both are now certified and current
(`H1BW_SINGLECORE_OUTCOME_2026-09-04.md`) and claims elsewhere in the draft
were re-verified against the **new** figures, not the archive's.

**Result:** 116 claims checked. 20 edit sites across 5 files. 22 pages before
and after; 7 overfull `\hbox`es before and after at identical widths;
**undefined references 3 → 0**.

---

## 1. Status summary

| Status | Count | Disposition |
|---|---:|---|
| **current** | 84 | no action |
| **superseded** | 15 | 15 fixed |
| **contradicted** | 9 | 6 fixed, 3 reported (2 disclosure gaps, 1 owned elsewhere) |
| **unlocatable** | 8 | reported for routing; none deleted, no source invented |

---

## 2. Does any other claim cite an unlicensed, failed or voided campaign?

**One did, and it is fixed. No others remain.** This was the r2 defect class
and it was checked exhaustively rather than by inspection of suspicious-looking
claims.

Sources of licensing instructions, all read in full:

- `STATE_2026-09-01.md` §"Do NOT do" (10 items), §"Next" (7 items), and
  addenda 1–7, each of which carries its own "Do not …" clauses.
- `INDEX.md` §"Withdrawn during 2026-09-03→04" (11 rows),
  §"Withdrawn during 2026-08-30" (3 rows), §"Superseded — kept, do not cite"
  (6 rows), and the `AMENDED` marker convention.
- Every `## What this campaign does not license` / `Not licensed` section in
  the certified outcomes.

| Instruction | Source | Draft status |
|---|---|---|
| **"Quote H2 admission r2 as a licensed proof (campaign FAIL)"** | `STATE` §Do NOT; §Q-table: *"Campaign FAIL: STREAMING-arm A3r 27.36% HNF demand hits… Do not quote r2 as an H2 admission proof"* | **VIOLATED** at `Sec7:105`. **Fixed** (edit 5). |
| "Treat r12 as an application-performance result" | `STATE` §Do NOT | Clean — `Sec7:107` says *"counter-based existence proofs, not timing results"* |
| "Quote ~1.07× model↔silicon calibration except as the 1-way cost point" | `STATE` §Do NOT | Clean — `1.07` appears nowhere in the draft |
| "Treat `wm20` ≡ `wb` as a mask-path control" | `STATE` §Do NOT | Clean — `wm20` appears nowhere |
| "Combine silicon CAT/FB tuples/s with modelled STREAMING in one unlabeled figure" | `STATE` §Do NOT; silicon e2e prereg | Clean — `fig:frontier` caption: *"Each panel is internally comparable; no line between"* |
| "Treat `DUCKDB_JOIN_CORUN_OUTCOME` as tenant CAT (wrong polarity); do not cite the 21 Aug DuckDB dump" | `STATE` §Do NOT | Clean — draft cites `DUCKDB_TENANT_CAT_OUTCOME` figures and states *"\textsc{Streaming} is not an arm in that campaign, and we make no DuckDB speedup claim"* |
| "H3 end-to-end" | `STATE` §Do NOT | Clean — H3 is a capability claim throughout; `Appendix:671` prices it |
| "Cite `STATE_2026-08-30.md` as current" | `STATE` §Do NOT | Clean |
| "Quote **both** wedges (+9.97% / +8.42%)" | `STATE` §Next 3 | Satisfied — `Sec7:175` (9.97%) and `Sec7:178` (8.42%) |
| **"Do NOT quote 101.92%"** (r6e recovery) | `FS_COMPLETE_JOIN_OUTCOME_2026-09-04.md` | Clean — absent |
| **"Do not report the pre-fix `h2` cell's 7.718 GB/s as an H2 number"** | `H1BW_SLICE_BRACKET_OUTCOME` §8 | Clean — absent |
| **"Do not attribute the magnitude drop to the HNF transaction-buffer pool"** | same; `INDEX` withdrawn row | Clean — no buffer-pool mechanism claim in the draft |
| **"Do not cite HNF TBE occupancy as an independent measurement"** | same | Clean — absent |
| **the 96.0% engagement "ceiling" as a fraction** | `INDEX` withdrawn row | Clean — draft says *"83.5–90.4% engagement"* without the withdrawn denominator |
| **"the LLC supplied none of the measured pass"** | `INDEX` withdrawn row | Clean — draft states the opposite, correctly (`Sec7:74-76`) |
| **"WB and H2 are on equal footing"** | `INDEX` withdrawn row | Clean — draft states the margins as **lower bounds** (`Sec7:78-81`) |
| `H2H_FUSED_OUTCOME` / `FUSED_TABLESWEEP_OUTCOME` (superseded) | `INDEX` §Superseded | Clean — the correction record notes *"Nothing from either reached the paper"* |
| `M3B_OUTCOME` "27% is residency" (overturned) | `INDEX` §Superseded | Clean — absent |
| `REDTEAM_REVIEW` S1-1 (self-retracted) | `INDEX` §Superseded | Clean |
| `preserved/gem5_streaming.tar.gz` §4 (superseded) | `INDEX` §Superseded | Clean — multi-core cells cite `H1BW_MULTICORE_OUTCOME` |
| **`preserved/…` §1 single-core rows** — *not* superseded as of `INDEX`, superseded as of 2026-09-04 | `H1BW_SINGLECORE_OUTCOME_2026-09-04.md` | **VIOLATED** at `Sec7:61-68`. **Fixed** (edit 17). |

**Two distinct defects of the class, then**, both now closed: r2 (a campaign
that failed its own gate) and the single-core archive rows (a campaign whose
supersession landed today). A third candidate was checked and cleared: the
silicon e2e campaign's **S3 and S5 read "FAIL — refuted"**, but those are
pre-registered *hypotheses* being refuted, not the campaign failing a gate.
The campaign is certified and the draft reports the refutations correctly
(flush-behind is cheaper than registered, `PREFETCHNTA` protects more).
`SILICON_E2E_OUTCOME` addendum 1 confirms S1/S4 stand and S2 is `UNTESTABLE`,
which the draft does not contradict.

---

## 3. Reconciliation table

Legend: **C** current, **S** superseded, **X** contradicted, **U** unlocatable.

### 3.1 Front matter

| # | File:line | Claim as written | Backing record | St. |
|---|---|---|---|---|
| 1 | `Abstract.tex:6` | removes 22% of neighbour's charge | `COMPLETE_JOIN_OUTCOME_2026-09-01` §reduction (22.59% mean) | **S** |
| 2 | `Abstract.tex:6` | "matching that protection with a partition costs the tenant 8.4%" | same §frontier: partition costs **2.8%**; 8.4% is the *gap* | **X** |
| 3 | `Abstract.tex:6` | tenant 5.4% faster than unprotected | same §tenant (+5.35%) | **C** |
| 4 | `Abstract.tex:2` | WC "at a quarter of the bandwidth" | `Sec1:32` AMD 12.4→3.2 GB/s = 3.9×; genuine WC memory type on AMD | **C** |
| 5 | `Abstract.tex:2` | "terabyte pool" | none — rhetorical framing | **U** |
| 6 | `Abstract.tex:2`, `Sec1:25` | "one LLC's worth of lines every 10 ms" | derived: 320 MB / 34 GB/s = 9.4 ms (9.9 ms if MiB) | **U** |
| 7 | `Sec1:56` | `\cref{fig:io-to-load}` | no label, no artifact, no `figures/` source — target cut | **X** |
| 8 | `Sec1:39` | 8592+ WB CXL stream doubles a 170 MB neighbour | `E1_OUTCOME_2026-08-28` §Result 1 (2.61×→2.287× per platform) | **C** |
| 9 | `Sec1:53` | split restructuring costs 36% of throughput | `A6_SMT_SPLIT_OUTCOME_2026-08-24`; `SUBMISSION_READINESS` C2 | **C** |
| 10 | `Sec1:96` | 8.4% matched-protection advantage | `COMPLETE_JOIN_OUTCOME` add. 1 (+8.42% interpolated) | **C** |

### 3.2 Silicon — Intel

| # | File:line | Claim | Record | St. |
|---|---|---|---|---|
| 11 | `Sec3:41` | 34 GB/s single-stream CXL read | `E1_OUTCOME_2026-08-28` §Result 2 | **C** |
| 12 | `Sec3:47` | 2.61× victim slowdown, 8592+ | same §Result 1 | **C** |
| 13 | `Sec3:66` | PREFETCHNTA does not avoid the tax | `E2_NTA_OUTCOME_2026-08-26` §Verdict | **C** |
| 14 | `Sec3:97` | cross-socket CXL placement is noise (Intel) | `spr_cxl8.csv`, 0.992× | **C** |
| 15 | `Sec3:118` | MBA 100→30% costs the stream 17% | `CATMBA_REDUCTION_RESOLUTION_2026-09-04` §MBA | **C** |
| 16 | `Sec4:26-31` | MBA caps 100–30% "leave both the CXL stream and the victim essentially unchanged" | same: stream loses 17%, 29→24 GB/s | **X** |
| 17 | `Sec4:33` | 20%/10% caps → 16 / 8.7 GB/s, victim 1.82×/1.46× | same | **C** |
| 18 | `Sec4:51` | fused 88.5 cyc/access | `A4_HITRATE_FINDING` (88.35) / ledger (88.45) | **C** (rounding, §6.2) |
| 19 | `Sec4:94` | flush-behind substantially cheaper, 8462Y+ | `SILICON_E2E_OUTCOME` §S5 | **C** |
| 20 | `Sec4:142` | BRRIP 0.8–1.7% faster | `TASK28_PREDICTOR_HEADTOHEAD_2026-08-18` | **C** |
| 21 | `Sec7:195-197` | 1-way CAT removes 91.4% for 42.0% tenant cost | `SILICON_E2E_OUTCOME` §S4 (42.02%) | **C** |
| 22 | `Sec7:199-201` | flush-behind 44.5% for 6.31%; CAT point 44.1% for 25.18% | same §fb256k; addendum 1 table | **C** |
| 23 | `Sec7:201-203` | PREFETCHNTA 15.3% recovery, tenant 2.95% faster | same §S3 (`nta_R=15.3%`) | **C** |
| 24 | `Sec7:205-211` | DuckDB 53% of 60 MiB LLC; 1-of-15 ways removes 55.4%, 0.835→1.708 s, 51% loss | `DUCKDB_TENANT_CAT_OUTCOME_2026-09-01` (+104.5% s at 55.4% R) | **C** — 1−0.835/1.708 = **51.1%** ✓ |
| 25 | `Sec7:212-216` | "Streaming is not an arm… no DuckDB speedup claim" | `STATE` add. 2/3 | **C** (required disclaimer present) |
| 26 | `Appendix:47` (`tab:appplat`) | LLC ways "20 (15 CLOSes)" spanning both Intel parts | `W4.3` F7.1: 8462Y+ has **15** ways | **X** |
| 27 | `Appendix` (`tab:appplat`) | reps n=5 / n=12 / n=30 | column split is correct as printed | **C** |
| 28 | `Appendix:295-332` (`tab:catmba` caption) | 17–41% / 0–2% fused tenant cost; 0.3–4.4% reproducibility | `E1_OUTCOME` add.; `M11B_OUTCOME:83`; `REDTEAM_REVIEW:393` | **C** |
| 29 | `Appendix:319,332` | `\cref{tab:fused}` ×2 | table existed (`CLAIM_REWRITE:96,134`) and was cut | **X** |
| 30 | `Appendix:307` | AMD cap at 24 GB/s = 96% of pullable bandwidth → 1.08× | `CATMBA_REDUCTION_RESOLUTION` | **C** |

### 3.3 Silicon — AMD

| # | File:line | Claim | Record | St. |
|---|---|---|---|---|
| 31 | `Sec1:32` | WC single-core 12.4 → 3.2 GB/s | AMD WC campaign | **C** |
| 32 | `Sec3:151` | 1.30× other-CCX slowdown | AMD CCX arm | **C** |
| 33 | `Sec3:152` | "moving it to the other socket reduces it to measurement noise" | **no AMD cross-socket arm exists in any record** | **U** |
| 34 | `Sec7:298` | 91.4% L3 occupancy restored, victim still 9.2× slower | `AMD_CATOCC_OUTCOME_2026-08-30` §title | **C** |
| 35 | `Appendix:368` | "$\sim$1.9× same-CCX tax; occupancy identifies…" | `BERGAMO_BACKINVAL_OUTCOME` add. 1 | **C** (correctly carries the withdrawal) |
| 36–45 | `Sec3`, `Sec7` | remaining 10 AMD numerics | `AMD_CATOCC`, `AMD_NARROWMASK`, `AMD_L3OCC`, `BERGAMO_*` | **C** |

### 3.4 Model — single-core H1 bandwidth (`tab:h1bw` and its body text)

| # | File:line | Claim | Record | St. |
|---|---|---|---|---|
| 46 | `Sec7:61-62` | "At 16 MSHRs the three executions remain near the concurrency ceiling: WB, H1–H2, prefetch-off sustain **4.24, 4.90, 4.60** GB/s" | `H1BW_SINGLECORE_OUTCOME_2026-09-04` §1: **3.271 / 4.046 / 2.527**; and the arms sit at **50–80%** of ceiling, not "near" it | **S** |
| 47 | `Sec7:63-64` | "H1–H2 sustains **5.82**, above WB's **5.44** and prefetch-off's **4.60**" | same: **4.852 / 4.099 / 2.527** | **S** |
| 48 | `Sec7:65-66` | "writes fall from **529,k** under WB to **354,k**, near prefetch-off's **290,k**" | same §3: whole-program figures replaced by windowed per-pass **262,244 → 137**, floor **83** | **S** |
| 49 | `Sec7:77-78` | ordering "H1–H2 ≥ WB > prefetch-off **once concurrency is available**" | `H1BW_SLICE_BRACKET_OUTCOME_2026-09-04` §7: qualifier is load-bearing, *"should not be dropped or softened"* | **C** — verified present and **preserved** |
| 50 | `tab:h1bw` body + caption | six certified cells, 28.5% LLC-served, supersession note | `H1BW_SINGLECORE_OUTCOME_2026-09-04` | **C** (owner's edit, verified consistent) |
| 51 | `Sec7:85-92` | residency confound disclosed | `AGGBW_VALIDITY_2026-09-03` §Q1; single-core share now **measured** at 28.5% | **C** after edit 18 |

### 3.5 Model — multi-reader bandwidth

| # | File:line | Claim | Record | St. |
|---|---|---|---|---|
| 52 | `Sec7:71-72` | 20.1/25.1/13.3 and 31.0/43.1/27.0 GB/s | `H1BW_MULTICORE_OUTCOME_2026-09-03` | **C** |
| 53 | `Sec7:74-75` | controller supplies "at most 78% of WB's and at most **45%** of H1–H2's" | `AGGBW_VALIDITY_2026-09-03`: 4-core H2 bound is **45.4%** | **X** |
| 54 | `Sec7:78-81` | margins +25%/+39%, widening to +34%/+45%, both lower bounds | `H2_BYPASS_COLLAPSE_2026-09-03`; `AGGBW_VALIDITY` | **C** |
| 55 | `Sec7:82-84` | 13.6 vs 13.8 lines in flight; 1.78× fewer far-memory lines | `H1BW_MULTICORE_OUTCOME` | **C** |
| 56 | `Sec7:33-37` | "two-core O3+CHI model with a 5 MiB shared cache" for **all** H1–H2 | `H1BW_MULTICORE_OUTCOME`: one HNF per reader → 20 MiB at 4, 40 MiB at 8 | **X** |

### 3.6 Model — frontier, recovery, sensitivity

| # | File:line | Claim | Record | St. |
|---|---|---|---|---|
| 57 | `Sec7:168` | removes **22.4%** of neighbour's WB charge | `COMPLETE_JOIN_OUTCOME_2026-09-01` (22.59% mean) | **S** |
| 58 | `Sec7:168` | tenant +5.35% | same | **C** |
| 59 | `Sec7:171` | declared range is **32%** of fills | same (32.3%) | **S** |
| 60 | `Sec7:234` | "22.4% rather than 89%: only 32% of fills" | same | **S** |
| 61 | `Sec7:175,178` | wedge 9.97% and 8.42% | `STATE` §Q-table; `COMPLETE_JOIN_OUTCOME` add. 1 | **C** (both quoted, as required) |
| 62 | `Sec7:238` | "a **held-out** complete-join point" | `RECOVERY_CURVE_OUTCOME_2026-09-04` add.: the test was not blind | **X** |
| 63 | `Sec7:267` | recovery "falls **monotonically** from 89.4% to 56.8%" | `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30` curve: 81.95 → **82.33** at 4.0 MB rises | **X** |
| 64 | `Sec7:289` | "89–92%" and "89–91%" recovery spans | `GATE1_SENS_RERUN_OUTCOME`: floors are **88.8%** in both | **S** |
| 65 | `Appendix:185` (`tab:sens` caption) | "holds (89–92%)" | same | **S** |
| 66 | `fig:recovery` caption | r6e exclusion not disclosed | `RECOVERY_CURVE_OUTCOME_2026-09-04` §Excluded requires it stated | **X** (gap) |
| 67 | `fig:frontier` caption | "no line between" panels | `STATE` §Do NOT (unlabeled-figure prohibition) | **C** |
| 68–75 | `tab:sens` rows | 8-way 90.8, 12-way 91.9, 53% 88.8, 97% 90.5 | `GATE1_SENS_RERUN_OUTCOME`; R=(WB−H2)/(WB−1) recomputed, all ✓ | **C** |

### 3.7 Full-system and kernel

| # | File:line | Claim | Record | St. |
|---|---|---|---|---|
| 76 | `Sec7:120` | "38 assertions pass and eight skip" | `KERNEL_TEST_AGGREGATE_OUTCOME_2026-09-03`: **47 / 0 / 0** + 10 KUnit, both THP modes | **S** |
| 77 | `Sec7:124`, `Sec6_Impl:70` | fork returns `ENOMEM` — open defect | same: fixed in `copy_mm()`, returns `EBUSY` | **S** |
| 78 | `Sec6_Impl:66` | "38 passing assertions and eight skips" | same | **S** |
| 79 | `Sec7:105` | "isolated cold-admission control: 390,524 bypasses, 79.5%, 524,263→34,322" | `STATE_2026-09-01`: campaign **r2 FAIL — do NOT quote** | **X** |
| 80 | `Sec7:103` | 118,260 HNF fill bypasses; 682,901→436,911 | `STATE` §Q-table (r12 gate PASS); r12 `stats.txt` | **C** |
| 81 | `Sec7:107` | "counter-based existence proofs, not timing results" | `STATE` §Do NOT (r12 not an application result) | **C** |
| 82 | `Sec6_Impl` | "eight generations" lifecycle | `…os_contract_r12_lifecycle/system.pc.com_1.device` | **C** |
| 83 | `Sec6_Impl` | seal cost 46.2 ms / 49.3 ms | not in `experiments/asplos/`; only in the HotStorage'26 draft | **U** |
| 84 | `Sec6_Impl:145` | `clflushopt` unimplemented, so flush-behind is silicon-only | `GEM5_RUBY_CLFLUSH_NOOP_2026-09-01`; `STATE` §Do NOT | **C** |
| 85–92 | `Sec6_Impl`, `Sec7` | remaining FS/kernel claims | `KERNEL_TEST_AGGREGATE`, r12 logs | **C** |

### 3.8 Appendix gem5 tables

| # | File:line | Claim | Record | St. |
|---|---|---|---|---|
| 93 | `Appendix:464,467,528` | `tab:declpredx` harm "grows with the victim" / "increasing margins" | `XCORE_SWEEP_2026-08-19`: margins 10.0, **2.0**, 13.8, 13.9 pp — non-monotonic | **X** |
| 94 | `Appendix:457` | "an order of magnitude more LLC writes" | `TASK28`: 17.8× and 10.6× — holds at both depths | **C** |
| 95 | `Appendix:575` | "conservative for **every claim** the model is cited for" | `H1BW_ARM_IDENTITY_2026-09-04` §Q4 endorses only the *anchored* under-prediction; adjacent caveat now assigns **no** direction | **X** |
| 96 | `Appendix` (`tab:gem5cfg`) | `SimpleMemory.bandwidth` −9.05% mis-realization undisclosed | `QUANTIZATION_AUDIT_2026-09-03` §Verdict | **X** (disclosure gap) |
| 97 | `Appendix` (`tab:gem5cfg` Prefetch row) | "L1/L2 Stride(4) + DCPT" | `CHI_config_8592.py:703-721`: L2 is Stride(4)+**Tagged**; caveat names four engines | **X** (three-way split) |
| 98 | `Appendix:198,203` | `\cref{tab:gem5}` ×2 | no such label; target is `tab:gem5cfg` | **X** |
| 99 | `Appendix` (`tab:gem5cfg` SF row) | 65,536 SF entries | `H1BW_SINGLECORE_OUTCOME` §7.3: scoped to the finite-SF H3 runs of `tab:h3sf`, `sf_finite=false` in `tab:h1bw` cells | **C** (scope correct as printed) |
| 100 | `Appendix:361` (`tab:h3sf` caption) | table measured "under an LRU LLC" | `HNFRP_REMAINING_CELLS_OUTCOME_2026-08-29`: infinite rows 1.336/1.068 are LRU ✓; finite rows coincide across policies by design (≤0.5 pp) | **C** — see §6.4 |
| 101 | `Appendix` (`tab:h3sf`) | H3 costs 4.53% over H2 | same: *"H3's cost is 4.53%, not 3.45%"* — paper already updated | **C** |
| 102 | `Appendix` (`tab:h3sf`) | H2+H3 removes 95.5% of finite-SF charge | same, Q2 = 95.45% | **C** |
| 103 | `Appendix:582` | commit `b2c6499`, sim 1.60× vs hw 2.61×, 39% under-predict | `GATE1_LOCALDRAM_COLUMN_OUTCOME`; manifests | **C** — (2.61−1.60)/2.61 = **38.7%** ✓ |
| 104–116 | `tab:sens`, `tab:h3sf`, `tab:declpredmeas`, `tab:declpredx`, `tab:gem5cfg`, `tab:checklist`, `tab:contract`, `tab:implementation` | all remaining cells | `GATE1_SENS_RERUN`, `H3SF_REMEASURED`, `TASK28`, `XCORE_SWEEP`, `CONFIG_FIDELITY_AUDIT`, `W4.5`, `W1.5` | **C** |

---

## 4. Edits applied

Twenty sites. Every figure written traces to a named record.

### 4.1 Applied in the first pass (unchanged, listed for completeness)

| # | File:line | Before → After | Record |
|---|---|---|---|
| 1 | `Abstract.tex:6` | `removes 22\%` … `matching that protection with a partition costs the tenant 8.4\% instead` → `removes 23\%` … `the partition that matches that protection leaves the tenant 2.8\% slower --- an 8.4\% throughput gap` | `COMPLETE_JOIN_OUTCOME_2026-09-01` |
| 2 | `Sec4_Knobs.tex:26-31` | `caps from 100\% through 30\% leave both the CXL stream and the victim essentially unchanged` → `caps from 100\% through 30\% cost the stream 17\% of its bandwidth, 29 to 24~GB/s, and leave the victim where it was, 2.03$\times$ to 2.04$\times$` | `CATMBA_REDUCTION_RESOLUTION_2026-09-04` |
| 3 | `Sec6_Implementation.tex:66-71` | `38 passing assertions and eight skips` + open `ENOMEM` defect → `47 passing assertions with no failures and no skips` + `copy\_mm()` fix returning `EBUSY` | `KERNEL_TEST_AGGREGATE_OUTCOME_2026-09-03` |
| 4 | `Sec7_Evaluation.tex:120-127` | `38 assertions pass and eight skip` → `passes 47 \texttt{mm} assertions with no failures and no skips, alongside ten in-kernel unit assertions` | same |
| 5 | `Sec7_Evaluation.tex:103-107` | `An isolated cold-admission control sharpens the same result: \num{390524} fills bypass… 79.5\%… \num{524263} to \num{34322}` → `and home-node data-array writes fall from \num{682901} to \num{436911}` | `STATE_2026-09-01` (r2 FAIL) → r12 |
| 6 | `Sec7_Evaluation.tex:75` | `at most 45\%` → `at most 46\%` | `AGGBW_VALIDITY_2026-09-03` (45.4%) |
| 7 | `Sec7_Evaluation.tex:33-37` | `a two-core O3+CHI model with a 5~MiB shared cache` → `5~MiB of shared cache per home node` + explicit 20/40 MiB scaling | `H1BW_MULTICORE_OUTCOME_2026-09-03` |
| 8 | `Sec7_Evaluation.tex:168-171` | `22.4%` / `32%` → `22.6%` / `32.3%` | `COMPLETE_JOIN_OUTCOME_2026-09-01` (mean) |
| 9 | `Sec7_Evaluation.tex:234` | same | same |
| 10 | `Sec7_Evaluation.tex:238` | `a held-out complete-join point` → `a complete-join point` | `RECOVERY_CURVE_OUTCOME_2026-09-04` add. |
| 11 | `Sec7_Evaluation.tex:270` | `falls monotonically from` → `falls from` | `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30` |
| 12 | `Sec7_Evaluation.tex:292`, `Appendix.tex:185` | `89--92%` / `89--91%` → `88.8--91.9%` / `88.8--90.5%` | `GATE1_SENS_RERUN_OUTCOME` |
| 13 | `Appendix.tex:47` | `20 (15 CLOSes)` → `20 / 15 (15 CLOSes)` | `W4.3` F7.1 |
| 14 | `Appendix.tex:464,467,528` | `margins that grow with the victim` / `harm grows as more of the victim lives in the LLC` / `by increasing margins` → `by 2--14 percentage points` / `harm appears only once the victim lives in the LLC` / `by 2--14 percentage points` | `XCORE_SWEEP_2026-08-19` |
| 15 | `Appendix.tex:198,203` | `\cref{tab:gem5}` ×2 → `\cref{tab:gem5cfg}` | dangling label |
| 16 | `Appendix.tex:575` | `The direction of the error is conservative for every claim the model is cited for.` → `The direction of this anchor error is conservative for the protection claims the model is cited for: a model that under-predicts the WB tax also under-predicts the charge H2 removes.` | `H1BW_ARM_IDENTITY_2026-09-04` §Q4 |

### 4.2 New in this pass

#### Edit 17 — `Sec7_Evaluation.tex:61-67` (claims 46, 47, 48)

The single most consequential remaining defect: the body carried the twelve
archive magnitudes while `tab:h1bw`, one section later, carried the certified
replacements. The two disagreed on every number.

**Before:**
> floor.  At 16 MSHRs the three executions remain near the concurrency ceiling:
> WB, H1--H2, and prefetch-off sustain 4.24, 4.90, and 4.60~GB/s.  At 48 MSHRs,
> where the prefetch path can separate from demand traffic, H1--H2 sustains
> 5.82~GB/s, above WB's 5.44~GB/s and the prefetch-off arm's 4.60~GB/s.
> Shared data-array writes fall from 529,k under WB to 354,k under H1--H2,
> near the prefetch-off arm's 290,k.  The conjunction therefore exists:

**After:**
> floor.  At 16 MSHRs, where the request pool binds hardest and the three arms
> reach 50 to 80\% of its 5.04~GB/s ceiling, WB, H1--H2, and prefetch-off
> sustain 3.27, 4.05, and 2.53~GB/s.  At 48 MSHRs,
> where the prefetch path can separate from demand traffic, H1--H2 sustains
> 4.85~GB/s, above WB's 4.10~GB/s and the prefetch-off arm's unchanged
> 2.53~GB/s.  Shared data-array writes fall from 262,244 per stream pass under
> WB to 137 under H1--H2, near the prefetch-off arm's 83.  The conjunction exists:

All six bandwidths and all three footprints are `H1BW_SINGLECORE_OUTCOME`
§1. Three further corrections are folded in:

- **"remain near the concurrency ceiling" was false** and is replaced with the
  measured 50–80% of the 5.04 GB/s pool ceiling (§4 magnitude bands).
- **The footprint row is now per measured pass**, matching the window-bracketed
  counters, rather than a whole-program total. The record is explicit that the
  archive's column was whole-program and **not** like-for-like (§5).
- **"unchanged 2.53"** records prediction S1, that prefetch-off is
  MSHR-insensitive to four significant figures — the arm-identity evidence.

The claim moves in both directions and is reported as measured: bandwidths are
lower than the archive's throughout, while fill suppression is far more
complete (99.95% against the archive's implied 33%). No number was chosen to
preserve the original strength.

#### Edit 18 — `Sec7_Evaluation.tex:90-93` (claim 51)

**Before:**
> far-memory fetch benefit from a shared-cache hit benefit.  We therefore claim

**After:**
> far-memory fetch benefit from a shared-cache hit benefit.  The single-core
> sweep measures that share rather than bounding it: 28.5\% of the streaming
> arms' reads are LLC-served against WB's zero.  We therefore claim

`H1BW_SINGLECORE_OUTCOME` §8: *"28.5% of the streaming arms' read traffic is
served by the LLC, not by CXL… a material qualification of the H2-over-WB
bandwidth ratio, not a footnote."* Placed in the paragraph that already
declines to claim the residency advantage, so the existing disclaimer now
covers a measured share rather than only the multi-reader bound. Same class as
the far-memory naming correction already applied at `Sec7:73-76`.

#### Edit 19 — `Sec1_Introduction.tex:56` (claim 7)

**Before:**
> own. The objects are separable by address and inseparable by requester~\cref{fig:io-to-load}.

**After:**
> own. The objects are separable by address and inseparable by requester.

#### Edit 20 — `Appendix.tex:319, 332` (claim 29)

**Before:**
> whether its reused structure fits the mask it keeps (\cref{tab:fused}): 0--2\%
>
> …cannot spare (\cref{tab:fused}).}

**After:**
> whether its reused structure fits the mask it keeps: 0--2\%
>
> …cannot spare.}

---

## 5. The three broken references

All three resolved; the build now reports **zero** undefined references.

### `fig:io-to-load` — genuinely cut, argument unaffected

Referenced once at `Sec1:56`, defined nowhere. Only two figure labels exist in
the draft (`fig:frontier`, `fig:recovery`) and `figures/` holds only
`eval_frontiers` and `recovery_curve`. No `.py`, `.tex` or `.pdf` artifact
anywhere in the paper tree matches `io-to-load` under any spelling, so there is
no rename candidate and no evidence a figure was ever built.

**Nothing the argument depends on was cut.** The sentence is a one-line summary
of the preceding eight lines, which carry the whole argument in prose — the
fused hash-join geometry, CAT's inability to assign two policies to one
requester, and the 36% cost of splitting (backed by `A6_SMT_SPLIT_OUTCOME`).
The figure would have illustrated a conclusion the text states and supports.
Removing the pointer leaves the sentence intact.

### `tab:fused` — cut, and it *was* a real table

Referenced twice, both inside `tab:catmba`'s caption. This one did exist:
`CLAIM_REWRITE_2026-08-26.md:96` discusses "`tab:fused`'s +19--44% column" and
:134 lists "**`tab:fused` caption** — add the hit-rate scope on the +19--44%
column" as a pending paper edit. No surviving label matches, and none of the
thirteen table labels in the draft is a fused-aggressor cost table, so there is
no unambiguous repoint target.

**The argument does not depend on the cut table, and I checked rather than
assumed.** The caption *asserts* the figures inline rather than deferring to
the table for them — "0–2% when it does, 17–41% when it does not, tightening as
the mask narrows" — and each is independently backed:

| figure | record |
|---|---|
| 17–41% tenant cost | `E1_OUTCOME_2026-08-28` addendum (+43.2/+41.5/+16.9/+2.1/+0.3% across widths 2/4/8/12/16); `E1_FRONTIER_PREREG:203` records it as vindicated by E2 |
| 0–2% when the structure fits | `M11B_OUTCOME_2026-08-28:83` |
| 0.3–4.4% reproducibility at hit rate 0.5 | `REDTEAM_REVIEW_2026-08-28:393` |
| withdrawal of the earlier 2.9% / 7.5% | `CLAIM_REWRITE_2026-08-26:91` (the n=3, hit-rate-1.0 arm) |

The hit-rate scope that `CLAIM_REWRITE` asked for is present in the caption
("those came from an n=3 arm at a 100% probe hit rate… withdrawn in favour of
the 50%-hit-rate figures"), so the outstanding edit that record requested has
in fact been made. Removing the two pointers costs no content.

**One consequence worth routing:** these figures are now asserted in a caption
with no table in the paper displaying them. That is legitimate — they are
prose claims with records behind them — but if the intent was for a reader to
see the fused sweep, the table needs reinstating, and that is a page-budget
decision rather than a correctness one.

---

## 6. Internal inconsistencies

### 6.1 Same quantity, two values (all resolved)

- **Single-core H1 bandwidth and footprint** stated one way in `Sec7:61-67`
  (archive) and another in `tab:h1bw` (certified). Six bandwidths and three
  footprints in direct conflict across two sections of the same paper. *Fixed.*
- Neighbour-charge reduction as **22% / 22.4% / 22.6%**. *Fixed* to 22.6%
  (23% in abstract prose).
- Declared-fill share as **32% / 32.3%**. *Fixed.*
- MBA effect as "essentially unchanged" (`Sec4`) against a 17% bandwidth cost
  (`Sec3`). *Fixed.*
- Sensitivity floor as **89%** against a measured **88.8%**, twice. *Fixed.*
- Reuse-predictor harm described as growing, in three places, against a
  non-monotonic sweep. *Fixed.*
- `tab:appplat` LLC ways **20** against `Sec7:191,206`'s reliance on **15**
  for the same part. *Fixed.*

### 6.2 Same quantity, two roundings (not fixed, low stakes)

Fused hit-rate-0.5 latency appears as **88.5** cyc/access (`Sec4:51`) and
**88.3** (`Appendix:116`) from the same underlying 88.35–88.45, in two
different comparisons. Neither is wrong; worth harmonizing only if someone is
editing both.

### 6.3 Prefetch stack described three ways (not fixed)

`tab:gem5cfg`'s Prefetch row ("L1/L2 Stride(4) + DCPT"), the Fidelity caveat
(four named Intel engines, L2 "next-line"), and `CHI_config_8592.py:703-721`
(L2 is Stride(4) + **Tagged**) disagree. Both
`H1BW_ARM_IDENTITY_2026-09-04` and `H1BW_SINGLECORE_OUTCOME` §9 flag the row
as "a paper-text defect in a row this campaign does not own". Left for the
owner of the caveat, since the row and the caveat must be settled together.

### 6.4 Two flagged inconsistencies that dissolved on inspection

Recorded so they are not re-raised.

- **`tab:h3sf` policy mix.** Reported as blending TreePLRU and LRU because its
  finite rows (2.501 / 2.513) nearly match the TreePLRU values the caption
  itself lists (2.501 / 2.512). They coincide *because* the caption's own claim
  is that finite-SF conclusions shift ≤0.5 pp between policies. The rows that
  discriminate — infinite WB 1.336 and H2+H3 1.068 — are LRU, as stated. No
  defect.
- **`tab:appplat` repetitions.** Reported as conflicting with `spr_cxl8.csv`'s
  n=30. The n=12 entry is in the AMD column and annotated for `tab:amdcat`;
  n=30 is the Intel column. The table is correct as printed.

### 6.5 Arithmetic

All derived ratios, percentages and speedups were recomputed rather than
trusted. `R = (WB − H2)/(WB − 1)` reproduces every printed recovery in
`tab:sens` and `tab:h3sf` to printed precision. Also checked: the DuckDB
throughput loss (1 − 0.835/1.708 = **51.1%**, printed 51%); the 39%
under-prediction ((2.61−1.60)/2.61 = **38.7%**); `tab:declpredmeas`'s 0.8%/1.7%
and 17.8×/10.6×; `tab:declpredx`'s 2.4%; the 2.07× fill-rate ratio; 5 MiB =
320/64; the 4 MiB snoop filter; and the AMD WC ratio (12.4/3.2 = **3.9×**,
printed as "a quarter of the bandwidth").

---

## 7. Unlocatable claims — for routing, not for deletion

None removed, no source invented for any. Eight remain; **U7 of the earlier
version is now resolved** by `H1BW_SINGLECORE_OUTCOME_2026-09-04.md`, which
supplies the missing per-run artifacts.

| # | Site | Claim | What exists |
|---|---|---|---|
| U1 | `Abstract.tex:2` | "terabyte pool" | no measurement; rhetorical scale-setting |
| U2 | `Abstract.tex:2`, `Sec1:25` | "one LLC's worth of lines every 10 ms" | derivable as 9.4 ms (320 MB) or 9.9 ms (320 MiB); no record states 10 ms |
| U3 | `Sec3:152` | AMD "moving it to the other socket reduces it to measurement noise" | only an **other-CCX, same-socket** arm (1.30×). No AMD cross-socket measurement in any record |
| U4 | `Sec6_Impl` | seal cost 46.2 ms / 49.3 ms | present only in the HotStorage'26 draft, not in `experiments/asplos/` |
| U5 | `fig:recovery` caption | r6e exclusion undisclosed | `RECOVERY_CURVE_OUTCOME_2026-09-04` requires the exclusion be stated; the caption it prescribes does not state it |
| U6 | `tab:gem5cfg` memory row | `SimpleMemory.bandwidth` realized −9.05% off request | `QUANTIZATION_AUDIT_2026-09-03` documents it; the table discloses no quantization |
| U7 | `tab:gem5cfg` Prefetch row | L2 prefetcher pair | source says Stride+Tagged; table says Stride+DCPT; caveat says next-line (§6.3) |
| U8 | — | FS complete-join result is **licensed but uncited** | `FS_COMPLETE_JOIN_OUTCOME_2026-09-04` §"Paper status": its licensed paragraph *"is not in"* the paper. The only place an OS-installed declaration and a performance number coexist. An omission, not a defect — adding it is a page-budget decision |

U3 is the one where the established response — replacing an unbacked figure
with a certified campaign — would apply.

---

## 8. Page budget

| | Pages | Overfull `\hbox` | Undefined refs |
|---|---:|---:|---:|
| Baseline (re-established this pass, after the `tab:h1bw` owner's edits) | 22 | 7 | 3 |
| After | 22 | 7 | **0** |

Same seven boxes at identical widths (37.82, 95.45, 33.58, 65.03, 2.85, 42.86,
80.55 pt). No new overfull or underfull boxes. `latexmk` exit 0.

---

## 9. Handed back — index and ledger wording

`INDEX.md` and `A1_PROVENANCE_LEDGER_2026-08-28.md` were not edited.

**For `INDEX.md`, "Withdrawn during 2026-09-03→04":**

> | `Sec7_Evaluation.tex`'s cold-admission control (390,524 bypasses, 79.5% coverage, 524,263→34,322) | `STATE_2026-09-01.md` (campaign r2 FAIL, "do not quote") | the paper cited a campaign that failed its own gate as a licensed proof. Replaced with r12's 682,901→436,911, which weakens the claim |
> | `Sec7_Evaluation.tex:61-67`'s twelve single-core magnitudes (4.24/4.90/4.60, 5.82/5.44/4.60 GB/s; 529k/354k/290k) | `H1BW_SINGLECORE_OUTCOME_2026-09-04.md` | body text still carried the archive's figures after `tab:h1bw` was replaced, so the two disagreed within one paper. Now 3.27/4.05/2.53, 4.10/4.85/2.53 GB/s and 262,244/137/83 per pass |
> | `tab:declpredx`'s "margins that grow with the victim" | `XCORE_SWEEP_2026-08-19.md` | margins are non-monotonic (10.0, 2.0, 13.8, 13.9 pp); replaced with "2–14 percentage points" |
> | `tab:gem5cfg`'s "conservative for every claim the model is cited for" | `H1BW_ARM_IDENTITY_2026-09-04.md` §Q4 | narrowed to the anchored under-prediction; the unrestricted form contradicted the adjacent caveat's "no direction" |
> | `Sec7_Evaluation.tex`'s recovery "falls monotonically" | `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` | the curve rises at 4.0 MB (81.95 → 82.33) |
> | `fig:io-to-load` and `tab:fused` as paper cross-references | this document §5 | both targets cut; `tab:fused` demonstrably existed (`CLAIM_REWRITE_2026-08-26.md:96,134`). Pointers removed, asserted figures verified against `E1_OUTCOME`, `M11B_OUTCOME` and `REDTEAM_REVIEW` |

**For the ledger, new record line:**

> `PAPER_RECONCILIATION_2026-09-04.md` — draft-wide claim reconciliation, 116
> claims, 20 edit sites, 8 unlocatable claims routed, 3 dangling cross-references
> resolved. Includes a full licensing audit of every paper citation against
> `INDEX.md`'s withdrawn/superseded tables and `STATE_2026-09-01.md`'s "Do NOT"
> lists: two violations found (r2, and the single-core archive rows), both
> fixed. No simulations launched, no `gem5/src/` or `gem5/logs/` modification,
> no `*_PREREG_*` edited.

## 10. Addenda appended to certified outcome documents

None required. Every supersession relied on here was already recorded in its
superseding document (`KERNEL_TEST_AGGREGATE_OUTCOME_2026-09-03`,
`HNFRP_REMAINING_CELLS_OUTCOME_2026-08-29`,
`CATMBA_REDUCTION_RESOLUTION_2026-09-04`, `H1BW_ARM_IDENTITY_2026-09-04`,
`H1BW_SINGLECORE_OUTCOME_2026-09-04`, `H1BW_SLICE_BRACKET_OUTCOME_2026-09-04`,
`FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30`, `STATE_2026-09-01`). This pass
consumed those findings rather than producing new ones about the campaigns.

**Constraints observed:** `INDEX.md` and `A1_PROVENANCE_LEDGER_2026-08-28.md`
not edited; no `*_PREREG_*.md` edited; no rebuild, no `gem5/src/` change,
nothing written under `gem5/logs/`, no simulation launched.

---

# Addendum 1 — 2026-09-04: the page budget above was measured on a document that was silently dropping text; `fig:recovery` narrowed; three queued corrections applied

**§8 "Page budget" is retracted in full.** Every figure in it — 22 pages, 7
overfull `\hbox`es — was measured against a `main.pdf` in which
`Sec7_Evaluation.tex` carried **35 unescaped `%`** in body prose (plus 11 in
`Sec3_Measurement.tex`, all inside comment lines, and 2 in `Appendix.tex`).
LaTeX treats each as a comment marker, so the remainder of each of those lines
never rendered. It compiled with zero errors and no overfull box, which is why
neither this document's check nor any other worker's caught it. The rendered
PDF read *"the neighbour's recovery under Streaming falls from 89.4that is a
weakness."*

The escaping was repaired by the draft's owner (48 sites, backups at
`/tmp/pctfix_*.bak`). **The true baseline was 23 pages and 8 overfull boxes.**

## A regression in the repair, found and fixed here

The 2 sites in `Appendix.tex` were **not** prose truncation. Lines 146–147 read

> `\providecommand{\cmark}{{\color{green!50!black}$\checkmark$}}%`
> `\providecommand{\xmark}{{\color{red}$\times$}}%`

where the trailing `%` is a newline-suppressing comment, the standard idiom.
Escaping them to `}\%` typeset two literal percent signs into the body; `%%`
was rendering in the appendix of the 23-page PDF. Reverted (edit 21). All 46
prose sites were correct and are untouched.

**Verified after the revert:** zero unescaped `%` remain in any `Text/*.tex`
body line, and `pdftotext | grep '^ *%%'` returns zero. Every figure this
document introduced already used `\%`.

## What the restored line-endings turned out to say

Twenty-six line-tails in `Sec7_Evaluation.tex` became visible for the first
time. None was *wrong*. Three were **redundant** once rendered, and those are
the cuts:

| Restored tail | Why it is redundant now that it renders |
|---|---|
| `Sec7:19` "delivers 8.42\% more tenant throughput and leaves the tenant 5.35\% faster than" | the section-summary sentence became an exact numeric preview of the paragraph that *derives* both figures 150 lines later (`Sec7:170-181`). Made qualitative; the numbers stay where they are earned |
| `Sec7:286` "32.3\% of the fills, and it recovers 22.6\%" | the same pair now appears three times — at the frontier result, here, and in the `fig:recovery` caption on the facing page. Cut here; kept at the derivation and in the caption |
| `Sec3:165-168` 91.4\% / 9.2$\times$ | `Sec3` forward-references `\S\ref{sec:eval}` for this experiment and then restates its two headline numbers in full. Compressed to the L2-hit detail that is unique to `Sec3` |

## Edits applied in this pass

| # | Site | Before | After |
|---|---|---|---|
| 21 | `Appendix.tex:146-147` | `...$\checkmark$}}\%` | `...$\checkmark$}}%` — stray `%%` no longer renders |
| 22 | `fig:recovery` caption | "Panels~(a) and~(b) report a registered sweep" | the five 2.0–4.0 MB sizes registered (45 runs); 6.0/8.0 MB an unregistered exploratory extension (18 runs); all 63 completed — verbatim from `RECOVERY_CURVE_OUTCOME_2026-09-04` add. 2 |
| 23 | `fig:recovery` caption | "inside the sweep's own run-to-run spread" | "a small excess that reproduces across seeds rather than a scatter effect" — verbatim, add. 2 |
| 24 | `Sec7` §tenant's own footprint | "falls from 89.4\% to 56.8\%, while a four-way CAT mask holds a flat 86--89\%" | 89.4\%→82.0\% between 2.0 and 3.5 MB, no further by 4.0 MB (82.3\%), across the five registered sizes; CAT declines ~4× more slowly, 89.3\%→87.3\%; seed spread <0.25 pp; 6.0/8.0 MB extension reported as exploratory — verbatim, add. 2 |
| 25 | `Sec7` same paragraph | "the mask buys its **flat** protection" | "its **far flatter** protection" — add. 2 |
| 26 | `fig:recovery` panels (a)/(b) + `\Description` | "a four-way CAT mask's does not"; "pays for that **flatness**"; "CAT **flat** near 87 percent" | "declines about four times more slowly"; "that flatter protection"; "declining only slightly, from 89 to 86 percent". **Not in add. 2's routed list** — found here, same withdrawn claim, same record |
| 27 | `Sec7:360` | "sealing a 256~MiB object takes 46.2~ms with 2~MiB pages and 49.3~ms with 4~KiB pages, nearly independent of page count" | "sealing costs $\sim$48~ms and is *size-independent*: a 4~KiB epoch costs the same as a 256~MiB one, because the cost scales with logical-CPU count rather than object size" — `RANGED_DRAIN_DOS_WRITEUP.md:23`. **Resolves U4.** **Framing restored 2026-09-04:** in the paper this sentence sits under the `\emph{Optional H3.}` heading (`Sec7:356`) and is followed at `Sec7:362-365` by "it is **not a cost of baseline H2**, which preserves ordinary coherence and requires no global clean". Quoted without those two anchors the cell reads as a baseline cost, which it is not — baseline H2 entry is **microseconds**. See "Correction — 2026-09-04" at the end of this file |
| 28 | `Appendix.tex` `tab:gem5cfg` Prefetch row | one row, "L1/L2 Stride(4) + DCPT" | two rows, "Prefetch (L1) — Stride(4) + DCPT" and "Prefetch (L2) — Stride(4) + Tagged". **Resolves U7 and §6.3** |
| 29 | `Appendix.tex` `tab:gem5cfg` Memory row | "256\,GiB DDR + 128\,GiB CXL" | "128\,GiB DDR + 128\,GiB CXL" — **F6.1, open since 2026-08-23** |
| 30–37 | 8 trim sites (below) | — | — |

### `tab:gem5cfg` — the recount the ledger row asked for

`A1_PROVENANCE_LEDGER_2026-08-28.md:142` asks whether the Prefetch row is the
already-counted defect or a second one. **It is neither: it is the already-counted
*imprecision*.** `W4.3_PROVENANCE_LEDGER_2026-08-23.md` §F6 is titled *"one
wrong capacity, one over-stated prefetcher"* and splits explicitly:

- **F6.1 — defect** = the **memory row** (`256 GiB` against `128 GiB`
  instantiated in all 214 run directories). Still open in the draft until
  edit 29 today.
- **F6.2 — imprecision** = the **Prefetch row** over-stating DCPT as covering
  both levels. Closed by edit 28 today.

So the count stays **1 defect, 1 imprecision**; what changes is that **both are
now applied to the draft**, five weeks after they were found. Corroboration
that F6.2 was only ever a *table* error: the adjacent fidelity caveat has always
described the stack correctly as *"a strided and a delta-correlating prefetcher
at the L1D, and a strided and a next-line prefetcher at the L2"* — `Tagged` is
gem5's next-line-with-tag-bit prefetcher, so prose and configuration agreed and
only the table did not.

## The trim: 23 pages → 22

Cut ~320 words. Every cut is a duplication, and no claim, figure or citation
was removed. Sites 30–37:

| # | Site | Cut |
|---|---|---|
| 30 | `Appendix.tex` §"Why the optional entry broadcast is conservative" + §"…unprivileged primitive…" | **merged two adjacent headings**. Both stated the broadcast is not an inherent H2 cost, and both prescribed bounding by sharers rather than logical-CPU count. All nine distinct points kept |
| 31 | `Appendix.tex` §"H2 in the fill path" | **deleted**. Its LLC-displacement sentence duplicated §"Line lifecycle" 20 lines later; its `ReadOnce` sentence duplicated §"Snoop filter" **verbatim** 40 lines later, and both duplicated `Sec6_Implementation:91-105`. Its two unique clauses (fill-destination predicate vs.\ replacement hint; per-request tag gating) folded into §"Line lifecycle" |
| 32 | `Sec7:19` | numeric preview of the frontier result (see table above) |
| 33 | `Sec7:286` | third statement of 32.3\%/22.6\% |
| 34 | `Sec3:165-168` | second statement of 91.4\%/9.2$\times$ |
| 35 | `Sec7` §Platform and scale | "The modeled frontier uses two cores, a 5~MiB shared cache, and one home node" — stated at `Sec7:33-37` |
| 36 | `Sec7` dominance paragraph, flush-behind and H3 limitations | three sentence-level compressions of restated points |
| 37 | `Appendix.tex` WC-arm note, fidelity caveat, prefetcher-interaction note | three compressions; the WC note stated "cannot be re-run" three ways |

| | Pages | Overfull | Undefined refs |
|---|---:|---:|---:|
| **True baseline** (after the `%` repair) | **23** | **8** (7 `\hbox`, 1 `\vbox`) | 0 |
| **After this pass** | **22** | **7** (7 `\hbox`, 0 `\vbox`) | 0 |

The seven `\hbox`es are the same seven, at **identical widths** (37.82, 95.45,
33.58, 65.03, 2.85, 42.86, 80.55 pt). The `\vbox` overflow is gone. Edit 28
initially widened `tab:gem5cfg` from 80.55 to 119.62 pt; the two-row form
restores it to 80.55 pt exactly. `latexmk` exit 0.

## Unlocatable claims — updated

**Resolved this pass: U4** (seal cost, edit 27) and **U7** (prefetch row,
edit 28). **Six remain**, unchanged and none deleted: U1, U2, U3, U5, U6, U8.
U3 remains the one where the established response would apply — the draft
claims an AMD **cross-socket** placement result and no record contains one,
while the **other-CCX, same-socket** arm it does have is cited correctly at
`Sec7:313`.

## Handed back — new rows only

`INDEX.md` and `A1_PROVENANCE_LEDGER_2026-08-28.md` not edited.
`RECOVERY_CURVE_OUTCOME_2026-09-04.md` add. 2 has already queued its own rows
for the `fig:recovery` narrowing, the `R(cat4)` "flat" withdrawal, the 10σ
excess, and `FUSED_TABLESWEEP_PREREG`'s liveness assertion. **Those are not
re-proposed here.** Three rows are new:

**For the ledger, amending the `tab:gem5cfg` row** (recount, as it asked):

> **Both items applied to the draft 2026-09-04.** F6.1 (memory row, `256 GiB`
> → `128 GiB` DDR) and F6.2 (Prefetch row, split into `L1 Stride(4)+DCPT` /
> `L2 Stride(4)+Tagged`). The count is unchanged — the Prefetch row is the
> already-counted **imprecision**, not a second defect — and the row is now
> clean at 15/15.

**For `INDEX.md`, "Withdrawn during 2026-09-03→04":**

> | `Sec7_Evaluation.tex`'s seal costs, "46.2~ms with 2~MiB pages and 49.3~ms with 4~KiB pages" | `RANGED_DRAIN_DOS_WRITEUP.md` | the pair traces only to the HotStorage'26 draft and to no campaign record. Replaced with the record's **~48 ms, size-independent**, which is also the stronger statement: the cost scales with logical-CPU count, not object size. **This is an `\emph{Optional H3}` oracle cost, not a baseline H2 one** (`Sec7:356`, `Sec7:362-365`); baseline H2 entry performs no global clean and is measured in **microseconds**. Framing restored 2026-09-04 — see the correction at the end of this file |
> | `tab:gem5cfg`'s memory row, "256~GiB DDR" | `W4.3_PROVENANCE_LEDGER_2026-08-23.md` §F6.1 | all 214 run directories instantiate `mem_ctrls[0]` over 128 GiB. Found 2026-08-23, applied 2026-09-04 |

**For `INDEX.md`, a rendering-fault row** (per add. 2's request that this
document's U-list carry it — recording it here since `INDEX.md` is not ours):

> | 48 unescaped `%` in `Text/*.tex` body prose (35 in `Sec7`, 11 in `Sec3` comments, 2 in `Appendix`) | this document, add. 1 | LaTeX commented out the remainder of 35 lines, silently deleting ~46 sentence-tails including four numbers in the `fig:recovery` paragraph. **It compiles clean and passes both a page-count and an overfull-box check**, so it is invisible to the standard length gate; every "22 pages" reading recorded on 2026-09-04 before the repair was measured on a truncated document. Repaired; the true count was 23. Two of the 48 were newline-suppressing comments wrongly escaped by the repair, typesetting a literal `%%`, and were reverted |

**Constraints observed:** `INDEX.md` and `A1_PROVENANCE_LEDGER_2026-08-28.md`
not edited; no `*_PREREG_*.md` edited; `RECOVERY_CURVE_OUTCOME_2026-09-04.md`
read only, not rewritten; no rebuild, no `gem5/src/` change, nothing written
under `gem5/logs/`, no simulation launched.

---

## Correction — 2026-09-04: the 48 ms rows' `Optional H3` framing, and the DoS argument checked end to end

### 1. What changed in this file

Edits 27 and the `INDEX.md` hand-back row both quote today's paper text
correctly and **drop the framing that makes it correct in situ**. In
`Sec7_Evaluation.tex` the sentence sits under the heading `\emph{Optional H3.}`
(`Sec7:356`), is introduced by "We do price one deliberately conservative
clean-home oracle" (`Sec7:359`), and is closed by "it is **not a cost of
baseline H2**, which preserves ordinary coherence and requires no global clean"
(`Sec7:362-365`). Quoted without those anchors, "sealing costs $\sim$48~ms and
is *size-independent*" reads as a baseline transition cost. **It is not**, and
at the kernel tip nothing in baseline H2 costs milliseconds: entry is
**72–90 µs** (QEMU/KVM, four boots) and **124 µs** in gem5 r12, the latter
clock-quantisation-limited (see
`KERNEL_TEST_AGGREGATE_OUTCOME_2026-09-03.md`, addendum 2026-09-04). Both rows
now carry the framing inline; **neither quotation was altered**, per `A6.19`.
**The paper needed no change for this** — the exposure was this document being
quotable out of context.

### 2. The DoS argument: the paper is clean, and it was made clean on 2026-09-02

Checked today across all eleven `Text/*.tex`, in both `HEAD` (`75d8841`) and the
working tree. **`DoS`, `denial`, `storm`, `attack`, `adversar`, `malicious` and
`threat` appear nowhere.** `unprivileged` appears exactly once:

- **working tree** `Appendix.tex:669`, under `\heading{Why the **optional** entry
  broadcast is conservative, and why ranging alone does not close it}`, whose
  subject is set at `Appendix.tex:660` as "The prototype's **H3-oracle**
  $\sim$48~ms entry cost", called "**not an inherent H2 cost**" at 663, and
  closed at 674 with "**Removing the broadcast from H2 closes it** for the
  portable path."
- **`HEAD`** `Appendix.tex:650,653`, under `\heading{The **optional** entry
  broadcast is an unprivileged primitive…}`, preceded by the same "H3-oracle" /
  "not an inherent H2 cost" anchors and containing "Removing the broadcast from
  H2 closes this problem for the portable path."

Both are correctly scoped, and the availability claim is **true of the oracle**:
`mm/mprotect.c:900` gates the global clean on `IS_ENABLED(CONFIG_PAT_STREAMING_H3_SEAL_ORACLE)`
with **no privilege check**, so in an oracle build any process does trigger it.
The scoping is what matters, and it is present. Four further sites say the same
thing independently: `Sec5_Streaming.tex:156`, `Sec6_Implementation.tex:55`,
`Sec6_Implementation.tex:142`, `Sec6_Conclusion.tex:23`.

**The concern was well founded historically.** At `c6f5c80` (2026-08-19) and
`1058877` (2026-08-24) the heading read `\heading{The entry broadcast is an
unprivileged primitive…}` — **no "optional", no "H3-oracle" anywhere in the
file** — and the surrounding text said "we report the un-relocated number
because it is the one we measured". That version *did* present the DoS primitive
as a live property of the mechanism. It was rescoped at **`7abf70b`
(2026-09-02)**, which introduced both "optional" and "H3-oracle". Edit 30 of
this pass ("merged two adjacent headings") then merged the two paragraphs,
preserving the scoping. **So the defect existed, and was closed two days before
this sweep looked for it.** No paper edit is proposed; cost **0 words**, which
matters at 22 pages with under a caption line of slack.

**One thing for the lead, not a defect.** The rescoping and edit 30 are **not
committed** — seven `Text/*.tex` files are modified in the `STREAMING_Paper`
working tree, and `HEAD` (`75d8841`) still carries the pre-merge two-heading
form. The committed form is correctly scoped too, so there is no claim risk
either way; but the trim this document records is unsaved. Not committed here,
per this pass's constraints.

### 3. `SUBMISSION_READINESS_2026-08-19.md` — the earlier decision not to annotate is **endorsed**

That file asserts 48 ms as a live cost twice — line 47 ("a disclosed weakness
(the unprivileged 48 ms DoS)") and line 118, C10 ("48 ms measured on silicon;
mitigation implemented but **unmeasured**"). A prior pass declined to annotate
it, reasoning that its staleness is **global rather than local**, so correcting
one clause would falsely imply the other eleven matrix rows are current. **That
reasoning is endorsed, on two grounds, and the file is left unedited.**

*First, the premise is not merely sound — it is understated.* Re-verified today,
the 48 ms clauses are two of at least **five** independently stale sites, only
two of which this sweep would have touched:

| site | why stale at the tip |
|---|---|
| Part 1, "A ranged drain now exists in the prototype (PR #3, boot-tested)" | `888060f6a66e` removed the `streaming_drain_range()` **call site**; no caller in the tree |
| Part 2 OS item 1, "The mitigation is merged and boot-tested in QEMU; its benefit is unmeasured" | entry is now measured in µs; the exit arm is unreachable without reverting code |
| Part 2 OS item 1, "the unprivileged 48 ms DoS" *(line 47)* | not a baseline cost |
| Part 3, C4, "sealed memfd merged" | `888060f6a66e` narrows admission to private anon/hugetlb; the tip asserts `EINVAL` for a sealed single-mapper memfd |
| Part 3, C10, "48 ms measured on silicon; mitigation … **unmeasured**" *(line 118)* | measured; and not a baseline cost |

Annotating two of five would produce exactly the false signal of currency the
prior pass predicted: a reader seeing two dated corrections in a matrix
reasonably infers the remaining rows were checked. That is **worse than no
annotation**, because it upgrades "undated snapshot, read with suspicion" to
"audited document, two known issues".

*Second — and this is the ground the prior pass did not cite — the supersession
is already recorded, at the right granularity, in the successor document.*
`REVIEWER_STATE_2026-08-24.md:15-20` carries an explicit, dated,
**document-level** notice naming this file: "`SUBMISSION_READINESS_2026-08-19.md`
and `REVIEWER2_RESPONSE_2026-08-19.md` predate W1's replication, W2.1's
de-confound, W3.1's H3 null, W7's failure and W8's attribution result. Where
they and this memo disagree, **this memo is later** … Neither is withdrawn."
Global staleness already has a global annotation. Adding per-clause blocks would
duplicate it at the wrong granularity and contradict its "neither is withdrawn"
framing. **The correct action is the one taken: none.**
