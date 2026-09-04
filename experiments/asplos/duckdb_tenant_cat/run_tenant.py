#!/usr/bin/env python3
"""DuckDB tenant-CAT runner (named-engine join on silicon).

Pre-registration: experiments/asplos/DUCKDB_TENANT_CAT_PREREG_2026-09-01.md
STREAMING / nta / flush-behind are not measured.  Host mos182 / c4 only.

One JSONL record per (arm, rep).  Existing OUT is refused (A6.19).
`--smoke` is SQL+JSON apparatus on any host and is not a result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import statistics as st
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "experiments", "lib"))
sys.path.insert(0, HERE)

from dutyfree import resctrl  # noqa: E402
from tenant_gates import (  # noqa: E402
    CAMPAIGN, LOAD_MAX, MEASURED_QUERIES, WANT_CHAIN, WANT_N,
    WANT_PROBE, WARMUP_QUERIES, checksum_of, clos_check, geom_check, host_check,
    identity_check, idle_check, live_check, mask_check, mask_held_check,
    parse_duckdb_output, parse_victim_cycles, pid_check, self_test,
    threads_check, version_check,
)

CLOS = os.path.join(ROOT, "benchmarks", "e2e", "hash_join", "scripts",
                    "resctrl_clos.sh")
MON_GROUP = "/sys/fs/resctrl/mon_groups/df_tenant"
TCPU_DEFAULT = 4
VCPU_DEFAULT = 6
SMOKE_N = 1024
SMOKE_PROBE = 256


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def comms_now() -> list[str]:
    out = []
    try:
        pids = os.listdir("/proc")
    except OSError:
        return out
    for name in pids:
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/comm") as f:
                out.append(f.read().strip())
        except OSError:
            pass
    return out


def load1() -> float:
    return float(open("/proc/loadavg").read().split()[0])


def host_idle() -> tuple[bool, str]:
    return idle_check(load1(), comms_now(), LOAD_MAX)


def sudo_sh(cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["sudo", "-n", "bash", "-c", cmd],
                          capture_output=True, text=True)


def sudo_clos(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["sudo", "-n", "bash", CLOS, *args],
                          capture_output=True, text=True)


def teardown() -> None:
    sudo_sh(f"rmdir {MON_GROUP} 2>/dev/null || true")
    sudo_clos("teardown")


def setup_tenant(ways: int, tcpu: int) -> None:
    r = sudo_clos("setup_b", str(ways), str(tcpu))
    if r.returncode != 0:
        raise RuntimeError(f"setup_b failed: {r.stderr or r.stdout}")


def setup_mon_group() -> None:
    r = sudo_sh(f"mkdir {MON_GROUP}")
    if r.returncode != 0 and "File exists" not in (r.stderr or ""):
        raise RuntimeError(f"mon group failed: {r.stderr or r.stdout}")


def write_pid(group: str, pid: int) -> bool:
    r = sudo_sh(f"echo {int(pid)} > {group}/tasks")
    return r.returncode == 0


def pid_in_group(group: str, pid: int) -> bool:
    try:
        txt = open(os.path.join(group, "tasks")).read()
    except OSError:
        return False
    return str(int(pid)) in txt.split()


def clos_cpus(group: str) -> str:
    p = os.path.join("/sys/fs/resctrl", group, "cpus_list")
    try:
        return open(p).read().strip()
    except OSError:
        return ""


def snapshot_clos(ways: int) -> dict:
    present = os.path.isdir("/sys/fs/resctrl/clos_b")
    if not present:
        return dict(mask_got_after=None, clos_cpus_after="",
                    clos_b_present_after=False)
    return dict(mask_got_after=resctrl.schemata_l3("/sys/fs/resctrl/clos_b"),
                clos_cpus_after=clos_cpus("clos_b"),
                clos_b_present_after=True)


def percentile(xs: list[float], p: float) -> float | None:
    xs = sorted(xs)
    if not xs:
        return None
    if len(xs) == 1:
        return float(xs[0])
    k = (len(xs) - 1) * p
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return float(xs[f])
    return float(xs[f] + (xs[c] - xs[f]) * (k - f))


def victim_stats(text: str) -> tuple[float | None, int, float | None]:
    v = parse_victim_cycles(text)
    if not v:
        return None, 0, None
    return float(st.median(v)), len(v), percentile(v, 0.99)


def wait_marker(path: str, marker: str, proc: subprocess.Popen,
                timeout: float) -> str:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            txt = open(path, errors="replace").read()
        except OSError:
            txt = ""
        if marker in txt:
            return txt
        if proc.poll() is not None:
            return open(path, errors="replace").read() if os.path.exists(path) else ""
        time.sleep(0.05)
    raise TimeoutError(f"timeout waiting for {marker} in {path}")


def duckdb_version(bin_path: str) -> str:
    r = subprocess.run([bin_path, "--version"], capture_output=True, text=True)
    return (r.stdout or r.stderr or "").strip()


def measure_sql(n_warmup: int, n_meas: int) -> str:
    q = "SELECT count(*), sum(b.payload) FROM p JOIN b ON p.k=b.k;\n"
    parts = ["SET threads=1;\n.timer on\n"]
    for _ in range(n_warmup):
        parts.append(q)
    parts.append(".timer off\nSELECT 'DUCKDB_MEASURE_BEGIN' AS marker;\n.timer on\n")
    for _ in range(n_meas):
        parts.append(q)
    parts.append(".timer off\nSELECT 'DUCKDB_MEASURE_END' AS marker;\n")
    return "".join(parts)


def build_db(duckdb: str, dbfile: str, n: int, chain: int, probe: int,
             mem_node: int, use_numactl: bool) -> int:
    k = max(1, n // chain)
    meta_path = dbfile + ".meta.json"
    meta = dict(n=n, chain=chain, probe=probe, k=k)
    if os.path.exists(dbfile):
        if os.path.exists(meta_path):
            got = json.loads(open(meta_path).read())
            if any(got.get(x) != meta[x] for x in ("n", "chain", "probe", "k")):
                raise SystemExit(f"FAIL {dbfile} meta mismatch {got} vs {meta}")
        return k
    os.makedirs(os.path.dirname(dbfile) or ".", exist_ok=True)
    sql = (f"SET threads=1;\nSET memory_limit='200GB';\n"
           f"CREATE TABLE b AS SELECT (i%{k})::BIGINT AS k, (i*7)::BIGINT AS payload "
           f"FROM range({n}) t(i);\n"
           f"CREATE TABLE p AS SELECT (hash(i) % {k})::BIGINT AS k "
           f"FROM range({probe}) t(i);\n")
    cmd = [duckdb, dbfile, "-c", sql]
    if use_numactl:
        cmd = ["numactl", f"--membind={mem_node}"] + cmd
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"build failed n={n} chain={chain}: {r.stderr[-400:]}")
    with open(meta_path, "w") as fh:
        json.dump(meta, fh)
        fh.write("\n")
    return k


class OccupancySampler(threading.Thread):
    def __init__(self, group: str, domain: str = "00"):
        super().__init__(daemon=True)
        self.group, self.domain = group, domain
        self.rows: list[tuple[float, int | None]] = []
        self.stop = False

    def run(self) -> None:
        while not self.stop:
            self.rows.append((time.time(),
                              resctrl.llc_occupancy(self.group, self.domain)))
            time.sleep(0.25)


def steady_occ(rows: list[tuple[float, int | None]], t_begin: float | None) -> int | None:
    vals = []
    for t, v in rows:
        if v is None:
            continue
        if t_begin is not None and t < t_begin:
            continue
        vals.append(int(v))
    if not vals:
        return None
    tail = vals[int(len(vals) * 0.4):] or vals
    return int(st.median(tail))


def arm_list(calib: bool, joinuniq: bool) -> list[tuple[str, int, int]]:
    """(arm, ways, chain)."""
    if calib:
        arms = [("qui", 0, WANT_CHAIN), ("wb", 0, WANT_CHAIN),
                ("cat04", 4, WANT_CHAIN), ("cat15", 15, WANT_CHAIN)]
        if joinuniq:
            arms.append(("wb_joinuniq", 0, 1))
        return arms
    arms = [("qui", 0, WANT_CHAIN), ("wb", 0, WANT_CHAIN)]
    if joinuniq:
        arms.append(("wb_joinuniq", 0, 1))
    for w in range(1, 16):
        arms.append((f"cat{w:02d}", w, WANT_CHAIN))
    return arms


def run_one(arm: str, ways: int, chain: int, args, sha_ddb: str, sha_vic: str,
            out_dir: str, dbfile: str, sqlfile: str, sql_text: str,
            ref_matches: int | None) -> dict:
    ok, why = host_idle() if not args.smoke else (True, "smoke")
    rec = {
        "campaign": CAMPAIGN,
        "arm": arm, "ways": ways, "chain": chain,
        "n": args.n, "probe": args.probe,
        "r_bytes": 40 * args.n,
        "host": os.uname().nodename,
        "load1": load1(), "idle_ok": ok, "idle_why": why,
        "tenant_cpu": args.tcpu, "victim_cpu": args.vcpu,
        "mem_node": args.mnode,
        "sha_duckdb": sha_ddb, "sha_victim": sha_vic,
        "duckdb_version": args._ddb_ver,
        "sql_sha256": hashlib.sha256(sql_text.encode()).hexdigest(),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "policy": "wb", "join_path": "duckdb_join",
        "flush_distance": 0, "pf_distance": 0,
        "streaming": False,
    }
    if not ok:
        rec["status"] = "skip_busy"
        rec["victim_cyc_per_load"] = None
        rec["query_seconds"] = None
        return rec

    iok, iwhy = identity_check(arm)
    rec["identity_ok"], rec["identity_why"] = iok, iwhy
    vok, vwhy = version_check(args._ddb_ver)
    rec["version_ok"], rec["version_why"] = vok, vwhy
    tok, twhy = threads_check(sql_text)
    rec["threads_ok"], rec["threads_why"] = tok, twhy
    if not args.smoke:
        gok, gwhy = geom_check(args.n, args.probe, chain)
    else:
        gok, gwhy = True, "smoke"
    rec["geom_ok"], rec["geom_why"] = gok, gwhy
    if not iok or not vok or not tok or not gok:
        rec["status"] = "gate_fail"
        rec["victim_cyc_per_load"] = None
        rec["query_seconds"] = None
        return rec

    clos_group = None
    mask_got = None
    occ_group = None
    if ways > 0:
        setup_tenant(ways, args.tcpu)
        clos_group = "clos_b"
        occ_group = "/sys/fs/resctrl/clos_b"
        mask_got = resctrl.schemata_l3("/sys/fs/resctrl/clos_b")
        rec["clos_cpus"] = clos_cpus("clos_b")
        rec["clos_group"] = clos_group
        mok, mwhy = mask_check(mask_got, ways)
        cok, cwhy = clos_check(rec["clos_cpus"], args.tcpu, args.vcpu)
        rec["mask_got"] = mask_got
        rec["mask_want"] = hex((1 << ways) - 1)
        rec["mask_ok"] = mok
        rec["mask_why"] = mwhy
        rec["clos_ok"] = cok
        rec["clos_why"] = cwhy
        if not mok or not cok:
            rec["status"] = "gate_fail"
            teardown()
            rec["victim_cyc_per_load"] = None
            rec["query_seconds"] = None
            return rec
    else:
        teardown()
        rec["clos_group"] = None
        rec["clos_cpus"] = ""
        rec["mask_got"] = None
        rec["mask_want"] = None
        rec["mask_ok"], rec["mask_why"] = mask_check(None, 0)
        rec["clos_ok"] = True
        rec["clos_why"] = "no clos"
        if arm != "qui":
            try:
                setup_mon_group()
                occ_group = MON_GROUP
            except RuntimeError as e:
                rec["status"] = "gate_fail"
                rec["error"] = str(e)
                rec["victim_cyc_per_load"] = None
                rec["query_seconds"] = None
                return rec

    tag = f"{arm}_r{args._rep}"
    t_out = os.path.join(out_dir, f"{tag}.tenant.out")
    t_err = os.path.join(out_dir, f"{tag}.tenant.err")
    v_out = os.path.join(out_dir, f"{tag}.victim.out")
    v_err = os.path.join(out_dir, f"{tag}.victim.err")

    vproc = None
    tproc = None
    sampler = None
    captured = False
    t_begin = None

    def capture_mask_after() -> None:
        nonlocal captured
        if captured:
            return
        rec.update(snapshot_clos(ways))
        captured = True
        okh, whyh = mask_held_check(
            rec.get("mask_got"), rec.get("mask_got_after"), ways,
            rec.get("clos_cpus_after"), rec.get("tenant_cpu"),
            rec.get("victim_cpu"), rec.get("clos_b_present_after"))
        rec["mask_held_ok"] = okh
        rec["mask_held_why"] = whyh
        if rec.get("status") == "ok" and not okh:
            rec["status"] = "gate_fail"

    try:
        if arm == "qui":
            vcmd = [args.victim, "--cpu", str(args.vcpu), "--node", "0",
                    "--wss", str(args.vwss), "--trials", str(args.vtrials_quiet),
                    "--run-sec", str(args.vsec)]
            with open(v_out, "w") as vo, open(v_err, "w") as ve:
                vproc = subprocess.Popen(vcmd, stdout=vo, stderr=ve)
            vproc.wait(timeout=args.vtrials_quiet + 30)
            vtxt = open(v_out, errors="replace").read()
            vc, vn, vp99 = victim_stats(vtxt)
            rec.update(victim_cyc_per_load=vc, victim_n_trials=vn,
                       victim_p99=vp99, query_seconds=None, matches=None,
                       occupancy_bytes_steady=None, status="ok")
            if vc is None or vn < 1:
                rec["status"] = "no_victim"
            return rec

        tcmd = ["stdbuf", "-oL", "-eL"]
        if args.numactl:
            tcmd += ["numactl", f"--physcpubind={args.tcpu}",
                     f"--membind={args.mnode}"]
        tcmd += [args.duckdb, "-json", "-readonly", dbfile, "-c",
                 f".read {sqlfile}"]
        rec["tenant_cmd"] = tcmd
        with open(t_out, "w") as to, open(t_err, "w") as te:
            tproc = subprocess.Popen(tcmd, stdout=to, stderr=te)
        rec["tenant_pid"] = tproc.pid
        if ways > 0:
            rec["pid_in_clos"] = write_pid("/sys/fs/resctrl/clos_b", tproc.pid) \
                and pid_in_group("/sys/fs/resctrl/clos_b", tproc.pid)
        elif occ_group == MON_GROUP:
            rec["pid_in_clos"] = False
            rec["pid_in_mon"] = write_pid(MON_GROUP, tproc.pid) \
                and pid_in_group(MON_GROUP, tproc.pid)
        pok, pwhy = pid_check(arm, ways, rec.get("tenant_pid"),
                              rec.get("pid_in_clos"))
        rec["pid_ok"], rec["pid_why"] = pok, pwhy
        if ways > 0 and not pok:
            rec["status"] = "gate_fail"
            rec["query_seconds"] = None
            rec["victim_cyc_per_load"] = None
            return rec

        if occ_group:
            sampler = OccupancySampler(occ_group)
            sampler.start()

        try:
            begin_txt = wait_marker(t_out, "DUCKDB_MEASURE_BEGIN", tproc,
                                    timeout=args.begin_timeout)
        except TimeoutError as e:
            rec["status"] = "timeout_begin"
            rec["error"] = str(e)
            rec["tenant_stdout_tail"] = open(t_out, errors="replace").read()[-2000:]
            rec["victim_cyc_per_load"] = None
            rec["query_seconds"] = None
            return rec
        if "DUCKDB_MEASURE_BEGIN" not in begin_txt:
            rec["status"] = "no_begin"
            rec["tenant_stdout_tail"] = begin_txt[-2000:]
            rec["victim_cyc_per_load"] = None
            rec["query_seconds"] = None
            if tproc.poll() is None:
                tproc.send_signal(signal.SIGTERM)
            return rec
        t_begin = time.time()

        vcmd = [args.victim, "--cpu", str(args.vcpu), "--node", "0",
                "--wss", str(args.vwss), "--trials", str(args.vtrials),
                "--run-sec", str(args.vsec)]
        with open(v_out, "w") as vo, open(v_err, "w") as ve:
            vproc = subprocess.Popen(vcmd, stdout=vo, stderr=ve)

        tproc.wait(timeout=args.tenant_timeout)
        if vproc.poll() is None:
            vproc.send_signal(signal.SIGTERM)
            try:
                vproc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                vproc.kill()
                vproc.wait(timeout=3)

        if sampler is not None:
            sampler.stop = True
            sampler.join(timeout=2)

        ttxt = open(t_out, errors="replace").read()
        terr = open(t_err, errors="replace").read()
        vtxt = open(v_out, errors="replace").read()
        parsed = parse_duckdb_output(ttxt)
        rec["duckdb_measure_begin"] = parsed["begin"]
        rec["duckdb_measure_end"] = parsed["end"]
        rec["query_seconds_all"] = parsed["times_all"]
        rec["query_seconds_measured"] = parsed["times_measured"]
        rec["matches_all"] = parsed["matches_all"]
        rec["stderr_tail"] = terr[-400:]
        matches, checksum = checksum_of(parsed)
        rec["matches"] = matches
        rec["sum_payload"] = checksum
        qs = parsed["times_measured"]
        rec["query_seconds"] = float(st.median(qs)) if qs else None
        vc, vn, vp99 = victim_stats(vtxt)
        rec["victim_cyc_per_load"] = vc
        rec["victim_n_trials"] = vn
        rec["victim_p99"] = vp99
        rec["occupancy_bytes_steady"] = (
            steady_occ(sampler.rows, t_begin) if sampler is not None else None)
        rec["occupancy_n_samples"] = (
            len(sampler.rows) if sampler is not None else 0)

        if rec["query_seconds"] is None:
            rec["status"] = "tenant_no_json"
            rec["tenant_stdout_tail"] = ttxt[-2000:]
            return rec

        lok, lwhy = live_check(rec["query_seconds"], rec["matches"],
                               ref_matches, vn, arm)
        rec["live_ok"] = lok
        rec["live_why"] = lwhy
        rec["status"] = "ok" if all((
            lok, rec["mask_ok"], rec["clos_ok"], rec.get("mask_held_ok", True),
            rec.get("pid_ok", True), rec["identity_ok"], rec["geom_ok"],
            rec["threads_ok"], rec["version_ok"],
            parsed["begin"], parsed["end"],
            vc is not None, vn >= 1,
        )) else "gate_fail"
        if vc is None:
            rec["status"] = "no_victim"
        return rec
    finally:
        capture_mask_after()
        if sampler is not None:
            sampler.stop = True
        for p in (tproc, vproc):
            if p is not None and p.poll() is None:
                p.send_signal(signal.SIGTERM)
                try:
                    p.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    p.kill()
        teardown()


def run_smoke(args) -> int:
    """Tiny SQL + JSON parse.  Not a result.  No resctrl, no victim, any host."""
    print("NOT A RESULT: --smoke (SQL+JSON apparatus)")
    args.n, args.probe = SMOKE_N, SMOKE_PROBE
    dbdir = args.db_dir or os.path.join(os.environ.get("TMPDIR", "/tmp"),
                                        "duckdb_tenant_cat_smoke")
    os.makedirs(dbdir, exist_ok=True)
    dbfile = os.path.join(dbdir, f"smoke_n{SMOKE_N}.duckdb")
    if os.path.exists(dbfile):
        os.remove(dbfile)
        meta = dbfile + ".meta.json"
        if os.path.exists(meta):
            os.remove(meta)
    build_db(args.duckdb, dbfile, SMOKE_N, WANT_CHAIN, SMOKE_PROBE,
             args.mnode, use_numactl=False)
    sql = measure_sql(1, 2)
    sqlfile = os.path.join(dbdir, "smoke.sql")
    open(sqlfile, "w").write(sql)
    cmd = ["stdbuf", "-oL", args.duckdb, "-json", "-readonly", dbfile, "-c",
           f".read {sqlfile}"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    parsed = parse_duckdb_output(r.stdout)
    matches, checksum = checksum_of(parsed)
    rec = dict(campaign=CAMPAIGN, smoke=True, not_a_result=True,
               returncode=r.returncode, parsed=parsed,
               matches=matches, sum_payload=checksum,
               query_seconds=(float(st.median(parsed["times_measured"]))
                              if parsed["times_measured"] else None),
               duckdb_version=duckdb_version(args.duckdb),
               stderr_tail=(r.stderr or "")[-400:])
    print(json.dumps(rec, indent=2))
    if r.returncode != 0 or not parsed["begin"] or not parsed["end"]:
        print("FAIL smoke: DuckDB did not emit BEGIN/END + timer", file=sys.stderr)
        return 1
    if matches is None or rec["query_seconds"] is None:
        print("FAIL smoke: parse missed checksum or times", file=sys.stderr)
        return 1
    print("smoke parse ok")
    return 0


def default_duckdb() -> str:
    for p in (os.path.expanduser("~/duckdb-1.1.3/duckdb"),
              os.path.join(ROOT, "benchmarks", "e2e", "duckdb_join", "duckdb")):
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return os.path.expanduser("~/duckdb-1.1.3/duckdb")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duckdb", default=default_duckdb())
    ap.add_argument("--victim",
                    default=os.path.join(ROOT, "benchmarks", "bench",
                                         "victim", "pointer_chase"))
    ap.add_argument("--out", default="")
    ap.add_argument("--db-dir", default="")
    ap.add_argument("--calib", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="tiny SQL+JSON parse; not a result; any host")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--tcpu", type=int, default=TCPU_DEFAULT)
    ap.add_argument("--vcpu", type=int, default=VCPU_DEFAULT)
    ap.add_argument("--mnode", type=int, default=0)
    ap.add_argument("--n", type=int, default=WANT_N)
    ap.add_argument("--probe", type=int, default=WANT_PROBE)
    ap.add_argument("--vwss", type=int, default=32 * 1024 * 1024)
    ap.add_argument("--vtrials", type=int, default=20)
    ap.add_argument("--vtrials-quiet", type=int, default=8)
    ap.add_argument("--vsec", type=float, default=1.0)
    ap.add_argument("--warmup", type=int, default=WARMUP_QUERIES)
    ap.add_argument("--measured", type=int, default=MEASURED_QUERIES)
    ap.add_argument("--begin-timeout", type=float, default=180)
    ap.add_argument("--tenant-timeout", type=float, default=600)
    ap.add_argument("--no-joinuniq", action="store_true")
    ap.add_argument("--no-numactl", action="store_true")
    ap.add_argument("--self-test-only", action="store_true")
    args = ap.parse_args()
    args.numactl = not args.no_numactl
    if args.calib and args.reps == 5:
        args.reps = 2
    if args.calib and args.measured == MEASURED_QUERIES:
        args.measured = 4

    self_test()
    if args.self_test_only:
        print("gates self-test passed")
        return 0

    if not os.path.isfile(args.duckdb):
        print(f"FAIL missing duckdb {args.duckdb}", file=sys.stderr)
        return 2
    args._ddb_ver = duckdb_version(args.duckdb)

    if args.smoke:
        return run_smoke(args)

    hok, hwhy = host_check(os.uname().nodename)
    if not hok:
        print(f"FAIL {hwhy}; this campaign is mos182/c4 only", file=sys.stderr)
        return 5

    if not args.out:
        print("FAIL --out is required for a campaign run", file=sys.stderr)
        return 2
    if os.path.exists(args.out):
        print(f"FAIL {args.out} exists (A6.19)", file=sys.stderr)
        return 2
    for p in (args.duckdb, args.victim, CLOS):
        if not os.path.exists(p):
            print(f"FAIL missing {p}", file=sys.stderr)
            return 2

    out_dir = args.out + ".d"
    os.makedirs(out_dir, exist_ok=True)
    db_dir = args.db_dir or os.path.join(out_dir, "db")
    os.makedirs(db_dir, exist_ok=True)

    sql_text = measure_sql(args.warmup, args.measured)
    sqlfile = os.path.join(out_dir, "measure.sql")
    open(sqlfile, "w").write(sql_text)

    dbs = {}
    chains_needed = {WANT_CHAIN}
    if not args.no_joinuniq:
        chains_needed.add(1)
    for ch in chains_needed:
        dbs[ch] = os.path.join(db_dir, f"n{args.n}_p{args.probe}_c{ch}.duckdb")
        print(f"== build chain={ch} N={args.n} P={args.probe} -> {dbs[ch]}",
              flush=True)
        build_db(args.duckdb, dbs[ch], args.n, ch, args.probe,
                 args.mnode, use_numactl=args.numactl)

    sha_ddb, sha_vic = sha256(args.duckdb), sha256(args.victim)
    arms = arm_list(args.calib, joinuniq=not args.no_joinuniq)
    print(f"== duckdb tenant CAT host={os.uname().nodename} "
          f"N={args.n} P={args.probe} R={40 * args.n} "
          f"tcpu={args.tcpu} vcpu={args.vcpu} reps={args.reps} "
          f"calib={args.calib} ver={args._ddb_ver}")
    print(f"== duckdb={sha_ddb[:12]} victim={sha_vic[:12]}")
    print("== STREAMING/nta/FB are not arms.  Exclusive host required.")

    ref_chain8 = None
    ref_joinuniq = None
    n_ok = 0
    with open(args.out, "w") as fh:
        for rep in range(1, args.reps + 1):
            order = arms[rep - 1:] + arms[:rep - 1]
            for arm, ways, chain in order:
                args._rep = rep
                ref = ref_joinuniq if chain == 1 else ref_chain8
                rec = run_one(arm, ways, chain, args, sha_ddb, sha_vic,
                              out_dir, dbs[chain], sqlfile, sql_text, ref)
                rec["rep"] = rep
                if rec.get("matches") and rec.get("status") == "ok":
                    if chain == 1 and ref_joinuniq is None:
                        ref_joinuniq = rec["matches"]
                    if chain == WANT_CHAIN and arm == "wb" and ref_chain8 is None:
                        ref_chain8 = rec["matches"]
                fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
                fh.flush()
                qs = rec.get("query_seconds")
                vc = rec.get("victim_cyc_per_load")
                occ = rec.get("occupancy_bytes_steady")
                print(f"  {arm:12s} rep{rep} query_s={qs} victim={vc} "
                      f"occ={occ} status={rec.get('status')} "
                      f"mask={rec.get('mask_got')}", flush=True)
                if rec.get("status") == "skip_busy":
                    print("FAIL host not idle; refusing to continue",
                          file=sys.stderr)
                    teardown()
                    return 3
                if rec.get("status") in ("no_begin", "timeout_begin",
                                         "tenant_no_json"):
                    print(f"FAIL {arm} rep{rep} status={rec.get('status')}; "
                          f"refusing to continue", file=sys.stderr)
                    teardown()
                    return 4
                if rec.get("status") == "ok":
                    n_ok += 1
    teardown()
    print(f"== done {n_ok} ok records -> {args.out}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        if "--smoke" not in sys.argv and "--self-test-only" not in sys.argv:
            teardown()
