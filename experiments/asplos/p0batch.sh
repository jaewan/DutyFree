#!/usr/bin/env bash
# P0-1 de-confound batch. Each run in its own tmux session (loop-& unreliable).
# Finite-SF knee = SETS=8192 WAYS=8 (65536 entries). DMT off (assert-guarded).
set -u
SF="HNF_SF_SETS=8192 HNF_SF_WAYS=8 HNF_DMT=0"
launch(){ # <session> <envstr> <b4run2 args...>
  local s=$1; shift; local e=$1; shift
  tmux kill-session -t "$s" 2>/dev/null
  tmux new-session -d -s "$s" "cd ~/DutyFree-Gem5; env $e /tmp/b4run2.sh $*; echo ${s}_EXIT_\$? >> /tmp/$1.log"
}

# --- ITERS contamination gate (aggressor-free, fast) ---
launch g_i3e5 "ITERS=300000  $SF"                          gate_i3e5 alone 1 0
launch g_i3e6 "ITERS=3000000 $SF"                          gate_i3e6 alone 1 0

# --- Victim-neutrality: alone across MSHR caps (must be flat) ---
launch vn_m2   "L1_MSHR=2  L2_MSHR=2  $SF"                  vn_m2   alone 1 0
launch vn_m4   "L1_MSHR=4  L2_MSHR=4  $SF"                  vn_m4   alone 1 0
launch vn_m8   "L1_MSHR=8  L2_MSHR=8  $SF"                  vn_m8   alone 1 0
launch vn_nat  "$SF"                                        vn_nat  alone 1 0

# --- H2 bandwidth band: st (H3=0) throttled via MSHR caps ---
launch h2_m2   "L1_MSHR=2  L2_MSHR=2  $SF"                  h2_m2   st 1 0
launch h2_m4   "L1_MSHR=4  L2_MSHR=4  $SF"                  h2_m4   st 1 0
launch h2_m8   "L1_MSHR=8  L2_MSHR=8  $SF"                  h2_m8   st 1 0
launch h2_m16  "L1_MSHR=16 L2_MSHR=16 $SF"                  h2_m16  st 1 0
launch h2_nat  "$SF"                                        h2_nat  st 1 0

echo "launched:"; tmux ls 2>/dev/null | grep -E "g_i|vn_|h2_"
