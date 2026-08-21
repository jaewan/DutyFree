#!/bin/bash
NB=$1; NODE=$2; MODE=$3; AGGNODE=$4
if [ "$MODE" != none ]; then
  /home/domin/tmp_dutyfree_exp/bin/aggressor -m $MODE -t 8 -c 8,9,10,11,12,13,14,15 -N $AGGNODE -s 512 -d 120 > /tmp/claude-1001/ag_${MODE}_${AGGNODE}.log 2>&1 &
  AP=$!
fi
OUT=$(numactl --membind=$NODE --physcpubind=40 ./duckdb -c ".read /tmp/claude-1001/q_$NB.sql" 2>&1 | grep 'Run Time' | sed 's/.*real //;s/ user.*//' | tr '\n' ' ')
echo "build=$NB victim_node=$NODE agg=$MODE@node$AGGNODE  times: $OUT"
if [ "$MODE" != none ]; then kill $AP 2>/dev/null; wait $AP 2>/dev/null; grep -h RESULT /tmp/claude-1001/ag_${MODE}_${AGGNODE}.log; fi
