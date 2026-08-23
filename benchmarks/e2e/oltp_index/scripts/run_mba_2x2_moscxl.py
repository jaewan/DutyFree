#!/usr/bin/env python3
"""Complete the 2x2 at the knee: is CAT actually needed once MBA binds?

The conclusion now rests on one cell -- CAT12 + a nominal 24 GB/s cap gives
1.08x while the streamer keeps 96% of its bandwidth. That cell says the
deployed pair is cheap. It does not say the pair is needed: if MBA at the same
barely-binding setting recovers the victim on its own, then CAT contributes
nothing and the story is MBA alone.

Monotonicity already argues CAT is needed -- MBA128 alone (a harder throttle,
61% bandwidth) reads 3.94x, so MBA192 alone should be no better than that --
but the cell the claim rests on should be measured, not inferred from the
neighbouring one.

ws=8192 only: that is the operating point the whole section is about, and the
one with a 0.3% rep spread.
"""
import os
import run_mba_moscxl as M

M.ARMS = [
    ("quiescent",     None, M.P.FULL, M.P.FULL, M.MB_MAX),
    ("WB_local",      0,    M.P.FULL, M.P.FULL, M.MB_MAX),  # neither knob
    ("MBA192",        0,    M.P.FULL, M.P.FULL, 192),        # MBA only, barely binding
    ("MBA176",        0,    M.P.FULL, M.P.FULL, 176),
    ("CAT12",         0,    "0fff", "f000", M.MB_MAX),       # CAT only
    ("CAT12_MBA192",  0,    "0fff", "f000", 192),            # both
]
M.WS_LIST = [8192]
os.environ.setdefault("OUT", "probe_moscxl_mba_2x2.jsonl")

if __name__ == "__main__":
    try:
        M.main()
    finally:
        M.P.cat_teardown()
