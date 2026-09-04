#!/usr/bin/env python3
"""Tabulate requested-versus-realized for every tick-quantised parameter.

Consumes the TSV emitted by the temporary _df_quant_trace instrumentation in
src/python/m5/SimObject.py (see enumerate_quantized_params.sh) and reports the
relative quantisation error of every Latency, Clock, Frequency,
MemoryBandwidth and NetworkBandwidth parameter that reaches config.ini.

Error is defined in the domain the parameter is *used* in, which is the domain
the user requested it in:

  Latency / Clock   requested seconds        -> realized ticks / simFreq
  Frequency         requested Hz             -> simFreq / realized ticks
  MemoryBandwidth   requested bytes/s        -> simFreq / realized ticks-per-byte
  NetworkBandwidth  requested bits/s         -> 8 * simFreq / realized ticks-per-byte

Instance indices are collapsed so that the 4/8 identical copies of a per-core
or per-slice parameter appear once, with their multiplicity.
"""

import re
import sys
from collections import defaultdict

SIM_FREQ = 1e12  # ticks per simulated second, from stats.txt


def collapse(path):
    """system.cpu3.l2.prefetcher -> system.cpuN.l2.prefetcher"""
    return re.sub(r"(?<=[a-z])\d+(?=\.|$)", "N", path)


def realized(cls, ini, requested):
    """(realized value in the requested domain, unit) or None if unquantised."""
    ticks = float(ini)
    if cls in ("Latency", "Clock"):
        return (ticks / SIM_FREQ, "s")
    if cls == "Frequency":
        return (SIM_FREQ / ticks, "Hz") if ticks else (0.0, "Hz")
    if cls == "MemoryBandwidth":
        return (SIM_FREQ / ticks, "B/s") if ticks else (0.0, "B/s")
    if cls == "NetworkBandwidth":
        return (8.0 * SIM_FREQ / ticks, "bit/s") if ticks else (0.0, "bit/s")
    raise AssertionError(cls)


def main(paths):
    rows = defaultdict(int)
    for p in paths:
        with open(p) as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue
                path, param, cls, req, ini = line.split("\t")
                rows[(collapse(path), param, cls, req, ini)] += 1

    out = []
    for (path, param, cls, req, ini), n in rows.items():
        unit, _, val = req.partition("=")
        val = float(val)
        if unit == "ticks":
            # already an integer tick count; fromSeconds is never called
            out.append((0.0, path, param, cls, req, ini, n, "as-ticks"))
            continue
        if val == 0.0:
            out.append((0.0, path, param, cls, req, ini, n, "zero"))
            continue
        got, _u = realized(cls, ini, val)
        err = abs(got - val) / val
        out.append((err, path, param, cls, req, ini, n, ""))

    out.sort(key=lambda r: (-r[0], r[1], r[2]))

    print(f"{len(rows)} distinct (path, param, value) rows; ", end="")
    print(f"{sum(rows.values())} parameter instances total")
    print()
    hdr = ("rel err", "n", "class", "path", "param", "requested", "realized")
    print("%-11s %3s %-16s %-34s %-22s %-24s %s" % hdr)
    print("-" * 150)
    for err, path, param, cls, req, ini, n, note in out:
        e = note if note else f"{err * 100:.4f}%"
        print(
            "%-11s %3d %-16s %-34s %-22s %-24s %s"
            % (e, n, cls, path, param, req, ini)
        )

    print()
    print("=== above 0.1% (the frequency_tolerance the fixed guard uses) ===")
    hits = [r for r in out if r[0] > 0.001]
    if not hits:
        print("(none)")
    for err, path, param, cls, req, ini, n, _ in hits:
        print(f"  {err*100:.4f}%  {path}.{param} ({cls})  {req} -> {ini}")
    print()
    print("=== above 1% (material) ===")
    hits = [r for r in out if r[0] > 0.01]
    if not hits:
        print("(none)")
    for err, path, param, cls, req, ini, n, _ in hits:
        print(f"  {err*100:.4f}%  {path}.{param} ({cls})  {req} -> {ini}")


if __name__ == "__main__":
    main(sys.argv[1:])
