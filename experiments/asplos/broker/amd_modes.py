#!/usr/bin/env python3
"""(a) Module-free non-allocation probe at MATCHED rate.

The published WC row is not rate-matched (13.8 vs 24.1 GB/s), so its 0.99x
cannot separate "did not allocate" from "moved 43% fewer bytes". These modes all
sustain ~24-25 GB/s, removing the rate confound.

The DISCRIMINATOR is the victim's L2 miss rate, not the tax: under wb the victim
is pinned at 100% (everything evicted); quiescent is ~86.5%. A mode that truly
avoids allocation must leave the victim near 86.5% while still moving ~24 GB/s.
wb_ntdqa is expected to be a NULL control -- movntdqa on write-back memory is
architecturally an ordinary load -- and is included precisely so a null looks
like a null.
"""
import json,os,subprocess,sys,time
BIN="/home/domin/tmp_dutyfree_exp/bin"
VICTIM=f"{BIN}/victim"; AGG=f"{BIN}/aggressor"
VCPU=0; CORES="1,2,3,4,5,6,7"; VWARM=2; VDUR=5; SETTLE=2; ADUR=VWARM+VDUR+5
ARMS=["quiescent","wb_load","wb_prefetchnta","wb_ntdqa"]
def one(mode,rep):
    agg=None;bw=None
    if mode!="quiescent":
        agg=subprocess.Popen(f"{AGG} -m {mode} -t 7 -c {CORES} -N 2 -s 64 -d {ADUR} "
                             f"> /tmp/md_agg.log 2>&1",shell=True); time.sleep(SETTLE)
    p=subprocess.run(f"{VICTIM} -c {VCPU} -w 4096 -P -d {VDUR} -W {VWARM}",
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
        for l in open("/tmp/md_agg.log",errors="replace"):
            if l.startswith("aggregate:"): bw=float(l.split()[1])
    rec=dict(arm=mode,rep=rep,cyc_per_access=d.get("cyc_per_access"),
             l2_miss_rate=d.get("l2_miss_rate"),agg_gbps=bw)
    print(f"  {mode:16s} rep{rep} cyc/acc={rec['cyc_per_access']:9.2f} "
          f"L2miss={rec['l2_miss_rate']:6.2f}% bw={bw if bw else 0:6.2f}",flush=True)
    return rec
def main():
    reps=int(sys.argv[1]); out=sys.argv[2]
    if os.path.exists(out): print("FAIL exists (A6.19)",file=sys.stderr); return 2
    recs=[]
    for r in range(1,reps+1):
        order=ARMS[r%len(ARMS):]+ARMS[:r%len(ARMS)]
        for m in order: recs.append(one(m,r))
    with open(out,"w") as f:
        for x in recs: f.write(json.dumps(x)+"\n")
    print(f"wrote {len(recs)} -> {out}")
    return 0
sys.exit(main())
