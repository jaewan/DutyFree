# Calibration, silicon hash-join e2e

Date: 2026-09-01.  Apparatus, not a result.  Pre-registration
`SILICON_E2E_PREREGISTRATION_2026-09-01.md`.  Host mos182 (`c4`), idle.

The brief said a calibration run has never failed to find at least one
apparatus bug.  It found three, one of them in a runner that had not yet been
committed.

## What was run

`cxl_join_bench --mode single` + `pointer_chase`, tenant cpu 4 / victim cpu 6,
`--fact-node 0 --hot-node 0 --hit-rate 1.0 --huge2m`, 256 MiB fact × 32 MiB
table.  Binaries `join=75e0af947243` / `victim=026e357ae21a`, rebuilt on c4.

## Bugs the calibration caught

1. **Staged `/tmp/domin_silicon_e2e/sil_e2e.sh` (pre-commit).** `cat04` wrote
   `mask_got=-1` because it read `clos_c_scan` after a planned `setup_c`, and
   the tenant was `taskset -c 4` against default `--cpu-list 0`.  Those two
   records are not results.
2. **`--flush-distance` was a silent no-op in `--mode single`.**  The flag was
   parsed and echoed into JSON; `join_range` still ran.  Fixed: dispatch to
   `join_range_flushbehind`, and `join_path` in the JSON must read
   `flushbehind` or the arm is not an arm.  A gate that now fails on the old
   behaviour is in `tests/test_silicon_e2e.py`.
3. **v3 (`--inner-reps 1`, 256 MiB).** Every co-run `victim_cyc_per_load` was
   null.  The join lasted 0.40 s; `pointer_chase` was SIGTERM'd before
   finishing its first 1 s trial (stdout 0 bytes).  Quiet still read 73.402,
   matching the established 73.398 floor, so the victim binary was fine.
   Fixed: calib uses `--inner-reps 12` so the measure window is ~5 s, and
   `status=ok` requires `victim_n_trials >= 1`.
4. **First 8 GiB launch, `--huge2m`.** Tenant died with SIGBUS (signal 7) in
   1.5 s, empty stdio, `JOIN_MEASURE_BEGIN` never printed.  Cause: node 0
   holds 1024 hugepages (2 GiB); 35488 of the 36512 sit on node 2.  1 GiB and
   2 GiB `--huge2m` joins succeed; 8 GiB does not.  The pool is not moved.
   The 8 GiB campaign runs without `--huge2m` (verified: 42.44 Mtuples/s,
   12.6 s join, fact on node 0).  The runner now aborts on `no_begin` rather
   than writing 100 empty records.

## v4, gates that passed

Raw: `/tmp/domin_silicon_e2e/calib_v4.jsonl` on c4, copied to
`experiments/asplos/data/silicon_e2e_calib_v4.jsonl`.

| arm | tuples/s | victim cyc/load | mask |
|---|---|---|---|
| qui | — | 73.400 (sd 0.003) | — |
| wb | 42.13 | 179.0 | — |
| cat04 | 28.41 | 111.7 | `000f` (integer-equal to 4 ways) |
| cat08 | 34.86 | 156.5 | `00ff` |
| nta | 43.38 | 164.3 | — |
| fb256k | 39.65 | 137.8 | — ; `join_path=flushbehind` |

- G-idle, G-mask, G-clos, G-size (no `HOT_TABLE_ROUNDED`), G-live (identical
  match counts), mapped cpu 4, fact on node 0.
- Quiet 73.400 vs the previously established 73.398: 0.003% — the floor is
  still there.
- S1 would pass even at this scale: wb/qui = **2.44x**.
- CAT already costs the tenant in application units: **32.6% at 4 ways, 17.3%
  at 8 ways**.  That is the quantity the paper needs; it is not yet the
  registered 8 GiB geometry and is not to be cited as the campaign outcome.
- S2 cannot be judged: two CAT widths.  S3/S5 at this scale are not the
  registered claim.

v4 victim sd on co-run arms is 8–13 cycles (n=2, 0.5 s trials).  The 8 GiB
campaign uses 1 s trials and 5 reps.

## What this does not authorise

Citing v4 numbers in the paper.  Running STREAMING.  Treating S3/S5 FAIL at
256 MiB as refutations of the registered 8 GiB predictions.
