#!/usr/bin/env bash
# W1: the two missing cells of tab:h3sf -- H2 and H2+H3 at INFINITE SF.
#
# tab:h3sf (re-measured 2026-08-20) is a 2x3 design with the load-bearing cell
# empty. H2 has never been tested against the capacity-only charge, which is
# the only charge either production host exhibits. See PLAN_B_REBUILD.md W1 for
# the pre-registered predictions and decision rules.
#
# Apparatus reconstructed from /tmp/sf_h2_fin_s1/config.ini, because the
# original launcher was typed at the shell and never committed (W4 item). The
# reconstruction is exact except HNF_SF_FINITE, which is the variable under
# test:
#   victim     testcase/dutyfree/victim 2650 3000000
#   aggressor  testcase/dutyfree/aggressor 16.0 stream   <- "stream" IS the H2
#                                                           declaration (gem5
#                                                           356e7b7d0e)
#   SF finite  4 MiB / 16-way = 65,536 entries (only bound when FINITE=1)
#   DMT off, RUBY_RANDOMIZATION=1, seeds 1..3
#
# NOTE on provenance: H3SF_REMEASURED_2026-08-20.md attributes the table to
# gem5 0f37c28. The runs actually used 356e7b7d0e -- 0f37c28 predates the
# argv[2] streaming gate those runs depend on. Recorded, not reconciled.
set -u
cd ~/DutyFree-Gem5
G=build_Intel_8592/gem5.opt
V=testcase/dutyfree/victim; A=testcase/dutyfree/aggressor
COMMON="configs/deprecated/example/se.py --ruby --topology=Pt2Pt \
--chi-config=$HOME/DutyFree-Gem5/configs/ruby/CHI_config_8592.py \
--num-l3caches=1 --num-dirs=1 --cpu-type=O3CPU --num-cpus=2 --cpu-clock=1.9GHz \
--l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
--l2_size=2MiB --l2_assoc=16 --l3_size=5MiB --l3_assoc=20 \
--mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
--dram-latency=98ns --cxl-latency=203ns"

for s in 1 2 3; do
  for cell in "sf_h2_inf:0" "sf_h3_inf:1"; do
    N=${cell%:*}_s$s; H3=${cell#*:}
    rm -rf /tmp/$N
    env RUBY_RANDOMIZATION=1 SEED=$s \
        HNF_SF_FINITE=0 HNF_SF_SETS=4096 HNF_SF_WAYS=16 HNF_H3=$H3 HNF_DMT=0 \
      $G --outdir=/tmp/$N $COMMON -c "$V;$A" --options "2650 3000000;16.0 stream" \
      > /tmp/$N.log 2>&1
    echo "DONE_$? NAME=$N H3=$H3 SF_FINITE=0 SEED=$s $(date +%s)" >> /tmp/$N.log
  done &
done
wait
echo "W1_SWEEP_DONE" > /tmp/w1_sf_inf.done
