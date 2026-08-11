#!/usr/bin/env python3
"""Summarize valid GAPBS sizing-gate JSONL records without hiding failures."""

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def summary(values):
    mean = statistics.mean(values)
    return {
        "n": len(values), "median_seconds": statistics.median(values),
        "mean_seconds": mean,
        "cov_percent": (statistics.stdev(values) / mean * 100) if len(values) > 1 and mean else 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    groups, invalid = defaultdict(list), []
    for path in args.inputs:
        for line_no, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
            rec = json.loads(line)
            times = rec.get("trial_seconds_measured", [])
            if rec.get("returncode") != 0 or len(times) != 3:
                invalid.append({"path": str(path), "line": line_no, "host": rec.get("host"),
                                "app": rec.get("app"), "scale": rec.get("scale"),
                                "returncode": rec.get("returncode"), "times": times})
                continue
            groups[(rec["host"], rec["app"], rec["scale"])].extend(times)
    rows = []
    for (host, app, scale), times in sorted(groups.items()):
        row = {"host": host, "app": app, "scale": scale, **summary(times)}
        rows.append(row)
    payload = {"valid_rows": rows, "invalid_records_retained": invalid}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii")
    for row in rows:
        print(f"{row['host']:6} {row['app']:3} g{row['scale']:2}: "
              f"median={row['median_seconds']:.6f}s CoV={row['cov_percent']:.3f}% n={row['n']}")
    if invalid:
        print(f"retained invalid records: {len(invalid)}")


if __name__ == "__main__":
    main()
