#!/usr/bin/env python3
"""
WSS sweep figure — reproduces paper Figure showing WB streaming tax vs WSS.

Reads:  data/emr_cxl8.csv, data/emr_local4.csv,
        data/spr_cxl8.csv, data/spr_local4.csv
Output: figures/wss_sweep.pdf  (and .png)

Usage:
  python3 analysis/plot_wss.py
  python3 analysis/plot_wss.py --data-dir data/ --out figures/
"""

import argparse
import csv
import statistics
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

DATA_FILES = {
    ("emr", "cxl8"):   "emr_cxl8.csv",
    ("emr", "local4"): "emr_local4.csv",
    ("spr", "cxl8"):   "spr_cxl8.csv",
    ("spr", "local4"): "spr_local4.csv",
}

PLATFORM_LABELS = {"emr": "EMR (320 MB LLC)", "spr": "SPR (60 MB LLC)"}
SWEEP_LABELS    = {"cxl8": "CXL-8", "local4": "Local-4"}
COLORS = {
    ("emr", "cxl8"):   "#d62728",
    ("emr", "local4"): "#ff7f0e",
    ("spr", "cxl8"):   "#1f77b4",
    ("spr", "local4"): "#aec7e8",
}
MARKERS = {("emr", "cxl8"): "o", ("emr", "local4"): "s",
           ("spr", "cxl8"): "^", ("spr", "local4"): "D"}


def load_csv(path: Path) -> list[dict]:
    rows = []
    with path.open() as f:
        for row in csv.DictReader(f):
            # skip duplicate header rows that may appear in concatenated files
            if row.get("condition") == "condition":
                continue
            rows.append(row)
    return rows


def compute_slowdowns(rows: list[dict]) -> dict[float, tuple[float, float, float]]:
    """Return {wss_frac: (median_slowdown, lo_95, hi_95)}."""
    by_wss: dict[float, dict[str, list[float]]] = {}
    for r in rows:
        frac = float(r["victim_wss_fraction_llc"])
        cond = r["condition"]
        cyc  = float(r["cycles_per_load"])
        by_wss.setdefault(frac, {"Q": [], "A": []})
        by_wss[frac][cond].append(cyc)

    result = {}
    for frac, d in sorted(by_wss.items()):
        q, a = d["Q"], d["A"]
        if not q or not a:
            continue
        qm = statistics.median(q)
        slowdowns = [x / qm for x in a]
        med = statistics.median(slowdowns)
        n = len(slowdowns)
        if n >= 2:
            se = statistics.stdev(slowdowns) / n**0.5
            lo, hi = med - 1.96 * se, med + 1.96 * se
        else:
            lo = hi = med
        result[frac] = (med, lo, hi)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data", type=Path)
    ap.add_argument("--out", default="figures", type=Path)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5), sharey=True)
    ax_emr, ax_spr = axes

    for (plat, sweep), fname in DATA_FILES.items():
        path = args.data_dir / fname
        if not path.exists():
            print(f"  [skip] {path} not found")
            continue

        rows = load_csv(path)
        sd   = compute_slowdowns(rows)
        if not sd:
            continue

        fracs = sorted(sd.keys())
        meds  = [sd[f][0] for f in fracs]
        lo    = [sd[f][1] for f in fracs]
        hi    = [sd[f][2] for f in fracs]
        yerr  = np.array([np.array(meds) - np.array(lo),
                          np.array(hi)   - np.array(meds)])

        ax = ax_emr if plat == "emr" else ax_spr
        label = SWEEP_LABELS[sweep]
        ax.errorbar(fracs, meds, yerr=yerr,
                    label=label, color=COLORS[(plat, sweep)],
                    marker=MARKERS[(plat, sweep)], markersize=6,
                    linewidth=1.5, capsize=3)

    for ax, plat in ((ax_emr, "emr"), (ax_spr, "spr")):
        ax.axhline(1.0, color="gray", linestyle="--", linewidth=0.8)
        ax.set_xlabel("WSS / LLC capacity", fontsize=11)
        ax.set_title(PLATFORM_LABELS[plat], fontsize=11)
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0))
        ax.legend(fontsize=9)
        ax.set_ylim(bottom=0.8)
        ax.grid(axis="y", alpha=0.3)

    ax_emr.set_ylabel("Slowdown (A / Q)", fontsize=11)
    fig.suptitle("WB Streaming Tax vs Working Set Size", fontsize=12)
    fig.tight_layout()

    for ext in ("pdf", "png"):
        out = args.out / f"wss_sweep.{ext}"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
