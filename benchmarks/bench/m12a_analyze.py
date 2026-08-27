#!/usr/bin/env python3
"""M12 pass A: does the label buy the tenant anything at a mask that protects
the neighbour? Primary metric is CMT occupancy; cost is secondary and caveated.
Pre-registration: experiments/asplos/M12_ISOPROTECTION_PREREG_2026-08-28.md (+ amendment 1)"""
import json, statistics as st, sys, collections
path = sys.argv[1] if len(sys.argv) > 1 else "../data/m12a_isocost/m12a.jsonl"
MASK_MIB = 128  # b8 = 8 of 20 ways x 16 MiB
cost = collections.defaultdict(list); occ = collections.defaultdict(list)
bw = collections.defaultdict(list); wall = collections.defaultdict(list)
for line in open(path):
    line = line.strip()
    if not line: continue
    d = json.loads(line)
    assert d['table'] == d['table_instantiated'], "silently rounded table"
    k = (d['mask'], d['table'], d['stream'])
    cost[k].append(d['record']['active_cycles_per_access'])
    bw[k].append(d['record']['stream_bandwidth_gbps'])
    wall[k].append(float(d['proc_wall_s']))
    if d['mask'] != 'none': occ[k].append(d['llc_occ_median'])
tables = sorted({t for _, t, _ in cost})
MiB = lambda b: b / 2**20

print("=== PRIMARY: F's LLC occupancy under the 8-way (128 MiB) mask ===")
print(f"{'table':>9} {'n':>3} {'retain MiB':>11} {'flush MiB':>10} {'flush/retain':>13} {'CoV r/f':>12}")
for t in tables:
    r, f = occ[('b8', t, 'retain')], occ[('b8', t, 'flush')]
    if not r or not f: continue
    mr, mf = st.median(r), st.median(f)
    cv = lambda x: 100*st.stdev(x)/st.mean(x) if len(x) > 1 else 0
    print(f"{MiB(t):9.0f} {min(len(r),len(f)):3d} {MiB(mr):11.1f} {MiB(mf):10.1f} "
          f"{mf/mr:13.3f} {cv(r):5.1f}/{cv(f):.1f}")

print("\n=== SECONDARY (caveated): F's cost, cyc/access ===")
print(f"{'table':>9} {'mask':>5} {'n':>3} {'retain':>9} {'flush':>9} {'proxy chg':>10} {'CoV r/f':>12}")
C = {}
for t in tables:
    for m in ('none', 'b8'):
        r, f = cost[(m, t, 'retain')], cost[(m, t, 'flush')]
        if not r or not f: continue
        C[(m, t, 'retain')], C[(m, t, 'flush')] = st.median(r), st.median(f)
        cv = lambda x: 100*st.stdev(x)/st.mean(x) if len(x) > 1 else 0
        print(f"{MiB(t):9.0f} {m:>5} {min(len(r),len(f)):3d} {st.median(r):9.3f} {st.median(f):9.3f} "
              f"{100*(st.median(f)/st.median(r)-1):+9.1f}% {cv(r):5.1f}/{cv(f):.1f}")

allcv = [100*st.stdev(v)/st.mean(v) for v in cost.values() if len(v) > 2]
worst = max(allcv) if allcv else 0.0
if allcv:
    print(f"\ncost CoV: median {st.median(allcv):.2f}%, worst {worst:.2f}%  "
          f"(P2's threshold was calibrated against a worst case of 8.0%)")
else:
    print("\ncost CoV: not enough reps yet")
readable = bool(allcv) and worst <= 8.0
if not readable:
    print("  !! worst CoV exceeds 8.0% -> per amendment 1, P2 is UNREADABLE, not evaluated")

print("\nstream bandwidth (checks the 1 GiB fact stays a stream, not resident):")
for t in tables:
    v = bw[('b8', t, 'retain')]
    if v: print(f"  b8 {MiB(t):5.0f} MiB retain: {st.median(v):.2f} GB/s")

print("\n=== registered checks ===")
T_SMALL, T_EQ = 33554432, 134217728
if occ[('b8', T_SMALL, 'retain')] and occ[('b8', T_SMALL, 'flush')]:
    mr = st.median(occ[('b8', T_SMALL, 'retain')]); mf = st.median(occ[('b8', T_SMALL, 'flush')])
    drop = 100*(1 - mf/mr)
    print(f"P1 occupancy: at 32 MiB, flush is {drop:+.1f}% vs retain "
          f"({MiB(mf):.1f} vs {MiB(mr):.1f} MiB); need >= 25% lower -> "
          f"{'HOLDS' if drop >= 25 else 'FAILS'}")
if all((('b8', t, s) in C) for t in (T_SMALL, T_EQ) for s in ('retain', 'flush')):
    gain_eq = C[('b8', T_EQ, 'retain')] - C[('b8', T_EQ, 'flush')]
    gain_sm = C[('b8', T_SMALL, 'retain')] - C[('b8', T_SMALL, 'flush')]
    dod = 100 * (gain_eq - gain_sm) / C[('b8', T_EQ, 'retain')]
    print(f"P2 sweet spot: label benefit at table=mask minus at table=mask/4 = "
          f"{dod:+.1f}% of the 128 MiB retain baseline; need >= +8% -> "
          f"{('HOLDS' if dod >= 8 else 'fails') if readable else 'UNREADABLE (CoV)'}")
    net = C[('b8', T_EQ, 'flush')] - C[('b8', T_EQ, 'retain')]
    print(f"P3 expected null: net cost at table=mask is {100*net/C[('b8',T_EQ,'retain')]:+.1f}% "
          f"-> flush is {'NOT lower (as expected)' if net >= 0 else 'LOWER (P3 broken -- label wins net of its own proxy charge)'}")
print("\nduration-bias audit (amendment 1): occupancy median vs max, and wall time")
for t in tables:
    for s in ('retain', 'flush'):
        o = occ[('b8', t, s)]; w = wall[('b8', t, s)]
        if o and w: print(f"  b8 {MiB(t):5.0f} MiB {s:>6}: occ_med {MiB(st.median(o)):6.1f} MiB, wall {st.median(w):.2f} s")
