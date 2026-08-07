#!/usr/bin/env python3
"""
Corrected quiescent baseline: --trials 4, discard cold trial 0 (matching
standard warm-up discipline, and cat_mba.py's own WARMUP_SEC convention),
report trial 1 as this rep's quiescent value. n=12, independent fresh
process per rep (matching E2b's own per-rep methodology otherwise).
"""
import json, subprocess, sys, statistics

VICTIM = "/home/domin/DutyFree/benchmarks/bench/victim/pointer_chase_nocap"
WSS_BYTES = 170 * 1024 * 1024
N = int(sys.argv[1]) if len(sys.argv) > 1 else 12

vals = []
for i in range(N):
    cmd = (f"numactl --membind=0 --cpunodebind=0 -- {VICTIM} "
           f"--cpu 0 --node 0 --wss {WSS_BYTES} --trials 4 --run-sec 4")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    trials = json.loads(r.stdout)
    v = trials[1]["cycles_per_load"]  # discard trial 0, take trial 1
    vals.append(v)
    print(f"  rep {i+1}/{N}: trial0(discarded)={trials[0]['cycles_per_load']:.2f}  "
          f"trial1(used)={v:.2f}", flush=True)

print(f"\nmedian (corrected quiescent, trial 1 of 4): {statistics.median(vals):.3f}")
print(f"raw: {sorted(f'{v:.2f}' for v in vals)}")
