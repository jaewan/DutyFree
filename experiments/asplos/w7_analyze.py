#!/usr/bin/env python3
"""W7 analysis -- the pre-registered metrics only, and the falsifiers evaluated.

Written before the campaign's data landed, so the analysis cannot be shaped by
the result (S6.6). Reads /tmp/w7/<cell>/stats.txt plus /tmp/w7/<cell>.log.

Pre-registration: W7_PREREGISTRATION_2026-08-23.md sections 3 (P1-P5) and its
2026-08-24 amendments. Metric definitions:

  cyc/access        active_cycles_per_access, from the bench's own JSON.
  DRAM read         mem_ctrls0.bytesRead::total  -- pool 0, 98 ns, the hot table.
  CXL read          mem_ctrls1.bytesRead::total  -- pool 1, 203 ns, the fact stream.
  LLC hit rate      hnf.cntrl.cache.m_demand_hits / (hits + misses).
                    Verified against the 2026-08-15 table: 1345828/(1345828+
                    1165875) = 53.58%, published as 53.6%.
  HNF fills         7th (HNF) column of Cache_Controller.DataArrayWriteOnFill.
                    Verified: 1340360 at the 4 MiB WB arm, as published.  The 7
                    columns are the 7 Cache_Controller instances (2 cores x
                    L1I/L1D/L2, plus the HNF), so the last one is the HNF.
  HNF array writes  hnf.cntrl.cache.numDataArrayWrites -- ALL data-array writes
                    at the HNF, not only fills.  Added 2026-08-24: at A1 the two
                    diverge sharply (1,475,801 writes vs 321,818 fills) because a
                    resident line is updated in place by the thrashing L2's clean
                    evictions, and it is this counter, not fills, that shows H2
                    is active at A1.  See W7.2_A1_SIZING_2026-08-24.md addendum.
  fused GB/s        the bench's own stream_bandwidth_gbps (morsel) or
                    bandwidth_gbps (stream-smoke), measured over the timed
                    region. NOT CXL bytes / simSeconds -- checked 2026-08-24
                    against the 2026-08-15 arms and they are different
                    quantities: simSeconds spans SE startup, table build and
                    warmup, so it reads 0.239 where the bench reports 0.420 at
                    the same 4 MiB WB arm, and 0.48 where the pure-stream smoke
                    reports 4.172. GATE1 section 4's table (4.17 / 4.78 / 0.52)
                    is bench-reported throughout, so P2's >=2.0 GB/s threshold
                    is on this quantity. simSeconds-derived is still printed as
                    `wholeGB/s` for reference; do not mix the two.
  [F9.4] A1's LLC is 20 MiB, not the 32 MiB it asks for.  gem5's CacheMemory
                    computes m_cache_num_sets = (size/assoc)/block = 26,214 for
                    32MiB/20-way, but indexes with m_cache_num_set_bits =
                    floorLog2(26,214) = 14, so only 16,384 sets are reachable:
                    16,384 x 20 x 64 = 20 MiB effective.  A0 is unaffected
                    (5MiB/20 = 4,096 sets exactly), as are both L2s (2MiB/16 =
                    2,048; 512KiB/16 = 512).  Consequence for the reading: A1's
                    8 MiB hot table is 40% of the LLC, not the 25% the
                    pre-registration reasoned about, so A1 is a HARDER cell than
                    intended, not a softer one.  The campaign was already running
                    when this was found and was not disturbed (apparatus rule);
                    the number is therefore reported as measured and labelled.
                    See W4.6_TAB_SENS_ASSOC_AXIS_2026-08-24.md addendum.

  lines in flight   Little's law on the bench figure, the same derivation GATE1
                    section 4 uses: (bytes/s) * 203e-9 / 64. There is no
                    MSHR-occupancy stat in this build -- lqAvgOccupancy exists
                    but is a load-queue ratio, not lines outstanding, and must
                    not be substituted.

  Arm identity for the GATE1 section 4 numbers, established 2026-08-24 and not
  recorded there: all three rows are the **2 MiB** hot-table configuration
  (m22_small_wb 0.5180, m22_bw_wb 4.172, m22_bw_st 4.777). The 4 MiB arm --
  the one the same memo calls "the window" -- is 0.4199 (WB) / 0.4224 (H2).
  The memo's neighbouring "~1.3 lines in flight" is the 4 MiB number
  (0.42 -> 1.33); 0.52 gives 1.65. Both are ~10% of the 5.04 GB/s ceiling, so
  the conclusion is unaffected, but the two figures are different arms.
"""
import json, re, sys, statistics as st
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/w7")
CXL_LAT_S, LINE_B = 203e-9, 64


def stats(d):
    f = d / "stats.txt"
    if not f.exists() or f.stat().st_size == 0:
        return None
    out, fills = {}, None
    # errors="replace" for the same reason t5_analyze.py carries it: gem5 has
    # been observed writing non-UTF-8 into its own output files, and a strict
    # decode here is a crash mode in the analyzer, on the artifact it exists to
    # read.  bench_json() below already did this; stats() did not.  A campaign
    # that took ~20 host-hours should not be unreadable because of one byte.
    for line in f.read_text(errors="replace").splitlines():
        if line.startswith("system.ruby.Cache_Controller.DataArrayWriteOnFill"):
            cols = [c.strip() for c in line.split("|")[1:] if c.strip()]
            if cols:
                fills = int(cols[-1].split()[0])
            continue
        m = re.match(r"^(\S+)\s+([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)(?:\s|$)", line)
        if m:
            out.setdefault(m.group(1), float(m.group(2)))
    out["_hnf_fills"] = fills
    return out


def bench_json(log):
    if not log.exists():
        return {}
    for line in log.read_text(errors="replace").splitlines():
        line = line.strip()
        if line.startswith("{") and '"mode"' in line:
            try:
                return json.loads(line)
            except Exception:
                pass
    return {}


def row(name):
    s = stats(ROOT / name)
    if s is None:
        return None
    j = bench_json(ROOT / f"{name}.log")
    sec = s.get("simSeconds", 0.0)
    cxl = s.get("system.mem_ctrls1.bytesRead::total", 0.0)
    hits = s.get("system.ruby.hnf.cntrl.cache.m_demand_hits", 0.0)
    miss = s.get("system.ruby.hnf.cntrl.cache.m_demand_misses", 0.0)
    # bench-reported, over the timed region -- see the header note
    gbs = j.get("stream_bandwidth_gbps", j.get("bandwidth_gbps", 0.0)) or 0.0
    whole = (cxl / sec / 1e9) if sec else 0.0
    return dict(
        name=name,
        cyc=j.get("active_cycles_per_access"),
        matches=j.get("matches_last_rep"),
        probe_batch=j.get("probe_batch"),
        dram_read=s.get("system.mem_ctrls0.bytesRead::total", 0.0),
        cxl_read=cxl,
        llc_hit=(hits / (hits + miss) * 100) if (hits + miss) else 0.0,
        fills=s["_hnf_fills"],
        hnfwr=s.get("system.ruby.hnf.cntrl.cache.numDataArrayWrites", 0.0),
        gbs=gbs,
        whole=whole,
        lif=gbs * 1e9 * CXL_LAT_S / LINE_B,
        sec=sec,
        host=s.get("hostSeconds", 0.0),
    )


def agg(cells):
    rs = [r for r in (row(c) for c in cells) if r]
    if not rs:
        return None
    out = {"n": len(rs)}
    for k in ("cyc", "dram_read", "cxl_read", "llc_hit", "fills", "hnfwr",
              "gbs", "whole", "lif", "host"):
        v = [r[k] for r in rs if r[k] is not None]
        if v:
            out[k] = st.mean(v)
            out[k + "_sd"] = st.pstdev(v) if len(v) > 1 else 0.0
    out["matches"] = sorted({r["matches"] for r in rs if r["matches"] is not None})
    return out


def main():
    seeds = ["1", "2", "3"]
    grid, allmatch = {}, set()
    for A in ("A0", "A1"):
        for B in ("B0", "B1"):
            for pol in ("wb", "stream"):
                a = agg([f"{A}_{B}_{pol}_s{s}" for s in seeds])
                if a:
                    grid[(A, B, pol)] = a
                    allmatch.update(a["matches"])

    print("== geometry as SIMULATED (not as requested) ==")
    print("  A0  L2 2MiB/16 = 2048 sets   LLC 5MiB/20  = 4096 sets   -> LLC  5 MiB, hot 4 MiB")
    print("  A1  L2 512KiB/16 = 512 sets  LLC 32MiB/20 = 26214 sets  -> LLC 20 MiB, hot 8 MiB  [F9.4]")
    print("  [F9.4] floorLog2(26214)=14 -> 16384 sets reachable -> 16384*20*64 = 20 MiB.")
    print("         A1's hot set is 40% of its LLC, not 25%.  A1 is harder than pre-registered,")
    print("         not softer.  Every A1 number below is at a 20 MiB LLC.")
    print("  [READING RULE, registered before the data in W7.2 'What this does and does not")
    print("   invalidate']  P1 and P3 are evaluated at A1.  Their thresholds were set for")
    print("   32 MiB / 64x L2 / victim at 25%; the realized point is 20 MiB / 40x / 40%.")
    print("   So: a FALSIFIED P1 or P3 here may NOT be reported as falsifying the registered")
    print("   prediction -- it is a null at a different point, and the prediction stays open.")
    print("   A CONFIRMED P1 or P3 is a real positive, but must be stated at the realized")
    print("   point per S5.1, never as confirmation at '32 MiB, 64x'.")
    print("  [P2 is unaffected: it is evaluated at A0/B1 against the A0 reference, and A0's")
    print("   reference is sound -- 5.03 CXL passes against a 4-pass compulsory floor.")
    print("   The A1 smoke references are NOT streaming references: the 16 MiB fact array")
    print("   fits the 20 MiB LLC and is read from CXL exactly once, so their 9.27 GB/s is")
    print("   an on-chip bandwidth.  They are printed below for completeness only.]")
    print()
    print("== cells (mean of completed seeds) ==")
    hdr = f"{'cell':<14}{'n':>2} {'cyc/acc':>9} {'sd':>7} {'LLChit%':>8} {'DRAMrd MB':>10} " \
          f"{'CXLrd MB':>9} {'GB/s':>7} {'wholeBW':>8} {'lines':>6} {'fills':>10} {'hnfWr':>10} {'host h':>7}"
    print(hdr)
    for k in sorted(grid):
        a = grid[k]
        print(f"{'_'.join(k):<14}{a['n']:>2} {a.get('cyc',0):>9.3f} {a.get('cyc_sd',0):>7.3f} "
              f"{a.get('llc_hit',0):>8.2f} {a.get('dram_read',0)/1e6:>10.2f} "
              f"{a.get('cxl_read',0)/1e6:>9.2f} {a.get('gbs',0):>7.3f} {a.get('whole',0):>8.3f} {a.get('lif',0):>6.2f} "
              f"{a.get('fills',0):>10.0f} {a.get('hnfwr',0):>10.0f} "
              f"{a.get('host',0)/3600:>7.2f}")

    print("\n== correctness gate (F12: --check is inert in morsel mode; this IS the gate) ==")
    print(f"distinct matches_last_rep across all completed cells: {sorted(allmatch)}")
    # An empty set is NOT a pass.  Fixed 2026-08-24 after the first run against
    # partial data printed "PASS -- invariant" with zero morsel cells complete:
    # a gate that passes on no evidence is worse than no gate.
    if not allmatch:
        print("**NO DATA -- gate not evaluated** (no completed morsel cell reports matches_last_rep)")
    elif len(allmatch) == 1:
        print("PASS -- invariant")
    else:
        print("**FAIL -- arms are not comparable**")

    print("\n== pre-registered falsifiers ==")

    def gap(A, B):
        w, h = grid.get((A, B, "wb")), grid.get((A, B, "stream"))
        if not w or not h:
            return None
        return (w["cyc"] - h["cyc"]) / w["cyc"] * 100

    # P1 -- O2 isolated at A1/B0 [F9.4: LLC 20 MiB effective, not 32]. Achievable saving vs a one-compulsory-load floor.
    w, h = grid.get(("A1", "B0", "wb")), grid.get(("A1", "B0", "stream"))
    if w and h:
        d_hit = h["llc_hit"] - w["llc_hit"]
        floor = 8 * 1024 * 1024  # one compulsory load of the 8 MiB hot table
        achievable = w["dram_read"] - floor
        realised = (w["dram_read"] - h["dram_read"]) / achievable * 100 if achievable > 0 else float("nan")
        print(f"P1 A1/B0 [LLC 20MiB eff]: LLC hit {w['llc_hit']:.2f} -> {h['llc_hit']:.2f} "
              f"(+{d_hit:.2f} pts, need >=15) | DRAM saving realised {realised:.1f}% "
              f"of achievable (need >=50, falsified <25.8)")
    else:
        print("P1: incomplete")

    # P2 -- O1 isolated at A0/B1. Batching must take.
    h = grid.get(("A0", "B1", "stream"))
    b = grid.get(("A0", "B0", "stream"))
    if h and b:
        print(f"P2 A0/B1: lines in flight {b['lif']:.2f} -> {h['lif']:.2f} (need >=6, "
              f"falsified <3) | fused {b['gbs']:.3f} -> {h['gbs']:.3f} GB/s (need >=2.0)")
    else:
        print("P2: incomplete")

    # P3 -- convergence.
    g = gap("A1", "B1")
    if g is not None:
        v = "CONFIRMED" if g >= 5 else ("FALSIFIED" if g < 2 else "inconclusive (2-5%)")
        print(f"P3 A1/B1 [LLC 20MiB eff]: cyc/acc WB->H2 {g:+.2f}% (need >=5, falsified <2) -- {v}")
    else:
        print("P3: incomplete")

    # P5 -- ordering. P4 needs a CAT run and is not computed here.
    parts = {k: gap(*k) for k in (("A0", "B0"), ("A0", "B1"), ("A1", "B0"), ("A1", "B1"))}
    if all(v is not None for v in parts.values()):
        single = max(parts[("A0", "B1")], parts[("A1", "B0")])
        print(f"P5: A0/B0 {parts[('A0','B0')]:+.2f}%  A0/B1 {parts[('A0','B1')]:+.2f}%  "
              f"A1/B0 {parts[('A1','B0')]:+.2f}%  A1/B1 {parts[('A1','B1')]:+.2f}%  -- "
              f"{'2x2 justified' if parts[('A1','B1')] > single else 'a single knob already suffices; report the simpler experiment'}")
        print("     [F9.4] the two A1 entries are at a 20 MiB LLC, not 32 MiB; see the geometry banner.")
    else:
        print("P5: incomplete")

    print("\nP4 (CAT must recover <2% of the A1/B1 gap) is NOT computed here: it needs a "
          "resctrl arm, which SE mode cannot run. See the memo.")

    print("\n== stream-smoke references (the P2 denominator) ==")
    # Compulsory CXL traffic for the reference: fact_bytes x (1 warmup + reps).
    # If the measured CXL read is at that floor, the array is LLC-resident after
    # the warmup and the number is NOT a streaming ceiling.  See
    # W7.2_A1_SIZING_2026-08-24.md.
    for A in ("A0", "A1"):
        for pol in ("wb", "stream"):
            r = row(f"{A}_SMOKE_{pol}")
            if r:
                j = bench_json(ROOT / f"{A}_SMOKE_{pol}.log")
                fb = j.get("fact_bytes", 0)
                passes = (r["cxl_read"] / fb) if fb else 0.0
                flag = "  <-- one compulsory pass: LLC-RESIDENT, not a streaming reference" \
                       if 0 < passes < 1.5 else ""
                print(f"{A}_SMOKE_{pol:<7} {r['gbs']:.3f} GB/s  lines {r['lif']:.2f}  "
                      f"CXL {r['cxl_read']/1e6:.2f} MB = {passes:.2f} passes over the fact array  "
                      f"host {r['host']/3600:.2f} h{flag}")
                # hnfWr vs fills separates "H2 did nothing" from "H2 did something
                # that did not reach memory".  At A1 the first is false and the
                # second is true; fills alone cannot tell them apart.
                print(f"{'':16} HNF data-array writes {r['hnfwr']:>10.0f}   "
                      f"of which fills {r['fills']:>10.0f} "
                      f"({100*r['fills']/r['hnfwr'] if r['hnfwr'] else 0:.1f}%)")


if __name__ == "__main__":
    main()
