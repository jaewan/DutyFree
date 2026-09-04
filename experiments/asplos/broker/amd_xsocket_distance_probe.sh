#!/usr/bin/env bash
# Diagnostic D1 of AMD_XSOCKET_PREREG_2026-09-04.md. Reported without a
# threshold.
#
# The ACPI SLIT advertises node 2 (CXL, no CPUs) at distance 60 from node 0 and
# 50 from node 1, so the other socket is nominally NEARER the CXL device than
# the socket the published arms streamed from. "Cross-socket" and "further from
# the CXL device" are therefore two variables this topology could bundle -- and
# on this machine they point in OPPOSITE directions. This probe measures the
# asymmetry the SLIT claims, so the outcome document can state which way it runs
# instead of inferring it from a firmware table.
#
# One thread, one core, same binary and same CXL-bound buffer as the arms.
set -u
A=/home/domin/tmp_dutyfree_exp/bin/aggressor
OUT=${1:?usage: amd_xsocket_distance_probe.sh <out.jsonl>}
[ -e "$OUT" ] && { echo "FAIL exists (A6.19)" >&2; exit 2; }

echo "{\"probe\":\"cxl_distance\",\"date_utc\":\"$(date -u)\",\"host\":\"$(hostname)\"," \
     "\"node_distances\":\"$(tr '\n' '|' < /sys/devices/system/node/node0/distance)$(tr '\n' '|' < /sys/devices/system/node/node1/distance)\"}" >> "$OUT"

for rep in 1 2 3; do
  for core in 1 9 129; do
    pkg=$(cat /sys/devices/system/cpu/cpu$core/topology/physical_package_id)
    bw=$("$A" -m wb_load -t 1 -c "$core" -N 2 -s 64 -d 5 2>/dev/null \
         | sed -n 's/^RESULT .*bw_gbps=\([0-9.]*\).*/\1/p')
    echo "{\"rep\":$rep,\"core\":$core,\"pkg\":$pkg,\"bw_gbps\":${bw:-null}}" >> "$OUT"
    echo "  rep$rep core=$core pkg=$pkg bw=${bw:-FAIL} GB/s"
  done
done
echo "wrote -> $OUT"
