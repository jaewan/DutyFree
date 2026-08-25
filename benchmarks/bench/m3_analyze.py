#!/usr/bin/env python3
"""M3 analysis: does non-allocation remove the neighbour's harm?

Computes only the reading registered in M3_FLUSHBEHIND_PREREG_2026-08-25.md:

    recovery = (harm_alloc - harm_fb) / (harm_alloc - harm_ns)

the fraction of the stream-attributable harm that declining to RETAIN the
stream's lines removes, while still reading every byte. Committed before the
data exists.

Thresholds, fixed in advance: >=70% means the harm is cache residency and H2
removes it; <=20% means the harm is bytes in flight and no admission-control
mechanism helps; between is partial and only the fraction may be claimed.
"""
import json, sys, statistics as st, collections
from pathlib import Path

ARMS = ["V", "V+F_alloc", "V+F_fb", "V+F_ns"]


def main(argv):
    p = Path(argv[1] if len(argv) > 1 else "../data/m3_flushbehind/m3.jsonl")
    by, pos = collections.defaultdict(list), collections.defaultdict(list)
    for l in p.read_text().splitlines():
        if not l.strip():
            continue
        r = json.loads(l); v = r.get("median_cyc_per_load")
        if v is None:
            print(f"  BAD RECORD: {r}"); continue
        by[r["arm"]].append(float(v)); pos[r["arm"]].append(r["pos"])

    base = st.mean(by["V"])
    print(f"{'arm':<12}{'n':>3} {'cyc/load':>10}{'sd':>7}{'CoV%':>7}  {'harm':>8}  pos")
    h = {}
    for a in ARMS:
        v = by.get(a)
        if not v:
            print(f"{a:<12} -- absent"); continue
        m = st.mean(v); sd = st.pstdev(v); h[a] = m / base
        print(f"{a:<12}{len(v):>3} {m:>10.3f}{sd:>7.3f}{sd/m*100:>7.2f}  {h[a]:>8.4f}  "
              f"{[pos[a].count(i) for i in (1,2,3,4)]}")

    if not all(k in h for k in ("V+F_alloc", "V+F_fb", "V+F_ns")):
        print("\nincomplete; cannot compute the registered reading"); return 2

    span = h["V+F_alloc"] - h["V+F_ns"]
    rec = (h["V+F_alloc"] - h["V+F_fb"]) / span if span else float("nan")
    print(f"\n== registered reading ==")
    print(f"  harm allocating      {h['V+F_alloc']:.4f}x")
    print(f"  harm flush-behind    {h['V+F_fb']:.4f}x")
    print(f"  harm no stream       {h['V+F_ns']:.4f}x")
    print(f"  stream-attributable span = {span:.4f}")
    print(f"  RECOVERY = {rec*100:.1f}%")
    if rec >= 0.70:
        print("  -> **THE HARM IS CACHE RESIDENCY, AND NON-ALLOCATION REMOVES IT.**")
        print("     STREAMING has a measured configuration where it uniquely helps:")
        print("     one thread, two access classes, no context-scoped label can name")
        print("     them apart, and the shipped alternatives charge F's own reuse")
        print("     structure. This is a lower bound on H2 -- clflushopt evicts lines")
        print("     already allocated, where hardware would never allocate them.")
    elif rec <= 0.20:
        print("  -> **THE HARM IS BYTES IN FLIGHT, NOT RESIDENCY.**")
        print("     No admission-control mechanism helps, H2 included. The mechanism")
        print("     has no configuration and the paper is a measurement paper.")
    else:
        print("  -> PARTIAL. Claim only the fraction. Per the prereg, a mid-range")
        print("     result under a saturating metric is a reason to sweep the flush")
        print("     distance before interpreting, not to interpolate.")
    print("\n  (reminder: the victim metric saturates, 78 -> ~209 with little between)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
