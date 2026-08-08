#!/usr/bin/env python3
"""
Three cheap OS-level probes before conceding the CCX0 WB anomaly is
"beyond OS-level tooling" (panel-directed, per-CCX, using tooling already
built this campaign):

(1) per-CCX aggressor bandwidth (self-report + MBM) during the WB-loaded
    arm -- if CCX0's aggressors sustain different bandwidth/concurrency,
    the WB gap may be aggressor-side, not victim-side.
(2) per-CCX IDLE latency to local DRAM and to CXL (node2), no aggressor,
    large WSS (256 MiB, far exceeding the 16 MiB per-CCX L3 slice) so the
    victim's own pointer-chase becomes a real memory-latency probe. A
    GMI/quadrant fabric-distance asymmetry would show up here directly.
(3) per-CCX LOADED XI sampled latency (raw PMU encodings r01ac/r01ad
    dram_near, r10ac/r10ad ext_near) during the same WB-loaded arm as (1)
    -- the occupancy-relevant latency quantity, measured where it binds.

If all three come back flat across CCXes, the anomaly really is beyond
OS-level inspection; if any shows a CCX0-specific asymmetry, that's the
mechanism.
"""
import subprocess, time, os, sys, statistics

RESCTRL = "/sys/fs/resctrl"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"

VICTIM_WARMUP, VICTIM_DUR, AGG_SETTLE = 2, 8, 2
AGG_DUR = VICTIM_WARMUP + VICTIM_DUR + 4
IDLE_WSS_KB = 262144  # 256 MiB, far exceeds 16 MiB/CCX L3


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


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


def parse_perf_csv(path):
    out = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",")
                if len(parts) < 3:
                    continue
                val, unit, event = parts[0], parts[1], parts[2]
                try:
                    out[event] = int(val) if val not in ("<not counted>", "<not supported>") else None
                except ValueError:
                    out[event] = None
    except FileNotFoundError:
        pass
    return out


def discover_domain(cpu):
    """Live occupancy probe to find which resctrl L3 domain a CPU's CCX
    actually is -- domain index does NOT track CCX index sequentially
    (verified earlier: CCX0->0, CCX1->1, CCX2->8, CCX3->9)."""
    grp = f"{RESCTRL}/probe_domdisc"
    os.makedirs(grp, exist_ok=True)
    open(f"{grp}/cpus_list", "w").write(str(cpu))
    proc = subprocess.Popen(f"{VICTIM} -c {cpu} -w 4096 -P -d 5 -W 1 > /tmp/probe_domdisc.log 2>&1", shell=True)
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


def read_mbm(grp, domain):
    # NOTE: mon_data enumerates ALL domains under every group (mon_L3_00
    # .. mon_L3_31), not just the one the group's cpus live on -- reading
    # a hardcoded mon_L3_00 for a non-CCX0 group is the exact same class
    # of bug as the schemata domain-index mistake, just in the monitoring
    # path instead of the control path. Must use the DISCOVERED domain.
    for _ in range(10):
        with open(f"{grp}/mon_data/mon_L3_{domain:02d}/mbm_total_bytes") as f:
            v = f.read().strip()
        if v != "Unavailable":
            return int(v)
        time.sleep(0.5)
    raise RuntimeError(f"mbm stayed Unavailable on domain {domain}")


def probe1_3_loaded(ccx_idx, base_cpu, reps):
    """WB-loaded arm with aggressor bandwidth capture (1) and raw-encoding
    XI latency capture via perf (3), combined since both need the same
    live aggressor."""
    victim_cpu = base_cpu
    agg_cores = ",".join(str(base_cpu + i) for i in range(1, 8))
    vgrp, agrp = f"{RESCTRL}/probe1_{ccx_idx}_v", f"{RESCTRL}/probe1_{ccx_idx}_a"
    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)

    domain = discover_domain(victim_cpu)
    print(f"  CCX{ccx_idx} (cpu{victim_cpu}) -> resctrl domain {domain}", flush=True)

    os.makedirs(vgrp, exist_ok=True)
    os.makedirs(agrp, exist_ok=True)
    open(f"{vgrp}/cpus_list", "w").write(str(victim_cpu))
    open(f"{agrp}/cpus_list", "w").write(agg_cores)
    # writing ffff (full access, the default) to domain 0 specifically is
    # harmless here since no arm in this probe restricts CAT -- every
    # domain, including the real one, is already at ffff by default. Kept
    # simple (not full per-domain lines like check_ccx_comparison_v2.py's
    # write_schemata) since correctness doesn't depend on it for this probe.
    open(f"{vgrp}/schemata", "w").write("L3:0=ffff\nSMBA:0=2048\n")
    open(f"{agrp}/schemata", "w").write("L3:0=ffff\nSMBA:0=2048\n")
    time.sleep(1.0)  # let RMID/monitoring settle before the first mbm read

    agg_bws, dram_lats, ext_lats = [], [], []
    try:
        for r in range(1, reps + 1):
            agg_log = f"/tmp/probe1_{ccx_idx}_agg_{r}.log"
            mbm0 = read_mbm(agrp, domain)
            t0 = time.time()
            agg = subprocess.Popen(
                f"{AGGRESSOR} -m wb_load -t 7 -c {agg_cores} -N 2 -s 64 -d {AGG_DUR} "
                f"> {agg_log} 2>&1", shell=True)
            time.sleep(AGG_SETTLE)

            perf_out = f"/tmp/probe1_{ccx_idx}_perf_{r}.csv"
            perf_dur = VICTIM_WARMUP + VICTIM_DUR + 1
            perf_proc = subprocess.Popen(
                f"perf stat -e r01ac,r01ad,r10ac,r10ad -C {victim_cpu} -x, -o {perf_out} "
                f"-- sleep {perf_dur}", shell=True)
            time.sleep(0.2)

            # NOTE: cyc/iter is not reliable here -- the victim's own internal
            # perf_event_open counters (4: cycles/insns/l2_hit/l2_miss) plus
            # this external perf's 4 raw events exceed available PMCs on this
            # core, contending for counter slots. Not needed for this probe
            # (bandwidth/XI-latency only) -- the tax number is already known
            # from check_ccx_comparison_v2.py's clean, uncontended run.
            vproc = subprocess.run(
                f"{VICTIM} -c {victim_cpu} -w 4096 -P -d {VICTIM_DUR} -W {VICTIM_WARMUP}",
                shell=True, capture_output=True, text=True)

            perf_proc.wait(timeout=perf_dur + 5)
            agg.wait(timeout=AGG_DUR + 10)
            t1 = time.time()
            mbm1 = read_mbm(agrp, domain)

            with open(agg_log) as f:
                agg_bw = parse_agg_bw(f.read())
            mbm_bw = (mbm1 - mbm0) / (t1 - t0) / 1e9
            perf_data = parse_perf_csv(perf_out)
            dram_sum, dram_n = perf_data.get("r01ac"), perf_data.get("r01ad")
            ext_sum, ext_n = perf_data.get("r10ac"), perf_data.get("r10ad")
            dram_lat = (dram_sum / dram_n) if (dram_sum and dram_n) else None
            ext_lat = (ext_sum / ext_n) if (ext_sum and ext_n) else None

            agg_bws.append(agg_bw)
            if dram_lat:
                dram_lats.append(dram_lat)
            if ext_lat:
                ext_lats.append(ext_lat)

            print(f"    CCX{ccx_idx} rep={r} agg_bw(self)={agg_bw} "
                  f"agg_bw(mbm)={mbm_bw:.2f} dram_near_lat={dram_lat} ext_near_lat={ext_lat}",
                  flush=True)
            for f in (agg_log, perf_out):
                try:
                    os.remove(f)
                except OSError:
                    pass
    finally:
        sh("pkill -f 'bin/aggressor' 2>/dev/null")
        time.sleep(0.3)
        for g in (vgrp, agrp):
            try:
                os.rmdir(g)
            except OSError:
                pass

    return {
        "agg_bw_self_median": statistics.median([b for b in agg_bws if b]) if any(agg_bws) else None,
        "dram_near_lat_median": statistics.median(dram_lats) if dram_lats else None,
        "ext_near_lat_median": statistics.median(ext_lats) if ext_lats else None,
    }


def probe2_idle_latency(ccx_idx, base_cpu, reps):
    """Idle latency (no aggressor) to local DRAM (node0) vs CXL (node2),
    large WSS to defeat L3, per CCX."""
    victim_cpu = base_cpu
    results = {}
    for label, node in [("local", 0), ("cxl", 2)]:
        cyc_vals = []
        for r in range(1, reps + 1):
            cmd = (f"numactl --membind={node} --cpunodebind=0 -- {VICTIM} "
                   f"-c {victim_cpu} -n {node} -w {IDLE_WSS_KB} -P -d 4 -W 1")
            vproc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            line = next((l for l in vproc.stdout.splitlines() if l.startswith("VICTIM")), "")
            vdata = parse_victim(line)
            if vdata.get("iters"):
                # chase_steps = ws_bytes / 64 (pnode_t is cache-line sized)
                ws_bytes = IDLE_WSS_KB * 1024
                chase_steps = ws_bytes // 64
                cyc_per_access = (vdata["cycles"] / vdata["iters"]) / chase_steps
                cyc_vals.append(cyc_per_access)
                print(f"    CCX{ccx_idx} {label:6s} rep={r} cyc/access={cyc_per_access:.2f}", flush=True)
        if cyc_vals:
            results[f"{label}_cyc_per_access"] = statistics.median(cyc_vals)
    return results


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    ccx_bases = [(0, 0), (1, 8), (2, 16), (3, 24)]
    if len(sys.argv) > 2:
        wanted = set(int(x) for x in sys.argv[2].split(","))
        ccx_bases = [(c, b) for c, b in ccx_bases if c in wanted]

    all_results = {}
    for ccx, base in ccx_bases:
        print(f"=== CCX{ccx} (cpu{base}): probe 1+3 (loaded, aggressor bw + XI latency) ===", flush=True)
        r13 = probe1_3_loaded(ccx, base, reps)
        print(f"=== CCX{ccx} (cpu{base}): probe 2 (idle latency, local vs CXL) ===", flush=True)
        r2 = probe2_idle_latency(ccx, base, reps)
        all_results[ccx] = {**r13, **r2}
        print(f"CCX{ccx} SUMMARY: {all_results[ccx]}", flush=True)

    print("\n=== FULL SUMMARY ===")
    print(f"{'CCX':>4s} {'agg_bw_self':>12s} {'dram_near_lat':>14s} {'ext_near_lat':>13s} "
          f"{'idle_local_cyc':>15s} {'idle_cxl_cyc':>13s}")
    for ccx, r in all_results.items():
        print(f"{ccx:4d} {r.get('agg_bw_self_median'):>12} {r.get('dram_near_lat_median'):>14} "
              f"{r.get('ext_near_lat_median'):>13} {r.get('local_cyc_per_access'):>15} "
              f"{r.get('cxl_cyc_per_access'):>13}")


if __name__ == "__main__":
    main()
