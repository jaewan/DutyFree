#!/usr/bin/env python3
"""RocksDB CAT capacity-sensitivity gate.

Same decision rule and the same resctrl handling as the GAPBS/HNSW gates: the
sysfs/resctrl helpers are imported from the GAPBS runner so the mask floor and
the read-back-the-installed-mask behaviour cannot drift between victims.

No streamer and no aggressor is launched. The only manipulated variable is the
LLC way mask granted to the pinned victim CPU. Per config, db_bench runs at the
full mask and at the minimum legal contiguous mask; the ratio of medians is an
UPPER BOUND on the capacity-mediated co-run tax.

Every config names the RocksDB structure whose reuse it is trying to place in
the band the shared cache acts on (above private L2, below the full LLC).
"""
import importlib.util, json, os, platform, re, shutil, statistics, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve()
RDB = HERE.parents[1]
GAPBS_RUNNER = RDB.parent / "gapbs/scripts/run_cat_sensitivity_gate.py"
_spec = importlib.util.spec_from_file_location("gapbs_gate", GAPBS_RUNNER)
_g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_g)
RESCTRL, CFG = _g.RESCTRL, _g.CFG
sudo, slurp, cpu_l3, l3_domains, freeze_state = (
    _g.sudo, _g.slurp, _g.cpu_l3, _g.l3_domains, _g.freeze_state)

OUT = RDB / "artifacts"
DBROOT = Path(os.environ.get("RDB_DBROOT", "/tmp/rdbgate"))
BIN = os.environ.get("RDB_BIN", "/home/domin/rocksdb-9.11.2/db_bench")
OPRE = re.compile(r"^(\w+)\s+:\s+([0-9.]+)\s+micros/op")

BASE = ["--key_size=16", "--value_size=100", "--threads=1",
        "--compression_type=none", "--histogram=1"]

# name -> (prebuild benchmarks or None, extra flags, measure benchmark,
#          structure whose reuse is under test)
CONFIGS = {
    # Control: reproduce the published null shape -- default 32 MiB block cache,
    # a DB far larger than any LLC, reuse concentrated in a structure smaller
    # than one way.
    "R0_readrandom_default": dict(
        num=5_000_000, prebuild="fillrandom,compact", measure="readrandom",
        reads=1_000_000,
        flags=["--cache_size=33554432", "--block_size=4096", "--bloom_bits=10"],
        structure="32 MiB block cache (below one 16 MiB way)"),
    # Memtable skiplist: InlineSkipList::FindGreaterOrEqual over a ~200 MiB
    # arena. Real pointer chase, no block cache, no page cache, no decode.
    "M_memtable_200M": dict(
        num=1_500_000, prebuild=None, measure="fillrandom,readrandom",
        reads=1_000_000,
        flags=["--write_buffer_size=4294967296", "--max_write_buffer_number=4",
               "--disable_auto_compactions=1",
               "--level0_file_num_compaction_trigger=1000",
               "--level0_slowdown_writes_trigger=1000",
               "--level0_stop_writes_trigger=1000"],
        structure="memtable skiplist arena, ~200 MiB"),
    "M_memtable_400M": dict(
        num=3_000_000, prebuild=None, measure="fillrandom,readrandom",
        reads=1_000_000,
        flags=["--write_buffer_size=8589934592", "--max_write_buffer_number=4",
               "--disable_auto_compactions=1",
               "--level0_file_num_compaction_trigger=1000",
               "--level0_slowdown_writes_trigger=1000",
               "--level0_stop_writes_trigger=1000"],
        structure="memtable skiplist arena, ~400 MiB"),
    "M_memtable_64M": dict(
        num=450_000, prebuild=None, measure="fillrandom,readrandom",
        reads=1_000_000,
        flags=["--write_buffer_size=4294967296", "--max_write_buffer_number=4",
               "--disable_auto_compactions=1",
               "--level0_file_num_compaction_trigger=1000",
               "--level0_slowdown_writes_trigger=1000",
               "--level0_stop_writes_trigger=1000"],
        structure="memtable skiplist arena, ~64 MiB"),
    # mmap reads over a tmpfs-resident, fully compacted, uncompressed DB: the
    # reused structure is the SSTable bytes themselves, no copy into a block
    # cache and no page-cache memcpy on the critical path.
    "T_mmap_tmpfs_200M": dict(
        num=1_500_000, prebuild="fillrandom,compact", measure="readrandom",
        reads=1_000_000,
        flags=["--mmap_read=1", "--cache_size=8388608", "--block_size=4096",
               "--bloom_bits=10"],
        structure="mmap'd SSTable bytes, ~180 MiB"),
    "S_seek_mmap_tmpfs_200M": dict(
        num=1_500_000, prebuild="fillrandom,compact", measure="seekrandom",
        reads=300_000,
        flags=["--mmap_read=1", "--cache_size=8388608", "--block_size=4096",
               "--bloom_bits=10", "--seek_nexts=0"],
        structure="mmap'd index + data blocks, ~180 MiB"),
    # Filter+index pool sized into the band, keys that do not exist: the
    # critical path is a serial chain of one-cache-line bloom probes, one per
    # level, into a filter pool larger than one way.
    # readmissing never reaches a data block: BlockBasedTable::Get consults the
    # filter first and a negative answer returns before the index block is
    # touched. So the ONLY reused structure is the bloom filter pool, whose size
    # depends on key count alone -- value_size=8 keeps the DB small while the
    # filter pool is placed squarely in the band.  bloom_bits=10 is the default.
    "B_readmissing_125M": dict(
        measure_flags=["--disable_auto_compactions=1", "--max_background_jobs=1"],
        num=100_000_000, prebuild="fillrandom,waitforcompaction", measure="readmissing",
        reads=500_000, value_size=8,
        flags=["--cache_size=2147483648",
               "--cache_index_and_filter_blocks=1",
               "--partition_index_and_filters=1",
               "--pin_top_level_index_and_filter=1",
               "--metadata_block_size=4096",
               "--block_size=4096",
               "--bloom_bits=10", "--max_bytes_for_level_base=134217728"],
        structure="bloom filter pool, ~125 MiB (100M keys x 10 bits)"),
    # Same DB as B_readmissing_31M, read through the leanest path RocksDB has:
    # unpartitioned filters (one block-cache lookup per level instead of two)
    # and the lock-free HyperClockCache instead of LRUCache, whose
    # LRUCacheShard::Lookup takes a shard mutex on EVERY block cache hit
    # (cache/lru_cache.cc:430).  Tests whether the per-Get software cost that
    # dilutes the memory tax is irreducible or is block-cache bookkeeping.
    "B_lean_hyperclock_31M": dict(
        db_alias="B_readmissing_31M",
        measure_flags=["--disable_auto_compactions=1", "--max_background_jobs=1"],
        num=25_000_000, prebuild="fillrandom,waitforcompaction",
        measure="readmissing", reads=500_000, value_size=8,
        flags=["--cache_size=2147483648", "--cache_type=auto_hyper_clock_cache",
               "--cache_index_and_filter_blocks=1",
               "--pin_l0_filter_and_index_blocks_in_cache=1",
               "--block_size=4096", "--bloom_bits=10",
               "--max_bytes_for_level_base=134217728"],
        structure="bloom filter pool, ~31 MiB, unpartitioned + HyperClockCache"),
    "B_readmissing_31M": dict(
        measure_flags=["--disable_auto_compactions=1", "--max_background_jobs=1"],
        num=25_000_000, prebuild="fillrandom,waitforcompaction", measure="readmissing",
        reads=500_000, value_size=8,
        flags=["--cache_size=2147483648",
               "--cache_index_and_filter_blocks=1",
               "--partition_index_and_filters=1",
               "--pin_top_level_index_and_filter=1",
               "--metadata_block_size=4096",
               "--block_size=4096",
               "--bloom_bits=10", "--max_bytes_for_level_base=134217728"],
        structure="bloom filter pool, ~31 MiB (25M keys x 10 bits)"),
}


def db_flags(cfg, path, measure=False):
    extra = cfg.get("measure_flags", []) if measure else []
    base = [f for f in BASE
            if not (cfg.get("value_size") and f.startswith("--value_size"))]
    if cfg.get("value_size"):
        base.append(f"--value_size={cfg['value_size']}")
    return [f"--db={path}", f"--num={cfg['num']}"] + base + cfg["flags"] + extra


def run(cmd, cwd=None):
    return subprocess.run(cmd, text=True, capture_output=True, cwd=cwd)


def parse(text, bench):
    """Take the last reported line for the measured benchmark."""
    got = None
    for ln in text.splitlines():
        m = OPRE.match(ln.strip())
        if m and m.group(1) == bench:
            got = float(m.group(2))
    return got


def main():
    host = platform.node().split(".")[0]
    cpu = os.environ.get("RDB_CPU") or CFG[host]
    names = os.environ.get("RDB_CONFIGS", ",".join(CONFIGS)).split(",")
    invocations = int(os.environ.get("RDB_INVOCATIONS", "5"))
    domain, l3_bytes, ways, shared = cpu_l3(cpu)
    domains = l3_domains()
    full_mask = slurp(RESCTRL / "info/L3/cbm_mask")
    min_bits = max(int(slurp(RESCTRL / "info/L3/min_cbm_bits")), 1)
    min_mask = format((1 << min_bits) - 1, "x")
    way_bytes = l3_bytes // ways
    frozen = freeze_state(cpu)
    binver = run([BIN, "--version"]).stdout.strip()
    asserts = "Assertions are enabled" in run(
        [BIN, "--benchmarks=readrandom", "--num=100", "--reads=1",
         f"--db={DBROOT}/probe"]).stdout
    DBROOT.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"rocksdb_cat_gate_{host}.jsonl"
    print(f"{BIN}: {binver} assertions={asserts}")
    print(f"{host}: cpu{cpu} L3 domain {domain}, {l3_bytes>>20} MiB / {ways} ways "
          f"= {way_bytes>>20} MiB per way; full={full_mask} min={min_mask}",
          flush=True)

    for name in names:
        cfg = CONFIGS[name]
        path = DBROOT / cfg.get("db_alias", name)
        prebuilt_bytes = None
        if cfg["prebuild"]:
            if not (path / "CURRENT").is_file():
                shutil.rmtree(path, ignore_errors=True)
                t0 = time.time()
                cmd = ([ "taskset", "-c", cpu, BIN,
                        f"--benchmarks={cfg['prebuild']}", "--use_existing_db=0"]
                       + db_flags(cfg, path))
                r = run(cmd)
                if r.returncode != 0:
                    print(f"{name}: PREBUILD FAILED\n{r.stdout[-2000:]}{r.stderr[-2000:]}")
                    continue
                print(f"{name}: prebuilt in {time.time()-t0:.0f}s", flush=True)
            prebuilt_bytes = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        res = {}
        for label, mask in (("full", full_mask), ("min", min_mask)):
            samples, occ = [], []
            for inv in range(invocations):
                if not cfg["prebuild"]:
                    shutil.rmtree(path, ignore_errors=True)
                group = RESCTRL / f"rdb_{os.getpid()}_{label}_{inv}"
                sudo(["mkdir", str(group)])
                try:
                    line = "L3:" + ";".join(
                        f"{d}={mask if d == domain else full_mask}" for d in domains)
                    sudo(["sh", "-c", f"echo '{line}' > {group}/schemata"])
                    sudo(["sh", "-c", f"echo {cpu} > {group}/cpus_list"])
                    installed = None
                    for ln in slurp(group / "schemata").splitlines():
                        if ln.strip().startswith("L3:"):
                            installed = dict(p.split("=") for p in ln.strip()[3:].split(";"))
                    got = installed[str(domain)]
                    eff = bin(int(got, 16)).count("1") * way_bytes
                    cmd = (["taskset", "-c", cpu, BIN,
                            f"--benchmarks={cfg['measure']}",
                            f"--reads={cfg['reads']}",
                            f"--use_existing_db={0 if not cfg['prebuild'] else 1}"]
                           + db_flags(cfg, path, measure=True))
                    t0 = time.time()
                    r = run(cmd)
                    mon = group / "mon_data" / f"mon_L3_{domain:02d}"
                    o = slurp(mon / "llc_occupancy")
                    us = parse(r.stdout, cfg["measure"].split(",")[-1])
                    rec = {"campaign": "rocksdb_cat_sensitivity_gate", "host": host,
                           "config": name, "structure": cfg["structure"],
                           "bin": BIN, "bin_version": binver,
                           "assertions_enabled": asserts,
                           "mask_label": label, "invocation": inv, "command": cmd,
                           "cpu_requested": cpu, "l3_domain": domain,
                           "l3_bytes": l3_bytes, "l3_ways": ways,
                           "way_bytes": way_bytes, "shared_cpu_list": shared,
                           "mask_requested": mask, "mask_installed": got,
                           "effective_bytes": eff, "cbm_mask_full": full_mask,
                           "schemata_readback": slurp(group / "schemata"),
                           "returncode": r.returncode, "micros_per_op": us,
                           "llc_occupancy_end": o, "db_bytes": prebuilt_bytes,
                           "freeze_state": frozen,
                           "wall_seconds": time.time() - t0,
                           "stdout_tail": r.stdout[-4000:],
                           "timestamp_unix": time.time()}
                    rec["valid"] = r.returncode == 0 and us is not None
                    with out.open("a") as f:
                        f.write(json.dumps(rec, sort_keys=True) + "\n")
                    if rec["valid"]:
                        samples.append(us)
                        if o:
                            occ.append(int(o))
                    print(f"  {name} {label:4s} inv{inv} eff={eff>>20:4d}MiB "
                          f"{us} us/op occ={int(o)>>20 if o else '?'}MiB", flush=True)
                finally:
                    sudo(["sh", "-c", f"echo {cpu} > {RESCTRL}/cpus_list"], check=False)
                    sudo(["rmdir", str(group)], check=False)
            res[label] = samples
            if samples:
                m = statistics.median(samples)
                cv = (statistics.stdev(samples)/statistics.mean(samples)*100
                      if len(samples) > 1 else 0.0)
                print(f"  -> {name} {label}: median {m:.4f} us/op CoV {cv:.2f}% "
                      f"occ_med={statistics.median(occ)>>20 if occ else '?'}MiB",
                      flush=True)
        if res.get("full") and res.get("min"):
            ratio = statistics.median(res["min"]) / statistics.median(res["full"])
            print(f"== {name}: RATIO {ratio:.3f}  "
                  f"{'PASS' if ratio >= 2.0 else 'fail'}  "
                  f"[{cfg['structure']}]", flush=True)


if __name__ == "__main__":
    main()
