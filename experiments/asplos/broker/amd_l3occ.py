#!/usr/bin/env python3
"""AMD L3-occupancy instrument: does the victim get EVICTED from L3, or
BACK-INVALIDATED from L2 while still resident in L3?

The campaign has been arguing about L3 using only L2 counters. resctrl exposes
llc_occupancy on this part, which measures the question directly:

  victim L3 occupancy COLLAPSES under the aggressor -> L3 eviction (capacity/rate)
  victim L3 occupancy HOLDS but L2 hits vanish      -> back-invalidation

Sampled during the victim's run, not before or after, because occupancy is a
live residency measure and a before/after reading would miss the transient the
victim actually experiences.
"""
import json, os, subprocess, sys, time, statistics as st

R="/sys/fs/resctrl"; VG=f"{R}/mon_groups/occ_v"; AG=f"{R}/mon_groups/occ_a"
V="/home/domin/tmp_dutyfree_exp/bin/victim"; A="/home/domin/tmp_dutyfree_exp/bin/aggressor"
SAME="1,2,3,4,5,6,7"; OTHER="9,10,11,12,13,14,15"
VDUR, VWARM, SETTLE, ADUR = 4, 1, 2, 12

def sh(c): return subprocess.run(c,shell=True,capture_output=True,text=True).stdout.strip()
def setup():
    subprocess.run("pkill -f 'bin/aggressor'",shell=True,capture_output=True); time.sleep(0.3)
    for g,c in ((VG,"0"),(AG,SAME)):
        os.makedirs(g,exist_ok=True); open(f"{g}/cpus_list","w").write(c)
def teardown():
    subprocess.run("pkill -f 'bin/aggressor'",shell=True,capture_output=True); time.sleep(0.3)
    for g in (VG,AG):
        try: os.rmdir(g)
        except OSError: pass
def occ(g, dom="00"):
    try: return int(open(f"{g}/mon_data/mon_L3_{dom}/llc_occupancy").read().strip())
    except Exception: return None

def one(arm, wss, rep):
    cores = None if arm=="quiescent" else (OTHER if arm=="other" else SAME)
    if cores: open(f"{AG}/cpus_list","w").write(cores)
    agg=None; bw=None
    if cores:
        agg=subprocess.Popen(f"{A} -m wb_load -t 7 -c {cores} -N 2 -s 64 -d {ADUR} "
                             f"> /tmp/occ_agg.log 2>&1",shell=True)
        time.sleep(SETTLE)
    vp=subprocess.Popen(f"{V} -c 0 -w {wss} -P -d {VDUR} -W {VWARM}",
                        shell=True,stdout=subprocess.PIPE,text=True)
    samples=[]; t0=time.time()
    while vp.poll() is None and time.time()-t0 < VDUR+VWARM+4:
        time.sleep(0.25)
        if time.time()-t0 > VWARM+0.5:            # skip warmup
            o=occ(VG)
            if o is not None: samples.append(o)
    out,_=vp.communicate()
    line=next((l for l in out.splitlines() if l.startswith("VICTIM")),"")
    d={}
    for t in line.split():
        if "=" in t:
            k,v=t.split("=",1)
            try: d[k]=float(v)
            except ValueError: d[k]=v
    if agg is not None:
        agg.wait(timeout=ADUR+15)
        for l in open("/tmp/occ_agg.log",errors="replace"):
            if l.startswith("aggregate:"): bw=float(l.split()[1])
    hit,miss=d.get("l2_hit"),d.get("l2_miss")
    hr=100*hit/(hit+miss) if hit is not None and (hit+miss) else None
    med=st.median(samples) if samples else None
    rec=dict(arm=arm,wss_kb=wss,rep=rep,cyc_per_access=d.get("cyc_per_access"),
             l2_hit=hit,l2_miss=miss,hit_rate=hr,agg_gbps=bw,
             victim_l3_occ_median=med,victim_l3_occ_n=len(samples),
             victim_l3_occ_min=min(samples) if samples else None,
             victim_l3_occ_max=max(samples) if samples else None)
    print(f"  {arm:9s} wss={wss:5d} rep{rep:2d} cyc/acc={rec['cyc_per_access'] or 0:8.2f} "
          f"L2hit%={hr or 0:6.2f} L3occ={((med or 0)/1024):8.1f}KB (n={len(samples)}) "
          f"bw={bw or 0:6.2f}",flush=True)
    return rec

def main():
    reps=int(sys.argv[1]); out=sys.argv[2]
    if os.path.exists(out): print("FAIL exists (A6.19)",file=sys.stderr); return 2
    setup(); recs=[]
    try:
        for wss in (512, 4096):
            for arm in ("quiescent","same","other"):
                for r in range(1,reps+1): recs.append(one(arm,wss,r))
    finally:
        teardown()
        with open(out,"w") as f:
            for x in recs: f.write(json.dumps(x)+"\n")
        print(f"wrote {len(recs)} -> {out}")
    return 0
sys.exit(main())
