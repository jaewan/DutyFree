#!/bin/bash
set -u
arm() { MODE=$1; AN=$2; TAG=$3
  if [ "$MODE" != none ]; then /home/domin/tmp_dutyfree_exp/bin/aggressor -m $MODE -t 7 -c 9,10,11,12,13,14,15 -N $AN -s 64 -d 200 > /tmp/ac_$TAG.log 2>&1 & AP=$!; sleep 6; fi
  echo -n "$TAG: "
  numactl --membind=2 --physcpubind=8 /tmp/duckdb -c ".read /tmp/qa.sql" 2>&1 | grep 'Run Time' | sed 's/.*real //;s/ user.*//' | tr '\n' ' '
  echo -n " occ_MiB=$(( $(cat /sys/fs/resctrl/dvcat/mon_data/mon_L3_01/llc_occupancy) / 1048576 ))  "
  if [ "$MODE" != none ]; then kill $AP 2>/dev/null; wait $AP 2>/dev/null; grep -h RESULT /tmp/ac_$TAG.log; else echo; fi
}
arm wb_prefetchnta 2 NTA_cxl
arm wb_local 0 WB_local
arm none 0 quiescent_b
