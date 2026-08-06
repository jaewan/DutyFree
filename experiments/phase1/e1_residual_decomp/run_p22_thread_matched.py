#!/usr/bin/env python3
"""
Phase 2.2: A5 redo, thread-matched, unthrottled (no -R pacing artifact).
CXL nT vs local nT, n=1..7, same cores each time (1..n of cpus1-7), same
victim (4 MiB pointer chase, cpu0). Also captures AMD's l3_xi_sampled_latency
PMU event (a real measured average fill latency by source: ext_near=CXL,
dram_near=local DRAM -- not a count) via `perf stat -C 0`, so the Little's-
law occupancy estimate (N = BW * service_time / 64B) uses a MEASURED
service time per arm, not an assumed constant.

n=12, rep-interleaved: quiescent / cxl_1T..cxl_7T / local_1T..local_7T
(15 arms/rep).
"""
import json, os, subprocess, sys, time, threading

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/p22v"
AGRP = f"{RESCTRL}/p22a"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"

VICTIM_WARMUP = 2
VICTIM_DUR = 8
AGG_DUR = 16
AGG_SETTLE = 2
CORES_ALL = "1,2,3,4,5,6,7"

# l3_xi_sampled_latency.X is a raw cycle-domain SUM, not an average -- must
# be normalized by the paired l3_xi_sampled_latency_requests.X count to get
# a real per-request value (still in L3-clock cycles, not ns, until Phase
# 2.3 pins/measures the uncore clock -- reported as raw cycles/request here,
# convert once uncore frequency is known).
PERF_EVENTS = ("l3_xi_sampled_latency.ext_near,l3_xi_sampled_latency_requests.ext_near,"
               "l3_xi_sampled_latency.dram_near,l3_xi_sampled_latency_requests.dram_near,"
               "l3_lookup_state.l3_hit,l3_lookup_state.l3_miss")

ARMS = [("quiescent", None, None, 0)]
for n in range(1, 8):
    cores = ",".join(CORES_ALL.split(",")[:n])
    ARMS.append((f"cxl_{n}t", "wb_load", cores, 2))
for n in range(1, 8):
    cores = ",".join(CORES_ALL.split(",")[:n])
    # NOTE: "wb_load" is hardcoded in aggressor.c to alloc_wb_cxl() regardless
    # of -N -- it ignores the node flag entirely. "wb_local" is the mode that
    # actually honors -N and calls alloc_wb_node(). Using "wb_load" here was
    # a real bug in the first draft (both arms silently ran on CXL; caught
    # in smoke-test review, not in a full n=12 run).
    ARMS.append((f"local_{n}t", "wb_local", cores, 0))


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def write_schemata(grp, l3, smba="2048"):
    with open(f"{grp}/schemata", "w") as f:
        f.write(f"L3:0={l3}\nSMBA:0={smba}\n")


def read_mbm(grp):
    for _ in range(10):
        with open(f"{grp}/mon_data/mon_L3_00/mbm_total_bytes") as f:
            v = f.read().strip()
        if v != "Unavailable":
            return int(v)
        time.sleep(0.5)
    raise RuntimeError("mbm stayed Unavailable")


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
    write_schemata(VGRP, "ffff")
    write_schemata(AGRP, "ffff")
    time.sleep(1.0)


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
            out[event] = float(val) if val not in ("<not counted>", "<not supported>") else None
        except ValueError:
            out[event] = None
    return out


def occ_sampler(stop_evt, samples):
    while not stop_evt.is_set():
        v = read_occ(VGRP)
        if v is not None:
            samples.append(v)
        time.sleep(0.25)


def run_one(name, mode, cores, node, rep, outf):
    agg_proc = None
    agg_log = f"/tmp/p22_agg_{name}_{rep}.log"
    mbm_start = t_agg_start = None

    if mode is not None:
        nthreads = len(cores.split(","))
        mbm_start = read_mbm(AGRP)
        t_agg_start = time.time()
        agg_proc = subprocess.Popen(
            f"{AGGRESSOR} -m {mode} -t {nthreads} -c {cores} -N {node} -s 64 -d {AGG_DUR} "
            f"> {agg_log} 2>&1", shell=True)
        time.sleep(AGG_SETTLE)

    perf_dur = VICTIM_WARMUP + VICTIM_DUR + 1
    perf_out = f"/tmp/p22_perf_{name}_{rep}.csv"
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

    agg_bw_self = mbm_bw_gbps = None
    if agg_proc is not None:
        agg_proc.wait(timeout=AGG_DUR + 10)
        t_agg_end = time.time()
        mbm_end = read_mbm(AGRP)
        with open(agg_log) as f:
            agg_bw_self = parse_agg_bw(f.read())
        mbm_bw_gbps = (mbm_end - mbm_start) / (t_agg_end - t_agg_start) / 1e9

    with open(perf_out) as f:
        perf_data = parse_perf(f.read())

    rec = {
        "arm": name, "rep": rep, "node": node,
        "victim": vdata,
        "cyc_per_iter": (vdata.get("cycles", 0) / vdata["iters"]) if vdata.get("iters") else None,
        "agg_bw_self_gbps": agg_bw_self,
        "agg_mbm_bw_gbps": mbm_bw_gbps,
        "victim_llc_occ_bytes": {
            "n": len(occ_samples),
            "mean": sum(occ_samples) / len(occ_samples) if occ_samples else None,
        },
        "l3_xi_perf_raw": perf_data,  # raw sum + count, both buckets, for the record
    }
    src = "ext_near" if node == 2 else "dram_near"
    lat_sum = perf_data.get(f"l3_xi_sampled_latency.{src}")
    lat_n = perf_data.get(f"l3_xi_sampled_latency_requests.{src}")
    rec["xi_cycles_per_request"] = (lat_sum / lat_n) if (lat_sum and lat_n) else None
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(f"  {name:10s} rep={rep:2d}  cyc/iter={rec['cyc_per_iter']:.0f}  "
          f"agg_bw={agg_bw_self}  xi_cyc/req={rec['xi_cycles_per_request']}  "
          f"occ={rec['victim_llc_occ_bytes']['mean']}", flush=True)

    for f in (agg_log, perf_out):
        try:
            os.remove(f)
        except OSError:
            pass


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/p22_raw.jsonl"
    ensure_groups()
    try:
        with open(outpath, "w") as outf:
            for r in range(1, reps + 1):
                for name, mode, cores, node in ARMS:
                    run_one(name, mode, cores, node, r, outf)
    finally:
        cleanup()
    print(f"DONE -> {outpath}")


if __name__ == "__main__":
    main()
