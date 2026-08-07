#!/usr/bin/env python3
"""
Matched-methodology E2b spot-check: quiescent and d_32kb measured with the
IDENTICAL victim protocol (--trials 2 --run-sec 4, discard cold trial 0,
report trial 1), interleaved rep-by-rep, n=12. Purpose: test whether the
tax ratio moves toward ~1.00x when both arms get the same self-warmup
discipline (distinct from the ticker fix, which failed -- see
phase2_pmqos_ticker_RESULTS.md and its addendum).
"""
import json, os, subprocess, sys, time, statistics

BENCH = "/home/domin/DutyFree/benchmarks/bench"
AGG = f"{BENCH}/aggressor/stream_wb_flushbehind"
VICTIM = f"{BENCH}/victim/pointer_chase_nocap"
VICTIM_CPU, VICTIM_NODE, WSS_MB = 0, 0, 170
AGG_CPUS = [1, 2, 3, 4, 5, 6, 7, 8]
AGG_NODE = 2
AGG_REGION_GB = 2
AGG_DURATION = 30
RESCTRL = "/sys/fs/resctrl"
AGRP = f"{RESCTRL}/e2b_agg"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 12
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/e2b_matched_warmup_n12.jsonl"


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def ensure_group():
    sh("pkill -f stream_wb_flushbehind 2>/dev/null")
    time.sleep(0.3)
    os.makedirs(AGRP, exist_ok=True)
    open(f"{AGRP}/cpus_list", "w").write("1-8")


def cleanup():
    sh("pkill -f stream_wb_flushbehind 2>/dev/null")
    time.sleep(0.3)
    try:
        os.rmdir(AGRP)
    except OSError:
        pass


def launch_aggressors(flush_kb):
    procs = []
    for cpu in AGG_CPUS:
        cmd = (f"numactl --membind={AGG_NODE} --cpunodebind=0 -- {AGG} "
               f"--cpu {cpu} --node {AGG_NODE} --region-gb {AGG_REGION_GB} "
               f"--duration-sec {AGG_DURATION} --flush-distance-kb {flush_kb}")
        procs.append(subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True))
    time.sleep(2.0)  # settle, matching run_e2b_flushbehind's fixed settle window
    return procs


def stop_aggressors(procs):
    for p in procs:
        p.terminate()
    for p in procs:
        try:
            p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate()


def run_victim_warmed():
    cmd = (f"numactl --membind={VICTIM_NODE} --cpunodebind=0 -- {VICTIM} "
           f"--cpu {VICTIM_CPU} --node {VICTIM_NODE} --wss {WSS_MB*1024*1024} "
           f"--trials 2 --run-sec 4")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    trials = json.loads(r.stdout)
    return trials[0]["cycles_per_load"], trials[1]["cycles_per_load"]


def main():
    ensure_group()
    q_vals, d_vals = [], []
    try:
        with open(OUT, "w") as outf:
            for rep in range(1, N + 1):
                # quiescent, matched protocol (no aggressor)
                t0, t1 = run_victim_warmed()
                q_vals.append(t1)
                outf.write(json.dumps({"config": "quiescent", "rep": rep,
                                        "trial0_discarded": t0, "trial1_used": t1}) + "\n")
                print(f"  rep {rep:2d} quiescent: trial0={t0:.2f} trial1={t1:.2f}", flush=True)

                # d_32kb, matched protocol (aggressor concurrent)
                procs = launch_aggressors(32)
                t0, t1 = run_victim_warmed()
                stop_aggressors(procs)
                d_vals.append(t1)
                outf.write(json.dumps({"config": "d_32kb", "rep": rep,
                                        "trial0_discarded": t0, "trial1_used": t1}) + "\n")
                print(f"  rep {rep:2d} d_32kb   : trial0={t0:.2f} trial1={t1:.2f}", flush=True)
                outf.flush()
    finally:
        cleanup()

    qm, dm = statistics.median(q_vals), statistics.median(d_vals)
    print(f"\nquiescent (warmed) median: {qm:.3f}  raw={sorted(f'{v:.2f}' for v in q_vals)}")
    print(f"d_32kb    (warmed) median: {dm:.3f}  raw={sorted(f'{v:.2f}' for v in d_vals)}")
    print(f"tax = d_32kb/quiescent = {dm/qm:.4f}")


if __name__ == "__main__":
    main()
