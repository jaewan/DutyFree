#!/usr/bin/env bash
# Proof obligation for the run_h1bw_multicore.sh / configs/ruby/Ruby.py
# bracket parameters.
#
#   A. With L3_SLICES and CXL_MEM_BW unset, the generated config.ini must be
#      byte-identical to the completed campaign's.
#   B. With CXL_MEM_BW set, the ONLY thing that may change is
#      system.mem_ctrls1.bandwidth, and it must land on the integer
#      ticks/byte the pre-registration gates on.
#
# Runs the real runner (not a transcription of its command line, which could
# drift from it) into a scratch OUTROOT, waits for gem5 to write config.ini
# during m5.instantiate(), kills it before it simulates anything, and diffs.
#
# config.ini embeds its own outdir in three `host_paths=` lines under
# system.redirect_paths*, so two runs to different directories can never be
# literally identical.  Those three lines are canonicalised to @OUTDIR@ before
# comparison and the raw diff is printed so the substitution is auditable.
#
# Reads gem5/logs/se_chi/h1bw_mc_wb_4c_20260904/config.ini.  Writes nothing
# under gem5/logs/.
set -u

ROOT=/home/domin/DutyFree
REFDIR=$ROOT/gem5/logs/se_chi/h1bw_mc_wb_4c_20260904
REF=$REFDIR/config.ini
SCRATCH=$(mktemp -d /tmp/h1bw_prove.XXXXXX)
SIM_FREQ=1000000000000

[ -f "$REF" ] || { echo "FATAL: reference $REF missing"; exit 1; }

PGID=""
cleanup() { [ -n "$PGID" ] && kill -9 -"$PGID" 2>/dev/null; }
trap cleanup EXIT

canon() { sed "s#$2#@OUTDIR@#g" "$1"; }

# generate <tag> <cxl_mem_bw or empty>  ->  echoes the produced config.ini path
generate() {
  local tag=$1 bw=$2 dir out
  dir=$SCRATCH/$tag
  mkdir -p "$dir"
  env -u L3_SLICES -u CXL_MEM_BW ${bw:+CXL_MEM_BW=$bw} \
    OUTROOT=$dir STAMP=$tag \
    setsid "$ROOT/experiments/asplos/run_h1bw_multicore.sh" 4 \
    > "$dir/runner.log" 2>&1 &
  local runner=$!
  sleep 1
  PGID=$(ps -o pgid= -p $runner 2>/dev/null | tr -d ' ')
  out=$(ls -d "$dir"/h1bw_mc_wb_4c_* 2>/dev/null | head -1)
  local i
  for i in $(seq 1 300); do
    out=$(ls -d "$dir"/h1bw_mc_wb_4c_* 2>/dev/null | head -1)
    [ -n "$out" ] && [ -s "$out/config.ini" ] && { sleep 3; break; }
    sleep 1
  done
  kill -9 -"$PGID" 2>/dev/null; PGID=""
  wait 2>/dev/null
  [ -n "$out" ] && [ -s "$out/config.ini" ] || { echo ""; return 1; }
  echo "$out/config.ini"
}

bwline() {
  awk '/^\[system\.mem_ctrls1\]/{s=1} s&&/^bandwidth=/{sub("bandwidth=","");print;exit}' "$1"
}

rc=0

# ---------------------------------------------------------------- A: default
echo "=============================================================="
echo "A. DEFAULT (L3_SLICES and CXL_MEM_BW unset) vs the completed campaign"
echo "=============================================================="
A=$(generate default "") || { echo "FAIL: gem5 produced no config.ini"; exit 1; }
ADIR=$(dirname "$A")
echo "reference: $REF"
echo "generated: $A"
echo
echo "--- raw diff (expected: only the three self-referential host_paths) ---"
diff "$REF" "$A" | sed 's/^/    /'
echo "--- canonicalised diff (outdir -> @OUTDIR@) ---"
if diff <(canon "$REF" "$REFDIR") <(canon "$A" "$ADIR") > "$SCRATCH/a.diff"; then
  echo "    (empty)"
  echo
  echo "PASS: identical in all $(grep -c . "$REF") lines once each file's own"
  echo "      outdir is canonicalised.  The bracket default is inert."
  echo "      realized mem_ctrls1 bandwidth: $(bwline "$REF") ticks/byte (reference)"
  echo "                                     $(bwline "$A") ticks/byte (generated)"
else
  echo "FAIL: the default is NOT inert:"
  head -60 "$SCRATCH/a.diff" | sed 's/^/    /'
  rc=1
fi

# --------------------------------------------------- B: bandwidth is realized
for spec in 32258064516:31 62500000000:16; do
  req=${spec%%:*}; want=${spec##*:}
  echo
  echo "=============================================================="
  echo "B. CXL_MEM_BW=${req}B/s  -> expect bandwidth=${want}.000000 ticks/byte"
  echo "   ($(awk -v f=$SIM_FREQ -v t=$want 'BEGIN{printf "%.4f", f/t/1e9}') GB/s realized)"
  echo "=============================================================="
  B=$(generate bw$want "${req}B/s") || { echo "FAIL: no config.ini"; rc=1; continue; }
  BDIR=$(dirname "$B")
  got=$(bwline "$B")
  echo "generated: $B"
  echo "realized system.mem_ctrls1.bandwidth = $got ticks/byte"
  if [ "$got" = "$(printf '%f' "$want")" ]; then
    echo "PASS: realized == pre-registered expectation."
  else
    echo "FAIL: realized $got != expected $(printf '%f' "$want")."
    rc=1
  fi
  echo "--- canonicalised diff against the default config (must be 1 line) ---"
  diff <(canon "$A" "$ADIR") <(canon "$B" "$BDIR") > "$SCRATCH/b$want.diff"
  sed 's/^/    /' "$SCRATCH/b$want.diff"
  n=$(grep -c '^[<>]' "$SCRATCH/b$want.diff" || true)
  if [ "$n" = 2 ] && grep -q '^< bandwidth=2.000000' "$SCRATCH/b$want.diff" \
     && grep -q "^> bandwidth=$(printf '%f' "$want")" "$SCRATCH/b$want.diff"; then
    echo "PASS: the override touches system.mem_ctrls1.bandwidth and nothing else."
    echo "      In particular system.mem_ctrls0 (local DRAM) stays at"
    echo "      $(awk '/^\[system\.mem_ctrls0\]/{s=1} s&&/^bandwidth=/{sub("bandwidth=","");print;exit}' "$B") ticks/byte."
  else
    echo "FAIL: the override changed $((n / 2)) settings, not 1."
    rc=1
  fi
done

echo
echo "scratch kept at $SCRATCH"
exit $rc
