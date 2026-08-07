#!/usr/bin/env python3
"""
Diagnostic: is the wb_cat drift specific to CCX0 (cores 0-7, where every
prior measurement in this campaign has run), or does it reproduce on a
different CCX? Replicates the exact A2_wb_cat setup (victim 1 core /
aggressor 7 cores, same-CCX, 8/8 way split) on CCX1 (cores 8-15) instead.
If the tax is similar to CCX0's 9.87x, the effect is general to the box;
if it looks like the historical 7.23x, something specific to CCX0 (its
physical position, e.g. proximity to the IO die / CXL root port) is
implicated.
"""
import json, os, subprocess, sys, time, threading

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/ccx1_v"
AGRP = f"{RESCTRL}/ccx1_a"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"

VICTIM_CPU = 8       # first core of CCX1
AGG_CORES = "9,10,11,12,13,14,15"  # remaining 7 cores of CCX1
VICTIM_WARMUP = 2
VICTIM_DUR = 8
AGG_SETTLE = 2
AGG_DUR = VICTIM_WARMUP + VICTIM_DUR + 4


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def write_schemata(grp, l3, smba="2048"):
    with open(f"{grp}/schemata", "w") as f:
        f.write(f"L3:0={l3}\nSMBA:0={smba}\n")


def ensure_groups():
    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)
    for g in (VGRP, AGRP):
        os.makedirs(g, exist_ok=True)
    open(f"{VGRP}/cpus_list", "w").write(str(VICTIM_CPU))
    open(f"{AGRP}/cpus_list", "w").write(AGG_CORES)


def cleanup():
    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)
    for g in (VGRP, AGRP):
        try:
            os.rmdir(g)
        except OSError:
            pass


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


def run_one(name, vL3, aL3, rep):
    write_schemata(VGRP, vL3)
    write_schemata(AGRP, aL3)
    agg = None
    if name != "quiescent":
        agg = subprocess.Popen(
            f"{AGGRESSOR} -m wb_load -t 7 -c {AGG_CORES} -N 2 -s 64 -d {AGG_DUR} "
            f"> /tmp/ccx1_agg.log 2>&1", shell=True)
        time.sleep(AGG_SETTLE)

    vproc = subprocess.run(
        f"{VICTIM} -c {VICTIM_CPU} -w 4096 -P -d {VICTIM_DUR} -W {VICTIM_WARMUP}",
        shell=True, capture_output=True, text=True)
    line = next((l for l in vproc.stdout.splitlines() if l.startswith("VICTIM")), "")
    vdata = parse_victim(line)
    cyc = (vdata.get("cycles", 0) / vdata["iters"]) if vdata.get("iters") else None

    if agg is not None:
        agg.wait(timeout=AGG_DUR + 10)

    print(f"  {name:10s} rep={rep:2d}  cyc/iter={cyc:.0f}", flush=True)
    return cyc


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    ensure_groups()
    q_vals, cat_vals = [], []
    try:
        for r in range(1, reps + 1):
            q_vals.append(run_one("quiescent", "ffff", "ffff", r))
            cat_vals.append(run_one("wb_cat", "ff00", "00ff", r))
    finally:
        cleanup()

    import statistics
    qm, cm = statistics.median(q_vals), statistics.median(cat_vals)
    print(f"\nCCX1 quiescent median: {qm:.0f}")
    print(f"CCX1 wb_cat median: {cm:.0f}")
    print(f"CCX1 wb_cat tax: {cm/qm:.3f}")
    print(f"(for comparison: CCX0 now=9.87x, CCX0 original=7.23x)")


if __name__ == "__main__":
    main()
