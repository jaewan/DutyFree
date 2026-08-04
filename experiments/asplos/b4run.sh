#!/usr/bin/env bash
# b4run.sh <name> <victim_tag alone|wb|st> <SF_FINITE> <H3>
# SF geometry + DMT come from env: HNF_SF_SETS HNF_SF_WAYS HNF_H3 HNF_DMT
set -u
NAME=$1; TAG=$2; SFF=$3; H3=$4; WSS=2650; ITERS=300000; AGG=10.0
SETS=${HNF_SF_SETS:-512}; WAYS=${HNF_SF_WAYS:-8}; DMT=${HNF_DMT:-0}
cd ~/DutyFree-Gem5
G=build_Intel_8592/gem5.opt
V=testcase/dirtax/victim; A=testcase/dirtax/aggressor; SA=testcase/dutyfree/aggressor; D=testcase/dirtax/dummy
COMMON="configs/deprecated/example/se.py --ruby --topology=Pt2Pt --chi-config=$HOME/DutyFree-Gem5/configs/ruby/CHI_config_8592.py --num-l3caches=1 --num-dirs=1 --cpu-type=O3CPU --num-cpus=2 --cpu-clock=1.9GHz --l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 --l2_size=2MiB --l2_assoc=16 --l3_size=5MiB --l3_assoc=20 --mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB --dram-latency=98ns --cxl-latency=203ns"
case $TAG in
  alone) C="$V;$D"; O="$WSS $ITERS;";;
  wb)    C="$V;$A"; O="$WSS $ITERS;$AGG";;
  st)    C="$V;$SA"; O="$WSS $ITERS;$AGG";;
esac
rm -rf /tmp/$NAME
env RUBY_RANDOMIZATION=1 HNF_SF_FINITE=$SFF HNF_SF_SETS=$SETS HNF_SF_WAYS=$WAYS HNF_H3=$H3 HNF_DMT=$DMT \
  $G --outdir=/tmp/$NAME $COMMON -c "$C" --options "$O" > /tmp/$NAME.log 2>&1
echo "DONE_$? SETS=$SETS WAYS=$WAYS $(date +%s)" >> /tmp/$NAME.log
