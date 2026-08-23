#!/usr/bin/env python3
"""CAT12 no-streamer control for the mos182 MBA arm. The Intel twin of
run_cat12_control_moscxl.py, and required for the same reason.

probe_mos182_mba.jsonl reports CAT12 at 1.221x quiescent at ws=61440 KB, with
MBA unable to move it. Called a "CAT-irrecoverable co-run residual" that would
be the Intel analogue of moscxl's 13.05x. But it cannot be called that yet,
because at this working set the partition is not free: the victim's set is
60 MiB and a 12-of-15-way grant caps it at 48 MiB, so the victim necessarily
loses residency it had in the quiescent arm -- before any streamer runs.

    CAT12_nostream / quiescent      = what the partition itself costs
    CAT12 / CAT12_nostream          = the co-run residual, which is the only
                                      ratio that may be described as one

On moscxl the same control turned a 12.43x headline into 12.43/1.066, i.e.
almost all co-run. Here it could plausibly account for the entire 1.221x, and
if it does, the honest Intel statement is that CAT recovers the tax completely
and there is no residual for MBA to fail to fix.

CAT1_nostream is included at these working sets too, since the wsext sweep's
WB_cxl_CAT1 arms (2.34x-2.92x) have the same uninterpretable denominator.

Imports run_probe so placement, CAT plumbing, occupancy sampling, the
foreign-load check and the D1 l2_counters gate cannot drift from the arms this
controls.
"""
import json, os, sys
from pathlib import Path

import run_probe as P

ARMS = [
    # name,             stream_node, victim_mask, streamer_mask
    ("quiescent",       None, P.FULL, P.FULL),
    ("CAT12_nostream",  None, "0fff", "7000"),
    ("CAT1_nostream",   None, "0001", "7ffe"),
]


def main():
    out = Path(__file__).resolve().parent.parent / "artifacts"
    out.mkdir(exist_ok=True)
    dst = out / os.environ.get("OUT", "probe_mos182_cat12_control.jsonl")
    if dst.exists():
        sys.exit(f"{dst} exists. Move it aside; this script does not append to "
                 "a file it did not create in this run (A6.19).")
    with open(dst, "w") as fh:
        for rep in range(1, P.NREPS + 1):
          for WS_KB in P.WS_LIST:
            for (name, snode, vm, sm) in ARMS:
                r = P.run_arm(name, snode, vm, sm, WS_KB)
                r["rep"], r["ws_kb"] = rep, WS_KB
                fh.write(json.dumps(r, sort_keys=True) + "\n"); fh.flush()
                tag = (f"{r['cyc_per_access']:8.2f} cyc  L2miss {r['l2_miss_rate']:6.2f}%  "
                       f"vocc {r['victim_occ_mib']:5.1f} MiB"
                       ) if r["valid"] else f"INVALID: {r['why']}"
                print(f"rep{rep:2d} ws{WS_KB:<6d} {name:15s} {tag}", flush=True)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    try:
        main()
    finally:
        P.cat_teardown()
