#!/usr/bin/env python3
"""Run the pre-registered, standalone GAPBS sizing gate on one silicon host."""

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GAPBS = ROOT / "benchmarks/e2e/gapbs/third_party/gapbs"
OUT = ROOT / "benchmarks/e2e/gapbs/artifacts"
APPS = {"bfs": "bfs", "pr": "pr", "cc": "cc"}
HOSTS = {
    "mos181": {"cpu": "32", "node": "0", "private_l2_bytes": 2 * 1024**2},
    "moscxl": {"cpu": "8", "node": "0", "private_l2_bytes": 1 * 1024**2},
}
TRIAL_RE = re.compile(r"Trial Time:\s+([0-9.]+)")


def output(cmd):
    return subprocess.run(cmd, text=True, capture_output=True, check=False).stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scales", default="20,22,24,25")
    parser.add_argument("--apps", default="bfs,pr,cc")
    parser.add_argument("--trials", type=int, default=4,
                        help="one warm-up plus this many GAPBS trials; default is 4")
    parser.add_argument("--repeat", type=int, default=1,
                        help="repeat the whole trial block; used only after the raw scale sweep")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    host = platform.node().split(".")[0]
    if host not in HOSTS:
        raise SystemExit(f"unsupported host {host}; expected one of {sorted(HOSTS)}")
    if args.trials < 4:
        raise SystemExit("--trials must be >= 4: one warm-up and three measured trials")
    config = HOSTS[host]
    if not (GAPBS / ".git").is_dir():
        raise SystemExit(f"GAPBS source missing at {GAPBS}; run setup_gapbs.sh first")

    scales = [int(x) for x in args.scales.split(",")]
    apps = args.apps.split(",")
    unknown = sorted(set(apps) - APPS.keys())
    if unknown:
        raise SystemExit(f"unknown apps: {unknown}")
    out_path = args.output or OUT / f"sizing_gate_{host}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    git_commit = output(["git", "-C", str(GAPBS), "rev-parse", "HEAD"])
    env = os.environ.copy()
    env.update({"OMP_NUM_THREADS": "1", "OMP_PROC_BIND": "true", "OMP_PLACES": "cores"})

    with out_path.open("a", encoding="ascii") as f:
        for app in apps:
            for scale in scales:
                for block in range(1, args.repeat + 1):
                    cmd = ["taskset", "-c", config["cpu"], str(GAPBS / APPS[app]),
                           "-g", str(scale), "-n", str(args.trials), "-r", "1", "-l"]
                    started = time.time()
                    proc = subprocess.Popen(cmd, cwd=GAPBS, text=True, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, env=env)
                    lines, numa_sample, sampled = [], None, False
                    assert proc.stdout is not None
                    for line in proc.stdout:
                        lines.append(line)
                        # The graph exists after this line; sample actual allocation while trials run.
                        if not sampled and line.startswith("Graph has"):
                            numa_sample = output(["numastat", "-p", str(proc.pid)])
                            sampled = True
                    rc = proc.wait()
                    trial_times = [float(x) for x in TRIAL_RE.findall("".join(lines))]
                    record = {
                        "campaign": "gapbs_sizing_gate", "host": host, "hostname": platform.node(),
                        "app": app, "scale": scale, "block": block, "command": cmd,
                        "gapbs_commit": git_commit, "cpu_requested": config["cpu"],
                        "node_requested": config["node"], "private_l2_bytes": config["private_l2_bytes"],
                        "omp_num_threads": 1, "returncode": rc, "wall_seconds": time.time() - started,
                        "trial_seconds_all": trial_times, "trial_seconds_measured": trial_times[1:],
                        "numastat_after_graph_build": numa_sample, "stdout": "".join(lines),
                        "timestamp_unix": started,
                    }
                    f.write(json.dumps(record, sort_keys=True) + "\n")
                    f.flush()
                    print(f"{host} {app} g{scale} block {block}: rc={rc} trials={trial_times}",
                          file=sys.stderr, flush=True)
                    if rc or len(trial_times) != args.trials:
                        raise SystemExit(f"invalid run for {app} g{scale}; raw record retained at {out_path}")


if __name__ == "__main__":
    main()
