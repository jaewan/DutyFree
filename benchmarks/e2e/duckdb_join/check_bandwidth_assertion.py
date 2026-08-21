#!/usr/bin/env python3
"""Section 5's per-repetition aggressor-bandwidth assertion, checked from an artifact.

Section 5 requires: "Aggressor achieved bandwidth recorded per repetition and
asserted within 10% of section 3." The runner records the bandwidth but does
not assert it, so the assertion has to be discharged at reduction time or not
at all. This is that check, run over every repetition rather than over the
per-arm median -- a median can sit inside 10% while individual repetitions do
not, and it is the repetitions that enter the paired bootstrap.

Reference values are the declared characterisation tables, quoted by their
source so a changed reference is visible in a diff:
  - AMD:   preregistration A4.5, full victimless sweep, streaming from CXL
           node 2, cores 9-15 of the victim's CCX.
  - Intel: preregistration section 3.

WB_local has no reference and is deliberately absent from both tables: it
streams from local DRAM, while every characterisation arm streamed from node 2,
so the declared numbers do not predict it. It is reported for information and
not asserted. Asserting it against a node-2 reference would be an arm-identity
error of exactly the kind section 5.1 exists to prevent.
"""
import json, statistics as st, sys
from collections import defaultdict

TOL = 0.10

# arm -> (declared GB/s, provenance)
AMD_REF = {
    "WB_sat":      (24.72, "A4.5 wb_load t=7"),
    "NTA_sat":     (24.68, "A4.5 wb_prefetchnta t=7"),
    "FB0_sat":     (24.69, "A4.5 flushbehind -f 0 t=7"),
    "FB256_sat":   (17.01, "A4.5 flushbehind -f 256 t=7"),
    "FB0_match":   (12.88, "A4.5 flushbehind -f 0 t=1"),
    "FB256_match": (15.39, "A4.5 flushbehind -f 256 t=3"),
    "WB_fbmatch":  (12.85, "A4.5 wb_load t=1"),
}
# Transcribed from the section 3 table, not from any measured median. An
# earlier draft of this file carried rounded values back-derived from the
# campaign's own medians, which makes the check circular: it would have
# compared the run against itself and passed by construction.
INTEL_REF = {
    "WB_sat":      (25.019, "section 3 wb_load t=8"),
    "NTA_sat":     (17.969, "section 3 wb_prefetchnta t=8"),
    "WB_match_hi": (18.484, "section 3 wb_load t=2"),
    "WB_match_lo": (10.308, "section 3 wb_load t=1"),
    "NTA_lo":      (10.751, "section 3 wb_prefetchnta t=2"),
}
NO_REF = {"quiescent", "WB_local"}


def main(path):
    hosts = {json.loads(l)["host"] for l in open(path) if l.strip()}
    if len(hosts) != 1:
        raise SystemExit(f"{path} mixes hosts {hosts}; refusing to check")
    host = hosts.pop()
    ref = AMD_REF if host.startswith("moscxl") else INTEL_REF
    bw = defaultdict(list)
    for l in open(path):
        r = json.loads(l)
        if not r["valid"] or not r.get("agg_bw_gbps"):
            continue
        bw[r["arm"]].append((r["invocation"], r["agg_bw_gbps"]))

    print(f"\n{path}  host={host}  tolerance +-{TOL:.0%}\n")
    print(f"{'arm':<14}{"declared":>9}{'min':>8}{'median':>8}{'max':>8}"
          f"{'worst dev':>11}  {'n':>3}  verdict")
    fails = 0
    for a in sorted(bw):
        vals = [v for _, v in bw[a]]
        if a in NO_REF:
            print(f"{a:<14}{'--':>9}{min(vals):>8.2f}{st.median(vals):>8.2f}"
                  f"{max(vals):>8.2f}{'--':>11}  {len(vals):>3}  not asserted (no node-2 reference)")
            continue
        if a not in ref:
            print(f"{a:<14}{'MISSING':>9}{min(vals):>8.2f}{st.median(vals):>8.2f}"
                  f"{max(vals):>8.2f}{'--':>11}  {len(vals):>3}  NO REFERENCE DECLARED")
            fails += 1
            continue
        d, prov = ref[a]
        devs = [(v - d) / d for _, v in bw[a]]
        worst = max(devs, key=abs)
        bad = [(i, v, (v - d) / d) for i, v in bw[a] if abs((v - d) / d) > TOL]
        ok = not bad
        fails += 0 if ok else 1
        print(f"{a:<14}{d:>9.2f}{min(vals):>8.2f}{st.median(vals):>8.2f}"
              f"{max(vals):>8.2f}{worst:>+10.1%}  {len(vals):>3}  "
              f"{'PASS' if ok else 'FAIL'}  [{prov}]")
        for i, v, dv in bad:
            print(f"{'':<14}  inv{i}: {v:.2f} GB/s, {dv:+.1%}")
    print(f"\nsection 5 bandwidth assertion: "
          f"{'PASS -- every repetition of every referenced arm within 10%' if not fails else f'FAIL on {fails} arm(s)'}")
    return fails


if __name__ == "__main__":
    # Evaluate every file before deciding the exit status: any() short-circuits,
    # so a failing first artifact would silently skip the rest.
    results = [main(p) for p in sys.argv[1:]]
    sys.exit(1 if any(results) else 0)
