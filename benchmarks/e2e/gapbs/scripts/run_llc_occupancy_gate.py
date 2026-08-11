#!/usr/bin/env python3
"""Quiescent PageRank CMT occupancy gate; no aggressor is ever launched."""
import json, os, platform, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GAPBS = ROOT / "benchmarks/e2e/gapbs/third_party/gapbs"
OUT = ROOT / "benchmarks/e2e/gapbs/artifacts"
CFG = {"mos181": ("32", 0, 320 * 1024**2), "moscxl": ("8", 0, 16 * 1024**2)}
TRIAL = re.compile(r"Trial Time:\s+([0-9.]+)")

def sh(cmd, check=True):
    return subprocess.run(cmd, text=True, capture_output=True, check=check)

def sudo(cmd, check=True):
    return sh(["sudo", "-n"] + cmd, check=check)

def read(path):
    return int(Path(path).read_text().strip())

def main():
    host = platform.node().split(".")[0]
    if host not in CFG: raise SystemExit(f"unsupported host {host}")
    cpu, domain, llc_bytes = CFG[host]
    scales = [int(x) for x in os.environ.get("GAPBS_OCC_SCALES", "21,22,23,24,25").split(",")]
    if not (GAPBS / ".git").is_dir(): raise SystemExit("run setup_gapbs.sh first")
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"llc_occupancy_gate_{host}.jsonl"
    env = {**os.environ, "OMP_NUM_THREADS":"1", "OMP_PROC_BIND":"true", "OMP_PLACES":"cores"}
    for scale in scales:
        group = f"gapbs_occ_{os.getpid()}_{scale}"
        group_path = Path("/sys/fs/resctrl") / group
        sudo(["mkdir", str(group_path)])
        proc = None
        try:
            cmd = ["taskset", "-c", cpu, str(GAPBS / "pr"), "-g", str(scale), "-n", "4", "-r", "1", "-l"]
            proc = subprocess.Popen(cmd, cwd=GAPBS, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            lines, samples, attached = [], [], False
            for line in proc.stdout:
                lines.append(line)
                if line.startswith("Graph has") and not attached:
                    sudo(["sh", "-c", f"echo {proc.pid} > {group_path}/tasks"])
                    attached = True
                if attached and line.startswith("Trial Time:"):
                    mon = group_path / "mon_data" / f"mon_L3_{domain:02d}"
                    samples.append({"llc_occupancy":read(mon / "llc_occupancy"),
                                    "mbm_local_bytes":read(mon / "mbm_local_bytes"),
                                    "mbm_total_bytes":read(mon / "mbm_total_bytes")})
            rc = proc.wait()
            rec = {"campaign":"gapbs_llc_occupancy_gate", "host":host, "scale":scale,
                   "command":cmd, "cpu_requested":cpu, "l3_domain":domain, "llc_bytes":llc_bytes,
                   "returncode":rc, "attached":attached, "trial_seconds_all":[float(x) for x in TRIAL.findall(''.join(lines))],
                   "cmt_samples":samples, "stdout":''.join(lines), "timestamp_unix":time.time()}
            with out.open("a") as f: f.write(json.dumps(rec, sort_keys=True) + "\n")
            if rc or not attached or len(samples) != 4: raise SystemExit(f"invalid g{scale}; record retained")
        finally:
            if proc and proc.poll() is None: proc.terminate()
            sudo(["rmdir", str(group_path)], check=False)

if __name__ == "__main__": main()
