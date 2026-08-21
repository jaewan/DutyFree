#!/bin/bash
set -u
/home/domin/tmp_dutyfree_exp/bin/amd_flushbehind_aggressor --help 2>&1 | head -8
arm() { CMD="$1"; TAG=$2
  if [ -n "$CMD" ]; then $CMD > /tmp/afb_$TAG.log 2>&1 & AP=$!; sleep 6; fi
  echo -n "$TAG: "
  numactl --membind=2 --physcpubind=8 /tmp/duckdb -c ".read /tmp/qa.sql" 2>&1 | grep 'Run Time' | sed 's/.*real //;s/ user.*//' | tr '\n' ' '
  echo -n " occ_MiB=$(( $(cat /sys/fs/resctrl/dvcat/mon_data/mon_L3_01/llc_occupancy) / 1048576 ))  "
  if [ -n "$CMD" ]; then kill $AP 2>/dev/null; wait $AP 2>/dev/null; grep -hE 'RESULT|GB/s' /tmp/afb_$TAG.log | tail -2; else echo; fi
}
arm "" quiescent
arm "/home/domin/tmp_dutyfree_exp/bin/amd_flushbehind_aggressor -f 256 -t 7 -c 9,10,11,12,13,14,15 -N 2 -s 64 -d 200" flushbehind256
