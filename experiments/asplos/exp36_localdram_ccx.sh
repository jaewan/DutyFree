#!/usr/bin/env bash
# exp36 — panel Tier-1 controls. Victim = 4 MiB pointer chase on cpu0 (CCX0, local DRAM).
#  #1 local-DRAM vs CXL aggressor, +/- CAT  -> is the CAT residual CXL-specific (fill-latency
#      occupancy, which a shared-only bypass would NOT remove) or general (lookup/fill path)?
#  #2 residual-vs-bandwidth under CAT (CXL, threads 1..7) -> occupancy vs footprint.
#  #3 aggressor on a DIFFERENT CCX (cores 8-14) -> confirms the tax is a shared-L3 effect (~1.0x).
#  #4 SMT: victim cpu0 sibling=256 stays idle (aggressor on 1-7 or 8-14); recorded, not run.
# Integrity: aggressor runs to completion and self-reports bw_gbps; assert no orphans; verify bw>0.
set -uo pipefail
cd /home/domin/tmp_dutyfree_exp
R=/sys/fs/resctrl; V=./bin/victim; A=./bin/aggressor
REPS=${1:-5}
AGGLOG=/tmp/exp36_agg.log
OUT=${OUT:-/tmp/exp36_results.tsv}

cleanup(){ pkill -f "bin/aggressor" 2>/dev/null; sleep 0.3
  echo 0-511 > $R/cpus_list 2>/dev/null || true
  rmdir $R/h3v $R/h3a 2>/dev/null || true; }
trap cleanup EXIT
assert_dead(){ pgrep -f "bin/aggressor" >/dev/null && { echo "WARN kill -9"; pkill -9 -f "bin/aggressor"; sleep 0.5; }; }
vipc(){ $V -c 0 -w 4096 -P -d 8 -W 2 2>/dev/null | grep -oE "ipc=[0-9.]+" | head -1 | cut -d= -f2; }
agg_bw(){ grep -oE "bw_gbps=[0-9.]+" "$AGGLOG" | head -1 | cut -d= -f2; }

cleanup; mkdir -p $R/h3v $R/h3a
echo 0 > $R/h3v/cpus_list
echo -e "arm\trep\tnode\tcores\tcat\tagg_bw\tvipc" > $OUT

# arm: name mode node "corelist" vL3 aL3 aggcpus_for_group
run_arm(){ local name=$1 node=$2 cores=$3 vL3=$4 aL3=$5 grpcpus=$6
  echo "$grpcpus" > $R/h3a/cpus_list
  printf "L3:0=%s\nSMBA:0=2048\n" "$vL3" > $R/h3v/schemata 2>/dev/null || echo "L3:0=$vL3" > $R/h3v/schemata
  printf "L3:0=%s\nSMBA:0=2048\n" "$aL3" > $R/h3a/schemata 2>/dev/null || echo "L3:0=$aL3" > $R/h3a/schemata
  for r in $(seq 1 $REPS); do
    assert_dead
    ( $A -m wb_load -t $(echo $cores|tr ',' '\n'|wc -l) -c "$cores" -N $node -s 64 -d 16 >"$AGGLOG" 2>&1 ) & local AP=$!
    sleep 2; local ip; ip=$(vipc); wait $AP 2>/dev/null; local bw; bw=$(agg_bw); assert_dead
    echo -e "$name\t$r\t$node\t$cores\t$vL3/$aL3\t${bw:-0}\t${ip:-NA}" >> $OUT
    printf '  %-12s rep%s node%s bw=%-7s ipc=%s\n' "$name" "$r" "$node" "${bw:-0}" "${ip:-NA}"
  done
}

for r in $(seq 1 $REPS); do echo -e "baseline\t$r\t-\t-\t-\t0\t$(vipc)" >> $OUT; done
# #1 the 2x2 core comparison (same CCX0, 7 threads): CXL vs local-DRAM, no-CAT vs CAT(8/8)
run_arm cxl_nocat  2 "1,2,3,4,5,6,7" ffff ffff "1-7"
run_arm cxl_cat    2 "1,2,3,4,5,6,7" ff00 00ff "1-7"
run_arm dram_nocat 0 "1,2,3,4,5,6,7" ffff ffff "1-7"
run_arm dram_cat   0 "1,2,3,4,5,6,7" ff00 00ff "1-7"
# #2 residual-vs-bandwidth under CAT (CXL): sweep aggressor threads
run_arm cxlcat_t1  2 "1"             ff00 00ff "1"
run_arm cxlcat_t2  2 "1,2"           ff00 00ff "1-2"
run_arm cxlcat_t3  2 "1,2,3"         ff00 00ff "1-3"
run_arm cxlcat_t5  2 "1,2,3,4,5"     ff00 00ff "1-5"
# #3 different CCX (cores 8-14, CCX1): no shared L3 with victim cpu0 -> expect ~1.0x
run_arm diffccx    2 "8,9,10,11,12,13,14" ffff ffff "8-14"
echo "=== DONE $(date +%s) ==="; column -t $OUT
