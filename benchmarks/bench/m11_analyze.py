#!/usr/bin/env python3
"""M11: localise the M6-vs-M8 F-cost contradiction.
Pre-registration: experiments/asplos/M11_FACTSIZE_PREREG_2026-08-28.md"""
import json, statistics as st, sys, collections
path = sys.argv[1] if len(sys.argv) > 1 else "../data/m11_factsize/m11.jsonl"
c = collections.defaultdict(list); bw = collections.defaultdict(list)
for line in open(path):
    line = line.strip()
    if not line: continue
    d = json.loads(line)
    assert d['table'] == d['table_instantiated']
    k = (d['arm'], d['fact'], f"{d['reps']}/{d['warmups']}")
    c[k].append(d['record']['active_cycles_per_access'])
    bw[k].append(d['record']['stream_bandwidth_gbps'])
C = {}
print(f"{'fact':>5} {'r/w':>5} {'n':>3} {'none':>8} {'b2':>8} {'b4':>8} {'C(b2)%':>8} {'C(b4)%':>8} {'BW':>7}")
for fact in ('256m','1g'):
    for rw in ('1/2','4/1'):
        n = c[('none',fact,rw)]
        if not n: continue
        b = st.median(n)
        for a in ('b2','b4'):
            if c[(a,fact,rw)]: C[(a,fact,rw)] = 100*(st.median(c[(a,fact,rw)])/b - 1)
        print(f"{fact:>5} {rw:>5} {len(n):3d} {b:8.2f} "
              f"{st.median(c[('b2',fact,rw)]):8.2f} {st.median(c[('b4',fact,rw)]):8.2f} "
              f"{C[('b2',fact,rw)]:8.1f} {C[('b4',fact,rw)]:8.1f} {st.median(bw[('none',fact,rw)]):7.2f}")
print("\n  M6 pass A's config = 256m, 4/1, b2   |   M8's config = 1g, 1/2, b4")
print("\n=== registered checks ===")
v = st.median(c[('none','1g','1/2')])
print(f"INSTRUMENT none/1g/(1/2) = {v:.3f}, window [43.04, 50.52] (M8 46.782 +/-8%) -> "
      f"{'PASS' if 43.04 <= v <= 50.52 else 'MISS'}")
m6, m8 = C[('b2','256m','4/1')], C[('b4','1g','1/2')]
p1 = m6 <= 15 and m8 >= 30
print(f"P1 both endpoints reproduce: M6-config {m6:.1f}% <= 15 and M8-config {m8:.1f}% >= 30 -> "
      f"{'HOLDS' if p1 else 'fails'}")
print(f"   (M6 reported +7.5%; M8 reported +40%)")
deltas = []
for a in ('b2','b4'):
    for rw in ('1/2','4/1'):
        d = C[(a,'1g',rw)] - C[(a,'256m',rw)]; deltas.append(d)
        print(f"P2 fact-size term, {a} at r/w {rw}: {C[('' if False else a,'1g',rw)]:.1f} - "
              f"{C[(a,'256m',rw)]:.1f} = {d:+.1f} pp")
p2 = all(d >= 15 for d in deltas)
print(f"P2 fact size >= 15 pp everywhere -> {'HOLDS' if p2 else 'fails'}  (min {min(deltas):+.1f} pp)")
p3 = C[('b2','1g','1/2')] > C[('b4','1g','1/2')]
print(f"P3 monotone at 1g,1/2: C(b2) {C[('b2','1g','1/2')]:.1f} > C(b4) {C[('b4','1g','1/2')]:.1f} -> "
      f"{'HOLDS' if p3 else 'FAILS'}")
rwd = []
for a in ('b2','b4'):
    for fact in ('256m','1g'):
        d = abs(C[(a,fact,'4/1')] - C[(a,fact,'1/2')]); rwd.append(d)
        print(f"P4 reps/warmups term, {a} at {fact}: {d:.1f} pp")
p4 = all(d < 8 for d in rwd)
print(f"P4 reps/warmups < 8 pp everywhere -> {'HOLDS' if p4 else 'fails'}  (max {max(rwd):.1f} pp)")
print()
if p1 and p2 and p3:
    print("=> CONSEQUENCE: M6 pass A's F-cost is measured on a partly-resident stream and must")
    print("   NOT be quoted as the price of the shipped knob. Re-price contribution (2) from the")
    print("   1 GiB arms; this RAISES CAT's cost to F and narrows its margin over the label.")
    print("   M6 pass B (V's harm) is unaffected -- it measures V, not F.")
elif not p3:
    print("=> CONSEQUENCE: apparatus non-monotone; BOTH M6's and M8's F-costs withdrawn pending re-run.")
elif not p2 and not p4:
    print("=> CONSEQUENCE: discrepancy is in warm-up state, not footprint. Same action on M6's numbers.")
else:
    print("=> CONSEQUENCE: mixed; report both terms and quote no single price for CAT.")
