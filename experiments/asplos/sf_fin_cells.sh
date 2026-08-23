#!/usr/bin/env bash
# W1/W3: the FINITE-SF sibling of sf_inf_cells.sh -- four arms x three seeds.
#
# WHY THIS EXISTS. The finite-SF arms behind tab:h3sf (the 2026-08-20 remeasure)
# were launched from a shell line that was never committed. That is F10, and it
# is not repairable: this script does NOT recover the provenance of those runs
# and must never be described as doing so (S6.6 -- when provenance is gone, say
# it is gone). What it does is make a *re-measurement* reproducible, on the same
# commit and the same geometry as the infinite arms, so that finite and infinite
# become comparable without a cross-campaign caveat.
#
# WHEN TO RUN IT. Not on a whim. Two documents currently place a finite number
# beside an infinite one and both flag the gap rather than closing it:
#   W1.4_CHARGE_DECOMPOSITION_2026-08-24.md  -- "if this comparison ever becomes
#       load-bearing, the finite arms must be re-run"
#   W1.5_H3_INFINITE_SF_OUTCOME_2026-08-24.md -- flags the 151.1 vs 152.2
#       agreement as not-load-bearing for exactly this reason
#   W3.4_H3_PERFORMANCE_CASE_2026-08-24.md   -- puts 2.512x -> 1.061x (finite)
#       in the same table as -3.45% (infinite), for a lead decision
# Run it when one of those becomes load-bearing, or when the lead wants the
# finite column re-grounded. It is 12 O3CPU cells and will occupy the machine.
#
# THE ONLY DIFFERENCE FROM sf_inf_cells.sh IS HNF_SF_FINITE=1, plus the qui and
# wb arms, which sf_inf_cells.sh did not launch (they came from the earlier
# campaign). Geometry, commit, seeds, randomization and DMT setting are
# identical by construction -- the COMMON block below is copied verbatim.
#
# GUARD. This script does nothing unless SF_FIN_GO=1 is set in the environment.
# A launcher that starts a 12-cell campaign because someone typed --help is a
# defect we have already had once (A6.19); this one cannot.
set -u

if [ "${SF_FIN_GO:-0}" != "1" ]; then
  cat <<'MSG'
sf_fin_cells.sh: refusing to launch without SF_FIN_GO=1.

  12 cells (4 arms x 3 seeds), O3CPU, gem5 356e7b7d0e, ~hours, writes /tmp/sf_*_fin_s*.
  Check that no other gem5 campaign is running first:  pgrep -c -f 'build_.*gem5.opt'

  To launch:  SF_FIN_GO=1 experiments/asplos/sf_fin_cells.sh
MSG
  exit 3
fi

cd ~/DutyFree-Gem5 || exit 1
G=build_Intel_8592/gem5.opt
V=testcase/dutyfree/victim; A=testcase/dutyfree/aggressor; D=testcase/dutyfree/dummy
COMMON="configs/deprecated/example/se.py --ruby --topology=Pt2Pt \
--chi-config=$HOME/DutyFree-Gem5/configs/ruby/CHI_config_8592.py \
--num-l3caches=1 --num-dirs=1 --cpu-type=O3CPU --num-cpus=2 --cpu-clock=1.9GHz \
--l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
--l2_size=2MiB --l2_assoc=16 --l3_size=5MiB --l3_assoc=20 \
--mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
--dram-latency=98ns --cxl-latency=203ns"

# arm : H3 : second program.  "stream" in argv[2] IS the H2 declaration on gem5
# 356e7b7d0e; its absence is the write-back arm.  The quiescent arm runs
# testcase/dutyfree/dummy on cpu1, NOT nothing -- verified from
# /tmp/sf_qui_inf_s1/config.ini, whose second cmd= line is the dummy. That is
# why cpu1.numCycles reads 0 in the qui arm. Dropping the second program
# instead would change the SE setup and is not the same experiment.
ARMS=(
  "sf_qui_fin:0:$D"
  "sf_wb_fin:0:$A 16.0"
  "sf_h2_fin:0:$A 16.0 stream"
  "sf_h3_fin:1:$A 16.0 stream"
)

git -C ~/DutyFree-Gem5 rev-parse HEAD > /tmp/sf_fin_gem5_head.txt 2>/dev/null || true
echo "SF_FIN_CAMPAIGN_START $(date +%s) head=$(cat /tmp/sf_fin_gem5_head.txt 2>/dev/null)" \
  > /tmp/sf_fin_cells.launch

for s in 1 2 3; do
  for cell in "${ARMS[@]}"; do
    NAME=${cell%%:*}; rest=${cell#*:}; H3=${rest%%:*}; SECOND=${rest#*:}
    N=${NAME}_s$s
    # SECOND is "<binary> [args...]": split the binary from its options so the
    # se.py -c/--options pairing stays aligned.
    SBIN=${SECOND%% *}
    if [ "$SBIN" = "$SECOND" ]; then SOPT=""; else SOPT=${SECOND#* }; fi
    rm -rf /tmp/$N
    env RUBY_RANDOMIZATION=1 SEED=$s \
        HNF_SF_FINITE=1 HNF_SF_SETS=4096 HNF_SF_WAYS=16 HNF_H3=$H3 HNF_DMT=0 \
      $G --outdir=/tmp/$N $COMMON -c "$V;$SBIN" --options "2650 3000000;$SOPT" \
      > /tmp/$N.log 2>&1
    echo "DONE_$? NAME=$N H3=$H3 SF_FINITE=1 SEED=$s $(date +%s)" >> /tmp/$N.log
  done &
done
wait
echo "SF_FIN_SWEEP_DONE $(date +%s)" > /tmp/sf_fin_cells.done
