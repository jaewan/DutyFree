#!/usr/bin/env bash
# W8 / T4: build the guest disk image for the full-system contract test.
#
# WHY THIS EXISTS AND WHAT IT IS NOT
# ----------------------------------
# The boot scripts in gem5/scripts point at
#   ~/.cache/gem5/x86-ubuntu-18.04-img-hashjoin-v2
# That image is gone -- ~/.cache/gem5 does not exist on this host, and it is not
# on c4 or on broker either. Its binary had a --line-stride option that the
# committed cxl_join_bench.cpp source does not have, so the image was built from
# a source revision this repository no longer contains.
#
# This script does NOT rebuild that image. It builds a different, much smaller
# one, and gives it a different name so no reader can confuse the two:
#
#   RECONSTRUCTED, NOT RECOVERED. Any number produced on this image must say so.
#   It is a busybox rootfs, not Ubuntu 18.04; it has no --line-stride; and it
#   cannot reproduce a v2-image row.
#
# Unprivileged by construction: mke2fs -d populates the filesystem from a
# staging directory, so no loop mount and no sudo. The partition table is real
# (sfdisk on a plain file, one 0x83 partition at 1 MiB) because the committed
# boot cmdline says root=/dev/sda1, and inventing a new cmdline would be an
# apparatus change made for convenience.
set -euo pipefail

HJ=$(cd "$(dirname "$0")/.." && pwd)
OUT=${OUT:-$HOME/.cache/gem5}
NAME=${NAME:-w8-busybox-streaming-r1.img}
IMG="$OUT/$NAME"
STAGE=${STAGE:-/tmp/w8_rootfs}
FS_MB=${FS_MB:-256}
BENCH="$HJ/build/cxl_join_bench.gem5fs"
M5DIR="$HJ/w8/guest"
EXTRA_BINS=${EXTRA_BINS:-}

for f in "$BENCH" "$M5DIR/m5mini.c" "$M5DIR/m5ops.S"; do
  [ -e "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }
done
for f in $EXTRA_BINS; do
  [ -x "$f" ] || { echo "FAIL missing/non-executable EXTRA_BINS entry $f" >&2; exit 2; }
done
command -v busybox >/dev/null || { echo "FAIL no busybox on the host" >&2; exit 2; }
# ldd exits 1 on a static binary, which `set -o pipefail` turns into a failure
# of the whole check -- so capture first, test second. readelf is the direct
# question anyway: a static binary has no PT_INTERP.
if readelf -l "$(command -v busybox)" 2>/dev/null | grep -q "INTERP"; then
  echo "FAIL host busybox is dynamically linked; the guest has no libc" >&2; exit 2
fi

rm -rf "$STAGE"; mkdir -p "$STAGE"
mkdir -p "$STAGE"/{bin,sbin,etc,proc,sys,dev,tmp,root,var/log,usr/bin,usr/sbin}
chmod 1777 "$STAGE/tmp"

# ---- busybox and its applet links ----------------------------------------
cp "$(command -v busybox)" "$STAGE/bin/busybox"
chmod 755 "$STAGE/bin/busybox"
for a in $("$STAGE/bin/busybox" --list); do
  case "$a" in
    busybox|init) continue ;;   # /sbin/init is ours, below
  esac
  ln -sf /bin/busybox "$STAGE/bin/$a"
done
ln -sf /bin/busybox "$STAGE/bin/sh"

# ---- m5 ------------------------------------------------------------------
gcc -O2 -static -o "$STAGE/sbin/m5" "$M5DIR/m5mini.c" "$M5DIR/m5ops.S"
chmod 755 "$STAGE/sbin/m5"

# ---- the benchmark -------------------------------------------------------
cp "$BENCH" "$STAGE/root/cxl_join_bench.gem5fs"
chmod 755 "$STAGE/root/cxl_join_bench.gem5fs"
for f in $EXTRA_BINS; do
  cp "$f" "$STAGE/root/$(basename "$f")"
  chmod 755 "$STAGE/root/$(basename "$f")"
done

# ---- init ----------------------------------------------------------------
# Replicates configs/boot/hack_back_ckpt.rcS. The environment-variable trick in
# the original relies on the variable surviving into the restored process; here
# init IS pid 1 and the checkpoint is taken from inside it, so the same
# "have I already run?" test is done against a file in /tmp, which is a tmpfs
# and therefore empty again on a fresh boot but present after a restore.
cat > "$STAGE/sbin/init" <<'INIT'
#!/bin/sh
/bin/mount -t proc     proc     /proc
/bin/mount -t sysfs    sysfs    /sys
/bin/mount -t debugfs  debugfs  /sys/kernel/debug 2>/dev/null \
  || echo "W8-WARN: debugfs did not mount; the PTE readback gate will be UNVERIFIED"
/bin/mount -t tmpfs    tmpfs    /tmp
/bin/hostname w8guest
echo "W8-GUEST-UP $(/bin/uname -r)"
/bin/grep -q streaming /proc/kallsyms 2>/dev/null \
  && echo "W8-GUEST-STREAMING-SYMBOLS present" \
  || echo "W8-WARN: no streaming symbols in kallsyms"

if [ -f /tmp/w8_second_pass ]; then
  echo "W8-GUEST second pass; exiting"
  /sbin/m5 exit
fi
: > /tmp/w8_second_pass

echo "W8-GUEST checkpointing..."
/sbin/m5 checkpoint

echo "W8-GUEST loading runscript..."
/sbin/m5 readfile > /tmp/runscript
/bin/chmod 755 /tmp/runscript
if [ -s /tmp/runscript ]; then
  exec /tmp/runscript
fi
echo "W8-GUEST no runscript supplied; exiting rather than dropping to a shell"
/sbin/m5 exit
INIT
chmod 755 "$STAGE/sbin/init"

printf 'root::0:0:root:/root:/bin/sh\n' > "$STAGE/etc/passwd"
printf 'root:x:0:\n'                    > "$STAGE/etc/group"
printf 'w8guest\n'                      > "$STAGE/etc/hostname"
cat > "$STAGE/etc/W8-PROVENANCE" <<PROV
RECONSTRUCTED image, built by benchmarks/e2e/hash_join/w8/build_rootfs_t4.sh.
This is NOT x86-ubuntu-18.04-img-hashjoin-v2 and cannot reproduce its rows.
busybox $("$STAGE/bin/busybox" 2>&1 | head -1 | cut -d, -f1)
bench sha256 $(sha256sum "$BENCH" | cut -d' ' -f1)
PROV
for f in $EXTRA_BINS; do
  printf 'extra %s sha256 %s\n' "$(basename "$f")" \
    "$(sha256sum "$f" | cut -d' ' -f1)" >> "$STAGE/etc/W8-PROVENANCE"
done

# ---- filesystem, then partition table ------------------------------------
mkdir -p "$OUT"
FS="$STAGE.ext2"
rm -f "$FS" "$IMG"
# mke2fs -d copies the staging tree's ownership, which is the unprivileged
# build user. The guest runs as uid 0 so DAC never bites, but a rootfs whose
# every inode is owned by 1001 is a trap for anyone who later adds a
# non-root step. fakeroot gives the chown without privilege.
fakeroot -- sh -c 'chown -R 0:0 "$1" && mke2fs -q -t ext2 -L w8root -d "$1" -b 4096 "$2" "$3"' \
  _ "$STAGE" "$FS" "${FS_MB}m"
# 1 MiB of gap for the MBR + alignment, then the filesystem.
dd if=/dev/zero of="$IMG" bs=1M count=$((FS_MB + 1)) status=none
printf 'label: dos\nstart=2048, type=83, bootable\n' | sfdisk -q "$IMG" >/dev/null
dd if="$FS" of="$IMG" bs=1M seek=1 conv=notrunc status=none
rm -f "$FS"

echo
echo "== T4 image built =="
ls -la "$IMG"
sfdisk -l "$IMG" 2>/dev/null | tail -3
echo "sha256 $(sha256sum "$IMG" | cut -d' ' -f1)"
# This sidecar is a provenance input, not a convenience checksum: the image
# digest binds the embedded /etc/W8-PROVENANCE and hence the guest executable.
# Runners must record these values, never hash a mutable host build after a run.
printf 'image_sha256=%s\nguest_bench_sha256=%s\n' \
  "$(sha256sum "$IMG" | cut -d' ' -f1)" \
  "$(sha256sum "$BENCH" | cut -d' ' -f1)" > "$IMG.provenance"
echo "provenance $IMG.provenance"
