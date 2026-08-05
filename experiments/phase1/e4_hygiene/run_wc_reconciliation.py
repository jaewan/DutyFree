#!/usr/bin/env python3
"""
E4: AMD per-core WC/WB bandwidth reconciliation. No victim needed here --
this is pure aggressor-side bandwidth characterization, run alone (no
resctrl contention setup required beyond reading MBM on the aggressor's own
group for independent verification).

Configs: {WB, WC} x {1 thread, 7 threads} x {same-CCX, spread-across-CCX}.
  same-CCX cores: 1 (1T) / 1,2,3,4,5,6,7 (7T) -- CCX0, same CCX as the
    victim core (cpu0) used elsewhere in this campaign, though no victim
    runs here.
  spread-across-CCX cores: 8 (1T) / 8,16,24,32,40,48,56 (7T) -- first core
    of each of CCX1..CCX7 on socket0, one thread per distinct CCX.
n=12, rep-interleaved across all 8 configs.
"""
import json, os, subprocess, sys, time

RESCTRL = "/sys/fs/resctrl"
AGRP = f"{RESCTRL}/h4a"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
AGGRESSOR = f"{BIN}/aggressor"
DUR = 10

CONFIGS = [
    ("wb_1t_same", "wb_load", "1"),
    ("wb_7t_same", "wb_load", "1,2,3,4,5,6,7"),
    ("wc_1t_same", "wc_ntdqa", "1"),
    ("wc_7t_same", "wc_ntdqa", "1,2,3,4,5,6,7"),
    ("wb_1t_spread", "wb_load", "8"),
    ("wb_7t_spread", "wb_load", "8,16,24,32,40,48,56"),
    ("wc_1t_spread", "wc_ntdqa", "8"),
    ("wc_7t_spread", "wc_ntdqa", "8,16,24,32,40,48,56"),
]


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def ensure_group():
    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)
    os.makedirs(AGRP, exist_ok=True)
    open(f"{AGRP}/cpus_list", "w").write("0-127")
    open(f"{AGRP}/schemata", "w").write("L3:0=ffff\nSMBA:0=2048\n")
    time.sleep(1.0)  # let RMID/monitoring settle before the first mbm read


def cleanup():
    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)
    try:
        os.rmdir(AGRP)
    except OSError:
        pass


def domains_for_cores(cores_str):
    # 8 physical cores per CCX/L3 domain on this box (confirmed via
    # shared_cpu_list earlier in the campaign); mon_L3_NN follows the same
    # sequential CCX enumeration order.
    cores = [int(c) for c in cores_str.split(",")]
    return sorted(set(c // 8 for c in cores))


def read_mbm(domains):
    total = 0
    for d in domains:
        for attempt in range(5):
            with open(f"{AGRP}/mon_data/mon_L3_{d:02d}/mbm_total_bytes") as f:
                v = f.read().strip()
            if v != "Unavailable":
                total += int(v)
                break
            time.sleep(0.5)
        else:
            raise RuntimeError(f"mbm_total_bytes for domain {d} stayed Unavailable after 5 retries")
    return total


def parse_bw(text):
    threads = []
    for line in text.splitlines():
        if line.startswith("thread"):
            parts = line.split()
            threads.append(float(parts[4]))  # "thread N  core M  X.XX GB/s  (...)"
    agg = None
    for line in text.splitlines():
        if line.startswith("RESULT"):
            for tok in line.split():
                if tok.startswith("bw_gbps="):
                    agg = float(tok.split("=", 1)[1])
    return threads, agg


def run_one(name, mode, cores, rep, outf):
    nthreads = len(cores.split(","))
    domains = domains_for_cores(cores)
    mbm0 = read_mbm(domains)
    t0 = time.time()
    p = subprocess.run(
        f"{AGGRESSOR} -m {mode} -t {nthreads} -c {cores} -N 2 -s 64 -d {DUR}",
        shell=True, capture_output=True, text=True, timeout=DUR + 30)
    t1 = time.time()
    mbm1 = read_mbm(domains)
    per_thread, agg_bw = parse_bw(p.stdout)
    mbm_bw = (mbm1 - mbm0) / (t1 - t0) / 1e9
    rec = {
        "config": name, "mode": mode, "cores": cores, "nthreads": nthreads,
        "rep": rep, "agg_bw_self_gbps": agg_bw, "agg_mbm_bw_gbps": mbm_bw,
        "per_thread_gbps": per_thread,
        "per_core_gbps_self": (agg_bw / nthreads) if agg_bw else None,
    }
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(f"  {name:14s} rep={rep:2d}  agg_bw(self)={agg_bw}  agg_bw(mbm)={mbm_bw:.3f}  "
          f"per_core={rec['per_core_gbps_self']}", flush=True)


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/e4_wc_recon.jsonl"
    ensure_group()
    try:
        with open(outpath, "w") as outf:
            for r in range(1, reps + 1):
                for name, mode, cores in CONFIGS:
                    run_one(name, mode, cores, r, outf)
    finally:
        cleanup()
    print(f"DONE -> {outpath}")


if __name__ == "__main__":
    main()
