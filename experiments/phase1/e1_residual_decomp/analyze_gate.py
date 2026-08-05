#!/usr/bin/env python3
"""
Analyze E1 A0-A3 gate raw JSONL: median cyc/iter per arm, tax ratio vs A0
(paired bootstrap CI, matching reps by index since arms are rep-interleaved),
and MBM-vs-self-report bandwidth cross-check.

Usage: python3 analyze_gate.py <raw.jsonl>
"""
import json, sys, statistics, random

PAPER = {"A1_wb": 19.85, "A2_wb_cat": 6.92, "A3_wc": 1.02}
GATE_TOL = 0.15


def load(path):
    by_arm = {}
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            by_arm.setdefault(d["arm"], {})[d["rep"]] = d
    return by_arm


def bootstrap_ratio_ci(base_vals, arm_vals, B=20000, seed=0):
    rng = random.Random(seed)
    n = len(base_vals)
    ratios = []
    idxs = list(range(n))
    for _ in range(B):
        samp = [rng.choice(idxs) for _ in range(n)]
        b = statistics.median([base_vals[i] for i in samp])
        a = statistics.median([arm_vals[i] for i in samp])
        if b > 0:
            ratios.append(a / b)
    ratios.sort()
    lo = ratios[int(0.025 * len(ratios))]
    hi = ratios[int(0.975 * len(ratios))]
    return lo, hi


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/e1gate_raw_n12.jsonl"
    by_arm = load(path)
    reps = sorted(by_arm["A0_quiescent"].keys())
    n = len(reps)
    base_vals = [by_arm["A0_quiescent"][r]["cyc_per_iter"] for r in reps]
    base_med = statistics.median(base_vals)
    print(f"n={n} reps, A0 quiescent median cyc/iter = {base_med:.0f}")
    print()
    print(f"{'arm':14s} {'median tax':>11s} {'95% CI':>18s} {'paper':>7s} {'diff%':>7s} {'gate':>6s}  agg_bw(self) med  agg_bw(mbm) med")
    for arm in ["A1_wb", "A2_wb_cat", "A3_wc"]:
        arm_vals = [by_arm[arm][r]["cyc_per_iter"] for r in reps]
        tax_med = statistics.median(arm_vals) / base_med
        lo, hi = bootstrap_ratio_ci(base_vals, arm_vals)
        paper = PAPER[arm]
        diff = (tax_med - paper) / paper * 100
        gate = "PASS" if abs(diff) <= GATE_TOL * 100 else "FAIL"
        bw_self = [by_arm[arm][r]["agg_bw_self_gbps"] for r in reps]
        bw_mbm = [by_arm[arm][r]["agg_mbm_bw_gbps"] for r in reps]
        print(f"{arm:14s} {tax_med:11.3f} [{lo:6.3f},{hi:6.3f}] {paper:7.2f} {diff:+6.1f}% {gate:>6s}  "
              f"{statistics.median(bw_self):15.3f}  {statistics.median(bw_mbm):15.3f}")

    print()
    print("Victim LLC occupancy (mean bytes, median across reps):")
    for arm in ["A0_quiescent", "A1_wb", "A2_wb_cat", "A3_wc"]:
        occ = [by_arm[arm][r]["victim_llc_occ_bytes"]["mean"] for r in reps]
        print(f"  {arm:14s} median occ_mean = {statistics.median(occ):>14,.0f} bytes")

    print()
    print("L3 uncore PMU (median across reps, perf window = victim warmup+meas):")
    for arm in ["A0_quiescent", "A1_wb", "A2_wb_cat", "A3_wc"]:
        events = by_arm[arm][reps[0]]["l3_perf"].keys()
        line = f"  {arm:14s}"
        for ev in events:
            vals = [by_arm[arm][r]["l3_perf"].get(ev) for r in reps if by_arm[arm][r]["l3_perf"].get(ev) is not None]
            if vals:
                line += f"  {ev}={statistics.median(vals):,.0f}"
        print(line)


if __name__ == "__main__":
    main()
