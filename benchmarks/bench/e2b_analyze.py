#!/usr/bin/env python3
"""E2B: victim decomposition at a fixed 1 GiB stream, tenant footprint swept.
Pre-registration: experiments/asplos/E2B_FOOTPRINT_PREREG_2026-08-28.md"""
import json, statistics as st, sys, collections
path = sys.argv[1] if len(sys.argv) > 1 else "../data/e2b_footprint/e2b.jsonl"
v = collections.defaultdict(list); live = collections.Counter(); inst = collections.defaultdict(set)
for l in open(path):
    l=l.strip()
    if not l: continue
    d=json.loads(l)
    if d['victim_cyc_per_load'] is None: continue
    v[(d['kind'], d['table'], d['mode'])].append(d['victim_cyc_per_load'])
    T=d.get('tenant')
    if isinstance(T,dict):
        live[bool(T['alive_at_end'] and T['warmed'])]+=1
        inst[d['table']].add(T.get('table_instantiated'))
base = v.get(('base',0,'none'))
if not base: print("no baseline yet"); sys.exit(0)
u = st.median(base)
cv = lambda x: 100*st.stdev(x)/st.mean(x) if len(x)>1 else 0.0
MiB = lambda b: b/2**20
tables = sorted({k[1] for k in v if k[0]=='t'})
print(f"victim alone: {u:.3f} cyc/load  (n={len(base)}, CoV {cv(base):.2f}%)\n")
print(f"{'tenant table':>13} {'n':>3} {'H retain':>9} {'H flush':>8} {'removed':>8} "
      f"{'CoV r/f':>11} {'instantiated':>13}")
H={}; F={}
for t in tables:
    r,f = v.get(('t',t,'retain')), v.get(('t',t,'flush'))
    if not r or not f: continue
    hr, hf = st.median(r)/u, st.median(f)/u
    H[t]=(hr,hf); F[t]=100*(hr-hf)/(hr-1) if hr>1 else float('nan')
    ok = 'ok' if inst[t]=={t} else f'!! {inst[t]}'
    print(f"{MiB(t):12.0f}M {min(len(r),len(f)):3d} {hr:9.3f} {hf:8.3f} {F[t]:7.1f}% "
          f"{cv(r):5.2f}/{cv(f):.2f} {ok:>13}")
print(f"\ntenant liveness ok: {live[True]}/{live[True]+live[False]}")
print("\n=== registered checks ===")
print(f"INSTRUMENT victim alone = {u:.3f}, window [75.70, 80.38] -> "
      f"{'PASS' if 75.70<=u<=80.38 else 'MISS'}")
T4, T128, T256 = 4194304, 134217728, 268435456
if F:
    ks=sorted(F)
    mono = all(F[ks[i+1]] <= F[ks[i]]+3 for i in range(len(ks)-1))
    ends = (F.get(T4,0) >= 90) and (F.get(T256,100) <= 50)
    print(f"P1 monotone decline, F(4MiB)>=90% and F(256MiB)<=50%: "
          f"F = {', '.join(f'{MiB(k):.0f}M:{F[k]:.1f}%' for k in ks)} -> "
          f"{'HOLDS' if mono and ends else 'fails'} (monotone={mono}, endpoints={ends})")
    hf=[H[k][1] for k in ks]
    p2 = all(hf[i+1] >= hf[i]-0.03 for i in range(len(hf)-1)) and H.get(T256,(0,0))[1] >= 1.8
    print(f"P2 residue grows with footprint, H_flush(256MiB)>=1.8: "
          f"{[f'{x:.3f}' for x in hf]} -> {'HOLDS' if p2 else 'fails'}")
    if T128 in F:
        print(f"P3 arm identity: F(128MiB) = {F[T128]:.1f}% vs M12's 75.3% "
              f"(|d|={abs(F[T128]-75.3):.1f}, need <=8) -> "
              f"{'HOLDS' if abs(F[T128]-75.3)<=8 else 'FAILS -- quarantine'}")
    if T4 in H:
        hf4=H[T4][1]
        print(f"P4 strong form: H_flush(4MiB) = {hf4:.3f}, need <=1.10 -> "
              f"{'HOLDS' if hf4<=1.10 else 'FAILS'}")
        if hf4>1.10:
            print("   !! P4's registered branch: a component that is NEITHER stream residency")
            print("      NOR tenant footprint, scaling with stream volume. Partly revives the")
            print("      M3b transport claim. Two-component account becomes three-component.")
