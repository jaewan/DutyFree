#!/usr/bin/env python3
"""Blast radius of the non-power-of-two Ruby set-count defect.

gem5's `CacheMemory::init()` computes

    m_cache_num_sets     = (size / assoc) / block_size
    m_cache_num_set_bits = floorLog2(m_cache_num_sets)

and `addressToCacheSet()` selects exactly `m_cache_num_set_bits` address bits.
When `m_cache_num_sets` is not a power of two the surplus sets are allocated
but never indexed, so the cache silently simulates

    reachable_sets = 2 ** floor(log2(configured_sets))
    realized_bytes = reachable_sets * assoc * block_size

with no warning and no assertion.

This walks every `config.ini` under a gem5 run tree --- config.ini is the
binary's own dump of what it actually instantiated, so it is the authoritative
instrument, not the launcher's flags --- and reports every Ruby cache
structure whose set count is not a power of two.  Every Ruby cache is covered,
not just the LLC: L1I, L1D, L2, the HNF LLC and any snoop-filter / directory
structure (`SFDirectory`, `RubyDirectoryMemory`) that is indexed the same way.

Usage:
    audit_nonpow2_sets.py <root> [<root> ...]
    audit_nonpow2_sets.py --geometry SIZE ASSOC [BLOCK]   # one-off arithmetic
"""

import configparser
import json
import os
import sys

# Ruby structures that are CacheMemory (or a subclass of it) and therefore
# index with floorLog2 set bits.  PerfectCacheMemory is deliberately absent: it
# is an unbounded map and has no set index at all.
CACHE_TYPES = {"RubyCache", "SFDirectory", "CacheMemory"}


def geometry(size, assoc, block):
    """Return (configured_sets, reachable_sets, realized_bytes, pow2)."""
    sets = (size // assoc) // block
    if sets < 1:
        return sets, 0, 0, None
    bits = sets.bit_length() - 1          # == floorLog2(sets)
    reachable = 1 << bits
    return sets, reachable, reachable * assoc * block, (reachable == sets)


def scan_config(path):
    """Yield dicts, one per Ruby cache structure in one config.ini."""
    cp = configparser.ConfigParser(strict=False)
    cp.optionxform = str
    try:
        cp.read(path)
    except Exception as exc:                      # noqa: BLE001
        print(f"  !! unreadable {path}: {exc}", file=sys.stderr)
        return

    # RubySystem's block size is the fallback when a cache leaves block_size=0
    # (CacheMemory::setRubySystem picks it up).
    ruby_block = 64
    for sec in cp.sections():
        if cp.get(sec, "type", fallback="") == "RubySystem":
            ruby_block = int(cp.get(sec, "block_size_bytes", fallback=64))
            break

    for sec in cp.sections():
        if cp.get(sec, "type", fallback="") not in CACHE_TYPES:
            continue
        size = int(cp.get(sec, "size", fallback=0))
        assoc = int(cp.get(sec, "assoc", fallback=0))
        block = int(cp.get(sec, "block_size", fallback=0)) or ruby_block
        if not size or not assoc:
            continue
        sets, reach, real, pow2 = geometry(size, assoc, block)
        yield {
            "obj": sec,
            "type": cp.get(sec, "type"),
            "size": size,
            "assoc": assoc,
            "block": block,
            "start_index_bit": int(cp.get(sec, "start_index_bit", fallback=-1)),
            "sets": sets,
            "reachable": reach,
            "realized": real,
            "pow2": pow2,
            "rp": cp.get(sec, "replacement_policy", fallback=""),
        }


def role(objname):
    """Collapse per-core object paths to a role, so 8 cores are one row."""
    tail = objname.split(".")
    for key in ("L1Icache", "L1Dcache", "l1i", "l1d"):
        if key in tail:
            return "L1I" if key.lower().startswith("l1i") else "L1D"
    if "sf" in tail:
        return "HNF snoop filter"
    if any(t.startswith("hnf") for t in tail):
        return "HNF LLC"
    if "l2" in tail or "L2cache" in tail:
        return "L2"
    if any(t.startswith("dir") or t.startswith("snf") for t in tail):
        return "directory"
    if any(t.startswith("rni") or t.startswith("dma") for t in tail):
        return "RNI/DMA"
    if any(t.startswith("mn") for t in tail):
        return "MN"
    return tail[-2] if len(tail) > 1 else objname


def main(argv):
    if argv and argv[0] == "--geometry":
        size, assoc = int(argv[1]), int(argv[2])
        block = int(argv[3]) if len(argv) > 3 else 64
        sets, reach, real, pow2 = geometry(size, assoc, block)
        print(json.dumps({
            "size": size, "assoc": assoc, "block": block,
            "sets": sets, "reachable_sets": reach, "realized_bytes": real,
            "power_of_two": pow2,
            "shortfall_pct": 0.0 if pow2 else 100.0 * (1 - real / size),
        }, indent=2))
        return 0

    roots = argv or ["gem5/logs"]
    configs = []
    for root in roots:
        for dirpath, _dirnames, filenames in os.walk(root):
            if "config.ini" in filenames:
                configs.append(os.path.join(dirpath, "config.ini"))
    configs.sort()
    print(f"# {len(configs)} config.ini under {', '.join(roots)}\n")

    # Deduplicate: a campaign has many run dirs with identical geometry, and
    # the interesting unit is the distinct (role, size, assoc, block) tuple.
    tally = {}
    for cfg in configs:
        run = os.path.dirname(cfg)
        for rec in scan_config(cfg):
            key = (role(rec["obj"]), rec["type"], rec["size"], rec["assoc"],
                   rec["block"], rec["start_index_bit"])
            slot = tally.setdefault(key, {"rec": rec, "runs": set()})
            slot["runs"].add(run)

    hdr = (f"{'role':<18} {'type':<12} {'size':>10} {'as':>3} {'blk':>4} "
           f"{'sib':>3} {'sets':>7} {'reach':>7} {'realized':>10} "
           f"{'short%':>7} {'runs':>5}")
    print(hdr)
    print("-" * len(hdr))
    bad = []
    for key in sorted(tally, key=lambda k: (k[0], k[2], k[3])):
        r = tally[key]["rec"]
        n = len(tally[key]["runs"])
        short = 0.0 if r["pow2"] else 100.0 * (1 - r["realized"] / r["size"])
        flag = "" if r["pow2"] else "   <== NOT POWER OF TWO"
        print(f"{key[0]:<18} {r['type']:<12} {r['size']:>10} {r['assoc']:>3} "
              f"{r['block']:>4} {r['start_index_bit']:>3} {r['sets']:>7} "
              f"{r['reachable']:>7} {r['realized']:>10} {short:>7.2f} "
              f"{n:>5}{flag}")
        if not r["pow2"]:
            bad.append((key, tally[key]))

    print()
    if not bad:
        print("CLEAN: every Ruby cache in every config.ini has a "
              "power-of-two set count.")
    else:
        print(f"AFFECTED: {len(bad)} distinct geometries are not a power of "
              f"two.  Run directories:")
        for key, slot in bad:
            print(f"\n  {key[0]} size={key[2]} assoc={key[3]} "
                  f"({len(slot['runs'])} runs)")
            for run in sorted(slot["runs"]):
                print(f"    {run}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
