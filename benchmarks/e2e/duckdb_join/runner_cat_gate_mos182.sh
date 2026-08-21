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
echo 4 | sudo tee /sys/fs/resctrl/dvcat/cpus_list >/dev/null
gate() { MASK=$1; NODE=$2; TAG=$3
  echo "L3:0=$MASK;1=7fff" | sudo tee /sys/fs/resctrl/dvcat/schemata >/dev/null
  echo -n "$TAG mask=$MASK node=$NODE times:"
  numactl --membind=$NODE --physcpubind=4 /tmp/duckdb -c ".read /tmp/qa.sql" 2>&1 | grep 'Run Time' | sed 's/.*real //;s/ user.*//' | tr '\n' ' '
  echo "occ_MiB=$(( $(cat /sys/fs/resctrl/dvcat/mon_data/mon_L3_00/llc_occupancy) / 1048576 ))"
}
mk 1000000 125000 10000000
for N in 0 2; do gate 7fff $N "i2_chain8_b1M"; gate 1 $N "i2_chain8_b1M"; done
mk 1000000 1000000 20000000
for N in 0 2; do gate 7fff $N "i2_uniq_b1M"; gate 1 $N "i2_uniq_b1M"; done
