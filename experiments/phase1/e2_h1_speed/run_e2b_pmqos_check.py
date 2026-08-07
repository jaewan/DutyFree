#!/usr/bin/env python3
"""
Decisive follow-up: does E2b's tax ratio (quiescent vs D=256KiB) change when
BOTH arms are measured under PM-QoS (blocking deep C-states), not just
quiescent alone? The PM-QoS/ticker tests already showed medians barely move
for quiescent in isolation (bimodal tail-outlier elimination, not a median
shift) -- this checks whether the same holds once the co-run arm is also
covered.
"""
import ctypes, json, os, subprocess, sys, time, threading

BENCH = "/home/domin/DutyFree/benchmarks/bench"
AGG = f"{BENCH}/aggressor/stream_wb_flushbehind"
VICTIM = f"{BENCH}/victim/pointer_chase_nocap"
VICTIM_NODE = 0
WSS_MB = 170
AGG_CPUS = [1, 2, 3, 4, 5, 6, 7, 8]
AGG_NODE = 2
AGG_REGION_GB = 2
AGG_DURATION = 30
VICTIM_RUN_SEC = 4
N = int(sys.argv[1]) if len(sys.argv) > 1 else 12


class PMQoS:
    def __enter__(self):
        self.fd = os.open("/dev/cpu_dma_latency", os.O_WRONLY)
        os.write(self.fd, ctypes.c_int32(0).value.to_bytes(4, "little"))
        return self

    def __exit__(self, *a):
        os.close(self.fd)


def run_victim_once():
    cmd = (f"numactl --membind={VICTIM_NODE} --cpunodebind=0 -- {VICTIM} "
           f"--cpu 0 --node {VICTIM_NODE} --wss {WSS_MB * 1024 * 1024} "
           f"--trials 1 --run-sec {VICTIM_RUN_SEC}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    trials = json.loads(r.stdout)
    return trials[0]["cycles_per_load"]


def launch_aggressors():
    procs = []
    for cpu in AGG_CPUS:
        cmd = (f"numactl --membind={AGG_NODE} --cpunodebind=0 -- {AGG} "
               f"--cpu {cpu} --node {AGG_NODE} --region-gb {AGG_REGION_GB} "
               f"--duration-sec {AGG_DURATION} --flush-distance-kb 256")
        procs.append(subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL))
    return procs


def stop_aggressors(procs):
    for p in procs:
        p.terminate()
    for p in procs:
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()


def run_block(label, n, loaded):
    vals = []
    for i in range(n):
        procs = launch_aggressors() if loaded else []
        if loaded:
            time.sleep(2)
        v = run_victim_once()
        if loaded:
            stop_aggressors(procs)
        vals.append(v)
        print(f"  [{label}] {i+1}/{n}: {v:.2f} cyc/load", flush=True)
    return vals


def main():
    import statistics
    print("=== quiescent, PM-QoS held ===", flush=True)
    with PMQoS():
        q_vals = run_block("quiescent+pmqos", N, loaded=False)
    q_med = statistics.median(q_vals)
    print(f"quiescent+pmqos median: {q_med:.3f}\n")

    print("=== D=256KiB, PM-QoS held ===", flush=True)
    with PMQoS():
        d_vals = run_block("d256+pmqos", N, loaded=True)
    d_med = statistics.median(d_vals)
    print(f"d256+pmqos median: {d_med:.3f}\n")

    print(f"TAX under PM-QoS (both arms): {d_med/q_med:.4f}")
    print(f"(original unpinned/uncontrolled tax at D=256KiB: 0.902; "
          f"uncore-pinned tax: 0.905)")


if __name__ == "__main__":
    main()
