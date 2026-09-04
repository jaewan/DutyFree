#!/usr/bin/env python3
"""Fail-closed analyzer for silicon hash-join e2e.

Thresholds are the pre-registered ones in
SILICON_E2E_PREREGISTRATION_2026-09-01.md, held as module constants so that
changing one after seeing data is visible in git.

Refuses to certify on incomplete data.  A refuted prediction is printed as
FAIL, not reframed as a discovery.  S2 is UNTESTABLE on this part (addendum 1);
UNTESTABLE does not fail certify.
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
                                "silicon_e2e"))
from dutyfree import stats  # noqa: E402
from gates import (  # noqa: E402
    fb_identity_check, live_check, mask_check, mask_held_check,
    nta_identity_check, size_check,
    CALIB_FACT_BYTES, WANT_FACT_BYTES, WANT_HOT_BYTES,
)

# --- pre-registered thresholds ------------------------------------------------
S1_TAX_MIN = 1.30
S2_DROP_PP = 2.0          # shape diagnostic only; S2 is UNTESTABLE (addendum 1)
# S2 is untestable on a 15-way 60 MiB LLC.  The model's non-monotonicity
# lived at 0.25–1.5 MiB/way (1–6 of 20 HNF ways).  SPR grants 4.0 MiB at
# one way.  See SILICON_E2E_OUTCOME addendum 1.
S2_TESTABLE = False
S2_WHY = (
    "SPR socket-0 LLC is 60 MiB / 15 ways = 4.0 MiB at a 1-way mask. "
    "The model's starvation bend was 1–6 of 20 HNF ways at 0.25 MiB/way "
    "(0.25–1.5 MiB), peaking at 8/20 = 2.0 MiB.  Silicon's tightest CAT "
    "slice is 16× the model's floor and 2× its peak.  Bergamo "
    "(16 MiB / 16 ways = 1.0 MiB/way) is still 4× the floor.  S2 requires "
    "a cache slice CAT cannot express."
)
LLC_MIB = 60.0
CAT_WAYS_HOST = 15
MODEL_WAY_MIB = 5.0 / 20.0
S3_NTA_FRAC_MAX = 0.10    # nta protection <= 10% of best CAT
S4_CAT_COST_MIN = 0.10    # tenant cost at best-protection CAT
S5_FB_COST_MIN = 0.10
MIN_REPS = 5
CAT_WAYS = list(range(1, 16))
FB_ARMS = ("fb64k", "fb256k", "fb1m")
FULL_ARMS = ("qui", "wb", "nta") + FB_ARMS + tuple(f"cat{w:02d}" for w in CAT_WAYS)

PREREG = "SILICON_E2E_PREREGISTRATION_2026-09-01.md"


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


def tenant_cost(t_arm, t_wb):
    if None in (t_arm, t_wb) or t_wb <= 0:
        return None
    return 1.0 - (t_arm / t_wb)


def cat_nonmonotone(R: dict[int, float], drop_pp: float = S2_DROP_PP):
    """Shape diagnostic, not the S2 verdict.

    True iff protection peaks at an intermediate width, not at the narrowest.
    Kept so a future part that *can* express the starvation regime is judged
    against the original claim.  On this 15-way 60 MiB LLC, S2 is UNTESTABLE
    regardless of the curve (see S2_WHY).
    """
    if len(R) < 3:
        return False, "fewer than 3 CAT widths", None
    peak_w = max(R, key=lambda w: (R[w], -w))  # tie -> wider, still not "narrowest peak"
    # If several widths share the max, the interesting one is the widest of them
    # only when judging a plateau; for "peak at narrowest" any max at min(R) fails.
    min_w = min(R)
    max_at = [w for w in R if abs(R[w] - R[peak_w]) < 1e-9]
    if min_w in max_at or peak_w == min_w:
        return False, (f"peak at narrowest width cat{min_w:02d} ({R[min_w]:.1f}%) "
                       f"— protection rises as the mask narrows"), min_w
    narrower = [w for w in R if w < peak_w]
    worst_n = min(narrower, key=lambda w: R[w])
    d = R[peak_w] - R[worst_n]
    if d >= drop_pp:
        return True, (f"peak at cat{peak_w:02d} ({R[peak_w]:.1f}%), "
                      f"narrower cat{worst_n:02d} is {d:.1f} pp worse"), peak_w
    return False, (f"peak at cat{peak_w:02d} but narrower drop {d:.1f} pp "
                   f"< {drop_pp}"), peak_w


def group(rows):
    g = collections.defaultdict(list)
    for r in rows:
        g[r["arm"]].append(r)
    return g


def record_problems(rows, want_fact):
    probs = []
    ref_matches = None
    wb = [r for r in rows if r.get("arm") == "wb"]
    if wb:
        ref_matches = median([r.get("matches") for r in wb])
        if ref_matches is not None:
            ref_matches = int(ref_matches)
    for r in rows:
        arm, rep = r.get("arm"), r.get("rep")
        tag = f"{arm} rep{rep}"
        ways = int(r.get("ways") or 0)
        ok, why = mask_check(r.get("mask_got"), ways)
        if not ok:
            probs.append(f"{tag} G-mask: {why}")
        # Post-rep re-read.  Absent field = legacy JSONL, not a failure.
        if "mask_got_after" in r:
            ok, why = mask_held_check(
                r.get("mask_got"), r.get("mask_got_after"), ways,
                r.get("clos_cpus_after"), r.get("tenant_cpu"), r.get("victim_cpu"),
                r.get("clos_b_present_after"))
            if not ok:
                probs.append(f"{tag} G-mask-after: {why}")
        if ways > 0:
            if r.get("tenant_cpu") is not None and r.get("clos_cpus") is not None:
                from gates import clos_check
                ok, why = clos_check(str(r["clos_cpus"]), int(r["tenant_cpu"]),
                                     int(r["victim_cpu"]))
                if not ok:
                    probs.append(f"{tag} G-clos: {why}")
        ok, why = fb_identity_check(arm, r.get("join_path") or "join_range",
                                    int(r.get("flush_distance") or 0))
        if not ok:
            probs.append(f"{tag} G-fb: {why}")
        ok, why = nta_identity_check(arm, r.get("policy") or "wb",
                                     int(r.get("pf_distance") or 0))
        if not ok:
            probs.append(f"{tag} G-nta: {why}")
        if arm != "qui":
            ok, why = live_check(r.get("join_mtuples_per_s"), r.get("matches"),
                                 ref_matches)
            if not ok:
                probs.append(f"{tag} G-live: {why}")
            hot = r.get("instantiated_hot_bytes")
            fact = r.get("fact_bytes")
            if fact is not None and hot is not None:
                stderr = "HOT_TABLE_ROUNDED" if r.get("hot_table_rounded") else ""
                ok, why = size_check(int(fact), int(hot), stderr, want_fact=want_fact)
                if not ok:
                    probs.append(f"{tag} G-size: {why}")
        if r.get("victim_cyc_per_load") is None:
            probs.append(f"{tag} victim_cyc_per_load is null")
        if arm != "qui" and not r.get("join_mtuples_per_s"):
            probs.append(f"{tag} missing tenant metric")
    return probs


def judge(rows, min_reps=MIN_REPS, expected_arms=FULL_ARMS, want_fact=WANT_FACT_BYTES):
    g = group(rows)
    missing = [a for a in expected_arms if len(g.get(a, [])) < min_reps]
    probs = record_problems(rows, want_fact)
    complete = not missing and not probs

    vm = {a: median([r.get("victim_cyc_per_load") for r in g[a]]) for a in g}
    tm = {a: median([r.get("join_mtuples_per_s") for r in g[a] if a != "qui"])
          for a in g}

    report = []
    report.append("=" * 78)
    report.append(f"SILICON HASH-JOIN E2E -- {PREREG}")
    report.append("tenant = 8 GiB stream + 32 MiB hash table; victim = pointer chase")
    report.append("STREAMING is not measured on this platform.")
    hrs = sorted({r.get("hit_rate") for r in rows if r.get("arm") != "qui"
                  and r.get("hit_rate") is not None})
    if hrs:
        report.append(f"hit_rate={hrs} on silicon (model used 0.5; 1.0 is M3 "
                      "saturation — comparability is two dimensions, not one)")
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
            report.append(f"  {a:8s} n={len(vs)}  {vm[a]:8.3f}  sd={sd:.3f}")
    report.append("\nTENANT join_mtuples_per_s (median)")
    for a in expected_arms:
        if a == "qui":
            continue
        if a in tm and tm[a] is not None:
            ts = [r["join_mtuples_per_s"] for r in g[a]
                  if r.get("join_mtuples_per_s") is not None]
            sd = st.stdev(ts) if len(ts) > 1 else 0.0
            report.append(f"  {a:8s} n={len(ts)}  {tm[a]:8.4f}  sd={sd:.4f}")

    p99m = {}
    for a in expected_arms:
        xs = [r.get("victim_p99") for r in g.get(a, [])
              if r.get("victim_p99") is not None]
        if xs:
            p99m[a] = median(xs)
    if p99m:
        report.append("\nVICTIM p99 cycles/load (median of per-rep p99)")
        for a in expected_arms:
            if a in p99m:
                report.append(f"  {a:8s}  {p99m[a]:8.3f}")

    judgements = []

    def decide(name, pred, ok, detail, testable=True):
        if not testable:
            verdict = "UNTESTABLE"
            judgements.append((name, verdict, True, detail))
        else:
            verdict = "PASS" if ok else "FAIL"
            judgements.append((name, verdict, ok, detail))
        report.append(f"\n{verdict} {name}: {pred}")
        report.append(f"      {detail}")

    v_qui, v_wb = vm.get("qui"), vm.get("wb")
    t_wb = tm.get("wb")
    tax = (v_wb / v_qui) if (v_qui and v_wb) else None
    decide("S1", f"wb degrades victim by >= {S1_TAX_MIN:.2f}x over quiet",
           tax is not None and tax >= S1_TAX_MIN,
           f"tax={tax:.3f}x" if tax is not None else "missing qui or wb")

    R = {}
    for w in CAT_WAYS:
        a = f"cat{w:02d}"
        p = protection(vm.get(a), v_wb, v_qui)
        if p is not None:
            R[w] = p
    decide("S2", "CAT protection is non-monotone in mask width",
           True, S2_WHY, testable=S2_TESTABLE)
    if R:
        curve = " ".join(f"w{w}={R[w]:.1f}%" for w in sorted(R))
        report.append(f"      descriptive curve (not an S2 test): {curve}")
        _, why_shape, _ = cat_nonmonotone(R)
        report.append(f"      shape diagnostic (not a verdict): {why_shape}")

    p_nta = protection(vm.get("nta"), v_wb, v_qui)
    p_best = max(R.values()) if R else None
    frac = (p_nta / p_best) if (p_nta is not None and p_best and p_best > 0) else None
    decide("S3", "nta protects victim by <= 10% of best CAT",
           frac is not None and frac <= S3_NTA_FRAC_MAX,
           f"nta_R={p_nta:.1f}% best_CAT={p_best:.1f}% frac={frac:.3f}"
           if frac is not None else "missing nta or CAT")

    best_w = max(R, key=R.get) if R else None
    best_arm = f"cat{best_w:02d}" if best_w is not None else None
    cost = tenant_cost(tm.get(best_arm), t_wb) if best_arm else None
    decide("S4", "best-protection CAT costs tenant >= 10% tuples/s vs wb",
           cost is not None and cost >= S4_CAT_COST_MIN,
           f"best={best_arm} cost={100*cost:.2f}%" if cost is not None
           else "missing tenant metric at best CAT")

    fb_costs = {a: tenant_cost(tm.get(a), t_wb) for a in FB_ARMS if tm.get(a)}
    best_fb = max(fb_costs, key=lambda a: fb_costs[a]) if fb_costs else None
    fb_c = fb_costs.get(best_fb) if best_fb else None
    decide("S5", "flush-behind's best setting costs tenant >= 10% tuples/s",
           fb_c is not None and fb_c >= S5_FB_COST_MIN,
           f"best={best_fb} cost={100*fb_c:.2f}%" if fb_c is not None
           else "missing fb tenant metric")

    # Finding, not a registered prediction: iso-protection flush-behind vs CAT.
    # Promoted 2026-09-01 after S5 FAIL; raises STREAMING's bar, does not
    # favour STREAMING.
    p_fb = protection(vm.get("fb256k"), v_wb, v_qui)
    if p_fb is not None and R:
        nearest_w = min(R, key=lambda w: abs(R[w] - p_fb))
        near_arm = f"cat{nearest_w:02d}"
        c_near = tenant_cost(tm.get(near_arm), t_wb)
        c_fb = tenant_cost(tm.get("fb256k"), t_wb)
        ratio = (c_near / c_fb) if (c_near and c_fb and c_fb > 0) else None
        report.append("\nFINDING F-fb (unregistered at measurement; promoted after S5):")
        report.append(f"      fb256k R={p_fb:.1f}% cost={100*c_fb:.2f}%  vs "
                      f"{near_arm} R={R[nearest_w]:.1f}% cost={100*c_near:.2f}%"
                      + (f"  ({ratio:.1f}× cheaper than CAT at matched R)"
                         if ratio else ""))
        report.append("      STREAMING's silicon bar is flush-behind at matched "
                      "median protection, not CAT at 42%.")

    if p_nta is not None and R:
        nearest_nta = min(R, key=lambda w: abs(R[w] - p_nta))
        nta_arm = f"cat{nearest_nta:02d}"
        c_nta = tenant_cost(tm.get("nta"), t_wb)
        c_ncat = tenant_cost(tm.get(nta_arm), t_wb)
        report.append("\nFINDING F-nta (unregistered at measurement; promoted after S3):")
        report.append(f"      nta R={p_nta:.1f}% cost="
                      + (f"{100*c_nta:.2f}%" if c_nta is not None else "?")
                      + f"  vs {nta_arm} R={R[nearest_nta]:.1f}% cost="
                      + (f"{100*c_ncat:.2f}%" if c_ncat is not None else "?"))
        if c_nta is not None and c_nta < 0:
            report.append("      nta is faster than unprotected wb and still "
                          "recovers ~15% — it dominates CAT at this protection.")
        report.append("      STREAMING must also beat free recovery at ~15%.")

    testable_ok = all(ok for name, verdict, ok, _ in judgements
                      if verdict != "UNTESTABLE")
    certify = complete and testable_ok
    report.append("")
    if not complete:
        report.append("CERTIFY: NO  (incomplete or gate failure -- not a result)")
    elif not testable_ok:
        report.append("CERTIFY: NO  (complete; one or more testable predictions "
                      "FAIL -- report as refutation)")
    else:
        report.append("CERTIFY: YES")
    return dict(report="\n".join(report) + "\n",
                complete=complete, certify=certify,
                judgements=judgements, vm=vm, tm=tm, R=R,
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
        want_fact = CALIB_FACT_BYTES
        min_reps = min(args.min_reps, 2)
    else:
        arms = FULL_ARMS
        want_fact = WANT_FACT_BYTES
        min_reps = args.min_reps
    out = judge(rows, min_reps=min_reps, expected_arms=arms, want_fact=want_fact)
    sys.stdout.write(out["report"])
    if not out["complete"]:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
