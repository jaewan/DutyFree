#!/usr/bin/env python3
"""
E4: CI-qualify the paper's AMD matched-bandwidth pair (+28% WB / +0.3% WC),
Sec2_DirectoryTax.tex:43-49. Aggressor on a DIFFERENT CCX from the victim
(cores 8-14, a "milder operating point than the same-L3 worst case" per the
paper) -- victim on cpu0 (CCX0), aggressor on CCX1.

Per the paper: 2 WB threads reach the target ~20.9 GB/s (CXL-path limited,
so 2 threads rather than 2x15.8), while matching that same byte rate under
WC takes 5 threads (WC ~4.2 GB/s/thread => 5x4.2=21 GB/s).

PILOT FINDING that shaped this script's final core placement: WB is
insensitive to same-CCX-packing (2 WB threads packed into one neighbor CCX
already reach ~20.3-20.4 GB/s, matching the target) but WC is NOT -- 5 WC
threads packed into one CCX only reach ~13.9-14.2 GB/s (per the
`run_wc_reconciliation.py` finding: WC degrades to ~1.98 GB/s/core when 7
threads share a CCX, vs ~2.93 GB/s/core when spread across CCXs). So the WC
arm here spreads its 5 threads one-per-CCX to avoid that packing penalty and
actually hit the ~20.9 GB/s target the paper's "matching its byte rate takes
5 WC aggressor cores" sentence implies; the WB arm stays packed (2 threads,
one neighbor CCX), matching the paper's "different L3 domain" framing and
already hitting the target without needing to spread.

n=12, rep-interleaved: quiescent / wb_2t_diffccx / wc_5t_spread.
"""
import json, os, subprocess, sys, time, threading

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/h4v"
AGRP = f"{RESCTRL}/h4a2"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"

VICTIM_WARMUP = 2
VICTIM_DUR = 8
AGG_DUR = 16
AGG_SETTLE = 2
ARMS = {
    # name: (mode_or_None, cores, mbm_domains)
    "quiescent":      (None,      None,                    []),
    "wb_2t_diffccx":  ("wb_load", "8,9",                    [1]),
    "wc_5t_spread":   ("wc_ntdqa","8,16,24,32,40",           [1, 2, 3, 4, 5]),
}
ARM_ORDER = ["quiescent", "wb_2t_diffccx", "wc_5t_spread"]


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def ensure_groups():
    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)
    for g in (VGRP, AGRP):
        os.makedirs(g, exist_ok=True)
    open(f"{VGRP}/cpus_list", "w").write("0")
    # covers every core used by any arm: 8,9 (wb) and 8,16,24,32,40 (wc)
    open(f"{AGRP}/cpus_list", "w").write("8,9,16,24,32,40")
    open(f"{VGRP}/schemata", "w").write("L3:0=ffff\nSMBA:0=2048\n")
    open(f"{AGRP}/schemata", "w").write("L3:0=ffff\nSMBA:0=2048\n")
    time.sleep(1.0)
    # Per-domain RMID/MBM counters appear to initialize lazily on first
    # activity -- warm every domain used by any arm before relying on reads.
    warm_cores = "8,9,16,24,32,40"
    subprocess.run(f"{AGGRESSOR} -m wb_load -t {len(warm_cores.split(','))} "
                    f"-c {warm_cores} -N 2 -s 1 -d 2 > /dev/null 2>&1",
                    shell=True)
    time.sleep(1.0)


def cleanup():
    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)
    for g in (VGRP, AGRP):
        try:
            os.rmdir(g)
        except OSError:
            pass


def read_mbm(domains):
    total = 0
    for d in domains:
        for _ in range(10):
            with open(f"{AGRP}/mon_data/mon_L3_{d:02d}/mbm_total_bytes") as f:
                v = f.read().strip()
            if v != "Unavailable":
                total += int(v)
                break
            time.sleep(0.5)
        else:
            raise RuntimeError(f"mbm domain {d} stayed Unavailable")
    return total


def read_occ():
    with open(f"{VGRP}/mon_data/mon_L3_00/llc_occupancy") as f:
        return int(f.read().strip())


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
            samples.append(read_occ())
        except (FileNotFoundError, ValueError):
            pass
        time.sleep(0.25)


def run_one(arm_name, rep, outf):
    mode, cores, domains = ARMS[arm_name]
    agg_proc = None
    agg_log = f"/tmp/e4mb_agg_{arm_name}_{rep}.log"
    mbm_start = t_agg_start = None

    if mode is not None:
        nthreads = len(cores.split(","))
        # MBM cross-check only for single-domain arms -- summing mbm_total_bytes
        # across >1 simultaneous domain for one RMID was found unreliable on
        # this platform (some domains read "Unavailable" even after warm-up,
        # inconsistently; the wc_reconciliation experiment independently found
        # multi-domain summing under-reports by ~2x). Self-report is primary;
        # documented as a platform limitation, not silently worked around.
        mbm_start = read_mbm(domains) if len(domains) <= 1 else None
        t_agg_start = time.time()
        agg_proc = subprocess.Popen(
            f"{AGGRESSOR} -m {mode} -t {nthreads} -c {cores} -N 2 -s 64 -d {AGG_DUR} "
            f"> {agg_log} 2>&1", shell=True)
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
        with open(agg_log) as f:
            agg_bw_self = parse_agg_bw(f.read())
        if mbm_start is not None:
            mbm_end = read_mbm(domains)
            mbm_bw_gbps = (mbm_end - mbm_start) / (t_agg_end - t_agg_start) / 1e9

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
    }
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(f"  {arm_name:16s} rep={rep:2d}  cyc/iter={rec['cyc_per_iter']:.0f}  "
          f"agg_bw(self)={agg_bw_self}  agg_bw(mbm)={mbm_bw_gbps}", flush=True)

    for f in (agg_log,):
        try:
            os.remove(f)
        except OSError:
            pass


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/e4_matched_bw.jsonl"
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
