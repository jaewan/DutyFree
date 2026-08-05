#!/usr/bin/env python3
import json, sys, statistics, random


def load(path):
    by_arm = {}
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            by_arm.setdefault(d["arm"], {})[d["rep"]] = d
    return by_arm


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
    by_arm = load(path)
    reps = sorted(by_arm["A0_quiescent"].keys())
    base_vals = [by_arm["A0_quiescent"][r]["cyc_per_iter"] for r in reps]
    base_med = statistics.median(base_vals)
    print(f"n={len(reps)} reps, A0 quiescent median cyc/iter = {base_med:.0f}\n")
    print(f"{'arm':14s} {'median tax':>11s} {'95% CI':>18s}  {'agg_bw(self)':>13s} {'agg_bw(mbm)':>13s}  {'occ_mean':>14s}")
    for arm in [a for a in by_arm if a != "A0_quiescent"]:
        vals = [by_arm[arm][r]["cyc_per_iter"] for r in reps]
        tax = statistics.median(vals) / base_med
        lo, hi = boot_ci(base_vals, vals)
        bw_self = [by_arm[arm][r]["agg_bw_self_gbps"] for r in reps if by_arm[arm][r]["agg_bw_self_gbps"] is not None]
        bw_mbm = [by_arm[arm][r]["agg_mbm_bw_gbps"] for r in reps if by_arm[arm][r]["agg_mbm_bw_gbps"] is not None]
        occ = [by_arm[arm][r]["victim_llc_occ_bytes"]["mean"] for r in reps]
        bw_self_s = f"{statistics.median(bw_self):.3f}" if bw_self else "n/a"
        bw_mbm_s = f"{statistics.median(bw_mbm):.4f}" if bw_mbm else "n/a"
        print(f"{arm:14s} {tax:11.3f} [{lo:6.3f},{hi:6.3f}]  {bw_self_s:>13s} {bw_mbm_s:>13s}  {statistics.median(occ):14,.0f}")
    print()
    occ_q = statistics.median([by_arm['A0_quiescent'][r]['victim_llc_occ_bytes']['mean'] for r in reps])
    print(f"A0_quiescent    occ_mean median = {occ_q:,.0f}")


if __name__ == "__main__":
    main()
