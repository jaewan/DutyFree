#!/usr/bin/env python3
"""M10: is the restriction boundary the mask, or aggregate private L2?
Pre-registration: experiments/asplos/M10_MASKBOUNDARY_PREREG_2026-08-27.md"""
import json, statistics as st, sys, collections
path = sys.argv[1] if len(sys.argv) > 1 else "../data/m10_maskboundary/m10.jsonl"
MASK_MIB = {'none': 320, 'b2': 32, 'b4': 64, 'b8': 128}
L2_AGG = 32  # 16 cores x 2 MiB private L2
c = collections.defaultdict(list); schem = collections.defaultdict(set); bad = 0
for line in open(path):
    line = line.strip()
    if not line: continue
    try: d = json.loads(line)
    except Exception: bad += 1; continue
    assert d['table'] == d['table_instantiated'], f"rounded! {d['table']}"
    c[(d['arm'], d['table'])].append(d['record']['active_cycles_per_access'])
    schem[d['arm']].add(d['schemata'])
if bad: print(f"!! {bad} unparseable")
tables = sorted({t for _, t in c})
print(f"{'table':>8} {'vs L2agg':>9} " + "".join(f"{a+' R':>10}" for a in ('b2','b4','b8')))
R = {}
for t in tables:
    if not c[('none', t)]: continue
    base = st.median(c[('none', t)]); row = ""
    for a in ('b2','b4','b8'):
        if c[(a, t)]:
            R[(a,t)] = st.median(c[(a,t)])/base; row += f"{R[(a,t)]:10.4f}"
        else: row += f"{'-':>10}"
    print(f"{t/2**20:8.1f} {('fits' if t/2**20<=L2_AGG else 'exceeds'):>9} {row}   (none={base:.2f})")
print("\nmask capacities: b2=32 MiB, b4=64 MiB, b8=128 MiB; aggregate private L2 = 32 MiB")

def knee(a):
    for t in tables:
        if (a,t) in R and R[(a,t)] > 1.15: return t/2**20
    return None
print("\n=== knee: smallest table with R > 1.15 ===")
kn = {}
for a in ('b2','b4','b8'):
    kn[a] = knee(a)
    print(f"  {a}: mask {MASK_MIB[a]:4d} MiB -> knee at {kn[a]} MiB")
print("\n=== registered checks ===")
if c[('none', 268435456)]:
    v = st.median(c[('none', 268435456)])
    print(f"INSTRUMENT none/256MiB = {v:.3f}, window [86.03, 95.09] (M8 90.558 +/-5%) -> "
          f"{'PASS' if 86.03 <= v <= 95.09 else 'MISS'}")
p3 = all((a,16777216) in R and R[(a,16777216)] <= 1.10 for a in ('b2','b4','b8'))
print(f"P3 apparatus control: R(16 MiB) <= 1.10 under all masks -> {'HOLDS' if p3 else 'FAILS'}"
      + ("" if p3 else "  [P1/P2 unreadable if this fails]"))
p1 = (kn['b2'] is not None and kn['b4'] is not None and kn['b8'] is not None
      and kn['b2'] <= 32 and kn['b4'] == 64 and kn['b8'] == 128)
print(f"P1 mask-capacity (knee tracks mask 32/64/128) -> {'HOLDS' if p1 else 'fails'}")
p2 = ((('b8',67108864) in R and R[('b8',67108864)] > 1.15)
      and kn['b2'] is not None and kn['b8'] is not None
      and kn['b2'] in (32,64) and kn['b8'] in (32,64))
print(f"P2 private-L2 (knee at 32-64 MiB for ALL masks incl. b8) -> {'HOLDS' if p2 else 'fails'}")
if ('b8',268435456) in R:
    r = R[('b8',268435456)]
    print(f"P4 R(b8, 256 MiB) = {r:.4f} >= 1.15 -> {'HOLDS' if r >= 1.15 else 'FAILS'}")
print("\n=== is R a function of table/mask (P1) or of table alone (P2)? ===")
print(f"{'table/mask':>11} " + "".join(f"{a:>10}" for a in ('b2','b4','b8')))
for ratio in (0.5, 1, 2, 4):
    row = ""
    for a in ('b2','b4','b8'):
        t = int(MASK_MIB[a]*ratio*2**20)
        row += f"{R[(a,t)]:10.4f}" if (a,t) in R else f"{'-':>10}"
    print(f"{ratio:11.1f} {row}")
print("  (P1 predicts each ROW is flat across arms; P2 predicts flatness by absolute table size)")
