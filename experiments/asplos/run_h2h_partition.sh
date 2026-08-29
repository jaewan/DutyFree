#!/usr/bin/env bash
# Head-to-head: way partitioning vs H2, one model, both sides measured.
# Pre-registration: H2H_PARTITION_VS_H2_PREREG_2026-08-29.md (7b69cc7)
#
# Runs in DutyFree/gem5 (the way-partitioning tip), NOT ~/DutyFree-Gem5, because
# only this tree has the partitioning implementation. The two defaults that
# changed since the W1 apparatus (356e7b7d0e) are pinned back explicitly:
# HNF_FWD_UNIQUE=0 and SEQ_OUT=1024. Everything else in that delta is the
# way-partitioning work, which check 1 proved bit-identical when unmasked.
#
# cat arms confine ONLY the stream's requestor. NodeID 5 = cpu1.l2, read from
# config.ini, not inferred: the version assignment is not creation-order-per-CPU
# (l1i/l1d for both CPUs come first, then the L2s), so a guess gives NodeID 2.
set -uo pipefail
G=${DUTYFREE_GEM5:-/home/domin/DutyFree/gem5}
cd "$G" || { echo "FAIL no $G" >&2; exit 2; }
BIN=build_Intel_8592/gem5.opt
T=$G/testcase/dutyfree
V=$T/victim; A=$T/aggressor; D=$T/dummy
for f in "$BIN" "$V" "$A" "$D"; do [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }; done

COMMON="configs/deprecated/example/se.py --ruby --topology=Pt2Pt \
--chi-config=$G/configs/ruby/CHI_config_8592.py \
--num-l3caches=1 --num-dirs=1 --cpu-type=O3CPU --num-cpus=2 --cpu-clock=1.9GHz \
--l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
--l2_size=2MiB --l2_assoc=16 --l3_size=5MiB --l3_assoc=20 \
--mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
--dram-latency=98ns --cxl-latency=203ns"

one() {   # $1=arm  $2=seed
  local arm=$1 s=$2 N c o masks
  N=/tmp/hh_${arm}_s${s}
  masks=""
  case $arm in
    qui)   c="$V;$D"; o="2650 3000000;" ;;
    wb)    c="$V;$A"; o="2650 3000000;16.0" ;;
    h2)    c="$V;$A"; o="2650 3000000;16.0 stream" ;;
    cat4)  c="$V;$A"; o="2650 3000000;16.0";  masks="5:0xf" ;;
    cat10) c="$V;$A"; o="2650 3000000;16.0";  masks="5:0x3ff" ;;
    *) echo "bad arm $arm" >&2; return 3 ;;
  esac
  rm -rf "$N"
  env RUBY_RANDOMIZATION=1 SEED="$s" \
      HNF_RP=lru HNF_REQ_MASKS="$masks" \
      HNF_SF_FINITE=0 HNF_SF_SETS=4096 HNF_SF_WAYS=16 HNF_H3=0 HNF_DMT=0 \
      HNF_FWD_UNIQUE=0 SEQ_OUT=1024 \
    "$BIN" --outdir="$N" $COMMON -c "$c" --options "$o" > "$N.log" 2>&1
  echo "DONE_$? NAME=$(basename $N) ARM=$arm MASKS=${masks:-none} SEED=$s $(date +%s)" >> "$N.log"
}
export -f one; export BIN COMMON V A D G

JOBS=${JOBS:-15}
echo "== head-to-head: 15 runs (5 arms x 3 seeds), ${JOBS} concurrent"
{ for arm in wb cat4 cat10 h2 qui; do for s in 1 2 3; do echo "$arm $s"; done; done; } \
  | xargs -P "$JOBS" -n 2 bash -c 'one "$0" "$1"'
echo "== all launched runs returned"
echo "H2H_SWEEP_DONE $(date +%s)" > /tmp/hh_sweep.done
