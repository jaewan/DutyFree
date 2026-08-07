#!/usr/bin/env python3
"""
Isolation check: does run_amd_matched_warmup.py's WC(W=2)=~12M discrepancy
against the original run_e1_gate.py's A3_wc=~3.6M come from the warmup
duration itself, or from the combined script's structure (two victim calls
sharing one longer-lived aggressor launch, AGG_DUR=40 vs original's 16)?

This is an EXACT structural replica of run_e1_gate.py's A3_wc measurement:
one fresh aggressor launch per rep, AGG_DUR=16, AGG_SETTLE=2, ONE victim
call at W=2. If this reproduces ~3.6M, the discrepancy is caused by the
combined script's structure, not by warmup duration, and the whole
matched-warmup result needs to be redesigned around fresh-aggressor-per-
measurement instead of shared-aggressor-two-calls.
"""
import json, os, subprocess, sys, time, threading

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/wcheck_v"
AGRP = f"{RESCTRL}/wcheck_a"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"

VICTIM_WARMUP = 2
VICTIM_DUR = 8
AGG_DUR = 16
AGG_SETTLE = 2


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def write_schemata(grp, l3, smba="2048"):
    with open(f"{grp}/schemata", "w") as f:
        f.write(f"L3:0={l3}\nSMBA:0={smba}\n")


def read_occ(grp):
    with open(f"{grp}/mon_data/mon_L3_00/llc_occupancy") as f:
        v = f.read().strip()
    return None if v == "Unavailable" else int(v)


def ensure_groups():
    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)
    for g in (VGRP, AGRP):
        os.makedirs(g, exist_ok=True)
    open(f"{VGRP}/cpus_list", "w").write("0")
    open(f"{AGRP}/cpus_list", "w").write("1-7")


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


def occ_sampler(stop_evt, samples):
    while not stop_evt.is_set():
        v = read_occ(VGRP)
        if v is not None:
            samples.append(v)
        time.sleep(0.25)


def run_one(rep, do_wb_cat_before, outf):
    write_schemata(VGRP, "ffff")
    write_schemata(AGRP, "ffff")

    # optionally replay a preceding wb_cat arm first, to test carryover,
    # exactly mirroring the A2->A3 sequence in run_e1_gate.py
    if do_wb_cat_before:
        write_schemata(VGRP, "ff00")
        write_schemata(AGRP, "00ff")
        agg = subprocess.Popen(
            f"{AGGRESSOR} -m wb_load -t 7 -c 1,2,3,4,5,6,7 -N 2 -s 64 -d {AGG_DUR} "
            f"> /tmp/wcheck_precat.log 2>&1", shell=True)
        time.sleep(AGG_SETTLE)
        subprocess.run(f"{VICTIM} -c 0 -w 4096 -P -d {VICTIM_DUR} -W {VICTIM_WARMUP}",
                        shell=True, capture_output=True, text=True)
        agg.wait(timeout=AGG_DUR + 10)
        write_schemata(VGRP, "ffff")
        write_schemata(AGRP, "ffff")

    agg_proc = subprocess.Popen(
        f"{AGGRESSOR} -m wc_ntdqa -t 7 -c 1,2,3,4,5,6,7 -N 2 -s 64 -d {AGG_DUR} "
        f"> /tmp/wcheck_wc.log 2>&1", shell=True)
    time.sleep(AGG_SETTLE)

    stop_evt = threading.Event()
    occ_samples = []
    samp_thread = threading.Thread(target=occ_sampler, args=(stop_evt, occ_samples))
    samp_thread.start()

    vproc = subprocess.run(
        f"{VICTIM} -c 0 -w 4096 -P -d {VICTIM_DUR} -W {VICTIM_WARMUP}",
        shell=True, capture_output=True, text=True)

    stop_evt.set()
    samp_thread.join()
    agg_proc.wait(timeout=AGG_DUR + 10)

    victim_line = next((l for l in vproc.stdout.splitlines() if l.startswith("VICTIM")), "")
    vdata = parse_victim(victim_line)
    cyc_per_iter = (vdata.get("cycles", 0) / vdata["iters"]) if vdata.get("iters") else None
    occ_mean = (sum(occ_samples) / len(occ_samples)) if occ_samples else None

    rec = {"rep": rep, "preceded_by_wb_cat": do_wb_cat_before,
           "cyc_per_iter": cyc_per_iter, "occ_mean": occ_mean}
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(f"  rep={rep:2d} preceded_by_wb_cat={do_wb_cat_before}  cyc/iter={cyc_per_iter:.0f}  occ={occ_mean}",
          flush=True)


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/wc_isolation.jsonl"
    ensure_groups()
    try:
        with open(outpath, "w") as outf:
            for r in range(1, reps + 1):
                run_one(r, False, outf)
            for r in range(1, reps + 1):
                run_one(r, True, outf)
    finally:
        cleanup()
    print(f"DONE -> {outpath}")


if __name__ == "__main__":
    main()
