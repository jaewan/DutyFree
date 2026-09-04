#!/usr/bin/env python3
"""Complete-join campaign: STREAMING vs CAT in tuples/s at table/LLC ≈ 0.53.

Pre-registration: COMPLETE_JOIN_PREREG_2026-09-01.md

Usage: analyze_complete_join.py <r5_runs.jsonl>
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from pathlib import Path

WIDTHS = (1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20)
SEEDS = 3
WANT_L3 = 7_864_320
WANT_HOT = 4_194_304
RATIO_MIN, RATIO_MAX = 0.530, 0.537
WB_TAX_FLOOR = 1.15
WB_TOL = 0.01
MONO_TOL = 0.005
TPS_AGREE = 0.08
VICTIM_ITERS = 12_000_000
CONTENDED_LOADS = (100_000, 6_000_000)
QUIET_LOADS = (11_000_000, 12_100_000)
CPU_HZ = 1.9e9


def mark(name, ok, detail):
    print(f"  {name:48s} {'PASS' if ok else 'FAIL'}  {detail}")
    return ok


def mean(g, k):
    v = [x[k] for x in g if x.get(k) is not None]
    return st.mean(v) if v else None


def tps_of(r):
    """Prefer JSON tuples/s; fall back to stats-derived if chrono disagrees."""
    js = r.get("join_mtuples_per_s")
    derived = r.get("join_mtuples_per_s_from_cycles")
    if js is None:
        return derived
    if derived is None:
        return js
    if js == 0:
        return derived
    if abs(js - derived) / max(js, derived) > TPS_AGREE:
        return derived
    return js


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    rows = [json.loads(l) for l in Path(argv[1]).read_text().splitlines() if l.strip()]
    ref, front = {}, {}
    for r in rows:
        m = re.match(r"r(?:j|[0-9])_([a-z0-9]+)_s(\d+)$", r["run"])
        if not m:
            continue
        tag = m.group(1)
        w = re.match(r"wm(\d+)$", tag)
        (front.setdefault(int(w.group(1)), []) if w else ref.setdefault(tag, [])).append(r)

    missing = [w for w in WIDTHS if len(front.get(w, [])) != SEEDS]
    incomplete = [w for w in front if not all(x.get("completed") for x in front[w])]
    gates = [mark("F1 all frontier points present", not missing and not incomplete,
                  f"missing={missing} incomplete={incomplete}")]
    for t in ("qui", "wb", "h2"):
        gates.append(mark(f"F2 reference arm {t} present",
                          len(ref.get(t, [])) == SEEDS
                          and all(x.get("completed") for x in ref[t]),
                          f"{len(ref.get(t, []))}/{SEEDS}"))
    if not all(gates):
        print("===== VERDICT =====\nFAIL: incomplete; no dominance claim licensed")
        return 1

    geo_ok = True
    for r in rows:
        if not r.get("completed"):
            continue
        l3 = r.get("l3_size_bytes")
        hot = r.get("instantiated_hot_bytes")
        if r["run"].startswith("r5_qui"):
            if l3 != WANT_L3:
                geo_ok = False
            continue
        ratio = (hot / l3) if l3 and hot else None
        if l3 != WANT_L3 or hot != WANT_HOT or ratio is None or not (RATIO_MIN <= ratio <= RATIO_MAX):
            geo_ok = False
    gates.append(mark("G0 table/LLC ≈ 0.53 (4 MiB / 7680 KiB)", geo_ok,
                      f"want l3={WANT_L3} hot={WANT_HOT} ratio in [{RATIO_MIN},{RATIO_MAX}]"))

    complete_ok = True
    bypass_ok = True
    mask_ok = True
    details = []
    for r in rows:
        if not r.get("completed"):
            continue
        tag = re.match(r"r(?:j|[0-9])_([a-z0-9]+)_s", r["run"]).group(1)
        loads = r.get("victim_loads") or 0
        byp = r.get("hnf_streaming_bypasses") or 0
        if tag == "qui":
            if not (QUIET_LOADS[0] <= loads <= QUIET_LOADS[1]):
                complete_ok = False
                details.append(f"{r['run']} qui loads={loads}")
            if byp != 0:
                bypass_ok = False
                details.append(f"{r['run']} qui bypasses={byp}")
            continue
        if not r.get("join_m5_exit") or not r.get("join_measure_end"):
            complete_ok = False
            details.append(f"{r['run']} missing JOIN markers")
        if not (r.get("join_mtuples_per_s") or 0) > 0:
            complete_ok = False
            details.append(f"{r['run']} no tuples/s")
        if not (CONTENDED_LOADS[0] <= loads <= CONTENDED_LOADS[1]):
            complete_ok = False
            details.append(f"{r['run']} loads={loads} (want tenant-ended window)")
        if tag == "h2":
            if byp <= 0:
                bypass_ok = False
                details.append(f"{r['run']} h2 bypasses={byp}")
        elif byp != 0:
            bypass_ok = False
            details.append(f"{r['run']} bypasses={byp} want 0")
        raw = (r.get("hnf_requestor_masks") or "").strip()
        node5 = int(raw.split()[5]) if raw.split() else 0
        if tag.startswith("wm"):
            w = int(tag[2:])
            want = 0 if w == 20 else (1 << w) - 1
        else:
            want = 0
        if node5 != want:
            mask_ok = False
            details.append(f"{r['run']} node5={node5} want {want}")
    gates.append(mark("P_complete tenant ended contended windows", complete_ok,
                      "; ".join(details[:6]) or "JOIN_M5_EXIT + JSON + victim_loads band"))
    gates.append(mark("P_bypass H2 only", bypass_ok,
                      "; ".join(d for d in details if "bypass" in d)[:200] or "h2>0 others=0"))
    gates.append(mark("A4 requestor mask matches arm", mask_ok,
                      "; ".join(d for d in details if "node5=" in d)[:200] or "node5 from config.ini"))

    q = mean(ref["qui"], "cyc_per_load")
    wb = mean(ref["wb"], "cyc_per_load")
    wb_tps = st.mean([tps_of(x) for x in ref["wb"]])
    h2_c = mean(ref["h2"], "cyc_per_load")
    h2_tps = st.mean([tps_of(x) for x in ref["h2"]])
    h2_prot = (wb - h2_c) / (wb - q) if wb != q else 0.0
    tax = wb / q

    print("===== COMPLETE JOIN =====")
    print(f"  quiet={q:.3f}  wb={wb:.3f} (tax {tax:.4f}x, tenant {wb_tps:.4f} MT/s)")
    print(f"  STREAMING  victim {h2_c:.3f}  protection {h2_prot*100:.2f}%  "
          f"tenant {h2_tps:.4f} MT/s ({(h2_tps/wb_tps-1)*100:+.2f}% vs wb)")
    print(f"  {'ways':>5s} {'mask':>8s} {'victim':>10s} {'R':>8s} {'MT/s':>10s} {'vs wb':>8s} {'dom H2?':>8s}")

    pts, dominators = [], []
    for w in WIDTHS:
        g = front[w]
        c = mean(g, "cyc_per_load")
        tps = st.mean([tps_of(x) for x in g])
        p = (wb - c) / (wb - q)
        pts.append((w, p, tps))
        dom = p >= h2_prot and tps >= h2_tps
        if dom:
            dominators.append(w)
        print(f"  {w:>5d} {((1<<w)-1) if w < 20 else 0:>#8x} {c:>10.3f} {p*100:>7.2f}% "
              f"{tps:>10.4f} {(tps/wb_tps-1)*100:>+7.2f}% {('YES' if dom else 'no'):>8s}")

    print("\n===== REGISTERED PREDICTIONS =====")
    p2 = mark("P2 WB tax >= 1.15x", tax >= WB_TAX_FLOOR,
              f"{tax:.4f}x (floor 1.15; r3 was 1.30)")
    p5 = mark("P5 STREAMING outside CAT frontier (tuples/s)", not dominators,
              "no width matches H2 on both axes" if not dominators
              else f"widths {dominators} match or beat H2 on BOTH R and tuples/s")
    w20 = next(p for p in pts if p[0] == 20)
    tps20 = w20[2]
    c20 = mean(front[20], "cyc_per_load")
    ctrl = abs(c20 / wb - 1) <= WB_TOL and abs(tps20 / wb_tps - 1) <= WB_TOL
    mark("P6a w=20 reproduces wb", ctrl,
         f"w=20 victim {c20:.3f} vs wb {wb:.3f}; MT/s {tps20:.4f} vs {wb_tps:.4f}; "
         "empty masks on both — tautological, not a mask-path control")
    asc = sorted(pts, key=lambda t: t[0])
    tps_mono = all(asc[i][2] <= asc[i + 1][2] + MONO_TOL * wb_tps for i in range(len(asc) - 1))
    mark("P6c tenant tuples/s monotone in width", tps_mono,
         "non-decreasing as ways are added" if tps_mono else "NON-MONOTONE")

    eligible = [(w, p, t) for (w, p, t) in pts if p >= h2_prot]
    print("\n===== WEDGE (tuples/s at equal-or-better protection) =====")
    if eligible:
        bw, bp, bt = max(eligible, key=lambda t: t[2])
        print(f"  Cheapest CAT >= STREAMING R ({h2_prot*100:.2f}%): w={bw} at {bp*100:.2f}%")
        print(f"  CAT costs {(bt/wb_tps-1)*100:+.2f}% tuples/s; STREAMING {(h2_tps/wb_tps-1)*100:+.2f}%")
        print(f"  WEDGE = {(h2_tps/bt-1)*100:+.2f}%")
        # Post-hoc: interpolate tenant throughput at H2's R between the
        # registered comparator and the next wider (under-protecting) point.
        # Does not change P5.
        wider = [p for p in pts if p[0] > bw]
        if wider:
            nw, np_, nt = min(wider, key=lambda t: t[0])
            if (bp - np_) != 0:
                frac = (h2_prot - bp) / (np_ - bp)
                t_iso = bt + frac * (nt - bt)
                print("  POST-HOC (not registered): interpolated tuples/s at matched "
                      f"R={h2_prot*100:.2f}% between w={bw} and w={nw}: {t_iso:.4f} MT/s")
                print(f"  POST-HOC iso-R WEDGE = {(h2_tps/t_iso-1)*100:+.2f}% "
                      f"(wm{bw} over-protects by {(bp-h2_prot)*100:.2f} pp)")
    else:
        print(f"  No way width reaches STREAMING's {h2_prot*100:.2f}% protection.")

    print("\n===== VERDICT =====")
    if not p2:
        print("VOID for a cost claim: WB tax below floor. Geometry still reported.")
        return 1
    print("PASS: STREAMING dominates the CAT frontier in tuples/s" if p5
          else "REFUTED: P5 — report the width at which partitioning suffices")
    return 0 if p5 and geo_ok and complete_ok and bypass_ok and mask_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
