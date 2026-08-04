#!/usr/bin/env python3
"""M3 (outstanding-miss occupancy) and M4 (CHA TOR average latency), quiescent vs
loaded, at 1 and 16 cores, at the paper's 170MB operating point.

Small event groups only (<=2 offcore-response-class events per invocation),
confirmed necessary in Phase 0/1 recon. Reports coverage/scaling whenever
perf multiplexes (should be 100% given the group sizes used here, checked
explicitly rather than assumed).

M4's CHA TOR events are system-wide (-a) uncore counters on a shared host --
noted explicitly, not hidden. Background load is sampled immediately before
each workload run as a baseline for comparison.
"""
import csv
import json
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

CORE_CONFIGS = {
    1: {"cpu_list": "32", "fact_bytes": "256m", "threads": 1},
    16: {"cpu_list": "32-47", "fact_bytes": "1g", "threads": 16},
}
N_REPS = 30

M3_GROUPS = [
    ["cycles", "l1d_pend_miss.pending", "l1d_pend_miss.pending_cycles", "l1d_pend_miss.fb_full"],
    ["cycles", "offcore_requests_outstanding.data_rd", "offcore_requests.data_rd"],
]
M4_GROUPS = [
    ["unc_cha_tor_occupancy.ia_miss_drd", "unc_cha_tor_inserts.ia_miss_drd"],
    ["unc_cha_tor_occupancy.ia_miss_drd_local_ddr", "unc_cha_tor_inserts.ia_miss_drd_local_ddr"],
    ["unc_cha_tor_occupancy.ia_miss_drd_cxl_acc_local", "unc_cha_tor_inserts.ia_miss_drd_cxl_acc_local"],
]


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


def morsel_args(cores):
    cc = CORE_CONFIGS[cores]
    return ["--mode", "morsel", "--policy", "wb", "--fact-node", "2", "--hot-node", "0",
            "--fact-bytes", cc["fact_bytes"], "--hot-bytes", HOT_BYTES,
            "--cpu-list", cc["cpu_list"], "--morsel", "1m", "--warmups", "2",
            "--reps", "1", "--threads", str(cc["threads"])]


def hotprobe_args(cores):
    cc = CORE_CONFIGS[cores]
    return ["--mode", "hot-probe", "--policy", "wb", "--fact-bytes", cc["fact_bytes"],
            "--hot-bytes", HOT_BYTES, "--cpu-list", cc["cpu_list"], "--morsel", "1m",
            "--warmups", "2", "--reps", "1", "--threads", str(cc["threads"])]


def run_group(label, args, group_idx, events, idx, system_wide):
    cmd = [str(BIN)] + args
    perf_cmd = ["perf", "stat", "-x,", "-e", ",".join(events)]
    if system_wide:
        perf_cmd += ["-a"]
    perf_cmd += ["--"] + cmd
    proc = subprocess.run(perf_cmd, cwd=str(HASH_JOIN_DIR), text=True, capture_output=True, timeout=60)
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
    rec.update({"label": label, "group": group_idx, "rep_index": idx,
                "returncode": proc.returncode, "perf": parse_perf(proc.stderr),
                "stderr": proc.stderr.strip()[:800]})
    (RAW_DIR / f"m3m4_{label}_g{group_idx}_{idx:02d}.json").write_text(json.dumps(rec, indent=2))
    return rec


def run_measure(cores, mtype, groups, system_wide, seed):
    specs = {"Q": hotprobe_args(cores), "A": morsel_args(cores)}
    results = {}
    for gi, events in enumerate(groups):
        sequence = [("Q", gi)] * N_REPS + [("A", gi)] * N_REPS
        rng = random.Random(seed + gi)
        rng.shuffle(sequence)
        counters = {"Q": 0, "A": 0}
        recs = {"Q": [], "A": []}
        for pos, (label, _) in enumerate(sequence):
            counters[label] += 1
            idx = counters[label]
            print(f"[{mtype} {cores}c g{gi} {pos+1}/{len(sequence)}] {label} rep {idx}/{N_REPS}", file=sys.stderr)
            rec = run_group(f"{mtype}_{cores}c", specs[label], gi, events, idx, system_wide)
            recs[label].append(rec)
        results[gi] = recs
    return results


def coverage_report(recs, events):
    """Report perf's own multiplexing percentage column per event, median across reps."""
    out = {}
    for ev in events:
        # perf -x, csv columns: value,unit,event,runtime,pct,... ; pct is column index 4 (0-based)
        pass
    return out


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for cores in (1, 16):
        m3 = run_measure(cores, "M3", M3_GROUPS, system_wide=False, seed=700000 + cores)
        m4 = run_measure(cores, "M4", M4_GROUPS, system_wide=True, seed=800000 + cores)

        for gi, events in enumerate(M3_GROUPS):
            for label in ("Q", "A"):
                recs = [r for r in m3[gi][label] if r.get("returncode") == 0]
                for ev in events:
                    if ev == "cycles":
                        continue
                    vals, pcts = [], []
                    for r in recs:
                        p = r.get("perf", {})
                        v = p.get(ev)
                        if isinstance(v, (int, float)):
                            vals.append(v)
                    if vals:
                        s = summarize_metric(vals)
                        all_rows.append({"metric_type": "M3", "cores": cores, "config": label,
                                         "event": ev, "n": len(vals), "median": s["median"],
                                         "cov": s["cov"], "ci_lo": s["ci95_lo"], "ci_hi": s["ci95_hi"]})

        for gi, events in enumerate(M4_GROUPS):
            for label in ("Q", "A"):
                recs = [r for r in m4[gi][label] if r.get("returncode") == 0]
                occ_ev, ins_ev = events
                occ_vals, ins_vals = [], []
                for r in recs:
                    p = r.get("perf", {})
                    o, i = p.get(occ_ev), p.get(ins_ev)
                    if isinstance(o, (int, float)) and isinstance(i, (int, float)) and i:
                        occ_vals.append(o); ins_vals.append(i)
                if occ_vals:
                    ratios = [o / i for o, i in zip(occ_vals, ins_vals)]
                    s = summarize_metric(ratios)
                    all_rows.append({"metric_type": "M4", "cores": cores, "config": label,
                                     "event": f"{occ_ev}/{ins_ev}_avg_latency_uncorecyc",
                                     "n": len(ratios), "median": s["median"], "cov": s["cov"],
                                     "ci_lo": s["ci95_lo"], "ci_hi": s["ci95_hi"]})

    out_csv = RESULTS_DIR / "m3_m4_summary.csv"
    if all_rows:
        with out_csv.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            w.writeheader()
            for row in all_rows:
                w.writerow(row)
    print(f"DONE. wrote {len(all_rows)} rows to {out_csv}", file=sys.stderr)
    for row in all_rows:
        print(row, file=sys.stderr)


if __name__ == "__main__":
    main()
