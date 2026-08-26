#!/usr/bin/env bash
# M6 pass B: V's harm under {table} x {stream} x {CAT}. The hostile control.
# Pre-registration: experiments/asplos/M6_FRONTIER_PREREG_2026-08-26.md
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
OUT=${1:-$B/../data/m6b_frontier}
REPS=${REPS:-10}; SEC=${SEC:-1}; TRIALS=${TRIALS:-6}; # 170 MB, matching Sec2's Intel victim. The first attempt used 4 MiB, which on
# this host is only 2x the 2 MiB private L2 -- standing rule S5.2 says check the
# hot set against the PRIVATE L2 before believing a null.
WSS=${WSS:-178257920}; VCPU=${VCPU:-8}
mkdir -p "$OUT/stderr"; JSONL="$OUT/m6b.jsonl"
[ -e "$JSONL" ] && { echo "FAIL $JSONL exists (A6.19)" >&2; exit 2; }
trap 'sudo bash "$B/../e2e/hash_join/scripts/resctrl_clos.sh" teardown >/dev/null 2>&1 || true' EXIT
for f in "$VIC" "$FUSED" "$STREAM"; do [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }; done

CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
set_cat() { # $1 = none|narrow
  if [ "$1" = narrow ]; then sudo bash "$CLOS" setup_c 2 32-47 8 >/dev/null 2>&1
  else sudo bash "$CLOS" teardown >/dev/null 2>&1; fi
}
start_co() { # $1=arm, $2=stderr -> echoes pid or empty
  # arm forms: Vnone | Vnarrow | F_<cat>_<tbl>_<stream>
  case $1 in
    Vnone)   set_cat none;   return ;;
    Vnarrow) set_cat narrow; return ;;
  esac
  IFS=_ read -r _ cat tbl sm <<< "$1"
  set_cat "$cat"
  hb=177838489; [ "$tbl" = 4m ] && hb=4194304
  fd=0; [ "$sm" = flush ] && fd=262144
  "$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 256m \
    --hot-bytes $hb --morsel 1m --warmups 0 --reps 20000 --cpu-list 32-47 --threads 16 \
    --hit-rate 1.0 --flush-distance $fd >/dev/null 2>"$2" & echo $!
}
echo "== M6b: $REPS reps x 10 arms, victim cpu$VCPU wss $((WSS>>20))MiB, ${TRIALS}x${SEC}s per arm"
ARMS=(Vnone Vnarrow F_none_4m_retain F_none_4m_flush F_none_256m_retain F_none_256m_flush F_narrow_4m_retain F_narrow_4m_flush F_narrow_256m_retain F_narrow_256m_flush)
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
    printf '  rep%-2s pos%s %-22s victim cyc/load = %s\n' "$rep" "$pos" "$arm" "${med:-NA}"
    rm -f "$o"
  done
done
echo "== M6b done: $(grep -c . "$JSONL") records -> $JSONL"
