#!/usr/bin/env python3
"""
WSS Sweep — WB streaming tax measurement under frozen system state.

Runs pointer_chase_nocap victim against stream_wb aggressors for all
WSS points on a given platform. Outputs one CSV per sweep configuration.

Usage (requires frozen system state — run setup/<platform>_freeze.sh first):
  python3 wss_sweep.py --platform emr --sweep cxl8 --out-dir results/
  python3 wss_sweep.py --platform spr --sweep local4 --out-dir results/
  python3 wss_sweep.py --platform emr --sweep all --out-dir results/

Platforms:
  emr  Intel Xeon Platinum 8592+ (Emerald Rapids), 320 MB LLC, same-socket CXL
  spr  Intel Xeon Platinum 8462Y+ (Sapphire Rapids), 60 MB LLC, cross-socket CXL

Sweeps:
  cxl8    8 aggressors on CXL NUMA node (node 2)
  local4  4 aggressors on local DRAM (node 0)
  all     both cxl8 and local4
"""

import argparse
import csv
import json
import re
import signal
import statistics
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1] / "bench"
VICTIM_BIN = BENCH / "victim" / "pointer_chase_nocap"
AGG_BIN    = BENCH / "aggressor" / "stream_wb"

N_TRIALS   = 30
MEASURE_SEC = 10
WARMUP_SEC  = 8
COOLDOWN_SEC = 2
READY_TIMEOUT_SEC = 180
VICTIM_CPU = 0
VICTIM_NODE = 0
AGGR_REGION_GB = 5


@dataclass(frozen=True)
class Platform:
    name: str
    llc_mb: int
    wss_points_mb: list
    cxl_node: int

    @property
    def wss_fractions(self):
        return [round(w / self.llc_mb, 2) for w in self.wss_points_mb]


@dataclass(frozen=True)
class SweepConfig:
    name: str
    aggr_cpus: list
    aggr_node: int


PLATFORMS = {
    "emr": Platform("emr", 320, [80, 170, 320], cxl_node=2),
    "spr": Platform("spr", 60,  [15, 32, 60],   cxl_node=2),
}

def make_sweeps(platform: Platform) -> dict:
    return {
        "cxl8":   SweepConfig("cxl8",   [1,2,3,4,5,6,7,8], platform.cxl_node),
        "local4": SweepConfig("local4", [1,2,3,4],          0),
    }


class Aggressor:
    def __init__(self, cpu: int, node: int, duration_sec: int):
        self.cpu = cpu
        self.node = node
        self.duration_sec = duration_sec
        self.proc = None
        self.err: list[str] = []
        self.out: list[str] = []

    def start(self):
        cmd = [
            "numactl", f"--membind={self.node}", "--cpunodebind=0", "--",
            str(AGG_BIN),
            "--cpu", str(self.cpu),
            "--node", str(self.node),
            "--region-gb", str(AGGR_REGION_GB),
            "--duration-sec", str(self.duration_sec),
            "--no-verify",
        ]
        self.proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        threading.Thread(target=lambda: [self.err.append(l.rstrip()) for l in self.proc.stderr], daemon=True).start()
        threading.Thread(target=lambda: [self.out.append(l.rstrip()) for l in self.proc.stdout], daemon=True).start()

    def is_ready(self) -> bool:
        return any(re.search(r"bw=[0-9.]+", l) for l in self.err)

    def current_bw(self) -> float:
        for line in reversed(self.err):
            m = re.search(r"bw=([0-9.]+) GB/s", line)
            if m:
                return float(m.group(1))
        return 0.0

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill(); self.proc.wait()


def wait_ready(aggs: list, label: str):
    deadline = time.monotonic() + READY_TIMEOUT_SEC
    while time.monotonic() < deadline:
        dead = [a.cpu for a in aggs if a.proc.poll() is not None]
        if dead:
            raise RuntimeError(f"{label}: aggressor cpus={dead} exited early")
        if all(a.is_ready() for a in aggs):
            return
        time.sleep(0.5)
    raise RuntimeError(f"{label}: aggressor readiness timeout")


def run_victim(wss_mb: int) -> list[dict]:
    cmd = [
        "numactl", f"--membind={VICTIM_NODE}", "--cpunodebind=0", "--",
        str(VICTIM_BIN),
        "--cpu", str(VICTIM_CPU),
        "--node", str(VICTIM_NODE),
        "--wss", str(wss_mb * 1024 * 1024),
        "--trials", str(N_TRIALS),
        "--run-sec", str(MEASURE_SEC),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True,
                       timeout=N_TRIALS * (MEASURE_SEC + 2) + 60)
    if r.returncode != 0:
        raise RuntimeError(f"victim failed:\n{r.stderr[-1000:]}")
    return json.loads(r.stdout)


def check_frozen_state():
    """Warn if governor or no_turbo look wrong."""
    issues = []
    try:
        gov = open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor").read().strip()
        if gov != "performance":
            issues.append(f"governor={gov} (want performance)")
    except FileNotFoundError:
        pass
    try:
        turbo = open("/sys/devices/system/cpu/intel_pstate/no_turbo").read().strip()
        if turbo != "1":
            issues.append("turbo is ON (want no_turbo=1)")
    except FileNotFoundError:
        pass
    try:
        nb = open("/proc/sys/kernel/numa_balancing").read().strip()
        if nb != "0":
            issues.append("numa_balancing=1 (want 0)")
    except FileNotFoundError:
        pass
    if issues:
        print("WARNING: system may not be frozen:", "; ".join(issues), flush=True)
        print("         Run setup/<platform>_freeze.sh first for reproducible results.\n", flush=True)


def check_binaries():
    for b in [VICTIM_BIN, AGG_BIN]:
        if not b.exists():
            sys.exit(f"ERROR: binary not found: {b}\n       Run: make -C bench/")


def run_sweep(platform: Platform, sw: SweepConfig, out_dir: Path) -> Path:
    tag = f"{platform.name}_{sw.name}"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    kernel = subprocess.check_output(["uname", "-r"], text=True).strip()

    for wss_mb in platform.wss_points_mb:
        frac = round(wss_mb / platform.llc_mb, 3)
        for cond in ("Q", "A"):
            print(f"  [{tag}] wss={wss_mb}MB cond={cond}", flush=True)
            aggs = []

            if cond == "A":
                dur = N_TRIALS * (MEASURE_SEC + COOLDOWN_SEC + 2) + 60
                for cpu in sw.aggr_cpus:
                    a = Aggressor(cpu, sw.aggr_node, dur)
                    a.start()
                    aggs.append(a)
                wait_ready(aggs, f"{tag}/wss{wss_mb}")
                print(f"    {len(aggs)} aggressors ready on node {sw.aggr_node}", flush=True)
                time.sleep(WARMUP_SEC)

            try:
                trials = run_victim(wss_mb)
            finally:
                for a in aggs:
                    a.stop()

            agg_bw = sum(a.current_bw() for a in aggs) if aggs else 0.0

            for tr in trials:
                rows.append({
                    "platform": platform.name,
                    "kernel": kernel,
                    "llc_mb": platform.llc_mb,
                    "sweep": sw.name,
                    "aggr_node": sw.aggr_node if cond == "A" else "",
                    "aggr_cpus": len(sw.aggr_cpus) if cond == "A" else 0,
                    "victim_wss_mb": wss_mb,
                    "victim_wss_fraction_llc": frac,
                    "condition": cond,
                    "trial": tr["trial"],
                    "cycles_per_load": round(float(tr["cycles_per_load"]), 4),
                    "total_loads": int(tr["total_loads"]),
                    "elapsed_sec": float(tr["elapsed_sec"]),
                    "tsc_hz": int(tr["tsc_hz"]),
                    "agg_bw_gbps": round(agg_bw, 3),
                })
            time.sleep(COOLDOWN_SEC)

    csv_path = out_dir / f"{tag}.csv"
    fields = list(rows[0].keys()) if rows else []
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

    _print_summary(rows, platform, sw)
    print(f"  Wrote {csv_path}\n", flush=True)
    return csv_path


def _print_summary(rows, platform, sw):
    for wss_mb in platform.wss_points_mb:
        q = [float(r["cycles_per_load"]) for r in rows if r["condition"] == "Q" and int(r["victim_wss_mb"]) == wss_mb]
        a = [float(r["cycles_per_load"]) for r in rows if r["condition"] == "A" and int(r["victim_wss_mb"]) == wss_mb]
        if not q:
            continue
        qm = statistics.median(q)
        am = statistics.median(a) if a else None
        sx = f"{am/qm:.3f}x" if am else "—"
        bw_vals = [float(r["agg_bw_gbps"]) for r in rows if r["condition"] == "A" and int(r["victim_wss_mb"]) == wss_mb]
        bw = statistics.mean(bw_vals) if bw_vals else 0
        a_str = f"{am:.1f}" if am else "—"
        print(f"  wss={wss_mb:3d}MB  Q={qm:.1f}  A={a_str}  slowdown={sx}  aggBW={bw:.1f}GB/s",
              flush=True)


def main():
    ap = argparse.ArgumentParser(description="WSS sweep: WB streaming tax measurement")
    ap.add_argument("--platform", required=True, choices=["emr", "spr"],
                    help="Target platform (emr=8592+ 320MB LLC, spr=8462Y+ 60MB LLC)")
    ap.add_argument("--sweep", default="all", choices=["cxl8", "local4", "all"],
                    help="Aggressor configuration to run")
    ap.add_argument("--out-dir", default="results", type=Path,
                    help="Output directory for CSV results")
    ap.add_argument("--skip-env-check", action="store_true",
                    help="Skip frozen-state environment validation")
    args = ap.parse_args()

    check_binaries()
    if not args.skip_env_check:
        check_frozen_state()

    platform = PLATFORMS[args.platform]
    sweeps = make_sweeps(platform)
    to_run = list(sweeps.values()) if args.sweep == "all" else [sweeps[args.sweep]]

    print(f"Platform: {platform.name.upper()}  LLC={platform.llc_mb}MB  "
          f"WSS={platform.wss_points_mb}MB", flush=True)
    for sw in to_run:
        print(f"\n=== Sweep: {sw.name} ({len(sw.aggr_cpus)} aggressors, node {sw.aggr_node}) ===",
              flush=True)
        run_sweep(platform, sw, args.out_dir / platform.name)


if __name__ == "__main__":
    main()
