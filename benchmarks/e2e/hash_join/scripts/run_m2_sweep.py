#!/usr/bin/env python3
"""M2: hot-set size sweep across the L1/L2/LLC boundary, Q vs A, 1 and 16 cores.

No PEBS (decision metrics stay PEBS-free per the pre-registered constraint).
Minimal perf-stat wrap (cycles, ref-cycles, cpu-migrations only) for frequency/
pinning corroboration, avoiding offcore-response events entirely here since
M2 does not need them and the multiplexing risk is a distraction for this sweep.
"""
import csv
import json
import os
import random
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clos_stats import summarize_metric  # noqa: E402

HASH_JOIN_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
BIN = HASH_JOIN_DIR / "build" / "cxl_join_bench"
RESULTS_DIR = REPO_ROOT / "results" / "mechanism_decomp"
RAW_DIR = RESULTS_DIR / "raw"
HOT_BYTES = "177838489"

# F9 (W4.3 provenance ledger, 2026-08-23): this request is 169.6 MiB, but
# cxl_join_bench.cpp:369 `table_capacity` rounds the entry count up to a power
# of two and `build_table` instantiates it in full, so the RESIDENT hot table
# is 2^24 entries * 16 B = 256 MiB -- 80.0% of the 8592+'s 320 MiB LLC, not the
# 53% every document claimed. Ratio 1.5094. No measured number changes; the
# geometry attached to them does.
#
# The "170M" key below is deliberately NOT renamed. It is the record
# identifier baked into 1650 committed raw records under
# results/mechanism_decomp/raw/ and results/clos_split/raw/; renaming it would
# silently orphan the corpus. Read it as a request label, not a size.

SIZES = {
    "256K": "256k", "512K": "512k", "1M": "1m", "2M": "2m",
    "4M": "4m", "16M": "16m", "64M": "64m", "170M": HOT_BYTES,  # resident: 256 MiB
}

CORE_CONFIGS = {
    1: {"cpu_list": "32", "fact_bytes": "256m", "threads": 1},
    16: {"cpu_list": "32-47", "fact_bytes": "1g", "threads": 16},
}

N_REPS = int(os.environ.get("M2_N_REPS", "30"))
PERF_EVENTS = ["cycles", "ref-cycles", "cpu-migrations"]


def parse_perf(text):
    import csv as csv_, io
    out = {}
    for row in csv_.reader(io.StringIO(text)):
        if len(row) < 3:
            continue
        val = row[0].strip(); ev = row[2].strip()
        if not ev or val in ("<not supported>", "<not counted>"):
            out[ev] = val; continue
        try:
            out[ev] = int(val.replace(",", ""))
        except ValueError:
            try:
                out[ev] = float(val)
            except ValueError:
                out[ev] = val
    return out


def morsel_args(cores, size_bytes):
    cc = CORE_CONFIGS[cores]
    return ["--mode", "morsel", "--policy", "wb", "--fact-node", "2", "--hot-node", "0",
            "--fact-bytes", cc["fact_bytes"], "--hot-bytes", size_bytes,
            "--cpu-list", cc["cpu_list"], "--morsel", "1m", "--warmups", "2",
            "--reps", "1", "--threads", str(cc["threads"])]


def hotprobe_args(cores, size_bytes):
    cc = CORE_CONFIGS[cores]
    return ["--mode", "hot-probe", "--policy", "wb", "--fact-bytes", cc["fact_bytes"],
            "--hot-bytes", size_bytes, "--cpu-list", cc["cpu_list"], "--morsel", "1m",
            "--warmups", "2", "--reps", "1", "--threads", str(cc["threads"])]


def run_one(label, args, idx):
    cmd = [str(BIN)] + args
    full = ["perf", "stat", "-x,", "-e", ",".join(PERF_EVENTS), "--"] + cmd
    proc = subprocess.run(full, cwd=str(HASH_JOIN_DIR), text=True, capture_output=True, timeout=120)
    lines = proc.stdout.strip().splitlines()
    rec = None
    for line in reversed(lines):
        try:
            rec = json.loads(line)
            break
        except Exception:
            pass
    if rec is None:
        rec = {"raw_stdout": proc.stdout, "status": "parse_failed"}
    rec.update({"label": label, "rep_index": idx, "returncode": proc.returncode,
                "cmd": full, "stderr": proc.stderr.strip()[:1000], "perf": parse_perf(proc.stderr)})
    (RAW_DIR / f"m2_{label}_{idx:02d}.json").write_text(json.dumps(rec, indent=2))
    return rec


def throughput_field(rec):
    if rec.get("mode") == "hot-probe":
        return rec.get("probe_mops_per_s")
    return rec.get("join_mtuples_per_s")


def run_core_count(cores, seed):
    specs = {}
    for size_label, size_bytes in SIZES.items():
        specs[f"Q_{size_label}_{cores}c"] = hotprobe_args(cores, size_bytes)
        specs[f"A_{size_label}_{cores}c"] = morsel_args(cores, size_bytes)

    sequence = []
    for label, args in specs.items():
        sequence += [(label, args)] * N_REPS
    rng = random.Random(seed)
    rng.shuffle(sequence)
    counters = {l: 0 for l in specs}
    records = {l: [] for l in specs}
    for pos, (label, args) in enumerate(sequence):
        counters[label] += 1
        idx = counters[label]
        print(f"[{cores}c {pos+1}/{len(sequence)}] {label} rep {idx}/{N_REPS}", file=sys.stderr)
        rec = run_one(label, args, idx)
        if rec.get("returncode") != 0 or rec.get("status") != "ok":
            print(f"  WARN {label}#{idx}: rc={rec.get('returncode')} status={rec.get('status')}", file=sys.stderr)
        records[label].append(rec)
    return records


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    all_records = {}
    all_records.update(run_core_count(1, seed=555001))
    all_records.update(run_core_count(16, seed=555016))

    rows = []
    for cores in (1, 16):
        for size_label in SIZES:
            q = [r for r in all_records[f"Q_{size_label}_{cores}c"] if r.get("status") == "ok"]
            a = [r for r in all_records[f"A_{size_label}_{cores}c"] if r.get("status") == "ok"]
            hq = [r["active_cycles_per_access"] for r in q]
            ha = [r["active_cycles_per_access"] for r in a]
            tq = summarize_metric(hq)
            ta = summarize_metric(ha)
            delta_total = ta["median"] - tq["median"]
            row = {
                "cores": cores, "size_label": size_label, "size_bytes": SIZES[size_label],
                "n_Q": len(hq), "n_A": len(ha),
                "H_Q_median": tq["median"], "H_Q_cov": tq["cov"],
                "H_Q_ci_lo": tq["ci95_lo"], "H_Q_ci_hi": tq["ci95_hi"],
                "H_A_median": ta["median"], "H_A_cov": ta["cov"],
                "H_A_ci_lo": ta["ci95_lo"], "H_A_ci_hi": ta["ci95_hi"],
                "delta_total_abs_cycles": delta_total,
                "ratio_A_over_Q": ta["median"] / tq["median"] if tq["median"] else None,
            }
            rows.append(row)
            print(f"{cores}c {size_label}: H_Q={tq['median']:.3f} H_A={ta['median']:.3f} "
                  f"delta={delta_total:.3f} ratio={row['ratio_A_over_Q']:.4f}", file=sys.stderr)

    out_csv = RESULTS_DIR / "m2_summary.csv"
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"DONE. wrote {len(rows)} rows to {out_csv}", file=sys.stderr)


if __name__ == "__main__":
    main()
