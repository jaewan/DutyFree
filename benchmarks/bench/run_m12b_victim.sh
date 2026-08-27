#!/usr/bin/env bash
# M12 pass B: does an 8-way mask on F actually protect V? (the iso-protection premise)
# Pre-registration: experiments/asplos/M12_ISOPROTECTION_PREREG_2026-08-28.md
# Unlike M6b, F's liveness is ASSERTED per run from its stderr -- the AMD n=6 WC arm
# that moved 0.0108 GB/s while reporting no harm is why that now matters.
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
VIC=$B/victim/pointer_chase
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/m12b_victim}; REPS=${REPS:-10}
SEC=${SEC:-1}; TRIALS=${TRIALS:-6}; WSS=${WSS:-178257920}; VCPU=${VCPU:-8}
TBL=134217728          # 128 MiB = exactly the 8-way mask (M12a's sweet-spot cell)
mkdir -p "$OUT/stderr"; J="$OUT/m12b.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
for f in "$VIC" "$FUSED"; do [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }; done
echo "== as-found resctrl clos groups: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT

set_cat() { # none | wide  (wide: F 8 ways, V the complementary 12 -- enforced)
  if [ "$1" = wide ]; then sudo bash "$CLOS" setup_c 8 32-47 "$VCPU" >/dev/null 2>&1
  else sudo bash "$CLOS" teardown >/dev/null 2>&1; fi
}
# arms: Vnone | Vwide (V alone, partitioning-cost control) | F_<cat>_<stream>
ARMS=(Vnone Vwide F_none_retain F_none_flush F_wide_retain F_wide_flush)
echo "== M12b: ${#ARMS[@]} arms x $REPS reps, V cpu$VCPU wss $((WSS>>20))MiB, F table $((TBL>>20))MiB"
for rep in $(seq 1 "$REPS"); do
  n=${#ARMS[@]}; off=$(( (rep-1) % n )); ORDER=()
  for i in $(seq 0 $((n-1))); do ORDER+=("${ARMS[$(( (i+off) % n ))]}"); done
  pos=0
  for arm in "${ORDER[@]}"; do
    pos=$((pos+1)); e="$OUT/stderr/rep${rep}_pos${pos}_${arm}.err"
    fpid=""; live=null; fbw=null
    case $arm in
      Vnone) set_cat none ;;
      Vwide) set_cat wide ;;
      *) IFS=_ read -r _ cat sm <<< "$arm"
         set_cat "$cat"
         fd=0; [ "$sm" = flush ] && fd=262144
         "$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g \
           --hot-bytes $TBL --morsel 1m --warmups 0 --reps 20000 --cpu-list 32-47 --threads 16 \
           --hit-rate 0.5 --flush-distance $fd >/dev/null 2>"$e" & fpid=$!
         sleep 4 ;;
    esac
    sch=$(cat /sys/fs/resctrl/clos_*/schemata 2>/dev/null | tr -d ' ' | grep -o 'L3:[^ ]*' | tr '\n' ';')
    [ -z "$sch" ] && sch="ROOT:$(grep -m1 L3 /sys/fs/resctrl/schemata 2>/dev/null | tr -d ' ')"
    o=$(mktemp)
    "$VIC" --cpu "$VCPU" --node 0 --wss "$WSS" --run-sec "$SEC" --trials "$TRIALS" >"$o" 2>>"$e"
    if [ -n "$fpid" ]; then
      # liveness asserted from F's own stderr AND from the process still existing
      kill -0 "$fpid" 2>/dev/null && alive=1 || alive=0
      grep -q HOT_TABLE_WARMED "$e" && warmed=1 || warmed=0
      live="{\"alive_at_end\":$alive,\"warmed\":$warmed}"
      kill -TERM "$fpid" 2>/dev/null; sleep 1; kill -KILL "$fpid" 2>/dev/null; wait "$fpid" 2>/dev/null
      [ "$alive" = 0 ] && echo "  WARN F not alive at end of window: $arm rep$rep" >&2
      [ "$warmed" = 0 ] && echo "  WARN F never warmed: $arm rep$rep" >&2
    fi
    med=$(python3 -c "
import json,statistics as st
d=json.load(open('$o')); v=[x['cycles_per_load'] for x in d]
print(f'{st.median(v):.4f}' if v else 'null')" 2>/dev/null)
    REC="{\"arm\":\"$arm\",\"rep\":$rep,\"pos\":$pos,\"table\":$TBL,\"victim_cyc_per_load\":${med:-null},\"f_liveness\":$live,\"schemata\":\"$sch\"}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad record $arm rep$rep" >&2; exit 3; }
    printf '  rep%-2s pos%s %-15s victim cyc/load = %-10s F=%s\n' "$rep" "$pos" "$arm" "${med:-NA}" "$live"
    rm -f "$o"
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== M12b done: $(grep -c . "$J") records; clos groups left: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
