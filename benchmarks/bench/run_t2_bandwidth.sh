#!/usr/bin/env bash
# T2: single-core stream bandwidth by memory-access arm.
# Pre-registration: experiments/asplos/T2_WBWC_PREREG_2026-08-24.md
#
# Six arms, n reps, ARMS INTERLEAVED WITHIN EACH REP so that thermal or
# frequency drift is spread across arms instead of confounding one.
#
# Host state is RECORDED AS FOUND and deliberately not changed: mos182 and
# moscxl are shared, and running setup/*_freeze.sh to suit this measurement
# would disturb other users. Arms are compared within-host and interleaved.
#
# Arms B (stream_wb_nopf) and Cp (stream_wc_nopf) need MSR 0x1A4, which is
# Intel-specific. On AMD they are expected to exit(1) loudly; this script
# records UNAVAILABLE and continues rather than aborting the host's run.
#
# Usage: run_t2_bandwidth.sh <host-label> [outdir]
# Env:   REPS (default 5) SECS (default 10) REGION_GB (default 2) CPU (default 8) NODE (default 0)
set -uo pipefail
B=$(cd "$(dirname "$0")" && pwd)
LABEL=${1:?usage: run_t2_bandwidth.sh <host-label> [outdir]}
OUT=${2:-$B/../data/t2_bandwidth}
REPS=${REPS:-5}; SECS=${SECS:-10}; REGION_GB=${REGION_GB:-2}
CPU=${CPU:-8}; NODE=${NODE:-0}
mkdir -p "$OUT"
JSONL="$OUT/t2_${LABEL}.jsonl"
STATE="$OUT/t2_${LABEL}_state.txt"
[ -e "$JSONL" ] && { echo "FAIL $JSONL exists; refusing to append (A6.19)" >&2; exit 2; }

# --- arm table: label -> binary. Order is the interleave order. ---
ARMS=(A:stream_wb B:stream_wb_nopf C:stream_wc D:stream_nt Cp:stream_wc_nopf E:stream_sw_prefetch)

# --- record host state as found ---
{
  echo "== T2 host state as found: $LABEL @ $(date -Is)"
  echo "-- identity"; hostname; lscpu | grep -E "Model name|Socket|NUMA node\(s\)|L3 cache|Thread"
  echo "-- governor / turbo (NOT changed by this script)"
  cat /sys/devices/system/cpu/cpu$CPU/cpufreq/scaling_governor 2>/dev/null || echo "governor: n/a"
  cat /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null || echo "intel_pstate/no_turbo: n/a"
  cat /sys/devices/system/cpu/cpufreq/boost 2>/dev/null || echo "cpufreq/boost: n/a"
  echo "-- THP"; cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null
  echo "-- hugepages"; grep -E "HugePages_Total|Hugepagesize" /proc/meminfo
  echo "-- numa"; numactl --hardware 2>/dev/null | head -6
  echo "-- cpu$CPU node"; for n in /sys/devices/system/node/node*; do
      grep -qw "$CPU" <(tr ',' '\n' < "$n/cpulist" 2>/dev/null | while read -r r; do
        case $r in *-*) seq "${r%-*}" "${r#*-}";; *) echo "$r";; esac; done) \
        && echo "cpu$CPU is on $(basename "$n")"; done
  echo "-- msr device"; ls -l /dev/cpu/$CPU/msr 2>&1
  echo "-- MSR 0x1A4 as found (0 = all prefetchers enabled)"
  sudo rdmsr -p $CPU 0x1A4 2>/dev/null || echo "rdmsr unavailable"
  echo "-- build"; gcc --version | head -1; git -C "$B" rev-parse --short HEAD 2>/dev/null
} > "$STATE" 2>&1

echo "== T2 $LABEL: $REPS reps x ${#ARMS[@]} arms x ${SECS}s, region ${REGION_GB}GB, cpu$CPU node$NODE"
echo "== state -> $STATE ; data -> $JSONL"

for rep in $(seq 1 "$REPS"); do
  for entry in "${ARMS[@]}"; do
    arm=${entry%%:*}; bin=${entry##*:}
    exe="$B/aggressor/$bin"
    if [ ! -x "$exe" ]; then
      echo "{\"host\":\"$LABEL\",\"arm\":\"$arm\",\"bin\":\"$bin\",\"rep\":$rep,\"status\":\"MISSING_BINARY\"}" >> "$JSONL"
      continue
    fi
    log=$(mktemp); rc=0
    sudo "$exe" --cpu "$CPU" --node "$NODE" --region-gb "$REGION_GB" \
         --duration-sec "$SECS" >"$log" 2>"$log.err" || rc=$?
    j=$(grep -o '{.*}' "$log" | tail -1)
    if [ "$rc" -ne 0 ] || [ -z "$j" ]; then
      why=$(tr '\n' ' ' < "$log.err" | tail -c 300)
      echo "{\"host\":\"$LABEL\",\"arm\":\"$arm\",\"bin\":\"$bin\",\"rep\":$rep,\"status\":\"UNAVAILABLE\",\"rc\":$rc,\"stderr\":\"$(echo "$why" | sed 's/"/\\"/g')\"}" >> "$JSONL"
      printf '  rep%-2s %-3s %-20s UNAVAILABLE rc=%s\n' "$rep" "$arm" "$bin" "$rc"
    else
      bw=$(printf '%s' "$j" | sed -n 's/.*"avg_bw_gbps": *\([0-9.]*\).*/\1/p')
      echo "{\"host\":\"$LABEL\",\"arm\":\"$arm\",\"bin\":\"$bin\",\"rep\":$rep,\"status\":\"ok\",\"record\":$j}" >> "$JSONL"
      printf '  rep%-2s %-3s %-20s %8s GB/s\n' "$rep" "$arm" "$bin" "$bw"
    fi
    rm -f "$log" "$log.err"
  done
done
echo "== T2 $LABEL done: $(grep -c . "$JSONL") records"
