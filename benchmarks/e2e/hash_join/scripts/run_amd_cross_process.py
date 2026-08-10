#!/usr/bin/env python3
"""AMD cross-process hash-join victim vs stream_wb/stream_wc aggressors.

Run on broker with sudo. The runner mirrors the AMD E1 triple discipline:
fresh aggressor launch per loaded arm, rep-interleaved arms, victim in a
separate resctrl group from seven same-CCX aggressor processes.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

RESCTRL = Path("/sys/fs/resctrl")
VGRP = RESCTRL / "hj_v"
AGRP = RESCTRL / "hj_a"

DEFAULT_ROOT = Path("/home/domin/tmp_dutyfree_exp/hash_join_cross_process")
DEFAULT_VICTIM = DEFAULT_ROOT / "cxl_join_bench"
DEFAULT_AGG_DIR = Path("/home/domin/tmp_dutyfree_exp/intel_experiments/bench/aggressor")

VICTIM_CPU = "0"
AGG_CPUS = [1, 2, 3, 4, 5, 6, 7]
AGG_NODE = 2
HOT_NODE = 0

ARMS = {
    "quiescent": None,
    "wb": "stream_wb",
    "wc": "stream_wc",
}
ARM_ORDER = ["quiescent", "wb", "wc"]


def sh(cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, shell=True, text=True, capture_output=True, check=False)


def write(path: Path, text: str) -> None:
    path.write_text(text)


def write_schemata(grp: Path, l3: str = "ffff", smba: str = "2048") -> None:
    write(grp / "schemata", f"L3:0={l3}\nSMBA:0={smba}\n")


def read_int(path: Path) -> int | None:
    try:
        text = path.read_text().strip()
        if text == "Unavailable":
            return None
        return int(text)
    except (FileNotFoundError, ValueError):
        return None


def read_mbm(grp: Path) -> int | None:
    return read_int(grp / "mon_data/mon_L3_00/mbm_total_bytes")


def read_occ(grp: Path) -> int | None:
    return read_int(grp / "mon_data/mon_L3_00/llc_occupancy")


def pkill_aggressors(agg_dir: Path) -> None:
    for name in ("stream_wb", "stream_wc"):
        sh(f"pkill -f {str(agg_dir / name)!r} 2>/dev/null")
    time.sleep(0.2)


def ensure_groups(agg_dir: Path) -> None:
    pkill_aggressors(agg_dir)
    for grp in (VGRP, AGRP):
        grp.mkdir(exist_ok=True)
    write(VGRP / "cpus_list", VICTIM_CPU)
    write(AGRP / "cpus_list", ",".join(str(c) for c in AGG_CPUS))
    write_schemata(VGRP)
    write_schemata(AGRP)


def cleanup(agg_dir: Path) -> None:
    pkill_aggressors(agg_dir)
    for grp in (VGRP, AGRP):
        try:
            grp.rmdir()
        except OSError:
            pass


def hugepages_total() -> int:
    return int(Path("/proc/sys/vm/nr_hugepages").read_text().strip())


def ensure_hugepages(min_pages: int) -> int:
    old = hugepages_total()
    if old < min_pages:
        write(Path("/proc/sys/vm/nr_hugepages"), f"{min_pages}\n")
        time.sleep(0.5)
    got = hugepages_total()
    if got < min_pages:
        raise RuntimeError(f"could not reserve {min_pages} hugepages; got {got}")
    return old


def restore_hugepages(old: int) -> None:
    write(Path("/proc/sys/vm/nr_hugepages"), f"{old}\n")


def parse_json_line(text: str) -> dict:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise RuntimeError(f"no JSON object in victim stdout:\n{text[-1000:]}")


def parse_aggressor_json(text: str) -> dict | None:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    return None


def occ_sampler(stop: threading.Event, samples: list[int]) -> None:
    while not stop.is_set():
        occ = read_occ(VGRP)
        if occ is not None:
            samples.append(occ)
        time.sleep(0.25)


def launch_aggressors(arm: str, agg_dir: Path, region_gb: int, duration_s: float, log_dir: Path, rep: int):
    exe_name = ARMS[arm]
    if exe_name is None:
        return []
    procs = []
    for cpu in AGG_CPUS:
        log = log_dir / f"agg_{arm}_rep{rep}_cpu{cpu}.log"
        cmd = [
            str(agg_dir / exe_name),
            "--cpu", str(cpu),
            "--node", str(AGG_NODE),
            "--region-gb", str(region_gb),
            "--duration-sec", f"{duration_s:.3f}",
        ]
        if exe_name == "stream_wb":
            cmd.append("--no-verify")
        fh = log.open("w")
        proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT)
        procs.append((proc, fh, log))
    return procs


def collect_aggressors(procs, timeout_s: float) -> list[dict]:
    out = []
    for proc, fh, log in procs:
        try:
            proc.wait(timeout=timeout_s)
        finally:
            fh.close()
        text = log.read_text(errors="replace") if log.exists() else ""
        rec = parse_aggressor_json(text) or {"parse_error": True}
        rec["log"] = str(log)
        rec["returncode"] = proc.returncode
        out.append(rec)
    return out


def run_victim(victim: Path, hot_bytes: int, fact_bytes: str, warmups: int, reps: int) -> subprocess.CompletedProcess[str]:
    cmd = [
        str(victim),
        "--mode", "morsel",
        "--policy", "wb",
        "--no-stream",
        "--fact-bytes", fact_bytes,
        "--fact-node", str(HOT_NODE),
        "--hot-node", str(HOT_NODE),
        "--hot-bytes", str(hot_bytes),
        "--threads", "1",
        "--cpu-list", VICTIM_CPU,
        "--warmups", str(warmups),
        "--reps", str(reps),
        "--morsel", "1m",
        "--check",
    ]
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def run_one(args: argparse.Namespace, arm: str, rep: int, outf) -> None:
    write_schemata(VGRP)
    write_schemata(AGRP)

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    mbm_start = read_mbm(AGRP)
    t_agg_start = time.time()
    procs = launch_aggressors(arm, Path(args.agg_dir), args.agg_region_gb, args.agg_duration_s, log_dir, rep)
    if procs:
        time.sleep(args.agg_settle_s)

    occ_samples: list[int] = []
    stop = threading.Event()
    sampler = threading.Thread(target=occ_sampler, args=(stop, occ_samples))
    sampler.start()
    t0 = time.time()
    victim_proc = run_victim(Path(args.victim), args.hot_bytes, args.fact_bytes, args.warmups, args.reps_per_call)
    t1 = time.time()
    stop.set()
    sampler.join()

    agg_records = collect_aggressors(procs, args.agg_duration_s + 10.0) if procs else []
    t_agg_end = time.time()
    mbm_end = read_mbm(AGRP)

    if victim_proc.returncode != 0:
        raise RuntimeError(
            f"victim failed arm={arm} rep={rep} rc={victim_proc.returncode}\n"
            f"stdout={victim_proc.stdout}\nstderr={victim_proc.stderr}"
        )
    victim_json = parse_json_line(victim_proc.stdout)
    agg_bw = [r.get("avg_bw_gbps") for r in agg_records if isinstance(r.get("avg_bw_gbps"), (int, float))]
    occ = {
        "n": len(occ_samples),
        "mean": (sum(occ_samples) / len(occ_samples)) if occ_samples else None,
        "min": min(occ_samples) if occ_samples else None,
        "max": max(occ_samples) if occ_samples else None,
    }
    rec = {
        "arm": arm,
        "rep": rep,
        "victim_mode": "morsel_no_stream",
        "wall_dur_s": t1 - t0,
        "victim": victim_json,
        "metric_cycles_per_access": victim_json.get("active_cycles_per_access"),
        "aggressor_records": agg_records,
        "agg_bw_self_gbps_sum": sum(agg_bw) if agg_bw else None,
        "agg_bw_self_gbps_mean_per_proc": (sum(agg_bw) / len(agg_bw)) if agg_bw else None,
        "agg_mbm_bw_gbps": ((mbm_end - mbm_start) / (t_agg_end - t_agg_start) / 1e9)
        if mbm_start is not None and mbm_end is not None and t_agg_end > t_agg_start
        else None,
        "victim_llc_occ_bytes": occ,
    }
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(
        f"{arm:9s} rep={rep:02d} cpa={rec['metric_cycles_per_access']:.2f} "
        f"victim_s={rec['wall_dur_s']:.3f} agg_sum={rec['agg_bw_self_gbps_sum']} "
        f"mbm={rec['agg_mbm_bw_gbps']} occ={occ['mean']}",
        flush=True,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=12)
    ap.add_argument("--hot-bytes", type=int, default=8 * 1024 * 1024)
    ap.add_argument("--fact-bytes", default="512m")
    ap.add_argument("--warmups", type=int, default=1)
    ap.add_argument("--reps-per-call", type=int, default=3)
    ap.add_argument("--agg-region-gb", type=int, default=1)
    ap.add_argument("--agg-duration-s", type=float, default=16.0)
    ap.add_argument("--agg-settle-s", type=float, default=2.0)
    ap.add_argument("--victim", default=str(DEFAULT_VICTIM))
    ap.add_argument("--agg-dir", default=str(DEFAULT_AGG_DIR))
    ap.add_argument("--out", default=str(DEFAULT_ROOT / "amd_hash_join_cross_process_n12.jsonl"))
    ap.add_argument("--log-dir", default=str(DEFAULT_ROOT / "logs"))
    ap.add_argument("--keep-hugepages", action="store_true")
    args = ap.parse_args()

    if os.geteuid() != 0:
        raise SystemExit("run with sudo: resctrl and hugepage reservation require root")

    min_hugepages = len(AGG_CPUS) * args.agg_region_gb * 512
    old_hugepages = ensure_hugepages(min_hugepages)

    def handle_signal(signum, frame):
        cleanup(Path(args.agg_dir))
        if not args.keep_hugepages:
            restore_hugepages(old_hugepages)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    ensure_groups(Path(args.agg_dir))
    try:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w") as outf:
            for rep in range(1, args.reps + 1):
                for arm in ARM_ORDER:
                    run_one(args, arm, rep, outf)
    finally:
        cleanup(Path(args.agg_dir))
        if not args.keep_hugepages:
            restore_hugepages(old_hugepages)
    print(f"DONE -> {args.out}")


if __name__ == "__main__":
    main()
