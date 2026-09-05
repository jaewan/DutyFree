#!/usr/bin/env bash
# Silicon hash-join e2e.  Pre-registration:
#   experiments/asplos/SILICON_E2E_PREREGISTRATION_2026-09-01.md
# STREAMING is not measured.  Do not run on mos181.
set -euo pipefail
# This script lives in experiments/asplos, so the repo root is two levels up,
# not three.  With ../../.. it resolved to the parent of the checkout, every
# path below pointed at a file that does not exist, and the launcher could not
# start the campaign at all -- the registered 105-record run reached the runner
# by some other invocation.
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
JOIN=${JOIN:-$ROOT/benchmarks/e2e/hash_join/build/cxl_join_bench}
VIC=${VIC:-$ROOT/benchmarks/bench/victim/pointer_chase}
PY=${PY:-python3}
exec "$PY" "$ROOT/experiments/asplos/silicon_e2e/run_hashjoin.py" \
  --join "$JOIN" --victim "$VIC" "$@"
