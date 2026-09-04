#!/usr/bin/env python3
"""H1 bandwidth bracket campaigns -- analyzer.

Sibling of `analyze_h1bw_multicore.py`, which is left untouched so it keeps
working on the completed `h1bw_mc_*_20260904` runs.  This one handles the two
bracket campaigns, which vary parameters that analyzer hard-codes:

  cxlbw   H1BW_CXLBW_PREREG_2026-09-03.md
          CXL range capped at a realistic link bandwidth; 2 caps x 3 arms x
          {4, 8} cores.
  slice   H1BW_SLICE_BRACKET_PREREG_2026-09-03.md
          --num-l3caches=1 instead of =N; 3 arms at 4 cores.

Usage: analyze_h1bw_bracket.py {cxlbw|slice} [campaign-date]

Five pre-registered gates, all fail-closed.  A run that fails any of them is
printed as VOID and contributes no number to the verdict:

  G1  every instance reports status == "ok"                    (carried forward)
  G2  realized instance count == N                             (carried forward)
  G3  realized LLC == declared_slices x 5 MiB                   (generalised
      from `N x 5 MiB`, and the realized slice count must equal the declared
      bracket, so an accidental slice change still voids)
  G4  realized system.mem_ctrls1.bandwidth == the pre-registered integer
      ticks/byte for this cell                                 (new)
  G5  the arm's declared policy measurably engaged: a `stream` arm must
      suppress at least A1_MIN_FILL_SUPPRESSION of its WB peer's HNF fills and
      bypass at least A1_MIN_BYPASS_PER_DECISION of the fill decisions the HNF
      presented; a `wb` arm must bypass exactly none    (added 2026-09-03, see
      H2_BYPASS_COLLAPSE_2026-09-03.md)

G4 is the point of the cxlbw campaign.  `bandwidth` in config.ini is TICKS PER
BYTE, and MemoryBandwidth.getValue() quantises it to an INTEGER tick via
m5.ticks.fromSeconds (ROUND_HALF_UP).  That quantisation is why the 512GiB/s
SimObject default (1.819 ticks/byte) is realized as exactly 2.000000, i.e.
500 GB/s -- and fromSeconds only warns when it rounds *down*, so rounding up
is silent.  Requesting a bandwidth and reporting it without reading the
realized integer back is the defect class this campaign exists to catch, so
the gate compares against the realized value and nothing else.

Everything is a module constant, not an argument, so changing a threshold
after seeing data is visible in git (the W1 rule).
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path

LOGROOT = "/home/domin/DutyFree/gem5/logs/se_chi"
DATADIR = Path("/home/domin/DutyFree/experiments/asplos/data/gem5")

# --- frozen configuration, inherited unchanged from the superseded campaign
ARMS = ("wb", "h2", "pfoff")
ARM_POLICY = {"wb": "wb", "h2": "stream", "pfoff": "stream"}
L3_PER_SLICE = 5 * 1024 * 1024          # 5 MiB / 20-way per HNF slice
PER_CORE_BYTES = 8 * 1024 * 1024        # 8 MiB per instance
PASSES = 2                              # --warmups 1 --reps 1
L1_MSHR = 48
HNF_TBE_PER_SLICE = 32                  # CHI_config_8592.py:435, HNF_MSHR unset
SNF_TBE = 256                           # CHI_config_8592.py:961, SNF_MSHR unset
CXL_LATENCY_NS = 203.0
LINE_BYTES = 64
CPU_HZ = 1.9e9
RUBY_TICKS_PER_CY = 500                 # system.ruby.clk_domain.clock -> 2 GHz
TICKS_PER_S = 1e12                      # stats.txt simFreq
BW_TICKS_DEFAULT = 2                    # unset CXL_MEM_BW -> 2 ticks/byte

# --- the superseded campaign, as the comparison baseline.
# H1BW_MULTICORE_OUTCOME_2026-09-03.md, "Results".  agg_bw_sum, GB/s.
BASELINE = {
    ("wb", 4): 20.0866, ("h2", 4): 25.1083, ("pfoff", 4): 13.2741,
    ("wb", 8): 30.9972, ("h2", 8): 43.1402, ("pfoff", 8): 26.9832,
}


def gbps(ticks_per_byte):
    return TICKS_PER_S / ticks_per_byte / 1e9


CAMPAIGNS = {
    # (ncores, slices, bw_ticks) cells; every arm is run in every cell.
    "cxlbw": {
        "prereg": "H1BW_CXLBW_PREREG_2026-09-03.md",
        "jsonl": DATADIR / "h1bw_cxlbw.jsonl",
        "cells": [(n, n, t) for t in (31, 16) for n in (4, 8)],
        "title": "H1BW CXL-BANDWIDTH BRACKET",
    },
    "slice": {
        "prereg": "H1BW_SLICE_BRACKET_PREREG_2026-09-03.md",
        "jsonl": DATADIR / "h1bw_slice_bracket.jsonl",
        "cells": [(4, 1, BW_TICKS_DEFAULT)],
        "title": "H1BW LLC-SLICE BRACKET",
    },
}

# --- pre-declared predictions (see each pre-registration's outcome table).
# Checked mechanically below so the result can confirm or refute them rather
# than being narrated after the fact.  Each entry is a closed band on
# agg_bw_sum / uncapped-baseline agg_bw_sum, with a one-word label.
CXLBW_PREDICTION = {
    # 32.26 GB/s cap.  Sits above every 4-core baseline (20.09/25.11/13.27)
    # and below h2_8c (43.14) while sitting just 4% above wb_8c (31.00).
    (4, 31): {"wb": ("unchanged", 0.95, 1.05),
              "h2": ("unchanged", 0.95, 1.05),
              "pfoff": ("unchanged", 0.95, 1.05)},
    (8, 31): {"wb": ("clipped mildly", 0.75, 1.00),
              "h2": ("clipped hard", 0.55, 0.85),
              "pfoff": ("unchanged", 0.95, 1.05)},
    # 62.5 GB/s cap.  Above every baseline; h2_8c is the only one that gets
    # within 70% of it, and WB is the arm whose controller traffic most
    # exceeds its useful rate.
    (4, 16): {"wb": ("unchanged", 0.95, 1.05),
              "h2": ("unchanged", 0.95, 1.05),
              "pfoff": ("unchanged", 0.95, 1.05)},
    (8, 16): {"wb": ("unchanged", 0.90, 1.05),
              "h2": ("unchanged", 0.85, 1.05),
              "pfoff": ("unchanged", 0.95, 1.05)},
}
# The alarming outcome: the H2-over-WB advantage shrinks or inverts once the
# interconnect is realistically constrained.
ALARM_SHRINK_FRAC = 0.95     # capped h2/wb < 0.95 x baseline h2/wb -> shrunk

# --- G5: did the labelled policy actually ENGAGE?
# The predecessor of this gate lived in the A1 identity block and tested only
# `bypasses > 0`.  That is satisfied by a cell in which the streaming policy has
# almost entirely disengaged: `h2_4c_l3x1` reported 17,197 bypasses -- 24.5x
# below its four-slice sibling, and 1.1% of its own fill opportunities -- and was
# certified without comment.  Two independent measures, both fail-closed:
#
#   fill suppression   1 - arm_fills / wb_fills, WB arm of the SAME cell.
#                      Observed 44.5-59.0% in every engaged cell across three
#                      campaigns; 1.2% in the collapsed cell.
#   bypass/decision    bypasses / write-request allocation decisions at the HNF
#                      (see hnf_write_decisions).  Self-contained: needs no WB
#                      partner, so a campaign without one is still checked.
#                      Observed 37.5-48.6% engaged; 1.1% collapsed.
#
# Both thresholds sit at 0.20 -- under half the smallest engaged observation and
# an order of magnitude above the collapsed one -- so the gate is insensitive to
# where in that gap it is placed.  See H2_BYPASS_COLLAPSE_2026-09-03.md.
A1_MIN_FILL_SUPPRESSION = 0.20
A1_MIN_BYPASS_PER_DECISION = 0.20
# slice campaign: bands on agg_bw_sum in GB/s, not on the baseline ratio,
# because the mechanism (a 32-buffer HNF pool against a measured occupancy
# near 60) predicts an absolute ceiling rather than a fractional loss.
SLICE_PREDICTION = {"wb": (6.0, 11.0), "h2": (6.0, 11.0), "pfoff": (10.0, 15.0)}

HNF_RE = re.compile(r"^system\.ruby\.hnf(\d*)\.cntrl\.cache$")


def mark(name, ok, detail):
    print(f"  {name:52s} {'PASS' if ok else 'FAIL'}  {detail}")
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
    """Realized HNF geometry -> {stats_prefix: (size, assoc)}.

    gem5 collapses a length-1 SimObjectVector to an unindexed name, so at
    --num-l3caches=1 the section is `system.ruby.hnf`, not `system.ruby.hnf0`.
    The superseded analyzer's `hnf(\\d+)` regex matches zero sections there and
    reports a 0-byte LLC, which would void the slice bracket for the wrong
    reason.  Match both spellings and hand back the prefix so the stats reader
    uses the same one.
    """
    out = {}
    for name, body in ini.items():
        m = HNF_RE.match(name)
        if m:
            prefix = name[: -len(".cache")]      # system.ruby.hnf[i].cntrl
            out[prefix] = (int(body["size"]), int(body["assoc"]))
    return out


def mem_ticks_per_byte(ini, section):
    """SimpleMemory.bandwidth is TICKS PER BYTE, quantised to an integer."""
    return float(ini[section]["bandwidth"])


def hnf_read_latency_ns(stats, prefixes):
    """Sample-weighted HNF in-transaction latency = TBE occupancy per request."""
    num = den = 0.0
    for p in prefixes:
        for t in ("ReadShared", "ReadUnique_PoC"):
            b = f"{p}.inTransLatHist.{t}"
            n = stats.get(b + "::samples", 0.0)
            m = stats.get(b + "::mean", 0.0)
            num += n * m
            den += n
    if not den:
        return None
    return (num / den) * RUBY_TICKS_PER_CY / TICKS_PER_S * 1e9


def analyze(outdir, arm, n, slices, bw_ticks):
    r = {
        "run": os.path.basename(outdir),
        "outdir": outdir,
        "arm": arm,
        "ncores": n,
        "declared_slices": slices,
        "declared_bw_ticks_per_byte": bw_ticks,
        "declared_bw_gbps": round(gbps(bw_ticks), 4),
    }
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
    r["free_invalid_size"] = log.count("free(): invalid size")
    r["reached_exit"] = "Exiting @ tick" in log
    # Requested values, kept only so requested-vs-realized can be shown side by
    # side.  Nothing below gates on them.
    r["requested_cxl_mem_bw"] = manifest.get("cxl_mem_bw_requested")
    r["requested_num_l3caches"] = manifest.get("num_l3caches")
    r["requested_bw_ticks"] = manifest.get("cxl_bw_ticks_per_byte_expected")

    # ---- realized identity, from the artifact (S5.1)
    cmds = re.findall(r"^cmd=(.*)$", Path(outdir, "config.ini").read_text(errors="replace"), re.M)
    pols = {m.group(1) for c in cmds for m in [re.search(r"--policy (\S+)", c)] if m}
    r["realized_policy"] = sorted(pols)[0] if len(pols) == 1 else f"MIXED:{sorted(pols)}"
    r["realized_instances"] = len(inst)
    r["realized_workloads"] = len(cmds)
    r["prefetcher_sections"] = sum(1 for s in ini if "prefetcher" in s.lower())

    # ---- realized geometry, from the artifact (F9)
    sl = hnf_slices(ini)
    prefixes = sorted(sl)
    r["hnf_slices"] = len(sl)
    r["llc_bytes_realized"] = sum(s for s, _ in sl.values())
    r["l3_per_slice_realized"] = sorted({s for s, _ in sl.values()})
    r["l3_assoc_realized"] = sorted({a for _, a in sl.values()})
    r["cxl_latency_ns_realized"] = float(ini["system.mem_ctrls1"]["latency"]) / 1000.0
    r["dram_latency_ns_realized"] = float(ini["system.mem_ctrls0"]["latency"]) / 1000.0
    r["cxl_latency_var_realized"] = float(ini["system.mem_ctrls1"]["latency_var"])
    r["mem_type_realized"] = ini["system.mem_ctrls1"]["type"]
    r["cxl_bw_ticks_per_byte_realized"] = mem_ticks_per_byte(ini, "system.mem_ctrls1")
    r["dram_bw_ticks_per_byte_realized"] = mem_ticks_per_byte(ini, "system.mem_ctrls0")
    r["cxl_bw_ceiling_gbps"] = round(gbps(r["cxl_bw_ticks_per_byte_realized"]), 4)
    r["dram_bw_ceiling_gbps"] = round(gbps(r["dram_bw_ticks_per_byte_realized"]), 4)

    # ---- pre-registered gates.  Fail-closed: void, do not report.
    statuses = [x.get("status") for x in inst]
    r["g1_status_ok"] = bool(inst) and all(s == "ok" for s in statuses)
    r["g2_instances"] = r["realized_instances"] == n
    r["g3_llc"] = (r["hnf_slices"] == slices
                   and r["llc_bytes_realized"] == slices * L3_PER_SLICE)
    # G4 compares the realized integer, never the request.
    r["g4_cxl_bw"] = r["cxl_bw_ticks_per_byte_realized"] == float(bw_ticks)
    r["completed"] = bool(r["g1_status_ok"] and r["g2_instances"]
                          and r["g3_llc"] and r["g4_cxl_bw"])
    if not r["completed"]:
        r["reason"] = "; ".join(
            x for x in (
                None if r["g1_status_ok"] else f"status={statuses}",
                None if r["g2_instances"] else f"instances={r['realized_instances']}!={n}",
                None if r["g3_llc"] else
                f"llc={r['llc_bytes_realized']} B over {r['hnf_slices']} slices "
                f"!= {slices}x{L3_PER_SLICE}",
                None if r["g4_cxl_bw"] else
                f"cxl bandwidth={r['cxl_bw_ticks_per_byte_realized']} ticks/byte "
                f"!= requested {bw_ticks} -- VOID, not reported as requested",
            ) if x)
        return r
    r["reason"] = "ok"

    # ---- metric 1: agg_bw_sum.  agg_bw_wall is retired (superseded campaign's
    # outcome doc, "agg_bw_wall is unusable"); the reconstructable substitute
    # is bytes over the widest single instance window.
    bws = sorted((x["bandwidth_gbps"] for x in inst), reverse=True)
    secs = [x["seconds"] for x in inst]
    r["per_instance_bw_gbps"] = bws
    r["agg_bw_sum"] = sum(bws)
    r["bw_per_core"] = r["agg_bw_sum"] / n
    r["bw_spread_pct"] = (max(bws) - min(bws)) / (sum(bws) / n) * 100.0
    r["reps_per_instance"] = len(inst[0].get("samples", []))
    total_bytes = n * PER_CORE_BYTES
    r["total_bytes"] = total_bytes
    r["simSeconds"] = stats["simSeconds"]
    r["agg_bw_maxwindow"] = total_bytes / max(secs) / 1e9

    # ---- window alignment.  No barrier exists, so bound the skew instead.
    cycles = [stats[f"system.cpu{i}.numCycles"] for i in range(n)]
    skew_s = (max(cycles) - min(cycles)) / CPU_HZ
    r["measured_window_s"] = [round(s, 9) for s in sorted(secs)]
    r["exit_skew_s"] = skew_s
    r["window_overlap_floor"] = max(0.0, (min(secs) - skew_s) / min(secs))

    # ---- LLC residency and home-node behaviour
    acc = hit = fills = byp = 0.0
    per_slice = []
    for p in prefixes:
        b = f"{p}.cache."
        a = stats.get(b + "m_demand_accesses", 0.0) + stats.get(b + "m_prefetch_accesses", 0.0)
        h = stats.get(b + "m_demand_hits", 0.0) + stats.get(b + "m_prefetch_hits", 0.0)
        acc += a
        hit += h
        per_slice.append(a)
        fills += stats.get(b + "numDataArrayWrites", 0.0)
        byp += stats.get(b + "streamingHnfFillBypasses", 0.0)
    r["hnf_accesses"] = acc
    r["hnf_hit_frac"] = hit / acc if acc else None
    r["hnf_fills"] = fills
    r["hnf_streaming_bypasses"] = byp
    r["hnf_slice_imbalance"] = max(per_slice) / min(per_slice) if min(per_slice) else None

    # ---- the population in which a bypass is even possible.  This HNF is a
    # non-inclusive victim cache (alloc_on_read* all False), so a read never
    # presents a fill opportunity; only WriteEvictFull/WriteBackFull do, and only
    # when they find the LLC data entry invalid -- dir state RU.  Counting the
    # RU->{I,UC,UD} transitions therefore gives the exact denominator for
    # engagement, and RU->I is the numerator that CacheMemory increments.
    dec = 0.0
    for p in prefixes:
        for t in ("WriteEvictFull", "WriteBackFull"):
            for final in ("I", "UC", "UD"):
                dec += stats.get(f"{p}.inTransLatHist.{t}.RU.{final}.total", 0.0)
    r["hnf_write_decisions"] = dec
    r["hnf_bypass_per_decision"] = byp / dec if dec else None
    # Retried requests reach the HNF with isStreaming reset to its field default,
    # so the retry rate bounds how much of the policy can survive the fabric.
    r["hnf_write_retries"] = sum(
        stats.get(f"{p}.inTransLatHist.{t}.retries", 0.0)
        for p in prefixes for t in ("WriteEvictFull", "WriteBackFull"))
    r["hnf_write_arrivals"] = sum(
        stats.get(f"{p}.inTransLatHist.{t}::samples", 0.0)
        for p in prefixes for t in ("WriteEvictFull", "WriteBackFull"))
    r["hnf_write_retry_frac"] = (r["hnf_write_retries"] / r["hnf_write_arrivals"]
                                 if r["hnf_write_arrivals"] else None)
    r["cxl_bytes_read"] = stats.get("system.mem_ctrls1.bytesRead::total", 0.0)
    r["cxl_bytes_written"] = stats.get("system.mem_ctrls1.bytesWritten::total", 0.0)
    r["dram_bytes_read"] = stats.get("system.mem_ctrls0.bytesRead::total", 0.0)
    r["twopass_demand_bytes"] = total_bytes * PASSES
    r["cxl_read_over_demand"] = r["cxl_bytes_read"] / r["twopass_demand_bytes"]

    # ---- concurrency, and what fraction of each budget it occupies
    lat_ns = hnf_read_latency_ns(stats, prefixes)
    lines_per_s = r["agg_bw_sum"] * 1e9 / LINE_BYTES
    r["hnf_read_latency_ns"] = lat_ns
    r["hnf_concurrency"] = lines_per_s * lat_ns * 1e-9 if lat_ns else None
    r["hnf_tbe_budget"] = HNF_TBE_PER_SLICE * len(sl)
    r["hnf_tbe_occupancy_frac"] = (r["hnf_concurrency"] / r["hnf_tbe_budget"]
                                   if r["hnf_concurrency"] else None)
    r["l1_mshr_budget"] = L1_MSHR * n
    r["l1_mshr_occupancy_frac"] = (r["hnf_concurrency"] / r["l1_mshr_budget"]
                                   if r["hnf_concurrency"] else None)
    r["snf_concurrency"] = lines_per_s * CXL_LATENCY_NS * 1e-9
    r["snf_tbe_occupancy_frac"] = r["snf_concurrency"] / SNF_TBE
    r["snf_avg_util_wholerun"] = stats.get("system.ruby.snf.cntrl.avg_util")
    r["snf_req2mem_avg_stall_ticks"] = stats.get(
        "system.ruby.snf.cntrl.requestToMemory.m_avg_stall_time", 0.0)
    r["snf_datout_avg_stall_ticks"] = stats.get(
        "system.ruby.snf.cntrl.datOut.m_avg_stall_time", 0.0)

    # ---- the quantity this bracket exists to move: how much of the realized
    # CXL ceiling the run actually consumed.  In the superseded campaign this
    # was 2.65-8.63%; a cap that binds must push it toward 100%.
    r["cxl_bw_used_frac"] = r["agg_bw_sum"] / r["cxl_bw_ceiling_gbps"]
    r["baseline_agg_bw_sum"] = BASELINE.get((arm, n))
    if r["baseline_agg_bw_sum"]:
        r["vs_baseline"] = r["agg_bw_sum"] / r["baseline_agg_bw_sum"]

    r["simInsts"] = stats.get("simInsts")
    return r


def apply_engagement_gate(recs):
    """G5, applied across runs: did each arm's declared policy actually engage?

    Cross-run, so it cannot live inside analyze(): the fill-suppression measure
    is relative to the WB arm of the same cell.  A cell that fails is voided in
    place, exactly like a G1-G4 failure, so it contributes no number to the
    verdict.  A streaming cell that did not engage is not a weaker H2 result --
    it is a WB result wearing an H2 label, and reporting its bandwidth as H2
    would be a category error, not a conservative estimate.
    """
    wb = {}
    for r in recs:
        if r["arm"] == "wb" and r.get("completed") and r.get("hnf_fills"):
            wb[(r["ncores"], r["declared_slices"],
                r["declared_bw_ticks_per_byte"])] = r

    for r in recs:
        r["g5_engaged"] = None
        r["fill_suppression_vs_wb"] = None
        r["wb_peer"] = None
        if not r.get("completed"):
            continue                     # already void on geometry/status
        peer = wb.get((r["ncores"], r["declared_slices"],
                       r["declared_bw_ticks_per_byte"]))
        if peer is not None and peer["run"] != r["run"]:
            r["wb_peer"] = peer["run"]
            r["fill_suppression_vs_wb"] = 1.0 - r["hnf_fills"] / peer["hnf_fills"]

        if ARM_POLICY[r["arm"]] == "wb":
            # A writeback arm must never bypass.  Exact, not a threshold: a
            # single bypass here would mean a STREAMING tag leaked into the
            # control arm.
            r["g5_engaged"] = r["hnf_streaming_bypasses"] == 0
            r["g5_detail"] = f"{r['hnf_streaming_bypasses']:.0f} bypasses (must be 0)"
            if not r["g5_engaged"]:
                r["completed"] = False
                r["reason"] = (f"wb arm recorded {r['hnf_streaming_bypasses']:.0f} "
                               f"streaming bypasses -- STREAMING leaked into the "
                               f"control arm; VOID")
            continue

        e = r["hnf_bypass_per_decision"]
        s = r["fill_suppression_vs_wb"]
        fails = []
        if e is None:
            fails.append("no HNF write allocation decisions found in stats.txt")
        elif e < A1_MIN_BYPASS_PER_DECISION:
            fails.append(f"bypass/decision {e:.3f} < {A1_MIN_BYPASS_PER_DECISION}")
        if s is None:
            # Judged on the self-contained measure alone, and said so.
            r["g5_no_wb_peer"] = True
        elif s < A1_MIN_FILL_SUPPRESSION:
            fails.append(f"fill suppression vs {peer['run']} {s:.3f} "
                         f"< {A1_MIN_FILL_SUPPRESSION}")
        r["g5_engaged"] = not fails
        r["g5_detail"] = (
            f"bypass/decision {e if e is None else round(e, 3)}, "
            f"fill suppression {s if s is None else round(s, 3)}, "
            f"HNF write retry frac "
            f"{r['hnf_write_retry_frac'] if r['hnf_write_retry_frac'] is None else round(r['hnf_write_retry_frac'], 3)}")
        if fails:
            r["completed"] = False
            r["reason"] = ("policy=stream DID NOT ENGAGE: " + "; ".join(fails)
                           + " -- VOID, this cell measured the writeback policy "
                             "with an inert STREAMING tag and is not an H2 number")


def wall_hours(rec):
    from datetime import datetime
    try:
        a = datetime.fromisoformat(rec["started"])
        b = datetime.fromisoformat(rec["ended"])
        return (b - a).total_seconds() / 3600.0
    except Exception:
        return None


def outdir_for(arm, n, slices, bw_ticks, stamp):
    tag = "def" if bw_ticks == BW_TICKS_DEFAULT else f"t{bw_ticks}"
    return f"{LOGROOT}/h1bw_mc_{arm}_{n}c_l3x{slices}_bw{tag}_{stamp}"


def main(argv):
    if len(argv) < 2 or argv[1] not in CAMPAIGNS:
        print(f"usage: {argv[0]} {{{'|'.join(CAMPAIGNS)}}} [campaign-date]")
        return 2
    name = argv[1]
    camp = CAMPAIGNS[name]
    stamp = argv[2] if len(argv) > 2 else "*"

    recs, voids = [], []
    for (n, slices, bw_ticks) in camp["cells"]:
        for arm in ARMS:
            pat = outdir_for(arm, n, slices, bw_ticks, stamp)
            hits = sorted(glob.glob(pat))
            if not hits:
                voids.append(f"{os.path.basename(pat)}: no outdir")
                continue
            rec = analyze(hits[-1], arm, n, slices, bw_ticks)
            rec["wall_hours"] = wall_hours(rec)
            recs.append(rec)

    # G5 is cross-run (it needs each cell's WB arm), so it runs once here and
    # voids in place before anything is printed or reported.
    apply_engagement_gate(recs)

    print("=" * 86)
    print(f"{camp['title']} -- prereg {camp['prereg']}  (stamp {stamp})")
    print("=" * 86)

    # ---------------- gates ----------------
    print("\nPRE-REGISTERED GATES (fail-closed: a failing run is VOID, not reported)")
    for r in recs:
        print(f"  {r['run']}")
        mark("G1 every instance status == ok", bool(r.get("g1_status_ok")),
             f"{r.get('realized_instances')} instances")
        mark("G2 realized instance count == N", bool(r.get("g2_instances")),
             f"{r.get('realized_instances')} vs N={r['ncores']}")
        mark("G3 realized LLC == slices x 5 MiB", bool(r.get("g3_llc")),
             f"{r.get('hnf_slices')} slices x {r.get('l3_per_slice_realized')} "
             f"= {r.get('llc_bytes_realized')} B (declared {r['declared_slices']} slices)")
        mark("G4 realized CXL bandwidth == request", bool(r.get("g4_cxl_bw")),
             f"config.ini {r.get('cxl_bw_ticks_per_byte_realized')} ticks/byte "
             f"vs declared {r['declared_bw_ticks_per_byte']} "
             f"({r['declared_bw_gbps']:.4f} GB/s)")
        if r.get("g5_engaged") is None:
            print(f"  {'G5 declared policy engaged':52s} n/a   "
                  f"not evaluated (already void on G1-G4)")
        else:
            mark("G5 declared policy engaged", bool(r["g5_engaged"]),
                 r.get("g5_detail", ""))
        if not r["completed"]:
            voids.append(f"{r['run']}: {r['reason']}")
    if voids:
        print("\nVOID RUNS (reported, never silently dropped):")
        for v in voids:
            print("  " + v)

    live = [r for r in recs if r["completed"]]
    expected = len(camp["cells"]) * len(ARMS)
    by = {(r["arm"], r["ncores"], r["declared_bw_ticks_per_byte"]): r for r in live}

    # ---------------- realized configuration ----------------
    if live:
        print("\nREALIZED CONFIGURATION (read back from config.ini, never requested)")
        print(f"  {'run':>34s} {'slices':>7s} {'LLC':>9s} {'CXL lat':>8s} "
              f"{'CXL tk/B':>9s} {'CXL ceiling':>12s} {'DRAM ceiling':>13s}")
        for r in live:
            print(f"  {r['run'][:34]:>34s} {r['hnf_slices']:>7d} "
                  f"{r['llc_bytes_realized']/2**20:>6.0f} MiB "
                  f"{r['cxl_latency_ns_realized']:>5.0f} ns "
                  f"{r['cxl_bw_ticks_per_byte_realized']:>9.3f} "
                  f"{r['cxl_bw_ceiling_gbps']:>9.2f} GB/s "
                  f"{r['dram_bw_ceiling_gbps']:>10.2f} GB/s")
        print("  DRAM ceiling is deliberately left at the 500 GB/s default: a")
        print("  multi-channel server socket, not the device under test.")

        print("\nARM IDENTITY AND POLICY ENGAGEMENT (S5.1)")
        print("  config.ini supplies the label; the HNF transition counters "
              "supply whether the")
        print("  label did anything.  'engaged' is bypasses over the write "
              "allocation decisions")
        print("  the HNF actually presented, not merely bypasses > 0.")
        print(f"  {'run':>40s} {'policy':>7s} {'pf':>4s} {'bypasses':>10s} "
              f"{'decisions':>10s} {'engaged':>8s} {'suppr':>7s} {'wr retry':>9s} {'':>9s}")
        ident_ok = True
        for r in recs:
            if "realized_policy" not in r:
                # Never got as far as config.ini (run absent or still in
                # flight).  Already void; nothing to check identity against.
                print(f"  {r['run'][:40]:>40s} "
                      f"{'not analyzed -- ' + str(r.get('reason', '')):>72s}")
                continue
            want = ARM_POLICY[r["arm"]]
            pf_expect = (r["arm"] != "pfoff")
            ok = (r["realized_policy"] == want
                  and (r["prefetcher_sections"] > 0) == pf_expect
                  and bool(r.get("g5_engaged")))
            ident_ok &= ok
            e, s = r.get("hnf_bypass_per_decision"), r.get("fill_suppression_vs_wb")
            q = r.get("hnf_write_retry_frac")
            print(f"  {r['run'][:40]:>40s} {str(r.get('realized_policy'))[:7]:>7s} "
                  f"{r.get('prefetcher_sections', -1):>4d} "
                  f"{r.get('hnf_streaming_bypasses', float('nan')):>10.0f} "
                  f"{r.get('hnf_write_decisions', float('nan')):>10.0f} "
                  f"{('n/a' if e is None else f'{e*100:.1f}%'):>8s} "
                  f"{('n/a' if s is None else f'{s*100:.1f}%'):>7s} "
                  f"{('n/a' if q is None else f'{q*100:.1f}%'):>9s} "
                  f"{'ok' if ok else 'MISMATCH':>9s}")
        mark("A1 realized arm matches its label AND its policy engaged", ident_ok,
             "policy + prefetcher instantiation + fill-suppression engagement")
        dis = [r for r in recs if r.get("g5_engaged") is False
               and ARM_POLICY[r["arm"]] == "stream"]
        if dis:
            print()
            print("  " + "!" * 74)
            print("  !! STREAMING POLICY DID NOT ENGAGE -- these cells are VOID")
            for r in dis:
                print(f"  !!   {r['run']}")
                print(f"  !!     bypasses {r['hnf_streaming_bypasses']:.0f} over "
                      f"{r['hnf_write_decisions']:.0f} HNF write allocation "
                      f"decisions "
                      f"({(r['hnf_bypass_per_decision'] or 0)*100:.1f}%)")
                if r.get("fill_suppression_vs_wb") is not None:
                    print(f"  !!     HNF fills {r['hnf_fills']:.0f} vs WB peer "
                          f"{r['wb_peer']} -- suppression "
                          f"{r['fill_suppression_vs_wb']*100:.1f}%")
                print(f"  !!     HNF write-request retry fraction "
                      f"{(r['hnf_write_retry_frac'] or 0)*100:.1f}% "
                      f"-- a retried CHI request arrives with isStreaming reset")
                print(f"  !!     to its field default, so the fabric, not the "
                      f"policy, decided this cell.")
            print("  !! This cell measured the WRITEBACK policy with an inert "
                  "STREAMING tag.")
            print("  !! Do not report its bandwidth as an H2 number under any "
                  "qualification.")
            print("  " + "!" * 74)

        # ---------------- primary result ----------------
        print("\nAGGREGATE BANDWIDTH vs THE SUPERSEDED CAMPAIGN")
        print(f"  {'run':>34s} {'agg_bw_sum':>11s} {'per core':>9s} {'spread':>7s} "
              f"{'baseline':>9s} {'vs base':>8s} {'of ceiling':>11s} {'wall h':>7s}")
        for r in live:
            base = r.get("baseline_agg_bw_sum")
            print(f"  {r['run'][:34]:>34s} {r['agg_bw_sum']:>8.2f} GB/s "
                  f"{r['bw_per_core']:>6.2f} GB/s {r['bw_spread_pct']:>6.2f}% "
                  f"{(base or 0):>8.2f} "
                  f"{(r.get('vs_baseline') or 0):>7.3f}x "
                  f"{r['cxl_bw_used_frac']*100:>10.1f}% "
                  f"{(r['wall_hours'] or 0):>7.2f}")
        print("  'of ceiling' is agg_bw_sum over the REALIZED CXL ceiling.  In the")
        print("  superseded campaign it was 2.65-8.63%; a cap that binds pushes it up.")

        # ---------------- home-node / concurrency decomposition ----------------
        print("\nCONCURRENCY DECOMPOSITION (throughput = concurrency x 64 B / latency)")
        print(f"  {'run':>34s} {'HNF lat':>9s} {'concurrency':>12s} {'of HNF TBE':>11s} "
              f"{'of L1 MSHR':>11s} {'of SNF TBE':>11s} {'CXL rd/demand':>14s}")
        for r in live:
            print(f"  {r['run'][:34]:>34s} {r['hnf_read_latency_ns']:>6.1f} ns "
                  f"{r['hnf_concurrency']:>9.1f} ln "
                  f"{r['hnf_tbe_occupancy_frac']*100:>10.1f}% "
                  f"{r['l1_mshr_occupancy_frac']*100:>10.1f}% "
                  f"{r['snf_tbe_occupancy_frac']*100:>10.1f}% "
                  f"{r['cxl_read_over_demand']:>13.3f}x")

        print("\nWINDOW ALIGNMENT (no cross-process barrier exists; this is a bound)")
        for r in live:
            print(f"  {r['run'][:44]:>44s} min window "
                  f"{min(r['measured_window_s'])*1e3:>8.4f} ms  skew "
                  f"{r['exit_skew_s']*1e3:>7.4f} ms  overlap floor "
                  f"{r['window_overlap_floor']*100:>5.1f}%")

    # ---------------- pre-declared predictions ----------------
    print("\nPRE-DECLARED PREDICTIONS (registered before launch; not narrated after)")
    pred_hits = pred_total = 0
    if name == "cxlbw":
        for (n, _s, t) in camp["cells"]:
            want = CXLBW_PREDICTION[(n, t)]
            for arm in ARMS:
                label, lo, hi = want[arm]
                tag = f"P {arm}_{n}c @ {gbps(t):.2f} GB/s: {label} [{lo:.2f},{hi:.2f}]x"
                r = by.get((arm, n, t))
                pred_total += 1
                if not r:
                    mark(tag, False, "run void/missing")
                    continue
                ratio = r["vs_baseline"]
                ok = lo <= ratio <= hi
                pred_hits += ok
                mark(tag, ok,
                     f"{r['agg_bw_sum']:.2f} vs baseline "
                     f"{r['baseline_agg_bw_sum']:.2f} = {ratio:.3f}x")

        print("\nTHE ALARMING OUTCOME: does the H2-over-WB advantage survive a real cap?")
        alarm = False
        for (n, _s, t) in camp["cells"]:
            h2, wb = by.get(("h2", n, t)), by.get(("wb", n, t))
            if not (h2 and wb):
                continue
            got = h2["agg_bw_sum"] / wb["agg_bw_sum"]
            base = BASELINE[("h2", n)] / BASELINE[("wb", n)]
            shrunk = got < base * ALARM_SHRINK_FRAC
            inverted = got < 1.0
            alarm |= shrunk or inverted
            # got/base - 1, not got/base: this line reports a CHANGE, and the
            # predicate below is a 5% shrink test.  Printing the ratio itself as
            # a percentage rendered a 0.5% change as "+100.5% relative".
            print(f"  {n}c @ {gbps(t):>6.2f} GB/s cap:  h2/wb = {got:.4f} "
                  f"(uncapped {base:.4f}, {got/base - 1:+.1%} relative)"
                  f"{'  <-- SHRUNK' if shrunk else ''}"
                  f"{'  <-- INVERTED' if inverted else ''}")
        if alarm:
            print("  ALARM: H1's bandwidth-survival claim is contingent on an")
            print("  unphysical interconnect and must be rescoped in the paper.")
        elif len(live) == expected:
            print("  No alarm: the H2-over-WB advantage survives a realistic CXL cap.")
    else:
        for arm in ARMS:
            lo, hi = SLICE_PREDICTION[arm]
            r = by.get((arm, 4, BW_TICKS_DEFAULT))
            pred_total += 1
            if not r:
                mark(f"P {arm}_4c in {lo}-{hi} GB/s band", False, "run void/missing")
                continue
            ok = lo <= r["agg_bw_sum"] <= hi
            pred_hits += ok
            mark(f"P {arm}_4c in {lo}-{hi} GB/s band", ok,
                 f"{r['agg_bw_sum']:.2f} GB/s (4-slice {r['baseline_agg_bw_sum']:.2f})")
        wb, h2, pf = (by.get((a, 4, BW_TICKS_DEFAULT)) for a in ("wb", "h2", "pfoff"))
        if wb and h2 and pf:
            print(f"  ordering  h2 {h2['agg_bw_sum']:.2f} / wb {wb['agg_bw_sum']:.2f} "
                  f"/ pfoff {pf['agg_bw_sum']:.2f}")
            if not (h2["agg_bw_sum"] >= wb["agg_bw_sum"] > pf["agg_bw_sum"]):
                print("  ORDERING INVERTED -- pre-declared as possible; informative")
                print("  negative, and evidence the archive was not buffer-capped.")
        else:
            print("  ordering NOT EVALUATED: at least one arm is void.  An H2-vs-WB")
            print("  ordering requires an H2 cell in which H2 engaged (G5).")
        if live:
            # The quantity that drives G5 failures here: the per-slice HNF
            # transaction-buffer pool is what a retried request had to be
            # rejected from, and a retried request loses its STREAMING tag.
            print(f"  HNF TBE budget fell to {live[0]['hnf_tbe_budget']}; "
                  f"measured occupancy and HNF write-retry fraction:")
            for r in recs:
                occ = r.get("hnf_tbe_occupancy_frac")
                print(f"    {r['run'][:44]:>44s} "
                      f"occupancy {('n/a' if occ is None else f'{occ*100:.1f}%'):>6s} "
                      f"write-retry "
                      f"{(r.get('hnf_write_retry_frac') or 0)*100:>5.1f}%"
                      f"{'   (VOID)' if not r['completed'] else ''}")

    # ---------------- verdict ----------------
    print("\n===== VERDICT =====")
    if len(live) != expected:
        print(f"INCOMPLETE: {len(live)}/{expected} cells certified; no claim licensed.")
        rc = 1
    else:
        print(f"COMPLETE: {len(live)}/{expected} cells certified against all four gates.")
        print(f"Pre-declared predictions confirmed: {pred_hits}/{pred_total}.")
        rc = 0
    print("Every configuration figure above is read back from config.ini.  A run")
    print("whose realized CXL bandwidth did not match its request is VOID above")
    print("and contributes no number here.")

    # One record file per stamp.  Both stamps of this campaign used to write
    # the same path with mode "w", so re-analyzing a re-run silently replaced
    # the original campaign's records with the re-run's.
    jsonl = camp["jsonl"]
    if stamp != "*":
        jsonl = jsonl.with_name(f"{jsonl.stem}_{stamp}.jsonl")
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    lead = ("run", "completed", "reason")
    with jsonl.open("w") as f:
        for r in recs:
            r.pop("outdir", None)
            ordered = {k: r[k] for k in lead if k in r}
            ordered.update({k: v for k, v in r.items() if k not in lead})
            f.write(json.dumps(ordered) + "\n")
    print(f"\nwrote {len(recs)} records to {jsonl}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
