#!/usr/bin/env python3
"""Generate figures/recovery_curve.pdf for the ASPLOS'27 STREAMING paper.

Answers the question a reviewer asks first about H2: why does it recover 89% of
the neighbour's charge in one experiment and 22% in another?  Because H2 can
only decline fills belonging to the declared range.  Whatever charge the
tenant's own reused state imposes was never the type's to remove -- and as that
state grows, H2's share of the contested capacity falls with it.

Reads committed archives only (no /tmp), all n=3 seeds:

  panels (a),(b)  data/gem5/{kn,kb}_runs.jsonl   fused tenant, 7 table sizes
                  data/gem5/fh_runs.jsonl        the shared quiescent arm
  panel  (c)      the same, plus
                  data/gem5/r5_runs.jsonl        complete join -- HELD OUT

Definitions, matching analyze_h2h_fused.py exactly (means over seeds):
  tax       = victim cyc/access / quiescent cyc/access
  recovery  = (tax_wb - tax_arm) / (tax_wb - 1)
  tenant    = tenant_misses_per_kcyc relative to WB; positive = faster
  share     = (HNF allocations under WB - under H2) / under WB

The fused build predates the streamingHnfFillBypasses counter (it reads 0 in
those runs), so `share` is measured by differencing allocations rather than
from the bypass counter.  In r5, where both exist, differencing gives 32.3%
and the bypass counter 17.4%: differencing also captures the secondary fills
H2 removes (fewer evictions, fewer writebacks), which is the quantity the
victim actually experiences.  Stated in the caption.

Usage: make_recovery_curve.py [out.pdf]
"""
import json
import statistics as st
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else \
    Path.home() / "STREAMING_Paper/ASPLOS27/figures/recovery_curve.pdf"

BODY = "Linux Libertine O"
ACCENT = "#0072B2"      # STREAMING
CAT = "#D55E00"         # partitioning
GREY = "#8a8a8a"
HELD = "#009E73"        # the held-out instrument

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
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "figure.dpi": 300,
})

TABLES = ["2.0", "2.5", "3.0", "3.5", "4.0", "6.0", "8.0"]
LLC_MIB = 5.0


def load(name):
    p = HERE / "data/gem5" / name
    return [x for x in (json.loads(l) for l in open(p)) if x["completed"]]


def fused():
    rows = load("kn_runs.jsonl") + load("kb_runs.jsonl")
    fh = load("fh_runs.jsonl")
    qui = st.mean([x["cyc_per_access"] for x in fh if x["run"].startswith("fh_qui_")])
    out = []
    for tb in TABLES:
        sel = lambda a: [x for x in rows if f"_{a}_t{tb}_" in x["run"]]
        W, H, C = sel("wb"), sel("h2"), sel("cat4")
        assert len(W) == len(H) == len(C) == 3, (tb, len(W), len(H), len(C))
        v = lambda A: st.mean([x["cyc_per_access"] for x in A])
        al = lambda A: st.mean([sum(x["hnf_allocs_by_way"]) for x in A])
        tn = lambda A: st.mean([x["tenant_misses_per_kcyc"] for x in A])
        tw = v(W) / qui
        R = lambda A: 100 * (tw - v(A) / qui) / (tw - 1)
        # positive = the tenant is faster than unprotected WB
        thr = lambda A: 100 * (tn(A) / tn(W) - 1)
        out.append(dict(table=float(tb), realized=st.mean([x["realized_table_mb"] for x in H]),
                        wb_tax=tw, R_h2=R(H), R_cat=R(C),
                        t_h2=thr(H), t_cat=thr(C),
                        share=100 * (al(W) - al(H)) / al(W)))
    return out


def complete_join():
    """The held-out instrument: a different tenant, never used to place the line.

    r5's runner did not record realized_table_mb (it is None in the archive).
    The size is the pre-registered G0 gate, verified in
    COMPLETE_JOIN_OUTCOME_2026-09-01.md as 4,194,304 B against a 7,864,320 B
    HNF (table/LLC = 0.5333), so it is quoted from there, not measured here.
    """
    rs = load("r5_runs.jsonl")
    pick = lambda a: [x for x in rs if x["run"].startswith(f"r5_{a}_s")]
    v = lambda A: st.mean([x["cyc_per_load"] for x in A])
    al = lambda A: st.mean([sum(x["hnf_allocs_by_way"]) for x in A])
    Q, W, H = pick("qui"), pick("wb"), pick("h2")
    assert len(Q) == len(W) == len(H) == 3
    llc = st.mean([x["l3_size_bytes"] for x in H])
    tw = v(W) / v(Q)
    return dict(R=100 * (tw - v(H) / v(Q)) / (tw - 1),
                share=100 * (al(W) - al(H)) / al(W),
                table=4194304 / 2 ** 20, table_source="G0 gate, not in archive",
                llc=llc / 2 ** 20)


def main():
    F = fused()
    J = complete_join()
    x = [f["table"] for f in F]

    fig, ax = plt.subplots(1, 3, figsize=(7.0, 2.55))
    fig.subplots_adjust(left=0.060, right=0.995, top=0.865, bottom=0.235, wspace=0.34)

    # ---- (a) protection ----
    a = ax[0]
    a.axvline(LLC_MIB, color=GREY, lw=0.6, ls=":")
    a.annotate("table outgrows\nthe shared cache", (LLC_MIB, 99), xytext=(2, -1),
               textcoords="offset points", fontsize=6.0, color=GREY,
               ha="left", va="top", linespacing=1.15)
    a.plot(x, [f["R_cat"] for f in F], "s--", color=CAT, ms=3.2, lw=1.0,
           label="CAT, 4 of 20 ways")
    a.plot(x, [f["R_h2"] for f in F], "o-", color=ACCENT, ms=3.6, lw=1.3,
           label="Streaming")
    a.set_xlabel("tenant's own hot table (MB)")
    a.set_ylabel("neighbour recovery (%)")
    a.set_title("(a) protection", loc="left")
    a.set_ylim(25, 103)
    a.set_xlim(1.5, 8.5)
    a.legend(loc="lower left", frameon=False, handlelength=1.6)

    # ---- (b) tenant cost ----  legend omitted: same two series as (a)
    b = ax[1]
    b.axhline(0, color="black", lw=0.6)
    b.fill_between(x, [f["t_cat"] for f in F], [f["t_h2"] for f in F],
                   color=ACCENT, alpha=0.10, lw=0)
    b.plot(x, [f["t_cat"] for f in F], "s--", color=CAT, ms=3.2, lw=1.0)
    b.plot(x, [f["t_h2"] for f in F], "o-", color=ACCENT, ms=3.6, lw=1.3)
    b.annotate("Streaming", (8.0, F[-1]["t_h2"]), xytext=(-2, 6),
               textcoords="offset points", fontsize=6.6, color=ACCENT, ha="right")
    b.annotate("CAT", (8.0, F[-1]["t_cat"]), xytext=(-2, -9),
               textcoords="offset points", fontsize=6.6, color=CAT, ha="right")
    b.text(4.6, -6.5, "the wedge:\n20--36 pp at every point".replace("--", "\u2013"),
           fontsize=6.4, color=ACCENT, ha="center", va="center", linespacing=1.2)
    b.set_xlabel("tenant's own hot table (MB)")
    b.set_ylabel("tenant progress vs WB (%)")
    b.set_title("(b) what the tenant pays", loc="left")
    b.set_xlim(1.5, 8.5)
    b.set_ylim(-30, 18)

    # ---- (c) mechanism ----
    c = ax[2]
    lim = (0, 100)
    c.plot(lim, lim, "-", color=GREY, lw=0.7, zorder=1)
    c.text(29, 33, "$R$ = share", fontsize=6.4, color=GREY, rotation=45,
           rotation_mode="anchor", ha="left", va="bottom")
    c.plot([f["share"] for f in F], [f["R_h2"] for f in F], "o", color=ACCENT,
           ms=3.6, zorder=3, label="fused tenant, 7 table sizes")
    c.plot([J["share"]], [J["R"]], "D", color=HELD, ms=4.4, zorder=3,
           label="complete join, held out")
    c.annotate("complete join", (J["share"], J["R"]), textcoords="offset points",
               xytext=(8, -2), fontsize=6.4, color=HELD, va="center")
    c.set_xlabel("declared range's share of\nshared-cache fills (%)",
                 linespacing=1.2)
    c.set_ylabel("neighbour recovery (%)")
    c.set_title("(c) why the number moves", loc="left")
    c.set_xlim(*lim)
    c.set_ylim(*lim)
    c.set_xticks([0, 25, 50, 75, 100])
    c.set_yticks([0, 25, 50, 75, 100])
    c.set_aspect("equal", adjustable="box")
    c.legend(loc="upper left", frameon=False, handlelength=1.0, numpoints=1,
             borderpad=0.1, labelspacing=0.35)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT)
    fig.savefig(OUT.with_suffix(".png"))

    print(f"wrote {OUT}")
    print(f"\n{'table':>7s} {'wb tax':>7s} {'R h2':>7s} {'R cat4':>7s} "
          f"{'t h2':>7s} {'t cat4':>7s} {'share':>7s}")
    for f in F:
        print(f"{f['table']:7.1f} {f['wb_tax']:7.4f} {f['R_h2']:6.2f}% {f['R_cat']:6.2f}% "
              f"{f['t_h2']:+6.2f}% {f['t_cat']:+6.2f}% {f['share']:6.2f}%")
    print(f"\ncomplete join (held out): R={J['R']:.2f}%  share={J['share']:.2f}%  "
          f"table={J['table']:.2f} MB  LLC={J['llc']:.2f} MiB")
    viol = [f for f in F if f["R_h2"] > f["share"]]
    print(f"\nceiling R <= share: {len(F) + 1 - len(viol)}/8 satisfied"
          + (f"; exceeded at table={viol[0]['table']} by "
             f"{viol[0]['R_h2'] - viol[0]['share']:.2f} pp" if viol else ""))


if __name__ == "__main__":
    main()
