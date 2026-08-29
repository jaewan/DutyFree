#!/usr/bin/env python3
"""Bergamo back-invalidation experiment.
Pre-registration: BERGAMO_BACKINVAL_PREREG_2026-08-30.md (0ff6ca4)

2x2x2 factorial + quiescent controls. Every claim about a run's configuration is
read back from the machine into that run's own record: THP from sysfs, the
aggressor's L3 domain from the cache topology, core-0 frequency during the run.
"""
import json, os, subprocess, sys, time

V="/home/domin/tmp_dutyfree_exp/bin/victim"
A="/home/domin/tmp_dutyfree_exp/bin/aggressor"
SAME="1,2,3,4,5,6,7"        # CCX0, with the victim on core 0
OTHER="9,10,11,12,13,14,15" # CCX1
VDUR, VWARM, SETTLE, ADUR = 3, 1, 2, 10

def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()

def l3_domain(cpu):
    return sh(f"cat /sys/devices/system/cpu/cpu{cpu}/cache/index3/shared_cpu_list")

def thp_state():
    s = sh("cat /sys/kernel/mm/transparent_hugepage/enabled")
    for tok in s.replace("[", " [").split():
        if tok.startswith("["): return tok.strip("[]")
    return s

def set_thp(mode):
    subprocess.run(f"echo {mode} > /sys/kernel/mm/transparent_hugepage/enabled",
                   shell=True, capture_output=True)
    return thp_state()

def freq0():
    f = sh("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
    try: return int(f)
    except ValueError: return None

def one(place, wss, thp, rep):
    cores = None if place=="quiescent" else (SAME if place=="same" else OTHER)
    agg=None; bw=None
    if cores:
        agg=subprocess.Popen(f"{A} -m wb_load -t 7 -c {cores} -N 2 -s 64 -d {ADUR} "
                             f"> /tmp/bi_agg.log 2>&1", shell=True)
        time.sleep(SETTLE)
    f_mid = freq0()
    p=subprocess.run(f"{V} -c 0 -w {wss} -P -d {VDUR} -W {VWARM}",
                     shell=True, capture_output=True, text=True)
    line=next((l for l in p.stdout.splitlines() if l.startswith("VICTIM")), "")
    d={}
    for t in line.split():
        if "=" in t:
            k,v=t.split("=",1)
            try: d[k]=float(v)
            except ValueError: d[k]=v
    if agg is not None:
        agg.wait(timeout=ADUR+15)
        for l in open("/tmp/bi_agg.log", errors="replace"):
            if l.startswith("aggregate:"): bw=float(l.split()[1])
    hit, miss = d.get("l2_hit"), d.get("l2_miss")
    hr = 100*hit/(hit+miss) if hit is not None and (hit+miss) else None
    rec = dict(place=place, wss_kb=wss, thp_requested=thp, thp_readback=thp_state(),
               rep=rep, cyc_per_access=d.get("cyc_per_access"),
               l2_hit=hit, l2_miss=miss, hit_rate=hr, agg_gbps=bw,
               freq_khz=f_mid, ok=bool(line),
               agg_cores=cores, agg_l3_domain=(l3_domain(cores.split(",")[0]) if cores else None),
               victim_l3_domain=l3_domain(0))
    print(f"  {place:9s} wss={wss:5d} thp={rec['thp_readback']:6s} rep{rep:2d} "
          f"cyc/acc={rec['cyc_per_access'] if rec['cyc_per_access'] else 0:8.2f} "
          f"hit%={hr if hr else 0:6.2f} bw={bw if bw else 0:6.2f}", flush=True)
    return rec

def main():
    reps=int(sys.argv[1]); out=sys.argv[2]
    if os.path.exists(out): print("FAIL exists (A6.19)", file=sys.stderr); return 2
    recs=[]
    try:
        for thp in ("never","always"):
            got=set_thp(thp)
            print(f"== THP requested={thp} readback={got} ==", flush=True)
            for wss in (512, 4096):
                for place in ("quiescent","same","other"):
                    for r in range(1, reps+1):
                        recs.append(one(place, wss, thp, r))
    finally:
        set_thp("madvise")   # restore the kernel default, not whatever we last set
        with open(out,"w") as f:
            for x in recs: f.write(json.dumps(x)+"\n")
        print(f"wrote {len(recs)} -> {out}; THP restored to {thp_state()}")
    return 0

sys.exit(main())
