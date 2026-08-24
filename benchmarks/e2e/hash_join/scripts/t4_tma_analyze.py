#!/usr/bin/env python3
"""T4 phase-1 gate analysis. Computes the readings registered in
T4_SCOPING_PREREG_2026-08-24.md S5 and Addendum 1 A2.

Written AFTER the run (recorded, as for t3_analyze.py). There is no discretion
left: A2 fixes the formula, S5 fixes the thresholds, and both were committed
before the data existed.

    Dcyc_X = (frac_X(A) * cyc(A) - frac_X(Q) * cyc(Q)) / access
    share  = Dcyc_mem / (cyc(A) - cyc(Q))

TMA fractions are fractions of pipeline slots and total slots scale with cycles,
so frac * cyc is the per-access cycle contribution of that category.
"""
import json, re, sys, statistics as st
from pathlib import Path

CATS = ["tma_frontend_bound", "tma_bad_speculation", "tma_retiring",
        "tma_backend_bound", "tma_memory_bound", "tma_core_bound"]
# perf prints bad-spec as its two L2 children on this part
ALT = {"tma_bad_speculation": ["tma_branch_mispredicts", "tma_machine_clears"]}


def parse(errfile):
    txt = Path(errfile).read_text(errors="replace")
    out = {}
    for m in re.finditer(r"([0-9.]+)\s*%\s*(tma_[a-z_]+)", txt):
        out[m.group(2)] = float(m.group(1)) / 100.0
    mux = [float(x) for x in re.findall(r"\(([0-9.]+)%\)", txt)]
    return out, (min(mux) if mux else 100.0)


def main(argv):
    d = Path(argv[1] if len(argv) > 1 else "../artifacts/t4_tma")
    rows = [json.loads(l) for l in (d / "t4_tma.jsonl").read_text().splitlines() if l.strip()]
    ok = [r for r in rows if r.get("status") == "ok"]
    print(f"records={len(rows)} ok={len(ok)}")
    by = {}
    for r in ok:
        f, mux = parse(d / "stderr" / r["stderr_file"])
        for k, kids in ALT.items():
            if k not in f and all(c in f for c in kids):
                f[k] = sum(f[c] for c in kids)
        a = by.setdefault(r["arm"], {"cyc": [], "mux": [], **{c: [] for c in CATS}})
        a["cyc"].append(float(r["record"]["active_cycles_per_access"]))
        a["mux"].append(mux)
        for c in CATS:
            if c in f:
                a[c].append(f[c])

    print("\n== instrument falsifier: L1 slots must sum to ~1.0, no multiplexing ==")
    for arm in ("Q", "A"):
        a = by[arm]
        s = sum(st.mean(a[c]) for c in ("tma_frontend_bound", "tma_bad_speculation",
                                        "tma_retiring", "tma_backend_bound") if a[c])
        print(f"  {arm}: slots sum = {s:.4f}   min enabled = {min(a['mux']):.1f}%   "
              f"{'PASS' if abs(s-1) < 0.03 and min(a['mux']) >= 99.9 else '**CHECK**'}")

    print(f"\n== per-arm means (n per arm) ==")
    print(f"  {'arm':<3}{'n':>3} {'cyc/acc':>9} " + "".join(f"{c.replace('tma_',''):>16}" for c in CATS))
    for arm in ("Q", "A"):
        a = by[arm]
        print(f"  {arm:<3}{len(a['cyc']):>3} {st.mean(a['cyc']):>9.3f} " +
              "".join(f"{st.mean(a[c])*100:>15.2f}%" if a[c] else f"{'--':>16}" for c in CATS))

    cq, ca = st.mean(by["Q"]["cyc"]), st.mean(by["A"]["cyc"])
    dcyc = ca - cq
    print(f"\n== registered differential (A2): Delta = {ca:.3f} - {cq:.3f} = {dcyc:.3f} cyc/access ==")
    print(f"  {'category':<22}{'Q cyc':>9}{'A cyc':>9}{'Dcyc':>9}{'share of Delta':>16}")
    shares = {}
    for c in CATS:
        if not (by["Q"][c] and by["A"][c]):
            continue
        q = st.mean(by["Q"][c]) * cq
        a = st.mean(by["A"][c]) * ca
        shares[c] = (a - q) / dcyc
        print(f"  {c.replace('tma_',''):<22}{q:>9.3f}{a:>9.3f}{a-q:>9.3f}{shares[c]*100:>15.1f}%")

    mem = shares.get("tma_memory_bound")
    print(f"\n== GATE (S5 thresholds on the memory-bound share of Delta) ==")
    print(f"  memory-bound share of Delta = {mem*100:.1f}%")
    if mem >= 0.60:
        v = "MEMORY-SIDE (>=60%): the original T4 occupancy fit is the right experiment"
    elif mem <= 0.30:
        v = ("NOT MEMORY-SIDE (<=30%): **no memory-side mechanism can address the fused case** "
             "-- not H2, not a staging buffer, not MSHR QoS. Original T4 CANCELLED, not deferred.")
    else:
        v = "MIXED (30-60%): memory-side mechanism only with a recoverable ceiling = this share"
    print(f"  -> {v}")

    top = max((k for k in shares if k not in ("tma_backend_bound",)), key=lambda k: shares[k])
    print(f"\n== dominant category of Delta, reported by name as registered ==")
    print(f"  {top.replace('tma_','')} at {shares[top]*100:.1f}% of Delta")
    print("  (backend_bound excluded from the argmax: it is the parent of memory+core)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
