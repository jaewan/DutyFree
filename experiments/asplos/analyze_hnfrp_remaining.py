#!/usr/bin/env python3
"""Analyzer for the remaining tab:h3sf cells under both LLC policies.

Committed BEFORE the data lands. Every threshold is the pre-registered one from
HNFRP_REMAINING_CELLS_PREREG_2026-08-28.md (5036cec), held as a module constant.

Reads /tmp/rq_{arm}_{sf}_{rp}_s{n} for the new cells, and reuses the previous
batch's /tmp/rp_{arm}_{rp}_s{n} for qui_inf / wb_inf / h2_inf as the prereg
states.
"""
import glob, math, os, re, statistics as st, sys

ITERS = 3_000_000
# --- pre-registered thresholds -----------------------------------------------
Q1_SIGN_LIMIT = -0.05    # I_lru below this => "H2 is inert under finite SF" is policy-dependent
Q2_ROBUST, Q2_MATERIAL = 2.0, 10.0     # pp on dR3
Q3_ROBUST, Q3_MATERIAL = 1.0, 3.0      # pp on dC3
EXPECT_RP = {"treeplru": "TreePLRURP", "lru": "LRURP"}
# archived means for the instrument check, and the registered bit-identity call
ARCHIVED = {
    ("qui", "fin"): (33.8814, 0.0140, "absolute"), ("wb", "fin"): (84.7541, 0.0692, "absolute"),
    ("h2", "fin"): (85.0959, 0.0173, "absolute"), ("h3", "fin"): (35.9474, 0.0121, "absolute"),
    ("h3", "inf"): (36.2328, 0.0117, "relative"),
}
ARCHIVED_SEEDS = {
    ("qui", "fin"): [33.8654, 33.8912, 33.8877], ("wb", "fin"): [84.8334, 84.7273, 84.7017],
    ("h2", "fin"): [85.0787, 85.0959, 85.1132], ("h3", "fin"): [35.9582, 35.9340, 35.9501],
    ("h3", "inf"): [36.2391, 36.2401, 36.2193],
}


def cyc(d):
    p = os.path.join(d, "stats.txt")
    if not (os.path.exists(p) and os.path.getsize(p)):
        return None
    with open(p) as f:
        for line in f:
            if line.startswith("system.cpu0.numCycles "):
                return int(line.split()[1]) / ITERS
    return None


def cpu1_cycles(d):
    p = os.path.join(d, "stats.txt")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        for line in f:
            if line.startswith("system.cpu1.numCycles "):
                return int(line.split()[1])
    return None


def alive(d):
    log = d + ".log"
    if not os.path.exists(log):
        return False, "no log"
    t = open(log, errors="replace").read()
    if "Exiting @ tick" not in t:
        return False, "no 'Exiting @ tick' -- truncated or died"
    m = re.search(r"^DONE_(\d+) ", t, re.M)
    if m and m.group(1) != "0":
        return False, f"gem5 exit code {m.group(1)}"
    return True, "ok"


def identity(d):
    """S5.1: policy, declaration, H3 and SF geometry from the run's own artifact."""
    ci = os.path.join(d, "config.ini")
    if not os.path.exists(ci):
        return {}
    c = open(ci).read()
    m = re.search(r"\[system\.ruby\.hnf\.cntrl\.cache\.replacement_policy\]\n"
                  r"((?:[^\[]*\n)*)", c)
    rp = re.search(r"^type=(\S+)", m.group(1), re.M).group(1) if m else None
    cmds = re.findall(r"^cmd=(.*)$", c, re.M)
    return {"rp": rp, "declared": any("stream" in x for x in cmds),
            "abs_paths": all(x.startswith("/") for x in cmds) if cmds else None}


def collect(pattern, rp, expect_declared, arm, sf, problems):
    out = {}
    for d in sorted(glob.glob(pattern)):
        if d.endswith(".log"):
            continue
        ok, why = alive(d)
        if not ok:
            problems.append(f"{os.path.basename(d)}: {why}"); continue
        idt = identity(d)
        if idt.get("rp") != EXPECT_RP[rp]:
            problems.append(f"{os.path.basename(d)}: policy {idt.get('rp')}, "
                            f"expected {EXPECT_RP[rp]}"); continue
        if idt.get("declared") != expect_declared:
            problems.append(f"{os.path.basename(d)}: declaration "
                            f"{'present' if idt.get('declared') else 'absent'}, "
                            f"arm {arm}"); continue
        if arm == "qui":
            c1 = cpu1_cycles(d)
            if c1:
                problems.append(f"{os.path.basename(d)}: cpu1.numCycles={c1} != 0 "
                                f"-- denominator is not quiescent")
                continue
        v = cyc(d)
        if v is None:
            problems.append(f"{os.path.basename(d)}: no numCycles"); continue
        out[os.path.basename(d)] = v
    return out


def main():
    problems = []
    m = {}
    # new cells
    for sf in ("inf", "fin"):
        for arm in ("qui", "wb", "h2", "h3"):
            if sf == "inf" and arm != "h3":
                continue
            for rp in ("treeplru", "lru"):
                v = collect(f"/tmp/rq_{arm}_{sf}_{rp}_s*", rp, arm in ("h2", "h3"),
                            arm, sf, problems)
                if v:
                    m[(rp, sf, arm)] = v
    # reused from the previous batch
    for arm in ("qui", "wb", "h2"):
        for rp in ("treeplru", "lru"):
            v = collect(f"/tmp/rp_{arm}_{rp}_s*", rp, arm == "h2", arm, "inf", problems)
            if v:
                m[(rp, "inf", arm)] = v

    print("=" * 76)
    print("REMAINING tab:h3sf CELLS -- prereg HNFRP_REMAINING_CELLS_PREREG_2026-08-28.md")
    print("=" * 76)
    if problems:
        print("\nPROBLEM RUNS (reported, not silently dropped):")
        for p in problems:
            print("  " + p)

    print("\ncyc/access")
    mean = {}
    for rp in ("treeplru", "lru"):
        for sf in ("inf", "fin"):
            for arm in ("qui", "wb", "h2", "h3"):
                k = (rp, sf, arm)
                if k not in m:
                    continue
                v = list(m[k].values())
                mean[k] = st.mean(v)
                src = "reused" if (sf == "inf" and arm != "h3") else "new"
                sd = st.stdev(v) if len(v) > 1 else float("nan")
                print(f"  {rp:9s} {sf} {arm:4s}: n={len(v)} mean={st.mean(v):9.4f} "
                      f"sd={sd:.4f} [{src}]")

    # ---- instrument check: per-arm bit-identity prediction ----------------
    print("\nINSTRUMENT CHECK -- registered per-arm bit-identity prediction")
    for (arm, sf), (am, asd, conv) in ARCHIVED.items():
        k = ("treeplru", sf, arm)
        if k not in m:
            print(f"  {arm}_{sf}: no data"); continue
        got_seeds = [m[k][x] for x in sorted(m[k])]
        predicted = (conv == "absolute")   # runner uses absolute paths
        b = max(4 * asd, 0.005 * am)
        inband = abs(mean[k] - am) <= b
        if len(got_seeds) != 3:
            # Bit-identity is a per-seed claim over the full triple. With fewer
            # seeds the mean legitimately differs from a 3-seed archived mean, and
            # calling that a falsified prediction is a false alarm on partial data
            # -- the same defect class as a criterion a crashed run can satisfy.
            print(f"  {arm}_{sf}: only {len(got_seeds)}/3 seeds -- bit-identity "
                  f"NOT EVALUABLE yet (mean {mean[k]:.4f} vs archived {am:.4f}, "
                  f"{'in band' if inband else 'OUT OF BAND'})")
            continue
        ident = all(abs(a - b2) < 5e-5
                    for a, b2 in zip(got_seeds, ARCHIVED_SEEDS[(arm, sf)]))
        flag = "PASS" if ident == predicted else "** PREDICTION FALSIFIED **"
        print(f"  {arm}_{sf}: archived-{conv:8s} predicted bit-identical="
              f"{str(predicted):5s} observed={str(ident):5s} -> {flag}")
        print(f"           mean {mean[k]:9.4f} vs archived {am:9.4f}, "
              f"window +/-{b:.3f} -> {'in band' if inband else 'OUT OF BAND'}")

    # ---- the three registered quantities ---------------------------------
    def tax(rp, sf, arm):
        return mean[(rp, sf, arm)] / mean[(rp, sf, "qui")]

    print("\nTAX TABLE")
    for rp in ("treeplru", "lru"):
        for sf in ("inf", "fin"):
            if not all((rp, sf, a) in mean for a in ("qui", "wb", "h2", "h3")):
                print(f"  {rp:9s} {sf}: incomplete"); continue
            print(f"  {rp:9s} {sf}: " + "  ".join(
                f"{a}={tax(rp, sf, a):.4f}" for a in ("wb", "h2", "h3")))

    print("\nREGISTERED QUANTITIES")
    res = {}
    for rp in ("treeplru", "lru"):
        ok_fin = all((rp, "fin", a) in mean for a in ("qui", "wb", "h2", "h3"))
        ok_inf = all((rp, "inf", a) in mean for a in ("qui", "h2", "h3"))
        I = tax(rp, "fin", "h2") - tax(rp, "fin", "wb") if ok_fin else None
        R3 = (100 * (tax(rp, "fin", "wb") - tax(rp, "fin", "h3"))
              / (tax(rp, "fin", "wb") - 1)) if ok_fin else None
        C3 = 100 * (tax(rp, "inf", "h3") / tax(rp, "inf", "h2") - 1) if ok_inf else None
        res[rp] = (I, R3, C3)
        f = lambda x, s: (s % x) if x is not None else "n/a"
        print(f"  {rp:9s} I={f(I, '%+.4f')}  R3={f(R3, '%.2f%%')}  C3={f(C3, '%.2f%%')}")

    print("\nVERDICTS")
    rc = 0
    It, Rt, Ct = res["treeplru"]; Il, Rl, Cl = res["lru"]
    if Il is None or It is None:
        print("  Q1: CANNOT DECIDE"); rc = 1
    else:
        v = ("H2 stays inert under a finite SF -- the paper's claim holds"
             if Il >= Q1_SIGN_LIMIT else
             "** H2 becomes materially helpful under LRU -- the inertness claim is "
             "policy-dependent and must be re-stated **")
        print(f"  Q1: I_treeplru={It:+.4f} -> I_lru={Il:+.4f} (limit {Q1_SIGN_LIMIT}) -> {v}")
    if Rl is None or Rt is None:
        print("  Q2: CANNOT DECIDE"); rc = 1
    else:
        d = Rl - Rt; a = abs(d)
        v = ("ROBUST" if a <= Q2_ROBUST else
             "SENSITIVE -- report the LRU figure" if a <= Q2_MATERIAL else
             "MATERIAL -- H3's headline recovery is policy-dependent; ESCALATE")
        print(f"  Q2: R3 {Rt:.2f}% -> {Rl:.2f}%, dR3={d:+.2f} pp -> {v}")
    if Cl is None or Ct is None:
        print("  Q3: CANNOT DECIDE"); rc = 1
    else:
        d = Cl - Ct; a = abs(d)
        v = ("ROBUST -- registered prediction CONFIRMED" if a <= Q3_ROBUST else
             "SENSITIVE -- registered prediction REFUTED" if a <= Q3_MATERIAL else
             "MATERIAL -- registered prediction REFUTED; ESCALATE")
        print(f"  Q3: C3 {Ct:.2f}% -> {Cl:.2f}%, dC3={d:+.2f} pp -> {v}")
        print("      (Q3 was the only quantity with a registered direction:")
        print("       abs(dC3) < 1 pp, because both arms decline to allocate the stream)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
