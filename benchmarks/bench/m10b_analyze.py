import json, statistics as st, collections, sys
c=collections.defaultdict(list)
for l in open('/home/domin/DutyFree/benchmarks/data/m10b_control/m10b.jsonl'):
    d=json.loads(l)
    assert d['table']==d['table_instantiated']
    c[(d['arm'],d['table'])].append(d['record']['active_cycles_per_access'])
T={4194304:'4 MiB',8388608:'8 MiB',134217728:'128 MiB'}
R={}
print(f"{'table':>9} " + "".join(f"{a:>10}" for a in ('b2','b4','b8')) + f"{'none':>10}")
for t in sorted(T):
    if not c[('none',t)]: continue
    b=st.median(c[('none',t)]); row=""
    for a in ('b2','b4','b8'):
        if c[(a,t)]: R[(a,t)]=st.median(c[(a,t)])/b; row+=f"{R[(a,t)]:10.4f}"
        else: row+=f"{'-':>10}"
    print(f"{T[t]:>9} {row}{b:10.2f}")
n=min(len(v) for v in c.values())
print(f"\nn per cell (min) = {n}")
print("\n=== registered checks ===")
ctl=[(a,t) for a in ('b2','b4','b8') for t in (4194304,8388608) if (a,t) in R]
p3=all(R[k]<=1.10 for k in ctl)
print(f"P3' corrected control: R(4 MiB), R(8 MiB) <= 1.10 under all masks -> {'HOLDS' if p3 else 'FAILS'}")
for k in ctl: print(f"     {k[0]} {T[k[1]]:>7}: {R[k]:.4f}" + ("" if R[k]<=1.10 else "   <-- over"))
t=134217728
if all((a,t) in R for a in ('b2','b4','b8')):
    r2,r4,r8=R[('b2',t)],R[('b4',t)],R[('b8',t)]
    print(f"\n  fixed 128 MiB table:  b2 {r2:.4f}  b4 {r4:.4f}  b8 {r8:.4f}")
    p1=(r2>r4>r8) and (r2-r8)>=0.15
    p2=(max(r2,r4,r8)-min(r2,r4,r8))<=0.08
    print(f"P1' mask-capacity (strictly ordered b2>b4>b8 and b2-b8 >= 0.15) -> {'HOLDS' if p1 else 'fails'}"
          f"   [ordered={r2>r4>r8}, spread={r2-r8:.4f}]")
    print(f"P2' private-L2 (spread <= 0.08) -> {'HOLDS' if p2 else 'fails'}   [spread={max(r2,r4,r8)-min(r2,r4,r8):.4f}]")
    print()
    if p3 and p1: print("=> CONSEQUENCE: mask-capacity mechanism ESTABLISHED; §3's sentence stands, cited to M10+M10b.")
    elif p3 and p2: print("=> CONSEQUENCE: §3's mechanism sentence is WRONG; replace with aggregate-private-L2.")
    elif not p3: print("=> CONSEQUENCE: both runs void; DELETE §3's mask-capacity sentence as unsupported.")
    else: print("=> CONSEQUENCE: neither P1' nor P2' fires cleanly; report both boundaries, attribute neither.")
