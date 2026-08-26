#!/usr/bin/env bash
# M6 pass A: F's own cost under {table} x {stream} x {CAT}. No victim.
# Pre-registration: experiments/asplos/M6_FRONTIER_PREREG_2026-08-26.md
# F's stdout is captured here because the co-run pass (B) kills F before it prints.
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
FUSED=$B/../e2e/hash_join/build/cxl_join_bench
CLOS=$B/../e2e/hash_join/scripts/resctrl_clos.sh
OUT=${1:-$B/../data/m6a_fcost}; REPS=${REPS:-3}
mkdir -p "$OUT"; J="$OUT/m6a.jsonl"
[ -e "$J" ] && { echo "FAIL $J exists (A6.19)" >&2; exit 2; }
echo "== as-found resctrl groups: $(ls /sys/fs/resctrl | grep -c clos_ || true)"
trap 'sudo bash "$CLOS" teardown >/dev/null 2>&1 || true' EXIT
for cat in none narrow; do
  if [ "$cat" = narrow ]; then sudo bash "$CLOS" setup_c 2 32-47 8 >/dev/null 2>&1
  else sudo bash "$CLOS" teardown >/dev/null 2>&1; fi
  for tbl in 4m 256m; do
    hb=177838489; [ "$tbl" = 4m ] && hb=4194304
    for sm in retain flush; do
      fd=0; [ "$sm" = flush ] && fd=262144
      for r in $(seq 1 "$REPS"); do
        o=$("$FUSED" --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 256m \
             --hot-bytes $hb --morsel 1m --warmups 1 --reps 4 --cpu-list 32-47 --threads 16 \
             --hit-rate 1.0 --flush-distance $fd 2>/dev/null | grep -o '{.*}' | tail -1)
        [ -z "$o" ] && { echo "  FAIL cat=$cat tbl=$tbl sm=$sm rep=$r" >&2; continue; }
        REC="{\"cat\":\"$cat\",\"table\":\"$tbl\",\"stream\":\"$sm\",\"rep\":$r,\"record\":$o}"
        printf '%s\n' "$REC" | python3 -c 'import json,sys;json.loads(sys.stdin.read())' 2>/dev/null \
          && printf '%s\n' "$REC" >> "$J" || { echo "FATAL bad JSON" >&2; exit 3; }
        cpa=$(printf '%s' "$o" | sed -n 's/.*"active_cycles_per_access":\([0-9.]*\).*/\1/p')
        bw=$(printf '%s' "$o" | sed -n 's/.*"stream_bandwidth_gbps":\([0-9.]*\).*/\1/p')
        printf '  cat=%-6s tbl=%-4s %-6s rep%s  cyc/acc=%-8s stream=%s GB/s\n' "$cat" "$tbl" "$sm" "$r" "${cpa:-?}" "${bw:-?}"
      done
    done
  done
done
sudo bash "$CLOS" teardown >/dev/null 2>&1
echo "== M6a done: $(grep -c . "$J") records; resctrl groups left: $(ls /sys/fs/resctrl | grep -c clos_ || true)"
