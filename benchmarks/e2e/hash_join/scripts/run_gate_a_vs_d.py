#!/usr/bin/env python3
"""Decisive A-vs-D gate at 16 cores, approved before the full CLOS-split sweep.

Config A: fused morsel (scan+probe per thread), CAT off.
Config D: split scan/probe threads via queue, CAT off (isolates the cost of
          splitting itself, with no CAT involved).

Single rep per process invocation (--reps 1), 30 reps each, order randomized
across A/D so drift cannot masquerade as a config effect. Every run is written
raw to results/clos_split/raw/; a summary with median/CoV/95% CI is appended
to results/clos_split/summary.csv.
"""
import csv
import json
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

HASH_JOIN_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
BIN = HASH_JOIN_DIR / "build" / "cxl_join_bench"
RESULTS_DIR = REPO_ROOT / "results" / "clos_split"
RAW_DIR = RESULTS_DIR / "raw"
SUMMARY_CSV = RESULTS_DIR / "summary.csv"

CPU_LIST = "32-47"
FACT_BYTES = "1g"
HOT_BYTES = "177838489"
MORSEL = "1m"
THREADS = 16
N_REPS = 30
SEED = 20260729

PERF_EVENTS = [
    "cycles",
    "ref-cycles",
    "instructions",
    "cpu-migrations",
    "LLC-loads",
    "LLC-load-misses",
    "mem_load_l3_miss_retired.local_dram",
    "mem_load_l3_miss_retired.remote_dram",
    "offcore_requests.l3_miss_demand_data_rd",
]

COMMON = [
    "--policy", "wb",
    "--fact-node", "2", "--hot-node", "0",
    "--fact-bytes", FACT_BYTES, "--hot-bytes", HOT_BYTES,
    "--cpu-list", CPU_LIST, "--morsel", MORSEL,
    "--warmups", "2", "--reps", "1",
]


def parse_perf(text):
    out = {}
    for row in csv.reader(text.splitlines()):
        if len(row) < 3:
            continue
        val = row[0].strip()
        event = row[2].strip()
        if not event or val in ("<not supported>", "<not counted>"):
            out[event] = val
            continue
        try:
            out[event] = int(val.replace(",", ""))
        except ValueError:
            try:
                out[event] = float(val)
            except ValueError:
                out[event] = val
    return out


def freq_snapshot():
    freqs = {}
    for cpu in (32, 39, 47):
        p = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_cur_freq")
        if p.exists():
            freqs[cpu] = int(p.read_text().strip())
    return freqs


def run_one(label, cfg, args, idx, out_path):
    cmd = [str(BIN)] + args
    full = ["perf", "stat", "-x,", "-e", ",".join(PERF_EVENTS), "--"] + cmd
    freq_before = freq_snapshot()
    t0 = time.time()
    proc = subprocess.run(full, cwd=str(HASH_JOIN_DIR), text=True,
                          capture_output=True, timeout=120)
    elapsed_wall = time.time() - t0
    freq_after = freq_snapshot()
    stdout_lines = proc.stdout.strip().splitlines()
    rec = None
    for line in reversed(stdout_lines):
        try:
            rec = json.loads(line)
            break
        except Exception:
            pass
    if rec is None:
        rec = {"raw_stdout": proc.stdout, "status": "parse_failed"}
    rec.update({
        "label": label,
        "rep_index": idx,
        "returncode": proc.returncode,
        "elapsed_wall": elapsed_wall,
        "cmd": full,
        "stderr": proc.stderr.strip()[:2000],
        "perf": parse_perf(proc.stderr),
        "freq_before_khz": freq_before,
        "freq_after_khz": freq_after,
    })
    out_path.write_text(json.dumps(rec, indent=2, sort_keys=True))
    return rec


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not BIN.exists():
        print(f"binary not found: {BIN}", file=sys.stderr)
        sys.exit(1)

    a_args = COMMON + ["--mode", "morsel", "--threads", str(THREADS)]
    d_args = COMMON + ["--mode", "split", "--scan-threads", "8", "--probe-threads", "8",
                       "--queue-depth", "8"]

    sequence = [("A", a_args)] * N_REPS + [("D", d_args)] * N_REPS
    rng = random.Random(SEED)
    rng.shuffle(sequence)

    counters = {"A": 0, "D": 0}
    records = {"A": [], "D": []}
    for pos, (label, args) in enumerate(sequence):
        counters[label] += 1
        idx = counters[label]
        out_path = RAW_DIR / f"gate_{label}_{idx:02d}.json"
        print(f"[{pos+1}/{len(sequence)}] running {label} rep {idx}/{N_REPS}...", file=sys.stderr)
        rec = run_one(label, label, args, idx, out_path)
        if rec.get("returncode") != 0:
            print(f"  FAILED rc={rec.get('returncode')} stderr={rec.get('stderr','')[:300]}",
                  file=sys.stderr)
        records[label].append(rec)

    summarize(records)


def ci95(vals):
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    mean = statistics.mean(vals)
    sd = statistics.stdev(vals)
    half = 1.96 * sd / (len(vals) ** 0.5)
    return (mean - half, mean + half)


def cov(vals):
    if len(vals) < 2:
        return float("nan")
    mean = statistics.mean(vals)
    if mean == 0:
        return float("nan")
    return statistics.stdev(vals) / mean


def summarize(records):
    rows = []
    for label, recs in records.items():
        ok = [r for r in recs if r.get("status") == "ok" and r.get("returncode") == 0]
        if not ok:
            print(f"NO SUCCESSFUL RUNS for {label}", file=sys.stderr)
            continue
        thr = [r["join_mtuples_per_s"] for r in ok]
        cyc = [r["active_cycles_per_access"] for r in ok]
        migr = [r.get("perf", {}).get("cpu-migrations", None) for r in ok]
        migr = [m for m in migr if isinstance(m, (int, float))]
        cyc_ratio = []
        for r in ok:
            p = r.get("perf", {})
            c = p.get("cycles")
            rc = p.get("ref-cycles")
            if isinstance(c, (int, float)) and isinstance(rc, (int, float)) and rc:
                cyc_ratio.append(c / rc)
        row = {
            "label": label,
            "n": len(ok),
            "throughput_mtuples_median": statistics.median(thr),
            "throughput_mtuples_cov": cov(thr),
            "throughput_mtuples_ci95_lo": ci95(thr)[0],
            "throughput_mtuples_ci95_hi": ci95(thr)[1],
            "active_cyc_per_access_median": statistics.median(cyc),
            "active_cyc_per_access_cov": cov(cyc),
            "active_cyc_per_access_ci95_lo": ci95(cyc)[0],
            "active_cyc_per_access_ci95_hi": ci95(cyc)[1],
            "cpu_migrations_total": sum(migr) if migr else None,
            "cycles_over_refcycles_median": statistics.median(cyc_ratio) if cyc_ratio else None,
        }
        rows.append(row)
        print(json.dumps(row, indent=2))

    write_header = not SUMMARY_CSV.exists()
    with SUMMARY_CSV.open("a", newline="") as f:
        if not rows:
            return
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if write_header:
            w.writeheader()
        for row in rows:
            w.writerow(row)

    a_row = next((r for r in rows if r["label"] == "A"), None)
    d_row = next((r for r in rows if r["label"] == "D"), None)
    if a_row and d_row:
        ratio = d_row["throughput_mtuples_median"] / a_row["throughput_mtuples_median"]
        print(f"\nTHROUGHPUT RATIO T_D/T_A = {ratio:.4f}")
        print(f"A active cyc/access median = {a_row['active_cyc_per_access_median']:.3f}")
        print(f"D active cyc/access median (probe-side) = {d_row['active_cyc_per_access_median']:.3f}")


if __name__ == "__main__":
    main()
