# DuckDB mmap-probe — declaration site, not STREAMING e2e

In-process DuckDB v1.1.3 table function over a file-backed probe `mmap`.
Hash table `b` stays a DuckDB table. Native identity gates only.

```bash
# smoke (any host)
make -C benchmarks/e2e/duckdb_mmap_probe test

# full geometry: mos182 / c4 only
experiments/asplos/run_duckdb_mmap_probe.sh --full
```

Needs `~/duckdb-1.1.3/libduckdb.so` (C API, same 1.1.3 family as the CLI).
Prereg: `experiments/asplos/DUCKDB_MMAP_PROBE_PREREG_2026-09-01.md`.
Outcome: `experiments/asplos/DUCKDB_MMAP_PROBE_OUTCOME_2026-09-02.md`.
