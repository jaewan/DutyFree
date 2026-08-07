#!/usr/bin/env python3
"""
Clean, matched, same-script, same-session comparison: quiescent / WB
(no CAT) / WB+CAT, run on a given CCX (victim = first core, aggressor =
remaining 7 cores of that CCX). Parameterized by CCX index so CCX0 and
CCX1 (or others) can be measured identically, back to back, in one
session -- removes any possibility of the comparison being confounded by
script/session differences.
"""
import subprocess, time, os, sys, statistics

RESCTRL = "/sys/fs/resctrl"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"

VICTIM_WARMUP = 2
VICTIM_DUR = 8
AGG_SETTLE = 2
AGG_DUR = VICTIM_WARMUP + VICTIM_DUR + 4


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def write_schemata(grp, l3, smba="2048"):
    with open(f"{grp}/schemata", "w") as f:
        f.write(f"L3:0={l3}\nSMBA:0={smba}\n")


def parse_victim(line):
    d = {}
    for tok in line.split():
        if "=" in tok:
            k, v = tok.split("=", 1)
            try:
                d[k] = float(v) if "." in v else int(v)
            except ValueError:
                d[k] = v
    return d


def run_one(vgrp, agrp, victim_cpu, agg_cores, name, mode, vL3, aL3, rep):
    write_schemata(vgrp, vL3)
    write_schemata(agrp, aL3)
    agg = None
    if mode is not None:
        agg = subprocess.Popen(
            f"{AGGRESSOR} -m {mode} -t 7 -c {agg_cores} -N 2 -s 64 -d {AGG_DUR} "
            f"> /tmp/ccxcmp_agg.log 2>&1", shell=True)
        time.sleep(AGG_SETTLE)

    vproc = subprocess.run(
        f"{VICTIM} -c {victim_cpu} -w 4096 -P -d {VICTIM_DUR} -W {VICTIM_WARMUP}",
        shell=True, capture_output=True, text=True)
    line = next((l for l in vproc.stdout.splitlines() if l.startswith("VICTIM")), "")
    vdata = parse_victim(line)
    cyc = (vdata.get("cycles", 0) / vdata["iters"]) if vdata.get("iters") else None

    if agg is not None:
        agg.wait(timeout=AGG_DUR + 10)

    print(f"    {name:10s} rep={rep:2d}  cyc/iter={cyc:.0f}", flush=True)
    return cyc


def measure_ccx(ccx_idx, reps):
    base = ccx_idx * 8
    victim_cpu = base
    agg_cores = ",".join(str(base + i) for i in range(1, 8))
    vgrp = f"{RESCTRL}/ccxcmp{ccx_idx}_v"
    agrp = f"{RESCTRL}/ccxcmp{ccx_idx}_a"

    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)
    os.makedirs(vgrp, exist_ok=True)
    os.makedirs(agrp, exist_ok=True)
    open(f"{vgrp}/cpus_list", "w").write(str(victim_cpu))
    open(f"{agrp}/cpus_list", "w").write(agg_cores)

    print(f"  === CCX{ccx_idx} (victim=cpu{victim_cpu}, agg={agg_cores}) ===", flush=True)
    q, wb, wbcat = [], [], []
    try:
        for r in range(1, reps + 1):
            q.append(run_one(vgrp, agrp, victim_cpu, agg_cores, "quiescent", None, "ffff", "ffff", r))
            wb.append(run_one(vgrp, agrp, victim_cpu, agg_cores, "wb", "wb_load", "ffff", "ffff", r))
            wbcat.append(run_one(vgrp, agrp, victim_cpu, agg_cores, "wb_cat", "wb_load", "ff00", "00ff", r))
    finally:
        sh("pkill -f 'bin/aggressor' 2>/dev/null")
        time.sleep(0.3)
        try:
            os.rmdir(vgrp)
        except OSError:
            pass
        try:
            os.rmdir(agrp)
        except OSError:
            pass

    qm, wbm, wbcatm = statistics.median(q), statistics.median(wb), statistics.median(wbcat)
    print(f"  CCX{ccx_idx}: quiescent={qm:.0f}  wb_tax={wbm/qm:.3f}  wb_cat_tax={wbcatm/qm:.3f}"
          f"  cat_benefit={(wbm/qm)/(wbcatm/qm):.3f}x", flush=True)
    return qm, wbm/qm, wbcatm/qm


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    ccxs = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0, 1]
    results = {}
    for ccx in ccxs:
        results[ccx] = measure_ccx(ccx, reps)

    print("\n=== SUMMARY ===")
    print(f"{'CCX':>4s} {'quiescent':>12s} {'wb_tax':>8s} {'wb_cat_tax':>11s} {'cat_benefit':>12s}")
    for ccx, (qm, wbt, wbcatt) in results.items():
        print(f"{ccx:4d} {qm:12.0f} {wbt:8.3f} {wbcatt:11.3f} {wbt/wbcatt:12.3f}")


if __name__ == "__main__":
    main()
