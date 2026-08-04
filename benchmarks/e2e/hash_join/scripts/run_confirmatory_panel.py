#!/usr/bin/env python3
"""Confirmatory panel following the A-vs-D gate (T_D/T_A = 0.476 at 16 cores).

Sequence 1 (16 cores, CAT off, fully randomized together, n=30 each):
    Q16, A2_16, D_1_3, D_1_1, D_3_1, E16
Sequence 2 (16 cores, CAT on/off toggled per single run, n=30 each):
    A3_16 vs B16              (fused, one restricted CLOS)
    Dref vs C_1way vs C_2way  (split at best-of-seq1 ratio; scan CLOS 1 or 2 ways)
Sequence 3 (1 core, smaller fact size for wall-clock, n=30 each):
    A_1c vs Q_1c   (no CAT)
    A2_1c vs B_1c  (CAT toggle)

All CAT profile switches use scripts/resctrl_clos.sh via passwordless sudo, and are
re-applied before every single run (not once per block), so config order can be fully
randomized even across CAT and non-CAT points.
"""
import json
import os
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clos_stats import summarize_metric  # noqa: E402

HASH_JOIN_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
BIN = HASH_JOIN_DIR / "build" / "cxl_join_bench"
RESCTRL_SH = HASH_JOIN_DIR / "scripts" / "resctrl_clos.sh"
RESULTS_DIR = REPO_ROOT / "results" / "clos_split"
RAW_DIR = RESULTS_DIR / "raw"
SUMMARY_CSV = RESULTS_DIR / "summary.csv"

CPU16 = "32-47"
FACT_16C = "1g"
HOT_BYTES = "177838489"
MORSEL = "1m"
N_REPS = int(os.environ.get("PANEL_N_REPS", "30"))
SEED_BASE = 900001

PERF_EVENTS = [
    "cycles", "ref-cycles", "instructions", "cpu-migrations",
    "LLC-loads", "LLC-load-misses",
    "mem_load_l3_miss_retired.local_dram", "mem_load_l3_miss_retired.remote_dram",
    "offcore_requests.l3_miss_demand_data_rd",
]


def sh(cmd, check=True):
    p = subprocess.run(cmd, text=True, capture_output=True)
    if check and p.returncode != 0:
        print(f"CMD FAILED: {cmd}\nstdout={p.stdout}\nstderr={p.stderr}", file=sys.stderr)
        raise SystemExit(1)
    return p


def cat_teardown():
    sh(["sudo", "bash", str(RESCTRL_SH), "teardown"])


def cat_setup(profile):
    if profile is None:
        cat_teardown()
        return
    kind = profile["kind"]
    if kind == "b":
        sh(["sudo", "bash", str(RESCTRL_SH), "setup_b", str(profile["ways"]), profile["cpus"]])
    elif kind == "c":
        sh(["sudo", "bash", str(RESCTRL_SH), "setup_c", str(profile["scan_ways"]),
            profile["scan_cpus"], profile["probe_cpus"]])
    else:
        raise ValueError(kind)


def parse_perf(text):
    out = {}
    import csv
    import io
    for row in csv.reader(io.StringIO(text)):
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


def run_one(label, args, idx, cat_profile):
    cat_setup(cat_profile)
    cmd = [str(BIN)] + args
    full = ["perf", "stat", "-x,", "-e", ",".join(PERF_EVENTS), "--"] + cmd
    t0 = time.time()
    proc = subprocess.run(full, cwd=str(HASH_JOIN_DIR), text=True, capture_output=True, timeout=180)
    elapsed_wall = time.time() - t0
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
        "label": label, "rep_index": idx, "returncode": proc.returncode,
        "elapsed_wall": elapsed_wall, "cmd": full, "stderr": proc.stderr.strip()[:1500],
        "perf": parse_perf(proc.stderr),
    })
    out_path = RAW_DIR / f"panel_{label}_{idx:02d}.json"
    out_path.write_text(json.dumps(rec, indent=2, sort_keys=True))
    return rec


def run_sequence(seq_name, label_specs, n_reps, seed):
    """label_specs: dict label -> {"args": [...], "cat": None|profile}"""
    sequence = []
    for label, spec in label_specs.items():
        sequence += [(label, spec)] * n_reps
    rng = random.Random(seed)
    rng.shuffle(sequence)
    counters = {label: 0 for label in label_specs}
    records = {label: [] for label in label_specs}
    for pos, (label, spec) in enumerate(sequence):
        counters[label] += 1
        idx = counters[label]
        print(f"[{seq_name} {pos+1}/{len(sequence)}] {label} rep {idx}/{n_reps}", file=sys.stderr)
        rec = run_one(label, spec["args"], idx, spec.get("cat"))
        if rec.get("returncode") != 0 or rec.get("status") != "ok":
            print(f"  WARN {label}#{idx}: rc={rec.get('returncode')} status={rec.get('status')} "
                  f"stderr={rec.get('stderr','')[:300]}", file=sys.stderr)
        records[label].append(rec)
    cat_teardown()
    return records


def morsel_args(fact_bytes, threads, cpu_list, policy="wb"):
    # No --result-hash here: it adds a non-uniform timing overhead (~12% on fused,
    # ~3% on split, measured directly) that would contaminate every ratio in this
    # panel. Correctness is validated once, separately, at small scale instead.
    return ["--mode", "morsel", "--policy", policy, "--fact-node", "2", "--hot-node", "0",
            "--fact-bytes", fact_bytes, "--hot-bytes", HOT_BYTES, "--cpu-list", cpu_list,
            "--morsel", MORSEL, "--warmups", "2", "--reps", "1", "--threads", str(threads)]


def split_args(fact_bytes, n_scan, n_probe, cpu_list, queue_depth=16):
    return ["--mode", "split", "--policy", "wb", "--fact-node", "2", "--hot-node", "0",
            "--fact-bytes", fact_bytes, "--hot-bytes", HOT_BYTES, "--cpu-list", cpu_list,
            "--morsel", MORSEL, "--warmups", "2", "--reps", "1",
            "--scan-threads", str(n_scan), "--probe-threads", str(n_probe),
            "--queue-depth", str(queue_depth)]


def hotprobe_args(fact_bytes, threads, cpu_list):
    return ["--mode", "hot-probe", "--policy", "wb", "--fact-bytes", fact_bytes,
            "--hot-bytes", HOT_BYTES, "--cpu-list", cpu_list, "--morsel", MORSEL,
            "--warmups", "2", "--reps", "1", "--threads", str(threads)]


def throughput_field(rec):
    if rec.get("mode") == "hot-probe":
        return rec.get("probe_mops_per_s")
    return rec.get("join_mtuples_per_s")


def cycles_field(rec):
    return rec.get("active_cycles_per_access")


def summarize_records(records):
    rows = {}
    for label, recs in records.items():
        ok = [r for r in recs if r.get("status") == "ok" and r.get("returncode") == 0]
        if not ok:
            print(f"NO SUCCESSFUL RUNS for {label}", file=sys.stderr)
            continue
        thr = [throughput_field(r) for r in ok if throughput_field(r) is not None]
        cyc = [cycles_field(r) for r in ok if cycles_field(r) is not None]
        migr = [r.get("perf", {}).get("cpu-migrations") for r in ok]
        migr = [m for m in migr if isinstance(m, (int, float))]
        row = {"label": label, "n": len(ok)}
        row.update({f"throughput_{k}": v for k, v in summarize_metric(thr).items()})
        row.update({f"active_cyc_{k}": v for k, v in summarize_metric(cyc).items()})
        row["cpu_migrations_median"] = statistics.median(migr) if migr else None
        rows[label] = row
    return rows


def append_summary(rows):
    write_header = not SUMMARY_CSV.exists()
    import csv
    all_rows = list(rows.values())
    if not all_rows:
        return
    with SUMMARY_CSV.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        if write_header:
            w.writeheader()
        for row in all_rows:
            w.writerow(row)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cat_teardown()  # clean slate

    # ---------------- Sequence 1: CAT-off family, 16 cores ----------------
    seq1_specs = {
        "Q16": {"args": hotprobe_args(FACT_16C, 16, CPU16), "cat": None},
        "A2_16": {"args": morsel_args(FACT_16C, 16, CPU16), "cat": None},
        "D_1_3": {"args": split_args(FACT_16C, 4, 12, CPU16), "cat": None},
        "D_1_1": {"args": split_args(FACT_16C, 8, 8, CPU16), "cat": None},
        "D_3_1": {"args": split_args(FACT_16C, 12, 4, CPU16), "cat": None},
        "E16": {"args": morsel_args(FACT_16C, 16, CPU16, policy="nta"), "cat": None},
    }
    seq1_records = run_sequence("seq1", seq1_specs, N_REPS, SEED_BASE + 1)
    seq1_rows = summarize_records(seq1_records)
    append_summary(seq1_rows)
    for label, row in seq1_rows.items():
        print(f"SEQ1 {label}: throughput_median={row['throughput_median']:.3f} "
              f"active_cyc_median={row['active_cyc_median']:.3f}", file=sys.stderr)

    d_ratios = {"D_1_3": (4, 12), "D_1_1": (8, 8), "D_3_1": (12, 4)}
    best_label = max(d_ratios, key=lambda lb: seq1_rows[lb]["throughput_median"])
    best_ns, best_np = d_ratios[best_label]
    print(f"BEST D RATIO: {best_label} (n_scan={best_ns}, n_probe={best_np})", file=sys.stderr)

    scan_cpus = f"32-{32 + best_ns - 1}"
    probe_cpus = f"{32 + best_ns}-47"

    # ---------------- Sequence 2: CAT toggle family, 16 cores ----------------
    seq2_specs = {
        "A3_16": {"args": morsel_args(FACT_16C, 16, CPU16), "cat": None},
        "B16": {"args": morsel_args(FACT_16C, 16, CPU16),
               "cat": {"kind": "b", "ways": 4, "cpus": CPU16}},
        "Dref": {"args": split_args(FACT_16C, best_ns, best_np, CPU16, queue_depth=16), "cat": None},
        "C_1way": {"args": split_args(FACT_16C, best_ns, best_np, CPU16, queue_depth=16),
                  "cat": {"kind": "c", "scan_ways": 1, "scan_cpus": scan_cpus, "probe_cpus": probe_cpus}},
        "C_2way": {"args": split_args(FACT_16C, best_ns, best_np, CPU16, queue_depth=16),
                  "cat": {"kind": "c", "scan_ways": 2, "scan_cpus": scan_cpus, "probe_cpus": probe_cpus}},
    }
    seq2_records = run_sequence("seq2", seq2_specs, N_REPS, SEED_BASE + 2)
    seq2_rows = summarize_records(seq2_records)
    append_summary(seq2_rows)
    for label, row in seq2_rows.items():
        print(f"SEQ2 {label}: throughput_median={row['throughput_median']:.3f} "
              f"active_cyc_median={row['active_cyc_median']:.3f}", file=sys.stderr)

    # ---------------- Sequence 3: 1-core family (smaller fact for wall-clock) ----------------
    FACT_1C = "256m"
    seq3a_specs = {
        "A_1c": {"args": morsel_args(FACT_1C, 1, "32"), "cat": None},
        "Q_1c": {"args": hotprobe_args(FACT_1C, 1, "32"), "cat": None},
    }
    seq3a_records = run_sequence("seq3a", seq3a_specs, N_REPS, SEED_BASE + 3)
    seq3a_rows = summarize_records(seq3a_records)
    append_summary(seq3a_rows)

    seq3b_specs = {
        "A2_1c": {"args": morsel_args(FACT_1C, 1, "32"), "cat": None},
        "B_1c": {"args": morsel_args(FACT_1C, 1, "32"),
                "cat": {"kind": "b", "ways": 4, "cpus": "32"}},
    }
    seq3b_records = run_sequence("seq3b", seq3b_specs, N_REPS, SEED_BASE + 4)
    seq3b_rows = summarize_records(seq3b_records)
    append_summary(seq3b_rows)

    all_rows = {}
    all_rows.update(seq1_rows)
    all_rows.update(seq2_rows)
    all_rows.update(seq3a_rows)
    all_rows.update(seq3b_rows)
    (RESULTS_DIR / "panel_summary.json").write_text(json.dumps(all_rows, indent=2, sort_keys=True))
    print("DONE. Full summary written to panel_summary.json", file=sys.stderr)


if __name__ == "__main__":
    main()
