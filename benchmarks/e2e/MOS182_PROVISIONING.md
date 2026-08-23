# `mos182` provisioning record

Dated 2026-08-23. `mos182` (`ssh c4`) was idle but unprovisioned: no
`hostguard.py`, no DuckDB, no `cxl_join_bench`, a `DutyFree` checkout 208
commits stale at `ebd93a4`, and an `aggressor` binary that would not run.
This records what was installed, what was verified, and one provenance hazard
the work exposed.

## State at launch of any campaign here

| item | value |
|---|---|
| `DutyFree` HEAD | `33eaf07` |
| `tmp_dutyfree_exp` HEAD | `481115c` **plus uncommitted `src/aggressor.c` and `src/common.h`** |
| `hostguard.py` md5 | `38320f01831446605f6210c8aa708453` (identical on all three hosts) |
| `src/aggressor.c` md5 | `6d16f42de44e50a7a970087650767959` (identical on mos181, moscxl, mos182) |
| `src/common.h` md5 | `db65fc68c6a708299d3b51e14b8437ee` (identical on all three) |
| DuckDB | v1.1.3 `19864453f7`, md5 `ff25dd5491cdbf6a2e347cd949d9dcd8` |
| `cxl_join_bench` md5 | `d9c3fdc08374168fa9b0665d0ed17c25` |

Binary md5s are **not** comparable across hosts: everything is built
`-march=native` and the three machines are different microarchitectures. Source
md5 is the parity check that means anything, and it is recorded above.

## The provenance hazard, which is the important part of this document

**The aggressor that produced every published number in this project is built
from an uncommitted source file.**

`~/tmp_dutyfree_exp` is a second repository, separate from `DutyFree`. On mos181
and moscxl its `src/aggressor.c` is modified relative to its own `HEAD`
(`481115c`) and has never been committed. The modification is not cosmetic: it
adds the `-N <mem_node>` flag and the `wb_local` mode. `run_join_campaign.py`
passes `-N` on **every** arm, so the committed version of the aggressor cannot
run any campaign in this project.

mos182 had the committed version. Had it been built and used as found, it would
have failed at the first arm — visibly, which is the good case. The bad case is
the one to name: two hosts carry an instrument that exists in no repository, and
if either disk is lost the instrument that produced the Intel and AMD campaigns
is gone, with no way to rebuild it or to prove what it did.

Provisioning here was therefore done by copying `src/aggressor.c` from mos181
rather than by building what `tmp_dutyfree_exp` tracks, so that all three hosts
run a byte-identical instrument. mos182's committed version is preserved at
`src/aggressor.c.pre_provision_20260823`.

**Resolved 2026-08-23, by vendoring, on the lead's instruction.** The source
now lives in `benchmarks/e2e/instrument/`, with a manifest and a cross-host
drift check; see that directory's `README.md`. The md5 above is no longer the
only record of which aggressor produced which data.

Vendoring surfaced a second instance that this document had not found, and it
is worse than the one described above. `amd_flushbehind_aggressor.c` — which
produced the `FB0`/`FB256` arms, the primary de-confound pair of the AMD
campaign — was **untracked in any repository and present on `moscxl` alone**,
absent from mos181 and mos182 and from `tmp_dutyfree_exp`'s Makefile. It is
vendored too. Had that disk been lost, the source of a paper number would have
been gone outright, which is the §6.6 case rather than a hazard of it.

Two things vendoring did **not** do, both left for the lead. It did not change
what the hosts build from: the campaign scripts still resolve the streamer under
`~/tmp_dutyfree_exp/bin/`, so the vendored copy is monitored for drift rather
than authoritative. And it did not commit the modified files upstream in
`tmp_dutyfree_exp`, so they still have no hash of their own.

## What was installed

1. **`DutyFree` checkout** advanced `ebd93a4` -> `33eaf07` by git bundle from
   mos181 (`origin` does not have these 208 commits; nothing was pushed).
   Verified first that the 11 paths colliding with mos182's untracked
   `benchmarks/e2e/` were byte-identical, so nothing was overwritten, and that
   the five mos182-only artifacts (GAPBS and HNSW CAT gates) were already
   tracked in `DutyFree` with matching md5s. The 116 untracked build products
   under `gapbs/` and `hnsw/` were left in place.
2. **`hostguard.py`** arrived with the checkout, md5 matching the copy
   reconciled to moscxl on the same day (A6.11/A6.18).
3. **Instrument binaries** rebuilt natively from source in `~/tmp_dutyfree_exp`:
   `aggressor`, `victim`, `validate`, `latency_chase`, `intra_app_corun`. The
   previous `aggressor` was built against GLIBC_2.38 and mos182 has 2.35, so it
   did not run at all. `latency_chase` was rebuilt too; contrary to the note in
   `run_join_campaign.py`'s host table, the copy already present did run, so
   GLIBC was not blocking it. Old binary kept as
   `bin/latency_chase.glibc238_broken`.
4. **DuckDB v1.1.3** via `scripts_setup_duckdb.sh`.
5. **`cxl_join_bench`** built from `benchmarks/e2e/hash_join`;
   `--self-test reference` passes (`matches=262262`).

## What was verified

- `hostguard.py` survey returns `quiescent`; resctrl mounted, 15 ways
  (`cbm_mask 7fff`), 15 CLOSIDs, no foreign groups.
- Victim `cpu32` resolves to **L3 domain 1, 60 MiB, 15 ways** — the expected
  mos182 geometry, and package 1 per A4.7.
- NUMA: node 0 = cpus 0--31, node 1 = cpus 32--63, **node 2 = 256 GiB with no
  CPUs** (the CXL device). Distances 24 from node 0 and **14 from node 1**,
  confirming package 1 is the near socket, which is why A4.7 moved the victim
  there. 256 MiB allocated on node 2 from a node-1 CPU as a live check.
- All three aggressor modes the Intel arms need run and report bandwidth:
  `wb_load -N 2` 16.97 GB/s, `wb_prefetchnta -N 2` 11.31, `wb_load -N 1` 17.16,
  at 2 threads / 3 s. These are functional checks, **not measurements**, and no
  figure may be drawn from them.
- The A6.19 argv guard is present and fires here.
- DuckDB executes a query and reports the pinned version.

## What is still blocked

Provisioning does not unblock the mos182 campaigns. Still outstanding, and
**lead-only** per §9:

- the gate size re-derivation (24 MiB) and the ~96 MiB spill-point positive
  control (A4.8);
- the A5 latency ladder must be rebuilt *and pass from package 1* before any
  node-2 arm is credited — provisioning supplies the binary, not the pass;
- the `-n 4` parity defect in `GAPBS_DUCKDB_CORUN_PREREGISTRATION.md`.

The host itself is now ready to run one when those are decided.
