#!/usr/bin/env python3
"""H2 engagement, every completed cell of the three 2026-09-04 campaigns.

Reads only stats.txt from completed run directories (DONE.json present).
Read-only; touches nothing under gem5/logs.

Engagement is measured on the population where an HNF fill decision is
actually available: WriteEvictFull / WriteBackFull requests that arrive at the
HNF and find the LLC data entry INVALID (dir state RU / no local copy).  The
HNF in this configuration is a NINE victim cache -- alloc_on_read* are all
False -- so reads never present an allocation opportunity and cannot be
bypassed.  See H2_BYPASS_COLLAPSE_2026-09-03.md.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

LOGROOT = Path("/home/domin/DutyFree/gem5/logs/se_chi")
# Optional argv[1] selects a different run stamp; the default reproduces the
# invocation in H2_BYPASS_COLLAPSE_2026-09-03.md exactly.  Used to read the
# post-fix re-run cells, which carry the stamp "20260904fix".
STAMP = sys.argv[1] if len(sys.argv) > 1 else "20260904"

# (label, ncores, slices, bwtag)
CELLS = [
    ("baseline 4c",    4, 4, None),
    ("baseline 8c",    8, 8, None),
    ("cap t31 4c",     4, 4, "t31"),
    ("cap t16 4c",     4, 4, "t16"),
    ("slice x1 4c",    4, 1, "def"),
]
ARMS = ("wb", "h2", "pfoff")


def rundir(arm, n, slices, bwtag):
    if bwtag is None:
        return LOGROOT / f"h1bw_mc_{arm}_{n}c_{STAMP}"
    return LOGROOT / f"h1bw_mc_{arm}_{n}c_l3x{slices}_bw{bwtag}_{STAMP}"


def load(path):
    st = {}
    with open(path, errors="replace") as f:
        for line in f:
            line = line.split("#")[0].strip()
            p = line.split()
            if len(p) >= 2:
                try:
                    st[p[0]] = float(p[1])
                except ValueError:
                    pass
    return st


def hsum(st, suffix):
    tot = 0.0
    for k, v in st.items():
        if re.fullmatch(r"system\.ruby\.hnf\d*\.cntrl" + re.escape(suffix), k):
            tot += v
    return tot


def hpat(st, pattern):
    """Sum every HNF-scoped key matching `pattern` (applied after the prefix)."""
    tot = 0.0
    for k, v in st.items():
        if re.fullmatch(r"system\.ruby\.hnf\d*\.cntrl\." + pattern, k):
            tot += v
    return tot


def rsum(st, pattern):
    tot = 0.0
    for k, v in st.items():
        if re.fullmatch(r"system\.cpu\d+\." + pattern, k):
            tot += v
    return tot


def metrics(d):
    st = load(d / "stats.txt")
    m = {"run": d.name}
    m["slices"] = len({k.split(".")[2] for k in st
                       if k.startswith("system.ruby.hnf")})
    m["byp"] = hsum(st, ".cache.streamingHnfFillBypasses")
    m["fills"] = hsum(st, ".cache.numDataArrayWrites")
    m["acc"] = (hsum(st, ".cache.m_demand_accesses")
                + hsum(st, ".cache.m_prefetch_accesses"))
    m["hits"] = (hsum(st, ".cache.m_demand_hits")
                 + hsum(st, ".cache.m_prefetch_hits"))
    m["hitfrac"] = m["hits"] / m["acc"] if m["acc"] else None

    # non-HNF instances of the counter must be identically zero (is_HN gate)
    m["byp_nonhnf"] = rsum(st, r"l1[di]|l2\.(cache|sf)\.streamingHnfFillBypasses")
    m["byp_nonhnf"] = sum(v for k, v in st.items()
                          if k.endswith("streamingHnfFillBypasses")
                          and not k.startswith("system.ruby.hnf"))

    for t in ("WriteEvictFull", "WriteBackFull"):
        m[f"{t}_arr"] = hpat(st, rf"inTransLatHist\.{t}::samples")
        m[f"{t}_ret"] = hpat(st, rf"inTransLatHist\.{t}\.retries")
        m[f"{t}_RU_I"] = hpat(st, rf"inTransLatHist\.{t}\.RU\.I\.total")
        m[f"{t}_RU_alloc"] = (hpat(st, rf"inTransLatHist\.{t}\.RU\.UC\.total")
                              + hpat(st, rf"inTransLatHist\.{t}\.RU\.UD\.total"))
    m["ReadShared_arr"] = hpat(st, r"inTransLatHist\.ReadShared::samples")
    m["ReadShared_ret"] = hpat(st, r"inTransLatHist\.ReadShared\.retries")
    m["hnf_evictions"] = hpat(st, r"inTransLatHist\.LocalHN_Eviction::samples")

    # allocation-decision population: write requests that missed in the LLC
    m["decisions"] = sum(m[f"{t}_RU_I"] + m[f"{t}_RU_alloc"]
                         for t in ("WriteEvictFull", "WriteBackFull"))
    m["decisions_clean"] = m["WriteEvictFull_RU_I"] + m["WriteEvictFull_RU_alloc"]
    m["writes_arr"] = m["WriteEvictFull_arr"] + m["WriteBackFull_arr"]
    m["writes_ret"] = m["WriteEvictFull_ret"] + m["WriteBackFull_ret"]

    # requester-side view of the same retries
    m["l2_wr_sent"] = rsum(st, r"l2\.outTransLatHist\.SendWriteBackOrWriteEvict::samples")
    m["l2_wr_ret"] = rsum(st, r"l2\.outTransLatHist\.SendWriteBackOrWriteEvict\.retries")
    m["l2_rd_ret"] = rsum(st, r"l2\.outTransLatHist\.SendReadShared\.retries")
    # second hop: L1D -> L2.  The same omission drops the attribute here too,
    # which leaves the L2's cache_entry.isStreaming false and therefore its
    # later WriteEvictFull unmarked even if that eviction is never retried.
    m["l1d_ret_up"] = sum(
        rsum(st, rf"l1d\.outTransLatHist\.{t}\.retries")
        for t in ("SendReadShared", "SendEvict", "SendWriteBackOrWriteEvict",
                  "SendReadUnique"))
    m["simSeconds"] = st.get("simSeconds")
    return m


def main():
    rows = {}
    for label, n, slices, bwtag in CELLS:
        for arm in ARMS:
            d = rundir(arm, n, slices, bwtag)
            if not (d / "DONE.json").exists():
                continue
            rows[(label, arm)] = metrics(d)

    print("=" * 118)
    print("COUNTER PROVENANCE: streamingHnfFillBypasses == sum of "
          "(WriteEvictFull|WriteBackFull) RU->I transitions at the HNF")
    print("=" * 118)
    print(f"{'run':>44s} {'byp':>10s} {'WEF RU->I':>10s} {'WBF RU->I':>10s} "
          f"{'sum':>10s} {'exact':>6s} {'non-HNF':>8s}")
    for (label, arm), m in rows.items():
        s = m["WriteEvictFull_RU_I"] + m["WriteBackFull_RU_I"]
        print(f"{m['run'][:44]:>44s} {m['byp']:>10.0f} "
              f"{m['WriteEvictFull_RU_I']:>10.0f} {m['WriteBackFull_RU_I']:>10.0f} "
              f"{s:>10.0f} {'YES' if s == m['byp'] else 'NO':>6s} "
              f"{m['byp_nonhnf']:>8.0f}")

    print()
    print("=" * 118)
    print("RETRY IDENTITY: HNF write retries == L2 SendWriteBackOrWriteEvict retries")
    print("(BEFORE the 2026-09-03 fix, prepareRequestRetry() did not copy "
          "isStreaming, so a retried "
          "request reaches the HNF with isStreaming=false)")
    print("=" * 118)
    print(f"{'run':>44s} {'L2 wr sent':>11s} {'L2 wr retry':>12s} {'HNF wr retry':>13s} "
          f"{'exact':>6s} {'retry frac':>11s} {'rd retry':>10s}")
    for (label, arm), m in rows.items():
        print(f"{m['run'][:44]:>44s} {m['l2_wr_sent']:>11.0f} {m['l2_wr_ret']:>12.0f} "
              f"{m['writes_ret']:>13.0f} "
              f"{'YES' if m['l2_wr_ret'] == m['writes_ret'] else 'NO':>6s} "
              f"{m['writes_ret']/m['writes_arr']*100:>10.1f}% {m['l2_rd_ret']:>10.0f}")

    print()
    print("=" * 118)
    print("DEFECT SIGNATURE: bypasses cannot exceed NON-RETRIED clean-evict "
          "arrivals IF the attribute survives only the first send.")
    print("This held in all fifteen pre-fix runs.  On a run made with the "
          "fixed binary it is EXPECTED to read VIOL in both")
    print("columns -- a retried request now keeps its tag, so 'ok' here would "
          "mean the fix did not take.")
    print("=" * 118)
    print(f"{'run':>44s} {'WEF arr':>9s} {'retried':>9s} {'non-retr':>9s} "
          f"{'WEF RU->I':>10s} {'<= ?':>5s} {'RU->alloc':>10s} {'>=retry?':>9s}")
    for (label, arm), m in rows.items():
        nr = m["WriteEvictFull_arr"] - m["WriteEvictFull_ret"]
        print(f"{m['run'][:44]:>44s} {m['WriteEvictFull_arr']:>9.0f} "
              f"{m['WriteEvictFull_ret']:>9.0f} {nr:>9.0f} "
              f"{m['WriteEvictFull_RU_I']:>10.0f} "
              f"{'ok' if m['WriteEvictFull_RU_I'] <= nr else 'VIOL':>5s} "
              f"{m['WriteEvictFull_RU_alloc']:>10.0f} "
              f"{'ok' if m['WriteEvictFull_RU_alloc'] >= m['WriteEvictFull_ret'] else 'VIOL':>9s}")

    print()
    print("=" * 132)
    print("H2 ENGAGEMENT, EVERY COMPLETED CELL")
    print("  E_all   = all bypasses / all write allocation decisions at the HNF")
    print("            (denominator includes dirty writebacks, which STREAMING "
          "cannot tag -> hard LOWER bound)")
    print("  E_clean = WriteEvictFull RU->I / WriteEvictFull RU-state arrivals")
    print("            (matched numerator and denominator, clean evictions only "
          "-- the population where streaming lines live)")
    print("  suppr   = 1 - arm_fills/wb_fills in the SAME cell "
          "(NOT a capacity measure; see fill accounting below)")
    print("=" * 132)
    print(f"{'cell':>13s} {'arm':>6s} {'bypasses':>10s} {'HNF fills':>10s} "
          f"{'fills avoid':>11s} {'suppr':>7s} {'decisions':>10s} {'E_all':>7s} "
          f"{'clean dec':>10s} {'E_clean':>8s} {'wr retry':>9s} {'L1D retry':>10s} "
          f"{'LLC hit':>8s}")
    for label, n, slices, bwtag in CELLS:
        wb = rows.get((label, "wb"))
        for arm in ARMS:
            m = rows.get((label, arm))
            if not m:
                continue
            avoid = (wb["fills"] - m["fills"]) if wb else None
            suppr = (avoid / wb["fills"]) if wb and wb["fills"] else None
            cd = m["decisions_clean"]
            print(f"{label:>13s} {arm:>6s} {m['byp']:>10.0f} {m['fills']:>10.0f} "
                  f"{(avoid if avoid is not None else 0):>11.0f} "
                  f"{(suppr*100 if suppr is not None else 0):>6.1f}% "
                  f"{m['decisions']:>10.0f} {m['byp']/m['decisions']*100:>6.1f}% "
                  f"{cd:>10.0f} "
                  f"{m['WriteEvictFull_RU_I']/cd*100 if cd else 0:>7.1f}% "
                  f"{m['writes_ret']/m['writes_arr']*100:>8.1f}% "
                  f"{m['l1d_ret_up']:>10.0f} "
                  f"{m['hitfrac']*100:>7.1f}%")
        print()

    print("=" * 118)
    print("FILL ACCOUNTING: HNF data-array writes = write arrivals - bypasses "
          "- suppressed rewrites of already-resident streaming lines")
    print("(the CheckCacheFill guard also skips the data write on an LLC HIT, so "
          "'fills avoided' is not all capacity)")
    print("=" * 118)
    print(f"{'run':>44s} {'wr arrivals':>12s} {'fills':>10s} {'deficit':>10s} "
          f"{'bypasses':>10s} {'rewrite-suppr':>14s} {'LLC hit':>8s}")
    for (label, arm), m in rows.items():
        deficit = m["writes_arr"] - m["fills"]
        print(f"{m['run'][:44]:>44s} {m['writes_arr']:>12.0f} {m['fills']:>10.0f} "
              f"{deficit:>10.0f} {m['byp']:>10.0f} {deficit-m['byp']:>14.0f} "
              f"{m['hitfrac']*100:>7.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
