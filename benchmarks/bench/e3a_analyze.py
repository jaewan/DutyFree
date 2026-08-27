#!/usr/bin/env python3
"""E3 pass A: does the 2/3 occupancy knee travel to mos182's 60 MiB / 15-way cache?
Pre-registration: experiments/asplos/E3_GEOMETRY_PREREG_2026-08-28.md"""
import json, statistics as st, sys, collections
path = sys.argv[1] if len(sys.argv) > 1 else "../data/e3a_geometry/e3a.jsonl"
v = collections.defaultdict(list); masks = collections.defaultdict(set); WT=[None]
for l in open(path):
    l=l.strip()
    if not l: continue
    d=json.loads(l)
    if d['victim_cyc_per_load'] is None: continue
    v[(d['victim_ways'], d['wss'])].append(d['victim_cyc_per_load'])
    WT[0]=d['ways_total']
    if d['victim_ways']!='none': masks[d['victim_ways']].add(d['victim_mask'])
if not v: print("no data"); sys.exit(0)
ways_total = WT[0]; per_way = 60/ways_total  # MiB per way on this host
cv = lambda x: 100*st.stdev(x)/st.mean(x) if len(x)>1 else 0.0
MiB = lambda b: b/2**20
wsss = sorted({k[1] for k in v}); kvs = sorted({k[0] for k in v if k[0]!='none'}, key=int)
print(f"host geometry: {ways_total} ways, {per_way:.1f} MiB/way, masks {dict((k,sorted(s)) for k,s in masks.items())}")
print(f"\n{'victim ways':>11} {'partition':>10} {'WSS':>6} {'occupancy':>10} {'cost':>8} {'CoV%':>6}")
pts=[]; worstcv=0
for kv in kvs:
    part = int(kv)*per_way
    for w in wsss:
        c = v.get((kv,w)); u = v.get(('none',w))
        if not c or not u: continue
        cost = 100*(st.median(c)/st.median(u)-1)
        occ = 100*MiB(w)/part
        worstcv=max(worstcv, cv(c), cv(u))
        pts.append((occ,cost,int(kv)))
        print(f"{kv:>11} {part:9.0f}M {MiB(w):5.0f}M {occ:9.0f}% {cost:+7.1f}% {cv(c):6.2f}")
print("\n=== registered checks ===")
u16 = v.get(('none',16777216))
if u16:
    m=st.median(u16)
    print(f"INSTRUMENT unconfined @16 MiB = {m:.3f}, window [77.05, 81.81] -> "
          f"{'PASS' if 77.05<=m<=81.81 else 'MISS'}")
print(f"observed worst CoV = {worstcv:.2f}% (basis assumed <=0.66%) -> "
      f"{'within basis' if worstcv<=0.66 else 'EXCEEDS -- affected cells unresolved per registration'}")
lo=[c for o,c,_ in pts if o<=60]; hi=[c for o,c,_ in pts if o>=85]
if lo and hi:
    p1 = max(lo)<=3 and min(hi)>=8
    print(f"P1 knee travels: occ<=60% max cost {max(lo):+.1f}% (need <=3); "
          f"occ>=85% min cost {min(hi):+.1f}% (need >=8) -> {'HOLDS' if p1 else 'fails'}")
# P2: cells at similar occupancy, different way counts
print("\nP2 occupancy is the variable -- cells grouped by occupancy band:")
bands=[(0,30),(30,50),(50,70),(70,95),(95,150),(150,300)]
p2ok=True
for a,b in bands:
    g=[(o,c,k) for o,c,k in pts if a<=o<b]
    if len(g)>=2:
        spread=max(c for _,c,_ in g)-min(c for _,c,_ in g)
        if spread>5: p2ok=False
        print(f"  {a:3d}-{b:3d}%: " + ", ".join(f"{k}w@{o:.0f}%={c:+.1f}%" for o,c,k in sorted(g))
              + f"   spread {spread:.1f} pts{'' if spread<=5 else '  <-- >5'}")
print(f"P2 -> {'HOLDS' if p2ok else 'fails'} (all multi-cell bands within 5 points)")
