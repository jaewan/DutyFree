#!/usr/bin/env bash
# Knee sweep: WHERE does H2 protection collapse, and which model explains it?
# Pre-registration: FUSED_KNEE_PREREG_2026-08-29.md
# Requires the multiply-shift index (fused.c, no power-of-two rounding), so the
# 2 MB and 4 MB anchors are RE-RUN here rather than reused: the index changed.
#
# The 3 MB point is already measured at n=3 (H2H_FUSED_OUTCOME_2026-08-29.md)
# and is NOT re-run; nor is `qui`, which does not involve the tenant and has been
# bit-identical (33.8814) in every batch today. Sizes here are the four new ones.
#
# Apparatus identical to the fused head-to-head: HNF_FWD_UNIQUE=0, SEQ_OUT=1024,
# infinite SF, DMT off, LRU at the HNF, masks confine only the stream's requestor
# (NodeID 5 = cpu1.l2).
set -uo pipefail
G=/home/domin/DutyFree/gem5
cd "$G" || { echo "FAIL no $G" >&2; exit 2; }
BIN=build_Intel_8592/gem5.opt
T=$G/testcase/dutyfree
V=$T/victim; A=$T/fused
for f in "$BIN" "$V" "$A"; do [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }; done

COMMON="configs/deprecated/example/se.py --ruby --topology=Pt2Pt \
--chi-config=$G/configs/ruby/CHI_config_8592.py \
--num-l3caches=1 --num-dirs=1 --cpu-type=O3CPU --num-cpus=2 --cpu-clock=1.9GHz \
--l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
--l2_size=2MiB --l2_assoc=16 --l3_size=5MiB --l3_assoc=20 \
--mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
--dram-latency=98ns --cxl-latency=203ns"

one() {   # $1=arm $2=table_mb $3=seed
  local arm=$1 tb=$2 s=$3 N o masks
  N=/tmp/kn_${arm}_t${tb}_s${s}
  masks=""
  case $arm in
    wb)   o="2650 3000000;16.0 ${tb}" ;;
    h2)   o="2650 3000000;16.0 ${tb} stream" ;;
    cat4) o="2650 3000000;16.0 ${tb}"; masks="5:0xf" ;;
    *) echo "bad arm $arm" >&2; return 3 ;;
  esac
  rm -rf "$N"
  env RUBY_RANDOMIZATION=1 SEED="$s" HNF_RP=lru HNF_REQ_MASKS="$masks" \
      HNF_SF_FINITE=0 HNF_SF_SETS=4096 HNF_SF_WAYS=16 HNF_H3=0 HNF_DMT=0 \
      HNF_FWD_UNIQUE=0 SEQ_OUT=1024 \
    "$BIN" --outdir="$N" $COMMON -c "$V;$A" --options "$o" > "$N.log" 2>&1
  echo "DONE_$? NAME=$(basename $N) ARM=$arm TABLE_MB=$tb MASKS=${masks:-none} SEED=$s $(date +%s)" >> "$N.log"
}
export -f one; export BIN COMMON V A G

JOBS=${JOBS:-45}
echo "== fused KNEE sweep: 5 sizes x 3 arms x 3 seeds = 45 runs, ${JOBS} concurrent"
{ for tb in 2.0 2.5 3.0 3.5 4.0; do for arm in wb h2 cat4; do for s in 1 2 3; do
    echo "$arm $tb $s"
  done; done; done; } | xargs -P "$JOBS" -n 3 bash -c 'one "$0" "$1" "$2"'
echo "== all launched runs returned"
echo "KNEE_DONE $(date +%s)" > /tmp/kn_sweep.done
