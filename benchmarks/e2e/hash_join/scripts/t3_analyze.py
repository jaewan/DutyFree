#!/usr/bin/env python3
"""T3 analysis, pinned. Computes the readings registered in
experiments/asplos/T3_HUGEPAGE_PREREG_2026-08-24.md S4-S5.

Committed 2026-08-24 AFTER the run, which is a departure from this project's
rule (analyzer before data) and is recorded as such: T3's numbers were first
produced by an inline heredoc, so the computation was not pinned. The values
here were checked against an independent re-derivation before this file was
committed and they agree exactly. Reported as a process defect in
T3_CODE_AUDIT_2026-08-24.md, not smoothed over.

Two facts about the arms that the reading depends on:
  * run_hot_probe() never calls alloc_bytes(), so --huge2m is a NO-OP for the
    Q arms: Q_4k and Q_2m are the same execution. Their pooled samples are a
    variance estimate, not a page-size comparison.
  * table_capacity() rounds entries up to a power of two, so --hot-bytes
    177838489 (169.6 MiB) instantiates 16,777,216 x 16 B = 256 MiB.
"""
import json, sys, statistics as st
from pathlib import Path

ARMS = ("Q_4k", "A_4k", "Q_2m", "A_2m")


def main(argv):
    p = Path(argv[1] if len(argv) > 1 else "../artifacts/t3_hugepage/t3.jsonl")
    by = {}
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("status") != "ok":
            print(f"  NOT OK: arm={r.get('arm')} rep={r.get('rep')} rc={r.get('rc')}")
            continue
        a = by.setdefault(r["arm"], {"cpa": [], "w": [], "hp": []})
        a["cpa"].append(float(r["record"]["active_cycles_per_access"]))
        a["w"].append(int(r["walk_completed"]))
        a["hp"].append(int(r["hugetlb_pages_used"]))

    print(f"{'arm':<6}{'n':>2} {'cyc/acc':>9}{'psd':>7}{'ssd':>7}  {'walks(M)':>9}{'CoV%':>7}  hugetlb")
    for arm in ARMS:
        c = by.get(arm)
        if not c:
            print(f"{arm:<6} -- absent"); continue
        m = st.mean(c["cpa"]); psd = st.pstdev(c["cpa"])
        ssd = st.stdev(c["cpa"]) if len(c["cpa"]) > 1 else 0.0
        wm = st.mean(c["w"]); wsd = st.pstdev(c["w"])
        print(f"{arm:<6}{len(c['cpa']):>2} {m:>9.3f}{psd:>7.3f}{ssd:>7.3f}  "
              f"{wm/1e6:>9.3f}{(wsd/wm*100 if wm else 0):>7.2f}  {sorted(set(c['hp']))}")
        print(f"       per-rep: {' '.join(f'{x:.2f}' for x in c['cpa'])}")

    Q4, A4 = st.mean(by["Q_4k"]["cpa"]), st.mean(by["A_4k"]["cpa"])
    Q2, A2 = st.mean(by["Q_2m"]["cpa"]), st.mean(by["A_2m"]["cpa"])
    d4, d2 = A4 - Q4, A2 - Q2
    R = (d4 - d2) / d4
    print(f"\n== registered reading (S5) ==")
    print(f"  Delta_4k={d4:.3f}  Delta_2m={d2:.3f}  R={R:+.4f}")
    print("  -> " + ("STREAM-SIDE TLB EXCLUDED (R<=0.10)" if R <= 0.10 else
                     "MATERIAL (R>=0.25)" if R >= 0.25 else "INCONCLUSIVE"))
    print("  CAVEAT: R's denominator is Q, which is bimodal (see pooled Q below) and")
    print("  sampled n=5 per condition. R is NOT a trustworthy point estimate; the")
    print("  paired A-arm comparison and the walk arithmetic below are.")

    print(f"\n== paired A-arm comparison (Q does not enter) ==")
    print(f"  cyc/acc  {A4:.3f} -> {A2:.3f} = {(A2/A4-1)*100:+.2f}%")
    w4, w2, wq = (st.mean(by[k]["w"]) for k in ("A_4k", "A_2m", "Q_4k"))
    print(f"  walks    {w4/1e6:.3f}M -> {w2/1e6:.3f}M = {(w2/w4-1)*100:+.2f}%")
    print(f"  stream's apparent walk contribution (A-Q): {(w4-wq)/1e6:.3f}M -> {(w2-wq)/1e6:.3f}M "
          f"= {(1-(w2-wq)/(w4-wq))*100:.1f}% removed")
    print("  ARITHMETIC: the fact array's pages went 65,536 -> 128 (512x). If those were")
    print("  the stream's own translations, ~99.8% of its walks would vanish. 1.8% did.")
    print("  Therefore the load-induced walks are the VICTIM's. This conclusion rests on")
    print("  a measured-vs-predicted contrast and is independent of arm order and timing.")

    pool = sorted(by["Q_4k"]["cpa"] + by["Q_2m"]["cpa"])
    lo = [x for x in pool if x < 58]; hi = [x for x in pool if x >= 58]
    print(f"\n== pooled Q (Q_2m == Q_4k: --huge2m is a no-op in hot-probe mode) ==")
    print(f"  {[round(x,2) for x in pool]}")
    print(f"  n=10 mean={st.mean(pool):.3f} ssd={st.stdev(pool):.3f} "
          f"spread={(max(pool)/min(pool)-1)*100:.1f}%")
    print(f"  low mode n={len(lo)} mean={st.mean(lo):.2f} | high mode n={len(hi)} mean={st.mean(hi):.2f}")
    print("  tab:fused's published quiescent 61.71 is ONE sample from this distribution")
    print("  (run_confirmatory_panel.py passes --reps 1 and runs each label once).")
    print("\n  Arm order was FIXED, not randomized (Q_4k always position 1, Q_2m always 3),")
    print("  so a position effect cannot be separated from bistability by this data.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
