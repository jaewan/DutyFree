#!/usr/bin/env python3
"""AMD cross-process hash-join victim vs AMD stream controls.

Run on broker with sudo. The runner mirrors the AMD E1 triple discipline:
fresh aggressor launch per loaded arm, rep-interleaved arms, victim in a
separate resctrl group from seven same-CCX aggressor processes.
"""
from __future__ import annotations

import argparse
import math
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
DEFAULT_AMD_BIN = Path("/home/domin/tmp_dutyfree_exp/bin")

VICTIM_CPU = "8"
AGG_CPUS = [9, 10, 11, 12, 13, 14, 15]
AGG_NODE = 2
HOT_NODE = 0

ARMS = {
    "quiescent": None,
    "wb": "amd_aggressor_wb",
    "wc": "amd_aggressor_wc",
    "flush_d256kb": "amd_flushbehind_aggressor",
}
ARM_ORDER = ["quiescent", "wb", "wc", "flush_d256kb"]


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


def read_mon_metric(grp: Path, metric: str) -> int | None:
    vals = []
    for path in sorted((grp / "mon_data").glob(f"mon_L3_*/{metric}")):
        val = read_int(path)
        if val is not None:
            vals.append(val)
    if vals:
        return sum(vals)
    return read_int(grp / "mon_data/mon_L3_00" / metric)


def read_mbm(grp: Path) -> int | None:
    return read_mon_metric(grp, "mbm_total_bytes")


def read_occ(grp: Path) -> int | None:
    return read_mon_metric(grp, "llc_occupancy")


def pkill_aggressors(amd_bin: Path) -> None:
    sh(f"pkill -f {str(amd_bin / 'aggressor')!r} 2>/dev/null")
    sh(f"pkill -f {str(amd_bin / 'amd_flushbehind_aggressor')!r} 2>/dev/null")
    time.sleep(0.2)


def ensure_groups(amd_bin: Path) -> None:
    pkill_aggressors(amd_bin)
    for grp in (VGRP, AGRP):
        grp.mkdir(exist_ok=True)
    write(VGRP / "cpus_list", VICTIM_CPU)
    write(AGRP / "cpus_list", ",".join(str(c) for c in AGG_CPUS))
    write_schemata(VGRP)
    write_schemata(AGRP)


def cleanup(amd_bin: Path) -> None:
    pkill_aggressors(amd_bin)
    for grp in (VGRP, AGRP):
        try:
            grp.rmdir()
        except OSError:
            pass


def hugepages_total() -> int:
    return int(Path("/proc/sys/vm/nr_hugepages").read_text().strip())


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


def parse_flushbehind_result(text: str) -> dict | None:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith("RESULT "):
            continue
        out: dict[str, object] = {}
        for tok in line.split()[1:]:
            if "=" not in tok:
                continue
            key, val = tok.split("=", 1)
            try:
                out[key] = float(val) if "." in val else int(val)
            except ValueError:
                out[key] = val
        if out.get("mode") != "flushbehind":
            continue
        out["condition"] = "flush_d256kb"
        return out
    return None


def parse_amd_aggressor_result(text: str) -> dict | None:
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith("RESULT "):
            continue
        out: dict[str, object] = {}
        for tok in line.split()[1:]:
            if "=" not in tok:
                continue
            key, val = tok.split("=", 1)
            try:
                out[key] = float(val) if "." in val else int(val)
            except ValueError:
                out[key] = val
        if "condition" not in out and "mode" in out:
            out["condition"] = out["mode"]
        return out
    return None


def occ_sampler(stop: threading.Event, samples: list[int]) -> None:
    while not stop.is_set():
        occ = read_occ(VGRP)
        if occ is not None:
            samples.append(occ)
        time.sleep(0.25)


def launch_aggressors(args: argparse.Namespace, arm: str, duration_s: float, log_dir: Path, rep: int):
    exe_name = ARMS[arm]
    if exe_name is None:
        return []
    amd_bin = Path(args.amd_bin)
    cores = ",".join(str(c) for c in AGG_CPUS)
    duration_i = str(int(round(duration_s)))
    if exe_name in ("amd_aggressor_wb", "amd_aggressor_wc"):
        mode = "wb_load" if exe_name == "amd_aggressor_wb" else "wc_ntdqa"
        log = log_dir / f"agg_{arm}_rep{rep}.log"
        cmd = [
            str(amd_bin / "aggressor"),
            "-m", mode,
            "-t", str(len(AGG_CPUS)),
            "-c", cores,
            "-N", str(AGG_NODE),
            "-s", str(args.amd_per_thread_mb),
            "-d", duration_i,
        ]
        fh = log.open("w")
        return [(subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT), fh, log)]
    if exe_name == "amd_flushbehind_aggressor":
        log = log_dir / f"agg_{arm}_rep{rep}.log"
        cmd = [
            str(amd_bin / exe_name),
            "-t", str(len(AGG_CPUS)),
            "-c", cores,
            "-N", str(AGG_NODE),
            "-s", str(args.flush_per_thread_mb),
            "-d", duration_i,
            "-f", str(args.flush_distance_kb),
        ]
        fh = log.open("w")
        return [(subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT), fh, log)]
    raise ValueError(f"unknown arm executable: {exe_name}")


def collect_aggressors(procs, timeout_s: float) -> list[dict]:
    out = []
    for proc, fh, log in procs:
        try:
            proc.wait(timeout=timeout_s)
        finally:
            fh.close()
        text = log.read_text(errors="replace") if log.exists() else ""
        rec = (
            parse_aggressor_json(text)
            or parse_flushbehind_result(text)
            or parse_amd_aggressor_result(text)
            or {"parse_error": True}
        )
        rec["log"] = str(log)
        rec["returncode"] = proc.returncode
        out.append(rec)
    return out


def parse_perf_csv(path: Path) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    if not path.exists():
        return out
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        val, event = parts[0].strip(), parts[2].strip()
        if val in ("<not counted>", "<not supported>"):
            out[event] = None
            continue
        try:
            out[event] = int(val)
        except ValueError:
            out[event] = None
    return out


def parse_hot_table_line(line: str) -> dict[str, int] | None:
    if not line.startswith("HOT_TABLE "):
        return None
    out: dict[str, int] = {}
    for tok in line.split()[1:]:
        if "=" not in tok:
            continue
        key, val = tok.split("=", 1)
        try:
            out[key] = int(val, 0)
        except ValueError:
            continue
    if {"pid", "base", "bytes"} <= set(out):
        return out
    return None


def summarize_counts(counts: list[int]) -> dict[str, float | int | None]:
    if not counts:
        return {"n": 0, "mean": None, "sd": None, "cov": None, "min": None, "max": None}
    mean = sum(counts) / len(counts)
    var = sum((x - mean) ** 2 for x in counts) / len(counts)
    return {
        "n": len(counts),
        "mean": mean,
        "sd": math.sqrt(var),
        "cov": (math.sqrt(var) / mean) if mean else None,
        "min": min(counts),
        "max": max(counts),
    }


def histogram_mod(vals: list[int], modulus: int) -> list[int]:
    hist = [0] * modulus
    for val in vals:
        hist[val % modulus] += 1
    return hist


def run_lengths(vals: list[int]) -> list[int]:
    if not vals:
        return []
    runs: list[int] = []
    cur = 1
    for prev, val in zip(vals, vals[1:]):
        if val == prev + 1:
            cur += 1
        else:
            runs.append(cur)
            cur = 1
    runs.append(cur)
    return runs


def dump_hot_table_pagemap(
    pid: int, base: int, byte_len: int, args: argparse.Namespace
) -> dict[str, object]:
    page_size = args.page_size
    line_size = args.llc_line_size
    llc_sets = args.llc_sets
    first_page = base // page_size
    last_page = (base + byte_len - 1) // page_size
    pfns: list[int | None] = []
    present_pfns: list[int] = []
    set_counts = [0] * llc_sets
    pagemap = Path(f"/proc/{pid}/pagemap")
    with pagemap.open("rb", buffering=0) as fh:
        for page in range(first_page, last_page + 1):
            fh.seek(page * 8)
            raw = fh.read(8)
            if len(raw) != 8:
                pfns.append(None)
                continue
            entry = int.from_bytes(raw, "little")
            if not (entry & (1 << 63)):
                pfns.append(None)
                continue
            pfn = entry & ((1 << 55) - 1)
            pfns.append(pfn)
            present_pfns.append(pfn)
            page_start = page * page_size
            region_start = max(base, page_start)
            region_end = min(base + byte_len, page_start + page_size)
            first_line = (region_start - page_start) // line_size
            last_line = (region_end - page_start + line_size - 1) // line_size
            for line in range(first_line, last_line):
                set_counts[((pfn * page_size) // line_size + line) % llc_sets] += 1
    nonzero_set_counts = [x for x in set_counts if x]
    sorted_pfns = sorted(present_pfns)
    runs = run_lengths(sorted_pfns)
    top_sets = sorted(
        ((count, idx) for idx, count in enumerate(set_counts) if count),
        reverse=True,
    )[:16]
    return {
        "pid": pid,
        "base": base,
        "bytes": byte_len,
        "page_size": page_size,
        "llc_line_size": line_size,
        "llc_sets": llc_sets,
        "total_pages": len(pfns),
        "present_pages": len(present_pfns),
        "unique_pfns": len(set(present_pfns)),
        "pfns": pfns,
        "pfn_min": min(present_pfns) if present_pfns else None,
        "pfn_max": max(present_pfns) if present_pfns else None,
        "pfn_run_summary": summarize_counts(runs),
        "pfn_mod_16_hist": histogram_mod(present_pfns, 16),
        "pfn_mod_64_hist": histogram_mod(present_pfns, 64),
        "pfn_mod_512_hist": histogram_mod(present_pfns, 512),
        "pfn_2m_frame_mod_32_hist": histogram_mod([p // 512 for p in present_pfns], 32),
        "llc_set_nonzero": len(nonzero_set_counts),
        "llc_set_count_summary": summarize_counts(nonzero_set_counts),
        "llc_set_top16": [{"set": idx, "lines": count} for count, idx in top_sets],
    }


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


def run_victim_with_optional_perf(
    args: argparse.Namespace, arm: str, rep: int, on_warmed=None
) -> tuple[subprocess.CompletedProcess[str], dict[str, int | None] | None, dict[str, object] | None]:
    victim = Path(args.victim)
    cmd = [
        str(victim),
        "--mode", "morsel",
        "--policy", "wb",
        "--no-stream",
        "--fact-bytes", args.fact_bytes,
        "--fact-node", str(HOT_NODE),
        "--hot-node", str(HOT_NODE),
        "--hot-bytes", str(args.hot_bytes),
        "--threads", "1",
        "--cpu-list", VICTIM_CPU,
        "--warmups", str(args.warmups),
        "--reps", str(args.reps_per_call),
        "--morsel", "1m",
        "--check",
    ]
    if args.victim_pre_measure_sleep_s > 0.0:
        cmd.extend(["--pre-measure-sleep-s", str(args.victim_pre_measure_sleep_s)])
    if not args.perf_cpu_events and not args.dump_pagemap and on_warmed is None:
        return subprocess.run(cmd, text=True, capture_output=True, check=False), None, None

    full_cmd = cmd
    perf_out = Path(args.log_dir) / f"perf_{arm}_rep{rep}.csv"
    if args.perf_cpu_events:
        full_cmd = [
            "perf", "stat",
            "-e", args.perf_cpu_events,
            "-C", str(args.perf_cpu),
            "-x", ",",
            "-o", str(perf_out),
            "--",
            *cmd,
        ]

    proc = subprocess.Popen(
        full_cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    stderr_lines: list[str] = []
    hot_table: dict[str, int] | None = None
    hot_event = threading.Event()
    warmed_called = False

    def read_stderr() -> None:
        nonlocal hot_table, warmed_called
        assert proc.stderr is not None
        for line in proc.stderr:
            stderr_lines.append(line)
            parsed = parse_hot_table_line(line.strip())
            if parsed and hot_table is None:
                hot_table = parsed
                hot_event.set()
            if line.startswith("HOT_TABLE_WARMED ") and on_warmed is not None and not warmed_called:
                warmed_called = True
                on_warmed()

    err_thread = threading.Thread(target=read_stderr)
    err_thread.start()
    pagemap_summary = None
    if args.dump_pagemap:
        if hot_event.wait(args.pagemap_timeout_s) and hot_table is not None:
            pagemap_summary = dump_hot_table_pagemap(
                hot_table["pid"], hot_table["base"], hot_table["bytes"], args
            )
        elif proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)
            err_thread.join(timeout=5)
            raise RuntimeError(
                f"timed out waiting for HOT_TABLE arm={arm} rep={rep}\n"
                f"stderr={''.join(stderr_lines)}"
            )

    assert proc.stdout is not None
    stdout = proc.stdout.read()
    proc.wait()
    err_thread.join(timeout=5)
    completed = subprocess.CompletedProcess(
        full_cmd, proc.returncode, stdout, "".join(stderr_lines)
    )
    return completed, (parse_perf_csv(perf_out) if args.perf_cpu_events else None), pagemap_summary


def run_one(args: argparse.Namespace, arm: str, rep: int, outf) -> None:
    write_schemata(VGRP)
    write_schemata(AGRP)

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    mbm_start = None
    t_agg_start = None
    procs = []
    if args.arrival_order == "aggressor-first":
        mbm_start = read_mbm(AGRP)
        t_agg_start = time.time()
        procs = launch_aggressors(args, arm, args.agg_duration_s, log_dir, rep)
        if procs:
            time.sleep(args.agg_settle_s)

    launch_lock = threading.Lock()

    def launch_after_warm() -> None:
        nonlocal mbm_start, t_agg_start, procs
        with launch_lock:
            if procs:
                return
            mbm_start = read_mbm(AGRP)
            t_agg_start = time.time()
            procs = launch_aggressors(args, arm, args.agg_duration_s, log_dir, rep)
            if procs and args.agg_settle_s > 0:
                time.sleep(args.agg_settle_s)

    if args.arrival_order == "victim-first" and arm == "quiescent":
        # Keep quiescent as the same victim command, but there is no aggressor arrival.
        launch_after_warm_cb = None
    elif args.arrival_order == "victim-first":
        launch_after_warm_cb = launch_after_warm
    else:
        launch_after_warm_cb = None

    if args.arrival_order == "victim-first" and arm != "quiescent" and args.victim_pre_measure_sleep_s <= args.agg_settle_s:
        raise RuntimeError("--victim-pre-measure-sleep-s must exceed --agg-settle-s for victim-first loaded arms")

    occ_samples: list[int] = []
    stop = threading.Event()
    sampler = threading.Thread(target=occ_sampler, args=(stop, occ_samples))
    sampler.start()
    t0 = time.time()
    victim_proc, perf_counts, pagemap_summary = run_victim_with_optional_perf(
        args, arm, rep, on_warmed=launch_after_warm_cb
    )
    t1 = time.time()
    stop.set()
    sampler.join()

    for proc, _, _ in procs:
        if proc.poll() is None:
            proc.terminate()
    agg_records = collect_aggressors(procs, 10.0) if procs else []
    t_agg_end = time.time()
    mbm_end = read_mbm(AGRP)
    bad_aggs = [r for r in agg_records if r.get("returncode") not in (0, -15) or r.get("parse_error")]
    if bad_aggs:
        raise RuntimeError(f"aggressor failed arm={arm} rep={rep}: {bad_aggs}")

    if victim_proc.returncode != 0:
        raise RuntimeError(
            f"victim failed arm={arm} rep={rep} rc={victim_proc.returncode}\n"
            f"stdout={victim_proc.stdout}\nstderr={victim_proc.stderr}"
        )
    victim_json = parse_json_line(victim_proc.stdout)
    agg_bw = []
    for r in agg_records:
        for key in ("avg_bw_gbps", "bw_gbps"):
            if isinstance(r.get(key), (int, float)):
                agg_bw.append(float(r[key]))
                break
    occ = {
        "n": max(0, len(occ_samples) - 1),
        "dropped_initial_sample": bool(occ_samples),
        "mean": (sum(occ_samples[1:]) / len(occ_samples[1:])) if len(occ_samples) > 1 else None,
        "min": min(occ_samples[1:]) if len(occ_samples) > 1 else None,
        "max": max(occ_samples[1:]) if len(occ_samples) > 1 else None,
    }
    rec = {
        "arm": arm,
        "rep": rep,
        "victim_mode": "morsel_no_stream",
        "wall_dur_s": t1 - t0,
        "arrival_order": args.arrival_order,
        "agg_settle_s": args.agg_settle_s,
        "victim_pre_measure_sleep_s": args.victim_pre_measure_sleep_s,
        "configured_fact_bytes": args.fact_bytes,
        "victim": victim_json,
        "actual_fact_bytes": victim_json.get("fact_bytes"),
        "metric_cycles_per_access": victim_json.get("active_cycles_per_access"),
        "perf_cpu": args.perf_cpu if args.perf_cpu_events else None,
        "perf_counts": perf_counts,
        "perf_cycles_per_ref_cycle": (
            perf_counts.get("cycles") / perf_counts["ref-cycles"]
            if perf_counts and perf_counts.get("cycles") is not None and perf_counts.get("ref-cycles")
            else None
        ),
        "hot_table_pagemap": pagemap_summary,
        "aggressor_records": agg_records,
        "agg_bw_self_gbps_sum": sum(agg_bw) if agg_bw else None,
        "agg_bw_self_gbps_mean_per_proc": (sum(agg_bw) / len(agg_bw)) if agg_bw else None,
        "agg_mbm_bw_gbps": ((mbm_end - mbm_start) / (t_agg_end - t_agg_start) / 1e9)
        if (
            mbm_start is not None
            and t_agg_start is not None
            and mbm_end is not None
            and t_agg_end > t_agg_start
        )
        else None,
        "victim_llc_occ_bytes": occ,
    }
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(
        f"{arm:13s} rep={rep:02d} cpa={rec['metric_cycles_per_access']:.2f} "
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
    ap.add_argument("--agg-duration-s", type=float, default=120.0)
    ap.add_argument("--agg-settle-s", type=float, default=2.0)
    ap.add_argument("--arrival-order", choices=("aggressor-first", "victim-first"), default="aggressor-first")
    ap.add_argument("--victim-pre-measure-sleep-s", type=float, default=0.0)
    ap.add_argument("--amd-per-thread-mb", type=int, default=64)
    ap.add_argument("--flush-distance-kb", type=int, default=256)
    ap.add_argument("--flush-per-thread-mb", type=int, default=64)
    ap.add_argument("--victim", default=str(DEFAULT_VICTIM))
    ap.add_argument("--amd-bin", default=str(DEFAULT_AMD_BIN))
    ap.add_argument("--out", default=str(DEFAULT_ROOT / "amd_hash_join_cross_process_n12.jsonl"))
    ap.add_argument("--log-dir", default=str(DEFAULT_ROOT / "logs"))
    ap.add_argument("--arms", default=",".join(ARM_ORDER))
    ap.add_argument("--perf-cpu-events", default="")
    ap.add_argument("--perf-cpu", type=int, default=int(VICTIM_CPU))
    ap.add_argument("--dump-pagemap", action="store_true")
    ap.add_argument("--pagemap-timeout-s", type=float, default=10.0)
    ap.add_argument("--page-size", type=int, default=4096)
    ap.add_argument("--llc-line-size", type=int, default=64)
    ap.add_argument("--llc-sets", type=int, default=16384)
    ap.add_argument("--keep-hugepages", action="store_true")
    args = ap.parse_args()

    if os.geteuid() != 0:
        raise SystemExit("run with sudo: resctrl and hugepage reservation require root")

    old_hugepages = hugepages_total()

    def handle_signal(signum, frame):
        cleanup(Path(args.amd_bin))
        if not args.keep_hugepages:
            restore_hugepages(old_hugepages)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    ensure_groups(Path(args.amd_bin))
    try:
        arms = [a.strip() for a in args.arms.split(",") if a.strip()]
        unknown = sorted(set(arms) - set(ARMS))
        if unknown:
            raise SystemExit(f"unknown arm(s): {', '.join(unknown)}")
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w") as outf:
            for rep in range(1, args.reps + 1):
                for arm in arms:
                    run_one(args, arm, rep, outf)
    finally:
        cleanup(Path(args.amd_bin))
        if not args.keep_hugepages:
            restore_hugepages(old_hugepages)
    print(f"DONE -> {args.out}")


if __name__ == "__main__":
    main()
