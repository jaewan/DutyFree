#!/usr/bin/env bash
# Freeze and capture platform state on the AMD EPYC 9754 (Bergamo) host.
#
# The Intel hosts have had emr_freeze.sh / spr_freeze.sh since 2026-07-15; the
# AMD host had neither, so tab:appplat's "performance governor, turbo off"
# claim covered a machine whose state was never scripted or captured. On
# 2026-08-21 moscxl was found running schedutil with boost enabled after an
# 2026-08-19 reboot. This script closes that gap in both directions: it can
# freeze the host, and it can capture state without changing anything.
#
#   sudo bash bergamo_freeze.sh          # freeze, then capture
#   VERIFY_ONLY=1 bash bergamo_freeze.sh # capture only; no writes, no root
#
# Hugepage provisioning is opt-in (HP_PROVISION=1 with HP_NODE0/HP_NODE2),
# never silent: changing hugepage counts changes memory placement, which is an
# experimental variable on this host rather than part of freezing it.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/state"
VERIFY_ONLY="${VERIFY_ONLY:-0}"
mkdir -p "$OUT_DIR"

w() {  # write $2 to $1, tolerating absence; no-op under VERIFY_ONLY
    [ "$VERIFY_ONLY" = "1" ] && return 0
    [ -w "$1" ] || [ -e "$1" ] || return 0
    echo "$2" > "$1" 2>/dev/null || true
}

if [ "$VERIFY_ONLY" != "1" ] && [ "$(id -u)" != "0" ]; then
    echo "must run as root to freeze; use VERIFY_ONLY=1 to capture only" >&2
    exit 1
fi
grep -qm1 "AMD EPYC 9754" /proc/cpuinfo || {
    echo "warning: /proc/cpuinfo does not report AMD EPYC 9754" >&2; }

echo "=== Step 1: mount resctrl ==="
if ! mount | grep -q resctrl; then
    if [ "$VERIFY_ONLY" = "1" ]; then
        echo "  NOT mounted (verify-only; not mounting)"
    else
        mount -t resctrl resctrl /sys/fs/resctrl && echo "  mounted /sys/fs/resctrl"
    fi
else
    echo "  already mounted"
fi

echo "=== Step 2: freeze CPU ==="
# EPYC 9754 here runs acpi-cpufreq, not amd-pstate: there is no
# energy_performance_preference and turbo is /sys/.../cpufreq/boost, not
# intel_pstate/no_turbo.
if [ "$VERIFY_ONLY" != "1" ]; then
    if command -v cpupower >/dev/null 2>&1; then
        cpupower -c all frequency-set -g performance 2>&1 | tail -1
    else
        for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
            echo performance > "$g" 2>/dev/null || true
        done
    fi
fi
w /sys/devices/system/cpu/cpufreq/boost 0
w /proc/sys/kernel/numa_balancing 0
w /sys/kernel/mm/transparent_hugepage/enabled madvise
w /sys/kernel/mm/transparent_hugepage/defrag madvise
echo "  governor=$(cat /sys/devices/system/cpu/cpu8/cpufreq/scaling_governor 2>/dev/null)" \
     " boost=$(cat /sys/devices/system/cpu/cpufreq/boost 2>/dev/null)" \
     " numa_balancing=$(cat /proc/sys/kernel/numa_balancing 2>/dev/null)"

echo "=== Step 3: MSR + PMU access ==="
w /proc/sys/kernel/perf_event_paranoid -1
if [ "$VERIFY_ONLY" != "1" ]; then
    modprobe msr || true
    chmod a+r /dev/cpu/*/msr 2>/dev/null || true
fi
echo "  perf_event_paranoid=$(cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null)"

echo "=== Step 4: hugepages (report; provision only on request) ==="
for n in 0 1 2; do
    d="/sys/devices/system/node/node$n/hugepages/hugepages-2048kB"
    [ -d "$d" ] && echo "  node$n nr/free: $(cat "$d/nr_hugepages") / $(cat "$d/free_hugepages")"
done
if [ "${HP_PROVISION:-0}" = "1" ] && [ "$VERIFY_ONLY" != "1" ]; then
    [ -n "${HP_NODE0:-}" ] && w /sys/devices/system/node/node0/hugepages/hugepages-2048kB/nr_hugepages "$HP_NODE0"
    [ -n "${HP_NODE2:-}" ] && w /sys/devices/system/node/node2/hugepages/hugepages-2048kB/nr_hugepages "$HP_NODE2"
    echo "  provisioned node0=${HP_NODE0:-unchanged} node2=${HP_NODE2:-unchanged}"
else
    echo "  (unchanged; set HP_PROVISION=1 with HP_NODE0/HP_NODE2 to change)"
fi

echo "=== Step 5: CAT/MBA capabilities ==="
CBM_HEX=$(cat /sys/fs/resctrl/info/L3/cbm_mask 2>/dev/null || echo "MISSING")
MINBITS=$(cat /sys/fs/resctrl/info/L3/min_cbm_bits 2>/dev/null || echo N/A)
echo "  L3 CBM mask    : $CBM_HEX"
echo "  min_cbm_bits   : $MINBITS"
echo "  num_closids    : $(cat /sys/fs/resctrl/info/L3/num_closids 2>/dev/null || echo N/A)"
echo "  sparse_masks   : $(cat /sys/fs/resctrl/info/L3/sparse_masks 2>/dev/null || echo N/A)"
if [ "$CBM_HEX" != "MISSING" ]; then
    echo "  n_ways         : $(python3 -c "print(bin(int('$CBM_HEX',16)).count('1'))")"
fi
if [ "$MINBITS" = "0" ]; then
    echo "  NOTE: min_cbm_bits=0 and this driver accepts the mask 0, which"
    echo "        allocates no L3 at all. Any capacity sweep must floor the"
    echo "        mask at one way; see gapbs/GAPBS_CAT_SENSITIVITY_RUN_DECISIONS.md."
fi
if [ -f /sys/fs/resctrl/info/MB/bandwidth_gran ]; then
    echo "  MBA supported  : yes (gran=$(cat /sys/fs/resctrl/info/MB/bandwidth_gran)% min=$(cat /sys/fs/resctrl/info/MB/min_bandwidth)%)"
else
    echo "  MBA supported  : NO"
fi

echo "=== Step 6: write bergamo_system_state.txt ==="
OUT="$OUT_DIR/bergamo_system_state.txt"
{
    echo "# Bergamo system state ($([ "$VERIFY_ONLY" = 1 ] && echo "as-found, VERIFY_ONLY" || echo "frozen"))"
    echo "# Platform: AMD EPYC 9754 (Bergamo)"
    date --iso-8601=seconds
    echo ""; echo "## host"; hostname; echo -n "uptime: "; uptime
    echo ""; echo "## uname"; uname -r
    echo ""; echo "## cpu model"
    grep -m1 "model name" /proc/cpuinfo
    grep -m1 "microcode" /proc/cpuinfo
    grep -m1 "stepping" /proc/cpuinfo
    echo ""; echo "## freq"
    echo -n "scaling_driver cpu8: "; cat /sys/devices/system/cpu/cpu8/cpufreq/scaling_driver 2>/dev/null || echo N/A
    echo -n "governor cpu8: ";       cat /sys/devices/system/cpu/cpu8/cpufreq/scaling_governor 2>/dev/null || echo N/A
    echo -n "cpufreq boost: ";       cat /sys/devices/system/cpu/cpufreq/boost 2>/dev/null || echo N/A
    echo -n "scaling_cur_freq kHz cpu8: "; cat /sys/devices/system/cpu/cpu8/cpufreq/scaling_cur_freq 2>/dev/null || echo N/A
    echo ""; echo "## cache geometry (cpu8)"
    for i in 0 1 2 3; do
        d="/sys/devices/system/cpu/cpu8/cache/index$i"
        [ -d "$d" ] && echo "index$i level=$(cat "$d/level") type=$(cat "$d/type") size=$(cat "$d/size") ways=$(cat "$d/ways_of_associativity") id=$(cat "$d/id") shared=$(cat "$d/shared_cpu_list")"
    done
    echo ""; echo "## numa"; numactl --hardware
    echo ""; echo "## hugepages"
    for n in 0 1 2; do
        d="/sys/devices/system/node/node$n/hugepages/hugepages-2048kB"
        [ -d "$d" ] && printf "node%s nr/free: %s %s\n" "$n" "$(cat "$d/nr_hugepages")" "$(cat "$d/free_hugepages")"
    done
    echo ""; echo "## resctrl capabilities"
    echo -n "L3 CBM mask: ";  cat /sys/fs/resctrl/info/L3/cbm_mask 2>/dev/null || echo N/A
    echo -n "min_cbm_bits: "; cat /sys/fs/resctrl/info/L3/min_cbm_bits 2>/dev/null || echo N/A
    echo -n "num_closids: ";  cat /sys/fs/resctrl/info/L3/num_closids 2>/dev/null || echo N/A
    echo -n "sparse_masks: "; cat /sys/fs/resctrl/info/L3/sparse_masks 2>/dev/null || echo N/A
    echo -n "L3 domain count: "; grep -o "^ *L3:.*" /sys/fs/resctrl/schemata 2>/dev/null | tr ';' '\n' | wc -l
    echo ""; echo "## kernel knobs"
    echo -n "numa_balancing: ";      cat /proc/sys/kernel/numa_balancing 2>/dev/null || echo N/A
    echo -n "perf_event_paranoid: "; cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo N/A
    echo -n "THP enabled: ";         cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null || echo N/A
    echo ""; echo "## logged-in users (timing noise)"; who || true
} > "$OUT" 2>&1
[ "$VERIFY_ONLY" != "1" ] && chown -R "${SUDO_USER:-root}": "$OUT_DIR" 2>/dev/null || true
echo ""; echo "Done. State written to: $OUT"
