#!/usr/bin/env python3
"""Judge the AMD cross-socket placement sweep against AMD_XSOCKET_PREREG_2026-09-04.md.

Every threshold below is a MODULE CONSTANT, frozen with the pre-registration
before the data existed, so changing one after seeing data is visible in git.

Usage: analyze_amd_xsocket.py data/amd_xsocket.jsonl
"""
import json, sys, statistics as st, random

# ---------------------------------------------------------------- constants
N_EXPECTED       = 20          # matches bergamo_backinval.py / BERGAMO_BACKINVAL_OUTCOME
PRIMARY          = ("always", 4096)   # the cell whose other-CCX value is the published 1.30x
PUBLISHED_OTHER  = 1.30        # Sec7_Evaluation.tex:313
G0_BAND          = (1.20, 1.40)       # same-socket control must bracket the published figure
G5_RATE_TOL      = 0.10        # streamer bandwidth must match same-CCX within +/-10%
G6_FREQ_TOL      = 0.10        # core-0 frequency must match quiescent_a within +/-10%
G7_NB_CEILING    = 0.10        # a noise band wider than this makes the apparatus unfit
G10_SAME_MIN     = 10.0        # positive control: same-CCX harm must be at least this
NB_FLOOR         = 0.02        # noise band floor, so a freak-tight control cannot overfit
ALPHA            = 0.05
BOOT_N           = 10000
BOOT_SEED        = 20260904
VICTIM_CORE      = 0
VICTIM_NODE      = 0
STREAM_NODE      = 2           # CXL; held fixed in every arm by mbind MPOL_MF_STRICT
NODE_FRAC_MIN    = 0.99
PLACES           = ("quiescent_a", "same", "other", "xsock", "quiescent_b")
XSOCK_PKG        = "1"
SAMESOCK_PKG     = "0"


def med(xs):
    return st.median(xs)


def boot_ratio(num, den, seed=BOOT_SEED, n=BOOT_N):
    """Percentile bootstrap CI for median(num)/median(den), resampled independently."""
    rng = random.Random(seed)
    rs = []
    for _ in range(n):
        a = med([num[rng.randrange(len(num))] for _ in num])
        b = med([den[rng.randrange(len(den))] for _ in den])
        rs.append(a / b)
    rs.sort()
    lo = rs[int(0.025 * n)]
    hi = rs[int(0.975 * n) - 1]
    return lo, hi


def mannwhitney_p(a, b):
    """Two-sided Mann-Whitney U with a normal approximation and tie correction."""
    na, nb = len(a), len(b)
    allv = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks, i, ties = [0.0] * len(allv), 0, 0.0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        t = j - i + 1
        ties += t ** 3 - t
        for k in range(i, j + 1):
            ranks[k] = r
        i = j + 1
    ra = sum(r for r, (_, g) in zip(ranks, allv) if g == 0)
    u = ra - na * (na + 1) / 2.0
    mu = na * nb / 2.0
    n = na + nb
    var = na * nb / 12.0 * ((n + 1) - ties / (n * (n - 1)))
    if var <= 0:
        return 1.0
    z = (abs(u - mu) - 0.5) / var ** 0.5
    # two-sided normal tail
    import math
    return max(0.0, min(1.0, math.erfc(z / math.sqrt(2))))


def cell(recs, thp, wss, place):
    return [r for r in recs
            if r["thp_readback"] == thp and r["wss_kb"] == wss and r["place"] == place]


def frac_on(hist, node):
    if not hist:
        return 0.0
    tot = sum(hist.values())
    return hist.get(str(node), hist.get(node, 0)) / tot if tot else 0.0


def main():
    recs = [json.loads(l) for l in open(sys.argv[1])]
    gates, notes = {}, []

    # ---------------- G8 liveness / completeness
    bad_ok = [r for r in recs if not r["ok"] or r["cyc_per_access"] is None]
    counts = {(t, w, p): len(cell(recs, t, w, p))
              for t in ("never", "always") for w in (512, 4096) for p in PLACES}
    quiet_bw = [r for r in recs if r["place"].startswith("quiescent") and r["agg_gbps"]]
    gates["G8_liveness"] = (not bad_ok and all(v == N_EXPECTED for v in counts.values())
                            and not quiet_bw)
    notes.append(f"G8: {len(recs)} runs, {len(bad_ok)} without a VICTIM line, "
                 f"cell sizes {sorted(set(counts.values()))}, "
                 f"{len(quiet_bw)} quiescent runs with nonzero streamer bandwidth")

    # ---------------- G9 THP readback
    gates["G9_thp"] = all(r["thp_readback"] == r["thp_requested"] for r in recs)

    # ---------------- G1 victim pinning
    g1 = all(r["victim_cpus_allowed"] == str(VICTIM_CORE)
             and r["victim_realized_cpus"]
             and set(r["victim_realized_cpus"]) == {VICTIM_CORE}
             for r in recs)
    gates["G1_victim_pinning"] = g1

    # ---------------- G2 streamer placement realized
    g2 = True
    for r in recs:
        if not r["agg_cores"]:
            continue
        want = {int(x) for x in r["agg_cores"].split(",")}
        if not r["agg_realized_cpus"] or not set(r["agg_realized_cpus"]) <= want:
            g2 = False
        if not r["agg_l3_domains_all"] or len(r["agg_l3_domains_all"]) != 1:
            g2 = False
        same_dom = r["agg_l3_domains_all"] == [r["victim_l3_domain"]]
        if r["place"] == "same" and not same_dom:
            g2 = False
        if r["place"] in ("other", "xsock") and same_dom:
            g2 = False
    gates["G2_streamer_placement"] = g2

    # ---------------- G3 socket realized
    g3 = True
    for r in recs:
        if not r["agg_cores"]:
            continue
        want = XSOCK_PKG if r["place"] == "xsock" else SAMESOCK_PKG
        if r["agg_pkgs_all"] != [want] or r["victim_pkg"] != SAMESOCK_PKG:
            g3 = False
    gates["G3_socket"] = g3

    # ---------------- G4 realized NUMA placement of victim and stream
    g4 = True
    for r in recs:
        if frac_on(r["victim_numa_pages"], VICTIM_NODE) < NODE_FRAC_MIN:
            g4 = False
        if r["agg_cores"]:
            if r["agg_fatal"] or frac_on(r["agg_numa_pages"], STREAM_NODE) < NODE_FRAC_MIN:
                g4 = False
    gates["G4_numa_placement"] = g4

    # ---------------- G6 SMT and frequency state
    g6 = all(r["smt_control"] == "on" and r["smt_active"] == "1" and r["boost"] == "1"
             for r in recs)
    gates["G6_smt_boost"] = g6

    # ---------------- per-cell statistics
    out = {}
    for thp in ("never", "always"):
        for wss in (512, 4096):
            qa = [r["cyc_per_access"] for r in cell(recs, thp, wss, "quiescent_a")]
            if not qa:
                continue
            row = {"quiescent_a_median": med(qa)}
            for p in PLACES[1:]:
                xs = [r["cyc_per_access"] for r in cell(recs, thp, wss, p)]
                if not xs:
                    continue
                lo, hi = boot_ratio(xs, qa)
                bws = [r["agg_gbps"] for r in cell(recs, thp, wss, p) if r["agg_gbps"]]
                fq = [r["freq_khz"] for r in cell(recs, thp, wss, p) if r["freq_khz"]]
                row[p] = {
                    "median": med(xs), "iqr": (st.quantiles(xs, n=4)[2] - st.quantiles(xs, n=4)[0]),
                    "slowdown": med(xs) / med(qa), "ci95": [lo, hi],
                    "p_vs_quiescent_a": mannwhitney_p(xs, qa),
                    "agg_gbps_median": med(bws) if bws else None,
                    "freq_khz_median": med(fq) if fq else None,
                }
            row["quiescent_a_freq_khz_median"] = med(
                [r["freq_khz"] for r in cell(recs, thp, wss, "quiescent_a") if r["freq_khz"]])
            out[f"{thp}/{wss}"] = row

    # ---------------- noise band, from the negative control
    nb = {}
    for k, row in out.items():
        qb = row.get("quiescent_b")
        if not qb:
            continue
        lo, hi = qb["ci95"]
        nb[k] = max(NB_FLOOR, abs(lo - 1.0), abs(hi - 1.0))
    pk = f"{PRIMARY[0]}/{PRIMARY[1]}"
    NB = nb.get(pk)
    gates["G7_noise_band"] = NB is not None and NB <= G7_NB_CEILING

    # ---------------- G0 same-socket control, G10 positive control
    prow = out.get(pk, {})
    s_other = prow.get("other", {}).get("slowdown")
    s_same = prow.get("same", {}).get("slowdown")
    gates["G0_samesocket_control"] = (s_other is not None
                                      and G0_BAND[0] <= s_other <= G0_BAND[1])
    gates["G10_positive_control"] = s_same is not None and s_same >= G10_SAME_MIN

    # ---------------- G5 rate matching, G6b frequency
    g5 = True
    for k, row in out.items():
        base = row.get("same", {}).get("agg_gbps_median")
        for p in ("other", "xsock"):
            v = row.get(p, {}).get("agg_gbps_median")
            if base and v and abs(v - base) / base > G5_RATE_TOL:
                g5 = False
    gates["G5_rate_match"] = g5

    g6b = True
    for k, row in out.items():
        base = row.get("quiescent_a_freq_khz_median")
        for p in PLACES[1:]:
            v = row.get(p, {}).get("freq_khz_median")
            if base and v and abs(v - base) / base > G6_FREQ_TOL:
                g6b = False
    gates["G6b_frequency"] = g6b

    # ---------------- verdict on the claim
    verdict, reason = "INCONCLUSIVE", []
    xs = prow.get("xsock")
    if xs and NB is not None:
        lo, hi = xs["ci95"]
        p = xs["p_vs_quiescent_a"]
        inside = (hi <= 1 + NB) and (lo >= 1 - NB)
        above = lo > 1 + NB
        below = hi < 1 - NB
        if inside and p > ALPHA:
            verdict = "A_CONFIRMED"
        elif above and p <= ALPHA:
            verdict = "B_REFUTED_WITH_RESIDUAL"
        elif below:
            verdict = "C2_ANOMALOUS_SPEEDUP"
        elif inside and p <= ALPHA:
            verdict = "C1_DETECTABLE_BUT_WITHIN_BAND"
        else:
            verdict = "C_INCONCLUSIVE"
        reason = [f"S={xs['slowdown']:.4f} CI95=[{lo:.4f},{hi:.4f}] "
                  f"NB={NB:.4f} band=[{1-NB:.4f},{1+NB:.4f}] p={p:.3g}"]

    blocking = ["G0_samesocket_control", "G1_victim_pinning", "G2_streamer_placement",
                "G3_socket", "G4_numa_placement", "G5_rate_match", "G6_smt_boost",
                "G6b_frequency", "G7_noise_band", "G8_liveness", "G9_thp",
                "G10_positive_control"]
    failed = [g for g in blocking if not gates.get(g)]
    certified = not failed

    print(json.dumps({
        "n_expected": N_EXPECTED, "cells": out, "noise_band": nb,
        "primary_cell": pk, "NB_primary": NB,
        "published_other_ccx": PUBLISHED_OTHER,
        "gates": gates, "failed_gates": failed,
        "verdict": verdict if certified else f"{verdict} (UNCERTIFIED: {failed})",
        "certified": certified, "reason": reason, "notes": notes,
    }, indent=2, default=str))
    return 0


sys.exit(main())
