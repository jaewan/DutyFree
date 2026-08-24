#!/usr/bin/env bash
# Diagnostic: V-alone read 201.33 in M1 and 78.09 in M1b, same binary, same
# wss=170MB, same cpu, both with CoV ~0.1%. One of them is an artifact and it
# decides whether M1's instrument falsifier was itself an artifact.
#
# Tests whether V-alone depends on history: run it cold, then after a fused
# tenant, then cold again, then after a stream aggressor, then cold again.
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
VIC=$B/victim/pointer_chase
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
AGG=$B/../e2e/instrument/bin/aggressor
WSS=${WSS:-178257920}; VCPU=${VCPU:-8}
v() { "$VIC" --cpu "$VCPU" --node 0 --wss "$WSS" --run-sec 1 --trials 6 2>/dev/null \
      | python3 -c "import json,sys,statistics as st; d=json.load(sys.stdin); print(f'{st.median([x[\"cycles_per_load\"] for x in d]):.3f}')"; }
hp() { grep -E "^HugePages_Free" /proc/meminfo | awk '{print $2}'; }

echo "step                         victim cyc/load   HugePages_Free"
printf "%-28s %14s   %s\n" "cold #1" "$(v)" "$(hp)"
printf "%-28s %14s   %s\n" "cold #2" "$(v)" "$(hp)"
printf "%-28s %14s   %s\n" "cold #3" "$(v)" "$(hp)"

"$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 256m \
  --hot-bytes 177838489 --morsel 1m --warmups 0 --reps 2000 --cpu-list 32-47 --threads 16 \
  >/dev/null 2>&1 & FP=$!
sleep 3
printf "%-28s %14s   %s\n" "WITH fused tenant" "$(v)" "$(hp)"
kill -TERM $FP 2>/dev/null; sleep 1; kill -KILL $FP 2>/dev/null; wait $FP 2>/dev/null
printf "%-28s %14s   %s\n" "after fused, +0s" "$(v)" "$(hp)"
sleep 5
printf "%-28s %14s   %s\n" "after fused, +5s" "$(v)" "$(hp)"

"$AGG" -m wb_load -t 8 -c 16,17,18,19,20,21,22,23 -N 2 -s 512 -d 120 >/dev/null 2>&1 & AP=$!
sleep 3
printf "%-28s %14s   %s\n" "WITH 23 GB/s streamer" "$(v)" "$(hp)"
kill -TERM $AP 2>/dev/null; sleep 1; kill -KILL $AP 2>/dev/null; wait $AP 2>/dev/null
printf "%-28s %14s   %s\n" "after streamer, +0s" "$(v)" "$(hp)"
sleep 5
printf "%-28s %14s   %s\n" "after streamer, +5s" "$(v)" "$(hp)"
