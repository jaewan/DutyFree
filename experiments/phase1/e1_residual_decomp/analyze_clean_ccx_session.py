#!/usr/bin/env python3
"""Analyze the clean-CCX co-measured session against the three
pre-registered predictions in PHASE2_CLEAN_CCX_PREREGISTRATION.md."""
import json, random, statistics, sys
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/clean_ccx1_n12.jsonl"

byarm = defaultdict(dict)
for line in open(path):
    rec = json.loads(line)
    byarm[rec["arm"]][rec["rep"]] = rec

q_reps = sorted(byarm["quiescent"])
qvals = [byarm["quiescent"][r]["cyc_per_iter"] for r in q_reps]
qmed = statistics.median(qvals)

random.seed(20260809)


def bootstrap_tax(arm):
    reps = sorted(byarm[arm])
    avals = [byarm[arm][r]["cyc_per_iter"] for r in reps]
    pairs = list(zip(qvals, avals))
    amed = statistics.median(avals)
    boot = []
    for _ in range(10000):
        sample = [random.choice(pairs) for _ in range(len(pairs))]
        qm = statistics.median([p[0] for p in sample])
        am = statistics.median([p[1] for p in sample])
        boot.append(am / qm)
    boot.sort()
    return amed / qmed, boot[250], boot[9750]


print(f"quiescent median: {qmed:.0f}  (n={len(qvals)})")
print()
print(f"{'arm':14s} {'tax':>8s} {'95% CI':>18s} {'agg_bw_self':>12s} {'agg_bw_mbm':>11s} {'occ_MiB':>9s}")
for arm in ["wb", "wb_cat", "wc", "flush_d256kb", "t1", "t2", "t3"]:
    if arm not in byarm:
        continue
    tax, lo, hi = bootstrap_tax(arm)
    reps = sorted(byarm[arm])
    bw_self = [byarm[arm][r]["agg_bw_self_gbps"] for r in reps if byarm[arm][r]["agg_bw_self_gbps"]]
    bw_mbm = [byarm[arm][r]["agg_mbm_bw_gbps"] for r in reps if byarm[arm][r]["agg_mbm_bw_gbps"]]
    occ = [byarm[arm][r]["occ_mean_bytes"] for r in reps if byarm[arm][r]["occ_mean_bytes"]]
    bw_self_m = statistics.median(bw_self) if bw_self else None
    bw_mbm_m = statistics.median(bw_mbm) if bw_mbm else None
    occ_m = statistics.median(occ) / 1e6 if occ else None
    print(f"{arm:14s} {tax:8.4f} [{lo:.4f},{hi:.4f}] "
          f"{bw_self_m if bw_self_m else 0:12.2f} {bw_mbm_m if bw_mbm_m else 0:11.2f} "
          f"{occ_m if occ_m else 0:9.2f}")

print()
print("=== Predictions check ===")
wbcat_tax = bootstrap_tax("wb_cat")[0]
flush_tax = bootstrap_tax("flush_d256kb")[0]
wc_tax = bootstrap_tax("wc")[0]
wb_tax = bootstrap_tax("wb")[0]
t2_tax = bootstrap_tax("t2")[0]
t3_tax = bootstrap_tax("t3")[0]
t2_bw = statistics.median([byarm["t2"][r]["agg_bw_self_gbps"] for r in sorted(byarm["t2"])])
t3_bw = statistics.median([byarm["t3"][r]["agg_bw_self_gbps"] for r in sorted(byarm["t3"])])

print(f"1. flush-behind ({flush_tax:.3f}) vs CAT invariant band (~9.66-10.03x): "
      f"{'CONFIRMED' if 9.0 <= flush_tax <= 11.0 else 'FALSIFIED -- flush-behind is NOT in the same band'}")
print(f"2. WC parity ({wc_tax:.3f}): {'CONFIRMED' if 0.9 <= wc_tax <= 1.1 else 'FALSIFIED'}")
print(f"3. WB ceiling on CCX1 ({wb_tax:.3f}) vs CCX0's 20.8x: "
      f"{'CONFIRMED (CCX1-scale, ~13.4x)' if wb_tax < 16 else 'unexpected'}")
print(f"   knee shape: t2 bw={t2_bw:.2f} GB/s, t3 bw={t3_bw:.2f} GB/s, "
      f"t2/t3 bw ratio={t2_bw/t3_bw:.3f} (paper's knee: ~0.98)")
