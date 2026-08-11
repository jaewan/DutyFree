#!/usr/bin/env python3
"""Adjudicate GATE1_LOCALDRAM_COLUMN_PREREGISTRATION.md from the 12 arms.

Methodology is parse_p0.py's, unchanged: the victim is cpu0, its cost is
`system.cpu0.numCycles / ITERS`, and a cell's tax is that cell's own
`wb` cyc/iter divided by its own matched `alone` cyc/iter -- same WSS,
same placement, same config.  Ratios are never taken across configs.

ITERS is read from each arm's DONE_ line rather than assumed, so an arm
that silently ran at the b4run default instead of 3e6 shows up as a
mismatch rather than as a wrong tax.

Placement is reported from `mem_pool_observed` (the run's own controller
counters), not from `mem_pool_policy` (the manifesting shell's env).
When those two disagree the counters are right.
"""
import json, os, re, sys

WSSES = [1280, 2650, 5120]
PLACES = ["def", "loc"]
TAGS = ["alone", "wb"]

# What the paper prints, for the reconciliation column.
PUBLISHED = {1280: 1.79, 2650: 2.57, 5120: 2.82}
# The Gate 1 re-run that motivated this exercise (CXL aggressor, 53%).
CORUN_V2_53 = 1.2189


def field(lines, pat):
    rx = re.compile(pat)
    out = []
    for ln in lines:
        if rx.search(ln):
            p = ln.split()
            try:
                out.append((p[0], float(p[1])))
            except (IndexError, ValueError):
                pass
    return out


def load(name):
    d = f"/tmp/{name}"
    sp = os.path.join(d, "stats.txt")
    lg = f"/tmp/{name}.log"
    r = {"name": name, "ok": False}
    if os.path.exists(lg):
        txt = open(lg, errors="replace").read()
        m = re.search(r"DONE_(\d+)", txt)
        r["done_rc"] = int(m.group(1)) if m else None
        m = re.search(r"MANIFEST_(\d+)", txt)
        r["manifest_rc"] = int(m.group(1)) if m else None
        m = re.search(r"ITERS=(\d+)", txt)
        r["iters"] = int(m.group(1)) if m else None
    if not (os.path.exists(sp) and os.path.getsize(sp) > 0):
        return r
    stats = open(sp).read().splitlines()
    nc = field(stats, r"^system\.cpu0?0?\.numCycles\b")
    r["vcyc"] = nc[0][1] if nc else None
    if r["vcyc"] and r.get("iters"):
        r["cyciter"] = r["vcyc"] / r["iters"]
        r["ok"] = True
    ss = field(stats, r"^simSeconds\b")
    r["simSec"] = ss[0][1] if ss else None
    # per-controller traffic, the placement ground truth
    traf = {}
    for n, v in field(stats, r"^system\.mem_ctrls(\d+)\.bytes(?:Read|Written)::total\b"):
        i = int(re.search(r"mem_ctrls(\d+)", n).group(1))
        traf[i] = traf.get(i, 0.0) + v
    r["traffic"] = traf
    tot = sum(traf.values())
    r["pct_ctrl0"] = (100.0 * traf.get(0, 0.0) / tot) if tot else None
    mp = os.path.join(d, "manifest.json")
    if os.path.exists(mp):
        try:
            prov = json.load(open(mp)).get("_provenance", {})
            r["policy"] = prov.get("mem_pool_policy")
            obs = prov.get("mem_pool_observed") or {}
            r["observed"] = obs.get("derived_placement")
            r["sha"] = prov.get("commit_sha", "")[:10]
            r["dirty"] = prov.get("dirty_tree")
        except (json.JSONDecodeError, OSError) as e:
            r["manifest_error"] = str(e)
    return r


def main():
    arms = {}
    for w in WSSES:
        for p in PLACES:
            for t in TAGS:
                n = f"ld_{w}_{p}_{t}"
                arms[n] = load(n)

    print("== arm health ==")
    print(f"{'arm':22} {'rc':>3} {'mrc':>4} {'iters':>8} {'cyc/iter':>9} {'%ctrl0':>7}  placement (observed)")
    for n, r in arms.items():
        print(f"{n:22} {str(r.get('done_rc')):>3} {str(r.get('manifest_rc')):>4} "
              f"{str(r.get('iters')):>8} {r.get('cyciter') or float('nan'):9.2f} "
              f"{r.get('pct_ctrl0') if r.get('pct_ctrl0') is not None else float('nan'):7.2f}  "
              f"{r.get('observed')}")

    bad = [n for n, r in arms.items() if not r["ok"] or r.get("done_rc") != 0]
    if bad:
        print(f"\n!! {len(bad)} arm(s) incomplete or failed: {', '.join(bad)}")
    iterset = {r.get("iters") for r in arms.values() if r.get("iters")}
    if len(iterset) > 1:
        print(f"!! ITERS not uniform across arms: {iterset}")
    shas = {r.get("sha") for r in arms.values() if r.get("sha")}
    dirty = {r.get("dirty") for r in arms.values() if "dirty" in r}
    print(f"\nproducing commit(s): {shas or 'unknown'}   dirty_tree: {dirty or 'unknown'}")

    print("\n== tax: each cell's own wb / its own matched alone ==")
    print(f"{'WSS (%LLC)':14} {'placement':10} {'alone c/i':>10} {'wb c/i':>10} {'tax':>7} {'published':>10}")
    tax = {}
    for w in WSSES:
        pct = round(100.0 * w / 5120)
        for p in PLACES:
            a = arms[f"ld_{w}_{p}_alone"]
            b = arms[f"ld_{w}_{p}_wb"]
            if a.get("cyciter") and b.get("cyciter"):
                t = b["cyciter"] / a["cyciter"]
                tax[(w, p)] = t
            else:
                t = None
            lbl = "local DRAM" if p == "loc" else "CXL (dflt)"
            pubs = f"{PUBLISHED[w]:.2f}x" if p == "loc" else "--"
            print(f"{f'{w} ({pct}%)':14} {lbl:10} "
                  f"{a.get('cyciter') or float('nan'):10.2f} {b.get('cyciter') or float('nan'):10.2f} "
                  f"{t if t else float('nan'):7.3f} {pubs:>10}")

    print("\n== pre-registered predictions ==")
    t53l = tax.get((2650, "loc"))
    if t53l:
        near_pub = abs(t53l - PUBLISHED[2650]) / PUBLISHED[2650] <= 0.15
        above = t53l > CORUN_V2_53 * 1.15
        verdict = ("HOLDS" if (above and near_pub) else
                   "PARTIAL (rises but not to 2.57x)" if above else "FAILS")
        print(f"P1  53% local-DRAM tax = {t53l:.3f}x  "
              f"(vs re-run CXL {CORUN_V2_53}x, published {PUBLISHED[2650]}x)  -> {verdict}")
    else:
        print("P1  pending -- 2650/loc pair incomplete")

    t25 = [tax.get((1280, p)) for p in PLACES]
    if all(t25):
        near1 = all(abs(t - 1.0) <= 0.05 for t in t25)
        print(f"P2  25% tax = {t25[0]:.3f}x (CXL) / {t25[1]:.3f}x (local), published "
              f"{PUBLISHED[1280]}x  -> {'HOLDS (near 1.00x -- row is hot-set<L2, withdraw)' if near1 else 'FAILS (row carries a real tax)'}")
    else:
        print("P2  pending -- 1280 pair(s) incomplete")

    print("P3  HNF_SF_FINITE=0 for every arm by construction; back-inval counters below "
          "should be ~0. A nonzero count is the surprise P3 exists to flag.")
    # Count SnpCleanInvalid *transactions*, i.e. the `::samples` field of each
    # cache's inTransLatHist.  Matching the bare name instead sums bucket_size,
    # gmean, mean, stdev and total in with the counts -- and gem5 prints `nan`
    # for the stdev of a single-sample histogram, which poisons the whole sum.
    for w in WSSES:
        for p in PLACES:
            r = arms[f"ld_{w}_{p}_wb"]
            sp = f"/tmp/{r['name']}/stats.txt"
            if os.path.exists(sp) and os.path.getsize(sp) > 0:
                per = field(open(sp).read().splitlines(),
                            r"\.inTransLatHist\.SnpCleanInvalid::samples\b")
                tot = sum(v for _, v in per)
                where = ", ".join(
                    f"{n.split('.inTransLatHist')[0].replace('system.', '')}={v:.0f}"
                    for n, v in per if v)
                print(f"    {r['name']:22} SnpCleanInvalid transactions={tot:.0f}  [{where}]")

    print("\n== placement cross-check (deliverable 4) ==")
    for n, r in arms.items():
        want0 = 100.0 if n.endswith("_alone") or "_loc_" in n else None
        got = r.get("pct_ctrl0")
        note = ""
        if "_loc_" in n and got is not None and got < 99.9:
            note = "  <-- ALL_LOCAL arm has traffic off ctrl0"
        if "_def_" in n and n.endswith("_wb") and got is not None and got > 99.9:
            note = "  <-- default arm should have CXL traffic"
        print(f"{n:22} pct_on_ctrl0={got if got is not None else float('nan'):7.2f}  "
              f"bytes={ {f'c{k}': int(v) for k, v in sorted(r.get('traffic', {}).items())} }{note}")
        # `alone` arms cannot distinguish the two policies: the tag runs
        # victim+dummy, the dummy issues no memory traffic, so ctrl1 is silent
        # under either placement.  Only the loaded arms are diagnostic.
        if n.endswith("_wb") and r.get("policy") and r.get("observed") and (
                ("ALL_LOCAL" in r["policy"]) != ("mem_ctrls0 --" in (r["observed"] or ""))):
            print(f"    !! policy/observed disagree: policy={r['policy']!r} observed={r['observed']!r}"
                  "  (counters win)")


if __name__ == "__main__":
    sys.exit(main())
