#!/usr/bin/env bash
# M11b: setup_c vs setup_b at M6 pass A's exact cell. Prereg: M11B_PREREG_2026-08-28.md
# Pre-registration: experiments/asplos/M11_FACTSIZE_PREREG_2026-08-28.md
# Walks fact size and reps/warmups one at a time from M8's config to M6's, at a
# fixed 256 MiB table (exact power of two) and hit rate 1.0. No victim.
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/m11b_helper}; REPS=${REPS:-10}
TBL=268435456                 # 256 MiB, exact power of two x 16 B
mkdir -p "$OUT"; J="$OUT/m11b.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
echo "== as-found resctrl clos groups: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT

CELLS=()
for arm in none b2_setupb b2_setupc; do CELLS+=("$arm:256m:4:1"); done
NC=${#CELLS[@]}; echo "== $NC cells x $REPS reps = $((NC*REPS)) runs"
CUR=unset
for r in $(seq 1 "$REPS"); do
  off=$(( (r - 1) * 5 % NC ))
  for k in $(seq 0 $((NC-1))); do
    IFS=: read -r arm fact reps warm <<< "${CELLS[$(( (k + off) % NC ))]}"
    if [ "$arm" != "$CUR" ]; then
      case $arm in
        none)       sudo bash "$CLOS" teardown >/dev/null 2>&1 ;;
        b2_setupb)  sudo bash "$CLOS" setup_b 2 32-47 >/dev/null 2>&1 ;;
        b2_setupc)  sudo bash "$CLOS" setup_c 2 32-47 8 >/dev/null 2>&1 ;;
      esac
      CUR=$arm
    fi
    sch=$(cat /sys/fs/resctrl/clos_*/schemata 2>/dev/null | tr -d ' ' | grep -o 'L3:[^ ]*' | tr '\n' ';')
    [ -z "$sch" ] && sch="ROOT:$(grep -m1 L3 /sys/fs/resctrl/schemata 2>/dev/null | tr -d ' ')"
    err=$(mktemp)
    o=$("$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes "$fact" \
         --hot-bytes "$TBL" --cpu-list 32-47 --morsel 1m --warmups "$warm" --reps "$reps" \
         --threads 16 --hit-rate 1.0 2>"$err" | grep -o '{.*}' | tail -1)
    inst=$(sed -n 's/^HOT_TABLE .*bytes=\([0-9]*\) entries.*/\1/p' "$err" | head -1)
    rounded=$(grep -c HOT_TABLE_ROUNDED "$err" || true); rm -f "$err"
    [ -z "$o" ] && { echo "  FAIL $arm $fact $reps/$warm rep=$r" >&2; continue; }
    [ "$rounded" != "0" ] && { echo "FATAL table silently rounded (F9) -- aborting" >&2; exit 4; }
    REC="{\"arm\":\"$arm\",\"fact\":\"$fact\",\"reps\":$reps,\"warmups\":$warm,\"table\":$TBL,\"table_instantiated\":${inst:-null},\"rep\":$r,\"pos\":$((k+1)),\"schemata\":\"$sch\",\"record\":$o}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad JSON" >&2; exit 3; }
    cpa=$(printf '%s' "$o" | sed -n 's/.*"active_cycles_per_access":\([0-9.]*\).*/\1/p')
    bw=$(printf '%s' "$o" | sed -n 's/.*"stream_bandwidth_gbps":\([0-9.]*\).*/\1/p')
    printf '  rep%-2s pos%-3s %-5s fact=%-5s r/w=%s/%s cyc/acc=%-9s stream=%s GB/s\n' \
      "$r" "$((k+1))" "$arm" "$fact" "$reps" "$warm" "${cpa:-?}" "${bw:-?}"
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== M11b done: $(grep -c . "$J") records (expect $((REPS*NC))); clos groups left: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
