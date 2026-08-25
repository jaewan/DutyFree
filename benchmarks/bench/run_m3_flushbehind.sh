#!/usr/bin/env bash
# M3: does NON-ALLOCATION remove the neighbour's harm? (the decisive arm)
# Pre-registration: experiments/asplos/M3_FLUSHBEHIND_PREREG_2026-08-25.md
# Comparisons are among F configurations, so this does not depend on M1's
# failed positive control.
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
HJ=$B/../e2e/hash_join
VIC=$B/victim/pointer_chase
FUSED=$HJ/build/cxl_join_bench
# The multi-threaded aggressor lives in the instrument tree; bench/aggressor/stream_wb
# is a DIFFERENT binary with different flags (--cpu/--node/--region-gb). The first
# attempt pointed at the latter with the former's flags, so the positive control
# silently never ran ("invalid option -- 'm'") and V+STREAM was just V. That run was
# discarded. Second instance today of two similarly-named binaries being confused.
STREAM=$B/../e2e/instrument/bin/aggressor
OUT=${1:-$B/../data/m3_flushbehind}
REPS=${REPS:-6}; SEC=${SEC:-1}; TRIALS=${TRIALS:-6}; # 170 MB, matching Sec2's Intel victim. The first attempt used 4 MiB, which on
# this host is only 2x the 2 MiB private L2 -- standing rule S5.2 says check the
# hot set against the PRIVATE L2 before believing a null.
WSS=${WSS:-178257920}; VCPU=${VCPU:-8}
mkdir -p "$OUT/stderr"; JSONL="$OUT/m3.jsonl"
[ -e "$JSONL" ] && { echo "FAIL $JSONL exists (A6.19)" >&2; exit 2; }
for f in "$VIC" "$FUSED" "$STREAM"; do [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }; done

start_co() { # $1=arm, $2=stderr -> echoes pid or empty
  F="$FUSED --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 256m --hot-bytes 177838489 --morsel 1m --warmups 0 --reps 4000 --cpu-list 32-47 --threads 16 --hit-rate 1.0"
  case $1 in
    V) : ;;
    V+F_alloc) $F                          >/dev/null 2>"$2" & echo $! ;;
    V+F_fb)    $F --flush-distance 262144   >/dev/null 2>"$2" & echo $! ;;
    V+F_ns)    $F --no-stream               >/dev/null 2>"$2" & echo $! ;;
  esac
}
echo "== M3: $REPS reps x 4 arms, victim cpu$VCPU wss $((WSS>>20))MiB, ${TRIALS}x${SEC}s per arm"
ARMS=(V "V+F_alloc" "V+F_fb" "V+F_ns")
for rep in $(seq 1 "$REPS"); do
  n=${#ARMS[@]}; off=$(( (rep-1) % n )); ORDER=()
  for i in $(seq 0 $((n-1))); do ORDER+=("${ARMS[$(( (i+off) % n ))]}"); done
  pos=0
  for arm in "${ORDER[@]}"; do
    pos=$((pos+1)); e="$OUT/stderr/rep${rep}_pos${pos}_${arm//[+]/_}.err"
    pid=$(start_co "$arm" "$e"); [ -n "${pid:-}" ] && sleep 3
    o=$(mktemp)
    "$VIC" --cpu "$VCPU" --node 0 --wss "$WSS" --run-sec "$SEC" --trials "$TRIALS" >"$o" 2>>"$e"
    [ -n "${pid:-}" ] && { kill -TERM "$pid" 2>/dev/null; sleep 1; kill -KILL "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; }
    med=$(python3 -c "
import json,sys,statistics as st
d=json.load(open('$o')); v=[x['cycles_per_load'] for x in d]
print(f'{st.median(v):.4f}' if v else 'NA')" 2>/dev/null)
    REC="{\"arm\":\"$arm\",\"rep\":$rep,\"pos\":$pos,\"median_cyc_per_load\":${med:-null}}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$JSONL" || { echo "FATAL bad record $arm rep$rep" >&2; exit 3; }
    printf '  rep%-2s pos%s %-14s victim cyc/load = %s\n' "$rep" "$pos" "$arm" "${med:-NA}"
    rm -f "$o"
  done
done
echo "== M3 done: $(grep -c . "$JSONL") records -> $JSONL"
