#!/usr/bin/env python3
"""M9: does tab:fused's restriction penalty survive a NON-ALLOCATING stream?
Evaluates the registered instrument check and P1-P4.
Pre-registration: experiments/asplos/M9_STREAMCONTROL_PREREG_2026-08-26.md"""
import json, statistics as st, sys, collections
path = sys.argv[1] if len(sys.argv) > 1 else "../data/m9_streamcontrol/m9.jsonl"
TF, FIT = 177838489, 33554432
cells = collections.defaultdict(list); schem = collections.defaultdict(set); bad = 0
for line in open(path):
    line = line.strip()
    if not line: continue
    try: d = json.loads(line)
    except Exception: bad += 1; continue
    cells[(d["cat"], d["table"], float(d["hr"]), d["stream"])].append(
        d["record"]["active_cycles_per_access"])
    schem[d["cat"]].add(d["schemata"])
if bad: print(f"!! {bad} unparseable lines")
R = {}
for hr in sorted({k[2] for k in cells}):
    print(f"\n=== hit rate {hr} ===")
    print(f"{'table':>9} {'stream':>7} {'n':>3} {'none':>9} {'b4':>9} {'R':>7}  CoV%")
    for t in (FIT, TF):
        for sm in ("retain", "flush"):
            a, b = cells[('none', t, hr, sm)], cells[('b4', t, hr, sm)]
            if not a or not b: continue
            ma, mb = st.median(a), st.median(b); R[(t, hr, sm)] = mb / ma
            cv = lambda xs: 100*st.stdev(xs)/st.mean(xs) if len(xs) > 1 else 0.0
            lbl = f"{t/2**20:.1f}M" + ("(fits)" if t == FIT else "")
            print(f"{lbl:>9} {sm:>7} {min(len(a),len(b)):3d} {ma:9.3f} {mb:9.3f} "
                  f"{mb/ma:7.4f}  {cv(a):.1f}/{cv(b):.1f}")
print("\n--- schemata per arm ---")
for c in sorted(schem):
    for s in sorted(schem[c]): print(f"  {c:5} {s}")

print("\n=== registered checks ===")
if ('none', TF, 0.5, 'retain') in cells:
    v = st.median(cells[('none', TF, 0.5, 'retain')])
    print(f"INSTRUMENT  none/retain/169.6M/0.5 = {v:.3f}, window [84.86, 93.79] "
          f"-> {'PASS' if 84.86 <= v <= 93.79 else 'MISS'}")
hrs = sorted({k[2] for k in cells})
fl = {hr: R.get((TF, hr, 'flush')) for hr in hrs}
rt = {hr: R.get((TF, hr, 'retain')) for hr in hrs}
if all(v is not None for v in list(fl.values()) + list(rt.values())):
    p1 = all(fl[hr] >= 1.20 for hr in hrs)
    p2 = all(fl[hr] <= 1.10 and rt[hr] >= 1.20 for hr in hrs)
    for hr in hrs: print(f"  hr={hr}: R(169.6,retain) = {rt[hr]:.4f}   R(169.6,flush) = {fl[hr]:.4f}")
    print(f"P1 (H_capacity: flush >= 1.20 both) -> {'HOLDS' if p1 else 'fails'}")
    print(f"P2 (H_stream: flush <= 1.10 and retain >= 1.20 both) -> {'HOLDS' if p2 else 'fails'}")
    if not p1 and not p2:
        print("   -> INTERMEDIATE: partial attribution; size both components")
        for hr in hrs:
            cap = (fl[hr] - 1.0) / (rt[hr] - 1.0) * 100 if rt[hr] > 1.0 else float('nan')
            print(f"      hr={hr}: capacity share of the penalty = {cap:.1f}%, "
                  f"stream share = {100-cap:.1f}%")
for hr in hrs:
    a, b = R.get((FIT, hr, 'retain')), R.get((FIT, hr, 'flush'))
    if None not in (a, b):
        print(f"P3 control hr={hr}: R(32M,retain) = {a:.4f}, R(32M,flush) = {b:.4f} "
              f"-> {'HOLDS' if a <= 1.10 and b <= 1.10 else 'FAILS'}")
for hr in hrs:
    a = cells.get(('none', TF, hr, 'retain')); b = cells.get(('none', TF, hr, 'flush'))
    if a and b:
        d = 100 * (st.median(b) / st.median(a) - 1)
        print(f"P4 hr={hr}: flush proxy cost in none/169.6M = {d:+.1f}% "
              f"(registered 10-25%, M3 band 14-19%) -> {'HOLDS' if 10 <= d <= 25 else 'outside'}")
