# `tab:fused` raw data — pinned 2026-08-23

This directory backs `tab:fused` (Sec3) and its derived claims. It was
gitignored until now (`.gitignore:3 results/`); it is committed with
`git add -f` so that the paper's strongest experiment has raw data under
version control. See `experiments/asplos/W4.3_PROVENANCE_LEDGER_2026-08-23.md`
finding F1 for the audit that motivated this, and F8 and F9 for the two
defects it exposes.

**Nothing in this directory has been edited.** The files are as written by the
runner on 2026-07-29.

## Contents

| | files | note |
|---|---:|---|
| `raw/` | 660 | **canonical.** All nine published `tab:fused` rows recompute exactly from these. |
| `raw_v1_contaminated_with_hash_overhead/` | 512 | superseded. Kept because a referee who finds it referenced nowhere is worse off than one who finds it explained: these runs verified a per-tuple result hash inline, and the hash perturbs the timings. Do not quote. |
| `report.md`, `CLOS_SPLIT_FULL_REPORT.md`, `summary.csv`, `panel_summary.json` | 4 | runner-emitted summaries. |

## Known provenance defects — read before using this data

These are recorded in the ledger and are **not** fixed by committing the files.

1. **F1.2 — the way-sweep runner does not exist.** The three sweep rows
   (`bsweep_B_8way`, `bsweep_B_12way`, `bsweep_A_bsweep`) were produced by a
   script that is in no commit. `scripts/run_bsweep_RECONSTRUCTED.py`
   reconstructs the arms and marks what is unrecoverable.
2. **The applied way count is carried by the filename, not by the
   instrument.** `bsweep_*` records have **no `cmd` field and no CAT/way
   field** — compare a `panel_*` record, which does carry `cmd`. So
   "8way"/"12way" is an assertion of the filename. `app:kernel` must say so.
3. **F8 — at least two different, uncommitted binaries.** `bsweep_*` records
   emit `no_stream`; `panel_*` records do not. `--no-stream` first appears in
   committed source at `389c9f2` (2026-08-05), a week *after* this run, so the
   bsweep binary matches no commit at all. Both binaries are gone from
   `~/tmp_dutyfree_exp/.../build/cxl_join_bench`.
4. **F9 — the hot table is 256 MiB, not the 170 MB every record implies.**
   Every record stores `"hot_bytes": 177838489` (169.6 MiB), which is the
   *request*. `table_capacity()` rounds the entry count up to the next power of
   two, so the resident table is 2^24 x 16 B = **256 MiB = 80.0% of the
   8592+ LLC**. The measured numbers are unaffected; every geometry
   description of them is wrong. `HOT_TABLE_ROUNDED` (`fef3e5e`) makes future
   runs self-evidencing.

## Host

mos181, Xeon Platinum 8592+ (Emerald Rapids), 320 MiB LLC / 20 ways, 16 threads
on CPUs 32-47, fact stream on node 2 (CXL), hot table on node 0. n=30 per cell.
