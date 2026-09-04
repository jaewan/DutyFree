#!/usr/bin/env python3
"""DuckDB mmap-probe SE H2 kill-gate.

Pre-registration: DUCKDB_MMAP_SE_H2_PREREG_2026-09-02.md

Usage: analyze_duckdb_mmap_se.py <duckdb_mmap_se_h2.jsonl>
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from pathlib import Path

ARMS = ("qui", "wb", "h2")
SEEDS = 3
WANT_L3 = 7_864_320
WANT_TABLE = 4_194_240
WANT_PROBE = 8_388_608
WANT_N = 104856
WANT_P = 1_048_576
RATIO_MIN, RATIO_MAX = 0.530, 0.537
WB_TAX_FLOOR = 1.15
TPS_AGREE = 0.08
CONTENDED_LOADS = (100_000, 6_000_000)
QUIET_LOADS = (11_000_000, 12_100_000)


def mark(name, ok, detail):
    print(f"  {name:48s} {'PASS' if ok else 'FAIL'}  {detail}")
    return ok


def mean(g, k):
    v = [x[k] for x in g if x.get(k) is not None]
    return st.mean(v) if v else None


def rows_per_s(r):
    js = r.get("query_seconds")
    n = r.get("mmap_count")
    chrono = (n / js) if js and n else None
    derived = r.get("mmap_rows_per_s_from_cycles")
    if chrono is None:
        return derived
    if derived is None:
        return chrono
    if chrono == 0:
        return derived
    if abs(chrono - derived) / max(chrono, derived) > TPS_AGREE:
        return derived
    return chrono


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    path = Path(argv[1])
    if not path.exists():
        print("===== VERDICT =====\nFAIL: no archive; no STREAMING DuckDB claim licensed")
        return 1
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    ref = {}
    for r in rows:
        m = re.match(r"(?:.*_)?([a-z0-9]+)_s(\d+)$", r.get("run") or "")
        if not m:
            continue
        ref.setdefault(m.group(1), []).append(r)

    gates = []
    missing = [t for t in ARMS if len(ref.get(t, [])) != SEEDS]
    incomplete = [t for t in ARMS if t in ref and not all(x.get("completed") for x in ref[t])]
    gates.append(mark("F1 all arms present", not missing and not incomplete,
                      f"missing={missing} incomplete={incomplete}"))
    if not all(gates):
        print("===== VERDICT =====\nFAIL: incomplete; no STREAMING DuckDB claim licensed")
        return 1

    geo_ok = True
    geo_d = []
    for r in rows:
        if not r.get("completed"):
            continue
        l3 = r.get("l3_size_bytes")
        if l3 != WANT_L3:
            geo_ok = False
            geo_d.append(f"{r['run']} l3={l3}")
        tag = re.search(r"([a-z0-9]+)_s\d+$", r["run"])
        tag = tag.group(1) if tag else ""
        if tag == "qui":
            continue
        n = r.get("duckdb_n")
        p = r.get("duckdb_probe")
        tb = r.get("table_bytes")
        pb = r.get("probe_bytes")
        ratio = (tb / l3) if l3 and tb else None
        if n != WANT_N or p != WANT_P or tb != WANT_TABLE or pb != WANT_PROBE:
            geo_ok = False
            geo_d.append(f"{r['run']} n={n} p={p} tb={tb} pb={pb}")
        if ratio is None or not (RATIO_MIN <= ratio <= RATIO_MAX):
            geo_ok = False
            geo_d.append(f"{r['run']} table/LLC={ratio}")
        if r.get("duckdb_keys") != "mod":
            geo_ok = False
            geo_d.append(f"{r['run']} keys={r.get('duckdb_keys')}")
    gates.append(mark("G0 table/LLC ≈ 0.53 (104856 × 40 B / 7680 KiB)", geo_ok,
                      "; ".join(geo_d[:6]) or "n,P,bytes,l3"))

    complete_ok = True
    bypass_ok = True
    match_ok = True
    details = []
    counts = {}
    for r in rows:
        if not r.get("completed"):
            continue
        tag = re.search(r"([a-z0-9]+)_s\d+$", r["run"])
        tag = tag.group(1) if tag else ""
        loads = r.get("victim_loads") or 0
        byp = r.get("hnf_streaming_bypasses") or 0
        if tag == "qui":
            if not (QUIET_LOADS[0] <= loads <= QUIET_LOADS[1]):
                complete_ok = False
                details.append(f"{r['run']} qui loads={loads}")
            if byp != 0:
                bypass_ok = False
                details.append(f"{r['run']} qui bypasses={byp}")
            continue
        if not r.get("join_m5_exit") or not r.get("join_measure_end"):
            complete_ok = False
            details.append(f"{r['run']} missing JOIN markers")
        if not (r.get("mmap_count") or 0) > 0 or not (r.get("query_seconds") or 0) > 0:
            complete_ok = False
            details.append(f"{r['run']} no mmap_count/query_seconds")
        if not (CONTENDED_LOADS[0] <= loads <= CONTENDED_LOADS[1]):
            complete_ok = False
            details.append(f"{r['run']} loads={loads}")
        if tag == "h2":
            if byp <= 0:
                bypass_ok = False
                details.append(f"{r['run']} h2 bypasses={byp}")
        elif byp != 0:
            bypass_ok = False
            details.append(f"{r['run']} bypasses={byp} want 0")
        counts.setdefault(tag, []).append((r.get("mmap_count"), r.get("mmap_sum")))
    wb_cs = counts.get("wb") or []
    h2_cs = counts.get("h2") or []
    if wb_cs and h2_cs:
        if {x[0] for x in wb_cs} != {x[0] for x in h2_cs} or {x[1] for x in wb_cs} != {x[1] for x in h2_cs}:
            match_ok = False
            details.append(f"mmap_count/sum wb={wb_cs} h2={h2_cs}")
    gates.append(mark("P_complete tenant ended contended windows", complete_ok,
                      "; ".join(details[:6]) or "JOIN_M5_EXIT + JSON + victim_loads band"))
    gates.append(mark("P_match wb and h2 same join", match_ok,
                      "; ".join(d for d in details if "mmap_count" in d)[:200] or "count/sum"))
    p1 = mark("P1 H2 engagement (h2 bypasses>0, others 0)", bypass_ok,
              "; ".join(d for d in details if "bypass" in d)[:200] or "h2>0 others=0")
    gates.append(p1)

    q = mean(ref["qui"], "cyc_per_load")
    wb = mean(ref["wb"], "cyc_per_load")
    h2_c = mean(ref["h2"], "cyc_per_load")
    tax = (wb / q) if q else None
    p2_ok = tax is not None and tax >= WB_TAX_FLOOR
    gates.append(mark(f"P2 wb tax ≥ {WB_TAX_FLOOR:.2f}× qui", p2_ok,
                      f"qui={q} wb={wb} tax={tax}"))

    prot = ((wb - h2_c) / (wb - q)) if q and wb and h2_c is not None and wb != q else None
    p3_ok = prot is not None and prot > 0
    p3_neg = p1 and p2_ok and (prot is not None) and prot <= 0
    gates.append(mark("P3 protection R>0 (directional)", p3_ok,
                      f"R={prot}"))

    wb_s = mean(ref["wb"], "query_seconds")
    h2_s = mean(ref["h2"], "query_seconds")
    p4_ok = wb_s is not None and h2_s is not None and h2_s <= wb_s
    gates.append(mark("P4 tenant h2 query_seconds ≤ wb (unprotected)", p4_ok,
                      f"wb={wb_s} h2={h2_s}"))

    print("===== DUCKDB MMAP SE H2 =====")
    print(f"  quiet={q}  wb={wb} (tax {tax})  h2={h2_c}  R={prot}")
    print(f"  tenant s wb={wb_s} h2={h2_s}")
    print("===== VERDICT =====")
    form = complete_ok and match_ok and geo_ok
    if not p1:
        print("VOID: P1 fail — m5op path did not engage; not a STREAMING negative")
        return 1
    if form and not p2_ok:
        print("VOID: P2 fail — no contention; not a STREAMING negative")
        return 1
    if form and p2_ok and p3_neg:
        print("REPORTABLE NEGATIVE: P1 held, R<=0 — engine working set is not the probe")
        return 1
    if not all(gates):
        print("FAIL: a registered gate missed; no STREAMING DuckDB claim licensed")
        return 1
    print("PASS: H2 engaged on the DuckDB mmap probe (SE m5op). Not FS, not E5.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
