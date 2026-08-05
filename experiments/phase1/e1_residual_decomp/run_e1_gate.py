#!/usr/bin/env python3
"""
E1 AMD reproduction gate: A0 (quiescent) / A1 (WB CXL 7T) / A2 (WB+CAT 8/8) /
A3 (WC CXL 7T), rep-interleaved (A0,A1,A2,A3 repeated), n>=12.

Runs on broker (AMD EPYC 9754). Victim = 4 MiB pointer chase on cpu0.
Aggressor = 7 threads on cpus1-7 (same CCX0), CXL node 2, 64 MB/thread.

Per rep-arm, collects:
  - victim: ipc, l2_miss_rate, cycles, insns, iters, sec (from victim's own
    stdout) -> cycles/iteration = cycles/iters
  - victim RMID llc_occupancy sampled at ~4 Hz across the run (resctrl CMT)
  - aggressor bandwidth: (a) self-reported bw_gbps from aggressor's own
    stdout, (b) independent verification via resctrl MBM (mbm_total_bytes
    delta / elapsed) on the aggressor group -- ground rule #3.
  - AMD L3 uncore PMU events wrapped around the victim's full process
    lifetime (warmup+measurement -- see CAVEAT in RESULTS.md) via
    `perf stat -C 0`: l3_lookup_state.{l3_hit,l3_miss,all_coherent_accesses_to_l3},
    l3_xi_sampled_latency.{near_cache,dram_near}. No probe-filter/back-
    invalidation-specific event exists in this perf event list (Zen4c/
    Bergamo, perf 6.17.13) -- documented, not substituted.

Output: JSON-lines, one record per (arm, rep), appended incrementally.
"""
import json, os, subprocess, sys, time, threading, signal

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/h3v"
AGRP = f"{RESCTRL}/h3a"
BIN = "/home/domin/tmp_dutyfree_exp/bin"  # hardcoded: script runs under sudo, which resets $HOME to /root
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"

PERF_EVENTS = (
    "l3_lookup_state.l3_hit,l3_lookup_state.l3_miss,"
    "l3_lookup_state.all_coherent_accesses_to_l3,"
    "l3_xi_sampled_latency.near_cache,l3_xi_sampled_latency.dram_near"
)

ARMS = {
    # name: (mode_or_None, victim_L3, agg_L3, smba)
    "A0_quiescent": (None,      "ffff", "ffff", "2048"),
    "A1_wb":        ("wb_load", "ffff", "ffff", "2048"),
    "A2_wb_cat":    ("wb_load", "ff00", "00ff", "2048"),
    "A3_wc":        ("wc_ntdqa","ffff", "ffff", "2048"),
}
ARM_ORDER = ["A0_quiescent", "A1_wb", "A2_wb_cat", "A3_wc"]

VICTIM_WARMUP = 2
VICTIM_DUR = 8
AGG_DUR = 16
AGG_SETTLE = 2  # sleep after launching aggressor, before starting victim


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def write_schemata(grp, l3, smba):
    with open(f"{grp}/schemata", "w") as f:
        f.write(f"L3:0={l3}\nSMBA:0={smba}\n")


def read_mbm(grp):
    p = f"{grp}/mon_data/mon_L3_00/mbm_total_bytes"
    with open(p) as f:
        return int(f.read().strip())


def read_occ(grp):
    p = f"{grp}/mon_data/mon_L3_00/llc_occupancy"
    with open(p) as f:
        return int(f.read().strip())


def ensure_groups():
    sh(f"pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)
    sh(f"pkill -9 -f 'bin/aggressor' 2>/dev/null")
    for g in (VGRP, AGRP):
        os.makedirs(g, exist_ok=True)
    with open(f"{VGRP}/cpus_list", "w") as f:
        f.write("0")
    with open(f"{AGRP}/cpus_list", "w") as f:
        f.write("1-7")


def cleanup():
    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)
    try:
        os.rmdir(VGRP)
    except OSError:
        pass
    try:
        os.rmdir(AGRP)
    except OSError:
        pass


def parse_victim(line):
    # VICTIM core=0 ipc=0.0446 l2_miss_rate=85.67 cycles=... insns=... l2_hit=... l2_miss=... iters=... sec=...
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
    # perf stat -x, output: value,unit,event,...
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        val, unit, event = parts[0], parts[1], parts[2]
        try:
            out[event] = int(val) if val not in ("<not counted>", "<not supported>") else None
        except ValueError:
            out[event] = None
    return out


def occ_sampler(stop_evt, samples):
    while not stop_evt.is_set():
        try:
            samples.append((time.time(), read_occ(VGRP)))
        except (FileNotFoundError, ValueError):
            pass
        time.sleep(0.25)


def run_one(arm_name, rep, outf):
    mode, vL3, aL3, smba = ARMS[arm_name]
    write_schemata(VGRP, vL3, smba)
    write_schemata(AGRP, aL3, smba)

    agg_proc = None
    agg_log = f"/tmp/e1gate_agg_{arm_name}_{rep}.log"
    mbm_start = mbm_end = None
    t_agg_start = t_agg_end = None

    if mode is not None:
        mbm_start = read_mbm(AGRP)
        t_agg_start = time.time()
        agg_proc = subprocess.Popen(
            f"{AGGRESSOR} -m {mode} -t 7 -c 1,2,3,4,5,6,7 -N 2 -s 64 -d {AGG_DUR} "
            f"> {agg_log} 2>&1",
            shell=True,
        )
        time.sleep(AGG_SETTLE)

    # perf stat wraps the victim's full lifetime (warmup+measurement)
    perf_dur = VICTIM_WARMUP + VICTIM_DUR + 1
    perf_out = f"/tmp/e1gate_perf_{arm_name}_{rep}.csv"
    perf_proc = subprocess.Popen(
        f"perf stat -e {PERF_EVENTS} -C 0 -x, -o {perf_out} -- sleep {perf_dur}",
        shell=True,
    )
    time.sleep(0.2)  # let perf attach before victim starts

    stop_evt = threading.Event()
    occ_samples = []
    samp_thread = threading.Thread(target=occ_sampler, args=(stop_evt, occ_samples))
    samp_thread.start()

    t0 = time.time()
    vproc = subprocess.run(
        f"{VICTIM} -c 0 -w 4096 -P -d {VICTIM_DUR} -W {VICTIM_WARMUP}",
        shell=True, capture_output=True, text=True,
    )
    t1 = time.time()

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

    occ_vals = [v for _, v in occ_samples]
    rec = {
        "arm": arm_name, "rep": rep, "wall_start": t0, "wall_dur_s": t1 - t0,
        "victim": vdata,
        "cyc_per_iter": (vdata.get("cycles", 0) / vdata["iters"]) if vdata.get("iters") else None,
        "agg_bw_self_gbps": agg_bw_self,
        "agg_mbm_bw_gbps": mbm_bw_gbps,
        "victim_llc_occ_bytes": {
            "n": len(occ_vals),
            "mean": sum(occ_vals) / len(occ_vals) if occ_vals else None,
            "min": min(occ_vals) if occ_vals else None,
            "max": max(occ_vals) if occ_vals else None,
        },
        "l3_perf_caveat": "perf stat -C 0 window covers victim warmup+measurement (not measurement-only)",
        "l3_perf": perf_data,
    }
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(f"  {arm_name:14s} rep={rep:2d}  cyc/iter={rec['cyc_per_iter']:.0f}  "
          f"agg_bw(self)={agg_bw_self}  agg_bw(mbm)={mbm_bw_gbps}  "
          f"occ_mean={rec['victim_llc_occ_bytes']['mean']}", flush=True)

    for f in (agg_log, perf_out):
        try:
            os.remove(f)
        except OSError:
            pass


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/e1gate_raw.jsonl"

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
