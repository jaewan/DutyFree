#!/usr/bin/env bash
# Derive the CXL window from /proc/iomem and load the reconstructed module.
# Refuses rather than guessing: a wrong base would expose a WC alias of system
# RAM, which the module also refuses independently.
set -uo pipefail
KMOD=$(cd "$(dirname "$0")" && pwd)
KO=$KMOD/cxl_memtype_RECONSTRUCTED.ko
[ -f "$KO" ] || { echo "FAIL $KO not built; run make in $KMOD" >&2; exit 2; }

echo "== candidate non-RAM windows in /proc/iomem (need root to see ranges):"
sudo awk -F'[ :-]+' '/Soft Reserved|CXL|Reserved/ {print}' /proc/iomem | head -20

BASE=${BASE:-}; LEN=${LEN:-}
if [ -z "$BASE" ] || [ -z "$LEN" ]; then
  # "Soft Reserved" is how a CXL Type-3 window presenting as a cpuless node
  # usually appears; take the largest such range.
  read -r B E < <(sudo awk '/Soft Reserved/ {split($1,a,"-"); s=strtonum("0x" a[1]); e=strtonum("0x" a[2]);
                            if (e-s > best) {best=e-s; bs=s; be=e}} END {if (best) printf "%d %d\n", bs, be+1}' /proc/iomem)
  if [ -n "${B:-}" ]; then BASE=$B; LEN=$((E-B)); fi
fi
[ -n "${BASE:-}" ] && [ -n "${LEN:-}" ] || {
  echo "FAIL could not derive a CXL window; set BASE= and LEN= explicitly after" >&2
  echo "     inspecting /proc/iomem. Refusing to guess." >&2; exit 2; }

# keep the exposed window modest; the aggressor asks for tens of MB per thread
MAXLEN=$((8*1024*1024*1024))
[ "$LEN" -gt "$MAXLEN" ] && LEN=$MAXLEN
BASE=$(( BASE & ~4095 )); LEN=$(( LEN & ~4095 ))

echo "== loading with base=$BASE len=$LEN ($((LEN>>20)) MiB)"
sudo rmmod cxl_memtype_RECONSTRUCTED 2>/dev/null
sudo insmod "$KO" base=$BASE len=$LEN || { echo "FAIL insmod; see dmesg" >&2; sudo dmesg | tail -5; exit 2; }
sudo dmesg | tail -3
ls -l /dev/cxl_wc /dev/cxl_uc
