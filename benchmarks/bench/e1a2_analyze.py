#!/usr/bin/env python3
"""E1 pass A2: tenant cost as the median of per-pair ratios.
Pre-registration: E1_FRONTIER_PREREG_2026-08-28.md, amendment 1."""
import json, statistics as st, sys, collections
path = sys.argv[1] if len(sys.argv) > 1 else "../data/e1a2_paired/e1a2.jsonl"
p = collections.defaultdict(list); cpus=set(); order=collections.Counter()
for l in open(path):
    l=l.strip()
    if not l: continue
    d=json.loads(l)
    p[d['width']].append(d); cpus.add(d['cpus_masked']); order[(d['width'],d['order'])]+=1
cv=lambda x: 100*st.stdev(x)/st.mean(x) if len(x)>1 else 0.0
print(f"{'tenant ways':>12} {'MiB':>5} {'pairs':>6} {'median ratio':>13} {'cost':>8} "
      f"{'ratio CoV':>10} {'order balance':>14}")
R={}
for w in sorted(p):
    rs=[d['ratio'] for d in p[w]]
    R[w]=st.median(rs)
    nf=order[(w,'none_first')]; mf=order[(w,'masked_first')]
    flag = '' if cv(rs) < 3 else '   <-- CoV>3%, samples below'
    print(f"{w:>12} {w*16:>5} {len(rs):>6} {R[w]:13.4f} {100*(R[w]-1):+7.1f}% "
          f"{cv(rs):9.2f}% {f'{nf}/{mf}':>14}{flag}")
print(f"\ncpus_masked values seen: {sorted(cpus)}  (must be exactly ['32-47'])")
for w in sorted(p):
    rs=[d['ratio'] for d in p[w]]
    if cv(rs) >= 3:
        print(f"\n  w={w} individual pairs (registered: print rather than summarise):")
        for d in sorted(p[w], key=lambda x:x['rep']):
            print(f"    rep{d['rep']:2d} {d['order']:>13}  none {d['cyc_none']:7.3f}  "
                  f"masked {d['cyc_masked']:7.3f}  ratio {d['ratio']:.4f}")
print("\n=== registered checks ===")
if 8 in R:
    ok = abs(R[8]-1.1697)/1.1697 <= 0.03
    print(f"CHECK ratio at 8 ways = {R[8]:.4f}, must be within +/-3% of 1.1697 -> "
          f"{'PASS' if ok else 'MISS -- pass A2 void, quote E2 only'}")
allcv=[cv([d['ratio'] for d in p[w]]) for w in p]
print(f"per-pair ratio CoV: max {max(allcv):.2f}% (registered expectation <3%) -> "
      f"{'met' if max(allcv)<3 else 'exceeded; those widths printed individually above'}")
if len(R)>=2:
    ks=sorted(R); mono=all(R[ks[i]] >= R[ks[i+1]]-0.005 for i in range(len(ks)-1))
    print(f"monotone in ways (narrower costs more): {mono}")
print("\n=== the corrected frontier gates at the 170 MB victim ===")
CVv={2:0.1,4:0.4,8:13.1,12:65.2,16:137.7}   # pass B, unaffected
print(f"{'tenant ways':>12} {'C_T':>8} {'cheap?':>8} {'C_V':>8} {'cheap?':>8} {'both?':>7}")
for w in sorted(R):
    ct=100*(R[w]-1); cvv=CVv[w]
    tc=ct<=10; vc=cvv<=5
    print(f"{w:>12} {ct:+7.1f}% {'yes' if tc else 'NO':>8} {cvv:+7.1f}% {'yes' if vc else 'NO':>8} "
          f"{'YES' if tc and vc else '--':>7}")
free=[w for w in R if 100*(R[w]-1)<=10 and CVv[w]<=5]
print(f"\n  splits cheap for both: {free if free else 'NONE'} -> "
      f"{'P2 -- claim collapses' if free else 'P1 holds'}")
