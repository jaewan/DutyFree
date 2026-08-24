#!/usr/bin/env bash
# T3: does the fused same-thread tax shrink when the STREAM is on 2 MiB pages?
# Pre-registration: experiments/asplos/T3_HUGEPAGE_PREREG_2026-08-24.md
#
# Four arms, interleaved within each rep so drift spreads across arms:
#   Q_4k  hot-probe, no stream            A_4k  morsel (fused), 4 KiB stream
#   Q_2m  hot-probe + --huge2m (control)  A_2m  morsel + --huge2m, 2 MiB stream
#
# Reproduces run_confirmatory_panel.py's 1-core operating point verbatim; the
# only thing added to any arm is the --huge2m flag the binary already has.
# Nothing in cxl_join_bench.cpp or the panel runner is edited.
set -uo pipefail
HJ=$(cd "$(dirname "$0")/.." && pwd)
BIN=$HJ/build/cxl_join_bench
OUT=${1:-$HJ/artifacts/t3_hugepage}
REPS=${REPS:-5}
FACT=${FACT:-256m}; HOT=${HOT:-177838489}; MORSEL=${MORSEL:-1m}; CPUL=${CPUL:-32}
PERF_EV=dtlb_load_misses.walk_completed,dtlb_load_misses.walk_active,cycles,instructions
mkdir -p "$OUT"
JSONL="$OUT/t3.jsonl"
[ -e "$JSONL" ] && { echo "FAIL $JSONL exists; refusing to append (A6.19)" >&2; exit 2; }
[ -x "$BIN" ] || { echo "FAIL $BIN not executable" >&2; exit 2; }

# panel-verbatim argument builders
q_args() { echo --mode hot-probe --policy wb --fact-bytes "$FACT" --hot-bytes "$HOT" \
                --cpu-list "$CPUL" --morsel "$MORSEL" --warmups 2 --reps 1 --threads 1; }
a_args() { echo --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes "$FACT" \
                --hot-bytes "$HOT" --cpu-list "$CPUL" --morsel "$MORSEL" --warmups 2 --reps 1 --threads 1; }

{ echo "== T3 host state as found @ $(date -Is)"; hostname
  echo "-- THP"; cat /sys/kernel/mm/transparent_hugepage/enabled
  cat /sys/kernel/mm/transparent_hugepage/defrag
  echo "-- hugepages per node"; for n in 0 1 2; do f=/sys/devices/system/node/node$n/hugepages/hugepages-2048kB/nr_hugepages; [ -f "$f" ] && echo "node$n $(cat "$f")"; done
  echo "-- governor cpu$CPUL"; cat /sys/devices/system/cpu/cpu$CPUL/cpufreq/scaling_governor 2>/dev/null
  echo "-- MSR 0x1A4 cpu$CPUL"; sudo rdmsr -p "$CPUL" 0x1A4 2>/dev/null || echo n/a
  echo "-- perf_event_paranoid"; cat /proc/sys/kernel/perf_event_paranoid
  echo "-- binary"; ls -l "$BIN"; git -C "$HJ" rev-parse --short HEAD
} > "$OUT/t3_state.txt" 2>&1

echo "== T3: $REPS reps x 4 arms, fact=$FACT hot=$HOT cpu=$CPUL"
for rep in $(seq 1 "$REPS"); do
  for arm in Q_4k A_4k Q_2m A_2m; do
    case $arm in
      Q_4k) ARGS=$(q_args) ;;
      A_4k) ARGS=$(a_args) ;;
      Q_2m) ARGS="$(q_args) --huge2m" ;;
      A_2m) ARGS="$(a_args) --huge2m" ;;
    esac
    o=$(mktemp); e=$(mktemp); hp=$(mktemp); rc=0
    # F12 guard for the FACT array: alloc_bytes() silently falls back from
    # MAP_HUGETLB to plain mmap+MADV_HUGEPAGE and prints nothing either way, so
    # there is no in-band evidence of which path ran. Sample node2's hugetlb
    # free count during the arm; a MAP_HUGETLB success for a 256 MB fact array
    # consumes 128 pages. External to the binary, so no apparatus edit.
    HPF=/sys/devices/system/node/node2/hugepages/hugepages-2048kB/free_hugepages
    hp_before=$(cat $HPF 2>/dev/null || echo NA)
    ( while :; do cat $HPF 2>/dev/null; sleep 0.02; done ) > "$hp" 2>/dev/null &
    sampler=$!
    perf stat -x, -e "$PERF_EV" -- "$BIN" $ARGS >"$o" 2>"$e" || rc=$?
    kill $sampler 2>/dev/null; wait $sampler 2>/dev/null
    hp_min=$(sort -n "$hp" 2>/dev/null | head -1); hp_min=${hp_min:-NA}
    hp_used=$(( ${hp_before:-0} - ${hp_min:-0} )) 2>/dev/null || hp_used=NA
    j=$(grep -o '{.*}' "$o" | tail -1)
    # perf writes its CSV to stderr; pull the two walk counters out
    wc_done=$(grep -E "dtlb_load_misses.walk_completed" "$e" | head -1 | cut -d, -f1)
    wc_act=$(grep -E "dtlb_load_misses.walk_active" "$e" | head -1 | cut -d, -f1)
    if [ -z "$j" ]; then
      msg=$(tr '\n' ' ' < "$e" | tail -c 300 | sed 's/"/\\"/g')
      echo "{\"arm\":\"$arm\",\"rep\":$rep,\"status\":\"FAIL\",\"rc\":$rc,\"stderr\":\"$msg\"}" >> "$JSONL"
      printf '  rep%-2s %-5s FAIL rc=%s\n' "$rep" "$arm" "$rc"
    else
      echo "{\"arm\":\"$arm\",\"rep\":$rep,\"status\":\"ok\",\"walk_completed\":\"${wc_done:-NA}\",\"walk_active\":\"${wc_act:-NA}\",\"hugetlb_node2_before\":\"${hp_before}\",\"hugetlb_node2_min\":\"${hp_min}\",\"hugetlb_pages_used\":\"${hp_used}\",\"record\":$j}" >> "$JSONL"
      cpa=$(printf '%s' "$j" | sed -n 's/.*"active_cycles_per_access":\([0-9.]*\).*/\1/p')
      # NOTE: table_* fields describe the HOT TABLE, not the fact array.
      tkb=$(printf '%s' "$j" | sed -n 's/.*"table_kernel_page_kb":\([0-9]*\).*/\1/p')
      printf '  rep%-2s %-5s cyc/acc=%-10s hugetlb_used=%-6s tbl_pg_kb=%-4s walks=%s\n' "$rep" "$arm" "${cpa:-?}" "${hp_used:-?}" "${tkb:-?}" "${wc_done:-NA}"
    fi
    rm -f "$o" "$e" "$hp"
  done
done
echo "== T3 done: $(grep -c . "$JSONL") records -> $JSONL"
