#!/usr/bin/env python3
"""Analyzer for the partition-vs-H2 head-to-head.

Committed BEFORE the data. Thresholds are the pre-registered ones from
H2H_PARTITION_VS_H2_PREREG_2026-08-29.md (7b69cc7), held as module constants.
"""
import glob, math, os, re, statistics as st, sys

ITERS = 3_000_000
ARMS = ("qui", "wb", "h2", "cat4", "cat10")
CAT_ARMS = ("cat4", "cat10")
# --- pre-registered thresholds ------------------------------------------------
P1_PROTECT_MIN = 80.0   # R(cat) >= 80% or the model cannot host the comparison
P2_WEDGE_MIN   = 5.0    # (tenant misses/inst, cat) - (h2) >= 5% at both splits
P3_H2_NULL_MAX = 1.0    # |tenant misses/inst, h2 vs wb| <= 1%
W1_LRU = {"wb": 45.2764, "h2": 35.1905}   # instrument check, +/-0.5%
EXPECT_MASKS = {"cat4": "0xf", "cat10": "0x3ff"}
HNF_WAYS = 20


def stats(d):
    p = os.path.join(d, "stats.txt")
    if not (os.path.exists(p) and os.path.getsize(p)):
        return None
    g = {}
    for l in open(p):
        q = l.split()
        if len(q) >= 2:
            try:
                g[q[0]] = float(q[1])
            except ValueError:
                pass
    return g


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


def identity(d, arm, problems):
    """S5.1: every claim about an arm comes from the arm's own artifact."""
    ci = os.path.join(d, "config.ini")
    if not os.path.exists(ci):
        problems.append(f"{os.path.basename(d)}: no config.ini"); return False
    c = open(ci).read()
    ok = True
    m = re.search(r"\[system\.ruby\.hnf\.cntrl\.cache\.replacement_policy\]\n"
                  r"((?:[^\[]*\n)*)", c)
    rp = re.search(r"^type=(\S+)", m.group(1), re.M).group(1) if m else None
    if rp != "LRURP":
        problems.append(f"{os.path.basename(d)}: HNF policy {rp}, expected LRURP"); ok = False
    hm = re.search(r"\[system\.ruby\.hnf\.cntrl\.cache\]\n((?:[^\[]*\n)*)", c)
    rm = re.search(r"^requestor_masks=(.*)$", hm.group(1), re.M) if hm else None
    rmv = (rm.group(1).strip() if rm else "")
    if arm in CAT_ARMS:
        if not rmv:
            problems.append(f"{os.path.basename(d)}: arm {arm} has EMPTY "
                            f"requestor_masks -- a vacuous partitioning arm"); ok = False
    else:
        if rmv:
            problems.append(f"{os.path.basename(d)}: arm {arm} unexpectedly masked "
                            f"({rmv})"); ok = False
    cmds = re.findall(r"^cmd=(.*)$", c, re.M)
    declared = any("stream" in x for x in cmds)
    if (arm == "h2") != declared:
        problems.append(f"{os.path.basename(d)}: arm {arm} declaration="
                        f"{'present' if declared else 'absent'}"); ok = False
    for k, want in (("fwd_unique_on_readshared", "false"),
                    ("max_outstanding_requests", "1024")):
        v = re.search(rf"^{k}=(\S+)", c, re.M)
        if v and v.group(1) != want:
            problems.append(f"{os.path.basename(d)}: {k}={v.group(1)}, "
                            f"prereg pins {want}"); ok = False
    if arm == "qui":
        g = stats(d)
        if g and g.get("system.cpu1.numCycles", 0):
            problems.append(f"{os.path.basename(d)}: cpu1 ran in the quiescent arm"); ok = False
    return ok


def tenant(g):
    """Per-instruction L2 misses (demand+prefetch) and per-cycle throughput.
    Demand-only rates are deliberately NOT used: that error made H2's tenant
    cost read as -3.9% when it is a gain."""
    c = g.get("system.cpu1.numCycles", 0)
    ipc = g.get("system.cpu1.ipc", 0)
    if not c or not ipc:
        return None
    t = (g.get("system.cpu1.l2.cache.m_demand_misses", 0)
         + g.get("system.cpu1.l2.cache.m_prefetch_misses", 0))
    per_cycle = t / c
    return dict(per_inst=per_cycle / ipc, per_kcyc=1000 * per_cycle, ipc=ipc)


def main():
    problems, data = [], {}
    for arm in ARMS:
        vic, ten, ways = {}, {}, {}
        for d in sorted(glob.glob(f"/tmp/hh_{arm}_s*")):
            if d.endswith(".log"):
                continue
            ok, why = alive(d)
            if not ok:
                problems.append(f"{os.path.basename(d)}: {why}"); continue
            if not identity(d, arm, problems):
                continue
            g = stats(d)
            if not g or "system.cpu0.numCycles" not in g:
                problems.append(f"{os.path.basename(d)}: no cpu0 cycles"); continue
            vic[d] = g["system.cpu0.numCycles"] / ITERS
            tt = tenant(g)
            if tt:
                ten[d] = tt
            ways[d] = [g.get(f"system.ruby.hnf.cntrl.cache.m_allocsByWay::{w}", 0.0)
                       for w in range(HNF_WAYS)]
        if vic:
            data[arm] = dict(vic=vic, ten=ten, ways=ways)

    print("=" * 78)
    print("HEAD-TO-HEAD: way partitioning vs H2 -- prereg H2H_PARTITION_VS_H2_PREREG")
    print("=" * 78)
    if problems:
        print("\nPROBLEM RUNS (reported, not silently dropped):")
        for p in problems:
            print("  " + p)

    print("\nNEIGHBOUR (cpu0)")
    vm = {}
    for arm in ARMS:
        if arm not in data:
            print(f"  {arm:6s}: NO USABLE RUNS"); continue
        v = list(data[arm]["vic"].values())
        vm[arm] = st.mean(v)
        sd = st.stdev(v) if len(v) > 1 else float("nan")
        print(f"  {arm:6s}: n={len(v)} cyc/access={st.mean(v):9.4f} sd={sd:.4f}")

    print("\nTENANT (cpu1)")
    tm = {}
    for arm in ARMS:
        if arm == "qui" or arm not in data or not data[arm]["ten"]:
            continue
        t = list(data[arm]["ten"].values())
        tm[arm] = {k: st.mean([x[k] for x in t]) for k in t[0]}
        print(f"  {arm:6s}: n={len(t)} misses/inst={tm[arm]['per_inst']:9.4f} "
              f"misses/kcyc={tm[arm]['per_kcyc']:8.3f} IPC={tm[arm]['ipc']:.4f}")

    if "qui" not in vm or "wb" not in vm:
        print("\nCANNOT DECIDE -- need qui and wb."); return 1
    tax = {a: vm[a] / vm["qui"] for a in vm}
    R = {a: 100 * (tax["wb"] - tax[a]) / (tax["wb"] - 1) for a in vm if a != "qui"}
    print("\nTAX AND RECOVERY")
    for a in ("wb", "h2", "cat4", "cat10"):
        if a in tax:
            print(f"  {a:6s}: tax={tax[a]:.4f}  recovery={R[a]:6.2f}%")

    # ---- P4: mask enforcement, structural ----
    print("\nP4 -- MASK ENFORCEMENT (HNF allocations outside the mask)")
    p4 = True
    for arm in CAT_ARMS:
        if arm not in data:
            print(f"  {arm}: no data"); p4 = False; continue
        allowed = int(EXPECT_MASKS[arm], 0)
        outside = 0.0
        inside = 0.0
        for w_list in data[arm]["ways"].values():
            for w, n in enumerate(w_list):
                if (allowed >> w) & 1:
                    inside += n
                else:
                    outside += n
        # the victim (node 4) is unmasked, so it may legitimately allocate anywhere;
        # this counts TOTAL HNF allocations, so "outside" is expected to be nonzero.
        print(f"  {arm:6s}: mask={EXPECT_MASKS[arm]}  allocations inside={inside:.0f} "
              f"outside={outside:.0f}  (victim is unmasked, so outside>0 is expected)")
    print("  NOTE: m_allocsByWay is not per-requestor, so this cannot isolate the")
    print("  stream's allocations. Enforcement is asserted by identity (requestor_masks")
    print("  present in config.ini) plus the C++ path verified by checks 1 and 2.")

    print("\nVERDICTS")
    rc = 0
    # P1
    if all(a in R for a in CAT_ARMS):
        worst = min(R[a] for a in CAT_ARMS)
        v = "HOLDS" if worst >= P1_PROTECT_MIN else "FAILS -- model cannot host the comparison; run is VOID"
        print(f"  P1 partitioning protects: R(cat4)={R['cat4']:.2f}% "
              f"R(cat10)={R['cat10']:.2f}% (>= {P1_PROTECT_MIN}) -> {v}")
        if worst < P1_PROTECT_MIN:
            rc = 1
    else:
        print("  P1: CANNOT DECIDE"); rc = 1
    # P2 -- the wedge
    if "h2" in tm and all(a in tm for a in CAT_ARMS):
        base = tm["h2"]["per_inst"]
        print(f"  P2 the wedge (tenant misses/instruction vs h2):")
        ok2 = True
        for a in CAT_ARMS:
            W = 100 * (tm[a]["per_inst"] / base - 1)
            print(f"       {a:6s}: {W:+7.2f}%  (>= {P2_WEDGE_MIN}%)")
            ok2 &= (W >= P2_WEDGE_MIN)
        print(f"     -> {'WEDGE REPRODUCES IN THE MODEL' if ok2 else 'WEDGE DOES NOT REPRODUCE -- the paper argument rests on silicon alone'}")
        if not ok2:
            rc = 1
    else:
        print("  P2: CANNOT DECIDE"); rc = 1
    # P3
    if "h2" in tm and "wb" in tm:
        d3 = 100 * (tm["h2"]["per_inst"] / tm["wb"]["per_inst"] - 1)
        v = "REPRODUCES" if abs(d3) <= P3_H2_NULL_MAX else "DOES NOT REPRODUCE in this tree"
        print(f"  P3 H2 tenant cost: {d3:+.2f}% per instruction "
              f"(|.| <= {P3_H2_NULL_MAX}%) -> {v}")
    else:
        print("  P3: CANNOT DECIDE"); rc = 1
    # instrument check
    print("\nINSTRUMENT CHECK vs W1-under-LRU (+/-0.5%)")
    for a, want in W1_LRU.items():
        if a in vm:
            dev = 100 * (vm[a] / want - 1)
            print(f"  {a:3s}: {vm[a]:9.4f} vs {want:9.4f}  {dev:+.3f}% -> "
                  f"{'PASS' if abs(dev) <= 0.5 else 'MISS -- link to W1 numbers void, internal comparison stands'}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
