#!/usr/bin/env python3
"""Does the mos182 null survive a much larger snoop-filter footprint?

The matrix used 8 streaming cores. Bandwidth saturates at 4 on this host, so
more threads buy no bandwidth -- but snoop-filter pressure does not scale with
bandwidth, it scales with the aggregate PRIVATE-CACHE footprint of the
streaming cores. 8 cores x 2 MiB = 16 MiB of L2 footprint against a socket
whose 32 cores hold 64 MiB of L2 in total. If SPR's SF is provisioned at
roughly 1-1.5x aggregate private capacity, 16 MiB may simply not pressure it
while 48 MiB would.

That is the strongest remaining way the null could be wrong, and it is cheap to
close. Thread count is the honest way to vary this; the -R pacing throttle
carries a known confound and is not used.

Victim fixed at ws=1024 KB -- L2-resident, the decisive operating point.
No CAT: this asks only whether the streamer can reach the victim's private L2.

    threads   streaming L2 footprint
       8       16 MiB
      16       32 MiB
      24       48 MiB
      31       62 MiB   (all remaining socket-1 cores)
"""
import json, os, re, subprocess, sys, time
from pathlib import Path
import run_probe as P

WS_KB  = int(os.environ.get("WS_KB", "1024"))
NREPS  = int(os.environ.get("NREPS", "3"))
SNODE  = int(os.environ.get("SNODE", "2"))
THREADS = [int(x) for x in os.environ.get("THREADS", "8,16,24,31").split(",")]
FIRST_SCORE = 33          # victim is core 32; socket 1 is 32-63


def arm(nthreads):
    """nthreads=0 means quiescent."""
    fr = P.foreign()
    if fr:
        return {"arm": f"t{nthreads}", "valid": False, "why": f"foreign load {fr}"}
    scpus_l = ",".join(str(FIRST_SCORE + i) for i in range(nthreads)) if nthreads else ""
    # CMT groups with full masks, so occupancy is comparable to the matrix arms
    if nthreads:
        hi = FIRST_SCORE + nthreads - 1
        P.SCPUS = f"{FIRST_SCORE}-{hi},{FIRST_SCORE+64}-{hi+64}"
    applied = P.cat_setup(P.FULL, P.FULL)

    vp = subprocess.Popen(
        [str(P.BIN/"victim"), "-P", "-c", str(P.VCPU), "-n", "1",
         "-w", str(WS_KB), "-d", str(P.DUR), "-W", str(P.WARMUP)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    sp = None
    if nthreads:
        time.sleep(1.0)
        sp = subprocess.Popen(
            [str(P.BIN/"aggressor"), "-m", "wb_load", "-t", str(nthreads),
             "-c", scpus_l, "-d", str(P.WARMUP + P.DUR + 3), "-N", str(SNODE)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

    time.sleep((P.WARMUP - 1.0 if nthreads else P.WARMUP) + P.DUR / 2.0)
    vocc, socc = P.occ(P.VGRP), P.occ(P.SGRP)

    vout, _ = vp.communicate(timeout=90)
    sout = ""
    if sp:
        try:
            sout, _ = sp.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            sp.kill(); sout, _ = sp.communicate()
    P.cat_teardown()

    v = P.parse(None, vout)
    s = P.parse(None, sout) if sout else {}
    if "cyc_per_access" not in v:
        return {"arm": f"t{nthreads}", "valid": False, "why": "victim produced no result"}
    if v.get("l2_counters") != "ok":
        return {"arm": f"t{nthreads}", "valid": False, "why": "L2 counters SUSPECT (D1)"}
    if nthreads and float(s.get("bw_gbps", 0)) <= 0:
        return {"arm": f"t{nthreads}", "valid": False, "why": "streamer produced no traffic"}

    return {"arm": f"t{nthreads}", "valid": True, "threads": nthreads,
            "stream_l2_footprint_mib": nthreads * 2,
            "cyc_per_access": float(v["cyc_per_access"]),
            "ipc": float(v["ipc"]),
            "l2_miss_rate": float(v["l2_miss_rate"]),
            "l2_hit": int(v["l2_hit"]), "l2_miss": int(v["l2_miss"]),
            "victim_occ_mib": vocc, "streamer_occ_mib": socc,
            "stream_node": SNODE if nthreads else None,
            "stream_gbps": float(s["bw_gbps"]) if s else None}


def main():
    out = Path(__file__).resolve().parent.parent / "artifacts"
    out.mkdir(exist_ok=True)
    dst = out / os.environ.get("OUT", "sfpressure.jsonl")
    if dst.exists():
        sys.exit(f"{dst} exists. Move it aside (A6.19).")
    with open(dst, "w") as fh:
        for rep in range(1, NREPS + 1):
            for n in [0] + THREADS:
                r = arm(n)
                r["rep"] = rep; r["ws_kb"] = WS_KB
                fh.write(json.dumps(r, sort_keys=True) + "\n"); fh.flush()
                tag = (f"{r['cyc_per_access']:7.2f} cyc  L2miss {r['l2_miss_rate']:5.2f}%  "
                       f"occ {r['victim_occ_mib']:.1f}/{r['streamer_occ_mib']:.1f} MiB  "
                       f"bw {r['stream_gbps'] or 0:.1f}") if r["valid"] else f"INVALID: {r['why']}"
                print(f"rep{rep:2d} t{n:<3d} ({n*2:2d} MiB L2)  {tag}", flush=True)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    try:
        main()
    finally:
        P.cat_teardown()
