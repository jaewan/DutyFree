#!/usr/bin/env python3
"""M1 analysis. Computes the readings registered in
experiments/asplos/M1_THREEPARTY_PREREG_2026-08-25.md, in the registered order:
the instrument falsifier FIRST, because a weak positive control voids the rest.
"""
import json, sys, statistics as st, collections
from pathlib import Path

ARMS = ["V", "V+F1", "V+F8", "V+F16", "V+STREAM"]


def main(argv):
    p = Path(argv[1] if len(argv) > 1 else "../data/m1_threeparty/m1.jsonl")
    rows = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    by = collections.defaultdict(list); pos = collections.defaultdict(list)
    for r in rows:
        v = r.get("median_cyc_per_load")
        if v is None: continue
        by[r["arm"]].append(float(v)); pos[r["arm"]].append(r["pos"])
    print(f"records={len(rows)}")
    print(f"\n{'arm':<10}{'n':>3} {'cyc/load':>10}{'sd':>7}{'CoV%':>7}  {'harm vs V':>10}  pos balance")
    base = st.mean(by["V"]) if by["V"] else None
    harm = {}
    for a in ARMS:
        v = by.get(a)
        if not v: print(f"{a:<10} -- absent"); continue
        m = st.mean(v); sd = st.pstdev(v)
        h = m / base if base else float("nan"); harm[a] = h
        print(f"{a:<10}{len(v):>3} {m:>10.3f}{sd:>7.3f}{sd/m*100:>7.2f}  {h:>10.4f}  "
              f"{[pos[a].count(i) for i in (1,2,3,4,5)]}")

    print("\n== INSTRUMENT FALSIFIER (checked first, as registered) ==")
    hs = harm.get("V+STREAM", float("nan"))
    print(f"  positive control V+STREAM harm = {hs:.4f}x   (registered requirement: >= 1.50x)")
    if not (hs >= 1.50):
        print("  **FIRES: the control does not show clear harm.**")
        print("  Per the pre-registration, this victim/host/geometry cannot detect")
        print("  neighbour harm, so EVERY OTHER ARM IS VOID and a null from V+F16")
        print("  says nothing about fused tenants. The fused numbers below are")
        print("  reported for the record only and must not be used as a verdict.")
    else:
        print("  passes; the fused arms are readable.")

    print("\n== registered primary (readable only if the control passed) ==")
    h16 = harm.get("V+F16", float("nan"))
    print(f"  V+F16 harm = {h16:.4f}x")
    print("  -> " + ("scenario MOOT (<1.15x)" if h16 < 1.15 else
                     "scenario exists (>=1.15x)" if h16 >= 1.15 else "?"))
    print("\n== registered secondary: harm vs worker count ==")
    for a in ("V+F1", "V+F8", "V+F16"):
        if a in harm: print(f"  {a:<8} {harm[a]:.4f}x")

    print("\n== unregistered observation, flagged as such ==")
    if "V+STREAM" in harm and "V+F16" in harm:
        print(f"  the fused tenant ({harm['V+F16']:.4f}x) vs a dedicated 23.3 GB/s streamer "
              f"({harm['V+STREAM']:.4f}x)")
        if harm["V+F16"] > harm["V+STREAM"]:
            print("  The FUSED tenant harms the neighbour MORE than a streamer 4.4x its")
            print("  bandwidth. That cannot be a stream-rate effect. The obvious candidate")
            print("  is F's own 256 MiB hot table: F(256) + V(170) = 426 MiB against a")
            print("  320 MiB LLC, so F may displace V through its REUSE STRUCTURE, not its")
            print("  stream -- which a stream-scoped mechanism would not address.")
            print("  NOT REGISTERED. Requires its own pre-registered test (M1b).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
