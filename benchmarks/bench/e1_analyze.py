#!/usr/bin/env python3
"""E1: the allocation frontier. Is there a static split that satisfies both parties?
Pre-registration: experiments/asplos/E1_FRONTIER_PREREG_2026-08-28.md"""
import json, statistics as st, sys, collections
A = sys.argv[1] if len(sys.argv) > 1 else "../data/e1a_tenantcost/e1a.jsonl"
Bp = sys.argv[2] if len(sys.argv) > 2 else "../data/e1b_frontier/e1b.jsonl"
WAY = 16  # MiB per way
cv = lambda x: 100*st.stdev(x)/st.mean(x) if len(x) > 1 else 0.0

# ---- pass A: tenant cost vs its own ways
ta = collections.defaultdict(list)
for l in open(A):
    l=l.strip()
    if not l: continue
    d=json.loads(l); assert d['table']==d['table_instantiated']
    ta[d['arm']].append(d['record']['active_cycles_per_access'])
CT = {}
if ta.get('none'):
    base = st.median(ta['none'])
    print("=== pass A: the tenant's own cost, table 128 MiB ===")
    print(f"{'tenant ways':>12} {'MiB':>6} {'n':>3} {'cyc/acc':>9} {'cost':>7} {'CoV%':>6}")
    print(f"{'20 (none)':>12} {320:>6} {len(ta['none']):3d} {base:9.3f} {'--':>7} {cv(ta['none']):6.2f}")
    for k in (2,4,8,12,16):
        v = ta.get(f'b{k}', [])
        if not v: continue
        CT[k] = 100*(st.median(v)/base - 1)
        print(f"{k:>12} {k*WAY:>6} {len(v):3d} {st.median(v):9.3f} {CT[k]:+6.1f}% {cv(v):6.2f}")

# ---- pass B: the victim, three quantities per split
try: lines = [l for l in open(Bp) if l.strip()]
except FileNotFoundError: lines = []
vb = collections.defaultdict(list); live = collections.Counter()
for l in lines:
    d=json.loads(l)
    if d['victim_cyc_per_load'] is None: continue
    vb[(d['split'], d['wss'], d['mode'])].append(d['victim_cyc_per_load'])
    L=d.get('tenant_liveness')
    if isinstance(L,dict): live[bool(L['alive_at_end'] and L['warmed'])]+=1
if not vb:
    print("\n(pass B has no records yet)"); sys.exit(0)
wsss = sorted({k[1] for k in vb}); splits=[2,4,8,12,16]
print("\n=== pass B: the frontier ===")
CV={}; H={}
for w in wsss:
    unc = vb.get(('none', w, 'none'))
    if not unc: continue
    u = st.median(unc)
    print(f"\n victim WSS {w/2**20:.0f} MB   unconfined {u:.3f} cyc/load (n={len(unc)}, CoV {cv(unc):.2f}%)")
    print(f"{'tenant ways':>12} {'victim ways':>12} {'occupancy':>10} {'C_V':>8} {'C_T':>8} "
          f"{'H retain':>9} {'H flush':>8}")
    for k in splits:
        conf = vb.get((str(k), w, 'none')); r = vb.get((str(k), w, 'retain')); f = vb.get((str(k), w, 'flush'))
        if not conf: continue
        c = st.median(conf); CV[(k,w)] = 100*(c/u - 1)
        vw = (20-k)*WAY
        occ = 100*(w/2**20)/vw
        hr = st.median(r)/c if r else float('nan'); hf = st.median(f)/c if f else float('nan')
        H[(k,w,'retain')] = hr; H[(k,w,'flush')] = hf
        ct = CT.get(k, float('nan'))
        print(f"{k:>12} {20-k:>12} {occ:9.0f}% {CV[(k,w)]:+7.1f}% {ct:+7.1f}% {hr:9.3f} {hf:8.3f}")
print("\n  C_V = victim's own confinement cost (no tenant).  C_T = tenant's cost (pass A).")
print("  H   = victim's harm while the tenant runs, measured against its OWN confined baseline.")
print(f"\ntenant liveness ok: {live[True]}/{live[True]+live[False]}")

print("\n=== registered checks ===")
u170 = vb.get(('none', 178257920, 'none'))
if u170:
    m = st.median(u170)
    print(f"INSTRUMENT victim unconfined @170 MB = {m:.3f}, window [75.72, 80.40] -> "
          f"{'PASS' if 75.72 <= m <= 80.40 else 'MISS'}")
w170 = 178257920
free = [k for k in splits if (k,w170) in CV and k in CT
        and CV[(k,w170)] <= 5 and CT[k] <= 10 and H.get((k,w170,'retain'), 9) <= 1.05]
if any((k,w170) in CV for k in splits):
    print(f"P1/P2 splits cheap for BOTH (C_V<=5%, C_T<=10%) and protecting (H<=1.05): "
          f"{free if free else 'NONE'}")
    print(f"   -> {'P2 HOLDS -- the trade-off claim COLLAPSES' if free else 'P1 HOLDS -- no free split'}")
tight=[(k,w) for (k,w) in CV if 100*(w/2**20)/((20-k)*WAY) >= 80]
loose=[(k,w) for (k,w) in CV if 100*(w/2**20)/((20-k)*WAY) <= 50]
if tight and loose:
    lo=max(CV[x] for x in loose); hi=min(CV[x] for x in tight)
    print(f"P3 tight-fit: loose cells (occ<=50%) max C_V = {lo:+.1f}% (need <=3); "
          f"tight cells (occ>=80%) min C_V = {hi:+.1f}% (need >=8) -> "
          f"{'HOLDS' if lo<=3 and hi>=8 else 'fails'}")
if (8,w170) in CV and 8 in CT:
    print(f"P4 vs M12 at k=8, 170 MB: C_T {CT[8]:+.1f}% (M12 16.7%, +/-5), "
          f"C_V {CV[(8,w170)]:+.1f}% (M12 13.1%, +/-4) -> "
          f"{'HOLDS' if abs(CT[8]-16.7)<=5 and abs(CV[(8,w170)]-13.1)<=4 else 'fails'}")
hs=[(k,H[(k,w170,'retain')]) for k in splits if (k,w170,'retain') in H]
if len(hs)>1:
    mono=all(hs[i+1][1] <= hs[i][1]+0.02 for i in range(len(hs)-1))
    print(f"P5 monotonicity of H as victim gains ways: {[f'{k}:{v:.3f}' for k,v in hs]} -> "
          f"{'HOLDS' if mono else 'FAILS -- frontier void'}")
