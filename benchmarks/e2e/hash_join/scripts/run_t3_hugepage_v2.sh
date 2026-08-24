#!/usr/bin/env bash
# T3 run 2: same experiment, three runner defects fixed.
# Pre-registration: experiments/asplos/T3_HUGEPAGE_PREREG_2026-08-24.md + Addendum 1.
# Audit that motivated it: experiments/asplos/T3_CODE_AUDIT_2026-08-24.md (D1-D3).
#
# v1 is retained unchanged because it produced the committed run-1 data; this is
# a separate script with a separate output path, not a revision of it (A6.19).
#
# Fixed here:
#   D1  arm order is a RANDOMIZED LATIN SQUARE: 3 blocks of 4 reps, each block a
#       randomly-labelled, randomly-ordered 4x4 square from a recorded SEED, so
#       every arm occupies every position exactly 3 times over 12 reps. A plain
#       per-rep shuffle was written first and rejected on inspection: at the
#       intended seed it put Q_4k in position 1 zero times and position 4 six
#       times, i.e. it relocated the confound instead of removing it.
#   D2  per-arm stderr is ARCHIVED, not parsed-then-deleted. v1 discarded it and
#       with it the HOT_TABLE_ROUNDED warning, which is why run 1's outcome doc
#       reported the requested 169.6 MiB hot table instead of the instantiated
#       256 MiB.
#   D3  the hugepage guard emits NA rather than a misleading 0 when a sysfs read
#       fails. In v1, bash arithmetic on the string "NA" yields 0, which reads as
#       "the manipulation did not take" -- the exact failure the guard exists to
#       catch.
#   plus the INSTANTIATED hot-table size is now captured in-band from the
#       binary's own HOT_TABLE line, so the F9 quantization can never again be
#       invisible in this experiment's own records.
#
# Unchanged: arms, operating point, metric, guards, thresholds. Nothing in
# cxl_join_bench.cpp or run_confirmatory_panel.py is touched.
set -uo pipefail
HJ=$(cd "$(dirname "$0")/.." && pwd)
BIN=$HJ/build/cxl_join_bench
OUT=${1:-$HJ/artifacts/t3_hugepage_v2}
REPS=${REPS:-12}
SEED=${SEED:-20260824}
FACT=${FACT:-256m}; HOT=${HOT:-177838489}; MORSEL=${MORSEL:-1m}; CPUL=${CPUL:-32}
PERF_EV=dtlb_load_misses.walk_completed,dtlb_load_misses.walk_active,cycles,instructions
HPF=/sys/devices/system/node/node2/hugepages/hugepages-2048kB/free_hugepages
mkdir -p "$OUT" "$OUT/stderr"
JSONL="$OUT/t3_v2.jsonl"
[ -e "$JSONL" ] && { echo "FAIL $JSONL exists; refusing to append (A6.19)" >&2; exit 2; }
[ -x "$BIN" ] || { echo "FAIL $BIN not executable" >&2; exit 2; }

q_args() { echo --mode hot-probe --policy wb --fact-bytes "$FACT" --hot-bytes "$HOT" \
                --cpu-list "$CPUL" --morsel "$MORSEL" --warmups 2 --reps 1 --threads 1; }
a_args() { echo --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes "$FACT" \
                --hot-bytes "$HOT" --cpu-list "$CPUL" --morsel "$MORSEL" --warmups 2 --reps 1 --threads 1; }

{ echo "== T3 v2 host state as found @ $(date -Is)"; hostname
  echo "-- SEED=$SEED REPS=$REPS (order randomized per rep, reproducible from SEED)"
  echo "-- THP"; cat /sys/kernel/mm/transparent_hugepage/enabled; cat /sys/kernel/mm/transparent_hugepage/defrag
  echo "-- hugepages per node"; for n in 0 1 2; do f=/sys/devices/system/node/node$n/hugepages/hugepages-2048kB/nr_hugepages; [ -f "$f" ] && echo "node$n $(cat "$f")"; done
  echo "-- governor cpu$CPUL"; cat /sys/devices/system/cpu/cpu$CPUL/cpufreq/scaling_governor 2>/dev/null
  echo "-- MSR 0x1A4 cpu$CPUL"; sudo rdmsr -p "$CPUL" 0x1A4 2>/dev/null || echo n/a
  echo "-- perf_event_paranoid"; cat /proc/sys/kernel/perf_event_paranoid
  echo "-- binary"; ls -l "$BIN"; git -C "$HJ" rev-parse --short HEAD
} > "$OUT/t3_v2_state.txt" 2>&1

echo "== T3 v2: $REPS reps x 4 arms, SEED=$SEED, randomized order per rep"
for rep in $(seq 1 "$REPS"); do
  ORDER=$(python3 -c "
import random,sys
seed=int(sys.argv[1]); rep=int(sys.argv[2])
arms=['Q_4k','A_4k','Q_2m','A_2m']
blk, row = (rep-1)//4, (rep-1)%4
rb=random.Random(seed*100+blk)
perm=arms[:]; rb.shuffle(perm)
shift=list(range(4)); rb.shuffle(shift)
i=shift[row]
print(' '.join(perm[(i+j)%4] for j in range(4)))" "$SEED" "$rep")
  pos=0
  for arm in $ORDER; do
    pos=$((pos+1))
    case $arm in
      Q_4k) ARGS=$(q_args) ;;
      A_4k) ARGS=$(a_args) ;;
      Q_2m) ARGS="$(q_args) --huge2m" ;;
      A_2m) ARGS="$(a_args) --huge2m" ;;
    esac
    o=$(mktemp); e="$OUT/stderr/rep${rep}_pos${pos}_${arm}.err"; hp=$(mktemp); rc=0
    # D3: only treat the guard as numeric when it actually read numerically.
    hp_before=$(cat $HPF 2>/dev/null); case "${hp_before:-}" in ''|*[!0-9]*) hp_before=NA;; esac
    ( while :; do cat $HPF 2>/dev/null; sleep 0.02; done ) > "$hp" 2>/dev/null &
    sampler=$!
    perf stat -x, -e "$PERF_EV" -- "$BIN" $ARGS >"$o" 2>"$e" || rc=$?
    kill $sampler 2>/dev/null; wait $sampler 2>/dev/null
    hp_min=$(grep -E '^[0-9]+$' "$hp" 2>/dev/null | sort -n | head -1)
    case "${hp_min:-}" in ''|*[!0-9]*) hp_min=NA;; esac
    if [ "$hp_before" = NA ] || [ "$hp_min" = NA ]; then hp_used=NA
    else hp_used=$(( hp_before - hp_min )); fi
    j=$(grep -o '{.*}' "$o" | tail -1)
    wc_done=$(grep -E "dtlb_load_misses\.walk_completed" "$e" | head -1 | cut -d, -f1)
    wc_act=$(grep -E "dtlb_load_misses\.walk_active" "$e" | head -1 | cut -d, -f1)
    # D2 follow-up: capture the INSTANTIATED hot-table size in-band.
    tbl_inst=$(grep -oE "HOT_TABLE .*bytes=[0-9]+" "$e" | head -1 | grep -oE "bytes=[0-9]+" | cut -d= -f2)
    tbl_round=$(grep -c "HOT_TABLE_ROUNDED" "$e" 2>/dev/null || echo 0)
    if [ -z "$j" ]; then
      echo "{\"arm\":\"$arm\",\"rep\":$rep,\"pos\":$pos,\"status\":\"FAIL\",\"rc\":$rc,\"stderr_file\":\"$(basename "$e")\"}" >> "$JSONL"
      printf '  rep%-3s pos%s %-5s FAIL rc=%s\n' "$rep" "$pos" "$arm" "$rc"
    else
      echo "{\"arm\":\"$arm\",\"rep\":$rep,\"pos\":$pos,\"status\":\"ok\",\"seed\":$SEED,\"walk_completed\":\"${wc_done:-NA}\",\"walk_active\":\"${wc_act:-NA}\",\"hugetlb_node2_before\":\"${hp_before}\",\"hugetlb_node2_min\":\"${hp_min}\",\"hugetlb_pages_used\":\"${hp_used}\",\"hot_table_instantiated_bytes\":\"${tbl_inst:-NA}\",\"hot_table_rounded_warns\":${tbl_round:-0},\"stderr_file\":\"$(basename "$e")\",\"record\":$j}" >> "$JSONL"
      cpa=$(printf '%s' "$j" | sed -n 's/.*"active_cycles_per_access":\([0-9.]*\).*/\1/p')
      printf '  rep%-3s pos%s %-5s cyc/acc=%-10s hugetlb=%-4s tbl_inst=%-10s walks=%s\n' \
             "$rep" "$pos" "$arm" "${cpa:-?}" "${hp_used:-?}" "${tbl_inst:-NA}" "${wc_done:-NA}"
    fi
    rm -f "$o" "$hp"
  done
done
echo "== T3 v2 done: $(grep -c . "$JSONL") records -> $JSONL ; stderr archived in $OUT/stderr/"
