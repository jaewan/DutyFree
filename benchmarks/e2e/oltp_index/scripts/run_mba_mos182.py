#!/usr/bin/env python3
"""The section-5.6 MBA arm, repeated on Intel. Same question, different knob.

On moscxl, CAT+MBA took an 18.7x co-run tax to 1.07x while the streamer kept
96% of its bandwidth, which is what killed the L5 "no deployed alternative
occupies this corner" claim at that operating point. The obvious next question
is whether the same is true on the Intel leg. Two things make it a different
experiment rather than a re-run, and both were measured on this host before any
arm was written:

1. The knob is not the same knob. moscxl's MB is a group-level 1/8 GB/s cap
   with 2048 steps. mos182 reports bandwidth_gran 10, min_bandwidth 10,
   delay_linear 1 -- ten coarse steps of a PER-CORE request delay scaled to a
   single core's peak, not to the group's share of a shared ceiling.
   mba_calib_mos182.py measures the consequence: for an 8-thread streamer,
   settings 90 down to 30 all deliver 23.9-24.0 GB/s, i.e. nothing at all. Only
   20 (22.57 GB/s, 94.7% of full) and 10 (12.57, 52.8%) bind. So the Intel arm
   has exactly one barely-binding setting, and MB=30 is a free non-binding
   control -- the analogue of moscxl's MBA256/224.

   That the one usable Intel setting lands at 94.7% delivered, almost exactly
   where moscxl's knee sat (96%), is a coincidence of this host's core count
   and is not to be read as the two knobs behaving alike.

2. There may be no tax to recover. mos182's largest co-run tax anywhere in the
   matrix is 1.065x. An MBA 2x2 run at a 1.065x operating point measures
   nothing: every cell would read ~1x and the null would be uninterpretable.
   So WS_LIST is not defaulted here. It must be set to a working set where
   mos182 actually shows a tax, or to a documented "there is none" -- see
   mos182_wsext.jsonl, which extends the matrix past 16 MiB to the relative
   operating point where moscxl blew up (victim at ~50% of LLC, never probed on
   Intel by the original matrix).

Arms give the full 2x2 plus the binding control:

     WB           CAT off, MBA off      (on,off) / (off,off) cells
     MBA30        non-binding: does arming MBA alone change anything?
     MBA20        MBA only, barely binding
     MBA10        MBA only, deeper Pareto point
     CAT12        CAT only
     CAT12_MBA30  non-binding control with CAT
     CAT12_MBA20  the headline cell
     CAT12_MBA10  deeper Pareto point with CAT

Implementation mirrors run_mba_moscxl.py: monkeypatch run_probe.cat_setup so
placement, victim-first arrival, occupancy sampling, the foreign-load check and
the D1 l2_counters gate are the matrix's own code, not a copy.
"""
import json, os, re, sys
from pathlib import Path

import run_probe as P

MB_MAX = 100                       # Intel MB is a percentage, 10..100 by 10
CUR_MB = MB_MAX                    # set per arm before P.run_arm is called
NDOM   = 2                         # two sockets
SNODE  = int(os.environ.get("SNODE", "1"))   # 1 = local DRAM, 2 = CXL

CAT_V, CAT_S = "0fff", "7000"      # victim 12 of 15 ways, streamer 3

# name,           snode, victim L3, streamer L3, streamer MB
ARMS = [
    ("quiescent",    None,  P.FULL, P.FULL, MB_MAX),
    ("WB",           SNODE, P.FULL, P.FULL, MB_MAX),
    ("MBA30",        SNODE, P.FULL, P.FULL, 30),     # non-binding: ~23.9 GB/s
    ("MBA20",        SNODE, P.FULL, P.FULL, 20),     # ~22.6 GB/s (94.7%)
    ("MBA10",        SNODE, P.FULL, P.FULL, 10),     # ~12.6 GB/s (52.8%)
    ("CAT12",        SNODE, CAT_V,  CAT_S,  MB_MAX),
    ("CAT12_MBA30",  SNODE, CAT_V,  CAT_S,  30),
    ("CAT12_MBA20",  SNODE, CAT_V,  CAT_S,  20),
    ("CAT12_MBA10",  SNODE, CAT_V,  CAT_S,  10),
]

if not os.environ.get("WS_LIST"):
    sys.exit("WS_LIST must be set explicitly on this host -- see the docstring. "
             "Running the 2x2 where there is no tax measures nothing.")
WS_LIST = [int(x) for x in os.environ["WS_LIST"].split(",")]


def mb_line(mb):
    """Both domains stated explicitly; a partial line leaves the rest as-is."""
    return "MB:" + ";".join(f"{d}={mb if d == P.DOM else MB_MAX}" for d in range(NDOM))


def cat_setup_with_mba(vmask, smask):
    for g in (P.VGRP, P.SGRP):
        P.sh(f"sudo -n mkdir -p {g}")
    P.sudo_write(P.VGRP/"schemata", f"L3:0={P.FULL};{P.DOM}={vmask}")
    P.sudo_write(P.SGRP/"schemata", f"L3:0={P.FULL};{P.DOM}={smask}")
    P.sudo_write(P.VGRP/"schemata", mb_line(MB_MAX))     # victim never throttled
    P.sudo_write(P.SGRP/"schemata", mb_line(CUR_MB))
    # Both SMT siblings must be in the streamer group: thread_throttle_mode is
    # "max" on this host, so a core whose sibling sits in an unthrottled group
    # takes the unthrottled setting and MBA silently does nothing. P.SCPUS does.
    P.sudo_write(P.VGRP/"cpus_list", P.VCPUS)
    P.sudo_write(P.SGRP/"cpus_list", P.SCPUS)

    got = {}
    for tag, g, wl3, wmb in (("victim", P.VGRP, vmask, MB_MAX),
                             ("streamer", P.SGRP, smask, CUR_MB)):
        txt = (g/"schemata").read_text()
        m3 = re.search(rf"L3:.*?\b{P.DOM}=([0-9a-f]+)", txt)
        # Intel pads MB values with a leading space ("MB:0= 100"); AMD does not.
        mm = re.search(rf"^\s*MB:.*?\b{P.DOM}=\s*(\d+)", txt, re.M)
        got[tag] = m3.group(1) if m3 else "??"
        if not m3 or int(m3.group(1), 16) != int(wl3, 16):
            sys.exit(f"CAT NOT APPLIED for {tag}: wanted {wl3}, schemata says {txt}")
        if not mm or int(mm.group(1)) != int(wmb):
            sys.exit(f"MBA NOT APPLIED for {tag}: wanted {wmb}, schemata says {txt}")
    got["victim_mb"], got["streamer_mb"] = MB_MAX, CUR_MB
    return got


P.cat_setup = cat_setup_with_mba


def main():
    global CUR_MB
    out = Path(__file__).resolve().parent.parent / "artifacts"
    out.mkdir(exist_ok=True)
    dst = out / os.environ.get("OUT", "probe_mos182_mba.jsonl")
    if dst.exists():
        sys.exit(f"{dst} exists. Move it aside; this script does not append to "
                 "a file it did not create in this run (A6.19).")
    with open(dst, "w") as fh:
        for rep in range(1, P.NREPS + 1):
          for WS_KB in WS_LIST:
            for (name, snode, vm, sm, mb) in ARMS:
                CUR_MB = mb
                r = P.run_arm(name, snode, vm, sm, WS_KB)
                r["rep"], r["ws_kb"] = rep, WS_KB
                r["streamer_mb_setting"] = mb
                fh.write(json.dumps(r, sort_keys=True) + "\n"); fh.flush()
                tag = (f"{r['cyc_per_access']:8.2f} cyc  L2m {r['l2_miss_rate']:6.2f}%  "
                       f"socc {r['streamer_occ_mib']:5.1f} MiB  "
                       f"bw {r['stream_gbps'] or 0:6.2f} GB/s"
                       ) if r["valid"] else f"INVALID: {r['why']}"
                print(f"rep{rep:2d} ws{WS_KB:<6d} {name:13s} {tag}", flush=True)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    try:
        main()
    finally:
        P.cat_teardown()
