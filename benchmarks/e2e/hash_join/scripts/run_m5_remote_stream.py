#!/usr/bin/env python3
"""M5: remote-socket bandwidth-matched residual control.

A stream-smoke process runs on a remote-socket core (node 1), duty-cycled via
repeated short bursts + computed sleep gaps to approximate the fused case's
own achieved aggregate CXL bandwidth (measured separately, from the CLOS-split
panel: ~0.34 GB/s at 1 core, ~5.37 GB/s at 16 cores -- both far below a single
thread's uncontended ceiling, hence the need to throttle rather than just run
flat out). Concurrently, a hot-probe process runs on the local (node 0) core(s)
against the 170MB hot table. The residual tax on the probe, versus a true
quiescent baseline with no remote stream at all, is reported as an UPPER BOUND
on component (d) (memory-path queueing) -- it also still loads part of the
mesh, so it cannot cleanly isolate queueing alone, and that is stated, not
hidden.

Bandwidth is matched "as closely as practical", not exactly -- both arms'
achieved bandwidth are reported explicitly, and the residual is not compared
against a target that wasn't actually achieved.
"""
import json
import os
import random
import signal
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clos_stats import summarize_metric  # noqa: E402

HASH_JOIN_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
BIN = HASH_JOIN_DIR / "build" / "cxl_join_bench"
RESULTS_DIR = REPO_ROOT / "results" / "mechanism_decomp"
RAW_DIR = RESULTS_DIR / "raw"
HOT_BYTES = "177838489"

# From CLOS-split panel (results/clos_split/raw), the fused case's own achieved
# aggregate stream bandwidth -- the target M5 approximates, not a theoretical rate.
TARGET_BW_GBPS = {1: 0.339, 16: 5.376}
# Measured fresh on node1 core 70 (huge2m, continuous): 5.22 GB/s -- notably
# below node0's ~8.8-9.4 GB/s single-thread ceiling used elsewhere in this
# project. Real, not a bug: node distances show node1->node2(CXL) = 24 vs
# node0->node2 = 14 (numactl -H), so node1 genuinely has a lower CXL ceiling.
# This means the 16-core target (5.376) is *slightly above* what one remote
# thread can deliver even fully on -- duty_fraction clamps to 1.0 and the
# achieved bandwidth (~5.22) is reported as the best available match, not
# forced to an unreachable target.
FULL_SINGLE_THREAD_BW_GBPS = 5.22

CORE_CONFIGS = {
    1: {"probe_cpu": "32", "remote_cpu": "70", "fact_bytes": "256m"},
    16: {"probe_cpu": "32-47", "remote_cpu": "70-77", "fact_bytes": "1g"},
}
N_REPS = 30
BURST_FACT_BYTES = "256m"  # ~29ms per burst at ~8.8 GB/s uncontended


def remote_socket_of(cpu_str):
    # sanity check the chosen remote cpus are actually node 1, not node 0/2
    first = int(cpu_str.split("-")[0].split(",")[0])
    out = subprocess.run(["bash", "-c", f"cat /sys/devices/system/node/node1/cpulist"],
                        capture_output=True, text=True).stdout.strip()
    return out


BURST_BYTES = 256 * 1024 * 1024  # matches BURST_FACT_BYTES="256m"


class DutyCycleStreamer:
    """Duty-cycles ONE continuously-running stream-smoke process on a remote
    (node 1) core via SIGSTOP/SIGCONT, to approximate a target effective
    aggregate bandwidth.

    Earlier version restarted a fresh process per burst; measured wall-clock
    (not just the binary's own self-reported in-stream "seconds") showed
    mmap+mbind+prefault of a fresh region dominates cost for any burst small
    enough to duty-cycle usefully -- true achievable ceiling via restart was
    ~0.5-2 GB/s, actually *below* the 16-core target (5.376 GB/s). Pausing an
    already-running, already-prefaulted process via SIGSTOP/SIGCONT avoids
    paying that setup cost repeatedly, and a single thread's continuous
    ceiling (~8.8-9 GB/s, this repo's own characterization) already covers
    both targets via duty-cycle fraction alone, so one remote thread is used
    regardless of core count.
    """
    CYCLE_PERIOD_S = 0.5

    def __init__(self, cpu, target_bw_gbps, ceiling_bw_gbps):
        self.cpu = cpu
        self.target_bw = target_bw_gbps
        self.ceiling_bw = ceiling_bw_gbps
        self.duty_fraction = min(1.0, target_bw_gbps / ceiling_bw_gbps)
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self._run)
        self.proc = None
        self.total_on_time = 0.0
        self.total_elapsed = 0.0

    def _run(self):
        cmd = [str(BIN), "--mode", "stream-smoke", "--policy", "wb", "--fact-node", "2",
               "--fact-bytes", "16g", "--cpu-list", str(self.cpu), "--threads", "1",
               "--warmups", "0", "--reps", "5000", "--huge2m"]
        self.proc = subprocess.Popen(cmd, cwd=str(HASH_JOIN_DIR),
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        on_time = self.CYCLE_PERIOD_S * self.duty_fraction
        off_time = self.CYCLE_PERIOD_S * (1 - self.duty_fraction)
        run_start = time.time()
        try:
            while not self.stop_flag.is_set():
                t_on0 = time.time()
                time.sleep(on_time)
                self.total_on_time += time.time() - t_on0
                if off_time > 0 and not self.stop_flag.is_set():
                    os.kill(self.proc.pid, signal.SIGSTOP)
                    time.sleep(off_time)
                    os.kill(self.proc.pid, signal.SIGCONT)
        finally:
            self.total_elapsed = time.time() - run_start
            try:
                os.kill(self.proc.pid, signal.SIGCONT)
            except ProcessLookupError:
                pass
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()

    def effective_bw_gbps(self):
        """Estimated from measured on-duty fraction x the independently
        measured single-thread ceiling -- not from a byte count, since the
        process is killed mid-run and never emits its own JSON report."""
        if self.total_elapsed <= 0:
            return None
        achieved_duty_fraction = self.total_on_time / self.total_elapsed
        return achieved_duty_fraction * self.ceiling_bw

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_flag.set()
        self.thread.join(timeout=15)


def hotprobe_args(cores):
    cc = CORE_CONFIGS[cores]
    return ["--mode", "hot-probe", "--policy", "wb", "--fact-bytes", cc["fact_bytes"],
            "--hot-bytes", HOT_BYTES, "--cpu-list", cc["probe_cpu"], "--morsel", "1m",
            "--warmups", "2", "--reps", "1", "--threads", str(1 if cores == 1 else 16)]


def run_probe_once(cores, idx, label):
    args = hotprobe_args(cores)
    cmd = [str(BIN)] + args
    proc = subprocess.run(cmd, cwd=str(HASH_JOIN_DIR), capture_output=True, text=True, timeout=60)
    rec = None
    for line in reversed(proc.stdout.strip().splitlines()):
        try:
            rec = json.loads(line)
            break
        except Exception:
            pass
    if rec is None:
        rec = {"status": "parse_failed", "raw_stdout": proc.stdout}
    (RAW_DIR / f"M5_{label}_{cores}c_{idx:02d}.json").write_text(json.dumps(rec, indent=2))
    return rec


def run_block(cores, with_remote):
    """The 16-core probe window is only ~150ms -- too short for a duty-cycle
    streamer to converge if started/stopped per rep. Instead the streamer (if
    any) is started once, given time to reach steady state, and left running
    continuously through all N_REPS probe reps back-to-back; this trades
    per-rep randomized interleaving (not possible here without the streamer
    losing its converged duty cycle) for a stable, converged bandwidth match,
    disclosed as a block design rather than presented as interleaved."""
    label = "with_remote" if with_remote else "quiescent"
    streamer = None
    if with_remote:
        remote_cpu = int(CORE_CONFIGS[cores]["remote_cpu"].split("-")[0])
        streamer = DutyCycleStreamer(remote_cpu, TARGET_BW_GBPS[cores], FULL_SINGLE_THREAD_BW_GBPS)
        streamer.start()
        settle = 3.0
        print(f"  settling remote streamer for {settle}s...", file=sys.stderr)
        time.sleep(settle)
    recs = []
    for idx in range(1, N_REPS + 1):
        print(f"[M5 {cores}c {label}] rep {idx}/{N_REPS}", file=sys.stderr)
        recs.append(run_probe_once(cores, idx, label))
    eff_bw = None
    if streamer:
        streamer.stop()
        eff_bw = streamer.effective_bw_gbps()
    return recs, eff_bw


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print("node1 cpulist (sanity check remote cpus are truly remote-socket):",
          remote_socket_of(CORE_CONFIGS[1]["remote_cpu"]), file=sys.stderr)

    rows = []
    for cores in (1, 16):
        q_recs, _ = run_block(cores, with_remote=False)
        r_recs, eff_bw = run_block(cores, with_remote=True)

        hq = [r["active_cycles_per_access"] for r in q_recs if r.get("status") == "ok"]
        hr = [r["active_cycles_per_access"] for r in r_recs if r.get("status") == "ok"]
        sq = summarize_metric(hq); sr = summarize_metric(hr)
        row = {
            "cores": cores,
            "H_quiescent_median": sq["median"], "H_quiescent_ci": (sq["ci95_lo"], sq["ci95_hi"]),
            "H_with_remote_median": sr["median"], "H_with_remote_ci": (sr["ci95_lo"], sr["ci95_hi"]),
            "delta_M5_abs_cycles": sr["median"] - sq["median"],
            "target_bw_gbps": TARGET_BW_GBPS[cores],
            "remote_effective_bw_gbps": eff_bw,
        }
        rows.append(row)
        print(row, file=sys.stderr)

    (RESULTS_DIR / "m5_summary.json").write_text(json.dumps(rows, indent=2))
    print("DONE.", file=sys.stderr)


if __name__ == "__main__":
    main()
