#!/usr/bin/env bash
# M1: does a fused tenant harm a neighbour at all?
# Pre-registration: experiments/asplos/M1_THREEPARTY_PREREG_2026-08-25.md
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
HJ=$B/../e2e/hash_join
VIC=$B/victim/pointer_chase
FUSED=$HJ/build/cxl_join_bench
STREAM=$B/aggressor/stream_wb
OUT=${1:-$B/../data/m1_threeparty}
REPS=${REPS:-6}; SEC=${SEC:-5}; WSS=${WSS:-4194304}; VCPU=${VCPU:-8}
mkdir -p "$OUT/stderr"; JSONL="$OUT/m1.jsonl"
[ -e "$JSONL" ] && { echo "FAIL $JSONL exists (A6.19)" >&2; exit 2; }
for f in "$VIC" "$FUSED" "$STREAM"; do [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }; done

start_co() { # $1=arm -> echoes pid, or empty
  case $1 in
    V) : ;;
    V+F1)  "$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 256m \
             --hot-bytes 177838489 --morsel 1m --warmups 0 --reps 500 --cpu-list 32 --threads 1 \
             >/dev/null 2>"$2" & echo $! ;;
    V+F8)  "$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 256m \
             --hot-bytes 177838489 --morsel 1m --warmups 0 --reps 500 --cpu-list 32-39 --threads 8 \
             >/dev/null 2>"$2" & echo $! ;;
    V+F16) "$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 256m \
             --hot-bytes 177838489 --morsel 1m --warmups 0 --reps 500 --cpu-list 32-47 --threads 16 \
             >/dev/null 2>"$2" & echo $! ;;
    V+STREAM) "$STREAM" -m wb_load -t 8 -c 16,17,18,19,20,21,22,23 -N 2 -s 512 -d 600 \
             >/dev/null 2>"$2" & echo $! ;;
  esac
}
echo "== M1: $REPS reps x 5 arms, victim cpu$VCPU wss $((WSS>>20))MiB, ${SEC}s per arm"
ARMS=(V "V+F1" "V+F8" "V+F16" "V+STREAM")
for rep in $(seq 1 "$REPS"); do
  n=${#ARMS[@]}; off=$(( (rep-1) % n )); ORDER=()
  for i in $(seq 0 $((n-1))); do ORDER+=("${ARMS[$(( (i+off) % n ))]}"); done
  pos=0
  for arm in "${ORDER[@]}"; do
    pos=$((pos+1)); e="$OUT/stderr/rep${rep}_pos${pos}_${arm//[+]/_}.err"
    pid=$(start_co "$arm" "$e"); [ -n "${pid:-}" ] && sleep 3
    o=$(mktemp)
    "$VIC" --cpu "$VCPU" --node 0 --wss "$WSS" --run-sec "$SEC" >"$o" 2>>"$e"
    [ -n "${pid:-}" ] && { kill -TERM "$pid" 2>/dev/null; sleep 1; kill -KILL "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; }
    med=$(python3 -c "
import json,sys,statistics as st
d=json.load(open('$o')); v=[x['cycles_per_load'] for x in d]
print(f'{st.median(v):.4f}' if v else 'NA')" 2>/dev/null)
    REC="{\"arm\":\"$arm\",\"rep\":$rep,\"pos\":$pos,\"median_cyc_per_load\":${med:-null}}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$JSONL" || { echo "FATAL bad record $arm rep$rep" >&2; exit 3; }
    printf '  rep%-2s pos%s %-9s victim cyc/load = %s\n' "$rep" "$pos" "$arm" "${med:-NA}"
    rm -f "$o"
  done
done
echo "== M1 done: $(grep -c . "$JSONL") records -> $JSONL"
