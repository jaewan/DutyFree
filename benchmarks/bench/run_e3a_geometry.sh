#!/usr/bin/env bash
# E3 pass A: the occupancy knee on a DIFFERENT cache geometry (mos182: 60 MiB / 15 ways).
# Pre-registration: experiments/asplos/E3_GEOMETRY_PREREG_2026-08-28.md
# Victim alone, confined to k_v ways, WSS swept. No tenant runs.
# NOTE: resctrl_clos.sh's echo hardcodes "20 - scan_ways" so its printed way count
# is wrong on a 15-way part; the MASK it writes is computed from FULL_MASK and is
# correct. This runner records the mask, never the echo.
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
VIC=$B/victim/pointer_chase
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/e3a_geometry}; REPS=${REPS:-6}
SEC=${SEC:-1}; TRIALS=${TRIALS:-6}; VCPU=${VCPU:-8}; TCPUS=${TCPUS:-16-31}
WAYS_TOTAL=$(python3 -c "print(bin(int(open('/sys/fs/resctrl/info/L3/cbm_mask').read().strip(),16)).count('1'))")
VWAYS=(5 10 14)                                   # victim ways
WSSL=(8388608 16777216 25165824 33554432 50331648) # 8/16/24/32/48 MiB
mkdir -p "$OUT"; J="$OUT/e3a.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
[ -x "$VIC" ] || { echo "FAIL missing $VIC" >&2; exit 2; }
echo "== host $(hostname), $WAYS_TOTAL ways total, cbm_mask=$(cat /sys/fs/resctrl/info/L3/cbm_mask)"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT

CELLS=()
for w in "${WSSL[@]}"; do CELLS+=("none:$w"); done
for k in "${VWAYS[@]}"; do for w in "${WSSL[@]}"; do CELLS+=("$k:$w"); done; done
NC=${#CELLS[@]}; echo "== $NC cells x $REPS reps = $((NC*REPS)) runs"
for rep in $(seq 1 "$REPS"); do
  off=$(( (rep-1) * 7 % NC )); pos=0
  for i in $(seq 0 $((NC-1))); do
    IFS=: read -r kv w <<< "${CELLS[$(( (i+off) % NC ))]}"
    pos=$((pos+1))
    if [ "$kv" = none ]; then
      sudo bash "$CLOS" teardown >/dev/null 2>&1
      sch="ROOT:$(grep -m1 L3 /sys/fs/resctrl/schemata | tr -d ' ')"; vmask=""
    else
      sw=$((WAYS_TOTAL - kv))
      sudo bash "$CLOS" setup_c "$sw" "$TCPUS" "$VCPU" >/dev/null 2>&1
      vmask=$(grep -o 'L3:0=[0-9a-f]*' /sys/fs/resctrl/clos_c_probe/schemata | cut -d= -f2)
      vbits=$(python3 -c "print(bin(int('$vmask',16)).count('1'))")
      [ "$vbits" != "$kv" ] && { echo "FATAL victim mask $vmask has $vbits ways, wanted $kv" >&2; exit 5; }
      vcpu_l=$(cat /sys/fs/resctrl/clos_c_probe/cpus_list)
      [ "$vcpu_l" != "$VCPU" ] && { echo "FATAL victim cpus_list='$vcpu_l' wanted $VCPU" >&2; exit 5; }
      sch=$(cat /sys/fs/resctrl/clos_*/schemata | tr -d ' ' | grep -o 'L3:[^ ]*' | tr '\n' ';')
    fi
    o=$(mktemp)
    "$VIC" --cpu "$VCPU" --node 0 --wss "$w" --run-sec "$SEC" --trials "$TRIALS" >"$o" 2>/dev/null
    med=$(python3 -c "
import json,statistics as st
d=json.load(open('$o')); v=[x['cycles_per_load'] for x in d]
print(f'{st.median(v):.4f}' if v else 'null')" 2>/dev/null)
    REC="{\"victim_ways\":\"$kv\",\"ways_total\":$WAYS_TOTAL,\"wss\":$w,\"rep\":$rep,\"pos\":$pos,\"victim_cyc_per_load\":${med:-null},\"victim_mask\":\"$vmask\",\"schemata\":\"$sch\"}"
    printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
      && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad record" >&2; exit 3; }
    printf '  rep%-2s pos%-3s kv=%-5s wss=%-5s victim=%s\n' "$rep" "$pos" "$kv" "$((w>>20))M" "${med:-NA}"
    rm -f "$o"
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== E3a done: $(grep -c . "$J") records (expect $((REPS*NC))); groups left: $(ls /sys/fs/resctrl | grep -c clos_ || true)"
