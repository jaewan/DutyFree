#!/usr/bin/env bash
# DuckDB mmap-probe declaration site. Pre-registration:
#   experiments/asplos/DUCKDB_MMAP_PROBE_PREREG_2026-09-01.md
# Native identity only. Not H2, not CAT, not gem5.
# --full is mos182 / ssh c4 only. Do not run on mos181.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
HOST=$(hostname -s)
FULL=0
for a in "$@"; do
  [ "$a" = "--full" ] && FULL=1
done
if [ "$FULL" = 1 ]; then
  case "$HOST" in
    mos182|c4) ;;
    *) echo "FATAL: --full is c4/mos182 only (host=$HOST)" >&2; exit 2 ;;
  esac
fi
export DUCKDB_HOME=${DUCKDB_HOME:-$HOME/duckdb-1.1.3}
export LD_LIBRARY_PATH=${DUCKDB_HOME}:${LD_LIBRARY_PATH:-}
BIN=$ROOT/benchmarks/e2e/duckdb_mmap_probe/build/mmap_probe
if [ ! -x "$BIN" ]; then
  make -C "$ROOT/benchmarks/e2e/duckdb_mmap_probe"
fi
if [ "$FULL" = 1 ]; then
  OUT=${OUT:-$ROOT/experiments/asplos/data/duckdb_mmap_probe.jsonl}
  if [ -e "$OUT" ]; then
    echo "FATAL: $OUT exists (A6.19)" >&2
    exit 2
  fi
  mkdir -p "$(dirname "$OUT")"
  "$BIN" --mode both --mprotect streaming --outdir /tmp/duckdb_mmap_probe_full \
    --n 838864 --probe 10000000 --chain 8 | tee "$OUT"
else
  exec "$BIN" "$@"
fi
