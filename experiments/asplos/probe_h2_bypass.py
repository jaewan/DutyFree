#!/usr/bin/env python3
"""Scratch probe: where does streamingHnfFillBypasses come from, and where does
it go at one LLC slice?  Reads only completed run directories (DONE.json
present) under gem5/logs/se_chi.  Read-only.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

LOGROOT = Path("/home/domin/DutyFree/gem5/logs/se_chi")
HNF_RE = re.compile(r"^system\.ruby\.hnf(\d*)\.cntrl\.")


def load_stats(path):
    d = {}
    with open(path, errors="replace") as f:
        for line in f:
            line = line.split("#")[0].strip()
            if not line:
                continue
            p = line.split()
            if len(p) >= 2:
                try:
                    d[p[0]] = float(p[1])
                except ValueError:
                    pass
    return d


def hnf_prefixes(stats):
    out = set()
    for k in stats:
        m = HNF_RE.match(k)
        if m:
            out.add(k[: m.end() - 1])   # system.ruby.hnfN.cntrl
    return sorted(out)


def rnf_prefixes(stats, ncores):
    out = []
    for i in range(ncores):
        for lvl in ("l1d", "l1i", "l2"):
            out.append(f"system.cpu{i}.{lvl}")
    return out


def summarize(outdir):
    st = load_stats(outdir / "stats.txt")
    hn = hnf_prefixes(st)
    ncores = len([k for k in st if re.fullmatch(r"system\.cpu\d+\.numCycles", k)])
    r = {"run": outdir.name, "ncores": ncores, "slices": len(hn)}

    def hsum(suffix):
        return sum(st.get(p + suffix, 0.0) for p in hn)

    r["byp"] = hsum(".cache.streamingHnfFillBypasses")
    r["fills"] = hsum(".cache.numDataArrayWrites")
    r["acc"] = hsum(".cache.m_demand_accesses") + hsum(".cache.m_prefetch_accesses")
    r["hits"] = hsum(".cache.m_demand_hits") + hsum(".cache.m_prefetch_hits")
    r["tagreads"] = hsum(".cache.numTagArrayReads")
    r["tagwrites"] = hsum(".cache.numTagArrayWrites")

    # ---- per-request-type arrivals at the HNF (inTransLatHist.<T>::samples)
    types = set()
    for k in st:
        m = re.match(r"^system\.ruby\.hnf\d*\.cntrl\.inTransLatHist\.([A-Za-z_]+)::samples$", k)
        if m:
            types.add(m.group(1))
    r["in_types"] = {t: hsum(f".inTransLatHist.{t}::samples") for t in sorted(types)}
    r["in_retries"] = {t: hsum(f".inTransLatHist.{t}.retries")
                       for t in sorted(types)
                       if hsum(f".inTransLatHist.{t}.retries")}

    # ---- transition-level: which final state does each write request reach?
    trans = {}
    for k in st:
        m = re.match(r"^system\.ruby\.hnf\d*\.cntrl\.inTransLatHist\."
                     r"(Write\w+|LocalHN_Eviction|SF_Eviction)\.(\w+)\.(\w+)\.total$", k)
        if m:
            key = f"{m.group(1)}:{m.group(2)}->{m.group(3)}"
            trans[key] = trans.get(key, 0.0) + st[k]
    r["write_trans"] = {k: v for k, v in sorted(trans.items())}

    # ---- outbound from HNF
    outt = {}
    for k in st:
        m = re.match(r"^system\.ruby\.hnf\d*\.cntrl\.outTransLatHist\.(\w+)::samples$", k)
        if m:
            outt[m.group(1)] = outt.get(m.group(1), 0.0) + st[k]
    r["out_types"] = outt

    # ---- HNF buffer pressure
    r["hnf_avg_util"] = sum(st.get(p + ".avg_util", 0.0) for p in hn) / max(1, len(hn))
    r["hnf_avg_size"] = sum(st.get(p + ".avg_size", 0.0) for p in hn) / max(1, len(hn))
    r["hnf_avg_reserved"] = sum(st.get(p + ".avg_reserved", 0.0) for p in hn) / max(1, len(hn))
    r["hnf_reqRdy_stall_count"] = hsum(".reqRdy.m_stall_count")
    r["hnf_reqRdy_stall_time"] = hsum(".reqRdy.m_stall_time")
    r["hnf_reqIn_msgs"] = hsum(".reqIn.m_msg_count")

    # ---- RNF-side: eviction pressure and TBE/repl pressure
    def rsum(suffix, levels=("l1d", "l1i", "l2")):
        tot = 0.0
        for i in range(ncores):
            for lvl in levels:
                tot += st.get(f"system.cpu{i}.{lvl}.{suffix}", 0.0)
        return tot

    r["l2_avg_util"] = (sum(st.get(f"system.cpu{i}.l2.avg_util", 0.0)
                            for i in range(ncores)) / max(1, ncores))
    r["l2_avg_size"] = (sum(st.get(f"system.cpu{i}.l2.avg_size", 0.0)
                            for i in range(ncores)) / max(1, ncores))
    r["l1d_avg_util"] = (sum(st.get(f"system.cpu{i}.l1d.avg_util", 0.0)
                             for i in range(ncores)) / max(1, ncores))
    r["l1d_avg_size"] = (sum(st.get(f"system.cpu{i}.l1d.avg_size", 0.0)
                             for i in range(ncores)) / max(1, ncores))
    for q in ("replTriggerQueue", "reqRdy", "triggerQueue", "retryTriggerQueue"):
        r[f"l2_{q}_msgs"] = rsum(f"{q}.m_msg_count", ("l2",))
        r[f"l2_{q}_stall_time"] = rsum(f"{q}.m_stall_time", ("l2",))
        r[f"l1d_{q}_msgs"] = rsum(f"{q}.m_msg_count", ("l1d",))
        r[f"l1d_{q}_stall_time"] = rsum(f"{q}.m_stall_time", ("l1d",))

    # RNF-side outbound request mix (what the L2 actually sends to the HNF)
    for lvl in ("l1d", "l2"):
        mix = {}
        for k in st:
            m = re.match(rf"^system\.cpu(\d+)\.{lvl}\.outTransLatHist\.(\w+)::samples$", k)
            if m:
                mix[m.group(2)] = mix.get(m.group(2), 0.0) + st[k]
        r[f"{lvl}_out_types"] = mix
        rep = {}
        for k in st:
            m = re.match(rf"^system\.cpu(\d+)\.{lvl}\.inTransLatHist\."
                         r"(\w*Eviction\w*|Repl\w*)::samples$", k)
            if m:
                rep[m.group(2)] = rep.get(m.group(2), 0.0) + st[k]
        r[f"{lvl}_evict_types"] = rep

    r["simSeconds"] = st.get("simSeconds")
    r["simInsts"] = st.get("simInsts")
    r["cxl_rd"] = st.get("system.mem_ctrls1.bytesRead::total", 0.0)
    r["cxl_wr"] = st.get("system.mem_ctrls1.bytesWritten::total", 0.0)
    r["dram_rd"] = st.get("system.mem_ctrls0.bytesRead::total", 0.0)
    r["dram_wr"] = st.get("system.mem_ctrls0.bytesWritten::total", 0.0)
    return r


def main(argv):
    pats = argv[1:] or ["h1bw_mc_*_20260904"]
    seen = []
    for pat in pats:
        for d in sorted(LOGROOT.glob(pat)):
            if not (d / "DONE.json").exists() or not (d / "stats.txt").exists():
                continue
            seen.append(summarize(d))
    print(json.dumps(seen, indent=1, sort_keys=False))


if __name__ == "__main__":
    main(sys.argv)
