#!/usr/bin/env bash
# P1-4 (assoc) + P1-5 (WSS on real setstreaming path). Infinite SF (SFF=0) -> no self-thrash.
# H2 recovery = data-array non-allocation, does not need finite SF. ITERS=3e5 exploratory.
set -u
launch(){ local s=$1; shift; local e=$1; shift
  tmux kill-session -t "$s" 2>/dev/null
  tmux new-session -d -s "$s" "cd ~/DutyFree-Gem5; env $e /tmp/b4run2.sh $*; echo ${s}_EXIT_\$? >> /tmp/$1.log"
}

# --- P1-5: WSS/LLC-ratio sweep, real setstreaming (st) vs wb vs alone, infinite SF ---
for W in 1250 2650 5000; do
  launch w5_a$W "WSS=$W" w5_a$W alone 0 0
  launch w5_wb$W "WSS=$W" w5_wb$W wb 0 0
  launch w5_st$W "WSS=$W" w5_st$W st 0 0
done

# --- P1-4: LLC associativity sweep at fixed 53% WSS, infinite SF ---
for A in 8 12 20; do
  launch a4_a$A "L3_ASSOC=$A" a4_a$A alone 0 0
  launch a4_wb$A "L3_ASSOC=$A" a4_wb$A wb 0 0
  launch a4_st$A "L3_ASSOC=$A" a4_st$A st 0 0
done

echo "launched P1:"; tmux ls 2>/dev/null | grep -cE "w5_|a4_"
