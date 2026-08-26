#!/usr/bin/env bash
# M7: the fused way-restriction penalty as a function of probe hit rate.
# Pre-registration: experiments/asplos/M7_HITRATE_PREREG_2026-08-26.md
# Arms reproduce tab:fused's A3_16 (none) and B16 (4 of 20 ways) exactly;
# only --hit-rate varies. Cells are interleaved and rotated per rep (F10).
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/m7_hitrate}; REPS=${REPS:-15}
HRS=(0.0 0.1 0.25 0.5 0.75 0.9 1.0)
mkdir -p "$OUT"; J="$OUT/m7.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
echo "== as-found resctrl clos groups: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT

# cell list: 14 entries "cat:hr"
CELLS=(); for hr in "${HRS[@]}"; do CELLS+=("none:$hr" "b4:$hr"); done
NC=${#CELLS[@]}
CUR=unset
for r in $(seq 1 "$REPS"); do
  off=$(( (r - 1) % NC ))
  for k in $(seq 0 $((NC-1))); do
    cell=${CELLS[$(( (k + off) % NC ))]}
    cat=${cell%%:*}; hr=${cell##*:}
    if [ "$cat" != "$CUR" ]; then
      if [ "$cat" = b4 ]; then sudo bash "$CLOS" setup_b 4 32-47 >/dev/null 2>&1
      else sudo bash "$CLOS" teardown >/dev/null 2>&1; fi
      CUR=$cat
    fi
    sch=$(cat /sys/fs/resctrl/clos_*/schemata 2>/dev/null | tr '\n' ';' | tr -d ' ')
    [ -z "$sch" ] && sch="ROOT:$(grep -m1 L3 /sys/fs/resctrl/schemata 2>/dev/null | tr -d ' ')"
    o=$("$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g \
         --hot-bytes 177838489 --cpu-list 32-47 --morsel 1m --warmups 2 --reps 1 \
         --threads 16 --hit-rate "$hr" 2>/dev/null | grep -o '{.*}' | tail -1)
    [ -z "$o" ] && { echo "  FAIL cat=$cat hr=$hr rep=$r" >&2; continue; }
    REC="{\"cat\":\"$cat\",\"hr\":$hr,\"rep\":$r,\"pos\":$((k+1)),\"schemata\":\"$sch\",\"record\":$o}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad JSON cat=$cat hr=$hr rep=$r" >&2; exit 3; }
    cpa=$(printf '%s' "$o" | sed -n 's/.*"active_cycles_per_access":\([0-9.]*\).*/\1/p')
    mt=$(printf '%s' "$o" | sed -n 's/.*"join_mtuples_per_s":\([0-9.]*\).*/\1/p')
    printf '  rep%-3s pos%-3s %-5s hr=%-5s cyc/acc=%-9s Mtup/s=%s\n' "$r" "$((k+1))" "$cat" "$hr" "${cpa:-?}" "${mt:-?}"
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== M7 done: $(grep -c . "$J") records (expect $((REPS*NC))); clos groups left: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
