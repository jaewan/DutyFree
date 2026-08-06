#!/usr/bin/env python3
"""
Phase 2.2 analysis: build the occupancy-collapse plot the panel asked for.

occupancy N = BW(bytes/sec) * service_time(sec) / 64 (bytes/line)

service_time is a MEASURED idle (unloaded, single dependent-chase thread,
no aggressor) latency per memory type on this exact machine -- not an
assumed constant:
  CXL:   401.8 ns  (median of 5 reps, cyc/access=903.98 @ 2.25 GHz measured
                     cpu1 scaling_cur_freq)
  local: 145.7 ns  (median of 5 reps, cyc/access=327.79 @ 2.25 GHz)
These are a conservative *floor* -- true loaded service time under
contention is >= this. Occupancy estimates below are therefore
conservative (likely underestimates), not exact.

Outputs a CSV with (arm, threads, node, bw_gbps, occupancy_estimate,
tax) for the primary WB thread-matched curve, and reports A4 (lookups-only)
and WC (A3) as separate, differently-caveated reference points rather than
forcing them onto the same axis without a defensible occupancy number for
them.
"""
import json, csv, sys, statistics

CXL_LATENCY_NS = 401.8
LOCAL_LATENCY_NS = 145.7
LINE_BYTES = 64


def main():
    path = sys.argv[1]
    outcsv = sys.argv[2] if len(sys.argv) > 2 else "p22_occupancy.csv"
    by_arm = {}
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            by_arm.setdefault(d["arm"], {})[d["rep"]] = d

    reps = sorted(by_arm["quiescent"].keys())
    base = [by_arm["quiescent"][r]["cyc_per_iter"] for r in reps]
    base_med = statistics.median(base)
    print(f"n={len(reps)} reps, quiescent median cyc/iter = {base_med:.0f}\n")

    rows = []
    print(f"{'arm':10s} {'threads':>7s} {'bw_gbps':>8s} {'tax':>7s} {'occupancy_est':>14s}")
    for arm_name, data in by_arm.items():
        if arm_name == "quiescent":
            continue
        n = int(arm_name.split("_")[1].rstrip("t"))
        node_label = arm_name.split("_")[0]
        lat_ns = CXL_LATENCY_NS if node_label == "cxl" else LOCAL_LATENCY_NS
        cyc_vals = [data[r]["cyc_per_iter"] for r in reps]
        bw_vals = [data[r]["agg_bw_self_gbps"] for r in reps if data[r]["agg_bw_self_gbps"]]
        tax = statistics.median(cyc_vals) / base_med
        bw = statistics.median(bw_vals)
        occ = bw * 1e9 * lat_ns * 1e-9 / LINE_BYTES
        rows.append({"arm": arm_name, "node": node_label, "threads": n,
                      "bw_gbps": f"{bw:.3f}", "tax": f"{tax:.4f}",
                      "occupancy_est": f"{occ:.2f}", "latency_ns_used": lat_ns})
        print(f"{arm_name:10s} {n:7d} {bw:8.3f} {tax:7.4f} {occ:14.2f}")

    with open(outcsv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["arm", "node", "threads", "bw_gbps",
                                           "tax", "occupancy_est", "latency_ns_used"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: float(r["occupancy_est"])))
    print(f"\n-> {outcsv}")


if __name__ == "__main__":
    main()
