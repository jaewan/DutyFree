#!/usr/bin/env python3
"""CAT12 no-streamer control for the moscxl matrix.

The moscxl matrix produced one number that the matrix alone cannot interpret.
At ws=1024 KB the WB_local_CAT12 arm reads 4.98x quiescent while the victim
holds 12 of 16 L3 ways (12 MiB, for a 1 MiB working set) and the streamer is
boxed into the remaining 4 MiB. If that 4.98x is real co-run residual it is a
large CAT-irrecoverable tax; if it is CAT starvation it is an artefact of the
partition. The matrix cannot tell them apart because it has a no-streamer
control only at the 1-way grant (CAT1_nostream, 1.733x), not at the 12-way one.

This adds the missing cell: victim on the same 12-way mask, streamer group
created and masked exactly as in the matrix arm, but no streamer started.

Everything else -- placement, CAT plumbing, occupancy sampling, the foreign-load
check, the D1 l2_counters validity gate -- is imported from run_probe_moscxl
rather than restated, so the control cannot drift from the arm it controls.

Reading it: WB_local_CAT12 / CAT12_nostream is the co-run tax on an already
partitioned victim. CAT12_nostream / quiescent is the cost of the partition
itself. The matrix's 4.98x is the product of the two.
"""
import json, os, sys
from pathlib import Path

import run_probe_moscxl as P

ARMS = [
    # name,             stream_node, victim_mask,  streamer_mask
    ("quiescent",       None, P.FULL, P.FULL),
    ("CAT12_nostream",  None, "0fff", "f000"),
    ("CAT1_nostream",   None, "0001", "fffe"),
]


def main():
    out = Path(__file__).resolve().parent.parent / "artifacts"
    out.mkdir(exist_ok=True)
    dst = out / os.environ.get("OUT", "probe_moscxl_cat12_control.jsonl")
    if dst.exists():
        sys.exit(f"{dst} exists. Move it aside; this script does not append to "
                 "a file it did not create in this run (A6.19).")
    with open(dst, "w") as fh:
        for rep in range(1, P.NREPS + 1):
          for WS_KB in P.WS_LIST:
            for (name, snode, vm, sm) in ARMS:
                r = P.run_arm(name, snode, vm, sm, WS_KB)
                r["rep"] = rep
                r["ws_kb"] = WS_KB
                fh.write(json.dumps(r, sort_keys=True) + "\n"); fh.flush()
                tag = (f"{r['cyc_per_access']:8.2f} cyc  L2miss {r['l2_miss_rate']:6.2f}%  "
                       f"occ {r['victim_occ_mib']:.1f}/{r['streamer_occ_mib']:.1f} MiB"
                       ) if r["valid"] else f"INVALID: {r['why']}"
                print(f"rep{rep:2d} ws{WS_KB:<6d} {name:15s} {tag}", flush=True)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    try:
        main()
    finally:
        P.cat_teardown()
