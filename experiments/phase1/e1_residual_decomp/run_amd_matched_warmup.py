#!/usr/bin/env python3
"""
AMD matched-warmup re-measurement, per panel request: the "no bimodality on
inspection" check that cleared AMD's retained data is invalid by the same
failure mode that hid Intel's 10% artifact -- per-arm distributions can be
tight and unimodal while still being uniformly biased. AMD's victim binary
already has a first-class internal warmup (-W seconds, self+concurrent
traffic before the measured window begins), unlike Intel's pointer_chase_
nocap which had none -- so the fix here is not a new protocol, just
extending -W from the original 2s (run_e1_gate.py / run_p24_amd_flushbehind.py)
to a duration clearly past Intel's observed dose-saturation point (~8s
cumulative), and comparing both under IDENTICAL concurrent conditions.

For each (arm, rep): launch the aggressor once, settle, then run the victim
TWICE back-to-back under the SAME live aggressor -- once with the original
W=2, once with W=10 -- so any warmup-duration effect isn't confounded by
aggressor run-to-run variation. Quiescent gets the same treatment with no
aggressor (self-generated dose only, which is exactly the arm most exposed
per Intel's diagnosis).

Arms: quiescent (A0), wb (A1), wb_cat (A2), wc (A3) -- the original A0-A3
gate -- plus flush_d256kb, Phase 2.4's best-case (lowest-tax) D point
(5.94x original). n=12, rep-interleaved across all 5 arms.

Highest-stakes number: A3_wc's 0.989x is the quadrilateration anchor
(type-exempt traffic reaches baseline outright). If broker's quiescent
carries cold inflation, WC's true tax drifts upward from parity.
"""
import json, os, subprocess, sys, time, threading, signal

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/amdw_v"
AGRP = f"{RESCTRL}/amdw_a"
BIN = "/home/domin/tmp_dutyfree_exp/bin"  # hardcoded: sudo resets $HOME to /root
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"
FLUSH_AGGRESSOR = f"{BIN}/amd_flushbehind_aggressor"

VICTIM_DUR = 8
WARMUPS = [2, 10]  # original, then a clearly-saturating duration
AGG_DUR = 40        # must cover AGG_SETTLE + both victim calls with margin
AGG_SETTLE = 2

PERF_EVENTS = (
    "l3_lookup_state.l3_hit,l3_lookup_state.l3_miss,"
    "l3_lookup_state.all_coherent_accesses_to_l3"
)

# name -> (kind, mode/flush_kb, victim_L3, agg_L3, smba)
#   kind: "none" | "wbwc" (use `aggressor -m <mode>`) | "flush" (use amd_flushbehind_aggressor -f <kb>)
ARMS = {
    "quiescent": ("none",  None,        "ffff", "ffff", "2048"),
    "wb":        ("wbwc",  "wb_load",   "ffff", "ffff", "2048"),
    "wb_cat":    ("wbwc",  "wb_load",   "ff00", "00ff", "2048"),
    "wc":        ("wbwc",  "wc_ntdqa",  "ffff", "ffff", "2048"),
    "flush_d256kb": ("flush", 256,      "ffff", "ffff", "2048"),
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


def run_victim(warmup, outf, arm_name, rep, agg_bw_self, agg_mbm_bw_gbps):
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
    occ_vals = occ_samples

    rec = {
        "arm": arm_name, "rep": rep, "warmup_s": warmup,
        "victim": vdata,
        "cyc_per_iter": (vdata.get("cycles", 0) / vdata["iters"]) if vdata.get("iters") else None,
        "agg_bw_self_gbps": agg_bw_self,
        "agg_mbm_bw_gbps": agg_mbm_bw_gbps,
        "victim_llc_occ_bytes": {
            "n": len(occ_vals),
            "mean": sum(occ_vals) / len(occ_vals) if occ_vals else None,
        },
    }
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(f"  {arm_name:14s} rep={rep:2d}  W={warmup:2d}s  cyc/iter={rec['cyc_per_iter']:.0f}  "
          f"agg_bw={agg_bw_self}  agg_mbm={agg_mbm_bw_gbps}  "
          f"occ={rec['victim_llc_occ_bytes']['mean']}", flush=True)
    return rec


def run_one(arm_name, rep, outf):
    kind, param, vL3, aL3, smba = ARMS[arm_name]
    write_schemata(VGRP, vL3, smba)
    write_schemata(AGRP, aL3, smba)

    agg_proc = None
    agg_log = f"/tmp/amdw_agg_{arm_name}_{rep}.log"
    mbm_start = t_agg_start = None

    if kind == "wbwc":
        mbm_start = read_mbm(AGRP)
        t_agg_start = time.time()
        agg_proc = subprocess.Popen(
            f"{AGGRESSOR} -m {param} -t 7 -c 1,2,3,4,5,6,7 -N 2 -s 64 -d {AGG_DUR} "
            f"> {agg_log} 2>&1", shell=True)
        time.sleep(AGG_SETTLE)
    elif kind == "flush":
        mbm_start = read_mbm(AGRP)
        t_agg_start = time.time()
        agg_proc = subprocess.Popen(
            f"{FLUSH_AGGRESSOR} -t 7 -c 1,2,3,4,5,6,7 -N 2 -s 64 -d {AGG_DUR} -f {param} "
            f"> {agg_log} 2>&1", shell=True)
        time.sleep(AGG_SETTLE)

    # both W=2 and W=10 victim calls happen under this SAME live aggressor
    for warmup in WARMUPS:
        run_victim(warmup, outf, arm_name, rep, None, None)

    if agg_proc is not None:
        agg_proc.terminate()
        try:
            agg_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            agg_proc.kill()
            agg_proc.wait()
        t_agg_end = time.time()
        mbm_end = read_mbm(AGRP)
        agg_bw_self = None
        try:
            with open(agg_log) as f:
                agg_bw_self = parse_agg_bw(f.read())
        except FileNotFoundError:
            pass
        mbm_bw_gbps = (mbm_end - mbm_start) / (t_agg_end - t_agg_start) / 1e9
        # patch the two just-written records with the aggressor summary
        # (bw is a whole-launch aggregate, not per-victim-call, so both
        # rows for this arm/rep share the same value)
        outf.write(json.dumps({
            "arm": arm_name, "rep": rep, "aggressor_summary": True,
            "agg_bw_self_gbps": agg_bw_self, "agg_mbm_bw_gbps": mbm_bw_gbps,
        }) + "\n")
        outf.flush()
        print(f"    [{arm_name} rep={rep}] aggressor summary: self={agg_bw_self} mbm={mbm_bw_gbps:.3f}",
              flush=True)
        try:
            os.remove(agg_log)
        except OSError:
            pass


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/amd_matched_warmup.jsonl"

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
