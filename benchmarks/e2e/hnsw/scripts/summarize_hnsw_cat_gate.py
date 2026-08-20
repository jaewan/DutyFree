#!/usr/bin/env python3
"""Apply the pre-registered decision rule to the HNSW CAT gate.

Rule, unchanged from the GAPBS gate: pass requires a minimum-way median at
least 2x the full-mask median with CoV at or below 5% in both. HNSW has one
operating point rather than a scale ladder, so there is nothing to select
between -- each host either passes or does not.
"""
import json, statistics
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "artifacts"
RATIO_MIN, COV_MAX = 2.0, 0.05

out = {}
for path in sorted(ART.glob("hnsw_cat_gate_*.jsonl")):
    host = path.stem.replace("hnsw_cat_gate_", "")
    pool, meta, invalid = {}, {}, []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if not r.get("valid"):
            invalid.append((r["mask_label"], r["invocation"]))
            continue
        e = pool.setdefault(r["mask_label"], [])
        e += r["trial_seconds_measured"]
        meta[r["mask_label"]] = r["effective_bytes"]
        meta["index_sha256"] = r["index_sha256"]
        meta["hnswlib_commit"] = r["hnswlib_commit"]
        meta["freeze_state"] = r["freeze_state"]
    if "full" not in pool or "min" not in pool:
        print(f"{host}: incomplete ({sorted(pool)})")
        continue
    f, m = pool["full"], pool["min"]
    fmed, mmed = statistics.median(f), statistics.median(m)
    fcov = statistics.stdev(f) / statistics.mean(f)
    mcov = statistics.stdev(m) / statistics.mean(m)
    ratio = mmed / fmed
    ok = ratio >= RATIO_MIN and fcov <= COV_MAX and mcov <= COV_MAX
    out[host] = {"full_mib": meta["full"] >> 20, "min_mib": meta["min"] >> 20,
                 "full_median_s": round(fmed, 6), "full_cov": round(fcov, 5),
                 "min_median_s": round(mmed, 6), "min_cov": round(mcov, 5),
                 "ratio": round(ratio, 4), "n_full": len(f), "n_min": len(m),
                 "passes": ok, "index_sha256": meta["index_sha256"],
                 "hnswlib_commit": meta["hnswlib_commit"],
                 "freeze_state": meta["freeze_state"], "invalid_records": invalid,
                 "rule": {"ratio_min": RATIO_MIN, "cov_max": COV_MAX}}
    print(f"{host:8s} full {meta['full']>>20:3d} MiB {fmed:9.6f}s CoV {fcov*100:5.3f}%   "
          f"min {meta['min']>>20:3d} MiB {mmed:9.6f}s CoV {mcov*100:5.3f}%   "
          f"ratio {ratio:6.3f}  {'PASS' if ok else 'fail'}  "
          f"index {meta['index_sha256'][:12]}")
    if invalid:
        print(f"         invalid records retained: {invalid}")

if out:
    shas = {v["index_sha256"] for v in out.values()}
    print(f"\nindex identical across hosts: {len(shas) == 1} ({len(shas)} distinct digest(s))")
    (ART / "hnsw_cat_gate_summary.json").write_text(
        json.dumps(out, indent=2, sort_keys=True) + "\n")
