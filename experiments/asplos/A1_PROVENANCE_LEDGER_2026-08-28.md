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
| F13 | **The `gem5.opt` behind every published magnitude in three campaigns was replaced in place on 2026-09-04, and at the moment of replacement its source state was captured by no commit.** Reserved here since 2026-09-04 and **registered for the first time today**, as `BUILD_PROVENANCE.md` asks in its §5 and its §"Open". Same family as `F10` — a result whose launcher was never committed — applied to the **simulator** rather than to the harness: "a transcript is not an artifact". Scope is the `h1bw_multicore`, `h1bw_cxlbw` and `h1bw_slice_bracket` campaigns. `cfd37207` (compiled 2026-08-31 12:40:39) produced all 21 completed `h1bw_mc_*_20260904` cells and was overwritten 2026-09-04 12:51; it survives only as tag `build-cb290444`'s sibling `build-cfd37207`, which is **a reproduction point for those 21 cells, not a photograph of the tree** (§3 states the three places it departs from one). `cb290444` produced the three `*_20260904fix` cells. A related half of the same defect: `gem5_sha256` is **not** sufficient provenance, because `configs/` is read from the working tree at run time, so the six `bwt` cells ran an 08-31 binary against an 09-03 `Ruby.py`. Prevention is **implemented at build time** (`gem5/scripts/build_gem5.sh`, `fa27f665db`) rather than in a run manifest, that being the only point where source and binary provably coexist. Four older compile dates in `gem5/logs/` console logs are covered by no tag and were not investigated; anything still cited from those runs carries this defect unrepaired. **Repaired in two halves on 2026-09-04, by two different actions, and the second landed while this row was being written.** *Identity:* commit `065fd80` advanced this repository's gem5 gitlink `b0eea53b → fa27f665`, so the recorded simulator is the one that produced the cells — a checkout at `b0eea53b` gets a gem5 without the `isStreaming` retry-path fix, i.e. one that cannot produce them. *Reachability:* a separate property, and this row first stated it as unrepaired. **That wording is superseded within the day and is quoted rather than deleted, per `A6.19`:** "Verified here today: all **19** STREAMING commits on the submodule's `pr4-work` are unreachable from every remote-tracking ref in this clone, and `b0eea53b` was **one of them**, so the pointer `065fd80` replaced was **already unfetchable from any clone**. `git submodule update` failed from a clone before `065fd80` and still does; what changed is which unfetchable commit is named. The build tags stand in the same position — `build-cb290444` has **18** unpushed ancestors and `build-cfd37207` **13** … **The remaining action is a push, not a commit**, and it is outside this repository's tree." **Every figure in that paragraph was correct when measured and the conclusion is now false**: `pr4-work` and all three build tags were pushed to `origin` at `2026-09-05 01:51:32 +0900` (KST; project-local 2026-09-04), which is after this row's check ran and before it was committed. Re-verified here after an explicit `git fetch --all`: `git rev-list HEAD --not --remotes` is **0**, `origin/pr4-work` resolves to `fa27f665db`, and `git ls-remote --tags origin` carries `build-cb290444`, `build-cfd37207` and `build-481d7e12` as annotated tag objects dereferencing to `a5f366456e`, `830905739a` and `1bb6418e01`. `BUILD_PROVENANCE.md` records the end-to-end check this ledger did not have to repeat: a throwaway clone of this superproject at `065fd80` followed by `git submodule update --init gem5` fetched from GitHub and checked out `fa27f665db`. **The lesson worth keeping is methodological**: `git rev-list --not --remotes` reads *local* remote-tracking refs, so an unfetched clone reports a push as absent — that is what happened here, and a reachability claim should be made only after a fetch. **Logged open on one remaining ground, and it is not the simulator.** The **superproject is unpushed** — `main` carries **95** commits absent from `origin`, whose `main` is still `73f0332f6c` — so the simulator is now obtainable while the pointer naming it is not visible to a third party. `BUILD_PROVENANCE.md` tracks that as a superproject push separate from `F13`, and this row agrees with that scoping: `F13`'s own subject, the simulator behind three campaigns, is **recoverable by commit and by label**. What the push did **not** touch are the two limits stated earlier in this cell — the four untagged compile dates, and `build-cfd37207` being a reproduction point rather than a photograph of its tree. **That last remaining ground is now discharged too, later the same day, and the wording above is superseded rather than deleted, per `A6.19`:** "The **superproject is unpushed** — `main` carries **95** commits absent from `origin`, whose `main` is still `73f0332f6c` — so the simulator is now obtainable while the pointer naming it is not visible to a third party." Verified here after a fetch and confirmed **server-side** rather than from local remote-tracking refs, which is the discipline this row's own lesson demands: `git ls-remote origin refs/heads/main` on `https://github.com/jaewan/DutyFree.git` returns **`322c9564ee`**, the push having moved `origin/main` `73f0332f6c → 322c9564ee` (**103** commits); `git ls-tree 322c956 gem5` records **`fa27f665db02`**; and `git ls-remote origin pr4-work` in the submodule resolves `pr4-work` to that same `fa27f665db02`. So a third party cloning the published superproject now reaches the simulator behind the three campaigns by pointer as well as by commit and label. **`F13` therefore closes outright.** Two things it does not license: the ninety-five figure was never re-derived and does not verify against anything measured here (the published range `73f0332f6c..322c9564ee` is **103** commits, and `322c9564ee..main` was in double figures and rising while this pass ran, other workers still committing), and the repository around the pointer is **not** fully published — what remains unpublished is enumerated in the close-out below. **One item is folded into this row rather than given a number of its own, because it is this row's second half — reachability of a pin — on the sibling submodule.** `c34305f` re-pinned `linux` `0f82e89 → 6a7e5b09bd8b`, a commit that existed only in the local submodule, so from the moment of that commit `git submodule update --init linux` could not succeed from any clone and the superproject could not usefully be published again. `081bc3d` registered the bump and misdiagnosed it: it recorded the loss as **searchability** — "`git log -- linux` names `c34305f` as the commit that re-pinned the prototype, and its message gives a reader no reason why" — and stated that "a clone gets the right kernel and nothing measured moves", which was false for any clone, the pointer being unfetchable rather than merely unexplained. Checked live in this pass rather than inherited, and it has since closed: the submodule's `origin/pr4-work` reflog records the push of `6a7e5b09bd8b` at **`2026-09-05 02:58:56 +0900`** (KST; project-local 2026-09-04), twenty minutes after `c34305f` and confirmed server-side by `git ls-remote`, so the pin is fetchable and `ae43f80e6793` — the gitlink the *published* commit carries — is reachable from that branch as well. Registered and closed inside one entry, like `F14`. **The reusable half is process, not provenance**: `git add` in a shared checkout is not a private operation. `c34305f` carries a `linux` gitlink its subject line never mentions because the path was staged by one worker and swept up by another's commit; stage and commit in one step, or accept that the next commit may not be yours | 09-04 | **closed** 2026-09-04, subject and remaining ground both |
| F16 | **For ten of the fourteen campaign pre-registrations, "this was pre-registered" is corroborated by nothing outside the document's own dated self-attestation, and for an eleventh it cannot be settled either way.** *(This row read **nine** until a birth-time re-audit later on 2026-09-04. The superseded headline is quoted rather than deleted, per `A6.19` — "**For nine of the fourteen campaign pre-registrations, 'this was pre-registered' is corroborated by nothing outside the document's own dated self-attestation.**" — and the two reclassifications that moved it, both verified here against the repository rather than accepted from the handback, are set out where the witness list used to be. The row's **verdict does not move and is better founded than when written**; see the birth-time paragraph at the end of this cell.)* All fourteen are now committed, and every citation in "Status history"'s freeze list verifies — but **commit order proves less than the commit dates suggest**, because the registration commits all landed in one 2026-09-04 pass (author timestamps read `2026-09-05 01:32–01:37`, this host's clock being **KST**, UTC+9, against the project-local UTC-7 by which records in this directory are dated — the convention `BUILD_PROVENANCE.md` states in its own dating note, and every wall-clock instant quoted in this row is labelled KST for the same reason), after the campaigns they register had run. Verified here today, campaign by campaign: **eight** registrations were committed **in the same commit as their own outcome document** (`SILICON_E2E_PREREGISTRATION` + `SILICON_E2E_OUTCOME` at `74e37b2`; `COMPLETE_JOIN_PREREG` + `COMPLETE_JOIN_OUTCOME` at `61c8a8e`; `H2H_REALJOIN_PREREG` at `61c8a8e`, whose verdict lives in two sections **of the registration itself**; `DUCKDB_TENANT_CAT_PREREG` at `cda8602`; `DUCKDB_MMAP_PROBE_PREREG` at `bff2622`; `IVF_LIST_DOM_PREREG` at `a1bfbfa`; `H1BW_MULTICORE_PREREG` at `a4b0c5e`; `H1BW_CXLBW_PREREG` at `b21cd21`), and in every one of those eight the campaign's **raw data was already committed in an earlier commit of the same pass** (`fee8417`, `ea28693`, `c271a22`, `931b248`, `7cd63f3`, `84dfd65`), so git witnesses the data preceding the registration rather than the reverse. A **ninth**, `FS_COMPLETE_JOIN_PREREG` at `fa30418`, is committed ahead of an outcome document that is still untracked, but behind r6b–r6e data that already existed on disk. **Filesystem mtimes cannot substitute, and there is a proof rather than an argument:** `COMPLETE_JOIN_OUTCOME_2026-09-01.md` is stamped `05:32:53` while its own `COMPLETE_JOIN_PREREG_2026-09-01.md` is stamped `05:32:58` — the outcome's mtime is **five seconds earlier** than the registration it followed, which is what a last-write timestamp records rather than a creation order. **Three of the fourteen hold an external witness, one is indeterminate, and the figure this row first published was five.** The superseded sentence is quoted rather than deleted, per `A6.19`: "**Five of the fourteen do hold an external witness**, and it is worth naming which: `DUCKDB_MMAP_SE_H2_PREREG` (`bff2622`), `AGGBW_WINDOW_PREREG` (`443b637`), `FB_ORACLE_PREREG` (`e2b1b90`) and `IVF_FLAT_SILICON_PREREG` (`a1bfbfa`) are committed and their campaigns have produced **no committed data and no outcome at all**, so git will witness precedence for them from here forward; and `H1BW_SLICE_BRACKET_PREREG` (`e35cfa3`) was deliberately committed **ahead of its outcome** — though its run data was already committed at `84dfd65`, so what git witnesses there is the registration preceding the *outcome document*, not the runs. One orphan qualifies that: `/tmp/fbo_validate` holds an `fbo`/`wb` run pair from 2026-09-03 13:06–13:21, referenced by no document, script or record in this repository, and named as an arm by no registration." **The surviving three are `DUCKDB_MMAP_SE_H2_PREREG`, `AGGBW_WINDOW_PREREG` and `IVF_FLAT_SILICON_PREREG`**, and the reason they survive is worth stating explicitly rather than left as a residue, because the error class that moved the other two **cannot reach them**: their witness is *absence of any data at all* plus a committed registration, which is a **forward-looking guarantee that never consults a timestamp**. There is no mtime, birth time or in-band stamp in their argument to have read wrongly, and nothing measured after the commit can precede it. That is the strongest form the property takes in a bulk pass, and it is also the emptiest — it licenses nothing about a campaign that has not run. **Two reclassifications, both verified here against the repository:** (1) `H1BW_SLICE_BRACKET_PREREG` was **miscounted as witnessed and is unwitnessed**. Its committed data carries an in-band `started`, and `data/gem5/h1bw_slice_bracket.jsonl`'s three cells read `2026-09-04T09:11:27+09:00` to `09:11:31`, against a registration commit `e35cfa3` at `2026-09-05 01:37:06` KST — the runs began **16 h 25 m 39 s before the registration was in git**, and the post-fix triple (`_20260904fix`, `12:52:44`) began 12 h 44 m before it. The cell had already conceded the substance ("what git witnesses there is the registration preceding the *outcome document*, not the runs"); what changes is that the concession is now measured rather than inferred, and the count is taken on one criterion — precedence over **run start** — instead of two. (2) `FB_ORACLE_PREREG` moves to **indeterminate**, and this row's own supporting claim about it was **false**. The orphan pair is not unregistered: `FB_ORACLE_PREREG_2026-09-03.md` §"Arms" registers exactly "`qui` / `wb` / `h2` / `fbo`, three seeds each, 12 runs", so `fbo` **is** a registered arm, and the `fbo`/`wb` pair in `/tmp/fbo_validate` is that registration's own **`P-O1`** check — "`fbo` must show a materially lower HNF occupancy/insertion count than `wb`", the first thing its own text says to check. In-band banners put it at `Sep 3 2026 13:06:48` (`wb`) and `13:21:50` (`fbo`), matching both directories' birth times to the millisecond and predating `e2b1b90` by **1 d 12 h 25 m 56 s**. So the witness cannot rest on absence of data, because data exists. It is **indeterminate rather than unwitnessed for a reason that runs the other way**, and the reason is recorded because it is the more interesting half: the pair is **one run per arm at the wrong geometry** — `--fact-bytes 2097152 --hot-bytes 1048576 --reps 2` against the registered `8388608`/`4194304`/`reps 1`, no victim process at all, and a different build directory (`build_Intel_8592_FBO`) — so it is a plumbing check and not a campaign cell; and the registration document's own **birth time is `2026-09-03 09:16:46`, 3 h 50 m 2 s *before* the earlier of the two runs**, which corroborates its attestation at exactly the point where git cannot. Neither reading is provable from a clone. Both are recorded. **This is a limit on external verifiability and not a defect in the claims, and the ledger says so deliberately** — the reasoning is in "Status history" below. **What is recoverable is recorded rather than assumed:** four of the fourteen are **not sealed originals**, and their amendment counts verify — `SILICON_E2E_PREREGISTRATION` 1 amendment, `COMPLETE_JOIN_PREREG` 1 addendum, `H2H_REALJOIN_PREREG` 5 (four addenda plus "Amendment 1, three corrections made AFTER data existed", which the document itself labels as such), `FS_COMPLETE_JOIN_PREREG` 7. The remaining ten carry no addendum at all. From `065fd80` forward **git witnesses every further change to all fourteen**, sealed or not, which is the half of the property that is now secured even though the originating half cannot be. **No number moves**, here or in the paper. **The birth-time re-audit that cost this row two witnesses also strengthened its verdict, and that belongs in the row rather than in a footnote.** The mtime pair this cell offers as its inversion proof inverts only in *mtime*: the birth times run the right way round, `COMPLETE_JOIN_PREREG_2026-09-01.md` born `2026-09-01 23:48:22.666` and `COMPLETE_JOIN_OUTCOME_2026-09-01.md` born `2026-09-02 05:02:16.092`, five hours and fourteen minutes apart in the order the documents assert — while their mtimes read `05:32:58` and `05:32:53`, five seconds the wrong way. And that registration's birth **precedes its own campaign's in-band launch by 4 min 21 s**: r5's first wave of fifteen arms reports `gem5 started Sep 1 2026 23:52:44` in fifteen separate logs. The pattern holds for every bulk-pass registration where an in-band launch time exists to check it against, measured here: `H1BW_SINGLECORE` **28.9 s**, `H1BW_SLICE_BRACKET` **35 s**, `H1BW_MULTICORE` **40 s**, `H1BW_CXLBW` **1 m 29 s**, `COMPLETE_JOIN` **4 m 21 s**, `DUCKDB_TENANT_CAT` **12 m 54 s** and `SILICON_E2E` **41 m 08 s** — in every case the document was **on disk before the campaign started**. So the filesystem **corroborates these attestations rather than contradicting them**; what it cannot do is show a reviewer, because git records no mtime, no ctime and no birth time and none of it survives a clone. That is precisely what "a limit on external verifiability, not a defect in the claims" was asserting when this row was written, and it is now founded on a measurement instead of on an argument. **Read the two facts together and not separately**: the same instrument that removed two witnesses from the count corroborated ten attestations, and neither result is available to anybody who has only the repository. **Paper exposure is one passage, not eight** — the eight registration-claiming passages were read and seven of them are git-witnessed; see "Status history". **One of those seven is now witnessed on a narrower ordering than the one first claimed for it**, and the exposure count survives that: `Appendix.tex:403` rests on `H1BW_SINGLECORE_PREREG`, whose registration commit is **21 m 46 s after its runs launched** and **25 m 45 s before the earliest of them reported** — so what git witnesses is the thresholds being fixed before any result existed, which is the ordering the word "pre-registered" needs there, and not the thresholds being fixed before the runs began, which the bullet in "Status history" originally claimed from a directory mtime. Corrected there, not rewritten | 09-04 | **open as a verifiability limit** 2026-09-04 |
| F17 | **A fail-closed gate whose instrument cannot observe the quantity at one of the levels its own campaign sweeps, or whose sample is taken at a point in the run schedule that differs by arm.** Registered here 2026-09-04 from `AMD_XSOCKET_OUTCOME_2026-09-04.md` §10, which proposed it and left the number to this table. Two instances, both in `AMD_XSOCKET_PREREG_2026-09-04.md`, both caught **by the gate failing** rather than by review, and both leaving that campaign **NOT CERTIFIED** (10 of 12 gates pass). (1) `G4` required ≥99% of the victim's pages on node 0 and read a histogram that filters mappings below 1024 pages; the campaign sweeps a **512 KB (384-page)** victim, which is invisible to it, so 200 of 400 runs scored 0% while the 4096 KB cells passed at 100%. The ≥99% threshold was **also** wrong for an unfiltered view, which fails even the primary cell at 87.2%, because ~457 pages of `libc`/`ld.so`/`libnuma` text are page-cache-resident on the other socket. (2) `G6b` required per-arm core-0 frequency to match the quiescent arm within 10% and sampled it **before the victim started** --- which in a co-run arm follows a 2-second settle sleep that lets core 0 drop to its 1.5 GHz minimum, and in a quiescent arm does not. It measured its own sampling schedule and split 3.1 GHz against 1.5 GHz with perfect correlation to placement. **Same root cause as two prior instances, which is why it is registered as a class rather than as two mistakes**: `BERGAMO_BACKINVAL_PREREG`'s `P1` was recorded as mis-specified for calibrating a threshold in one configuration and applying it in another, and `AMD_L3OCC_PREREG` opens by naming the recurring cause in as many words --- *"the instrument does not measure the quantity in the claim."* Distinct from **`F12`** (a criterion a crashed run could satisfy): `F12` is a gate too weak to fail, this is a gate that fails for a reason unrelated to what it tests. **Both questions were answered by fresh post-hoc diagnostics** (`broker/amd_xsocket_gatecheck.py`, `d23_gatecheck.jsonl`, n=5 per cell, disclosed as post-hoc) and both came back clean --- the 512 KB working set **is** on node 0, the size-invariant 457-page node-1 residue being `libc`/`ld.so` text shared with ~100 processes and identical in all five arms, and core 0 runs at **3.100 GHz in every one of 20 samples, in every arm, at both sizes** during the measured window --- so **no measurement is impeached and no number moves.** What is impeached is the certification. **The behaviour this row exists to reward is the diagnosis, not the failure**: the two gates were recorded as mis-specified rather than converted to passes, and the campaign's headline was held to the same standard --- Outcome A failed on the **lower (faster-than-baseline) edge by 2.8x10⁻⁴** under a two-sided rule the worker had frozen and did not loosen, and the primary cell was not relocated to the secondary 4096 KB cell that returns A cleanly. That is the same pattern that makes `F16`'s pre-registrations credible: a registration that goes on to fail its own thresholds and reports it. **Prevention worth registering**: a gate should be dry-run against every level of its campaign's own sweep before the campaign is frozen, and any gate reading a point-in-time sample must state where in the run schedule the sample is taken. **A third convention is registered alongside those two, from a different pass and the same category — fix the harness, not the record.** Every committed per-run record should carry an in-band `started` and `ended`, as the `h1bw_*` harness already does. Measured 2026-09-04: only **9 of the 30** committed `.jsonl` files under `data/` carry any in-band timestamp at all, in **two schemas** — ISO-8601 `started`/`ended` per record in the five `h1bw_*` files, and a single `ts` per record in `duckdb_tenant_cat.jsonl` and the three `silicon_e2e_*` files — and the remaining 21 carry none, `r5_runs.jsonl` and the two fused archives among them. The whole birth-time re-audit recorded at the end of this document, which cost two of `F16`'s witnesses and corrected four passages including two of this ledger's own, would have been a two-command check against those fields; instead it was done against tmpfs metadata that no clone can see and that means *launch* on one harness and *completion* on another. This is registered as a convention rather than as a defect number for the same reason as the two above: nothing measured is wrong, and the remedy is what the next harness does. Logged **open**; the remedy is a convention, not a patch, and the affected campaign is closed | 09-04 | **open** |
| F18 | **A simulator that quantizes a configured quantity and reports the unquantized one, with no output naming the difference; and records that then quote the requested figure as though it were realized.** Registered here 2026-09-04 from `NONPOW2_SETS_MEASURED_2026-09-04.md`, which proposed it and left the number to this table, as `AMD_XSOCKET_OUTCOME` did for `F17` and `BUILD_PROVENANCE.md` for `F13`. **Deliberately *not* a re-registration of the arithmetic.** The arithmetic is `[F9.4]` in `W4.3_PROVENANCE_LEDGER_2026-08-23.md` --- `CacheMemory::init()` computes `m_cache_num_sets = (size/assoc)/block`, takes `floorLog2` of it for the index width, and allocates the surplus sets without ever indexing them --- and it has been on record since 2026-08-23, with its LLC form worked out in `W7.2_A1_SIZING_2026-08-24.md`. **Note the numbering, because it crosses ledgers**: `F9.4` belongs to that document's series and appears nowhere in this table (checked: this ledger contains no `F9` at all), so a reader meeting both should not look for `F9.4` here. `F9.4` is a defect in a **computation**; `F18` is a defect in **observability plus record-keeping**, and it is why `F9.4` survived four separate enumerations of its own affected list and still reached a published ratio. Three components with three dispositions. **(1) The simulator was silent --- *repaired*.** At `--l3_size=7680KiB --l3_assoc=20`, `init()` allocated **6,144** sets, indexed **4,096**, and emitted no warning, no assertion and no stat, while `config.ini` faithfully recorded the *requested* `size=7864320`; every instrument the harness had reported the number that was wrong. Realized capacity is **5,242,880 B, 66.7% of configured**, verified here by arithmetic and by measurement. The repair is a `warn()` in `CacheMemory::init()` naming the realized capacity, at gem5 `c030d776ee` (read here, verbatim as the record quotes it). **`warn()` rather than `fatal_if`, and the reason is sound rather than convenient**: four committed launchers request affected geometries, and a fatal would break them at exactly the moment their realized geometry needs confirming --- the measurement below could not have been taken under one. **Proved inert, to the standard `BUILD_PROVENANCE.md` set for the `isStreaming` re-run**: all four probe cells were re-run pre- and post-guard and each differs on **5 lines out of 2,019 / 2,019 / 2,021 / 2,016**, all five being `hostSeconds`, `hostTickRate`, `hostMemory`, `hostInstRate` and `hostOpRate` --- re-derived here rather than accepted, including for **cell B, the cell that fires**. Pre-guard bytes preserved on disk as `gem5/build_Intel_8592/gem5.opt.pre-npot-guard.cb290444`, digest `cb2904444d…`; post-guard `d4e798601e…`; both `sha256sum`'d here and both matching. **The guard's second effect is worth more than the guard**: a run's console log now records reachable capacity, which is exactly the quantity `F9.4`'s own r5 wording cites as missing (*"no run emits a set count"*). **(2) A fail-closed gate read the wrong side --- *open*.** r5's `G0` was a requested-versus-realized gate that read a *requested* value on both sides: it required `l3_size_bytes == 7864320` and a `table/LLC` band computed against that same number, both sourced from `config.ini`'s `size=` field. **Same family as `F17`** --- an instrument that cannot observe the quantity in its own claim --- and it stays **open** because no artifact yet carries realized capacity for a *completed* run: the guard supplies it from that build forward only, so every campaign already on record is unauditable on this quantity except by re-derivation. Prevention is the same shape as `F17`'s: a gate must name the artifact carrying the **realized** quantity, and where none exists the gate is not yet implementable and should say so instead of passing. **(3) The records propagated it --- *corrected by addendum*.** `COMPLETE_JOIN_OUTCOME_2026-09-01.md` is wrong in **six** places including its own title, and `COMPLETE_JOIN_PREREG_2026-09-01.md` line 28 is the origin (`4/7.5 = 0.5333… = 32/60`); both now carry an Addendum 2 dated 2026-09-04 with the superseded wording quoted in place, per `A6.19`, and both were checked here as landed. **`F9.4`'s r5 cell is closed by measurement, and that is the substantive upgrade**: it stood as *"derived from source, not measured"*, and it is now measured. `--l3_size=7680KiB --l3_assoc=20` is **bit-identical to `--l3_size=5MiB --l3_assoc=20` on all 2,014 simulated quantities** --- 5 differing lines out of 2,019, all five host-side, confirmed here --- while `--l3_size=7680KiB --l3_assoc=15`, the *same requested bytes* at a power-of-two set count, differs from it on **914 lines (956 distinct stats)**. That control is what makes it an experiment rather than a demonstration, and its figure is corrected: the record reports it as 1,825, which is both sides of the same `diff` and is not the convention its neighbouring rows use; see the close-out below. **No published magnitude moves, and the reason is structural rather than lucky**: all **45** r5 runs share one realized geometry --- `l3_size_bytes = 7864320` in all 45 committed records, all `completed`, 15 arms, verified here --- and a ratio common to every arm cannot distort a comparison between arms, so `fig:frontier`(a) is **internally valid** and `P5`, the **+9.97%** wedge, the **+8.42%** matched-R wedge, `R(h2) = 22.59%` and the **1.185×** WB tax all stand as measured. Nothing is recomputed. **What is void is a claim and an argument, not a number.** r5 existed to move `table/LLC` from r3's 0.800 to silicon's 0.533; realized, it is **0.800**, and realized `victim/LLC` is **0.518** --- *both identical to r3's*, because 5 MiB against the same 4 MiB table and 2650 KiB victim is r3's geometry exactly (4,194,304/5,242,880 and 2,713,600/5,242,880, re-derived here). So r5 is **r3's cache geometry, not r3 with one knob fixed**, and Addendum 1's explanation of r5's fallen victim tax *by* a shrunken `victim/LLC` explains an effect with a cause that never occurred. **The supersession of r3 by r5 survives on the workload and not on the geometry** --- a complete join reporting tuples/s against a truncated join reporting IPC --- and that distinction is the part a reader would otherwise get wrong. **Blast radius audited rather than assumed, and one reasonable suspicion refuted.** `audit_nonpow2_sets.py` re-run here over every `config.ini` under `gem5/logs/` finds **one** affected distinct geometry and every L1I, L1D, L2, snoop filter and directory structure clean at every slice count; only r5 among campaigns with committed data. **`H1BW_SLICE_BRACKET` is clean**, and the suspicion against it was reasonable, since dividing a fixed total across a varying slice count is precisely how this defect arises unseen --- but it pins `L3_PER_SLICE=5MiB` and varies the slice count instead, so each slice is independently 4,096 sets and the *aggregate* varies. **`FB_ORACLE_PREREG_2026-09-03.md` is amended before it can run**, at zero cost to its `P-O2` reproduction check since the two flags name one machine, and its Amendment 1 was checked here as landed. `DUCKDB_MMAP_SE_H2` was affected and is **VOID with no arm run**. **Paper exposure: none, and the paper is the only artifact in this chain that stated realized values.** `Sec7:42-44`'s 1--3 pp CAT claim traces to `MODEL_SILICON_CAT_CALIBRATION_2026-09-01.md`, whose gem5 input is `rj3_runs.jsonl` --- **r3**, not r5 --- and it normalizes by CAT **way** fraction rather than bytes, which set-count quantization cannot touch; `0.533`, `7680`, `7864320`, `7.5 MiB` and `table/LLC` appear in no `.tex`. Logged **closed on repair** for component (1), **corrected** for (3), and **open** for (2) | 09-04 | **open** on the gate half |
| F19 | **An inline-asm statement that under-declares what the instruction writes.** Registered here 2026-09-04 from `M5OP_RAX_CLOBBER_AUDIT_2026-09-04.md` §8, which proposed it and left the number to this table. gem5 decodes the magic instruction as `BasicOperate::gem5Op` and its body ends `Rax = result;` **unconditionally** (`arch/x86/isa/decoder/two_byte_opcodes.isa:163`, read here), while `pseudo_inst.hh:140` sets `result = 0` before dispatch, so **every void m5op zeroes `%rax`**. This tree's wrappers declared only `"memory"`, which tells the compiler `%rax` survives. Realized in `mmap_probe.gem5`: the optimiser had scheduled the store of `mmap`'s return value into a global *after* an intervening `bind_pool` m5op, so the global took 0, `SET_STREAMING` was called with `addr=0`, and gem5's own trace records `setstreaming: addr=0 size=0x10000 -> 16/16 pages marked` — **16 pages of the tenant's own PIE image instead of the probe, and the probe never marked at all** (`DUCKDB_MMAP_SE_H2_HANDBACK_2026-09-04.md` §6). **Registered as a class, and the case for that is the second property below rather than the defect's severity.** *(i) It is silent in both directions.* The corrupted call still *succeeded*; the fill still worked, from a surviving `%rbp` copy, so nothing failed earlier and the tenant's own null check never fired. *(ii) **It is compiler-schedule dependent, and this is what makes it a class and not an `F18` instance.*** Identical source is safe in one binary and wrong in the next depending on optimization level and surrounding code, so **source review cannot settle it and only disassembly of the binary that actually ran can**. That is a different epistemic situation from every defect above it: `F18` was settled for every campaign from `config.ini` and arithmetic, with no binary required — this ledger closed `F9.4`'s r5 cell that way one pass ago — whereas here a lost binary makes the question permanently unanswerable. *(iii) It would have been misdiagnosed.* `P1` (`DUCKDB_MMAP_SE_H2_PREREG_2026-09-02.md:86`, `streamingHnfFillBypasses > 0` on `h2`) could never have passed, and the natural reading would have been "the m5op did not reach the HNF" — true, and completely misleading about why. *(iv) **It compounds `F13`.*** Three campaigns' *tenant* binaries no longer exist, so for those the class can only ever be argued and never disassembled; `F13` was until now a simulator-side defect and this is its tenant-side recurrence. **Distinct from `F18`** on (ii) and on the shape of the remedy: `F18`'s prevention is to *emit* the realized quantity, an observability fix, whereas `F19`'s is to *declare* the clobber, a contract fix that makes the question schedule-independent and therefore removes the need to observe it at all. **`fused.c` is the proof that the two are different**: it is clean *by construction*, a status no amount of output could confer and one `F18` has no analogue of. **Distinct from `F9`** — nothing here is recorded as configuration. **Audited across seven campaigns and no declared range was mismarked; no published claim is in doubt.** Re-verified here by re-running the committed instrument `audit_m5op_rax.py` rather than reading its output: `COMPLETE_JOIN`/r5 **CLEAN** on in-band evidence from the binary that ran (§below), `FUSED_KNEE` **CLEAN by construction**, `H1BW_SINGLECORE` **CLEAN** on hash-matched `2b9d6732`, `H1BW_MULTICORE`/`H1BW_CXLBW`/`H1BW_SLICE_BRACKET` **CLEAN** on hash-matched `cac9e27a`, `FS_COMPLETE_JOIN` r6b–r6e **CLEAN** on binaries extracted from their disk images, and **`H2H_REALJOIN`/r3 CLEAN on counters but INDETERMINATE on disassembly** — see the close-out for why that distinction is preserved rather than rounded up. **One genuine defect was found, in a path nothing runs, and its failure mode is safe**: in `join_range_flushbehind` (`--policy fbo`) `%rax` is the **loop induction variable** compared against a bound in `%rbp`, so the m5op zeroes it every iteration and the loop cannot terminate. Reproduced here in all three binaries that contain it (`cxl_join_bench.gem5` `0x40ced1`, `.gem5wbrk` `0x40cf11`, `.gem5fs` `0x40d7b1`, each reading `%rax` twelve bytes later). **Any cell taking that branch would have hung rather than produced a wrong number**, so no campaign can have used it silently — which is *stronger* than `BUILD_PROVENANCE.md`'s standing note that the opcode is compiled in but inert. **Fixed** by declaring `%rax` as an output operand — a register cannot be both an input constraint and a clobber — in 31 wrappers across 14 files, 19 committed and 12 applied but handed back because they are other workers' in-flight paths. **Prevention, in three parts.** A declared clobber is schedule-independent and is therefore the only durable fix. A runner that hashes the **tenant** binary, as `run_complete_join.sh` does at its lines 78–80 and `run_fused_knee.sh` does not at all, is the difference between "the binary is lost" and "we cannot even say what was lost". And **a third belongs beside `F17`'s and `F18`(2)'s, being the same pattern one level down — in the audit tool rather than in the experiment**: `0f 04` is an invalid opcode, so `objdump` desynchronizes past it and an enumerator driven off its output misses any second m5op emitted inside the first's desync shadow. This was not hypothetical — it hid two real sites in `cxl_join_bench.gem5wbrk`, and re-running the corrected instrument here finds them at `0x411b57` and `0x411b86`, each immediately following a `dump_stats` at `0x411b53` and `0x411b82`. `audit_m5op_rax.py` enumerates by raw byte scan of the PROGBITS sections instead. **An instrument that cannot observe the quantity in its own claim is now recorded three times in this table at three different levels: a campaign gate (`F17`), a simulator output (`F18`), and an audit tool (here).** Logged **closed on repair** for the executed paths and the one broken path, and **open** on r3's indeterminacy and on the twelve uncommitted wrapper fixes | 09-04 | **open** on r3 and on the handed-back fixes |
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
free number is **`F20`**. **Four of the six are now one family**, which is the
most useful thing this list says: `F17` (a campaign gate), `F18`(2) (a simulator
output), `F19`'s prevention note (an audit tool) and `F16` (a missing witness
rather than a missing instrument) are all the same failure — *the instrument
cannot observe the quantity in the claim* — recorded at four different levels of
the apparatus. `F19` is open on r3's indeterminacy, which no future work can
close, and on twelve wrapper fixes applied in the working tree and awaiting their
owners. **No published magnitude moves in this pass either.** `fig:frontier`(a),
`fig:recovery`, `tab:h1bw` and the full-system P1 claims are all confirmed to rest
on correctly-marked ranges; the paper is untouched and was read only.
