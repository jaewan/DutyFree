#!/usr/bin/env bash
# E1 pass B: the allocation frontier from the victim's side.
# Pre-registration: experiments/asplos/E1_FRONTIER_PREREG_2026-08-28.md
# Three quantities per split: the victim unconfined, the victim's OWN confinement
# cost (no tenant -- the control M12's P5 proved indispensable), and the victim's
# harm with the tenant present, stream retained or non-allocating.
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
VIC=$B/victim/pointer_chase
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/e1b_frontier}; REPS=${REPS:-6}
SEC=${SEC:-1}; TRIALS=${TRIALS:-6}; VCPU=${VCPU:-8}
TBL=134217728                       # 128 MiB, exact power of two
SPLITS=(2 4 8 12 16)                # tenant ways; victim gets 20-k
WSSL=(33554432 100663296 178257920) # 32 / 96 / 170 MB
mkdir -p "$OUT/stderr"; J="$OUT/e1b.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
for f in "$VIC" "$FUSED"; do [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }; done
echo "== as-found resctrl clos groups: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT

set_split() { # "" = torn down, else k tenant ways with the complement enforced to VCPU
  if [ -z "$1" ]; then sudo bash "$CLOS" teardown >/dev/null 2>&1
  else sudo bash "$CLOS" setup_c "$1" 32-47 "$VCPU" >/dev/null 2>&1; fi
}
# cell = "<k|none>:<wss>:<none|retain|flush>"
CELLS=()
for w in "${WSSL[@]}"; do CELLS+=("none:$w:none"); done              # unconfined baseline
for k in "${SPLITS[@]}"; do for w in "${WSSL[@]}"; do
  CELLS+=("$k:$w:none" "$k:$w:retain" "$k:$w:flush"); done; done
NC=${#CELLS[@]}; echo "== $NC cells x $REPS reps = $((NC*REPS)) runs"

for rep in $(seq 1 "$REPS"); do
  off=$(( (rep-1) * 7 % NC )); pos=0
  for i in $(seq 0 $((NC-1))); do
    IFS=: read -r k w mode <<< "${CELLS[$(( (i + off) % NC ))]}"
    pos=$((pos+1)); e="$OUT/stderr/rep${rep}_pos${pos}_k${k}_w$((w>>20))_${mode}.err"
    [ "$k" = none ] && set_split "" || set_split "$k"
    fpid=""; live=null
    if [ "$mode" != none ]; then
      fd=0; [ "$mode" = flush ] && fd=262144
      "$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g \
        --hot-bytes $TBL --morsel 1m --warmups 0 --reps 20000 --cpu-list 32-47 \
        --threads 16 --hit-rate 0.5 --flush-distance $fd >/dev/null 2>"$e" & fpid=$!
      sleep 4
    fi
    sch=$(cat /sys/fs/resctrl/clos_*/schemata 2>/dev/null | tr -d ' ' | grep -o 'L3:[^ ]*' | tr '\n' ';')
    [ -z "$sch" ] && sch="ROOT:$(grep -m1 L3 /sys/fs/resctrl/schemata 2>/dev/null | tr -d ' ')"
    o=$(mktemp)
    "$VIC" --cpu "$VCPU" --node 0 --wss "$w" --run-sec "$SEC" --trials "$TRIALS" >"$o" 2>>"$e"
    if [ -n "$fpid" ]; then
      kill -0 "$fpid" 2>/dev/null && alive=1 || alive=0
      grep -q HOT_TABLE_WARMED "$e" && warmed=1 || warmed=0
      grep -q HOT_TABLE_ROUNDED "$e" && { echo "FATAL table rounded (F9)" >&2; exit 4; }
      live="{\"alive_at_end\":$alive,\"warmed\":$warmed}"
      kill -TERM "$fpid" 2>/dev/null; sleep 1; kill -KILL "$fpid" 2>/dev/null; wait "$fpid" 2>/dev/null
      [ "$alive$warmed" != "11" ] && echo "  WARN tenant liveness k=$k w=$((w>>20)) $mode rep$rep" >&2
    fi
    med=$(python3 -c "
import json,statistics as st
d=json.load(open('$o')); v=[x['cycles_per_load'] for x in d]
print(f'{st.median(v):.4f}' if v else 'null')" 2>/dev/null)
    REC="{\"split\":\"$k\",\"wss\":$w,\"mode\":\"$mode\",\"rep\":$rep,\"pos\":$pos,\"victim_cyc_per_load\":${med:-null},\"tenant_liveness\":$live,\"schemata\":\"$sch\"}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad record" >&2; exit 3; }
    printf '  rep%-2s pos%-3s k=%-4s wss=%-4s %-6s victim=%-10s F=%s\n' \
      "$rep" "$pos" "$k" "$((w>>20))M" "$mode" "${med:-NA}" "$live"
    rm -f "$o"
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== E1b done: $(grep -c . "$J") records (expect $((REPS*NC))); clos groups left: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
