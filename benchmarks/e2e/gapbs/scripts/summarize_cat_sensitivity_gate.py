#!/usr/bin/env python3
"""Apply the pre-registered decision rule to the CAT capacity-sensitivity gate.

Rule (GAPBS_CAT_SENSITIVITY_PREREGISTRATION.md): select the smallest scale per
host whose minimum-way median runtime is at least 2x its same-scale/full-mask
median, with CoV <= 5% in both configurations. The measured population is the
final three trials of each invocation, pooled across invocations.
"""
import json, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ART = ROOT / "benchmarks/e2e/gapbs/artifacts"
RATIO_MIN, COV_MAX = 2.0, 0.05


def stats(vals):
    med = statistics.median(vals)
    cov = statistics.stdev(vals) / statistics.mean(vals) if len(vals) > 1 else 0.0
    return med, cov


def main():
    out = {}
    for path in sorted(ART.glob("cat_sensitivity_gate_*.jsonl")):
        host = path.stem.replace("cat_sensitivity_gate_", "")
        pool, invalid = {}, []
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if not r.get("valid"):
                invalid.append((r["scale"], r["mask_label"], r["invocation"]))
                continue
            key = (r["scale"], r["mask_label"])
            e = pool.setdefault(key, {"trials": [], "inv_medians": [],
                                      "effective_bytes": r["effective_bytes"],
                                      "mask": r["mask_installed"]})
            e["trials"] += r["trial_seconds_measured"]
            e["inv_medians"].append(statistics.median(r["trial_seconds_measured"]))
        scales = sorted({s for s, _ in pool})
        rows, selected = [], None
        for s in scales:
            f, m = pool.get((s, "full")), pool.get((s, "min"))
            if not (f and m):
                continue
            fmed, fcov = stats(f["trials"])
            mmed, mcov = stats(m["trials"])
            ratio = mmed / fmed
            ok = ratio >= RATIO_MIN and fcov <= COV_MAX and mcov <= COV_MAX
            rows.append({"scale": s, "full_mib": f["effective_bytes"] >> 20,
                         "min_mib": m["effective_bytes"] >> 20,
                         "full_median_s": round(fmed, 6), "full_cov": round(fcov, 5),
                         "min_median_s": round(mmed, 6), "min_cov": round(mcov, 5),
                         "ratio": round(ratio, 4), "n_full": len(f["trials"]),
                         "n_min": len(m["trials"]), "passes": ok})
            if ok and selected is None:
                selected = s
        out[host] = {"rows": rows, "selected_scale": selected,
                     "invalid_records": invalid,
                     "rule": {"ratio_min": RATIO_MIN, "cov_max": COV_MAX}}
        print(f"\n=== {host} ===  selected: "
              f"{'g%d' % selected if selected else 'NONE (fails magnitude pre-gate)'}")
        print(f"{'scale':>5} {'full MiB':>8} {'min MiB':>7} {'full med':>10} "
              f"{'CoV':>7} {'min med':>10} {'CoV':>7} {'ratio':>7}  pass")
        for r in rows:
            print(f"{r['scale']:>5} {r['full_mib']:>8} {r['min_mib']:>7} "
                  f"{r['full_median_s']:>10.6f} {r['full_cov']*100:>6.3f}% "
                  f"{r['min_median_s']:>10.6f} {r['min_cov']*100:>6.3f}% "
                  f"{r['ratio']:>7.3f}  {'PASS' if r['passes'] else 'fail'}")
        if invalid:
            print(f"  invalid records retained: {invalid}")
    (ART / "cat_sensitivity_gate_summary.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n")
    if not out:
        print("no gate records found", file=sys.stderr)


if __name__ == "__main__":
    main()
