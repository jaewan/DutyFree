#!/usr/bin/env bash
# DuckDB tenant CAT on silicon.  Pre-registration:
#   experiments/asplos/DUCKDB_TENANT_CAT_PREREG_2026-09-01.md
# STREAMING / nta / flush-behind are not measured.
# Host mos182 / ssh c4 only.  Do not run on mos181.
# Do not start the 15-wide frontier unless the host is exclusive/idle.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
DUCKDB=${DUCKDB:-$HOME/duckdb-1.1.3/duckdb}
VIC=${VIC:-$ROOT/benchmarks/bench/victim/pointer_chase}
PY=${PY:-python3}
exec "$PY" "$ROOT/experiments/asplos/duckdb_tenant_cat/run_tenant.py" \
  --duckdb "$DUCKDB" --victim "$VIC" "$@"
