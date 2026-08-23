# Preserved raw for paper-bound tables that `results/` does not version

`.gitignore:3` excludes `results/` with the instruction "Preserve via a tarball /
GitHub Release, not the code repo." That was never done, so two published tables
rested on files that existed on mos181 and nowhere else. This directory closes
that gap for those two. See `../W4.3_PROVENANCE_LEDGER_2026-08-23.md` F1 and F3.

| Tarball | Backs | Contents | Taken | Runner |
|---|---|---|---|---|
| `clos_split_raw.tar.gz` (396K) | `tab:fused` — all 18 cells, verified to reproduce 2026-08-23 | `results/clos_split/`: 660 raw JSON (60 gate + 450 panel + 90 way-sweep + 60 l2-preview), `panel_summary.json`, `summary.csv`, both reports, and `raw_v1_contaminated_with_hash_overhead/` (390 runs, the discarded per-tuple-hash pass) | 2026-07-29 | `benchmarks/e2e/hash_join/scripts/run_confirmatory_panel.py` (added `389c9f2`, a week *after* the run); the way-sweep runner does not exist in the repo |
| `gem5_streaming.tar.gz` (2.5K) | `tab:h1bw` — all 12 numbers | `results/gem5_streaming/REPORT.md` | 2026-07-30 | gone (`/tmp/run_arm.sh`, `/tmp/run_arm_mshr.sh`, dead session) |

Integrity: `sha256sum -c SHA256SUMS`.

These are archives of state that already existed; nothing here was re-measured.
Preserving them does not repair the two real gaps — no commit binds the
`tab:fused` run, and no runner exists for its way-sweep rows — it only means a
disk failure no longer costs the paper its strongest table.
