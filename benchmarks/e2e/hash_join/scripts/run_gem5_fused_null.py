#!/usr/bin/env python3
"""Launch gem5 fused-null audit runs as tmux sessions.

Usage:
  ./benchmarks/e2e/hash_join/scripts/run_gem5_fused_null.py launch t1
  ./benchmarks/e2e/hash_join/scripts/run_gem5_fused_null.py status t1
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
GEM5_SRC = REPO / "gem5"
GEM5 = Path("/home/domin/DutyFree-Gem5/build_Intel_8592/gem5.opt")
CFG = GEM5_SRC / "configs/deprecated/example/se.py"
CHI = GEM5_SRC / "configs/ruby/CHI_config_8592.py"
BIN = REPO / "benchmarks/e2e/hash_join/build/cxl_join_bench.gem5"
OUT_ROOT = REPO / "results/gem5/hash_join_fused_null"

COMMON_ENV = {
    "RUBY_RANDOMIZATION": "1",
    "L1_MSHR": "16",
    "PF_DEGREE_L1": "4",
    "PF_DEGREE_L2": "8",
    "PF_PAGE": "4KiB",
}

GEOMETRIES = {
    "t1": {
        "num_cpus": 2,
        "l2_size": "256KiB",
        "l2_assoc": "8",
        "l3_size": "5MiB",
        "l3_assoc": "20",
        # F9.4 (W4.3 ledger, 2026-08-23): this arithmetic intends 53% of the
        # 5 MiB modelled LLC = 2,778,726 B, but cxl_join_bench.cpp:369
        # `table_capacity` rounds 173,670 entries up to 2^18 = 262,144 and
        # `build_table` instantiates them all, so the RESIDENT hot table is
        # 4 MiB = 80.0% of the LLC and 16.0x the 256 KiB L2 -- not 53% / 10.6x.
        # No published number depends on this: the T1 campaign it configures
        # was stopped after 1:11:28 with zero-byte stats for all three arms
        # (GEM5_FUSED_NULL_OUTCOME.md). Left as written rather than "fixed",
        # because 53% of 5 MiB is unreachable by this kernel: the achievable
        # neighbours are 2 MiB (40%) and 4 MiB (80%). Any re-run must choose.
        "hot_bytes": 5 * 1024 * 1024 * 53 // 100,
        "fact_bytes": "16m",
        "threads": 1,
        "cpu_list": "0",
    },
}

ARMS = {
    "q": ("probe-workload", "wb", ""),
    "wb": ("morsel", "wb", "--morsel 1m --check"),
    "h2": ("morsel", "stream", "--morsel 1m --check"),
}


def run(cmd: list[str], **kwargs):
    return subprocess.run(cmd, text=True, capture_output=True, check=False, **kwargs)


def gem5_command(geometry: str, arm: str) -> tuple[str, Path]:
    g = GEOMETRIES[geometry]
    mode, policy, extra = ARMS[arm]
    outdir = OUT_ROOT / "stats" / f"{geometry}_{arm}"
    opts = (
        f"--mode {mode} --policy {policy} --fact-bytes {g['fact_bytes']} "
        f"--fact-node 1 --hot-node 0 --hot-bytes {g['hot_bytes']} "
        f"--threads {g['threads']} --cpu-list {g['cpu_list']} "
        f"--warmups 1 --reps 3 {extra}"
    )
    env = " ".join(f"{k}={shlex.quote(v)}" for k, v in COMMON_ENV.items())
    cmd = f"""
set -euo pipefail
cd {shlex.quote(str(REPO))}
{env} {shlex.quote(str(GEM5))} --outdir={shlex.quote(str(outdir))} \\
  {shlex.quote(str(CFG))} --cmd={shlex.quote(str(BIN))} \\
  --options={shlex.quote(opts)} \\
  --ruby --topology=Pt2Pt --chi-config={shlex.quote(str(CHI))} \\
  --num-l3caches=1 --num-dirs=1 --cpu-type=O3CPU --num-cpus={g['num_cpus']} --cpu-clock=1.9GHz \\
  --l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \\
  --l2_size={g['l2_size']} --l2_assoc={g['l2_assoc']} \\
  --l3_size={g['l3_size']} --l3_assoc={g['l3_assoc']} \\
  --mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \\
  --dram-latency=98ns --cxl-latency=203ns
"""
    return cmd.strip(), outdir


def launch(geometry: str):
    OUT_ROOT.joinpath("stats").mkdir(parents=True, exist_ok=True)
    manifest = []
    for arm in ARMS:
        name = f"gem5_fused_null_{geometry}_{arm}"
        cmd, outdir = gem5_command(geometry, arm)
        script = OUT_ROOT / f"{geometry}_{arm}.sh"
        script.write_text(cmd + "\n")
        script.chmod(0o755)
        log = OUT_ROOT / f"{geometry}_{arm}.launch.log"
        exists = run(["tmux", "has-session", "-t", name]).returncode == 0
        if exists:
            print(f"{name}: already running")
        else:
            wrapped = f"{shlex.quote(str(script))} > {shlex.quote(str(log))} 2>&1"
            cp = run(["tmux", "new-session", "-d", "-s", name, wrapped])
            if cp.returncode != 0:
                raise SystemExit(cp.stderr)
            print(f"{name}: launched")
        manifest.append({"name": name, "arm": arm, "outdir": str(outdir), "script": str(script)})
    (OUT_ROOT / f"{geometry}_launch_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def status(geometry: str):
    for arm in ARMS:
        name = f"gem5_fused_null_{geometry}_{arm}"
        tmux = run(["tmux", "has-session", "-t", name]).returncode == 0
        _, outdir = gem5_command(geometry, arm)
        stats = outdir / "stats.txt"
        if stats.exists():
            stats_state = f"{stats.stat().st_size} bytes"
        else:
            stats_state = "missing"
        print(f"{name}: {'running' if tmux else 'not-running'} stats={stats_state}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["launch", "status"])
    ap.add_argument("geometry", choices=GEOMETRIES)
    ns = ap.parse_args()
    if ns.cmd == "launch":
        launch(ns.geometry)
    else:
        status(ns.geometry)


if __name__ == "__main__":
    main()
