#!/bin/bash
# A6 (Amendment 6, DUCKDB_JOIN_CORUN_PREREGISTRATION.md @ 08d0775):
# AMD co-run re-run, n=30, all nine arms, one contiguous night block from 22:00.
# Nothing changes from the campaign except REPS. No VICTIM_PRELOAD.
set -u
cd "$HOME/DutyFree/benchmarks/e2e/duckdb_join" || exit 1
LOG="$HOME/DutyFree/benchmarks/e2e/duckdb_join/artifacts/corun30_moscxl.log"
mkdir -p "$(dirname "$LOG")"

# --- start time ------------------------------------------------------------
# Declared 22:00 (A6.2). A6_START_NOW=1 starts immediately instead; that is a
# deviation from the pre-registration and is only legitimate as the lead-
# directed one recorded in A6.8. It is never taken on the runner's judgement.
NOW=$(date +%s)
if [ "${A6_START_NOW:-0}" = "1" ]; then
  TARGET=$NOW
else
  TARGET=$(date -d 'today 22:00' +%s)
  [ "$TARGET" -le "$NOW" ] && TARGET=$(date -d 'tomorrow 22:00' +%s)
fi
{
  echo "=== A6 re-run, pre-registration 08d0775 ==="
  echo "launched  $(date -Iseconds)"
  echo "start at  $(date -d "@$TARGET" -Iseconds)  (waiting $((TARGET-NOW))s)"
} >>"$LOG"
sleep $((TARGET-NOW))
sleep 30   # let any login/session burst settle before hostguard looks

# --- A6.2: verify the freeze and record it BEFORE the first arm ------------
{
  echo
  echo "=== freeze verification against d8eda44, $(date -Iseconds) ==="
  echo "governors distinct : $(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort -u | tr '\n' ' ')"
  echo "cpufreq boost      : $(cat /sys/devices/system/cpu/cpufreq/boost)"
  echo "numa_balancing     : $(cat /proc/sys/kernel/numa_balancing)"
  echo "perf_event_paranoid: $(cat /proc/sys/kernel/perf_event_paranoid)"
  echo "THP enabled        : $(cat /sys/kernel/mm/transparent_hugepage/enabled)"
  echo "cur freq cpu8      : $(cat /sys/devices/system/cpu/cpu8/cpufreq/scaling_cur_freq)"
  echo "boot               : $(uptime -s)"
  echo "runner md5         : $(md5sum run_join_campaign.py | cut -d' ' -f1)"
  echo "expected           : governors=performance boost=0 numa_balancing=0 paranoid=-1 THP=madvise freq~2250000 runner=dc90186ba057584e9b06a8354b4db73f"
  echo
} >>"$LOG"

# --- the run ---------------------------------------------------------------
MODE=corun30 CHAIN=8 REPS=30 BUILDS=100000 PROBE=250000 QUERIES=301 \
  python3 -u run_join_campaign.py >>"$LOG" 2>&1
rc=$?
echo "=== A6 exit rc=$rc  $(date -Iseconds)  records=$(wc -l < artifacts/join_corun30_moscxl.jsonl 2>/dev/null || echo 0) ===" >>"$LOG"
