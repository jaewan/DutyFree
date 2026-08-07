#!/usr/bin/env python3
"""
E1 AMD arms A4 (lookups-only, with/without CAT) and A5 (fills+churn, no CXL,
local-DRAM >L3 buffer) -- extends run_e1_gate.py's methodology (rep-
interleaved, n>=12, victim-side counters, resctrl MBM verification).

A0_quiescent is re-included here (not reused from the gate run) so this is a
self-contained comparison set measured in the same session/thermal state as
A4/A5.

A4_nocat / A4_cat: 7 threads on cpus1-7 re-stream a SHARED 8 MiB local-DRAM
  buffer (< 16 MiB per-CCX L3) via lookups_aggressor -- after warm-up, should
  be L3-resident (near-zero MBM bytes). Verify that explicitly per rep.
A5_local: 7 threads on cpus1-7 stream a >64 MiB LOCAL DRAM (node 0) buffer via
  the existing aggressor's wb_local mode -- fills+churn without any CXL path,
  for comparison against A1 (CXL) at matched-ish bandwidth.
"""
import json, os, subprocess, sys, time, threading, signal

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/h3v"
AGRP = f"{RESCTRL}/h3a"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"
LOOKUPS_AGG = f"{BIN}/lookups_aggressor"

# Raw PMU encodings, not perf alias names -- see PHASE2_AMD_WARMUP_CHECK.md
# and run_e1_gate.py for why (linux-tools-common silently dropped these
# AMD Zen4 aliases on 2026-08-06). Sourced from AMD's own pmu-events JSON
# (arch/x86/amdzen4/cache.json): l3_lookup_state.l3_hit=rfe04,
# .l3_miss=r0104, .all_coherent_accesses_to_l3=rff04,
# l3_xi_sampled_latency.near_cache=r04ac, .dram_near=r01ac.
PERF_EVENTS = "rfe04,r0104,rff04,r04ac,r01ac"

VICTIM_WARMUP = 2
VICTIM_DUR = 8
AGG_DUR = 16
AGG_SETTLE = 2

# name: (agg_cmd_template_or_None, victim_L3, agg_L3)
# NOTE on A4 buffer size: an 8 MiB shared buffer exactly fills an 8-way/8 MiB
# CAT slice with zero associativity slack, causing real conflict-miss fill
# traffic under A4_cat (observed ~8.4 GB/s MBM in a pilot, not near-zero).
# Shrunk to 4 MiB (comfortably fits both the full 16-way/16 MiB and the
# 8-way/8 MiB CAT slice) so nocat/cat are a clean apples-to-apples pair.
# NOTE on A5: added a bandwidth-matched variant (-R throttle) alongside the
# uncapped one, since uncapped local-DRAM streams at ~45 GB/s (7T), not the
# ~24 GB/s A1 CXL rate the mission wants for the matched-BW comparison.
ARMS = {
    "A0_quiescent":  (None, "ffff", "ffff"),
    "A4_nocat":      (f"{LOOKUPS_AGG} -t 7 -c 1,2,3,4,5,6,7 -s 4 -d {AGG_DUR} -n 0", "ffff", "ffff"),
    "A4_cat":        (f"{LOOKUPS_AGG} -t 7 -c 1,2,3,4,5,6,7 -s 4 -d {AGG_DUR} -n 0", "ff00", "00ff"),
    "A5_local":      (f"{AGGRESSOR} -m wb_local -t 7 -c 1,2,3,4,5,6,7 -N 0 -s 64 -d {AGG_DUR}", "ffff", "ffff"),
    "A5_local_bwm":  (f"{AGGRESSOR} -m wb_local -t 7 -c 1,2,3,4,5,6,7 -N 0 -s 64 -d {AGG_DUR} -R 3450", "ffff", "ffff"),
}
ARM_ORDER = ["A0_quiescent", "A4_nocat", "A4_cat", "A5_local", "A5_local_bwm"]


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def write_schemata(grp, l3, smba="2048"):
    with open(f"{grp}/schemata", "w") as f:
        f.write(f"L3:0={l3}\nSMBA:0={smba}\n")


def read_mbm(grp):
    with open(f"{grp}/mon_data/mon_L3_00/mbm_total_bytes") as f:
        return int(f.read().strip())


def read_occ(grp):
    with open(f"{grp}/mon_data/mon_L3_00/llc_occupancy") as f:
        return int(f.read().strip())


def ensure_groups():
    sh("pkill -f 'bin/aggressor' 2>/dev/null; pkill -f 'bin/lookups_aggressor' 2>/dev/null")
    time.sleep(0.3)
    sh("pkill -9 -f 'bin/aggressor' 2>/dev/null; pkill -9 -f 'bin/lookups_aggressor' 2>/dev/null")
    for g in (VGRP, AGRP):
        os.makedirs(g, exist_ok=True)
    open(f"{VGRP}/cpus_list", "w").write("0")
    open(f"{AGRP}/cpus_list", "w").write("1-7")


def cleanup():
    sh("pkill -f 'bin/aggressor' 2>/dev/null; pkill -f 'bin/lookups_aggressor' 2>/dev/null")
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


def parse_agg_bw(text):
    for line in text.splitlines():
        if line.startswith("RESULT"):
            for tok in line.split():
                if tok.startswith("bw_gbps="):
                    return float(tok.split("=", 1)[1])
    return None


def parse_perf(text):
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        val, event = parts[0], parts[2]
        try:
            out[event] = int(val) if val not in ("<not counted>", "<not supported>") else None
        except ValueError:
            out[event] = None
    return out


def occ_sampler(stop_evt, samples):
    while not stop_evt.is_set():
        try:
            samples.append(read_occ(VGRP))
        except (FileNotFoundError, ValueError):
            pass
        time.sleep(0.25)


def run_one(arm_name, rep, outf):
    agg_cmd, vL3, aL3 = ARMS[arm_name]
    write_schemata(VGRP, vL3)
    write_schemata(AGRP, aL3)

    agg_proc = None
    agg_log = f"/tmp/e1a4a5_agg_{arm_name}_{rep}.log"
    mbm_start = mbm_end = t_agg_start = t_agg_end = None

    if agg_cmd is not None:
        mbm_start = read_mbm(AGRP)
        t_agg_start = time.time()
        agg_proc = subprocess.Popen(f"{agg_cmd} > {agg_log} 2>&1", shell=True)
        time.sleep(AGG_SETTLE)

    perf_dur = VICTIM_WARMUP + VICTIM_DUR + 1
    perf_out = f"/tmp/e1a4a5_perf_{arm_name}_{rep}.csv"
    perf_proc = subprocess.Popen(
        f"perf stat -e {PERF_EVENTS} -C 0 -x, -o {perf_out} -- sleep {perf_dur}", shell=True)
    time.sleep(0.2)

    stop_evt = threading.Event()
    occ_samples = []
    samp_thread = threading.Thread(target=occ_sampler, args=(stop_evt, occ_samples))
    samp_thread.start()

    vproc = subprocess.run(
        f"{VICTIM} -c 0 -w 4096 -P -d {VICTIM_DUR} -W {VICTIM_WARMUP}",
        shell=True, capture_output=True, text=True)

    stop_evt.set()
    samp_thread.join()
    perf_proc.wait(timeout=perf_dur + 5)

    victim_line = next((l for l in vproc.stdout.splitlines() if l.startswith("VICTIM")), "")
    vdata = parse_victim(victim_line)

    agg_bw_self = None
    if agg_proc is not None:
        agg_proc.wait(timeout=AGG_DUR + 10)
        t_agg_end = time.time()
        mbm_end = read_mbm(AGRP)
        with open(agg_log) as f:
            agg_bw_self = parse_agg_bw(f.read())

    mbm_bw_gbps = None
    if mbm_start is not None:
        mbm_bw_gbps = (mbm_end - mbm_start) / (t_agg_end - t_agg_start) / 1e9

    with open(perf_out) as f:
        perf_data = parse_perf(f.read())

    rec = {
        "arm": arm_name, "rep": rep,
        "victim": vdata,
        "cyc_per_iter": (vdata.get("cycles", 0) / vdata["iters"]) if vdata.get("iters") else None,
        "agg_bw_self_gbps": agg_bw_self,
        "agg_mbm_bw_gbps": mbm_bw_gbps,
        "victim_llc_occ_bytes": {
            "n": len(occ_samples),
            "mean": sum(occ_samples) / len(occ_samples) if occ_samples else None,
        },
        "l3_perf_caveat": "perf stat -C 0 window covers victim warmup+measurement (not measurement-only)",
        "l3_perf": perf_data,
    }
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(f"  {arm_name:12s} rep={rep:2d}  cyc/iter={rec['cyc_per_iter']:.0f}  "
          f"agg_bw(self)={agg_bw_self}  agg_bw(mbm)={mbm_bw_gbps}  "
          f"occ_mean={rec['victim_llc_occ_bytes']['mean']}", flush=True)

    for f in (agg_log, perf_out):
        try:
            os.remove(f)
        except OSError:
            pass


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/e1a4a5_raw.jsonl"

    def handle_sigterm(signum, frame):
        cleanup()
        sys.exit(1)
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    ensure_groups()
    try:
        with open(outpath, "w") as outf:
            for r in range(1, reps + 1):
                for arm in ARM_ORDER:
                    run_one(arm, r, outf)
    finally:
        cleanup()
    print(f"DONE -> {outpath}")


if __name__ == "__main__":
    main()
