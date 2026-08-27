#!/usr/bin/env bash
# M12 pass A: the tenant's own cost AND LLC residency at a mask that protects the
# neighbour. Pre-registration: experiments/asplos/M12_ISOPROTECTION_PREREG_2026-08-28.md
# Primary metric is CMT llc_occupancy, not cyc/access -- the flush proxy's own
# 13-19% charge cancels the 12-16% effect being sought (registered up front).
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/m12a_isocost}; REPS=${REPS:-10}
TABLES=(33554432 67108864 134217728)   # 32/64/128 MiB -- ratios .25/.5/1.0 vs a 128 MiB mask
mkdir -p "$OUT"; J="$OUT/m12a.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
echo "== as-found resctrl clos groups: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT

occ() {  # F's group occupancy in bytes, or empty when unmasked
  cat /sys/fs/resctrl/clos_b/mon_data/mon_L3_00/llc_occupancy 2>/dev/null
}
CELLS=()
for t in "${TABLES[@]}"; do for m in none b8; do for sm in retain flush; do
  CELLS+=("$m:$t:$sm"); done; done; done
NC=${#CELLS[@]}; echo "== $NC cells x $REPS reps = $((NC*REPS)) runs"
CUR=unset
for r in $(seq 1 "$REPS"); do
  off=$(( (r - 1) * 5 % NC ))
  for k in $(seq 0 $((NC-1))); do
    IFS=: read -r mask tbl sm <<< "${CELLS[$(( (k + off) % NC ))]}"
    fd=0; [ "$sm" = flush ] && fd=262144
    if [ "$mask" != "$CUR" ]; then
      if [ "$mask" = b8 ]; then sudo bash "$CLOS" setup_b 8 32-47 >/dev/null 2>&1
      else sudo bash "$CLOS" teardown >/dev/null 2>&1; fi
      CUR=$mask
    fi
    sch=$(cat /sys/fs/resctrl/clos_*/schemata 2>/dev/null | tr -d ' ' | grep -o 'L3:[^ ]*' | tr '\n' ';')
    [ -z "$sch" ] && sch="ROOT:$(grep -m1 L3 /sys/fs/resctrl/schemata 2>/dev/null | tr -d ' ')"
    err=$(mktemp)
    "$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g \
         --hot-bytes "$tbl" --cpu-list 32-47 --morsel 1m --warmups 2 --reps 1 \
         --threads 16 --hit-rate 0.5 --flush-distance $fd >"$err.out" 2>"$err" &
    fpid=$!
    # sample occupancy while the measured window is live, take the max
    omax=0
    while kill -0 $fpid 2>/dev/null; do
      v=$(occ); [ -n "$v" ] && [ "$v" -gt "$omax" ] 2>/dev/null && omax=$v
      sleep 0.15
    done
    wait $fpid 2>/dev/null
    o=$(grep -o '{.*}' "$err.out" | tail -1)
    inst=$(sed -n 's/^HOT_TABLE .*bytes=\([0-9]*\) entries.*/\1/p' "$err" | head -1)
    rounded=$(grep -c HOT_TABLE_ROUNDED "$err" || true); rm -f "$err" "$err.out"
    [ -z "$o" ] && { echo "  FAIL $mask tbl=$tbl $sm rep=$r" >&2; continue; }
    [ "$rounded" != "0" ] && { echo "FATAL table silently rounded (F9) -- aborting" >&2; exit 4; }
    REC="{\"mask\":\"$mask\",\"table\":$tbl,\"table_instantiated\":${inst:-null},\"stream\":\"$sm\",\"rep\":$r,\"pos\":$((k+1)),\"llc_occupancy_max\":$omax,\"schemata\":\"$sch\",\"record\":$o}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad JSON" >&2; exit 3; }
    cpa=$(printf '%s' "$o" | sed -n 's/.*"active_cycles_per_access":\([0-9.]*\).*/\1/p')
    printf '  rep%-2s pos%-3s %-4s tbl=%-10s %-6s cyc/acc=%-9s occ=%s MiB\n' \
      "$r" "$((k+1))" "$mask" "$tbl" "$sm" "${cpa:-?}" "$((omax/1048576))"
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== M12a done: $(grep -c . "$J") records (expect $((REPS*NC))); clos groups left: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
