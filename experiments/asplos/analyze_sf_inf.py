#!/usr/bin/env python3
"""W1 analyzer for the tab:h3sf infinite-SF cells.

Committed before the data lands, per the W1 lesson that every campaign gets a
committed artifact rather than a shell one-liner. Thresholds are the
pre-registered ones in PLAN_B_REBUILD.md and are not arguments -- editing them
after the fact would be visible in git.

Usage: python3 analyze_sf_inf.py            (reads /tmp/sf_*_inf_s*/stats.txt)

PROVENANCE NOTE added 2026-08-24, output deliberately unchanged (this script
printed a result that is now quoted in W1, W1.4, W1.5 and W3.4, so its stdout is
left byte-for-byte as it was).  It reads four arms; only two of them came from a
committed launcher.  sf_h2_inf and sf_h3_inf are from sf_inf_cells.sh
(2026-08-22/23); sf_qui_inf and sf_wb_inf are from the uncommitted 2026-08-20
batch and are F10 artifacts, and the qui arm is the denominator of every ratio
below.  W4.5_SF_CAMPAIGN_PROVENANCE_2026-08-24.md pins the apparatus for all
four from config.ini and records what stays gone (the seed values).  The sibling
analyze_sf_fin.py derives this distinction at run time from the DONE_ sentinels;
it is stated here rather than printed, for the reason above.
"""
import glob, os, re, statistics, sys

ITERS = 3_000_000          # Sec5.3 gate; victim is `dutyfree/victim 2650 3000000`
PASS_MAX, PARTIAL_MAX = 1.10, 1.30
ARMS = ["qui", "wb", "h2", "h3"]   # h3 == H2+H3


def cyc_per_access(path):
    with open(path) as f:
        for line in f:
            if line.startswith("system.cpu0.numCycles "):
                return int(line.split()[1]) / ITERS
    return None


def collect(arm):
    out = {}
    for d in sorted(glob.glob(f"/tmp/sf_{arm}_inf_s*")):
        p = os.path.join(d, "stats.txt")
        if os.path.getsize(p) if os.path.exists(p) else 0:
            v = cyc_per_access(p)
            if v is not None:
                out[os.path.basename(d)] = v
    return out


def main():
    data = {a: collect(a) for a in ARMS}
    for a in ARMS:
        d = data[a]
        if not d:
            print(f"{a:4s}: no completed runs")
            continue
        vals = list(d.values())
        print(f"{a:4s}: n={len(vals)} " +
              " ".join(f"{k.split('_')[-1]}={v:.3f}" for k, v in d.items()) +
              f"  mean={statistics.mean(vals):.3f}" +
              (f" sd={statistics.stdev(vals):.3f}" if len(vals) > 1 else ""))

    if not data["qui"]:
        print("\nno quiescent baseline -- cannot compute a tax")
        return 1
    base = statistics.mean(data["qui"].values())
    print(f"\nquiescent baseline = {base:.3f} cyc/access")
    print(f"pre-registered bands on cyc/access: "
          f"PASS <= {base*PASS_MAX:.2f}, PARTIAL <= {base*PARTIAL_MAX:.2f}, FAIL above")

    taxes = {}
    for a in ("wb", "h2", "h3"):
        if data[a]:
            taxes[a] = statistics.mean(data[a].values()) / base
            print(f"  {a:2s}/inf tax = {taxes[a]:.4f}x")

    if "h2" in taxes:
        t = taxes["h2"]
        verdict = ("PASS -- H2 removes the capacity charge; instruments meet; proceed to W2"
                   if t <= PASS_MAX else
                   "PARTIAL -- H2 recovers some capacity; report the fraction"
                   if t < PARTIAL_MAX else
                   "FAIL -- HARD STOP. No working mechanism. Escalate to lead before further work.")
        print(f"\nDECISIVE CELL  H2/infinite-SF = {t:.4f}x  ->  {verdict}")
        if "wb" in taxes:
            span = taxes["wb"] - 1.0
            print(f"  fraction of the WB/inf charge removed: "
                  f"{(taxes['wb']-t)/span*100:.1f}% (WB/inf = {taxes['wb']:.4f}x)")
    if "h2" in taxes and "h3" in taxes:
        rel = taxes["h3"] / taxes["h2"]
        print(f"\nCONSISTENCY  (H2+H3)/inf / H2/inf = {rel:.4f}")
        print("  W1.2 revision (registered 2026-08-23 23:41): expect same-or-slightly-worse,")
        print("  i.e. within +/-5%. >10% better => withdraw the tab:h3sf H3 attribution;")
        print("  >10% worse => the no-retention traffic penalty is large and must be stated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
