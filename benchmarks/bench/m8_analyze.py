#!/usr/bin/env python3
"""M8: restriction penalty vs table size across the 4-way (64 MiB) mask boundary.
Evaluates the registered instrument check and P1-P4.
Pre-registration: experiments/asplos/M8_TABLEFIT_PREREG_2026-08-26.md"""
import json, statistics as st, sys, collections
path = sys.argv[1] if len(sys.argv) > 1 else "../data/m8_tablefit/m8.jsonl"
MASK_MIB = 64  # 4 of 20 ways x 16 MiB
cells = collections.defaultdict(list); schem = collections.defaultdict(set); bad = 0
for line in open(path):
    line = line.strip()
    if not line: continue
    try: d = json.loads(line)
    except Exception: bad += 1; continue
    cells[(d["cat"], d["table"], float(d["hr"]))].append(d["record"]["active_cycles_per_access"])
    schem[d["cat"]].add(d["schemata"])
if bad: print(f"!! {bad} unparseable lines")
tables = sorted({t for _, t, _ in cells}); hrs = sorted({h for _, _, h in cells})
R = {}
for hr in hrs:
    print(f"\n=== hit rate {hr} ===")
    print(f"{'table MiB':>10} {'fits 64MiB':>11} {'n':>3} {'none':>9} {'b4':>9} {'R':>7}  CoV%")
    for t in tables:
        a, b = cells[('none', t, hr)], cells[('b4', t, hr)]
        if not a or not b: continue
        ma, mb = st.median(a), st.median(b); R[(t, hr)] = mb / ma
        cv = lambda xs: 100*st.stdev(xs)/st.mean(xs) if len(xs) > 1 else 0.0
        print(f"{t/2**20:10.1f} {'yes' if t/2**20 <= MASK_MIB else 'NO':>11} {min(len(a),len(b)):3d} "
              f"{ma:9.3f} {mb:9.3f} {mb/ma:7.4f}  {cv(a):.1f}/{cv(b):.1f}")
print("\n--- schemata per arm ---")
for c in sorted(schem):
    for s in sorted(schem[c]): print(f"  {c:5} {s}")

TF = 177838489  # tab:fused's table
print("\n=== registered checks ===")
if ('none', TF, 0.5) in cells:
    v = st.median(cells[('none', TF, 0.5)])
    print(f"INSTRUMENT  none/169.6MiB/0.5 = {v:.3f}, window [84.86, 93.79] (M7 89.326 +/-5%) "
          f"-> {'PASS' if 84.86 <= v <= 93.79 else 'MISS'}")
small = [t for t in tables if t/2**20 <= 32]
for hr in hrs:
    sm = [R[(t,hr)] for t in small if (t,hr) in R]
    big = R.get((TF,hr))
    p1 = (all(r <= 1.10 for r in sm) and big is not None and big >= 1.30)
    print(f"P1  hr={hr}: R(<=32MiB) = {', '.join(f'{r:.3f}' for r in sm)}; R(169.6MiB) = "
          f"{big:.3f} -> {'HOLDS' if p1 else 'fails'}" if big else "P1 incomplete")
for hr in hrs:
    rs = [R[(t,hr)] for t in tables if (t,hr) in R]
    if rs: print(f"P2  hr={hr}: max/min = {max(rs)/min(rs):.3f} <= 1.15 -> "
                 f"{'HOLDS' if max(rs)/min(rs) <= 1.15 else 'fails'}")
if (TF,0.5) in R:
    r = R[(TF,0.5)]
    print(f"P3  R(169.6MiB, 0.5) = {r:.4f}, window [1.310, 1.448] (M7 1.379 +/-5%) -> "
          f"{'HOLDS' if 1.310 <= r <= 1.448 else 'FAILS'}")
for hr in hrs:
    a, b, c = R.get((33554432,hr)), R.get((67108864,hr)), R.get((134217728,hr))
    if None not in (a,b,c):
        print(f"P4  hr={hr}: R(32)={a:.3f} R(64)={b:.3f} R(128)={c:.3f} -> "
              f"{'HOLDS' if min(a,c) <= b <= max(a,c) else 'fails'}")
