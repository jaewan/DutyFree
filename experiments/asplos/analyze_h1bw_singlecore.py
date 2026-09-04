#!/usr/bin/env python3
"""H1 single-core bandwidth / LLC-footprint MSHR sweep -- analyzer.

The certified replacement for Appendix.tex tab:h1bw.  Pre-registered in
H1BW_SINGLECORE_PREREG_2026-09-04.md; read it first.

Sibling of `analyze_h1bw_bracket.py` and `analyze_h1bw_multicore.py`, both of
which are left UNTOUCHED so they keep certifying the completed campaigns.  This
one handles what neither can:

  * three stats sections per run instead of one, because the measured loop is
    bracketed by m5 ops 0x41/0x40 (AGGBW_WINDOW_PREREG_2026-09-03.md section 1).
    Every counter is therefore available WINDOWED -- scoped to the measured
    pass -- as well as whole-program.  This is the first campaign in the project
    where the footprint column and the bandwidth column describe the same
    interval;
  * `L1_MSHR` as a swept variable, gated against config.ini rather than trusted;
  * `L1_REPL` set explicitly, and a diagnostic cell set at the default value;
  * a single instance, so there is no window-stagger question at all
    (AGGBW_VALIDITY_2026-09-03.md section Q2 does not apply here).

Usage: analyze_h1bw_singlecore.py [campaign-date]

Twelve pre-registered gates, all fail-closed.  A cell failing any of them is
printed VOID and contributes no number to the verdict or to the paper table.

Everything is a module constant, not an argument, so changing a threshold after
seeing data is visible in git (the W1 rule).
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from pathlib import Path

LOGROOT = "/home/domin/DutyFree/logs/se_chi_h1bw_sc"
DATADIR = Path("/home/domin/DutyFree/experiments/asplos/data/gem5")
PREREG = "H1BW_SINGLECORE_PREREG_2026-09-04.md"

# --- frozen configuration.  Every one of these is checked against the artifact.
ARMS = ("wb", "h2", "pfoff")
ARM_POLICY = {"wb": "wb", "h2": "stream", "pfoff": "stream"}
ARM_LABEL = {"wb": "WB", "h2": "+H2", "pfoff": "pf-off"}   # tab:h1bw column heads
NCORES = 1
L3_SLICES = 1
L3_PER_SLICE = 5 * 1024 * 1024          # 5 MiB / 20-way, one HNF slice
L3_ASSOC = 20
FACT_BYTES = 16 * 1024 * 1024           # 16 MiB stream, > the 5 MiB LLC
WARMUPS = 2
REPS = 8
PASSES = WARMUPS + REPS                 # 10, EVEN, so checksum must be 0 (G11)
LINE_BYTES = 64
LINES_PER_PASS = FACT_BYTES // LINE_BYTES        # 262,144
L2_MSHR = 48                            # CHI_config_8592.py:364 default
HNF_TBE_PER_SLICE = 32                  # CHI_config_8592.py:435, HNF_MSHR unset
SNF_TBE = 256                           # CHI_config_8592.py:961, SNF_MSHR unset
CXL_LATENCY_NS = 203.0
DRAM_LATENCY_NS = 98.0
CPU_HZ = 1.9e9
RUBY_TICKS_PER_CY = 500                 # system.ruby.clk_domain.clock -> 2 GHz
TICKS_PER_S = 1e12                      # stats.txt simFreq
BW_TICKS_EXPECT = 2                     # no cap requested; SimObject default
N_SECTIONS = 2 * NCORES + 1             # 3: setup | measured window | epilogue
WINDOW_SECTION = 1                      # 0-indexed; validated by G7

# --- cells.  (arm, l1_mshr, l1_repl, kind)
PRIMARY_CELLS = [(a, m, 48, "primary") for m in (16, 48) for a in ARMS]
DIAG_CELLS = [(a, 48, 16, "diag") for a in ARMS]
CELLS = PRIMARY_CELLS + DIAG_CELLS

# --- G5, RE-DERIVED FOR THE FIXED BINARY.  See the pre-registration, section
# --- "G5 re-derived -- the thresholds are not inherited".
#
# `analyze_h1bw_bracket.py` uses 0.20 on both fill suppression and
# bypass/decision.  AGGBW_VALIDITY_2026-09-03.md flags those as derived from
# PRE-FIX cells and requiring re-derivation against gem5.opt cb290444, which
# carries commit b9c8714c93 ("CHI: carry isStreaming across the request retry
# path").  Both move, and they move in OPPOSITE directions.
#
# PRIMARY GATE -- a residue COUNT, not a fraction.
#   H2_BYPASS_FIX_OUTCOME_2026-09-03.md section 4 corrects the earlier "96.0%
#   engagement ceiling" to a constant ~4,408 un-bypassable clean evictions PER
#   CORE.  It is measured at 4,408/core at 4 slices/4 cores, 4,408/core at 8
#   slices/8 cores -- four significant figures across different core AND slice
#   counts -- and 4,433/core and 5,315/core in the two post-fix one-slice cells
#   (computed directly from their stats.txt for this pre-registration).
#
#   A constant count is the right gate because the defect signature is that the
#   residue SCALES WITH TRAFFIC while the fixed behaviour holds it constant.
#   8,000 is 1.51x the largest observation.  This campaign's clean-decision
#   denominator is predicted near 437,000 (the post-fix 8 MiB cells give
#   218,682/core; 16 MiB doubles it), so a cell at the collapsed 1.8%
#   engagement would read a residue near 429,000 -- 54x the gate -- and one at
#   40% engagement near 262,000 -- 33x.  The gate separates "fixed and engaged"
#   from "retry leak present" by 1.5 orders of magnitude with a 1.5x margin.
#
#   Why the inherited 0.20 fraction fails: post-fix engagement is pinned at its
#   structural ceiling, 97.6-98.0%, and bypass/decision at 0.570-0.571.  A 0.20
#   floor would pass a cell that had lost FOUR FIFTHS of the policy -- exactly
#   the failure the fix removed.  The inherited gate is loose by ~3x.
A1_MAX_UNBYPASSABLE_PER_CORE = 8000

# CORROBORATING GATE -- fill suppression against the matched WB arm, required by
# the brief, re-derived DOWN from 0.20 to 0.25 (up in value, down in strictness
# relative to the post-fix observation of 0.562-0.577).
#   The archive's own h2 rows imply suppression of 0.433 at 16 MSHRs and 0.332
#   at 48, and there is a real mechanism for the fall: a PREFETCHED line reaches
#   the HNF without the STREAMING tag the demand path would have given it
#   (H2_BYPASS_FIX_OUTCOME section 4 measures this as 882 evictions/core), and
#   deeper MSHRs let the prefetcher run further ahead.  Prediction S3 says that
#   population GROWS with the swept variable.  A floor above ~0.30 would void
#   the 48-MSHR h2 cell for exhibiting the very effect the sweep measures.
#   0.25 is 25% below the lowest archive-consistent expectation and 20x above
#   the collapsed cell's 0.012.
# Suppression is therefore the CORROBORATING measure and the residue count the
# PRIMARY one: suppression is sensitive to exactly the population this sweep
# varies, the residue is not.
A1_MIN_FILL_SUPPRESSION = 0.25

# Reference values from the post-fix cells, printed alongside so a failing cell
# is diagnosed rather than merely voided.  Not thresholds.
POSTFIX_RESIDUE_PER_CORE_MAX = 5315
POSTFIX_E_CLEAN = (0.9757, 0.9796)

# --- G7: the bracket has to land where the source puts it.
G7_WINDOW_SECONDS_TOL = 0.005           # 0.5%; the pilot read 0.0018

# --- the archive, as the comparison baseline.  results/gem5_streaming/REPORT.md
# --- section 1, the twelve numbers tab:h1bw publishes.  Bandwidth GB/s; fills
# --- are WHOLE-PROGRAM LLC data-array writes, which is what that column is
# --- (its WB figure of 529,330 is 2.02x the stream's 262,144 lines, i.e. a warm
# --- pass plus a measured pass), so the comparison is made on the whole-program
# --- quantity and NOT on the windowed one.
ARCHIVE = {
    ("wb", 16): {"bw": 4.24, "ipc": 0.209, "fills": 529330},
    ("h2", 16): {"bw": 4.90, "ipc": 0.209, "fills": 300238},
    ("pfoff", 16): {"bw": 4.60, "ipc": 0.204, "fills": 289695},
    ("wb", 48): {"bw": 5.44, "ipc": 0.210, "fills": 529309},
    ("h2", 48): {"bw": 5.82, "ipc": 0.211, "fills": 353739},
    ("pfoff", 48): {"bw": 4.60, "ipc": 0.204, "fills": 289698},
}
# A cell "reproduces" an archived figure within this band.  Set at 20% because
# the one prior attempted reproduction (GATE1_H1BW_RERUN_OUTCOME.md, gem5
# b2c6499) had NO cell within 25% and inverted the WB/H2 ordering, so 20% is
# demanding against that history and lenient against a reproduction claim.
ARCHIVE_REPRODUCE_TOL = 0.20
ARCHIVE_STRUCTURE_MIN_REPRODUCED = 9    # of 12, for outcome A rather than B

# --- pre-declared structural predictions.  These are the sharp tests and they
# --- do not depend on any magnitude reproducing.  See the pre-registration.
S1_PFOFF_BW_MSHR_TOL = 0.10       # |bw(48)-bw(16)|/bw(16) for pf-off
S2_PFOFF_FILL_MSHR_TOL = 0.02     # windowed footprint, pf-off
S3_H2_FILL_MUST_RISE = True       # h2 windowed footprint rises with MSHR depth
S4_WB_FILL_MSHR_TOL = 0.05        # wb footprint, either scope
# S5: h2 fills < wb fills at both depths.  S6: h2 >= wb > pfoff at 48 MSHRs.
# S7: the 16-MSHR ordering is deliberately NOT pre-declared -- the archive has
#     wb (4.24) BELOW pf-off (4.60) there, the sign flips inside the sweep, and
#     both signs are admissible in advance.  No pooled WB/pf-off ratio is
#     computed anywhere in this file; see `forbidden_pooled_ratio()`.

# --- windowed footprint bands, per measured pass, as a fraction of the 262,144
# --- lines one pass reads.  The HNF is a non-inclusive victim cache with
# --- alloc_on_read* all false (CHI_config_8592.py:298-300), so a read never
# --- allocates and every data-array write comes from an eviction.
WINDOW_FILL_BAND = {"wb": (0.85, 1.15), "h2": (0.02, 0.35), "pfoff": (0.02, 0.20)}
# --- magnitude bands, absolute GB/s.  16-MSHR bands are anchored on the
# --- concurrency ceiling the archive itself names, 16 x 64 B / 203 ns = 5.04
# --- GB/s; the 48-MSHR ceiling is the HNF's own pool, 32 x 64 B / 203 ns = 10.1.
BW_BAND = {("wb", 16): (3.0, 5.5), ("h2", 16): (3.0, 5.5), ("pfoff", 16): (2.0, 5.2),
           ("wb", 48): (4.0, 11.0), ("h2", 48): (4.0, 11.0), ("pfoff", 48): (2.0, 5.2)}

# --- the one-slice hazard, declared in advance (H2_BYPASS_FIX_OUTCOME section 5:
# --- at 1 slice with 4 cores the ordering inverted to pfoff > h2 > wb because
# --- the 32-entry HNF pool bound, not LLC fills).  With one core the pool sees
# --- ~a quarter of the demand, so:
HAZARD_RETRY_FRAC_EXPECT_BELOW = 0.20   # predicted; an observable, not a gate
HAZARD_RETRY_FRAC_BUFFER_CAPPED = 0.50  # above this, an inversion is a home-node
                                        # result rather than an H2 result
HAZARD_HNF_OCCUPANCY_EXPECT_BELOW = 0.60

HNF_RE = re.compile(r"^system\.ruby\.hnf(\d*)\.cntrl\.cache$")
HNF_CNTRL_RE = re.compile(r"^system\.ruby\.hnf(\d*)\.cntrl$")
# The L1 controller sections.  PARSER CORRECTION, 2026-09-04, post-launch:
# this was written as ^system\.ruby\.rnf(\d+)\.cntrl$ on the assumption that
# CHI names L1 controllers under the rnf node.  It does not.  The realized
# names in every cell of this campaign are system.cpu.l1d and system.cpu.l1i
# (system.cpu<i>.l1[di] at more than one core), so the old pattern matched
# nothing, G8 read an empty realized set and fail-closed all nine cells.  That
# is the gate behaving correctly on an unreadable knob; the knob itself was
# realized correctly all along (16/48, 48/48 and 48/16 as declared, verified
# by hand in config.ini before this line was changed).
#
# G8's SEMANTICS AND DECLARED VALUES ARE UNCHANGED -- this edit changes where
# the gate looks, not what it requires.  It is committed as its own commit,
# after the pre-registration commit, so the sequence is visible in git.
#
# system.cpu.l2 must NOT match: L2_MSHR is a separate knob defaulting to 48,
# so matching it would compare the L2's 48 against a declared L1_MSHR of 16
# and fail the 16-MSHR cells for the wrong reason.
L1_TBE_RE = re.compile(r"^system\.cpu(\d*)\.l1[di]$")


def mark(name, ok, detail):
    print(f"  {name:56s} {'PASS' if ok else 'FAIL'}  {detail}")
    return ok


def gbps(ticks_per_byte):
    return TICKS_PER_S / ticks_per_byte / 1e9


def load_stats_sections(path):
    """stats.txt -> [ {stat: value}, ... ], one dict per section.

    Streamed, not slurped: at three sections this file is only ~3 MB, but the
    sibling campaign's bracketed 8-core cells are ~83 MB and this reader is
    meant to survive being pointed at one.
    """
    secs, cur = [], None
    with open(path, errors="replace") as f:
        for line in f:
            if "Begin Simulation Statistics" in line:
                cur = {}
                secs.append(cur)
                continue
            if cur is None:
                continue
            line = line.split("#")[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    cur[parts[0]] = float(parts[1])
                except ValueError:
                    pass
    return secs


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


def hnf_prefixes(ini):
    """Realized HNF geometry -> {stats_prefix: (size, assoc)}.

    gem5 collapses a length-1 SimObjectVector to an unindexed name, so at
    --num-l3caches=1 the section is `system.ruby.hnf`, not `system.ruby.hnf0`.
    A `hnf(\\d+)` regex matches zero sections there and would report a 0-byte
    LLC, voiding every cell in this campaign for the wrong reason.  Both
    spellings are matched and the prefix is handed back so the stats reader uses
    the same one.
    """
    out = {}
    for name, body in ini.items():
        m = HNF_RE.match(name)
        if m:
            out[name[: -len(".cache")]] = (int(body["size"]), int(body["assoc"]))
    return out


def l1_tbes(ini):
    """Realized L1 (number_of_TBEs, number_of_repl_TBEs) -- G8's authority.

    L1_MSHR and L1_REPL are the swept knobs, so they are read back rather than
    trusted.  A silently-ignored L1_MSHR would turn the sweep into two
    replicates of one point, and publishing that as a sweep is the F9 defect
    class.  The L1D controller is the RNF cntrl section that carries both a
    sequencer and a cache; the L1I controller of the same RNF takes the same
    env values, so a disagreement between them would itself be a finding.
    """
    vals = []
    for name, body in ini.items():
        if L1_TBE_RE.match(name) and "number_of_TBEs" in body:
            vals.append((int(body["number_of_TBEs"]),
                         int(body["number_of_repl_TBEs"])))
    return vals


def hnf_counters(stats, prefixes):
    """The engagement and footprint counters, for ONE stats section."""
    c = dict(fills=0.0, bypasses=0.0, decisions=0.0, clean_decisions=0.0,
             clean_bypassed=0.0, accesses=0.0, hits=0.0,
             write_retries=0.0, write_arrivals=0.0, read_misses=0.0,
             read_shared_miss=0.0, read_unique_miss=0.0)
    for p in prefixes:
        b = f"{p}.cache."
        c["fills"] += stats.get(b + "numDataArrayWrites", 0.0)
        c["bypasses"] += stats.get(b + "streamingHnfFillBypasses", 0.0)
        c["accesses"] += (stats.get(b + "m_demand_accesses", 0.0)
                          + stats.get(b + "m_prefetch_accesses", 0.0))
        c["hits"] += (stats.get(b + "m_demand_hits", 0.0)
                      + stats.get(b + "m_prefetch_hits", 0.0))
        # This HNF is a non-inclusive victim cache (alloc_on_read* all False),
        # so a read never presents a fill opportunity; only WriteEvictFull and
        # WriteBackFull do, and only when they find the LLC entry invalid --
        # dir state RU.  The RU->{I,UC,UD} transitions are therefore the exact
        # denominator for engagement, and RU->I is the numerator CacheMemory
        # increments.
        for t in ("WriteEvictFull", "WriteBackFull"):
            for final in ("I", "UC", "UD"):
                c["decisions"] += stats.get(f"{p}.inTransLatHist.{t}.RU.{final}.total", 0.0)
            c["write_retries"] += stats.get(f"{p}.inTransLatHist.{t}.retries", 0.0)
            c["write_arrivals"] += stats.get(f"{p}.inTransLatHist.{t}::samples", 0.0)
        # WriteEvictFull alone is the CLEAN eviction path, which is the only one
        # STREAMING can tag: a dirty writeback cannot carry the attribute
        # (H2_BYPASS_FIX_OUTCOME section 6).  E_clean and the residue are
        # computed on it, and that is what makes the residue a constant count.
        for final in ("I", "UC", "UD"):
            c["clean_decisions"] += stats.get(f"{p}.inTransLatHist.WriteEvictFull.RU.{final}.total", 0.0)
        c["clean_bypassed"] += stats.get(f"{p}.inTransLatHist.WriteEvictFull.RU.I.total", 0.0)
        c["read_shared_miss"] += stats.get(f"{p}.inTransLatHist.ReadShared.I.RU.total", 0.0)
        c["read_unique_miss"] += stats.get(f"{p}.inTransLatHist.ReadUnique_PoC.I.RU.total", 0.0)
        c["read_misses"] += stats.get(f"{p}.cache.ReadMissPipe", 0.0)
    return c


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
    return (num / den) * RUBY_TICKS_PER_CY / TICKS_PER_S * 1e9 if den else None


def analyze(outdir, arm, mshr, repl, kind):
    r = {
        "run": os.path.basename(outdir),
        "outdir": outdir,
        "arm": arm,
        "arm_label": ARM_LABEL[arm],
        "cell_kind": kind,
        "ncores": NCORES,
        "declared_l1_mshr": mshr,
        "declared_l1_repl": repl,
    }
    need = ("console.log", "stats.txt", "config.ini", "MANIFEST.json", "DONE.json")
    missing = [f for f in need if not os.path.exists(os.path.join(outdir, f))]
    if missing:
        r.update(completed=False, reason=f"missing {','.join(missing)}")
        return r

    console = os.path.join(outdir, "console.log")
    secs = load_stats_sections(os.path.join(outdir, "stats.txt"))
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
    r["gem5_git_describe"] = manifest.get("gem5_git_describe")
    r["configs_git_describe"] = manifest.get("configs_git_describe")
    r["gem5_build_provenance_json_present"] = manifest.get(
        "gem5_build_provenance_json_present")
    r["host"] = manifest.get("host")
    r["free_invalid_size"] = log.count("free(): invalid size")
    # a5f366456e's abs() guard on SimpleMemory.bandwidth tick quantization.
    # Warning-only (config.ini byte-identical, wb bit-identical across the fix),
    # so this is COUNTED AND REPORTED and is explicitly NOT a gate.
    r["rounding_error_warnings"] = len(re.findall(r"rounding error > tolerance", log))
    r["reached_exit"] = "Exiting @ tick" in log
    r["window_open_markers"] = len(re.findall(r"^AGGBW_WINDOW_OPEN\b", log, re.M))
    r["window_close_markers"] = len(re.findall(r"^AGGBW_WINDOW_CLOSE\b", log, re.M))
    r["stats_sections"] = len(secs)

    # ---- realized identity, from the artifact
    cmds = re.findall(r"^cmd=(.*)$", Path(outdir, "config.ini").read_text(errors="replace"), re.M)
    pols = {m.group(1) for c in cmds for m in [re.search(r"--policy (\S+)", c)] if m}
    r["realized_policy"] = sorted(pols)[0] if len(pols) == 1 else f"MIXED:{sorted(pols)}"
    r["realized_instances"] = len(inst)
    r["realized_workloads"] = len(cmds)
    r["prefetcher_sections"] = sum(1 for s in ini if "prefetcher" in s.lower())

    # ---- realized geometry, from config.ini and never from MANIFEST.json
    sl = hnf_prefixes(ini)
    prefixes = sorted(sl)
    r["hnf_slices"] = len(sl)
    r["llc_bytes_realized"] = sum(s for s, _ in sl.values())
    r["l3_assoc_realized"] = sorted({a for _, a in sl.values()})
    r["cxl_latency_ns_realized"] = float(ini["system.mem_ctrls1"]["latency"]) / 1000.0
    r["dram_latency_ns_realized"] = float(ini["system.mem_ctrls0"]["latency"]) / 1000.0
    r["cxl_latency_var_realized"] = float(ini["system.mem_ctrls1"]["latency_var"])
    r["mem_type_realized"] = ini["system.mem_ctrls1"]["type"]
    r["cxl_bw_ticks_per_byte_realized"] = float(ini["system.mem_ctrls1"]["bandwidth"])
    r["dram_bw_ticks_per_byte_realized"] = float(ini["system.mem_ctrls0"]["bandwidth"])
    r["cxl_bw_ceiling_gbps"] = round(gbps(r["cxl_bw_ticks_per_byte_realized"]), 4)
    l1 = l1_tbes(ini)
    r["l1_tbes_realized"] = sorted({t for t, _ in l1})
    r["l1_repl_tbes_realized"] = sorted({t for _, t in l1})
    # The finite snoop filter is instantiated only under HNF_SF_FINITE=1
    # (CHI_config_8592.py:866-872), which this campaign does not set.  Recorded
    # rather than gated: tab:gem5cfg's 65,536-entry row is annotated
    # "finite-SF runs" and scopes itself to the H3 runs of tab:h3sf.
    # Reconciliation 5 of the pre-registration.  Section PRESENCE is not the
    # question and was a misleading thing to record: CHI_config_8592.py always
    # attaches an `sf` RubyCache to the HNF controller, but it is a placeholder
    # (assoc 1, block_size 0, size 1024) unless HNF_SF_FINITE=1.  The
    # load-bearing flag is `sf_finite` on the controller, which gates whether
    # SLICC enforces directory capacity at all.  Both are recorded; the second
    # is the one the pre-registration's reconciliation 5 turns on.
    r["hnf_sf_section_present"] = any(
        "snoop" in s.lower() or s.endswith(".sf") for s in ini)
    hnf_cntrl = next((b for n, b in ini.items()
                      if HNF_CNTRL_RE.match(n)), {})
    r["hnf_sf_finite"] = hnf_cntrl.get("sf_finite")
    r["hnf_sf_size"] = ini.get("system.ruby.hnf.cntrl.sf", {}).get("size")
    # The fill accounting the windowed footprint prediction rests on: a read
    # must never allocate, so every data-array write is an eviction.
    r["hnf_alloc_on_read"] = {
        k: hnf_cntrl.get(k) for k in
        ("alloc_on_readshared", "alloc_on_readunique",
         "alloc_on_readonce", "alloc_on_writeback")}

    # ---- gates G1-G4, G6, G8-G12 (G5 and G7 below; G5 is cross-run)
    statuses = [x.get("status") for x in inst]
    r["g1_status_ok"] = bool(inst) and all(s == "ok" for s in statuses)
    r["g2_instances"] = (r["realized_instances"] == NCORES
                         and r["realized_workloads"] == NCORES)
    r["g3_llc"] = (r["hnf_slices"] == L3_SLICES
                   and r["llc_bytes_realized"] == L3_SLICES * L3_PER_SLICE
                   and r["l3_assoc_realized"] == [L3_ASSOC])
    r["g4_memory"] = (
        r["cxl_bw_ticks_per_byte_realized"] == float(BW_TICKS_EXPECT)
        and r["dram_bw_ticks_per_byte_realized"] == float(BW_TICKS_EXPECT)
        and abs(r["cxl_latency_ns_realized"] - CXL_LATENCY_NS) < 0.5
        and abs(r["dram_latency_ns_realized"] - DRAM_LATENCY_NS) < 0.5
        and r["cxl_latency_var_realized"] == 0.0
        and r["mem_type_realized"] == "SimpleMemory")
    r["g6_bracketing"] = (r["stats_sections"] == N_SECTIONS
                          and r["window_open_markers"] == NCORES
                          and r["window_close_markers"] == NCORES)
    r["g8_mshr"] = (r["l1_tbes_realized"] == [mshr]
                    and r["l1_repl_tbes_realized"] == [repl])

    # G9: with ALL_CXL=1 there must be no local-DRAM traffic AT ALL.  The only
    # non-zero mem_ctrls0 counter permitted is the power-state residency tick,
    # which gem5 emits unconditionally.  Checked on the whole-program total,
    # i.e. across every section.
    mc0 = []
    for s in secs:
        for k, v in s.items():
            if k.startswith("system.mem_ctrls0.") and v != 0.0 \
                    and "pwrStateResidencyTicks" not in k:
                mc0.append(k)
    r["mem_ctrls0_nonzero"] = sorted(set(mc0))
    r["g9_placement"] = not mc0

    one = inst[0] if inst else {}
    r["g10_workload"] = (one.get("fact_bytes") == FACT_BYTES
                         and one.get("warmups") == WARMUPS
                         and one.get("reps") == REPS
                         and one.get("window_brackets") is True
                         and abs((one.get("hit_rate") or 0) - 0.5) < 1e-9)
    # G11: warmups + reps == 10 is EVEN, so the XOR over identical unmodified
    # data must be exactly 0.  AGGBW_VALIDITY_2026-09-03.md recommended this as
    # fail-closed and recorded that no analyzer implements it; nine of that
    # campaign's 120 instances would have failed it.
    r["checksum"] = one.get("checksum")
    r["g11_checksum"] = one.get("checksum") == 0
    pf_expect = (arm != "pfoff")
    r["g12_prefetchers"] = (r["prefetcher_sections"] > 0) == pf_expect
    r["realized_policy_ok"] = r["realized_policy"] == ARM_POLICY[arm]

    hard = ("g1_status_ok", "g2_instances", "g3_llc", "g4_memory", "g6_bracketing",
            "g8_mshr", "g9_placement", "g10_workload", "g11_checksum",
            "g12_prefetchers", "realized_policy_ok")
    if not all(r[k] for k in hard):
        r["completed"] = False
        r["reason"] = "; ".join(x for x in (
            None if r["g1_status_ok"] else f"G1 status={statuses}",
            None if r["g2_instances"] else
            f"G2 instances={r['realized_instances']}/workloads={r['realized_workloads']} != {NCORES}",
            None if r["g3_llc"] else
            f"G3 llc={r['llc_bytes_realized']} B over {r['hnf_slices']} slices "
            f"assoc {r['l3_assoc_realized']} != {L3_SLICES}x{L3_PER_SLICE}/{L3_ASSOC}",
            None if r["g4_memory"] else
            f"G4 cxl {r['cxl_bw_ticks_per_byte_realized']} tk/B "
            f"{r['cxl_latency_ns_realized']} ns var {r['cxl_latency_var_realized']}, "
            f"dram {r['dram_bw_ticks_per_byte_realized']} tk/B "
            f"{r['dram_latency_ns_realized']} ns, type {r['mem_type_realized']}",
            None if r["g6_bracketing"] else
            f"G6 {r['stats_sections']} stats sections (want {N_SECTIONS}), "
            f"{r['window_open_markers']} OPEN / {r['window_close_markers']} CLOSE "
            f"markers (want {NCORES} each) -- the bracketing did not fire",
            None if r["g8_mshr"] else
            f"G8 realized L1 TBEs {r['l1_tbes_realized']} / repl "
            f"{r['l1_repl_tbes_realized']} != declared {mshr}/{repl} -- the SWEPT "
            f"knob was not realized; this cell is not the point it claims to be",
            None if r["g9_placement"] else
            f"G9 local-DRAM traffic present: {r['mem_ctrls0_nonzero'][:4]}",
            None if r["g10_workload"] else
            f"G10 workload fact_bytes={one.get('fact_bytes')} warmups={one.get('warmups')} "
            f"reps={one.get('reps')} brackets={one.get('window_brackets')}",
            None if r["g11_checksum"] else
            f"G11 checksum={one.get('checksum')} != 0 over {PASSES} passes of "
            f"identical unmodified data -- the run did not read what it thought "
            f"it read, so its footprint column is not publishable",
            None if r["g12_prefetchers"] else
            f"G12 {r['prefetcher_sections']} prefetcher sections, expected "
            f"{'>0' if pf_expect else 'exactly 0'} for arm {arm}",
            None if r["realized_policy_ok"] else
            f"realized policy {r['realized_policy']} != {ARM_POLICY[arm]}",
        ) if x)
        return r

    # ---- the sections.  0 = setup, 1 = the measured window, 2 = epilogue.
    win, whole = secs[WINDOW_SECTION], {}
    for s in secs:
        for k, v in s.items():
            whole[k] = whole.get(k, 0.0) + v
    r["section_simSeconds"] = [round(s.get("simTicks", 0.0) / TICKS_PER_S, 9) for s in secs]
    r["window_simSeconds"] = win.get("simTicks", 0.0) / TICKS_PER_S
    r["whole_simSeconds"] = whole.get("simTicks", 0.0) / TICKS_PER_S
    r["window_frac_of_program"] = (r["window_simSeconds"] / r["whole_simSeconds"]
                                   if r["whole_simSeconds"] else None)

    # ---- G7: the bracket landed where the source puts it.
    r["reported_seconds"] = one.get("seconds")
    r["window_vs_reported_err"] = (
        abs(r["window_simSeconds"] - r["reported_seconds"]) / r["reported_seconds"]
        if r["reported_seconds"] else None)
    r["g7_window_fidelity"] = (r["window_vs_reported_err"] is not None
                               and r["window_vs_reported_err"] <= G7_WINDOW_SECONDS_TOL)
    if not r["g7_window_fidelity"]:
        r["completed"] = False
        r["reason"] = (f"G7 window section simSeconds {r['window_simSeconds']:.9f} vs "
                       f"guest-reported {r['reported_seconds']} = "
                       f"{(r['window_vs_reported_err'] or 0)*100:.3f}% > "
                       f"{G7_WINDOW_SECONDS_TOL*100}% -- the m5 ops did not land "
                       f"where the source puts them")
        return r
    r["reason"] = "ok"
    r["completed"] = True          # provisional; G5 is cross-run and runs later

    # ---- the primary metrics
    r["bandwidth_gbps"] = one.get("bandwidth_gbps")
    samples = one.get("samples") or []
    r["reps_realized"] = len(samples)
    r["sample_min"] = min(samples) if samples else None
    r["sample_max"] = max(samples) if samples else None
    if len(samples) > 1:
        m = sum(samples) / len(samples)
        var = sum((x - m) ** 2 for x in samples) / (len(samples) - 1)
        r["sample_mean"] = m
        r["cov"] = (var ** 0.5) / m if m else None
        r["sample_halfrange_pct"] = (max(samples) - min(samples)) / 2 / m * 100.0
    else:
        r["sample_mean"] = r["cov"] = r["sample_halfrange_pct"] = None
    r["ipc"] = (win.get("system.cpu0.ipc") or win.get("system.cpu.ipc")
                or (win.get("simInsts", 0.0) / win["system.cpu0.numCycles"]
                    if win.get("system.cpu0.numCycles") else None))
    r["window_simInsts"] = win.get("simInsts")
    r["whole_simInsts"] = whole.get("simInsts")

    hw, hp = hnf_counters(win, prefixes), hnf_counters(whole, prefixes)
    # THE footprint column.  Windowed and per measured pass, so it is directly
    # comparable to the 262,144 lines one pass reads -- which is the prediction
    # the archive's whole-program column could not make.
    r["llc_fills_window"] = hw["fills"]
    r["llc_fills_window_per_pass"] = hw["fills"] / REPS
    r["llc_fills_window_per_pass_frac"] = hw["fills"] / REPS / LINES_PER_PASS
    # And the whole-program column, because THAT is what the archive's is.
    r["llc_fills_total"] = hp["fills"]
    r["llc_fills_total_over_stream_lines"] = hp["fills"] / LINES_PER_PASS

    for tag, c in (("window", hw), ("whole", hp)):
        r[f"{tag}_hnf_accesses"] = c["accesses"]
        r[f"{tag}_hnf_hit_frac"] = c["hits"] / c["accesses"] if c["accesses"] else None
        r[f"{tag}_bypasses"] = c["bypasses"]
        r[f"{tag}_decisions"] = c["decisions"]
        r[f"{tag}_bypass_per_decision"] = (c["bypasses"] / c["decisions"]
                                           if c["decisions"] else None)
        r[f"{tag}_clean_decisions"] = c["clean_decisions"]
        r[f"{tag}_clean_bypassed"] = c["clean_bypassed"]
        r[f"{tag}_e_clean"] = (c["clean_bypassed"] / c["clean_decisions"]
                              if c["clean_decisions"] else None)
        residue = c["clean_decisions"] - c["clean_bypassed"]
        r[f"{tag}_unbypassable_residue"] = residue
        r[f"{tag}_residue_per_core"] = residue / NCORES
        # The achievable ceiling implied by the post-fix residue constant, so a
        # cell that misses a threshold is diagnosed rather than merely voided.
        r[f"{tag}_e_clean_achievable"] = (
            1.0 - POSTFIX_RESIDUE_PER_CORE_MAX * NCORES / c["clean_decisions"]
            if c["clean_decisions"] else None)
        r[f"{tag}_hnf_write_retry_frac"] = (c["write_retries"] / c["write_arrivals"]
                                           if c["write_arrivals"] else None)
        r[f"{tag}_read_shared_miss"] = c["read_shared_miss"]
        r[f"{tag}_read_unique_miss"] = c["read_unique_miss"]

    # ---- windowed controller traffic.  At one instance with a bracketed
    # section this is a MEASUREMENT of the CXL-served share, where
    # AGGBW_VALIDITY section Q1 could only bound it one-sidedly from
    # whole-program counters.
    r["window_cxl_bytes_read"] = win.get("system.mem_ctrls1.bytesRead::total", 0.0)
    r["window_cxl_bytes_written"] = win.get("system.mem_ctrls1.bytesWritten::total", 0.0)
    r["whole_cxl_bytes_read"] = whole.get("system.mem_ctrls1.bytesRead::total", 0.0)
    useful = FACT_BYTES * REPS
    r["window_useful_bytes"] = useful
    r["window_cxl_read_per_useful_byte"] = r["window_cxl_bytes_read"] / useful
    r["window_cxl_write_per_useful_byte"] = r["window_cxl_bytes_written"] / useful
    # The complement is what the 5 MiB LLC supplied.  This is the residency
    # confound of AGGBW_VALIDITY finding 4, MEASURED in-window rather than
    # bounded -- and it is not removed by measuring it.
    r["window_llc_supplied_frac"] = max(0.0, 1.0 - r["window_cxl_read_per_useful_byte"])

    # ---- concurrency, on windowed counters.  throughput = concurrency x 64 B / latency
    lat = hnf_read_latency_ns(win, prefixes)
    r["hnf_read_latency_ns"] = lat
    lines_per_s = (r["bandwidth_gbps"] or 0.0) * 1e9 / LINE_BYTES
    r["hnf_concurrency"] = lines_per_s * lat * 1e-9 if lat else None
    r["l1_mshr_budget"] = mshr
    r["l1_mshr_occupancy_frac"] = (r["hnf_concurrency"] / mshr
                                   if r["hnf_concurrency"] else None)
    r["hnf_tbe_budget"] = HNF_TBE_PER_SLICE * L3_SLICES
    r["hnf_tbe_occupancy_frac"] = (r["hnf_concurrency"] / r["hnf_tbe_budget"]
                                   if r["hnf_concurrency"] else None)
    r["snf_tbe_occupancy_frac"] = lines_per_s * CXL_LATENCY_NS * 1e-9 / SNF_TBE
    # The ceiling the archive itself names for the 16-MSHR rows.
    r["mshr_concurrency_ceiling_gbps"] = mshr * LINE_BYTES / (CXL_LATENCY_NS * 1e-9) / 1e9
    r["frac_of_mshr_ceiling"] = ((r["bandwidth_gbps"] or 0.0)
                                 / r["mshr_concurrency_ceiling_gbps"])
    return r


def apply_engagement_gate(recs):
    """G5, applied across cells: did each arm's declared policy actually engage?

    Cross-cell, so it cannot live inside analyze(): the fill-suppression measure
    is relative to the WB arm of the SAME cell -- same MSHR point, same L1_REPL,
    same cell kind.  A cell that fails is voided in place, exactly like a G1-G4
    failure, so it contributes no number.  A streaming cell that did not engage
    is not a weaker H2 result -- it is a WB result wearing an H2 label, and
    reporting its bandwidth as H2 would be a category error rather than a
    conservative estimate.

    Both thresholds are RE-DERIVED for gem5.opt cb290444; see the module
    constants and the pre-registration.  The primary measure is the residue
    COUNT (a retry leak makes the residue scale with traffic; the fixed
    behaviour holds it at a constant per-core count).  The corroborating measure
    is fill suppression against the matched WB arm, which the brief requires and
    which this campaign has a peer for in every cell.
    """
    wb = {}
    for r in recs:
        if r["arm"] == "wb" and r.get("completed") and r.get("llc_fills_window"):
            wb[(r["declared_l1_mshr"], r["declared_l1_repl"], r["cell_kind"])] = r

    for r in recs:
        r["g5_engaged"] = None
        r["fill_suppression_window"] = None
        r["fill_suppression_whole"] = None
        r["wb_peer"] = None
        if not r.get("completed"):
            continue
        peer = wb.get((r["declared_l1_mshr"], r["declared_l1_repl"], r["cell_kind"]))
        if peer is not None and peer["run"] != r["run"]:
            r["wb_peer"] = peer["run"]
            r["fill_suppression_window"] = 1.0 - r["llc_fills_window"] / peer["llc_fills_window"]
            r["fill_suppression_whole"] = 1.0 - r["llc_fills_total"] / peer["llc_fills_total"]

        if ARM_POLICY[r["arm"]] == "wb":
            # Exact, not a threshold, and it needs no re-derivation: wb never
            # sets isStreaming, so one bypass would mean a STREAMING tag leaked
            # into the control arm.
            r["g5_engaged"] = (r["window_bypasses"] == 0 and r["whole_bypasses"] == 0)
            r["g5_detail"] = (f"{r['whole_bypasses']:.0f} bypasses whole-program, "
                              f"{r['window_bypasses']:.0f} in-window (both must be 0)")
            if not r["g5_engaged"]:
                r["completed"] = False
                r["reason"] = (f"wb arm recorded {r['whole_bypasses']:.0f} streaming "
                               f"bypasses -- STREAMING leaked into the control arm; VOID")
            continue

        fails = []
        res = r["window_residue_per_core"]
        if res is None:
            fails.append("no HNF clean-eviction decisions found in the window section")
        elif res > A1_MAX_UNBYPASSABLE_PER_CORE:
            fails.append(
                f"un-bypassable clean-eviction residue {res:.0f}/core > "
                f"{A1_MAX_UNBYPASSABLE_PER_CORE} (post-fix reference "
                f"{POSTFIX_RESIDUE_PER_CORE_MAX}/core; E_clean {r['window_e_clean']:.4f} "
                f"against an achievable {r['window_e_clean_achievable']:.4f})")
        s = r["fill_suppression_window"]
        if s is None:
            r["g5_no_wb_peer"] = True
        elif s < A1_MIN_FILL_SUPPRESSION:
            fails.append(f"in-window fill suppression vs {peer['run']} {s:.3f} "
                         f"< {A1_MIN_FILL_SUPPRESSION}")
        r["g5_engaged"] = not fails
        r["g5_detail"] = (
            f"residue {res:.0f}/core (max {A1_MAX_UNBYPASSABLE_PER_CORE}), "
            f"E_clean {r['window_e_clean']:.4f}, "
            f"suppression {'n/a' if s is None else round(s, 3)}, "
            f"byp/dec {r['window_bypass_per_decision']:.3f}, "
            f"wr retry {(r['window_hnf_write_retry_frac'] or 0):.3f}")
        if fails:
            r["completed"] = False
            r["reason"] = ("policy=stream DID NOT ENGAGE: " + "; ".join(fails)
                           + " -- VOID, this cell measured the writeback policy with "
                             "an inert STREAMING tag and is not an H2 number")


def forbidden_pooled_ratio():
    """A note, deliberately in the code rather than only in the document.

    H1BW_ARM_IDENTITY_2026-09-04.md section "Question 3" records that the
    appendix quoted a WB-over-pf-off ratio of 1.18x from the 48-MSHR row without
    noting that the 16-MSHR row of the same two rows reads 0.922x -- the sign
    FLIPS inside the sweep whose own caption insists "the sweep is the claim,
    not a single point".  This analyzer therefore computes WB/pf-off at each
    MSHR point separately and computes NO pooled statistic over the two: no
    mean, no range, no n.  They are two operating points of one sweep, not two
    samples of one quantity.  Nothing in this file should be changed to emit
    one.
    """
    return None


def wall_hours(rec):
    from datetime import datetime
    try:
        a = datetime.fromisoformat(rec["started"])
        b = datetime.fromisoformat(rec["ended"])
        return (b - a).total_seconds() / 3600.0
    except Exception:
        return None


def outdir_for(arm, mshr, repl, stamp):
    return f"{LOGROOT}/h1bw_sc_{arm}_1c_l3x{L3_SLICES}_m{mshr}_r{repl}_{stamp}"


def main(argv):
    stamp = argv[1] if len(argv) > 1 else "*"
    recs, voids = [], []
    for (arm, mshr, repl, kind) in CELLS:
        hits = sorted(glob.glob(outdir_for(arm, mshr, repl, stamp)))
        if not hits:
            voids.append(f"h1bw_sc_{arm}_1c_l3x{L3_SLICES}_m{mshr}_r{repl}: no outdir")
            continue
        rec = analyze(hits[-1], arm, mshr, repl, kind)
        rec["wall_hours"] = wall_hours(rec)
        recs.append(rec)

    # G5 is cross-cell (it needs each cell's WB arm), so it runs once here and
    # voids in place before anything is printed or reported.
    apply_engagement_gate(recs)

    prim = [r for r in recs if r["cell_kind"] == "primary"]
    diag = [r for r in recs if r["cell_kind"] == "diag"]
    live = [r for r in prim if r["completed"]]
    dlive = [r for r in diag if r["completed"]]
    by = {(r["arm"], r["declared_l1_mshr"]): r for r in live}
    dby = {r["arm"]: r for r in dlive}
    expected = len(PRIMARY_CELLS)

    print("=" * 92)
    print(f"H1BW SINGLE-CORE MSHR SWEEP -- the certified replacement for tab:h1bw")
    print(f"prereg {PREREG}   (stamp {stamp})")
    print("=" * 92)

    # ---------------- gates ----------------
    print("\nPRE-REGISTERED GATES (fail-closed: a failing cell is VOID, not reported)")
    for r in recs:
        print(f"  {r['run']}  [{r['cell_kind']}]")
        if "g1_status_ok" not in r:
            print(f"    not analyzed -- {r.get('reason')}")
            voids.append(f"{r['run']}: {r['reason']}")
            continue
        mark("G1 instance status == ok", bool(r["g1_status_ok"]),
             f"{r['realized_instances']} instance(s)")
        mark("G2 realized instance/workload count == 1", bool(r["g2_instances"]),
             f"{r['realized_instances']} instances, {r['realized_workloads']} workloads")
        mark("G3 realized LLC == 1 x 5 MiB, 20-way, 1 slice", bool(r["g3_llc"]),
             f"{r['hnf_slices']} slice x {r['llc_bytes_realized']/2**20:.0f} MiB "
             f"assoc {r['l3_assoc_realized']}")
        mark("G4 realized memory model == frozen", bool(r["g4_memory"]),
             f"CXL {r['cxl_bw_ticks_per_byte_realized']:.0f} tk/B "
             f"({r['cxl_bw_ceiling_gbps']:.1f} GB/s) {r['cxl_latency_ns_realized']:.0f} ns "
             f"var {r['cxl_latency_var_realized']:.0f}, DRAM "
             f"{r['dram_bw_ticks_per_byte_realized']:.0f} tk/B "
             f"{r['dram_latency_ns_realized']:.0f} ns, {r['mem_type_realized']}")
        mark("G6 bracketing fired (3 sections, 1 OPEN, 1 CLOSE)", bool(r["g6_bracketing"]),
             f"{r['stats_sections']} sections, {r['window_open_markers']} OPEN, "
             f"{r['window_close_markers']} CLOSE")
        mark("G8 realized L1_MSHR / L1_REPL == declared", bool(r["g8_mshr"]),
             f"TBEs {r['l1_tbes_realized']} repl {r['l1_repl_tbes_realized']} "
             f"vs declared {r['declared_l1_mshr']}/{r['declared_l1_repl']}")
        mark("G9 no local-DRAM traffic (ALL_CXL=1)", bool(r["g9_placement"]),
             "mem_ctrls0 clean" if r["g9_placement"]
             else f"non-zero: {r['mem_ctrls0_nonzero'][:3]}")
        mark("G10 workload identical across arms", bool(r["g10_workload"]),
             f"16 MiB, warmups {WARMUPS}, reps {REPS}, brackets on")
        mark("G11 checksum == 0 over 10 passes", bool(r["g11_checksum"]),
             f"checksum {r.get('checksum')}")
        mark("G12 prefetcher instantiation matches arm", bool(r["g12_prefetchers"]),
             f"{r['prefetcher_sections']} prefetcher sections "
             f"({'>0' if r['arm'] != 'pfoff' else 'exactly 0'} expected)")
        if "g7_window_fidelity" in r:
            mark("G7 window section == guest-reported seconds", bool(r["g7_window_fidelity"]),
                 f"{r['window_simSeconds']*1e3:.6f} ms vs "
                 f"{(r['reported_seconds'] or 0)*1e3:.6f} ms = "
                 f"{(r['window_vs_reported_err'] or 0)*100:.3f}% "
                 f"(tol {G7_WINDOW_SECONDS_TOL*100:.1f}%)")
        if r.get("g5_engaged") is None:
            print(f"  {'G5 declared policy engaged (RE-DERIVED)':56s} n/a   "
                  f"not evaluated (already void)")
        else:
            mark("G5 declared policy engaged (RE-DERIVED)", bool(r["g5_engaged"]),
                 r.get("g5_detail", ""))
        if not r["completed"]:
            voids.append(f"{r['run']}: {r['reason']}")

    if voids:
        print("\nVOID CELLS (reported, never silently dropped):")
        for v in voids:
            print("  " + v)

    if not live:
        print("\n===== VERDICT =====")
        print(f"INCOMPLETE: 0/{expected} primary cells certified; no claim licensed.")
        return 1

    # ---------------- realized configuration ----------------
    print("\nREALIZED CONFIGURATION (read back from config.ini, never requested)")
    print(f"  {'cell':>40s} {'L1 TBE':>7s} {'L1 repl':>8s} {'LLC':>8s} "
          f"{'CXL':>10s} {'pf secs':>8s} {'rnd warn':>9s} {'wall h':>7s}")
    for r in prim + diag:
        if "l1_tbes_realized" not in r:
            continue
        print(f"  {r['run'][:40]:>40s} {str(r['l1_tbes_realized']):>7s} "
              f"{str(r['l1_repl_tbes_realized']):>8s} "
              f"{r['llc_bytes_realized']/2**20:>5.0f} MiB "
              f"{r['cxl_latency_ns_realized']:>4.0f} ns/"
              f"{r['cxl_bw_ticks_per_byte_realized']:.0f}tk "
              f"{r['prefetcher_sections']:>8d} {r['rounding_error_warnings']:>9d} "
              f"{(r['wall_hours'] or 0):>7.2f}")
    print("  'rnd warn' counts `rounding error > tolerance` lines from a5f366456e's")
    print("  abs() guard on SimpleMemory.bandwidth quantization.  Warning-only; NOT a")
    print("  gate (BUILD_PROVENANCE.md: config.ini byte-identical, wb bit-identical).")

    print("\nARM IDENTITY AND POLICY ENGAGEMENT (on WINDOWED counters)")
    print("  config.ini supplies the label; the HNF transition counters supply whether")
    print("  the label did anything.  The primary measure is the un-bypassable")
    print("  clean-eviction residue as a COUNT per core, re-derived for cb290444.")
    print(f"  {'cell':>40s} {'pol':>7s} {'pf':>4s} {'bypasses':>10s} {'E_clean':>8s} "
          f"{'ceil':>7s} {'resid/core':>11s} {'suppr':>7s} {'retry':>7s}")
    for r in prim + diag:
        if "window_bypasses" not in r:
            continue
        s = r.get("fill_suppression_window")
        print(f"  {r['run'][:40]:>40s} {str(r['realized_policy'])[:7]:>7s} "
              f"{r['prefetcher_sections']:>4d} {r['window_bypasses']:>10.0f} "
              f"{(r['window_e_clean'] or 0)*100:>7.2f}% "
              f"{(r['window_e_clean_achievable'] or 0)*100:>6.2f}% "
              f"{r['window_residue_per_core']:>11.0f} "
              f"{('n/a' if s is None else f'{s*100:.1f}%'):>7s} "
              f"{(r['window_hnf_write_retry_frac'] or 0)*100:>6.1f}%")
    print(f"  'ceil' is the achievable E_clean implied by the post-fix residue")
    print(f"  constant ({POSTFIX_RESIDUE_PER_CORE_MAX}/core, H2_BYPASS_FIX_OUTCOME s4): a count, not a fraction.")

    # ---------------- the replacement table ----------------
    print("\n" + "=" * 92)
    print("THE REPLACEMENT tab:h1bw -- both MSHR points, reported separately")
    print("=" * 92)
    print("  Bandwidth is one instance's own 16 MiB x 8 reps over its own measured")
    print("  window.  ONE instance, so there is no window-stagger question and no")
    print("  [R_union, agg_bw_sum] interval: AGGBW_VALIDITY s.Q2 does not apply here.")
    print("  LLC writes are WINDOWED and per measured pass -- the counters and the")
    print("  bandwidth describe the SAME interval, for the first time in this family.")
    for mshr in (16, 48):
        print(f"\n  --- {mshr} MSHRs "
              f"(concurrency ceiling {mshr*LINE_BYTES/(CXL_LATENCY_NS*1e-9)/1e9:.2f} GB/s) ---")
        print(f"  {'arm':>8s} {'bandwidth':>11s} {'cov':>7s} {'half-rng':>9s} "
              f"{'IPC':>6s} {'LLC wr/pass':>12s} {'of 262144':>10s} "
              f"{'LLC wr total':>13s} {'of ceiling':>11s}")
        for arm in ARMS:
            r = by.get((arm, mshr))
            if not r:
                print(f"  {ARM_LABEL[arm]:>8s} {'VOID or missing -- contributes no number':>60s}")
                continue
            print(f"  {ARM_LABEL[arm]:>8s} {r['bandwidth_gbps']:>8.3f} GB/s "
                  f"{(r['cov'] or 0)*100:>6.2f}% {(r['sample_halfrange_pct'] or 0):>8.2f}% "
                  f"{(r['ipc'] or 0):>6.3f} "
                  f"{r['llc_fills_window_per_pass']:>12.0f} "
                  f"{r['llc_fills_window_per_pass_frac']:>9.3f}x "
                  f"{r['llc_fills_total']:>13.0f} "
                  f"{r['frac_of_mshr_ceiling']*100:>10.1f}%")

    # ---------------- structural predictions ----------------
    print("\nPRE-DECLARED STRUCTURAL PREDICTIONS (registered before launch)")
    shits = stot = 0

    def spred(tag, ok, detail):
        nonlocal shits, stot
        stot += 1
        shits += bool(ok)
        mark(tag, ok, detail)

    pf16, pf48 = by.get(("pfoff", 16)), by.get(("pfoff", 48))
    h216, h248 = by.get(("h2", 16)), by.get(("h2", 48))
    wb16, wb48 = by.get(("wb", 16)), by.get(("wb", 48))

    if pf16 and pf48:
        d = abs(pf48["bandwidth_gbps"] - pf16["bandwidth_gbps"]) / pf16["bandwidth_gbps"]
        spred(f"S1 pf-off bandwidth MSHR-insensitive (<= {S1_PFOFF_BW_MSHR_TOL:.0%})",
              d <= S1_PFOFF_BW_MSHR_TOL,
              f"{pf16['bandwidth_gbps']:.3f} -> {pf48['bandwidth_gbps']:.3f} GB/s = "
              f"{d:+.2%}  (archive: 4.60 -> 4.60, exactly flat)")
        a, b = pf16["llc_fills_window_per_pass"], pf48["llc_fills_window_per_pass"]
        d2 = abs(b - a) / a if a else None
        spred(f"S2 pf-off windowed footprint MSHR-insensitive (<= {S2_PFOFF_FILL_MSHR_TOL:.0%})",
              d2 is not None and d2 <= S2_PFOFF_FILL_MSHR_TOL,
              f"{a:.0f} -> {b:.0f} lines/pass = {(d2 or 0):+.3%}  "
              f"(archive whole-program: 289,695 -> 289,698, 3 in 290,000)")
    else:
        spred("S1 pf-off bandwidth MSHR-insensitive", False, "a pf-off cell is void")
        spred("S2 pf-off windowed footprint MSHR-insensitive", False, "a pf-off cell is void")

    if h216 and h248:
        a, b = h216["llc_fills_window_per_pass"], h248["llc_fills_window_per_pass"]
        spred("S3 h2 windowed footprint RISES with MSHR depth",
              b > a, f"{a:.0f} -> {b:.0f} lines/pass = {(b-a)/a if a else 0:+.2%}  "
                     f"(archive: 300,238 -> 353,739 = +17.8%; mechanism is the "
                     f"untagged prefetch tail growing with depth)")
    else:
        spred("S3 h2 windowed footprint RISES with MSHR depth", False, "an h2 cell is void")

    if wb16 and wb48:
        a, b = wb16["llc_fills_window_per_pass"], wb48["llc_fills_window_per_pass"]
        d = abs(b - a) / a if a else None
        spred(f"S4 wb footprint MSHR-insensitive (<= {S4_WB_FILL_MSHR_TOL:.0%})",
              d is not None and d <= S4_WB_FILL_MSHR_TOL,
              f"{a:.0f} -> {b:.0f} lines/pass = {(d or 0):+.3%}  "
              f"(archive: 529,330 -> 529,309, -21)")
    else:
        spred("S4 wb footprint MSHR-insensitive", False, "a wb cell is void")

    for mshr in (16, 48):
        h2r, wbr = by.get(("h2", mshr)), by.get(("wb", mshr))
        if h2r and wbr:
            spred(f"S5 h2 footprint < wb footprint at {mshr} MSHRs",
                  h2r["llc_fills_window_per_pass"] < wbr["llc_fills_window_per_pass"],
                  f"{h2r['llc_fills_window_per_pass']:.0f} vs "
                  f"{wbr['llc_fills_window_per_pass']:.0f} lines/pass "
                  f"(suppression {(h2r.get('fill_suppression_window') or 0)*100:.1f}%)")
        else:
            spred(f"S5 h2 footprint < wb footprint at {mshr} MSHRs", False, "a cell is void")

    if h248 and wb48 and pf48:
        ok = (h248["bandwidth_gbps"] >= wb48["bandwidth_gbps"] > pf48["bandwidth_gbps"])
        spred("S6 ordering h2 >= wb > pf-off at 48 MSHRs", ok,
              f"h2 {h248['bandwidth_gbps']:.3f} / wb {wb48['bandwidth_gbps']:.3f} / "
              f"pf-off {pf48['bandwidth_gbps']:.3f} GB/s")
    else:
        spred("S6 ordering h2 >= wb > pf-off at 48 MSHRs", False, "a 48-MSHR cell is void")

    if h216 and wb16 and pf16:
        order = " > ".join(ARM_LABEL[a] for a in sorted(
            ("wb", "h2", "pfoff"), key=lambda a: -by[(a, 16)]["bandwidth_gbps"]))
        print(f"  {'S7 16-MSHR ordering NOT pre-declared':56s} ----  "
              f"observed {order}  (archive: +H2 > pf-off > WB, i.e. WB BELOW pf-off)")

    # ---------------- windowed footprint bands ----------------
    print("\nWINDOWED FOOTPRINT BANDS (the prediction the archive's column could not make)")
    print(f"  One measured pass reads exactly {LINES_PER_PASS:,} lines.  The HNF is a")
    print("  non-inclusive victim cache with alloc_on_read* all false, so a read never")
    print("  allocates and every data-array write comes from an eviction.")
    for arm in ARMS:
        lo, hi = WINDOW_FILL_BAND[arm]
        for mshr in (16, 48):
            r = by.get((arm, mshr))
            stot += 1
            if not r:
                mark(f"W {ARM_LABEL[arm]}@{mshr} in [{lo:.2f},{hi:.2f}]x", False, "cell void")
                continue
            f = r["llc_fills_window_per_pass_frac"]
            ok = lo <= f <= hi
            shits += ok
            mark(f"W {ARM_LABEL[arm]}@{mshr} in [{lo:.2f},{hi:.2f}]x", ok,
                 f"{r['llc_fills_window_per_pass']:.0f} lines/pass = {f:.4f}x")

    # ---------------- magnitude bands ----------------
    print("\nPRE-DECLARED MAGNITUDE BANDS (wide: the archive's harness is gone)")
    for arm in ARMS:
        for mshr in (16, 48):
            lo, hi = BW_BAND[(arm, mshr)]
            r = by.get((arm, mshr))
            stot += 1
            if not r:
                mark(f"P {ARM_LABEL[arm]}@{mshr} in {lo}-{hi} GB/s", False, "cell void")
                continue
            ok = lo <= r["bandwidth_gbps"] <= hi
            shits += ok
            mark(f"P {ARM_LABEL[arm]}@{mshr} in {lo}-{hi} GB/s", ok,
                 f"{r['bandwidth_gbps']:.3f} GB/s "
                 f"({r['frac_of_mshr_ceiling']*100:.1f}% of the {mshr}-MSHR ceiling)")

    # ---------------- the ratios that ARE licensed, both points, never pooled -----
    print("\nRATIOS -- REPORTED AT EACH MSHR POINT SEPARATELY, NEVER POOLED")
    print("  H1BW_ARM_IDENTITY_2026-09-04.md s.Q3: the appendix quoted WB-over-pf-off")
    print("  as 1.18x from the 48-MSHR row while the 16-MSHR row of the same two rows")
    print("  reads 0.922x -- the sign FLIPS inside the sweep.  No mean, no range and no")
    print("  n is computed over the two points; they are two operating points of one")
    print("  sweep, not two samples of one quantity.")
    print(f"  {'MSHRs':>6s} {'h2/wb':>9s} {'wb/pf-off':>11s} {'h2/pf-off':>11s}")
    for mshr in (16, 48):
        h2r, wbr, pfr = (by.get((a, mshr)) for a in ("h2", "wb", "pfoff"))
        if not (h2r and wbr and pfr):
            print(f"  {mshr:>6d} {'not evaluated: a cell in this row is void':>33s}")
            continue
        print(f"  {mshr:>6d} {h2r['bandwidth_gbps']/wbr['bandwidth_gbps']:>9.4f} "
              f"{wbr['bandwidth_gbps']/pfr['bandwidth_gbps']:>11.4f} "
              f"{h2r['bandwidth_gbps']/pfr['bandwidth_gbps']:>11.4f}")
    print("  h2/pf-off is the prefetcher-contribution measurement at FIXED policy and is")
    print("  the licensed one (AGGBW_VALIDITY: phase-invariant, the safest to quote).")
    print("  wb/pf-off bundles the prefetcher's contribution with the declaration's, in")
    print("  opposite directions, which is why it can come out below 1.0.")

    # ---------------- the one-slice hazard ----------------
    print("\nTHE ONE-SLICE HAZARD (declared in advance; H2_BYPASS_FIX_OUTCOME s5)")
    print("  At 1 slice with 4 CORES the ordering inverted to pf-off > h2 > wb because")
    print("  the 32-entry HNF pool bound, not LLC fills: 65% write-retry, 82.7% HNF")
    print("  occupancy.  With ONE core the pool sees ~a quarter of that demand.")
    print(f"  {'cell':>40s} {'HNF lat':>9s} {'concurrency':>12s} {'of HNF TBE':>11s} "
          f"{'of L1 MSHR':>11s} {'wr retry':>9s}")
    capped = False
    for r in live:
        rf = r["window_hnf_write_retry_frac"] or 0.0
        capped |= rf > HAZARD_RETRY_FRAC_BUFFER_CAPPED
        print(f"  {r['run'][:40]:>40s} {(r['hnf_read_latency_ns'] or 0):>6.1f} ns "
              f"{(r['hnf_concurrency'] or 0):>9.1f} ln "
              f"{(r['hnf_tbe_occupancy_frac'] or 0)*100:>10.1f}% "
              f"{(r['l1_mshr_occupancy_frac'] or 0)*100:>10.1f}% "
              f"{rf*100:>8.1f}%")
    print(f"  predicted: retry < {HAZARD_RETRY_FRAC_EXPECT_BELOW:.0%}, HNF occupancy "
          f"< {HAZARD_HNF_OCCUPANCY_EXPECT_BELOW:.0%}")
    if capped:
        print("  BUFFER-CAPPED: at least one cell retries more than "
              f"{HAZARD_RETRY_FRAC_BUFFER_CAPPED:.0%} of its writes.  Per the")
        print("  pre-registration, an ordering inversion here is a HOME-NODE result, not")
        print("  an H2 result, and the table must report the sweep with that stated.")
    else:
        print("  Not buffer-capped: the one-slice regime of H2_BYPASS_FIX_OUTCOME s5 does")
        print("  not reproduce at one core, so an ordering result here is about H2.")

    # ---------------- windowed CXL-served share ----------------
    print("\nWINDOWED CXL-SERVED SHARE (measured, not bounded -- what bracketing buys)")
    print("  AGGBW_VALIDITY s.Q1 could only bound this from whole-program counters.")
    print("  The complement is the LLC-residency confound of its finding 4: fill_fact")
    print("  writes the whole 16 MiB set immediately before the passes read it.  It is")
    print("  MEASURED here, not removed.  These figures are NOT far-memory bandwidth.")
    print(f"  {'cell':>40s} {'CXL rd/useful B':>16s} {'CXL wr/useful B':>16s} {'LLC-supplied':>13s}")
    for r in live:
        print(f"  {r['run'][:40]:>40s} {r['window_cxl_read_per_useful_byte']:>16.4f} "
              f"{r['window_cxl_write_per_useful_byte']:>16.4f} "
              f"{r['window_llc_supplied_frac']*100:>12.1f}%")

    # ---------------- the archive comparison ----------------
    print("\n" + "=" * 92)
    print("CONFIRMING OR REFUTING THE ARCHIVE'S TWELVE NUMBERS")
    print("=" * 92)
    print("  results/gem5_streaming/REPORT.md s1, the only surviving record of these")
    print("  figures -- a 4,609-byte hand-written summary, no stats.txt, no config.ini,")
    print("  no per-run JSON, runner (knee_sweep.sh) absent from this host.")
    print("  Footprint is compared WHOLE-PROGRAM, because that is what the archive's")
    print("  column is: its WB 529,330 is 2.02x the stream's 262,144 lines, i.e. a warm")
    print("  pass plus a measured pass.")
    print(f"  {'quantity':>22s} {'archive':>10s} {'new':>12s} {'delta':>9s} "
          f"{'within 20%':>11s}")
    repro = tot = 0
    for mshr in (16, 48):
        for arm in ARMS:
            a = ARCHIVE[(arm, mshr)]
            r = by.get((arm, mshr))
            for key, label, fmt in (("bw", "bandwidth", "{:.3f}"),
                                    ("fills", "LLC writes", "{:.0f}")):
                tot += 1
                name = f"{ARM_LABEL[arm]}@{mshr} {label}"
                if not r:
                    print(f"  {name:>22s} {a[key]:>10.3g} {'VOID':>12s} "
                          f"{'--':>9s} {'no':>11s}")
                    continue
                new = r["bandwidth_gbps"] if key == "bw" else r["llc_fills_total"]
                d = (new - a[key]) / a[key]
                ok = abs(d) <= ARCHIVE_REPRODUCE_TOL
                repro += ok
                print(f"  {name:>22s} {a[key]:>10.3g} {fmt.format(new):>12s} "
                      f"{d:>+8.1%} {('YES' if ok else 'no'):>11s}")
    print(f"\n  {repro}/{tot} archived figures reproduced within "
          f"{ARCHIVE_REPRODUCE_TOL:.0%}.")

    # ---- POST-HOC, NON-CERTIFYING: the footprint rows above are confounded.
    # Added 2026-09-04 AFTER the data existed, and labelled as such.  It scores
    # nothing, moves no threshold and changes no verdict; the certified archive
    # test is the whole-program one above, exactly as pre-registered.
    #
    # The confound the pre-registration did not anticipate: whole-program LLC
    # writes scale with the PASS COUNT, and the two campaigns do not share one.
    # The archive's WB figure of 529,330 is 2.019x the stream's 262,144 lines,
    # i.e. warmups+reps == 2.  This campaign runs 10 (warmups 2, reps 8, chosen
    # for the checksum gate and the error bar), so its whole-program column is
    # ~11 passes' worth.  Comparing 10 passes against 2 is a units mismatch and
    # the +443.7% on the WB rows above measures that mismatch, not a physical
    # disagreement.  Bandwidth is a rate and is NOT affected.
    print("\n  POST-HOC (labelled, non-certifying): footprint per measured pass")
    print("  The whole-program comparison above divides by different pass counts:")
    print("  the archive's WB column is 2.019x 262,144 lines, i.e. 2 passes, and")
    print("  this campaign runs 10.  Normalising both to ONE measured pass is the")
    print("  informative comparison.  It is post-hoc and certifies nothing.")
    print(f"  {'quantity':>22s} {'archive/pass':>13s} {'new/pass':>10s} {'delta':>9s}")
    ARCHIVE_PASSES = 2
    for mshr in (16, 48):
        for arm in ARMS:
            r = by.get((arm, mshr))
            a = ARCHIVE.get((arm, mshr))
            if not r or not a:
                continue
            ap = a["fills"] / ARCHIVE_PASSES
            np_ = r["llc_fills_window_per_pass"]
            name = f"{ARM_LABEL[arm]}@{mshr} LLC wr/pass"
            print(f"  {name:>22s} {ap:>13,.0f} {np_:>10,.0f} "
                  f"{(np_ - ap) / ap:>+8.1%}")
    print("  WB reproduces to ~1% at BOTH depths, which corroborates the fill")
    print("  accounting and the geometry: a full pass of 262,144 lines is filled")
    print("  and evicted at either MSHR depth, in both campaigns.  H2 and pf-off")
    print("  do not: this campaign suppresses ~3 orders of magnitude more.  The")
    print("  archive's own rows imply 43% (h2@16) and 33% (h2@48) suppression,")
    print("  which is the PARTIAL engagement signature of the pre-fix binary")
    print("  (H2_BYPASS_COLLAPSE_2026-09-03.md): pre-fix one-slice cells measure")
    print("  0.474 for pfoff and 0.012 for h2, and the archive sits inside that")
    print("  range while the fixed binary reads 0.999.  The most economical")
    print("  reading of the archive's footprint column is therefore that it was")
    print("  taken on a binary whose STREAMING attribute did not survive the")
    print("  retry path.  This is an INFERENCE, not a measurement: the archive's")
    print("  binary is gone and its engagement cannot be measured")
    print("  (H1BW_ARM_IDENTITY_2026-09-04.md s.Q4).")

    structure_ok = all(x for x in (
        pf16 and pf48 and abs(pf48["bandwidth_gbps"] - pf16["bandwidth_gbps"])
        / pf16["bandwidth_gbps"] <= S1_PFOFF_BW_MSHR_TOL,
        h216 and h248 and h248["llc_fills_window_per_pass"] > h216["llc_fills_window_per_pass"],
        h248 and wb48 and pf48 and
        h248["bandwidth_gbps"] >= wb48["bandwidth_gbps"] > pf48["bandwidth_gbps"],
    ))
    print(f"  structural predictions S1/S3/S6 (the load-bearing three): "
          f"{'HOLD' if structure_ok else 'DO NOT ALL HOLD'}")
    if structure_ok and repro >= ARCHIVE_STRUCTURE_MIN_REPRODUCED:
        print("  => OUTCOME A: the archive is corroborated and republished on the new")
        print("     campaign's figures with the new provenance.  F3 closes.")
    elif structure_ok:
        print("  => OUTCOME B (the pre-registered EXPECTED outcome): the archive's")
        print("     ordering and mechanism are corroborated a third time while its twelve")
        print("     magnitudes are SUPERSEDED, not reproduced.  The table carries the new")
        print("     figures.  The archived figures are not repaired, not averaged with the")
        print("     new ones, and not cited again as measurements.  This is NOT a failure")
        print("     of this campaign and must not be reported as one: the archive ran a")
        print("     different binary, a different benchmark from an unidentified tree, a")
        print("     different L2 prefetch degree and (inferred) a different")
        print("     replacement-path depth.")
    else:
        print("  => OUTCOME C or D: a structural prediction failed.  See the")
        print("     pre-registration; the mechanism reading, not merely the magnitudes,")
        print("     is what needs restating, and H1BW_ARM_IDENTITY_2026-09-04.md needs an")
        print("     addendum.")

    # ---------------- diagnostic set D ----------------
    print("\n" + "=" * 92)
    print("DIAGNOSTIC SET D -- L1_REPL = 16 at 48 MSHRs (the archive's presumed default)")
    print("=" * 92)
    print("  Contributes NO number to tab:h1bw.  It exists so that a 48-MSHR magnitude")
    print("  disagreement can be attributed to, or cleared of, replacement-path")
    print("  starvation (CHI_config_8592.py:315-321).")
    if not dlive:
        print("  No diagnostic cell certified.")
    else:
        print(f"  {'arm':>8s} {'repl=48':>11s} {'repl=16':>11s} {'delta':>9s} "
              f"{'E_clean 48':>11s} {'E_clean 16':>11s}")
        for arm in ARMS:
            p, d = by.get((arm, 48)), dby.get(arm)
            if not (p and d):
                print(f"  {ARM_LABEL[arm]:>8s} {'not evaluated (a cell is void)':>44s}")
                continue
            print(f"  {ARM_LABEL[arm]:>8s} {p['bandwidth_gbps']:>8.3f} GB/s "
                  f"{d['bandwidth_gbps']:>8.3f} GB/s "
                  f"{(d['bandwidth_gbps']-p['bandwidth_gbps'])/p['bandwidth_gbps']:>+8.2%} "
                  f"{(p['window_e_clean'] or 0)*100:>10.2f}% "
                  f"{(d['window_e_clean'] or 0)*100:>10.2f}%")
        print("  A material gap in the h2 row implicates replacement-path starvation as")
        print("  an explanation of the archive's 48-MSHR H2 figures.  A null result")
        print("  clears it and leaves the binary, the benchmark and the L2 prefetch")
        print("  degree as the remaining uncontrolled differences -- two of which no")
        print("  longer exist to run against.")

    # ---------------- verdict ----------------
    print("\n===== VERDICT =====")
    if len(live) != expected:
        print(f"INCOMPLETE: {len(live)}/{expected} primary cells certified against all "
              f"twelve gates; tab:h1bw is not licensed to be replaced.")
        rc = 1
    else:
        print(f"COMPLETE: {len(live)}/{expected} primary cells certified against all "
              f"twelve gates.")
        print(f"Pre-declared predictions confirmed: {shits}/{stot}.")
        print(f"Diagnostic cells certified: {len(dlive)}/{len(DIAG_CELLS)}.")
        rc = 0
    print("Every configuration figure above is read back from config.ini and every")
    print("counter from the run's own stats.txt.  A cell whose realized L1_MSHR, LLC")
    print("geometry, memory model, bracketing, placement, checksum, prefetcher")
    print("instantiation or policy engagement did not match its declaration is VOID")
    print("above and contributes no number here.")

    jsonl = DATADIR / (f"h1bw_singlecore_{stamp}.jsonl" if stamp != "*"
                       else "h1bw_singlecore.jsonl")
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    lead = ("run", "cell_kind", "completed", "reason")
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
