#!/bin/bash
set -u
cd /tmp
mk() { NB=$1; NK=$2; PR=$3; cat > /tmp/qa.sql <<EOF
SET threads=1;
SET memory_limit='100GB';
CREATE TABLE b AS SELECT (i%$NK)::BIGINT AS k, (i*7)::BIGINT AS payload FROM range($NB) t(i);
CREATE TABLE p AS SELECT (hash(i) % $NK)::BIGINT AS k FROM range($PR) t(i);
.timer on
SELECT count(*), sum(b.payload) FROM p JOIN b ON p.k=b.k;
SELECT count(*), sum(b.payload) FROM p JOIN b ON p.k=b.k;
SELECT count(*), sum(b.payload) FROM p JOIN b ON p.k=b.k;
EOF
}
sudo mkdir -p /sys/fs/resctrl/dvcat
echo 8 | sudo tee /sys/fs/resctrl/dvcat/cpus_list >/dev/null
NDOM=$(grep -o 'L3:.*' /sys/fs/resctrl/schemata | head -1 | tr ';' '\n' | wc -l)
gate() { MASK=$1; NODE=$2; TAG=$3
  SCH="L3:"; for d in $(seq 0 $((NDOM-1))); do if [ $d -eq 1 ]; then SCH="$SCH$d=$MASK;"; else SCH="$SCH$d=ffff;"; fi; done
  echo "${SCH%;}" | sudo tee /sys/fs/resctrl/dvcat/schemata >/dev/null
  echo -n "$TAG mask=$MASK node=$NODE times:"
  numactl --membind=$NODE --physcpubind=8 /tmp/duckdb -c ".read /tmp/qa.sql" 2>&1 | grep 'Run Time' | sed 's/.*real //;s/ user.*//' | tr '\n' ' '
  echo "occ_MiB=$(( $(cat /sys/fs/resctrl/dvcat/mon_data/mon_L3_01/llc_occupancy) / 1048576 ))"
}
mk 262144 32768 10000000
for N in 0 2; do gate ffff $N "amd_chain8_b256K"; gate 1 $N "amd_chain8_b256K"; done
mk 262144 262144 10000000
for N in 0 2; do gate ffff $N "amd_uniq_b256K"; gate 1 $N "amd_uniq_b256K"; done
