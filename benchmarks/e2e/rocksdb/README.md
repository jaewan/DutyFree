# RocksDB / LSM leg of the e2e search

Contributed by the ASPLOS'27 panel review of 2026-08-21 as *tooling plus
exploratory measurement*, not as a campaign. Read
`ROCKSDB_LSM_PANEL_FINDINGS.md` for the findings and, importantly, for the
disclosure of what these numbers can and cannot carry.

**These runs were NOT pre-registered** and therefore do not satisfy
`experiments/asplos/REPO_DISCIPLINE.md` §1. They were taken to answer a panel
question in one sitting. Any number here that a campaign wants to rely on must
be re-taken under a pre-registration, on a quiescent host.

## Scripts

- `scripts/run_ptr_cat_ceiling.py` — **the reusable one.** Applies the same CAT
  capacity-sensitivity gate as the GAPBS/HNSW runners (helpers are imported
  from `../gapbs/scripts/run_cat_sensitivity_gate.py`, so the mask floor and
  read-back behaviour cannot drift) to a bare dependent-load pointer chase
  (`~/tmp_dutyfree_exp/bin/victim -P`) across a working-set sweep. This
  measures the **host's own ceiling**: a real engine adds software work and
  memory-level parallelism per access, and both only lower the full/min ratio,
  so whatever a bare chase achieves at its best working-set size bounds every
  victim on that host. It costs minutes and should be run before any further
  victim is built.
- `scripts/run_rocksdb_cat_gate.py` — the same gate over a set of named
  `db_bench` configurations. Each configuration declares, in the source, the
  RocksDB structure whose reuse it is trying to place in the band the shared
  cache acts on.

## Build

No RocksDB release build existed on any of the three hosts; `/usr/bin/db_bench`
is the Ubuntu `rocksdb-tools` 9.11.2 package and is built **with assertions
enabled**, which it says so itself on every run. A matched release build at the
identical version:

    git clone --depth 1 --branch v9.11.2 https://github.com/facebook/rocksdb \
        /home/domin/rocksdb-9.11.2
    cd /home/domin/rocksdb-9.11.2
    DEBUG_LEVEL=0 PORTABLE=0 EXTRA_CXXFLAGS="-include cstdint -Wno-error" \
        EXTRA_CFLAGS="-Wno-error" make -j 96 db_bench

`-include cstdint` is required because gcc 15 no longer transitively includes
it; `-Wno-error` because gcc 15 raises warnings this release treats as errors.
Total build time under two minutes on 96 cores. `RDB_BIN` selects the binary.

## Environment

`RDB_CPU` (pinned victim CPU, overrides the per-host default),
`RDB_DBROOT` (default `/tmp/rdbgate`; `/tmp` is tmpfs on `mos181`),
`RDB_CONFIGS` (comma-separated config names), `RDB_INVOCATIONS`,
`PTR_WS_KB`, `PTR_DUR`, `PTR_INVOCATIONS`.
