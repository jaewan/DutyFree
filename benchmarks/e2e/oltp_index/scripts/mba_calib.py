#!/usr/bin/env python3
"""Calibrate what an AMD MBA setting actually delivers, before using it.

The kernel exposes MB in units this project has not previously used on AMD
(max 2048, gran 1, delay_linear 0), and the docs are ambiguous between MB/s and
1/8 GB/s -- 2048 would mean 2 GB/s under the first reading, which cannot be
right when the unthrottled streamer already does 24.7 GB/s. So the mapping is
measured rather than assumed: this is the only thing this script does.

Streamer only. No victim, no L3 masking.
"""
import json, re, subprocess, sys, time
from pathlib import Path

RC   = Path("/sys/fs/resctrl")
SGRP = RC/"probe_streamer"
BIN  = Path.home()/"tmp_dutyfree_exp"/"bin"
NDOM = 32
SCPUS_L = "1,2,3,4,5,6,7"
SCPUS   = "1-7,257-263"

def sh(c): return subprocess.run(c, shell=True, text=True, capture_output=True)
def w(p, v):
    r = sh(f"echo {v!r} | sudo -n tee {p} >/dev/null")
    if r.returncode: sys.exit(f"write failed {p} <- {v}\n{r.stderr}")

def line(res, val, full):
    return res + ":" + ";".join(f"{d}={val}" for d in range(NDOM))

OUT = Path(__file__).resolve().parent.parent / "artifacts" / "moscxl_mba_calib.jsonl"
if OUT.exists():
    sys.exit(f"{OUT} exists; move it aside (A6.19).")
fh = open(OUT, "w")

sh(f"sudo -n rmdir {SGRP} 2>/dev/null")
print(f"{'MB set':>8} {'MB readback':>12} {'GB/s':>8}")
for mb in [2048, 1024, 512, 256, 128, 64, 32, 16, 8]:
    sh(f"sudo -n mkdir -p {SGRP}")
    w(SGRP/"schemata", line("MB", mb, 2048))
    w(SGRP/"cpus_list", SCPUS)
    txt = (SGRP/"schemata").read_text()
    m = re.search(r"^\s*MB:0=(\d+)", txt, re.M)
    got = m.group(1) if m else "??"
    p = subprocess.Popen([str(BIN/"aggressor"), "-m", "wb_load", "-t", "7",
                          "-c", SCPUS_L, "-d", "4", "-N", "0"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    out, _ = p.communicate(timeout=60)
    bw = dict(re.findall(r"(\w+)=([-\w.]+)", out)).get("bw_gbps", "?")
    print(f"{mb:>8} {got:>12} {bw:>8}", flush=True)
    fh.write(json.dumps({"mb_set": mb, "mb_readback": got,
                         "nominal_gbps": mb / 8.0,
                         "bw_gbps": float(bw) if bw != "?" else None,
                         "threads": 7, "node": 0, "dur_s": 4},
                        sort_keys=True) + "\n"); fh.flush()
    sh(f"sudo -n rmdir {SGRP} 2>/dev/null")
fh.close()
print(f"\nwrote {OUT}")
