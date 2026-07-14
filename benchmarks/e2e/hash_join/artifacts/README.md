# Artifacts

Generated measurement outputs live here.

- `results.jsonl`: append-only raw benchmark records.
- `state.json`: resumability state for `scripts/run_all.py`.
- `logs/`: per-run stdout, stderr, and perf output.

Large logs are ignored by default. Promote only curated, reproducible results into `docs/RESULTS.md`.
