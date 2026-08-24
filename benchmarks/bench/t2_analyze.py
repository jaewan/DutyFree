#!/usr/bin/env python3
"""T2 analysis. Computes exactly the readings pre-registered in
experiments/asplos/T2_WBWC_PREREG_2026-08-24.md S6, and nothing else.

Usage: t2_analyze.py <t2_*.jsonl> [...]

Per-rep values and CoV are printed for every cell (prereg S5): this project has
published 3-rep means over a distribution documented as bimodal, and Addendum 3
C3 forbids repeating that.

Arm table, from the prereg (S3). Note C and D are the SAME PROGRAM plus an MSR
warning -- their agreement is a construction check, NOT a test of H4.
"""
import json, sys, statistics as st
from pathlib import Path

ARMS = ["A", "B", "C", "D", "Cp", "E"]
DESC = {
    "A":  "stream_wb          WB pages, regular loads, HW prefetch ON",
    "B":  "stream_wb_nopf     WB pages, regular loads, HW prefetch OFF",
    "C":  "stream_wc          WB pages, MOVNTDQA,      HW prefetch ON   <- the paper's 'WC' arm",
    "D":  "stream_nt          WB pages, MOVNTDQA,      HW prefetch ON   <- same program as C",
    "Cp": "stream_wc_nopf     WB pages, MOVNTDQA,      HW prefetch OFF  <- WC proxy (NOT WC)",
    "E":  "stream_sw_prefetch WB pages, regular + SW prefetch, HW PF ON",
}

def load(paths):
    hosts = {}
    for p in paths:
        for line in Path(p).read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            h = hosts.setdefault(r["host"], {})
            a = h.setdefault(r["arm"], {"bw": [], "bad": []})
            if r.get("status") == "ok":
                a["bw"].append(float(r["record"]["avg_bw_gbps"]))
            else:
                a["bad"].append(r.get("status", "?") + (f" rc={r.get('rc')}" if r.get("rc") else ""))
    return hosts

def cell(a):
    v = a["bw"]
    if not v:
        return None
    m = st.mean(v)
    sd = st.pstdev(v) if len(v) > 1 else 0.0
    return dict(n=len(v), mean=m, sd=sd, cov=(sd / m * 100 if m else 0.0), reps=v)

def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    hosts = load(argv[1:])
    verdicts = []
    for host in sorted(hosts):
        print(f"\n===== {host} =====")
        print(f"  {'arm':<4}{'n':>2} {'GB/s':>8} {'sd':>7} {'CoV%':>6}   per-rep")
        cells = {}
        for arm in ARMS:
            a = hosts[host].get(arm)
            if not a:
                print(f"  {arm:<4} -- not run"); continue
            c = cell(a)
            cells[arm] = c
            if c is None:
                print(f"  {arm:<4} -- ALL REPS UNAVAILABLE: {'; '.join(sorted(set(a['bad'])))[:70]}")
                continue
            reps = " ".join(f"{x:.3f}" for x in c["reps"])
            note = f"  [{len(a['bad'])} bad]" if a["bad"] else ""
            print(f"  {arm:<4}{c['n']:>2} {c['mean']:>8.3f} {c['sd']:>7.3f} {c['cov']:>6.2f}   {reps}{note}")
        print("  arms:")
        for arm in ARMS:
            print(f"    {arm:<3} {DESC[arm]}")

        A, C, D, Cp, B = (cells.get(k) for k in ("A", "C", "D", "Cp", "B"))

        # Reading 1 + 2: the intro's magnitude, and the falsifier.
        if A and C:
            ratio = A["mean"] / C["mean"]
            if ratio >= 3.0:
                v = "CORROBORATED (>=3.0)"
            elif ratio >= 2.0:
                v = "WEAKENED [2.0,3.0)"
            else:
                v = "**FALSIFIED (<2.0)**"
            print(f"\n  R1 intro magnitude A/C = {ratio:.3f}  (claim implies ~3.76) -- {v}")
            verdicts.append((host, ratio))
        if A and Cp:
            print(f"  R1' A/Cp (honest WC proxy) = {A['mean']/Cp['mean']:.3f}")

        # Reading 4: C == D construction check.
        if C and D:
            pooled = (C["sd"] + D["sd"]) / 2 or 1e-9
            d = abs(C["mean"] - D["mean"])
            print(f"  R4 C vs D: {C['mean']:.3f} vs {D['mean']:.3f}  |diff|={d:.3f}, "
                  f"pooled sd={pooled:.3f} -> {'AGREE (same program, as expected)' if d <= 2*pooled else 'DIFFER -- investigate'}")
            print("     [construction check only. stream_nt.c's 'if D~C the NT hint is honored'")
            print("      reading is CIRCULAR and is void; do not report it as an H4 test.]")

        # Reading 5: is the NT hint honored, at equal prefetch state?
        if A and C:
            print(f"  R5 NT hint at equal HW-PF state: C/A = {C['mean']/A['mean']:.3f} "
                  f"({'hint costs bandwidth' if C['mean'] < A['mean'] else 'no bandwidth cost'})")

        # Reading 6: Cp vs C -- was the paper's WC arm benefiting from prefetch?
        if C and Cp:
            r = Cp["mean"] / C["mean"]
            print(f"  R6 Cp/C = {r:.3f} -> " + (
                "prefetch was already ineffective under MOVNTDQA" if r >= 0.95 else
                "**the paper's 'WC' arm WAS benefiting from prefetch; published WC bandwidth is an OVERESTIMATE**"))

        # Reading 7: prefetch's contribution to WB.
        if A and B:
            print(f"  R7 B/A = {B['mean']/A['mean']:.3f} -> HW prefetch contributes "
                  f"{(1-B['mean']/A['mean'])*100:.1f}% of WB stream bandwidth")
        elif A and not (B and B.get('n')):
            print("  R7 unavailable (arm B did not run here -- expected on AMD, MSR 0x1A4 is Intel-only)")

    # Cross-host falsifier (prereg S6 R2).
    print("\n===== pre-registered falsifier (S6 R2) =====")
    if verdicts:
        print("  A/C by host: " + ", ".join(f"{h}={r:.2f}" for h, r in verdicts))
        if all(r < 2.0 for _, r in verdicts):
            print("  **FIRED: A/C < 2.0 on ALL hosts. The intro's motivating contrast does")
            print("   not survive and must be DELETED, not re-sourced.**")
        else:
            print("  not fired (at least one host >= 2.0)")
    print("\nReminder: no arm here measures the WC memory type. Cp is a documented proxy.")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
