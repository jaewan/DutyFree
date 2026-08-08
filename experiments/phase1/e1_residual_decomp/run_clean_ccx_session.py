#!/usr/bin/env python3
"""
Clean-CCX co-measured session, per PHASE2_CLEAN_CCX_PREREGISTRATION.md.
One CCX (default CCX1: victim=cpu8, aggressor cores=9-15), n=12,
rep-interleaved across: quiescent, wb, wb_cat, wc, flush_d256kb, and the
A6-style concurrency knee at 2T and 3T. Bandwidth (self+MBM) and
occupancy captured throughout; MSR verification for the wb_cat arm on
the actual CCX-under-test's cores (the lesson from the domain-index bug).
"""
import json, os, subprocess, sys, time, threading, signal, struct

RESCTRL = "/sys/fs/resctrl"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"
FLUSH_AGGRESSOR = f"{BIN}/amd_flushbehind_aggressor"

VICTIM_WARMUP, VICTIM_DUR, AGG_SETTLE = 2, 8, 2
PQR_ASSOC = 0xC8F
L3_MASK_BASE = 0xC90


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def read_msr(cpu, addr):
    fd = os.open(f"/dev/cpu/{cpu}/msr", os.O_RDONLY)
    try:
        return struct.unpack("<Q", os.pread(fd, 8, addr))[0]
    finally:
        os.close(fd)


def discover_domain(cpu, grp_base):
    grp = f"{grp_base}/domdisc"
    os.makedirs(grp, exist_ok=True)
    open(f"{grp}/cpus_list", "w").write(str(cpu))
    proc = subprocess.Popen(f"{VICTIM} -c {cpu} -w 4096 -P -d 5 -W 1 > /tmp/ccxsess_domdisc.log 2>&1", shell=True)
    time.sleep(3)
    found = None
    for f in sorted(os.listdir(f"{grp}/mon_data")):
        path = f"{grp}/mon_data/{f}/llc_occupancy"
        try:
            v = open(path).read().strip()
        except (FileNotFoundError, ValueError):
            continue
        if v not in ("0", "Unavailable") and int(v) > 100000:
            found = int(f.split("_")[-1])
            break
    proc.wait(timeout=15)
    os.rmdir(grp)
    if found is None:
        raise RuntimeError(f"could not discover domain for cpu{cpu}")
    return found


def write_schemata(grp, domain, l3, smba="2048", ndomains=32):
    parts = [f"{d}={l3 if d == domain else 'ffff'}" for d in range(ndomains)]
    smba_parts = [f"{d}={smba}" for d in range(ndomains)]
    with open(f"{grp}/schemata", "w") as f:
        f.write("L3:" + ";".join(parts) + "\n")
        f.write("SMBA:" + ";".join(smba_parts) + "\n")


def read_mbm(grp, domain):
    # mon_data enumerates ALL domains under every group -- must target the
    # DISCOVERED domain, not a hardcoded mon_L3_00 (that class of bug hit
    # twice already this investigation: the schemata writer and
    # probe_ccx0_mechanism.py's own read_mbm).
    for _ in range(10):
        with open(f"{grp}/mon_data/mon_L3_{domain:02d}/mbm_total_bytes") as f:
            v = f.read().strip()
        if v != "Unavailable":
            return int(v)
        time.sleep(0.5)
    raise RuntimeError(f"mbm stayed Unavailable on domain {domain}")


def read_occ(grp, domain):
    with open(f"{grp}/mon_data/mon_L3_{domain:02d}/llc_occupancy") as f:
        v = f.read().strip()
    return None if v == "Unavailable" else int(v)


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


def occ_sampler(grp, domain, stop_evt, samples):
    while not stop_evt.is_set():
        v = read_occ(grp, domain)
        if v is not None:
            samples.append(v)
        time.sleep(0.25)


def run_victim_once(victim_cpu):
    vproc = subprocess.run(
        f"{VICTIM} -c {victim_cpu} -w 4096 -P -d {VICTIM_DUR} -W {VICTIM_WARMUP}",
        shell=True, capture_output=True, text=True)
    line = next((l for l in vproc.stdout.splitlines() if l.startswith("VICTIM")), "")
    vdata = parse_victim(line)
    return (vdata.get("cycles", 0) / vdata["iters"]) if vdata.get("iters") else None


def run_arm(name, victim_cpu, agg_cores, domain, vgrp, agrp, kind, param, rep, outf, verify_msr=False):
    if kind == "wc_wb":
        write_schemata(vgrp, domain, "ffff")
        write_schemata(agrp, domain, "ffff")
    elif kind == "wb_cat":
        write_schemata(vgrp, domain, "ff00")
        write_schemata(agrp, domain, "00ff")
    else:
        write_schemata(vgrp, domain, "ffff")
        write_schemata(agrp, domain, "ffff")

    agg = None
    agg_dur = VICTIM_WARMUP + VICTIM_DUR + 8
    mbm0 = t0 = None
    if kind in ("wc_wb", "wb_cat"):
        mode = param  # "wb_load" or "wc_ntdqa"
        mbm0 = read_mbm(agrp, domain)
        t0 = time.time()
        agg = subprocess.Popen(
            f"{AGGRESSOR} -m {mode} -t {len(agg_cores.split(','))} -c {agg_cores} -N 2 -s 64 -d {agg_dur} "
            f"> /tmp/ccxsess_agg.log 2>&1", shell=True)
        time.sleep(AGG_SETTLE)
    elif kind == "flush":
        mbm0 = read_mbm(agrp, domain)
        t0 = time.time()
        agg = subprocess.Popen(
            f"{FLUSH_AGGRESSOR} -t {len(agg_cores.split(','))} -c {agg_cores} -N 2 -s 64 -d {agg_dur} -f {param} "
            f"> /tmp/ccxsess_agg.log 2>&1", shell=True)
        time.sleep(AGG_SETTLE)
    elif kind == "nthreads":
        n = param
        if n > 0:
            cores = ",".join(agg_cores.split(",")[:n])
            mbm0 = read_mbm(agrp, domain)
            t0 = time.time()
            agg = subprocess.Popen(
                f"{AGGRESSOR} -m wb_load -t {n} -c {cores} -N 2 -s 64 -d {agg_dur} "
                f"> /tmp/ccxsess_agg.log 2>&1", shell=True)
            time.sleep(AGG_SETTLE)

    msr_result = None
    if verify_msr and agg is not None:
        first_agg_cpu = int(agg_cores.split(",")[0])
        v_assoc = read_msr(victim_cpu, PQR_ASSOC)
        a_assoc = read_msr(first_agg_cpu, PQR_ASSOC)
        v_closid, a_closid = (v_assoc >> 32) & 0xffffffff, (a_assoc >> 32) & 0xffffffff
        v_mask = read_msr(victim_cpu, L3_MASK_BASE + v_closid)
        a_mask = read_msr(victim_cpu, L3_MASK_BASE + a_closid)
        msr_result = {"v_closid": v_closid, "v_mask": v_mask, "a_closid": a_closid, "a_mask": a_mask,
                      "disjoint": bool(v_mask) and bool(a_mask) and (v_mask & a_mask == 0)}

    stop_evt = threading.Event()
    occ_samples = []
    samp_thread = threading.Thread(target=occ_sampler, args=(vgrp, domain, stop_evt, occ_samples))
    samp_thread.start()

    cyc = run_victim_once(victim_cpu)

    stop_evt.set()
    samp_thread.join()

    agg_bw_self = mbm_bw = None
    if agg is not None:
        agg.wait(timeout=agg_dur + 10)
        if mbm0 is not None:
            mbm1 = read_mbm(agrp, domain)
            t1 = time.time()
            mbm_bw = (mbm1 - mbm0) / (t1 - t0) / 1e9
            try:
                with open("/tmp/ccxsess_agg.log") as f:
                    agg_bw_self = parse_agg_bw(f.read())
            except FileNotFoundError:
                pass

    rec = {
        "arm": name, "rep": rep, "cyc_per_iter": cyc,
        "agg_bw_self_gbps": agg_bw_self, "agg_mbm_bw_gbps": mbm_bw,
        "occ_mean_bytes": (sum(occ_samples) / len(occ_samples)) if occ_samples else None,
        "msr": msr_result,
    }
    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(f"  {name:14s} rep={rep:2d}  cyc/iter={cyc}  agg_bw={agg_bw_self}  "
          f"mbm_bw={mbm_bw}  occ={rec['occ_mean_bytes']}  msr={msr_result}", flush=True)


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    ccx_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    outpath = sys.argv[3] if len(sys.argv) > 3 else f"/tmp/clean_ccx{ccx_idx}_session.jsonl"

    base_cpu = ccx_idx * 8
    victim_cpu = base_cpu
    agg_cores = ",".join(str(base_cpu + i) for i in range(1, 8))
    vgrp, agrp = f"{RESCTRL}/ccxsess_v", f"{RESCTRL}/ccxsess_a"

    def handle_sigterm(signum, frame):
        sh("pkill -f 'bin/aggressor|bin/amd_flushbehind_aggressor' 2>/dev/null")
        sys.exit(1)
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    sh("pkill -f 'bin/aggressor|bin/amd_flushbehind_aggressor' 2>/dev/null")
    time.sleep(0.3)

    print(f"discovering domain for CCX{ccx_idx} (cpu{victim_cpu})...", flush=True)
    domain = discover_domain(victim_cpu, RESCTRL)
    print(f"CCX{ccx_idx} (cpu{victim_cpu}) -> resctrl domain {domain}, agg_cores={agg_cores}", flush=True)

    os.makedirs(vgrp, exist_ok=True)
    os.makedirs(agrp, exist_ok=True)
    open(f"{vgrp}/cpus_list", "w").write(str(victim_cpu))
    open(f"{agrp}/cpus_list", "w").write(agg_cores)

    ARMS = [
        ("quiescent", "none", None, False),
        ("wb", "wc_wb", "wb_load", False),
        ("wb_cat", "wb_cat", "wb_load", True),
        ("wc", "wc_wb", "wc_ntdqa", False),
        ("flush_d256kb", "flush", 256, False),
        ("t1", "nthreads", 1, False),
        ("t2", "nthreads", 2, False),
        ("t3", "nthreads", 3, False),
    ]

    try:
        with open(outpath, "w") as outf:
            for r in range(1, reps + 1):
                for name, kind, param, verify in ARMS:
                    run_arm(name, victim_cpu, agg_cores, domain, vgrp, agrp, kind, param, r, outf, verify)
    finally:
        sh("pkill -f 'bin/aggressor|bin/amd_flushbehind_aggressor' 2>/dev/null")
        time.sleep(0.3)
        for g in (vgrp, agrp):
            try:
                os.rmdir(g)
            except OSError:
                pass
    print(f"DONE -> {outpath}")


if __name__ == "__main__":
    main()
