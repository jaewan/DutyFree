#!/usr/bin/env python3
"""Control for the G-probe CAT arms: how much of WB_cxl_CAT1's tax is CAT?

The matrix reports WB_cxl_CAT1 at 1.89x (ws=4096) and 2.83x (ws=16384) against
the `quiescent` arm. That comparison is NOT a co-run tax and must never be
quoted as one: `quiescent` holds the full 15-way mask while WB_cxl_CAT1 holds
one way (4 MiB), so the ratio folds CAT capacity starvation together with
whatever the streamer does.

This runs the missing cell -- victim on the 1-way mask with NO streamer -- so
the two effects separate:

    CAT1_nostream / quiescent   = the cost of CAT starvation alone
    WB_cxl_CAT1  / CAT1_nostream = the co-run tax on an already-starved victim

The second ratio is the only one that is a co-run tax, and it is the one the
probe's CAT arms were meant to produce.

Reuses run_probe's placement, CAT setup, readback and validity rules unchanged;
this file adds arms and nothing else (apparatus is not modified mid-campaign).
"""
import json, os, sys
from pathlib import Path
import run_probe as P

ARMS = [
    # name,             stream_node, victim_mask, streamer_mask
    ("quiescent",       None, P.FULL, P.FULL),   # re-measured, same session
    ("CAT1_nostream",   None, "0001", "7ffe"),   # the missing cell
    ("WB_cxl_CAT1",     2,    "0001", "7ffe"),   # repeat, for a paired ratio
]

def main():
    out = Path(__file__).resolve().parent.parent / "artifacts"
    out.mkdir(exist_ok=True)
    dst = out / os.environ.get("OUT", "cat_control.jsonl")
    if dst.exists():
        sys.exit(f"{dst} exists. Move it aside (A6.19).")
    nreps  = int(os.environ.get("NREPS", "3"))
    wslist = [int(x) for x in os.environ.get("WS_LIST", "4096,16384").split(",")]
    with open(dst, "w") as fh:
        for rep in range(1, nreps + 1):
          for WS_KB in wslist:
            for (name, snode, vm, sm) in ARMS:
                r = P.run_arm(name, snode, vm, sm, WS_KB)
                r["rep"] = rep; r["ws_kb"] = WS_KB
                fh.write(json.dumps(r, sort_keys=True) + "\n"); fh.flush()
                tag = (f"{r['cyc_per_access']:7.2f} cyc  L2miss {r['l2_miss_rate']:5.2f}%  "
                       f"occ {r['victim_occ_mib']:.1f}/{r['streamer_occ_mib']:.1f} MiB  "
                       f"bw {r['stream_gbps'] or 0:.1f}") if r["valid"] else f"INVALID: {r['why']}"
                print(f"rep{rep:2d} ws{WS_KB:<6d} {name:14s} {tag}", flush=True)
    print(f"\nwrote {dst}")

if __name__ == "__main__":
    try:
        main()
    finally:
        P.cat_teardown()
