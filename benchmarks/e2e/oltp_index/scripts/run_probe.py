#!/usr/bin/env python3
"""G-probe: does an L2-resident, low-MLP victim take a CAT-irrecoverable tax?

Zero new victim code. `victim -P` is already a random pointer chase over 64 B
nodes on a Fisher-Yates Hamiltonian cycle, which is the victim shape
OLTP_INDEX_DESIGN.md section 1 derives from the gem5 decomposition. Sized
L2-resident and run against a CXL streamer with and without CAT, it tests the
design's central claim before any Masstree code is written.

Host: mos182 only (this runner hardcodes its socket-1 placement, because the
CXL there is near socket 1 -- the mirror of mos181).

Arms, all with the same victim:
  quiescent      victim alone
  WB_cxl         streamer 8 threads on node 2, no CAT
  WB_cxl_CAT12   same, victim granted 12 of 15 ways (48 MiB), streamer 3
  WB_cxl_CAT1    same, victim granted  1 of 15 ways ( 4 MiB), streamer 14
  WB_local       streamer 8 threads on node 1, no CAT (bandwidth-matched:
                 8 cores pull ~24 GB/s from either node on this host, so this
                 separates "CXL" from "bandwidth")

The victim's working set is 1 MiB. Every CAT grant above, including the 1-way
one, is at least 4x that -- so if the tax survives CAT, it cannot be because
the victim was denied capacity.

CMT is read in every arm, including the un-partitioned ones, so occupancy is
comparable across arms. Both groups always exist; the no-CAT arms simply give
both the full mask.
"""
import json, os, re, subprocess, sys, time
from pathlib import Path

RC       = Path("/sys/fs/resctrl")
VGRP, SGRP = RC/"probe_victim", RC/"probe_streamer"
BIN      = Path.home()/"tmp_dutyfree_exp"/"bin"
DOM      = 1                      # socket 1 == L3 domain 1 on mos182
VCPU     = 32                     # victim core (socket 1)
VCPUS    = "32,96"                # + SMT sibling
SCPUS_L  = "33,34,35,36,37,38,39,40"
SCPUS    = "33-40,97-104"
WS_LIST  = [int(x) for x in os.environ.get("WS_LIST", "1024").split(",")]
WARMUP, DUR = 3, 5
NREPS    = int(os.environ.get("NREPS", "10"))
FULL     = "7fff"                 # 15 ways

ARMS = [
    # name,          stream_node, victim_mask, streamer_mask
    ("quiescent",    None, FULL,   FULL),
    ("WB_cxl",       2,    FULL,   FULL),
    ("WB_cxl_CAT12", 2,    "0fff", "7000"),
    ("WB_cxl_CAT1",  2,    "0001", "7ffe"),
    ("WB_local",     1,    FULL,   FULL),
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

def cat_setup(vmask, smask):
    for g in (VGRP, SGRP):
        sh(f"sudo -n mkdir -p {g}")
    # Write only the L3 line; MB and L2 lines keep their defaults.
    sudo_write(VGRP/"schemata", f"L3:0={FULL};{DOM}={vmask}")
    sudo_write(SGRP/"schemata", f"L3:0={FULL};{DOM}={smask}")
    sudo_write(VGRP/"cpus_list", VCPUS)
    sudo_write(SGRP/"cpus_list", SCPUS)
    # Read back and verify, rather than assume. resctrl silently keeping an
    # old mask has cost this project three gates.
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
            sys.exit(f"CAT NOT APPLIED for {tag}: wanted {want}, schemata says {got[tag]}\n{txt}")
    return got

def cat_teardown():
    for g in (VGRP, SGRP):
        sh(f"sudo -n rmdir {g} 2>/dev/null")

def occ(grp):
    f = grp/"mon_data"/f"mon_L3_{DOM:02d}"/"llc_occupancy"
    try:
        return int(f.read_text().strip()) / 1024.0 / 1024.0     # MiB
    except Exception:
        return None

def foreign():
    out = sh("ps -eo pcpu=,etimes=,comm=").stdout.splitlines()
    bad = []
    for ln in out:
        f = ln.split(None, 2)
        if len(f) < 3:
            continue
        pcpu, et, comm = float(f[0]), int(f[1]), f[2].strip()
        if pcpu >= 20.0 and et >= 10 and comm not in BENIGN:
            bad.append((comm, pcpu))
    return bad

def parse(line_re, text, cast=float):
    d = {}
    for k, v in re.findall(r"(\w+)=([-\w.]+)", text):
        d[k] = v
    return d


def run_arm(name, snode, vmask, smask, WS_KB):
    fr = foreign()
    if fr:
        return {"arm": name, "valid": False, "why": f"foreign load {fr}"}
    applied = cat_setup(vmask, smask)

    vp = subprocess.Popen(
        [str(BIN/"victim"), "-P", "-c", str(VCPU), "-n", "1",
         "-w", str(WS_KB), "-d", str(DUR), "-W", str(WARMUP)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

    sp = None
    if snode is not None:
        time.sleep(1.0)                       # victim-first arrival
        sp = subprocess.Popen(
            [str(BIN/"aggressor"), "-m", "wb_load", "-t", "8", "-c", SCPUS_L,
             "-d", str(WARMUP + DUR + 3), "-N", str(snode)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

    # sample occupancy in the middle of the victim's measured window
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

    v = parse(None, vout)
    s = parse(None, sout) if sout else {}
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
    dst = out / os.environ.get("OUT", "probe_mos182.jsonl")
    if dst.exists():
        sys.exit(f"{dst} exists. Move it aside; this script does not append to "
                 "a file it did not create in this run (A6.19).")
    recs = []
    with open(dst, "w") as fh:
        for rep in range(1, NREPS + 1):
          for WS_KB in WS_LIST:
            for (name, snode, vm, sm) in ARMS:          # rep-interleaved
                r = run_arm(name, snode, vm, sm, WS_KB)
                r["rep"] = rep
                r["ws_kb"] = WS_KB
                fh.write(json.dumps(r, sort_keys=True) + "\n"); fh.flush()
                recs.append(r)
                tag = (f"{r['cyc_per_access']:7.2f} cyc  L2miss {r['l2_miss_rate']:5.2f}%  "
                       f"occ {r['victim_occ_mib']:.1f}/{r['streamer_occ_mib']:.1f} MiB  "
                       f"bw {r['stream_gbps'] or 0:.1f}") if r["valid"] else f"INVALID: {r['why']}"
                print(f"rep{rep:2d} ws{WS_KB:<6d} {name:14s} {tag}", flush=True)
    print(f"\nwrote {dst}")


if __name__ == "__main__":
    try:
        main()
    finally:
        cat_teardown()
