#!/usr/bin/env bash
# M8: is tab:fused's restriction penalty a table-fit cliff at the 4-way (64 MiB)
# mask boundary, or stream interference independent of table size?
# Pre-registration: experiments/asplos/M8_TABLEFIT_PREREG_2026-08-26.md
# Arms are tab:fused's A3_16 (none) and B16 (b4, L3:0=f). Only --hot-bytes and
# --hit-rate vary. Cells interleaved and rotated per rep (F10).
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/m8_tablefit}; REPS=${REPS:-8}
# 4-way mask = 64 MiB on mos181 (20 ways x 16 MiB). 169.6 MiB is tab:fused's value.
TABLES=(4194304 16777216 33554432 67108864 134217728 177838489 268435456)
HRS=(0.5 1.0)
mkdir -p "$OUT"; J="$OUT/m8.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
echo "== as-found resctrl clos groups: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT

CELLS=()
for hr in "${HRS[@]}"; do for t in "${TABLES[@]}"; do CELLS+=("none:$t:$hr" "b4:$t:$hr"); done; done
NC=${#CELLS[@]}; echo "== $NC cells x $REPS reps = $((NC*REPS)) runs"
CUR=unset
for r in $(seq 1 "$REPS"); do
  off=$(( (r - 1) * 3 % NC ))
  for k in $(seq 0 $((NC-1))); do
    IFS=: read -r cat tbl hr <<< "${CELLS[$(( (k + off) % NC ))]}"
    if [ "$cat" != "$CUR" ]; then
      if [ "$cat" = b4 ]; then sudo bash "$CLOS" setup_b 4 32-47 >/dev/null 2>&1
      else sudo bash "$CLOS" teardown >/dev/null 2>&1; fi
      CUR=$cat
    fi
    sch=$(cat /sys/fs/resctrl/clos_*/schemata 2>/dev/null | tr -d ' ' | grep -o 'L3:[^ ]*' | tr '\n' ';')
    [ -z "$sch" ] && sch="ROOT:$(grep -m1 L3 /sys/fs/resctrl/schemata 2>/dev/null | tr -d ' ')"
    o=$("$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g \
         --hot-bytes "$tbl" --cpu-list 32-47 --morsel 1m --warmups 2 --reps 1 \
         --threads 16 --hit-rate "$hr" 2>/dev/null | grep -o '{.*}' | tail -1)
    [ -z "$o" ] && { echo "  FAIL cat=$cat tbl=$tbl hr=$hr rep=$r" >&2; continue; }
    REC="{\"cat\":\"$cat\",\"table\":$tbl,\"hr\":$hr,\"rep\":$r,\"pos\":$((k+1)),\"schemata\":\"$sch\",\"record\":$o}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad JSON cat=$cat tbl=$tbl hr=$hr rep=$r" >&2; exit 3; }
    cpa=$(printf '%s' "$o" | sed -n 's/.*"active_cycles_per_access":\([0-9.]*\).*/\1/p')
    printf '  rep%-2s pos%-3s %-5s tbl=%-10s hr=%-4s cyc/acc=%s\n' "$r" "$((k+1))" "$cat" "$tbl" "$hr" "${cpa:-?}"
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== M8 done: $(grep -c . "$J") records (expect $((REPS*NC))); clos groups left: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
