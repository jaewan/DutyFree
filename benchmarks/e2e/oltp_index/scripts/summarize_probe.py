#!/usr/bin/env python3
"""Summarize the G-probe matrix: victim tax vs working set, per arm.

Tax is rep-paired against the quiescent arm at the SAME working set, because
the quiescent cost of a chase changes with footprint and a cross-WS baseline
would fold that into the tax.
"""
import json, statistics as st, sys
from collections import defaultdict

recs = [json.loads(l) for l in open(sys.argv[1])]
bad = [r for r in recs if not r["valid"]]
ok = [r for r in recs if r["valid"]]
print(f"{len(ok)} valid, {len(bad)} invalid")
for b in bad:
    print("  INVALID", b.get("ws_kb"), b["arm"], b["why"])

# key: (ws, arm) -> {rep: record}
byk = defaultdict(dict)
for r in ok:
    byk[(r["ws_kb"], r["arm"])][r["rep"]] = r
wss = sorted({r["ws_kb"] for r in ok})
arms = [a for a in ["quiescent","WB_cxl","WB_cxl_CAT12","WB_cxl_CAT1","WB_local"]
        if any(k[1] == a for k in byk)]

hdr = f"{'ws_KB':>7} {'arm':<14} {'cyc/acc':>9} {'tax':>7} {'L2miss%':>8} {'v_occ':>7} {'s_occ':>7} {'GB/s':>6} {'n':>3}"
print("\n" + hdr); print("-" * len(hdr))
for ws in wss:
    q = byk[(ws, "quiescent")]
    for a in arms:
        d = byk[(ws, a)]
        if not d:
            continue
        cyc = [d[r]["cyc_per_access"] for r in sorted(d)]
        # rep-paired tax: only reps present in both
        shared = sorted(set(d) & set(q))
        tax = st.median([d[r]["cyc_per_access"] / q[r]["cyc_per_access"] for r in shared]) if shared else float("nan")
        f = lambda k: st.median([d[r][k] for r in sorted(d) if d[r].get(k) is not None]) if any(d[r].get(k) is not None for r in d) else float("nan")
        print(f"{ws:>7} {a:<14} {st.median(cyc):>9.2f} {tax:>7.3f} "
              f"{f('l2_miss_rate'):>8.2f} {f('victim_occ_mib'):>7.1f} "
              f"{f('streamer_occ_mib'):>7.1f} {f('stream_gbps') or 0:>6.1f} {len(cyc):>3}")
    print()
