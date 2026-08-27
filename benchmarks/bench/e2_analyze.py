#!/usr/bin/env python3
"""E2: does M12a's own occupancy sampler, or setup_b vs setup_c, explain the
tenant-cost disagreement? Pre-registration: experiments/asplos/E2_RECONCILE_PREREG_2026-08-28.md"""
import json, statistics as st, sys, collections, math
path = sys.argv[1] if len(sys.argv) > 1 else "../data/e2_reconcile/e2.jsonl"
c = collections.defaultdict(list); ns = collections.defaultdict(list)
for l in open(path):
    l=l.strip()
    if not l: continue
    d=json.loads(l); assert d['table']==d['table_instantiated']
    c[(d['helper'],d['sampler'])].append(d['record']['active_cycles_per_access'])
    ns[(d['helper'],d['sampler'])].append(d['nsamp'])
cv=lambda x:100*st.stdev(x)/st.mean(x) if len(x)>1 else 0.0
n=min(len(v) for v in c.values()) if c else 0
print(f"{'helper':>7} {'sampler':>8} {'n':>3} {'samples/run':>12} {'cyc/acc':>9} {'CoV%':>6} {'cost':>8}")
base={}
for h in ('none','b','c'):
    for s in ('off','on'):
        v=c.get((h,s))
        if not v: continue
        if h=='none': base[s]=st.median(v)
        cost = 100*(st.median(v)/base.get(s, st.median(v))-1) if s in base else float('nan')
        print(f"{h:>7} {s:>8} {len(v):3d} {st.median(ns[(h,s)]):12.0f} {st.median(v):9.3f} "
              f"{cv(v):6.2f} {cost:+7.1f}%")
C = lambda h,s: 100*(st.median(c[(h,s)])/base[s]-1)
res = math.sqrt(2*((1.96+0.84)**2)*(3.27**2)/n) if n else float('nan')
print(f"\nregistered resolution at n={n}: ~{res:.2f}% (threshold everywhere is 4 points)")
print("\n=== registered checks ===")
if c.get(('none','off')):
    v=st.median(c[('none','off')])
    print(f"INSTRUMENT none/sampler-off = {v:.3f}, window [75.83, 80.52] -> "
          f"{'PASS' if 75.83<=v<=80.52 else 'MISS'}")
if all(c.get(k) for k in (('b','on'),('b','off'))):
    d=C('b','on')-C('b','off')
    print(f"P1 sampler inflates (setup_b, on - off) = {d:+.1f} pts, need >=4 -> "
          f"{'HOLDS' if d>=4 else ('unresolved' if abs(d)<4 else 'fails')}")
if all(c.get(k) for k in (('b','off'),('c','off'))):
    d=C('b','off')-C('c','off')
    print(f"P2 helper matters (setup_b - setup_c, sampler off) = {d:+.1f} pts, need >=4 -> "
          f"{'HOLDS' if d>=4 else ('unresolved' if abs(d)<4 else 'fails')}")
if c.get(('b','on')) and c.get(('c','off')):
    a,b_=C('b','on'),C('c','off')
    print(f"P3 endpoints: setup_b+on {a:+.1f}% vs M12a 16.7% (|d|={abs(a-16.7):.1f}); "
          f"setup_c+off {b_:+.1f}% vs E1a 8.7% (|d|={abs(b_-8.7):.1f}) -> "
          f"{'HOLDS' if abs(a-16.7)<=4 and abs(b_-8.7)<=4 else 'fails'}")
if c.get(('none','on')) and c.get(('none','off')):
    d=100*(st.median(c[('none','on')])/st.median(c[('none','off')])-1)
    print(f"P4 no-mask sampler effect = {d:+.1f} pts, need <4 -> "
          f"{'HOLDS' if abs(d)<4 else 'FAILS -- decomposition void'}")
