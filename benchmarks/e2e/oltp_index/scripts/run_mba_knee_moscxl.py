#!/usr/bin/env python3
"""Where exactly is the knee for CAT12 + MBA? The L5 cost figure depends on it.

run_mba_moscxl.py samples the combined arm at only two throttle levels, 8.65
and 1.98 GB/s, and the victim is fully recovered at both. That bounds the knee
from below but not from above: the cheapest MBA setting that works with CAT12
may be much higher than 8.65 GB/s, and the whole "what does the deployed
alternative cost the streamer" number turns on which it is. Reporting 35%
bandwidth retained when the true answer is 62% would understate how well the
existing mechanisms already do, in the direction that flatters this project.

So: fill in the CAT12 curve above 8.65 GB/s. MBA192 is nominally 24 GB/s, above
what 7 cores can pull here, and is therefore an unthrottled control that should
reproduce the plain CAT12 arm.

Arms and plumbing are run_mba_moscxl's, overridden only in the list.

RESULT (recorded after the run, because the prediction above was wrong): the
knee is far higher than 62%. MBA192 is *not* an unthrottled control -- it costs
the streamer 4% of delivered bandwidth (24.5 -> 23.6 GB/s) and that is enough
to take the CAT12 tax from 13.3x to 1.08x. Since the "unthrottled control"
prediction failed, the arm cannot serve as its own control; run_mba_knee2 adds
genuinely non-binding settings (256, 224) to check that it is the cap doing the
work and not the act of arming MBA. See GPROBE_OUTCOME.md 5.6.
"""
import os
import run_mba_moscxl as M

M.ARMS = [
    ("quiescent",     None, M.P.FULL, M.P.FULL, M.MB_MAX),
    ("CAT12",         0,    "0fff", "f000", M.MB_MAX),
    ("CAT12_MBA192",  0,    "0fff", "f000", 192),   # ~24 GB/s: above the ceiling
    ("CAT12_MBA160",  0,    "0fff", "f000", 160),   # ~19.6
    ("CAT12_MBA128",  0,    "0fff", "f000", 128),   # ~15.4
    ("CAT12_MBA96",   0,    "0fff", "f000",  96),   # ~11.6
]
M.WS_LIST = [int(x) for x in os.environ.get("WS_LIST", "8192,65536").split(",")]
os.environ.setdefault("OUT", "probe_moscxl_mba_knee.jsonl")

if __name__ == "__main__":
    try:
        M.main()
    finally:
        M.P.cat_teardown()
