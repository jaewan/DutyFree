#!/usr/bin/env bash
# Multi-core H1 bandwidth survival, 4c and 8c.
# Pre-registered in H1BW_MULTICORE_PREREG_2026-09-03.md -- read it first; this
# is a new measurement with a new harness, not a reproduction of the archived
# gem5_streaming REPORT (whose runner no longer exists).
#
#   run_h1bw_multicore.sh [ncores ...]      default: 4 8
#
# Two brackets are parameterised on top of the frozen baseline.  Both default
# to the baseline, so an unset environment reproduces the completed campaign's
# gem5 invocation exactly (see PROOF below):
#
#   L3_SLICES=k     --num-l3caches=k instead of =ncores.  Default: ncores.
#                   Registered in H1BW_SLICE_BRACKET_PREREG_2026-09-03.md.
#   CXL_MEM_BW=s    SimpleMemory.bandwidth for the CXL range (mem_ctrls1)
#                   only; the local DRAM range is left alone.  Consumed by
#                   configs/ruby/Ruby.py.  Default: unset -> untouched.
#                   Registered in H1BW_CXLBW_PREREG_2026-09-03.md.
#
# CXL_MEM_BW MUST be a bare "<integer>B/s".  Prefixed forms are a trap:
# m5.util.convert.toMemoryBandwidth uses BINARY prefixes, so "32GB/s" means
# 32 GiB/s and additionally emits a base-10-to-base-2 cast warning.
#
# gem5 stores bandwidth as an INTEGER number of ticks per byte
# (MemoryBandwidth.getValue -> m5.ticks.fromSeconds, ROUND_HALF_UP), so only
# simFreq/k B/s for integer k is exactly realizable.  The runner records the
# expected integer here; the analyzer reads the realized one back out of
# config.ini and voids the run on a mismatch.
#
# PROOF OF NO-CHANGE DEFAULT: with L3_SLICES and CXL_MEM_BW unset, the
# generated config.ini is byte-identical to gem5/logs/se_chi/h1bw_mc_wb_4c_
# 20260904/config.ini.  Regenerate with experiments/asplos/prove_default_
# unchanged.sh.
#
# Launches 3 arms per core count concurrently and waits.
set -u

ROOT=/home/domin/DutyFree
GEM5=$ROOT/gem5/build_Intel_8592/gem5.opt
SE=$ROOT/gem5/configs/deprecated/example/se.py
CHI=$ROOT/gem5/configs/ruby/CHI_config_8592.py
BIN=$ROOT/benchmarks/e2e/hash_join/build/cxl_join_bench.gem5
OUTROOT=${OUTROOT:-$ROOT/gem5/logs/se_chi}   # overridden only by the proof script
STAMP=${STAMP:-$(date +%Y%m%d)}

PER_CORE_BYTES=8m          # frozen: 8 MiB per instance
L3_PER_SLICE=5MiB          # frozen: 5 MiB / 20-way per HNF slice
MSHR=48                    # frozen: L1_MSHR=48 (L1_REPL left at default 16)
WARMUPS=1
REPS=1
SIM_FREQ=1000000000000     # stats.txt simFreq; ticks per simulated second

CXL_MEM_BW=${CXL_MEM_BW:-}

for f in "$GEM5" "$SE" "$CHI" "$BIN"; do
  [ -x "$f" ] || [ -f "$f" ] || { echo "FATAL: missing $f"; exit 1; }
done

# CXL bandwidth request -> (bytes/s, expected realized ticks/byte, tag).
# Empty request means "leave the SimObject default alone", whose realized
# value is 2 ticks/byte = 500 GB/s (the 512GiB/s class default rounds up).
BW_BYTES=""; BW_TICKS=2; BW_TAG=def
if [ -n "$CXL_MEM_BW" ]; then
  case $CXL_MEM_BW in
    *[0-9]B/s) BW_BYTES=${CXL_MEM_BW%B/s} ;;
    *) echo "FATAL: CXL_MEM_BW must be a bare '<integer>B/s', got '$CXL_MEM_BW'"
       exit 1 ;;
  esac
  case $BW_BYTES in
    ''|*[!0-9]*) echo "FATAL: CXL_MEM_BW mantissa not an integer: '$BW_BYTES'"
                 exit 1 ;;
  esac
  # ROUND_HALF_UP, matching m5.ticks.fromSeconds.
  BW_TICKS=$(( (2 * SIM_FREQ + BW_BYTES) / (2 * BW_BYTES) ))
  BW_TAG=t$BW_TICKS
  echo "CXL_MEM_BW=$CXL_MEM_BW -> expect bandwidth=$BW_TICKS ticks/byte" \
       "= $(awk -v f=$SIM_FREQ -v t=$BW_TICKS 'BEGIN{printf "%.3f", f/t/1e9}') GB/s"
fi

# arm -> policy, and whether prefetchers are disabled on all cores
arm_policy() { case $1 in wb) echo wb ;; h2|pfoff) echo stream ;; esac; }

run_arm() {
  local arm=$1 n=$2
  local pol; pol=$(arm_policy "$arm")
  local slices=${L3_SLICES:-$n}
  # The bracket variables are always in the directory name, so no bracket can
  # collide with another or with the six completed h1bw_mc_*_20260904 runs.
  local out=$OUTROOT/h1bw_mc_${arm}_${n}c_l3x${slices}_bw${BW_TAG}_$STAMP
  rm -rf "$out"; mkdir -p "$out"

  # N independent single-threaded instances, one per simulated CPU.
  local cmd="" opts="" i
  for ((i = 0; i < n; i++)); do
    [ -n "$cmd" ] && { cmd="$cmd;"; opts="$opts;"; }
    cmd="$cmd$BIN"
    opts="$opts--mode stream-smoke --policy $pol --fact-bytes $PER_CORE_BYTES"
    opts="$opts --fact-node 1 --hot-node 0 --threads 1 --cpu-list $i"
    opts="$opts --warmups $WARMUPS --reps $REPS"
  done

  # pfoff disables the L1D/L2 prefetchers on every core, matching run_se.sh's
  # w1 "WC" arm (which is policy=stream with prefetch off, not the WC type).
  local pfoff=""
  if [ "$arm" = pfoff ]; then
    for ((i = 0; i < n; i++)); do
      [ -n "$pfoff" ] && pfoff="$pfoff,"
      pfoff="$pfoff$i"
    done
  fi

  # Provenance first, so a killed run is still attributable.  Every value here
  # is REQUESTED; the analyzer gates on what config.ini says was realized.
  cat > "$out/MANIFEST.json" <<EOF
{
  "campaign": "h1bw_multicore",
  "prereg": "experiments/asplos/H1BW_MULTICORE_PREREG_2026-09-03.md",
  "arm": "$arm",
  "ncores": $n,
  "policy": "$pol",
  "prefetch_off_cores": "$pfoff",
  "per_core_bytes": "$PER_CORE_BYTES",
  "total_bytes": $((n * 8 * 1024 * 1024)),
  "l3_per_slice": "$L3_PER_SLICE",
  "num_l3caches": $slices,
  "cxl_mem_bw_requested": $([ -n "$CXL_MEM_BW" ] && echo "\"$CXL_MEM_BW\"" || echo null),
  "cxl_mem_bw_bytes_per_s": $([ -n "$BW_BYTES" ] && echo "$BW_BYTES" || echo null),
  "cxl_bw_ticks_per_byte_expected": $BW_TICKS,
  "cxl_bw_note": "config.ini 'bandwidth' is ticks/byte, quantised to an integer by m5.ticks.fromSeconds; expected value is what the analyzer gates on",
  "l1_mshr": $MSHR,
  "l1_repl": 16,
  "l1_repl_note": "default, left unset; CHI_config_8592.py:315 flags this as a confound at high L1_MSHR",
  "warmups": $WARMUPS,
  "reps": $REPS,
  "bench_sha256": "$(sha256sum "$BIN" | cut -d' ' -f1)",
  "gem5_sha256": "$(sha256sum "$GEM5" | cut -d' ' -f1)",
  "host": "$(hostname)",
  "started": "$(date -Is)"
}
EOF

  env ALL_CXL=1 L1_MSHR=$MSHR ${pfoff:+PF_OFF_CORES=$pfoff} \
    ${CXL_MEM_BW:+CXL_MEM_BW=$CXL_MEM_BW} \
    "$GEM5" --outdir="$out" "$SE" \
      --cmd="$cmd" --options="$opts" \
      --ruby --topology=Pt2Pt --chi-config="$CHI" \
      --num-l3caches=$slices --num-dirs=1 --cpu-type=O3CPU --num-cpus=$n \
      --cpu-clock=1.9GHz \
      --l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
      --l2_size=2MiB --l2_assoc=16 --l3_size=$L3_PER_SLICE --l3_assoc=20 \
      --mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
      --dram-latency=98ns --cxl-latency=203ns \
    > "$out/console.log" 2>&1

  echo "{\"exit\":$?,\"ended\":\"$(date -Is)\"}" > "$out/DONE.json"
}

for N in "${@:-4 8}"; do
  for ARM in wb h2 pfoff; do
    run_arm "$ARM" "$N" &
    echo "launched h1bw_mc_${ARM}_${N}c_l3x${L3_SLICES:-$N}_bw${BW_TAG} (pid $!)"
    sleep 2
  done
done
wait
echo "all arms complete"
