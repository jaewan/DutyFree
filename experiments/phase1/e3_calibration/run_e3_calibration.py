#!/usr/bin/env python3
"""
E3: calibration_targets.csv for gem5. Three legs, all n=12, rep-interleaved
within each leg:

  1. Thread-count sweep: {WB, WC} x {CXL, local} x {1,2,4,8} threads.
  2. SW-prefetch-distance sweep (HW prefetchers off via MSR 0x1A4=0xF):
     distance in {0,1,2,4,8,16,32,64} cache lines, hint in {T0, NTA},
     single thread, CXL and local.
  3. Idle load latency (dependent pointer chase, no aggressor), CXL and
     local, for the Little's-law column: implied_mlp = bw_gbps * latency_ns
     / 64 (bytes/line), pairing each leg-1/leg-2 BW row with the matching
     idle latency for its memory type.

Output: calibration_targets.csv with columns
  platform,leg,config,threads,node,bw_gbps,latency_ns,implied_mlp
"""
import csv, json, os, subprocess, sys, time

BENCH = "/home/domin/DutyFree/benchmarks/bench"
STREAM_WB = f"{BENCH}/aggressor/stream_wb"
STREAM_WC = f"{BENCH}/aggressor/stream_wc"
SWPF = f"{BENCH}/aggressor/stream_sw_prefetch"
PCHASE = f"{BENCH}/victim/pointer_chase"

CXL_NODE = 2
LOCAL_NODE = 0
REPS = 12
DUR = 4
THREAD_COUNTS = [1, 2, 4, 8]
PF_DISTANCES = [0, 1, 2, 4, 8, 16, 32, 64]
PF_HINTS = ["t0", "nta"]
CORES = list(range(1, 9))  # cpus1-8


def run_stream(binpath, cpu, node, extra=""):
    cmd = (f"numactl --membind={node} --cpunodebind=0 -- {binpath} "
           f"--cpu {cpu} --node {node} --region-gb 1 --duration-sec {DUR} {extra}")
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True)
    return p


def collect_bw(procs):
    total = 0.0
    for p in procs:
        out, _ = p.communicate(timeout=DUR + 30)
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    total += json.loads(line)["avg_bw_gbps"]
                except (json.JSONDecodeError, KeyError):
                    pass
    return total


def leg1_thread_sweep(rows):
    print("=== Leg 1: thread-count sweep ===", flush=True)
    configs = [
        ("wb_cxl", STREAM_WB, CXL_NODE),
        ("wb_local", STREAM_WB, LOCAL_NODE),
        ("wc_cxl", STREAM_WC, CXL_NODE),
        ("wc_local", STREAM_WC, LOCAL_NODE),
    ]
    for rep in range(1, REPS + 1):
        for name, binpath, node in configs:
            for t in THREAD_COUNTS:
                procs = [run_stream(binpath, CORES[i], node) for i in range(t)]
                bw = collect_bw(procs)
                rows.append({
                    "platform": "intel_emr", "leg": "thread_sweep",
                    "config": name, "threads": t, "node": node,
                    "bw_gbps": bw, "latency_ns": None, "implied_mlp": None,
                })
                print(f"  {name:10s} t={t} rep={rep:2d}  bw={bw:.2f} GB/s", flush=True)


def leg2_pf_sweep(rows):
    print("=== Leg 2: SW-prefetch-distance sweep (HW pf off) ===", flush=True)
    for rep in range(1, REPS + 1):
        for node, label in [(CXL_NODE, "cxl"), (LOCAL_NODE, "local")]:
            for hint in PF_HINTS:
                for dist in PF_DISTANCES:
                    p = subprocess.run(
                        f"numactl --membind={node} --cpunodebind=0 -- {SWPF} "
                        f"--cpu 1 --node {node} --region-gb 1 --duration-sec {DUR} "
                        f"--pf-distance {dist} --pf-hint {hint}",
                        shell=True, capture_output=True, text=True, timeout=DUR + 30)
                    bw = None
                    for line in p.stdout.splitlines():
                        if line.strip().startswith("{"):
                            bw = json.loads(line)["avg_bw_gbps"]
                    rows.append({
                        "platform": "intel_emr", "leg": "sw_prefetch_sweep",
                        "config": f"{label}_{hint}_d{dist}", "threads": 1, "node": node,
                        "bw_gbps": bw, "latency_ns": None, "implied_mlp": None,
                    })
                    print(f"  {label:6s} hint={hint:3s} d={dist:3d} rep={rep:2d}  bw={bw}", flush=True)


def leg3_idle_latency():
    print("=== Leg 3: idle load latency ===", flush=True)
    out = {}
    for node, label in [(CXL_NODE, "cxl"), (LOCAL_NODE, "local")]:
        p = subprocess.run(
            f"numactl --membind={node} --cpunodebind=0 -- {PCHASE} "
            f"--cpu 1 --node {node} --wss {512*1024*1024} --trials {REPS} --run-sec 1.0",
            shell=True, capture_output=True, text=True, timeout=REPS * 3 + 60)
        trials = json.loads(p.stdout)
        cyc = sorted(t["cycles_per_load"] for t in trials)
        median_cyc = cyc[len(cyc) // 2]
        tsc_hz = trials[0]["tsc_hz"]
        latency_ns = median_cyc / tsc_hz * 1e9
        out[label] = latency_ns
        print(f"  {label:6s}  median={median_cyc:.1f} cyc/load  "
              f"tsc_hz={tsc_hz}  latency={latency_ns:.2f} ns", flush=True)
    return out


def main():
    outpath = sys.argv[1] if len(sys.argv) > 1 else "/tmp/calibration_targets.csv"
    rows = []
    leg1_thread_sweep(rows)
    leg2_pf_sweep(rows)
    latency = leg3_idle_latency()

    for r in rows:
        lat = latency["cxl"] if r["node"] == CXL_NODE else latency["local"]
        r["latency_ns"] = lat
        if r["bw_gbps"]:
            r["implied_mlp"] = r["bw_gbps"] * 1e9 * lat * 1e-9 / 64.0

    with open(outpath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["platform", "leg", "config", "threads",
                                           "node", "bw_gbps", "latency_ns", "implied_mlp"])
        w.writeheader()
        w.writerows(rows)
    print(f"DONE -> {outpath} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
