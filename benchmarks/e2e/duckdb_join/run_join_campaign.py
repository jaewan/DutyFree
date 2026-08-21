#!/usr/bin/env python3
"""DuckDB many-to-many join: CAT gate and co-run campaign.

Implements DUCKDB_JOIN_CORUN_PREREGISTRATION.md. Two modes:

  MODE=gate   quiescent, full mask vs one way, per build size -> selects the
              operating point and evaluates the three validity conditions.
  MODE=corun  at the selected build size, the eight arms of section 5,
              rep-interleaved in a fixed seeded order.

Host exclusivity is asserted before every arm via lib/hostguard.py, because the
failure this campaign is repairing was caused by concurrent operators.
"""
import json, os, platform, random, re, subprocess, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
from hostguard import HostGuard, Contention          # noqa: E402

RESCTRL = Path("/sys/fs/resctrl")
DUCKDB = Path(os.environ.get("DUCKDB_BIN", str(Path.home() / "duckdb-1.1.3/duckdb")))
AGG = Path(os.environ.get("AGG_BIN", str(Path.home() / "tmp_dutyfree_exp/bin/aggressor")))
FB = Path(str(Path.home() / "tmp_dutyfree_exp/bin/amd_flushbehind_aggressor"))
OUT = HERE / "artifacts"
RUNTIME = re.compile(r"Run Time \(s\): real ([0-9.]+)")
# Parse the whole RESULT line into key=value pairs rather than matching a fixed
# field order. The two aggressor binaries do not agree on one:
#   RESULT mode=wb_load     threads=1 bw_gbps=5.305 throttle=0
#   RESULT mode=flushbehind threads=1 flush_kb=256 bw_gbps=2.735
# A pattern anchored on "threads=N bw_gbps=" matches the first and not the
# second, so every flush-behind arm would have recorded a null bandwidth --
# and bandwidth is the variable the matched pair is defined by.
AGGRES = re.compile(r"^RESULT (.*)$", re.M)


def parse_agg(txt):
    last = None
    for last in AGGRES.finditer(txt):
        pass
    if not last:
        return {}
    return dict(p.split("=", 1) for p in last.group(1).split() if "=" in p)

# victim cpu, aggressor cores, victim memory node, LLC bytes, ways, per-host builds
# builds admitted by R(N)=40N against max(4*L2, min_mask) < R < 0.5*LLC;
# probe scaled so the streamed, never-reused probe scan is ~12% of LLC rather
# than 25% (mos181) or 500% (moscxl) of it. Amendment A1/A2.
HOSTS = {
    "mos181": dict(vcpu="40", agg=[8, 9, 10, 11, 12, 13, 14, 15], node="2",
                   builds=[500_000, 1_000_000, 2_000_000, 3_000_000, 4_000_000],
                   probe=4_000_000),
    # Package 1, per A4.7: cpu16 and cpus 4-11 are all in package 0, which on
    # THIS host is the socket the CXL device does not hang off. Every node-2
    # access in the orphaned mos182 data therefore crossed the inter-socket
    # link first. Package 1 is L3 domain 1, NUMA node 1, cpus 32-63 (SMT
    # siblings 96-127, none recruited: cpu32's sibling is cpu96, and 33-40 are
    # eight distinct physical cores). This does NOT unblock any mos182 node-2
    # arm -- A5 still requires the latency ladder to be rebuilt there
    # (GLIBC_2.38) and to actually pass from package 1 first.
    "mos182": dict(vcpu="32", agg=[33, 34, 35, 36, 37, 38, 39, 40], node="2",
                   builds=[250_000, 400_000, 500_000, 625_000, 750_000],
                   probe=1_000_000),
    "moscxl": dict(vcpu="8", agg=[9, 10, 11, 12, 13, 14, 15], node="2",
                   builds=[100_000, 125_000, 150_000, 175_000, 200_000],
                   probe=250_000),
}
# arm -> (aggressor mode, threads, memory node) ; None = quiescent
#
# Host-keyed, because the AMD arms are not the Intel arms (Amendment 4). Three
# measured facts force the split, all from victimless characterisation:
#   - PREFETCHNTA holds the entire 16 MiB CCX L3 on Zen4c, so it is a declared
#     negative control there and not a recovery arm;
#   - the L3 domain IS the CCX and the victim owns one of its eight cores, so
#     nothing above -t 7 is expressible;
#   - flush-behind saturates at ~16.1 GB/s while wb_load jumps 12.8 -> 21.7
#     between one and two threads, so no thread count makes wb_load meet
#     flush-behind at its own rate. The matched pair is built the other way
#     round instead: the non-allocating arm is given MORE bandwidth than its
#     allocating partner, which handicaps it.
INTEL_ARMS = {
    "quiescent":    None,
    "WB_sat":       ("wb_load", 8, "2"),
    "WB_match_hi":  ("wb_load", 2, "2"),
    "NTA_sat":      ("wb_prefetchnta", 8, "2"),
    "WB_match_lo":  ("wb_load", 1, "2"),
    "NTA_lo":       ("wb_prefetchnta", 2, "2"),
    "WB_local":     ("wb_load", 8, "0"),
}
# Bandwidths quoted are the victimless characterisation of 2026-08-21 on the
# frozen host (~/amd_char.jsonl), 40 s runs, 22 s settle, 12 s window.
AMD_ARMS = {
    "quiescent":    None,
    "WB_sat":       ("wb_load", 7, "2"),          # 24.72 GB/s, occ 16.00 MiB
    "WB_local":     ("wb_load", 7, "0"),          # local-DRAM placement control
    "NTA_sat":      ("wb_prefetchnta", 7, "2"),   # 24.68, occ 16.00 -- allocates
    "FB0_sat":      ("flushbehind_f0", 7, "2"),   # 24.69, occ 16.00
    "FB256_sat":    ("flushbehind_f256", 7, "2"), # ~15.8, occ ~0.8
    "FB0_match":    ("flushbehind_f0", 1, "2"),   # 12.88, occ 16.00
    "FB256_match":  ("flushbehind_f256", 3, "2"), # 15.39, occ 0.87 -- +20% BW
    "WB_fbmatch":   ("wb_load", 1, "2"),          # 12.82 -- cross-binary check
}
ARMS_BY_HOST = {"mos181": INTEL_ARMS, "mos182": INTEL_ARMS, "moscxl": AMD_ARMS}
ARMS = INTEL_ARMS


def sh(cmd, check=True):
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def sudo(cmd, check=True):
    return sh(["sudo", "-n"] + cmd, check=check)


def slurp(p, default=None):
    try:
        return Path(p).read_text().strip()
    except OSError:
        return default


def cpu_l3(cpu):
    b = Path(f"/sys/devices/system/cpu/cpu{cpu}/cache/index3")
    size = slurp(b / "size")
    return (int(slurp(b / "id")), int(size[:-1]) * 1024,
            int(slurp(b / "ways_of_associativity")))


def l3_domains():
    for line in slurp(RESCTRL / "schemata").splitlines():
        if line.strip().startswith("L3:"):
            return [int(p.split("=")[0]) for p in line.strip()[3:].split(";")]
    raise SystemExit("no L3 line in schemata")


# 1 discarded + N-1 measured; N-1 must stay EVEN, per the GAPBS parity defect.
# Overridable because the joinuniq control emits an eighth of the output rows
# of chain8 at the same build size and its query is 2.3x shorter (0.276 s vs
# 0.64 s at N=2M on mos181). Left at 13 the control's measured window would be
# 3.6 s against chain8's 8.3 s, giving the occupancy sampler a third of the
# samples and a shorter exposure to the settled streamer. The tax is a
# within-configuration ratio of medians, so query count cannot bias it; only
# the measurement quality changes. QUERIES=31 matches the two wall times.
QUERIES = int(os.environ.get("QUERIES", "13"))
assert (QUERIES - 1) % 2 == 0, "measured query count must be even"


def build_db(dbfile, n, chain, probe):
    """Build the tables ONCE into a persistent database.

    Generating inside the measured process makes allocator state and physical
    page placement differ between repetitions and contaminates the first query,
    and the orphaned runs used different generation thread counts on different
    hosts. Generation is single-threaded everywhere so hosts are comparable.
    """
    k = max(1, n // chain)
    if dbfile.exists():
        return k
    sql = (f"SET threads=1;\nSET memory_limit='200GB';\n"
           f"CREATE TABLE b AS SELECT (i%{k})::BIGINT AS k, (i*7)::BIGINT AS payload "
           f"FROM range({n}) t(i);\n"
           f"CREATE TABLE p AS SELECT (hash(i) % {k})::BIGINT AS k "
           f"FROM range({probe}) t(i);\n")
    r = subprocess.run([str(DUCKDB), str(dbfile), "-c", sql], text=True,
                       capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"build failed for n={n}: {r.stderr[-400:]}")
    return k


def write_queries(path):
    path.write_text("SET threads=1;\n.timer on\n"
                    + "SELECT count(*), sum(b.payload) FROM p JOIN b ON p.k=b.k;\n"
                    * QUERIES)


class Sampler(threading.Thread):
    """Occupancy/traffic time series for the victim's monitoring group."""

    def __init__(self, mon):
        super().__init__(daemon=True)
        self.mon, self.rows, self.stop = mon, [], False

    def run(self):
        while not self.stop:
            self.rows.append((time.time(),
                              slurp(self.mon / "llc_occupancy"),
                              slurp(self.mon / "mbm_local_bytes"),
                              slurp(self.mon / "mbm_total_bytes")))
            time.sleep(0.25)


def mbm_span(rows, idx):
    """First and last NUMERIC samples of an MBM series, and how many were not.

    resctrl returns the literal string "Unavailable" for a monitoring file
    whose RMID has not yet been programmed, and on AMD that is reliably true
    of the first sample after a group is created: every mbm_local_first in the
    moscxl gate run was "Unavailable" while every mbm_local_last was numeric.
    Taking rows[0] as the baseline therefore threw away the local-traffic delta
    outright, and would have done the same to mbm_total on a slower start --
    silently, because "Unavailable" is a string and nothing downstream was
    checking. Validity condition 3 is a traffic ratio, so this is not a
    cosmetic field.
    """
    nums = [int(r[idx]) for r in rows if r[idx] is not None and r[idx].isdigit()]
    if not nums:
        return None, None, len(rows)
    return nums[0], nums[-1], len(rows) - len(nums)


def steady(rows, idx):
    """Median over the last 60% of samples: skips the table-build phase."""
    vals = [int(r[idx]) for r in rows if r[idx] is not None]
    if not vals:
        return None
    tail = vals[int(len(vals) * 0.4):]
    return sorted(tail)[len(tail) // 2]


def wait_for_streamer(cfg, agg_group, domain, floor=25.0, cap=60.0, tol=0.05):
    """Block until the streamer's own LLC occupancy is stable; return elapsed.

    A 3 s settle understates the loaded arm: a measured ramp of 123.7 -> 162.4
    -> 190.7 -> 222.6 -> 252.0 ns across repetitions shows the streamer needs
    more than 20 s to reach steady-state occupancy.
    """
    mon = agg_group / "mon_data" / f"mon_L3_{domain:02d}"
    t0, hist = time.time(), []
    while True:
        el = time.time() - t0
        v = slurp(mon / "llc_occupancy")
        if v is not None:
            hist.append(int(v))
        if el >= cap:
            return el
        if el >= floor and len(hist) >= 3:
            w = hist[-3:]
            if max(w) > 0 and (max(w) - min(w)) / max(w) <= tol:
                return el
        time.sleep(1.0)


def run_arm(cfg, group, agg_group, sqlfile, dbfile, arm, mask, domains, domain,
            full_mask):
    """One victim invocation, optionally under an aggressor. Returns a record."""
    agg_proc, agg_out, settle = None, "", None
    spec = ARMS[arm]
    line = "L3:" + ";".join(f"{d}={mask if d == domain else full_mask}" for d in domains)
    sudo(["sh", "-c", f"echo '{line}' > {group}/schemata"])
    sudo(["sh", "-c", f"echo {cfg['vcpu']} > {group}/cpus_list"])
    installed = None
    for ln in slurp(group / "schemata").splitlines():
        if ln.strip().startswith("L3:"):
            installed = dict(p.split("=") for p in ln.strip()[3:].split(";"))
    try:
        if spec:
            mode, nt, node = spec
            # cfg["agg"][:nt] truncates silently: moscxl lists seven aggressor
            # cores, so an Intel-shaped -t 8 arm would pin seven cores while
            # telling the binary to start eight threads, and two threads would
            # share a core. Refuse instead.
            if len(cfg["agg"]) < nt:
                raise SystemExit(f"arm {arm} wants {nt} cores; host lists "
                                 f"{len(cfg['agg'])} ({cfg['agg']})")
            cores = ",".join(str(c) for c in cfg["agg"][:nt])
            if mode.startswith("flushbehind"):
                # flushbehind_f<KiB>; f0 disables flushing and is the
                # within-binary allocating control for f256. -s 512 matches the
                # write-back path: an unmatched per-thread buffer would change
                # whether the stream exceeds the cache, which is the variable.
                dist = mode.split("_f")[1] if "_f" in mode else "256"
                cmd = [str(FB), "-f", dist, "-t", str(nt), "-c", cores, "-N", node,
                       "-s", "512", "-d", "600"]
            else:
                cmd = [str(AGG), "-m", mode, "-t", str(nt), "-c", cores, "-N", node,
                       "-s", "512", "-d", "600"]
            agg_proc = subprocess.Popen(cmd, text=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
            sudo(["sh", "-c",
                  f"echo {','.join(str(c) for c in cfg['agg'][:nt])} "
                  f"> {agg_group}/cpus_list"], check=False)
            settle = wait_for_streamer(cfg, agg_group, domain)
        mon = group / "mon_data" / f"mon_L3_{domain:02d}"
        smp = Sampler(mon)
        smp.start()
        # A5.3: the streamer's OWN occupancy, during the victim query rather
        # than only during settle. A4.1 measured PREFETCHNTA holding the whole
        # CCX with no victim present, which cannot distinguish MRU from LRU
        # insertion -- an idle cache fills either way. Only occupancy under
        # competition can, and nothing sampled it until now.
        asmp = None
        if spec:
            asmp = Sampler(agg_group / "mon_data" / f"mon_L3_{domain:02d}")
            asmp.start()
        t0 = time.time()
        v = subprocess.run(["numactl", f"--membind={cfg['node']}",
                            f"--physcpubind={cfg['vcpu']}", str(DUCKDB),
                            "-readonly", str(dbfile), "-c", f".read {sqlfile}"],
                           text=True, capture_output=True)
        wall = time.time() - t0
        smp.stop = True
        smp.join(timeout=2)
        if asmp:
            asmp.stop = True
            asmp.join(timeout=2)
        times = [float(x) for x in RUNTIME.findall(v.stdout)]
    finally:
        if agg_proc:
            agg_proc.terminate()
            try:
                agg_out = agg_proc.communicate(timeout=10)[0] or ""
            except subprocess.TimeoutExpired:
                agg_proc.kill()
                agg_out = ""
    kv = parse_agg(agg_out)
    loc_f, loc_l, loc_u = mbm_span(smp.rows, 2)
    tot_f, tot_l, tot_u = mbm_span(smp.rows, 3)
    got = installed[str(domain)] if installed else None
    return {
        "arm": arm, "mask_requested": mask, "mask_installed": got,
        "trial_seconds_all": times, "trial_seconds_measured": times[1:],
        "returncode": v.returncode, "wall_seconds": wall,
        "occupancy_bytes_steady": steady(smp.rows, 1),
        "mbm_local_first": loc_f, "mbm_local_last": loc_l,
        "mbm_local_unavailable": loc_u,
        # total, not only local: the hand-rolled campaign found flush-behind
        # moving MORE total controller traffic than write-back while taxing the
        # victim far less, which no bandwidth artifact can produce.
        "mbm_total_first": tot_f, "mbm_total_last": tot_l,
        "mbm_total_unavailable": tot_u,
        # A counter that went backwards means the RMID was reassigned mid-arm;
        # the delta is then meaningless rather than merely noisy.
        "mbm_monotonic": (loc_f is not None and tot_f is not None
                          and loc_l >= loc_f and tot_l >= tot_f),
        "streamer_settle_seconds": settle,
        "occupancy_series": [(round(r[0] - t0, 2), r[1]) for r in smp.rows],
        # Streamer-side, same sampler and same steady() window as the victim's.
        "agg_occupancy_bytes_steady": steady(asmp.rows, 1) if asmp else None,
        "agg_occupancy_series": ([(round(r[0] - t0, 2), r[1]) for r in asmp.rows]
                                 if asmp else None),
        "agg_bw_gbps": float(kv["bw_gbps"]) if "bw_gbps" in kv else None,
        "agg_threads": int(kv["threads"]) if "threads" in kv else None,
        "agg_mode": kv.get("mode"),
        "agg_flush_kb": int(kv["flush_kb"]) if "flush_kb" in kv else None,
        "agg_result_fields": kv,
        "stderr_tail": v.stderr[-400:],
    }


def main():
    host = platform.node().split(".")[0]
    if host not in HOSTS:
        raise SystemExit(f"unsupported host {host}")
    cfg = HOSTS[host]
    global ARMS
    ARMS = ARMS_BY_HOST[host]
    mode = os.environ.get("MODE", "gate")
    chain = int(os.environ.get("CHAIN", "8"))
    reps = int(os.environ.get("REPS", "10"))
    builds = [int(x) for x in os.environ["BUILDS"].split(",")] if os.environ.get("BUILDS") \
        else cfg["builds"]
    probe = int(os.environ.get("PROBE", cfg["probe"]))
    arms = os.environ.get("ARMS", ",".join(ARMS)).split(",")
    if not DUCKDB.is_file():
        raise SystemExit(f"missing {DUCKDB}; run scripts_setup_duckdb.sh")
    domain, l3_bytes, ways = cpu_l3(cfg["vcpu"])
    domains = l3_domains()
    full_mask = slurp(RESCTRL / "info/L3/cbm_mask")
    min_bits = max(int(slurp(RESCTRL / "info/L3/min_cbm_bits")), 1)
    min_mask = format((1 << min_bits) - 1, "x")
    way_bytes = l3_bytes // ways
    OUT.mkdir(parents=True, exist_ok=True)
    # chain8 keeps the bare name the published artifacts already use; any other
    # chain gets its own file. The joinuniq control has the same mode, host and
    # build size as chain8, so a shared file would silently mix two populations
    # that differ only in a field an analysis is free to ignore. It nearly did:
    # two joinuniq records landed in the committed chain8 file before this.
    out = OUT / (f"join_{mode}_{host}.jsonl" if chain == 8
                 else f"join_{mode}_{host}_chain{chain}.jsonl")
    if out.exists():
        for ln in out.read_text().splitlines():
            if ln.strip() and json.loads(ln).get("chain") not in (None, chain):
                raise SystemExit(f"{out} already holds a different chain; refusing to append")
    tag = f"joinchain{chain}"
    print(f"{host}: victim cpu{cfg['vcpu']} L3 domain {domain}, {l3_bytes>>20} MiB / "
          f"{ways} ways = {way_bytes>>20} MiB/way; full={full_mask} min={min_mask}; "
          f"mode={mode} chain={chain} builds={builds} probe={probe} "
          f"(scan {8*probe>>20} MiB = {100.0*8*probe/l3_bytes:.0f}% of LLC)",
          flush=True)

    with HostGuard(f"duckdb_join_{mode}") as guard:
        for n in builds:
            dbfile = Path(f"/tmp/claude-1001/join_{tag}_{n}.duckdb")
            sqlfile = Path(f"/tmp/claude-1001/join_{tag}_queries.sql")
            k = build_db(dbfile, n, chain, probe)
            write_queries(sqlfile)
            order = []
            if mode == "select":
                # Outcome-blind: quiescent full-mask only. No masked and no
                # loaded arm may enter the operating-point selection.
                order = [("full", full_mask, "quiescent", i) for i in range(3)]
            elif mode == "gate":
                for label, mask in (("full", full_mask), ("min", min_mask)):
                    order += [(label, mask, "quiescent", i) for i in range(3)]
            else:
                rng = random.Random(20260821)
                for i in range(reps):
                    a = list(arms)
                    rng.shuffle(a)
                    order += [("full", full_mask, arm, i) for arm in a]
            for label, mask, arm, inv in order:
                gname, aname = f"djoin_{os.getpid()}", f"dagg_{os.getpid()}"
                group, agg_group = RESCTRL / gname, RESCTRL / aname
                sudo(["mkdir", str(group)], check=False)
                sudo(["mkdir", str(agg_group)], check=False)

                def cleanup():
                    sudo(["sh", "-c",
                          f"echo {cfg['vcpu']} > {RESCTRL}/cpus_list"], check=False)
                    sudo(["sh", "-c",
                          f"echo {','.join(str(c) for c in cfg['agg'])} "
                          f"> {RESCTRL}/cpus_list"], check=False)
                    sudo(["rmdir", str(agg_group)], check=False)
                    sudo(["rmdir", str(group)], check=False)

                try:
                    guard.assert_quiescent(max_load=64.0,
                                           expect_groups=(gname, aname))
                except Contention as e:
                    print(f"ABORT arm {arm}: {e}", flush=True)
                    cleanup()
                    raise
                try:
                    rec = run_arm(cfg, group, agg_group, sqlfile, dbfile, arm,
                                  mask, domains, domain, full_mask)
                finally:
                    cleanup()
                occ = rec["occupancy_bytes_steady"]
                eff = bin(int(rec["mask_installed"], 16)).count("1") * way_bytes \
                    if rec["mask_installed"] else None
                outputs = probe * chain
                rec.update(campaign="duckdb_join", host=host, mode=mode, chain=chain,
                           build_rows=n, probe_rows=probe, output_rows=outputs,
                           reused_bytes_model=40 * n, scan_bytes=8 * probe,
                           distinct_keys=k, mask_label=label, invocation=inv,
                           l3_bytes=l3_bytes, l3_ways=ways, way_bytes=way_bytes,
                           l3_domain=domain, effective_bytes=eff,
                           victim_cpu=cfg["vcpu"], victim_node=cfg["node"],
                           # QUERIES is host-tuned (the AMD query is ~23x
                           # shorter than the Intel one) and is not recoverable
                           # from the record otherwise: trial_seconds_all has
                           # the count, but a reader comparing two files needs
                           # to know the measured window was set deliberately.
                           queries=QUERIES,
                           duckdb=str(DUCKDB), timestamp_unix=time.time())
                rec["valid"] = (rec["returncode"] == 0
                                and len(rec["trial_seconds_all"]) == QUERIES)
                med = (sorted(rec["trial_seconds_measured"])[
                    len(rec["trial_seconds_measured"]) // 2]
                    if rec["valid"] else float("nan"))
                rec["per_output_ns"] = (med / outputs * 1e9) if rec["valid"] else None
                with out.open("a") as f:
                    f.write(json.dumps(rec, sort_keys=True) + "\n")
                print(f"  n={n:>9} R={40*n>>20:3d}MiB {label:4s} {arm:12s} inv{inv} "
                      f"eff={(eff or 0)>>20:4d}MiB occ={(occ or 0)>>20:4d}MiB "
                      f"bw={rec['agg_bw_gbps'] or 0:6.2f} settle={rec.get('streamer_settle_seconds') or 0:4.0f}s "
                      f"med={med:8.4f}s {rec['per_output_ns'] or 0:6.2f}ns/out "
                      f"valid={rec['valid']}", flush=True)
                if not rec["valid"]:
                    print(f"    INVALID: rc={rec['returncode']} "
                          f"n_times={len(rec['trial_seconds_all'])} "
                          f"{rec['stderr_tail'][:200]}", flush=True)


if __name__ == "__main__":
    main()
