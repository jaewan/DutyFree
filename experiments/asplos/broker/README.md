# Broker-side (AMD / moscxl) experiment runners

These ran on `moscxl` (`ssh broker`, AMD EPYC 9754) and produced the AMD results
in `experiments/asplos/data/amd_*.jsonl`. They were previously **only** on that
host — an F10 (unpinned apparatus) instance, recorded in `HARNESS_MANIFEST.md`
and fixed by committing them here.

| file | produced |
|---|---|
| `amd_narrowmask.py` | `data/amd_narrowmask_v2.jsonl` — CAT way sweep, 8→1 ways |
| `amd_modes.py` | `data/amd_modes.jsonl` — module-free non-allocation probe |
| `bergamo_backinval.py` | `data/amd_backinval.jsonl` — 2×2×2 placement/WSS/THP factorial |
| `amd_l3occ.py` | `data/amd_l3occ.jsonl` — L3-occupancy instrument |
| `amd_wc_full.sh`, `amd_wc_stage.sh` | the WC path attempt; **blocked**, see `AMD_NARROWMASK_OUTCOME` |

## They will not run unmodified here

They hardcode `/home/domin/tmp_dutyfree_exp/bin` — the surviving tree on `moscxl`
holding the `victim`/`aggressor` binaries **dated 2026-08-23 that produced the
published AMD numbers**. That is deliberate: rebuilding those binaries would
confound any comparison against published AMD figures with a recompile. Copy this
directory to the AMD host to re-run.

`amd_wc_full.sh` offlines CXL memory and loads a kernel module. It restores on
every exit path including failure, and the module refuses to map a range that is
not provably disjoint from System RAM. **Read `AMD_NARROWMASK_OUTCOME_2026-08-30.md`
before running it** — it is currently blocked by host configuration, and the
blocker is not a bug.
