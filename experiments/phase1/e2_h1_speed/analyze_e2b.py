#!/usr/bin/env python3
import json, sys, statistics, random

def boot_ci(base_vals, arm_vals, B=20000, seed=0):
    rng = random.Random(seed)
    n = len(base_vals)
    idxs = list(range(n))
    ratios = []
    for _ in range(B):
        samp = [rng.choice(idxs) for _ in range(n)]
        b = statistics.median([base_vals[i] for i in samp])
        a = statistics.median([arm_vals[i] for i in samp])
        if b > 0:
            ratios.append(a / b)
    ratios.sort()
    return ratios[int(0.025 * len(ratios))], ratios[int(0.975 * len(ratios))]

def main():
    path = sys.argv[1]
    by_cfg = {}
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            by_cfg.setdefault(d["config"], {})[d["rep"]] = d
    reps = sorted(by_cfg["quiescent"].keys())
    base = [by_cfg["quiescent"][r]["victim_cycles_per_load"] for r in reps]
    base_med = statistics.median(base)
    print(f"n={len(reps)}  quiescent median cyc/load = {base_med:.2f}\n")
    print(f"{'config':10s} {'D (KB)':>8s} {'tax':>7s} {'95% CI':>16s} {'agg_bw':>8s} {'occ_mean(MB)':>13s} {'occ/D':>7s}")
    for name in ["d_32kb", "d_256kb", "d_2mb", "d_16mb", "d_64mb", "d_off"]:
        vals = [by_cfg[name][r]["victim_cycles_per_load"] for r in reps]
        tax = statistics.median(vals) / base_med
        lo, hi = boot_ci(base, vals)
        bw = statistics.median([by_cfg[name][r]["agg_bw_total_gbps"] for r in reps])
        occ = statistics.median([by_cfg[name][r]["occ_mean_bytes"] for r in reps])
        d_kb = by_cfg[name][reps[0]]["flush_distance_kb"]
        d_bytes_nominal = d_kb * 1024 * 8 if d_kb else None  # 8 threads
        ratio = (occ / d_bytes_nominal) if d_bytes_nominal else None
        print(f"{name:10s} {str(d_kb):>8s} {tax:7.3f} [{lo:6.3f},{hi:6.3f}] {bw:8.2f} {occ/1e6:13.2f} "
              f"{f'{ratio:.2f}' if ratio else '(off)':>7s}")

if __name__ == "__main__":
    main()
