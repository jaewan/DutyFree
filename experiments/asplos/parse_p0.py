#!/usr/bin/env python3
# Parse P0-1 de-confound batch. Per run: victim cyc/iter, aggressor CXL BW, back-invals, SF-evicts.
# Tax computed against the MSHR-matched `alone` baseline (vn_*), the clean per-throttle baseline.
import os, re, glob, sys

def field(stats, pat):
    rx = re.compile(pat)
    out = []
    for ln in stats:
        m = rx.search(ln)
        if m:
            parts = ln.split()
            try: out.append((parts[0], float(parts[1])))
            except: pass
    return out

def load(name):
    d = f"/tmp/{name}"
    sp = os.path.join(d, "stats.txt")
    lg = f"/tmp/{name}.log"
    if not (os.path.exists(sp) and os.path.getsize(sp) > 0): return None
    stats = open(sp).read().splitlines()
    # iters from DONE line
    iters = 300000
    if os.path.exists(lg):
        for ln in open(lg):
            m = re.search(r"ITERS=(\d+)", ln)
            if m: iters = int(m.group(1))
    r = {"name": name, "iters": iters}
    # victim = cpu0 (or cpu00) numCycles
    nc = field(stats, r"^system\.cpu0?0?\.numCycles\b")
    r["vcyc"] = nc[0][1] if nc else None
    r["cyciter"] = (r["vcyc"]/iters) if r["vcyc"] else None
    # sim time
    ss = field(stats, r"^simSeconds\b")
    r["simSec"] = ss[0][1] if ss else None
    # per-mem-ctrl bytesRead -> attribute aggressor to the largest (CXL) reader
    br = field(stats, r"bytesRead::total\b")
    br = [(n,v) for (n,v) in br if v > 0]
    br.sort(key=lambda x: -x[1])
    r["memReaders"] = br[:3]
    if br and r["simSec"]:
        r["aggGBps"] = br[0][1] / r["simSec"] / 1e9
    else:
        r["aggGBps"] = None
    # back-invals: SnpCleanInvalid occurrences (sum of matching scalar counters)
    bi = field(stats, r"SnpCleanInvalid")
    r["backinval"] = sum(v for _,v in bi)
    r["backinval_fields"] = [(n,v) for n,v in bi if v>0][:4]
    # SF evictions
    sfe = field(stats, r"SF_Eviction")
    r["sfevict"] = sum(v for _,v in sfe)
    return r

names = ["gate_i3e5","gate_i3e6","vn_m2","vn_m4","vn_m8","vn_nat",
         "h2_m2","h2_m4","h2_m8","h2_m16","h2_nat","val_h2h3"]
rows = {n: load(n) for n in names}

# baseline cyc/iter per MSHR level from vn_*
base = {}
for lvl in ["m2","m4","m8","nat"]:
    r = rows.get(f"vn_{lvl}")
    if r and r["cyciter"]: base[lvl] = r["cyciter"]

print(f"{'run':10} {'cyc/iter':>9} {'tax':>6} {'aggGB/s':>8} {'backinv':>8} {'sfevict':>8} {'simSec':>9}")
for n in names:
    r = rows[n]
    if not r: print(f"{n:10}  (no stats yet)"); continue
    lvl = "nat"
    for k in ["m2","m4","m8","m16"]:
        if k in n: lvl = k if k in base else "nat"
    b = base.get(lvl if lvl in base else "nat")
    tax = (r["cyciter"]/b) if (r["cyciter"] and b) else None
    print(f"{n:10} {r['cyciter'] or -1:9.2f} {tax or -1:6.2f} {r['aggGBps'] or -1:8.3f} "
          f"{r['backinval']:8.0f} {r['sfevict']:8.0f} {r['simSec'] or -1:9.6f}")
print("\nbaselines (vn_* cyc/iter):", base)
# show back-inval field names for the H2 native arm to confirm we grep the right counter
h = rows.get("h2_nat")
if h: print("h2_nat backinval fields:", h["backinval_fields"], "| memReaders:", h["memReaders"])
