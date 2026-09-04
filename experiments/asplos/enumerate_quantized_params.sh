#!/usr/bin/env bash
# Enumerates every parameter in this project's configuration path that is
# quantised to an integer tick count by m5.ticks.fromSeconds, and reports
# requested versus realized for each.
#
# Mechanically complete by construction: the trace is emitted from
# SimObject.print_ini, so it covers every parameter that reaches config.ini
# whose Python type is Latency, Clock, Frequency, MemoryBandwidth or
# NetworkBandwidth -- the five types whose getValue() calls fromSeconds.
#
# quant_trace_instrument.py applies that hook to src/python/m5/SimObject.py on
# entry and reverts it on exit, so the tree is left clean; gem5 marshals
# src/python/ into the binary at build time, so the hook only takes effect
# under M5_OVERRIDE_PY_SOURCE=true and never needs a rebuild.
#
# The trace carries the requested SI value, so the relative error is computed
# offline for every parameter, including the ones below the 0.1% tolerance.
# The fixed guard's own warnings are collected alongside as an independent
# cross-check: the set the guard reports must equal the set the table computes
# as above 0.1%.
#
# Covers all four configurations this project has run: the baseline 4c and 8c,
# the single-slice bracket, and the two CXL-bandwidth brackets.
#
# Config-generation only; each gem5 is killed once it has written config.ini.
# Writes nothing under gem5/logs/.
set -u

ROOT=/home/domin/DutyFree
SCRATCH=$(mktemp -d /tmp/quant_enum.XXXXXX)
cd "$ROOT/experiments/asplos" || exit 1

INSTR=$ROOT/experiments/asplos/quant_trace_instrument.py

PGID=""
cleanup() {
  [ -n "$PGID" ] && kill -9 -"$PGID" 2>/dev/null
  python3 "$INSTR" revert
}
trap cleanup EXIT

python3 "$INSTR" apply || exit 1

# generate <tag> <ncores> <env assignments...>
generate() {
  local tag=$1 ncores=$2; shift 2
  local dir=$SCRATCH/$tag out i
  mkdir -p "$dir"
  env -u L3_SLICES -u CXL_MEM_BW "$@" \
    M5_OVERRIDE_PY_SOURCE=true DF_QUANT_TRACE=$dir/trace \
    OUTROOT=$dir STAMP=$tag \
    setsid "$ROOT/experiments/asplos/run_h1bw_multicore.sh" "$ncores" \
    > "$dir/runner.log" 2>&1 &
  local runner=$!
  sleep 1
  PGID=$(ps -o pgid= -p $runner 2>/dev/null | tr -d ' ')
  for i in $(seq 1 400); do
    out=$(ls -d "$dir"/h1bw_mc_wb_${ncores}c_* 2>/dev/null | head -1)
    [ -n "$out" ] && [ -s "$out/config.ini" ] && { sleep 8; break; }
    sleep 1
  done
  kill -9 -"$PGID" 2>/dev/null; PGID=""
  wait 2>/dev/null
  echo "$dir"
}

declare -A DIRS
DIRS[base4c]=$(generate base4c 4)
DIRS[base8c]=$(generate base8c 8)
DIRS[l3x1]=$(generate l3x1 4 L3_SLICES=1)
DIRS[bwt31]=$(generate bwt31 4 CXL_MEM_BW=32258064516B/s)
DIRS[bwt16]=$(generate bwt16 4 CXL_MEM_BW=62500000000B/s)

for tag in base4c base8c l3x1 bwt31 bwt16; do
  d=${DIRS[$tag]}
  echo "=============================================================="
  echo "$tag"
  echo "=============================================================="
  n=$(cat "$d"/trace.* 2>/dev/null | wc -l)
  echo "traced quantised params (all instances): $n"
  echo "guard warnings (fixed guard, tolerance 0.1%):"
  grep -hA1 -i 'rounding error' "$d"/h1bw_mc_wb_*/console.log 2>/dev/null \
    | grep -oE '[0-9.]+ rounded to [0-9]+' | sort | uniq -c | sort -rn \
    | sed 's/^/    /'
  echo
  cat "$d"/trace.* 2>/dev/null > "$SCRATCH/$tag.tsv"
done

echo "=============================================================="
echo "requested vs realized, all five configurations pooled"
echo "=============================================================="
python3 "$ROOT/experiments/asplos/audit_quantized_params.py" "$SCRATCH"/*.tsv

echo
echo "scratch kept at $SCRATCH"
echo "$SCRATCH" > /tmp/quant_enum.last
