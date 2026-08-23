#!/usr/bin/env bash
# W8 / T4: boot the reconstructed image and take the restorable checkpoint.
#
# This is a WRAPPER, not a replacement. gem5/scripts/fs_boot_checkpoint.sh is
# committed apparatus and already takes DISK and SCRIPT_OVERRIDE from the
# environment, so W8 supplies its two differences there rather than editing it:
#
#   DISK             the reconstructed image (see build_rootfs_t4.sh -- it is
#                    NOT the v2 image and is named so nobody can confuse them)
#   SCRIPT_OVERRIDE  an empty file. The reconstructed image's /sbin/init already
#                    contains the hack_back checkpoint logic, so handing it
#                    hack_back_ckpt.rcS through m5 readfile would make it run
#                    the sequence a second time and take a second checkpoint.
#                    An empty readfile makes init checkpoint once and exit,
#                    which is exactly what the boot pass is for.
#
# Checkpoint name carries the image identity: a checkpoint taken on the
# reconstructed rootfs cannot be restored against the v2 image.
set -euo pipefail
W8=$(cd "$(dirname "$0")" && pwd)
G=${G:-$HOME/DutyFree/gem5}
N=${N:-2}
export DISK=${DISK:-$HOME/.cache/gem5/w8-busybox-streaming-r1.img}
export SCRIPT_OVERRIDE="$W8/empty.rcS"
[ -f "$DISK" ] || { echo "FAIL no image at $DISK -- run build_rootfs_t4.sh" >&2; exit 2; }
NAME=${NAME:-atomic_${N}cpu_w8busybox}
echo "== boot: N=$N image=$(basename "$DISK") ckpt=$NAME"
exec "$G/scripts/fs_boot_checkpoint.sh" "$N" "$NAME"
