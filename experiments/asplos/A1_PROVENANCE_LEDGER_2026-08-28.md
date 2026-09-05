# A1 --- fresh provenance ledger: every published number re-bound to an artifact

Built 2026-08-28. Supersedes `W4.3_PROVENANCE_LEDGER_2026-08-23`, which predates
four withdrawals, the S1-1 retraction, M6--M12, E1, E2, E2B, and three rewritten
tables.

**Method, and it is the same as W4.3's:** for each published table, recompute the
cells **from the raw artifact**, not from a summary that claims them. A row says
VERIFIED only where the recomputation ran here today and matched. Where it
disagreed, the disagreement is stated.

Distinct from `QUANTITY_INDEX_2026-08-28` (A2): that maps *quantity -> owning
document*. This maps *published table -> raw artifact -> does it recompute*.

---

## Ledger

| table | artifact | in git? | recomputed today | verdict |
|---|---|:--|---|---|
| `tab:amdcat` | `experiments/phase1/e1_residual_decomp/e1gate_raw_n12.jsonl`, `e1gate_rerun_n6.jsonl` | **yes** (`e14e621`, `6caf699`) | WB 19.886 / 20.545; CAT 7.225 / 9.867; WC 0.989; removed 54.6%; WC rate 57.3% of WB | **VERIFIED --- 7/7** |
| `tab:fused` | `results/clos_split/raw/` (660 files) + `PROVENANCE.md` | **yes** (`a41df38`) | 336.99/87.65, 281.02/105.12, 253.36/115.81, 234.44/126.86, 214.98/95.37, 214.58/95.69, 298.06/98.37, 336.58/88.45 | **VERIFIED --- 8/8 quantitative cells** |
| `tab:catmba` | `benchmarks/data/catmba_s*.csv` (11 files, 660 rows, 11 conditions x n=60) | **yes** (`ebd93a4`) | artifact present and complete; W4.3's 14/14 cell verification stands | **VERIFIED (inherited)** |
| Sec5 trade-off table (inline, `Sec5:471`) | `benchmarks/data/m12b_victim/m12b.jsonl` | **yes** | 2.258 / 1.311 / 1.122 / 1.120; victim's own cost 13.1% | **VERIFIED --- 5/5** |
| Sec5 decomposition table (inline, `Sec5:224`) | `benchmarks/data/e2b_footprint/e2b.jsonl` | **yes** | 100.7 / 100.7 / 96.6 / 74.1 / 14.3% | **STALE IN PAPER** --- the paper still shows M5/M3b's three rows at two stream sizes; E2B supersedes it |
| `tab:gem5` (hw cols) | `benchmarks/data/emr_cxl8.csv`, `emr_local4.csv` | yes (`ebd93a4`) | not re-run today | VERIFIED 2026-08-23, unchanged since |
| `tab:gem5` (gem5 WB col) | `GATE1_LOCALDRAM_COLUMN_OUTCOME.md`, gem5 `b2c6499194` | yes | not re-run today | VERIFIED 2026-08-23, unchanged since |
| `tab:gem5` (+H2 col) | --- | --- | --- | **DECLARED GAP** --- never re-instantiated at the WB column's commit. Open since 08-23. |
| `tab:sens` | `GATE1_SENS_RERUN_OUTCOME.md`, gem5 `b2c64991` | yes | not re-run today | VERIFIED 2026-08-23 |
| `tab:declpredmeas` | `TASK28_PREDICTOR_HEADTOHEAD_2026-08-18.md`, gem5 `0f37c28` | yes | not re-run today | VERIFIED 2026-08-23 (18/18) |
| `tab:declpredx` | `XCORE_SWEEP_2026-08-19.md`, gem5 `0f37c28` | yes | not re-run today | VERIFIED 2026-08-23 (24/24) |
| `tab:h1bw` | `experiments/asplos/data/gem5/h1bw_singlecore.jsonl`, nine per-cell records; retained `stats.txt`/`config.ini`/`MANIFEST.json`/`DONE.json` under `logs/se_chi_h1bw_sc/`. Was `results/gem5_streaming/REPORT.md` §1, which is **not** provenance for anything the table now prints | **yes** (`6fa71f5`) | not re-run here; certified 2026-09-04 by `analyze_h1bw_singlecore.py`, 6/6 primary cells on twelve fail-closed gates | **REPLACED, NOT REPRODUCED** (F3 **closed on replacement** --- the archive's twelve magnitudes are unpublished rather than repaired; see F3 below) |
| `tab:h3sf` | `/tmp/sf_*` | **no** | --- | **DATA VERIFIED, ANNOTATION WRONG** (F4, open) |
| `tab:appplat` | live host state | n/a | not re-read today | VERIFIED 2026-08-23 |
| `tab:gem5cfg` | run dirs in `/tmp` | **no** | --- | VERIFIED 13/15 2026-08-23; 1 defect, 1 imprecision |
| `fig:recovery` (all three panels) | `data/gem5/kn_runs.jsonl` (**45** records, 2.0–4.0 MB) + `data/gem5/kb_runs.jsonl` (**18** records, 6.0 and 8.0 MB); quiescent denominator `data/gem5/fh_runs.jsonl` (`fh_qui`, n=3, 33.8814 cyc/access). Runners `run_fused_knee.sh`, `run_fused_knee_big.sh`; figure built by `make_recovery_curve.py` → `figures/recovery_curve.pdf`. Registered by `FUSED_KNEE_PREREG_2026-08-29.md`; campaign closed by `FUSED_KNEE_CLOSED_2026-09-04.md`. **Raw launch and completion evidence for all 63 runs added 2026-09-04 at `3ed6ff0`: `artifacts/fused_knee/`**, the 63 sibling `.log` files carrying gem5's own `gem5 started` banner plus the two `*_sweep.done` runner stamps, byte-for-byte originals (65 files, 223.5 KiB), with the **504** larger per-run originals (`stats.txt`, `config.json`, `config.ini`, `citations.bib`, `fs/**`, 124.79 MiB) SHA-256'd rather than committed in the same directory. Selection argued in `FUSED_KNEE_RUNLOG_PROVENANCE_2026-09-04.md`; **the two banners are not one banner** — 45 `kn_*` at `Aug 29 22:58:38` and 18 `kb_*` at `Aug 30 01:33:02`, two separate launches | **archives yes** (`acc722a`), **runners yes** (`94bfbef`), **generator yes** (`9791976`). `make_recovery_curve.py` was untracked when this row was first written; it is tracked as of 2026-09-04, so the figure is no longer built by a file in no commit. One input this row's artifact list does not name: panel (c)'s held-out complete-join point reads `data/gem5/r5_runs.jsonl`, which was untracked until `fee8417` | **recomputed here today from the raw archives**, `R = (wb − arm)/(wb − qui)`, at 2.0 / 2.5 / 3.0 / 3.5 / 4.0 / 6.0 / 8.0 MB. `R(h2)` = **89.44 / 87.69 / 84.51 / 81.95 / 82.33 / 67.14 / 56.84 %**; `R(cat4)` = **89.26 / 88.20 / 87.79 / 87.45 / 87.26 / 86.25 / 86.31 %**; `wb` tax 1.4679 / 1.5012 / 1.5141 / 1.5186 / 1.5100 / 1.5223 / 1.5477x; tenant L2 misses per kilocycle vs `wb`, `h2` **+4.14 / +7.07 / +11.92 / +12.03 / +7.81 / +11.38 / +10.42 %** (faster at every size) and `cat4` **−15.84 / −23.54 / −23.17 / −24.22 / −19.28 / −18.95 / −22.09 %**. **That list read six values and the analyzer prints seven**; the missing one was 6.0 MB's **−18.95%**, and the omission was carried by a clause that rationalised it — quoted rather than deleted, per `A6.19`: "at the six sizes where protection is matched". `analyze_registered_scope.py` prints a `t(cat4)` at **all seven** sizes, so there was no sixth-versus-seventh distinction to make and the gap was simply a transcription short by one. Corrected 2026-09-04 and re-run to confirm; nothing else in the row moves. Every cell matches `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` and `RECOVERY_CURVE_OUTCOME_2026-09-04.md` to the digits printed there | **VERIFIED --- 63/63.** Every record `completed: true` and `reason: ok`; `realized_table_mb` non-null in all 63, covering exactly {2.0, 2.5, 3.0, 3.5, 4.0, 6.0, 8.0}; 7 sizes x 3 arms x 3 seeds; **none dropped and no size omitted**. Two things this row does **not** certify: the *attribution* of the sweep to a pre-registration (**`F15`, open**, below), and counter-based engagement evidence — `hnf_streaming_bypasses` is **absent, not zero**, from every one of the 63 records, so panel (c)'s declared share is obtained by differencing allocations because it is the only definition the fused build supports |
| `tab:declpred`, `tab:checklist`, `tab:contract`, `tab:workload_taxonomy` | --- | n/a | qualitative | no quantitative provenance to bind |

## New numbers added to the paper this week, and their bindings

| number | in paper | artifact | verdict |
|---|---|---|---|
| 12.4 / 3.2 GB/s single-core WB/WC | yes, 5 places | `experiments/phase1/e4_hygiene/RESULTS.md` | bound; supersedes 15.8/4.2 |
| 55% CAT removal (within-run) | yes | recomputed above from `e1gate_rerun_n6` | **VERIFIED today** |
| WC rate gap, 57.3% of WB | yes, disclosed | recomputed above | **VERIFIED today** |
| 13.1% victim confinement cost | yes | `m12b_victim`, reproduced in `e1b_frontier` | **VERIFIED today** |
| 16.7% tenant cost at 8 ways | yes | `m12a_isocost`; confirmed by `e2_reconcile` (+17.1%) and `e1a2_paired` (+16.9%) | **VERIFIED three ways** |
| 0.9 of 16.7 points recovered | yes | `m12a_isocost` | bound |
| 1.16--1.47x hit-rate range | yes | `m7_hitrate` | bound |
| 1.00/1.01/1.06 and 1.53/1.40/1.12 mask-capacity | yes | `m8_tablefit`, `m10_maskboundary`, `m10b_control` | bound |
| 1.26x vs 1.22x stream-control | yes | `m9_streamcontrol` | bound |
| AMD cross-socket 0.993--0.999x, and the same-socket 1.30x now cited in `Sec3` as well as `Sec7:313` | yes, `Sec3_Measurement.tex:151-155` | `data/amd_xsocket_2026-09-04/amd_xsocket.jsonl` (**400** records, 20 per cell over 2 THP x 2 WSS x 5 placements), diagnostics `d1_distance.jsonl` and `d23_gatecheck.jsonl`, provenance `amd_xsocket.jsonl.provenance.json`, all 240 streamer logs in `agg_logs.tar.gz`; **all committed** at `c34305f` and `03f4613`. Runner `broker/amd_xsocket.py` and analyzer `analyze_amd_xsocket.py` committed **before launch** at `d65f768` (01:26:55 KST) against a campaign start of 01:34:20 KST, judged against `AMD_XSOCKET_PREREG_2026-09-04.md` frozen in the same commit. Binaries deliberately not in-tree (`broker/README.md`): `victim` sha256 `90089579…`, `aggressor` sha256 `583257f5…`, both mtime 2026-08-23 15:24, recorded per run | **VERIFIED --- 400/400**, and re-runnable rather than transcribed: `analyze_amd_xsocket.py data/amd_xsocket_2026-09-04/amd_xsocket.jsonl` reproduces the verdict from a **seeded** bootstrap (`20260904`), so the interval that decided it is deterministic. Every record emits a `VICTIM` line, 20 per cell, **none dropped**; 0 quiescent runs with nonzero streamer bandwidth; realized placement recorded **per run** and read from the artifact rather than the launcher (`S5.1`). Two things this row does **not** certify: the campaign is **NOT CERTIFIED** on gates `G4` and `G6b` (`F17` below), and the number is a **`C`-verdict** number --- anyone quoting `0.993`--`0.999x` must also say that the pre-registered rule declined to call it noise |

## Two corrections A1 forced on A2, written the same day

Building this ledger caught **two errors in the quantity index I wrote hours
earlier** --- which is the argument for doing both rather than one:

1. **A2's gap 4 was wrong.** It says *"`tab:fused`'s raw data is still not in git
   (F1, open since 08-23)"*. **F1 was closed on 08-23**, by commit `a41df38`,
   hours after W4.3 opened it: 660 raw records plus a `PROVENANCE.md` stating the
   four defects at the data. I read W4.3's finding and did not check whether a
   later commit closed it --- **the identical failure A2 exists to prevent, committed
   inside A2 itself.** Fourth instance this week.
2. **A2 understated `tab:fused`'s standing.** With the data pinned, its eight
   quantitative cells recompute exactly today. The remaining defects are the ones
   `PROVENANCE.md` already states at the data --- the way-sweep runner is in no
   commit, the way count comes from the filename rather than the instrument, at
   least two uncommitted binaries produced the nine rows, and `hot_bytes` records
   the request not the resident table --- but the *numbers* are sound.

## Provenance defects

Written 2026-08-28 as "open provenance defects, all inherited and none new".
Both clauses have since expired: the status column is maintained in place, and
`F14` below was opened and closed on 2026-09-04. Every change of status is
dated in "Status history" underneath the table, so a row that has moved can be
read back to what it said before.

| id | defect | since | status |
|---|---|---|:--|
| F3 | **F3 — `tab:h1bw`, twelve magnitudes: CLOSED on replacement, 2026-09-04.** The original twelve figures remain unbacked and are now unpublished: their artifacts never existed beyond a 4,609-byte hand-written `REPORT.md` in `preserved/gem5_streaming.tar.gz`, and their runner (`knee_sweep.sh`) and binary are absent from this host. They are superseded rather than repaired. `tab:h1bw` now carries six certified cells from `H1BW_SINGLECORE_OUTCOME_2026-09-04.md` — 3 arms x `L1_MSHR` {16, 48} at `L1_REPL = 48`, pre-registered at commit `b4ac57c` before any cell emitted a statistic, 6/6 passing all twelve fail-closed gates, with retained `stats.txt`, `config.ini`, per-cell `MANIFEST.json`/`DONE.json` and `data/gem5/h1bw_singlecore.jsonl`. Counters are window-bracketed, so the footprint column and the bandwidth column describe the same interval. Provenance: `gem5.opt` `cb290444…` (not rebuilt), benchmark `cxl_join_bench.gem5wbrk` `2b9d6732…`, `configs_git_describe` `build-cb290444-1-gfa27f665db` recorded at launch. **Disclosure: these are new magnitudes from a new harness, not a recovery of the old ones.** 6 of the archive's 12 figures reproduce within 20% (pre-registered outcome B). The archive's ordering is corroborated at 48 MSHRs and its 16-MSHR ordering is not: it had WB below `pf-off`, and the certified sweep has WB above at both depths. The archive's third arm was mislabelled `WC`; gem5 has no write-combining memory type (`H1BW_ARM_IDENTITY_2026-09-04.md`), and the arm is labelled `pf-off`. **This cell supersedes a same-day edit that kept F3 open; both prior states are quoted in "Status history" below** | 08-23 | **closed on replacement** 2026-09-04 |
| F4 | `tab:h3sf` annotation names a commit predating the required one | 08-23 | **open** |
| F14 | `fig:recovery`'s axis is **post-hoc** and its single external validation is **metric-dependent**. The relation "recovery is bounded by the declared range's share of shared-cache fills" was identified after the data existed; panels (a)/(b) rest on the registered sweep `FUSED_TABLESWEEP_PREREG_2026-08-29.md` but panel (c)'s x-axis does not. The one held-out point (complete join, r5) is metric-dependent: differencing home-node allocations gives a 32.32% share against `R = 22.59%` and the bound holds with 9.7 pp slack, while the later `hnf_streaming_bypasses` counter puts the same point at **17.43%** and the bound is **violated by 5.2 pp**. The differencing choice is forced rather than chosen — `hnf_streaming_bypasses` is absent entirely from every fused record — but the constraint became visible only after the alternative was computed, so it is a researcher degree of freedom and not a pre-registration. Mitigating and recorded as such: **nothing is fitted** (the panel-(c) line is `y = x`, zero free parameters), **point selection is verified clean** (63 records, 7 table sizes x 3 arms x 3 seeds, every record `completed: true`, no point dropped and no table size omitted), and the mechanism is corroborated independently by `W1.4_CHARGE_DECOMPOSITION_2026-08-24.md`. FS r6e is off the curve because its **`R` of 101.92% exceeds 100%, which no share can bound** — not because its counters are whole-run. That figure appears here only as the ground for exclusion; `FS_COMPLETE_JOIN_OUTCOME_2026-09-04.md`'s standing instruction to report `R ≈ 100%` and never quote 101.92% as a result is unchanged. See `RECOVERY_CURVE_OUTCOME_2026-09-04.md` add. 1 and `FS_COMPLETE_JOIN_OUTCOME_2026-09-04.md` add. 1. **Logged closed by disclosure, not open, because the claim was weakened in the paper to match the evidence.** The disclosure now lives in the `fig:recovery` caption in `Sec7_Evaluation.tex` — which states that panel (c)'s axis was chosen afterwards, that nothing is fitted, and that the fill-bypass counter puts the complete join at 17.4% — and in full in `RECOVERY_CURVE_OUTCOME_2026-09-04.md` Addendum 1, whose "Licensed / Not licensed" paragraph is the governing statement. The withdrawn phrasing ("played no part in establishing the relation and lands on it"; "two tenants, a 3x range of declared share, and one relation") is out of the draft | 09-04 | **closed by disclosure** 2026-09-04 |
| F15 | **`fig:recovery`'s "registered sweep" attribution names the wrong pre-registration, and its 8.0 MB endpoint — which carries the headline — is in no pre-registration's design.** `RECOVERY_CURVE_OUTCOME_2026-09-04.md` add. 1 defends panel selection with "the seven fused points are the whole of a registered sweep (`FUSED_TABLESWEEP_PREREG_2026-08-29.md`)", and the `fig:recovery` caption in `Sec7_Evaluation.tex` carries "Panels~(a) and~(b) report a registered sweep." **The defence is substantially right and the data is sound** — no point was dropped, all 63 records are `completed`, and the row above verifies 63/63. What is wrong is the credit. Registered by `FUSED_KNEE_PREREG_2026-08-29.md`, not by `FUSED_TABLESWEEP_PREREG`: **2.0, 2.5, 3.0, 3.5, 4.0 MB** are that pre-registration's five-size design, plotted from `kn_*` via `run_fused_knee.sh`. **6.0 MB** is a size `FUSED_TABLESWEEP_PREREG` registers, but *its* runs (`ts_*`) are at the aliased power-of-two probe stride and **are not plotted**; the plotted 6.0 MB point is `kb_*`. **8.0 MB is in no pre-registration's design at all.** `FUSED_TABLESWEEP_PREREG` registered {1, 2, 4, 6} plus a reused 3 MB point and explicitly named 6 MB as its top end ("Explicitly NOT predicted --- the shape at the top end"); its executed sweep `ts_runs.jsonl` (45 records) covers {1, 2, 4, 6, 8}, itself one size beyond its own registration, and **none of its runs appears in the figure** --- 36 of those 45 records carry a null `realized_table_mb`, verified here today. The consequence worth stating plainly: **8.0 MB is the endpoint of the paper's headline range** ("falls from 89.4% to 56.8%") **and is the least-registered point on the curve.** The honest attribution, per `FUSED_KNEE_CLOSED_2026-09-04.md`, is that panels (a)/(b) report `FUSED_KNEE_PREREG`'s sweep, **extended by two sizes that were not pre-registered**, all 63 runs of which completed and none of which was dropped. Two knock-on notes: **`F14`'s own cell above repeats the wrong attribution** ("panels (a)/(b) rest on the registered sweep `FUSED_TABLESWEEP_PREREG_2026-08-29.md`") and is corrected by this row rather than rewritten, per `A6.19`; and this is a **separate defect from `F14`, not a reopening of it** --- `F14` is about panel (c)'s axis being post-hoc and closed by disclosure, whereas this is about panels (a)/(b)'s registration credit. **No number moves**, in this ledger or in the paper. **Logged open and deliberately not resolved here**: a separate worker is analyzing what the headline claim should be narrowed to, and the caption is paper text owned by the reconciliation pass, so nothing was edited in `Sec7_Evaluation.tex` or in the certified outcome document | 09-04 | **open** |
| F13 | **The `gem5.opt` behind every published magnitude in three campaigns was replaced in place on 2026-09-04, and at the moment of replacement its source state was captured by no commit.** Reserved here since 2026-09-04 and **registered for the first time today**, as `BUILD_PROVENANCE.md` asks in its §5 and its §"Open". Same family as `F10` — a result whose launcher was never committed — applied to the **simulator** rather than to the harness: "a transcript is not an artifact". Scope is the `h1bw_multicore`, `h1bw_cxlbw` and `h1bw_slice_bracket` campaigns. `cfd37207` (compiled 2026-08-31 12:40:39) produced all 21 completed `h1bw_mc_*_20260904` cells and was overwritten 2026-09-04 12:51; it survives only as tag `build-cb290444`'s sibling `build-cfd37207`, which is **a reproduction point for those 21 cells, not a photograph of the tree** (§3 states the three places it departs from one). `cb290444` produced the three `*_20260904fix` cells. A related half of the same defect: `gem5_sha256` is **not** sufficient provenance, because `configs/` is read from the working tree at run time, so the six `bwt` cells ran an 08-31 binary against an 09-03 `Ruby.py`. Prevention is **implemented at build time** (`gem5/scripts/build_gem5.sh`, `fa27f665db`) rather than in a run manifest, that being the only point where source and binary provably coexist. Four older compile dates in `gem5/logs/` console logs are covered by no tag and were not investigated; anything still cited from those runs carries this defect unrepaired. **Repaired in two halves on 2026-09-04, by two different actions, and the second landed while this row was being written.** *Identity:* commit `065fd80` advanced this repository's gem5 gitlink `b0eea53b → fa27f665`, so the recorded simulator is the one that produced the cells — a checkout at `b0eea53b` gets a gem5 without the `isStreaming` retry-path fix, i.e. one that cannot produce them. *Reachability:* a separate property, and this row first stated it as unrepaired. **That wording is superseded within the day and is quoted rather than deleted, per `A6.19`:** "Verified here today: all **19** STREAMING commits on the submodule's `pr4-work` are unreachable from every remote-tracking ref in this clone, and `b0eea53b` was **one of them**, so the pointer `065fd80` replaced was **already unfetchable from any clone**. `git submodule update` failed from a clone before `065fd80` and still does; what changed is which unfetchable commit is named. The build tags stand in the same position — `build-cb290444` has **18** unpushed ancestors and `build-cfd37207` **13** … **The remaining action is a push, not a commit**, and it is outside this repository's tree." **Every figure in that paragraph was correct when measured and the conclusion is now false**: `pr4-work` and all three build tags were pushed to `origin` at `2026-09-05 01:51:32 +0900` (KST; project-local 2026-09-04), which is after this row's check ran and before it was committed. Re-verified here after an explicit `git fetch --all`: `git rev-list HEAD --not --remotes` is **0**, `origin/pr4-work` resolves to `fa27f665db`, and `git ls-remote --tags origin` carries `build-cb290444`, `build-cfd37207` and `build-481d7e12` as annotated tag objects dereferencing to `a5f366456e`, `830905739a` and `1bb6418e01`. `BUILD_PROVENANCE.md` records the end-to-end check this ledger did not have to repeat: a throwaway clone of this superproject at `065fd80` followed by `git submodule update --init gem5` fetched from GitHub and checked out `fa27f665db`. **The lesson worth keeping is methodological**: `git rev-list --not --remotes` reads *local* remote-tracking refs, so an unfetched clone reports a push as absent — that is what happened here, and a reachability claim should be made only after a fetch. **Logged open on one remaining ground, and it is not the simulator.** The **superproject is unpushed** — `main` carries **95** commits absent from `origin`, whose `main` is still `73f0332f6c` — so the simulator is now obtainable while the pointer naming it is not visible to a third party. `BUILD_PROVENANCE.md` tracks that as a superproject push separate from `F13`, and this row agrees with that scoping: `F13`'s own subject, the simulator behind three campaigns, is **recoverable by commit and by label**. What the push did **not** touch are the two limits stated earlier in this cell — the four untagged compile dates, and `build-cfd37207` being a reproduction point rather than a photograph of its tree. **That last remaining ground is now discharged too, later the same day, and the wording above is superseded rather than deleted, per `A6.19`:** "The **superproject is unpushed** — `main` carries **95** commits absent from `origin`, whose `main` is still `73f0332f6c` — so the simulator is now obtainable while the pointer naming it is not visible to a third party." Verified here after a fetch and confirmed **server-side** rather than from local remote-tracking refs, which is the discipline this row's own lesson demands: `git ls-remote origin refs/heads/main` on `https://github.com/jaewan/DutyFree.git` returns **`322c9564ee`**, the push having moved `origin/main` `73f0332f6c → 322c9564ee` (**103** commits); `git ls-tree 322c956 gem5` records **`fa27f665db02`**; and `git ls-remote origin pr4-work` in the submodule resolves `pr4-work` to that same `fa27f665db02`. So a third party cloning the published superproject now reaches the simulator behind the three campaigns by pointer as well as by commit and label. **`F13` therefore closes outright.** Two things it does not license: the ninety-five figure was never re-derived and does not verify against anything measured here (the published range `73f0332f6c..322c9564ee` is **103** commits, and `322c9564ee..main` was in double figures and rising while this pass ran, other workers still committing), and the repository around the pointer is **not** fully published — what remains unpublished is enumerated in the close-out below. **One item is folded into this row rather than given a number of its own, because it is this row's second half — reachability of a pin — on the sibling submodule.** `c34305f` re-pinned `linux` `0f82e89 → 6a7e5b09bd8b`, a commit that existed only in the local submodule, so from the moment of that commit `git submodule update --init linux` could not succeed from any clone and the superproject could not usefully be published again. `081bc3d` registered the bump and misdiagnosed it: it recorded the loss as **searchability** — "`git log -- linux` names `c34305f` as the commit that re-pinned the prototype, and its message gives a reader no reason why" — and stated that "a clone gets the right kernel and nothing measured moves", which was false for any clone, the pointer being unfetchable rather than merely unexplained. Checked live in this pass rather than inherited, and it has since closed: the submodule's `origin/pr4-work` reflog records the push of `6a7e5b09bd8b` at **`2026-09-05 02:58:56 +0900`** (KST; project-local 2026-09-04), twenty minutes after `c34305f` and confirmed server-side by `git ls-remote`, so the pin is fetchable and `ae43f80e6793` — the gitlink the *published* commit carries — is reachable from that branch as well. Registered and closed inside one entry, like `F14`. **The reusable half is process, not provenance**: `git add` in a shared checkout is not a private operation. `c34305f` carries a `linux` gitlink its subject line never mentions because the path was staged by one worker and swept up by another's commit; stage and commit in one step, or accept that the next commit may not be yours. **Extended to the tenant side 2026-09-04, and the tenant side is worse — the wording this ledger declined to guess at one pass ago, now that the sources it covers are committed.** `F19`'s row already noted the recurrence; `BENCH_SOURCE_PROVENANCE_2026-09-04.md` measures its extent. `cxl_join_bench.cpp` was **1,103 insertions and 29 deletions ahead of `HEAD`** at 2,974 lines (verified at `abccb31`), and `mmap_probe.cpp` — cited by a committed VOID outcome (`5f29346`) and a committed handback (`8da6499`) — was **untracked entirely**, so a committed record had been citing a source in no commit. **The aggravating finding is structural rather than procedural, and it explains most of `F13`'s scope in one fact: `HEAD` could not build its own gem5 tenant.** `join_range_flushbehind` calls `_mm_clflushopt` while the Makefile omitted `-mclflushopt` from the `gem5`, `gem5fs` and `w7` recipes; the `native` target survived only because `-march=native` happens to enable the feature on this host. **So no committed state of this repository has ever built the gem5 tenant, and every gem5 tenant binary this project has produced necessarily came from an uncommitted tree.** Fixed at `73da510`, verified here as adding the flag to four gem5 recipes and separated from the source commit because it is a defect in its own right rather than packaging. Of the **twelve** tenant binaries tabulated: **one** is byte-reproducible from the now-committed source minus a single reviewable hunk — `2b9d6732…`, the `H1BW_SINGLECORE` tenant, **reconstructible for the first time**, its source having previously existed in no commit at all — and that is a **recipe, not a checkout**, since no single commit in this history builds it. **Its reach is 9 records, not the 19 the record and the handback both claim**; verified here, the digest occurs in exactly 9 records of exactly one file, `h1bw_singlecore.jsonl`, which is the campaign's full cell count. `cac9e27a…` (**39** records across `H1BW_MULTICORE`/`H1BW_CXLBW`/`H1BW_SLICE_BRACKET`, confirmed) is **not** reproducible and its source state is lost. **r5's `401373ce…` is the weakest position of the three**: the bytes are gone, overwritten in place, and `bench_sha256` **was never populated in `r5_runs.jsonl`** — not null, the key is **absent from all 45 records**, verified here, so unlike `cac9e27a` it cannot even be hash-matched. **A counter-intuitive consequence that belongs in the ledger and not only in the provenance record: a reviewer who runs the committed source at r5's geometry and obtains r5's match count has made an error.** The committed source computes a **different** join — 261,864 against r5's 260,875 — because the corrupting call is *fixed* here; reproducing r5's number from this checkout would mean the fix is absent. **Still open on the tenant side:** `benchmarks/e2e/ivf_flat/src/ivf_flat_bench.cpp` (1,252 lines) remains **untracked** while committed files name it — `IVF_FLAT_SILICON_PREREG_2026-09-01.md`, `run_silicon_ivf.sh` and `run_ivf_list_dom.sh` cite it as a source, and **a fourth, `silicon_e2e/ivf_gates.py`, names it as a process**, so the count is four rather than the three claimed. A campaign running on host `c4` put it out of bounds and it is registered here rather than closed. **Prognosis upgraded 2026-09-04, and the distinction matters: `ivf_flat` will be the first tenant whose source lands while its binary is still reproducible from it.** `IVF_RECALL_REFERENCE_2026-09-04.md` reports a scratch build bit-identical to the live campaign binary, and that is **independently reproduced here** rather than accepted — `make BUILD=/tmp/ivfverify native` from the untracked source yields `b17ddd4c3ad166e2…`, byte-identical to `build/ivf_flat_bench`, with the live binary's digest confirmed unchanged before and after. **This does not close anything**: the source is still untracked, which *is* the defect, and a binary that happens to be rebuildable today from a file in no commit is exactly the state `F13` exists to name. What it does mean is that committing `ivf_flat_bench.cpp` will make the live campaign's binary **reproducible** rather than merely **readable** — the outcome r5's `401373ce…` and `cac9e27a…` (39 records) did not get, and better even than `2b9d6732…`, which needs a hunk reverted. So the tenant half of `F13` is on course to close in a strictly stronger state than any earlier tenant, provided the commit happens before the toolchain or the working copy moves. The `Makefile` also carries a mild form of the hazard the duckdb probe carries acutely: `BUILD := build` is a simple assignment, so a bare `make` writes over `build/ivf_flat_bench`, but unlike duckdb's hardcoded target it **is** overridable from the command line, which is how both this pass and the reference pass avoided touching it. **A third tenant-side provenance state is registered here 2026-09-04, and it is neither of the two this row already names — it is the *mirror* of them.** `run_silicon_e2e.sh`, the documented launcher of the registered 105-record silicon hash-join campaign, **could never have launched it**: `ROOT=$(cd "$(dirname "$0")/../../.." && pwd)` resolves **three** levels up from `experiments/asplos/`, i.e. to the parent of the checkout, so `$JOIN`, `$VIC` and the `exec`'d `run_hashjoin.py` path all pointed outside the tree and the script could not reach the runner at all. **Verified here as broken at birth, which is the strongest form:** `740bc69:6`, the commit that created the file, already carries `../../..`, so **no commit in this history has ever contained a working version of it** — the same shape as this row's finding that no committed state could build the gem5 tenant, arrived at independently on the launcher rather than the compiler. Its two siblings are correct (`run_silicon_ivf.sh:9`, `run_ivf_list_dom.sh:8`, both `../..`, read here), which is what makes it a typo rather than a design. Fixed at `f4eafdb`. **The provenance consequence, and it is a state this row has not previously had to name:** the 105 records reached `run_hashjoin.py` by some invocation that is *not* the committed launcher, so **a runner that is tracked but demonstrably was not on the path that produced the data is a distinct state from one that is untracked** — `F10`'s neighbour, not `F10`'s instance, because `F10` is a launcher that was never committed and this one was committed and never worked. It is the mirror of `F13`'s usual failure: `F13` is normally *untracked source that produced the artifact*, and this is *tracked apparatus that produced nothing*. Both defeat reproduction, from opposite directions, and the tracked case is the more deceptive because `git log` shows an apparatus and a reader has no reason to run it. **Recorded as a state within `F13` rather than as a new number, because the remedy is `F13`'s remedy applied to a different artifact class** — make the committed thing be the thing that ran — and not a new kind of remedy. **The uncomfortable half is that this ledger is the document that over-credited it, twice, and both citations are mine.** `F20`'s row says "`run_silicon_e2e.sh:7` runs the same `build/cxl_join_bench`, and its 105 records carry a constant `matches`", and the `F20` scoping passage says "`run_silicon_e2e.sh:7` runs the same native tenant and its 105 records show the same constant-across-arms `matches`". **Both are quoted rather than deleted, per `A6.19`, and the conclusions they support stand while the citations do not:** the tenant identity rests on `sha_join = sha256(args.join)` recorded 105 times, and the cross-arm invariance rests on the records, neither on the script. **And the detail worth keeping is where line 7 sits.** `:7` is `JOIN=${JOIN:-$ROOT/benchmarks/e2e/hash_join/build/cxl_join_bench}` — the line that *expands* `$ROOT` — so the defect was on line **6**, directly above the line this ledger cited as evidence, twice, and was read past both times. **A citation to a line is not a reading of that line's dependencies**, which is the same failure-to-apply shape that produced `A1.R1`. **Prognosis narrowed later the same day, and what needed narrowing was this row's own sentence rather than the reference's figure — quoted rather than deleted, per `A6.19`:** "`IVF_RECALL_REFERENCE_2026-09-04.md` reports a scratch build bit-identical to the live campaign binary", and "committing `ivf_flat_bench.cpp` will make the live campaign's binary **reproducible** rather than merely **readable**". Both say *the* campaign binary where the evidence reaches only *a* local one. `0d5872f` corrects the reference in its §11 and this row follows it. **Re-verified here rather than accepted — and only the local half is verifiable from this host, which is itself the finding.** `build/ivf_flat_bench` is still `b17ddd4c3ad166e2…` at **104 344 B** with `mtime 2026-09-02 16:20:47`, untouched by three passes of verification; this host is `mos181`, **Xeon Platinum 8592+** (Emerald Rapids), **`g++ (Ubuntu 15.2.0-16ubuntu1) 15.2.0`**; and `Makefile:2` carries `-march=native -mclflushopt`. **The `c4` half is attributed, not measured, and deliberately so** — `1b63e006…` at 100 832 B, `sha_ivf` in all 38 records, `g++ 11.4.0` on a Xeon Platinum 8462Y+ (Sapphire Rapids), all reported by the reviewer who read `c4`'s records. Those figures occur nowhere in this repository outside `IVF_RECALL_REFERENCE_2026-09-04.md` itself — grepped, and the campaign's records live on `c4`, which is out of bounds — so this row marks them **sourced rather than verified**, the same discipline it applied to r5's lost bytes. **What is checkable from here is the *shape* of the claim, and it holds on two independent points.** `run_ivf.py:456` computes `sha_ivf = sha256(args.ivf)` and `:174` stamps it into every record, so "in all 38 records" is a well-formed statement about a field that exists rather than one inferred from a build log. And the 37/1 split is **predicted, not merely plausible**: `qui` (`:244`) returns before the tenant is ever launched, so it is the one arm carrying no `id_sum`, and the rotation at `:468` — `order = arms[rep-1:] + arms[:rep-1]` over 21 arms and 5 reps — places `qui` at record 1 and not again until record 42, so **exactly one `None` in the first 38 records is what the committed launcher must produce**. Without that rotation the same 38 records would contain two, so a figure this row cannot measure is nonetheless entailed by code it can read. **Read the prognosis as:** committing the source makes **`mos181`'s** binary reproducible **on `mos181` with `g++ 15.2.0`**; it is not known to make `c4`'s binary reproducible on `c4`, and for a `-march=native` target byte-identity across that pair **is neither expected nor claimed** — see `A1.R1`, which exists because of this correction. **Not a second instance of `F13`, and the handed-over framing survives checking — the first framing of the four put to this ledger today that did.** *(i) The shape-of-the-remedy test, run for the first time to a negative answer.* `F13`'s remedy is *commit the source*; committing `ivf_flat_bench.cpp` would not have prevented this error by one byte, because the two binaries would still differ and "bit-identical to the live binary" would still have been false. A remedy that leaves the error entirely in place is evidence the error is not of that class — and it matters that the test *can* answer no, since the same test split `F19` from `F18` and `F21` from `F20` earlier today, and a test that only ever divides is not a test. *(ii) The subject differs.* `F13` names source state that **no commit captured**; this is source state that **two coordinates capture**. The divergence is not lost but *determined* — same source, named host, named compiler, same bytes, on demand. Host-relativity is provenance with one more coordinate, and the coordinate is knowable and now written down. `F13` exists for binaries whose originating tree cannot be named at all, which is r5's `401373ce…` and `cac9e27a…`'s 39 records, not this. *(iii) The locus differs, and this is decisive: nothing was done to an artifact.* `F13` is a defect in artifact *management* — a file was overwritten, a tree went uncommitted. Here the repository, both hosts and all three binaries stood in exactly the same state after the erroneous sentence as before it; what was defective was a **claim**. A class about lost artifacts cannot absorb a defect about an over-broad noun phrase without expanding to cover everything, and the remedy for a wrong sentence is a rule about sentences — which is why this pass yields `A1.R1` and not `F22`. **One consequence for `F13` that is worse than an extra instance would have been, because it is permanent.** `ivf_flat/Makefile` has **no** gem5 target — verified here, its only targets are `all`, `native`, `test` and `clean` — so every `ivf_flat_bench` that can exist is built `-march=native` and is host-specific by construction. The tenant half of `F13` therefore **cannot** close in the strong form the superseded wording implied, not for this tenant and not for any host tenant ever: the best attainable state is "reproducible on a named host+toolchain pair". That is a **ceiling on the class**, not an instance of it. **And the ceiling contains an inversion that reorganizes the tenant story.** Verified here across `hash_join/Makefile`: **six** recipes carry no `-march=native` — `h3-dirty-owner` (`:34`), `h3-dirty-owner-fs` (`:40`), `gem5` (`:44`), `gem5-window` (`:59`), `w7`'s gem5 half (`:76`) and `gem5fs` (`:89`) — every one of them `-static` and gem5-guest-bound. So the binaries for which **cross-host byte-reproducibility is actually attainable are exactly the gem5 guest binaries**, and those are precisely the ones this row found *least* reproducible, their source having been lost. The two halves are complementary rather than parallel: `2b9d6732…` sits where reproducibility was attainable and the source was missing, `ivf_flat_bench` sits where the source is present and reproducibility is host-bounded. **No tenant in this project has ever occupied both good positions at once**, and `ivf_flat` will not be the first — it will be the first in the second one. **Offsetting all of the above, and this is the larger fact of the correction: the *correctness* anchor moved the other way.** Per the reviewer's reading of `c4`, `id_sum = 147039988` in all 37 search records and `recall_at_k = 0.5082999999999956` in the same 37 — so a NumPy reimplementation (reproduced independently by this ledger one pass ago) and **two independently built binaries, across two microarchitectures and two compilers**, agree on one exact 64-bit integer summed over 10 000 returned ids, meaning every top-10 set was identical in all three. The float32 accumulation order genuinely differs between those builds, so the reference's margin argument was tested across instruction selection rather than assumed. **This retires the one real objection to the `F20` fix recorded below** — pinning an exact integer is safe against toolchain drift precisely because the integer has now survived a toolchain change. **Still pending and deliberately not run:** whether `1b63e006…` rebuilds byte-identically on `c4`, which would require compiling on the host and polluting the shared LLC the victim samples are measured through, with under five hours of campaign left. The hazard in that future check is this row's own subject — `BUILD := build` means a bare `make` on `c4` would overwrite the campaign's binary in place, the `F13` failure mode exactly, so it must run as `make BUILD=<scratch>`; the reviewer reports having `chmod a-w`'d `c4`'s copy against precisely that | 09-04 | **closed** 2026-09-04 on the simulator, subject and remaining ground both; **reopened on the tenant side** 2026-09-04, open on `ivf_flat`, **prognosis narrowed to host+toolchain scope 2026-09-04** |
| F16 | **For ten of the fourteen campaign pre-registrations, "this was pre-registered" is corroborated by nothing outside the document's own dated self-attestation, and for an eleventh it cannot be settled either way.** *(This row read **nine** until a birth-time re-audit later on 2026-09-04. The superseded headline is quoted rather than deleted, per `A6.19` — "**For nine of the fourteen campaign pre-registrations, 'this was pre-registered' is corroborated by nothing outside the document's own dated self-attestation.**" — and the two reclassifications that moved it, both verified here against the repository rather than accepted from the handback, are set out where the witness list used to be. The row's **verdict does not move and is better founded than when written**; see the birth-time paragraph at the end of this cell.)* All fourteen are now committed, and every citation in "Status history"'s freeze list verifies — but **commit order proves less than the commit dates suggest**, because the registration commits all landed in one 2026-09-04 pass (author timestamps read `2026-09-05 01:32–01:37`, this host's clock being **KST**, UTC+9, against the project-local UTC-7 by which records in this directory are dated — the convention `BUILD_PROVENANCE.md` states in its own dating note, and every wall-clock instant quoted in this row is labelled KST for the same reason), after the campaigns they register had run. Verified here today, campaign by campaign: **eight** registrations were committed **in the same commit as their own outcome document** (`SILICON_E2E_PREREGISTRATION` + `SILICON_E2E_OUTCOME` at `74e37b2`; `COMPLETE_JOIN_PREREG` + `COMPLETE_JOIN_OUTCOME` at `61c8a8e`; `H2H_REALJOIN_PREREG` at `61c8a8e`, whose verdict lives in two sections **of the registration itself**; `DUCKDB_TENANT_CAT_PREREG` at `cda8602`; `DUCKDB_MMAP_PROBE_PREREG` at `bff2622`; `IVF_LIST_DOM_PREREG` at `a1bfbfa`; `H1BW_MULTICORE_PREREG` at `a4b0c5e`; `H1BW_CXLBW_PREREG` at `b21cd21`), and in every one of those eight the campaign's **raw data was already committed in an earlier commit of the same pass** (`fee8417`, `ea28693`, `c271a22`, `931b248`, `7cd63f3`, `84dfd65`), so git witnesses the data preceding the registration rather than the reverse. A **ninth**, `FS_COMPLETE_JOIN_PREREG` at `fa30418`, is committed ahead of an outcome document that is still untracked, but behind r6b–r6e data that already existed on disk. **Filesystem mtimes cannot substitute, and there is a proof rather than an argument:** `COMPLETE_JOIN_OUTCOME_2026-09-01.md` is stamped `05:32:53` while its own `COMPLETE_JOIN_PREREG_2026-09-01.md` is stamped `05:32:58` — the outcome's mtime is **five seconds earlier** than the registration it followed, which is what a last-write timestamp records rather than a creation order. **Three of the fourteen hold an external witness, one is indeterminate, and the figure this row first published was five.** The superseded sentence is quoted rather than deleted, per `A6.19`: "**Five of the fourteen do hold an external witness**, and it is worth naming which: `DUCKDB_MMAP_SE_H2_PREREG` (`bff2622`), `AGGBW_WINDOW_PREREG` (`443b637`), `FB_ORACLE_PREREG` (`e2b1b90`) and `IVF_FLAT_SILICON_PREREG` (`a1bfbfa`) are committed and their campaigns have produced **no committed data and no outcome at all**, so git will witness precedence for them from here forward; and `H1BW_SLICE_BRACKET_PREREG` (`e35cfa3`) was deliberately committed **ahead of its outcome** — though its run data was already committed at `84dfd65`, so what git witnesses there is the registration preceding the *outcome document*, not the runs. One orphan qualifies that: `/tmp/fbo_validate` holds an `fbo`/`wb` run pair from 2026-09-03 13:06–13:21, referenced by no document, script or record in this repository, and named as an arm by no registration." **The surviving three are `DUCKDB_MMAP_SE_H2_PREREG`, `AGGBW_WINDOW_PREREG` and `IVF_FLAT_SILICON_PREREG`**, and the reason they survive is worth stating explicitly rather than left as a residue, because the error class that moved the other two **cannot reach them**: their witness is *absence of any data at all* plus a committed registration, which is a **forward-looking guarantee that never consults a timestamp**. There is no mtime, birth time or in-band stamp in their argument to have read wrongly, and nothing measured after the commit can precede it. That is the strongest form the property takes in a bulk pass, and it is also the emptiest — it licenses nothing about a campaign that has not run. **Two reclassifications, both verified here against the repository:** (1) `H1BW_SLICE_BRACKET_PREREG` was **miscounted as witnessed and is unwitnessed**. Its committed data carries an in-band `started`, and `data/gem5/h1bw_slice_bracket.jsonl`'s three cells read `2026-09-04T09:11:27+09:00` to `09:11:31`, against a registration commit `e35cfa3` at `2026-09-05 01:37:06` KST — the runs began **16 h 25 m 39 s before the registration was in git**, and the post-fix triple (`_20260904fix`, `12:52:44`) began 12 h 44 m before it. The cell had already conceded the substance ("what git witnesses there is the registration preceding the *outcome document*, not the runs"); what changes is that the concession is now measured rather than inferred, and the count is taken on one criterion — precedence over **run start** — instead of two. (2) `FB_ORACLE_PREREG` moves to **indeterminate**, and this row's own supporting claim about it was **false**. The orphan pair is not unregistered: `FB_ORACLE_PREREG_2026-09-03.md` §"Arms" registers exactly "`qui` / `wb` / `h2` / `fbo`, three seeds each, 12 runs", so `fbo` **is** a registered arm, and the `fbo`/`wb` pair in `/tmp/fbo_validate` is that registration's own **`P-O1`** check — "`fbo` must show a materially lower HNF occupancy/insertion count than `wb`", the first thing its own text says to check. In-band banners put it at `Sep 3 2026 13:06:48` (`wb`) and `13:21:50` (`fbo`), matching both directories' birth times to the millisecond and predating `e2b1b90` by **1 d 12 h 25 m 56 s**. So the witness cannot rest on absence of data, because data exists. It is **indeterminate rather than unwitnessed for a reason that runs the other way**, and the reason is recorded because it is the more interesting half: the pair is **one run per arm at the wrong geometry** — `--fact-bytes 2097152 --hot-bytes 1048576 --reps 2` against the registered `8388608`/`4194304`/`reps 1`, no victim process at all, and a different build directory (`build_Intel_8592_FBO`) — so it is a plumbing check and not a campaign cell; and the registration document's own **birth time is `2026-09-03 09:16:46`, 3 h 50 m 2 s *before* the earlier of the two runs**, which corroborates its attestation at exactly the point where git cannot. Neither reading is provable from a clone. Both are recorded. **This is a limit on external verifiability and not a defect in the claims, and the ledger says so deliberately** — the reasoning is in "Status history" below. **What is recoverable is recorded rather than assumed:** four of the fourteen are **not sealed originals**, and their amendment counts verify — `SILICON_E2E_PREREGISTRATION` 1 amendment, `COMPLETE_JOIN_PREREG` 1 addendum, `H2H_REALJOIN_PREREG` 5 (four addenda plus "Amendment 1, three corrections made AFTER data existed", which the document itself labels as such), `FS_COMPLETE_JOIN_PREREG` 7. The remaining ten carry no addendum at all. From `065fd80` forward **git witnesses every further change to all fourteen**, sealed or not, which is the half of the property that is now secured even though the originating half cannot be. **No number moves**, here or in the paper. **The birth-time re-audit that cost this row two witnesses also strengthened its verdict, and that belongs in the row rather than in a footnote.** The mtime pair this cell offers as its inversion proof inverts only in *mtime*: the birth times run the right way round, `COMPLETE_JOIN_PREREG_2026-09-01.md` born `2026-09-01 23:48:22.666` and `COMPLETE_JOIN_OUTCOME_2026-09-01.md` born `2026-09-02 05:02:16.092`, five hours and fourteen minutes apart in the order the documents assert — while their mtimes read `05:32:58` and `05:32:53`, five seconds the wrong way. And that registration's birth **precedes its own campaign's in-band launch by 4 min 21 s**: r5's first wave of fifteen arms reports `gem5 started Sep 1 2026 23:52:44` in fifteen separate logs. The pattern holds for every bulk-pass registration where an in-band launch time exists to check it against, measured here: `H1BW_SINGLECORE` **28.9 s**, `H1BW_SLICE_BRACKET` **35 s**, `H1BW_MULTICORE` **40 s**, `H1BW_CXLBW` **1 m 29 s**, `COMPLETE_JOIN` **4 m 21 s**, `DUCKDB_TENANT_CAT` **12 m 54 s** and `SILICON_E2E` **41 m 08 s** — in every case the document was **on disk before the campaign started**. So the filesystem **corroborates these attestations rather than contradicting them**; what it cannot do is show a reviewer, because git records no mtime, no ctime and no birth time and none of it survives a clone. That is precisely what "a limit on external verifiability, not a defect in the claims" was asserting when this row was written, and it is now founded on a measurement instead of on an argument. **Read the two facts together and not separately**: the same instrument that removed two witnesses from the count corroborated ten attestations, and neither result is available to anybody who has only the repository. **Paper exposure is one passage, not eight** — the eight registration-claiming passages were read and seven of them are git-witnessed; see "Status history". **One of those seven is now witnessed on a narrower ordering than the one first claimed for it**, and the exposure count survives that: `Appendix.tex:403` rests on `H1BW_SINGLECORE_PREREG`, whose registration commit is **21 m 46 s after its runs launched** and **25 m 45 s before the earliest of them reported** — so what git witnesses is the thresholds being fixed before any result existed, which is the ordering the word "pre-registered" needs there, and not the thresholds being fixed before the runs began, which the bullet in "Status history" originally claimed from a directory mtime. Corrected there, not rewritten | 09-04 | **open as a verifiability limit** 2026-09-04 |
| F17 | **A fail-closed gate whose instrument cannot observe the quantity at one of the levels its own campaign sweeps, or whose sample is taken at a point in the run schedule that differs by arm.** Registered here 2026-09-04 from `AMD_XSOCKET_OUTCOME_2026-09-04.md` §10, which proposed it and left the number to this table. Two instances, both in `AMD_XSOCKET_PREREG_2026-09-04.md`, both caught **by the gate failing** rather than by review, and both leaving that campaign **NOT CERTIFIED** (10 of 12 gates pass). (1) `G4` required ≥99% of the victim's pages on node 0 and read a histogram that filters mappings below 1024 pages; the campaign sweeps a **512 KB (384-page)** victim, which is invisible to it, so 200 of 400 runs scored 0% while the 4096 KB cells passed at 100%. The ≥99% threshold was **also** wrong for an unfiltered view, which fails even the primary cell at 87.2%, because ~457 pages of `libc`/`ld.so`/`libnuma` text are page-cache-resident on the other socket. (2) `G6b` required per-arm core-0 frequency to match the quiescent arm within 10% and sampled it **before the victim started** --- which in a co-run arm follows a 2-second settle sleep that lets core 0 drop to its 1.5 GHz minimum, and in a quiescent arm does not. It measured its own sampling schedule and split 3.1 GHz against 1.5 GHz with perfect correlation to placement. **Same root cause as two prior instances, which is why it is registered as a class rather than as two mistakes**: `BERGAMO_BACKINVAL_PREREG`'s `P1` was recorded as mis-specified for calibrating a threshold in one configuration and applying it in another, and `AMD_L3OCC_PREREG` opens by naming the recurring cause in as many words --- *"the instrument does not measure the quantity in the claim."* Distinct from **`F12`** (a criterion a crashed run could satisfy): `F12` is a gate too weak to fail, this is a gate that fails for a reason unrelated to what it tests. **Both questions were answered by fresh post-hoc diagnostics** (`broker/amd_xsocket_gatecheck.py`, `d23_gatecheck.jsonl`, n=5 per cell, disclosed as post-hoc) and both came back clean --- the 512 KB working set **is** on node 0, the size-invariant 457-page node-1 residue being `libc`/`ld.so` text shared with ~100 processes and identical in all five arms, and core 0 runs at **3.100 GHz in every one of 20 samples, in every arm, at both sizes** during the measured window --- so **no measurement is impeached and no number moves.** What is impeached is the certification. **The behaviour this row exists to reward is the diagnosis, not the failure**: the two gates were recorded as mis-specified rather than converted to passes, and the campaign's headline was held to the same standard --- Outcome A failed on the **lower (faster-than-baseline) edge by 2.8x10⁻⁴** under a two-sided rule the worker had frozen and did not loosen, and the primary cell was not relocated to the secondary 4096 KB cell that returns A cleanly. That is the same pattern that makes `F16`'s pre-registrations credible: a registration that goes on to fail its own thresholds and reports it. **Prevention worth registering**: a gate should be dry-run against every level of its campaign's own sweep before the campaign is frozen, and any gate reading a point-in-time sample must state where in the run schedule the sample is taken. **A third convention is registered alongside those two, from a different pass and the same category — fix the harness, not the record.** Every committed per-run record should carry an in-band `started` and `ended`, as the `h1bw_*` harness already does. Measured 2026-09-04: only **9 of the 30** committed `.jsonl` files under `data/` carry any in-band timestamp at all, in **two schemas** — ISO-8601 `started`/`ended` per record in the five `h1bw_*` files, and a single `ts` per record in `duckdb_tenant_cat.jsonl` and the three `silicon_e2e_*` files — and the remaining 21 carry none, `r5_runs.jsonl` and the two fused archives among them. The whole birth-time re-audit recorded at the end of this document, which cost two of `F16`'s witnesses and corrected four passages including two of this ledger's own, would have been a two-command check against those fields; instead it was done against tmpfs metadata that no clone can see and that means *launch* on one harness and *completion* on another. This is registered as a convention rather than as a defect number for the same reason as the two above: nothing measured is wrong, and the remedy is what the next harness does. Logged **open**; the remedy is a convention, not a patch, and the affected campaign is closed | 09-04 | **open** |
| F18 | **A simulator that quantizes a configured quantity and reports the unquantized one, with no output naming the difference; and records that then quote the requested figure as though it were realized.** Registered here 2026-09-04 from `NONPOW2_SETS_MEASURED_2026-09-04.md`, which proposed it and left the number to this table, as `AMD_XSOCKET_OUTCOME` did for `F17` and `BUILD_PROVENANCE.md` for `F13`. **Deliberately *not* a re-registration of the arithmetic.** The arithmetic is `[F9.4]` in `W4.3_PROVENANCE_LEDGER_2026-08-23.md` --- `CacheMemory::init()` computes `m_cache_num_sets = (size/assoc)/block`, takes `floorLog2` of it for the index width, and allocates the surplus sets without ever indexing them --- and it has been on record since 2026-08-23, with its LLC form worked out in `W7.2_A1_SIZING_2026-08-24.md`. **Note the numbering, because it crosses ledgers**: `F9.4` belongs to that document's series and appears nowhere in this table (checked: this ledger contains no `F9` at all), so a reader meeting both should not look for `F9.4` here. `F9.4` is a defect in a **computation**; `F18` is a defect in **observability plus record-keeping**, and it is why `F9.4` survived four separate enumerations of its own affected list and still reached a published ratio. Three components with three dispositions. **(1) The simulator was silent --- *repaired*.** At `--l3_size=7680KiB --l3_assoc=20`, `init()` allocated **6,144** sets, indexed **4,096**, and emitted no warning, no assertion and no stat, while `config.ini` faithfully recorded the *requested* `size=7864320`; every instrument the harness had reported the number that was wrong. Realized capacity is **5,242,880 B, 66.7% of configured**, verified here by arithmetic and by measurement. The repair is a `warn()` in `CacheMemory::init()` naming the realized capacity, at gem5 `c030d776ee` (read here, verbatim as the record quotes it). **`warn()` rather than `fatal_if`, and the reason is sound rather than convenient**: four committed launchers request affected geometries, and a fatal would break them at exactly the moment their realized geometry needs confirming --- the measurement below could not have been taken under one. **Proved inert, to the standard `BUILD_PROVENANCE.md` set for the `isStreaming` re-run**: all four probe cells were re-run pre- and post-guard and each differs on **5 lines out of 2,019 / 2,019 / 2,021 / 2,016**, all five being `hostSeconds`, `hostTickRate`, `hostMemory`, `hostInstRate` and `hostOpRate` --- re-derived here rather than accepted, including for **cell B, the cell that fires**. Pre-guard bytes preserved on disk as `gem5/build_Intel_8592/gem5.opt.pre-npot-guard.cb290444`, digest `cb2904444d…`; post-guard `d4e798601e…`; both `sha256sum`'d here and both matching. **The guard's second effect is worth more than the guard**: a run's console log now records reachable capacity, which is exactly the quantity `F9.4`'s own r5 wording cites as missing (*"no run emits a set count"*). **(2) A fail-closed gate read the wrong side --- *open*.** r5's `G0` was a requested-versus-realized gate that read a *requested* value on both sides: it required `l3_size_bytes == 7864320` and a `table/LLC` band computed against that same number, both sourced from `config.ini`'s `size=` field. **Same family as `F17`** --- an instrument that cannot observe the quantity in its own claim --- and it stays **open** because no artifact yet carries realized capacity for a *completed* run: the guard supplies it from that build forward only, so every campaign already on record is unauditable on this quantity except by re-derivation. Prevention is the same shape as `F17`'s: a gate must name the artifact carrying the **realized** quantity, and where none exists the gate is not yet implementable and should say so instead of passing. **(3) The records propagated it --- *corrected by addendum*.** `COMPLETE_JOIN_OUTCOME_2026-09-01.md` is wrong in **six** places including its own title, and `COMPLETE_JOIN_PREREG_2026-09-01.md` line 28 is the origin (`4/7.5 = 0.5333… = 32/60`); both now carry an Addendum 2 dated 2026-09-04 with the superseded wording quoted in place, per `A6.19`, and both were checked here as landed. **`F9.4`'s r5 cell is closed by measurement, and that is the substantive upgrade**: it stood as *"derived from source, not measured"*, and it is now measured. `--l3_size=7680KiB --l3_assoc=20` is **bit-identical to `--l3_size=5MiB --l3_assoc=20` on all 2,014 simulated quantities** --- 5 differing lines out of 2,019, all five host-side, confirmed here --- while `--l3_size=7680KiB --l3_assoc=15`, the *same requested bytes* at a power-of-two set count, differs from it on **914 lines (956 distinct stats)**. That control is what makes it an experiment rather than a demonstration, and its figure is corrected: the record reports it as 1,825, which is both sides of the same `diff` and is not the convention its neighbouring rows use; see the close-out below. **No published magnitude moves, and the reason is structural rather than lucky**: all **45** r5 runs share one realized geometry --- `l3_size_bytes = 7864320` in all 45 committed records, all `completed`, 15 arms, verified here --- and a ratio common to every arm cannot distort a comparison between arms, so `fig:frontier`(a) is **internally valid** and `P5`, the **+9.97%** wedge, the **+8.42%** matched-R wedge, `R(h2) = 22.59%` and the **1.185×** WB tax all stand as measured. Nothing is recomputed. **What is void is a claim and an argument, not a number.** r5 existed to move `table/LLC` from r3's 0.800 to silicon's 0.533; realized, it is **0.800**, and realized `victim/LLC` is **0.518** --- *both identical to r3's*, because 5 MiB against the same 4 MiB table and 2650 KiB victim is r3's geometry exactly (4,194,304/5,242,880 and 2,713,600/5,242,880, re-derived here). So r5 is **r3's cache geometry, not r3 with one knob fixed**, and Addendum 1's explanation of r5's fallen victim tax *by* a shrunken `victim/LLC` explains an effect with a cause that never occurred. **The supersession of r3 by r5 survives on the workload and not on the geometry** --- a complete join reporting tuples/s against a truncated join reporting IPC --- and that distinction is the part a reader would otherwise get wrong. **Blast radius audited rather than assumed, and one reasonable suspicion refuted.** `audit_nonpow2_sets.py` re-run here over every `config.ini` under `gem5/logs/` finds **one** affected distinct geometry and every L1I, L1D, L2, snoop filter and directory structure clean at every slice count; only r5 among campaigns with committed data. **`H1BW_SLICE_BRACKET` is clean**, and the suspicion against it was reasonable, since dividing a fixed total across a varying slice count is precisely how this defect arises unseen --- but it pins `L3_PER_SLICE=5MiB` and varies the slice count instead, so each slice is independently 4,096 sets and the *aggregate* varies. **`FB_ORACLE_PREREG_2026-09-03.md` is amended before it can run**, at zero cost to its `P-O2` reproduction check since the two flags name one machine, and its Amendment 1 was checked here as landed. `DUCKDB_MMAP_SE_H2` was affected and is **VOID with no arm run**. **Paper exposure: none, and the paper is the only artifact in this chain that stated realized values.** `Sec7:42-44`'s 1--3 pp CAT claim traces to `MODEL_SILICON_CAT_CALIBRATION_2026-09-01.md`, whose gem5 input is `rj3_runs.jsonl` --- **r3**, not r5 --- and it normalizes by CAT **way** fraction rather than bytes, which set-count quantization cannot touch; `0.533`, `7680`, `7864320`, `7.5 MiB` and `table/LLC` appear in no `.tex`. Logged **closed on repair** for component (1), **corrected** for (3), and **open** for (2) | 09-04 | **open** on the gate half |
| F19 | **An inline-asm statement that under-declares what the instruction writes.** Registered here 2026-09-04 from `M5OP_RAX_CLOBBER_AUDIT_2026-09-04.md` §8, which proposed it and left the number to this table. gem5 decodes the magic instruction as `BasicOperate::gem5Op` and its body ends `Rax = result;` **unconditionally** (`arch/x86/isa/decoder/two_byte_opcodes.isa:163`, read here), while `pseudo_inst.hh:140` sets `result = 0` before dispatch, so **every void m5op zeroes `%rax`**. This tree's wrappers declared only `"memory"`, which tells the compiler `%rax` survives. Realized in `mmap_probe.gem5`: the optimiser had scheduled the store of `mmap`'s return value into a global *after* an intervening `bind_pool` m5op, so the global took 0, `SET_STREAMING` was called with `addr=0`, and gem5's own trace records `setstreaming: addr=0 size=0x10000 -> 16/16 pages marked` — **16 pages of the tenant's own PIE image instead of the probe, and the probe never marked at all** (`DUCKDB_MMAP_SE_H2_HANDBACK_2026-09-04.md` §6). **Registered as a class, and the case for that is the second property below rather than the defect's severity.** *(i) It is silent in both directions.* The corrupted call still *succeeded*; the fill still worked, from a surviving `%rbp` copy, so nothing failed earlier and the tenant's own null check never fired. *(ii) **It is compiler-schedule dependent, and this is what makes it a class and not an `F18` instance.*** Identical source is safe in one binary and wrong in the next depending on optimization level and surrounding code, so **source review cannot settle it and only disassembly of the binary that actually ran can**. That is a different epistemic situation from every defect above it: `F18` was settled for every campaign from `config.ini` and arithmetic, with no binary required — this ledger closed `F9.4`'s r5 cell that way one pass ago — whereas here a lost binary makes the question permanently unanswerable. *(iii) It would have been misdiagnosed.* `P1` (`DUCKDB_MMAP_SE_H2_PREREG_2026-09-02.md:86`, `streamingHnfFillBypasses > 0` on `h2`) could never have passed, and the natural reading would have been "the m5op did not reach the HNF" — true, and completely misleading about why. *(iv) **It compounds `F13`.*** Three campaigns' *tenant* binaries no longer exist, so for those the class can only ever be argued and never disassembled; `F13` was until now a simulator-side defect and this is its tenant-side recurrence. **Distinct from `F18`** on (ii) and on the shape of the remedy: `F18`'s prevention is to *emit* the realized quantity, an observability fix, whereas `F19`'s is to *declare* the clobber, a contract fix that makes the question schedule-independent and therefore removes the need to observe it at all. **`fused.c` is the proof that the two are different**: it is clean *by construction*, a status no amount of output could confer and one `F18` has no analogue of. **Distinct from `F9`** — nothing here is recorded as configuration. **Audited across seven campaigns and no declared range was mismarked; no published claim is in doubt.** Re-verified here by re-running the committed instrument `audit_m5op_rax.py` rather than reading its output: `COMPLETE_JOIN`/r5 **CLEAN** on in-band evidence from the binary that ran (§below), `FUSED_KNEE` **CLEAN by construction**, `H1BW_SINGLECORE` **CLEAN** on hash-matched `2b9d6732`, `H1BW_MULTICORE`/`H1BW_CXLBW`/`H1BW_SLICE_BRACKET` **CLEAN** on hash-matched `cac9e27a`, `FS_COMPLETE_JOIN` r6b–r6e **CLEAN** on binaries extracted from their disk images, and **`H2H_REALJOIN`/r3 CLEAN on counters but INDETERMINATE on disassembly** — see the close-out for why that distinction is preserved rather than rounded up. **One genuine defect was found, in a path nothing runs, and its failure mode is safe**: in `join_range_flushbehind` (`--policy fbo`) `%rax` is the **loop induction variable** compared against a bound in `%rbp`, so the m5op zeroes it every iteration and the loop cannot terminate. Reproduced here in all three binaries that contain it (`cxl_join_bench.gem5` `0x40ced1`, `.gem5wbrk` `0x40cf11`, `.gem5fs` `0x40d7b1`, each reading `%rax` twelve bytes later). **Any cell taking that branch would have hung rather than produced a wrong number**, so no campaign can have used it silently — which is *stronger* than `BUILD_PROVENANCE.md`'s standing note that the opcode is compiled in but inert. **Fixed** by declaring `%rax` as an output operand — a register cannot be both an input constraint and a clobber — in 31 wrappers across 14 files, 19 committed and 12 applied but handed back because they are other workers' in-flight paths. **Prevention, in three parts.** A declared clobber is schedule-independent and is therefore the only durable fix. A runner that hashes the **tenant** binary, as `run_complete_join.sh` does at its lines 78–80 and `run_fused_knee.sh` does not at all, is the difference between "the binary is lost" and "we cannot even say what was lost". And **a third belongs beside `F17`'s and `F18`(2)'s, being the same pattern one level down — in the audit tool rather than in the experiment**: `0f 04` is an invalid opcode, so `objdump` desynchronizes past it and an enumerator driven off its output misses any second m5op emitted inside the first's desync shadow. This was not hypothetical — it hid two real sites in `cxl_join_bench.gem5wbrk`, and re-running the corrected instrument here finds them at `0x411b57` and `0x411b86`, each immediately following a `dump_stats` at `0x411b53` and `0x411b82`. `audit_m5op_rax.py` enumerates by raw byte scan of the PROGBITS sections instead. **An instrument that cannot observe the quantity in its own claim is now recorded three times in this table at three different levels: a campaign gate (`F17`), a simulator output (`F18`), and an audit tool (here).** Logged **closed on repair** for the executed paths and the one broken path, and **open** on r3's indeterminacy and on the twelve uncommitted wrapper fixes | 09-04 | **open** on r3 and on the handed-back fixes |
| F20 | **A correctness gate whose reference is derived from the same input it is meant to validate — a self-consistency check reported as a correctness result.** Registered here 2026-09-04 from `BENCH_SOURCE_PROVENANCE_2026-09-04.md`, whose §9 proposed its finding as an extension of `F13` and left the class question to this table; the provenance half *is* an `F13` extension and is recorded there, but the gate is not, for the reasons below. **Realized in the headline campaign, and this is measured rather than inferred.** At the pre-series `HEAD` (`58b7558`) `run_single` calls `fill_fact()` at `cxl_join_bench.cpp:1162` and `prefault_region(fact, c.fact_bytes)` at **`:1163`**, immediately after, and `prefault_region` **mutates**: `q[off] = q[off] + 1` on the first byte of every 4096 B page and again on the last byte of the object (`:413–419`, read here). r5 ran `--mode single` (`run_complete_join.sh:37–38`, both arms), so an 8 MiB fact is **2,048 pages and 524,288 tuples of 16 B** and **2,048 fact keys — 0.390625%, the record's 0.391% — were corrupted in every r5 cell**. The corruption leaves an in-band fingerprint in the reported match count, and three source states rebuilt at r5's exact geometry separate them: `HEAD` → **260,875**, the m5op audit's independent r5-era reconstruction → **260,875**, the fixed source → **261,864**. **Verified here from committed data rather than from the record's cited source**: `join_matches` is **260,875 in 42 of the 45 records of `r5_runs.jsonl`** (the three nulls are the `qui` cells, which run no join), so the finding rests on a committed artifact and **not** on the `/tmp/r5` launch logs that `BENCH_SOURCE_PROVENANCE`'s §8 lists as newly load-bearing for it — a correction in the record's favour. **Why the gate could not fire, from the source rather than by argument.** `bool ok = !c.check \|\| (out.matches == ref.matches * reps && …)` (`:1193`), where `ref` is `join_range` over **the same `fact` object** the measured path reads; the file says as much at `:677` — the batched finish loop *"reproduces probe() exactly … so `matches` and `sum` are equal to join_range's for every input. --check compares them; that equality is the correctness gate."* Agreement between two implementations of one probe over one corrupted array is **invariant to the corruption**, so `correct` is `true` in the corrupted rows and the clean one alike. **Registered as a class rather than folded into `F17`, `F18`(2) or `F19`'s prevention note, and the case is the first property below, not the severity.** *(i) **It is not under-instrumentation, and that is the discriminator.*** Every earlier member of the family is an instrument that failed to **see** a quantity, and in every case the remedy is to observe better — `F18`'s is to *emit* realized capacity, `F19`'s note is to *enumerate* by byte scan rather than off `objdump`, `F17`'s is to name the artifact carrying the quantity. This gate observes its quantity perfectly and **still cannot fail**, because it is a *tautology*: its reference is a function of the same input as its subject. No output and no better instrument repairs it; the remedy is different in kind — a reference computed from something **other** than the object under test, or a check of the input against its generator. That is the same test by which `F19` was held distinct from `F18`, applied to the shape of the remedy, and it separates this cleanly from all three. *(ii) It is a **correctness** gate, which makes it the sharpest member rather than merely another one.* `F17`'s and `F18`(2)'s failures cost a certification; everything downstream of a correctness gate is *licensed* by it, and `correct: true` in all 42 r5 cells is the reason a corrupted join went unremarked for the entire life of the campaign behind `fig:frontier`(a). *(iii) Two instances, in different files from different passes* — the standard `F17` used to register a class rather than two mistakes *(**now four**, per the silicon close-out below: `gates.py:166–175`'s `live_check` seeds its reference from the first `wb` **arm**, and `ivf_gates.py:82–89` does the same on `ref_id_sum`. **And a fifth, `recall_at_k` itself**, confirmed 2026-09-04: it grades the approximate search against `exact_query(lists, …)` over **the same `lists` mapping** the approximate path scans (`ivf_flat_bench.cpp:975–980`, `:652–666`), so a corrupted mapping corrupts both sides equally. **The family is now sub-divided by *why* a gate cannot fail** — `F20` because its reference does not move, `F21` because nothing bounds a reference that does; see `F21`.)*. The tenant's `--check` gate is one; the FS analyzer's *"the join must be the same computation in every contended arm at a seed"*, which compares `matches` between `wb` and `h2` (`w8/fs_join_analyze.py`, read here), is the second, and is likewise invariant to any defect common to both arms. *(iv) Distinct from `F16`*, which is the absence of a witness. This is a **present, passing, load-bearing** gate, which is worse in kind: an absence advertises itself and a green tautology does not. **No published magnitude moves, and the reason is structural rather than lucky.** The mutation is a deterministic function of the fact region's size and page layout, both identical across every r5 arm at a seed — all 42 join cells report the same 260,875, confirmed here — and every r5 figure the paper cites is a **ratio** against unprotected write-back: **+5.35%** tenant throughput, **+9.97%**, **8.42%**, and both `fig:frontier`(a) axes. A defect common to every arm cannot distort a comparison between arms, which is the same argument `F18` gave for r5's realized L3 geometry and holds here for the same reason. **`Sec7:28-29` is a cross-arm invariance claim and that is exactly what survives.** Read verbatim here: *"All arms preserve the workload's input, completed work, and result hash."* It would be **false** read as a claim of absolute correctness and **it does not make one**; the distinction is load-bearing and must not be smoothed into "the paper is fine". Even the workload description holds to two figures — realized hit rate **49.76%** corrupted against **49.95%** clean, versus a nominal 0.5 (verified: 260,875/524,288 and 261,864/524,288). **What must be said plainly, and both halves of it: the claims stand, and r5's tenant was not computing the join it reported.** 0.391% of its probes missed for a reason with nothing to do with the workload. **One figure in this chain does not survive and is not applied:** the record scores the 989-match loss (verified, 261,864 − 260,875) against *"~1,024 expected at `hit_rate 0.5` and a Bernoulli σ of ~362"*. 989 and 1,024 are right, but **362 is the σ of the *total* match count** (√(524,288·0.25)); the σ of the 2,048-key loss is **22.6**, so the deviation is **1.55σ**, not the ~0.1σ the pairing implies. The agreement is comfortable on the correct scale; the stated comparison flatters it by mixing two. **Fixed** at `abccb31`, and the fix's own figure is corrected here: the record says *"removal of the 7 `prefault_region` calls that ran after `fill_fact`"*, but the commit removes **six** and adds **two**, taking the file from **7 call sites to 3** — five of the six removals are the `prefault_region(fact, c.fact_bytes)` form and the sixth is `(fact, phys_bytes)`, and the three survivors prefault regions *before* anything writes them, which is the helper's only safe use. A fail-closed guard and a `what` parameter were added so it cannot be called on an already-written region, and the code now carries the reason inline at **ten** places (*"prefault_region MUTATES"*). **Prevention:** a gate that reports *correctness* must name a reference derived from something other than its subject, and where none exists it should report **agreement** and say so, not `correct`. **Open**, and not on the tenant fix: the `--check` gate remains a two-implementation agreement test, the FS analyzer's cross-arm check remains cross-arm, and **the silicon campaigns are unaudited on this** — `run_silicon_e2e.sh:7` runs the same `build/cxl_join_bench`, and its 105 records carry a constant `matches` of 534,773,760 across 100 cells, which is the same cross-arm invariance and therefore the same blind spot. Whether silicon's absolute join is clean cannot be settled from committed artifacts and was out of bounds this pass *(that last sentence is **superseded the same day** and quoted rather than deleted per `A6.19`: silicon **was** settleable, because unlike r5 its records carry a tenant digest and its match counts are committed. **Silicon is now measured and this component is closed** — see the silicon close-out below — and it closed by confirming the corruption, not by clearing it.)* **The realized half of this class now has a clean counter-measurement, recorded 2026-09-04 from `SILICON_E2E_RERUN_OUTCOME_2026-09-04.md` (`7a72050`), attributed rather than verified because the records are on `c4`.** `G-exact` — the absolute arithmetic assertion that replaced the self-consistency gate, and the independent rediscovery of this class's remedy noted in the index — **PASSED**: a tenant built from committed `HEAD` (`a677c52d…`) reports `matches = 536,870,912` in all 100 tenant records, deficit **0**, against the corrupted dataset's 534,773,760 and deficit of 2,097,152. **The required value is checkable from here and was re-derived** (`8,589,934,592 / 16 × 1`); the achievement of it is not, the re-run's records having been written to `/home/domin/sil_e2e_rerun/out/` on `c4` and deliberately not committed to `data/`. **So on one workload this class now holds both halves of a controlled comparison: a self-consistency gate that admitted 100 corrupted records, and an absolute gate that rejects exactly the defect the first could not see.** No other defect in this ledger has that pairing. **One caveat on how the campaign is described, because "all gates passed" is not what happened:** `G-pred`, the precondition on the predecessor campaign, **FAILED** and was **waived** — recorded in `SILICON_E2E_RERUN_GPRED_WAIVER_2026-09-04.md` (`d709bf7`), written and committed *before any statistic of the campaign existed*, and verified here as preceding the first record by 2 m 48 s (waiver 01:25:18, first record ts 01:28:06). **Two precedence figures circulate and both are right, for different runs — stated together here because a reader comparing the two records will otherwise conclude one is wrong.** The waiver `d709bf7` is authored **2026-09-06 01:25:18 +0900** (re-verified here; author and committer dates are identical, so the distinction does not arise). Measured against the **VOIDed** run's first record, ts **01:28:06**, precedence is **2 m 48 s** — that is the figure this ledger derived, and its referent is the run that was *discarded*. Measured against the **certified 105-record** run's first record, ts **01:43:58**, it is **18 m 40 s** — the figure another worker reported, and **the one that matters, because it is the referent of the dataset anyone will cite**. The arithmetic of the second is confirmed here (01:25:18 → 01:43:58 is 18 m 40 s exactly); **its input is not, and that is disclosed rather than glossed**: ts `01:43:58` appears in no committed document in this clone, and `a8c9b83f`, the commit said to report it, is **not a valid object here even after `git fetch --all`** — a check run in that order because this row's own `git rev-list --not --remotes` lesson demands a fetch before any reachability claim. So the 18 m 40 s figure is **sourced**, the 2 m 48 s figure is **measured**, and the two differ by referent rather than by disagreement. The *admission* gates passed and `G-exact` passed; a *precondition* failed and was overridden on the record. That distinction is the waiver's own and is preserved here rather than smoothed. | 09-04 | **open** on the gate class and on the mode scope; **silicon closed** 2026-09-04, and its realized half **counter-measured** 2026-09-04 |
| F21 | **A gate whose predicate accepts the entire range its quantity can take — a type check presented as a correctness gate.** Registered here 2026-09-04 from `IVF_RECALL_REFERENCE_2026-09-04.md` (`45956d4`), which set out to show that IVF-Flat's `recall_at_k` was tautological in `F20`'s sense and **measured that it is not**. That negative result is the reason this number exists. **The measurement, re-run here rather than accepted.** The reference's corruption control zeroes the leading fraction of the list payload — what a stray `prefault_region`-style write to the mmap'd object would do — and reports recall both self-referentially and against the *uncorrupted* exhaustive top-k. Reproduced independently: at `nlist 1024 dim 64 nb 4096 nq 200 nprobe 4 k 10`, self-referential recall runs **0.6660 → 0.3945 → 0.3170** at 0 / 205 / 1,024 rows zeroed, against **0.6660 → 0.6500 → 0.5540** measured from clean truth, with `id_sum` **3,762,767 → 3,738,789 → 3,205,553**. **So the self-referential quantity moves by 41% of its own value under a 5% corruption. The reference is genuinely sensitive to the defect and the instrument works.** The corruption still goes undetected, and the reason is that **nothing reads the instrument**: `--require-recall` asserts only `out.recall_at_k > 0.0 && out.recall_at_k <= 1.0` (`ivf_flat_bench.cpp:1014`, read here), so 0.3945 passes, and so would 0.02. **Registered as a class rather than as a sub-shape of `F20`, and the argument is the same shape-of-the-remedy test, run to the opposite answer.** *(i) **The two remedies are mutually non-substitutable and point in opposite directions**, which is a stronger separation than `F19` had from `F18`.* `F20` cannot be fixed by any threshold, because no bound rescues a quantity that does not move; its only remedy is a reference computed from something other than the subject. `F21` does not need an external reference at all — the internal quantity already responds correctly — and its only remedy is a **bound**. A fix for either is a non-fix for the other, in both directions. `F19` vs `F18` separated on *emit* versus *declare*, which are at least both additions to the same artifact; these two are disjoint. *(ii) The diagnostic question differs.* To find an `F20` you ask *"is the reference derived from the subject?"*; to find an `F21` you ask *"does any consumer bound this quantity, and does the bound exclude anything the quantity can actually take?"* Both are answerable statically, but they interrogate different halves of a gate — its baseline versus its predicate. *(iii) **The sharpest characterization, and the real reason for the number: `(0,1]` is not a loose bound, it is the quantity's entire definitional range.*** `recall_at_k` is a mean of `\|ivf_k ∩ exact_k\| / k` (`:652–666`) and is in `[0,1]` **by construction**; the predicate therefore asserts only that the value is a well-formed, non-zero recall. It tests **no proposition about the result** — it is a **type check wearing a correctness gate's name**, and that is a different defect from testing a real proposition against the wrong reference. *(**One clause of that sentence is wrong and is corrected 2026-09-04 later the same day, quoted rather than deleted per `A6.19`: "it is a **type check wearing a correctness gate's name**".** The predicate does not wear that name **in its own specification**. `IVF_FLAT_SILICON_PREREG_2026-09-01.md:50-51` registers it, in these words, read here: "Recall is a costume check: if it is missing or not in (0, 1], the cell is void." **So the weak bound is the pre-registered design, and the word "costume" concedes exactly what it does** — the author was not fooled, used the same term of art two lines later for a different sham (`:56`, "A costume quantizer is worse than omitting RAG"), and `analyze_silicon_ivf.py:14` carries the label forward verbatim, "G-recall recall@k in (0, 1], else the cell is VOID (costume check)". **The name is acquired downstream, not claimed upstream, and that relocates the defect rather than dissolving it — see the adoption paragraph below.** This correction is a point in the project's favour and must not be flattened into "someone wrote a bad gate".)* *(iv) It is easier to fix and easier to miss than `F20`, and the second half is what makes it dangerous.* A constant suffices to fix it. But an `F20` leaves a smell — the reference *is* the subject, visible on inspection — whereas a vacuous bound reads as a deliberate engineering choice, and the gate around it performs a real computation on a real quantity that really moves. *(**Confirmed in the strongest available form by the costume-check finding: it did not merely *read* as a deliberate engineering choice, it **was** one, registered in advance and labelled honestly. A reviewer looking for a mistake would have found none, because there was none at that site.**)* *(v) **The positive control corroborates the reading exactly.*** `ivf_gates.py:130–134` feeds `recall_check(0.0)` (must fail) and `recall_check(1.0)` (must pass) — the only two boundary values of the *type* — so the self-test confirms the type check works and can say nothing about 0.3945. This is the second instance in two passes of a control built from an arbitrary failing input rather than from the defect, after `gates.py`'s `self_test()`, and it is now a two-instance pattern in its own right. *(**That criticism is withdrawn for this instance and the wording is kept per `A6.19`: "a control built from an arbitrary failing input rather than from the defect".** Once the specification is known to be a *costume check*, a control that exercises the two boundary values of the type is **exactly the right control for what was registered** — it is faithful, not lazy, and it fails to catch 0.3945 because 0.3945 satisfies the specification. The pattern remains real for `gates.py`'s `self_test()`, where no such specification licenses it, so the count of that sub-pattern drops from two to one. **A control cannot be faulted for not testing a proposition its gate never asserted; the fault is one level up.**)* **Scope, and it is narrower than `F20`'s: the defect is latent, not realized.** Verified here that the IVF tenant contains **no** `prefault_region`-style mutation — the only writes to the mapping are `memset(p, 0, map_bytes)` (`:470`) and `invert`'s payload `memcpy` (`:631–633`), both before `IVF_MEASURE_BEGIN` (`:944`), as the file's own header comment at `:6` states. **No IVF number is wrong and none is in doubt.** **The predicate appears three times, not once**, which is the blast radius: `--require-recall` (`:1014`), the `void_streaming_ivf` determination, which ORs the identical `(0,1]` test into its four conditions (`:1008–1009`), and the harness's own `ivf_gates.recall_check` (`:53–57`). So the VOID decision for the campaign shares the toothless bound with the gate. *(**That last sentence is wrong on both halves and is corrected 2026-09-04 later the same day, quoted rather than deleted per `A6.19`: "So the VOID decision for the campaign shares the toothless bound with the gate."** Re-read at source. **Wrong campaign:** `:1008` is `out.void_streaming_ivf = c.identity && (…)`, so the determination is gated on `--identity` and belongs to the **completed list-dominated identity** campaign; the frontier campaign now running passes `--preset silicon --require-ratio --require-recall` with no `--identity`, so the field is constant `false` in every record it writes. **Wrong direction:** the expression is a disjunction of *failure* predicates — `!g_vma \|\| !g_copy \|\| !g_list_dom \|\| !(recall ∈ (0,1])` — so a disjunct that cannot become true cannot suppress the three that can. **No VOID verdict was ever weakened, and the identity campaign's stands.** The correct statement is stronger in the project's favour than "benign", because the redundancy is **double**: under `--identity` each of `g_vma`, `g_copy` and `g_list_dom` independently prints a `FATAL` and calls `std::exit(1)` at `:1017–1031`, so the process is gone before any record could carry the flag, and the one disjunct that could set it observably — the recall term — is itself shadowed by `--require-recall`'s `std::exit(4)` at `:1014–1016`. `:1108`'s self-test then asserts the field **must be false** for the identity site. So `void_streaming_ivf` decides nothing in either direction; it is a reported field with no reachable authority, and citing it as a blast-radius site overstated it. **The corrected count of the predicate is two implementations and four consumers, not three appearances:** implemented in the tenant (`:1014` and `:1008–1009`) and independently in the harness (`ivf_gates.recall_check`, `:53–57`), and consumed at the tenant's abort, the inert `void_streaming_ivf` field, the analyzer's per-record problem list (`analyze_silicon_ivf.py:105–107`) and the analyzer's **registered**-gate list (`:186–192`, where G-recall is `rc`'s third entry). The fourth of those is the one that matters and it was missing from the count above.)* **The statement of this defect is refined 2026-09-04, later the same day, and the refinement moves its locus from the gate to the *adoption of* the gate — accepted from the handback that raised it, with one amendment.** Given the costume check is registered and honestly labelled, `F21` here is **not** a gate written weaker than intended; it is a gate **correctly implementing a knowingly weak specification that other mechanisms then rely on as though it certified correctness**. Two do so: `--require-recall` (`:1014`) turns it into an **abort** condition, and the analyzer counts G-recall among `registered_gates_ok` (`:186–192`), whose failure prints "a registered kill/void gate fired". *(The handback named `void_streaming_ivf` as the second adopter; corrected above — it is inert, and the analyzer's registered-gate list is the real second adopter, which is a worse one, because it is the line a reader consults to learn whether the registration was violated.)* **The amendment is where the honesty is lost, and it is a clean boundary: the label survives in both *documents* and dies at both *enforcement* sites.** `IVF_FLAT_SILICON_PREREG_2026-09-01.md:50` says "costume check" and `analyze_silicon_ivf.py:14` repeats it; `ivf_gates.recall_check` (`:53–57`) carries no such comment, and the tenant prints `FATAL: recall@k=… not in (0, 1]` and exits 4 with no hint that a costume check is what fired. **The prose kept the caveat and the code kept the authority.** In mitigation of the tenant, `--help` at `:824` states the predicate exactly — "abort unless recall@k in (0, 1]" — so what overstates the check is its **name** and its `FATAL:` prefix, not its documentation. **The consequence for prevention is that no single edit created this defect and no single-file review could have caught it**: the pre-registration was honest, the tenant implemented the specification, the analyzer copied the label, and the harness re-implemented the predicate. It exists only in the composition. **Prevention, restated accordingly:** a gate's predicate must exclude some value the quantity can actually take; a gate whose bound is its quantity's definitional range must be labelled a well-formedness check **at every site that enforces it, not only where it is described**; and a check registered as a costume check must not be counted in any tally called "registered gates" without that qualifier travelling with it. **Fixable now and deliberately not fixed** — and the sequencing reason has changed and grown, see the close-out: the fix is now known to be **an amendment to a registered gate**, not a code repair, so it requires a pre-registration addendum rather than an edit. Logged **open** | 09-04 | **open**, latent; two pending fixes sequenced behind the live `c4` campaign |
| --- | `tab:gem5`'s +H2 column never re-instantiated | 08-23 | **open** (agenda E6) |
| --- | `tab:fused`'s way-sweep runner exists in no commit | 08-23 | **open**, disclosed at the data |
| --- | Sec5 decomposition table is stale against E2B | today | **fix in the writing pass** |

**`F13` is no longer reserved: it is registered above, 2026-09-04.** The
wording this replaces is quoted rather than deleted, per `A6.19`, because it is
the record of why the number sat empty for a day:

> `F13` is deliberately skipped rather than reused. `BUILD_PROVENANCE.md`
> claims it for the `gem5.opt` replaced in place on 2026-09-04 whose source
> state was captured by no commit, and asks (its §5, §"Open") for it to be
> registered in this table. That registration is a separate handback and is
> **not** applied in this pass, so `F13` stays reserved and the next free
> number was taken as `F14` (`F16` in `M1_OUTCOME` is a workload name, not a
> defect).

That handback is the one applied today, and the reservation was honoured
exactly: `F13` was taken by the defect it was held for and by nothing else.
Two consequences for the numbering. `F16` is now **taken as a defect**, so the
parenthetical above no longer reads as a note about a free number — the
`V+F16` in `M1_OUTCOME_2026-08-25.md`, `M1_THREEPARTY_PREREG_2026-08-25.md`
and `M1B_PREREG_2026-08-25.md` is a **workload name and is unrelated to the
defect registered above**, and the collision is stated here so that a reader
meeting both does not merge them. **Update 2026-09-04, later the same day:**
`F17` has since been taken, by the mis-specified-gate class handed back from
`AMD_XSOCKET_OUTCOME_2026-09-04.md` §10 and registered in the table above. The
wording this replaces is quoted rather than deleted, per `A6.19`:

> The next free defect number is **`F17`**.

The next free defect number is now **`F18`**, and no number is reserved.
*(Superseded later the same day and quoted rather than deleted, per `A6.19`:
`F18` has since been taken, by the quantize-and-report-the-unquantized class
handed back from `NONPOW2_SETS_MEASURED_2026-09-04.md` §6 and registered in the
table above. It was confirmed free before use --- this table's series ran
`F3`, `F4`, `F13`–`F17` and this document contained no `F18` anywhere.
**The next free defect number is now `F19`**, and no number is reserved.)*
*(Superseded again, same day, quoted rather than deleted per `A6.19`: `F19` has
since been taken, by the under-declared-inline-asm class handed back from
`M5OP_RAX_CLOBBER_AUDIT_2026-09-04.md` §8 and registered in the table above. It
was confirmed free before use — the only `F19` in this document was the
sentence above and the closing paragraph that pointed at it. **The next free
defect number is now `F20`**, and no number is reserved.)*
*(Superseded a third time, same day, quoted rather than deleted per `A6.19`:
`F20` has since been taken, by the tautological-correctness-gate class derived
from `BENCH_SOURCE_PROVENANCE_2026-09-04.md` and registered in the table above.
It was confirmed free before use — the only occurrences of `F20` in this
document were this numbering note and the two closing paragraphs that pointed at
it, none of them a defect entry. **The next free defect number is now `F21`**,
and no number is reserved.)*
*(Superseded a fourth time, same day, quoted rather than deleted per `A6.19`:
`F21` has since been taken, by the vacuous-predicate class derived from
`IVF_RECALL_REFERENCE_2026-09-04.md` and registered in the table above. It was
confirmed free before use — every `F21` in this document was a "next free
number" note, and none was a defect entry. **The next free defect number is now
`F22`**, and no number is reserved. Note for anyone reading the sequence: `F18`
through `F21` were all registered on 2026-09-04, and three of the four came out
of one thread of work on a single defect mechanism, so the density is a property
of that day's auditing rather than of the apparatus decaying.)*

### Status history

**F3, three states.** The row has moved twice on 2026-09-04, and the sequence
matters more than the endpoint, because the second move supersedes the first on
the same day.

1. **08-23 → 2026-09-04 (morning), as originally opened:**

   > `tab:h1bw` ordering not reproduced; harness gone — **open**

2. **2026-09-04, first same-day edit** (handed back by
   `H1BW_ARM_IDENTITY_2026-09-04.md` §"Index changes handed back", which
   explicitly recorded "F3 stays open"). The cell then read, and this wording is
   **now superseded**:

   > `tab:h1bw` ordering not reproduced; harness gone. **Updated 2026-09-04:**
   > the *arm identity* is now settled and the paper relabelled — the third arm
   > is prefetch-off, and the model has no write-combining memory type from
   > which a WC arm could be built (`H1BW_ARM_IDENTITY_2026-09-04.md`). The
   > ordering is corroborated by `GATE1_H1BW_ANOMALY_RESOLVED_2026-08-18.md` at
   > matched work and by the certified multi-core campaign. **What remains open
   > is the twelve magnitudes, not the claim** — **open**

   That edit was correct when made. Its stated ground for keeping F3 open was
   that the twelve magnitudes were still unbacked, and at the time they were:
   the arm-identity audit settled the *label* on the third arm without putting
   an artifact behind any number in the table.

3. **2026-09-04, superseding the above** — the current cell. What changed is
   not the reasoning but the evidence: `H1BW_SINGLECORE_OUTCOME_2026-09-04.md`
   landed six certified cells with retained artifacts, so the twelve magnitudes
   are no longer unbacked-and-published; they are unpublished and replaced. The
   ground the earlier edit named is therefore discharged rather than overruled.
   **F3 closes on replacement, not on reproduction** — the archive's runs are
   not recovered and the disclosure in the cell above says so.

**`F13`, three states in one day, and two of them arrived mid-write.** Opened and
registered in the same entry, 2026-09-04, having been reserved without a row
since the day before.

1. **As first written, and now superseded:** logged **open**, on the ground its
   own cell draws — the gitlink bump at `065fd80` repaired *which* simulator
   this repository names, not *whether* anyone can obtain it, and a defect
   needing a `git push` in another repository to close is still open here.

   > open, identity repaired and reachability not

2. **Superseding the above, the same day:** **closed on its own subject.** The
   push happened, at `2026-09-05 01:51:32` KST, between this row's measurement
   and its commit. The reasoning in state 1 was right and its premise expired;
   the ground it named — that the simulator could not be obtained — is
   **discharged rather than overruled**, which is the same shape as `F3`'s
   third state above. What stays open is the **superproject** push, a different
   repository's gap that `BUILD_PROVENANCE.md` tracks separately, and this
   ledger does not count it against `F13`.

3. **Superseding state 2's remainder, later the same day:** **closed outright.**
   The superproject push happened. `origin/main` moved `73f0332f6c →
   322c9564ee`, verified **server-side** with `git ls-remote` rather than from
   this clone's remote-tracking refs, and the published commit records the
   `gem5` gitlink `fa27f665db02` which resolves on the submodule's remote. The
   wording state 2 left standing is quoted in the cell above rather than
   deleted, per `A6.19`.

   > open only on the superproject push, tracked elsewhere

   Two qualifications belong with the closure and are in the cell. The
   **95-commit figure state 2 carried does not verify** and was not re-derived
   by whoever wrote it: the published range is **103** commits, and `main` sat
   in double figures beyond the published tip and rising while this was written,
   so do not read a count out of this state history either. And
   closing `F13` does **not** make
   the repository published — it makes the *pointer to the simulator*
   published, which is the only thing this row ever claimed.

The measurement error that produced state 1 is recorded in the cell because it
generalises: `git rev-list --not --remotes` reads *local* remote-tracking refs,
so without a `git fetch` it reports an already-completed push as absent. Every
future reachability claim in this ledger should be preceded by a fetch, and this
one now is.

**`F16`, and why it is logged as a verifiability limit rather than a defect in
the claims.** The verdict was not obvious and the reasoning is recorded so it
can be argued with.

*The case for calling it a claims defect.* The paper says "pre-registered",
"registered before the runs", "registered in advance". A reader takes those as
claims about the order in which two things happened. For ten of the fourteen
campaigns (**this read "nine" until the 2026-09-04 birth-time re-audit**; quoted
per `A6.19`, and the two reclassifications are in `F16`'s cell), the only
evidence for that order is the registration document
saying so in its own first two lines — `COMPLETE_JOIN_PREREG`'s "Date:
2026-09-01. Registered **before any arm of this campaign produced a number.**"
is representative. Nothing external corroborates it: git has the data landing
first, and the one filesystem timestamp anybody would reach for is
demonstrably inverted. A hostile reviewer can therefore decline to credit the
word "pre-registered" for those nine, and nothing in this repository stops
them.

*The case for calling it a verifiability limit — which is the one this ledger
adopts.* Three things are true at once and only the third is in doubt. **The
documents exist**, all fourteen, and are now committed. **They are internally
consistent with pre-registration in a way that is expensive to fake**: they
carry action-on-miss thresholds that later went on to fail — `FUSED_KNEE`'s
model A refuted at 87.69% against its own registered `< 80%`, `H2H_REALJOIN`'s
P6b monotonicity failing, `H1BW_CXLBW`'s `h2_8c` clipping prediction missed at
0.994×, four `H1BW_SINGLECORE` footprint bands failed and **reported as
failures** — and a registration written after the data would not have
registered predictions its own data refutes. `H2H_REALJOIN_PREREG` goes
further and labels its own "Amendment 1, three corrections made AFTER data
existed" as exactly that. **What is absent is only the external witness.**
That is a different finding from "the claims are wrong", and conflating the
two would misreport the project's discipline as badly as overstating it would.
The registered/unregistered distinction in particular appears to be reported
accurately — see the passage audit below, where it is the part that *is*
witnessed.

*The consequence, stated in the form a reviewer would use.* For ten
campaigns (**"nine" as first written**, quoted per `A6.19`; `H1BW_SLICE_BRACKET`
joined them on 2026-09-04 and `FB_ORACLE` became indeterminate), "pre-registered"
should be read as **attested and internally
corroborated, not independently verifiable**. That is weaker than the word
alone implies and stronger than nothing. It is also **not recoverable** —
no action taken now can create a witness for an order of events that has
already happened — which is why this row is logged as a limit and left open
rather than routed for repair. **One addition from the birth-time re-audit
belongs in this reading rather than only in the cell**: the phrase "internally
corroborated" can now be said to include the filesystem. The registration
documents of every bulk-pass campaign with an in-band launch time to check
against were **on disk before their campaigns started** — by 29 seconds in the
tightest case and 41 minutes in the loosest — and the mtime pair this row offers
as its inversion proof runs the right way round in *birth* time. A reviewer
cannot see any of that, because git carries no filesystem timestamps. So the
correct reading is not "there is no evidence of order" but "**the evidence of
order exists and does not travel**", which is a materially different thing to
disclose and is the sharper form of the same conclusion.

**The eight paper passages, audited before the exposure was characterised.**
Read in `/home/domin/STREAMING_Paper/ASPLOS27/Text/`. **Seven of the eight are
git-witnessed and only one is not**, which narrows the exposure sharply and is
the reason `F16`'s cell says so rather than reporting eight.

- **`Appendix.tex:403`, "Pre-registered and certified: six cells, twelve
  fail-closed gates".** Witnessed, and **the ground under it has since been
  corrected rather than removed.** The reasoning first written here was:

  > `H1BW_SINGLECORE_PREREG_2026-09-04.md` is frozen at `b4ac57c` (2026-09-04
  > 21:22:22); the run directories under `logs/se_chi_h1bw_sc/` were created
  > 21:48–21:50, i.e. **26 minutes after the registration was in git**; and the
  > outcome plus `h1bw_singlecore.jsonl` landed separately at `6fa71f5`
  > (22:07:17). Three independent orderings, all in the same direction.

  Quoted rather than deleted, per `A6.19`, because the middle clause is a
  **method error and not a typo**. `21:48–21:50` is the run directories'
  **mtime**, and this harness writes `MANIFEST.json` and `DONE.json` at
  *completion*, so the figure is a completion time wearing a creation time's
  clothes. The committed data says so in band: `data/gem5/h1bw_singlecore.jsonl`
  records `started` for all nine cells at **21:00:20–21:00:36** and its earliest
  `ended` at **21:48:07**. The runs were therefore **already in flight 21 m 46 s
  before** the registration was committed, and the mtimes agree with `ended`, not
  with launch. **Two of the three orderings stand and the third reverses**: the
  registration precedes the earliest reported result by **25 m 45 s** and
  precedes the outcome-plus-data commit by 44 m 55 s, so the thresholds are
  witnessed to have been in git before any cell reported — which is the ordering
  `Appendix.tex:403`'s "pre-registered" needs, and which
  `H1BW_SINGLECORE_OUTCOME_2026-09-04.md` establishes independently by recording
  that all nine `stats.txt` were still 0 bytes at 21:22. It does **not** precede
  launch. The outcome document needs no correction: its header already says
  "before any cell emitted a statistic" and its §9 is candid about the 21:00
  launch. **The general lesson is the one worth keeping**: a directory's mtime
  tracks the last entry written into it, which is a property of the harness and
  not of the campaign, so it means *launch* for a tool that populates its output
  directory at startup and *completion* for one that closes it with a manifest.
  The same command gave opposite answers on this campaign and on `FUSED_KNEE`
  below, and only one of the two was ever checked against an in-band stamp.
- **`Sec7_Evaluation.tex:238, 239, 274, 276, 277, 280`** — six passages, all
  resting on the same registration, and the strongest-worded of them is 238's
  "the five table sizes from 2.0 to 4.0~MB were registered before the runs
  ($45$ runs)". Witnessed, and twice over. `FUSED_KNEE_PREREG_2026-08-29.md`
  was committed at **`eb20d93`, 2026-08-29 22:58:37**, has **never been
  modified since** (one commit in its whole history — the subject of that
  sentence is the *file*; `eb20d93` itself sits on 502 ancestors, 503 commits
  counting itself, and this is noted only because the clause is easy to misread
  as a claim about the commit's ancestry), and its data (`kn_runs.jsonl`,
  `kb_runs.jsonl`) landed at `acc722a` **nine and a half hours later**.

  **The independent half of this bullet was measured wrongly and is now
  measured from the artifacts themselves.** What it said, quoted rather than
  deleted per `A6.19`:

  > Independently: the first run directory, `/tmp/kn_cat4_t2.0_s1`, was created
  > at **22:58:38.53 — one second after the registration commit** — and the
  > unregistered extension's `/tmp/kb_*` directories at 2026-08-30 01:33,
  > afterwards. So the registered/unregistered distinction that `F15` narrowed
  > the `fig:recovery` claim onto is the part of the paper's registration story
  > that **is** externally corroborated.

  `22:58:38.53` is that directory's **mtime**; its birth time is
  **`22:58:38.127`** (measured across all 45: birth `22:58:38.1248–.1551`, mtime
  `22:58:38.5308–.5608`). **The verdict was right and the reasoning was not, and
  it was right by luck** — here gem5 creates the output directory and finishes
  writing its metadata inside half a second, so mtime and birth land in the same
  second; the identical inference on the `H1BW_SINGLECORE` harness above is wrong
  by 48 minutes. **The replacement is in-band and committed**, so it survives a
  clone where no filesystem timestamp does: all **45** `kn_*` runs report
  **`gem5 started Aug 29 2026 22:58:38`** in their own logs, one second after the
  registration commit, and the runner's own completion stamps close the sweep at
  **01:30:39** (`kn_sweep.done`, `KNEE_DONE 1788021039`). Tracked at `3ed6ff0`
  under **`artifacts/fused_knee/`** as byte-for-byte originals — 65 files,
  228,846 B (223.5 KiB) — with SHA-256 digests for the **504** larger originals
  left on tmpfs in the same directory, and the whole selection argued in
  `FUSED_KNEE_RUNLOG_PROVENANCE_2026-09-04.md`.

  **"Externally corroborated" is an overclaim and is withdrawn in favour of a
  narrower claim that is actually true.** The banner and the commit date come
  from the same host clock, a git author date is settable by whoever makes the
  commit, and `eb20d93` is **unsigned** (`%G?` = `N`, checked). What the evidence
  establishes is that the launch time is **generated by the simulator rather than
  asserted by the author** — 45 independent gem5 processes each wrote the same
  start second into its own file, the runner's stamps bound each run's span, and
  the uncommitted `stats.txt` and `config.ini` are digested and would have to
  agree with all of it. Falsifying it now means **forging 45 coherent logs**, not
  adjusting one number. That is weaker than third-party attestation and much
  stronger than the document's own say-so, and it is the strongest form the
  registration property takes anywhere in this project. So the
  registered/unregistered distinction that `F15` narrowed the `fig:recovery`
  claim onto is the part of the paper's registration story that is **corroborated
  by the instrument rather than by the author**, which is worth stating plainly
  given that this row could easily be misread as undermining it.

  **One scope limit, because the campaign is easy to treat as 63 uniform runs.**
  The 18 `kb_*` directories carry a **different** banner —
  `gem5 started Aug 30 2026 01:33:02`, a separate launch **2 h 34 m 25 s** after
  the registration commit and 2 m 23 s after the `kn` sweep closed. Both banners
  postdate `eb20d93`, so registration-before-run holds for all **63** runs; it is
  only the **one-second tightness that is `kn_*`-only**. This matters beyond
  bookkeeping: `kb_runs.jsonl` is what the `fig:recovery` row above, this
  ledger's `F15`, `FUSED_KNEE_CLOSED_2026-09-04.md`,
  `RECOVERY_CURVE_OUTCOME_2026-09-04.md` and `make_recovery_curve.py` all read,
  and the **8.0 MB endpoint carrying the headline "89.4% to 56.8%" is a `kb_*`
  point** already logged under `F15` as in no pre-registration's design. The two
  distinct banners are what makes that registered/unregistered split checkable
  from a clone rather than taken on trust, which is the distinction `F15` exists
  to protect.
- **`Sec7_Evaluation.tex:143`, "The registered discrete comparison uses the
  cheapest observed mask with at least as much recovery".** **Not witnessed —
  this is the one.** It cites `COMPLETE_JOIN_PREREG_2026-09-01.md:91` ("Wedge,
  if P5 holds: cheapest CAT width with protection >= H2"), which was committed
  at `61c8a8e` alongside its own outcome, three days after r5 ran
  (2026-09-01 23:51 → 2026-09-02 05:01) and after its data was committed at
  `fee8417`. It is also the campaign whose mtime pair supplies this row's
  inversion proof, so the filesystem does not help and in fact reads the wrong
  way. Precedence here rests solely on the document's own attestation.

**Recommended paper wording, handed back and deliberately not applied** — the
draft is owned by another worker and nothing in `Text/` was edited. One
passage needs a decision and the others do not. For `Sec7_Evaluation.tex:143`,
either qualify to

> The pre-registered discrete comparison uses the cheapest observed mask with
> at least as much recovery

leaving "registered" doing only the work it can support, or — the option this
ledger would prefer, since it costs one clause and settles the point — make
the attestation explicit at its single strongest use rather than hedging every
instance:

> The discrete comparison — the cheapest observed mask with at least as much
> recovery — was fixed in the campaign's pre-registration before its arms ran;
> that registration is committed alongside its outcome, so its precedence is
> attested by the document rather than witnessed by commit order.

The seven witnessed passages need **no qualification**, and `fig:recovery`'s
"registered before the runs" wording at line 238 should specifically **not** be
softened: it is the best-evidenced registration claim in the paper. Whether to
qualify 143 at all is a judgement about how much a reviewer is owed, not a
correction of a wrong statement, and it is routed rather than decided here.

### Handed back to this ledger and routed on, 2026-09-04

Two items arrived from `H1BW_SINGLECORE_OUTCOME_2026-09-04.md` §9 for documents
that campaign did not own, and neither has a home in the tables above. Recorded
here so they are not lost, per `F11`.

- **`tab:gem5cfg`'s `Prefetch` row** reads "L1/L2 Stride(4) + DCPT". The L2 pair
  is Stride + **Tagged**, not Stride + DCPT (`CHI_config_8592.py:703-721`), as
  `H1BW_ARM_IDENTITY_2026-09-04.md` already logged. This is paper text and was
  **not applied** — the draft is owned by the paper-reconciliation pass. Note
  for whoever applies it: the `tab:gem5cfg` row above records "1 defect, 1
  imprecision" from 2026-08-23, and whether this is that already-counted defect
  or a second one is **not established here**; recount before amending the row.
- **`CHI_config_8592.py:315-321`**, which names replacement-path starvation as
  "a candidate cause of H2 fill-suppression degrading at high `L1_MSHR`", is
  **measured inert at one core** by that campaign's diagnostic set D
  (`L1_REPL` 48 → 16 at `L1_MSHR = 48` moves `h2` 1.76%, less than `wb`'s 2.95%,
  with `E_clean` unchanged at 99.98/99.99%). Scope: one core, 48 MSHRs. This is
  a source comment rather than a published number or a certified outcome, so it
  is **not applied** and is left for that file's owner, as the handback asked.

## Standing wording rules

Rules that constrain how any future record in this project may **phrase** a
claim, as distinct from the defects above, which record things that went wrong.
They live here rather than in a defect row because a defect row is discoverable
only by someone already reading about that defect, whereas these bind on anyone
writing the sentence. Cited in the `A6.19` style — by the document that carries
them and their number — because that is how this project's one existing wording
rule is in fact cited.

**`A1.R1` (2026-09-04) — a byte-reproducibility claim must name a host and a
toolchain, or it must not be made.** "Rebuilds byte-identically", "bit-identical
to the live binary" and "reproducible from committed source" are **never
properties of a source tree**. Every benchmark binary in this repository that
runs on a host is compiled `-march=native`, so a reader on different hardware
gets different machine code *by construction*, and a reader with a different
compiler gets different machine code again. The admissible form names both
coordinates: *"byte-reproducible on `<host>` with `<compiler version>`;
cross-host byte-identity is neither expected nor claimed."*

*Scope, verified here rather than inherited.* `-march=native` is carried by all
four benchmark `Makefile`s — `ivf_flat/Makefile:2` (`-march=native
-mclflushopt`), `hash_join/Makefile:2`, `bench/Makefile:2` (`-march=native
-fno-tree-vectorize`, in `CFLAGS`), `instrument/Makefile:10` (`-march=native
-mavx2 -msse4.1`) — and by the three tenants that build by script or patch:
`hnsw/scripts/setup_hnsw.sh:19`, `oltp_index/patches/d1d2_pmu_and_l2size.patch:6`
and `duckdb_join` per `benchmarks/e2e/duckdb_join/DUCKDB_JOIN_CORUN_PREREGISTRATION.md:1385`.
**The exceptions are not one target but a category**, and the handback that
prompted this rule named only one of them: `hash_join`'s six gem5 recipes all
omit the flag and are all `-static` — `:34`, `:40`, `:44`, `:59`, `:76`, `:89`.
The dividing line is therefore **host target versus gem5-guest target**, not
"everything except `gem5fs`", and the corrected statement is the more useful one
because it says *why*: a guest binary has no native host to be tuned to.

**Why this is a wording rule and not a ninth note about a compiler flag, which is
the whole point of it.** The repository already documents the property in **eight
files**, and the error was still made — by a record that was itself assembling
the list of those eight files. Spot-checked here, all of them, not the two asked
for. Eight files carrying **nine** line citations, `instrument/README.md`
contributing two:
`instrument/Makefile:6` ("`-march=native` means the binary is host-specific. Each
host builds its own; binaries are never copied between hosts"),
`instrument/README.md:57` and `:68` ("part of the instrument, not an optimisation
detail"), `MOS182_PROVISIONING.md:22`, `E3_OUTCOME_2026-08-28.md:201` ("a caveat
that cannot be fixed, only stated"), `W5.4_VICTIM_MLP_2026-08-23.md:132`,
`benchmarks/e2e/hnsw/HNSW_CAT_SENSITIVITY_OUTCOME.md:95` and
`AGGBW_VALIDITY_2026-09-03.md:95` and
`BENCH_SOURCE_PROVENANCE_2026-09-04.md:406`. **All nine lines land on
`-march=native` text and not one is a miscitation.** Two files are cited by bare
name and resolve
under `benchmarks/e2e/` rather than `experiments/asplos/`, which costs a reader a
`find`; that is the only defect in the set and it is not a figure.

**One of the eight refutes the handback's own scope claim, and that is the
sharpest argument for the rule.** `AGGBW_VALIDITY_2026-09-03.md:88-97` states
that the `gem5` target "compiles with `-O3 -mclflushopt -DGEM5 -static` and **no
`-march=native`** (`benchmarks/e2e/hash_join/Makefile:44`), so `__AVX2__` is
undefined" — a documented, load-bearing omission at a line the handback did not
count among its exceptions. So the property was mis-applied **twice in one
document**: once to a binary and once to the list of places proving it was known.
Documentation of a *fact* failed eight times over; what has not been tried is a
constraint on the *sentence*. That is the gap this rule fills, and it is the
reason a ninth documentation would not have been the remedy.

**Placement, decided against the handback's suggestion and this is the fourth
framing overturned today.** The suggestion was to file this "in the same place as
`A6.19` and the other conventions". There is no such place. `A6.19` is item 19 of
a **dated incident journal inside one campaign's pre-registration** —
`DUCKDB_JOIN_CORUN_PREREGISTRATION.md:1977`, "I contaminated a committed artifact
on `mos181` after the block" — sitting among nineteen entries about outlier
rules, watcher hazards and a block that crossed midnight. It is not a conventions
registry; it is where one convention happened to be *born*, and it became
citable project-wide because the rule extracted from it was load-bearing, not
because the file is a home for rules. Appending `A1.R1` there would file a
constraint on every future provenance sentence inside an unrelated campaign's
journal, which is worse discoverability than a defect row, not better. It is also
outside this pass's permitted edit set. **A wording rule about provenance claims
belongs in the provenance ledger**, which is already this project's citation hub
for `A6.19` itself.

**`A1.R2` (2026-09-04) — a liveness or idleness probe must exclude the prober
from its own domain, or its positive result means nothing.** Match on
`/proc/*/comm`, or on `pgrep -x`, or on `[p]attern`; never on a full command line
that contains the pattern being searched for, because the searching shell's own
argv contains it. **Registered as a rule and deliberately not as a defect number**
— the reasoning is below, and it turns on this hazard having no reachable path to
any published figure.

*The count, verified here because the handback asked and because it is the whole
argument.* The handback reported "four separate times". **That is the project's
own prior count and it is now stale by at least one.** Four is what
`experiments/asplos/silicon_e2e/gates.py:7-8` states, in the module docstring of
the harness's own gate library: "G-idle looks at `/proc/*/comm`, never at the full
command line: `pgrep -f gem5` matching the invoking shell is a failure this
project has paid for **four times**." `AGENT_BRIEF_SILICON_E2E_2026-09-01.md:161`
independently states "**Four occurrences**", under a heading that reads "Failure
modes this project has already paid for — Read these; each cost hours."
**Both predate the 2026-09-04 recurrence**, which is recorded at
`SILICON_E2E_RERUN_GPRED_WAIVER_2026-09-04.md:131-135` — a first pass with
`pgrep -af "run_ivf|run_hashjoin"` matching its own `bash -c` command line. **So
the count is five, not four**, and the underlying tally is itself inconsistent
across the record: `HANDOFF_2026-08-21.md:82` says "three times" *in one session*
and already prescribes the remedy ("Match on `comm`, never on argv"), while
`PLAN_B_REBUILD.md:1023` (2026-08-24) calls its own instance "the ancestor-argv
trap seen live **a second time**". Those two cannot both be counts of the same
thing, so the project has been counting episodes in one place and invocations in
another. **This rule counts episodes and fixes the basis: five.**

**Why a rule and not a number, and the argument is stronger here than it was for
`A1.R1`.** *(i) It binds to no published figure, which every one of `F1`–`F21`
does.* The committed harness **already implements the remedy**: `host_idle()`
calls `idle_check(load1(), comms_now(), LOAD_MAX)` (`run_hashjoin.py:70-71`,
`run_ivf.py`), which reads `comm`, so no record has ever carried a wrong
`idle_ok` — and `rerun_analyze.py:224` *does* enforce `idle_ok`, which means a
self-matching harness **would** have voided records and the only reason none did
is that the harness is right. A defect class in this ledger must be citable
against a number; this one cannot be. *(ii) The polarity is opposite to
`F20`/`F21`, and the handback's proposal to seat it in that family founders on
exactly that.* `F20` and `F21` are gates that cannot **fail** — false negatives,
staying green while admitting bad data. A self-matching probe cannot **pass** — a
false positive, reporting a busy host that is idle, which by the brief's own
account "will skip every arm and look like a busy host". **A defect that screams
stops work; a defect that stays green licenses wrong work.** The surface
similarity is real — in all three the instrument contaminates its own reading —
but the consequence classes are disjoint, and this ledger's numbers exist for the
one that licenses. *(iii) The remedy is a constraint on practice, which is what
these rules are for.* Not an external reference, not a bound, not a commit: an
exclusion of the observer from the observed set. *(iv) **The decisive fact, and it
is new rather than inherited: the remedy was implemented in the wrong layer, and
that is why five documentations did not stop it.*** `gates.py` does not merely
document the hazard, it **is** the fix, and it carries a **positive control built
from the defect itself** — `:196-199`, `idle_check(0.1, ["bash", "ssh"])` must
return `True`, commented "The pgrep-self-match case: a command line containing the
word is irrelevant because we look at comm, not argv". That is the one control in
this project built from the actual failure rather than from an arbitrary input,
and it works. **It cannot help, because the recurrence happens at a shell prompt
during ad-hoc verification, on a path that never calls `gates.py`.** Hardening the
artifact is unreachable from the site of the error. `A1.R1` had a property
documented eight times and never implemented; this one is documented five times,
implemented, *and* regression-tested, and still recurred — which shows the
category of remedy that was missing was never code. **That is precisely what a
wording-and-practice rule is, and it is why the fifth instance earns a rule
instead of a sixth document.**

**`A1.R3` (2026-09-04) — a divergence or diff count must name the two objects
compared *and* the counting rule, or it must not be given.** "A 673-line
divergence" is not a property of a file. The admissible form names all three
coordinates: *"N changed lines between `<object A>` and `<object B>`, counted by
`<rule>`."*

*Why this is a rule and not a note, demonstrated four times in the single pass
that produced it — which is more evidence than either sibling rule had at
registration.* **(1)** One pair of files yields **three** different "correct"
counts: `c4`'s uncommitted `cxl_join_bench.cpp` (`e8d104588c756bae…`) against the
pre-hoist `HEAD` blob (`b843d46595873e14…`) is **673** by
`diff | grep -c '^[<>]'`, **675** by `diff -u | grep -c '^[-+]'` — which silently
counts the `---` and `+++` header lines — and **667** by
`diff -u | grep -c '^[-+][^-+]'`, which silently drops six added *blank* lines
because a bare `+` has no character after it to match. All three were re-derived
here. **The off-by-two and the off-by-six are properties of the grep, not of the
source.** **(2)** The same pair against **post**-hoist `HEAD` is **680**, so the
count moves when either object moves, and the record that reported it did not say
which `HEAD` it meant. **(3)** Against `33eaf07`, `c4`'s *actual checkout commit*,
it is **799** — the number a reader would plausibly assume "divergence from the
checkout" denotes, and no record states it. **(4)** And the rule caught its own
handback in the same breath: the hoist `77e06b6` was described as "7 lines added
and 1 line changed" where `git diff --numstat` reports "**8** insertions, 1
deletion". **Both are right** — the human counted a replaced line once, git counts
it as a deletion plus an insertion — and the figures differ by exactly the
convention nobody stated.

**The consequence for how this ledger reads other records.** A diff count that
disagrees with another diff count is, by default, **two different measurements
rather than one error**, and the burden is to identify the rule before alleging a
mistake. This ledger got that wrong once already, by carrying `675` as "the
record's figure" against `673` as "the handback's figure" as though one had to be
false. **Neither was false. Both were under-specified**, and so was this ledger's
report of the disagreement.

**Relation to `A1.R1`, and the standing rules are now a family with a common
principle.** `A1.R1` requires a rebuild claim to name a host and a toolchain;
`A1.R3` requires a comparison count to name its objects and its rule. **Both are
instances of one proposition: a number that is secretly a *comparison* is
meaningless without its coordinates, and the failure mode is always that the
coordinates felt too obvious to state.** Two instances is the standard `F17` set
for naming a class, so the family is named here — but the members are kept
separate rather than merged, because the coordinates each demands are different and
a merged rule would state neither. `A1.R2` is **not** a member: its subject is a
probe's construction, not a figure's phrasing.

## What this ledger establishes

Every number the paper newly relies on this week is bound to a committed artifact
and recomputes. The three tables whose cells I recomputed from raw data today ---
`tab:amdcat`, `tab:fused`, and the Sec5 trade-off table --- are **20/20**. No
number in the paper is currently untraceable, which was not true on 08-23 (RocksDB
and `tab:amdcat` both were).

What remains is four inherited annotation/harness defects, one stale inline table,
and the +H2 column --- none of which is a wrong number, all of which are
disclosed.

**Update 2026-09-04.** One of those four is closed: `F3` closes **on
replacement**, not on reproduction. Three inherited defects remain open (`F4`,
`tab:gem5`'s +H2 column, `tab:fused`'s way-sweep runner), alongside the stale
inline table. One record was opened and closed the same day (`F14`, closed by
disclosure), and one number is reserved but not yet registered here (`F13`, held
by `BUILD_PROVENANCE.md`). The sentence above still holds as written: none of
these is a wrong number and all of them are disclosed.

**Update 2026-09-04, close-out handback pass.** One row added, one defect opened,
nothing committed. `fig:recovery` now has a ledger row --- the first **figure**
in this table, every previous row being a `tab:*` --- and it is **VERIFIED
63/63** against the raw archives, recomputed here rather than transcribed, so the
paper's boundary argument is bound to artifacts for the first time. Against that,
**`F15` is opened and stays open**: the figure's registered-sweep attribution
names the wrong pre-registration, and its 8.0 MB endpoint --- the far end of the
"89.4% to 56.8%" range printed in `Sec7_Evaluation.tex` --- is in no
pre-registration's design. That is an **attribution** defect rather than a
measurement one, so the sentence above still holds: it is not a wrong number and
it is now disclosed. It is left open deliberately, for the worker analyzing how
the claim should be narrowed; the caption and body text are owned by the
paper-reconciliation pass and were not edited. The count of open items is
therefore **four defects** (`F4`, `F15`, `tab:gem5`'s +H2 column, `tab:fused`'s
way-sweep runner) plus the stale inline table, with `F13` still reserved.

One further exposure was recorded in the new row and was **not** logged as a
numbered defect here, because it is a repo-hygiene fact rather than a provenance
claim about a published number. **Update 2026-09-04: it is closed, and this
paragraph now records the closure.** The wording it replaces said that
`make_recovery_curve.py` and `make_eval_frontiers.py` were untracked, that
"both of the paper's two figures are currently produced by files in no commit",
and closed "Reported, not fixed". Every clause of that is now false, and the
superseded text is quoted here rather than deleted, per `A6.19`.

**Both generators are tracked**, at `9791976`, and so are the two inputs that
were missing: `data/gem5/r5_runs.jsonl` at `fee8417` and
`data/silicon_e2e_hashjoin.jsonl` at `ea28693`. Both figures were then
regenerated from tracked content alone and verified **pixel-identical** to the
PDFs the paper includes. **The campaign runners are tracked too** --- thirteen
of them, 2026-09-04, one commit per campaign --- so the data behind both figures
can now be **re-collected** and not merely re-plotted, which is the half of
reproducibility the generators alone did not buy. The single shell script under
this directory still left out is `data/kernel/initramfs_init_2026-09-03.sh`,
which is a guest initramfs init for a kernel campaign whose kernel source is
live in another worker's uncommitted tree and whose outcome document is itself
untracked; it produced nothing this ledger binds.

One correction to the replaced wording, which also claimed "`fig:recovery`'s own
inputs are committed". That was true of its **bulk** inputs --- `kn_runs.jsonl`,
`kb_runs.jsonl` and `fh_runs.jsonl`, all at `acc722a` --- and **not** of panel
(c)'s held-out complete-join point, which comes from `data/gem5/r5_runs.jsonl`
and was untracked until `fee8417`. `fig:recovery` was therefore one commit short
of reproducible for the same reason `fig:frontier` was, and the row above now
says so.

Two exposures remained once the generators landed. One of them is also now
closed:

1. **The matplotlib dependency was declared nowhere.** Both generators need it,
   the system `python3` on this host does not have it, and the interpreter that
   does was the untracked `~/fig-venv`. **Closed 2026-09-04** by
   `experiments/asplos/requirements.txt`, pinned to the `matplotlib==3.11.1`
   the figures were verified under and colocated with the generators, which is
   the convention `benchmarks/analysis/requirements.txt` already sets for the
   two plotters beside it. Only matplotlib is load-bearing: both generators
   request "Linux Libertine O" behind a declared Nimbus Roman then DejaVu Serif
   fallback, so a host missing the acmart body face gets different typography
   rather than a failed build, and no font package is declared.
2. **The figure PDFs themselves were untracked.** **Closed 2026-09-04**, in the
   paper repository rather than this one. The wording this replaces is quoted
   rather than deleted, per `A6.19`, and every clause of it that named a state
   is now false:

   > **The figure PDFs themselves are untracked**, and that is not this
   > repository's to close. `ASPLOS27/figures/` lives in the paper tree, a
   > separate repository in which that directory has never been committed at
   > all, so the paper's figure set exists only as working-tree files on one
   > machine. **Open, reported, and deliberately not acted on** --- the paper
   > tree is owned by another worker, and whether those PDFs should be tracked
   > there or built by the artifact pipeline from this repository is routed
   > rather than decided here.

   `ASPLOS27/figures/` now holds four tracked files and no untracked ones,
   verified here today: `recovery_curve.pdf`, `recovery_curve.png` and
   `eval_frontiers.pdf` at **`70a55c5`**, and `eval_frontiers.tex` at
   **`7e7e07d`**. The routing question the replaced wording left open was
   answered the first way — tracked in the paper tree — and this ledger did
   not decide it.

**What tracking the PDFs cost, recorded beside what it bought.** It bought a
paper tree that builds on its own, with no dependency on a figure pipeline in
another repository. It cost a **duplication of derivable content into a second
repository**, which is the thing the pipeline existed to avoid: three of those
four files are generator output (`make_recovery_curve.py` emits both
`recovery_curve.pdf` and `recovery_curve.png`; `make_eval_frontiers.py` emits
`eval_frontiers.pdf`), so the inputs, the generators and the committed copies
can now **drift apart silently**. Nothing enforces agreement. The only
available check is **manual: regenerate and compare**, which is what was done
once to establish pixel-identity and is not a standing gate. A reader who
believes the tracked PDF is current has no way to confirm it from either
repository.

**The more interesting find behind that commit, and it is a `F10`-family
result rather than a hygiene one.** `eval_frontiers.tex` — the file committed
separately at `7e7e07d`, and separately for a reason — is a **hand-written
pgfplots reimplementation of a matplotlib figure**, and **no generator in this
repository emits it**. Its data was **transcribed by hand**: verified here
today by running `make_eval_frontiers.py`, which prints panel (a) as
`R=22.35% tenant=+5.34%` against the file's literal
`coordinates {(22.35,5.34)}`, and prints `nta R=15.3%` against its
`(15.31,2.95)`. So `fig:frontier` had **two** sources of truth, one of which
was **never rebuildable by any pipeline** and never was going to be, no matter
how many generators or inputs this repository committed. Two further facts
worth carrying: the paper **includes the PDF, not the `.tex`** —
`Sec7_Evaluation.tex:137` is
`\includegraphics[width=\textwidth]{figures/eval_frontiers.pdf}` and no `.tex`
in `ASPLOS27/` `\input`s `eval_frontiers.tex`, so the hand-written file is
tracked but **not on the build path**; and tracking it is nevertheless the
right call, because an untracked hand-written source is unrecoverable while a
tracked off-path one is merely redundant.

**What the closing sentence used to say, and why it no longer holds.** Per
`A6.19` the superseded wording is quoted:

> What remains is therefore a figure pipeline whose every input, generator and
> declared dependency sits in a commit, and whose only unversioned link is the
> last one, in a repository this pass does not own.

That is now false in both halves. The last link **is** versioned, and it is
therefore no longer the only unversioned one — which matters because the
sentence's rhetorical shape invited the reading that closing it would leave
the repository fully versioned. **It does not, and this ledger does not claim
it.** Untracked in `experiments/asplos/` as found today, and out of this
pass's scope:

- **The seven phase-3 records**: `FS_COMPLETE_JOIN_OUTCOME_2026-09-04.md`,
  `FUSED_KNEE_CLOSED_2026-09-04.md`,
  `H1BW_SLICE_BRACKET_OUTCOME_2026-09-04.md`,
  `H2H_REALJOIN_CLOSED_2026-09-04.md`,
  `H2_BYPASS_FIX_OUTCOME_2026-09-03.md`,
  `PAPER_RECONCILIATION_2026-09-04.md` and
  `RECOVERY_CURVE_OUTCOME_2026-09-04.md`. Four of these are cited by rows in
  this ledger and by the index.
- **`analyze_registered_scope.py`**, and the two **byte-identical duplicate
  `.jsonl` re-emissions** — `data/gem5/h1bw_cxlbw_20260904.jsonl` (identical
  to the tracked `h1bw_cxlbw.jsonl`, `cmp` clean) and
  `data/gem5/h1bw_slice_bracket.jsonl` (identical to the tracked
  `h1bw_slice_bracket_20260904.jsonl`). No data is at risk in either;
  committing them would duplicate rather than preserve.
- **`HARNESS_MANIFEST.md`**, **`analyze_archives.py`** and **`.gitignore`** —
  modified rather than untracked, and owned elsewhere.
- Three items not previously named in this paragraph's scope and found today:
  **`data/duckdb_tenant_cat.log`**, **`data/r6e_analyzer_output_2026-09-04.txt`**
  and the whole of **`logs/`** (three `h1bw` console logs).
- **The kernel items, which landed while this list was being written.** They
  were routed here as another worker's concurrent work, checked directly rather
  than inherited, and found untracked; they were committed before this pass
  committed, so the finding is quoted and then corrected, per `A6.19`. What
  this bullet said: "`KERNEL_TEST_AGGREGATE_OUTCOME_2026-09-03.md` is **still
  untracked**, as are the **four** kernel boot logs under `data/kernel/` … and
  `data/kernel/initramfs_init_2026-09-03.sh`. The `linux` submodule prototype
  is likewise in no commit: **17 modified and 4 untracked paths** … the
  handback that routed this item said 19 modified, and **that figure does not
  verify**." The count correction stands as a correction — 17, not 19, at the
  moment it was measured — but **the state it described is gone**. All six
  paths are now tracked, at **`0bd79f8`**, and the `linux` gitlink was advanced
  to `ae43f80e67` at **`9aad8a2`**, so the prototype has a revision for the
  first time and the submodule reports **0 modified**; two built selftest
  binaries (`streaming_lifecycle`, `streaming_memfd`) remain untracked in it
  and are compiler output. This is the second time in one pass that a
  concurrent worker closed an item while it was being written up, the first
  being `F13`'s reachability half, and the pattern is worth naming: **in this
  repository a remaining-untracked list is a measurement with a timestamp, not
  a state.** Re-derive it rather than citing this one.

So the figure pipeline's every input, generator, declared dependency **and
output** now sits in a commit, in one repository or the other. The repository
around it does not, and the list above is what remains.

**Update 2026-09-04, ledger-and-index reconciliation pass.** Two defects
registered, one exposure closed, one closing sentence corrected, and both files
committed --- the first pass in three to commit them, the two prior passes
having correctly refused because their own actions had falsified the text.
`F13` is entered at last, the number having been reserved for it since
`BUILD_PROVENANCE.md` asked; it is **open**, because the gitlink bump at
`065fd80` repaired which simulator this repository names and not whether anyone
can fetch it, and those are separate properties. `F16` is **new and is the
substantive find of this pass**: with all fourteen campaign registrations now
committed, nine of them have no witness to their own precedence beyond their
own dated attestation, and the one timestamp anybody would reach for is proved
inverted. It is logged as a **limit on external verifiability, not a defect in
the claims**, and the argument for that reading --- along with the argument
against it --- is set out in "Status history" rather than asserted here. *(Left
as written, per `A6.19`, this paragraph being the record of what that pass found.
Two of its clauses were superseded later the same day: the figure is **ten**, and
the inverted timestamp is inverted only in **mtime** --- the birth times of the
same pair run in the order the documents assert. Both corrections are in `F16`'s
cell and in the final section of this document.)*

Two things this pass deliberately did **not** do. It did not edit the paper:
the eight registration-claiming passages were read, seven were found
git-witnessed, and the exact wording proposed for the eighth
(`Sec7_Evaluation.tex:143`) is handed back in "Status history" and applied
nowhere. And it did not claim the repository is fully versioned; the list two
paragraphs up is the honest remainder, checked today rather than inherited, and
one figure in the handback that produced it (`linux`, "19 modified") did not
verify and is corrected there.

**Two items closed under this pass while it was writing them up**, both by
other workers, and both corrected in place with the superseded wording quoted
rather than deleted. `F13`'s reachability half closed on a push at
`2026-09-05 01:51:32` KST --- `pr4-work` and all three build tags are on
`origin`, `rev-list --not --remotes` is `0` after a fetch, and a throwaway
clone at `065fd80` now completes `git submodule update --init gem5` --- so the
row is **closed on its own subject** and open only on the superproject push,
which `BUILD_PROVENANCE.md` tracks separately. And the kernel records this
ledger listed as untracked landed at `0bd79f8`, with the `linux` gitlink
advanced at `9aad8a2`. Neither closure was this pass's work and neither is
claimed as it. The methodological residue is the part worth keeping: the
reachability figure was measured before a fetch, and `rev-list --not
--remotes` reads *local* remote-tracking refs, so it reported a push that had
already happened as absent.

The sentence this ledger has carried since 08-28 still holds as written: none
of these is a wrong number and all of them are disclosed. The count of open
items is now **four defects** --- `F4`, `F15`, `F16` and `tab:gem5`'s +H2
column --- plus `tab:fused`'s way-sweep runner and the stale inline table, with
**no number reserved** and `F17` next free. *(That count is superseded by the
pass recorded at the end of this document; it is left as written, per `A6.19`,
and the new figure is given there.)* Only one of those, `F16`, is
**provenance-of-provenance** rather than provenance of a published magnitude:
it is about whether nine registrations can be *shown* to have come first, not
about whether any of them is wrong. It moves no cell in any table above, and
the ledger's 20/20 recomputation and `fig:recovery`'s 63/63 are untouched by
it. It is also the one open item on this list that **cannot be closed by
doing anything** --- no action now creates a witness for an ordering that has
already happened --- which is why it is logged as a limit and why the wording
proposed for `Sec7_Evaluation.tex:143` is a disclosure rather than a fix.

**Update 2026-09-04, publication-and-handback pass.** One defect registered
(`F17`), one closed outright (`F13`, with a sibling-submodule item folded into
it rather than numbered), one binding row added, and the publication of this
repository recorded with its limits. Every hash and figure below was checked
against the repository or against GitHub in this pass rather than carried over
from the handbacks that proposed them; three handed-back figures did not verify
and are corrected where they appear. Nothing outside this file and `INDEX.md`
was edited, and nothing was pushed.

**`F17` is the substantive registration and it is a defect in an instrument, not
in a number.** `AMD_XSOCKET_OUTCOME_2026-09-04.md` proposed it and left the
number here; the reservation convention was honoured exactly, as it was for
`F13`. Two of that campaign's twelve fail-closed gates failed and were
**diagnosed as mis-specified rather than converted to passes**, and the row
above is written to record that behaviour as well as the fault. The campaign's
own headline is held to the same standard and is worth carrying precisely:
Outcome A failed on the **lower (faster-than-baseline) edge of the measured
noise band by 2.8x10⁻⁴** under a rule that was two-sided by design, so the
registered verdict is **C --- INCONCLUSIVE** and the campaign is **NOT
CERTIFIED**; the secondary 4096 KB cell returns A cleanly and was **not** pooled
or promoted, the primary cell having been designated before any data existed.
Neither 4096 KB cell shows a residual tax --- Outcome B is nowhere near firing
--- so `C` is a verdict about the resolution of the instrument, not about the
existence of an effect. **The registration itself is witnessed by git**, which
is the point of contact with `F16`: `AMD_XSOCKET_PREREG_2026-09-04.md` and its
runner and analyzer were committed at `d65f768`, `2026-09-05 01:26:55` KST, and
its pre-launch addendum 0 at `c7b8d1c`, `01:33:10`, against a campaign start of
`2026-09-04 16:34:20 UTC` = `01:34:20` KST --- **7 min 25 s** and **70 s** ahead
of the first run respectively, with the data landing at `c34305f` an hour later. That makes it the best-witnessed registration in the project after
`H1BW_SINGLECORE`, and it is a **fifteenth** campaign registration rather than a
change to `F16`'s fourteen: `F16`'s nine attested-not-witnessed registrations
are unaffected, and none of its arithmetic moves.

**The repository is published, and what that did and did not achieve is worth
stating separately.** `origin/main` on `https://github.com/jaewan/DutyFree.git`
moved `73f0332f6c → 322c9564ee`, **103** commits, confirmed **server-side** by
`git ls-remote` and not from this clone's remote-tracking refs, per `F13`'s
standing lesson.

- **Content reproduces, and it was re-derived here rather than accepted.** The
  published commit's tree was extracted and the stdlib-only
  `analyze_registered_scope.py` run inside it: **63 fused records** (45 `kn` +
  18 `kb`), all `completed`, and **every number `fig:recovery` plots** comes
  back to the digit printed in this ledger's own row above --- `R(h2)` 89.44 /
  87.69 / 84.51 / 81.95 / 82.33 / 67.14 / 56.84 %, `R(cat4)` 89.26 / 88.20 /
  87.79 / 87.45 / 87.26 / 86.25 / 86.31 %, `wb` tax 1.4679 / 1.5012 / 1.5141 /
  1.5186 / 1.5100 / 1.5223 / 1.5477x, `realized_table_mb` equal to requested at
  all seven sizes. One presentational discrepancy is recorded and **not**
  repaired, this pass not restructuring rows: the `fig:recovery` row's `cat4`
  tenant-cost list names six values where the analyzer prints seven, omitting
  6.0 MB's **−18.95%**. The six it prints are correct.
- **The figure PDF could not be rebuilt on this host, so rendering is unproven
  while content is not.** `python3` is **3.14.4**, there is no `pip` or `pip3`
  on `PATH`, `import ensurepip` raises `ModuleNotFoundError`, and `matplotlib`
  is absent. `experiments/asplos/requirements.txt` declares the pin the figures
  were verified under (`matplotlib==3.11.1`), which is the right thing to have
  declared and is **not installable here**. So the earlier note that the
  dependency exposure is "closed" holds in the sense that the pin is recorded
  and colocated with the generators; it does not mean a reader on this
  interpreter can regenerate the PDF. The two tracked PDFs in the paper tree
  remain the only evidence of what the figures look like, and the standing
  observation that nothing enforces agreement between them and their inputs is
  unchanged.
- **The push bypassed branch protection on `refs/heads/main`, and this is
  recorded as a fact about how the artifact was published rather than as a
  complaint.** The remote carries an **active** repository ruleset, "Protect
  Main" (id `16069337`), whose rules include `update` and `pull_request` with
  one required approving review. GitHub's own rule-suite record for this push
  --- id `3950722155`, actor `jaewan`, `before_sha` `73f0332f6c`, `after_sha`
  `322c9564ee`, `ref` `refs/heads/main`, `pushed_at` **`2026-09-05T02:18:06+09:00`**
  --- reports `result: bypass`, with `update` failing on "Cannot update this
  protected ref." and `pull_request` failing on "Changes must be made through a
  pull request." The credentials carry admin bypass, so the two failed rules
  were logged and overridden rather than enforced. It is the **only** rule-suite
  record the API returns for this repository, so this is the one direct push
  evaluated against the ruleset. The user has since accepted direct pushes as
  policy, so this is how the artifact is published and not an accident; it is
  recorded here because a reader reconstructing the publication history from
  GitHub will find `Bypassed rule violations` against `refs/heads/main` and
  should find the same fact stated in the provenance record.
- **At the instant of publication `.gitmodules`' `branch` keys were wrong**, and
  the fix is still unpublished. `git show 322c956:.gitmodules` names `branch =
  main` for `linux`, whose pin lived only on `pr4-work` --- `main` on that
  remote is the bare base `b9f60fafda72` --- and carries **no** `branch` key at
  all for `gem5`, which git defaults to the remote `HEAD`, also `main`. Both
  keys now read `pr4-work`, fixed at **`6d6109e`**, which is a descendant of
  `322c956` and **not** an ancestor, so it is not in the published tree. The
  keys are inert for plain `git submodule update`, which uses the recorded
  gitlink; they matter for `--remote` and for a reader consulting `.gitmodules`
  to learn which branch to follow, and `BUILD_PROVENANCE.md` records that the
  `linux` key was exercised with a real `--remote` fetch rather than asserted.

**The dating convention, recorded explicitly so it stops recurring.** This
host's clock is **KST (UTC+9) and runs a day ahead** of the project-local
`UTC-7` by which every record in this directory is dated. Measured here today:
**54** of today's commits carry author dates reading `2026-09-05` while the
records inside them read `2026-09-04`; a further seven --- `e338400` through
`322c956` --- carry explicitly set `-0700` dates at exact one-minute intervals
that already read `2026-09-04`; and five (`b4ac57c` through `6fa71f5`) read
`2026-09-04 +0900`, which is project-local `2026-09-04` as well. **Rewriting
the skewed author dates is foreclosed, and not for reasons of taste.** Of the
32 commit hashes these two files cite by name, **22** are among the 54: they
are freeze citations, and a rewrite would change every one of them. It would
invalidate exactly the provenance it would appear to tidy, which is the same
argument `F16` makes about creating witnesses after the fact. Date records
project-local, label wall-clock instants KST when quoting them, and leave the
commit metadata alone.

**Three handed-back figures did not verify and are corrected rather than
propagated.** They are recorded because a handback that is right in substance
can still carry an unchecked number, and this ledger's method is to recompute.
(1) The document count was handed back as **`215 → 217`**; `INDEX.md` read
**`216`**, not 215, so the transition applied there is `216 → 217`. The `217` is
right, re-derived rather than trusted. (2) The date skew was handed back as
**43** commits; it is **54**. (3) The `.gitmodules` fix was handed back as
landing **"90 seconds"** after publication; it did not, and the interval cannot
be taken from this repository's own history at all. GitHub's server-side
`pushed_at` is `02:18:06` KST and `6d6109e` is committed at `02:25:42`, which is
**7 minutes 36 seconds**, while the local reflog entry for the same push carries
an *overridden* timestamp (`02:26:00`, identical to `322c956`'s own explicitly
set `-0700` commit date) that reads **eighteen seconds later** than the fix it is
supposed to precede. The ordering is not in doubt --- it is provable from the
commit graph, `6d6109e` being a descendant of `322c956` --- but the duration is
not measurable locally, and the reflog is the wrong instrument for it here.

**The `logs/se_chi_h1bw_sc/` citation gap closed while this pass was writing,
and it is described as found rather than as routed.** It was checked directly:
at the start of this pass `git ls-files logs/` returned two files and the whole
of `logs/se_chi_h1bw_sc/` was untracked, so the artifacts the `tab:h1bw` row
cites --- `stats.txt`, `config.ini`, `MANIFEST.json`, `DONE.json` --- were
unobtainable. They landed at **`7606f84`**, `2026-09-05 03:06:26` KST, as the
machine-readable subset and nothing else: **45 files**, five classes over the
nine cells (`console.log`, `stats.txt`, `config.ini`, `MANIFEST.json`,
`DONE.json`), which is exactly the need tuple `analyze_h1bw_singlecore.py`
declares, so the selection is bound to the certification rather than to taste.
`console.log` is in the set because gates G6 and G7 read the
`AGGBW_WINDOW_OPEN`/`CLOSE` lines and nothing else carries them. Still
untracked in those directories: **54** files --- `citations.bib`, `config.json`
and four `fs/` sysfs snapshots per cell. So the `tab:h1bw` row's artifact
citations now resolve for a reader with a clone, which they did not this
morning; the row is otherwise unchanged and its certification is unaffected.
Two items closed under a concurrent worker during this pass alone --- this one
and the `linux` pin folded into `F13` above --- after two closed the same way in
the previous one, which is why the instruction below is worded as it is.

**The repository is not fully versioned and this ledger does not claim it is.**
Re-derived here today, and the earlier list is corrected on three points rather
than cited: the **seven phase-3 records** are all tracked now, and so are
**`analyze_registered_scope.py`** (at `673eb73`, which is why this pass could
run it out of the published tree) and **`data/r6e_analyzer_output_2026-09-04.txt`**.
What remains out, as measured in this pass:

- The two **byte-identical duplicate `.jsonl` re-emissions**, re-checked with
  `cmp` and still identical: `data/gem5/h1bw_cxlbw_20260904.jsonl` against the
  tracked `h1bw_cxlbw.jsonl`, and `data/gem5/h1bw_slice_bracket.jsonl` against
  the tracked `h1bw_slice_bracket_20260904.jsonl`. No data is at risk in
  either; committing them would duplicate rather than preserve.
- **`data/duckdb_tenant_cat.log`**, and the whole of **`experiments/asplos/logs/`**
  (three `h1bw` console logs).
- **`PAPER_NUMBER_RECONCILIATION_2026-09-01.md`**, untracked at the repository
  root.
- **80 untracked paths under `benchmarks/` and `tests/`** with directories
  collapsed, **106** individual files.
- The 54 files under `logs/se_chi_h1bw_sc/` named above.

**That list is a measurement with a timestamp, not a state**, and this pass is
another demonstration of why: `analyze_registered_scope.py`, the phase-3 records
and the r6e analyzer output left it between one pass and the next, and
`logs/se_chi_h1bw_sc/`'s subset landed during this one. Re-derive it rather than
citing this paragraph.

**One item is routed on and deliberately not applied**, `PAPER_RECONCILIATION_2026-09-04.md`
being another worker's document: its §7 `U3` row and its "Unlocatable claims"
list still read "**Six remain** … U1, U2, U3, U5, U6, U8" and still describe
`U3` as the one where the established response *would* apply. It has applied.
The wording handed back by `AMD_XSOCKET_OUTCOME_2026-09-04.md` §10, quoted here
so it is not lost, per `F11`:

> **`U3` --- resolved 2026-09-04** by `AMD_XSOCKET_OUTCOME_2026-09-04.md`, and
> resolved by the established response: an unbacked claim replaced by a
> measured campaign on matched apparatus. `Sec3:152` no longer asserts an
> unmeasured cross-socket result. **Five remain**: `U1`, `U2`, `U5`, `U6`,
> `U8`. Note for the count: `U3` is the item the earlier pass twice identified
> as the one where "the established response would apply", and it did apply ---
> though the campaign it produced is `NOT CERTIFIED` and its verdict is
> `INCONCLUSIVE`, so the draft now carries a **measured, narrowed** claim
> rather than a confirmed one.

**The open count.** The sentence this ledger has carried since 08-28 still holds
as written: none of these is a wrong number and all of them are disclosed. Open
now: **four defects** --- `F4`, `F15`, `F16` and `F17` --- plus `tab:gem5`'s +H2
column, `tab:fused`'s way-sweep runner and the stale Sec5 inline table. `F13` is
**closed**, subject and remaining ground both, and no number is reserved; the
next free defect number is **`F18`**. Two of the four are not repairable by
doing anything: `F16`, because no action creates a witness for an ordering that
has already happened, and `F17`, whose remedy is a convention for future
pre-registrations and whose own campaign is closed. Neither moves a cell in any
table above; the ledger's 20/20 recomputation and `fig:recovery`'s 63/63 stand,
the latter now re-derived from the published tree rather than from this working
copy.

**Correction to the paragraph above, minutes after it was committed, and it is
the fourth instance of the same pattern in two passes.** A second publication
landed while this pass was committing: `origin/main` moved `322c9564ee →
a0cfe302d2`, **11** commits, at `2026-09-05T03:20:01+09:00` KST. Three clauses
written above are now false, and per `A6.19` they are quoted rather than deleted.

> At the instant of publication `.gitmodules`' `branch` keys were wrong, and
> **the fix is still unpublished** … Both keys now read `pr4-work`, fixed at
> `6d6109e`, which is a descendant of `322c956` and **not** an ancestor, so it
> is **not in the published tree**.

> It is the **only** rule-suite record the API returns for this repository, so
> this is the one direct push evaluated against the ruleset.

What is true now, re-measured rather than inferred: `git show
origin/main:.gitmodules` names `branch = pr4-work` for **both** submodules, so
`6d6109e` is published and the stale-key exposure is closed in the published
tree; `7606f84`'s `logs/se_chi_h1bw_sc/` subset is published with it, so the
`tab:h1bw` row's artifact citations now resolve for a stranger and not merely for
a reader of this working copy; and the published `linux` gitlink is
`6a7e5b09bd8b`, which the 02:58:56 push put on the submodule's `pr4-work`, so the
pin folded into `F13` above is fetchable from the published tree as well.

**The bypass finding is strengthened rather than weakened, which is why it is
worth correcting precisely.** There are now **two** rule-suite records for
`refs/heads/main` and both read `result: bypass` --- `3950722155`
(`73f0332f6c → 322c9564ee`, 02:18:06) and `3951418509` (`322c9564ee →
a0cfe302d2`, 03:20:01) --- each failing the same two rules of the "Protect Main"
ruleset. So direct pushes with admin bypass are not a single event but the
established practice, which is what the user's decision to accept them as policy
means in the record.

**What does not change.** The two-commit publication does not touch the content
finding: the `fig:recovery` reproduction above was run against `322c9564ee`'s
extracted tree and every figure in it stands, `a0cfe302d2` being a superset of
it. The matplotlib limit is unchanged --- still no `pip` and no `ensurepip` on
this interpreter --- so rendering remains unproven. And the repository is still
not fully versioned: `main` is ahead of the published tip again, this pass's own
two commits among the reasons, and the remaining-untracked list two paragraphs up
was re-measured after this push and is unchanged by it. **The instruction
stands and this is now its fourth demonstration in two passes: a
remaining-untracked list, an unpushed-commit count, and a publication state are
each a measurement with a timestamp, not a state.**

**Update 2026-09-04, birth-time re-audit and evidence-preservation pass.** No
defect registered, none closed, no number moved anywhere in this ledger or in the
paper. What this pass did is **correct four passages of precedence reasoning,
three of them in this file and one in `INDEX.md`, all four resting on the same
method error**, and record one convention. Every figure below was measured in
this pass; the two handbacks that proposed them were checked rather than trusted,
on the strength of the previous pass having found three of its own handed-back
figures wrong.

**The error, stated once because it produced all four.** A directory's mtime is
the time of the last entry written into it, which is a property of the *harness*
and not of the campaign. `FUSED_KNEE`'s gem5 output directories are populated at
startup, so their mtime is within half a second of launch; the `h1bw_*` harness
writes `MANIFEST.json` and `DONE.json` when a cell finishes, so its mtime is
completion. **The same `stat` gave the right answer on one campaign and an answer
48 minutes wrong on the other, and neither was checked against anything in band.**
Both corrections are in "Status history" above, with the superseded wording quoted
per `A6.19` — which this pass applied to its own text from earlier the same day,
the rule being no weaker against the author than against anyone else.

**What did not verify, and it is one thing rather than a figure.** Every
substantive measurement in both handbacks reproduced exactly: `H1BW_SLICE_BRACKET`'s
in-band `started 09:11:27` against `e35cfa3` at `01:37:06` the next morning
(**16 h 25 m 39 s**); `FB_ORACLE_PREREG` §"Arms" registering `qui`/`wb`/`h2`/`fbo`
verbatim, which makes this ledger's own "named as an arm by no registration"
false; the `/tmp/fbo_validate` pair's in-band banners at `13:06:48` and `13:21:50`,
**1 d 12 h 25 m 56 s** before `e2b1b90`; `COMPLETE_JOIN`'s birth times `23:48:22`
and `05:02:16` against inverted mtimes `05:32:58` and `05:32:53`; the registration
birth preceding r5's fifteen-arm launch banner by **4 m 21 s**; the bulk-pass range
of **28.9 s to 41 min 08 s**, whose two endpoints are `H1BW_SINGLECORE` and
`SILICON_E2E` and which was re-derived campaign by campaign rather than accepted;
`/tmp/kn_cat4_t2.0_s1` birth `22:58:38.127` against mtime `22:58:38.532`; all 45
`kn_*` banners at `22:58:38` and all 18 `kb_*` at `01:33:02`, the latter
**2 h 34 m 25 s** after `eb20d93`; `eb20d93` unsigned; `artifacts/fused_knee/` at
65 evidence files and 228,846 B against 504 digested originals; `9 of 30`
committed `.jsonl` carrying an in-band timestamp in two schemas; `−18.95%`;
`h1bw_singlecore.jsonl`'s `started 21:00:20–21:00:36` and earliest `ended 21:48:07`
against `b4ac57c` at `21:22:22` and `6fa71f5` at `22:07:17`. **One item did not
survive, and it is the universe rather than a number.** The re-audit counts
"**all sixteen registrations carrying a precedence claim**" and its arithmetic is
internally exact for the set it names — `F16`'s fourteen plus `H1BW_SINGLECORE`
plus `AMD_XSOCKET`, giving 4 witnessed / 11 unwitnessed / 1 indeterminate, all
three of which reproduce here. But `INDEX.md`'s curated table now carries
**seventeen** `*_PREREG_*` rows, and the seventeenth is **`FUSED_KNEE_PREREG`**,
added at `INDEX.md:149` by `f425779` a few hours earlier — which is the row the
same handback calls the strongest of all on in-band evidence. It was missed
because it is the one `*_PREREG_*` row that carried no freeze citation, that
citation convention having been introduced for the bulk pass and never applied
backwards to a registration from 2026-08-29. **So the counts are right and the
denominator is one short**; `INDEX.md` now tallies **seventeen** and gives
`FUSED_KNEE_PREREG` the freeze citation it lacked. One smaller slip, corrected
where it appears rather than argued: `eb20d93` has **502** ancestors, not 503 —
`git rev-list --count` includes the commit it is given.

**`F16` moves in both directions and the row is better founded than when it was
written.** Within its fourteen: **10 unwitnessed, 3 witnessed, 1 indeterminate**,
against the 9/5 first published. `H1BW_SLICE_BRACKET` was miscounted as witnessed
and its own cell had already conceded the substance; `FB_ORACLE` moves to
indeterminate because the witness rested on absence of data and data exists,
uncommitted, on tmpfs. The three that survive — `DUCKDB_MMAP_SE_H2`,
`AGGBW_WINDOW`, `IVF_FLAT_SILICON` — survive **for a reason the row now states
explicitly**: their witness is a committed registration plus the absence of any
data at all, which is a forward-looking guarantee that never consults a timestamp,
so this error class cannot reach them. Against those two losses, the same audit
found that the birth times of every bulk-pass registration checked **precede
their campaigns' in-band launches**, by 29 seconds to 41 minutes, and that the
mtime pair this row offers as its inversion proof inverts only in mtime. The
filesystem therefore **corroborates** the ten attestations and merely cannot show
a reviewer, which is what "a limit on external verifiability, not a defect in the
claims" was asserting on an argument and now asserts on a measurement.

**One overclaim of this ledger's own is withdrawn.** The `Sec7_Evaluation.tex:238`
bullet called `FUSED_KNEE`'s registration "externally corroborated". It is not:
the banner and the commit date come from the same host clock, a git author date is
settable, and `eb20d93` is unsigned. What is true, and is what the bullet now
says, is that the launch time is **generated by the simulator rather than asserted
by the author**, and that falsifying it would mean forging 45 coherent logs.
Weaker than external attestation, far stronger than a document's own say-so, and
the strongest form the property takes anywhere in this project — which is why the
`fig:recovery` caption's "registered before the runs" still should **not** be
softened, and why `INDEX.md`'s "best-witnessed" ranking now puts `FUSED_KNEE`
first and `H1BW_SINGLECORE` fourth. That ranking, and the criterion it is taken
on, are stated in `INDEX.md` rather than here.

**Two things handed back rather than applied**, both because this pass owns
neither file. `H1BW_SINGLECORE_PREREG_2026-09-04.md` says "frozen before launch"
at line 887 and "stated before launch" at line 44, and both are false about run
start. **The recommendation is an addendum and not a rewrite** — it is a sealed
registration and `A6.19` governs — and the addendum should be more precise than a
flat retraction, because the document's position is better than "wrong": its own
**birth time is `20:59:51`, 29 seconds before the first cell launched at
`21:00:20`**, so the file existed before launch and only its *freeze*, in the
sense this corpus uses the word, did not. Its **mtime is `21:07:00`**, so it was
still being written seven minutes into the runs, and the commit followed at
`21:22:22`. Suggested substance: the design was on disk before launch, the commit
was not, no cell had reported a statistic when the commit landed, and the
campaign's own outcome document already says exactly that. The
`FUSED_KNEE_RUNLOG_PROVENANCE_2026-09-04.md` handback also asks whether the 48.4
MiB of `stats.txt` and 19.4 MiB of `config.ini` should be committed so a reviewer
can rebuild the two JSONL archives rather than trust `acc722a`'s extraction; that
reverses a documented decision in `acc722a` and is **not this ledger's call**
either. Both are recorded here so they are not lost, per `F11`.

**One convention registered, folded into `F17` rather than numbered.** Standardise
in-band `started`/`ended` in every committed per-run record. It sits beside
`F17`'s two prevention notes because all three are the same kind of item: nothing
measured is wrong, and the remedy is what the next harness does rather than a
patch to anything already recorded.

**The open count does not change.** Open: **four defects** — `F4`, `F15`, `F16`
and `F17` — plus `tab:gem5`'s +H2 column, `tab:fused`'s way-sweep runner and the
stale Sec5 inline table. `F13` remains closed, no number is reserved, and the next
free defect number is still **`F18`**. `F16` stays open **on the same ground and
with a different count**: it is still the one open item that cannot be closed by
doing anything, and it is now the one whose evidence cuts both ways. Nothing on
that list moves a cell in any table above; the ledger's 20/20 recomputation stands
and `fig:recovery`'s 63/63 stands with one more value printed in its row than
before.

**State at the end of this pass, as a measurement and not a state.** `origin/main`
is at `a0cfe302d2`; `main` is **four** commits ahead of it — `f425779`, `5584644`
from the previous pass and `3ed6ff0`, `ebfd511` from the evidence-preservation
pass — plus whatever this commit adds, and nothing was pushed. The
remaining-untracked list four paragraphs above the previous section's end was
re-derived: **167** untracked paths repository-wide, with
`FUSED_KNEE_RUNLOG_PROVENANCE_2026-09-04.md` and the 66 paths under
`artifacts/fused_knee/` having left it at `3ed6ff0`, and the working tree also
carries uncommitted modifications to tracked files belonging to other workers,
which is why this pass committed with `--only` and explicit paths. **Fifth
demonstration of the same instruction in three passes.** One thing this pass adds
to it: the evidence-preservation pass's own commit `ebfd511` exists because
`3ed6ff0`'s handback listed an item that `f425779` had closed between the two
being written, so the pattern is now symmetric — this ledger has had items closed
underneath it by other workers, and it has closed items underneath them.

**Update 2026-09-04, non-power-of-two set count pass.** One defect registered
(`F18`), one cell of another ledger's defect closed by measurement, one sealed
registration given an addendum, and **no number moved in this ledger or in the
paper**. The source is `NONPOW2_SETS_MEASURED_2026-09-04.md`, committed with the
guard at superproject `c3101b2` and gem5 `c030d776ee`. Every figure below was
re-derived in this pass; three did not survive, and they are given before the
findings rather than after, because two of them bear on how this record should be
read.

**What did not verify.** (1) **The `1,825` differing-line figure is on a
different counting convention from the two rows beside it.** That record's §1
table gives `A vs B` as **5** differing lines and `C vs D` as five host-side
plus five `m_allocsByWay` buckets, i.e. **10** — both of which are
`diff | grep -c '^<'`, one side of the diff. `A vs D` is given as **1,825**,
which is `diff | grep -c '^[<>]'`, *both* sides. Re-measured on the neighbouring
rows' convention it is **914 changed lines**, or **956 distinct stat names**. The
verdict is untouched — B and D request identical bytes and differ on hundreds of
simulated quantities while B and A differ on none — so this is a figure
correction and not a result correction, and `F18` above carries the corrected
number. Every other figure in that table verified exactly, including the one the
argument rests on: **2,014 simulated quantities bit-identical between A and B**,
from a 2,019-line stat universe less the five host-side lines. (2) **The two
repositories are not both level with their remotes, and the record itself is
published in two versions.** gem5 is level: `origin/pr4-work` and the submodule's
`HEAD` are both `c030d776ee`, zero unpushed. The superproject is **diverged** —
`main` is `c944671` and `origin/main` is `c3101b2`, and the two are **siblings off
`5f29346`**, not one ahead of the other. They differ by 62 lines in
`NONPOW2_SETS_MEASURED_2026-09-04.md`: the local commit carries an **Addendum 1**
that the published one does not, which has the shape of an amend made after the
push. **The unpublished addendum is not filler and is the reason this matters** —
it corrects §2's "one affected run directory in the whole committed tree" to two,
and it records the guard's **first observation in the field**: another worker's
`diag_duckdb_store_localize/h2_s1_diag`, launched at the r5 geometry four minutes
after the guarded binary was linked, by someone who knew nothing about that pass,
whose console log now carries `REALIZED CAPACITY 5242880 B (66.7% of
configured)`. So a reader of the *published* tree gets the weaker version of the
strongest evidence in the record, and `main` cannot be fast-forwarded onto
`origin/main` without a decision that is not this pass's to make. Recorded, not
repaired: rewriting another worker's commit is exactly what `F13`'s process
lesson forbids, and publication is being sequenced elsewhere. (3) The
uncommitted-path figure was handed to this pass as **~127**; measured here it is
**168 untracked paths plus 15 modified tracked files, 183 in all**. Nothing turns
on it — it is the reason this pass committed with `--only` and explicit pathspecs
— and it is the sixth instance of the standing instruction two paragraphs up.

Two figures drifted rather than failed, and the record says so itself. The audit
universe was **161** `config.ini` when its §2 ran and is **166** now; re-run in
this pass it reports **one** affected distinct geometry across **four** run
directories, of which two are that pass's own probe cells, leaving the **two** its
Addendum 1 names. Every L1I, L1D, L2, snoop-filter and directory structure is
clean at every slice count. The instruction that generalises is the one that
addendum draws: `audit_nonpow2_sets.py` reads run directories that `.gitignore`
excludes, so its count is a measurement and not a property of a commit, whereas
its *campaign* table rests on committed `.jsonl` and committed launchers and does
not have that weakness.

**How `F9.4` is dispositioned, since this pass closes one cell of it and not the
defect.** `F9.4` is `W4.3_PROVENANCE_LEDGER_2026-08-23.md`'s number and its
disposition is recorded here rather than owned here.

- **The r5 cell closes by measurement.** It stood as *"derived from source, not
  measured"*; `--l3_size=7680KiB --l3_assoc=20` is now measured bit-identical to
  `--l3_size=5MiB --l3_assoc=20` on 2,014/2,014 simulated quantities, against a
  same-bytes power-of-two control that differs on 914 lines.
- **`W7 A1` is *not* closed by this pass and does not need to be, because it
  reaches no published claim.** This was checked rather than assumed, the
  handback having asked for exactly that. Its shortfall is worse than r5's —
  `32MiB`/20 gives 26,214 sets, 16,384 reachable, **20,971,520 B realized,
  37.5% short**, re-derived here. Three things make it unpublished rather than
  undisclosed: `W7.2_A1_SIZING_2026-08-24.md` was written *"while the 24 morsel
  cells are still running and before any of them has produced a stats file"*, so
  the disclosure precedes the data it describes; `W7_OUTCOME_2026-08-24.md`
  labels every A1 row `[F9.4]` and **re-scopes its own verdicts to the realized
  geometry** — *"a null at 20 MiB / 40× / 40%. P1 as registered is not
  tested"* — which is the honest form of the correction rather than a footnote;
  and `REVIEWER_STATE_2026-08-24.md`'s `N6` already carries it as *"disclosed and
  labelled everywhere"*. Against the paper, read here without editing anything:
  there is **no 32 MiB LLC claim in any `.tex`**, none of W7's measured values
  (97.685, 100.192, 101.193, 66.757) appears, and the only `20~MiB` in the draft
  is `Sec7:37`'s *"20~MiB at four readers"*, which is four 5 MiB slices in the
  `H1BW` campaigns and unrelated. W7 A1 also has **no committed data** under
  `data/gem5/` and no surviving run directory.
- **The two `tab:sens` rows are disclosed in the published artifact itself**,
  which is the strongest position of the three. `Appendix.tex` labels the column
  *"LLC assoc. (realized LLC, WSS/LLC)"*, prints *"8-way, 4 MiB (66%)"* and
  *"12-way, 3 MiB (88%)"*, and its caption states outright that *"Ruby quantizes
  LLC sets to a power of two, so at a requested 5 MiB the 8- and 12-way rows
  realize only **4 MiB** and **3 MiB**"* and that the axis *"therefore spans a
  joint associativity and capacity change"*. Re-derived: 20.0% and **40.0%**
  short, the 12-way row being the worst instance anywhere in the project.
- **`F9.4` does not close as a class, and the guard is why not.** The guard
  *reports* and does not *repair* — `addressToCacheSet()` still indexes
  `2^floorLog2(sets)` — so any future non-power-of-two geometry loses exactly the
  same capacity and the arithmetic remains live. What changed is that it can no
  longer do so silently. Closing `F9.4` wholesale on the strength of this pass
  would be the `F17` mistake in a new place: converting a diagnosis into a pass.

**Two findings recorded because they are arguments and not bookkeeping.** The
first is that **a void number here voided an argument**. Realized `victim/LLC` is
**0.518**, identical to r3's, and r5's own Addendum 1 explains its fallen victim
tax *by* a shrunken victim ratio — so it explains an effect with a cause that
never occurred, and the correction removes an explanation rather than adjusting a
value. The second is the **direction of the surviving supersession**: r5 is r3's
cache geometry on both ratios, so what r5 genuinely added over r3 is the complete
join and tuples/s in place of a truncated join and IPC. **The supersession holds
for the workload and not for the geometry**, and a reader who takes r5 as "r3
with the cache fixed" has it exactly backwards.

**One gap this pass found in the safety argument for the paper, and it closes on
a stronger ground than the one offered.** The record's first reason that
`Sec7:42-44` is unaffected is that r3 *"requests `5MiB` at 20 ways = 4096 sets
exactly"*. **That is not verifiable from an artifact.** `l3_size_bytes` appears in
exactly one committed `.jsonl` in this directory — `r5_runs.jsonl` — and
`rj3_runs.jsonl` carries no such field; no r3 launcher is committed, which is
`F10`'s own subject; and no r3 run directory survives under `gem5/logs/`. r3's
requested geometry therefore rests on prose in `H2H_REALJOIN_PREREG_2026-09-01.md`
and `MODEL_SILICON_CAT_CALIBRATION_2026-09-01.md`. **The claim is safe anyway, and
twice over.** *(a)* `5MiB`/20 and `7680KiB`/20 **realize the same 5,242,880 B**,
which is the whole content of §1's measurement — so the calibration record's
derived quantities are exact whichever of the two r3 requested: *"0.25 MiB per
way (5 MiB / 20)"* and *"2.59 MiB victim / 5 MiB LLC = 51.8%"* hold either way,
and 2,713,600/5,242,880 = 0.518 re-derives here. *(b)* The normalization is a CAT
**way** fraction, `w/20` against `w/15`, and way masking grants exactly
`4096 × w × 64` B for every `w` regardless of the set-count quantization, so the
axis is exact at all twelve widths. Reason *(b)* alone carries it and does not
depend on r3's request at all. **Worth stating for the corpus**: the paper is the
only artifact in this chain that reported realized values, and it says so at
`Sec7:29-31` — *"We report realized cache geometry and verified placement rather
than requested values"* — on the one quantity where the shortfall was real.

**What this pass edited and what it handed back.** Three files: this ledger,
`INDEX.md`, and an **Addendum 8** to `FS_COMPLETE_JOIN_PREREG_2026-09-02.md`.
That last is a sealed registration with seven prior addenda, so it is appended to
and not rewritten, per `A6.19`. The handback named one sentence in it —
*"10 MiB here against 7.5 MiB there"*, correctly, since realized it is **10 MiB
against 5 MiB, exactly 2×** — and the addendum covers **five** further places in
the same document that inherit the reading, including its geometry table, whose
`r5` column becomes **identical to its own `r3` column** once realized, and a
causal sentence at its line 237 attributing r6e's lower eviction pressure to
*"33% more capacity"* when the true figure is 100%. That last is the same shape of
error as item 6 in r5's outcome and is the reason the addendum was not confined to
the sentence handed back. Nothing under `/home/domin/STREAMING_Paper/` was
modified — the paper was read to check W7 A1's reach and `Appendix.tex`'s
disclosure, and read only. Nothing under `gem5/src/` was touched. **And one
explicit non-action, recorded so that nobody helpfully undoes it:
`run_complete_join.sh` must not be corrected.** It is the transcript of what r5
actually ran, and changing `7680KiB` there would make it reproduce a different
run — bit-identically, as it happens, which is precisely what would make the
substitution invisible. `F13`'s lesson is that a launcher's whole value is that it
reproduces its run; a corrected launcher is a claim, not a transcript.

**The open count.** The sentence this ledger has carried since 08-28 still holds
as written: none of these is a wrong number and all of them are disclosed. Open
now: **five defects** — `F4`, `F15`, `F16`, `F17` and `F18` — plus `tab:gem5`'s
+H2 column, `tab:fused`'s way-sweep runner and the stale Sec5 inline table. `F13`
remains closed, no number is reserved, and the next free defect number is
**`F19`** *(superseded within the day — see the pass below; it is now `F20`)*.
`F18` is open on **one** of its three components, the gate that read a
requested value, and that component is open for a reason worth keeping distinct
from the others: it is not waiting on a decision or a patch but on an
**artifact** — no output carries realized capacity for any run already completed,
and the guard supplies it only from `c030d776ee` forward. Three of the five open
items are now in the same family: `F17` and `F18`(2) are both gates that could not
observe the quantity in their own claim, and `F16` is the absence of a witness
rather than of an instrument. Nothing on the list moves a cell in any table above;
the ledger's 20/20 recomputation and `fig:recovery`'s 63/63 stand, and
`fig:frontier`(a) stands with a corrected description of the machine that produced
it.

**Update 2026-09-04, m5op `%rax` clobber pass.** One defect registered (`F19`),
one amendment appended to a sealed registration, and one claim of this ledger's
own index withdrawn. The source is `M5OP_RAX_CLOBBER_AUDIT_2026-09-04.md` at
`964fbf1`. **The previous pass's own report is corrected first, because its
subject has been resolved and one of its sentences is now false.** Quoted rather
than deleted, per `A6.19`:

> **The two repositories are not both level with their remotes, and the record
> itself is published in two versions.** … The superproject is **diverged** —
> `main` is `c944671` and `origin/main` is `c3101b2`, and the two are **siblings
> off `5f29346`** … So a reader of the *published* tree gets the weaker version
> of the strongest evidence in the record.

**That is no longer true, and it was resolved in the better of the two available
ways.** `origin/main` is now `964fbf1`, `main` equals it, and the history reads
`c3101b2` → `93061b0` → `57dd8e5` → `8da6499` → `964fbf1`. The divergence was
**rebased rather than amended away**, so Addendum 1 landed as its own commit
`93061b0` ("Non-power-of-two sets: the guard's first field observation") and the
guard's field observation is now published. **This pass's predecessor commit was
`826328c` and is now `57dd8e5`**; the content is identical and the hash moved in
that rebase, which is worth stating because the previous report gave the old one.
**Both repositories are level this time and it was checked, not accepted**: gem5
is at `503591ae` on `pr4-work`, equal to its remote; the superproject is at
`964fbf1`, equal to its remote. The lesson stands and is the same one, in the
other direction: **a publication state is a measurement with a timestamp.**
Recording the divergence rather than repairing it was right, and what repaired
it preserved the evidence.

**What did not verify.** Three items, and the third is the one that matters.

1. **§3.1's "All 10 sites in this binary … are SAFE" is wrong, and the same
   document's §6 says so.** Re-running the committed instrument here on
   `cxl_join_bench.gem5` (`cac9e27a`, re-hashed) returns
   `{'SAFE': 9, 'UNSAFE': 1} (10 sites)`. The tenth is `0x40ced1`, the
   flush-behind loop — the very defect §6 is about. **The conclusion is
   untouched and the clause that carries it is exact**: the three sites on r5's
   executed path (`0x4120c0` `set_streaming`, `0x412469` `reset_stats`,
   `0x412c59` `exit`) *are* all SAFE, verified individually here, and the UNSAFE
   site is in a `--policy fbo` branch r5 never enters. So this is a
   sentence over-claiming, not a verdict moving. Related and worth flagging so a
   reader does not conflate them: **§7.2's table reports 14 sites for a binary it
   also calls `cxl_join_bench.gem5`**, which is the *rebuilt scratch* binary from
   the current, heavily-modified source — not the 10-site `cac9e27a` of §3.1.
2. **The FS disk images and their manifests are not committed.** §3.5 and §10
   both say "the **committed** disk images", and the images are at
   `/home/domin/.cache/gem5/w8-fs-e2e-r6{b,e}.img`, 257 MB each, **outside the
   repository altogether**; the manifests they are hash-matched against are
   under `gem5/logs/`, which the submodule's `.gitignore:115` excludes, so
   **zero manifests are committed**. **The verdict itself stands and was checked
   rather than doubted**: r6e's image re-hashes to `a66930ab…` and r6b's manifest
   records `c4d3e2e1…` / `9bd3d1e3…`, exactly the values §3.5 tables. What fails
   is the durability word — and it fails precisely on the evidence the record
   calls "the strongest class available for any campaign in this audit", while
   its own §10 correctly flags `/tmp/r5` as "exactly the fragility that lost r5's
   binary in the first place". **A cache directory is not a worse place than
   `/tmp` by much and is not version control at all**; the same follow-up §10
   recommends for `/tmp/r5` applies here and is recorded rather than performed,
   these being another campaign's artifacts.
3. **§8's closing note — that the brief's premise about r3 and the paper "is
   not supported" — is itself unsupported, and the premise is correct.** The
   note reports searching `/home/domin/STREAMING_Paper/` for `rj3`/`realjoin`
   and for r3's magnitudes and finding nothing. **That search could not have
   found it**, because a paper cites a claim and not a data file. The chain, read
   here in both documents: `Sec7_Evaluation.tex:42-44` states *"its CAT
   tenant-cost curve is within 1--3 percentage points of silicon at the
   comparable widths"*, and `MODEL_SILICON_CAT_CALIBRATION_2026-09-01.md`'s
   fourth line names its own inputs as *"the 12-point gem5 CAT sweep
   (`data/gem5/rj3_runs.jsonl`)"* — which is r3. **This ledger already had the
   chain right one pass ago** and wrote it out in the `F18` close-out; it is the
   *index* that was wrong, and that is corrected in this pass. The same
   over-broad claim originates in `H2H_REALJOIN_CLOSED_2026-09-04.md` — *"No
   paper claim depends on this campaign … every frontier number in the paper is
   r5's"* — whose second clause is true and whose first does not follow from it.
   **The methodological point is the durable one: a paper's dependency on a
   campaign is discovered by following the claim's provenance record, never by
   grepping the `.tex` for the campaign's name.** That is `F11`'s territory
   (a correct artifact nobody read back into the paper) inverted.

Everything else verified, and the load-bearing figures verified exactly rather
than approximately. r5's in-band evidence: all **42** join cells in the 45
surviving `/tmp/r5` launch logs print `addr=0x7ffff77ff000` and
`"fact_base":"0x7ffff77ff000","fact_end":"0x7ffff7fff000"`, a span of exactly
**8,388,608 B**, with `"probe_accesses":131072` — and **no cell reports a zero
address anywhere**, which is the clobber's whole signature. All 45 record
`R5_JOIN 401373ce…`. The counters: `r5_h2` = **129,545 / 129,613 / 129,571**, i.e.
**98.83 / 98.89 / 98.85%** of the range's 131,072 lines, against **exactly 0 in
all 42** non-streaming cells; a 16-page mismark caps at **1,024** lines, so
reaching 129,545 would need **126.5** fills per line on a 64 KiB region that fits
in L1. `cxl_join_bench.gem5` is `EXEC`, not a PIE, loaded at `0x400000`, so
`addr=0` there would have allocated fresh untouched pages and yielded 0. The
scaling check: 4-core declares 1,048,576 lines and records 419,718–427,408
(**40.0–40.8%**), 8-core declares 2,097,152 and records 857,334–862,619
(**40.9–41.1%**) — the level is a workload property but **the derivative is not**,
and a fixed 16-page mismark cannot scale with `--fact-bytes`. §5.3's correction of
the inherited attribution is right: **853,853 is `h1bw_mc_h2_4c_l3x1_bwdef_20260904fix`**,
`H1BW_SLICE_BRACKET`'s post-fix single-slice cell, not r5's. `fused.c` declares
`: "rax"` at all four named revisions, and the `FUSED_KNEE`-era `d00caefd14`
contains **exactly one** m5op where the current file has two — **and that
revision is time-pinned, not merely inferred**: `d00caefd14` is dated
`2026-08-29 22:58:37 +0900`, the same second as `eb20d93`, the registration
freeze this ledger verified last pass, with the 45 `kn_*` launch banners one
second later. So the same second that witnesses `FUSED_KNEE`'s registration also
fixes which `fused.c` it was built from, and "clean by construction" is pinned in
time rather than argued from source history. The instrument's positive control
reproduces exactly: run against `mmap_probe.gem5` (`2139aa85…`, pin still intact)
it rediscovers `0x5260`, `mov %rax,0x6049(%rip) # g_probe+0x20`, UNSAFE, without
being told where to look.

**How r3's indeterminacy is worded, and why the distinction is kept.** r3 is
recorded as **`CLEAN on counters, INDETERMINATE on disassembly`** — not as clean,
and not as suspect. What the counters establish, verified here: of 66 cells the
**60** with `declared_streaming=false` record **exactly 0** bypasses, and the
**6** with it true record 1,274,276–1,277,320 (`r3_h2`) and
10,575,035–10,577,704 (`r3_fh2`), three to four orders above a 1,024-line
mismark. **That is enough to say a large, correctly-scaled range was marked. It
is not enough to exclude an offset or partial mismark**, because a
correctly-sized range at the wrong base produces a similar count and a 90%
mismark falls inside the seed spread. For r5 that gap is closed by the printed
`fact_base`/`fact_end`; **for r3 nothing closes it, because the binary is gone
and was never hashed** — not lost after being recorded, as r5's was, but never
recorded at all, which is the weaker of the two `F13` positions. **The distinction
is preserved rather than rounded up for one reason: r3 is the input to a claim the
paper still makes.** `Sec7:42-44` rests on it through the calibration record, so
"indeterminate" is load-bearing rather than pedantic, and rounding it to "clean"
would put a published sentence on an evidentiary basis the repository cannot
supply. **It is also not a reason for alarm, and the ledger should not be read as
raising one**: r3 is superseded, its 60 undeclared cells are exactly 0, the CAT
claim normalizes by way fraction rather than by any quantity this defect touches,
and no positive evidence of a mismark exists anywhere. The honest position is that
one published sentence rests on a campaign whose tenant binary cannot be
inspected, and that this is a **provenance debt, not a doubt about the number.**

**The `FB_ORACLE` amendment: yes, and it was not a close call.** Amendment 2 is
appended to `FB_ORACLE_PREREG_2026-09-03.md` (its second, after last pass's
`5MiB` correction), because that registration's `fbo` arm **could not have run as
written** — it would have hung — and `P-O1`, `P-O3` and `P-O4` all require `fbo`
cells to produce numbers. A registration whose primary predictions are
unreachable is not a detail to leave for its owner to discover at launch. Appended
and not rewritten, per `A6.19`.

**Two things deliberately not done.** The tenant sources are not touched:
`cxl_join_bench.cpp` is far ahead of its last commit and `mmap_probe.cpp` and
`streaming_h3_dirty_owner.cpp` are untracked, all another worker's in-flight
work, and the audit's own §7.3 declined to commit them for exactly the right
reason — `--only` with an explicit pathspec would still sweep unreviewed work
into this record's commit. **And `F13`'s scope is not rewritten here.** `F19`
extends `F13` from the simulator side to the tenant side, and that is stated in
`F19`'s own row, but re-scoping `F13` while the sources it would newly cover are
mid-commit by someone else would be pre-empting them; **the wording is handed
back rather than guessed at.**

**The open count.** Open now: **six defects** — `F4`, `F15`, `F16`, `F17`, `F18`
and `F19` — plus `tab:gem5`'s +H2 column, `tab:fused`'s way-sweep runner and the
stale Sec5 inline table. `F13` remains closed, no number is reserved, and the next
free number is **`F20`** *(all three clauses superseded within the day by the pass
below, quoted rather than deleted per `A6.19`: the count is now **eight**, `F13`
has **reopened on the tenant side**, `F20` is **taken**, and the next free number
is `F21`)*. **Four of the six are now one family**, which is the
most useful thing this list says: `F17` (a campaign gate), `F18`(2) (a simulator
output), `F19`'s prevention note (an audit tool) and `F16` (a missing witness
rather than a missing instrument) are all the same failure — *the instrument
cannot observe the quantity in the claim* — recorded at four different levels of
the apparatus. `F19` is open on r3's indeterminacy, which no future work can
close, and on twelve wrapper fixes applied in the working tree and awaiting their
owners. **No published magnitude moves in this pass either.** `fig:frontier`(a),
`fig:recovery`, `tab:h1bw` and the full-system P1 claims are all confirmed to rest
on correctly-marked ranges; the paper is untouched and was read only.

---

**Update 2026-09-04, tenant-source provenance pass.** One defect registered
(`F20`), one closed defect **reopened on a new side** (`F13`), and the sharpest
single sentence this ledger has had to write about the headline campaign. The
source is `BENCH_SOURCE_PROVENANCE_2026-09-04.md` at `1fbbcfc`, with the tenant
sources it describes committed in the eight-commit series `c0527e5`…`1fbbcfc`
plus `d3b43f1` — verified here as exactly eight commits and level with
`origin/main` at `d3b43f1` before this edit. Its §9 proposed its findings as an
extension of `F13` and **that is right for the provenance half and wrong for the
gate**, which is the one judgement this pass had to make against the handback.

**The sentence, first, because everything else is context for it: r5's tenant was
not computing the join it reported.** Both halves belong on the record and
neither may be dropped for the other. The artifact was defective — 2,048 of
524,288 fact keys corrupted in every one of r5's 42 join cells, 0.391% — and
every published magnitude stands, because the corruption is byte-identical in
every arm and every r5 figure the paper cites is a ratio. `F20`'s row carries the
measurement and the reasoning; what belongs here is that these are two facts and
not a fact plus a reassurance.

**How r5's exposure was scoped against the existing record, since this is a
correction to an under-scoped one rather than a new discovery.**
`FS_COMPLETE_JOIN_PREREG_2026-09-02.md` addendum 6 already identified and
*measured* this defect — 8,192 keys of 2,097,152 in a 32 MiB fact, **0.391%**,
one per page — and already contained the sentence *"the tenant was not computing
the join it reported."* What it did not do is ask who else ran the call. Read
here in full: addendum 6 opens *"Applied to source only; the running r6e arms are
unaffected"* and is confined to the r6f source fixes; **it names neither r5 nor
the silicon campaign anywhere.** So the brief's description of it as scoped "to
the FS path and silicon" **over-credits it** — the silicon half is not in that
addendum either, and no record in this directory pairs `prefault` with silicon.
The correct scoping is therefore wider than the handback states: **r5 *and*
silicon were both unaddressed; this pass settles r5 by measurement and leaves
silicon open**, registered in `F20`'s status rather than asserted either way,
because `run_silicon_e2e.sh:7` runs the same native tenant and its 105 records
show the same constant-across-arms `matches` that made the defect invisible in
r5. The scoping question was not a technicality: r5 ran `--mode single`, whose
`HEAD` path calls the mutating helper immediately after `fill_fact`, so the
narrow scope excluded the one campaign behind `fig:frontier`(a).

**Why the gate became `F20` and not a component of `F13`, `F17`, `F18` or
`F19`.** Two distinct findings arrived in one record and they do not belong in
one entry. The provenance finding — untracked and far-ahead tenant sources, a
Makefile that could not build its own target, twelve binaries of which one is
reconstructible — **is** `F13`'s defect at a second artifact, and is recorded by
extending `F13` and reopening it on that side, exactly the wording this ledger
declined to guess at one pass ago while the sources were mid-commit. The gate is
a different thing. `F17`, `F18`(2) and `F19`'s prevention note are all
instruments that could not **see** a quantity, and the remedy in each case is to
observe better; `correct: true` sees its quantity perfectly and **cannot fail**,
because its reference is computed from the same input as its subject. **The
discriminator is the shape of the remedy, which is the same test that held `F19`
distinct from `F18`**: no output repairs a tautology, only an external reference
does. The handback's own inclination was that this is the sharpest instance of
the family *because* it is a correctness gate rather than a performance one, and
that is sustained here and stated in `F20`'s row — everything downstream of a
correctness gate is licensed by it, which is why one green boolean covered a
corrupted join for the whole life of the campaign.

**Which figures failed verification.** Everything load-bearing verified exactly,
including several the record could have been expected to round: `+1,103/−29` on
`cxl_join_bench.cpp`, the four source line counts, 2,048 pages and 524,288
tuples, 0.390625%, the 989-match loss, `cac9e27a`'s 39 records, the absence of
`bench_sha256` from all 45 r5 records, the twelve-binary table, and
`Sec7:28-29`'s wording verbatim. **Five did not.** *(1) The `19 records` behind
`2b9d6732…` is **9**.* Verified by scanning every `data/gem5/*.jsonl`: the digest
occurs in 9 records of one file, `h1bw_singlecore.jsonl`. This is the figure that
mattered most to get right, because it is attached to the one genuine recovery
the pass claims and the claim was inflated roughly twofold; the recovery itself
is real and is recorded at 9. *(2) The Bernoulli σ.* The record scores a
989-match deviation against *"~1,024 expected … and a Bernoulli σ of ~362"*; 362
is the σ of the **total** count, and on the loss's own scale σ is **22.6**, so
the deviation is 1.55σ rather than the ~0.1σ the pairing implies — comfortable,
but not as comfortable as written. *(3) `make test` is 138 tests, not 139.* The
record's "138 tests, 1 failure, 1 skipped" is correct and the handback's
"137 pass / 1 fail / 1 skip" is not; re-run here, `Ran 138 tests` with
`failures=1, skipped=1`, so **136** passed. *(4) Three committed files cite
`ivf_flat_bench` — there are four.* `silicon_e2e/ivf_gates.py` names it too,
as a process rather than as a source, which is a weaker citation but a real one.
*(5) The fix removed **six** `prefault_region` calls, not seven.* The file goes
from 7 call sites to 3 at `abccb31` — six removed, two added — and the three
survivors are legitimate, prefaulting regions before anything writes them. The
corrected figure is in `F20`'s row; the defect and its measurement are unaffected.
**And one figure verified better than claimed**, which is recorded because it
changes what the finding depends on: `join_matches = 260,875` sits in **42 of the
45 committed records of `r5_runs.jsonl`**, so Finding 1 rests on committed data,
not on the `/tmp/r5` launch logs that the record's own §8 lists as newly
load-bearing for it. That §8 sentence is too pessimistic and `/tmp/r5` remains
load-bearing for the *binary digest* only.

**The test suite's health depends on which files happen to be present, and that
is worth its own note.** `make test` runs `unittest discover -s tests`
(`Makefile:19`, read here), which collects **untracked** test files. The single
failure — `test_fs_join_analyze.TestFsJoinAnalyzeDryRun.test_p1_zero_bypass_is_void_not_negative`
— has **both halves untracked**, the test and the analyzer it reads, each
confirmed here as absent from `git ls-files`. So **the red state is invisible
from a clean clone and appears only in a dirty tree**, and the converse is worse:
a suite whose membership is a property of the working directory cannot certify
anything about a commit. The failure itself is an assertion on a literal source
string (`arm == "h2" and byp <= 0`) against an analyzer that has since been
restructured to gate on bypass coverage of an eviction ceiling — a stale
assertion, not a live defect, and not this ledger's to fix. Recorded, routed to
the fs-e2e harness owner, and **not** counted in the open-defect list, since it
is an untracked test against an untracked subject and therefore not yet part of
any committed claim.

**Two handbacks recorded and deliberately not fixed.** `ivf_flat_bench.cpp`
remains unversioned with four committed files naming it, registered as an open
`F13` item and left alone because a campaign is live on host `c4`; the
`duckdb_mmap_probe` Makefile's `gem5` target hardcodes its output path and will
overwrite the registered pin `2139aa85…` when next run, which is its owner's
file to change. Neither is a number in the paper and neither is claimed closed.

**The open count.** Open now: **seven defects** — `F4`, `F13` (tenant side only),
`F15`, `F16`, `F17`, `F18` and `F19`, plus the newly registered **`F20`**, which
makes **eight** *(the count is unchanged by the pass below, but `F20`'s
components are superseded, quoted rather than deleted per `A6.19`: its silicon
component **closed** on 2026-09-04 and a **mode-scope** component opened in the
same movement; and the count itself is superseded one pass later — it is **nine**
once `F21` is registered, and the family is **six**)* — plus `tab:gem5`'s +H2 column, `tab:fused`'s way-sweep runner
and the stale Sec5 inline table. `F13` is **no longer wholly closed**: it stays
closed on the simulator, where it was earned, and reopens on the tenant side on
`ivf_flat` alone. No number is reserved and the next free number is **`F21`**
*(taken the same day; it is now `F22`)*.
**Five of the eight are now one family**, which remains the most useful thing
this list says, and `F20` is its sharpest member: `F17` (a campaign gate),
`F18`(2) (a simulator output), `F19`'s prevention note (an audit tool), `F16` (a
missing witness rather than a missing instrument) and now `F20` (a correctness
gate that cannot fail) are the same failure recorded at five levels of the
apparatus — with `F20` distinguished from the other four in that it is not
under-instrumented but **tautological**, so better observation is not its remedy.
**No published magnitude moves in this pass either, and here the reason had to be
argued rather than checked.** `fig:frontier`(a)'s axes, **+5.35%**, **+9.97%** and
**8.42%** are all ratios against unprotected write-back and survive a defect
common to every arm; `Sec7:28-29` is a cross-arm invariance claim and is exactly
what survives, and would be false as a claim of absolute correctness — it makes
no such claim, and rounding that distinction away is the one thing a reader of
this entry must not do. The paper is untouched and was read only. Nothing under
`benchmarks/`, `gem5/` or `/home/domin/STREAMING_Paper/` was modified and host
`c4` was not contacted; this pass edited two files, this ledger and `INDEX.md`.

---

**Update 2026-09-04, silicon close-out of `F20`.** `F20`'s silicon component
**closes**, and it closes by **confirming** the corruption rather than clearing
it. It also closes with an exposure that is larger than the component it
replaces, so the net movement of this pass is one component closed and one
opened. `247876c` is pushed; nothing here re-opens it.

**The measurement, verified independently rather than accepted.**
`data/silicon_e2e_hashjoin.jsonl`: 105 records, one `sha_join`
= `75e0af9472…` across **all 105**, `fact_bytes` = 8,589,934,592 (8 GiB),
`hit_rate` = 1, and `matches` = **534,773,760**. One refinement to the handback's
phrasing: `matches` is constant across **100 of the 105**, the five nulls being
the `qui` arm, which runs no join — so the correct statement is *constant across
all twenty joining arms at five reps*, which is stronger than "all 105 records"
rather than weaker. At 16 B rows that is 536,870,912 rows, the deficit is
**2,097,152**, and `fact_bytes / 4096` is **2,097,152** — the deficit is
**exactly** the page count, giving **0.390625% = 1/256**, one corrupted row per
4096 B page at 256 rows per page. Realized hit rate against a nominal 1.0 is
**99.609375%**, i.e. **99.609%**.

**The 16 B row size is confirmed from source and is no longer an inference.**
`struct Fact { int64_t fk; int64_t measure; };` at
`cxl_join_bench.cpp:53–56` is two 8 B fields, and the file corroborates it
independently at `:584` — `const size_t ents_per_line = 64 / sizeof(Fact); // 4`,
four entries per 64 B line. The row count is exact rather than rounded:
`:1034–1035` and `:1156–1157` set `n = c.fact_bytes / sizeof(Fact)` and then
*write back* `c.fact_bytes = n * sizeof(Fact)`, and 8 GiB divides by 16 with no
remainder. So the deficit landing on the page count is a **derivation**, not a
coincidence that had to be assumed.

**The clincher holds, and it is stronger than handed back: the fraction is
identical at four geometries, not two.** 0.390625% is exact — not approximately
equal — across r5's 2,048/524,288 at 8 MiB, addendum 6's 8,192/2,097,152 at
32 MiB, and silicon's 2,097,152/536,870,912 at 8 GiB. **A third silicon dataset
extends it to a fourth geometry**, found while verifying:
`silicon_e2e_calib_v4.jsonl` at `fact_bytes` = 268,435,456 (256 MiB) reports
`matches` = 200,540,160, which appears not to fit until the tenant's
reps-summation is applied — `ok` compares `out.matches == ref.matches * c.reps`,
so `matches` accumulates — and at **12 reps** it fits exactly:
12 × (16,777,216 − 65,536) = 200,540,160, with 65,536 = 268,435,456/4096 the page
count, again **1/256**. Four fact sizes spanning **1,024×**, one fraction fixed
by the mechanism. **And a fifth confirmation of a different kind**:
`silicon_e2e_hashjoin_4k.jsonl` is the same 105-record campaign with
`huge2m = False` instead of `True`, and it reports the **identical** 534,773,760.
The corruption rate is therefore invariant to the actual page size, which is
exactly what a **hardcoded 4096 B stride** in `prefault_region` predicts and what
a fault-driven mechanism would not. That is independent confirmation of the
mechanism, not a second assumption of it.

**The scope of silicon's exposure is three datasets and 222 records, not one and
105.** All three carry the same `sha_join` = `75e0af9472…`, so one tenant binary
produced `silicon_e2e_hashjoin` (105), `silicon_e2e_hashjoin_4k` (105) and
`silicon_e2e_calib_v4` (12). `run_silicon_e2e.sh` and
`silicon_e2e/run_hashjoin.py:255,260` run `--mode single --hit-rate 1.0`, the
same mode as r5, so the corrupting call is on the executed path structurally as
well as by fingerprint. **Silicon's position on `F13` is better than r5's and
worse than it looks**: `sha_join` is `sha256(args.join)`, a genuine tenant-binary
digest recorded 105 times, so unlike r5's `401373ce…` it *can* be hash-matched —
but `75e0af94…` is **not on this host**, and in particular is not
`build/cxl_join_bench`, which is `75813707…` and differs from the third hex digit.
Silicon therefore sits with `cac9e27a…`: digest recorded, bytes elsewhere, source
state uncommitted until this week. *(**Corrected 2026-09-04 later the same day.
The scoped clause was right and the conclusion drawn from it was wrong; both are
kept, per `A6.19`, and the wrong one is the last sentence: "Silicon therefore sits
with `cac9e27a…`".** "Not on **this host**" was true and remains true —
`build/cxl_join_bench` is re-verified here as `75813707490e5202…`, 142 752 B,
and the third-hex-digit confusability noted above is presumably how the two came
to be conflated in the first place. What is new is that the bytes have been
**located**: `SILICON_E2E_RERUN_OUTCOME_2026-09-04.md` reports `75e0af94…`
present as `benchmarks/e2e/hash_join/build/cxl_join_bench` **in `c4`'s checkout**.
So silicon's position is **better** than `cac9e27a…`'s, not equal to it: digest
recorded 105 times **and** bytes extant. **It is still not reproducible**, and the
reason is now `A1.R1`-shaped rather than merely absent: `c4`'s checkout sits at
`33eaf07` — verified here as a real ancestor, dated 2026-08-23, predating both
`abccb31` and `563ec54` — and carries an **uncommitted** `src/cxl_join_bench.cpp`
hashing `e8d10458…` that matches no commit. So the dataset is non-regenerable and
is retained rather than replaced. **The non-reproducibility became load-bearing
rather than cosmetic within the day**: the flush-behind discrepancy below is a
difference between `75e0af94…` and `HEAD` that **cannot be bisected**, because one
side's source is in no commit. That is the first time in this ledger that `F13`
has blocked a *diagnosis* rather than a reproduction.)*

**No published silicon figure moves, and the axis argument was checked in the
generator rather than taken on trust.** `make_eval_frontiers.py:86–99`
(`silicon_frontier()`) reads this dataset, takes `q` and `w` as the median
`victim_cyc_per_load` of `qui` and `wb`, `tw` as the median
`join_mtuples_per_s` of `wb`, and returns `100*(w-v)/(w-q)` and `100*(t/tw-1)`
for every point — **both `fig:frontier`(b) axes are cross-arm ratios normalized to
the `wb` and `qui` arms of this same dataset**, exactly as handed back. The
precise reason they survive is worth stating, because "the corruption cancels" is
not quite it: neither axis reads `matches` at all, and the corruption is a
property of the *fact region's size and page layout*, identical in every arm, so
all twenty joining arms perform the **same** work. The ratios therefore remain
valid comparisons between arms; what shifts is the **operating point** being
compared at — 99.609% rather than 100% probe hit rate. Corroborating this from
the other side, `join_mtuples_per_s` is `n * reps / total_sec / 1e6` at
`:1199`, where `n` is the nominal row count and **not** the match count, so the
throughput metric's definition is untouched by the corruption; only its measured
`total_sec` moves, and it moves identically in every arm.

**The appendix coincidence, recorded as the fortunate accident it is.**
`Appendix.tex:319–321` reads, verbatim: *"We previously printed 2.9\% and 7.5\%
here; those came from an $n{=}3$ arm at a 100\% probe hit rate, an operating
point whose run-to-run resolution we later measured at $\pm$15\%, and they are
withdrawn in favour of the 50\%-hit-rate figures."* So the one place the paper
quoted figures from the unit-hit-rate operating point had **already been retired,
for an unrelated reason** — sampling resolution, not correctness — and nobody
knew the operating point was also 0.391% corrupted. **This is luck and must not
be written up as diligence.** Two precisions the handback did not draw: the
withdrawn 2.9% and 7.5% were themselves *ratios* (aggressor cost), so they would
have survived on the cross-arm argument anyway — the accident is narrower and
cleaner than "absolute figures were withdrawn in time"; and the withdrawn arm was
`$n{=}3$` while this dataset is `$n{=}5$` (5 reps × 21 arms = 105, verified), so
the retired figures came from an **earlier** run of the same tenant at the same
operating point, not from these records.

**Two further instances of `F20`'s class, in the silicon apparatus itself, which
is where the component closes and the class does not.** `run_hashjoin.py:445,455–456`
sets `ref_matches = None`, then seeds it from **the first `wb` arm's own measured
match count**, and `gates.py:166–175`'s `live_check` fails an arm only if
`matches != ref_matches`. Its docstring names the defect without noticing it:
*"G-live: tenant produced work, and the checksum matches the reference arm."*
**The reference is an arm.** It is the same binary at the same geometry, so the
gate can detect arm-to-arm divergence and can never detect common-mode
corruption — `F20` exactly, at a third level. `ivf_gates.py:82–89` is the
identical construction on `ref_id_sum` for the IVF campaign, a fourth. **And the
sharpest prevention point of the day comes from `gates.py:178–182`**, which is a
*positive control on the gates*: *"Feed each gate a case that must fail, then a
case that must pass. Called by the runner before any arm. If a check cannot fail,
we find out here rather than in the JSONL."* That self-test **passed**, and
correctly — `live_check` *can* fail, on a mismatched count. **So a positive
control that a gate can fail is not a positive control that it can fail on the
defect class it appears to cover**, and this is the first time the ledger can
point at a campaign that built the right instrument for the wrong proposition.
`F19`'s prevention note asked for gates that observe the quantity in their claim;
this asks for something further — that a gate's negative control be constructed
from the *defect*, not from an arbitrary failing input. Recorded against
`F20`'s prevention half. `SILICON_E2E_OUTCOME_2026-09-01.md` then cites the
blind gate as reassurance in as many words — *"Match counts identical across
every tenant arm (534773760)"* — which is the class completing its circuit from
instrument to record.

**Check 1: does any main-text claim cite an absolute number from this dataset?
No — and the check found a larger exposure elsewhere, which is the substantive
result of this pass.** Every silicon-hashjoin figure in the main text is a ratio,
verified against the arm table in `SILICON_E2E_OUTCOME_2026-09-01.md`:
`Sec7:196–205` gives 91.4% recovery / 42.0% tenant cost for the one-way mask,
44.5% for 6.31%, the CAT point at 44.1% for 25.18%, and `PREFETCHNTA` at 15.3%
for 2.95%; `Sec4:94–105` gives 44.5%/6.31%, 44.1%/25.18%, and the window sweep's
46.2%, 44.5%, 31.8% for 5.88%, 6.31%, 6.12% at `$n{=}5$` per point. All are
recoveries or tenant-cost fractions. None of the dataset's absolute quantities
appears anywhere in the `.tex` — searched for 73.406, 167.875, 42.08, 141.849,
34.74, 153.411, 43.32, 124.277, 39.60, 81.536, 24.40, 534773760, 200540160 and
the 8 GiB fact size, with **no hits**. The one absolute pair in the neighbouring
prose, `Sec7:210–211`'s *"from 0.835 to 1.708~s"*, is **DuckDB v1.1.3**, a
different binary that never calls this helper. **So `F20`'s silicon half closes
clean on its own terms.**

**But the check that closed it opened a wider one, and this is the finding to
route.** Establishing that `--mode single` corrupts required mapping the helper's
call sites, and there are **seven, in seven modes** — `run_stream:1042`,
`run_latency:1092`, `run_single:1163`, `run_breakdown:1235`,
`run_probe_workload:1289`, `run_split:1431`, `run_morsel:1619`. **Six of the
seven run immediately after `fill_fact` and therefore corrupt**; only
`run_latency` is safe, and safe for the right reason — it prefaults a region
allocated on the line above and not yet written. **So the exposure was never
confined to `--mode single`, and two of the corrupting modes sit behind
*absolute* figures in the paper**: `run_split` is the SMT-split campaign behind
`Sec4:48–54`'s **336.6 → 214.6 Mtuple/s**, **88.5 → 95.7 cycles/access** and
**215.0 Mtuple/s / 95.4 cycles/access** (`$n{=}30$`), and `run_morsel` is the
fused mode — `w7_campaign.sh` runs `--mode morsel` — behind `Appendix:113,119,124`'s
**88.3 → 44.0**, **44.0 vs 55.2** and **−0.8 cycles/access**. **The direction of
the error is known and the magnitude is not**: a corrupted key turns a hit into a
miss, and a miss walks the open-addressing chain to an empty slot, so probe cost
is biased **upward**. Deliberately **not** quantified here — reading the paper's
own 88.3→44.0 hit-rate sensitivity linearly would put 0.39 pp of hit rate at
roughly 0.4%, which is inside the printed precision of some of those figures and
outside others, but that extrapolation crosses a 50 pp range to reach a 0.39 pp
one and is not evidence. **It needs measuring, exactly as r5's and silicon's
fingerprints were measured, and asserting it from arithmetic would repeat the
error this ledger has spent two passes correcting.** Registered as `F20`'s open
mode-scope component; the paper is **not** edited and this is handed back for
routing per the brief.

**Check 2: does the paper describe this workload as a unit hit rate anywhere it
should now read 99.6%? One instance, cosmetic, and one near-miss that is
correct.** The instance is `Appendix:319`'s own *"at a 100\% probe hit rate"*,
inside the sentence that withdraws the figures — realized 99.609%, so it is
wrong by 0.391 pp while describing an operating point whose numbers are already
retired and whose stated withdrawal reason (`$n{=}3$`, ±15% resolution) is
untouched. Reported, not edited. **The near-miss is `Appendix:110`, and it is the
phrase the brief warned would not survive rounding — *"so \textbf{all} of its
probes hit"* — and it is correct.** That sentence is about the quiescent
`hot-probe` mode, and `run_hot_probe:1729+` probes `keys[i % keys.size()]`, the
table's **own inserted keys**, not the fact array, and **calls
`prefault_region` nowhere**. Its probes do all hit. `Appendix:108`'s *"built at a
50\% hit rate, so half of its probes miss"* holds at two figures, realized
49.76%. Every other `100\%` in the paper is an MBA throttle setting or an
L2-miss rate and is unrelated.

**The open count.** Open now: **eight defects** — `F4`, `F13` (tenant side, on
`ivf_flat`), `F15`, `F16`, `F17`, `F18` (gate half), `F19` (r3 and the handed-back
fixes) and `F20` — plus `tab:gem5`'s +H2 column, `tab:fused`'s way-sweep runner
and the stale Sec5 inline table. The **count is unchanged at eight** and that is
the honest summary of this pass: `F20`'s silicon component closed and its
**mode-scope** component opened in the same movement, so the number stayed put
while the exposure moved from "one campaign unaudited" to "two published sets of
absolute figures rest on a corrupting mode". `F20` is now open on two components
— the gate class, which no single fix closes, and the mode scope, which needs a
measurement. No number is reserved and the next free number is **`F21`** *(taken
the same day by the vacuous-predicate class; it is now `F22`, and the open count
is **nine**)*; the
mode-scope finding is a component of `F20` and not a new class, because it is the
same defect at more call sites rather than a different failure. **Five of the
eight remain one family.** **No published magnitude moves *from the silicon
close-out*** — `fig:frontier`(b)'s axes are cross-arm ratios in the generator and
every main-text silicon figure is a ratio — **but the mode-scope finding puts two
sets of absolute figures in question for the first time in this ledger**, and
that is the one thing a reader of this entry must carry away from it. The paper
was read only and is unmodified; nothing under `benchmarks/`, `gem5/` or
`/home/domin/STREAMING_Paper/` was touched and host `c4` was not contacted.

---

**Update 2026-09-04, IVF recall anchor and the `F20`/`F21` split.** One defect
registered (`F21`), the `F20` family sub-divided by cause, and — for the first
time in four passes — **not one handed-back figure failed verification.** The
source is `IVF_RECALL_REFERENCE_2026-09-04.md` at `45956d4`, with
`ivf_recall_reference.py` and `ivf_recall_compare.py`. `785c66d` is pushed.

**Everything was re-derived, and the strongest verification available was taken
rather than the cheapest.** `ivf_recall_reference.py` writes no files, so it was
re-run here end to end. It reproduces `recall_at_k = 0.5083` as **5,083 hits of
10,000**, `id_sum = 147039988` and `dist_sum = 3708791.656096697`; the exhaustive
cell at `--nprobe 8192` reproduces `id_sum = 149070802`; the alternate seed
`0xDEADBEEF` reproduces `0.5124` and `id_sum = 144262486`; and all six decision
margins reproduce to every digit printed (1.29e-04, 2.48e-04, 8.67e-05,
1.32e-03, and **zero** exact ties on both counters). **And it reproduced under a
different numeric stack than the record used** — NumPy 2.4.6 on CPython 3.11.15
here against the record's NumPy 2.5.2 on CPython 3.14.4 — which is a stronger
result than a re-run: the anchor is invariant to the library version, not merely
repeatable on one. `149070802 ≠ 147039988` confirms the exhaustive quantity is
genuinely distinct from the approximate one, so numerator and denominator are
separately anchored, exactly as claimed.

**`F21` rather than a sub-shape, and the handback's own reasoning is what carries
it.** The proposal was that a family whose members are distinguished by *why*
they cannot fail is more useful than one number covering both, and that is
sustained. The decisive test is the one this ledger has used twice already —
the **shape of the remedy** — and here it returns the cleanest separation yet,
because the two remedies are not merely different but **mutually
non-substitutable in both directions**: no threshold can rescue an `F20`, and no
external reference is *needed* for an `F21`, whose quantity already moves 41% of
its own value under a 5% corruption. `F19` separated from `F18` on *emit* versus
*declare*, both additions to one artifact; these two are disjoint. The
characterization that settled it is that **`(0,1]` is not a loose bound but
`recall_at_k`'s entire definitional range**, so the predicate asserts
well-formedness and no proposition about the result — a type check wearing a
correctness gate's name, which is a different defect from testing a real
proposition against the wrong reference. `F21`'s row carries the full argument.

**Why the evidence for the split is unusually good, and it is worth saying
plainly: this is a natural experiment, not an argument.** One campaign carries
one instance of each shape in two adjacent gates, and a measured control
separates them. `live_check` seeds `ref_id_sum` from the **first arm**
(`run_ivf.py:473–474`, read here) and every arm builds the same index, so the
`id_sum`s agree whatever they are — straight `F20`, the fifth instance of that
shape and now recorded in its row. `recall_at_k` grades the approximate search
against `exact_query(lists, …)` over **the same mapping** (`:975–980`), which is
also `F20` in construction — and yet the quantity it produces *does* move, so what
actually lets the corruption through is the absent bound, which is `F21`. **So
one gate can be both**, and the two numbers name the reference defect and the
predicate defect separately rather than competing to describe one gate. That is
the practical payoff of splitting and the reason it is more useful than one
number: fixing `recall_at_k`'s reference and fixing its bound are two different
tickets, and §7 of the record proposes exactly one of each.

**The "first absolute anchor" superlative survives, in a narrowed form that is
the form worth keeping.** Checked against the record set rather than asserted.
**Confirmed: `recall_at_k = 0.5083` with `id_sum = 147039988` is the first
absolute, externally-computed correctness anchor on a *workload result* anywhere
in this project.** Every other correctness check found is cross-arm or
multiple-implementations-over-one-input, and the nearest miss makes the point:
the hash-join tenant's `--self-test reference` (`cxl_join_bench.cpp:1790–1807`)
runs `scalar_join`, `join_range("wb")` and `join_range("nta")` over **one** `fact`
array, compares them to each other, and **hardcodes no expected value at all** —
it *prints* `matches` and `sum` rather than asserting them, so it would pass
unchanged on a corrupted array, which is precisely what r5 demonstrated. There is
no pinned golden result anywhere in the tracked benchmark sources (searched), and
`hnsw_bench.cc` contains no recall, brute-force or ground-truth path and backs no
campaign, no data file and no paper claim. **The narrowing, which must be kept or
the superlative becomes false:** the project does hold earlier absolute,
externally-derived quantities — `AGGBW_WINDOW_PREREG_2026-09-03.md`'s "bracketed
ground truth" for window-boundary reconstruction, and the DuckDB campaign's
analytic reused set `R(N) = 40N` — but those anchor an *instrumentation* quantity
and an *occupancy model* respectively, not a workload's computed result. So the
claim is "first anchor on a workload result", not "first absolute external
quantity", and stated the second way it would be wrong.

**No figure failed.** All thirteen `id_sum` agreements, the corruption ladder,
the decision margins, the three gate line references, the policy-independence
claim and the provenance digests verified as written. Two findings are *additions*
rather than corrections, both strengthening the record. First, the `(0,1]`
predicate occurs in **three** places rather than the one the record cites at
`:1014` — it is also ORed into the `void_streaming_ivf` determination
(`:1008–1009`) and reimplemented in the harness as `ivf_gates.recall_check`
(`:53–57`) — so the **campaign's VOID decision shares the toothless bound with
the gate it is supposed to police**, which widens `F21` from a gate to a verdict.
Second, the record's claim that `--policy nta` and `--flush-distance` cannot
change recall is better founded than "provably": it is **enforced by the tenant's
own self-test**, which fails the build on `sn.id_sum != s.id_sum` and
`sf.id_sum != s.id_sum` (`:1089`, `:1095`), so the determinism is a tested
invariant rather than an inspection.

**Two handbacks recorded as pending, with the sequencing reason, because the
reason is the substantive part.** `ivf_gates.py` was deliberately left alone:
changing a gate module while the campaign is writing records through it would
make those records' provenance depend on *when* during the campaign each was
written, which is a defect this ledger has already had to name once — a gate's
value is that every record it admitted was judged by the same predicate.
So both fixes are correct, neither is urgent, and both wait for `c4`:
**(1)** pin `ref_id_sum = 147039988` externally in `run_ivf.py:473–474` instead of
seeding from the first arm, which makes the gate able to fail on the *first* arm,
which today it cannot — this is the `F20` fix; and **(2)** replace the `(0,1]`
check with a `0.5083 ± 0.001` window — the `F21` fix — which needs no tenant
source change if it is enforced in `ivf_gates.recall_check`, and that is the
smaller move. Both are pinned to the full tuple `(nlist 8192, dim 1024, nb 32768,
nq 1000, nprobe 16, k 10, kmeans_iters 1, train_n 16384, seed 0x1F1FCAFE1234)`
and are worthless pinned to less; the window is defensible because recall is
deterministic across policies by tested invariant, per above. `ivf_flat_bench.cpp`
is committed in the same landing. **None of the three is applied here** and this
pass did not touch `ivf_gates.py`, `ivf_flat_bench.cpp`, `c4`, `gem5/` or the
paper.

**The open count.** Open now: **nine defects** — `F4`, `F13` (tenant side, on
`ivf_flat`, prognosis upgraded), `F15`, `F16`, `F17`, `F18` (gate half), `F19`
(r3 and the handed-back fixes), `F20` (gate class and mode scope) and the newly
registered `F21` — plus `tab:gem5`'s +H2 column, `tab:fused`'s way-sweep runner
and the stale Sec5 inline table. No number is reserved and the next free number
is **`F22`**. **Six of the nine are one family, and the family is now
sub-divided by cause rather than only enumerated**, which is the first structural
improvement to it since it was identified: `F17` (a campaign gate), `F18`(2) (a
simulator output), `F19`'s prevention note (an audit tool), `F16` (a missing
witness), `F20` (a reference that cannot move) and `F21` (a predicate that bounds
nothing) — with the last two distinguished by *why* the gate cannot fail and
therefore by which remedy applies. **No published magnitude moves and, unusually
for this week, none is even in question from this pass**: `F21` is **latent**, the
IVF tenant performs no mutation of its list object, no IVF number is wrong, and
the campaign now has the one thing every other workload in this project lacks —
an absolute figure computed by something that shares no code with it. The paper
was not read or modified in this pass at all.

---

**Update 2026-09-04, cross-host reproducibility scoping pass.** **No defect
registered and none closed; the count stands at nine.** What this pass produced
instead is the ledger's first **standing wording rule**, `A1.R1`, and a narrowed
`F13` prognosis. It is worth naming that shape: a pass whose output is a
constraint on language rather than an entry in a defect table, because the thing
that went wrong was a sentence and not an artifact. Sources are `0d5872f` (the
correction to `IVF_RECALL_REFERENCE_2026-09-04.md`, §11) and `afdeb8f`
(`SILICON_E2E_RERUN_PREREG_2026-09-04.md`, another worker's). `69eb794` is pushed.

**The handed-back framing was sustained, and it is the first of four put to this
ledger today to survive intact.** The claim was that `ivf_flat_bench`'s two
divergent binaries are *not* a second `F13` instance because `-march=native` plus
two different CPUs and two different compilers make two binaries the correct
outcome. Checked and agreed, on three grounds set out in `F13`'s row: the
shape-of-the-remedy test returns **no** for the first time (committing the source
would not have prevented the error by one byte); `F13`'s subject is source state
*no commit captured*, whereas this is source state *two coordinates capture*; and
the locus differs, in that nothing was done to any artifact — the repository, both
hosts and all three binaries were identical before and after the wrong sentence.
**The remedy for a wrong sentence is a rule about sentences, so this pass yields
`A1.R1` rather than `F22`.** Two ledger-side consequences that are not in the
handback. First, a **permanent ceiling**: `ivf_flat/Makefile` has no gem5 target,
so every `ivf_flat_bench` that can exist is host-specific, and the tenant half of
`F13` cannot close in the strong form this ledger claimed one pass ago — not for
this tenant, not for any host tenant, ever. Second, an **inversion**: the binaries
for which cross-host byte-reproducibility is attainable are exactly the gem5
guest binaries, which are precisely the ones `F13` found least reproducible
because their source was lost. Where reproducibility was attainable the source
was missing; where the source is present reproducibility is host-bounded. No
tenant has ever held both good positions at once.

**One handed-back figure failed, and it failed against one of the eight citations
the handback itself supplied.** The scope claim was that "the **only** deliberate
exception is the gem5 full-system target, `hash_join/Makefile:81-87` (`gem5fs`)".
Verified false: **six** of that Makefile's recipes omit `-march=native`, all of
them `-static` gem5 targets — `h3-dirty-owner` (`:34`), `h3-dirty-owner-fs`
(`:40`), `gem5` (`:44`), `gem5-window` (`:59`), `w7`'s gem5 half (`:76`) and
`gem5fs` (`:89`). The correct line is **host target versus gem5-guest target**,
which is both more accurate and more useful, since it states the reason. And
`AGGBW_VALIDITY_2026-09-03.md:88-97` — item eight of the eight — already
documented the omission at `:44` and made it load-bearing there ("so `__AVX2__`
is undefined", which is why the gem5 binary takes the scalar path). **So the
handback mis-applied a documented property twice in one document: once to a
binary, and once to the list of places proving the property was known.** That is
the strongest available argument for `A1.R1` and it is why the rule is about
phrasing rather than about a compiler flag. The correction is recorded here and
in `A1.R1`; `IVF_RECALL_REFERENCE_2026-09-04.md` was not edited, per the
constraint, so its §11.3 table still reads "the only deliberate exception" and
**that sentence is handed back to its owner as the one figure of this pass that
did not verify.**

**The eight citations otherwise came out clean, checked at nine lines rather than
the two or three asked for.** All nine land on `-march=native` text and none is a
miscitation. Two files are cited by bare name and live under `benchmarks/e2e/`
rather than `experiments/asplos/` — `HNSW_CAT_SENSITIVITY_OUTCOME.md` and, in the
reach table, `DUCKDB_JOIN_CORUN_PREREGISTRATION.md`. Both exist and both say what
they are cited for; the cost is a `find`, not a wrong figure, and it is recorded
because this ledger's first read of the duckdb citation concluded the file was
missing, which was this pass's own path assumption and not a defect in the
record. `instrument/Makefile:6-7` is the best of the eight and deserves quoting
in full, since it is `A1.R1` already written, two years of habit ahead of the
rule: "`-march=native` means the binary is host-specific. Each host builds its
own; binaries are never copied between hosts."

**A scope limit on this pass that should be stated rather than glossed: half of
the correction is unverifiable from here, and it stays unverified.** The `c4`
figures — `1b63e006…`, 100 832 B, 38 records, 37 × `id_sum = 147039988`, `g++
11.4.0`, Xeon Platinum 8462Y+ — occur nowhere in this repository outside the
corrected record itself, because the campaign's records are on `c4` and `c4` is
out of bounds. They are marked **sourced rather than verified** in `F13`'s row.
This is the first load-bearing figure in this series that could not be checked
from this host, and the honest position is to say so rather than to let a
re-derivation of the local half stand in for the whole. **What could be checked
is the claim's shape, and it holds better than plausibility.** `run_ivf.py:456`
computes `sha_ivf = sha256(args.ivf)` and `:174` stamps it into every record, so
"in all 38 records" is a statement about a field that exists. And the 37/1 split
is *entailed* by committed code: `qui` (`:244`) returns before the tenant is
launched, so it alone carries no `id_sum`, and the rotation at `:468` — `order =
arms[rep-1:] + arms[:rep-1]` over 21 arms and 5 reps — puts `qui` at record 1 and
not again until record 42. **Without that rotation the same 38 records would
contain two `None`s, so the reported figure is predicted by the launcher rather
than merely consistent with it.** The local half was re-measured: `b17ddd4c…`,
104 344 B, `mtime 2026-09-02 16:20:47`, unchanged across three verification
passes, on `mos181` / 8592+ / `g++ 15.2.0`.

**The anchor's strengthening is accepted on its consequence rather than on its
figures, and the consequence lands on a fix this ledger has already recorded.**
If a NumPy reimplementation and two independently built binaries across two
microarchitectures and two compilers all produce `id_sum = 147039988`, then the
one real objection to the pending `F20` fix — that pinning an exact 64-bit
integer is brittle against toolchain drift — is answered by the integer having
already survived a toolchain change. That is the reason to record the
strengthening in `F13`'s row even though its figures are sourced: it changes a
decision, not just a description. **Both pending fixes stand unchanged and
unapplied**, still sequenced behind the live campaign for the reason given above,
and this pass touched neither `ivf_gates.py`, `run_ivf.py`, `ivf_flat_bench.cpp`,
`c4`, `gem5/`, the paper, nor `IVF_RECALL_REFERENCE_2026-09-04.md`. One
refinement to the `F20` scope noticed while reading the rotation: the only record
preceding the `ref_id_sum` seed at `run_ivf.py:473-474` is rep 1's `qui`, which
runs no search, so the "cannot fail on the first arm" half of that defect has no
realized reach — the one ungated record is the one with nothing to gate. The
class is untouched; a reference derived from the campaign's own `wb` arm still
cannot detect a corruption common to all arms.

**Routing this pass's second source turned up the best corroboration `F20` has
received, and it is independent of this ledger.** `SILICON_E2E_RERUN_PREREG_2026-09-04.md`
was rowed rather than merely counted, and reading it to write the row found
another worker deriving `F20` and `F20`'s remedy from the workload, without
reference to the taxonomy: its `G-exact` section states that "a cross-arm
consistency check cannot detect an arm-identical defect … G-exact is its fix: an
**absolute** correctness assertion, anchored to arithmetic rather than to another
measurement." That is this class and this remedy in different words. The gate it
replaces is **`F20` instance three verbatim** — `run_hashjoin.py:455-456` seeds
`ref_matches` from the first `wb` record's own output, the same line-for-line
pattern as `run_ivf.py:473-474`'s `ref_id_sum`, confirmed here by reading both —
so the two campaigns share a runner family and a defect. **Verified from the
records rather than from the prereg**: `data/silicon_e2e_hashjoin.jsonl` holds 105
records, **every one `status=ok`**, a single `sha_join 75e0af94…`, and 100 tenant
records at `matches = 534,773,760` where `8,589,934,592/16 × 1` requires
**536,870,912**; the deficit is **2,097,152**, exactly `fact_bytes/4096`, i.e.
**1/256 = 0.390625%**, one key per 4 KiB page. Every figure reproduces. **The
value to the taxonomy is that `F20` now has a realized half and a latent half
measured on different workloads**: hash-join is where a self-consistency gate
admitted 100 corrupted records into a published dataset, IVF is where the same
shape sits over a tenant that mutates nothing. A class independently rediscovered
by someone solving a concrete problem is better evidence that it carves reality
than any amount of internal argument for it, which is worth more to this ledger
than a sixth instance would have been. One limitation to carry with the citation:
`G-exact` is enforced **post-hoc in `rerun_analyze.py`**, not in the committed
shared runner, so it can void a campaign but not abort one — the prereg says so
itself, and the reason is the same reason the two `F20`/`F21` fixes below are
still unapplied: that runner is shared with a live campaign.

**Routing.** `SILICON_E2E_RERUN_PREREG_2026-09-04.md` (`afdeb8f`), counted in the
index total last pass but not rowed, is now rowed in `INDEX.md` — before its
outcome document lands rather than after, which is the point of an index carrying
a pre-registration at all.

**One superlative from the previous pass re-examined against the new source, and
it survives on its exact wording while a looser reading of it does not.** That
pass closed by saying the IVF campaign "now has the one thing every other workload
in this project lacks — an absolute figure computed by something that shares no
code with it." **Still true as written**, and the qualifier is load-bearing:
`G-exact` is an absolute anchor on a workload result too, registered the same day,
but it is derived **in-band** from arithmetic rather than computed by an
independent implementation. By one measure `G-exact` is the stronger of the two —
an exact identity, `fact_bytes/sizeof(Fact) × reps`, that needs no reimplementation
to be believed — and it is available only because that join is exhaustive at
`hit_rate` 1.0, whereas an approximate top-k has no closed form and must be
recomputed by something. **So "first *externally-computed* absolute anchor" holds
and "the only absolute anchor in the project" would now be false**; the sentence
above happens not to say the latter, which is luck rather than precision, and it
is recorded here so the next pass does not paraphrase it into the false form.

**The open count is unchanged: nine defects** — `F4`, `F13` (tenant side on
`ivf_flat`, prognosis now narrowed to host+toolchain scope and ceilinged there),
`F15`, `F16`, `F17`, `F18` (gate half), `F19` (r3 and the handed-back fixes),
`F20` (gate class and mode scope, one sub-claim's reach narrowed above) and `F21`
— plus `tab:gem5`'s +H2 column, `tab:fused`'s way-sweep runner and the stale Sec5
inline table. No number is reserved and the next free number is still **`F22`**.
Six of the nine remain one family. **The list of standing wording rules is new
and has one member, `A1.R1`; the next free rule number is `A1.R2`.** No published
magnitude moved and none is in question from this pass.

---

**Update 2026-09-04, costume-check and live-transient pass.** **No defect
registered or closed; the count stands at nine.** `F21`'s *statement* is refined
and three of its clauses are corrected, two of them mine and one a handback's;
one pending fix is reclassified from a repair to a registered-gate amendment; and
a distinction is recorded ahead of an outcome document that does not yet exist.
Sources are `IVF_FLAT_SILICON_PREREG_2026-09-01.md`, the tenant and analyzer
sources, and a handback reporting the live campaign. `44df017` and `2cb6b50` are
pushed; the latter applied this ledger's six-recipe correction to
`IVF_RECALL_REFERENCE_2026-09-04.md`, which was out of bounds here, and conceded
the `A1.R1` placement argument.

**Finding 1, accepted with one amendment: the toothless bound was *registered*,
and the register was honest.** `IVF_FLAT_SILICON_PREREG_2026-09-01.md:50-51`
reads, verbatim: "Recall is a costume check: if it is missing or not in (0, 1],
the cell is void." So `(0,1]` is the **specification**, not a slip against a
stricter intent, and "costume" concedes precisely what the check does. The term is
deliberate — `:56` uses it again for a different sham, "A costume quantizer is
worse than omitting RAG" — and `analyze_silicon_ivf.py:14` carries it forward
verbatim. **This refines `F21` rather than splitting from it, and the
shape-of-the-remedy test is what settles it:** the remedy is still *a bound that
excludes something the quantity can take*. What the finding adds is a
**procedural precondition** on applying that remedy, not a different remedy, and a
governance step in front of an unchanged fix is a refinement by construction. The
core of the class — a predicate that excludes nothing, relied on as though it
excluded something — is untouched and is now better evidenced than when it was
registered. **The amendment to the handback's framing is about where the honesty
stops, and it is a clean boundary: the label survives in both documents and dies
at both enforcement sites.** `ivf_gates.recall_check` carries no such comment, and
the tenant prints `FATAL:` and exits 4 with no hint that a costume check is what
fired. The prose kept the caveat; the code kept the authority. In the tenant's
favour, `--help` (`:824`) states the predicate exactly, so what overstates the
check is its **name** and its `FATAL:` prefix rather than its documentation.
**One clause of `F21` is therefore false and is corrected rather than defended:**
"a type check wearing a correctness gate's name" — it does not wear that name in
its own specification; the name is acquired downstream. **A second clause of mine
is withdrawn outright**, and it was a criticism rather than a fact: the positive
control feeding `recall_check(0.0)` and `recall_check(1.0)` is **exactly the right
control for what was registered**, faithful rather than lazy, so the
"control-built-from-an-arbitrary-input" sub-pattern drops from two instances to
one, `gates.py`'s `self_test()` alone. **A control cannot be faulted for not
testing a proposition its gate never asserted.** *The prereg's honesty is a point
in this project's favour and is recorded as one.* **What makes the refined defect
worse rather than better is that no single edit created it**: the registration was
honest, the tenant implemented the specification, the analyzer copied the label,
the harness re-implemented the predicate. It exists only in the composition, so no
single-file review could have found it — which is a sharper prevention statement
than the row previously carried.

**Finding 2, accepted and my own wording was wrong on both halves.** The
superseded sentence, quoted per `A6.19` and corrected in `F21`'s row: "So the VOID
decision for the campaign shares the toothless bound with the gate." Wrong on
scope — `:1008` reads `out.void_streaming_ivf = c.identity && (…)`, so it belongs
to the **completed identity** campaign and is constant `false` in the running
frontier campaign, which passes no `--identity`. Wrong on direction — the
expression is a disjunction of *failure* predicates, so a disjunct that cannot
become true cannot suppress the three that can. **No VOID verdict was weakened.**
The correction goes further than the handback claimed, and further in the
project's favour: the redundancy is **double**, because under `--identity` each of
`g_vma`, `g_copy` and `g_list_dom` independently `FATAL`s and `std::exit(1)`s at
`:1017-1031`, so the process is gone before a record could carry the flag, and the
one disjunct that could set it observably is shadowed by `--require-recall`'s
`exit(4)`. `:1108`'s self-test asserts the field must be false. **So
`void_streaming_ivf` has no reachable authority in either direction and citing it
as a blast-radius site overstated it.** The corrected accounting of the predicate
is **two implementations and four consumers**, not three appearances, and the
consumer that matters was the one missing from my count: the analyzer's
**registered**-gate list, `rc`, where G-recall is the third of four entries
(`:186-192`). That is the line a reader consults to learn whether the registration
was violated, which makes it a worse adopter than the inert field I named instead.

**Finding 3, and the mechanism is corroborated from committed code even though the
records are on `c4` and out of bounds.** The reported transient is record 31,
`status=gate_fail`, mask correctly set going in and the post-rep readback `None`,
with that rep's throughput and victim cost at unconfined values. **Verified
structurally, and the structure is exact rather than merely consistent.** Record
31 is `cat05` rep 2 **by derivation**: `run_ivf.py:468` rotates the arm order per
rep (`order = arms[rep-1:] + arms[:rep-1]`) over 21 arms, so rep 2 spans records
22-42 beginning at `wb`, and its tenth entry is `cat05` — which is what the
handback reports, from records this ledger cannot read. The same rotation predicts
the `mask_got_after=None` census: in 62 records the non-CAT arms number 6 + 6 + 5
= **17**, matching "17 of the 18 are the six non-CAT arms where that is correct"
exactly, with the 18th being the transient. **And the gate's mechanism explains
the physics.** `snapshot_clos` (`run_ivf.py:102-108`) returns
`mask_got_after=None` only when `/sys/fs/resctrl/clos_b` is **absent**, so `None`
on a CAT arm means the CLOS group *disappeared* between setup and readback — the
tenant genuinely ran unconfined for that rep, which is why its numbers sit at
unconfined values. `mask_held_check` (`gates.py`) is `G-mask-after`, documented in
its own docstring as closing "the setup-then-measure TOCTOU", and it fails closed
for `ways > 0` while **requiring** `None` for `ways <= 0`. **The gate discriminates
correctly, caught a real event, and the measured values agree with it
independently.** One transient in 62 records, and no published magnitude is
touched: the analyzer's medians are taken over `status == "ok"` records only
(`:144`, `:197`), so the bad rep is already excluded.

**The registered-versus-house distinction, recorded before the outcome exists,
which is the whole point of recording it.** The pre-registration declares four
things that can stop something: the small-codebook kill, the S1-style void, the
CAT-tax condition on a *later* gem5 campaign, and the costume check. Grepped for
`certif`, `min_reps`, `transient`, `rep count` — **no hits**: the registration
contains **no certification rule, no rep-count requirement and no transient
policy.** The analyzer's `CERTIFY` line is therefore **not a registered gate
firing**. `analyze_silicon_ivf.py:290` computes `complete = (not probs and not
missing and len(reps) >= args.min_reps)` with `MIN_REPS = 5` (`:43`, an analyzer
constant), `record_problems` admits any `status != "ok"` (`:85`), and `:297` ANDs
`complete` with `gates_ok` into one headline. So one transient will print
**`CERTIFY: NO`** while every registered gate passes. **The wording that should be
used, and the reason it is available rather than invented: the analyzer already
draws this distinction in its own output and collapses it only in the headline.**
`:295-296` print `complete=` and `registered_gates_ok=` on separate lines, and
`:293` prints "a registered kill/void gate fired" **only** when `gates_ok` is
false. So the line to read is **`registered_gates_ok`**, not `CERTIFY`:
`registered_gates_ok=True` with `CERTIFY: NO` means *the registration was
satisfied and a house convention was not*. **Neither of the two available
misreadings is licensed.** Reporting a non-certification as a failed campaign
would be wrong, because no registered gate fired and the medians already exclude
the bad rep. **And relaxing the analyzer to make it green would be worse, for a
reason this pass can now supply as evidence rather than as preference:** the gate
that caught the transient, `G-mask-after`, is **itself unregistered** — it appears
nowhere in the pre-registration — so the registered set alone would have admitted
a rep in which the tenant demonstrably ran unconfined. **The house conventions are
doing real protective work, which means the registration is *incomplete* rather
than the analyzer over-strict, and the direction of repair is to register the
house gates by addendum, not to loosen them.** That settles the direction. It does
not settle the calibration: one event shows `MIN_REPS = 5` and the
zero-transient rule have non-zero power, and says nothing about whether 5 is the
right number, which is not answerable from a single failure and should not be
answered after seeing one.

**The pending `F21` fix is reclassified, and this is the actionable half of the
pass.** Recorded one pass ago as replacing the `(0,1]` check with a
`0.5083 ± 0.001` window and framed as a straightforward repair. **That framing is
superseded and quoted rather than deleted, per `A6.19`: "replace the `(0,1]` check
with a `0.5083 ± 0.001` window — the `F21` fix — which needs no tenant source
change if it is enforced in `ivf_gates.recall_check`, and that is the smaller
move."** The mechanics of that sentence are still right and the classification is
not: `(0,1]` is a **pre-registered specification**, so narrowing it is an
**amendment to a registered gate**, and project convention forbids adjusting a
gate after seeing results. It therefore requires a **pre-registration addendum
carrying its own justification** — that an absolute external anchor now exists and
did **not** exist when the costume check was specified on 2026-09-01, which is a
change in available evidence rather than a reaction to an outcome, and is the only
kind of justification that can license this — and it **must not be applied as a
silent edit to `ivf_gates.py`**. The `F20` fix, pinning `ref_id_sum = 147039988`,
is **not** in the same position: the pre-registration specifies no cross-arm
identity comparison at all, so that one adds a gate the registration never made
rather than narrowing one it did. **Both remain unapplied.** Nothing under
`experiments/asplos/silicon_e2e/` was modified in this pass — the campaign is live
and unattended, its launching worker having errored out — and neither
`analyze_silicon_ivf.py`, `ivf_flat_bench.cpp`, the pre-registrations, `c4`,
`gem5/` nor the paper was touched.

**The open count is unchanged: nine defects** — `F4`, `F13` (tenant side on
`ivf_flat`, prognosis ceilinged at host+toolchain scope), `F15`, `F16`, `F17`,
`F18` (gate half), `F19`, `F20` (gate class and mode scope) and `F21` (statement
refined, locus moved from the gate to its adoption, three clauses corrected). No
number is reserved and the next free number is **`F22`**; the standing wording
rules still have one member and the next free rule is `A1.R2`. **No published
magnitude moved and none is in question.** The live campaign's one transient is
excluded from its own medians by a filter that predates it, and the two
pre-registered gates that could void the campaign have not fired.

---

**Update 2026-09-04, silicon re-run routing pass.** **No defect registered and
none closed; the count stands at nine.** One standing rule added (`A1.R2`), a
third provenance state registered inside `F13`, a counter-measurement recorded
against `F20`'s realized half, **one of this ledger's own published-figure claims
falsified and rescoped**, and two of its citations withdrawn. Sources are
`SILICON_E2E_RERUN_OUTCOME_2026-09-04.md` (`7a72050`) with its §C addendum
(`49ffecb`), `SILICON_E2E_RERUN_GPRED_WAIVER_2026-09-04.md` (`d709bf7`, restored
`34f478a`), and `563ec54`, `f4eafdb`. `68c47ff` is pushed.

**The result, and the part of it that upgrades an argument this ledger recorded as
reasoning rather than measurement.** `G-exact` **PASSED** — recorded in `F20`'s
row, attributed rather than verified, the re-run's records being on `c4` and
deliberately not committed. The load-bearing upgrade is elsewhere: **the CAT
frontier is now measured unmoved rather than argued unmoved.** This ledger's
`F20` row justified "no published magnitude moves" *structurally* — "a defect
common to every arm cannot distort a comparison between arms", called at the time
"structural rather than lucky". The re-run tested it. `D3`, the registered
common-mode prediction, reports a mean signed shift of **+0.138 pp** protection
and **−0.191 pp** cost with absolute anchors inside **0.45%**, and **`cat01`,
which decides the registered CAT-tax kill, moves −0.048 pp.** So the cancellation
argument is confirmed by measurement where it could be tested, and the registered
kill decision is unmoved. **An a priori argument that survives a deliberate test
is worth more than the same argument unchallenged, and this ledger should say so
rather than only record the failures below.**

**"No published figure moves" is false as stated, and here is how it is scoped.**
The claim appears in this ledger in the `F20` row and in the silicon close-out, and
it was handed to this ledger as holding. **It holds by *arm*, not by dataset, and
the boundary is exact.** For the fifteen CAT arms and `nta` it holds and is now
measured. For the **three flush-behind arms** it fails and fails grossly: `D2`
(per-arm tenant cost, limit `max(1.0 pp, 2 × ENVELOPE_P95)`) is breached by
**−26.0 / −26.2 / −26.4 pp**, and `D1` (protection, limit `max(2.0 pp, …)`) by
**+12.2 / +13.6 / +16.1 pp**. `fig:frontier`(b)'s three `fb` points move from
about (45%, −6%) to about (58%, −32%). **The correction is not a lapse of
discipline but the pre-registration's own clause firing as designed**: `:297-301`
requires that any `D1`–`D4` failure be reported "loudly … prominently, not in a
footnote" and states it is "explicitly *not* permitted to relabel a material shift
as a correction and move on". Both workers did exactly that. **And the cause is
not the corruption, which is why the mechanism claim survives its own
counter-example.** §C traces it to `abccb31`, verified here at source: it inserted
`if (policy == "fbo")` **inside** `join_range_flushbehind`'s per-element loop
(`benchmarks/e2e/hash_join/src/cxl_join_bench.cpp`, the hunk at `@@ -594,8 +721,19
@@`), converting a bare guard into a string comparison plus `else if`. `policy` is
a `const std::string &` (`:707`, read here), `_mm_clflushopt`'s memory side
effects prevent hoisting, and **every arm passes `--policy wb`** — `extra_for`
(`run_hashjoin.py:169-174`) never emits `fbo` on silicon — so the comparison is
*always false and always evaluated*, 536,870,912 times per arm, as a PLT call to
`std::string::compare(char const*)` at `0x9421` where the old binary does three
ALU ops. **Two independent corroborations from this host.** The magnitude
arithmetic reproduces exactly: 42.78 Mt/s → 23.376 ns, 30.25 → 33.058, so
flush-behind adds **9.682 ns/tuple** in the clean binary against **1.242** in the
defective one, a residue of **8.440 ns/tuple** ≈ 24–32 cycles at 2.8–3.8 GHz. And
the disassembly is anchored to this function independently: `ents_per_line =
64 / sizeof(Fact) = 4` (`:711`), which is exactly the `test $0x3,%al` that appears
in both listings as the flush guard. **So the honest scope is: no flush-behind
cost number from *either* dataset is publishable — the old mis-joins and the new
measures a string comparison — and of the two the corrupted dataset's figure is
the closer estimate of the real quantity, which is an unwelcome sentence and is
recorded because it is true.** A one-line hoist and a re-measurement of three arms
is in progress. **This is the third defect bundled into `abccb31`**, after the
`prefault_region` corruption and the omitted `-mclflushopt`, which converts this
ledger's earlier concession about that commit's granularity into a third instance:
a commit that repairs three defects and introduces a fourth cannot be reviewed as
a unit, and its own record already conceded the point once.

**`cat06`'s separate `D1` breach is benign, diagnosed, and stays recorded as a
failure**, which is the right disposition. Its five clean reps are **bimodal** —
135.85, 123.93, 137.17, 123.61, 135.36, two clusters split three-to-two — so its
median lands in the upper cluster and the other split would have moved it by about
the whole observed 10.2 pp. The registered 3.42 pp envelope was bootstrapped from a
unimodal spread and understates that arm's variance. **The remedy is more reps, not
a fix, and `D1` is not un-fired because its cause is understood** — that is the
same discipline the `F21` costume-check pass established for a gate that fires on
a registered predicate.

**Two new defects, both routed into `F13` rather than given numbers.** The
launcher finding is in `F13`'s row as a **third provenance state**: a runner that
is **tracked but demonstrably was not on the path that produced the data**, which
is `F10`'s neighbour rather than its instance and the mirror of `F13`'s usual
failure. Verified **broken at birth** — `740bc69:6`, the creating commit, already
carries `../../..` — so no commit in this history ever held a working copy, the
same shape as this row's finding that no committed state could build the gem5
tenant. **And the citations that over-credited it are this ledger's own, both of
them, withdrawn in place**: `F20`'s row and its scoping passage each cite
`run_silicon_e2e.sh:7` as evidence that the campaign ran a particular tenant. The
conclusions stand on `sha_join` recorded 105 times; the citations do not. **The
detail worth keeping: `:7` is the line that expands `$ROOT`, so the defect sat on
line 6, directly above the line cited, and was read past twice.** A citation to a
line is not a reading of its dependencies — the same failure-to-apply shape that
produced `A1.R1`.

**The teardown defect closes an attribution this ledger left open one pass ago, and
the answer is us.** `IVF_FLAT_SILICON_OUTCOME_2026-09-04.md:272` recorded that "a
foreign process deleted the" CLOS group; the process is now named. An
unconditional `finally: teardown()` in both silicon runners destroyed `clos_b` on
**every** early exit, including `--self-test-only`, and a sibling runner's
self-test did exactly that mid-arm. **That is the mechanism this ledger derived
from committed code last pass and it is confirmed** — the prediction was that
`snapshot_clos` returns `mask_got_after=None` only when `/sys/fs/resctrl/clos_b` is
absent, so the group must have been deleted between setup and readback; the agent
of the deletion is now identified, reproduced on the host at `ways=5 mask=0x1f`,
the failing record's exact mask, failing with the old code and surviving with the
fix. Fixed at `563ec54`. **The limit is verified here and is larger than the fix
suggests:** `_CLOS_OWNED` guards only the **outermost** `finally` in each runner —
`run_hashjoin.py:499` and `run_ivf.py:517` — while each file has **seven**
`teardown()` call sites, so **six per runner remain unconditional**. Concurrent
campaigns are still unsafe and **exclusive host use remains a requirement, not a
courtesy.**

**The `pgrep` self-match became a rule and not a number: `A1.R2`, with the count
corrected from four to five.** Four is the project's own prior count, stated
independently at `gates.py:7-8` and `AGENT_BRIEF_SILICON_E2E_2026-09-01.md:161`,
**both predating the 2026-09-04 recurrence**, so the new instance is the fifth.
The full argument is in the rule; the short form is that it binds to no published
figure — the committed harness already reads `comm` — its polarity is the opposite
of `F20`/`F21`, which are gates that cannot fail whereas this is a probe that
cannot pass, and its remedy is already implemented **and regression-tested** in
`gates.py:196-199` from the defect itself. **The reason five documentations did not
stop it is that the remedy lives in a layer the error does not pass through:** the
recurrence happens at a shell prompt during ad-hoc verification, which never calls
`gates.py`. A sixth document would not have helped either.

**A coordination hazard, recorded as a note and not a number, because its subject
is dispatch rather than provenance.** Two workers were dispatched to one task and
neither knew of the other; the check for the first worker's output ran three
minutes before that worker committed its waiver, and the absence was read as
death. **The collision then reproduced the very defect under investigation** — the
second worker's CLOS diagnostics landed inside the first's `wb`/`nta` arms — and
the first run was correctly VOIDed at 11 records and relaunched. **It cost a run,
and it cost one wrong word that is now load-bearing in a directory name.** The
void directory is `VOIDED_2026-09-06_precedence_and_clos_contamination/`, and
**precedence was not a ground**: `34f478a` §A3 self-corrects `ae2626f`'s claim that
the stopped run's statistics "predate any waiver", and this pass verified the
sequencing independently — `d709bf7` committed 01:25:18, first record ts 01:28:06,
so the waiver led by **2 m 48 s**. The disqualification rests on contamination
alone. **Both workers behaved well under a hazard neither created**, and this is
recorded because good conduct under a process failure is evidence about the
process: the overwritten waiver was restored **byte-for-byte** — verified here, the
203 lines of `d709bf7` hash identically to the first 203 of `34f478a` — the false
precedence claim was self-corrected rather than dropped, and §C was appended as
**175 insertions with zero deletions**, verified by `--numstat`. **The lesson for
dispatch is the one `A1.R2` states in miniature: absence of output is not evidence
of death, and a three-minute window is not a liveness check.**

**One handed-back figure failed, and one piece of the waiver's own practice
improves guidance this ledger issued last pass.** The failure is small and is
reported rather than applied: the handback describes `c4`'s uncommitted tenant
source as "a **673**-line divergence", where the record it cites says **675**
(`SILICON_E2E_RERUN_OUTCOME_2026-09-04.md:132`, its only occurrence). Neither is
checkable from here — `c4` is out of bounds and the file is in no commit — so the
record's figure is carried and the discrepancy is noted rather than resolved. Its
role has also changed: `:132` sits under "What is therefore *not* established" and
was written *before* §C found the cause, so the delta is no longer a mystery to be
explained but a haystack with one identified needle in it. *(**Resolved 2026-09-04
later the same day by first-hand measurement, and the wording above is superseded
rather than deleted, per `A6.19`: "Neither is checkable from here … so the record's
figure is carried". It became checkable when both comparison inputs were placed on
this host, and the figure this ledger carried is the wrong one.** `/tmp/old_bench.cpp`
is `c4`'s uncommitted source, re-hashed here as `e8d104588c756bae…`, and
`/tmp/new_bench.cpp` is confirmed **byte-identical to the pre-hoist `HEAD` blob**
— `git show 77e06b6^:…/cxl_join_bench.cpp` hashes `b843d46595873e14…` and `diff`s
empty against it — which is the basis the clean re-run's tenant `a677c52d…` was
actually built from. **The count is 673**, re-derived here independently and then
confirmed by a second, unrelated tool: `diff | grep -c '^[<>]'` gives **673** over
2,367 lines against 2,974, and `git diff --numstat` gives **640 + 33 = 673**.
Against **post**-hoist `HEAD` it is **680**, and against `33eaf07` — `c4`'s actual
checkout commit — it is **799**, a figure no record states and which is the one a
reader might wrongly assume "divergence from the checkout" means. **The handback's
one claim that does not survive is that 675 "corresponds to no basis": it has an
exact and reproducible one.** `diff -u … | grep -c '^[-+]'` returns **675**,
because that pattern also counts the two unified-diff header lines `---` and
`+++`. Verified by displaying them. The third figure in play is explained the same
way from the other side: `grep -c '^[-+][^-+]'` returns **667** because it drops
**six** added *blank* lines, a bare `+` having no following character to match. So
**one pair of files yields 667, 673 and 675 under three counting rules, and all
three are "correct"** — which is the whole argument for `A1.R3` below, and it means
the record's 675 is a reproducible off-by-two with a named cause rather than a
number to be distrusted. Its author should be told the rule, not that the figure
was invented.)* **The improvement is to
this ledger's own guidance.** Last pass it recorded that the pending `F21` fix
"requires a **pre-registration addendum**". The waiver demonstrates a better
pattern and states the reason: it is a **separate document, explicitly not an
amendment**, because "the registration's value is that its predicates and
thresholds were frozen before any data existed, and appending to it would blur what
was registered ex ante with what was decided after seeing a failure". **That
reasoning applies with more force to the `F21` fix than to the waiver**, since the
`F21` fix narrows a predicate rather than overriding a precondition. So the
guidance is amended: the `F21` fix needs a **separate, dated waiver-or-narrowing
document that does not modify `IVF_FLAT_SILICON_PREREG_2026-09-01.md`**, and the
earlier wording "pre-registration addendum" is superseded and kept, per `A6.19`.

**The open count is unchanged: nine defects** — `F4`, `F13` (tenant side on
`ivf_flat`, prognosis ceilinged at host+toolchain scope, now carrying a third
provenance state and one located-bytes correction), `F15`, `F16`, `F17`, `F18`
(gate half), `F19`, `F20` (gate class and mode scope; realized half
counter-measured, `G-pred` waived not passed) and `F21` — plus `tab:gem5`'s +H2
column, `tab:fused`'s way-sweep runner and the stale Sec5 inline table. No number
is reserved and the next free number is **`F22`**. **The standing wording rules now
have two members, `A1.R1` and `A1.R2`; the next free rule is `A1.R3`.** **And this
is the first pass in this series in which a published figure did move**: the three
`fb` points of `fig:frontier`(b) are open, not corrected, and the cause is a
regression in the measuring tenant rather than anything about flush-behind or CXL.
Everything else in silicon e2e is measured unmoved.

---

**Update 2026-09-04, measurement of three carried figures.** **No defect
registered or closed; the count stands at nine.** One standing rule added
(`A1.R3`), **one figure this ledger carried last pass corrected by first-hand
measurement**, one apparent inconsistency between two records dissolved rather
than adjudicated, and one repair verified minimal. `c900534` is pushed. Nothing in
this pass touched the silicon outcome documents, `silicon_e2e/`, `c4`, `gem5/` or
the paper; a worker is mid-task on the first of those.

**The `673`/`675` question is settled by measurement and this ledger was on the
wrong side of it.** Last pass it carried the record's **675** over the handback's
**673** on the ground that neither was checkable from here, which was true at the
time and stopped being true when both comparison inputs were placed on this host.
**Re-derived first-hand rather than accepted, and confirmed by two unrelated
tools**: `diff | grep -c '^[<>]'` gives **673**, and `git diff --numstat` gives
**640 + 33 = 673**. The inputs were authenticated before use rather than trusted —
`/tmp/old_bench.cpp` re-hashes to `e8d104588c756bae…`, and `/tmp/new_bench.cpp` was
confirmed **byte-identical to the pre-hoist `HEAD` blob** by `diff` against
`git show 77e06b6^:…`, not merely by matching a quoted digest. **673 is the figure
and the basis is the pre-hoist `HEAD` blob, which is what the clean re-run's tenant
was built from.** Corrected in `F13`'s row.

**But the handback's own framing does not survive, and the part that fails is the
interesting part.** It reported that "**675 corresponds to no basis I can
construct**". It has an exact and reproducible one: `diff -u | grep -c '^[-+]'`
returns **675**, because that pattern counts the two unified-diff header lines
`---` and `+++` along with the content. Displayed here to be sure. And the third
figure resolves from the other side: `grep -c '^[-+][^-+]'` returns **667** because
it drops **six** added *blank* lines, a bare `+` having no following character.
**So one pair of files gives 667, 673 and 675, and all three are correct readings
of three different questions.** The record's 675 is therefore a **reproducible
off-by-two with a named cause, not an invented number**, which changes what is owed
to its author: the counting rule, not a correction. **That distinction is the
substance of `A1.R3`**, registered above, and the reason it is a rule rather than a
note is that the same phenomenon appeared **four** times in this one pass —
including once inside the handback that taught it, where the hoist's "7 lines added
and 1 changed" and git's "8 insertions, 1 deletion" describe the same commit under
two unstated conventions. **This ledger's own error last pass was not carrying the
wrong number; it was reporting a disagreement between two under-specified figures
as though one of them had to be false.**

**Two precedence figures, both correct, and the fix is to state referents rather
than to choose.** `d709bf7` is authored 2026-09-06 01:25:18 (re-verified; author
and committer dates identical, so that ambiguity does not arise). Against the
**VOIDed** run's first record, ts 01:28:06, precedence is **2 m 48 s** — this
ledger's figure, whose referent is the run that was *discarded*. Against the
**certified 105-record** run's first record, ts 01:43:58, it is **18 m 40 s** — the
other worker's figure, and **the one that matters, since it is the referent of the
dataset anyone will cite.** Both are now stated together in `F20`'s row with their
referents attached, because a reader comparing the two records would otherwise
conclude one is wrong, and neither is. **One disclosure that belongs with it:** the
18 m 40 s *arithmetic* is confirmed here (01:25:18 → 01:43:58), but its *input* is
not — ts `01:43:58` appears in no committed document in this clone, and `a8c9b83f`
is **not a valid object here even after `git fetch --all`**, a check run in that
order because `F13`'s own lesson forbids a reachability claim before a fetch. So
that figure is **sourced**; the 2 m 48 s one is **measured**. The distinction is
recorded, not smoothed. **This is the second time in three passes that two records
disagreed only by unstated referent** — the first being the `673`/`675` pair above
— and both are the same defect of phrasing rather than of measurement, which is why
`A1.R1` and `A1.R3` are now named as one family.

**The hoist is verified minimal, and it is the counter-example this ledger's
criticism of `abccb31` needed.** `77e06b6` touches **one file** and reports **8
insertions, 1 deletion**: six comment lines plus `const bool fbo = (policy ==
"fbo");`, and `if (policy == "fbo")` becomes `if (fbo)`. Diffed blob-to-blob here;
nothing else moved. **Two properties are worth the ledger's space.** *(i)* It
**deliberately leaves `policy == "nta"` in the loop**, and says why in-comment:
that comparison is present in the archived binary too, so hoisting it would break
comparability with `data/silicon_e2e_hashjoin.jsonl`. **A repair that declines to
fix an adjacent instance of its own defect, in order to preserve a comparison, is
the correct call and a rare one** — and it is the same reasoning this ledger
applied when it refused to touch `ivf_gates.py` mid-campaign. *(ii)* Its comment
names the **mechanism** rather than the symptom: `_mm_clflushopt`'s memory clobber
prevents the compiler proving the string's buffer unmodified across an iteration.
It also states a `1.34x` regression, which checks out against §C's own numbers
(33.058 / 24.728 = 1.337). **So `abccb31`'s granularity objection — carried in
`F13` and conceded by `BENCH_SOURCE_PROVENANCE` — now has its counter-example in
the same file: one defect, one commit, one file, the reason in the code.** A
criticism of a commit's granularity is worth more once the repository contains a
demonstration of the alternative, and it now does.

**The three flush-behind points remain OPEN, not corrected.** The hoist removes the
*cause*; the three-arm re-measurement has not run, so no `fb` cost number is
publishable from either dataset and `fig:frontier`(b)'s three points stay open.
Recorded explicitly because a reader who sees "cause found" and "fix landed" in one
pass will otherwise infer a correction that does not exist. **Nothing else in
silicon e2e moved**, and the fifteen CAT arms plus `nta` remain measured unmoved.

**The open count is unchanged: nine defects** — `F4`, `F13` (tenant side on
`ivf_flat`; the `c4` divergence figure now measured at **673** against a named
basis), `F15`, `F16`, `F17`, `F18` (gate half), `F19`, `F20` (gate class and mode
scope; both precedence referents now stated) and `F21` — plus `tab:gem5`'s +H2
column, `tab:fused`'s way-sweep runner and the stale Sec5 inline table. No number
is reserved and the next free number is **`F22`**. **The standing wording rules now
have three members — `A1.R1`, `A1.R2` and `A1.R3`, of which the first and third are
one family — and the next free rule is `A1.R4`.** **No published magnitude moved in
this pass**, and the one that moved in the last remains open rather than repaired.
