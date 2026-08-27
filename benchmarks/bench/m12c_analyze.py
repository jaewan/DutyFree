#!/usr/bin/env python3
"""M12c: isolate STREAM residency with a pinned table, to test P1' (proxy validity).
Pre-registration: experiments/asplos/M12_ISOPROTECTION_PREREG_2026-08-28.md, amendment 2"""
import json, statistics as st, sys, collections
path = sys.argv[1] if len(sys.argv) > 1 else "../data/m12c_streamresid/m12c.jsonl"
cost = collections.defaultdict(list); occ = collections.defaultdict(list)
for line in open(path):
    line = line.strip()
    if not line: continue
    d = json.loads(line)
    assert d['table'] == d['table_instantiated']
    k = (d['mask'], d['table'], d['stream'])
    cost[k].append(d['record']['active_cycles_per_access'])
    if d['mask'] != 'none': occ[k].append(d['llc_occ_median'])
MiB = lambda b: b / 2**20
cv = lambda x: 100*st.stdev(x)/st.mean(x) if len(x) > 1 else 0.0
tables = sorted({k[1] for k in occ})
print("=== stream residency under the 8-way (128 MiB) mask, table pinned ===")
print(f"{'table':>7} {'n':>3} {'occ ret':>8} {'occ fl':>7} {'ratio':>6} "
      f"{'stream ret':>11} {'stream fl':>10} {'removed':>8} {'CoV r/f':>11}")
R = {}
for t in tables:
    r, f = occ[('b8', t, 'retain')], occ[('b8', t, 'flush')]
    if not r or not f: continue
    mr, mf = MiB(st.median(r)), MiB(st.median(f)); R[t] = mf/mr
    sr, sf = mr - MiB(t), mf - MiB(t)
    print(f"{MiB(t):7.0f} {min(len(r),len(f)):3d} {mr:8.1f} {mf:7.1f} {mf/mr:6.3f} "
          f"{sr:11.1f} {sf:10.1f} {100*(1-sf/sr) if sr else 0:7.0f}% {cv(r):5.1f}/{cv(f):.1f}")
print("  (stream = occupancy - table; valid because the table is <= 1/16 of the mask)")
print("\n=== cost, for completeness ===")
for t in tables:
    for m in ('none','b8'):
        r, f = cost[(m,t,'retain')], cost[(m,t,'flush')]
        if r and f:
            print(f"  {MiB(t):5.0f} MiB {m:>5}: retain {st.median(r):7.3f}  flush {st.median(f):7.3f}  "
                  f"proxy {100*(st.median(f)/st.median(r)-1):+.1f}%")
print("\n=== registered check ===")
T4 = 4194304
if T4 in R:
    print(f"P1' occ(flush)/occ(retain) at 4 MiB = {R[T4]:.3f}, need <= 0.60 -> "
          f"{'HOLDS' if R[T4] <= 0.60 else 'FAILS'}")
    ocv = [cv(v) for v in occ.values() if len(v) > 2]
    print(f"   occupancy CoV: median {st.median(ocv):.1f}%, worst {max(ocv):.1f}%")
    if max(ocv) > 20:
        print("   NOTE: occupancy CoV exceeds 20%, so a 0.60 threshold is near this")
        print("   instrument's resolution -- read the direction, not the exact ratio.")
