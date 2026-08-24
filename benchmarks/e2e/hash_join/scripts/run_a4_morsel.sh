#!/usr/bin/env bash
# T4 / A4-followup: morsel-size sweep. Registered in T4_SCOPING_PREREG Addendum 4.
# Determines whether the published "fused tax" is morsel-driver overhead. the fused same-thread tax into memory / core / front-end / bad-spec.
# Pre-registration: experiments/asplos/T4_SCOPING_PREREG_2026-08-24.md + Addendum 1.
#
# Two arms at the panel's 1-core operating point. Order is BALANCED (odd reps run
# Q,A; even reps run A,Q) so each arm occupies each position exactly REPS/2 times
# -- T3 run 2 showed this kernel's quiescent arm is position-sensitive via mode
# selection, so fixed order is not acceptable.
#
# Carries the T3-v2 fixed idioms: records validated as JSON before being appended,
# per-arm stderr ARCHIVED (the analyzer parses TMA from it, so it is the primary
# artifact, not a byproduct), and no `grep -c` fallback.
set -uo pipefail
HJ=$(cd "$(dirname "$0")/.." && pwd)
BIN=$HJ/build/cxl_join_bench
OUT=${1:-$HJ/artifacts/a4_morsel}
REPS=${REPS:-6}
FACT=${FACT:-256m}; HOT=${HOT:-177838489}; MORSEL=${MORSEL:-1m}; CPUL=${CPUL:-32}
MG=${MG:-TopdownL1,TopdownL2}
EV=${EV:-l1d_pend_miss.fb_full,cycles,instructions}
mkdir -p "$OUT" "$OUT/stderr"
JSONL="$OUT/a4_morsel.jsonl"
[ -e "$JSONL" ] && { echo "FAIL $JSONL exists; refusing to append (A6.19)" >&2; exit 2; }
[ -x "$BIN" ] || { echo "FAIL $BIN not executable" >&2; exit 2; }

BASE="--policy wb --fact-node 2 --hot-node 0 --fact-bytes $FACT --hot-bytes $HOT --warmups 2 --reps 1"
f_args()     { echo --mode morsel $BASE --morsel "$M" --cpu-list 32 --threads 1; }
q_args()     { echo --mode morsel $BASE --morsel "$M" --no-stream --cpu-list 32 --threads 1; }
hp_args()    { echo --mode hot-probe --policy wb --fact-bytes $FACT --hot-bytes $HOT --morsel "$M" --warmups 2 --reps 1 --cpu-list 32 --threads 1; }

{ echo "== T4 TMA gate, host state as found @ $(date -Is)"; hostname
  echo "-- metrics: -M $MG  -e $EV"
  echo "-- governor cpu$CPUL"; cat /sys/devices/system/cpu/cpu$CPUL/cpufreq/scaling_governor 2>/dev/null
  echo "-- MSR 0x1A4 cpu$CPUL"; sudo rdmsr -p "$CPUL" 0x1A4 2>/dev/null || echo n/a
  echo "-- SMT sibling of cpu$CPUL"; cat /sys/devices/system/cpu/cpu$CPUL/topology/thread_siblings_list 2>/dev/null
  echo "-- perf_event_paranoid"; cat /proc/sys/kernel/perf_event_paranoid
  echo "-- binary"; ls -l "$BIN"; git -C "$HJ" rev-parse --short HEAD
} > "$OUT/t4_state.txt" 2>&1

echo "== A4 morsel sweep: morsels ${MORSELS:-256k 1m 4m 16m} x $REPS reps x 3 arms (F/Q/HP)"
for M in ${MORSELS:-256k 1m 4m 16m}; do
for rep in $(seq 1 "$REPS"); do
  if [ $((rep % 2)) -eq 1 ]; then ORDER="F Q HP"; else ORDER="HP Q F"; fi
  pos=0
  for arm in $ORDER; do
    pos=$((pos+1))
    case $arm in F) ARGS=$(f_args);; Q) ARGS=$(q_args);; HP) ARGS=$(hp_args);; esac
    o=$(mktemp); e="$OUT/stderr/rep${rep}_pos${pos}_${arm}.err"; rc=0
    perf stat -M "$MG" -e "$EV" -- "$BIN" $ARGS >"$o" 2>"$e" || rc=$?
    j=$(grep -o '{.*}' "$o" | tail -1)
    if [ -z "$j" ]; then
      echo "{\"arm\":\"$arm\",\"morsel\":\"$M\",\"rep\":$rep,\"pos\":$pos,\"status\":\"FAIL\",\"rc\":$rc,\"stderr_file\":\"$(basename "$e")\"}" >> "$JSONL"
      printf '  rep%-3s pos%s %-2s FAIL rc=%s\n' "$rep" "$pos" "$arm" "$rc"
    else
      REC="{\"arm\":\"$arm\",\"morsel\":\"$M\",\"rep\":$rep,\"pos\":$pos,\"status\":\"ok\",\"stderr_file\":\"$(basename "$e")\",\"record\":$j}"
      if ! printf '%s\n' "$REC" | python3 -c 'import json,sys; json.loads(sys.stdin.read())' 2>/dev/null; then
        echo "  FATAL rep$rep pos$pos $arm: record not valid JSON; aborting" >&2
        printf '%s\n' "$REC" > "$OUT/BAD_RECORD_rep${rep}_pos${pos}_${arm}.txt"; exit 3
      fi
      printf '%s\n' "$REC" >> "$JSONL"
      cpa=$(printf '%s' "$j" | sed -n 's/.*"active_cycles_per_access":\([0-9.]*\).*/\1/p')
      thr=$(printf '%s' "$j" | sed -n 's/.*"join_mtuples_per_s":\([0-9.]*\).*/\1/p')
      printf '  M=%-5s rep%-2s pos%s %-3s cyc/acc=%-11s thr=%s\n' "$M" "$rep" "$pos" "$arm" "${cpa:-?}" "${thr:-?}"
    fi
    rm -f "$o"
  done
done
done
echo "== A4 morsel sweep done: $(grep -c . "$JSONL") records -> $JSONL"
