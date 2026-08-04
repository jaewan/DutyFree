#!/usr/bin/env bash
# resctrl/CAT setup helpers for the CLOS-split experiment (configs B and C).
#
# CAT here is CPU-based (writes to <group>/cpus_list), not task-based: a CPU is
# assigned to a CLOS regardless of which process runs there. This matches how the
# benchmark pins threads (sched_setaffinity to a single CPU), so once a CPU is
# assigned to a CLOS, whatever thread runs on it inherits that CLOS's L3 mask for
# the whole run -- no need to track PIDs across --reps.
#
# All compute CPUs used by this benchmark (32-47) sit in resctrl L3 domain 0
# (confirmed via /sys/devices/system/cpu/cpu*/cache/index3/id -> mon_L3_00).
# Domain 1 (mon_L3_00's sibling, the other socket) must always keep the FULL mask
# in schemata -- restricting it would be a silent no-op since no thread runs
# there, and could manufacture a false null result.
#
# Usage (must run as root):
#   sudo bash resctrl_clos.sh setup_b <ways> <all_cpus>
#   sudo bash resctrl_clos.sh setup_c <scan_ways> <scan_cpus> <probe_cpus>
#   sudo bash resctrl_clos.sh teardown
#   sudo bash resctrl_clos.sh verify
set -euo pipefail

RESCTRL=/sys/fs/resctrl
FULL_MASK=$(cat "$RESCTRL/info/L3/cbm_mask")   # fffff on this host: 20 ways, domain 0 and 1

require_root() {
    if [ "$(id -u)" != "0" ]; then
        echo "ERROR: must run as root (sudo)" >&2
        exit 1
    fi
}

# Sanity: every cpu in $1 (a resctrl cpu-list string like 32-47) must resolve to
# L3 domain 0 via /sys/devices/system/cpu/cpuN/cache/index3/id. If any CPU maps to
# a different domain, refuse to proceed -- writing the mask to the wrong domain
# index would restrict nothing real and silently pass.
assert_domain0() {
    local list="$1"
    python3 - "$list" <<'PY'
import sys
spec = sys.argv[1]
cpus = []
for tok in spec.split(","):
    if "-" in tok:
        a, b = tok.split("-")
        cpus.extend(range(int(a), int(b) + 1))
    elif tok:
        cpus.append(int(tok))
bad = []
for c in cpus:
    with open(f"/sys/devices/system/cpu/cpu{c}/cache/index3/id") as f:
        dom = int(f.read().strip())
    if dom != 0:
        bad.append((c, dom))
if bad:
    print(f"FATAL: cpus not in L3 domain 0: {bad}", file=sys.stderr)
    sys.exit(1)
print(f"OK: all cpus in {spec} are L3 domain 0 ({len(cpus)} cpus)")
PY
}

teardown() {
    for g in clos_b clos_c_scan clos_c_probe; do
        if [ -d "$RESCTRL/$g" ]; then
            echo "" > "$RESCTRL/$g/cpus_list" 2>/dev/null || true
            rmdir "$RESCTRL/$g" 2>/dev/null || true
        fi
    done
}

setup_b() {
    local ways="$1" all_cpus="$2"
    require_root
    assert_domain0 "$all_cpus"
    teardown
    mkdir "$RESCTRL/clos_b"
    echo "$all_cpus" > "$RESCTRL/clos_b/cpus_list"
    local mask
    mask=$(python3 -c "print(hex((1<<$ways)-1))")
    echo "L3:0=$mask;1=$FULL_MASK" > "$RESCTRL/clos_b/schemata"
    echo "clos_b: cpus=$all_cpus ways=$ways mask=$mask (domain 1 left full: $FULL_MASK)"
}

setup_c() {
    local scan_ways="$1" scan_cpus="$2" probe_cpus="$3"
    require_root
    assert_domain0 "$scan_cpus"
    assert_domain0 "$probe_cpus"
    teardown
    mkdir "$RESCTRL/clos_c_scan"
    mkdir "$RESCTRL/clos_c_probe"
    echo "$scan_cpus" > "$RESCTRL/clos_c_scan/cpus_list"
    echo "$probe_cpus" > "$RESCTRL/clos_c_probe/cpus_list"
    local scan_mask probe_mask
    scan_mask=$(python3 -c "print(hex((1<<$scan_ways)-1))")
    probe_mask=$(python3 -c "m=int('$FULL_MASK',16); print(hex(m & ~((1<<$scan_ways)-1)))")
    echo "L3:0=$scan_mask;1=$FULL_MASK" > "$RESCTRL/clos_c_scan/schemata"
    echo "L3:0=$probe_mask;1=$FULL_MASK" > "$RESCTRL/clos_c_probe/schemata"
    echo "clos_c_scan: cpus=$scan_cpus ways=$scan_ways mask=$scan_mask"
    echo "clos_c_probe: cpus=$probe_cpus ways=$((20 - scan_ways)) mask=$probe_mask"
}

verify() {
    echo "=== schemata ==="
    for g in clos_b clos_c_scan clos_c_probe; do
        if [ -d "$RESCTRL/$g" ]; then
            echo "-- $g --"
            cat "$RESCTRL/$g/schemata"
            echo "cpus_list: $(cat "$RESCTRL/$g/cpus_list")"
        fi
    done
    echo "=== mon_data domain0 occupancy (bytes) ==="
    for g in clos_b clos_c_scan clos_c_probe; do
        f="$RESCTRL/$g/mon_data/mon_L3_00/llc_occupancy"
        if [ -f "$f" ]; then
            echo "$g: $(cat "$f")"
        fi
    done
}

cmd="${1:-}"
case "$cmd" in
    setup_b) setup_b "$2" "$3" ;;
    setup_c) setup_c "$2" "$3" "$4" ;;
    teardown) require_root; teardown ;;
    verify) verify ;;
    *)
        echo "usage: $0 {setup_b <ways> <all_cpus> | setup_c <scan_ways> <scan_cpus> <probe_cpus> | teardown | verify}" >&2
        exit 2
        ;;
esac
