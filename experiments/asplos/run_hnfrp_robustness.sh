#!/usr/bin/env bash
# HNF_RP robustness: does W1's H2 bound survive an unbiased LLC policy?
# Pre-registration: HNFRP_ROBUSTNESS_PREREG_2026-08-28.md (e626e15)
#
# Apparatus is W1's, not a new one: runs in ~/DutyFree-Gem5 against the
# 2026-08-09 binary. HNF_RP is read at run time from the Python config, so no
# rebuild is involved and the binary is bit-identical to W1's.
#
# The three invocations below were recovered from gem5's own "command line:"
# banner in the archived logs, NOT reconstructed from intent. This matters: the
# quiescent arm -- the denominator of every tax -- runs `dummy` on cpu1 to hold
# the CPU count constant, and a reconstruction that used `--num-cpus=1` or
# omitted cpu1 would have silently changed the denominator. sf_qui/sf_wb had no
# committed launcher (F10); this closes that gap for this experiment.
set -uo pipefail
cd "${DUTYFREE_W1_GEM5:-$HOME/DutyFree-Gem5}" || { echo "FAIL no ~/DutyFree-Gem5" >&2; exit 2; }
G=build_Intel_8592/gem5.opt
T=$HOME/DutyFree-Gem5/testcase/dutyfree
V=$T/victim; A=$T/aggressor; D=$T/dummy
for f in "$G" "$V" "$A" "$D"; do [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }; done

# Preflight: the tree must be the pinned one, or the run is measuring something else.
WANT=356e7b7d0e
HAVE=$(git rev-parse --short=10 HEAD)
[ "$HAVE" = "$WANT" ] || { echo "FAIL tree at $HAVE, prereg pins $WANT" >&2; exit 2; }

COMMON="configs/deprecated/example/se.py --ruby --topology=Pt2Pt \
--chi-config=$HOME/DutyFree-Gem5/configs/ruby/CHI_config_8592.py \
--num-l3caches=1 --num-dirs=1 --cpu-type=O3CPU --num-cpus=2 --cpu-clock=1.9GHz \
--l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
--l2_size=2MiB --l2_assoc=16 --l3_size=5MiB --l3_assoc=20 \
--mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
--dram-latency=98ns --cxl-latency=203ns"

one() {   # $1=arm  $2=rp  $3=seed
  local arm=$1 rp=$2 s=$3 N c o
  N=/tmp/rp_${arm}_${rp}_s${s}
  case $arm in
    qui) c="$V;$D";  o="2650 3000000;" ;;
    wb)  c="$V;$A";  o="2650 3000000;16.0" ;;
    h2)  c="$V;$A";  o="2650 3000000;16.0 stream" ;;
    *) echo "bad arm $arm" >&2; return 3 ;;
  esac
  rm -rf "$N"
  env RUBY_RANDOMIZATION=1 SEED="$s" HNF_RP="$rp" \
      HNF_SF_FINITE=0 HNF_SF_SETS=4096 HNF_SF_WAYS=16 HNF_H3=0 HNF_DMT=0 \
    "$G" --outdir="$N" $COMMON -c "$c" --options "$o" > "$N.log" 2>&1
  echo "DONE_$? NAME=$(basename $N) ARM=$arm HNF_RP=$rp SEED=$s SF_FINITE=0 H3=0 $(date +%s)" >> "$N.log"
}
export -f one; export G COMMON V A D

JOBS=${JOBS:-9}
echo "== HNF_RP robustness: 18 runs (3 arms x 2 policies x 3 seeds), ${JOBS} concurrent"
for rp in treeplru lru; do for arm in qui wb h2; do for s in 1 2 3; do
  echo "$arm $rp $s"
done; done; done | xargs -P "$JOBS" -n 3 bash -c 'one "$0" "$1" "$2"'
echo "== all launched runs returned"
echo "HNFRP_SWEEP_DONE" > /tmp/rp_sweep.done
