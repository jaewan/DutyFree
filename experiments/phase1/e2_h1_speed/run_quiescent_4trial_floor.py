#!/usr/bin/env python3
"""
Floor characterization: does the ~0.8-0.9% sub-baseline residual (tax CIs
now exclude 1.0 on the low side for small-D) reflect the protocol still
converging past trial 1, or a stable plateau? n=12 independent fresh
processes, each running --trials 4 --run-sec 4, all 4 trials recorded
(not just trial 1). If trials 2-3 keep dropping below trial 1, the floor
is still converging; if they plateau at ~trial-1 level, quote "baseline
within ~1%" and stop chasing it.
"""
import json, subprocess, sys, statistics

VICTIM = "/home/domin/DutyFree/benchmarks/bench/victim/pointer_chase_nocap"
WSS_BYTES = 170 * 1024 * 1024
N = int(sys.argv[1]) if len(sys.argv) > 1 else 12

all_trials = [[] for _ in range(4)]
for i in range(N):
    cmd = (f"numactl --membind=0 --cpunodebind=0 -- {VICTIM} "
           f"--cpu 0 --node 0 --wss {WSS_BYTES} --trials 4 --run-sec 4")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=90)
    trials = json.loads(r.stdout)
    vals = [t["cycles_per_load"] for t in trials]
    for k in range(4):
        all_trials[k].append(vals[k])
    print(f"  rep {i+1:2d}/{N}: " + "  ".join(f"t{k}={v:.2f}" for k, v in enumerate(vals)), flush=True)

print()
for k in range(4):
    m = statistics.median(all_trials[k])
    print(f"trial {k} median: {m:.3f}  raw={sorted(f'{v:.2f}' for v in all_trials[k])}")
