#!/usr/bin/env python3
"""Is the knee the rate cap, or merely having MBA switched on?

run_mba_knee_moscxl.py found that CAT12 plus a nominal 24 GB/s cap -- which
costs the streamer 4% of its delivered bandwidth, 24.53 -> 23.56 GB/s --
collapses the victim's tax from 13.24x to 1.10x. Read as queueing that is the
expected shape: 7 cores hold the CCX egress at saturation, where latency is a
cliff, and a few percent of rate backs it off the cliff.

But there is a second reading that would make the number worthless: that AMD's
MBA delay-injection machinery perturbs the streamer's issue behaviour whenever
it is armed, whether or not the cap binds. Those two are distinguishable, and
this is the arm that does it.

MB=256 is nominally 32 GB/s. Calibration measured 24.71 GB/s under it -- i.e.
above what 7 cores can pull here, so it does NOT bind and costs nothing. If
CAT12_MBA256 recovers the victim, the recovery is not the rate cap and the "4%"
figure must not be reported. If CAT12_MBA256 looks like plain CAT12, the cap is
doing the work and the knee is real.

224 and 176 bracket the transition either side of 192.
"""
import os
import run_mba_moscxl as M

M.ARMS = [
    ("quiescent",     None, M.P.FULL, M.P.FULL, M.MB_MAX),
    ("CAT12",         0,    "0fff", "f000", M.MB_MAX),
    ("CAT12_MBA256",  0,    "0fff", "f000", 256),   # nominal 32 GB/s: does NOT bind
    ("CAT12_MBA224",  0,    "0fff", "f000", 224),   # nominal 28: should not bind
    ("CAT12_MBA192",  0,    "0fff", "f000", 192),   # nominal 24: barely binds
    ("CAT12_MBA176",  0,    "0fff", "f000", 176),   # nominal 22
]
M.WS_LIST = [int(x) for x in os.environ.get("WS_LIST", "8192").split(",")]
os.environ.setdefault("OUT", "probe_moscxl_mba_knee2.jsonl")

if __name__ == "__main__":
    try:
        M.main()
    finally:
        M.P.cat_teardown()
