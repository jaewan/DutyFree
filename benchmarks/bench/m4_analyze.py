#!/usr/bin/env python3
"""M4 rate-sweep analysis. Computes only the readings registered in
M4_RATESWEEP_PREREG_2026-08-26.md. Committed before the data is complete.

    harm(w)      = victim cyc/load with F / victim alone
    floor(w)     = harm_flush(w) - 1          # the non-residency component
    residency(w) = harm_retain(w) - harm_flush(w)
    share(w)     = residency(w) / (harm_retain(w) - 1)

Primary: floor(16)/floor(1) over a 14.5x rate range. >20 superlinear (queueing);
7-20 proportional to traffic; <3 the rate-dependence rescue FAILS.
Secondary and independently decisive: share flat within +-15 points => rescue
fails whatever the floor does.
"""
import json, sys, statistics as st, collections
from pathlib import Path

W = [1, 2, 4, 8, 16]
GBS = {1: 0.702, 2: 1.394, 4: 2.748, 8: 5.403, 16: 10.157}   # calibrated, standalone


def main(argv):
    p = Path(argv[1] if len(argv) > 1 else "../data/m4_ratesweep/m4.jsonl")
    by, pos = collections.defaultdict(list), collections.defaultdict(list)
    for l in p.read_text().splitlines():
        if not l.strip():
            continue
        r = json.loads(l); v = r.get("median_cyc_per_load")
        if v is None:
            print(f"  BAD: {r}"); continue
        by[r["arm"]].append(float(v)); pos[r["arm"]].append(r["pos"])
    if "V" not in by:
        print("no baseline"); return 2
    base = st.mean(by["V"])
    n_v = len(by["V"])
    print(f"victim alone: {base:.3f} cyc/load  (n={n_v}, CoV {st.pstdev(by['V'])/base*100:.2f}%)")

    print(f"\n{'workers':>7}{'GB/s':>8}{'retain':>9}{'flush':>9}  {'harm_ret':>9}{'harm_fl':>9}"
          f"{'floor':>8}{'residency':>10}{'share':>8}")
    floors, shares, ok = {}, {}, True
    for w in W:
        rk, fk = f"F{w}_retain", f"F{w}_flush"
        if rk not in by or fk not in by:
            print(f"{w:>7}  -- incomplete"); ok = False; continue
        mr, mf = st.mean(by[rk]), st.mean(by[fk])
        hr, hf = mr / base, mf / base
        floors[w] = hf - 1.0
        shares[w] = (hr - hf) / (hr - 1.0) if hr > 1.0 else float("nan")
        print(f"{w:>7}{GBS[w]:>8.2f}{mr:>9.2f}{mf:>9.2f}  {hr:>9.4f}{hf:>9.4f}"
              f"{floors[w]:>8.3f}{hr-hf:>10.3f}{shares[w]*100:>7.1f}%")
    if not ok or 1 not in floors or 16 not in floors:
        print("\nincomplete; registered readings not computed"); return 2

    print(f"\n== instrument check (registered, not optional) ==")
    h16r = st.mean(by["F16_retain"]) / base; h16f = st.mean(by["F16_flush"]) / base
    c1 = abs(h16r - 2.7745) <= 0.1; c2 = abs(h16f - 2.2759) <= 0.1
    c3 = 78.05 <= base <= 78.20
    print(f"  harm_retain(16) {h16r:.4f} vs M3b 2.7745  {'OK' if c1 else '**MISS**'}")
    print(f"  harm_flush(16)  {h16f:.4f} vs M3b 2.2759  {'OK' if c2 else '**MISS**'}")
    print(f"  victim alone    {base:.3f} in [78.05,78.20] {'OK' if c3 else '**MISS**'}")
    if not (c1 and c2 and c3):
        print("  -> one or more checks missed; treat the readings below as suspect")

    ratio = floors[16] / floors[1] if floors[1] else float("inf")
    print(f"\n== PRIMARY: how does the non-residency floor scale? ==")
    print(f"  rate rises {GBS[16]/GBS[1]:.1f}x from 1 to 16 workers")
    print(f"  floor(1) = {floors[1]:.3f}   floor(16) = {floors[16]:.3f}   ratio = {ratio:.2f}")
    if ratio > 20:
        print("  -> SUPERLINEAR: queueing near saturation. Residency share is a curve;")
        print("     W5.3-Intel, M3b and AMD may lie on one axis. Model becomes predictive.")
    elif ratio >= 7:
        print("  -> ~PROPORTIONAL TO TRAFFIC. Model holds but is not a saturation story;")
        print("     W5.3's Intel row still needs a different explanation.")
    elif ratio < 3:
        print("  -> **FLAT: THE RATE-DEPENDENCE RESCUE FAILS.** The non-residency")
        print("     component is not set by rate. W5.3's Intel counter-point stays")
        print("     unexplained and the two-component model is a hypothesis with an")
        print("     outstanding contradiction. Report it that way.")
    else:
        print("  -> between 3 and 7: sub-linear, unregistered band. Report the curve only.")

    sv = [shares[w] for w in W if w in shares]
    spread = (max(sv) - min(sv)) * 100
    print(f"\n== SECONDARY (independently decisive): does the residency share move? ==")
    print("  share: " + "  ".join(f"{w}w={shares[w]*100:.1f}%" for w in W if w in shares))
    print(f"  spread across the {GBS[16]/GBS[1]:.1f}x rate range = {spread:.1f} points")
    if spread <= 15:
        print("  -> **FLAT within +-15: THE RESCUE FAILS regardless of the floor.**")
        print("     The residency share does not depend on rate, so the three")
        print("     conflicting decomposition points are NOT one curve in rate.")
    else:
        print("  -> moves; check whether it falls as rate rises, as the rescue requires:")
        print(f"     {'FALLS (consistent)' if sv[0] > sv[-1] else 'RISES (opposite of the rescue)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
