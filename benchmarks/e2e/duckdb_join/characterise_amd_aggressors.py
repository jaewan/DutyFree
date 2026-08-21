#!/usr/bin/env python3
"""AMD (Zen4c, EPYC 9754) aggressor characterisation for the DuckDB co-run.

Instrument characterisation only: no victim runs here. Records, per
(mode, threads): self-reported bandwidth, steady CCX-L3 occupancy from CMT,
and MBM total-bytes rate -- the last because A4 records a case where an arm
moved MORE total controller traffic than write-back while taxing far less,
which self-reported read bandwidth cannot show.
"""
import json, re, subprocess, sys, time
from pathlib import Path

AGG = Path.home() / "tmp_dutyfree_exp/bin/aggressor"
FB = Path.home() / "tmp_dutyfree_exp/bin/amd_flushbehind_aggressor"
G = Path("/sys/fs/resctrl/aggchar")
DOMAIN = 1                      # cpu8-15 share L3 id=1
MON = G / "mon_data" / f"mon_L3_{DOMAIN:02d}"
RES = re.compile(r"bw_gbps=([0-9.]+)")
CORES = [9, 10, 11, 12, 13, 14, 15]
DUR, SETTLE, WINDOW = 40, 22, 12

def sudo(c): subprocess.run(["sudo", "-n", "sh", "-c", c], check=True)
def rd(p, d=0):
    try: return int(Path(p).read_text().strip())
    except Exception: return d

sudo(f"mkdir -p {G}")
out = []
try:
    for mode in ["wb_load", "wb_prefetchnta", "flushbehind_f0", "flushbehind_f256"]:
        for nt in [1, 2, 3, 4, 5, 6, 7]:
            cores = ",".join(str(c) for c in CORES[:nt])
            sudo(f"echo {cores} > {G}/cpus_list")
            if mode.startswith("flushbehind"):
                f = mode.split("_f")[1]
                cmd = [str(FB), "-t", str(nt), "-c", cores, "-N", "2",
                       "-s", "512", "-d", str(DUR), "-f", f]
            else:
                cmd = [str(AGG), "-m", mode, "-t", str(nt), "-c", cores,
                       "-N", "2", "-s", "512", "-d", str(DUR)]
            p = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)
            time.sleep(SETTLE)
            occ = [rd(MON / "llc_occupancy")]
            mb0, t0 = rd(MON / "mbm_total_bytes"), time.time()
            time.sleep(WINDOW)
            occ.append(rd(MON / "llc_occupancy"))
            mb1, t1 = rd(MON / "mbm_total_bytes"), time.time()
            txt = p.communicate()[0] or ""
            m = RES.search(txt)
            r = dict(mode=mode, threads=nt, cores=cores,
                     bw_self_gbps=float(m.group(1)) if m else None,
                     occ_mib=round(sum(occ) / len(occ) / 2**20, 3),
                     occ_frac=round(sum(occ) / len(occ) / (16 * 2**20), 3),
                     mbm_total_gbps=round((mb1 - mb0) / (t1 - t0) / 1e9, 3))
            out.append(r)
            print(json.dumps(r), flush=True)
finally:
    subprocess.run(["sudo", "-n", "rmdir", str(G)], check=False)
Path.home().joinpath("amd_char.jsonl").write_text(
    "\n".join(json.dumps(r) for r in out) + "\n")
print("WROTE ~/amd_char.jsonl", flush=True)
