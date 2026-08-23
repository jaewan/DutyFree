#!/usr/bin/env bash
# W7 -- necessity and benefit at the same operating point.
# Pre-registration: W7_PREREGISTRATION_2026-08-23.md (+ amendments 1 and 2, dated
# 2026-08-24, at the top of that file). Knob B: W7.1_KNOB_B_2026-08-24.md.
#
# THIS SCRIPT IS COMMITTED BEFORE IT IS RUN. W1's launcher was typed at the shell
# and never committed, and reconstructing it cost a session (see sf_inf_cells.sh's
# header, and F10 in W4.3_PROVENANCE_LEDGER_2026-08-23.md).
#
# ---------------------------------------------------------------- apparatus ---
# A0 is reproduced EXACTLY from the completed 4 MiB arm of
# GATE1_FUSED_NULL_CORRECTION_2026-08-15.md section 3, recovered from
# /tmp/m22_mid_wb/{stats,config}.ini and its logged command line:
#   L1D 48KiB/12  L1I 32KiB/8  L2 2MiB/16  L3(HNF) 5MiB/20  2 CPUs  1.9 GHz
#   SimpleMemory, mem 256GiB / cxl 128GiB, 98 ns local / 203 ns CXL
#   --mode morsel --fact-bytes 16777216 --hot-bytes 4194304 --reps 3 --warmups 1
#   HNF: alloc_on_readshared=false, alloc_on_writeback=true, enable_DMT=TRUE
# Note enable_DMT is TRUE here. The W1 / tab:h3sf arms force HNF_DMT=0; this
# apparatus does not, and it is left as it is. Changing it would make W7's A0/B0
# cell something other than the baseline it exists to reproduce.
#
# THREE KNOWN DIFFERENCES from that 2026-08-15 run, all deliberate, all recorded:
#   1. gem5 is 356e7b7d0e; that run was 3d0d1ca2. All four W7 cells share one
#      build, so the 2x2 is internally consistent; cross-campaign comparison to
#      the 2026-08-15 table is NOT sound and W7 does not make one -- A0/B0 is
#      re-measured here for exactly that reason.
#   2. Binary is cxl_join_bench_w7.gem5, not cxl_join_bench.gem5. At
#      --probe-batch 0 it takes the identical join_range path; it is still a
#      different binary and is named differently. Pre-W7 binary sha256
#      917413d5fab4e61404b89e905e3d09af91fed37afbe357483f297fc07194a069,
#      verified unchanged.
#   3. RUBY_RANDOMIZATION=1 with SEED in 1..3, which is W1.3's variance method
#      (repeated runs, NOT a --seed sweep -- section 6.1 of the correction memo).
#      The bench --seed stays at its default so `matches` is invariant across
#      every run in the campaign and the cross-arm equality gate (F12: --check
#      is inert in morsel mode) has something to compare.
#
# A1 is the pre-registered realistic hierarchy: L2 512KiB, LLC 32MiB, hot 8MiB.
# Associativities are NOT changed (L2 16-way, LLC 20-way) -- the pre-registration
# specifies sizes only, and holding assoc keeps Knob A one-dimensional.
#
# Runtime, from the completed A0 arm: hostSeconds 9116.7 (2h32m), simInsts
# 178.6M, hostInstRate 19,590/s. A1 is larger and will be slower. 28 runs, all
# independent, on a 256-core host. No calibration run is needed -- the number
# already exists.
#
# NOT INCLUDED: the pre-registration's second A1 point at 8 cores. With
# --threads 1 the seven extra cores never fill their L2s, so 8 idle cores are
# indistinguishable from 1 for the aggregate-L2 : LLC ratio the point exists to
# vary. Making it meaningful requires --threads 8, which changes the workload
# and not only the hierarchy. Deferred with that reason stated; see the memo.
set -u
cd "$HOME/DutyFree-Gem5"

G=build_Intel_8592/gem5.opt
BIN=$HOME/DutyFree/benchmarks/e2e/hash_join/build/cxl_join_bench_w7.gem5
CHI=$HOME/DutyFree-Gem5/configs/ruby/CHI_config_8592.py
OUT=${W7_OUT:-/tmp/w7}
K=${W7_K:-16}          # Knob B batch depth; amendment 1 sets 16
REPS=${W7_REPS:-3}
SEEDS=${W7_SEEDS:-"1 2 3"}
DRY=${W7_DRY:-0}

mkdir -p "$OUT"

base_args() {   # $1 = l2_size  $2 = l3_size
  echo "configs/deprecated/example/se.py --ruby --topology=Pt2Pt \
--chi-config=$CHI --num-l3caches=1 --num-dirs=1 --cpu-type=O3CPU --num-cpus=2 \
--cpu-clock=1.9GHz --l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
--l2_size=$1 --l2_assoc=16 --l3_size=$2 --l3_assoc=20 \
--mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
--dram-latency=98ns --cxl-latency=203ns"
}

# hierarchy: name  l2      l3      hot_bytes
HIER="A0 2MiB 5MiB 4194304
A1 512KiB 32MiB 8388608"

launch() {  # $1 name  $2 l2  $3 l3  $4 opts
  local n=$1 l2=$2 l3=$3 opts=$4
  local cmd="$G --outdir=$OUT/$n $(base_args "$l2" "$l3") -c $BIN --options '$opts'"
  # DRY must be checked BEFORE the first side effect, and it was not.
  # Fixed 2026-08-24, after the campaign completed. As written, the `rm -rf
  # "$OUT/$n"` below and the `.cmd` write sat ABOVE this branch, so
  # `W7_DRY=1 ./w7_campaign.sh` -- the one invocation whose entire purpose is to
  # change nothing -- would have deleted all 28 completed cells in $OUT before
  # printing a single DRY line. That is the same shape as A6.19's
  # `run_join_campaign.py --help`: an inspection command with a destructive
  # body. The dry path now prints the command instead of writing it, so it has
  # no side effect at all and can be run against a live $OUT.
  if [ "$DRY" = 1 ]; then echo "DRY $n :: $opts"; echo "    $cmd"; return; fi
  rm -rf "$OUT/$n"
  echo "$cmd" > "$OUT/$n.cmd"
  ( eval "$cmd" > "$OUT/$n.log" 2>&1
    echo "DONE_$? NAME=$n $(date +%s)" >> "$OUT/$n.log" ) &
}

# ------------------------------------------------------------- the 2x2 x 3 ---
while read -r hname l2 l3 hot; do
  [ -z "$hname" ] && continue
  for b in 0 $K; do                          # B0 = serial, B1 = batched
    bname=$([ "$b" = 0 ] && echo B0 || echo B1)
    for pol in wb stream; do                 # WB vs H2
      for s in $SEEDS; do
        n="${hname}_${bname}_${pol}_s${s}"
        opts="--mode morsel --policy $pol --fact-bytes 16777216 --hot-bytes $hot \
--reps $REPS --warmups 1 --probe-batch $b --json"
        RUBY_RANDOMIZATION=1 SEED=$s launch "$n" "$l2" "$l3" "$opts"
      done
    done
  done
done <<< "$HIER"

# ------------------------------------------- stream-smoke bandwidth reference --
# One per hierarchy point per policy: the achievable-bandwidth denominator that
# P2 ("fused bandwidth >= 2.0 GB/s") is measured against. Single seed -- it is a
# reference, not a cell.
while read -r hname l2 l3 hot; do
  [ -z "$hname" ] && continue
  for pol in wb stream; do
    n="${hname}_SMOKE_${pol}"
    opts="--mode stream-smoke --policy $pol --fact-bytes 16777216 --reps $REPS --warmups 1 --json"
    RUBY_RANDOMIZATION=1 SEED=1 launch "$n" "$l2" "$l3" "$opts"
  done
done <<< "$HIER"

wait
# Guarded for the same reason as launch(): in DRY mode `wait` returns at once
# and this line would stamp a fresh completion marker over a real campaign's.
[ "$DRY" = 1 ] && { echo "DRY: no cells launched, w7.done not written"; exit 0; }
echo "W7_CAMPAIGN_DONE $(date +%s)" > "$OUT/w7.done"
