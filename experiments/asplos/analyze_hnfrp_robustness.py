#!/usr/bin/env python3
"""Analyzer for the HNF_RP robustness run.

Committed BEFORE the data lands, per the W1 lesson that every campaign gets a
committed artifact rather than a shell one-liner. Every threshold below is the
pre-registered one from HNFRP_ROBUSTNESS_PREREG_2026-08-28.md (e626e15) and is
a module constant, not an argument -- editing one after seeing data would be
visible in git.

Usage: python3 analyze_hnfrp_robustness.py     (reads /tmp/rp_{arm}_{rp}_s{n})
"""
import glob, math, os, re, statistics as st, sys

ITERS = 3_000_000
ARMS = ("qui", "wb", "h2")
POLICIES = ("treeplru", "lru")

# --- pre-registered thresholds (HNFRP_ROBUSTNESS_PREREG_2026-08-28.md) --------
ROBUST_PP   = 2.0    # |dR| <= 2 pp  -> bound insensitive to the policy bias
MATERIAL_PP = 10.0   # |dR| > 10 pp  -> every gem5 figure re-runs; escalate
# instrument check: archived W1 means, band = max(4 sd, 0.5% of mean)
ARCHIVED = {"qui": (33.8814, 0.0140), "wb": (46.3800, 0.0460), "h2": (35.0247, 0.0074)}
EXPECT_RP = {"treeplru": "TreePLRURP", "lru": "LRURP"}


def band(mean, sd):
    return max(4 * sd, 0.005 * mean)


def cyc_per_access(d):
    p = os.path.join(d, "stats.txt")
    if not (os.path.exists(p) and os.path.getsize(p)):
        return None
    with open(p) as f:
        for line in f:
            if line.startswith("system.cpu0.numCycles "):
                return int(line.split()[1]) / ITERS
    return None


def arm_identity(d):
    """S5.1: read the arm's identity from its own artifact, not the launcher."""
    ci = os.path.join(d, "config.ini")
    if not os.path.exists(ci):
        return None, None
    c = open(ci).read()
    m = re.search(r"\[system\.ruby\.hnf\.cntrl\.cache\.replacement_policy\]\n"
                  r"((?:[^\[]*\n)*)", c)
    rp = re.search(r"^type=(\S+)", m.group(1), re.M).group(1) if m else None
    cmds = re.findall(r"^cmd=(.*)$", c, re.M)
    return rp, cmds


def alive(d):
    """Liveness assertion 1: the run must have reached the exit instruction."""
    log = d + ".log"
    if not os.path.exists(log):
        return False, "no log"
    txt = open(log, errors="replace").read()
    if "Exiting @ tick" not in txt:
        return False, "no 'Exiting @ tick' -- truncated or died"
    m = re.search(r"^DONE_(\d+) ", txt, re.M)
    if m and m.group(1) != "0":
        return False, f"gem5 exit code {m.group(1)}"
    return True, "ok"


def main():
    data, dead, ident = {}, [], []
    for rp in POLICIES:
        for arm in ARMS:
            vals = {}
            for d in sorted(glob.glob(f"/tmp/rp_{arm}_{rp}_s*")):
                if d.endswith(".log"):
                    continue
                ok, why = alive(d)
                if not ok:
                    dead.append(f"{os.path.basename(d)}: {why}")
                    continue
                got_rp, cmds = arm_identity(d)
                if got_rp != EXPECT_RP[rp]:
                    ident.append(f"{os.path.basename(d)}: HNF policy is {got_rp}, "
                                 f"expected {EXPECT_RP[rp]}")
                    continue
                declared = any("stream" in c for c in (cmds or []))
                if (arm == "h2") != declared:
                    ident.append(f"{os.path.basename(d)}: arm={arm} but "
                                 f"declaration={'present' if declared else 'absent'}")
                    continue
                v = cyc_per_access(d)
                if v is None:
                    dead.append(f"{os.path.basename(d)}: no numCycles")
                    continue
                vals[os.path.basename(d)] = v
            data[(rp, arm)] = vals

    print("=" * 74)
    print("HNF_RP ROBUSTNESS -- prereg HNFRP_ROBUSTNESS_PREREG_2026-08-28.md")
    print("=" * 74)
    if dead:
        print("\nDEAD OR UNUSABLE RUNS (reported, not silently dropped):")
        for x in dead:
            print("  " + x)
    if ident:
        print("\nARM-IDENTITY FAILURES (S5.1 -- read from the artifact):")
        for x in ident:
            print("  " + x)

    print("\ncyc/access by policy and arm")
    means = {}
    for rp in POLICIES:
        for arm in ARMS:
            v = list(data[(rp, arm)].values())
            if not v:
                print(f"  {rp:9s} {arm:4s}: NO USABLE RUNS")
                continue
            means[(rp, arm)] = st.mean(v)
            sd = st.stdev(v) if len(v) > 1 else float("nan")
            print(f"  {rp:9s} {arm:4s}: n={len(v)} mean={st.mean(v):8.4f} "
                  f"sd={sd:.4f} " + " ".join(f"{k.split('_')[-1]}={x:.4f}"
                                             for k, x in data[(rp, arm)].items()))

    # ---- instrument check on the treeplru re-run --------------------------
    print("\nINSTRUMENT CHECK (treeplru re-run vs archived W1 means)")
    drift = []
    for arm in ARMS:
        if ("treeplru", arm) not in means:
            print(f"  {arm}: no data -- cannot check"); drift.append(arm); continue
        am, asd = ARCHIVED[arm]
        b = band(am, asd)
        got = means[("treeplru", arm)]
        ok = abs(got - am) <= b
        print(f"  {arm:4s}: got {got:8.4f}  archived {am:8.4f}  "
              f"window [{am-b:.3f}, {am+b:.3f}]  -> {'PASS' if ok else 'MISS'}")
        if not ok:
            drift.append(arm)
    if drift:
        print("  ** APPARATUS DRIFT in: " + ", ".join(drift))
        print("  ** Per the registered action-on-miss, this VOIDS the claim that")
        print("  ** this batch validates the archived figures. It does NOT void dR,")
        print("  ** which is internal to this batch. Reported as a finding.")
    else:
        print("  all three reproduce -- the archived W1 figures are validated.")

    # ---- primary test ----------------------------------------------------
    print("\nPRIMARY TEST")
    R = {}
    for rp in POLICIES:
        if not all((rp, a) in means for a in ARMS):
            print(f"  {rp}: incomplete -- cannot compute R"); continue
        tw = means[(rp, "wb")] / means[(rp, "qui")]
        th = means[(rp, "h2")] / means[(rp, "qui")]
        R[rp] = (tw - th) / (tw - 1.0)
        print(f"  {rp:9s} tax_wb={tw:.4f}  tax_h2={th:.4f}  R={100*R[rp]:.2f}%")
    if len(R) != 2:
        print("\nCANNOT DECIDE -- both policies needed.")
        return 1
    dR = 100 * (R["lru"] - R["treeplru"])
    print(f"\n  dR = R_lru - R_treeplru = {dR:+.2f} percentage points")
    print(f"  (registered: |dR| <= {ROBUST_PP} ROBUST; "
          f"{ROBUST_PP}-{MATERIAL_PP} SENSITIVE; > {MATERIAL_PP} MATERIAL)")
    a = abs(dR)
    if a <= ROBUST_PP:
        verdict = ("ROBUST -- the H2 bound does not depend on the TreePLRU bias. "
                   "Existing gem5 figures stand; report both values in the appendix.")
    elif a <= MATERIAL_PP:
        verdict = ("SENSITIVE -- HNF_RP=lru becomes the reporting configuration; "
                   "the qualitative claim survives, magnitudes must be re-run.")
    else:
        verdict = ("MATERIAL -- every gem5 figure must be re-measured under "
                   "HNF_RP=lru before the paper cites any of them. ESCALATE.")
    print(f"\n  VERDICT: {verdict}")
    print("\n  No direction was pre-registered (two opposing mechanisms); the sign")
    print(f"  observed is {'positive' if dR > 0 else 'negative'}, reported as an observation, not a confirmation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
