#!/usr/bin/env bash
# DuckDB mmap-probe SE H2 kill-gate. Pre-registration:
# DUCKDB_MMAP_SE_H2_PREREG_2026-09-02.md
#
# THIS SCRIPT IS COMMITTED BEFORE IT IS RUN (F10).
set -uo pipefail
G=${DUTYFREE_GEM5:-/home/domin/DutyFree/gem5}
ROOT=${DUTYFREE_ROOT:-/home/domin/DutyFree}
cd "$G" || { echo "FAIL no $G" >&2; exit 2; }
BIN=build_Intel_8592/gem5.opt
T=$G/testcase/dutyfree
V=$T/victim
D=$T/dummy
J=$ROOT/benchmarks/e2e/duckdb_mmap_probe/build/mmap_probe.gem5
MODE=${MODE:-dry}
OUT=${DUCKDB_SE_OUT:-$G/logs/se_duckdb_mmap_h2}
DRY=0
JOBS=${JOBS:-3}
PRESET=gem5
ARMS=${DUCKDB_SE_ARMS:-"qui wb h2"}
SEEDS=${DUCKDB_SE_SEEDS:-"1 2 3"}

r6b_running() {
  pgrep -f 'atomic_2cpu_w8_fs_e2e_r6b_16g_join' >/dev/null 2>&1
}

case "$MODE" in
  dry) DRY=1 ;;
  smoke)
    OUT=${DUCKDB_SE_OUT:-$G/logs/se_duckdb_mmap_h2_smoke}
    ARMS=${DUCKDB_SE_ARMS:-h2}
    SEEDS=${DUCKDB_SE_SEEDS:-1}
    PRESET=gem5-smoke
    ;;
  full)
    ARMS=${DUCKDB_SE_ARMS:-"qui wb h2"}
    SEEDS=${DUCKDB_SE_SEEDS:-"1 2 3"}
    PRESET=gem5
    ;;
  *) echo "FAIL MODE=dry|smoke|full" >&2; exit 2 ;;
esac

if [ "$MODE" != "dry" ] && r6b_running; then
  echo "FAIL r6b owns mos181 (atomic_2cpu_w8_fs_e2e_r6b_16g_join); refuse $MODE" >&2
  exit 2
fi

if [ "$MODE" != "dry" ]; then
  for f in "$BIN" "$V" "$D" "$J"; do
    [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }
  done
fi

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

TENANT_WB="--preset $PRESET --policy wb --outdir /tmp/duckdb_mmap_se_unused"
TENANT_H2="--preset $PRESET --policy stream --outdir /tmp/duckdb_mmap_se_unused"

one() {
  local arm=$1 s=$2 N c o
  N=${OUT}/${arm}_s${s}
  case $arm in
    qui)
      c="$V;$D"
      o="2650 12000000;"
      ;;
    wb)
      c="$V;$J"
      o="2650 12000000;$TENANT_WB"
      ;;
    h2)
      c="$V;$J"
      o="2650 12000000;$TENANT_H2"
      ;;
    *) echo "bad arm $arm" >&2; return 3 ;;
  esac
  if [ "$DRY" = 1 ]; then
    echo "DRY $N ARM=$arm SEED=$s PRESET=${PRESET:-gem5}"
    echo "    $BIN --outdir=$N ... -c $c"
    return 0
  fi
  mkdir -p "$OUT"
  rm -rf "$N"
  {
    echo "DUCKDB_SE_LAUNCH arm=$arm seed=$s preset=$PRESET out=$N $(date -Is)"
    echo "DUCKDB_SE_GEM5 $(sha256sum "$BIN")"
    echo "DUCKDB_SE_TENANT $(sha256sum "$J")"
    echo "DUCKDB_SE_VICTIM $(sha256sum "$V")"
  } > "$N.log"
  env RUBY_RANDOMIZATION=1 SEED="$s" \
      HNF_RP=lru HNF_REQ_MASKS="" \
      HNF_SF_FINITE=0 HNF_SF_SETS=4096 HNF_SF_WAYS=16 HNF_H3=0 HNF_DMT=0 \
      HNF_FWD_UNIQUE=0 SEQ_OUT=1024 \
    "$BIN" --outdir="$N" $COMMON -c "$c" --options "$o" >> "$N.log" 2>&1
  echo "DONE_$? NAME=$(basename $N) ARM=$arm SEED=$s $(date +%s)" >> "$N.log"
}
export -f one
export BIN COMMON V D J OUT DRY TENANT_WB TENANT_H2 PRESET

if [ "$MODE" = "dry" ]; then
  echo "== duckdb mmap SE dry: $(echo $ARMS | wc -w) arms x $(echo $SEEDS | wc -w) seeds preset=$PRESET"
  for arm in $ARMS; do for s in $SEEDS; do one "$arm" "$s"; done; done
  exit 0
fi

echo "== duckdb mmap SE $MODE: $(echo $ARMS | wc -w) arms x $(echo $SEEDS | wc -w) seeds, ${JOBS} concurrent, out=$OUT preset=$PRESET"
mkdir -p "$OUT"
{ for arm in $ARMS; do for s in $SEEDS; do echo "$arm $s"; done; done; } \
  | xargs -P "$JOBS" -n 2 bash -c 'one "$0" "$1"'
echo "== all launched runs returned"
echo "DUCKDB_SE_SWEEP_DONE $(date +%s)" > "$OUT/sweep.done"
