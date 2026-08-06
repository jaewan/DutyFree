#!/usr/bin/env python3
"""
E2b: flush-behind streamer (clflushopt at distance D) vs co-run victim tax,
plus stream-side bandwidth and RMID llc_occupancy vs D. Reuses the same
victim/8-aggressor-process convention as cat_mba.py (170 MB victim, 8
aggressor threads on cpus1-8, CXL node2), but with stream_wb_flushbehind
instead of stream_wb, parameterized by flush distance D.

D sweep per the mission: {32 KiB, 256 KiB, 2 MiB, 16 MiB, 64 MiB, off}.
"off" reduces to the already-passed s2_cxl8_baseline gate (D=off IS
stream_wb.c's behavior) -- not re-measured here as a separate gate, just
included in the sweep for a complete BW/occupancy/tax-vs-D curve.

n=12, rep-interleaved: quiescent / D=32KB / 256KB / 2MB / 16MB / 64MB / off.
"""
import json, os, re, subprocess, sys, time, threading

BENCH = "/home/domin/DutyFree/benchmarks/bench"
AGG = f"{BENCH}/aggressor/stream_wb_flushbehind"
VICTIM = f"{BENCH}/victim/pointer_chase_nocap"

VICTIM_CPU = 0
VICTIM_NODE = 0
WSS_MB = 170
AGG_CPUS = [1, 2, 3, 4, 5, 6, 7, 8]
AGG_NODE = 2
AGG_REGION_GB = 2  # smaller than cat_mba.py's 5GB -- keeps per-rep startup fast; D sweep cares about steady-state BW, not total volume
AGG_DURATION = 30  # long enough to cover victim warmup+measurement with margin
VICTIM_RUN_SEC = 4
READY_TIMEOUT = 60

RESCTRL = "/sys/fs/resctrl"
AGRP = f"{RESCTRL}/e2b_agg"

# name -> flush_distance_kb or None (off)
D_SWEEP = [
    ("quiescent", None, True),   # no aggressor at all
    ("d_32kb", 32, False),
    ("d_256kb", 256, False),
    ("d_2mb", 2048, False),
    ("d_16mb", 16384, False),
    ("d_64mb", 65536, False),
    ("d_off", 0, False),         # flush disabled: full residency
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
        # crude readiness: just give them a fixed settle window since stderr
        # buffering makes line-by-line polling unreliable across 8 procs
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


def run_victim_once():
    cmd = (f"numactl --membind={VICTIM_NODE} --cpunodebind=0 -- {VICTIM} "
           f"--cpu {VICTIM_CPU} --node {VICTIM_NODE} --wss {WSS_MB * 1024 * 1024} "
           f"--trials 1 --run-sec {VICTIM_RUN_SEC}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                        timeout=VICTIM_RUN_SEC + 60)
    trials = json.loads(r.stdout)
    return trials[0]["cycles_per_load"]


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

    cyc_per_load = run_victim_once()

    if samp_thread:
        stop_evt.set()
        samp_thread.join()

    bws = stop_aggressors(procs) if procs else []
    agg_bw_total = sum(bws) if bws else None

    rec = {
        "config": name, "flush_distance_kb": flush_kb, "rep": rep,
        "victim_cycles_per_load": cyc_per_load,
        "agg_bw_total_gbps": agg_bw_total,
        "agg_bw_per_thread": bws,
        "occ_mean_bytes": (sum(occ_samples) / len(occ_samples)) if occ_samples else None,
        "occ_n_samples": len(occ_samples),
    }
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(f"  {name:12s} rep={rep:2d}  cyc/load={cyc_per_load:7.2f}  "
          f"agg_bw_total={agg_bw_total}  occ_mean={rec['occ_mean_bytes']}", flush=True)


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/e2b_raw.jsonl"
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
