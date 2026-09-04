# Preserved raw for paper-bound tables that `results/` does not version

`.gitignore:3` excludes `results/` with the instruction "Preserve via a tarball /
GitHub Release, not the code repo." That was never done, so two published tables
rested on files that existed on mos181 and nowhere else. This directory closes
that gap for those two. See `../W4.3_PROVENANCE_LEDGER_2026-08-23.md` F1 and F3.

**Only one of the two is still published.** `tab:h1bw` was replaced on
2026-09-04 by a pre-registered campaign that retains its own artifacts, so the
second row below archives a withdrawn claim rather than backing a live one.
Archiving a summary was never provenance for the figures it summarised:
preserving it recorded the claim, and replacing the table is what closed the
gap.

| Tarball | Backs | Contents | Taken | Runner |
|---|---|---|---|---|
| `clos_split_raw.tar.gz` (396K) | `tab:fused` — all 18 cells, verified to reproduce 2026-08-23 | `results/clos_split/`: 660 raw JSON (60 gate + 450 panel + 90 way-sweep + 60 l2-preview), `panel_summary.json`, `summary.csv`, both reports, and `raw_v1_contaminated_with_hash_overhead/` (390 runs, the discarded per-tuple-hash pass) | 2026-07-29 | `benchmarks/e2e/hash_join/scripts/run_confirmatory_panel.py` (added `389c9f2`, a week *after* the run); the way-sweep runner does not exist in the repo |
| `gem5_streaming.tar.gz` (2.5K) | **nothing that is still published.** It holds a hand-written summary report and **no per-run artifacts**, so it records what was claimed and is not provenance for it: there is no `stats.txt`, no `config.ini`, no per-run JSON and no runner behind any of the twelve figures it summarises. As of 2026-09-04 those twelve figures are **superseded and no longer in the paper** — `tab:h1bw` now carries six certified cells from `../H1BW_SINGLECORE_OUTCOME_2026-09-04.md`, which retains its counters, so this tarball is a historical record of a withdrawn claim rather than the backing for a live one (`../A1_PROVENANCE_LEDGER_2026-08-28.md` F3; `../H1BW_ARM_IDENTITY_2026-09-04.md` §Q2, which also establishes that its third arm was mislabelled `WC` and was in fact prefetch-off) | `results/gem5_streaming/REPORT.md` — one 4,609-byte markdown file, and nothing else | 2026-07-30 | gone (`/tmp/run_arm.sh`, `/tmp/run_arm_mshr.sh`, dead session) |

Integrity: `sha256sum -c SHA256SUMS`.

These are archives of state that already existed; nothing here was re-measured.
Preserving them does not repair the two real gaps — no commit binds the
`tab:fused` run, and no runner exists for its way-sweep rows — it only means a
disk failure no longer costs the paper its strongest table.
