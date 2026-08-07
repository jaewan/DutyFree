#!/usr/bin/env python3
"""
CORRECTED cross-CCX comparison, fixing a critical bug in
check_ccx_comparison.py: that script's write_schemata() hardcoded
"L3:0=..." regardless of which CCX was under test. AMD's resctrl L3
schemata is PER-DOMAIN (one CBM per CCX: "L3:0=...;1=...;2=...;...;31=..."),
and domain index does NOT track CCX index sequentially -- verified
directly: CCX0(cpu0)->domain0, CCX1(cpu8)->domain1, CCX2(cpu16)->domain8,
CCX3(cpu24)->domain9. The original script's CCX1/2/3 "wb_cat" arms wrote
their mask to domain 0 (CCX0's domain, where nobody was running) while
the actual domain for CCX1/2/3 stayed at default ffff (no partition) the
whole time -- CAT was never actually applied on non-CCX0 CCXes in that
test. This version discovers each CCX's true domain via a live occupancy
probe before writing schemata, and verifies the fix at the raw MSR level
(not just sysfs) on the actual CCX-under-test's cores, not just CCX0's.
"""
import subprocess, time, os, sys, statistics, struct

RESCTRL = "/sys/fs/resctrl"
BIN = "/home/domin/tmp_dutyfree_exp/bin"
VICTIM = f"{BIN}/victim"
AGGRESSOR = f"{BIN}/aggressor"

VICTIM_WARMUP = 2
VICTIM_DUR = 8
AGG_SETTLE = 2
AGG_DUR = VICTIM_WARMUP + VICTIM_DUR + 4

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


def discover_domain(cpu):
    """Run a tiny probe workload on `cpu` alone, in an unrestricted
    monitoring-only group, and find which mon_L3_NN lights up."""
    grp = f"{RESCTRL}/domdisc"
    os.makedirs(grp, exist_ok=True)
    open(f"{grp}/cpus_list", "w").write(str(cpu))
    proc = subprocess.Popen(
        f"{VICTIM} -c {cpu} -w 4096 -P -d 5 -W 1 > /tmp/domdisc.log 2>&1",
        shell=True)
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
    """Write the FULL per-domain schemata line, targeting `domain`
    specifically and leaving all others at full access -- this is the
    fix: the old version always wrote 'L3:0=...', regardless of domain."""
    parts = [f"{d}={l3 if d == domain else 'ffff'}" for d in range(ndomains)]
    smba_parts = [f"{d}={smba}" for d in range(ndomains)]
    with open(f"{grp}/schemata", "w") as f:
        f.write("L3:" + ";".join(parts) + "\n")
        f.write("SMBA:" + ";".join(smba_parts) + "\n")


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


def run_one(vgrp, agrp, domain, victim_cpu, agg_cores, name, mode, vL3, aL3, rep):
    write_schemata(vgrp, domain, vL3)
    write_schemata(agrp, domain, aL3)
    agg = None
    if mode is not None:
        agg = subprocess.Popen(
            f"{AGGRESSOR} -m {mode} -t 7 -c {agg_cores} -N 2 -s 64 -d {AGG_DUR} "
            f"> /tmp/ccxcmp2_agg.log 2>&1", shell=True)
        time.sleep(AGG_SETTLE)

    vproc = subprocess.run(
        f"{VICTIM} -c {victim_cpu} -w 4096 -P -d {VICTIM_DUR} -W {VICTIM_WARMUP}",
        shell=True, capture_output=True, text=True)
    line = next((l for l in vproc.stdout.splitlines() if l.startswith("VICTIM")), "")
    vdata = parse_victim(line)
    cyc = (vdata.get("cycles", 0) / vdata["iters"]) if vdata.get("iters") else None

    if agg is not None:
        agg.wait(timeout=AGG_DUR + 10)

    print(f"    {name:10s} rep={rep:2d}  cyc/iter={cyc:.0f}", flush=True)
    return cyc


def verify_msr(victim_cpu, agg_first_cpu, domain):
    """Read the real hardware state on the CCX under test, not CCX0."""
    v_assoc = read_msr(victim_cpu, PQR_ASSOC)
    a_assoc = read_msr(agg_first_cpu, PQR_ASSOC)
    v_closid = (v_assoc >> 32) & 0xffffffff
    a_closid = (a_assoc >> 32) & 0xffffffff
    v_mask = read_msr(victim_cpu, L3_MASK_BASE + v_closid)
    a_mask = read_msr(victim_cpu, L3_MASK_BASE + a_closid)
    print(f"    MSR verify: victim(cpu{victim_cpu}) CLOSID={v_closid} mask=0x{v_mask:04x}  "
          f"agg(cpu{agg_first_cpu}) CLOSID={a_closid} mask=0x{a_mask:04x}  "
          f"disjoint={bool(v_mask) and bool(a_mask) and (v_mask & a_mask == 0)}",
          flush=True)
    return v_closid, v_mask, a_closid, a_mask


def measure_ccx(ccx_idx, reps, base_cpu):
    victim_cpu = base_cpu
    agg_cores = ",".join(str(base_cpu + i) for i in range(1, 8))
    vgrp = f"{RESCTRL}/ccxcmp2_{ccx_idx}_v"
    agrp = f"{RESCTRL}/ccxcmp2_{ccx_idx}_a"

    sh("pkill -f 'bin/aggressor' 2>/dev/null")
    time.sleep(0.3)

    print(f"  discovering domain for CCX{ccx_idx} (cpu{victim_cpu})...", flush=True)
    domain = discover_domain(victim_cpu)
    print(f"  CCX{ccx_idx} (cpu{victim_cpu}) -> resctrl domain {domain}", flush=True)

    os.makedirs(vgrp, exist_ok=True)
    os.makedirs(agrp, exist_ok=True)
    open(f"{vgrp}/cpus_list", "w").write(str(victim_cpu))
    open(f"{agrp}/cpus_list", "w").write(agg_cores)

    print(f"  === CCX{ccx_idx} (victim=cpu{victim_cpu}, agg={agg_cores}, domain={domain}) ===",
          flush=True)
    q, wb, wbcat = [], [], []
    msr_check = None
    try:
        for r in range(1, reps + 1):
            q.append(run_one(vgrp, agrp, domain, victim_cpu, agg_cores, "quiescent", None, "ffff", "ffff", r))
            wb.append(run_one(vgrp, agrp, domain, victim_cpu, agg_cores, "wb", "wb_load", "ffff", "ffff", r))
            # for the wb_cat rep, launch aggressor, then verify MSRs mid-run, then measure
            write_schemata(vgrp, domain, "ff00")
            write_schemata(agrp, domain, "00ff")
            agg = subprocess.Popen(
                f"{AGGRESSOR} -m wb_load -t 7 -c {agg_cores} -N 2 -s 64 -d {AGG_DUR} "
                f"> /tmp/ccxcmp2_agg.log 2>&1", shell=True)
            time.sleep(AGG_SETTLE)
            if r == 1:
                msr_check = verify_msr(victim_cpu, int(agg_cores.split(",")[0]), domain)
            vproc = subprocess.run(
                f"{VICTIM} -c {victim_cpu} -w 4096 -P -d {VICTIM_DUR} -W {VICTIM_WARMUP}",
                shell=True, capture_output=True, text=True)
            line = next((l for l in vproc.stdout.splitlines() if l.startswith("VICTIM")), "")
            vdata = parse_victim(line)
            cyc = (vdata.get("cycles", 0) / vdata["iters"]) if vdata.get("iters") else None
            agg.wait(timeout=AGG_DUR + 10)
            print(f"    wb_cat     rep={r:2d}  cyc/iter={cyc:.0f}", flush=True)
            wbcat.append(cyc)
    finally:
        sh("pkill -f 'bin/aggressor' 2>/dev/null")
        time.sleep(0.3)
        try:
            os.rmdir(vgrp)
        except OSError:
            pass
        try:
            os.rmdir(agrp)
        except OSError:
            pass

    qm, wbm, wbcatm = statistics.median(q), statistics.median(wb), statistics.median(wbcat)
    print(f"  CCX{ccx_idx}: domain={domain}  quiescent={qm:.0f}  wb_tax={wbm/qm:.3f}  "
          f"wb_cat_tax={wbcatm/qm:.3f}  cat_benefit={(wbm/qm)/(wbcatm/qm):.3f}x  "
          f"msr={msr_check}", flush=True)
    return domain, qm, wbm/qm, wbcatm/qm, msr_check


def main():
    reps = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    ccx_bases = [(0, 0), (1, 8), (2, 16), (3, 24)]
    if len(sys.argv) > 2:
        wanted = set(int(x) for x in sys.argv[2].split(","))
        ccx_bases = [(c, b) for c, b in ccx_bases if c in wanted]

    results = {}
    for ccx, base in ccx_bases:
        results[ccx] = measure_ccx(ccx, reps, base)

    print("\n=== SUMMARY ===")
    print(f"{'CCX':>4s} {'domain':>7s} {'quiescent':>12s} {'wb_tax':>8s} {'wb_cat_tax':>11s} {'cat_benefit':>12s} {'msr_disjoint':>13s}")
    for ccx, (domain, qm, wbt, wbcatt, msr) in results.items():
        disjoint = msr[1] != 0 and msr[3] != 0 and (msr[1] & msr[3] == 0) if msr else None
        print(f"{ccx:4d} {domain:7d} {qm:12.0f} {wbt:8.3f} {wbcatt:11.3f} {wbt/wbcatt:12.3f} {str(disjoint):>13s}")


if __name__ == "__main__":
    main()
