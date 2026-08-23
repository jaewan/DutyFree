#!/usr/bin/env python3
"""G-probe on moscxl (EPYC 9754 Bergamo) -- the harsh-capacity replication.

mos182 returned a null: an L2-resident pointer chase is completely unaffected
(0.00% L2 miss, bit-identical cyc/access) by a co-resident streamer that holds
41 MiB of its 60 MiB LLC. That kills the OLTP-index premise ON SPR. Before the
premise is declared dead in general it has to be tried where it is most likely
to be true, and that is here:

    host     private L2   shared LLC   cores sharing   LLC : L2 ratio
    mos182   2 MiB        60 MiB       32              30 : 1
    moscxl   1 MiB        16 MiB        8              16 : 1   <-- harsher

7 streaming cores against a 16 MiB L3 with 1 MiB per way will annihilate the
L3. If private-L2 back-invalidation exists anywhere in this fleet, it is here.

Deliberately NOT a rescue attempt for the Intel result. mos182's outcome stands
on its own and is reported unconditionally; this only decides whether the
finding is "SPR does not back-invalidate" or "shipping server LLCs do not
back-invalidate", which are very different claims.

Structural note: Zen's L3 is a VICTIM cache, so the victim's L2-resident lines
have essentially no L3 footprint to begin with, and CMT occupancy for an
L2-resident victim should read near zero even when quiescent. That is expected
here and is not the streamer evicting anything.

Placement: victim cpu0, streamer cpus 1-7 -- the other 7 physical cores of
cpu0's own CCX (0-7,256-263), which is the only way to share L3 on this part.
Cross-CCX cores share nothing but memory and would test nothing.
"""
import json, os, re, subprocess, sys, time
from pathlib import Path

RC       = Path("/sys/fs/resctrl")
VGRP, SGRP = RC/"probe_victim", RC/"probe_streamer"
BIN      = Path.home()/"tmp_dutyfree_exp"/"bin"
DOM      = 0                      # cpu0's L3 domain (one per CCX; 32 total)
NDOM     = 32
VCPU     = 0
VCPUS    = "0,256"                # + SMT sibling
SCPUS_L  = "1,2,3,4,5,6,7"        # 7 physical cores, same CCX
SCPUS    = "1-7,257-263"
VNODE    = 0                      # victim memory: local DDR
STHREADS = 7
WS_LIST  = [int(x) for x in os.environ.get("WS_LIST", "256,1024,8192,65536").split(",")]
WARMUP, DUR = 3, 5
NREPS    = int(os.environ.get("NREPS", "3"))
FULL     = "ffff"                 # 16 ways, 1 MiB each

ARMS = [
    # name,            stream_node, victim_mask, streamer_mask
    ("quiescent",      None, FULL,   FULL),
    ("WB_local",       0,    FULL,   FULL),   # local DDR streamer
    ("WB_cxl",         2,    FULL,   FULL),   # CXL streamer (SLIT says 255; it works)
    ("WB_local_CAT12", 0,    "0fff", "f000"), # victim 12 MiB, streamer 4 MiB
    ("WB_local_CAT1",  0,    "0001", "fffe"), # victim  1 MiB, streamer 15 MiB
    ("CAT1_nostream",  None, "0001", "fffe"), # separates CAT starvation from co-run
]
BENIGN = {"sshd","bash","sh","ps","python3","claude","node","tmux","systemd",
          "kworker","ksoftirqd","migration","rcu_sched","kthreadd","victim",
          "aggressor","sudo","awk","seq","grep"}


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, text=True, capture_output=True, **kw)

def sudo_write(path, val):
    r = sh(f"echo {val!r} | sudo -n tee {path} >/dev/null")
    if r.returncode:
        sys.exit(f"resctrl write failed: {path} <- {val}\n{r.stderr}")

def schemata_line(mask):
    """All 32 domains explicitly. Only DOM is constrained; the rest stay full.
    mos182's runner could write just two domains because it has two; here a
    partial line would leave 30 domains unstated."""
    return "L3:" + ";".join(f"{d}={mask if d == DOM else FULL}" for d in range(NDOM))

def cat_setup(vmask, smask):
    for g in (VGRP, SGRP):
        sh(f"sudo -n mkdir -p {g}")
    sudo_write(VGRP/"schemata", schemata_line(vmask))
    sudo_write(SGRP/"schemata", schemata_line(smask))
    sudo_write(VGRP/"cpus_list", VCPUS)
    sudo_write(SGRP/"cpus_list", SCPUS)
    got = {}
    for tag, g, want in (("victim", VGRP, vmask), ("streamer", SGRP, smask)):
        txt = (g/"schemata").read_text()
        m = re.search(rf"L3:.*?\b{DOM}=([0-9a-f]+)", txt)
        got[tag] = m.group(1) if m else "??"
        # Compare numerically, not as strings. AMD's resctrl normalises "0fff"
        # to "fff" while Intel's preserves the leading zero, so a string compare
        # makes this readback -- the check whose whole purpose is to catch a
        # silently-unapplied mask -- itself host-dependent.
        if got[tag] == "??" or int(got[tag], 16) != int(want, 16):
            sys.exit(f"CAT NOT APPLIED for {tag}: wanted {want}, got {got[tag]}\n{txt}")
    return got

def cat_teardown():
    for g in (VGRP, SGRP):
        sh(f"sudo -n rmdir {g} 2>/dev/null")

def occ(grp):
    f = grp/"mon_data"/f"mon_L3_{DOM:02d}"/"llc_occupancy"
    try:
        return int(f.read_text().strip()) / 1024.0 / 1024.0
    except Exception:
        return None

def foreign():
    bad = []
    for ln in sh("ps -eo pcpu=,etimes=,comm=").stdout.splitlines():
        f = ln.split(None, 2)
        if len(f) < 3:
            continue
        pcpu, et, comm = float(f[0]), int(f[1]), f[2].strip()
        if pcpu >= 20.0 and et >= 10 and comm not in BENIGN:
            bad.append((comm, pcpu))
    return bad

def parse(text):
    return dict(re.findall(r"(\w+)=([-\w.]+)", text))

def run_arm(name, snode, vmask, smask, WS_KB):
    fr = foreign()
    if fr:
        return {"arm": name, "valid": False, "why": f"foreign load {fr}"}
    applied = cat_setup(vmask, smask)

    vp = subprocess.Popen(
        [str(BIN/"victim"), "-P", "-c", str(VCPU), "-n", str(VNODE),
         "-w", str(WS_KB), "-d", str(DUR), "-W", str(WARMUP)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

    sp = None
    if snode is not None:
        time.sleep(1.0)                       # victim-first arrival
        sp = subprocess.Popen(
            [str(BIN/"aggressor"), "-m", "wb_load", "-t", str(STHREADS),
             "-c", SCPUS_L, "-d", str(WARMUP + DUR + 3), "-N", str(snode)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

    time.sleep((WARMUP - 1.0 if snode is not None else WARMUP) + DUR / 2.0)
    vocc, socc = occ(VGRP), occ(SGRP)

    vout, _ = vp.communicate(timeout=60)
    sout = ""
    if sp:
        try:
            sout, _ = sp.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            sp.kill(); sout, _ = sp.communicate()
    cat_teardown()

    v = parse(vout)
    s = parse(sout) if sout else {}
    if "cyc_per_access" not in v:
        return {"arm": name, "valid": False, "why": "victim produced no result",
                "raw": vout[:200]}
    if v.get("l2_counters") != "ok":
        return {"arm": name, "valid": False, "why": "L2 counters SUSPECT (D1)"}
    if snode is not None and float(s.get("bw_gbps", 0)) <= 0:
        return {"arm": name, "valid": False, "why": "streamer produced no traffic"}

    return {"arm": name, "valid": True,
            "cyc_per_access": float(v["cyc_per_access"]),
            "ipc": float(v["ipc"]),
            "l2_miss_rate": float(v["l2_miss_rate"]),
            "l2_hit": int(v["l2_hit"]), "l2_miss": int(v["l2_miss"]),
            "victim_occ_mib": vocc, "streamer_occ_mib": socc,
            "victim_mask": applied["victim"], "streamer_mask": applied["streamer"],
            "stream_node": snode,
            "stream_gbps": float(s["bw_gbps"]) if s else None}

def main():
    out = Path(__file__).resolve().parent.parent / "artifacts"
    out.mkdir(exist_ok=True)
    dst = out / os.environ.get("OUT", "probe_moscxl.jsonl")
    if dst.exists():
        sys.exit(f"{dst} exists. Move it aside (A6.19).")
    with open(dst, "w") as fh:
        for rep in range(1, NREPS + 1):
          for WS_KB in WS_LIST:
            for (name, snode, vm, sm) in ARMS:
                r = run_arm(name, snode, vm, sm, WS_KB)
                r["rep"] = rep; r["ws_kb"] = WS_KB
                fh.write(json.dumps(r, sort_keys=True) + "\n"); fh.flush()
                tag = (f"{r['cyc_per_access']:7.2f} cyc  L2miss {r['l2_miss_rate']:5.2f}%  "
                       f"occ {r['victim_occ_mib']:.1f}/{r['streamer_occ_mib']:.1f} MiB  "
                       f"bw {r['stream_gbps'] or 0:.1f}") if r["valid"] else f"INVALID: {r['why']}"
                print(f"rep{rep:2d} ws{WS_KB:<6d} {name:15s} {tag}", flush=True)
    print(f"\nwrote {dst}")

if __name__ == "__main__":
    try:
        main()
    finally:
        cat_teardown()
