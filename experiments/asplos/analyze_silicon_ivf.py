#!/usr/bin/env python3
"""Fail-closed analyzer for the silicon IVF-Flat operator cell.

Thresholds are the pre-registered ones in
IVF_FLAT_SILICON_PREREG_2026-09-01.md.  The per-record admission gates are
imported from silicon_e2e/ivf_gates.py rather than restated, so a threshold
cannot be edited here without the runner disagreeing.

The prereg's kill list is richer than its prediction list.  Each entry is
evaluated by its registered name and printed as PASS / FAIL / VOID / KILL:

  G-ratio       --require-ratio: codebook/LLC in [0.50, 0.55].  A kernel gate,
                not a measured result.  If it fires, IVF silicon must not run.
  G-recall      recall@k in (0, 1], else the cell is VOID (costume check).
  S1-void       wb must tax the pointer chase, else nothing to protect: stop.
  CAT-tax       the starving end of the CAT frontier vs wb must move tenant
                QPS materially, else do not run gem5 H2.  A miss here is the
                registered finding, not a failure of the campaign.

STREAMING is not an arm.  No gem5 point is computed or plotted here.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "silicon_e2e"))

from ivf_gates import (  # noqa: E402
    RATIO_HI, RATIO_LO, WANT_CODEBOOK_BYTES, WANT_DIM, WANT_LLC_BYTES,
    WANT_NLIST, cat_tax_material, codebook_size_check, fb_identity_check,
    nta_identity_check, ratio_check, recall_check,
)

# --- pre-registered thresholds -----------------------------------------------
S1_TAX_MIN = 1.30          # SILICON_E2E S1's bar, referenced by "S1-style void"
CAT_TAX_MIN_REL = 0.10     # ivf_gates.cat_tax_material default
MIN_REPS = 5
CAT_WAYS = list(range(1, 16))
FB_ARMS = ("fb64k", "fb256k", "fb1m")
FULL_ARMS = ("qui", "wb", "nta") + FB_ARMS + tuple(f"cat{w:02d}" for w in CAT_WAYS)

PREREG = "IVF_FLAT_SILICON_PREREG_2026-09-01.md"


def median(xs):
    xs = [x for x in xs if x is not None]
    return st.median(xs) if xs else None


def protection(v_arm, v_wb, v_qui):
    """R = (v_wb - v) / (v_wb - v_qui), percent."""
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


def group(rows):
    g = collections.defaultdict(list)
    for r in rows:
        g[r["arm"]].append(r)
    return g


def record_problems(rows):
    """Per-record admission gates.  Anything here blocks certification."""
    probs = []
    for r in rows:
        tag = f"{r.get('arm')} rep{r.get('rep')}"
        if r.get("status") != "ok":
            probs.append(f"{tag} status={r.get('status')} "
                         f"{r.get('error') or r.get('idle_why') or ''}".strip())
            continue
        if r.get("streaming_arm"):
            probs.append(f"{tag} streaming_arm is set; STREAMING is not an arm")
        if r.get("arm") == "qui":
            continue
        if r.get("sealed") is not True:
            probs.append(f"{tag} sealed={r.get('sealed')}")
        if not r.get("ivf_measure_end"):
            probs.append(f"{tag} no IVF_MEASURE_END")
        ok, why = ratio_check(int(r.get("codebook_bytes") or 0),
                             int(r.get("llc_bytes") or 0))
        if not ok:
            probs.append(f"{tag} G-ratio: {why}")
        ok, why = codebook_size_check(int(r.get("nlist") or 0),
                                     int(r.get("dim") or 0),
                                     int(r.get("codebook_bytes") or 0))
        if not ok:
            probs.append(f"{tag} G-codebook: {why}")
        ok, why = recall_check(r.get("recall_at_k"))
        if not ok:
            probs.append(f"{tag} G-recall: {why}")
        ok, why = fb_identity_check(r.get("arm"), r.get("list_path") or "",
                                   int(r.get("flush_distance") or 0))
        if not ok:
            probs.append(f"{tag} G-fb: {why}")
        ok, why = nta_identity_check(r.get("arm"), r.get("policy") or "",
                                    int(r.get("pf_distance") or 0))
        if not ok:
            probs.append(f"{tag} G-nta: {why}")
        for f in ("mask_ok", "clos_ok", "live_ok"):
            if r.get(f) is False:
                probs.append(f"{tag} {f}: {r.get(f.replace('_ok', '_why'))}")
        if r.get("mask_held_ok") is False:
            probs.append(f"{tag} mask_held: {r.get('mask_held_why')}")
    return probs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--min-reps", type=int, default=MIN_REPS)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.jsonl) if l.strip()]
    g = group(rows)

    print(f"== silicon IVF-Flat operator cell — judged against {PREREG}")
    print(f"== {len(rows)} records, {len(g)} arms, "
          f"host={sorted({r.get('host') for r in rows})}")
    shas = sorted({(r.get("sha_ivf") or "")[:12] for r in rows})
    shav = sorted({(r.get("sha_victim") or "")[:12] for r in rows})
    print(f"== ivf={shas} victim={shav}")
    if any(r.get("streaming_arm") for r in rows):
        print("FATAL: a record claims a STREAMING arm")
        return 2

    # ---- realized geometry, never requested --------------------------------
    ten = [r for r in rows if r.get("arm") != "qui" and r.get("status") == "ok"]
    if not ten:
        print("FATAL: no ok tenant records; nothing to analyze")
        return 2
    geo = {}
    for k in ("nlist", "dim", "codebook_bytes", "llc_bytes",
              "codebook_llc_ratio", "lists_bytes"):
        vals = sorted({r.get(k) for r in ten if r.get(k) is not None})
        if vals:
            geo[k] = vals
    for k in ("nlist", "dim", "codebook_bytes", "llc_bytes"):
        if k not in geo:
            print(f"FATAL: no record carries {k}; cannot report realized geometry")
            return 2
    print("\n-- realized configuration (from the tenant's own JSON) --")
    for k, v in geo.items():
        print(f"   {k:20s} {v if len(v) > 1 else v[0]}")
    # search parameters are on the tenant command line, not the JSON summary
    cmds = sorted({" ".join(r.get("tenant_cmd") or []) for r in ten})
    for c in cmds:
        for flag in ("--nq", "--nb", "--nprobe", "--k", "--reps"):
            toks = c.split()
            if flag in toks:
                print(f"   {flag:20s} {toks[toks.index(flag) + 1]}")
        break
    ratio = geo["codebook_llc_ratio"][0]
    cb = geo["codebook_bytes"][0]
    llc = geo["llc_bytes"][0]

    print("\n-- registered gates --")
    rc = []
    ok, why = ratio_check(int(cb), int(llc))
    print(f"   G-ratio      {'PASS' if ok else 'KILL'}  realized "
          f"codebook/LLC = {ratio:.6f} "
          f"({cb} / {llc}) window [{RATIO_LO}, {RATIO_HI}] :: {why}")
    rc.append(ok)
    ok2, why2 = codebook_size_check(int(geo['nlist'][0]), int(geo['dim'][0]), int(cb))
    print(f"   G-codebook   {'PASS' if ok2 else 'FAIL'}  nlist={geo['nlist'][0]} "
          f"dim={geo['dim'][0]} want nlist={WANT_NLIST} dim={WANT_DIM} "
          f"codebook={WANT_CODEBOOK_BYTES} :: {why2}")
    rc.append(ok2)

    recalls = [r.get("recall_at_k") for r in ten]
    rmed = median(recalls)
    okr, whyr = recall_check(rmed)
    print(f"   G-recall     {'PASS' if okr else 'VOID'}  median recall@k = "
          f"{rmed} over {len(recalls)} tenant records "
          f"(spread {min(recalls)} .. {max(recalls)}) :: {whyr}")
    rc.append(okr)

    # ---- per-arm aggregation: median of per-rep values ---------------------
    agg = {}
    for arm, rs in g.items():
        okrs = [r for r in rs if r.get("status") == "ok"]
        agg[arm] = dict(
            n=len(okrs),
            victim=median([r.get("victim_cyc_per_load") for r in okrs]),
            victim_sd=(st.stdev([r["victim_cyc_per_load"] for r in okrs
                                 if r.get("victim_cyc_per_load") is not None])
                       if len([r for r in okrs
                               if r.get("victim_cyc_per_load") is not None]) > 1
                       else 0.0),
            p99=median([r.get("victim_p99") for r in okrs]),
            qps=median([r.get("qps") for r in okrs]),
            recall=median([r.get("recall_at_k") for r in okrs]),
        )
    v_qui = agg.get("qui", {}).get("victim")
    v_wb = agg.get("wb", {}).get("victim")
    t_wb = agg.get("wb", {}).get("qps")

    # ---- S1-style void -----------------------------------------------------
    tax = (v_wb / v_qui) if (v_wb and v_qui) else None
    s1 = tax is not None and tax >= S1_TAX_MIN
    print(f"   S1-void      {'PASS' if s1 else 'KILL'}  wb taxes the chase "
          f"{tax:.3f}x ({v_wb:.3f} / {v_qui:.3f}) bar >= {S1_TAX_MIN}"
          f"{'' if s1 else '  -> nothing to protect; stop'}")
    rc.append(s1)

    # ---- the table ---------------------------------------------------------
    print("\n-- per-arm medians (realized) --")
    print(f"   {'arm':8s} {'n':>2s} {'victim':>9s} {'sd':>6s} {'p99':>8s} "
          f"{'R%':>7s} {'qps':>9s} {'cost%':>7s} {'recall':>8s}")
    order = [a for a in FULL_ARMS if a in agg]
    for arm in order:
        a = agg[arm]
        R = protection(a["victim"], v_wb, v_qui)
        c = tenant_cost(a["qps"], t_wb)
        print(f"   {arm:8s} {a['n']:2d} "
              f"{a['victim']:9.3f} {a['victim_sd']:6.3f} "
              f"{(a['p99'] if a['p99'] is not None else float('nan')):8.2f} "
              f"{(R if R is not None else float('nan')):7.1f} "
              f"{(a['qps'] if a['qps'] is not None else float('nan')):9.3f} "
              f"{(100.0 * c if c is not None else float('nan')):7.2f} "
              f"{(a['recall'] if a['recall'] is not None else float('nan')):8.4f}")

    # ---- CAT tax at the starving end ---------------------------------------
    print("\n-- CAT-tax gate (the registered kill for gem5 H2) --")
    Rc = {w: protection(agg[f"cat{w:02d}"]["victim"], v_wb, v_qui)
          for w in CAT_WAYS if f"cat{w:02d}" in agg
          and agg[f"cat{w:02d}"]["victim"] is not None}
    best_w = max(Rc, key=lambda w: Rc[w]) if Rc else None
    starve = min(Rc) if Rc else None
    verdicts = []
    seen_w = set()
    for label, w in ((f"starving end ({starve} way{'' if starve == 1 else 's'})"
                      if starve is not None else "starving end", starve),
                     ("best-protection CAT", best_w)):
        if w is None or w in seen_w:
            continue
        seen_w.add(w)
        arm = f"cat{w:02d}"
        okc, whyc = cat_tax_material(t_wb, agg[arm]["qps"], CAT_TAX_MIN_REL)
        c = tenant_cost(agg[arm]["qps"], t_wb)
        verdicts.append((label, arm, okc, whyc, c, Rc[w]))
        print(f"   {label:22s} {arm}  R={Rc[w]:6.1f}%  tenant QPS cost "
              f"{100.0 * c:6.2f}%  bar >= {100.0 * CAT_TAX_MIN_REL:.0f}%  "
              f"-> {'MATERIAL' if okc else 'TOO SMALL (do not run gem5 H2)'}")
    cat_material = any(v[2] for v in verdicts)
    cat_note = ("a material tenant tax exists" if cat_material
                else "no material tenant tax at any measured width")
    print(f"   CAT-tax      {'PASS' if cat_material else 'KILL'}  {cat_note}")

    # ---- software mitigations, for the H2 headroom question ----------------
    print("\n-- nta / flush-behind (the software analogue of tagging the lists) --")
    for arm in ("nta",) + FB_ARMS:
        if arm not in agg:
            continue
        a = agg[arm]
        R = protection(a["victim"], v_wb, v_qui)
        c = tenant_cost(a["qps"], t_wb)
        print(f"   {arm:8s} R={R:6.1f}%  tenant cost {100.0 * c:6.2f}%")

    # ---- admission ---------------------------------------------------------
    probs = record_problems(rows)
    reps = sorted({r.get("rep") for r in rows})
    missing = [a for a in FULL_ARMS if a not in agg]
    print("\n-- admission --")
    print(f"   reps={reps} arms_missing={missing or 'none'} "
          f"ok_records={sum(1 for r in rows if r.get('status') == 'ok')}/{len(rows)}")
    if probs:
        print(f"   {len(probs)} record problems:")
        for p in probs[:40]:
            print(f"     - {p}")
    else:
        print("   no record problems")

    complete = (not probs and not missing and len(reps) >= args.min_reps)
    gates_ok = all(rc)
    print("\n== VERDICT")
    if not gates_ok:
        print("   a registered kill/void gate fired; see above")
    print(f"   complete={complete}  registered_gates_ok={gates_ok}  "
          f"cat_tax_material={cat_material}")
    print(f"   CERTIFY: {'YES' if (complete and gates_ok) else 'NO'}")
    print(f"   gem5 H2 (ivf-gem5-conditional) motivated by CAT tax: "
          f"{'YES' if cat_material else 'NO'}")
    print("   STREAMING was not measured on silicon and is not an arm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
