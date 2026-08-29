#!/usr/bin/env bash
# (b) Stage the real WC path: offline the CXL window, load the WC/UC module.
# RESTORES on any exit path -- the window is online System RAM on this host and
# must be returned to the kernel.
set -uo pipefail
BASE=0x18400000000
LEN=$((8*1024*1024*1024))          # 8 GiB is the loader's cap and ample for 7x64 MB
KMOD=$HOME/DutyFree/amd_cat/kmod
OFFLINED=/tmp/offlined_blocks.txt
: > "$OFFLINED"

restore() {
  echo "== RESTORE =="
  sudo -n rmmod cxl_memtype_RECONSTRUCTED 2>/dev/null && echo "  module unloaded"
  local n=0
  while read -r b; do
    sudo -n sh -c "echo online > /sys/devices/system/memory/$b/state" 2>/dev/null && n=$((n+1))
  done < "$OFFLINED"
  echo "  re-onlined $n blocks"
  echo "  node2 MemTotal now: $(awk '/MemTotal/{print $4, $5}' /sys/devices/system/node/node2/meminfo)"
}
trap restore EXIT

echo "== node2 before: $(awk '/MemTotal/{print $4}' /sys/devices/system/node/node2/meminfo) kB, \
free $(awk '/MemFree/{print $4}' /sys/devices/system/node/node2/meminfo) kB"

echo "== offlining node2 memory blocks =="
ok=0; fail=0
for l in /sys/devices/system/node/node2/memory*; do
  b=$(basename "$l")
  if sudo -n sh -c "echo offline > /sys/devices/system/memory/$b/state" 2>/dev/null; then
    echo "$b" >> "$OFFLINED"; ok=$((ok+1))
  else
    fail=$((fail+1))
  fi
done
echo "  offlined=$ok  refused=$fail"
if [ "$ok" -eq 0 ]; then echo "FAIL: no blocks offlined; aborting" >&2; exit 3; fi

echo "== is the CXL window still System RAM? =="
sudo -n grep -A1 "CXL Window 0" /proc/iomem | sed 's/^/  /'

echo "== loading module base=$BASE len=$LEN =="
sudo -n insmod "$KMOD/cxl_memtype_RECONSTRUCTED.ko" base=$BASE len=$LEN 2>&1 | head -3
ls -la /dev/cxl_wc /dev/cxl_uc 2>/dev/null | sed 's/^/  /'
sudo -n dmesg 2>/dev/null | tail -2 | sed 's/^/  /'

echo "== VALIDATION of the reconstruction against frozen figures =="
echo "   (registered check: single-core WB 12.43 / WC 3.20 GB/s)"
A=/home/domin/tmp_dutyfree_exp/bin/aggressor
for m in wb_load wc_ntdqa; do
  bw=$($A -m $m -t 1 -c 1 -N 2 -s 64 -d 6 2>&1 | grep '^aggregate:' | awk '{print $2}')
  echo "   single-core $m: ${bw:-FAIL} GB/s"
done
echo "== staged; module stays loaded until this script exits =="
sleep "${HOLD:-1}"
