#!/usr/bin/env python3
"""Generate figures/eval_frontiers.pdf for the ASPLOS'27 STREAMING paper.

Reads the committed datasets so the figure is reproducible from data rather
than being an opaque asset:

  panel (a)  data/gem5/r5_runs.jsonl              model, n=3 seeds
  panel (b)  data/silicon_e2e_hashjoin.jsonl      Xeon 8462Y+, n=5 reps

Conventions match analyze_silicon_e2e.py exactly -- MEDIANS, not means:
  recovery = (wb - x) / (wb - quiescent)   on victim cycles/load
  tenant   = throughput relative to unprotected WB; positive = faster

The two panels are never joined: silicon cannot encode the declared type and
gem5's CHI cannot execute the flushes flush-behind needs, so no line between
panels denotes a controlled comparison.

Usage: make_eval_frontiers.py [out.pdf]
"""
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    Path.home() / "STREAMING_Paper/ASPLOS27/figures/eval_frontiers.pdf"

# Paper typography: acmart sigplan, textwidth 505.89 pt = 7.000 in, body font
# Linux Libertine.  Matching the body face is what makes a figure look native.
BODY = "Linux Libertine O"
ACCENT = "#0072B2"      # colour-blind safe; the star marker carries greyscale
GREY = "#8a8a8a"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": [BODY, "Nimbus Roman", "DejaVu Serif"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8.5,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 6.8,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "pdf.fonttype": 42,          # embed TrueType, not Type 3
    "ps.fonttype": 42,
    "figure.dpi": 300,
    # NOT bbox="tight": that trims the page, so \includegraphics[width=\textwidth]
    # then rescales the figure and every font with it (a 5.86in page stretched to
    # 7.0in prints 8pt labels at 9.6pt).  Emit exactly \textwidth so the mapping
    # is 1:1 and the declared point sizes are the printed point sizes.
    "savefig.bbox": None,
})


def med(rows, key):
    v = [r[key] for r in rows if r.get(key) is not None]
    return st.median(v) if v else None


def model_frontier():
    rs = [json.loads(l) for l in open(HERE / "data/gem5/r5_runs.jsonl")]
    g = defaultdict(list)
    for r in rs:
        g[re.sub(r"_s\d+$", "", r["run"])].append(r)
    q = med(g["r5_qui"], "cyc_per_load")
    w = med(g["r5_wb"], "cyc_per_load")
    tw = med(g["r5_wb"], "join_mtuples_per_s")
    def pt(a):
        v, t = med(g[a], "cyc_per_load"), med(g[a], "join_mtuples_per_s")
        return 100 * (w - v) / (w - q), 100 * (t / tw - 1)
    cat = [pt(a) for a in sorted(g) if a.startswith("r5_wm")]
    return cat, pt("r5_h2")


def silicon_frontier():
    rs = [json.loads(l) for l in open(HERE / "data/silicon_e2e_hashjoin.jsonl")]
    g = defaultdict(list)
    for r in rs:
        g[r["arm"]].append(r)
    q = med(g["qui"], "victim_cyc_per_load")
    w = med(g["wb"], "victim_cyc_per_load")
    tw = med(g["wb"], "join_mtuples_per_s")
    def pt(a):
        v, t = med(g[a], "victim_cyc_per_load"), med(g[a], "join_mtuples_per_s")
        return 100 * (w - v) / (w - q), 100 * (t / tw - 1)
    cat = [pt(f"cat{i:02d}") for i in range(1, 16)]
    fb = [pt(a) for a in ("fb64k", "fb256k", "fb1m")]
    return cat, fb, pt("nta")


def style(ax, title, ylabel=None):
    ax.set_title(title, pad=4)
    ax.set_xlabel("neighbour recovery (\\%)" if False else "neighbour recovery (%)")
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.axhline(0, color="0.55", lw=0.6, ls=(0, (4, 3)), zorder=1)
    ax.grid(True, lw=0.35, color="0.85", zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlim(-12, 102)
    ax.set_ylim(-46, 13)
    ax.set_xticks(range(0, 101, 25))


def main():
    mcat, mstream = model_frontier()
    scat, sfb, snta = silicon_frontier()

    # 7.000 in == 505.89 pt == acmart sigplan \textwidth for this paper
    fig, (axa, axb) = plt.subplots(1, 2, figsize=(7.0, 2.62),
                                   constrained_layout=True)
    fig.get_layout_engine().set(w_pad=0.02, h_pad=0.02, wspace=0.05)

    # ---- (a) modelled -----------------------------------------------------
    style(axa, "(a) modelled: same kernel, one platform",
          "tenant throughput vs unprotected WB (%)")
    x, y = zip(*mcat)
    axa.plot(x, y, "-o", color=GREY, lw=0.9, ms=2.6, mfc="white",
             mew=0.8, label="CAT, 12 mask widths", zorder=3)
    axa.plot(*mstream, marker="*", ms=11, color=ACCENT, ls="none",
             mec="black", mew=0.5, label="Streaming (H1\u2013H2)", zorder=5)
    # One annotation only: the point of the panel is the empty upper region.
    axa.text(56, 6.0, "no mask width reaches\nthis region", fontsize=6.6,
             color="0.3", ha="center", va="center", linespacing=1.25)
    axa.legend(loc="lower left", frameon=True, framealpha=0.95,
               edgecolor="0.8", borderpad=0.35, handletextpad=0.5)

    # ---- (b) silicon ------------------------------------------------------
    style(axb, "(b) silicon: mechanisms that ship")
    x, y = zip(*scat)
    axb.plot(x, y, "-o", color=GREY, lw=0.9, ms=2.6, mfc="white",
             mew=0.8, label="CAT, 15 mask widths", zorder=3)
    x, y = zip(*sfb)
    axb.plot(x, y, "-s", color="black", lw=1.1, ms=3.4,
             label="flush-behind", zorder=4)
    axb.plot(*snta, marker="^", ms=5, color="black", ls="none",
             mfc="white", mew=0.9, label="PREFETCHNTA", zorder=4)
    # Label the flush-behind endpoints in place: the story is that cost is flat
    # while recovery walks left, so the window labels ARE the axis.
    axb.annotate("1 MiB", sfb[2], textcoords="offset points", xytext=(-2, -9),
                 fontsize=6.2, color="0.15", ha="center")
    axb.annotate("64 KiB", sfb[0], textcoords="offset points", xytext=(3, -9),
                 fontsize=6.2, color="0.15", ha="center")
    axb.annotate("recovery ceiling \u2248 46%", xy=(sfb[0][0], sfb[0][1]),
                 xytext=(60, -8.5), fontsize=6.6, color="0.2",
                 ha="left", va="center",
                 arrowprops=dict(arrowstyle="->", lw=0.55, color="0.45",
                                 shrinkA=2, shrinkB=3))
    axb.annotate("91.4% recovery\ncosts 42%", xy=scat[0],
                 xytext=(88, -27), fontsize=6.6, color="0.2",
                 ha="center", va="center", linespacing=1.25,
                 arrowprops=dict(arrowstyle="->", lw=0.55, color="0.45",
                                 shrinkA=2, shrinkB=3))
    axb.annotate("wide masks: neighbour\nworse than unprotected",
                 xy=(-4.5, -2.4), xytext=(2, 10.2), fontsize=6.6,
                 color="0.3", ha="left", va="center", linespacing=1.25,
                 arrowprops=dict(arrowstyle="->", lw=0.55, color="0.45",
                                 shrinkA=2, shrinkB=3))
    axb.legend(loc="lower left", frameon=True, framealpha=0.95,
               edgecolor="0.8", borderpad=0.35, handletextpad=0.5)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    print(f"  wrote {OUT}")
    print(f"  (a) model    : Streaming R={mstream[0]:.2f}% tenant={mstream[1]:+.2f}%, "
          f"{len(mcat)} CAT widths")
    print(f"  (b) silicon  : {len(scat)} CAT widths, fb={[f'{r:.1f}%' for r,_ in sfb]}, "
          f"nta R={snta[0]:.1f}%")


if __name__ == "__main__":
    main()
