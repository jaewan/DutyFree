#!/usr/bin/env bash
# Launch both pre-registered bracket campaigns, detached so they survive the
# launching session ending.
#
#   Campaign A  H1BW_CXLBW_PREREG_2026-09-03.md
#               2 CXL bandwidth caps x 3 arms x {4,8} cores = 12 runs
#   Campaign B  H1BW_SLICE_BRACKET_PREREG_2026-09-03.md
#               --num-l3caches=1, 3 arms, 4 cores = 3 runs
#
# Analyze with:
#   analyze_h1bw_bracket.py cxlbw
#   analyze_h1bw_bracket.py slice
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
RUNNER=$HERE/run_h1bw_multicore.sh
LOGDIR=$HERE/logs
mkdir -p "$LOGDIR"
STAMP=$(date +%Y%m%d)

# Realizable ticks/byte only: SimpleMemory.bandwidth is quantised to an integer
# tick by m5.ticks.fromSeconds.  See the Campaign A pre-registration.
BW_T31=32258064516B/s     # -> 31 ticks/byte = 32.2581 GB/s
BW_T16=62500000000B/s     # -> 16 ticks/byte = 62.5000 GB/s

launch() {
  local tag=$1; shift
  local log=$LOGDIR/${tag}_$STAMP.log
  echo "=== $tag ===" > "$log"
  echo "cmd: $*" >> "$log"
  echo "started: $(date -Is)" >> "$log"
  setsid nohup env "$@" >> "$log" 2>&1 < /dev/null &
  echo "$tag  pid $!  log $log"
}

launch h1bw_cxlbw_t31 CXL_MEM_BW=$BW_T31 "$RUNNER" 4 8
sleep 3
launch h1bw_cxlbw_t16 CXL_MEM_BW=$BW_T16 "$RUNNER" 4 8
sleep 3
launch h1bw_slice_x1  L3_SLICES=1        "$RUNNER" 4

echo
echo "15 runs in flight (12 cxlbw + 3 slice)."
