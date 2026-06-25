#!/usr/bin/env bash
# Freeze SPR (Intel Xeon 8462Y+, 60 MB LLC) system state for reproducible measurements.
#
# Run as root from the benchmarks/ directory:
#   sudo bash setup/spr_freeze.sh
#
# Does:
#   1. Freeze CPU governor, disable turbo, disable NUMA balancing, set THP=madvise
#   2. Enable MSR + PMU access
#   3. Allocate hugepages (node 0: local DRAM, node 2: CXL NUMA, cross-socket)
#   4. Write system_state.txt
#
# Note: SPR CXL is cross-socket (NUMA distance 24), so the LLC pollution mechanism
# differs from EMR. The WSS sweep still demonstrates the tax; CAT/MBA not applicable
# because LLC pollution occurs on the aggressor's socket, not the victim's.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_DIR="$(dirname "$SCRIPT_DIR")"
OUT_DIR="$BENCH_DIR/setup/state"
mkdir -p "$OUT_DIR"

# ── 1. freeze CPU ─────────────────────────────────────────────────────────────
echo "=== Freeze CPU ==="
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

# ── 2. MSR + PMU access ───────────────────────────────────────────────────────
echo "=== MSR + PMU access ==="
echo -1 > /proc/sys/kernel/perf_event_paranoid || true
modprobe msr || true
chmod a+r /dev/cpu/*/msr 2>/dev/null || true
echo "  perf_event_paranoid=-1  MSR readable"

# ── 3. hugepages ──────────────────────────────────────────────────────────────
# node 0: victim (60 MB) + local-4 aggressors (4 × 5 GB = 20 GB)
# node 2: CXL-8 aggressors (8 × 5 GB = 40 GB)
echo "=== Hugepages ==="
node0_hp=$(cat /sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages 2>/dev/null || echo 0)
node2_hp=$(cat /sys/devices/system/node/node2/hugepages/hugepages-2048kB/nr_hugepages 2>/dev/null || echo 0)
[ "$node0_hp" -lt 11264 ] && echo 11264 > /sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages
[ "$node2_hp" -lt 20480 ] && echo 20480 > /sys/devices/system/node/node2/hugepages/hugepages-2048kB/nr_hugepages
echo "  node0=$(cat /sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages 2>/dev/null)"
echo "  node2=$(cat /sys/devices/system/node/node2/hugepages/hugepages-2048kB/nr_hugepages 2>/dev/null)"

# ── 4. write system_state.txt ─────────────────────────────────────────────────
echo "=== Write system_state.txt ==="
OUT="$OUT_DIR/spr_system_state.txt"
{
    echo "# SPR frozen system state"
    echo "# Platform: Intel Xeon Platinum 8462Y+ (Sapphire Rapids)"
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

    echo ""; echo "## kernel knobs"
    echo -n "numa_balancing: ";       cat /proc/sys/kernel/numa_balancing
    echo -n "perf_event_paranoid: ";  cat /proc/sys/kernel/perf_event_paranoid
    echo -n "THP enabled: ";          cat /sys/kernel/mm/transparent_hugepage/enabled

    echo ""; echo "## LLC size"
    lscpu | grep -i "L3 cache" || true
} > "$OUT" 2>&1

chown -R "${SUDO_USER:-$(logname 2>/dev/null || echo root)}": "$OUT_DIR" 2>/dev/null || true
echo ""
echo "Done. State written to: $OUT"
echo "Next: make -C bench/ && python3 experiments/wss_sweep.py --platform spr --sweep all"
