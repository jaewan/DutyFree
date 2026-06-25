#!/usr/bin/env bash
# Freeze EMR (Intel Xeon 8592+, 320 MB LLC) system state for reproducible measurements.
#
# Run as root from the benchmarks/ directory:
#   sudo bash setup/emr_freeze.sh
#
# Does:
#   1. Mount resctrl (idempotent)
#   2. Freeze CPU governor, disable turbo, disable NUMA balancing, set THP=madvise
#   3. Enable MSR + PMU access
#   4. Allocate hugepages (node 0: local DRAM, node 2: CXL NUMA)
#   5. Report CAT/MBA capabilities
#   6. Write system_state.txt
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_DIR="$(dirname "$SCRIPT_DIR")"
OUT_DIR="$BENCH_DIR/setup/state"
mkdir -p "$OUT_DIR"

# ── 1. resctrl ────────────────────────────────────────────────────────────────
echo "=== Step 1: mount resctrl ==="
if ! mount | grep -q resctrl; then
    mount -t resctrl resctrl /sys/fs/resctrl
    echo "  mounted /sys/fs/resctrl"
else
    echo "  already mounted"
fi

# ── 2. freeze CPU ─────────────────────────────────────────────────────────────
echo "=== Step 2: freeze CPU ==="
if command -v cpupower >/dev/null 2>&1; then
    cpupower -c all frequency-set -g performance 2>&1 | tail -1
else
    for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo performance > "$g" 2>/dev/null || true
    done
fi
echo 1 > /sys/devices/system/cpu/intel_pstate/no_turbo
for f in /sys/devices/system/cpu/cpufreq/policy*/energy_performance_preference; do
    echo performance > "$f" 2>/dev/null || true
done
echo 0 > /proc/sys/kernel/numa_balancing
echo madvise > /sys/kernel/mm/transparent_hugepage/enabled
echo madvise > /sys/kernel/mm/transparent_hugepage/defrag
echo "  governor=performance  no_turbo=1  numa_balancing=0  THP=madvise"

# ── 3. MSR + PMU access ───────────────────────────────────────────────────────
echo "=== Step 3: MSR + PMU access ==="
echo -1 > /proc/sys/kernel/perf_event_paranoid || true
modprobe msr || true
chmod a+r /dev/cpu/*/msr 2>/dev/null || true
echo "  perf_event_paranoid=-1  MSR readable"

# ── 4. hugepages ──────────────────────────────────────────────────────────────
# node 0: victim (170 MB) + local aggressor headroom
# node 2: CXL NUMA node, 8 aggressors × 5 GB = 40 GB
echo "=== Step 4: hugepages ==="
node0_hp=$(cat /sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages 2>/dev/null || echo 0)
node2_hp=$(cat /sys/devices/system/node/node2/hugepages/hugepages-2048kB/nr_hugepages 2>/dev/null || echo 0)
[ "$node0_hp" -lt 12288 ] && echo 12288 > /sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages
[ "$node2_hp" -lt 22000 ] && echo 22000 > /sys/devices/system/node/node2/hugepages/hugepages-2048kB/nr_hugepages
echo "  node0=$(cat /sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages 2>/dev/null)"
echo "  node2=$(cat /sys/devices/system/node/node2/hugepages/hugepages-2048kB/nr_hugepages 2>/dev/null)"

# ── 5. CAT/MBA capabilities ───────────────────────────────────────────────────
echo "=== Step 5: CAT/MBA capabilities ==="
CBM_HEX=$(cat /sys/fs/resctrl/info/L3/cbm_mask 2>/dev/null || echo "MISSING")
echo "  L3 CBM mask    : $CBM_HEX"
echo "  min_cbm_bits   : $(cat /sys/fs/resctrl/info/L3/min_cbm_bits 2>/dev/null || echo N/A)"
echo "  num_closids    : $(cat /sys/fs/resctrl/info/L3/num_closids  2>/dev/null || echo N/A)"
if [ "$CBM_HEX" != "MISSING" ]; then
    N_WAYS=$(python3 -c "print(bin(int('$CBM_HEX', 16)).count('1'))")
    echo "  n_ways         : $N_WAYS"
fi
if [ -f /sys/fs/resctrl/info/MB/bandwidth_gran ]; then
    echo "  MBA supported  : yes (gran=$(cat /sys/fs/resctrl/info/MB/bandwidth_gran)%  min=$(cat /sys/fs/resctrl/info/MB/min_bandwidth)%)"
else
    echo "  MBA supported  : NO"
fi
echo "  root schemata  : $(cat /sys/fs/resctrl/schemata 2>/dev/null | tr '\n' ' ')"

# ── 6. write system_state.txt ─────────────────────────────────────────────────
echo "=== Step 6: write system_state.txt ==="
OUT="$OUT_DIR/emr_system_state.txt"
{
    echo "# EMR frozen system state"
    echo "# Platform: Intel Xeon Platinum 8592+ (Emerald Rapids)"
    date --iso-8601=seconds

    echo ""; echo "## uname"
    uname -r

    echo ""; echo "## cpu model"
    grep -m1 "model name" /proc/cpuinfo
    grep -m1 "microcode"  /proc/cpuinfo

    echo ""; echo "## freq"
    echo -n "governor cpu0: ";    cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
    echo -n "no_turbo: ";         cat /sys/devices/system/cpu/intel_pstate/no_turbo
    echo -n "scaling_cur_freq kHz cpu0: "; cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq

    echo ""; echo "## numa"
    numactl --hardware

    echo ""; echo "## hugepages"
    for n in 0 1 2; do
        f="/sys/devices/system/node/node$n/hugepages/hugepages-2048kB"
        [ -d "$f" ] && printf "node%s nr/free: " "$n" && cat "$f/nr_hugepages" "$f/free_hugepages" | xargs || true
    done

    echo ""; echo "## resctrl capabilities"
    echo -n "L3 CBM mask: ";    cat /sys/fs/resctrl/info/L3/cbm_mask    2>/dev/null || echo N/A
    echo -n "min_cbm_bits: ";   cat /sys/fs/resctrl/info/L3/min_cbm_bits 2>/dev/null || echo N/A
    echo -n "num_closids: ";    cat /sys/fs/resctrl/info/L3/num_closids   2>/dev/null || echo N/A
    if [ -f /sys/fs/resctrl/info/MB/bandwidth_gran ]; then
        echo "MBA: yes  gran=$(cat /sys/fs/resctrl/info/MB/bandwidth_gran)%  min=$(cat /sys/fs/resctrl/info/MB/min_bandwidth)%"
    else
        echo "MBA: no"
    fi
    echo "root schemata:"; cat /sys/fs/resctrl/schemata 2>/dev/null | sed "s/^/  /"

    echo ""; echo "## kernel knobs"
    echo -n "numa_balancing: ";       cat /proc/sys/kernel/numa_balancing
    echo -n "perf_event_paranoid: ";  cat /proc/sys/kernel/perf_event_paranoid
    echo -n "THP enabled: ";          cat /sys/kernel/mm/transparent_hugepage/enabled
} > "$OUT" 2>&1

chown -R "${SUDO_USER:-$(logname 2>/dev/null || echo root)}": "$OUT_DIR" 2>/dev/null || true
echo ""
echo "Done. State written to: $OUT"
echo "Next: make -C bench/ && sudo bash experiments/cat_mba_driver.sh"
