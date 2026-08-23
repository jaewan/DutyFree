#!/usr/bin/env python3
"""Calibrate what an Intel MBA setting actually delivers, before using it.

The Intel knob is nothing like the AMD one and the two must not be assumed
interchangeable. mos182 reports:

    bandwidth_gran 10   min_bandwidth 10   delay_linear 1   thread_throttle_mode max

so the value is a *percentage* (10..100 in steps of 10), not the 1/8 GB/s unit
moscxl uses -- and `delay_linear 1` says the percentage is translated into a
core-level request delay rather than a bandwidth meter, which is documented to
track the nominal percentage only loosely. So the same rule as on moscxl
applies: measure the mapping, do not assume it.

`thread_throttle_mode max` matters for the arms this feeds: with SMT, a core
takes the *least* throttled of its two threads' groups, so the streamer group
must hold both siblings of every streaming core or the throttle silently does
nothing. SCPUS below does.

Streamer only. No victim, no L3 masking. Writes artifacts/mos182_mba_calib.jsonl.
"""
import json, re, subprocess, sys
from pathlib import Path

RC   = Path("/sys/fs/resctrl")
SGRP = RC/"probe_streamer"
BIN  = Path.home()/"tmp_dutyfree_exp"/"bin"
NDOM = 2                       # two sockets
DOM  = 1                       # streamer's socket
SCPUS_L = "33,34,35,36,37,38,39,40"
SCPUS   = "33-40,97-104"       # both SMT siblings -- see thread_throttle_mode
SNODE   = 1                    # local DRAM, the arm the 2x2 will use

def sh(c): return subprocess.run(c, shell=True, text=True, capture_output=True)
def w(p, v):
    r = sh(f"echo {v!r} | sudo -n tee {p} >/dev/null")
    if r.returncode: sys.exit(f"write failed {p} <- {v}\n{r.stderr}")

OUT = Path(__file__).resolve().parent.parent / "artifacts" / "mos182_mba_calib.jsonl"
if OUT.exists():
    sys.exit(f"{OUT} exists; move it aside (A6.19).")
fh = open(OUT, "w")

sh(f"sudo -n rmdir {SGRP} 2>/dev/null")
print(f"{'MB set':>8} {'readback':>10} {'GB/s':>8}")
for mb in [100, 90, 80, 70, 60, 50, 40, 30, 20, 10]:
    sh(f"sudo -n mkdir -p {SGRP}")
    w(SGRP/"schemata", "MB:" + ";".join(f"{d}={mb}" for d in range(NDOM)))
    w(SGRP/"cpus_list", SCPUS)
    txt = (SGRP/"schemata").read_text()
    # Intel pads MB values with a leading space ("MB:0= 100;1= 100"); AMD does
    # not. Same class of host-dependent readback bug as the 0fff/fff one, in the
    # same check. Allow whitespace and compare numerically.
    m = re.search(rf"^\s*MB:.*?\b{DOM}=\s*(\d+)", txt, re.M)
    got = m.group(1) if m else "??"
    if got == "??" or int(got) != mb:
        sys.exit(f"MBA NOT APPLIED: wanted {mb}, schemata says\n{txt}")
    p = subprocess.Popen([str(BIN/"aggressor"), "-m", "wb_load", "-t", "8",
                          "-c", SCPUS_L, "-d", "4", "-N", str(SNODE)],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    out, _ = p.communicate(timeout=60)
    bw = dict(re.findall(r"(\w+)=([-\w.]+)", out)).get("bw_gbps", "?")
    print(f"{mb:>8} {got:>10} {bw:>8}", flush=True)
    fh.write(json.dumps({"mb_set": mb, "mb_readback": int(got),
                         "bw_gbps": float(bw) if bw != "?" else None,
                         "threads": 8, "node": SNODE, "dur_s": 4},
                        sort_keys=True) + "\n"); fh.flush()
    sh(f"sudo -n rmdir {SGRP} 2>/dev/null")
fh.close()
print(f"\nwrote {OUT}")
