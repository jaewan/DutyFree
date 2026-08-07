#!/usr/bin/env python3
"""Check whether the CCX0-vs-rest gap seen in wb_cat also appears in plain
WB (no CAT partition) on CCX1. If WB matches CCX0's ~19.9-20.5x closely,
the anomaly is CAT-specific, not a general CCX0 property."""
import subprocess, time, os, sys, statistics

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/wbccx1_v"
AGRP = f"{RESCTRL}/wbccx1_a"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"

VICTIM_CPU = 8
AGG_CORES = "9,10,11,12,13,14,15"
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


def run_one(name, with_agg, rep):
    write_schemata(VGRP, "ffff")
    write_schemata(AGRP, "ffff")
    agg = None
    if with_agg:
        agg = subprocess.Popen(
            f"{AGGRESSOR} -m wb_load -t 7 -c {AGG_CORES} -N 2 -s 64 -d {AGG_DUR} "
            f"> /tmp/wbccx1_agg.log 2>&1", shell=True)
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
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    ensure_groups()
    q_vals, wb_vals = [], []
    try:
        for r in range(1, reps + 1):
            q_vals.append(run_one("quiescent", False, r))
            wb_vals.append(run_one("wb_nocat", True, r))
    finally:
        cleanup()

    qm, wm = statistics.median(q_vals), statistics.median(wb_vals)
    print(f"\nCCX1 quiescent median: {qm:.0f}")
    print(f"CCX1 wb(no cat) median: {wm:.0f}")
    print(f"CCX1 wb(no cat) tax: {wm/qm:.3f}")
    print("(for comparison: CCX0 original=19.89x, CCX0 v2=20.27-20.44x)")


if __name__ == "__main__":
    main()
