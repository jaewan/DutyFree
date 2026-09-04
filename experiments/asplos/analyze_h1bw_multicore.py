#!/usr/bin/env python3
"""Multi-core H1 bandwidth survival (4c / 8c) -- analyzer.

Pre-registration: H1BW_MULTICORE_PREREG_2026-09-03.md.  Every threshold and
every frozen geometry below is a module constant, not an argument, so that
changing one after seeing data is visible in git (the W1 rule).

Reads six `se.py` multi-program outdirs and, for each, judges the three
pre-registered gates before reporting anything.  A run that fails a gate is
printed as VOID and contributes no number to the verdict; per S5.1 the arm's
identity is taken from its own `config.ini`, never from MANIFEST or the runner.

The realized-vs-requested discipline (F9) is why the LLC, the CXL latency and
the memory bandwidth ceiling are all read back out of `config.ini` rather than
echoed from the manifest.

Usage: analyze_h1bw_multicore.py [campaign-date]      default 20260904
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path

LOGROOT = "/home/domin/DutyFree/gem5/logs/se_chi"
OUT_JSONL = Path("/home/domin/DutyFree/experiments/asplos/data/gem5/h1bw_multicore.jsonl")
DEFAULT_STAMP = "20260904"      # runner's STAMP is host-local; prereg is dated 09-03

# --- frozen configuration (H1BW_MULTICORE_PREREG_2026-09-03.md, "Frozen configuration")
ARMS = ("wb", "h2", "pfoff")
NCORES = (4, 8)
ARM_POLICY = {"wb": "wb", "h2": "stream", "pfoff": "stream"}
L3_PER_SLICE = 5 * 1024 * 1024          # 5 MiB / 20-way per HNF slice
L3_ASSOC = 20
PER_CORE_BYTES = 8 * 1024 * 1024        # 8 MiB per instance
PASSES = 2                              # --warmups 1 --reps 1
L1_MSHR = 48
HNF_TBE_PER_SLICE = 32                  # CHI_config_8592.py:435, HNF_MSHR unset
SNF_TBE = 256                           # CHI_config_8592.py:961, SNF_MSHR unset
CXL_LATENCY_NS = 203.0
LINE_BYTES = 64
CPU_HZ = 1.9e9
RUBY_TICKS_PER_CY = 500                 # system.ruby.clk_domain.clock -> 2 GHz
TICKS_PER_S = 1e12

# --- pre-registered outcome table ("Pre-declared outcomes")
# PASS    ordering h2 >= wb > pfoff at BOTH core counts
# PARTIAL ordering holds at one core count only
# NULL    ordering does not hold anywhere (publishable; the paper sentence comes out)

# HNF transaction types that carry the fact stream; used for the occupancy model.
HNF_TRANS = ("ReadShared", "ReadUnique_PoC", "WriteBackFull", "WriteEvictFull")

# --- A1 engagement thresholds, added 2026-09-03.
# A1 originally tested only `bypasses > 0`, which certified the slice-bracket
# cell `h2_4c_l3x1` in which the streaming mechanism had collapsed 24.5x and was
# suppressing 1.2% of its WB peer's LLC fills.  Both measures are fail-closed
# and identical to the ones in analyze_h1bw_bracket.py, so a cell that would be
# voided there is voided here.  See H2_BYPASS_COLLAPSE_2026-09-03.md.
A1_MIN_FILL_SUPPRESSION = 0.20          # 1 - arm_fills / wb_fills, same core count
A1_MIN_BYPASS_PER_DECISION = 0.20       # bypasses / HNF write allocation decisions


def mark(name, ok, detail):
    print(f"  {name:46s} {'PASS' if ok else 'FAIL'}  {detail}")
    return ok


def load_stats(path):
    d = {}
    with open(path, errors="replace") as f:
        for line in f:
            line = line.split("#")[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    d[parts[0]] = float(parts[1])
                except ValueError:
                    pass
    return d


def load_ini(path):
    """config.ini -> {section: {key: value}}.  The realized-geometry authority."""
    secs, cur = {}, None
    with open(path, errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("[") and line.endswith("]"):
                cur = line[1:-1]
                secs[cur] = {}
            elif cur is not None and "=" in line:
                k, v = line.split("=", 1)
                secs[cur][k] = v
    return secs


def instance_lines(path):
    """One JSON line per instance, printed by run_stream() on completion."""
    out = []
    with open(path, errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith('{"mode"') and line.endswith("}"):
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def hnf_slices(ini):
    """Realized HNF geometry, read back from config.ini (F9)."""
    pat = re.compile(r"^system\.ruby\.hnf(\d+)\.cntrl\.cache$")
    out = {}
    for name, body in ini.items():
        m = pat.match(name)
        if m:
            out[int(m.group(1))] = (int(body["size"]), int(body["assoc"]))
    return out


def mem_ceiling_gbps(ini, section):
    """SimpleMemory.bandwidth is TICKS PER BYTE, not bytes/s.  Invert it."""
    tpb = float(ini[section]["bandwidth"])
    return (TICKS_PER_S / tpb) / 1e9 if tpb else float("inf")


def hnf_read_latency_ns(stats, nslices):
    """Sample-weighted HNF in-transaction latency = TBE occupancy per request.

    inTransLatHist is in Ruby cycles; ReadShared/ReadUnique carry the stream.
    """
    num = den = 0.0
    for i in range(nslices):
        for t in ("ReadShared", "ReadUnique_PoC"):
            b = f"system.ruby.hnf{i}.cntrl.inTransLatHist.{t}"
            n = stats.get(b + "::samples", 0.0)
            m = stats.get(b + "::mean", 0.0)
            num += n * m
            den += n
    if not den:
        return None
    return (num / den) * RUBY_TICKS_PER_CY / TICKS_PER_S * 1e9


def analyze(outdir, arm, n):
    r = {"run": f"h1bw_mc_{arm}_{n}c", "outdir": outdir, "arm": arm, "ncores": n}
    need = ("console.log", "stats.txt", "config.ini", "MANIFEST.json", "DONE.json")
    missing = [f for f in need if not os.path.exists(os.path.join(outdir, f))]
    if missing:
        r.update(completed=False, reason=f"missing {','.join(missing)}")
        return r

    console = os.path.join(outdir, "console.log")
    stats = load_stats(os.path.join(outdir, "stats.txt"))
    ini = load_ini(os.path.join(outdir, "config.ini"))
    inst = instance_lines(console)
    manifest = json.loads(Path(outdir, "MANIFEST.json").read_text())
    done = json.loads(Path(outdir, "DONE.json").read_text())
    log = Path(console).read_text(errors="replace")

    # ---- provenance
    r["gem5_exit"] = done.get("exit")
    r["started"], r["ended"] = manifest.get("started"), done.get("ended")
    r["bench_sha256"] = manifest.get("bench_sha256")
    r["gem5_sha256"] = manifest.get("gem5_sha256")
    r["host"] = manifest.get("host")
    # Latent teardown defect: free() fires after the JSON and before a clean
    # exit, so it cannot touch a reported number -- but it is not deterministic.
    r["free_invalid_size"] = log.count("free(): invalid size")
    r["reached_exit"] = "Exiting @ tick" in log

    # ---- realized identity, from the artifact (S5.1)
    cmds = re.findall(r"^cmd=(.*)$", Path(outdir, "config.ini").read_text(errors="replace"), re.M)
    pols = {m.group(1) for c in cmds for m in [re.search(r"--policy (\S+)", c)] if m}
    r["realized_policy"] = sorted(pols)[0] if len(pols) == 1 else f"MIXED:{sorted(pols)}"
    r["realized_instances"] = len(inst)
    r["realized_workloads"] = len(cmds)
    r["prefetcher_sections"] = sum(1 for s in ini if "prefetcher" in s.lower())

    # ---- realized geometry, from the artifact (F9)
    slices = hnf_slices(ini)
    r["hnf_slices"] = len(slices)
    r["llc_bytes_realized"] = sum(s for s, _ in slices.values())
    r["l3_per_slice_realized"] = sorted({s for s, _ in slices.values()})
    r["l3_assoc_realized"] = sorted({a for _, a in slices.values()})
    r["cxl_latency_ns_realized"] = float(ini["system.mem_ctrls1"]["latency"]) / 1000.0
    r["dram_latency_ns_realized"] = float(ini["system.mem_ctrls0"]["latency"]) / 1000.0
    r["mem_type_realized"] = ini["system.mem_ctrls1"]["type"]
    r["cxl_bw_ceiling_gbps"] = round(mem_ceiling_gbps(ini, "system.mem_ctrls1"), 3)

    # ---- pre-registered gates.  Fail-closed: void, do not report.
    statuses = [x.get("status") for x in inst]
    r["all_status_ok"] = bool(inst) and all(s == "ok" for s in statuses)
    r["g_instances"] = r["realized_instances"] == n
    r["g_llc"] = r["llc_bytes_realized"] == n * L3_PER_SLICE
    r["completed"] = bool(r["all_status_ok"] and r["g_instances"] and r["g_llc"])
    if not r["completed"]:
        r["reason"] = "; ".join(
            x for x in (
                None if r["all_status_ok"] else f"status={statuses}",
                None if r["g_instances"] else f"instances={r['realized_instances']}!={n}",
                None if r["g_llc"] else f"llc={r['llc_bytes_realized']}!={n*L3_PER_SLICE}",
            ) if x)
        return r
    r["reason"] = "ok"

    # ---- metric 1: agg_bw_sum (prereg "Metrics" 1)
    bws = sorted((x["bandwidth_gbps"] for x in inst), reverse=True)
    secs = [x["seconds"] for x in inst]
    r["per_instance_bw_gbps"] = bws
    r["agg_bw_sum"] = sum(bws)
    r["bw_per_core"] = r["agg_bw_sum"] / n
    r["bw_spread_pct"] = (max(bws) - min(bws)) / (sum(bws) / n) * 100.0
    # reps=1, so `samples` has one entry and cov is identically 0: there is no
    # within-instance variance estimate anywhere in this campaign.
    r["reps_per_instance"] = len(inst[0].get("samples", []))
    r["within_instance_cov"] = inst[0].get("cov")

    # ---- metric 2: agg_bw_wall (prereg "Metrics" 2) -- reported, then rejected
    total_bytes = n * PER_CORE_BYTES
    r["total_bytes"] = total_bytes
    r["simSeconds"] = stats["simSeconds"]
    r["agg_bw_wall"] = total_bytes / stats["simSeconds"] / 1e9
    r["measured_window_s"] = [round(s, 9) for s in sorted(secs)]
    r["measured_window_frac_of_sim"] = (sum(secs) / n) / stats["simSeconds"]
    r["agg_bw_wall_over_sum"] = r["agg_bw_wall"] / r["agg_bw_sum"]
    # The only reconstructable window-scoped denominator: bytes over the widest
    # single instance window.  Not the true span (no start timestamps exist).
    r["agg_bw_maxwindow"] = total_bytes / max(secs) / 1e9

    # ---- window alignment.  No barrier exists, so bound the skew instead.
    # run_stream() emits its JSON and frees immediately after the measured pass,
    # so each instance's window ends a near-constant distance before its own
    # exit; program-length skew across cores therefore bounds window skew.
    cycles = [stats[f"system.cpu{i}.numCycles"] for i in range(n)]
    r["cpu_cycles_min"], r["cpu_cycles_max"] = min(cycles), max(cycles)
    skew_s = (max(cycles) - min(cycles)) / CPU_HZ
    r["exit_skew_s"] = skew_s
    r["exit_skew_pct_of_window"] = skew_s / min(secs) * 100.0
    r["window_overlap_floor"] = max(0.0, (min(secs) - skew_s) / min(secs))

    # ---- LLC residency: is the measured pass served from the LLC or from CXL?
    nsl = len(slices)
    acc = hit = fills = byp = 0.0
    per_slice = []
    for i in range(nsl):
        b = f"system.ruby.hnf{i}.cntrl.cache."
        a = stats.get(b + "m_demand_accesses", 0.0) + stats.get(b + "m_prefetch_accesses", 0.0)
        h = stats.get(b + "m_demand_hits", 0.0) + stats.get(b + "m_prefetch_hits", 0.0)
        acc += a
        hit += h
        per_slice.append(a)
        fills += stats.get(b + "numDataArrayWrites", 0.0)
        byp += stats.get(b + "streamingHnfFillBypasses", 0.0)
    r["hnf_accesses"] = acc
    r["hnf_hits"] = hit
    r["hnf_hit_frac"] = hit / acc if acc else None
    r["hnf_fills"] = fills
    r["hnf_streaming_bypasses"] = byp
    r["hnf_slice_imbalance"] = max(per_slice) / min(per_slice) if min(per_slice) else None
    # The population in which a bypass is possible at all.  This HNF allocates
    # only on writeback, so only WriteEvictFull/WriteBackFull present a fill
    # decision, and only when the LLC data entry is invalid -- dir state RU.
    # RU->I is what CacheMemory counts; RU->{I,UC,UD} is the denominator.
    dec = ret = arr = 0.0
    for i in range(nsl):
        b = f"system.ruby.hnf{i}.cntrl.inTransLatHist."
        for t in ("WriteEvictFull", "WriteBackFull"):
            arr += stats.get(f"{b}{t}::samples", 0.0)
            ret += stats.get(f"{b}{t}.retries", 0.0)
            for final in ("I", "UC", "UD"):
                dec += stats.get(f"{b}{t}.RU.{final}.total", 0.0)
    r["hnf_write_decisions"] = dec
    r["hnf_bypass_per_decision"] = byp / dec if dec else None
    r["hnf_write_arrivals"] = arr
    r["hnf_write_retries"] = ret
    r["hnf_write_retry_frac"] = ret / arr if arr else None
    # The decisive quantity: bytes the CXL controller actually delivered against
    # the two-pass demand.  >= 1.0 means the LLC supplied none of the stream.
    r["cxl_bytes_read"] = stats.get("system.mem_ctrls1.bytesRead::total", 0.0)
    r["cxl_bytes_written"] = stats.get("system.mem_ctrls1.bytesWritten::total", 0.0)
    r["dram_bytes_read"] = stats.get("system.mem_ctrls0.bytesRead::total", 0.0)
    r["twopass_demand_bytes"] = total_bytes * PASSES
    r["cxl_read_over_demand"] = r["cxl_bytes_read"] / r["twopass_demand_bytes"]

    # ---- MSHR-implied ceiling and realized memory-level parallelism
    r["mshr_ceiling_per_core_gbps"] = L1_MSHR * LINE_BYTES / (CXL_LATENCY_NS * 1e-9) / 1e9
    r["mshr_ceiling_frac"] = r["bw_per_core"] / r["mshr_ceiling_per_core_gbps"]
    lat_ns = hnf_read_latency_ns(stats, nsl)
    r["hnf_read_latency_ns"] = lat_ns
    lines_per_s = r["agg_bw_sum"] * 1e9 / LINE_BYTES
    r["hnf_concurrency"] = lines_per_s * lat_ns * 1e-9 if lat_ns else None
    r["hnf_tbe_budget"] = HNF_TBE_PER_SLICE * nsl
    r["hnf_tbe_occupancy_frac"] = (r["hnf_concurrency"] / r["hnf_tbe_budget"]
                                   if r["hnf_concurrency"] else None)
    r["l1_mshr_budget"] = L1_MSHR * n
    r["l1_mshr_occupancy_frac"] = (r["hnf_concurrency"] / r["l1_mshr_budget"]
                                   if r["hnf_concurrency"] else None)
    # SNF is the single --num-dirs=1 home for memory: the one unavoidably shared
    # structure.  Occupancy by Little's law over the measured window.
    r["snf_tbe_budget"] = SNF_TBE
    r["snf_concurrency"] = lines_per_s * CXL_LATENCY_NS * 1e-9
    r["snf_tbe_occupancy_frac"] = r["snf_concurrency"] / SNF_TBE
    r["snf_avg_util_wholerun"] = stats.get("system.ruby.snf.cntrl.avg_util")
    r["snf_req2mem_avg_stall_ticks"] = stats.get(
        "system.ruby.snf.cntrl.requestToMemory.m_avg_stall_time", 0.0)
    r["snf_datout_avg_stall_ticks"] = stats.get(
        "system.ruby.snf.cntrl.datOut.m_avg_stall_time", 0.0)
    r["mem_bw_used_frac"] = (r["agg_bw_sum"] / r["cxl_bw_ceiling_gbps"]
                             if r["cxl_bw_ceiling_gbps"] else None)

    r["simInsts"] = stats.get("simInsts")
    r["ipc_per_cpu"] = [stats.get(f"system.cpu{i}.ipc") for i in range(n)]
    return r


def wall_hours(rec):
    """Wall clock from MANIFEST 'started' to DONE 'ended'."""
    from datetime import datetime
    try:
        a = datetime.fromisoformat(rec["started"])
        b = datetime.fromisoformat(rec["ended"])
        return (b - a).total_seconds() / 3600.0
    except Exception:
        return None


def main(argv):
    stamp = argv[1] if len(argv) > 1 else DEFAULT_STAMP
    recs, voids = [], []
    for n in NCORES:
        for arm in ARMS:
            hits = sorted(glob.glob(f"{LOGROOT}/h1bw_mc_{arm}_{n}c_{stamp}"))
            if not hits:
                voids.append(f"h1bw_mc_{arm}_{n}c_{stamp}: no outdir")
                continue
            rec = analyze(hits[0], arm, n)
            rec["wall_hours"] = wall_hours(rec)
            recs.append(rec)

    by = {(r["arm"], r["ncores"]): r for r in recs}
    print("=" * 78)
    print(f"H1BW MULTICORE -- prereg H1BW_MULTICORE_PREREG_2026-09-03.md  (stamp {stamp})")
    print("=" * 78)

    # ---------------- gates ----------------
    print("\nPRE-REGISTERED GATES (fail-closed: a failing run is VOID, not reported)")
    for r in recs:
        tag = f"{r['arm']}_{r['ncores']}c"
        print(f"  {tag}")
        mark("G1 every instance status == ok", bool(r.get("all_status_ok")),
             f"{r.get('realized_instances')} instances")
        mark("G2 realized instance count == N", bool(r.get("g_instances")),
             f"{r.get('realized_instances')} vs N={r['ncores']}")
        mark("G3 realized LLC == N x 5 MiB", bool(r.get("g_llc")),
             f"{r.get('llc_bytes_realized')} B = {r.get('hnf_slices')} slices "
             f"x {r.get('l3_per_slice_realized')}")
        if not r["completed"]:
            voids.append(f"{tag}: {r['reason']}")
    if voids:
        print("\nVOID RUNS (reported, never silently dropped):")
        for v in voids:
            print("  " + v)

    live = [r for r in recs if r["completed"]]
    if len(live) != len(ARMS) * len(NCORES):
        print("\n===== VERDICT =====")
        print("INCOMPLETE: not all six arms certified; no ordering claim licensed.")
        return 1

    # ---------------- arm identity and engagement (S5.1) ----------------
    # `bypasses > 0` is not an engagement test.  A `stream` arm has to suppress
    # a material share of its WB peer's LLC fills and veto a material share of
    # the fill decisions the HNF actually presented to it; a `wb` arm has to
    # bypass exactly none.
    print("\nARM IDENTITY AND POLICY ENGAGEMENT, FROM EACH RUN'S OWN ARTIFACTS (S5.1)")
    wb_by_n = {r["ncores"]: r for r in live if r["arm"] == "wb"}
    ident_ok = True
    for r in live:
        want = ARM_POLICY[r["arm"]]
        pf_expect = (r["arm"] != "pfoff")
        peer = wb_by_n.get(r["ncores"])
        r["wb_peer"] = peer["run"] if peer and peer is not r else None
        r["fill_suppression_vs_wb"] = (
            1.0 - r["hnf_fills"] / peer["hnf_fills"]
            if peer is not None and peer is not r and peer["hnf_fills"] else None)
        e, s = r["hnf_bypass_per_decision"], r["fill_suppression_vs_wb"]
        if want == "wb":
            engaged = r["hnf_streaming_bypasses"] == 0
        else:
            engaged = (e is not None and e >= A1_MIN_BYPASS_PER_DECISION
                       and (s is None or s >= A1_MIN_FILL_SUPPRESSION))
        r["a1_engaged"] = engaged
        ok = (r["realized_policy"] == want
              and (r["prefetcher_sections"] > 0) == pf_expect
              and engaged)
        ident_ok &= ok
        print(f"  {r['arm']}_{r['ncores']}c  policy={r['realized_policy']} (want {want})  "
              f"prefetcher_sections={r['prefetcher_sections']}  "
              f"hnf_bypasses={r['hnf_streaming_bypasses']:.0f}  "
              f"of {r['hnf_write_decisions']:.0f} fill decisions "
              f"({'n/a' if e is None else f'{e*100:.1f}%'})  "
              f"fill suppression {'n/a' if s is None else f'{s*100:.1f}%'}  "
              f"{'ok' if ok else 'MISMATCH'}")
    mark("A1 realized arm matches its label AND its policy engaged", ident_ok,
         f"policy + prefetchers + bypass/decision >= {A1_MIN_BYPASS_PER_DECISION} "
         f"+ fill suppression >= {A1_MIN_FILL_SUPPRESSION}")
    if not ident_ok:
        print("  !! A LABELLED POLICY DID NOT ENGAGE.  A `stream` cell that does not")
        print("  !! suppress fills measured the writeback policy with an inert")
        print("  !! STREAMING tag; its bandwidth is not an H2 number.  The verdict")
        print("  !! below is withheld (main() returns non-zero).")

    # ---------------- realized configuration ----------------
    print("\nREALIZED CONFIGURATION (read back from config.ini, not requested)")
    print(f"  {'run':>10s} {'slices':>7s} {'LLC':>10s} {'assoc':>6s} {'CXL lat':>9s} "
          f"{'mem type':>13s} {'mem ceiling':>12s}")
    for r in live:
        print(f"  {r['arm']+'_'+str(r['ncores'])+'c':>10s} {r['hnf_slices']:>7d} "
              f"{r['llc_bytes_realized']/2**20:>7.0f} MiB {r['l3_assoc_realized'][0]:>6d} "
              f"{r['cxl_latency_ns_realized']:>7.0f} ns {r['mem_type_realized']:>13s} "
              f"{r['cxl_bw_ceiling_gbps']:>9.0f} GB/s")

    # ---------------- primary result ----------------
    print("\nAGGREGATE BANDWIDTH")
    print(f"  {'run':>10s} {'agg_bw_sum':>11s} {'per core':>9s} {'spread':>7s} "
          f"{'agg_bw_wall':>12s} {'wall/sum':>9s} {'wall h':>7s}")
    for r in live:
        print(f"  {r['arm']+'_'+str(r['ncores'])+'c':>10s} {r['agg_bw_sum']:>8.2f} GB/s "
              f"{r['bw_per_core']:>6.2f} GB/s {r['bw_spread_pct']:>6.2f}% "
              f"{r['agg_bw_wall']:>9.2f} GB/s {r['agg_bw_wall_over_sum']:>8.4f} "
              f"{(r['wall_hours'] or 0):>7.2f}")

    print("\nSCALING 4c -> 8c (agg_bw_sum, and per-core retention)")
    for arm in ARMS:
        a, b = by[(arm, 4)], by[(arm, 8)]
        print(f"  {arm:>6s}  {a['agg_bw_sum']:6.2f} -> {b['agg_bw_sum']:6.2f} GB/s  "
              f"= {b['agg_bw_sum']/a['agg_bw_sum']:.3f}x (ideal 2.000)   per-core "
              f"{a['bw_per_core']:.2f} -> {b['bw_per_core']:.2f} "
              f"({(b['bw_per_core']/a['bw_per_core']-1)*100:+.1f}%)")

    # ---------------- metric 2 is not usable ----------------
    print("\nMETRIC 2 (agg_bw_wall) -- CONFIRMED NON-COMPARABLE, DO NOT PUBLISH")
    for r in live:
        print(f"  {r['arm']+'_'+str(r['ncores'])+'c':>10s} simSeconds={r['simSeconds']:.6f} s "
              f"measured window={sum(r['measured_window_s'])/r['ncores']*1e3:.4f} ms "
              f"= {r['measured_window_frac_of_sim']*100:.2f}% of it -> "
              f"agg_bw_wall is {1/r['agg_bw_wall_over_sum']:.0f}x low")
    print("  simSeconds spans allocation, table build, fill_fact and the warm pass.")
    print("  Reconstructable substitute (bytes / widest instance window):")
    for r in live:
        print(f"    {r['arm']+'_'+str(r['ncores'])+'c':>10s} "
              f"{r['agg_bw_maxwindow']:6.2f} GB/s vs agg_bw_sum {r['agg_bw_sum']:6.2f} "
              f"({r['agg_bw_maxwindow']/r['agg_bw_sum']*100:.1f}%)")

    # ---------------- window alignment ----------------
    print("\nWINDOW ALIGNMENT (no cross-process barrier exists; this is a bound)")
    print(f"  {'run':>10s} {'min window':>11s} {'exit skew':>10s} {'skew/window':>12s} "
          f"{'overlap floor':>14s}")
    for r in live:
        print(f"  {r['arm']+'_'+str(r['ncores'])+'c':>10s} "
              f"{min(r['measured_window_s'])*1e3:>8.4f} ms {r['exit_skew_s']*1e3:>7.4f} ms "
              f"{r['exit_skew_pct_of_window']:>11.1f}% {r['window_overlap_floor']*100:>13.1f}%")
    floor = min(r["window_overlap_floor"] for r in live)
    print(f"  worst guaranteed pairwise overlap across all six runs: {floor*100:.1f}%")
    print("  Assumes run_stream()'s post-measurement tail (JSON emit + free) is a")
    print("  near-constant offset from program end, which the source supports.")

    # ---------------- LLC residency ----------------
    print("\nLLC RESIDENCY OF THE MEASURED PASS (the validity threat, quantified)")
    print(f"  {'run':>10s} {'HNF acc':>10s} {'HNF hit%':>9s} {'HNF fills':>10s} "
          f"{'bypasses':>10s} {'CXL read':>10s} {'/2-pass demand':>15s}")
    for r in live:
        print(f"  {r['arm']+'_'+str(r['ncores'])+'c':>10s} {r['hnf_accesses']:>10.0f} "
              f"{r['hnf_hit_frac']*100:>8.2f}% {r['hnf_fills']:>10.0f} "
              f"{r['hnf_streaming_bypasses']:>10.0f} "
              f"{r['cxl_bytes_read']/2**20:>7.1f} MiB {r['cxl_read_over_demand']:>14.3f}x")
    print("  cxl_read/demand >= 1.00 means the LLC supplied none of the stream, so")
    print("  the 1.6x working-set/LLC ratio did not leave the warm pass resident.")
    print("  pfoff has no prefetcher, so its ratio is the prefetch-free control.")

    # ---------------- MLP and the MSHR ceiling ----------------
    print("\nMSHR-IMPLIED CEILING AND REALIZED CONCURRENCY")
    ceil = L1_MSHR * LINE_BYTES / (CXL_LATENCY_NS * 1e-9) / 1e9
    print(f"  L1_MSHR={L1_MSHR} x {LINE_BYTES} B / {CXL_LATENCY_NS:.0f} ns "
          f"= {ceil:.2f} GB/s per core")
    print(f"  {'run':>10s} {'per core':>9s} {'of ceiling':>11s} {'HNF lat':>9s} "
          f"{'concurrency':>12s} {'of HNF TBE':>11s} {'of L1 MSHR':>11s} {'of SNF TBE':>11s}")
    for r in live:
        print(f"  {r['arm']+'_'+str(r['ncores'])+'c':>10s} {r['bw_per_core']:>6.2f} GB/s "
              f"{r['mshr_ceiling_frac']*100:>10.1f}% {r['hnf_read_latency_ns']:>6.1f} ns "
              f"{r['hnf_concurrency']:>9.1f} ln {r['hnf_tbe_occupancy_frac']*100:>10.1f}% "
              f"{r['l1_mshr_occupancy_frac']*100:>10.1f}% "
              f"{r['snf_tbe_occupancy_frac']*100:>10.1f}%")

    # ---------------- is anything shared actually saturated? ----------------
    print("\nSHARED-RESOURCE SATURATION (one SNF: --num-dirs=1)")
    print(f"  {'run':>10s} {'mem used':>9s} {'snf util':>9s} {'req2mem stall':>14s} "
          f"{'datOut stall':>13s} {'HNF imbalance':>14s}")
    for r in live:
        print(f"  {r['arm']+'_'+str(r['ncores'])+'c':>10s} "
              f"{r['mem_bw_used_frac']*100:>8.2f}% {r['snf_avg_util_wholerun']*100:>8.2f}% "
              f"{r['snf_req2mem_avg_stall_ticks']:>11.1f} tk "
              f"{r['snf_datout_avg_stall_ticks']:>10.2f} tk "
              f"{r['hnf_slice_imbalance']:>13.3f}x")
    print(f"  SimpleMemory imposes a {live[0]['cxl_bw_ceiling_gbps']:.0f} GB/s ceiling "
          "(bandwidth=2 ticks/byte) with latency_var=0:")
    print("  a fixed-latency device with no realistic link limit at these rates.")

    # ---------------- teardown defect ----------------
    print("\nTEARDOWN DEFECT (latent; after the JSON, before a clean exit)")
    for r in live:
        print(f"  {r['arm']+'_'+str(r['ncores'])+'c':>10s} "
              f"free(): invalid size x{r['free_invalid_size']}  "
              f"reached_exit={r['reached_exit']}  gem5_exit={r['gem5_exit']}")
    print("  Not deterministic across arms; cannot affect a reported number, but")
    print("  it is heap corruption in free_bytes() and warrants its own bug.")

    # ---------------- verdict ----------------
    print("\nPRE-REGISTERED ORDERING  h2 >= wb > pfoff")
    holds = {}
    for n in NCORES:
        h2, wb, pf = (by[(a, n)]["agg_bw_sum"] for a in ("h2", "wb", "pfoff"))
        holds[n] = (h2 >= wb) and (wb > pf)
        mark(f"ordering at {n}c", holds[n],
             f"h2 {h2:.2f} >= wb {wb:.2f} > pfoff {pf:.2f}  "
             f"(h2/wb {h2/wb:.4f}, wb/pfoff {wb/pf:.4f})")

    print("\n===== VERDICT =====")
    if all(holds.values()):
        verdict = "PASS"
        print("PASS: ordering h2 >= wb > pfoff holds at BOTH 4c and 8c.")
    elif any(holds.values()):
        verdict = "PARTIAL"
        print("PARTIAL: ordering holds at one core count only "
              f"({[n for n in NCORES if holds[n]]}).")
    else:
        verdict = "NULL"
        print("NULL: ordering does not hold. Publishable; the paper sentence comes out.")
    print("Supersedes preserved/gem5_streaming.tar.gz as the citable source for")
    print("both core counts. The archive's harness is unrecoverable, so the")
    print("magnitude difference cannot be attributed to archive vs harness.")
    print("agg_bw_wall is NOT published; see METRIC 2 above.")

    # data/gem5/*.jsonl convention: one record per line, run/completed/reason first.
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    lead = ("run", "completed", "reason")
    with OUT_JSONL.open("w") as f:
        for r in recs:
            r.pop("outdir", None)
            ordered = {k: r[k] for k in lead if k in r}
            ordered.update({k: v for k, v in r.items() if k not in lead})
            f.write(json.dumps(ordered) + "\n")
    print(f"\nwrote {len(recs)} records to {OUT_JSONL}")
    return 0 if verdict == "PASS" and ident_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
