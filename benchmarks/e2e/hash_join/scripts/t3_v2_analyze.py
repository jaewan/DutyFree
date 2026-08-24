#!/usr/bin/env python3
"""T3 run-2 analysis. Written and committed BEFORE run 2's data existed, so the
readings cannot be shaped by the result.

Registered in experiments/asplos/T3_HUGEPAGE_PREREG_2026-08-24.md S4-S5 and
Addendum 1. Computes those readings and nothing else, plus the two checks
Addendum 1 added:

  * POSITION EFFECT, testable for the first time. Run 1 used a fixed arm order,
    so a position effect and run-to-run variance were inseparable. Run 2 uses a
    randomized Latin square in which every arm occupies every position exactly 3
    times over 12 reps, so pooling by position isolates it.
  * Q_4k vs Q_2m AS A REPLICATE PAIR. run_hot_probe() never calls alloc_bytes(),
    so --huge2m is a no-op there and the two labels are the same execution.
    Registered check: if they differ by more than their pooled spread, something
    is order- or state-dependent and the cell set is suspect.

Also verifies in-band what run 1 could not: the INSTANTIATED hot-table size,
captured from the binary's own HOT_TABLE line (F9 quantization -- 177838489
requested becomes 268435456 = 256 MiB = 80.0% of the 8592+'s 320 MiB LLC).
"""
import json, sys, statistics as st
from pathlib import Path

ARMS = ("Q_4k", "A_4k", "Q_2m", "A_2m")
LLC = 320 * 2**20


def sd2(v):
    return (st.pstdev(v), st.stdev(v) if len(v) > 1 else 0.0)


def main(argv):
    p = Path(argv[1] if len(argv) > 1 else "../artifacts/t3_hugepage_v2/t3_v2.jsonl")
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    ok = [r for r in rows if r.get("status") == "ok"]
    print(f"records={len(rows)} ok={len(ok)} failed={len(rows)-len(ok)}")
    for r in rows:
        if r.get("status") != "ok":
            print(f"  FAILED arm={r.get('arm')} rep={r.get('rep')} rc={r.get('rc')} see {r.get('stderr_file')}")

    by, bypos, inst, warns = {}, {}, set(), 0
    for r in ok:
        a = by.setdefault(r["arm"], {"cpa": [], "w": [], "hp": [], "pos": []})
        c = float(r["record"]["active_cycles_per_access"])
        a["cpa"].append(c); a["w"].append(int(r["walk_completed"]))
        a["hp"].append(r["hugetlb_pages_used"]); a["pos"].append(r["pos"])
        bypos.setdefault((r["arm"], r["pos"]), []).append(c)
        inst.add(r.get("hot_table_instantiated_bytes"))
        warns += int(r.get("hot_table_rounded_warns", 0))

    print(f"\n== F9 check: instantiated hot-table size (in-band this time) ==")
    for v in sorted(inst):
        try:
            b = int(v); print(f"  {b} B = {b/2**20:.0f} MiB = {b/LLC*100:.1f}% of the 320 MiB LLC")
        except (TypeError, ValueError):
            print(f"  {v}  <- not captured")
    print(f"  HOT_TABLE_ROUNDED warnings seen: {warns} (requested 177838489 = 169.6 MiB = 53.0%)")

    print(f"\n{'arm':<6}{'n':>3} {'cyc/acc':>9}{'psd':>7}{'ssd':>7}  {'walks(M)':>9}{'CoV%':>7}  hugetlb")
    for arm in ARMS:
        c = by.get(arm)
        if not c:
            print(f"{arm:<6} -- absent"); continue
        m = st.mean(c["cpa"]); psd, ssd = sd2(c["cpa"])
        wm = st.mean(c["w"]); wsd = st.pstdev(c["w"])
        print(f"{arm:<6}{len(c['cpa']):>3} {m:>9.3f}{psd:>7.3f}{ssd:>7.3f}  "
              f"{wm/1e6:>9.3f}{(wsd/wm*100 if wm else 0):>7.2f}  {sorted(set(c['hp']))}")
        print(f"       per-rep: {' '.join(f'{x:.2f}' for x in c['cpa'])}")

    print("\n== POSITION EFFECT (run 1 could not test this) ==")
    print("  per-arm mean cyc/acc by position in the rep:")
    print(f"  {'arm':<6}" + "".join(f"{'pos'+str(i):>10}" for i in (1, 2, 3, 4)) + f"{'max-min':>10}")
    for arm in ARMS:
        cells = [bypos.get((arm, i), []) for i in (1, 2, 3, 4)]
        means = [st.mean(c) if c else float("nan") for c in cells]
        good = [x for x in means if x == x]
        rng = (max(good) - min(good)) if good else float("nan")
        print(f"  {arm:<6}" + "".join(f"{m:>10.2f}" for m in means) + f"{rng:>10.2f}")
    allpos = {i: [x for arm in ARMS for x in bypos.get((arm, i), [])] for i in (1, 2, 3, 4)}
    print("  pooled across arms (confounded with arm mix only if the square is unbalanced):")
    for i in (1, 2, 3, 4):
        v = allpos[i]
        if v: print(f"    pos{i}: n={len(v)} mean={st.mean(v):.2f}")
    print("  balance check (each arm should appear 3x per position):")
    for arm in ARMS:
        print(f"    {arm:<6} {[len(bypos.get((arm,i),[])) for i in (1,2,3,4)]}")

    Q4, A4 = st.mean(by["Q_4k"]["cpa"]), st.mean(by["A_4k"]["cpa"])
    Q2, A2 = st.mean(by["Q_2m"]["cpa"]), st.mean(by["A_2m"]["cpa"])
    d4, d2 = A4 - Q4, A2 - Q2
    R = (d4 - d2) / d4
    print(f"\n== registered reading (S5) ==")
    print(f"  Delta_4k = {A4:.3f} - {Q4:.3f} = {d4:.3f}   Delta_2m = {A2:.3f} - {Q2:.3f} = {d2:.3f}")
    print(f"  R = {R:+.4f}")
    print("  -> " + ("STREAM-SIDE TLB EXCLUDED (R<=0.10)" if R <= 0.10 else
                     "**MATERIAL (R>=0.25): RUN 1's VERDICT WAS WRONG -- report the reversal**"
                     if R >= 0.25 else "INCONCLUSIVE (0.10<R<0.25)"))
    print("  run 1 for comparison: R = -0.0877 (withdrawn as a point estimate, fixed arm order)")

    print(f"\n== Q replicate check (Q_2m == Q_4k by construction) ==")
    pooled_sd = (st.pstdev(by["Q_4k"]["cpa"]) + st.pstdev(by["Q_2m"]["cpa"])) / 2
    diff = abs(Q4 - Q2)
    print(f"  Q_4k {Q4:.3f} vs Q_2m {Q2:.3f}  |diff|={diff:.3f}  pooled sd={pooled_sd:.3f}")
    print("  -> " + ("consistent with variance" if diff <= pooled_sd
                     else "**EXCEEDS pooled spread: order/state dependence, cell set suspect**"))
    pool = sorted(by["Q_4k"]["cpa"] + by["Q_2m"]["cpa"])
    lo = [x for x in pool if x < 58]; hi = [x for x in pool if x >= 58]
    print(f"  pooled Q (n={len(pool)}): mean={st.mean(pool):.3f} ssd={st.stdev(pool):.3f} "
          f"spread={(max(pool)/min(pool)-1)*100:.1f}%  (run 1: 16.3%)")
    print(f"  modes: low n={len(lo)}" + (f" mean={st.mean(lo):.2f}" if lo else "") +
          f" | high n={len(hi)}" + (f" mean={st.mean(hi):.2f}" if hi else ""))

    print(f"\n== primary evidence: paired A-arm + walk arithmetic (independent of Q and of order) ==")
    print(f"  cyc/acc  A_4k {A4:.3f} -> A_2m {A2:.3f} = {(A2/A4-1)*100:+.2f}%")
    w4, w2, wq = (st.mean(by[k]["w"]) for k in ("A_4k", "A_2m", "Q_4k"))
    print(f"  walks    {w4/1e6:.3f}M -> {w2/1e6:.3f}M = {(w2/w4-1)*100:+.2f}%")
    got = (1 - (w2 - wq) / (w4 - wq)) * 100 if (w4 - wq) else float("nan")
    print(f"  stream's apparent walk contribution: {(w4-wq)/1e6:.3f}M -> {(w2-wq)/1e6:.3f}M = {got:.1f}% removed")
    print(f"  fact pages 65,536 -> 128 (512x). If those were the stream's own translations,")
    print(f"  ~99.8% of its walks would vanish. Measured: {got:.1f}%.")
    print("  -> load-induced walks are the VICTIM's" if got < 50 else
          "  -> **the stream's own walks DO dominate; run 1's reading was wrong**")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
