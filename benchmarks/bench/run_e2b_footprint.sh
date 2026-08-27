#!/usr/bin/env bash
# E2B: the victim decomposition on ONE stream size (1 GiB), tenant footprint swept.
# Pre-registration: experiments/asplos/E2B_FOOTPRINT_PREREG_2026-08-28.md
# No mask is ever applied; this is about the label alone.
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
VIC=$B/victim/pointer_chase
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
OUT=${1:-$B/../data/e2b_footprint}; REPS=${REPS:-8}
SEC=${SEC:-1}; TRIALS=${TRIALS:-6}; WSS=${WSS:-178257920}; VCPU=${VCPU:-8}
TABLES=(4194304 16777216 67108864 134217728 268435456)
mkdir -p "$OUT/stderr"; J="$OUT/e2b.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
for f in "$VIC" "$FUSED"; do [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }; done
g=$(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)
[ "$g" != "0" ] && { echo "FAIL $g resctrl groups present; E2B requires an unmasked machine" >&2; exit 2; }
echo "== resctrl verified clean (0 groups); no mask is applied by this runner"

CELLS=("base:0:none")
for t in "${TABLES[@]}"; do CELLS+=("t:$t:retain" "t:$t:flush"); done
NC=${#CELLS[@]}; echo "== $NC cells x $REPS reps = $((NC*REPS)) runs"
for rep in $(seq 1 "$REPS"); do
  off=$(( (rep-1) * 3 % NC )); pos=0
  for i in $(seq 0 $((NC-1))); do
    IFS=: read -r kind tbl mode <<< "${CELLS[$(( (i+off) % NC ))]}"
    pos=$((pos+1)); e="$OUT/stderr/rep${rep}_pos${pos}_${kind}$((tbl>>20))_${mode}.err"
    fpid=""; live=null
    if [ "$kind" = t ]; then
      fd=0; [ "$mode" = flush ] && fd=262144
      "$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g \
        --hot-bytes "$tbl" --morsel 1m --warmups 0 --reps 20000 --cpu-list 32-47 \
        --threads 16 --hit-rate 0.5 --flush-distance $fd >/dev/null 2>"$e" & fpid=$!
      sleep 4
    fi
    o=$(mktemp)
    "$VIC" --cpu "$VCPU" --node 0 --wss "$WSS" --run-sec "$SEC" --trials "$TRIALS" >"$o" 2>>"$e"
    if [ -n "$fpid" ]; then
      kill -0 "$fpid" 2>/dev/null && alive=1 || alive=0
      grep -q HOT_TABLE_WARMED "$e" && warmed=1 || warmed=0
      grep -q HOT_TABLE_ROUNDED "$e" && { echo "FATAL table rounded (F9) at $tbl" >&2; exit 4; }
      inst=$(sed -n 's/^HOT_TABLE .*bytes=\([0-9]*\) entries.*/\1/p' "$e" | head -1)
      live="{\"alive_at_end\":$alive,\"warmed\":$warmed,\"table_instantiated\":${inst:-null}}"
      kill -TERM "$fpid" 2>/dev/null; sleep 1; kill -KILL "$fpid" 2>/dev/null; wait "$fpid" 2>/dev/null
      [ "$alive$warmed" != "11" ] && echo "  WARN liveness t=$tbl $mode rep$rep" >&2
    fi
    med=$(python3 -c "
import json,statistics as st
d=json.load(open('$o')); v=[x['cycles_per_load'] for x in d]
print(f'{st.median(v):.4f}' if v else 'null')" 2>/dev/null)
    REC="{\"kind\":\"$kind\",\"table\":$tbl,\"mode\":\"$mode\",\"rep\":$rep,\"pos\":$pos,\"victim_cyc_per_load\":${med:-null},\"tenant\":$live}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad record" >&2; exit 3; }
    printf '  rep%-2s pos%-3s tbl=%-5s %-6s victim=%-10s T=%s\n' \
      "$rep" "$pos" "$((tbl>>20))M" "$mode" "${med:-NA}" "$live"
    rm -f "$o"
  done
done
echo "== E2B done: $(grep -c . "$J") records (expect $((REPS*NC))); resctrl groups: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
