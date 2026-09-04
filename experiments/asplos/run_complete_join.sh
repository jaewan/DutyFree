#!/usr/bin/env bash
# Complete 8 MiB join at table/LLC ≈ 0.53, tuples/s + victim latency.
# Pre-registration: COMPLETE_JOIN_PREREG_2026-09-01.md
#
# THIS SCRIPT IS COMMITTED BEFORE IT IS RUN (F10).
#
# --l3_size is 7680KiB, not 7.5MiB: gem5 toMemorySize rejects the latter.
set -uo pipefail
G=${DUTYFREE_GEM5:-/home/domin/DutyFree/gem5}
cd "$G" || { echo "FAIL no $G" >&2; exit 2; }
BIN=build_Intel_8592/gem5.opt
T=$G/testcase/dutyfree
V=$T/victim
D=$T/dummy
J=/home/domin/DutyFree/benchmarks/e2e/hash_join/build/cxl_join_bench.gem5
OUT=${R5_OUT:-/tmp/r5}
DRY=${R5_DRY:-0}
JOBS=${JOBS:-15}

for f in "$BIN" "$V" "$D" "$J"; do
  [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }
done

if [ "$DRY" != 1 ] && [ -e "$OUT" ]; then
  echo "FAIL $OUT exists (A6.19); refuse to clobber" >&2
  exit 2
fi

COMMON="configs/deprecated/example/se.py --ruby --topology=Pt2Pt \
--chi-config=$G/configs/ruby/CHI_config_8592.py \
--num-l3caches=1 --num-dirs=1 --cpu-type=O3CPU --num-cpus=2 --cpu-clock=1.9GHz \
--l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
--l2_size=2MiB --l2_assoc=16 --l3_size=7680KiB --l3_assoc=20 \
--mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
--dram-latency=98ns --cxl-latency=203ns"

JOIN_OPTS_WB="--mode single --policy wb --fact-bytes 8388608 --hot-bytes 4194304 --reps 1 --warmups 0 --hit-rate 0.5"
JOIN_OPTS_H2="--mode single --policy stream --fact-bytes 8388608 --hot-bytes 4194304 --reps 1 --warmups 0 --hit-rate 0.5"

one() {
  local arm=$1 s=$2 N c o masks pol
  N=${OUT}/${arm}_s${s}
  masks=""
  pol=""
  case $arm in
    qui)
      c="$V;$D"
      o="2650 12000000;"
      ;;
    wb)
      c="$V;$J"
      o="2650 12000000;$JOIN_OPTS_WB"
      ;;
    h2)
      c="$V;$J"
      o="2650 12000000;$JOIN_OPTS_H2"
      ;;
    wm*)
      local w=${arm#wm}
      w=$((10#$w))
      c="$V;$J"
      o="2650 12000000;$JOIN_OPTS_WB"
      if [ "$w" -lt 20 ]; then
        masks="5:$(printf '0x%x' $(( (1 << w) - 1 )))"
      fi
      ;;
    *) echo "bad arm $arm" >&2; return 3 ;;
  esac
  if [ "$DRY" = 1 ]; then
    echo "DRY $N ARM=$arm MASKS=${masks:-none} SEED=$s"
    echo "    $BIN --outdir=$N ... -c $c"
    return 0
  fi
  mkdir -p "$OUT"
  rm -rf "$N"
  {
    echo "R5_LAUNCH arm=$arm seed=$s masks=${masks:-none} out=$N $(date -Is)"
    echo "R5_GEM5 $(sha256sum "$BIN")"
    echo "R5_JOIN $(sha256sum "$J")"
    echo "R5_VICTIM $(sha256sum "$V")"
  } > "$N.log"
  env RUBY_RANDOMIZATION=1 SEED="$s" \
      HNF_RP=lru HNF_REQ_MASKS="$masks" \
      HNF_SF_FINITE=0 HNF_SF_SETS=4096 HNF_SF_WAYS=16 HNF_H3=0 HNF_DMT=0 \
      HNF_FWD_UNIQUE=0 SEQ_OUT=1024 \
    "$BIN" --outdir="$N" $COMMON -c "$c" --options "$o" >> "$N.log" 2>&1
  echo "DONE_$? NAME=$(basename $N) ARM=$arm MASKS=${masks:-none} SEED=$s $(date +%s)" >> "$N.log"
}
export -f one
export BIN COMMON V D J G OUT DRY JOIN_OPTS_WB JOIN_OPTS_H2

ARMS=${R5_ARMS:-"qui wb h2 wm01 wm02 wm03 wm04 wm06 wm08 wm10 wm12 wm14 wm16 wm18 wm20"}
SEEDS=${R5_SEEDS:-"1 2 3"}

echo "== complete join r5: $(echo $ARMS | wc -w) arms x $(echo $SEEDS | wc -w) seeds, ${JOBS} concurrent, out=$OUT"
if [ "$DRY" = 1 ]; then
  for arm in $ARMS; do for s in $SEEDS; do one "$arm" "$s"; done; done
  exit 0
fi
mkdir -p "$OUT"
{ for arm in $ARMS; do for s in $SEEDS; do echo "$arm $s"; done; done; } \
  | xargs -P "$JOBS" -n 2 bash -c 'one "$0" "$1"'
echo "== all launched runs returned"
echo "R5_SWEEP_DONE $(date +%s)" > "$OUT/sweep.done"
