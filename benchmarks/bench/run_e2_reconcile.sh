#!/usr/bin/env bash
# E2: separate two candidate causes of the tenant-cost disagreement --
#   (a) the occupancy sampler M12a ran inside its own measured window,
#   (b) setup_b vs setup_c.
# Pre-registration: experiments/asplos/E2_RECONCILE_PREREG_2026-08-28.md
# The sampler arms replicate M12a's loop exactly, python3 launches included,
# because the hypothesis is about that loop's cost.
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/e2_reconcile}; REPS=${REPS:-40}
TBL=134217728
mkdir -p "$OUT"; J="$OUT/e2.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
echo "== as-found resctrl clos groups: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT

occ() { cat /sys/fs/resctrl/clos_*/mon_data/mon_L3_00/llc_occupancy 2>/dev/null | head -1; }

# cells: helper:sampler
CELLS=(none:off none:on b:off b:on c:off c:on)
NC=${#CELLS[@]}; echo "== $NC cells x $REPS reps = $((NC*REPS)) runs"
CUR=unset
for r in $(seq 1 "$REPS"); do
  off=$(( (r-1) % NC ))
  for i in $(seq 0 $((NC-1))); do
    IFS=: read -r helper samp <<< "${CELLS[$(( (i+off) % NC ))]}"
    if [ "$helper" != "$CUR" ]; then
      case $helper in
        none) sudo bash "$CLOS" teardown >/dev/null 2>&1 ;;
        b)    sudo bash "$CLOS" setup_b 8 32-47 >/dev/null 2>&1 ;;
        c)    sudo bash "$CLOS" setup_c 8 32-47 8 >/dev/null 2>&1 ;;
      esac
      CUR=$helper
    fi
    sch=$(cat /sys/fs/resctrl/clos_*/schemata 2>/dev/null | tr -d ' ' | grep -o 'L3:[^ ]*' | tr '\n' ';')
    [ -z "$sch" ] && sch="ROOT:$(grep -m1 L3 /sys/fs/resctrl/schemata 2>/dev/null | tr -d ' ')"
    err=$(mktemp)
    "$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g \
      --hot-bytes $TBL --cpu-list 32-47 --morsel 1m --warmups 2 --reps 20 \
      --threads 16 --hit-rate 0.5 >"$err.out" 2>"$err" & fpid=$!
    nsamp=0
    if [ "$samp" = on ]; then
      # M12a's loop, verbatim in cost: a python3 launch for the elapsed check per
      # iteration, plus a sysfs read, every 150 ms, inside the measured window.
      t0=$(date +%s.%N)
      while kill -0 $fpid 2>/dev/null; do
        el=$(python3 -c "print(1 if $(date +%s.%N)-$t0 >= 1.5 else 0)")
        [ "$el" = 1 ] && { occ >/dev/null; nsamp=$((nsamp+1)); }
        sleep 0.15
      done
    fi
    wait $fpid 2>/dev/null
    o=$(grep -o '{.*}' "$err.out" | tail -1)
    inst=$(sed -n 's/^HOT_TABLE .*bytes=\([0-9]*\) entries.*/\1/p' "$err" | head -1)
    rounded=$(grep -c HOT_TABLE_ROUNDED "$err" || true); rm -f "$err" "$err.out"
    [ -z "$o" ] && { echo "  FAIL $helper/$samp rep=$r" >&2; continue; }
    [ "$rounded" != "0" ] && { echo "FATAL table rounded (F9)" >&2; exit 4; }
    REC="{\"helper\":\"$helper\",\"sampler\":\"$samp\",\"nsamp\":$nsamp,\"table\":$TBL,\"table_instantiated\":${inst:-null},\"rep\":$r,\"pos\":$((i+1)),\"schemata\":\"$sch\",\"record\":$o}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad JSON" >&2; exit 3; }
    cpa=$(printf '%s' "$o" | sed -n 's/.*"active_cycles_per_access":\([0-9.]*\).*/\1/p')
    printf '  rep%-3s %-5s samp=%-4s nsamp=%-3s cyc/acc=%s\n' "$r" "$helper" "$samp" "$nsamp" "${cpa:-?}"
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== E2 done: $(grep -c . "$J") records (expect $((REPS*NC))); clos groups left: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
