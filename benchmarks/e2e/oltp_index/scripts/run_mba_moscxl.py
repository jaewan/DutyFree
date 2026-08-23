#!/usr/bin/env python3
"""Does MBA recover the CAT-irrecoverable residual, and at what price?

GPROBE_OUTCOME.md section 5.3 measured a 12.43x co-run tax on a victim holding
12 of 16 L3 ways, with the partition itself costing 1.066x. That is a large
CAT-irrecoverable residual on shipping silicon. The obvious remaining
explanation is bandwidth-class contention -- 7 cores saturating this CCX's
egress at 24.7 GB/s with every victim miss queueing behind them -- and MBA is
the deployed mechanism for exactly that. If MBA recovers it cheaply, the corner
is occupied and no L5 claim survives here.

So the question is not "does MBA help" (throttle hard enough and of course it
does, because the streamer stops running). It is the PARETO CURVE: victim tax
as a function of the bandwidth the streamer actually still gets. Two readings
are decisive in opposite directions --

  the victim recovers while the streamer keeps most of its bandwidth
      -> ordinary bandwidth interference, MBA is the answer, corner occupied
  the victim only recovers when the streamer is throttled to near nothing
      -> MBA "works" only by paying the streamer's entire throughput, which is
         the trade the contract claims to avoid, and L5 survives

A third outcome is possible and would be the most interesting: the tax stays
high even at low streamer bandwidth, which would mean the residual is not
bandwidth at all.

MBA also separates bandwidth from capacity for free. Throttling the request
RATE does not stop a streamer from eventually filling the L3 -- over an 8 s arm
even 0.94 GB/s writes 16 MiB many times over. So if the victim recovers under
MBA while streamer_occ_mib still reads ~16, the harm was never capacity. That
column is recorded in every arm and should be read alongside the tax.

Units: AMD MB is 1/8 GB/s here, calibrated on this host rather than assumed
(2048 unlimited; 128 -> 15.39 GB/s, 64 -> 8.68, 32 -> 3.92, 8 -> 0.94, all
within 4% of nominal). 2048 is written explicitly in the unthrottled arms
rather than left to the group default, so every arm states its own MB.

Implementation: this monkeypatches run_probe_moscxl.cat_setup to write and
verify the MB line as well as L3, and then calls that module's run_arm
unchanged. Placement, victim-first arrival, occupancy sampling, the
foreign-load check and the D1 l2_counters validity gate are therefore literally
the same code as the matrix this is a follow-up to, not a copy of it.
"""
import json, os, re, sys
from pathlib import Path

import run_probe_moscxl as P

MB_MAX  = 2048                     # unlimited, per the root schemata
CUR_MB  = MB_MAX                   # set per arm before P.run_arm is called

# name,            snode, victim L3, streamer L3, streamer MB
ARMS = [
    ("quiescent",     None, P.FULL, P.FULL, MB_MAX),
    ("WB_local",      0,    P.FULL, P.FULL, MB_MAX),
    ("MBA128",        0,    P.FULL, P.FULL, 128),   # ~15.4 GB/s
    ("MBA96",         0,    P.FULL, P.FULL,  96),   # ~11.6
    ("MBA64",         0,    P.FULL, P.FULL,  64),   # ~8.7
    ("MBA32",         0,    P.FULL, P.FULL,  32),   # ~3.9
    ("MBA16",         0,    P.FULL, P.FULL,  16),   # ~2.0
    ("MBA8",          0,    P.FULL, P.FULL,   8),   # ~0.9
    ("CAT12",         0,    "0fff", "f000", MB_MAX),
    ("CAT12_MBA64",   0,    "0fff", "f000",  64),
    ("CAT12_MBA16",   0,    "0fff", "f000",  16),
]
WS_LIST = [int(x) for x in os.environ.get("WS_LIST", "256,8192,65536").split(",")]


def mb_line(mb):
    """All 32 domains, same reason as run_probe_moscxl.schemata_line: a partial
    line leaves the unstated domains at whatever they were."""
    return "MB:" + ";".join(f"{d}={mb if d == P.DOM else MB_MAX}" for d in range(P.NDOM))


def cat_setup_with_mba(vmask, smask):
    """Drop-in replacement for run_probe_moscxl.cat_setup that also sets MB.

    Both resources are read back and compared numerically before the arm runs.
    resctrl silently keeping an old value has cost this project three gates, and
    MB is a resource neither runner has written before on this host, so it gets
    the same treatment as L3 rather than being trusted."""
    for g in (P.VGRP, P.SGRP):
        P.sh(f"sudo -n mkdir -p {g}")
    P.sudo_write(P.VGRP/"schemata", P.schemata_line(vmask))
    P.sudo_write(P.SGRP/"schemata", P.schemata_line(smask))
    P.sudo_write(P.VGRP/"schemata", mb_line(MB_MAX))     # victim never throttled
    P.sudo_write(P.SGRP/"schemata", mb_line(CUR_MB))
    P.sudo_write(P.VGRP/"cpus_list", P.VCPUS)
    P.sudo_write(P.SGRP/"cpus_list", P.SCPUS)

    got = {}
    for tag, g, wl3, wmb in (("victim", P.VGRP, vmask, MB_MAX),
                             ("streamer", P.SGRP, smask, CUR_MB)):
        txt = (g/"schemata").read_text()
        m3 = re.search(rf"L3:.*?\b{P.DOM}=([0-9a-f]+)", txt)
        mm = re.search(rf"^\s*MB:.*?\b{P.DOM}=(\d+)", txt, re.M)
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
    dst = out / os.environ.get("OUT", "probe_moscxl_mba.jsonl")
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
                r["streamer_mb_nominal_gbps"] = mb / 8.0
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
