#!/usr/bin/env python3
"""(1) Victim L3 occupancy UNDER the CAT arms, and (2) the other-CCX re-measure.

Pre-registration: AMD_CATOCC_PREREG_2026-08-30.md

Why (1): AMD_L3OCC found the harm is L3 EVICTION (victim occupancy 3568 -> 196 KB).
AMD_NARROWMASK found a mask confining the streamer to 1 of 16 ways still leaves a
10.3x residual, flat below four ways. Those cannot both be simple: if the streamer
can only allocate in one way it cannot evict the victim from the other fifteen.
Measuring occupancy under the mask decides which.

Why (2): BERGAMO_BACKINVAL's P2 ("the harm is L3-domain-local") rests on
other-CCX = 1.31x, but AMD_L3OCC's other-CCX cell read 618.7 against 71.8 -- an
8.6x disagreement in one cell. P2 is marked provisional and is re-measured here
with THP pinned and the machine verified idle.
"""
import json, os, statistics as st, subprocess, sys, time

R = "/sys/fs/resctrl"
VG, AG = f"{R}/mon_groups/co_v", f"{R}/mon_groups/co_a"
CV, CA = f"{R}/cat_v", f"{R}/cat_a"          # allocation groups (CAT arms only)
BIN = "/home/domin/tmp_dutyfree_exp/bin"
V, A = f"{BIN}/victim", f"{BIN}/aggressor"
SAME, OTHER = "1,2,3,4,5,6,7", "9,10,11,12,13,14,15"
VDUR, VWARM, SETTLE, ADUR = 4, 1, 2, 12
FULL = "ffff"

# (name, aggressor cores, victim L3 mask, aggressor L3 mask)
ARMS = [("quiescent", None,  None,   None),
        ("wb",        SAME,  None,   None),
        ("cat8",      SAME,  "ff00", "00ff"),
        ("cat4",      SAME,  "fff0", "000f"),
        ("cat1",      SAME,  "fffe", "0001"),
        ("other",     OTHER, None,   None)]


def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True)

def setup():
    sh("pkill -f 'bin/aggressor'"); time.sleep(0.3)
    for g, c in ((VG, "0"), (AG, SAME)):
        os.makedirs(g, exist_ok=True); open(f"{g}/cpus_list", "w").write(c)

def teardown():
    sh("pkill -f 'bin/aggressor'"); time.sleep(0.3)
    for g in (VG, AG, CV, CA):
        try: os.rmdir(g)
        except OSError: pass

def set_masks(vmask, amask, acores):
    """Create/refresh CAT allocation groups; remove them when no mask is asked."""
    if vmask is None:
        for g in (CV, CA):
            try: os.rmdir(g)
            except OSError: pass
        return None, None
    for g, cpus, m in ((CV, "0", vmask), (CA, acores, amask)):
        os.makedirs(g, exist_ok=True)
        open(f"{g}/cpus_list", "w").write(cpus)
        open(f"{g}/schemata", "w").write(f"L3:0={m}\n")
    return readback(CV), readback(CA)

def readback(g):
    """Value-compare, never text: the kernel normalises 00ff -> ff and indents."""
    try:
        for line in open(f"{g}/schemata"):
            t = line.strip()
            if t.startswith("L3:"):
                return t.split(";")[0].split("=")[1].strip().lower()
    except OSError:
        pass
    return None

def occ(g, dom="00"):
    try: return int(open(f"{g}/mon_data/mon_L3_{dom}/llc_occupancy").read().strip())
    except (OSError, ValueError): return None

def thp():
    s = open("/sys/kernel/mm/transparent_hugepage/enabled").read()
    return next((t.strip("[]") for t in s.split() if t.startswith("[")), "?")

def one(name, acores, vmask, amask, wss, rep):
    gotv, gota = set_masks(vmask, amask, acores)
    if acores: open(f"{AG}/cpus_list", "w").write(acores)
    agg = None; bw = None
    if acores:
        agg = subprocess.Popen(f"{A} -m wb_load -t 7 -c {acores} -N 2 -s 64 -d {ADUR} "
                               f"> /tmp/co_agg.log 2>&1", shell=True)
        time.sleep(SETTLE)
    vp = subprocess.Popen(f"{V} -c 0 -w {wss} -P -d {VDUR} -W {VWARM}",
                          shell=True, stdout=subprocess.PIPE, text=True)
    samples, t0 = [], time.time()
    while vp.poll() is None and time.time() - t0 < VDUR + VWARM + 4:
        time.sleep(0.25)
        if time.time() - t0 > VWARM + 0.5:
            o = occ(VG)
            if o is not None: samples.append(o)
    out, _ = vp.communicate()
    line = next((l for l in out.splitlines() if l.startswith("VICTIM")), "")
    d = {}
    for t in line.split():
        if "=" in t:
            k, v = t.split("=", 1)
            try: d[k] = float(v)
            except ValueError: d[k] = v
    if agg is not None:
        agg.wait(timeout=ADUR + 15)
        for l in open("/tmp/co_agg.log", errors="replace"):
            if l.startswith("aggregate:"): bw = float(l.split()[1])
    hit, miss = d.get("l2_hit"), d.get("l2_miss")
    med = st.median(samples) if samples else None
    rec = dict(arm=name, wss_kb=wss, rep=rep, thp=thp(),
               cyc_per_access=d.get("cyc_per_access"),
               l2_hit=hit, l2_miss=miss,
               hit_rate=(100 * hit / (hit + miss)) if hit is not None and (hit + miss) else None,
               agg_gbps=bw, victim_l3_occ_median=med, victim_l3_occ_n=len(samples),
               vmask_set=vmask, vmask_readback=gotv,
               amask_set=amask, amask_readback=gota,
               mask_ok=(vmask is None) or
                       (gotv is not None and int(gotv, 16) == int(vmask, 16) and
                        gota is not None and int(gota, 16) == int(amask, 16)))
    print(f"  {name:9s} wss={wss:5d} rep{rep:2d} cyc/acc={rec['cyc_per_access'] or 0:8.2f} "
          f"L3occ={((med or 0)/1024):8.1f}KB L2hit%={rec['hit_rate'] or 0:6.2f} "
          f"bw={bw or 0:6.2f} mask_ok={rec['mask_ok']}", flush=True)
    return rec

def main():
    reps = int(sys.argv[1]); out = sys.argv[2]
    if os.path.exists(out):
        print("FAIL exists (A6.19)", file=sys.stderr); return 2
    setup(); recs = []
    try:
        for wss in (4096, 512):
            for (n, ac, vm, am) in ARMS:
                for r in range(1, reps + 1):
                    recs.append(one(n, ac, vm, am, wss, r))
    finally:
        teardown()
        with open(out, "w") as f:
            for x in recs: f.write(json.dumps(x) + "\n")
        print(f"wrote {len(recs)} -> {out}")
    return 0

sys.exit(main())
