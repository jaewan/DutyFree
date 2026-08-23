#!/usr/bin/env bash
# W8 / T5: restore the T4 checkpoint into the O3 + Ruby/CHI 8592 machine and run
# one benchmark arm. One arm per invocation, serially, so each arm's gate can be
# read before the next is started.
#
# WRAPPER, not a replacement -- same principle as boot_t4.sh. Everything W8
# needs that differs from the committed launcher is supplied through the
# environment; gem5/scripts/fs_restore_chi_8592.sh is not edited.
#
# The difference that matters is DISK. fs_restore_chi_8592.sh defaults to
# x86-ubuntu-18.04-img-hashjoin-v2, and T4's checkpoint was taken on the
# reconstructed busybox image. Restoring a checkpoint against a different
# filesystem does not necessarily fail loudly -- the guest's in-memory ext2
# state would simply address blocks belonging to another image -- so the
# mismatch is refused here rather than discovered in the numbers.
#
# Usage: run_t5.sh <arm>          arm in {wb, stream_m5op, stream_mprot}
# Env:   CKPT   checkpoint name under gem5/logs/fs_boot_ckpt (default the T4 one)
#        DISK   guest image; must match the checkpoint's image identity
#        RUN    output run name (default w8_t5_<arm>)
set -euo pipefail
W8=$(cd "$(dirname "$0")" && pwd)
G=${G:-$HOME/DutyFree/gem5}
ARM=${1:?usage: run_t5.sh <wb|stream_m5op|stream_mprot>}
case "$ARM" in wb|stream_m5op|stream_mprot) ;; *) echo "FAIL unknown arm '$ARM'" >&2; exit 2 ;; esac

CKPT=${CKPT:-atomic_2cpu_w8busybox}
export DISK=${DISK:-$HOME/.cache/gem5/w8-busybox-streaming-r1.img}
RUN=${RUN:-w8_t5_$ARM}
RCS="$W8/rcs/w8_$ARM.rcS"
CDIR="$G/logs/fs_boot_ckpt/$CKPT"
ODIR="$G/logs/fs_restore_chi/$RUN"

# --- gate 1: the checkpoint exists and is finished being written -------------
[ -d "$CDIR" ] || { echo "FAIL no checkpoint dir $CDIR" >&2; exit 2; }
# A stock gem5 FS checkpoint leaves TWO cpt.* directories behind, and only one
# of them is a checkpoint. src/python/m5/simulate.py:checkpoint() runs
# os.makedirs(dir) on the name Simulation.py handed it -- the literal,
# unsubstituted "cpt.%d" -- and only afterwards does C++ substitute the tick:
# CheckpointIn::setDir (src/sim/serialize.cc:142-147) csprintf()s curTick() in
# when it sees a '%', and serializeAll mkdir()s that. The result is an always-
# empty cpt.%d beside the real cpt.<tick>. This is upstream behaviour, not ours,
# and it happens on every FS checkpoint.
#
# So "exactly one cpt.* dir" is the wrong test -- it would refuse every valid
# T4 checkpoint. The test is "exactly one cpt.* dir that HAS a checkpoint in
# it", which still refuses if two real checkpoints are present.
shopt -s nullglob
ALLCPT=("$CDIR"/cpt.*)
shopt -u nullglob
CPTS=()
for c in "${ALLCPT[@]}"; do [ -s "$c/m5.cpt" ] && CPTS+=("$c"); done
[ ${#CPTS[@]} -eq 1 ] || {
  echo "FAIL expected exactly 1 cpt.* holding a non-empty m5.cpt in $CDIR;" >&2
  echo "     found ${#CPTS[@]} such, out of ${#ALLCPT[@]} cpt.* directories:" >&2
  for c in "${ALLCPT[@]}"; do
    echo "       ${c##*/}  m5.cpt $( [ -s "$c/m5.cpt" ] && stat -c %s "$c/m5.cpt" || echo "absent/empty" )" >&2
  done
  exit 2; }
# gem5 does NOT select the checkpoint the way the test above does, and the two
# rules can disagree. configs/common/Simulation.py:200-215 enumerates with
# re.compile(r"cpt\.([0-9]+)").match(), sorts by int(tick), and `-r 1` takes
# cpts[0] -- the LOWEST tick. Two consequences:
#   * the empty cpt.%d that upstream leaves behind does not match the regex, so
#     it is invisible to gem5 and -r 1 does land on the real checkpoint. That is
#     why the two-dir situation above is safe rather than merely tolerated.
#   * but a stale, interrupted cpt.<lower-tick> holding an EMPTY m5.cpt would be
#     selected by gem5 while still passing the "exactly one non-empty m5.cpt"
#     test above -- that test would see one complete checkpoint and wave it
#     through, and gem5 would silently restore the broken one instead.
# So the gate additionally requires that the directory gem5 will actually pick
# is the directory this gate validated. Verified 2026-08-24 against T4's real
# checkpoint: the parent holds cpt.%d and cpt.5548084949500, the regex matches
# only the latter, and both rules agree on it.
SEL=$(ls -1 "$CDIR" | sed -n 's/^cpt\.\([0-9]\+\)$/\1/p' | sort -n | head -1)
[ -n "$SEL" ] || { echo "FAIL no cpt.<digits> in $CDIR; gem5 -r 1 would fatal here" >&2; exit 2; }
[ "$CDIR/cpt.$SEL" = "${CPTS[0]}" ] || {
  echo "FAIL gem5 -r 1 would restore cpt.$SEL, but the only complete checkpoint is ${CPTS[0]##*/}" >&2
  echo "     (a stale lower-tick checkpoint dir is present; remove it or point CKPT elsewhere)" >&2
  exit 2; }
# A non-empty m5.cpt does NOT mean the checkpoint is finished, and the reason is
# stronger than first recorded. Measured across the whole of T4's checkpoint
# write (2026-08-24), m5.cpt appears EARLY and is finalized LAST:
#     03:02  m5.cpt   344,082 B   store0 14.2 MB complete, cow complete
#     03:15                       store1 254.1 MB complete
#     03:27  m5.cpt 20,339,682 B  store2 255.1 MB complete   <- gem5 exits
# So m5.cpt is not merely written before the stores; it grows by a factor of 59
# after it first becomes non-empty, and its final write is the last thing that
# happens. A gate that samples m5.cpt's existence, or even its size, at any
# point before gem5 exits can see a plausible-looking partial checkpoint.
# The process-ownership check below is what actually establishes completeness.
# NOTE: pgrep -f matches ANY process whose argv contains the pattern, including
# an ancestor shell -- observed 2026-08-24, where a `bash -c '... pgrep -f
# "outdir=/tmp/w7" ...'` wrapper matched itself. pgrep excludes only its own pid.
# The pattern below includes the "--outdir=" prefix, which nothing but gem5's own
# command line carries, so do not invoke this script from a command line that
# spells that string out.
if pgrep -a -f -- "--outdir=$CDIR" >/dev/null 2>&1; then
  echo "FAIL a gem5 process still owns $CDIR; m5.cpt is written after the dir appears (parse race)" >&2
  exit 2
fi

# --- gate 2: the image the checkpoint was taken on is the image we restore ---
# Exercised in BOTH directions against T4's real config.json (2026-08-24, while
# the boot was still running -- the file is written at startup):
#   * config.json contains exactly ONE image_file, at
#     /system/pc/south_bridge/ide/disks[0]/image/child, so the `head -1` below
#     is unambiguous and the fact that `return` does not unwind the recursion
#     cannot pick a wrong one.
#   * it resolves to w8-busybox-streaming-r1.img -> gate PASSES for $DISK.
#   * substituting x86-ubuntu-18.04-img-hashjoin-v2 -> gate REFUSES.
# A gate that has only ever been seen to fail is not known to protect anything;
# this one has now been seen to pass on the right image and refuse the wrong one.
BOOTIMG=$(python3 -c '
import json,sys
def walk(o):
    if isinstance(o,dict):
        for k,v in o.items():
            if k=="image_file" and isinstance(v,str) and v: print(v); return
            walk(v)
    elif isinstance(o,list):
        for v in o: walk(v)
walk(json.load(open(sys.argv[1])))' "$CDIR/config.json" | head -1)
[ -n "$BOOTIMG" ] || { echo "FAIL could not read the boot image out of $CDIR/config.json" >&2; exit 2; }
if [ "$(readlink -f "$BOOTIMG")" != "$(readlink -f "$DISK")" ]; then
  echo "FAIL image identity mismatch -- refusing to restore." >&2
  echo "  checkpoint was taken on: $BOOTIMG" >&2
  echo "  restore would attach:    $DISK" >&2
  exit 2
fi

# --- gate 3: the arm script exists and is non-empty --------------------------
# An empty readfile is how the boot pass tells init "no benchmark"; an empty one
# here would boot to exit and produce a stats file with no workload in it.
[ -s "$RCS" ] || { echo "FAIL arm script $RCS missing or empty" >&2; exit 2; }

[ -e "$ODIR" ] && { echo "FAIL $ODIR already exists; pick another RUN" >&2; exit 2; }

echo "== T5 arm=$ARM ckpt=$CKPT image=$(basename "$DISK") out=$RUN"
echo "== checkpoint ${CPTS[0]##*/}, m5.cpt $(stat -c %s "${CPTS[0]}/m5.cpt") bytes"

# gem5's own stdout/stderr is teed into the outdir because t5_analyze.py's G5
# reads it. The m5op arm's expected result is zero classifications, and gem5's
# "setstreaming called outside SE mode, ignored" warning is what separates that
# documented no-op from an unexplained zero. It goes to stderr and nowhere else;
# without this it would be lost the moment the terminal scrolled.
# DRYRUN=1 runs every gate and stops before launching gem5. The gates exist to
# protect a resource that is expensive to produce -- T4's checkpoint took ~2 h --
# and are restored three times by T5, so being able to exercise them against the
# real artifact without spending a run is worth the four lines. Deliberately
# placed AFTER every gate and BEFORE the first side effect: no outdir is created,
# so a dry run leaves nothing behind and can be repeated.
[ "${DRYRUN:-0}" = 1 ] && { echo "== DRYRUN: all gates passed for arm=$ARM; not launching gem5"; exit 0; }

mkdir -p "$ODIR"
set +e
"$G/scripts/fs_restore_chi_8592.sh" "$CKPT" "$RUN" "$RCS" 2>&1 | tee "$ODIR/gem5.log"
rc=${PIPESTATUS[0]}
set -e
echo "== T5 arm=$ARM gem5 exit $rc"
grep -c "setstreaming called outside SE mode" "$ODIR/gem5.log" \
  | xargs -I{} echo "== T5 arm=$ARM SE-only setstreaming warnings: {}"
exit $rc
