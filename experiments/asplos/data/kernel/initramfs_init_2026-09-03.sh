#!/bin/sh
# Runs the five streaming kselftests and prints a machine-readable aggregate.
# Boots to this directly; there is no userspace beyond busybox and the tests.
/bin/busybox mount -t proc none /proc
/bin/busybox mount -t sysfs none /sys
/bin/busybox mount -t devtmpfs none /dev 2>/dev/null

echo "=== HOST CONFIG ==="
echo -n "thp_enabled: "; cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || echo "ABSENT"
echo -n "khugepaged: "; ls /sys/kernel/mm/transparent_hugepage/khugepaged >/dev/null 2>&1 && echo present || echo absent

# streaming_hugetlb needs a pool; without one its cases skip rather than run.
# 1 GiB pages must come from the kernel command line -- the runtime sysfs knob
# cannot allocate gigantic pages once memory is fragmented -- so the boot
# reserves them and this only reports what was obtained.
echo 64 > /proc/sys/vm/nr_hugepages 2>/dev/null
/bin/busybox mkdir -p /mnt/huge
/bin/busybox mount -t hugetlbfs none /mnt/huge 2>/dev/null
echo -n "nr_hugepages_2M: "; cat /proc/sys/vm/nr_hugepages 2>/dev/null
echo -n "nr_hugepages_1G: "
cat /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages 2>/dev/null || echo "no 1G pool"
echo -n "ksm: "; cat /sys/kernel/mm/ksm/run 2>/dev/null || echo absent

for t in streaming_basic streaming_reject streaming_hugetlb streaming_memfd streaming_lifecycle; do
	echo "=== BEGIN $t ==="
	/tests/$t
	echo "=== END $t rc=$? ==="
done

echo "=== ALL TESTS COMPLETE ==="
/bin/busybox poweroff -f
