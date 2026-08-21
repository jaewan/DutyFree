# Artifacts

- `ptr_cat_ceiling_mos181.jsonl` — the reusable one: CAT full/min sweep over a
  bare pointer-chase working set on `mos181` cpu96. Peak sensitivity 4.067x at
  128 MiB. Contaminated host, see `../ROCKSDB_LSM_PANEL_FINDINGS.md` §2.
- `rocksdb_cat_gate_mos181.jsonl` — per-invocation records for the seven
  `db_bench` configurations, each carrying its installed mask, effective
  capacity, CMT occupancy, full command line, and `assertions_enabled`.
- `readmissing_perf_profile_mos181.txt` — flat `perf` profile of the
  `readmissing` / partitioned-filter configuration. `FastLocalBloomBitsReader::
  MayMatch`, the one access the paper's mechanism acts on, is 2.46% of cycles.
- `*.log` — console transcripts of each gate run, including the two runs whose
  configurations were wrong (`rdbgate_runB.log` has the 237 us/op mmap
  filter-checksum artefact and the unfrozen-LSM inversion). Retained on purpose:
  both are traps a future RocksDB arm can fall into.
