#!/usr/bin/env python3
"""Analyzer for the FUSED head-to-head (partitioning vs H2, tenant with reuse).

Thresholds are the pre-registered ones from H2H_FUSED_PREREG_2026-08-29.md.
Primary tenant metric is THROUGHPUT; misses-per-instruction is secondary and
decides nothing -- it was primary in the pure-stream attempt and proved blind to
confinement cost.
"""
import glob, os, re, statistics as st, sys

ITERS = 3_000_000
ARMS = ("qui", "wb", "h2", "cat4", "cat10")
CAT = ("cat4", "cat10")
P1_PROTECT_MIN = 80.0
P2_CAT_COST_MIN = 5.0
P2_H2_COST_MAX = 1.0
EXPECT_MASKS = {"cat4": 0xf, "cat10": 0x3ff}
HNF_WAYS = 20


def sget(d):
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
        return False, "no 'Exiting @ tick'"
    m = re.search(r"^DONE_(\d+) ", t, re.M)
    return (m is None or m.group(1) == "0"), "ok"


def ident(d, arm, probs):
    c = open(os.path.join(d, "config.ini")).read()
    ok = True
    rp = re.search(r"\[system\.ruby\.hnf\.cntrl\.cache\.replacement_policy\]\n"
                   r"((?:[^\[]*\n)*)", c)
    pol = re.search(r"^type=(\S+)", rp.group(1), re.M).group(1) if rp else None
    if pol != "LRURP":
        probs.append(f"{os.path.basename(d)}: HNF policy {pol}"); ok = False
    hm = re.search(r"\[system\.ruby\.hnf\.cntrl\.cache\]\n((?:[^\[]*\n)*)", c)
    rmv = (re.search(r"^requestor_masks=(.*)$", hm.group(1), re.M).group(1).strip()
           if hm and re.search(r"^requestor_masks=", hm.group(1), re.M) else "")
    if (arm in CAT) != bool(rmv):
        probs.append(f"{os.path.basename(d)}: arm {arm} masks='{rmv}'"); ok = False
    declared = any("stream" in x for x in re.findall(r"^cmd=(.*)$", c, re.M))
    if (arm == "h2") != declared:
        probs.append(f"{os.path.basename(d)}: arm {arm} declaration mismatch"); ok = False
    for k, want in (("fwd_unique_on_readshared", "false"),
                    ("max_outstanding_requests", "1024")):
        v = re.search(rf"^{k}=(\S+)", c, re.M)
        if v and v.group(1) != want:
            probs.append(f"{os.path.basename(d)}: {k}={v.group(1)} != {want}"); ok = False
    return ok


def main():
    probs, D = [], {}
    for arm in ARMS:
        vic, ten, ways, sacc = {}, {}, {}, {}
        for d in sorted(glob.glob(f"/tmp/fh_{arm}_s*")):
            if d.endswith(".log"):
                continue
            ok, why = alive(d)
            if not ok:
                probs.append(f"{os.path.basename(d)}: {why}"); continue
            if not ident(d, arm, probs):
                continue
            g = sget(d)
            vic[d] = g["system.cpu0.numCycles"] / ITERS
            c1, ipc = g.get("system.cpu1.numCycles", 0), g.get("system.cpu1.ipc", 0)
            if c1 and ipc:
                t = (g.get("system.cpu1.l2.cache.m_demand_misses", 0)
                     + g.get("system.cpu1.l2.cache.m_prefetch_misses", 0))
                ten[d] = dict(per_kcyc=1000 * t / c1, per_inst=(t / c1) / ipc, ipc=ipc)
                sacc[d] = g.get("system.cpu1.mmu.dtb.streamingAccesses", 0)
            ways[d] = [g.get(f"system.ruby.hnf.cntrl.cache.m_allocsByWay::{w}", 0.0)
                       for w in range(HNF_WAYS)]
        D[arm] = dict(vic=vic, ten=ten, ways=ways, sacc=sacc)

    print("=" * 78)
    print("FUSED HEAD-TO-HEAD -- prereg H2H_FUSED_PREREG_2026-08-29.md")
    print("tenant = 16 MB stream + 3 MB hot table; only the stream is declared")
    print("=" * 78)
    if probs:
        print("\nPROBLEM RUNS:")
        for p in probs:
            print("  " + p)

    vm = {a: st.mean(list(D[a]["vic"].values())) for a in ARMS if D[a]["vic"]}
    tm = {a: {k: st.mean([x[k] for x in D[a]["ten"].values()]) for k in ("per_kcyc", "per_inst", "ipc")}
          for a in ARMS if D[a]["ten"]}

    print("\nNEIGHBOUR (cpu0)")
    for a in ARMS:
        if a in vm:
            sd = st.stdev(list(D[a]["vic"].values()))
            print(f"  {a:6s} n={len(D[a]['vic'])} cyc/access={vm[a]:9.4f} sd={sd:.4f}")
    print("\nTENANT (cpu1)  -- primary metric is throughput")
    for a in ("wb", "h2", "cat4", "cat10"):
        if a in tm:
            print(f"  {a:6s} misses/kcyc={tm[a]['per_kcyc']:8.3f}  IPC={tm[a]['ipc']:.4f}  "
                  f"misses/inst={tm[a]['per_inst']:.6f}  streamingAcc={st.mean(list(D[a]['sacc'].values())):12.0f}")

    tax = {a: vm[a] / vm["qui"] for a in vm}
    R = {a: 100 * (tax["wb"] - tax[a]) / (tax["wb"] - 1) for a in tax if a != "qui"}
    print("\nTAX AND RECOVERY")
    for a in ("wb", "h2", "cat4", "cat10"):
        print(f"  {a:6s} tax={tax[a]:.4f}  recovery={R[a]:6.2f}%")

    cost = {a: 100 * (1 - tm[a]["per_kcyc"] / tm["wb"]["per_kcyc"]) for a in tm}
    print("\nTENANT COST (throughput lost vs wb; negative = the tenant gained)")
    for a in ("h2", "cat4", "cat10"):
        print(f"  {a:6s} {cost[a]:+7.2f}%")

    print("\nP4 -- per-way HNF allocations (mask enforcement)")
    for a in CAT:
        m = [st.mean(x) for x in zip(*D[a]["ways"].values())]
        ins = st.mean([m[w] for w in range(HNF_WAYS) if (EXPECT_MASKS[a] >> w) & 1])
        out = st.mean([m[w] for w in range(HNF_WAYS) if not (EXPECT_MASKS[a] >> w) & 1])
        print(f"  {a:6s} inside/way={ins:10.0f}  outside/way={out:9.0f}  ratio={ins/max(out,1e-9):7.1f}x")

    print("\nVERDICTS")
    rc = 0
    worst = min(R[a] for a in ("h2",) + CAT)
    v1 = "HOLDS" if worst >= P1_PROTECT_MIN else "FAILS -- comparison VOID"
    print(f"  P1 all protect (>= {P1_PROTECT_MIN}%): h2={R['h2']:.2f} cat4={R['cat4']:.2f} "
          f"cat10={R['cat10']:.2f} -> {v1}")
    if worst < P1_PROTECT_MIN:
        rc = 1
    c1 = cost["cat4"] >= P2_CAT_COST_MIN
    c2 = cost["cat4"] > cost["cat10"]
    c3 = cost["h2"] <= P2_H2_COST_MAX
    print(f"  P2 the wedge -- all three required:")
    print(f"       cost(cat4)={cost['cat4']:+.2f}% >= {P2_CAT_COST_MIN}%      -> {'PASS' if c1 else 'FAIL'}")
    print(f"       cost(cat4) > cost(cat10)={cost['cat10']:+.2f}%   -> {'PASS' if c2 else 'FAIL'}")
    print(f"       cost(h2)={cost['h2']:+.2f}% <= {P2_H2_COST_MAX}%        -> {'PASS' if c3 else 'FAIL'}")
    if c1 and c2 and c3:
        print("     -> WEDGE REPRODUCES IN THE MODEL. Partitioning charges the tenant;")
        print("        the page-scoped label does not. This is the paper's claim, measured")
        print("        in one apparatus with one variable changed.")
    else:
        print("     -> WEDGE DOES NOT REPRODUCE even with a tenant that has reuse to lose.")
        print("        Sec1's unconditional claim is NOT supported by our own simulator")
        print("        and must be scoped to silicon.")
        rc = 1
    print(f"\n  Secondary (decides nothing): tenant misses/instruction")
    for a in ("wb", "h2", "cat4", "cat10"):
        print(f"       {a:6s} {tm[a]['per_inst']:.6f}  "
              f"({100*(tm[a]['per_inst']/tm['wb']['per_inst']-1):+.2f}% vs wb)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
