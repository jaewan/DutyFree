#!/usr/bin/env python3
"""
Delta audit runner for AMD clean-CCX1.

Run on broker as root:
  sudo /usr/bin/python3 /home/domin/tmp_dutyfree_exp/delta_audit/run_delta_audit.py \
    12 /home/domin/tmp_dutyfree_exp/delta_audit/delta_audit_raw_n12.jsonl
"""
import json
import os
import signal
import subprocess
import sys
import threading
import time

RESCTRL = "/sys/fs/resctrl"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"
DELTA_AGGRESSOR = f"{BIN}/amd_delta_aggressor"

VICTIM_WARMUP = 2
VICTIM_DUR = 8
AGG_SETTLE = 2
AGG_DUR = VICTIM_WARMUP + VICTIM_DUR + 8
CCX_IDX = 1
VICTIM_CPU = 8
AGG_CORES = "9,10,11,12,13,14,15"
PERF_EVENTS = "rff04,rfe04,r0104,r10ac,r10ad,r01ac,r01ad"

FLUSH_RATIO = 17.03 / 24.69
T2_TARGET_GBPS = 11.5


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def parse_victim(line):
    out = {}
    for tok in line.split():
        if "=" not in tok:
            continue
        key, value = tok.split("=", 1)
        try:
            out[key] = float(value) if "." in value else int(value)
        except ValueError:
            out[key] = value
    return out


def parse_result(text):
    out = {}
    for line in text.splitlines():
        if not line.startswith("RESULT"):
            continue
        for tok in line.split()[1:]:
            if "=" not in tok:
                continue
            key, value = tok.split("=", 1)
            try:
                out[key] = float(value) if "." in value else int(value)
            except ValueError:
                out[key] = value
    return out


def parse_perf_csv(path):
    names = {
        "rff04": "l3_lookup_state.all_coherent_accesses_to_l3",
        "rfe04": "l3_lookup_state.l3_hit",
        "r0104": "l3_lookup_state.l3_miss",
        "r10ac": "l3_xi_sampled_latency.ext_near",
        "r10ad": "l3_xi_sampled_latency_requests.ext_near",
        "r01ac": "l3_xi_sampled_latency.dram_near",
        "r01ad": "l3_xi_sampled_latency_requests.dram_near",
    }
    out = {}
    try:
        text = open(path).read()
    except FileNotFoundError:
        return {"error": "missing_perf_output"}
    for line in text.splitlines():
        parts = line.strip().split(",")
        if len(parts) < 3 or not parts[0] or parts[0].startswith("#"):
            continue
        value, event = parts[0], parts[2]
        key = names.get(event, event)
        try:
            out[key] = float(value)
        except ValueError:
            out[key] = None
    return out


def discover_domain(cpu, grp_base):
    grp = f"{grp_base}/delta_domdisc"
    os.makedirs(grp, exist_ok=True)
    open(f"{grp}/cpus_list", "w").write(str(cpu))
    proc = subprocess.Popen(
        f"{VICTIM} -c {cpu} -w 4096 -P -d 5 -W 1 >/tmp/delta_domdisc.log 2>&1",
        shell=True,
    )
    time.sleep(3)
    found = None
    for ent in sorted(os.listdir(f"{grp}/mon_data")):
        path = f"{grp}/mon_data/{ent}/llc_occupancy"
        try:
            val = open(path).read().strip()
        except OSError:
            continue
        if val not in ("0", "Unavailable") and int(val) > 100000:
            found = int(ent.split("_")[-1])
            break
    proc.wait(timeout=15)
    os.rmdir(grp)
    if found is None:
        raise RuntimeError(f"could not discover resctrl domain for cpu{cpu}")
    return found


def write_schemata(grp, domain, l3="ffff", smba="2048", ndomains=32):
    l3_parts = [f"{d}={l3 if d == domain else 'ffff'}" for d in range(ndomains)]
    smba_parts = [f"{d}={smba}" for d in range(ndomains)]
    with open(f"{grp}/schemata", "w") as f:
        f.write("L3:" + ";".join(l3_parts) + "\n")
        f.write("SMBA:" + ";".join(smba_parts) + "\n")


def read_resctrl_counter(grp, domain, name):
    path = f"{grp}/mon_data/mon_L3_{domain:02d}/{name}"
    for _ in range(10):
        val = open(path).read().strip()
        if val != "Unavailable":
            return int(val)
        time.sleep(0.5)
    raise RuntimeError(f"{name} stayed Unavailable on domain {domain}")


def occ_sampler(grp, domain, stop_evt, samples):
    while not stop_evt.is_set():
        try:
            samples.append(read_resctrl_counter(grp, domain, "llc_occupancy"))
        except Exception:
            pass
        time.sleep(0.25)


def start_aggressor(arm):
    if arm == "wb":
        return (
            f"{AGGRESSOR} -m wb_load -t 7 -c {AGG_CORES} -N 2 -s 64 -d {AGG_DUR}",
            "wb_load",
        )
    if arm == "wb_matched":
        return (
            f"{AGGRESSOR} -m wb_load -t 7 -c {AGG_CORES} -N 2 -s 64 -d {AGG_DUR} -R 3200",
            "wb_load_rate_matched",
        )
    if arm == "flush1":
        return (
            f"{DELTA_AGGRESSOR} -m flushbehind -t 7 -c {AGG_CORES} -N 2 -s 64 "
            f"-d {AGG_DUR} -f 256 -F 1",
            "flushbehind_1x",
        )
    if arm == "flush2":
        return (
            f"{DELTA_AGGRESSOR} -m flushbehind -t 7 -c {AGG_CORES} -N 2 -s 64 "
            f"-d {AGG_DUR} -f 256 -F 2",
            "flushbehind_2x",
        )
    if arm == "flush1_matched":
        return (
            f"{DELTA_AGGRESSOR} -m flushbehind -t 7 -c {AGG_CORES} -N 2 -s 64 "
            f"-d {AGG_DUR} -f 256 -F 1 -R {T2_TARGET_GBPS:.3f}",
            "flushbehind_1x_rate_matched",
        )
    if arm == "flush2_matched":
        return (
            f"{DELTA_AGGRESSOR} -m flushbehind -t 7 -c {AGG_CORES} -N 2 -s 64 "
            f"-d {AGG_DUR} -f 256 -F 2 -R {T2_TARGET_GBPS:.3f}",
            "flushbehind_2x_rate_matched",
        )
    if arm == "wb_plus_flush":
        return (
            f"{DELTA_AGGRESSOR} -m wb_plus_flush -t 7 -c {AGG_CORES} -N 2 -s 64 "
            f"-S 4 -d {AGG_DUR} -q {FLUSH_RATIO:.8f}",
            "wb_plus_disjoint_flush",
        )
    return None, None


def run_arm(arm, rep, domain, vgrp, agrp, outf):
    write_schemata(vgrp, domain)
    write_schemata(agrp, domain)

    cmd, mode = start_aggressor(arm)
    agg = None
    agg_log = f"/tmp/delta_agg_{arm}_{rep}.log"
    mbm0 = local0 = t0 = None
    if cmd:
        mbm0 = read_resctrl_counter(agrp, domain, "mbm_total_bytes")
        local0 = read_resctrl_counter(agrp, domain, "mbm_local_bytes")
        t0 = time.time()
        agg = subprocess.Popen(f"{cmd} >{agg_log} 2>&1", shell=True)
        time.sleep(AGG_SETTLE)

    stop_evt = threading.Event()
    occ_samples = []
    sampler = threading.Thread(target=occ_sampler, args=(vgrp, domain, stop_evt, occ_samples))
    sampler.start()

    victim = subprocess.run(
        f"{VICTIM} -c {VICTIM_CPU} -w 4096 -P -d {VICTIM_DUR} -W {VICTIM_WARMUP}",
        shell=True,
        capture_output=True,
        text=True,
    )

    stop_evt.set()
    sampler.join()

    vline = next((line for line in victim.stdout.splitlines() if line.startswith("VICTIM")), "")
    if not vline:
        raise RuntimeError(f"victim produced no VICTIM line for {arm} rep {rep}: {victim.stderr}")
    vdata = parse_victim(vline)
    cyc = (vdata.get("cycles", 0) / vdata["iters"]) if vdata.get("iters") else None
    if not cyc:
        raise RuntimeError(f"victim counters invalid for {arm} rep {rep}: {vline} stderr={victim.stderr}")

    perf_out = f"/tmp/delta_perf_{arm}_{rep}.csv"
    perf_sleep = 4 if agg else 1
    perf = subprocess.run(
        f"perf stat -e {PERF_EVENTS} -C {VICTIM_CPU} -x, -o {perf_out} -- sleep {perf_sleep}",
        shell=True,
        capture_output=True,
        text=True,
    )
    perf_data = parse_perf_csv(perf_out)
    if perf.returncode != 0:
        perf_data["error"] = perf.stderr.strip() or f"perf_rc={perf.returncode}"

    agg_result = {}
    mbm_bw = mbm_local_bw = None
    if agg:
        agg.wait(timeout=AGG_DUR + 10)
        t1 = time.time()
        mbm1 = read_resctrl_counter(agrp, domain, "mbm_total_bytes")
        local1 = read_resctrl_counter(agrp, domain, "mbm_local_bytes")
        mbm_bw = (mbm1 - mbm0) / (t1 - t0) / 1e9
        mbm_local_bw = (local1 - local0) / (t1 - t0) / 1e9
        agg_result = parse_result(open(agg_log).read())

    rec = {
        "arm": arm,
        "mode": mode,
        "rep": rep,
        "ccx": CCX_IDX,
        "domain": domain,
        "victim_cpu": VICTIM_CPU,
        "agg_cores": AGG_CORES if cmd else None,
        "flush_ratio": FLUSH_RATIO if arm == "wb_plus_flush" else None,
        "t2_target_gbps": T2_TARGET_GBPS if arm in ("flush1_matched", "flush2_matched") else None,
        "victim": vdata,
        "cyc_per_iter": cyc,
        "agg_result": agg_result,
        "agg_bw_self_gbps": agg_result.get("stream_bw_gbps") or agg_result.get("bw_gbps"),
        "agg_mbm_total_gbps": mbm_bw,
        "agg_mbm_local_gbps": mbm_local_bw,
        "victim_llc_occ_bytes": {
            "n": len(occ_samples),
            "mean": sum(occ_samples) / len(occ_samples) if occ_samples else None,
        },
        "perf_raw": perf_data,
    }
    perf_raw = rec["perf_raw"]
    ext_lat, ext_req = (
        perf_raw.get("l3_xi_sampled_latency.ext_near"),
        perf_raw.get("l3_xi_sampled_latency_requests.ext_near"),
    )
    rec["xi_ext_cycles_per_request"] = (ext_lat / ext_req) if ext_lat and ext_req else None

    outf.write(json.dumps(rec) + "\n")
    outf.flush()
    print(
        f"{arm:14s} rep={rep:02d} cyc={cyc:.0f} "
        f"self={rec['agg_bw_self_gbps']} mbm={mbm_bw} local={mbm_local_bw} "
        f"flush_mops={agg_result.get('flush_mops')} xi_req={ext_req}",
        flush=True,
    )

    for path in (agg_log, perf_out):
        try:
            os.remove(path)
        except OSError:
            pass


def cleanup(vgrp, agrp):
    sh("pkill -f 'bin/aggressor|bin/amd_flushbehind_aggressor|bin/amd_delta_aggressor' 2>/dev/null")
    time.sleep(0.3)
    for grp in (vgrp, agrp):
        try:
            os.rmdir(grp)
        except OSError:
            pass


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    outpath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/delta_audit_raw.jsonl"
    os.makedirs(os.path.dirname(outpath) or ".", exist_ok=True)
    vgrp, agrp = f"{RESCTRL}/delta_v", f"{RESCTRL}/delta_a"

    signal.signal(signal.SIGINT, lambda *_: (cleanup(vgrp, agrp), sys.exit(1)))
    signal.signal(signal.SIGTERM, lambda *_: (cleanup(vgrp, agrp), sys.exit(1)))

    cleanup(vgrp, agrp)
    domain = discover_domain(VICTIM_CPU, RESCTRL)
    registry = {
        "host": os.uname().nodename,
        "ccx": CCX_IDX,
        "victim_cpu": VICTIM_CPU,
        "agg_cores": AGG_CORES,
        "resctrl_domain": domain,
        "perf_events": PERF_EVENTS,
        "event_names": {
            "rff04": "l3_lookup_state.all_coherent_accesses_to_l3",
            "rfe04": "l3_lookup_state.l3_hit",
            "r0104": "l3_lookup_state.l3_miss",
            "r10ac": "l3_xi_sampled_latency.ext_near",
            "r10ad": "l3_xi_sampled_latency_requests.ext_near",
            "r01ac": "l3_xi_sampled_latency.dram_near",
            "r01ad": "l3_xi_sampled_latency_requests.dram_near",
        },
        "flush_ratio_wb_plus_flush": FLUSH_RATIO,
        "t2_target_gbps": T2_TARGET_GBPS,
    }
    open(os.path.join(os.path.dirname(outpath), "delta_audit_event_registry.json"), "w").write(
        json.dumps(registry, indent=2) + "\n"
    )

    os.makedirs(vgrp, exist_ok=True)
    os.makedirs(agrp, exist_ok=True)
    open(f"{vgrp}/cpus_list", "w").write(str(VICTIM_CPU))
    open(f"{agrp}/cpus_list", "w").write(AGG_CORES)

    arms = ["quiescent", "wb", "flush1", "flush1_matched", "flush2_matched", "wb_plus_flush"]
    if len(sys.argv) > 3:
        arms = [a for a in sys.argv[3].split(",") if a]
    try:
        with open(outpath, "w") as outf:
            for rep in range(1, reps + 1):
                for arm in arms:
                    run_arm(arm, rep, domain, vgrp, agrp, outf)
    finally:
        cleanup(vgrp, agrp)
    print(f"DONE {outpath}")


if __name__ == "__main__":
    main()
