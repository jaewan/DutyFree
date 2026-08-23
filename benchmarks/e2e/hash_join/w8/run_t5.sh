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
shopt -s nullglob
CPTS=("$CDIR"/cpt.*)
shopt -u nullglob
[ ${#CPTS[@]} -eq 1 ] || { echo "FAIL expected exactly 1 cpt.* in $CDIR, found ${#CPTS[@]}" >&2; exit 2; }
[ -s "${CPTS[0]}/m5.cpt" ] || { echo "FAIL ${CPTS[0]}/m5.cpt missing or empty -- boot may still be writing it" >&2; exit 2; }
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
mkdir -p "$ODIR"
set +e
"$G/scripts/fs_restore_chi_8592.sh" "$CKPT" "$RUN" "$RCS" 2>&1 | tee "$ODIR/gem5.log"
rc=${PIPESTATUS[0]}
set -e
echo "== T5 arm=$ARM gem5 exit $rc"
grep -c "setstreaming called outside SE mode" "$ODIR/gem5.log" \
  | xargs -I{} echo "== T5 arm=$ARM SE-only setstreaming warnings: {}"
exit $rc
