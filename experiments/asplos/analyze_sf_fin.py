#!/usr/bin/env python3
"""Analyser for the FINITE-SF cells launched by sf_fin_cells.sh.

Committed before the data exists, per the W1 lesson. It is a sibling of
analyze_sf_inf.py, not a copy: it does a different job, and analyze_sf_inf.py
is deliberately left untouched because a landed, quoted result was printed by
the version in git.

What it deliberately does NOT do
--------------------------------
It does not print W1's PASS / PARTIAL / FAIL verdict. Those bands (1.10 /
1.30) were pre-registered for the *infinite*-SF decisive cell, where H2 is
expected to work. At a finite SF H2 is known to be inert (0.5% of the per-miss
excess, W1.4), so applying the infinite bands here would manufacture a "FAIL"
against a prediction nobody made. Re-using a threshold outside the arm it was
registered for is the S5.1 failure in its purest form.

What it is for
--------------
The finite arms behind tab:h3sf have no committed launcher (F10). Three memos
place a finite number beside an infinite one and each flags the gap rather than
closing it (W1.4, W1.5, W3.4). Re-running under sf_fin_cells.sh closes it. This
script reports the finite table in the same shape as W1.4's, and then the one
comparison that motivated the re-run: H2+H3's per-miss cost at a finite SF
against its cost at an infinite one, which the 2026-08-20 data put 0.7% apart
across a provenance gap.

Usage: python3 analyze_sf_fin.py            (reads /tmp/sf_*_fin_s*/stats.txt)
       python3 analyze_sf_fin.py --no-compare   (skip the infinite comparison)
"""
import glob, os, re, statistics, sys

ITERS = 3_000_000          # Sec5.3 gate; victim is `dutyfree/victim 2650 3000000`
ARMS = ["qui", "wb", "h2", "h3"]   # h3 == H2+H3

NUM = re.compile(r"^(\S+)\s+([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)(?:\s|$)")


def load(path):
    """First occurrence of each stat name. Strict numeric match: gem5 emits
    non-numeric second fields (distribution labels, 'nan') that a loose regex
    silently turns into garbage."""
    v = {}
    with open(path) as f:
        for line in f:
            m = NUM.match(line)
            if m:
                v.setdefault(m.group(1), float(m.group(2)))
    return v


def hnf_sum(v, suffix):
    return sum(x for k, x in v.items()
               if k.startswith("system.ruby.hnf") and k.endswith(suffix))


def cell(path):
    v = load(path)
    cyc = v.get("system.cpu0.numCycles")
    vmiss = v.get("system.cpu0.l2.cache.m_demand_misses")
    if not cyc or not vmiss:
        return None
    acc = hnf_sum(v, ".cache.m_demand_accesses")
    hit = hnf_sum(v, ".cache.m_demand_hits")
    return {
        "cyc_per_access": cyc / ITERS,
        "victim_l2_dmiss": vmiss,
        "cyc_per_miss": cyc / vmiss,
        "llc_hit_rate": (hit / acc) if acc else float("nan"),
    }


def collect(arm, suffix):
    out = {}
    for d in sorted(glob.glob(f"/tmp/sf_{arm}_{suffix}_s*")):
        p = os.path.join(d, "stats.txt")
        if os.path.exists(p) and os.path.getsize(p):
            c = cell(p)
            if c:
                out[os.path.basename(d)] = c
    return out


def mean_of(rows, key):
    return statistics.mean(r[key] for r in rows.values())


def report(suffix, data):
    print(f"\n=== {suffix.upper()}-SF arms ===")
    if not any(data.values()):
        print("NO DATA -- no /tmp/sf_*_%s_s*/stats.txt with content." % suffix)
        return None
    base = None
    if data["qui"]:
        base = (mean_of(data["qui"], "cyc_per_miss"),
                mean_of(data["qui"], "cyc_per_access"))
    hdr = ("| arm | cyc/access | sd | victim L2 dmiss | cyc/victim L2 dmiss "
           "| excess | LLC demand hit rate | tax |")
    print(hdr)
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    taxes = {}
    for a in ARMS:
        rows = data[a]
        if not rows:
            print(f"| {a} | -- no completed runs -- |")
            continue
        cpa = [r["cyc_per_access"] for r in rows.values()]
        sd = statistics.stdev(cpa) if len(cpa) > 1 else 0.0
        cpm = mean_of(rows, "cyc_per_miss")
        vm = mean_of(rows, "victim_l2_dmiss")
        hr = mean_of(rows, "llc_hit_rate") * 100
        exc = f"{cpm - base[0]:.1f}" if base else "n/a"
        tax = f"{statistics.mean(cpa) / base[1]:.4f}x" if base else "n/a"
        if base:
            taxes[a] = statistics.mean(cpa) / base[1]
        print(f"| {a} (n={len(cpa)}) | {statistics.mean(cpa):.4f} | {sd:.4f} "
              f"| {vm:,.0f} | {cpm:.1f} | {exc} | {hr:.2f}% | {tax} |")
    if not base:
        print("no quiescent baseline in this suffix -- taxes and excess omitted")
    return {a: mean_of(data[a], "cyc_per_miss") for a in ARMS if data[a]}


def launcher_status(arm, suffix):
    """Which arms came from a committed launcher.

    Both committed launchers append a `DONE_` sentinel to the run log; the
    2026-08-20 batch was typed at the shell and has none (F10).  This reads the
    artifacts rather than assuming, because as of 2026-08-24 the /tmp tree holds
    a mixture: sf_h2_inf / sf_h3_inf are from sf_inf_cells.sh, and everything
    else predates any committed runner.  See W4.5_SF_CAMPAIGN_PROVENANCE.
    """
    have, done = 0, 0
    for log in sorted(glob.glob(f"/tmp/sf_{arm}_{suffix}_s*.log")):
        have += 1
        try:
            with open(log, errors="replace") as f:
                if any(line.startswith("DONE_") for line in f):
                    done += 1
        except OSError:
            pass
    return done, have


def provenance_line(suffix, arms):
    committed, f10 = [], []
    for a in arms:
        done, have = launcher_status(a, suffix)
        (committed if have and done == have else f10).append(a)
    bits = []
    if committed:
        bits.append("committed launcher: " + ",".join(committed))
    if f10:
        bits.append("F10, no runner in git: " + ",".join(f10))
    return f"  {suffix}: " + "; ".join(bits) if bits else f"  {suffix}: no arms"


def main():
    compare = "--no-compare" not in sys.argv[1:]
    fin_data = {a: collect(a, "fin") for a in ARMS}
    fin = report("fin", fin_data)

    if fin is None:
        print("\nnothing to analyse. Launch with: SF_FIN_GO=1 experiments/asplos/sf_fin_cells.sh")
        return 1

    if not compare:
        return 0

    inf_data = {a: collect(a, "inf") for a in ARMS}
    inf = report("inf", inf_data)
    if inf is None:
        print("\nno infinite-SF arms on this host -- comparison skipped.")
        return 0

    print("\n=== the comparison this re-run exists to make ===")
    print("W1.5 flagged H2+H3 finite (151.1 cyc/miss, 2026-08-20 campaign) against")
    print("H2+H3 infinite (152.2, W1) as 0.7% apart across a provenance gap (F10).")
    print("Provenance of the two columns, read from the DONE_ sentinels on disk:")
    print(provenance_line("fin", [a for a in ARMS if a in fin]))
    print(provenance_line("inf", [a for a in ARMS if a in inf]))
    print("An F10 column is still worth comparing -- W4.5 pins the apparatus from")
    print("config.ini -- but it is not a re-run under a committed runner.\n")
    for a in ARMS:
        if a in fin and a in inf:
            d = (fin[a] / inf[a] - 1) * 100
            print(f"  {a:3s}  finite {fin[a]:7.1f}  infinite {inf[a]:7.1f}  "
                  f"cyc per victim L2 demand miss   ({d:+.1f}%)")
    if "h3" in fin and "h3" in inf:
        d = abs(fin["h3"] / inf["h3"] - 1) * 100
        print(f"\nH2+H3: {d:.1f}% apart.")
        print("Interpretation fixed in W1.5 before this re-run: if H3 is enrolment")
        print("relief, SF size should stop mattering once H3 is on, so these two")
        print("should agree. They are not a prediction with a threshold -- W1.5")
        print("registered none -- and must not be reported as a passed gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
