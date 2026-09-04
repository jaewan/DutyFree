#!/usr/bin/env bash
# Proof obligation for the src/python/m5/ticks.py rounding-guard fix.
#
# The fix changes  err = (value - int_value) / value
#             to   err = abs(value - int_value) / value
# so rounding error is reported in both directions.  `err` feeds nothing but
# the warn() predicate, so the returned integer tick count must be identical
# for every input.  This script demonstrates that end to end.
#
# gem5 MARSHALS src/python/ INTO gem5.opt at build time (see
# src/python/importer.py:CodeImporter), so an edit to src/python/m5/ticks.py is
# inert against the existing binary unless M5_OVERRIDE_PY_SOURCE=true is set,
# which makes the embedded importer recompile each module from the absolute
# path recorded at build time.  That is how this proof exercises the patch
# without rebuilding, and it doubles as the positive control:
#
#   C. control  -- override OFF: the binary's embedded (unpatched) ticks.py.
#                  Expect ZERO 'rounding error' lines, as on every completed
#                  run in this project.
#   P. patched  -- override ON: the on-disk (patched) ticks.py.  Expect
#                  'rounding error' lines to appear, which proves the override
#                  really loaded the edit, AND config.ini to be identical to
#                  the completed campaign's, which proves it changed no value.
#
# The on-disk src/python/ tree is clean at HEAD apart from the ticks.py hunk
# (last commit touching src/python/ is 2025-12-30; gem5.opt was built
# 2026-08-31), so the override introduces exactly one difference from what the
# binary embedded, and phase P isolates it.
#
# config.ini embeds its own outdir in three `host_paths=` lines under
# system.redirect_paths*, so two runs to different directories can never be
# literally identical.  Those lines are canonicalised to @OUTDIR@ before
# comparison and the raw diff is printed so the substitution is auditable.
#
# Reads gem5/logs/se_chi/h1bw_mc_wb_4c_20260904/config.ini.  Writes nothing
# under gem5/logs/.  Config-generation only: each gem5 is killed as soon as it
# has written config.ini, before it simulates anything.
set -u

ROOT=/home/domin/DutyFree
REFDIR=$ROOT/gem5/logs/se_chi/h1bw_mc_wb_4c_20260904
REF=$REFDIR/config.ini
SCRATCH=$(mktemp -d /tmp/ticks_guard.XXXXXX)

# se.py records the LAUNCHING SHELL's working directory in each Process's
# `cwd=` (four lines, one per simulated CPU).  It is an invocation property,
# not a configured value, so this script launches from the same directory the
# completed campaign was launched from -- $ROOT/experiments/asplos, per that
# run's own config.ini -- rather than papering over the difference in canon().
cd "$ROOT/experiments/asplos" || exit 1

[ -f "$REF" ] || { echo "FATAL: reference $REF missing"; exit 1; }
grep -q 'abs(value - int_value)' "$ROOT/gem5/src/python/m5/ticks.py" \
  || { echo "FATAL: ticks.py does not carry the fix"; exit 1; }

PGID=""
cleanup() { [ -n "$PGID" ] && kill -9 -"$PGID" 2>/dev/null; }
trap cleanup EXIT

canon() { sed "s#$2#@OUTDIR@#g" "$1"; }

# generate <tag> <override:true|false>  ->  echoes the produced outdir
generate() {
  local tag=$1 override=$2 dir out i
  dir=$SCRATCH/$tag
  mkdir -p "$dir"
  env -u L3_SLICES -u CXL_MEM_BW M5_OVERRIDE_PY_SOURCE=$override \
    OUTROOT=$dir STAMP=$tag \
    setsid "$ROOT/experiments/asplos/run_h1bw_multicore.sh" 4 \
    > "$dir/runner.log" 2>&1 &
  local runner=$!
  sleep 1
  PGID=$(ps -o pgid= -p $runner 2>/dev/null | tr -d ' ')
  for i in $(seq 1 300); do
    out=$(ls -d "$dir"/h1bw_mc_wb_4c_* 2>/dev/null | head -1)
    # config.ini is written inside m5.instantiate(); wait past it so the
    # getValue() conversions after the .ini dump also reach console.log
    [ -n "$out" ] && [ -s "$out/config.ini" ] && { sleep 10; break; }
    sleep 1
  done
  kill -9 -"$PGID" 2>/dev/null; PGID=""
  wait 2>/dev/null
  [ -n "${out:-}" ] && [ -s "$out/config.ini" ] || { echo ""; return 1; }
  echo "$out"
}

rc=0
REFLINES=$(wc -l < "$REF")
REFNONBLANK=$(grep -c . "$REF")

echo "=============================================================="
echo "C. CONTROL -- M5_OVERRIDE_PY_SOURCE=false (embedded, unpatched)"
echo "=============================================================="
C=$(generate control false) || { echo "FAIL: gem5 produced no config.ini"; exit 1; }
nc=$(grep -ci 'rounding error' "$C/console.log" || true)
echo "generated: $C/config.ini"
echo "'rounding error' lines: $nc"
if [ "$nc" = 0 ]; then
  echo "PASS: the unpatched guard is silent, as on all 21 runs in logs/se_chi."
else
  echo "FAIL: expected 0 from the unpatched guard, got $nc."
  rc=1
fi
if diff <(canon "$REF" "$REFDIR") <(canon "$C/config.ini" "$C") > "$SCRATCH/c.diff"; then
  echo "PASS: control config.ini identical to the reference."
else
  echo "FAIL: control differs from the reference before any patch is applied:"
  head -40 "$SCRATCH/c.diff" | sed 's/^/    /'
  rc=1
fi

echo
echo "=============================================================="
echo "P. PATCHED -- M5_OVERRIDE_PY_SOURCE=true (on-disk, patched)"
echo "=============================================================="
P=$(generate patched true) || { echo "FAIL: gem5 produced no config.ini"; exit 1; }
np=$(grep -ci 'rounding error' "$P/console.log" || true)
echo "generated: $P/config.ini"
echo "'rounding error' lines: $np"
if [ "$np" -gt 0 ]; then
  echo "PASS: the fixed guard fires, so the override really loaded the edit."
  echo "--- the warnings, de-duplicated with counts ---"
  grep -A1 -i 'rounding error' "$P/console.log" \
    | grep -oE '[0-9.]+ rounded to [0-9]+' | sort | uniq -c | sort -rn \
    | sed 's/^/    /'
else
  echo "FAIL: no warning fired -- the override did not load the patch, so the"
  echo "      inertness check below would be vacuous."
  rc=1
fi

echo
echo "--- raw diff vs reference (expected: only the three host_paths lines) ---"
diff "$REF" "$P/config.ini" | sed 's/^/    /'
echo "--- canonicalised diff (each file's own outdir -> @OUTDIR@) ---"
if diff <(canon "$REF" "$REFDIR") <(canon "$P/config.ini" "$P") > "$SCRATCH/p.diff"; then
  echo "    (empty)"
  echo
  echo "PASS: THE FIX IS INERT.  config.ini generated with the patched"
  echo "      ticks.py is identical to the completed run's in all $REFLINES"
  echo "      lines ($REFNONBLANK non-blank) once each file's three"
  echo "      self-referential host_paths lines are canonicalised."
  echo "      0 differing lines."
else
  echo "FAIL: NOT inert -- $(grep -c '^[<>]' "$SCRATCH/p.diff") differing lines:"
  head -60 "$SCRATCH/p.diff" | sed 's/^/    /'
  rc=1
fi

echo
echo "--- control config.ini vs patched config.ini (must also be empty) ---"
if diff <(canon "$C/config.ini" "$C") <(canon "$P/config.ini" "$P") > "$SCRATCH/cp.diff"; then
  echo "    (empty)  PASS"
else
  echo "FAIL: $(grep -c '^[<>]' "$SCRATCH/cp.diff") differing lines:"
  head -60 "$SCRATCH/cp.diff" | sed 's/^/    /'
  rc=1
fi

echo
echo "scratch kept at $SCRATCH"
exit $rc
