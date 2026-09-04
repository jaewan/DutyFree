#!/usr/bin/env python3
"""Fail-closed analyzer for DuckDB tenant CAT.

Thresholds are the pre-registered ones in
DUCKDB_TENANT_CAT_PREREG_2026-09-01.md, held as module constants (imported
from duckdb_tenant_cat/tenant_gates.py) so that changing one after seeing data is
visible in git.

Refuses to certify on incomplete data or on K1/K2 void.  K3 fail is a
valid null, not a void, and does not retract the named-app claim.
"""
from __future__ import annotations

import argparse
import collections
import os
import statistics as st
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "duckdb_tenant_cat"))
from dutyfree import stats  # noqa: E402
from tenant_gates import (  # noqa: E402
    CAMPAIGN, CAT_WAYS, JOINUNIQ_AGREE, K2_SLOWDOWN_MIN, K3_COST_MIN,
    MIN_REPS, PREREG, S1_TAX_MIN, WANT_CHAIN, WANT_N, WANT_PROBE, WANT_R_BYTES,
    clos_check, geom_check, host_check, identity_check, live_check, mask_check,
    mask_held_check, pid_check, query_cost, version_check,
)

FULL_ARMS = ("qui", "wb", "wb_joinuniq") + tuple(f"cat{w:02d}" for w in CAT_WAYS)


def median(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return st.median(xs)


def protection(v_arm, v_wb, v_qui):
    if None in (v_arm, v_wb, v_qui):
        return None
    denom = v_wb - v_qui
    if denom <= 0:
        return None
    return 100.0 * (v_wb - v_arm) / denom


def group(rows):
    g = collections.defaultdict(list)
    for r in rows:
        g[r["arm"]].append(r)
    return g


def record_problems(rows):
    probs = []
    ref_c8 = None
    ref_ju = None
    wb = [r for r in rows if r.get("arm") == "wb"]
    if wb:
        ref_c8 = median([r.get("matches") for r in wb])
        if ref_c8 is not None:
            ref_c8 = int(ref_c8)
    ju = [r for r in rows if r.get("arm") == "wb_joinuniq"]
    if ju:
        ref_ju = median([r.get("matches") for r in ju])
        if ref_ju is not None:
            ref_ju = int(ref_ju)
    for r in rows:
        arm, rep = r.get("arm"), r.get("rep")
        tag = f"{arm} rep{rep}"
        if r.get("campaign") and r.get("campaign") != CAMPAIGN:
            probs.append(f"{tag} wrong campaign={r.get('campaign')!r}")
        if r.get("smoke") or r.get("not_a_result"):
            probs.append(f"{tag} smoke/not_a_result record in campaign JSONL")
        ways = int(r.get("ways") or 0)
        ok, why = mask_check(r.get("mask_got"), ways)
        if not ok:
            probs.append(f"{tag} G-mask: {why}")
        if "mask_got_after" in r:
            ok, why = mask_held_check(
                r.get("mask_got"), r.get("mask_got_after"), ways,
                r.get("clos_cpus_after"), r.get("tenant_cpu"), r.get("victim_cpu"),
                r.get("clos_b_present_after"))
            if not ok:
                probs.append(f"{tag} G-mask-after: {why}")
        if ways > 0:
            if r.get("tenant_cpu") is not None and r.get("clos_cpus") is not None:
                ok, why = clos_check(str(r["clos_cpus"]), int(r["tenant_cpu"]),
                                     int(r["victim_cpu"]))
                if not ok:
                    probs.append(f"{tag} G-clos: {why}")
            ok, why = pid_check(arm, ways, r.get("tenant_pid"),
                                r.get("pid_in_clos"))
            if not ok:
                probs.append(f"{tag} G-pid: {why}")
        ok, why = identity_check(arm, r.get("policy"), r.get("join_path"),
                                 int(r.get("flush_distance") or 0),
                                 int(r.get("pf_distance") or 0))
        if not ok:
            probs.append(f"{tag} G-identity: {why}")
        hok, hwhy = host_check(str(r.get("host") or ""))
        if not hok:
            probs.append(f"{tag} G-host: {hwhy}")
        if arm != "qui":
            chain = int(r.get("chain") or WANT_CHAIN)
            ok, why = geom_check(int(r.get("n") or 0), int(r.get("probe") or 0),
                                 chain)
            if not ok:
                probs.append(f"{tag} G-geom: {why}")
            ok, why = version_check(r.get("duckdb_version"))
            if not ok:
                probs.append(f"{tag} G-ver: {why}")
            ref = ref_ju if chain == 1 else ref_c8
            ok, why = live_check(r.get("query_seconds"), r.get("matches"),
                                 ref, r.get("victim_n_trials"), arm)
            if not ok:
                probs.append(f"{tag} G-live: {why}")
        if r.get("victim_cyc_per_load") is None:
            probs.append(f"{tag} victim_cyc_per_load is null")
        if arm != "qui" and not r.get("query_seconds"):
            probs.append(f"{tag} missing tenant query_seconds")
        if r.get("join_mtuples_per_s") and not r.get("query_seconds"):
            probs.append(f"{tag} looks like hash-join silicon JSONL, not this campaign")
    return probs


def judge(rows, min_reps=MIN_REPS, expected_arms=FULL_ARMS):
    g = group(rows)
    missing = [a for a in expected_arms if len(g.get(a, [])) < min_reps]
    probs = record_problems(rows)
    vm = {a: median([r.get("victim_cyc_per_load") for r in g[a]]) for a in g}
    tm = {a: median([r.get("query_seconds") for r in g[a] if a != "qui"])
          for a in g}
    om = {a: median([r.get("occupancy_bytes_steady") for r in g[a]]) for a in g}
    if "wb" in expected_arms and "cat01" in expected_arms:
        occ_wb, occ_01 = om.get("wb"), om.get("cat01")
        if occ_wb is None or occ_01 is None or not (occ_01 < occ_wb):
            probs.append(
                f"G-cat-occ: cat01 occupancy is not < wb occupancy "
                f"(wb={occ_wb} cat01={occ_01})")
    complete = not missing and not probs

    report = []
    report.append("=" * 78)
    report.append(f"DUCKDB TENANT CAT -- {PREREG}")
    report.append(f"tenant = DuckDB v1.1.3 chain8 join N={WANT_N} "
                  f"P={WANT_PROBE} R={WANT_R_BYTES} B "
                  f"(R/LLC={WANT_R_BYTES / (60 * 1024 * 1024):.4f})")
    report.append("STREAMING / nta / flush-behind are not measured.")
    report.append("This is not DUCKDB_JOIN_CORUN_OUTCOME (wrong polarity).")
    report.append("=" * 78)

    if missing:
        report.append("\nINCOMPLETE:")
        for a in missing:
            report.append(f"  {a}: {len(g.get(a, []))} reps < {min_reps}")
    if probs:
        report.append("\nGATE FAILURES:")
        for p in probs:
            report.append("  " + p)

    report.append("\nVICTIM cycles/load (median)")
    for a in expected_arms:
        if a in vm and vm[a] is not None:
            vs = [r["victim_cyc_per_load"] for r in g[a]
                  if r.get("victim_cyc_per_load") is not None]
            sd = st.stdev(vs) if len(vs) > 1 else 0.0
            report.append(f"  {a:12s} n={len(vs)}  {vm[a]:8.3f}  sd={sd:.3f}")
    report.append("\nTENANT query_seconds (median)")
    for a in expected_arms:
        if a == "qui":
            continue
        if a in tm and tm[a] is not None:
            ts = [r["query_seconds"] for r in g[a]
                  if r.get("query_seconds") is not None]
            sd = st.stdev(ts) if len(ts) > 1 else 0.0
            report.append(f"  {a:12s} n={len(ts)}  {tm[a]:8.4f}  sd={sd:.4f}")
    report.append("\nTENANT CMT occupancy_bytes_steady (median)")
    for a in expected_arms:
        if a == "qui":
            continue
        if a in om and om[a] is not None:
            report.append(f"  {a:12s}  {om[a] / (1024 * 1024):8.2f} MiB")

    judgements = []

    def decide(name, pred, ok, detail, void=False):
        if void:
            verdict = "VOID" if not ok else "PASS"
        else:
            verdict = "PASS" if ok else "FAIL"
        judgements.append((name, verdict, ok, detail, void))
        report.append(f"\n{verdict} {name}: {pred}")
        report.append(f"      {detail}")

    v_qui, v_wb = vm.get("qui"), vm.get("wb")
    t_wb = tm.get("wb")
    tax = (v_wb / v_qui) if (v_qui and v_wb) else None
    k1 = tax is not None and tax >= S1_TAX_MIN
    decide("K1", f"wb degrades victim by >= {S1_TAX_MIN:.2f}x over quiet",
           k1, f"tax={tax:.3f}x" if tax is not None else "missing qui or wb",
           void=True)

    t_c01 = tm.get("cat01")
    t_c15 = tm.get("cat15")
    c_wb = query_cost(t_c01, t_wb)
    c_15 = query_cost(t_c01, t_c15)
    k2 = (c_wb is not None and c_wb >= K2_SLOWDOWN_MIN
          and c_15 is not None and c_15 >= K2_SLOWDOWN_MIN)
    decide("K2",
           (f"cat01 query seconds exceed wb and cat15 by "
            f">= {100 * K2_SLOWDOWN_MIN:.0f}%"),
           k2,
           (f"vs wb={100 * c_wb:.2f}%" if c_wb is not None else "vs wb=missing")
           + (f" vs cat15={100 * c_15:.2f}%" if c_15 is not None
              else " vs cat15=missing"),
           void=True)

    R = {}
    for w in CAT_WAYS:
        a = f"cat{w:02d}"
        p = protection(vm.get(a), v_wb, v_qui)
        if p is not None:
            R[w] = p
    best_w = max(R, key=R.get) if R else None
    best_arm = f"cat{best_w:02d}" if best_w is not None else None
    cost = query_cost(tm.get(best_arm), t_wb) if best_arm else None
    k3 = cost is not None and cost >= K3_COST_MIN
    decide("K3",
           (f"best-protection CAT costs tenant >= {100 * K3_COST_MIN:.0f}% "
            f"query seconds vs wb"),
           k3,
           f"best={best_arm} cost={100 * cost:.2f}%" if cost is not None
           else "missing tenant metric at best CAT",
           void=False)

    if R:
        curve = " ".join(f"w{w}={R[w]:.1f}%" for w in sorted(R))
        report.append(f"\nprotection curve (descriptive): {curve}")

    t_ju = tm.get("wb_joinuniq")
    if t_wb and t_ju:
        rel = abs(t_wb - t_ju) / t_wb
        report.append("\nDIAGNOSTIC joinuniq (not a kill):")
        report.append(f"      wb chain8={t_wb:.4f}s joinuniq={t_ju:.4f}s "
                      f"rel_diff={100 * rel:.2f}%")
        if rel <= JOINUNIQ_AGREE:
            report.append("      chain8 ≈ joinuniq: duplicate chain is not the "
                          "mechanism; claim narrows to hash-table reuse.")

    void = any((not ok) and is_void for _, _, ok, _, is_void in judgements)
    k3_ok = k3
    certify = complete and not void
    report.append("")
    if not complete:
        report.append("CERTIFY: NO  (incomplete or gate failure -- not a result)")
        report.append("VERDICT: VOID")
    elif void:
        report.append("CERTIFY: NO  (K1 or K2 failed -- campaign void)")
        report.append("VERDICT: VOID")
    elif not k3_ok:
        report.append("CERTIFY: YES  (valid measurement; K3 FAIL is a null)")
        report.append("VERDICT: NULL  (keep hash-join kernel as the e2e cell; "
                      "do not retract 'no named-application claim')")
    else:
        report.append("CERTIFY: YES")
        report.append("VERDICT: SUCCESS  (named-engine CAT tax in query seconds; "
                      "STREAMING still not in DuckDB)")
    return dict(report="\n".join(report) + "\n",
                complete=complete, certify=certify,
                void=void, k3=k3_ok,
                judgements=judgements, vm=vm, tm=tm, om=om, R=R,
                missing=missing, probs=probs)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--min-reps", type=int, default=MIN_REPS)
    ap.add_argument("--calib", action="store_true",
                    help="apparatus run: do not require the full arm set")
    args = ap.parse_args(argv)
    rows = stats.load_jsonl(args.jsonl)
    if args.calib:
        arms = tuple(sorted({r["arm"] for r in rows}))
        min_reps = min(args.min_reps, 2)
    else:
        arms = FULL_ARMS
        min_reps = args.min_reps
    out = judge(rows, min_reps=min_reps, expected_arms=arms)
    sys.stdout.write(out["report"])
    if not out["complete"] or out["void"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
