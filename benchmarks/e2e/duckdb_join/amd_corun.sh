#!/bin/bash
set -u
cat > /tmp/qa.sql <<EOF
SET threads=1;
SET memory_limit='100GB';
CREATE TABLE b AS SELECT (i%32768)::BIGINT AS k, (i*7)::BIGINT AS payload FROM range(262144) t(i);
CREATE TABLE p AS SELECT (hash(i) % 32768)::BIGINT AS k FROM range(10000000) t(i);
.timer on
EOF
for i in 1 2 3 4 5 6 7 8; do echo "SELECT count(*), sum(b.payload) FROM p JOIN b ON p.k=b.k;" >> /tmp/qa.sql; done
NDOM=$(grep -o 'L3:.*' /sys/fs/resctrl/schemata | head -1 | tr ';' '\n' | wc -l)
SCH="L3:"; for d in $(seq 0 $((NDOM-1))); do SCH="$SCH$d=ffff;"; done
echo "${SCH%;}" | sudo tee /sys/fs/resctrl/dvcat/schemata >/dev/null
arm() { MODE=$1; AN=$2; TAG=$3
  if [ "$MODE" != none ]; then /home/domin/tmp_dutyfree_exp/bin/aggressor -m $MODE -t 7 -c 9,10,11,12,13,14,15 -N $AN -s 64 -d 120 > /tmp/ac_$TAG.log 2>&1 & AP=$!; sleep 6; fi
  echo -n "$TAG: "
  numactl --membind=2 --physcpubind=8 /tmp/duckdb -c ".read /tmp/qa.sql" 2>&1 | grep 'Run Time' | sed 's/.*real //;s/ user.*//' | tr '\n' ' '
  echo -n " occ_MiB=$(( $(cat /sys/fs/resctrl/dvcat/mon_data/mon_L3_01/llc_occupancy) / 1048576 ))  "
  if [ "$MODE" != none ]; then kill $AP 2>/dev/null; wait $AP 2>/dev/null; grep -h RESULT /tmp/ac_$TAG.log; else echo; fi
}
arm none 0 quiescent
arm wb_load 2 WB_cxl
arm wb_prefetchnta 2 NTA_cxl
arm none 0 quiescent_b
