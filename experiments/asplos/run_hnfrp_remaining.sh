#!/usr/bin/env bash
# Remaining tab:h3sf cells under both LLC policies.
# Pre-registration: HNFRP_REMAINING_CELLS_PREREG_2026-08-28.md (5036cec)
#
# 30 runs: h3 at infinite SF, and the whole finite-SF row (qui/wb/h2/h3), each
# under HNF_RP=treeplru and HNF_RP=lru, seeds 1-3. qui_inf/wb_inf/h2_inf are NOT
# re-run -- they are reused from the previous batch (/tmp/rp_*), which is my own,
# one environment, absolute paths.
#
# All workload paths ABSOLUTE, matching the previous batch. The archive splits on
# this (F10): qui/wb inf+fin and h2/h3 fin used absolute; h2/h3 inf used
# relative. argv length shifts the simulated stack and moves cyc/access ~0.04%.
#
# Longest job first, so the tail is a short job rather than a 79-minute one.
set -uo pipefail
cd "$HOME/DutyFree-Gem5" || { echo "FAIL no ~/DutyFree-Gem5" >&2; exit 2; }
G=build_Intel_8592/gem5.opt
T=$HOME/DutyFree-Gem5/testcase/dutyfree
V=$T/victim; A=$T/aggressor; D=$T/dummy
for f in "$G" "$V" "$A" "$D"; do [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }; done
WANT=356e7b7d0e; HAVE=$(git rev-parse --short=10 HEAD)
[ "$HAVE" = "$WANT" ] || { echo "FAIL tree at $HAVE, prereg pins $WANT" >&2; exit 2; }

COMMON="configs/deprecated/example/se.py --ruby --topology=Pt2Pt \
--chi-config=$HOME/DutyFree-Gem5/configs/ruby/CHI_config_8592.py \
--num-l3caches=1 --num-dirs=1 --cpu-type=O3CPU --num-cpus=2 --cpu-clock=1.9GHz \
--l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
--l2_size=2MiB --l2_assoc=16 --l3_size=5MiB --l3_assoc=20 \
--mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
--dram-latency=98ns --cxl-latency=203ns"

one() {   # $1=arm  $2=sf(inf|fin)  $3=rp  $4=seed
  local arm=$1 sf=$2 rp=$3 s=$4 N c o h3 fin
  N=/tmp/rq_${arm}_${sf}_${rp}_s${s}
  case $arm in
    qui) c="$V;$D"; o="2650 3000000;";            h3=0 ;;
    wb)  c="$V;$A"; o="2650 3000000;16.0";        h3=0 ;;
    h2)  c="$V;$A"; o="2650 3000000;16.0 stream"; h3=0 ;;
    h3)  c="$V;$A"; o="2650 3000000;16.0 stream"; h3=1 ;;
    *) echo "bad arm $arm" >&2; return 3 ;;
  esac
  case $sf in inf) fin=0 ;; fin) fin=1 ;; *) echo "bad sf $sf" >&2; return 3 ;; esac
  rm -rf "$N"
  env RUBY_RANDOMIZATION=1 SEED="$s" HNF_RP="$rp" \
      HNF_SF_FINITE=$fin HNF_SF_SETS=4096 HNF_SF_WAYS=16 HNF_H3=$h3 HNF_DMT=0 \
    "$G" --outdir="$N" $COMMON -c "$c" --options "$o" > "$N.log" 2>&1
  echo "DONE_$? NAME=$(basename $N) ARM=$arm SF_FINITE=$fin H3=$h3 HNF_RP=$rp SEED=$s $(date +%s)" >> "$N.log"
}
export -f one; export G COMMON V A D

JOBS=${JOBS:-16}
echo "== remaining cells: 30 runs, ${JOBS} concurrent, longest job first"
# archived runtimes: h2_fin 4720s, wb_fin 4460s, h3_inf 2100s, h3_fin 2030s, qui_fin 740s
{ for rp in treeplru lru; do for s in 1 2 3; do echo "h2 fin $rp $s"; done; done
  for rp in treeplru lru; do for s in 1 2 3; do echo "wb fin $rp $s"; done; done
  for rp in treeplru lru; do for s in 1 2 3; do echo "h3 inf $rp $s"; done; done
  for rp in treeplru lru; do for s in 1 2 3; do echo "h3 fin $rp $s"; done; done
  for rp in treeplru lru; do for s in 1 2 3; do echo "qui fin $rp $s"; done; done
} | xargs -P "$JOBS" -n 4 bash -c 'one "$0" "$1" "$2" "$3"'
echo "== all launched runs returned"
echo "REMAINING_SWEEP_DONE $(date +%s)" > /tmp/rq_sweep.done
