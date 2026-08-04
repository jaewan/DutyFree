#!/usr/bin/env bash
# Collect all P0/P1 arms into one table. Reads stats.txt for done runs.
row(){ # <name> <iters> <baseline_cyciter>
  local n=$1 it=${2:-300000} base=${3:-33.83} s=/tmp/$1/stats.txt
  if ! grep -q "_EXIT_\|DONE_" /tmp/$n.log 2>/dev/null; then printf "%-12s  running\n" "$n"; return; fi
  local c bi br0 br1 ss sfe
  c=$(grep -E "^system.cpu0.numCycles" "$s" 2>/dev/null|awk '{print $2}')
  bi=$(grep -E "l1d.inTransLatHist.SnpCleanInvalid::total" "$s" 2>/dev/null|awk '{print $2}'|head -1)
  br0=$(grep -E "system.mem_ctrls0.bytesRead::total" "$s" 2>/dev/null|awk '{print $2}')
  br1=$(grep -E "system.mem_ctrls1.bytesRead::total" "$s" 2>/dev/null|awk '{print $2}')
  ss=$(grep -E "^simSeconds" "$s" 2>/dev/null|awk '{print $2}')
  sfe=$(grep -E "system.ruby.Cache_Controller.SF_Eviction::total" "$s" 2>/dev/null|awk '{print $2}'|head -1)
  python3 -c "
c=$c; it=$it; base=$base; bi=${bi:-0}; br1=${br1:-0}; ss=${ss:-1}; sfe=${sfe:-0}
print(f'%-12s cyc/iter={c/it:7.2f}  tax={c/it/base:5.2f}x  backinval={int(bi):6d}  aggBW={br1/ss/1e9:6.2f}GB/s  SFevict={int(sfe):6d}' % '$n')
"
}
echo '######## GATES ########'
row gate_i3e5 300000; row gate_i3e6 3000000
echo '######## VICTIM-NEUTRALITY (alone) ########'
row vn_m2; row vn_m4; row vn_m8; row vn_nat
echo '######## H2 BANDWIDTH BAND (st,H3=0,finiteSF) — de-confound ########'
row h2_m2; row h2_m4; row h2_m8; row h2_m16; row h2_nat
echo '  [H3 reference val_h2h3: tax 1.05x, backinval 11, aggBW 3.84]'
echo '######## P1-5 WSS SWEEP (infinite SF) ########'
for W in 1250 2650 5000; do b=$(grep -E "^system.cpu0.numCycles" /tmp/w5_a$W/stats.txt 2>/dev/null|awk '{print $2/300000}'); b=${b:-33.83};
  echo "-- WSS=$W (base=$b) --"; row w5_a$W 300000 $b; row w5_wb$W 300000 $b; row w5_st$W 300000 $b; done
echo '######## P1-4 ASSOC SWEEP (infinite SF) ########'
for A in 8 12 20; do b=$(grep -E "^system.cpu0.numCycles" /tmp/a4_a$A/stats.txt 2>/dev/null|awk '{print $2/300000}'); b=${b:-33.83};
  echo "-- assoc=$A (base=$b) --"; row a4_a$A 300000 $b; row a4_wb$A 300000 $b; row a4_st$A 300000 $b; done
