#!/usr/bin/env bash
# Grow mos182 node0's 2 MiB hugepage pool enough for the 8 GiB fact stream.
# As-found (2026-09-01): node0=1024, node1=0, node2=35488.  8 GiB MAP_HUGETLB
# SIGBUS'd because node0 only had 2 GiB.  User authorized sudo to grow node0;
# we grow node0 and leave node2 alone (no host-wide shrink).
#
# After the registered --huge2m campaign the pool was restored to as-found
# (node0=1024, 2026-09-01).  Re-run this script before reproducing 8 GiB
# --huge2m.  WANT=1024 restores the as-found size.
set -euo pipefail
NODE=${NODE:-0}
WANT=${WANT:-8192}   # 16 GiB: 8 GiB fact + 32 MiB victim + headroom
SYS=/sys/devices/system/node/node${NODE}/hugepages/hugepages-2048kB/nr_hugepages
[ -f "$SYS" ] || { echo "FAIL no $SYS" >&2; exit 2; }
echo "before node$NODE nr=$(cat "$SYS") free=$(cat "${SYS/nr_hugepages/free_hugepages}")"
echo "$WANT" | sudo -n tee "$SYS" >/dev/null
got=$(cat "$SYS")
echo "after  node$NODE nr=$got free=$(cat "${SYS/nr_hugepages/free_hugepages}")"
[ "$got" -ge "$WANT" ] || { echo "FAIL requested $WANT got $got" >&2; exit 3; }
