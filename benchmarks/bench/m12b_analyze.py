#!/usr/bin/env python3
"""M12 pass B: does an 8-way mask on F protect V, and does the label add anything?
Pre-registration: experiments/asplos/M12_ISOPROTECTION_PREREG_2026-08-28.md"""
import json, statistics as st, sys, collections
path = sys.argv[1] if len(sys.argv) > 1 else "../data/m12b_victim/m12b.jsonl"
v = collections.defaultdict(list); live = collections.Counter(); bad = []
for line in open(path):
    line = line.strip()
    if not line: continue
    d = json.loads(line)
    if d['victim_cyc_per_load'] is None: bad.append(d['arm']); continue
    v[d['arm']].append(d['victim_cyc_per_load'])
    L = d.get('f_liveness')
    if isinstance(L, dict):
        live[(d['arm'], L['alive_at_end'], L['warmed'])] += 1
        if not (L['alive_at_end'] and L['warmed']): bad.append(f"{d['arm']} liveness")
ARMS = ['Vnone','Vwide','F_none_retain','F_none_flush','F_wide_retain','F_wide_flush']
base = st.median(v['Vnone']) if v['Vnone'] else None
cv = lambda x: 100*st.stdev(x)/st.mean(x) if len(x) > 1 else 0.0
print(f"{'arm':>15} {'n':>3} {'cyc/load':>9} {'CoV%':>6} {'vs Vnone':>9}")
for a in ARMS:
    if not v[a]: continue
    m = st.median(v[a])
    print(f"{a:>15} {len(v[a]):3d} {m:9.3f} {cv(v[a]):6.2f} {m/base:9.3f}" if base else "")
print("\n=== F liveness audit (the check M6b lacked) ===")
tot = sum(n for n in live.values())
ok = sum(n for (a,al,w),n in live.items() if al and w)
print(f"  co-run records with F alive at end AND warmed: {ok}/{tot}")
for k,n in sorted(live.items()):
    if not (k[1] and k[2]): print(f"  !! {k[0]}: alive={k[1]} warmed={k[2]} x{n}")
if bad: print(f"  !! problems: {collections.Counter(bad)}")
print("\n=== registered checks ===")
if v['Vwide'] and base:
    r = st.median(v['Vwide'])/base
    print(f"P5 partitioning's own cost to V: Vwide/Vnone = {r:.4f}; need within 5% -> "
          f"{'HOLDS' if abs(r-1) <= 0.05 else 'FAILS'}")
if v['F_wide_retain'] and v['F_wide_flush'] and base:
    for s in ('retain','flush'):
        h = st.median(v[f'F_wide_{s}'])/base
        print(f"P4 V under the 8-way mask, stream {s:>6}: {h:.4f}x; need <= 1.05 -> "
              f"{'HOLDS' if h <= 1.05 else 'FAILS'}")
print("\n=== what the label buys V, at each mask ===")
if base:
    for m in ('none','wide'):
        r, f = v[f'F_{m}_retain'], v[f'F_{m}_flush']
        if r and f:
            hr, hf = st.median(r)/base, st.median(f)/base
            print(f"  mask={m:>4}: V harm {hr:.3f}x retained -> {hf:.3f}x non-allocating "
                  f"({100*(hr-hf)/(hr-1) if hr > 1 else 0:.0f}% of the harm removed)")
