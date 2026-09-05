#!/usr/bin/env python3
"""Silicon hash-join e2e runner.

Pre-registration: experiments/asplos/SILICON_E2E_PREREGISTRATION_2026-09-01.md
Operational pinning is in that file.  STREAMING is not measured.

One JSONL record per (arm, rep).  Existing OUT is refused (A6.19).
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
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "experiments", "lib"))
sys.path.insert(0, HERE)

from dutyfree import resctrl  # noqa: E402
from gates import (  # noqa: E402
    LOAD_MAX, WANT_FACT_BYTES, WANT_HOT_BYTES, CALIB_FACT_BYTES,
    clos_check, fb_identity_check, idle_check, live_check, mask_check,
    mask_held_check, nta_identity_check, parse_victim_cycles, self_test,
    size_check, hot_table_rounded,
)

CLOS = os.path.join(ROOT, "benchmarks", "e2e", "hash_join", "scripts", "resctrl_clos.sh")
TCPU_DEFAULT = 4
VCPU_DEFAULT = 6
FB = {"fb64k": 65536, "fb256k": 262144, "fb1m": 1048576}
NTA_PF = 32


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


def sudo_clos(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["sudo", "-n", "bash", CLOS, *args],
                          capture_output=True, text=True)


def teardown() -> None:
    sudo_clos("teardown")


# Set once this process has actually created clos_b.  The outermost teardown is
# conditioned on it because every early return in main() -- --self-test-only, an
# --out that already exists, a missing binary -- reaches that finally without
# having created anything, and tearing down there rmdir's whatever CLOS group
# another campaign is currently using.  Not hypothetical: `--self-test-only`,
# run to validate a staged harness, deleted clos_b mid-arm during the IVF
# silicon campaign and cost cat05/rep2, whose tenant then ran unconfined at the
# root CLOS's full 15 ways.
_CLOS_OWNED = False


def setup_tenant(ways: int, tcpu: int) -> None:
    global _CLOS_OWNED
    r = sudo_clos("setup_b", str(ways), str(tcpu))
    if r.returncode != 0:
        raise RuntimeError(f"setup_b failed: {r.stderr or r.stdout}")
    _CLOS_OWNED = True


def clos_cpus(group: str) -> str:
    p = os.path.join("/sys/fs/resctrl", group, "cpus_list")
    try:
        return open(p).read().strip()
    except OSError:
        return ""


def snapshot_clos(ways: int) -> dict:
    """Post-rep re-read, before teardown.  Closes the setup-then-measure TOCTOU."""
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


def wait_marker(path: str, marker: str, proc: subprocess.Popen, timeout: float) -> str:
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


def parse_tenant_json(text: str) -> dict | None:
    """Last complete JSON object.  Incremental: a killed tenant truncates."""
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def extra_for(arm: str) -> list[str]:
    if arm == "nta":
        return ["--policy", "nta", "--pf-distance", str(NTA_PF)]
    if arm in FB:
        return ["--policy", "wb", "--flush-distance", str(FB[arm])]
    return ["--policy", "wb"]


def run_one(arm: str, ways: int, args, sha_join: str, sha_vic: str,
            out_dir: str, ref_matches: int | None) -> dict:
    ok, why = host_idle()
    rec = {
        "arm": arm, "ways": ways, "host": os.uname().nodename,
        "load1": load1(), "idle_ok": ok, "idle_why": why,
        "tenant_cpu": args.tcpu, "victim_cpu": args.vcpu,
        "sha_join": sha_join, "sha_victim": sha_vic,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if not ok:
        rec["status"] = "skip_busy"
        rec["victim_cyc_per_load"] = None
        rec["join_mtuples_per_s"] = None
        return rec

    clos_group = None
    mask_got = None
    if ways > 0:
        setup_tenant(ways, args.tcpu)
        clos_group = "clos_b"
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
            rec["join_mtuples_per_s"] = None
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

    tag = f"{arm}_r{args._rep}"
    t_out = os.path.join(out_dir, f"{tag}.tenant.out")
    t_err = os.path.join(out_dir, f"{tag}.tenant.err")
    v_out = os.path.join(out_dir, f"{tag}.victim.out")
    v_err = os.path.join(out_dir, f"{tag}.victim.err")

    vproc = None
    tproc = None
    captured = False

    def capture_mask_after() -> None:
        nonlocal captured
        if captured:
            return
        rec.update(snapshot_clos(ways))
        captured = True
        ok, why = mask_held_check(
            rec.get("mask_got"), rec.get("mask_got_after"), ways,
            rec.get("clos_cpus_after"), rec.get("tenant_cpu"),
            rec.get("victim_cpu"), rec.get("clos_b_present_after"))
        rec["mask_held_ok"] = ok
        rec["mask_held_why"] = why
        if rec.get("status") == "ok" and not ok:
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
                       victim_p99=vp99,
                       join_mtuples_per_s=None, matches=None,
                       join_path="none", policy="none", pf_distance=0,
                       flush_distance=0, fact_bytes=None,
                       instantiated_hot_bytes=None, status="ok")
            return rec

        tcmd = [args.join, "--mode", "single",
                "--fact-bytes", str(args.fact), "--hot-bytes", str(args.hot),
                "--fact-node", "0", "--hot-node", "0",
                "--cpu-list", str(args.tcpu),
                "--reps", str(args.inner_reps), "--warmups", "0",
                "--hit-rate", "1.0",
                *(["--huge2m"] if args.huge2m else []),
                *extra_for(arm)]
        rec["tenant_cmd"] = tcmd
        with open(t_out, "w") as to, open(t_err, "w") as te:
            tproc = subprocess.Popen(tcmd, stdout=to, stderr=te)
        try:
            begin_txt = wait_marker(t_err, "JOIN_MEASURE_BEGIN", tproc,
                                    timeout=args.begin_timeout)
        except TimeoutError as e:
            rec["status"] = "timeout_begin"
            rec["error"] = str(e)
            rec["tenant_stderr_tail"] = open(t_err, errors="replace").read()[-2000:]
            rec["victim_cyc_per_load"] = None
            rec["join_mtuples_per_s"] = None
            return rec
        if "JOIN_MEASURE_BEGIN" not in begin_txt:
            rec["status"] = "no_begin"
            rec["tenant_stderr_tail"] = begin_txt[-2000:]
            rec["victim_cyc_per_load"] = None
            rec["join_mtuples_per_s"] = None
            if tproc.poll() is None:
                tproc.send_signal(signal.SIGTERM)
            rec["join_mtuples_per_s"] = None
            return rec

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

        tjson = parse_tenant_json(open(t_out, errors="replace").read())
        terr = open(t_err, errors="replace").read()
        vtxt = open(v_out, errors="replace").read()
        vc, vn, vp99 = victim_stats(vtxt)
        rec["victim_cyc_per_load"] = vc
        rec["victim_n_trials"] = vn
        rec["victim_p99"] = vp99
        rec["hot_table_rounded"] = hot_table_rounded(terr)
        rec["join_measure_begin"] = "JOIN_MEASURE_BEGIN" in terr
        rec["join_measure_end"] = "JOIN_MEASURE_END" in terr

        if tjson is None:
            rec["status"] = "tenant_no_json"
            rec["tenant_stderr_tail"] = terr[-2000:]
            rec["join_mtuples_per_s"] = None
            return rec

        rec["join_mtuples_per_s"] = tjson.get("join_mtuples_per_s")
        rec["matches"] = tjson.get("matches")
        rec["sum"] = tjson.get("sum")
        rec["seconds"] = tjson.get("seconds")
        rec["stream_bandwidth_gbps"] = tjson.get("stream_bandwidth_gbps")
        rec["fact_bytes"] = tjson.get("fact_bytes")
        rec["hot_bytes"] = tjson.get("hot_bytes")
        rec["instantiated_hot_bytes"] = tjson.get("instantiated_hot_bytes")
        rec["join_path"] = tjson.get("join_path")
        rec["policy"] = tjson.get("policy")
        rec["pf_distance"] = tjson.get("pf_distance")
        rec["flush_distance"] = tjson.get("flush_distance")
        rec["huge2m"] = tjson.get("huge2m")
        rec["hit_rate"] = tjson.get("hit_rate")
        rec["placement"] = tjson.get("placement")
        rec["thread_mapping"] = tjson.get("thread_mapping")
        mapped = None
        tm = tjson.get("thread_mapping") or []
        if tm:
            mapped = tm[0].get("cpu")
        rec["mapped_cpu"] = mapped
        if mapped != args.tcpu:
            rec["status"] = "cpu_mismatch"
            rec["error"] = f"thread_mapping cpu {mapped} != tenant {args.tcpu}"
            return rec

        sok, swhy = size_check(int(rec["fact_bytes"]), int(rec["instantiated_hot_bytes"]),
                               terr, want_fact=args.fact, want_hot=args.hot)
        lok, lwhy = live_check(rec["join_mtuples_per_s"], rec["matches"], ref_matches)
        fok, fwhy = fb_identity_check(arm, rec.get("join_path") or "",
                                      int(rec.get("flush_distance") or 0))
        nok, nwhy = nta_identity_check(arm, rec.get("policy") or "",
                                       int(rec.get("pf_distance") or 0))
        rec["size_ok"] = sok
        rec["live_ok"] = lok
        rec["fb_ok"] = fok
        rec["nta_ok"] = nok
        rec["size_why"] = swhy
        rec["live_why"] = lwhy
        rec["fb_why"] = fwhy
        rec["nta_why"] = nwhy
        rec["status"] = "ok" if all((sok, lok, fok, nok, rec["mask_ok"], rec["clos_ok"],
                                     rec.get("mask_held_ok", True),
                                     vc is not None, vn >= 1, rec.get("join_measure_end"))) else "gate_fail"
        if vc is None:
            rec["status"] = "no_victim"
        return rec
    finally:
        capture_mask_after()
        for p in (tproc, vproc):
            if p is not None and p.poll() is None:
                p.send_signal(signal.SIGTERM)
                try:
                    p.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    p.kill()
        teardown()


def arm_list(calib: bool) -> list[tuple[str, int]]:
    if calib:
        return [("qui", 0), ("wb", 0), ("cat04", 4), ("cat08", 8),
                ("nta", 0), ("fb256k", 0)]
    arms = [("qui", 0), ("wb", 0), ("nta", 0),
            ("fb64k", 0), ("fb256k", 0), ("fb1m", 0)]
    for w in range(1, 16):
        arms.append((f"cat{w:02d}", w))
    return arms


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--join", required=True)
    ap.add_argument("--victim", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--calib", action="store_true")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--tcpu", type=int, default=TCPU_DEFAULT)
    ap.add_argument("--vcpu", type=int, default=VCPU_DEFAULT)
    ap.add_argument("--fact", type=int, default=0)
    ap.add_argument("--hot", type=int, default=WANT_HOT_BYTES)
    ap.add_argument("--vwss", type=int, default=32 * 1024 * 1024)
    ap.add_argument("--vtrials", type=int, default=20)
    ap.add_argument("--vtrials-quiet", type=int, default=8)
    ap.add_argument("--vsec", type=float, default=1.0)
    ap.add_argument("--inner-reps", type=int, default=0,
                    help="tenant --reps per launch; 0 = 1 (full) or 12 (calib)")
    ap.add_argument("--begin-timeout", type=float, default=180)
    ap.add_argument("--tenant-timeout", type=float, default=300)
    ap.add_argument("--huge2m", action="store_true",
                    help="MAP_HUGETLB for the fact stream.  Off by default: "
                         "mos182 node0 has only 1024 2MiB pages (2 GiB); 8 GiB "
                         "SIGBUS'd (signal 7).")
    ap.add_argument("--self-test-only", action="store_true")
    args = ap.parse_args()
    if args.fact == 0:
        args.fact = CALIB_FACT_BYTES if args.calib else WANT_FACT_BYTES
    if args.calib and args.reps == 5:
        args.reps = 2
    if args.inner_reps <= 0:
        args.inner_reps = 12 if args.calib else 1
    if args.calib and args.vsec == 1.0:
        args.vsec = 0.5

    self_test()
    if args.self_test_only:
        print("gates self-test passed")
        return 0

    if os.path.exists(args.out):
        print(f"FAIL {args.out} exists (A6.19)", file=sys.stderr)
        return 2
    for p in (args.join, args.victim, CLOS):
        if not os.path.exists(p):
            print(f"FAIL missing {p}", file=sys.stderr)
            return 2

    out_dir = args.out + ".d"
    os.makedirs(out_dir, exist_ok=True)
    sha_join, sha_vic = sha256(args.join), sha256(args.victim)
    arms = arm_list(args.calib)
    print(f"== silicon e2e hashjoin host={os.uname().nodename} "
          f"fact={args.fact} hot={args.hot} tcpu={args.tcpu} vcpu={args.vcpu} "
          f"reps={args.reps} inner={args.inner_reps} huge2m={args.huge2m} "
          f"calib={args.calib}")
    print(f"== join={sha_join[:12]} victim={sha_vic[:12]}")

    ref_matches = None
    n_ok = 0
    with open(args.out, "w") as fh:
        for rep in range(1, args.reps + 1):
            # rotate arm order per rep so a slow drift does not alias onto one arm
            order = arms[rep - 1:] + arms[:rep - 1]
            for arm, ways in order:
                args._rep = rep
                rec = run_one(arm, ways, args, sha_join, sha_vic, out_dir, ref_matches)
                rec["rep"] = rep
                if arm == "wb" and rec.get("matches") and ref_matches is None:
                    ref_matches = rec["matches"]
                fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
                fh.flush()
                mt = rec.get("join_mtuples_per_s")
                vc = rec.get("victim_cyc_per_load")
                print(f"  {arm:8s} rep{rep} tuples/s={mt} victim={vc} "
                      f"status={rec.get('status')} mask={rec.get('mask_got')}",
                      flush=True)
                if rec.get("status") == "skip_busy":
                    print("FAIL host not idle; refusing to continue", file=sys.stderr)
                    teardown()
                    return 3
                if rec.get("status") in ("no_begin", "timeout_begin", "cpu_mismatch",
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
        if _CLOS_OWNED:
            teardown()
