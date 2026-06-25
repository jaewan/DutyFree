#!/usr/bin/env python3
"""
CAT/MBA double-dissociation figure — reproduces paper mechanism-proof figure.

Reads:  data/catmba_s{2,3,4,5}_*.csv  (11 files)
Output: figures/cat_mba.pdf  (and .png)

Usage:
  python3 analysis/plot_cat_mba.py
  python3 analysis/plot_cat_mba.py --data-dir data/ --out figures/
"""

import argparse
import csv
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Ordered condition list for x-axis
CONDITIONS = [
    # (filename_stem,            x_label,              group)
    ("catmba_s2_quiescent",      "Quiescent",          "baseline"),
    ("catmba_s2_cxl8_baseline",  "Baseline",           "baseline"),
    ("catmba_s3_cat_full",       "CAT full",           "cat"),
    ("catmba_s3_cat_3ways",      "CAT 3-way",          "cat"),
    ("catmba_s3_cat_1way",       "CAT 1-way",          "cat"),
    ("catmba_s4_mba_100",        "MBA 100%",           "mba"),
    ("catmba_s4_mba_30",         "MBA 30%",            "mba"),
    ("catmba_s4_mba_20",         "MBA 20%",            "mba"),
    ("catmba_s4_mba_10",         "MBA 10%",            "mba"),
    ("catmba_s5_neg_l2fit",      "Neg: L2-fit",        "neg"),
    ("catmba_s5_neg_turnover",   "Neg: SF-only",       "neg"),
]

GROUP_COLORS = {
    "baseline": "#7f7f7f",
    "cat":      "#2ca02c",
    "mba":      "#d62728",
    "neg":      "#9467bd",
}
GROUP_LABELS = {
    "baseline": "Baseline",
    "cat":      "CAT (LLC partition)",
    "mba":      "MBA (BW throttle)",
    "neg":      "Negative controls",
}


def load_csv(path: Path) -> list[dict]:
    rows = []
    with path.open() as f:
        for row in csv.DictReader(f):
            if row.get("condition") == "condition":
                continue
            rows.append(row)
    return rows


def compute_slowdown(rows: list[dict]) -> tuple[float, float, float, float]:
    """Return (slowdown_median, lo_95, hi_95, agg_bw_mean)."""
    q = [float(r["cycles_per_load"]) for r in rows if r["condition"] == "Q"]
    a = [float(r["cycles_per_load"]) for r in rows if r["condition"] == "A"]
    bw = [float(r["agg_bw_gbps"])    for r in rows if r["condition"] == "A" and r.get("agg_bw_gbps")]
    if not q:
        return 1.0, 1.0, 1.0, 0.0
    qm = statistics.median(q)
    if not a:
        return 1.0, 1.0, 1.0, 0.0
    slowdowns = [x / qm for x in a]
    med = statistics.median(slowdowns)
    n   = len(slowdowns)
    se  = statistics.stdev(slowdowns) / n**0.5 if n > 1 else 0.0
    lo, hi = med - 1.96 * se, med + 1.96 * se
    agg_bw = statistics.mean(bw) if bw else 0.0
    return med, lo, hi, agg_bw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data", type=Path)
    ap.add_argument("--out", default="figures", type=Path)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    results = []
    for stem, xlabel, group in CONDITIONS:
        path = args.data_dir / f"{stem}.csv"
        if not path.exists():
            print(f"  [skip] {path} not found")
            results.append((xlabel, group, None, None, None, None))
            continue
        rows = load_csv(path)
        med, lo, hi, bw = compute_slowdown(rows)
        results.append((xlabel, group, med, lo, hi, bw))

    fig, ax = plt.subplots(figsize=(10, 4))

    xs     = np.arange(len(results))
    meds   = [r[2] if r[2] is not None else 0 for r in results]
    lo_err = [r[2] - r[3] if r[2] is not None else 0 for r in results]
    hi_err = [r[4] - r[2] if r[2] is not None else 0 for r in results]
    colors = [GROUP_COLORS[r[1]] for r in results]
    xlabels = [r[0] for r in results]

    bars = ax.bar(xs, meds, color=colors, alpha=0.85, edgecolor="black", linewidth=0.5)
    ax.errorbar(xs, meds,
                yerr=[lo_err, hi_err],
                fmt="none", color="black", capsize=4, linewidth=1.2)

    ax.axhline(1.0, color="black", linestyle="--", linewidth=0.8, label="No slowdown (1×)")
    ax.set_xticks(xs)
    ax.set_xticklabels(xlabels, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Slowdown vs quiescent (A / Q)", fontsize=11)
    ax.set_title("LLC Mechanism Proof: CAT/MBA Double Dissociation (EMR, 53% WSS)", fontsize=11)
    ax.set_ylim(bottom=0.5)
    ax.grid(axis="y", alpha=0.3)

    # Group shading
    group_spans = {}
    for i, (_, group, *_) in enumerate(results):
        s, e = group_spans.get(group, (i, i))
        group_spans[group] = (min(s, i), max(e, i))

    for group, (s, e) in group_spans.items():
        ax.axvspan(s - 0.5, e + 0.5,
                   color=GROUP_COLORS[group], alpha=0.06, zorder=0)

    legend_patches = [
        mpatches.Patch(color=GROUP_COLORS[g], alpha=0.7, label=GROUP_LABELS[g])
        for g in ["baseline", "cat", "mba", "neg"]
    ]
    ax.legend(handles=legend_patches, fontsize=9, loc="upper right")

    # Annotate bandwidth for MBA conditions
    for i, (_, group, med, *_, bw) in enumerate(results):
        if group == "mba" and bw and bw > 0:
            ax.text(i, (med or 0) + 0.04, f"{bw:.0f}\nGB/s",
                    ha="center", va="bottom", fontsize=7, color="darkred")

    fig.tight_layout()

    for ext in ("pdf", "png"):
        out = args.out / f"cat_mba.{ext}"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
