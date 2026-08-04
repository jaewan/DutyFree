#!/usr/bin/env bash
# exp35 — SMBA (AMD slow-memory bandwidth QoS for CXL) vs admission-control Pareto.
# Round-3 reviewer mandate: test the bandwidth knob AMD built for CXL, not just CAT.
# Victim = 4 MiB pointer chase on cpu0 (reads LOCAL DRAM). Aggressor = 7 threads on
# cpus1-7 (same CCX / L3 domain 0) streaming from CXL node2 (SLOW memory).
# SMBA throttles only the aggressor's COS slow-memory BW -> hits the CXL reader,
# not the DRAM-reading victim. Isolate the bandwidth knob: L3 unrestricted in the
# SMBA arms. Aggressor runs to completion and self-reports bw_gbps (dead-agg guard).
set -uo pipefail
cd /home/domin/tmp_dutyfree_exp
R=/sys/fs/resctrl; V=./bin/victim; A=./bin/aggressor
REPS=${1:-5}
SMBA_VALS="${2:-2048 1024 512 256 128 64 32}"
AGGLOG=/tmp/exp35_agg.log
OUT=${OUT:-/tmp/exp35_results.tsv}

cleanup(){ pkill -f "bin/aggressor" 2>/dev/null; sleep 0.3
  echo 0-511 > $R/cpus_list 2>/dev/null || true
  rmdir $R/h3v $R/h3a 2>/dev/null || true; }
trap cleanup EXIT
assert_dead(){ if pgrep -f "bin/aggressor" >/dev/null; then
    echo "WARN: aggressor survived; killing -9"; pkill -9 -f "bin/aggressor"; sleep 0.5; fi; }

vipc(){ $V -c 0 -w 4096 -P -d 8 -W 2 2>/dev/null | grep -oE "ipc=[0-9.]+" | head -1 | cut -d= -f2; }
agg_bw(){ grep -oE "bw_gbps=[0-9.]+" "$AGGLOG" | head -1 | cut -d= -f2; }

cleanup; mkdir -p $R/h3v $R/h3a
echo 0 > $R/h3v/cpus_list; echo 1-7 > $R/h3a/cpus_list
echo -e "arm\trep\tsmba\tagg_bw\tvipc" > $OUT

# baseline: no aggressor
for r in $(seq 1 $REPS); do echo -e "baseline\t$r\tNA\t0\t$(vipc)" >> $OUT; done

# one arm: set victim/aggressor schemata, run aggressor to completion, measure victim mid-run
run_arm(){ local name=$1 mode=$2 vL3=$3 aL3=$4 aSMBA=$5
  printf "L3:0=%s\nSMBA:0=2048\n" "$vL3"   > $R/h3v/schemata
  printf "L3:0=%s\nSMBA:0=%s\n"   "$aL3" "$aSMBA" > $R/h3a/schemata
  for r in $(seq 1 $REPS); do
    assert_dead
    ( $A -m "$mode" -t 7 -c 1,2,3,4,5,6,7 -N 2 -s 64 -d 16 >"$AGGLOG" 2>&1 ) & local AP=$!
    sleep 2
    local ip; ip=$(vipc)
    wait $AP 2>/dev/null
    local bw; bw=$(agg_bw)
    assert_dead
    echo -e "$name\t$r\t$aSMBA\t${bw:-0}\t${ip:-NA}" >> $OUT
    printf '  %-14s rep%s smba=%-5s bw=%-7s ipc=%s\n' "$name" "$r" "$aSMBA" "${bw:-0}" "${ip:-NA}"
  done
}

# reference arms
run_arm wb_full     wb_load   ffff ffff 2048   # full-BW WB, no QoS
run_arm cat_8_8     wb_load   ff00 00ff 2048   # CAT 8/8 way split, full BW
run_arm wc_nonalloc wc_ntdqa  ffff ffff 2048   # non-allocating (admission denial)
# SMBA sweep: L3 unrestricted, throttle only aggressor slow-mem (CXL) BW
for v in $SMBA_VALS; do run_arm "smba_$v" wb_load ffff ffff $v; done
# combined CAT+SMBA (operator's actual toolkit), a couple of points
run_arm cat_smba_512 wb_load ff00 00ff 512
run_arm cat_smba_128 wb_load ff00 00ff 128

echo "=== DONE $(date +%s) ==="; column -t $OUT
