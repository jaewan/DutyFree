#!/usr/bin/env bash
# CAT/MBA double-dissociation driver for EMR (Intel Xeon 8592+, 320 MB LLC).
#
# Run as root from the benchmarks/ directory:
#   sudo bash experiments/cat_mba_driver.sh
#
# Requires:
#   - Binaries built:  make -C bench/
#   - System frozen:   sudo bash setup/emr_freeze.sh
#   - resctrl mounted: checked below
#
# Runs all 11 conditions (~2 hours total):
#   Step 2: baseline tax (quiescent + CXL-8)
#   Step 3: CAT sweep (3 disjoint way counts)
#   Step 4: MBA sweep (4 throttle levels)
#   Step 5: negative controls (L2-fit victim, forced-turnover SF aggressor)
#
# Results written to:  experiments/results/<cond_name>/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BENCH_DIR"

PYBIN="${PYBIN:-python3}"
CAT_MBA_PY="experiments/cat_mba.py"
OUTBASE="$SCRIPT_DIR/results"
WSS_MB=170          # 53% of 320 MB EMR LLC
WSS_L2_MB=2         # fits in L2 (1 MB/core on 8592+)

mkdir -p "$OUTBASE"

# ── prerequisite checks ───────────────────────────────────────────────────────

if ! mount | grep -q resctrl; then
    echo "ERROR: resctrl not mounted. Run: sudo bash setup/emr_freeze.sh" >&2
    exit 1
fi

if [ ! -f bench/victim/pointer_chase_nocap ]; then
    echo "ERROR: binaries not built. Run: make -C bench/" >&2
    exit 1
fi

# ── read CAT/MBA capabilities ─────────────────────────────────────────────────

CBM_HEX=$(cat /sys/fs/resctrl/info/L3/cbm_mask)
N_WAYS=$("$PYBIN" -c "print(bin(int('$CBM_HEX', 16)).count('1'))")
ALL_MASK="$CBM_HEX"
MBA_AVAIL=0
[ -f /sys/fs/resctrl/info/MB/bandwidth_gran ] && MBA_AVAIL=1

echo "=== CAT: CBM=$CBM_HEX  n_ways=$N_WAYS  MBA=$MBA_AVAIL ==="

# Contiguous bitmasks — aggressor uses LOW bits, victim uses HIGH bits (disjoint)
AGGR3_MASK=$(  "$PYBIN" -c "print(hex((1<<3)-1))")
VICTIM17_MASK=$("$PYBIN" -c "m=int('$CBM_HEX',16); print(hex(m & ~((1<<3)-1)))")
AGGR1_MASK=$(  "$PYBIN" -c "print(hex((1<<1)-1))")
VICTIM19_MASK=$("$PYBIN" -c "m=int('$CBM_HEX',16); print(hex(m & ~((1<<1)-1)))")

echo "  cat_3: aggr=$AGGR3_MASK  victim=$VICTIM17_MASK"
echo "  cat_1: aggr=$AGGR1_MASK  victim=$VICTIM19_MASK"
echo ""

# ── resctrl helpers ───────────────────────────────────────────────────────────

N_SOCKETS=$(awk '/^L3:/{gsub(/[^;]/,""); print length+1; exit}' /sys/fs/resctrl/schemata)
[ -z "$N_SOCKETS" ] || [ "$N_SOCKETS" -lt 1 ] && N_SOCKETS=2

make_l3_schema() {
    local s0="$1" s1="${2:-$ALL_MASK}"
    if [ "$N_SOCKETS" -ge 2 ]; then echo "L3:0=$s0;1=$s1"
    else echo "L3:0=$s0"; fi
}

make_mb_schema() {
    local p0="$1" p1="${2:-100}"
    if [ "$N_SOCKETS" -ge 2 ]; then echo "MB:0=$p0;1=$p1"
    else echo "MB:0=$p0"; fi
}

setup_resctrl() {
    local v_mask="$1" a_mask="$2" a_mb="${3:-100}"
    [ -d /sys/fs/resctrl/victim ]    || mkdir /sys/fs/resctrl/victim
    [ -d /sys/fs/resctrl/aggressor ] || mkdir /sys/fs/resctrl/aggressor
    echo 0   > /sys/fs/resctrl/victim/cpus_list
    echo 1-8 > /sys/fs/resctrl/aggressor/cpus_list
    { make_l3_schema "$v_mask"; [ "$MBA_AVAIL" = "1" ] && make_mb_schema "100"; } \
        > /sys/fs/resctrl/victim/schemata
    { make_l3_schema "$a_mask"; [ "$MBA_AVAIL" = "1" ] && make_mb_schema "$a_mb"; } \
        > /sys/fs/resctrl/aggressor/schemata
    echo "  resctrl: victim=$v_mask  aggr=$a_mask  aggr_mb=${a_mb}%"
}

teardown_resctrl() {
    if [ -d /sys/fs/resctrl/victim ]; then
        echo "" > /sys/fs/resctrl/victim/cpus_list    2>/dev/null || true
        rmdir     /sys/fs/resctrl/victim              2>/dev/null || true
    fi
    if [ -d /sys/fs/resctrl/aggressor ]; then
        echo "" > /sys/fs/resctrl/aggressor/cpus_list 2>/dev/null || true
        rmdir     /sys/fs/resctrl/aggressor           2>/dev/null || true
    fi
}

run() {
    local cond="$1" label="$2" wss="$3" aggr="$4"
    echo ""
    echo "======================================================================"
    echo "CONDITION: $cond  WSS=${wss}MB  aggr=${aggr}"
    echo "======================================================================"
    runuser -u "${SUDO_USER:-domin}" -- "$PYBIN" "$CAT_MBA_PY" \
        "$cond" "$label" "$wss" "$aggr"
}

trap 'teardown_resctrl; chown -R "${SUDO_USER:-domin}":"${SUDO_USER:-domin}" "$OUTBASE" 2>/dev/null || true' EXIT

# ==============================================================================
# Step 2 — Baseline tax
# ==============================================================================
echo ""
echo "====== STEP 2: baseline tax ======"
teardown_resctrl
run "s2_quiescent"     "Step2 quiescent (no aggressor)"              "$WSS_MB" "none"
run "s2_cxl8_baseline" "Step2 CXL-8 baseline (all ways shared)"      "$WSS_MB" "cxl8"

# ==============================================================================
# Step 3 — CAT sweep
# ==============================================================================
echo ""
echo "====== STEP 3: CAT sweep ======"

setup_resctrl "$ALL_MASK"     "$ALL_MASK"     100
run "s3_cat_full"   "Step3 CAT full (both groups all ways)"           "$WSS_MB" "cxl8"

setup_resctrl "$VICTIM17_MASK" "$AGGR3_MASK"  100
run "s3_cat_3ways" "Step3 CAT 3 disjoint aggressor ways (victim=17)" "$WSS_MB" "cxl8"

setup_resctrl "$VICTIM19_MASK" "$AGGR1_MASK"  100
run "s3_cat_1way"  "Step3 CAT 1 disjoint aggressor way (victim=19)"  "$WSS_MB" "cxl8"

# ==============================================================================
# Step 4 — MBA sweep
# ==============================================================================
echo ""
echo "====== STEP 4: MBA sweep ======"

if [ "$MBA_AVAIL" = "1" ]; then
    setup_resctrl "$ALL_MASK" "$ALL_MASK" 100
    run "s4_mba_100" "Step4 MBA 100% (no throttle)"  "$WSS_MB" "cxl8"

    setup_resctrl "$ALL_MASK" "$ALL_MASK" 30
    run "s4_mba_30"  "Step4 MBA 30% aggressor BW"    "$WSS_MB" "cxl8"

    setup_resctrl "$ALL_MASK" "$ALL_MASK" 20
    run "s4_mba_20"  "Step4 MBA 20% aggressor BW"    "$WSS_MB" "cxl8"

    setup_resctrl "$ALL_MASK" "$ALL_MASK" 10
    run "s4_mba_10"  "Step4 MBA 10% (minimum)"       "$WSS_MB" "cxl8"
else
    echo "  [SKIP] MBA not supported — skipping Step 4"
fi

# ==============================================================================
# Step 5 — Negative controls
# ==============================================================================
echo ""
echo "====== STEP 5: negative controls ======"
teardown_resctrl

run "s5_neg_l2fit"    "Step5 neg-ctrl: L2-fit victim (WSS=2MB, CXL-8 aggressor)"    "$WSS_L2_MB" "cxl8"
run "s5_neg_turnover" "Step5 neg-ctrl: forced-turnover (SF pressure, no eviction)"  "$WSS_MB"    "turnover8"

# ==============================================================================
# Done
# ==============================================================================
teardown_resctrl
chown -R "${SUDO_USER:-domin}":"${SUDO_USER:-domin}" "$OUTBASE" 2>/dev/null || true

echo ""
echo "======================================================================"
echo "All conditions complete.  Results in: $OUTBASE"
echo ""
for d in "$OUTBASE"/s{2,3,4,5}_*/; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    rpt="$d/${name}_report.md"
    if [ -f "$rpt" ]; then
        echo "  $name"
        grep -E "^(Q |A |Slowdown)" "$rpt" | sed 's/^/    /' || true
    fi
done
echo ""
echo "Run analysis scripts to reproduce paper figures:"
echo "  python3 analysis/plot_wss.py"
echo "  python3 analysis/plot_cat_mba.py"
