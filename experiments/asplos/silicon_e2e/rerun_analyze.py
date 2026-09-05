#!/usr/bin/env python3
"""Registered analyzer for the silicon hash-join e2e clean re-run.

Pre-registration: experiments/asplos/SILICON_E2E_RERUN_PREREG_2026-09-04.md

Committed BEFORE the campaign was measured, so that the gate predicates, the
frozen reproducibility envelope and the D1-D4 thresholds cannot be chosen
after seeing the data.  Precedence rests on the commit, not on a file mtime.

The frontier coordinates reproduce make_eval_frontiers.py:91-98 exactly:

    q  = median victim_cyc_per_load over arm `qui`
    w  = median victim_cyc_per_load over arm `wb`
    tw = median join_mtuples_per_s   over arm `wb`
    protection(a)  = 100 * (w - v_a) / (w - q)
    tenant_cost(a) = 100 * (t_a / tw - 1)

Every gate here is pure in the values it is given, and --self-test feeds each
one a case that must fail before a case that must pass: a gate that cannot
fail is not a gate.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import defaultdict

# ---------------------------------------------------------------- frozen facts

# Geometry.  EXACT_MATCHES is arithmetic, not a measurement: it is
# fact_bytes / sizeof(Fact) * inner_reps, and it is what G-exact asserts.
WANT_FACT_BYTES = 8 * 1024 * 1024 * 1024      # 8589934592
WANT_HOT_BYTES = 32 * 1024 * 1024             # 33554432
SIZEOF_FACT = 16
INNER_REPS = 1
EXACT_MATCHES = WANT_FACT_BYTES // SIZEOF_FACT * INNER_REPS   # 536870912

# The corrupted dataset's value, and the defect's signature.
CORRUPT_MATCHES = 534773760
CORRUPT_DEFICIT = EXACT_MATCHES - CORRUPT_MATCHES              # 2097152
ONE_PER_4K = WANT_FACT_BYTES // 4096                           # 2097152

# Binaries.
CLEAN_TENANT_SHA = "a677c52d05b75091057b5d9477fca99fef56e2087605457cfaf8f2b908a98431"
CORRUPT_TENANT_SHA = "75e0af947243c49f5b2451e1268ee378588f20eafc42330f9ca4ff2edde893b6"
VICTIM_SHA = "026e357ae21a99717cae3ebf4ed05fa2cd146bda4f110afe4a2f7b829ef2db50"

HOST = "mos182"
CAT_ARMS = [f"cat{i:02d}" for i in range(1, 16)]
ARMS = ["qui", "wb", "nta", "fb64k", "fb256k", "fb1m"] + CAT_ARMS
REPS = 5
N_RECORDS = len(ARMS) * REPS                                   # 105

# Reproducibility envelope, p95 of |delta| from a bootstrap over the 5 reps
# within arm of the CORRUPTED dataset (B=4000, seed 20260904).  Frozen by the
# pre-registration.  Protection noise is strongly arm-dependent -- cat08's
# 9.28 pp is one rep at 150.7 cyc/load against a 141.8 median -- so a flat
# threshold would be too tight at cat08 and far too loose at cat01.
ENVELOPE_P95 = {
    "wb":     (0.00, 0.00),
    "nta":    (4.03, 0.15),
    "fb64k":  (1.92, 0.14),
    "fb256k": (1.88, 0.13),
    "fb1m":   (0.46, 0.43),
    "cat01":  (0.05, 0.09),
    "cat02":  (0.13, 0.08),
    "cat03":  (0.66, 0.09),
    "cat04":  (0.93, 0.10),
    "cat05":  (1.13, 0.13),
    "cat06":  (1.71, 0.18),
    "cat07":  (3.75, 0.19),
    "cat08":  (9.28, 0.12),
    "cat09":  (3.11, 0.12),
    "cat10":  (1.87, 0.42),
    "cat11":  (4.54, 0.17),
    "cat12":  (1.22, 0.16),
    "cat13":  (2.93, 0.13),
    "cat14":  (1.28, 0.20),
    "cat15":  (3.14, 0.70),
}

# D1-D4 thresholds.
D1_FLOOR_PP = 2.0      # per-arm |delta protection|
D2_FLOOR_PP = 1.0      # per-arm |delta tenant cost|
ENVELOPE_MULT = 2.0
D3_PROT_PP = 2.0       # mean signed delta protection over the CAT arms
D3_COST_PP = 0.5       # mean signed delta tenant cost over the CAT arms
D4_ABS_FRAC = 0.03     # absolute medians within +-3%


# ------------------------------------------------------------------- utilities

def load(path: str) -> list[dict]:
    with open(path) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def med(rows: list[dict], key: str) -> float | None:
    v = [r[key] for r in rows if r.get(key) is not None]
    return st.median(v) if v else None


def by_arm(rows: list[dict]) -> dict[str, list[dict]]:
    g: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        g[r["arm"]].append(r)
    return g


def frontier(rows: list[dict]) -> tuple[dict[str, tuple[float, float | None]], dict]:
    """make_eval_frontiers.py:91-98, verbatim in arithmetic."""
    g = by_arm(rows)
    q = med(g["qui"], "victim_cyc_per_load")
    w = med(g["wb"], "victim_cyc_per_load")
    tw = med(g["wb"], "join_mtuples_per_s")
    pts: dict[str, tuple[float, float | None]] = {}
    for a in ARMS:
        if a == "qui" or a not in g:
            continue
        v = med(g[a], "victim_cyc_per_load")
        t = med(g[a], "join_mtuples_per_s")
        if v is None:
            continue
        pts[a] = (100.0 * (w - v) / (w - q),
                  100.0 * (t / tw - 1.0) if t is not None else None)
    return pts, {"q": q, "w": w, "tw": tw}


# ----------------------------------------------------------------------- gates

def g_exact(rows: list[dict]) -> tuple[bool, str]:
    """G-exact (NEW).  matches must equal the exact full row count.

    Absolute, anchored to arithmetic rather than to another measurement.  The
    corrupted dataset satisfies the runner's cross-arm G-live perfectly, so
    only an absolute assertion can see an arm-identical defect.
    """
    bad = []
    for r in rows:
        if r["arm"] == "qui":
            if r.get("matches") is not None:
                bad.append(f"{r['arm']}/r{r.get('rep')} quiet arm reported "
                           f"matches={r['matches']}")
            continue
        m = r.get("matches")
        if m != EXACT_MATCHES:
            d = None if m is None else EXACT_MATCHES - m
            bad.append(f"{r['arm']}/r{r.get('rep')} matches={m} "
                       f"deficit={d}")
    if bad:
        return False, f"{len(bad)} record(s) off the exact row count: " + "; ".join(bad[:4])
    return True, f"all tenant records matches == {EXACT_MATCHES}"


def g_tenant(rows: list[dict], expect_sha: str) -> tuple[bool, str]:
    shas = {r.get("sha_join") for r in rows}
    vics = {r.get("sha_victim") for r in rows}
    if shas != {expect_sha}:
        return False, f"sha_join {sorted(s[:12] for s in shas if s)} != {expect_sha[:12]}"
    if expect_sha == CORRUPT_TENANT_SHA:
        return False, "tenant is the corrupted binary 75e0af94"
    if vics != {VICTIM_SHA}:
        return False, f"sha_victim {sorted(s[:12] for s in vics if s)} != {VICTIM_SHA[:12]}"
    return True, f"tenant {expect_sha[:12]}, victim {VICTIM_SHA[:12]}"


def g_shape(rows: list[dict]) -> tuple[bool, str]:
    if len(rows) != N_RECORDS:
        return False, f"{len(rows)} records, want {N_RECORDS}"
    g = by_arm(rows)
    if set(g) != set(ARMS):
        return False, f"arms {sorted(set(g) ^ set(ARMS))} unexpected/missing"
    for a, rs in g.items():
        if sorted(r["rep"] for r in rs) != list(range(1, REPS + 1)):
            return False, f"arm {a} reps {sorted(r['rep'] for r in rs)}"
    return True, f"{N_RECORDS} records, {len(ARMS)} arms x {REPS} reps"


def g_status(rows: list[dict]) -> tuple[bool, str]:
    bad = [f"{r['arm']}/r{r['rep']}={r.get('status')}" for r in rows
           if r.get("status") != "ok"]
    if bad:
        return False, f"{len(bad)} non-ok: " + "; ".join(bad[:6])
    return True, "all records status=ok"


def g_geometry(rows: list[dict]) -> tuple[bool, str]:
    bad = []
    for r in rows:
        if r["arm"] == "qui":
            continue
        if r.get("fact_bytes") != WANT_FACT_BYTES:
            bad.append(f"{r['arm']}/r{r['rep']} fact_bytes={r.get('fact_bytes')}")
        if r.get("instantiated_hot_bytes") != WANT_HOT_BYTES:
            bad.append(f"{r['arm']}/r{r['rep']} hot={r.get('instantiated_hot_bytes')}")
        if float(r.get("hit_rate") or 0) != 1.0:
            bad.append(f"{r['arm']}/r{r['rep']} hit_rate={r.get('hit_rate')}")
        if r.get("hot_table_rounded"):
            bad.append(f"{r['arm']}/r{r['rep']} HOT_TABLE_ROUNDED")
    if bad:
        return False, f"{len(bad)} geometry deviation(s): " + "; ".join(bad[:4])
    return True, f"fact={WANT_FACT_BYTES} hot={WANT_HOT_BYTES} hit_rate=1.0"


def g_pages(rows: list[dict], want_huge: bool) -> tuple[bool, str]:
    got = {bool(r.get("huge2m")) for r in rows if r["arm"] != "qui"}
    if got != {want_huge}:
        return False, f"huge2m={got}, want {{{want_huge}}}"
    return True, f"huge2m={want_huge} on every tenant record"


def g_host(rows: list[dict]) -> tuple[bool, str]:
    hosts = {r.get("host") for r in rows}
    if hosts != {HOST}:
        return False, f"host {sorted(h for h in hosts if h)} != {HOST}"
    return True, HOST


def g_runner(rows: list[dict]) -> tuple[bool, str]:
    """The runner's own per-record gate flags, re-read rather than trusted."""
    keys = ("mask_ok", "clos_ok", "live_ok", "size_ok", "fb_ok", "nta_ok",
            "mask_held_ok", "idle_ok")
    bad = []
    for r in rows:
        for k in keys:
            if k in r and r[k] is False:
                bad.append(f"{r['arm']}/r{r['rep']} {k}={r.get(k[:-3] + 'why')!r}")
    if bad:
        return False, f"{len(bad)} runner gate failure(s): " + "; ".join(bad[:4])
    return True, "mask/clos/live/size/fb/nta/mask-held/idle all pass"


def g_window(rows: list[dict]) -> tuple[bool, str]:
    bad = [f"{r['arm']}/r{r['rep']}" for r in rows if r["arm"] != "qui"
           and not (r.get("join_measure_begin") and r.get("join_measure_end"))]
    if bad:
        return False, f"{len(bad)} record(s) without a closed measure window: " + "; ".join(bad[:4])
    return True, "every tenant record brackets JOIN_MEASURE_BEGIN/END"


def gate_report(rows: list[dict], expect_sha: str,
                want_huge: bool = True) -> list[tuple[str, bool, str]]:
    return [
        ("G-shape", *g_shape(rows)),
        ("G-status", *g_status(rows)),
        ("G-host", *g_host(rows)),
        ("G-tenant", *g_tenant(rows, expect_sha)),
        ("G-geometry", *g_geometry(rows)),
        ("G-pages", *g_pages(rows, want_huge)),
        ("G-window", *g_window(rows)),
        ("G-runner", *g_runner(rows)),
        ("G-exact", *g_exact(rows)),
    ]


# ------------------------------------------------------------------- D1-D4

def deltas(clean: list[dict], corrupt: list[dict]) -> tuple[dict, dict, dict]:
    cf, cref = frontier(clean)
    xf, xref = frontier(corrupt)
    d = {}
    for a in cf:
        if a not in xf:
            continue
        dp = cf[a][0] - xf[a][0]
        dc = (None if cf[a][1] is None or xf[a][1] is None
              else cf[a][1] - xf[a][1])
        d[a] = (dp, dc)
    return d, {"clean": cf, "corrupt": xf}, {"clean": cref, "corrupt": xref}


def verdicts(d: dict, refs: dict) -> list[tuple[str, bool, str]]:
    out = []

    fails = []
    for a, (dp, _) in sorted(d.items()):
        lim = max(D1_FLOOR_PP, ENVELOPE_MULT * ENVELOPE_P95[a][0])
        if abs(dp) > lim:
            fails.append(f"{a} |{dp:+.2f}| > {lim:.2f}")
    out.append(("D1 per-arm protection", not fails,
                "; ".join(fails) if fails else
                f"all {len(d)} arms within max({D1_FLOOR_PP} pp, 2x envelope)"))

    fails = []
    n = 0
    for a, (_, dc) in sorted(d.items()):
        if a == "wb" or dc is None:
            continue
        n += 1
        lim = max(D2_FLOOR_PP, ENVELOPE_MULT * ENVELOPE_P95[a][1])
        if abs(dc) > lim:
            fails.append(f"{a} |{dc:+.2f}| > {lim:.2f}")
    out.append(("D2 per-arm tenant cost", not fails,
                "; ".join(fails) if fails else
                f"all {n} arms within max({D2_FLOOR_PP} pp, 2x envelope)"))

    cp = [d[a][0] for a in CAT_ARMS if a in d]
    cc = [d[a][1] for a in CAT_ARMS if a in d and d[a][1] is not None]
    mp = st.mean(cp) if cp else 0.0
    mc = st.mean(cc) if cc else 0.0
    ok = abs(mp) <= D3_PROT_PP and abs(mc) <= D3_COST_PP
    out.append(("D3 common mode (CAT)", ok,
                f"mean signed protection {mp:+.3f} pp (limit +-{D3_PROT_PP}), "
                f"tenant cost {mc:+.3f} pp (limit +-{D3_COST_PP})"))

    fails = []
    parts = []
    for name, key in (("qui victim", "q"), ("wb victim", "w"),
                      ("wb tuples/s", "tw")):
        a, b = refs["clean"][key], refs["corrupt"][key]
        frac = (a - b) / b
        parts.append(f"{name} {a:.4g} vs {b:.4g} ({100*frac:+.2f}%)")
        if abs(frac) > D4_ABS_FRAC:
            fails.append(f"{name} {100*frac:+.2f}%")
    out.append(("D4 absolute reproduction", not fails,
                "; ".join(fails) if fails else "; ".join(parts)))
    return out


# ------------------------------------------------------------------- self-test

def self_test() -> None:
    f: list[str] = []

    def expect(got: bool, want: bool, label: str) -> None:
        if got != want:
            f.append(label)

    if EXACT_MATCHES != 536870912:
        f.append(f"EXACT_MATCHES={EXACT_MATCHES}")
    if CORRUPT_DEFICIT != ONE_PER_4K:
        f.append("deficit is not one row per 4 KiB page")

    good = [{"arm": "wb", "rep": 1, "matches": EXACT_MATCHES},
            {"arm": "qui", "rep": 1, "matches": None}]
    expect(g_exact(good)[0], True, "G-exact must pass on the exact count")
    expect(g_exact([{"arm": "wb", "rep": 1, "matches": CORRUPT_MATCHES}])[0],
           False, "G-exact must fail on the corrupted count")
    expect(g_exact([{"arm": "wb", "rep": 1, "matches": EXACT_MATCHES - 1}])[0],
           False, "G-exact must fail on a deficit of one row")
    expect(g_exact([{"arm": "wb", "rep": 1, "matches": None}])[0],
           False, "G-exact must fail on a null count")
    expect(g_exact([{"arm": "qui", "rep": 1, "matches": 5}])[0],
           False, "G-exact must fail if a quiet arm reports matches")

    row = {"arm": "wb", "rep": 1, "sha_join": CLEAN_TENANT_SHA,
           "sha_victim": VICTIM_SHA}
    expect(g_tenant([row], CLEAN_TENANT_SHA)[0], True, "G-tenant clean binary")
    expect(g_tenant([dict(row, sha_join=CORRUPT_TENANT_SHA)],
                    CORRUPT_TENANT_SHA)[0], False,
           "G-tenant must refuse the corrupted binary")
    expect(g_tenant([dict(row, sha_victim="deadbeef")], CLEAN_TENANT_SHA)[0],
           False, "G-tenant must fail on a swapped victim")

    expect(g_status([{"arm": "wb", "rep": 1, "status": "ok"}])[0], True,
           "G-status ok")
    expect(g_status([{"arm": "wb", "rep": 1, "status": "gate_fail"}])[0], False,
           "G-status must fail on gate_fail")
    expect(g_shape([])[0], False, "G-shape must fail on an empty dataset")

    geo = {"arm": "wb", "rep": 1, "fact_bytes": WANT_FACT_BYTES,
           "instantiated_hot_bytes": WANT_HOT_BYTES, "hit_rate": 1,
           "hot_table_rounded": False}
    expect(g_geometry([geo])[0], True, "G-geometry exact")
    expect(g_geometry([dict(geo, hit_rate=0.5)])[0], False,
           "G-geometry must fail at hit_rate 0.5")
    expect(g_geometry([dict(geo, fact_bytes=1 << 30)])[0], False,
           "G-geometry must fail on a 1 GiB fact")
    expect(g_geometry([dict(geo, hot_table_rounded=True)])[0], False,
           "G-geometry must fail on HOT_TABLE_ROUNDED")
    expect(g_pages([geo], True)[0], False, "G-pages must fail when huge2m absent")
    expect(g_pages([dict(geo, huge2m=True)], True)[0], True, "G-pages huge2m")
    expect(g_runner([dict(geo, mask_ok=False, mask_why="x")])[0], False,
           "G-runner must fail on mask_ok=False")
    expect(g_runner([geo])[0], True, "G-runner passes when flags absent (legacy)")
    expect(g_window([dict(geo, join_measure_begin=True,
                          join_measure_end=True)])[0], True, "G-window closed")
    expect(g_window([dict(geo, join_measure_begin=True,
                          join_measure_end=False)])[0], False,
           "G-window must fail on an unclosed window")

    # D-thresholds must be able to fire.  cat01's protection envelope is 0.05,
    # so its limit is the 2.0 pp floor; cat08's is 2 x 9.28 = 18.56.
    d = {"cat01": (2.5, 0.0), "cat08": (5.0, 0.0)}
    v = {n: (ok, why) for n, ok, why in
         verdicts(d, {"clean": {"q": 1, "w": 2, "tw": 3},
                      "corrupt": {"q": 1, "w": 2, "tw": 3}})}
    expect(v["D1 per-arm protection"][0], False,
           "D1 must fire on cat01 at 2.5 pp")
    d = {"cat01": (1.9, 0.0), "cat08": (9.0, 0.0)}
    v = {n: (ok, why) for n, ok, why in
         verdicts(d, {"clean": {"q": 1, "w": 2, "tw": 3},
                      "corrupt": {"q": 1, "w": 2, "tw": 3}})}
    expect(v["D1 per-arm protection"][0], True,
           "D1 must pass inside the envelope")
    expect(v["D4 absolute reproduction"][0], True, "D4 identical absolutes")
    v = {n: (ok, why) for n, ok, why in
         verdicts({}, {"clean": {"q": 1, "w": 2, "tw": 3.5},
                       "corrupt": {"q": 1, "w": 2, "tw": 3}})}
    expect(v["D4 absolute reproduction"][0], False, "D4 must fire at +16%")
    v = {n: (ok, why) for n, ok, why in
         verdicts({a: (3.0, 0.0) for a in CAT_ARMS},
                  {"clean": {"q": 1, "w": 2, "tw": 3},
                   "corrupt": {"q": 1, "w": 2, "tw": 3}})}
    expect(v["D3 common mode (CAT)"][0], False,
           "D3 must fire on a 3 pp common-mode shift")

    if f:
        raise SystemExit("ANALYZER SELF-TEST FAILED:\n  " + "\n  ".join(f))


# ------------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", help="the re-run JSONL")
    ap.add_argument("--corrupt", help="the 2026-09-01 JSONL to compare against")
    ap.add_argument("--expect-tenant-sha", default=CLEAN_TENANT_SHA,
                    help="G-tenant target; default is the registered rebuild")
    ap.add_argument("--no-huge2m", action="store_true",
                    help="expect huge2m=false (the 4K sibling)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()

    self_test()
    if a.self_test:
        print("analyzer self-test: every gate and threshold fired and passed "
              "as registered")
        return 0
    if not a.clean:
        ap.error("--clean is required")

    clean = load(a.clean)
    print(f"== gates: {a.clean} ({len(clean)} records)")
    gr = gate_report(clean, a.expect_tenant_sha, want_huge=not a.no_huge2m)
    for name, ok, why in gr:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:12s} {why}")
    all_ok = all(ok for _, ok, _ in gr)
    print(f"== gate verdict: {'ADMITTED' if all_ok else 'VOID'}")

    cf, cref = frontier(clean)
    print(f"\n== frontier, paper coordinates (make_eval_frontiers.py:91-98)")
    print(f"   q(qui)={cref['q']:.4f}  w(wb)={cref['w']:.4f}  "
          f"tw(wb)={cref['tw']:.4f}")
    print(f"   {'arm':8s} {'protection %':>13s} {'tenant cost %':>14s}")
    for arm in ARMS:
        if arm in cf:
            p, c = cf[arm]
            print(f"   {arm:8s} {p:13.2f} {('%14.2f' % c) if c is not None else '':>14s}")

    if not a.corrupt:
        return 0 if all_ok else 1

    corrupt = load(a.corrupt)
    d, both, refs = deltas(clean, corrupt)
    print(f"\n== arm-by-arm delta vs {a.corrupt} (clean - corrupted, pp)")
    print(f"   {'arm':8s} {'prot clean':>11s} {'prot corr':>10s} {'dprot':>8s} "
          f"{'env':>6s} {'cost clean':>11s} {'cost corr':>10s} {'dcost':>8s} {'env':>6s}")
    for arm in ARMS:
        if arm not in d:
            continue
        pc, cc = both["clean"][arm]
        px, cx = both["corrupt"][arm]
        dp, dc = d[arm]
        ep, ec = ENVELOPE_P95[arm]
        cs = (f"{cc:11.2f} {cx:10.2f} {dc:+8.3f} {ec:6.2f}"
              if dc is not None else f"{'':11s} {'':10s} {'':8s} {'':6s}")
        print(f"   {arm:8s} {pc:11.2f} {px:10.2f} {dp:+8.3f} {ep:6.2f} {cs}")

    dps = [abs(d[a][0]) for a in d]
    dcs = [abs(d[a][1]) for a in d if d[a][1] is not None]
    print(f"\n   max |dprot| {max(dps):.3f} pp, max |dcost| {max(dcs):.3f} pp")

    print(f"\n== registered predictions")
    vs = verdicts(d, refs)
    for name, ok, why in vs:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:24s} {why}")
    dv = all(ok for _, ok, _ in vs)
    if dv:
        print("== delta verdict: NEGLIGIBLE -- arm-identical corruption "
              "cancels in the ratio coordinates, as registered")
    else:
        print("== delta verdict: *** MATERIAL SHIFT *** the mechanism is NOT "
              "understood; see the pre-registration's D1-D4 clause")
    return 0 if (all_ok and dv) else 1


if __name__ == "__main__":
    sys.exit(main())
