#!/usr/bin/env python3
"""Aggregate the raw per-rep calibration_targets_raw_n12.csv (12 rows/config)
into the clean one-row-per-config deliverable, per the mission's
(platform, config, BW, latency, implied MLP) spec. Reports n, median, and
95% CI (bootstrap) for bw_gbps and implied_mlp."""
import csv, statistics, random, sys

def boot_ci(vals, B=20000, seed=0):
    rng = random.Random(seed)
    n = len(vals)
    meds = []
    for _ in range(B):
        samp = [vals[rng.randrange(n)] for _ in range(n)]
        meds.append(statistics.median(samp))
    meds.sort()
    return meds[int(0.025 * len(meds))], meds[int(0.975 * len(meds))]

def main():
    inpath = sys.argv[1]
    outpath = sys.argv[2]
    groups = {}
    with open(inpath) as f:
        for row in csv.DictReader(f):
            key = (row["platform"], row["leg"], row["config"], row["threads"], row["node"])
            groups.setdefault(key, []).append(row)

    out_rows = []
    for (platform, leg, config, threads, node), rows in groups.items():
        bws = [float(r["bw_gbps"]) for r in rows if r["bw_gbps"]]
        lat = float(rows[0]["latency_ns"])
        n = len(bws)
        bw_med = statistics.median(bws)
        lo, hi = boot_ci(bws) if n > 1 else (bw_med, bw_med)
        implied_mlp = bw_med * lat / 64.0  # GB/s * ns / (bytes/line) -> lines-in-flight
        out_rows.append({
            "platform": platform, "leg": leg, "config": config,
            "threads": threads, "node": node, "n": n,
            "bw_gbps_median": f"{bw_med:.3f}",
            "bw_gbps_ci_lo": f"{lo:.3f}", "bw_gbps_ci_hi": f"{hi:.3f}",
            "latency_ns": f"{lat:.2f}",
            "implied_mlp_lines": f"{implied_mlp:.2f}",
        })

    fields = ["platform", "leg", "config", "threads", "node", "n",
              "bw_gbps_median", "bw_gbps_ci_lo", "bw_gbps_ci_hi",
              "latency_ns", "implied_mlp_lines"]
    with open(outpath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)
    print(f"{len(out_rows)} config rows -> {outpath}")

if __name__ == "__main__":
    main()
