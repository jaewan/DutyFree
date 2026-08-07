#!/usr/bin/env python3
"""
Phase 2.3 follow-up: PM-QoS and keep-awake-ticker tests for E2b's bimodal
quiescent baseline (88.5 / 81.9-82.2 cyc/load, confirmed independent of
uncore frequency and of the C6 idle state specifically).

Three conditions, each running N independent single-trial quiescent victim
invocations (matching E2b's own methodology exactly -- fresh process,
--trials 1, no aggressor):
  1. baseline: nothing held, normal system behavior (reproduces bimodality)
  2. pmqos: /dev/cpu_dma_latency held open at 0us for the whole block,
     blocking deep C-states system-wide via PM QoS
  3. ticker: a background thread on a different core continuously touches
     a small DRAM buffer at low intensity (~1% of peak bandwidth) for the
     whole block, present during every trial including this "baseline"
     analog -- meant to normalize package activity level between
     nominally-quiescent and nominally-loaded conditions.

If the bimodal pattern (a ~87-90 cyc/load mode alongside a ~81.5-82.5 mode)
collapses to a single mode under either condition, that identifies (or at
least narrows) the mechanism behind E2b's "faster than quiescent" residual.
"""
import ctypes, os, statistics, subprocess, sys, threading, time

VICTIM = "/home/domin/DutyFree/benchmarks/bench/victim/pointer_chase_nocap"
WSS_BYTES = 170 * 1024 * 1024
N = int(sys.argv[1]) if len(sys.argv) > 1 else 12
TICKER_CORE = 20  # far from victim's cpu0, not used by anything else


def run_quiescent_trial():
    cmd = (f"numactl --membind=0 --cpunodebind=0 -- {VICTIM} "
           f"--cpu 0 --node 0 --wss {WSS_BYTES} --trials 1 --run-sec 4")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    import json
    trials = json.loads(r.stdout)
    return trials[0]["cycles_per_load"]


def run_block(label, n):
    vals = []
    for i in range(n):
        v = run_quiescent_trial()
        vals.append(v)
        print(f"  [{label}] trial {i+1}/{n}: {v:.2f} cyc/load", flush=True)
    return vals


def summarize(label, vals):
    vals_sorted = sorted(vals)
    med = statistics.median(vals)
    # crude bimodality check: gap between consecutive sorted values
    gaps = [vals_sorted[i+1] - vals_sorted[i] for i in range(len(vals_sorted)-1)]
    maxgap = max(gaps) if gaps else 0
    n_low = sum(1 for v in vals if v < med - 0.5)
    n_high = sum(1 for v in vals if v > med + 0.5)
    print(f"[{label}] n={len(vals)} median={med:.2f} min={min(vals):.2f} "
          f"max={max(vals):.2f} max_gap={maxgap:.2f} "
          f"below_med={n_low} above_med={n_high}")
    print(f"[{label}] raw: {[f'{v:.2f}' for v in vals_sorted]}")


class PMQoS:
    """Hold /dev/cpu_dma_latency open at 0us for the block's duration."""
    def __enter__(self):
        self.fd = os.open("/dev/cpu_dma_latency", os.O_WRONLY)
        os.write(self.fd, ctypes.c_int32(0).value.to_bytes(4, "little"))
        return self

    def __exit__(self, *a):
        os.close(self.fd)


class Ticker:
    """Background thread lightly touching DRAM on a spare core."""
    def __init__(self, core):
        self.core = core
        self.stop_evt = threading.Event()
        self.proc = None

    def __enter__(self):
        # Busy-spin, not time.sleep(): a sleep-based pacer lets its OWN core
        # (and thus the package, if that's what matters) go idle between
        # bursts -- exactly what this test needs to avoid. Continuously
        # touch a small buffer with a cheap busy-wait between writes so the
        # core running this never fully idles, at low but nonzero DRAM
        # traffic (small buffer, mostly cache-resident after warmup, but
        # the point is package/core non-idleness, not bandwidth volume).
        script = (
            "import mmap, os, time, sys\n"
            "os.sched_setaffinity(0, {" + str(self.core) + "})\n"
            "buf = mmap.mmap(-1, 4*1024*1024)\n"
            "buf[:] = b'\\xab' * len(buf)\n"
            "next_write = time.perf_counter()\n"
            "while True:\n"
            "    buf[0:65536] = b'\\xcd' * 65536\n"
            "    next_write += 0.001\n"
            "    while time.perf_counter() < next_write:\n"
            "        pass\n"
        )
        self.proc = subprocess.Popen([sys.executable, "-c", script])
        time.sleep(0.5)
        return self

    def __exit__(self, *a):
        self.proc.terminate()
        self.proc.wait(timeout=5)


def main():
    print("=== Condition 1: baseline (nothing held) ===", flush=True)
    base_vals = run_block("baseline", N)
    summarize("baseline", base_vals)
    print()

    print("=== Condition 2: PM-QoS held at 0us ===", flush=True)
    with PMQoS():
        pmqos_vals = run_block("pmqos", N)
    summarize("pmqos", pmqos_vals)
    print()

    print("=== Condition 3: keep-awake ticker on cpu%d ===" % TICKER_CORE, flush=True)
    with Ticker(TICKER_CORE):
        ticker_vals = run_block("ticker", N)
    summarize("ticker", ticker_vals)
    print()

    print("=== Summary ===")
    for label, vals in [("baseline", base_vals), ("pmqos", pmqos_vals), ("ticker", ticker_vals)]:
        summarize(label, vals)


if __name__ == "__main__":
    main()
