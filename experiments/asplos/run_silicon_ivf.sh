#!/usr/bin/env bash
# Silicon IVF-Flat e2e scaffold.  Pre-registration:
#   experiments/asplos/IVF_FLAT_SILICON_PREREG_2026-09-01.md
# STREAMING is not measured.  Do not run on mos181.
# No IVF campaign is started by creating this file; invoke only on exclusive mos182.
set -euo pipefail
# experiments/asplos -> DutyFree (two levels). The hash-join wrapper walks
# three; this one is pinned to the DutyFree root the kernel lives in.
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
IVF=${IVF:-$ROOT/benchmarks/e2e/ivf_flat/build/ivf_flat_bench}
VIC=${VIC:-$ROOT/benchmarks/bench/victim/pointer_chase}
PY=${PY:-python3}
exec "$PY" "$ROOT/experiments/asplos/silicon_e2e/run_ivf.py" \
  --ivf "$IVF" --victim "$VIC" "$@"
