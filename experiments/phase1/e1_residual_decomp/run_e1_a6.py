#!/usr/bin/env python3
"""
E1 arm A6: WB CXL aggressor concurrency sweep {1,2,3,5,7} threads, same-CCX,
no CAT (extends the paper's 2.77x/6.5x/18.3x single-thread-rate points with
CIs and victim-side counters). Rep-interleaved across thread counts, n>=12.
"""
import json, os, subprocess, sys, time, threading, signal

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/h3v"
AGRP = f"{RESCTRL}/h3a"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"

VICTIM_WARMUP = 2
VICTIM_DUR = 8
AGG_DUR = 16
AGG_SETTLE = 2

THREAD_COUNTS = [1, 2, 3, 5, 7]
CORES = "1,2,3,4,5,6,7"


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
    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)
    sh("pkill -9 -f 'bin/aggressor' 2>/dev/null")
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


def parse_agg_bw(text):
    for line in text.splitlines():
        if line.startswith("RESULT"):
            for tok in line.split():
                if tok.startswith("bw_gbps="):
                    return float(tok.split("=", 1)[1])
    return None


def occ_sampler(stop_evt, samples):
    while not stop_evt.is_set():
        try:
            samples.append(read_occ(VGRP))
        except (FileNotFoundError, ValueError):
            pass
        time.sleep(0.25)


def run_one(nthreads, rep, outf):
    write_schemata(VGRP, "ffff")
    write_schemata(AGRP, "ffff")
    agg_log = f"/tmp/e1a6_agg_{nthreads}_{rep}.log"
    cores = ",".join(CORES.split(",")[:nthreads])

    if nthreads == 0:
        mbm_start = t_agg_start = agg_proc = None
    else:
        mbm_start = read_mbm(AGRP)
        t_agg_start = time.time()
        agg_proc = subprocess.Popen(
            f"{AGGRESSOR} -m wb_load -t {nthreads} -c {cores} -N 2 -s 64 -d {AGG_DUR} > {agg_log} 2>&1",
            shell=True)
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

    victim_line = next((l for l in vproc.stdout.splitlines() if l.startswith("VICTIM")), "")
    vdata = parse_victim(victim_line)

    agg_bw_self = mbm_bw_gbps = None
    if agg_proc is not None:
        agg_proc.wait(timeout=AGG_DUR + 10)
        t_agg_end = time.time()
        mbm_end = read_mbm(AGRP)
        with open(agg_log) as f:
            agg_bw_self = parse_agg_bw(f.read())
        mbm_bw_gbps = (mbm_end - mbm_start) / (t_agg_end - t_agg_start) / 1e9

    rec = {
        "nthreads": nthreads, "rep": rep,
        "victim": vdata,
        "cyc_per_iter": (vdata.get("cycles", 0) / vdata["iters"]) if vdata.get("iters") else None,
        "agg_bw_self_gbps": agg_bw_self,
        "agg_mbm_bw_gbps": mbm_bw_gbps,
        "victim_llc_occ_bytes": {
            "n": len(occ_samples),
            "mean": sum(occ_samples) / len(occ_samples) if occ_samples else None,
        },
    }
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(f"  t={nthreads}  rep={rep:2d}  cyc/iter={rec['cyc_per_iter']:.0f}  "
          f"agg_bw(self)={agg_bw_self}  agg_bw(mbm)={mbm_bw_gbps}  "
          f"occ_mean={rec['victim_llc_occ_bytes']['mean']}", flush=True)

    for f in (agg_log,):
        try:
            os.remove(f)
        except OSError:
            pass


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/e1a6_raw.jsonl"

    def handle_sigterm(signum, frame):
        cleanup()
        sys.exit(1)
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    ensure_groups()
    try:
        with open(outpath, "w") as outf:
            for r in range(1, reps + 1):
                run_one(0, r, outf)  # quiescent baseline, interleaved
                for t in THREAD_COUNTS:
                    run_one(t, r, outf)
    finally:
        cleanup()
    print(f"DONE -> {outpath}")


if __name__ == "__main__":
    main()
