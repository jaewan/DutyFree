#!/usr/bin/env bash
# E3 pass B: does the label-vs-partitioning trade-off travel to mos182's geometry?
# Pre-registration: experiments/asplos/E3_GEOMETRY_PREREG_2026-08-28.md
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
VIC=$B/victim/pointer_chase
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/e3b_tradeoff}; REPS=${REPS:-6}
SEC=${SEC:-1}; TRIALS=${TRIALS:-6}; VCPU=${VCPU:-8}; TCPUS=${TCPUS:-16-31}
TBL=33554432; WSS=33554432       # 32 MiB each; LLC is 60 MiB here
WT=$(python3 -c "print(bin(int(open('/sys/fs/resctrl/info/L3/cbm_mask').read().strip(),16)).count('1'))")
mkdir -p "$OUT/stderr"; J="$OUT/e3b.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
for f in "$VIC" "$FUSED"; do [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }; done
echo "== host $(hostname), $WT ways; tenant table $((TBL>>20))M, victim wss $((WSS>>20))M"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT

ARMS=(Valone Vconf T_none_retain T_none_flush T_mask_retain)
NC=${#ARMS[@]}; echo "== $NC arms x $REPS reps = $((NC*REPS)) runs"
for rep in $(seq 1 "$REPS"); do
  off=$(( (rep-1) % NC )); pos=0
  for i in $(seq 0 $((NC-1))); do
    arm=${ARMS[$(( (i+off) % NC ))]}; pos=$((pos+1))
    e="$OUT/stderr/rep${rep}_pos${pos}_${arm}.err"; fpid=""; live=null
    case $arm in
      Valone)  sudo bash "$CLOS" teardown >/dev/null 2>&1 ;;
      Vconf|T_mask_retain) sudo bash "$CLOS" setup_c 5 "$TCPUS" "$VCPU" >/dev/null 2>&1 ;;
      *)       sudo bash "$CLOS" teardown >/dev/null 2>&1 ;;
    esac
    if [ "${arm#T_}" != "$arm" ]; then
      fd=0; [ "$arm" = T_none_flush ] && fd=262144
      "$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g \
        --hot-bytes $TBL --morsel 1m --warmups 0 --reps 20000 --cpu-list "$TCPUS" \
        --threads 16 --hit-rate 0.5 --flush-distance $fd >/dev/null 2>"$e" & fpid=$!
      sleep 4
    fi
    sch=$(cat /sys/fs/resctrl/clos_*/schemata 2>/dev/null | tr -d ' ' | grep -o 'L3:[^ ]*' | tr '\n' ';')
    [ -z "$sch" ] && sch="ROOT:$(grep -m1 L3 /sys/fs/resctrl/schemata | tr -d ' ')"
    o=$(mktemp)
    "$VIC" --cpu "$VCPU" --node 0 --wss "$WSS" --run-sec "$SEC" --trials "$TRIALS" >"$o" 2>>"$e"
    if [ -n "$fpid" ]; then
      kill -0 "$fpid" 2>/dev/null && a=1 || a=0
      grep -q HOT_TABLE_WARMED "$e" && w=1 || w=0
      grep -q HOT_TABLE_ROUNDED "$e" && { echo "FATAL rounded" >&2; exit 4; }
      live="{\"alive_at_end\":$a,\"warmed\":$w}"
      kill -TERM "$fpid" 2>/dev/null; sleep 1; kill -KILL "$fpid" 2>/dev/null; wait "$fpid" 2>/dev/null
      [ "$a$w" != "11" ] && echo "  WARN liveness $arm rep$rep" >&2
    fi
    med=$(python3 -c "
import json,statistics as st
d=json.load(open('$o')); v=[x['cycles_per_load'] for x in d]
print(f'{st.median(v):.4f}' if v else 'null')" 2>/dev/null)
    printf '{"arm":"%s","rep":%s,"pos":%s,"victim_cyc_per_load":%s,"tenant":%s,"schemata":"%s"}\n' \
      "$arm" "$rep" "$pos" "${med:-null}" "$live" "$sch" >> "$J"
    printf '  rep%-2s pos%s %-14s victim=%-10s T=%s\n' "$rep" "$pos" "$arm" "${med:-NA}" "$live"
    rm -f "$o"
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== E3b done: $(grep -c . "$J") records; groups left: $(ls /sys/fs/resctrl | grep -c clos_ || true)"
