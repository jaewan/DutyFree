#!/usr/bin/env python3
import json, sys, statistics, random


def main():
    path = sys.argv[1]
    by_t = {}
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            by_t.setdefault(d["nthreads"], {})[d["rep"]] = d
    reps = sorted(by_t[0].keys())
    base_vals = [by_t[0][r]["cyc_per_iter"] for r in reps]
    base_med = statistics.median(base_vals)
    print(f"n={len(reps)} reps, t=0 quiescent median cyc/iter = {base_med:.0f}\n")
    print(f"{'threads':>7s} {'median tax':>11s} {'95% CI':>18s} {'agg_bw(self)':>13s} {'agg_bw(mbm)':>13s} {'tax/GBps':>9s} {'occ_mean':>14s}")
    rng = random.Random(0)
    prev_tax = 1.0
    for t in sorted(k for k in by_t if k != 0):
        vals = [by_t[t][r]["cyc_per_iter"] for r in reps]
        tax = statistics.median(vals) / base_med
        idxs = list(range(len(reps)))
        ratios = []
        for _ in range(20000):
            samp = [rng.choice(idxs) for _ in range(len(reps))]
            b = statistics.median([base_vals[i] for i in samp])
            a = statistics.median([vals[i] for i in samp])
            if b > 0:
                ratios.append(a / b)
        ratios.sort()
        lo, hi = ratios[int(0.025 * len(ratios))], ratios[int(0.975 * len(ratios))]
        bw_self = statistics.median([by_t[t][r]["agg_bw_self_gbps"] for r in reps])
        bw_mbm = statistics.median([by_t[t][r]["agg_mbm_bw_gbps"] for r in reps])
        occ = statistics.median([by_t[t][r]["victim_llc_occ_bytes"]["mean"] for r in reps])
        print(f"{t:7d} {tax:11.3f} [{lo:6.3f},{hi:6.3f}] {bw_self:13.3f} {bw_mbm:13.3f} {tax/bw_mbm:9.3f} {occ:14,.0f}")


if __name__ == "__main__":
    main()
