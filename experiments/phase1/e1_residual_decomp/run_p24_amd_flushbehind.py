#!/usr/bin/env python3
"""
Phase 2.4: AMD flush-behind vs co-run victim tax. The cross-vendor
discriminator -- see PHASE2_AMD_FLUSHBEHIND_PREREGISTRATION.md, written
before this script existed or ran.

Same victim/aggressor placement as A0-A6 (victim cpu0, aggressor cpus1-7,
CXL node2), same D sweep as Intel's E2b ({32KiB,256KiB,2MiB,16MiB,64MiB,off}).
n=12, rep-interleaved: quiescent + 6 D values (7 arms/rep).
"""
import json, os, subprocess, sys, time, threading

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/p24v"
AGRP = f"{RESCTRL}/p24a"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/amd_flushbehind_aggressor"

VICTIM_WARMUP = 2
VICTIM_DUR = 8
AGG_DUR = 16
AGG_SETTLE = 2
CORES = "1,2,3,4,5,6,7"

# name -> flush_distance_kb or None (quiescent)
D_SWEEP = [
    ("quiescent", None),
    ("d_32kb", 32),
    ("d_256kb", 256),
    ("d_2mb", 2048),
    ("d_16mb", 16384),
    ("d_64mb", 65536),
    ("d_off", 0),
]


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
    sh("pkill -f 'bin/amd_flushbehind_aggressor' 2>/dev/null")
    time.sleep(0.3)
    for g in (VGRP, AGRP):
        os.makedirs(g, exist_ok=True)
    open(f"{VGRP}/cpus_list", "w").write("0")
    open(f"{AGRP}/cpus_list", "w").write("1-7")
    write_schemata(VGRP, "ffff")
    write_schemata(AGRP, "ffff")
    time.sleep(1.0)


def cleanup():
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


def run_one(name, flush_kb, rep, outf):
    agg_proc = None
    agg_log = f"/tmp/p24_agg_{name}_{rep}.log"
    mbm_start = t_agg_start = None

    if flush_kb is not None:
        mbm_start = read_mbm(AGRP)
        t_agg_start = time.time()
        agg_proc = subprocess.Popen(
            f"{AGGRESSOR} -t 7 -c {CORES} -N 2 -s 64 -d {AGG_DUR} -f {flush_kb} "
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
        mbm_end = read_mbm(AGRP)
        with open(agg_log) as f:
            agg_bw_self = parse_agg_bw(f.read())
        mbm_bw_gbps = (mbm_end - mbm_start) / (t_agg_end - t_agg_start) / 1e9

    rec = {
        "arm": name, "flush_kb": flush_kb, "rep": rep,
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
    print(f"  {name:10s} rep={rep:2d}  cyc/iter={rec['cyc_per_iter']:.0f}  "
          f"agg_bw={agg_bw_self}  agg_mbm={mbm_bw_gbps}  "
          f"occ={rec['victim_llc_occ_bytes']['mean']}", flush=True)

    for f in (agg_log,):
        try:
            os.remove(f)
        except OSError:
            pass


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/p24_raw.jsonl"
    ensure_groups()
    try:
        with open(outpath, "w") as outf:
            for r in range(1, reps + 1):
                for name, flush_kb in D_SWEEP:
                    run_one(name, flush_kb, r, outf)
    finally:
        cleanup()
    print(f"DONE -> {outpath}")


if __name__ == "__main__":
    main()
