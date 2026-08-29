#!/usr/bin/env python3
"""Reproduce every headline gem5 number from committed data with committed code.

WHY
---
Several 2026-08-29/30 analyses were written inline at analysis time and were not
recoverable -- a gap the harness manifest recorded. This replaces them: the
numbers cited in the outcome documents are recomputed here from
experiments/asplos/data/gem5/*.jsonl, and checked against the published values.

A mismatch means either the archive or a published number is wrong. Either way it
should fail loudly rather than be discovered by a referee.

Usage:  python3 experiments/asplos/analyze_archives.py
"""
import collections, os, re, statistics as st, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
from dutyfree import stats

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "gem5")
QUI_REF = 33.8814          # quiescent cyc/access, bit-identical in every batch

# published headline values, from the outcome documents named beside them
PUBLISHED = {
    "hh": {"h2": 88.51, "cat4": 89.47, "cat10": 88.62},   # H2H_PARTITION_VS_H2_OUTCOME
    "fh": {"h2": 90.61, "cat4": 89.47, "cat10": 91.04},   # H2H_FUSED_OUTCOME
}
TOL = 0.02   # percentage points; these are deterministic re-derivations


def load(prefix):
    p = os.path.join(DATA, f"{prefix}_runs.jsonl")
    return stats.load_jsonl(p) if os.path.exists(p) else []


def by_arm(recs, prefix):
    g = collections.defaultdict(list)
    for r in recs:
        if not r.get("completed") or r.get("cyc_per_access") is None:
            continue
        m = re.match(rf"{prefix}_(\w+?)_s\d", r["run"])
        if m:
            g[m.group(1)].append(r)
    return g


def recovery(g, qui_key="qui"):
    """R = (tax_wb - tax_arm)/(tax_wb - 1), the campaign's standard statistic."""
    q = st.mean([r["cyc_per_access"] for r in g[qui_key]])
    tw = st.mean([r["cyc_per_access"] for r in g["wb"]]) / q
    return {a: 100 * (tw - st.mean([r["cyc_per_access"] for r in v]) / q) / (tw - 1)
            for a, v in g.items() if a not in (qui_key, "wb")}


def check_head_to_head(prefix, label):
    g = by_arm(load(prefix), prefix)
    if not g:
        print(f"  {label}: NO ARCHIVE"); return False
    R = recovery(g)
    ok = True
    print(f"  {label}")
    for arm, want in PUBLISHED[prefix].items():
        got = R.get(arm)
        if got is None:
            print(f"    {arm:6s} MISSING"); ok = False; continue
        good = abs(got - want) <= TOL
        ok &= good
        print(f"    {arm:6s} {got:6.2f}%  published {want:6.2f}%  "
              f"{'ok' if good else '** MISMATCH **'}")
    return ok


def report_identity(prefix, label):
    """S5.1 evidence: the masked arms really carried a mask."""
    recs = load(prefix)
    masked = [r for r in recs if r.get("hnf_requestor_masks")]
    decl = [r for r in recs if r.get("declared_streaming")]
    print(f"  {label}: {len(masked)}/{len(recs)} runs masked, "
          f"{len(decl)}/{len(recs)} declared streaming")


def report_table_sizes():
    for p, lbl in (("ts", "table sweep (mask index, superseded)"),
                   ("kn", "knee sweep (multiply-shift index)"),
                   ("kb", "big-table sweep")):
        recs = load(p)
        sizes = sorted({r["realized_table_mb"] for r in recs if r.get("realized_table_mb")})
        req = sorted({float(m.group(1)) for r in recs
                      if (m := re.search(r"_t([\d.]+)_", r["run"]))})
        logged = sum(1 for r in recs if r.get("realized_table_mb"))
        if logged == 0:
            note, shown = "   (predates the self-reporting fix; realized size unknowable)", "unlogged"
        elif logged < len(recs):
            note = f"   ({logged}/{len(recs)} runs log a realized size; the rest predate the fix)"
            shown = sizes
        elif len(sizes) < len(req):
            note, shown = "   <-- F9: requested sizes COLLAPSED onto fewer realized ones", sizes
        else:
            note, shown = "", sizes
        print(f"  {lbl}: requested {req or 'n/a'} -> realized {shown}{note}")


def main():
    print("=" * 74)
    print("ARCHIVE CHECK -- committed code, committed data, published values")
    print("=" * 74)
    print("\nHEAD-TO-HEAD RECOVERY")
    ok = check_head_to_head("hh", "pure stream (H2H_PARTITION_VS_H2_OUTCOME)")
    ok &= check_head_to_head("fh", "fused tenant (H2H_FUSED_OUTCOME)")
    print("\nARM IDENTITY (S5.1)")
    report_identity("hh", "pure stream")
    report_identity("fh", "fused")
    print("\nREALIZED VS REQUESTED TABLE SIZE (F9)")
    report_table_sizes()
    print("\n" + ("ALL PUBLISHED VALUES REPRODUCE" if ok else "** MISMATCH -- investigate **"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
