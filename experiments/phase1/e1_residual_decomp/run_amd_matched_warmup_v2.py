#!/usr/bin/env python3
"""
AMD matched-warmup re-measurement, v2 -- corrected design.

v1 (run_amd_matched_warmup.py) shared one aggressor launch across two
back-to-back victim calls (W=2 then W=10) to save wall-clock time. This
introduced a NEW confound not present in the original protocol: each arm's
aggressor stayed alive ~3x longer than run_e1_gate.py's single-call design,
and WC specifically showed a large, reproducible anomaly (~12-15M cyc/iter
at W=2, vs ~3.6M at W=10) that traced to accumulated sustained-load depth
across the whole quiescent->wb->wb_cat->wc sequence, not to warmup duration
-- confirmed by direct isolation tests (see PHASE2_AMD_WARMUP_CHECK.md).
The ORIGINAL retained e1gate_raw_n12.jsonl shows zero rep-order drift across
its own 12 reps (~10 min total), ruling out this effect being present in
the original protocol itself.

v2 fix: run the WHOLE gate as two SEPARATE, structurally-identical passes
-- one at W=2 (exact replica of run_e1_gate.py, serving as an in-session
control), one at W=10 -- each with a FRESH aggressor launch per single
victim call, matching the original's lifecycle exactly. This isolates
warmup duration as the only variable, without introducing the shared-
aggressor-lifetime confound v1 had.

Arms: quiescent (A0), wb (A1), wb_cat (A2), wc (A3), flush_d256kb
(Phase 2.4 best-case D). n=12, rep-interleaved across all 5 arms, one full
n=12 sweep per warmup value.
"""
import json, os, subprocess, sys, time, threading, signal

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/amdw2_v"
AGRP = f"{RESCTRL}/amdw2_a"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"
FLUSH_AGGRESSOR = f"{BIN}/amd_flushbehind_aggressor"

VICTIM_DUR = 8
AGG_SETTLE = 2

# name -> (kind, mode/flush_kb, victim_L3, agg_L3, smba)
ARMS = {
    "quiescent":    ("none",  None,       "ffff", "ffff", "2048"),
    "wb":           ("wbwc",  "wb_load",  "ffff", "ffff", "2048"),
    "wb_cat":       ("wbwc",  "wb_load",  "ff00", "00ff", "2048"),
    "wc":           ("wbwc",  "wc_ntdqa", "ffff", "ffff", "2048"),
    "flush_d256kb": ("flush", 256,        "ffff", "ffff", "2048"),
}
ARM_ORDER = ["quiescent", "wb", "wb_cat", "wc", "flush_d256kb"]


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def write_schemata(grp, l3, smba):
    with open(f"{grp}/schemata", "w") as f:
        f.write(f"L3:0={l3}\nSMBA:0={smba}\n")


def read_mbm(grp):
    with open(f"{grp}/mon_data/mon_L3_00/mbm_total_bytes") as f:
        return int(f.read().strip())


def read_occ(grp):
    with open(f"{grp}/mon_data/mon_L3_00/llc_occupancy") as f:
        v = f.read().strip()
    return None if v == "Unavailable" else int(v)


def ensure_groups():
    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    sh("pkill -f 'bin/amd_flushbehind_aggressor' 2>/dev/null")
    time.sleep(0.3)
    for g in (VGRP, AGRP):
        os.makedirs(g, exist_ok=True)
    open(f"{VGRP}/cpus_list", "w").write("0")
    open(f"{AGRP}/cpus_list", "w").write("1-7")


def cleanup():
    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    sh("pkill -f 'bin/amd_flushbehind_aggressor' 2>/dev/null")
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
        v = read_occ(VGRP)
        if v is not None:
            samples.append(v)
        time.sleep(0.25)


def run_one(arm_name, rep, warmup, outf):
    kind, param, vL3, aL3, smba = ARMS[arm_name]
    write_schemata(VGRP, vL3, smba)
    write_schemata(AGRP, aL3, smba)

    # AGG_DUR scaled to just cover settle+warmup+measure+margin, matching
    # the original's tight per-arm aggressor lifetime discipline (never
    # shared across multiple victim calls).
    agg_dur = AGG_SETTLE + warmup + VICTIM_DUR + 4

    agg_proc = None
    agg_log = f"/tmp/amdw2_agg_{arm_name}_{rep}_{warmup}.log"
    mbm_start = t_agg_start = None

    if kind == "wbwc":
        mbm_start = read_mbm(AGRP)
        t_agg_start = time.time()
        agg_proc = subprocess.Popen(
            f"{AGGRESSOR} -m {param} -t 7 -c 1,2,3,4,5,6,7 -N 2 -s 64 -d {agg_dur} "
            f"> {agg_log} 2>&1", shell=True)
        time.sleep(AGG_SETTLE)
    elif kind == "flush":
        mbm_start = read_mbm(AGRP)
        t_agg_start = time.time()
        agg_proc = subprocess.Popen(
            f"{FLUSH_AGGRESSOR} -t 7 -c 1,2,3,4,5,6,7 -N 2 -s 64 -d {agg_dur} -f {param} "
            f"> {agg_log} 2>&1", shell=True)
        time.sleep(AGG_SETTLE)

    stop_evt = threading.Event()
    occ_samples = []
    samp_thread = threading.Thread(target=occ_sampler, args=(stop_evt, occ_samples))
    samp_thread.start()

    vproc = subprocess.run(
        f"{VICTIM} -c 0 -w 4096 -P -d {VICTIM_DUR} -W {warmup}",
        shell=True, capture_output=True, text=True)

    stop_evt.set()
    samp_thread.join()

    victim_line = next((l for l in vproc.stdout.splitlines() if l.startswith("VICTIM")), "")
    vdata = parse_victim(victim_line)

    agg_bw_self = mbm_bw_gbps = None
    if agg_proc is not None:
        agg_proc.wait(timeout=agg_dur + 10)
        t_agg_end = time.time()
        mbm_end = read_mbm(AGRP)
        try:
            with open(agg_log) as f:
                agg_bw_self = parse_agg_bw(f.read())
        except FileNotFoundError:
            pass
        mbm_bw_gbps = (mbm_end - mbm_start) / (t_agg_end - t_agg_start) / 1e9

    rec = {
        "arm": arm_name, "rep": rep, "warmup_s": warmup,
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
    print(f"  {arm_name:14s} rep={rep:2d}  W={warmup:2d}s  cyc/iter={rec['cyc_per_iter']:.0f}  "
          f"agg_bw={agg_bw_self}  agg_mbm={mbm_bw_gbps}  "
          f"occ={rec['victim_llc_occ_bytes']['mean']}", flush=True)

    for f in (agg_log,):
        try:
            os.remove(f)
        except OSError:
            pass


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    warmup = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    outpath = sys.argv[3] if len(sys.argv) > 3 else f"/tmp/amd_matched_warmup_v2_W{warmup}.jsonl"

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
                    run_one(arm, r, warmup, outf)
    finally:
        cleanup()
    print(f"DONE -> {outpath}")


if __name__ == "__main__":
    main()
