#!/usr/bin/env bash
# M9: does tab:fused's restriction penalty survive a NON-ALLOCATING stream?
# Pre-registration: experiments/asplos/M9_STREAMCONTROL_PREREG_2026-08-26.md
# 2x2x2x2: cat {none,b4} x stream {retain,flush} x table {32 MiB fits, 169.6 MiB
# does not} x hit rate {0.5,1.0}. --no-stream is NOT used (footprint collapse,
# cxl_join_bench.cpp:1560-1569); the stream control is --flush-distance, which
# keeps footprint/node/loop/bytes identical and changes only residency.
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/m9_streamcontrol}; REPS=${REPS:-10}
TABLES=(33554432 177838489)   # 32 MiB fits the 64 MiB mask; 169.6 MiB is tab:fused's
HRS=(0.5 1.0)
mkdir -p "$OUT"; J="$OUT/m9.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
echo "== as-found resctrl clos groups: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT

CELLS=()
for hr in "${HRS[@]}"; do for t in "${TABLES[@]}"; do for sm in retain flush; do
  CELLS+=("none:$t:$hr:$sm" "b4:$t:$hr:$sm"); done; done; done
NC=${#CELLS[@]}; echo "== $NC cells x $REPS reps = $((NC*REPS)) runs"
CUR=unset
for r in $(seq 1 "$REPS"); do
  off=$(( (r - 1) * 3 % NC ))
  for k in $(seq 0 $((NC-1))); do
    IFS=: read -r cat tbl hr sm <<< "${CELLS[$(( (k + off) % NC ))]}"
    fd=0; [ "$sm" = flush ] && fd=262144
    if [ "$cat" != "$CUR" ]; then
      if [ "$cat" = b4 ]; then sudo bash "$CLOS" setup_b 4 32-47 >/dev/null 2>&1
      else sudo bash "$CLOS" teardown >/dev/null 2>&1; fi
      CUR=$cat
    fi
    sch=$(cat /sys/fs/resctrl/clos_*/schemata 2>/dev/null | tr -d ' ' | grep -o 'L3:[^ ]*' | tr '\n' ';')
    [ -z "$sch" ] && sch="ROOT:$(grep -m1 L3 /sys/fs/resctrl/schemata 2>/dev/null | tr -d ' ')"
    o=$("$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g \
         --hot-bytes "$tbl" --cpu-list 32-47 --morsel 1m --warmups 2 --reps 1 \
         --threads 16 --hit-rate "$hr" --flush-distance $fd 2>/dev/null | grep -o '{.*}' | tail -1)
    [ -z "$o" ] && { echo "  FAIL cat=$cat tbl=$tbl hr=$hr sm=$sm rep=$r" >&2; continue; }
    REC="{\"cat\":\"$cat\",\"table\":$tbl,\"hr\":$hr,\"stream\":\"$sm\",\"rep\":$r,\"pos\":$((k+1)),\"schemata\":\"$sch\",\"record\":$o}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad JSON cat=$cat tbl=$tbl hr=$hr sm=$sm rep=$r" >&2; exit 3; }
    cpa=$(printf '%s' "$o" | sed -n 's/.*"active_cycles_per_access":\([0-9.]*\).*/\1/p')
    printf '  rep%-3s pos%-3s %-5s tbl=%-10s hr=%-4s %-6s cyc/acc=%s\n' "$r" "$((k+1))" "$cat" "$tbl" "$hr" "$sm" "${cpa:-?}"
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== M9 done: $(grep -c . "$J") records (expect $((REPS*NC))); clos groups left: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
