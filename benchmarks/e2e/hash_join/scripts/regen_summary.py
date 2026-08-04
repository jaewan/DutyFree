#!/usr/bin/env python3
"""Regenerate results/clos_split/summary.csv from raw/*.json with one consistent
schema. The two driver scripts (gate + panel) wrote incompatible column sets to
the same file incrementally; this rebuilds it from source of truth (raw JSON)
instead of trusting the incrementally-appended file.
"""
import csv
import glob
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clos_stats import summarize_metric  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[4]
RESULTS_DIR = REPO_ROOT / "results" / "clos_split"
RAW_DIR = RESULTS_DIR / "raw"
OUT_CSV = RESULTS_DIR / "summary.csv"

# Rename gate_A/gate_D (queue-depth=8, 8:8 ratio, first-pass untuned run) distinctly
# from the panel's tuned points, since they are genuinely different configurations,
# not duplicate measurements of the same one.
LABEL_RENAME = {
    "A": "gate_A_untuned_16c",
    "D": "gate_D_8x8_qd8_16c",
}

DESCRIPTIONS = {
    "gate_A_untuned_16c": "Config A: fused morsel, CAT off, 16 cores (first-pass gate)",
    "gate_D_8x8_qd8_16c": "Config D: split 8 scan/8 probe, queue-depth=8, CAT off, 16 cores (first-pass gate, superseded by tuned D_1_3)",
    "Q16": "Config Q: quiescent hot-table-only probe, 16 threads, 16 cores, H_quiescent",
    "A2_16": "Config A: fused morsel, CAT off, 16 cores (seq1 reference)",
    "A3_16": "Config A: fused morsel, CAT off, 16 cores (seq2 reference, paired with B16)",
    "D_1_3": "Config D: split 4 scan/12 probe (ratio 1:3), queue-depth=16, CAT off, 16 cores",
    "D_1_1": "Config D: split 8 scan/8 probe (ratio 1:1), queue-depth=16, CAT off, 16 cores",
    "D_3_1": "Config D: split 12 scan/4 probe (ratio 3:1), queue-depth=16, CAT off, 16 cores",
    "Dref": "Config D: split at best ratio (1:3), queue-depth=16, CAT off, 16 cores (seq2 reference, paired with C)",
    "B16": "Config B: fused morsel, CAT on (single CLOS, 4 of 20 ways), 16 cores",
    "C_1way": "Config C: split at best ratio (1:3), CAT on, scan CLOS=1 way / probe CLOS=19 ways, 16 cores",
    "C_2way": "Config C: split at best ratio (1:3), CAT on, scan CLOS=2 ways / probe CLOS=18 ways, 16 cores",
    "E16": "Config E: fused morsel, policy=PREFETCHNTA, CAT off, 16 cores",
    "A_1c": "Config A: fused morsel, CAT off, 1 core (seq3a reference)",
    "Q_1c": "Config Q: quiescent hot-table-only probe, 1 thread, 1 core, H_quiescent",
    "A2_1c": "Config A: fused morsel, CAT off, 1 core (seq3b reference, paired with B_1c)",
    "B_1c": "Config B: fused morsel, CAT on (single CLOS, 4 of 20 ways), 1 core",
}


def throughput_field(rec):
    if rec.get("mode") == "hot-probe":
        return rec.get("probe_mops_per_s")
    return rec.get("join_mtuples_per_s")


def main():
    by_label = {}
    for f in sorted(glob.glob(str(RAW_DIR / "*.json"))):
        d = json.load(open(f))
        label = d.get("label")
        if label is None:
            continue
        label = LABEL_RENAME.get(label, label)
        by_label.setdefault(label, []).append(d)

    rows = []
    for label, recs in sorted(by_label.items()):
        ok = [r for r in recs if r.get("status") == "ok" and r.get("returncode") == 0]
        if not ok:
            continue
        thr = [throughput_field(r) for r in ok if throughput_field(r) is not None]
        cyc = [r.get("active_cycles_per_access") for r in ok if r.get("active_cycles_per_access") is not None]
        migr = [r.get("perf", {}).get("cpu-migrations") for r in ok]
        migr = [m for m in migr if isinstance(m, (int, float))]
        ratio = []
        for r in ok:
            p = r.get("perf", {})
            c, rc = p.get("cycles"), p.get("ref-cycles")
            if isinstance(c, (int, float)) and isinstance(rc, (int, float)) and rc:
                ratio.append(c / rc)
        thr_s = summarize_metric(thr) if thr else {}
        cyc_s = summarize_metric(cyc) if cyc else {}
        row = {
            "label": label,
            "description": DESCRIPTIONS.get(label, ""),
            "n": len(ok),
            "mode": ok[0].get("mode"),
            "threads": ok[0].get("threads"),
            "scan_threads": ok[0].get("scan_threads"),
            "probe_threads": ok[0].get("probe_threads"),
            "queue_depth": ok[0].get("queue_depth"),
            "policy": ok[0].get("policy"),
            "throughput_mtuples_median": thr_s.get("median"),
            "throughput_mtuples_cov": thr_s.get("cov"),
            "throughput_mtuples_ci95_lo": thr_s.get("ci95_lo"),
            "throughput_mtuples_ci95_hi": thr_s.get("ci95_hi"),
            "active_cyc_per_access_median": cyc_s.get("median"),
            "active_cyc_per_access_cov": cyc_s.get("cov"),
            "active_cyc_per_access_ci95_lo": cyc_s.get("ci95_lo"),
            "active_cyc_per_access_ci95_hi": cyc_s.get("ci95_hi"),
            "cpu_migrations_median": statistics.median(migr) if migr else None,
            "cycles_over_refcycles_median": statistics.median(ratio) if ratio else None,
        }
        rows.append(row)

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print(f"wrote {len(rows)} rows to {OUT_CSV}")


if __name__ == "__main__":
    main()
