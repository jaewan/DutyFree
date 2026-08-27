#!/usr/bin/env bash
# E1 pass A2: the tenant's cost, measured as the MEDIAN OF PER-PAIR RATIOS.
# Pre-registration: E1_FRONTIER_PREREG_2026-08-28.md, amendment 1.
# Every masked run is paired with an unmasked run taken immediately beside it, so
# drift of any cause cannot survive into the ratio. Captures cpus_list per record
# and aborts if the tenant's CPU association is not exactly 32-47.
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/e1a2_paired}; REPS=${REPS:-10}
TBL=134217728; WIDTHS=(2 4 8 12 16)
mkdir -p "$OUT"; J="$OUT/e1a2.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
echo "== as-found resctrl clos groups: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT

run_one() { # $1 = none | <ways> ; echoes cyc/acc, and validates enforcement
  local w="$1" sch cpul
  if [ "$w" = none ]; then
    sudo bash "$CLOS" teardown >/dev/null 2>&1
    sch="ROOT:$(grep -m1 L3 /sys/fs/resctrl/schemata 2>/dev/null | tr -d ' ')"; cpul="root"
  else
    sudo bash "$CLOS" setup_c "$w" 32-47 8 >/dev/null 2>&1
    sch=$(grep -o 'L3:[^ ]*' /sys/fs/resctrl/clos_c_scan/schemata 2>/dev/null | tr -d ' ')
    cpul=$(cat /sys/fs/resctrl/clos_c_scan/cpus_list 2>/dev/null)
    [ "$cpul" != "32-47" ] && { echo "FATAL tenant cpus_list='$cpul', expected 32-47" >&2; exit 5; }
  fi
  local err=$(mktemp)
  local o=$("$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g \
      --hot-bytes $TBL --cpu-list 32-47 --morsel 1m --warmups 2 --reps 20 \
      --threads 16 --hit-rate 0.5 2>"$err" | grep -o '{.*}' | tail -1)
  grep -q HOT_TABLE_ROUNDED "$err" && { echo "FATAL table rounded" >&2; exit 4; }
  rm -f "$err"
  [ -z "$o" ] && { echo "FATAL empty record w=$w" >&2; exit 3; }
  printf '%s\t%s\t%s' "$o" "$sch" "$cpul"
}

echo "== ${#WIDTHS[@]} widths x $REPS pairs = $((${#WIDTHS[@]}*REPS*2)) runs"
for rep in $(seq 1 "$REPS"); do
  for w in "${WIDTHS[@]}"; do
    # alternate which half of the pair runs first, by rep parity
    if [ $((rep % 2)) -eq 1 ]; then first=none; second=$w; else first=$w; second=none; fi
    IFS=$'\t' read -r o1 s1 c1 <<< "$(run_one "$first")"
    IFS=$'\t' read -r o2 s2 c2 <<< "$(run_one "$second")"
    if [ "$first" = none ]; then on="$o1"; om="$o2"; sn="$s1"; sm="$s2"; cm="$c2"
    else on="$o2"; om="$o1"; sn="$s2"; sm="$s1"; cm="$c1"; fi
    gn() { printf '%s' "$1" | sed -n 's/.*"active_cycles_per_access":\([0-9.]*\).*/\1/p'; }
    vn=$(gn "$on"); vm=$(gn "$om")
    ratio=$(python3 -c "print(f'{$vm/$vn:.6f}')")
    REC="{\"width\":$w,\"rep\":$rep,\"order\":\"$( [ "$first" = none ] && echo none_first || echo masked_first)\",\"cyc_none\":$vn,\"cyc_masked\":$vm,\"ratio\":$ratio,\"schemata_none\":\"$sn\",\"schemata_masked\":\"$sm\",\"cpus_masked\":\"$cm\"}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad JSON" >&2; exit 3; }
    printf '  rep%-3s w=%-3s none=%-8s masked=%-8s ratio=%s\n' "$rep" "$w" "$vn" "$vm" "$ratio"
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== E1a2 done: $(grep -c . "$J") pairs; clos groups left: $(ls /sys/fs/resctrl 2>/dev/null | grep -c clos_ || true)"
