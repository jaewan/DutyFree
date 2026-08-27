#!/usr/bin/env bash
# E1 pass A: the tenant's own cost as a function of its mask width.
# Pre-registration: experiments/asplos/E1_FRONTIER_PREREG_2026-08-28.md
# Sweeps mask width (2/4/8 ways = 32/64/128 MiB) against table size. All table
# sizes are exact powers of two x 16 B so HOT_TABLE_ROUNDED must never fire; the
# instantiated size is captured from stderr into every record, which M7/M8/M9
# could not do because they discarded stderr.
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/e1a_tenantcost}; REPS=${REPS:-10}
TABLES=(134217728)   # 128 MiB, exact power of two
ARMS=(none b2 b4 b8 b12 b16)
mkdir -p "$OUT"; J="$OUT/e1a.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
echo "== as-found resctrl clos groups: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT

CELLS=(); for t in "${TABLES[@]}"; do for a in "${ARMS[@]}"; do CELLS+=("$a:$t"); done; done
NC=${#CELLS[@]}; echo "== $NC cells x $REPS reps = $((NC*REPS)) runs"
CUR=unset
for r in $(seq 1 "$REPS"); do
  off=$(( (r - 1) * 7 % NC ))
  for k in $(seq 0 $((NC-1))); do
    IFS=: read -r arm tbl <<< "${CELLS[$(( (k + off) % NC ))]}"
    if [ "$arm" != "$CUR" ]; then
      case $arm in
        none) sudo bash "$CLOS" teardown >/dev/null 2>&1 ;;
        *)    sudo bash "$CLOS" setup_c "${arm#b}" 32-47 8 >/dev/null 2>&1 ;;
      esac
      CUR=$arm
    fi
    sch=$(cat /sys/fs/resctrl/clos_*/schemata 2>/dev/null | tr -d ' ' | grep -o 'L3:[^ ]*' | tr '\n' ';')
    [ -z "$sch" ] && sch="ROOT:$(grep -m1 L3 /sys/fs/resctrl/schemata 2>/dev/null | tr -d ' ')"
    err=$(mktemp)
    o=$("$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g \
         --hot-bytes "$tbl" --cpu-list 32-47 --morsel 1m --warmups 2 --reps 20 \
         --threads 16 --hit-rate 0.5 2>"$err" | grep -o '{.*}' | tail -1)
    inst=$(sed -n 's/^HOT_TABLE .*bytes=\([0-9]*\) entries.*/\1/p' "$err" | head -1)
    rounded=$(grep -c HOT_TABLE_ROUNDED "$err" || true)
    rm -f "$err"
    [ -z "$o" ] && { echo "  FAIL $arm tbl=$tbl rep=$r" >&2; continue; }
    [ "$rounded" != "0" ] && { echo "FATAL table silently rounded at $tbl (F9) -- aborting" >&2; exit 4; }
    REC="{\"arm\":\"$arm\",\"table\":$tbl,\"table_instantiated\":${inst:-null},\"rep\":$r,\"pos\":$((k+1)),\"schemata\":\"$sch\",\"record\":$o}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad JSON $arm $tbl rep$r" >&2; exit 3; }
    cpa=$(printf '%s' "$o" | sed -n 's/.*"active_cycles_per_access":\([0-9.]*\).*/\1/p')
    printf '  rep%-2s pos%-3s %-5s tbl=%-10s inst=%-10s cyc/acc=%s\n' "$r" "$((k+1))" "$arm" "$tbl" "${inst:-?}" "${cpa:-?}"
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== E1a done: $(grep -c . "$J") records (expect $((REPS*NC))); clos groups left: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
