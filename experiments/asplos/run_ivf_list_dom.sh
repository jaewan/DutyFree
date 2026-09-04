#!/usr/bin/env bash
# IVF-Flat list-dominated declaration site. Pre-registration:
#   experiments/asplos/IVF_LIST_DOM_PREREG_2026-09-02.md
# Native identity only. Not H2, not CAT, not gem5.
# --full is mos182 / ssh c4 only. Do not run on mos181.
# Do not invoke run_silicon_ivf.sh from this runner.
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
    *) echo "FATAL: --full is c4/mos182 only (host=$HOST). Do not run on mos181." >&2; exit 2 ;;
  esac
fi
BIN=$ROOT/benchmarks/e2e/ivf_flat/build/ivf_flat_bench
if [ ! -x "$BIN" ]; then
  make -C "$ROOT/benchmarks/e2e/ivf_flat" native
fi
if [ "$FULL" = 1 ]; then
  OUT=${OUT:-$ROOT/experiments/asplos/data/ivf_list_dom.jsonl}
  if [ -e "$OUT" ]; then
    echo "FATAL: $OUT exists (A6.19)" >&2
    exit 2
  fi
  mkdir -p "$(dirname "$OUT")"
  LDIR=${LDIR:-/tmp/ivf_list_dom_full}
  mkdir -p "$LDIR"
  "$BIN" --preset list_dom --identity --require-list-dom --require-recall --json \
    --lists-file "$LDIR/lists.bin" | tee "$OUT"
else
  exec "$BIN" "$@"
fi
