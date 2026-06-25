#!/usr/bin/env python3
"""
CAT/MBA double-dissociation measurement — called by cat_mba_driver.sh.

Measures victim performance under one condition (Q=quiescent, A=with aggressors).
resctrl groups must be configured by the driver before calling this script.

Usage (called by driver):
  python3 cat_mba.py <cond_name> <label> <wss_mb> <aggr_type>

  cond_name : short identifier, used as output subdirectory name
  label     : human-readable description
  wss_mb    : victim working set size in MB
  aggr_type : "cxl8" | "turnover8" | "none"

Output: results/<cond_name>/<cond_name>.csv  and  <cond_name>_report.md
"""

import csv
import json
import re
import signal
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1] / "bench"
VICTIM_BIN    = BENCH / "victim" / "pointer_chase_nocap"
AGG_STREAM_WB = BENCH / "aggressor" / "stream_wb"
AGG_TURNOVER  = BENCH / "aggressor" / "forced_turnover"

N_TRIALS   = 30
MEASURE_SEC = 10
WARMUP_SEC  = 8
COOLDOWN_SEC = 2
READY_TIMEOUT_SEC = 120

VICTIM_CPU  = 0
VICTIM_NODE = 0
LLC_MB      = 320

CXL8_CPUS        = [1, 2, 3, 4, 5, 6, 7, 8]
CXL8_NODE        = 2
CXL8_REGION_GB   = 5

TURNOVER_CPUS         = [1, 2, 3, 4, 5, 6, 7, 8]
TURNOVER_NODE         = 0
TURNOVER_REGION_BYTES = 4 * 1024 * 1024


class Aggressor:
    def __init__(self, aggr_type: str, cpu: int, node: int):
        self.aggr_type = aggr_type
        self.cpu = cpu
        self.node = node
        self.proc = None
        self.err: list[str] = []
        self.out: list[str] = []

    def start(self, duration_sec: int):
        if self.aggr_type == "cxl8":
            cmd = [
                "numactl", f"--membind={self.node}", "--cpunodebind=0", "--",
                str(AGG_STREAM_WB),
                "--cpu", str(self.cpu),
                "--node", str(self.node),
                "--region-gb", str(CXL8_REGION_GB),
                "--duration-sec", str(duration_sec),
                "--no-verify",
            ]
        else:
            cmd = [
                "numactl", f"--membind={self.node}", "--cpunodebind=0", "--",
                str(AGG_TURNOVER),
                "--cpu", str(self.cpu),
                "--node", str(self.node),
                "--region-bytes", str(TURNOVER_REGION_BYTES),
            ]
        self.proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        threading.Thread(target=lambda: [self.err.append(l.rstrip()) for l in self.proc.stderr], daemon=True).start()
        threading.Thread(target=lambda: [self.out.append(l.rstrip()) for l in self.proc.stdout], daemon=True).start()

    def is_ready(self) -> bool:
        if self.aggr_type == "cxl8":
            return any(re.search(r"bw=[0-9.]+", l) for l in self.err)
        return any("forced_turnover: cpu=" in l for l in self.err)

    def current_bw(self) -> float:
        if self.aggr_type == "cxl8":
            for line in reversed(self.err):
                m = re.search(r"bw=([0-9.]+) GB/s", line)
                if m:
                    return float(m.group(1))
        return 0.0

    def final_bw(self) -> float:
        for line in self.out:
            try:
                d = json.loads(line)
                return float(d.get("avg_bw_gbps", d.get("approx_bw_gbps", 0.0)))
            except (json.JSONDecodeError, KeyError):
                pass
        return 0.0

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill(); self.proc.wait()


def wait_ready(aggs: list, label: str):
    deadline = time.monotonic() + READY_TIMEOUT_SEC
    while time.monotonic() < deadline:
        dead = [a.cpu for a in aggs if a.proc.poll() is not None]
        if dead:
            raise RuntimeError(f"{label}: aggressors exited early: cpus={dead}")
        if all(a.is_ready() for a in aggs):
            return
        time.sleep(0.5)
    not_ready = [a.cpu for a in aggs if not a.is_ready()]
    raise RuntimeError(f"{label}: aggressors not ready: cpus={not_ready}")


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
                       timeout=N_TRIALS * (MEASURE_SEC + 2) + 120)
    if r.returncode != 0:
        raise RuntimeError(f"victim failed:\n{r.stderr[-2000:]}")
    return json.loads(r.stdout)


def run_condition(out_dir: Path, cond_name: str, label: str, wss_mb: int, aggr_type: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    kernel = subprocess.check_output(["uname", "-r"], text=True).strip()
    all_rows = []

    for phase in ("Q", "A"):
        print(f"  [{cond_name}] WSS={wss_mb}MB phase={phase}", flush=True)
        aggs = []

        if phase == "A" and aggr_type != "none":
            dur = N_TRIALS * (MEASURE_SEC + COOLDOWN_SEC + 2) + 120
            if aggr_type == "cxl8":
                cpus, node = CXL8_CPUS, CXL8_NODE
            else:
                cpus, node = TURNOVER_CPUS, TURNOVER_NODE

            for cpu in cpus:
                a = Aggressor(aggr_type, cpu, node)
                a.start(dur)
                aggs.append(a)

            wait_ready(aggs, f"{cond_name}/wss{wss_mb}")
            print(f"    {len(aggs)} aggressors ready ({aggr_type} node={node})", flush=True)
            time.sleep(WARMUP_SEC)

        try:
            trials = run_victim(wss_mb)
        finally:
            for a in aggs:
                a.stop()

        if phase == "A":
            if aggr_type == "cxl8":
                agg_bw = sum(a.current_bw() for a in aggs)
            else:
                agg_bw = sum(a.final_bw() for a in aggs)
        else:
            agg_bw = 0.0

        for tr in trials:
            all_rows.append({
                "condition": phase,
                "trial": tr["trial"],
                "platform": "emr",
                "kernel": kernel,
                "cond_name": cond_name,
                "label": label,
                "llc_mb": LLC_MB,
                "wss_mb": wss_mb,
                "wss_frac_llc": round(wss_mb / LLC_MB, 4),
                "aggr_type": aggr_type if phase == "A" else "none",
                "aggr_cpus": len(aggs),
                "aggr_node": (CXL8_NODE if aggr_type == "cxl8" else TURNOVER_NODE) if phase == "A" else "",
                "agg_bw_gbps": round(agg_bw, 3),
                "cycles_per_load": round(float(tr["cycles_per_load"]), 3),
                "total_loads": int(tr["total_loads"]),
                "elapsed_sec": float(tr["elapsed_sec"]),
                "tsc_hz": int(tr["tsc_hz"]),
            })
        time.sleep(COOLDOWN_SEC)

    fields = [
        "condition", "trial", "platform", "kernel", "cond_name", "label",
        "llc_mb", "wss_mb", "wss_frac_llc",
        "aggr_type", "aggr_cpus", "aggr_node", "agg_bw_gbps",
        "cycles_per_load", "total_loads", "elapsed_sec", "tsc_hz",
    ]
    csv_path = out_dir / f"{cond_name}.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(all_rows)

    _summarize(out_dir, cond_name, label, wss_mb, all_rows)
    print(f"  Wrote {csv_path}", flush=True)


def _summarize(out_dir: Path, cond_name: str, label: str, wss_mb: int, rows: list[dict]):
    q = [float(r["cycles_per_load"]) for r in rows if r["condition"] == "Q"]
    a = [float(r["cycles_per_load"]) for r in rows if r["condition"] == "A"]
    if not q:
        return
    qm = statistics.median(q)
    am = statistics.median(a) if a else None
    sx = f"{am/qm:.3f}x" if am else "1.000x"
    bw = statistics.mean([float(r["agg_bw_gbps"]) for r in rows if r["condition"] == "A"]) if a else 0.0

    lines = [
        f"# {label}",
        f"# Condition: {cond_name}  WSS: {wss_mb} MB ({wss_mb/LLC_MB:.1%} LLC)",
        "",
        f"Q median: {qm:.3f} cyc/load  n={len(q)}",
    ]
    if a:
        lines += [
            f"A median: {am:.3f} cyc/load  n={len(a)}",
            f"Slowdown: {sx}  AggBW: {bw:.2f} GB/s",
        ]
    rpt = out_dir / f"{cond_name}_report.md"
    rpt.write_text("\n".join(lines) + "\n")
    for l in lines:
        if l:
            print(f"  {l}", flush=True)


def main():
    if len(sys.argv) != 5:
        sys.exit("usage: cat_mba.py <cond_name> <label> <wss_mb> <aggr_type>")
    cond_name, label = sys.argv[1], sys.argv[2]
    wss_mb, aggr_type = int(sys.argv[3]), sys.argv[4]

    if aggr_type not in ("cxl8", "turnover8", "none"):
        sys.exit(f"aggr_type must be cxl8|turnover8|none, got: {aggr_type}")

    for b in [VICTIM_BIN, AGG_STREAM_WB, AGG_TURNOVER]:
        if not b.exists():
            sys.exit(f"Binary not found: {b}\nRun: make -C bench/")

    out_dir = Path(__file__).resolve().parent / "results" / cond_name
    print(f"\n{'='*60}", flush=True)
    print(f"Condition: {cond_name} | {label}", flush=True)
    print(f"WSS: {wss_mb} MB ({wss_mb/LLC_MB:.1%} of {LLC_MB} MB LLC)  aggr: {aggr_type}", flush=True)
    run_condition(out_dir, cond_name, label, wss_mb, aggr_type)


if __name__ == "__main__":
    main()
