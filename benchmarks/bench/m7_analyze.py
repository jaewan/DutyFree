#!/usr/bin/env python3
"""M7 analysis: fused way-restriction penalty vs probe hit rate.
Evaluates the pre-registered instrument check, P1-P4, and the e2e gate.
Pre-registration: experiments/asplos/M7_HITRATE_PREREG_2026-08-26.md"""
import json, statistics as st, sys, collections

path = sys.argv[1] if len(sys.argv) > 1 else "../data/m7_hitrate/m7.jsonl"
cells = collections.defaultdict(list)
schem = collections.defaultdict(set)
bad = 0
for line in open(path):
    line = line.strip()
    if not line: continue
    try: d = json.loads(line)
    except Exception: bad += 1; continue
    r = d["record"]
    cells[(d["cat"], float(d["hr"]))].append((r["active_cycles_per_access"], r["join_mtuples_per_s"]))
    schem[d["cat"]].add(d["schemata"])
if bad: print(f"!! {bad} unparseable lines")

hrs = sorted({hr for _, hr in cells})
def med(cat, hr, i): return st.median([v[i] for v in cells[(cat, hr)]])
def cov(cat, hr, i):
    xs = [v[i] for v in cells[(cat, hr)]]
    return 100 * st.stdev(xs) / st.mean(xs) if len(xs) > 1 else 0.0

print(f"{'hr':>5} {'n':>3} {'none cyc':>9} {'b4 cyc':>9} {'R_cyc':>7} "
      f"{'none Mt/s':>10} {'b4 Mt/s':>9} {'R_thr':>7}  CoV%")
R = {}
for hr in hrs:
    n = min(len(cells[('none', hr)]), len(cells[('b4', hr)]))
    if not n: continue
    a, b = med('none', hr, 0), med('b4', hr, 0)
    ta, tb = med('none', hr, 1), med('b4', hr, 1)
    R[hr] = b / a
    print(f"{hr:5} {n:3d} {a:9.3f} {b:9.3f} {b/a:7.4f} {ta:10.2f} {tb:9.2f} "
          f"{tb/ta:7.4f}  {cov('none',hr,0):.2f}/{cov('b4',hr,0):.2f}")

print("\n--- schemata seen per arm ---")
for cat in sorted(schem):
    for s in sorted(schem[cat]): print(f"  {cat:5} {s[:110]}")

print("\n=== registered checks ===")
if 0.5 in R:
    a = med('none', 0.5, 0)
    ok = 84.08 <= a <= 92.93
    print(f"INSTRUMENT  none/0.5 = {a:.3f} cyc/acc, window [84.08, 92.93] -> {'PASS' if ok else 'MISS'}")
    p2 = 1.384 <= R[0.5] <= 1.484
    print(f"P2          R(0.5) = {R[0.5]:.4f}, window [1.384, 1.484] (tab:fused 1.434) -> {'HOLDS' if p2 else 'FAILS'}")
mono = all(R[hrs[i+1]] <= R[hrs[i]] + 0.02 for i in range(len(hrs)-1) if hrs[i] in R and hrs[i+1] in R)
print(f"P1          monotone non-increasing (+0.02 slack) -> {'HOLDS' if mono else 'FAILS'}")
if 1.0 in R:
    print(f"P3          R(1.0) = {R[1.0]:.4f} <= 1.10 -> {'HOLDS' if R[1.0] <= 1.10 else 'FAILS'}")
if 0.0 in R:
    mx = max(R, key=lambda h: R[h])
    print(f"P4          R(0.0) largest? argmax = {mx} (R={R[mx]:.4f}) -> {'HOLDS' if mx == 0.0 else 'FAILS'}")

print("\n=== registered e2e gate ===")
if 0.75 in R and 0.9 in R:
    r75, r90 = R[0.75], R[0.9]
    print(f"  R(0.75) = {r75:.4f}   R(0.9) = {r90:.4f}")
    if r75 <= 1.10 and r90 <= 1.10: print("  -> NO-GO (both <= 1.10): claim (b)'s magnitude is miss-driven")
    elif r75 >= 1.25 or r90 >= 1.25: print("  -> GO (one >= 1.25), queued behind the AMD cell")
    else: print("  -> DEFER (both in (1.10, 1.25)): state the penalty as a range over hit rate")
