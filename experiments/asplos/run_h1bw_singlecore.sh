#!/usr/bin/env bash
# Single-core H1 bandwidth / LLC-footprint MSHR sweep -- the certified
# replacement for Appendix.tex tab:h1bw.
#
# Pre-registered in H1BW_SINGLECORE_PREREG_2026-09-04.md -- read it first.
# This is a NEW measurement with a NEW harness, not a reproduction of the
# archived gem5_streaming REPORT.md.  That report's runner (knee_sweep.sh,
# named at gem5/scripts/run_se.sh:16-17) does not exist on this host, its
# binary is gone, and it left no stats.txt, no config.ini and no per-run JSON.
#
#   run_h1bw_singlecore.sh [primary|diag|all]      default: all
#
# Sibling of experiments/asplos/run_h1bw_multicore.sh, which is deliberately
# NOT edited: another worker holds a pending patch to it (BUILD_PROVENANCE.md
# section 5b, and AGGBW_WINDOW_PREREG_2026-09-03.md section 2).  Everything
# below that is shared with that runner is copied, not refactored, so that
# runner keeps certifying its own completed campaign.
#
# THREE DELIBERATE DEPARTURES from run_h1bw_multicore.sh, all pre-registered:
#
#   1. OUTROOT is NOT gem5/logs/.  The brief for this campaign forbids
#      modifying anything under gem5/logs/, so cells land in logs/se_chi_h1bw_sc/
#      at the repository root.  Nothing under gem5/logs/ is read, written or
#      enumerated by this script.
#   2. L1_REPL is set EXPLICITLY to 48 at both MSHR points instead of being
#      left at its default 16.  CHI_config_8592.py:313-321 warns that sweeping
#      L1_MSHR alone starves the replacement path relative to the request path,
#      and the STREAMING attribute has to survive the eviction path
#      (cache_entry.isStreaming -> TBE -> WriteEvictFull) to be honoured at the
#      HNF.  This sweep moves L1_MSHR across a 3x range, which is exactly that
#      situation.  48 >= max(L1_MSHR), so the replacement path is never the
#      narrower of the two at either point and cannot be the binding constraint
#      in either cell.  See the pre-registration, section "L1_REPL".
#   3. The benchmark is build/cxl_join_bench.gem5wbrk, not
#      build/cxl_join_bench.gem5.  Same source, same flags, separate name so
#      that cac9e27a -- the provenance of all 24 h1bw_mc_* cells -- is not
#      overwritten (F13).  --window-brackets is what the new name buys.
#
# gem5 stores SimpleMemory.bandwidth as an INTEGER number of ticks per byte.
# This campaign requests no bandwidth cap at all, so the realized value is the
# SimObject default's 2 ticks/byte = 500 GB/s; the analyzer reads that back out
# of config.ini and voids the cell on a mismatch.
set -u

ROOT=/home/domin/DutyFree
GEM5=$ROOT/gem5/build_Intel_8592/gem5.opt
SE=$ROOT/gem5/configs/deprecated/example/se.py
CHI=$ROOT/gem5/configs/ruby/CHI_config_8592.py
BIN=$ROOT/benchmarks/e2e/hash_join/build/cxl_join_bench.gem5wbrk
OUTROOT=${OUTROOT:-$ROOT/logs/se_chi_h1bw_sc}
STAMP=${STAMP:-$(date +%Y%m%d)}
PREREG=${PREREG:-H1BW_SINGLECORE_PREREG_2026-09-04.md}

# ---- frozen configuration.  Every value here is REQUESTED; the analyzer gates
# ---- on what config.ini and stats.txt say was REALIZED.
FACT_BYTES=16m             # frozen: 16 MiB single-core stream, > the 5 MiB LLC
L3_PER_SLICE=5MiB          # frozen: 5 MiB / 20-way per HNF slice
L3_SLICES=1                # frozen: tab:gem5cfg "1 LLC slice, 1 directory"
NCORES=1                   # frozen: single core.  This is the whole point.
# warmups + reps must be EVEN: `checksum` is an XOR over that many passes across
# identical unmodified data, so an even count must yield exactly 0 and G11 can
# gate on it (AGGBW_VALIDITY_2026-09-03.md recommended this and recorded that no
# analyzer implements it).  8 reps also give a cov, so the +7% H2-over-WB margin
# tab:h1bw is cited for finally has an error bar.  Costs ~10% of simulated ticks:
# the measured pass is 1.11% of the program.
WARMUPS=2
REPS=8
L1_REPL_PRIMARY=48         # departure 2 above
L1_REPL_DIAG=16            # the archive's presumed (default) replacement path
MSHR_POINTS="16 48"        # frozen: the two points tab:h1bw tabulates
SIM_FREQ=1000000000000     # stats.txt simFreq; ticks per simulated second

# ---- provenance, fail-closed.  gem5_sha256 names a binary and a binary gets
# ---- replaced in place (BUILD_PROVENANCE.md section 1: cfd37207 was overwritten
# ---- while it was the provenance of 21 published cells).  The pre-registration
# ---- names the binary this campaign must run, so refuse to run any other.
GEM5_SHA_EXPECT=cb2904444d5c5c4d31d9d8f07295209283d29e294ef1d885d789442d98e7bbe0
BENCH_SHA_EXPECT=2b9d67320ff86999b5e8e3d2cb98479043c3da62bbaa6135304a53ff48d9efad

for f in "$GEM5" "$SE" "$CHI" "$BIN"; do
  [ -x "$f" ] || [ -f "$f" ] || { echo "FATAL: missing $f"; exit 1; }
done

GEM5_SHA=$(sha256sum "$GEM5" | cut -d' ' -f1)
BENCH_SHA=$(sha256sum "$BIN" | cut -d' ' -f1)
[ "$GEM5_SHA" = "$GEM5_SHA_EXPECT" ] || {
  echo "FATAL: $GEM5 is $GEM5_SHA, pre-registered $GEM5_SHA_EXPECT."
  echo "       The isStreaming retry-path fix (H2_BYPASS_COLLAPSE_2026-09-03.md)"
  echo "       is what makes the h2 arm engage.  Refusing to run."; exit 1; }
[ "$BENCH_SHA" = "$BENCH_SHA_EXPECT" ] || {
  echo "FATAL: $BIN is $BENCH_SHA, pre-registered $BENCH_SHA_EXPECT."
  echo "       Rebuild with 'make -C benchmarks/e2e/hash_join gem5-window'"
  echo "       and reconcile the hash in the pre-registration before running."
  exit 1; }

# BUILD_PROVENANCE.md section 5b's fail-closed check against
# <build-dir>/BUILD_PROVENANCE.json cannot be applied: the current gem5.opt was
# built by hand on 2026-09-04 12:47 and the build wrapper that writes that file
# (commit fa27f665db) landed after it, so no manifest exists.  The sha256
# equality above is the stronger substitute HERE, because the pre-registration
# names the hash; it is not a general substitute.  Recorded, not papered over.
GEM5_PROV=$(dirname "$GEM5")/BUILD_PROVENANCE.json
GEM5_PROV_PRESENT=$([ -s "$GEM5_PROV" ] && echo true || echo false)
GEM5_DESCRIBE=$(git -C "$ROOT/gem5" describe --tags --long --dirty --always 2>/dev/null || echo unknown)
GEM5_HEAD=$(git -C "$ROOT/gem5" rev-parse HEAD 2>/dev/null || echo unknown)

# arm -> policy.  pfoff differs from h2 ONLY in prefetcher instantiation; both
# are --policy stream.  There is no WC arm and none can be built: the model
# derives only `streaming` and `uncacheable` from the PAT bits
# (src/arch/x86/pagetable_walker.cc:359-390).
arm_policy() { case $1 in wb) echo wb ;; h2|pfoff) echo stream ;; esac; }

run_cell() {
  local arm=$1 mshr=$2 repl=$3 kind=$4
  local pol; pol=$(arm_policy "$arm")
  # Both swept variables are in the directory name, so no cell can collide with
  # another or with any h1bw_mc_* run.
  local out=$OUTROOT/h1bw_sc_${arm}_1c_l3x${L3_SLICES}_m${mshr}_r${repl}_$STAMP
  rm -rf "$out"; mkdir -p "$out"

  # One single-threaded instance on one simulated CPU.  No second instance
  # exists, so no window-stagger question exists (AGGBW_VALIDITY_2026-09-03.md
  # Q2 does not apply to this campaign).
  local opts="--mode stream-smoke --policy $pol --fact-bytes $FACT_BYTES"
  opts="$opts --fact-node 1 --hot-node 0 --threads 1 --cpu-list 0"
  opts="$opts --warmups $WARMUPS --reps $REPS --window-brackets"

  # pfoff removes the L1D pair (Stride + DCPT) and the L2 pair (Stride +
  # Tagged) from the CONFIG for cpu 0 -- they are not instantiated, not
  # disabled at runtime (CHI_config_8592.py:723-751).  Matches run_se.sh:45's
  # third arm, whose output directory was misleadingly named `wc`.
  local pfoff=""
  [ "$arm" = pfoff ] && pfoff="0"

  # Provenance first, so a killed run is still attributable.
  cat > "$out/MANIFEST.json" <<EOF
{
  "campaign": "h1bw_singlecore",
  "prereg": "experiments/asplos/$PREREG",
  "cell_kind": "$kind",
  "arm": "$arm",
  "ncores": $NCORES,
  "policy": "$pol",
  "prefetch_off_cores": "$pfoff",
  "fact_bytes_requested": "$FACT_BYTES",
  "fact_bytes": $((16 * 1024 * 1024)),
  "l3_per_slice": "$L3_PER_SLICE",
  "num_l3caches": $L3_SLICES,
  "l1_mshr": $mshr,
  "l1_repl": $repl,
  "l1_repl_note": "set explicitly; CHI_config_8592.py:313-321 flags an unset L1_REPL as a confound when L1_MSHR is swept",
  "cxl_mem_bw_requested": null,
  "cxl_bw_ticks_per_byte_expected": 2,
  "cxl_bw_note": "config.ini 'bandwidth' is ticks/byte, quantised to an integer by m5.ticks.fromSeconds; the analyzer gates on the realized value",
  "warmups": $WARMUPS,
  "reps": $REPS,
  "window_brackets": true,
  "pf_degree_l1": 4,
  "pf_degree_l2": 4,
  "pf_page": "4KiB",
  "ruby_randomization": false,
  "bench_sha256": "$BENCH_SHA",
  "bench_path": "benchmarks/e2e/hash_join/build/cxl_join_bench.gem5wbrk",
  "gem5_sha256": "$GEM5_SHA",
  "gem5_git_describe": "$GEM5_DESCRIBE",
  "gem5_git_head": "$GEM5_HEAD",
  "gem5_build_provenance_json_present": $GEM5_PROV_PRESENT,
  "configs_git_describe": "$(git -C "$ROOT/gem5" describe --tags --long --dirty --always 2>/dev/null || echo unknown)",
  "host": "$(hostname)",
  "started": "$(date -Is)"
}
EOF

  # RUBY_RANDOMIZATION is deliberately NOT set.  run_se.sh:23 sets it; se.py:302-309
  # documents its purpose as breaking "per-CPU BW asymmetry", which cannot arise
  # with one CPU, and the certified multi-core campaign does not set it either.
  # Leaving it unset keeps these cells bit-reproducible.
  env ALL_CXL=1 L1_MSHR=$mshr L1_REPL=$repl ${pfoff:+PF_OFF_CORES=$pfoff} \
    "$GEM5" --outdir="$out" "$SE" \
      --cmd="$BIN" --options="$opts" \
      --ruby --topology=Pt2Pt --chi-config="$CHI" \
      --num-l3caches=$L3_SLICES --num-dirs=1 --cpu-type=O3CPU --num-cpus=$NCORES \
      --cpu-clock=1.9GHz \
      --l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
      --l2_size=2MiB --l2_assoc=16 --l3_size=$L3_PER_SLICE --l3_assoc=20 \
      --mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
      --dram-latency=98ns --cxl-latency=203ns \
    > "$out/console.log" 2>&1

  echo "{\"exit\":$?,\"ended\":\"$(date -Is)\"}" > "$out/DONE.json"
}

WHICH=${1:-all}
mkdir -p "$OUTROOT"
echo "outroot   $OUTROOT"
echo "gem5      $GEM5_SHA ($GEM5_DESCRIBE)"
echo "benchmark $BENCH_SHA"

if [ "$WHICH" = primary ] || [ "$WHICH" = all ]; then
  for MSHR in $MSHR_POINTS; do
    for ARM in wb h2 pfoff; do
      run_cell "$ARM" "$MSHR" "$L1_REPL_PRIMARY" primary &
      echo "launched primary h1bw_sc_${ARM}_1c_l3x${L3_SLICES}_m${MSHR}_r${L1_REPL_PRIMARY} (pid $!)"
      sleep 2
    done
  done
fi

# Diagnostic set D: the archive's presumed replacement-path depth, at the MSHR
# point where L1_REPL=16 departs from the request path.  Contributes no
# certified number; it exists so that a magnitude disagreement with the archive
# can be attributed to, or cleared of, replacement-path starvation.
if [ "$WHICH" = diag ] || [ "$WHICH" = all ]; then
  for ARM in wb h2 pfoff; do
    run_cell "$ARM" 48 "$L1_REPL_DIAG" diag &
    echo "launched diag    h1bw_sc_${ARM}_1c_l3x${L3_SLICES}_m48_r${L1_REPL_DIAG} (pid $!)"
    sleep 2
  done
fi

wait
echo "all cells complete"
