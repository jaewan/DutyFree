#!/usr/bin/env bash
# run_localdram_column.sh -- tab:gem5 local-DRAM column re-run (Gate 1).
#
# Pre-registration: GATE1_LOCALDRAM_COLUMN_PREREGISTRATION.md (commit it
# BEFORE the first measurement arm; that is the point of pre-registering).
#
# 12 arms: {1280,2650,5120 KiB} x {default,ALL_LOCAL} x {alone,wb}.
# Every loaded arm gets its own quiescent baseline from the SAME config --
# omitting that is what made the fused hash-join null misread once already.
#
# Runs the manifest generator inside each arm's own environment, because
# gate1_manifest.py reads the MANIFESTING shell's env, not the run's. The
# mem_pool_observed field it emits is env-independent and is the field to
# trust if the two ever disagree.
set -u

ITERS=${ITERS:-3000000}
SFF=0          # tab:gem5 is the capacity table; finite SF is tab:h3sf's subject
H3=0
G=$HOME/DutyFree-Gem5/build_Intel_8592/gem5.opt
HERE=$(cd "$(dirname "$0")" && pwd)

launch() {
  local wss=$1 place=$2 tag=$3
  local name="ld_${wss}_${place}_${tag}"
  local env_prefix=""
  [ "$place" = "loc" ] && env_prefix="ALL_LOCAL=1"

  tmux kill-session -t "$name" 2>/dev/null
  tmux new-session -d -s "$name" \
    "env $env_prefix WSS=$wss ITERS=$ITERS $HERE/b4run2.sh $name $tag $SFF $H3; \
     env $env_prefix HNF_SF_FINITE=$SFF RUBY_RANDOMIZATION=1 \
       ~/gem5-venv/bin/python $HERE/gate1_manifest.py /tmp/$name \
       --gem5-repo \$HOME/DutyFree-Gem5 --cmdline '$G' \
       >> /tmp/$name.log 2>&1; \
     echo MANIFEST_\$? >> /tmp/$name.log"
  echo "launched $name  (WSS=$wss place=$place tag=$tag)"
}

for wss in 1280 2650 5120; do
  for place in def loc; do
    for tag in alone wb; do
      launch "$wss" "$place" "$tag"
    done
  done
done

echo
echo "12 arms launched at ITERS=$ITERS. Watch: tmux ls | grep ld_"
