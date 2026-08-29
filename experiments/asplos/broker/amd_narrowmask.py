#!/usr/bin/env python3
"""AMD narrow-mask cell: can way partitioning reach the residual when AIMED?

Pre-registration: AMD_NARROWMASK_PREREG_2026-08-30.md

tab:amdcat claims a "real-hardware AMD refutation of way-partitioning" from a
9.87x residual at an 8/8 split -- i.e. the aggressor was given HALF the ways.
This asks whether the residual survives a mask aimed tightly at the aggressor.

Apparatus is the campaign's own, unchanged: /home/domin/tmp_dutyfree_exp/bin,
victim 1 core + aggressor 7 cores on the SAME CCX (CCX0 = cores 0-7, 16 MiB L3,
16 CAT ways), aggressor drawing from the CXL node.
"""
import json, os, subprocess, sys, time

RESCTRL="/sys/fs/resctrl"; VGRP=f"{RESCTRL}/nm_v"; AGRP=f"{RESCTRL}/nm_a"
BIN="/home/domin/tmp_dutyfree_exp/bin"
VICTIM=f"{BIN}/victim"; AGGRESSOR=f"{BIN}/aggressor"
VICTIM_CPU=0; AGG_CORES="1,2,3,4,5,6,7"
VWARM=2; VDUR=5; SETTLE=2; ADUR=VWARM+VDUR+5
# (name, victim L3 mask, aggressor L3 mask, aggressor ways)
ARMS=[("quiescent","ffff","ffff",None),
      ("wb",       "ffff","ffff",16),
      ("cat8",     "ff00","00ff",8),
      ("cat4",     "fff0","000f",4),
      ("cat2",     "fffc","0003",2),
      ("cat1",     "fffe","0001",1)]

def sh(c): return subprocess.run(c,shell=True,capture_output=True,text=True)
def wr(g,l3): open(f"{g}/schemata","w").write(f"L3:0={l3}\n")
def setup():
    sh("pkill -f 'bin/aggressor'"); time.sleep(0.3)
    for g in (VGRP,AGRP): os.makedirs(g,exist_ok=True)
    open(f"{VGRP}/cpus_list","w").write(str(VICTIM_CPU))
    open(f"{AGRP}/cpus_list","w").write(AGG_CORES)
def teardown():
    sh("pkill -f 'bin/aggressor'"); time.sleep(0.3)
    for g in (VGRP,AGRP):
        try: os.rmdir(g)
        except OSError: pass

def readback(g):
    # schemata lines are INDENTED on this kernel ("      L3:0=ffff;1=..."), so
    # startswith("L3:") silently never matched and every record recorded "?".
    for l in open(f"{g}/schemata"):
        t = l.strip()
        if t.startswith("L3:"):
            return t.split(";")[0].split("=")[1].strip().lower()
    return "?"

def one(name,vl3,al3,rep):
    wr(VGRP,vl3); wr(AGRP,al3)
    got_v, got_a = readback(VGRP), readback(AGRP)     # enforcement, from the artifact
    agg=None; bw=None
    if name!="quiescent":
        agg=subprocess.Popen(f"{AGGRESSOR} -m wb_load -t 7 -c {AGG_CORES} -N 2 -s 64 "
                             f"-d {ADUR} > /tmp/nm_agg.log 2>&1",shell=True)
        time.sleep(SETTLE)
    p=subprocess.run(f"{VICTIM} -c {VICTIM_CPU} -w 4096 -P -d {VDUR} -W {VWARM}",
                     shell=True,capture_output=True,text=True)
    line=next((l for l in p.stdout.splitlines() if l.startswith("VICTIM")),"")
    d={}
    for t in line.split():
        if "=" in t:
            k,v=t.split("=",1)
            try: d[k]=float(v)
            except ValueError: d[k]=v
    if agg is not None:
        agg.wait(timeout=ADUR+15)
        for l in open("/tmp/nm_agg.log",errors="replace"):
            if l.startswith("aggregate:"): bw=float(l.split()[1])
    cpa=d.get("cyc_per_access")
    ok = (got_v == vl3.lower() and got_a == al3.lower())
    rec=dict(arm=name,rep=rep,cyc_per_access=cpa,agg_gbps=bw,
             vmask_set=vl3,vmask_readback=got_v,amask_set=al3,amask_readback=got_a,
             mask_enforced=ok, l2_miss_rate=d.get("l2_miss_rate"))
    if not ok:
        print(f"    ** MASK MISMATCH: set v={vl3}/a={al3}, read v={got_v}/a={got_a}"
              f" -- record voided per liveness assertion 1", flush=True)
    print(f"  {name:9s} rep{rep} cyc/acc={cpa:9.2f} bw={bw if bw else 0:6.2f} "
          f"masks v={got_v}/a={got_a}",flush=True)
    return rec

def main():
    reps=int(sys.argv[1]) if len(sys.argv)>1 else 6
    out=sys.argv[2] if len(sys.argv)>2 else "/tmp/amd_narrowmask.jsonl"
    if os.path.exists(out): print(f"FAIL {out} exists (A6.19)",file=sys.stderr); return 2
    setup(); recs=[]
    try:
        for r in range(1,reps+1):
            order=ARMS[r%len(ARMS):]+ARMS[:r%len(ARMS)]   # rotate to spread drift
            for (n,v,a,_) in order: recs.append(one(n,v,a,r))
    finally:
        teardown()
    with open(out,"w") as f:
        for x in recs: f.write(json.dumps(x)+"\n")
    print(f"wrote {len(recs)} records -> {out}")
    return 0

sys.exit(main())
