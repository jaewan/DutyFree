#!/usr/bin/env python3
"""
Full E2b D-sweep under the corrected matched discard-cold-trial protocol
(see PHASE2_E2B_WARMUP_CORRECTION.md). Every arm, including quiescent, is
measured with --trials 2 --run-sec 4, discarding trial 0 and reporting
trial 1 -- removing the cold-vs-warm asymmetry that produced the retracted
~0.90x small-D tax. No ticker (that fix was tested and failed; this is a
different, confirmed fix). Otherwise identical structure/placement to
run_e2b_flushbehind.py / run_e2b_flushbehind_ticker.py: same victim/
aggressor placement, same D sweep, same bandwidth + RMID llc_occupancy
sampling, n=12, rep-interleaved.
"""
import json, os, subprocess, sys, time, threading

BENCH = "/home/domin/DutyFree/benchmarks/bench"
AGG = f"{BENCH}/aggressor/stream_wb_flushbehind"
VICTIM = f"{BENCH}/victim/pointer_chase_nocap"

VICTIM_CPU = 0
VICTIM_NODE = 0
WSS_MB = 170
AGG_CPUS = [1, 2, 3, 4, 5, 6, 7, 8]
AGG_NODE = 2
AGG_REGION_GB = 2
AGG_DURATION = 30
VICTIM_RUN_SEC = 4
READY_TIMEOUT = 60

RESCTRL = "/sys/fs/resctrl"
AGRP = f"{RESCTRL}/e2b_agg"

D_SWEEP = [
    ("quiescent", None, True),
    ("d_32kb", 32, False),
    ("d_256kb", 256, False),
    ("d_2mb", 2048, False),
    ("d_16mb", 16384, False),
    ("d_64mb", 65536, False),
    ("d_off", 0, False),
]


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def ensure_group():
    sh("pkill -f 'stream_wb_flushbehind' 2>/dev/null")
    time.sleep(0.3)
    os.makedirs(AGRP, exist_ok=True)
    open(f"{AGRP}/cpus_list", "w").write("1-8")


def cleanup():
    sh("pkill -f 'stream_wb_flushbehind' 2>/dev/null")
    time.sleep(0.3)
    try:
        os.rmdir(AGRP)
    except OSError:
        pass


def read_occ():
    with open(f"{AGRP}/mon_data/mon_L3_00/llc_occupancy") as f:
        v = f.read().strip()
    return None if v == "Unavailable" else int(v)


def occ_sampler(stop_evt, samples):
    while not stop_evt.is_set():
        v = read_occ()
        if v is not None:
            samples.append(v)
        time.sleep(0.25)


def launch_aggressors(flush_kb):
    procs = []
    for cpu in AGG_CPUS:
        cmd = (f"numactl --membind={AGG_NODE} --cpunodebind=0 -- {AGG} "
               f"--cpu {cpu} --node {AGG_NODE} --region-gb {AGG_REGION_GB} "
               f"--duration-sec {AGG_DURATION}")
        if flush_kb is not None:
            cmd += f" --flush-distance-kb {flush_kb}"
        procs.append(subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True))
    return procs


def wait_ready(procs, timeout=READY_TIMEOUT):
    deadline = time.time() + timeout
    ready = set()
    while time.time() < deadline and len(ready) < len(procs):
        for i, p in enumerate(procs):
            if i in ready:
                continue
            if p.poll() is not None:
                raise RuntimeError(f"aggressor cpu={AGG_CPUS[i]} exited early")
        time.sleep(0.3)
        if time.time() - (deadline - timeout) > 2.0:
            return
    return


def stop_aggressors(procs):
    for p in procs:
        p.terminate()
    bws = []
    for p in procs:
        try:
            out, _ = p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            out, _ = p.communicate()
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    bws.append(json.loads(line)["avg_bw_gbps"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return bws


def run_victim_warmed():
    """Matched discard-cold-trial protocol: 2 trials, report trial 1."""
    cmd = (f"numactl --membind={VICTIM_NODE} --cpunodebind=0 -- {VICTIM} "
           f"--cpu {VICTIM_CPU} --node {VICTIM_NODE} --wss {WSS_MB * 1024 * 1024} "
           f"--trials 2 --run-sec {VICTIM_RUN_SEC}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                        timeout=2 * VICTIM_RUN_SEC + 60)
    trials = json.loads(r.stdout)
    return trials[0]["cycles_per_load"], trials[1]["cycles_per_load"]


def run_one(name, flush_kb, is_quiescent, rep, outf):
    procs = []
    if not is_quiescent:
        procs = launch_aggressors(flush_kb)
        wait_ready(procs)

    stop_evt = threading.Event()
    occ_samples = []
    samp_thread = None
    if not is_quiescent:
        samp_thread = threading.Thread(target=occ_sampler, args=(stop_evt, occ_samples))
        samp_thread.start()

    trial0, trial1 = run_victim_warmed()

    if samp_thread:
        stop_evt.set()
        samp_thread.join()

    bws = stop_aggressors(procs) if procs else []
    agg_bw_total = sum(bws) if bws else None

    rec = {
        "config": name, "flush_distance_kb": flush_kb, "rep": rep,
        "victim_trial0_discarded": trial0,
        "victim_cycles_per_load": trial1,  # matched-protocol value used for tax
        "agg_bw_total_gbps": agg_bw_total,
        "agg_bw_per_thread": bws,
        "occ_mean_bytes": (sum(occ_samples) / len(occ_samples)) if occ_samples else None,
        "occ_n_samples": len(occ_samples),
    }
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(f"  {name:12s} rep={rep:2d}  trial0(disc)={trial0:7.2f}  "
          f"trial1(used)={trial1:7.2f}  agg_bw_total={agg_bw_total}  "
          f"occ_mean={rec['occ_mean_bytes']}", flush=True)


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/e2b_full_sweep_warmup.jsonl"
    ensure_group()
    try:
        with open(outpath, "w") as outf:
            for r in range(1, reps + 1):
                for name, flush_kb, is_q in D_SWEEP:
                    run_one(name, flush_kb, is_q, r, outf)
    finally:
        cleanup()
    print(f"DONE -> {outpath}")


if __name__ == "__main__":
    main()
