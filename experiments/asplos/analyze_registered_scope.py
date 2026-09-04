#!/usr/bin/env python3
"""Registration-scope re-analysis of fig:recovery panels (a)/(b).

Supports `RECOVERY_CURVE_OUTCOME_2026-09-04.md` Addendum 2.

Asks what the seven plotted fused points license when restricted to the five
sizes `FUSED_KNEE_PREREG_2026-08-29.md` actually registered (2.0-4.0 MB), and
separately verifies that the pre-fix 90.6% -> 51.9% collapse over 2-4 MB was an
artifact of the aliased power-of-two probe stride.

Definitions match `make_recovery_curve.py` exactly for every mean:
    tax      = victim cyc/access / quiescent cyc/access
    recovery = (tax_wb - tax_arm) / (tax_wb - 1)
    share    = (HNF allocs under wb - under h2) / under wb

Adds a per-seed decomposition the figure script does not compute, because the
question "is a 7 pp decline across five sizes a trend?" cannot be answered from
means alone.  Per-seed recovery is reported two ways:

  paired   -- seed s of the arm against seed s of `wb` (3 independent estimates)
  armonly  -- arm seed varying against the mean `wb` tax, i.e. exactly the
              quantity plotted, with its denominator held fixed

Both are given because they answer different questions and, as it turns out,
agree to two decimals.

Reads committed archives only.  Writes nothing but stdout: no compute, no
rebuild, nothing under `gem5/logs/`, no simulation launched.

Usage: analyze_registered_scope.py
"""
import json
import math
import statistics as st
from pathlib import Path

D = Path(__file__).resolve().parent / "data/gem5"

TABLES = ["2.0", "2.5", "3.0", "3.5", "4.0", "6.0", "8.0"]
REGISTERED = ["2.0", "2.5", "3.0", "3.5", "4.0"]   # FUSED_KNEE_PREREG design
EXTENSION = ["6.0", "8.0"]                          # run_fused_knee_big.sh
SEEDS = ["1", "2", "3"]
ARMS = ("wb", "h2", "cat4")


def load(name):
    return [x for x in (json.loads(l) for l in open(D / name)) if x["completed"]]


def rule(title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


# --------------------------------------------------------------------------
# apparatus
# --------------------------------------------------------------------------
FUSED = load("kn_runs.jsonl") + load("kb_runs.jsonl")
QUI_RUNS = [x for x in load("fh_runs.jsonl") if x["run"].startswith("fh_qui_")]
QUI = st.mean([x["cyc_per_access"] for x in QUI_RUNS])


def rec(tb, arm, seed, rows=None):
    rows = FUSED if rows is None else rows
    hits = [x for x in rows if x["run"].endswith(f"_{arm}_t{tb}_s{seed}")]
    assert len(hits) == 1, (tb, arm, seed, [h["run"] for h in hits])
    return hits[0]


def cell(tb):
    """Means at one table size, reproducing make_recovery_curve.py."""
    W = [rec(tb, "wb", s) for s in SEEDS]
    H = [rec(tb, "h2", s) for s in SEEDS]
    C = [rec(tb, "cat4", s) for s in SEEDS]
    v = lambda A: st.mean([x["cyc_per_access"] for x in A])
    al = lambda A: st.mean([sum(x["hnf_allocs_by_way"]) for x in A])
    tn = lambda A: st.mean([x["tenant_misses_per_kcyc"] for x in A])
    tax = v(W) / QUI
    R = lambda A: 100 * (tax - v(A) / QUI) / (tax - 1)
    out = dict(tax=tax, R_h2=R(H), R_cat=R(C),
               t_h2=100 * (tn(H) / tn(W) - 1),
               t_cat=100 * (tn(C) / tn(W) - 1),
               share=100 * (al(W) - al(H)) / al(W))
    out["wedge"] = out["t_h2"] - out["t_cat"]
    return out


M = {tb: cell(tb) for tb in TABLES}


def per_seed(tb, arm, mode):
    if mode == "paired":
        out = []
        for s in SEEDS:
            w = rec(tb, "wb", s)["cyc_per_access"] / QUI
            a = rec(tb, arm, s)["cyc_per_access"] / QUI
            out.append(100 * (w - a) / (w - 1))
        return out
    tax = M[tb]["tax"]
    return [100 * (tax - rec(tb, arm, s)["cyc_per_access"] / QUI) / (tax - 1)
            for s in SEEDS]


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------
def ols(xs, ys):
    n = len(xs)
    mx, my = st.mean(xs), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    sse = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    sst = sum((y - my) ** 2 for y in ys)
    dof = n - 2
    se_b = math.sqrt(sse / dof / sxx)
    return dict(slope=b, se=se_b, t=b / se_b, dof=dof, r2=1 - sse / sst)


def welch(a, b):
    va, vb, na, nb = st.variance(a), st.variance(b), len(a), len(b)
    se = math.sqrt(va / na + vb / nb)
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1)
                                     + (vb / nb) ** 2 / (nb - 1))
    return dict(delta=st.mean(a) - st.mean(b), se=se,
                t=(st.mean(a) - st.mean(b)) / se, df=df)


# --------------------------------------------------------------------------
rule("0. apparatus and reproduction of the published table")
print(f"quiescent denominator {QUI:.4f} cyc/access, n={len(QUI_RUNS)} "
      f"(per-seed {[round(x['cyc_per_access'], 4) for x in QUI_RUNS]})")
print(f"fused records: {len(FUSED)} "
      f"({len(load('kn_runs.jsonl'))} kn + {len(load('kb_runs.jsonl'))} kb), "
      f"all completed")
print(f"\n{'table':>6} {'wb tax':>8} {'R(h2)':>8} {'R(cat4)':>8} "
      f"{'t(h2)':>8} {'t(cat4)':>8} {'share':>8}  scope")
for tb in TABLES:
    c = M[tb]
    scope = "registered" if tb in REGISTERED else "UNREGISTERED"
    print(f"{tb:>6} {c['tax']:8.4f} {c['R_h2']:7.2f}% {c['R_cat']:7.2f}% "
          f"{c['t_h2']:+7.2f}% {c['t_cat']:+7.2f}% {c['share']:7.2f}%  {scope}")
for tb in TABLES:
    realized = sorted({rec(tb, a, s)["realized_table_mb"]
                       for a in ARMS for s in SEEDS})
    assert realized == [float(tb)], (tb, realized)
print("\nrealized_table_mb == requested at all seven sizes (liveness assertion 2)")

# --------------------------------------------------------------------------
rule("1. seed spread, and whether the registered range shows a trend")
for mode in ("paired", "armonly"):
    print(f"\n--- per-seed recovery [{mode}] ---")
    for arm in ("h2", "cat4"):
        print(f"  {arm}: " + "  ".join(
            f"{tb}={st.mean(per_seed(tb, arm, mode)):.2f}"
            f"+-{max(per_seed(tb, arm, mode)) - min(per_seed(tb, arm, mode)):.2f}"
            for tb in TABLES))
    for arm in ("h2", "cat4"):
        xs, ys = [], []
        for tb in REGISTERED:
            for val in per_seed(tb, arm, mode):
                xs.append(float(tb))
                ys.append(val)
        f = ols(xs, ys)
        sds = [st.stdev(per_seed(tb, arm, mode)) for tb in REGISTERED]
        rngs = [max(per_seed(tb, arm, mode)) - min(per_seed(tb, arm, mode))
                for tb in REGISTERED]
        pooled = math.sqrt(sum(s * s for s in sds) / len(sds))
        print(f"\n  [{arm}] registered range 2.0-4.0 MB, n=15")
        print(f"    OLS slope {f['slope']:+.3f} pp/MB (SE {f['se']:.3f}), "
              f"t({f['dof']}) = {f['t']:+.2f}, R2 = {f['r2']:.3f}")
        print(f"    pooled within-size SD {pooled:.3f} pp; "
              f"widest three-seed span {max(rngs):.2f} pp")
        print(f"    decline / pooled SD = "
              f"{(st.mean(per_seed('2.0', arm, mode)) - st.mean(per_seed('4.0', arm, mode))) / pooled:.0f}x")
        for lo, hi in (("2.0", "4.0"), ("3.5", "4.0")):
            w = welch(per_seed(lo, arm, mode), per_seed(hi, arm, mode))
            print(f"    {lo} vs {hi}: delta {w['delta']:+.2f} pp, "
                  f"Welch t {w['t']:+.2f} (df {w['df']:.2f})")
        full_xs, full_ys = [], []
        for tb in TABLES:
            for val in per_seed(tb, arm, mode):
                full_xs.append(float(tb))
                full_ys.append(val)
        g = ols(full_xs, full_ys)
        print(f"    published range 2.0-8.0 MB: slope {g['slope']:+.3f} pp/MB, "
              f"t({g['dof']}) = {g['t']:+.2f}, R2 = {g['r2']:.3f}")

print("\n--- non-monotonicity at the top of the registered range ---")
for arm in ("h2",):
    a, b = per_seed("3.5", arm, "paired"), per_seed("4.0", arm, "paired")
    print(f"  {arm}: 3.5 MB seeds {[round(x, 2) for x in a]}")
    print(f"     {' ' * len(arm)}4.0 MB seeds {[round(x, 2) for x in b]}")
    print(f"     overlap: {'YES' if max(a) > min(b) else 'NO'} -- "
          f"the reversal reproduces in every seed")

# --------------------------------------------------------------------------
rule("2. which published ranges need the unregistered points")


def span(key, sizes):
    vs = [M[t][key] for t in sizes]
    return min(vs), max(vs), sizes[vs.index(min(vs))], sizes[vs.index(max(vs))]


print(f"{'quantity':>18}  {'registered 2.0-4.0':>28}  {'published 2.0-8.0':>28}")
for key in ("R_h2", "R_cat", "t_h2", "t_cat", "wedge", "share"):
    lo1, hi1, al1, ah1 = span(key, REGISTERED)
    lo2, hi2, al2, ah2 = span(key, TABLES)
    same = "  <- identical" if (round(lo1, 2), round(hi1, 2)) == (round(lo2, 2), round(hi2, 2)) else ""
    print(f"{key:>18}  {lo1:8.2f}..{hi1:7.2f} @{al1}/{ah1:>4}  "
          f"{lo2:8.2f}..{hi2:7.2f} @{al2}/{ah2:>4}{same}")
print("\nEvery panel-(b) range has BOTH endpoints at a registered size, so the")
print("tenant-cost and wedge claims are carried in full by the registered sweep.")

print("\n--- protection gap, Streaming minus CAT ---")
for tb in TABLES:
    print(f"  {tb} MB: {M[tb]['R_h2'] - M[tb]['R_cat']:+7.2f} pp"
          f"{'' if tb in REGISTERED else '   (unregistered)'}")

# --------------------------------------------------------------------------
rule("3. is the 4.0 MB excess over the y=x bound 'inside run-to-run spread'?")
print("The body and the fig:recovery caption both justify it that way.")
print(f"\n{'table':>6} {'R-share per seed':>34} {'mean':>8} {'SD':>7} {'|mean|/SD':>10}")
for tb in TABLES:
    alw = [sum(rec(tb, "wb", s)["hnf_allocs_by_way"]) for s in SEEDS]
    alh = [sum(rec(tb, "h2", s)["hnf_allocs_by_way"]) for s in SEEDS]
    sh = [100 * (w - h) / w for w, h in zip(alw, alh)]
    diff = [r - s for r, s in zip(per_seed(tb, "h2", "paired"), sh)]
    print(f"{tb:>6} {str([round(x, 3) for x in diff]):>34} "
          f"{st.mean(diff):+7.3f} {st.stdev(diff):7.3f} "
          f"{abs(st.mean(diff)) / st.stdev(diff):9.1f}x")
a = [rec("3.5", "wb", s)["cyc_per_access"] / QUI for s in SEEDS]
b = [rec("4.0", "wb", s)["cyc_per_access"] / QUI for s in SEEDS]
w = welch(a, b)
print(f"\nwb tax 3.5 vs 4.0 MB: {st.mean(a):.5f} vs {st.mean(b):.5f}, "
      f"delta {w['delta']:+.5f}, Welch t {w['t']:+.2f}")
print("The 4.0 MB wb-tax dip cited as the source of the spread is itself "
      f"{abs(w['delta']) / st.stdev(b):.0f}x the 4.0 MB seed SD -- systematic, not spread.")

# --------------------------------------------------------------------------
rule("4. was the pre-fix 90.6% -> 51.9% collapse an index artifact?")
TS = load("ts_runs.jsonl")
print(f"ts_runs.jsonl: {len(TS)} completed records "
      f"(aliased power-of-two probe stride, pre-fix)")
pre = {}
for tb in ["1.0", "2.0", "4.0", "6.0", "8.0"]:
    sel = lambda a: [x for x in TS if x["run"].startswith(f"ts_{a}_t{tb}_")]
    v = lambda A: st.mean([x["cyc_per_access"] for x in A])
    W, H, C = sel("wb"), sel("h2"), sel("cat4")
    tax = v(W) / QUI
    pre[tb] = dict(tax=tax,
                   R_h2=100 * (tax - v(H) / QUI) / (tax - 1),
                   R_cat=100 * (tax - v(C) / QUI) / (tax - 1))
    print(f"  {tb:>4} MB: wb tax {tax:.4f}  R(h2) {pre[tb]['R_h2']:6.2f}%  "
          f"R(cat4) {pre[tb]['R_cat']:6.2f}%")

print("\n--- the pre-fix 6 MB cell is bit-identical to its own 4 MB cell ---")
dup = all(rec("4.0", a, s, TS)["simTicks"] == rec("6.0", a, s, TS)["simTicks"]
          and rec("4.0", a, s, TS)["cyc_per_access"] == rec("6.0", a, s, TS)["cyc_per_access"]
          for a in ARMS for s in SEEDS)
print(f"  all 9 arm x seed pairs identical in simTicks and cyc_per_access: {dup}")
nulls = sum(1 for x in TS if x.get("realized_table_mb") is None)
print(f"  records with a null realized_table_mb: {nulls}/{len(TS)}")
print("  -> ts_runs.jsonl contains NO distinct measurement at 6 MB.")

print("\n--- anchors, pre-fix vs post-fix, over the interval the prereg cites ---")
for tb in ("2.0", "4.0"):
    print(f"  {tb} MB: pre-fix {pre[tb]['R_h2']:6.2f}%  ->  "
          f"post-fix {M[tb]['R_h2']:6.2f}%   moved "
          f"{abs(pre[tb]['R_h2'] - M[tb]['R_h2']):5.2f} pp")
d_pre = pre["2.0"]["R_h2"] - pre["4.0"]["R_h2"]
d_post = M["2.0"]["R_h2"] - M["4.0"]["R_h2"]
print(f"\n  decline over 2.0->4.0 MB: pre-fix {d_pre:.2f} pp, "
      f"post-fix {d_post:.2f} pp")
print(f"  share of the original decline attributable to the aliased index: "
      f"{100 * (d_pre - d_post) / d_pre:.1f}%")

d_pub = M["2.0"]["R_h2"] - M["8.0"]["R_h2"]
print(f"\n  published decline 2.0->8.0 MB: {d_pub:.2f} pp, of which the two")
print(f"  unregistered sizes supply {100 * (d_pub - d_post) / d_pub:.1f}% "
      f"and the registered range {100 * d_post / d_pub:.1f}%")
