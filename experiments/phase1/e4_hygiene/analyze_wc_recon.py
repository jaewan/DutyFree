#!/usr/bin/env python3
import json, sys, statistics, random

def boot_ci(vals, B=20000, seed=0):
    rng = random.Random(seed)
    n = len(vals)
    idxs = list(range(n))
    meds = []
    for _ in range(B):
        samp = [vals[rng.choice(idxs)] for _ in range(n)]
        meds.append(statistics.median(samp))
    meds.sort()
    return meds[int(0.025 * len(meds))], meds[int(0.975 * len(meds))]

def main():
    path = sys.argv[1]
    by_cfg = {}
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            by_cfg.setdefault(d["config"], []).append(d)
    print(f"{'config':14s} {'n':>3s} {'bw_self median':>15s} {'95% CI':>18s} {'bw_mbm median':>14s} {'per_core(self)':>15s}")
    for cfg, recs in by_cfg.items():
        bw_self = [r["agg_bw_self_gbps"] for r in recs]
        bw_mbm = [r["agg_mbm_bw_gbps"] for r in recs]
        per_core = [r["per_core_gbps_self"] for r in recs]
        med = statistics.median(bw_self)
        lo, hi = boot_ci(bw_self)
        print(f"{cfg:14s} {len(recs):3d} {med:15.3f} [{lo:6.3f},{hi:6.3f}] {statistics.median(bw_mbm):14.3f} {statistics.median(per_core):15.3f}")

if __name__ == "__main__":
    main()
