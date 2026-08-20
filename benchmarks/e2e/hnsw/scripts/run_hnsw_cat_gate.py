#!/usr/bin/env python3
"""HNSW CAT capacity-sensitivity gate.

Implements HNSW_CAT_SENSITIVITY_PREREGISTRATION.md. Same decision rule and
same resctrl handling as the GAPBS gate -- the sysfs/resctrl helpers are
imported from that runner rather than copied, so the mask floor and the
read-back-the-installed-mask behaviour cannot drift between the two victims.

Differences from the GAPBS gate, both pre-registered: one operating point
instead of a scale ladder, and seven trials with the first discarded, so the
measured count is even and a two-phase signal cannot bias the median by
sampling parity.
"""
import hashlib, importlib.util, json, os, platform, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve()
HNSW = HERE.parents[1]
GAPBS_RUNNER = HNSW.parent / "gapbs/scripts/run_cat_sensitivity_gate.py"

_spec = importlib.util.spec_from_file_location("gapbs_gate", GAPBS_RUNNER)
_g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_g)   # main() is __main__-guarded; import is inert

RESCTRL = _g.RESCTRL
CFG = _g.CFG            # same pinned victim CPU per host as the GAPBS gate
TRIAL = _g.TRIAL
sudo, slurp, cpu_l3, l3_domains, freeze_state = (
    _g.sudo, _g.slurp, _g.cpu_l3, _g.l3_domains, _g.freeze_state)

OUT = HNSW / "artifacts"
BIN = HNSW / "build/hnsw_bench"
LIB = HNSW / "third_party/hnswlib"


def hnswlib_commit():
    r = subprocess.run(["git", "-C", str(LIB), "rev-parse", "HEAD"],
                       text=True, capture_output=True)
    return r.stdout.strip() if r.returncode == 0 else "unavailable"


def sha256(path, limit=None):
    """Digest the index so a silently different index cannot pass unnoticed."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    host = platform.node().split(".")[0]
    if host not in CFG:
        raise SystemExit(f"unsupported host {host}")
    cpu = CFG[host]
    if not (RESCTRL / "info" / "L3").is_dir():
        raise SystemExit("resctrl not mounted, or L3 CAT unavailable")
    if not BIN.is_file():
        raise SystemExit("run setup_hnsw.sh first")

    n = int(os.environ.get("HNSW_N", "1000000"))
    dim = int(os.environ.get("HNSW_DIM", "128"))
    nq = int(os.environ.get("HNSW_QUERIES", "10000"))
    ef = int(os.environ.get("HNSW_EF", "64"))
    k = int(os.environ.get("HNSW_K", "10"))
    trials = int(os.environ.get("HNSW_TRIALS", "7"))
    invocations = int(os.environ.get("HNSW_INVOCATIONS", "3"))
    index = Path(os.environ.get(
        "HNSW_INDEX", str(HNSW / f"index/hnsw_{n // 1000000}M_d{dim}_M16_efC100.bin")))
    if not index.is_file():
        raise SystemExit(f"index missing: {index}")

    domain, l3_bytes, ways, shared = cpu_l3(cpu)
    domains = l3_domains()
    full_mask = slurp(RESCTRL / "info/L3/cbm_mask")
    min_bits_reported = int(slurp(RESCTRL / "info/L3/min_cbm_bits"))
    min_bits = max(min_bits_reported, 1)   # AMD reports 0 and accepts mask 0
    min_mask = format((1 << min_bits) - 1, "x")
    way_bytes = l3_bytes // ways
    frozen = freeze_state(cpu)
    commit = hnswlib_commit()
    digest = sha256(index)

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"hnsw_cat_gate_{host}.jsonl"
    env = {**os.environ, "OMP_NUM_THREADS": "1"}
    print(f"hnswlib {commit}")
    print(f"index {index.name} {index.stat().st_size} B sha256={digest[:16]}...")
    print(f"{host}: cpu{cpu} L3 domain {domain} ({shared}), {l3_bytes >> 20} MiB / "
          f"{ways} ways = {way_bytes >> 20} MiB per way; full={full_mask} "
          f"min={min_mask} (reported floor {min_bits_reported}); freeze={frozen}",
          flush=True)

    for label, mask in (("full", full_mask), ("min", min_mask)):
        for inv in range(invocations):
            group = RESCTRL / f"hnsw_cat_{os.getpid()}_{label}_{inv}"
            sudo(["mkdir", str(group)])
            proc = None
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
                cmd = ["taskset", "-c", cpu, str(BIN), "query", str(index), str(n),
                       str(dim), str(nq), str(ef), str(k), str(trials)]
                t0 = time.time()
                proc = subprocess.Popen(cmd, cwd=str(HNSW), env=env, text=True,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
                lines, samples = [], []
                mon = group / "mon_data" / f"mon_L3_{domain:02d}"
                for ln in proc.stdout:
                    lines.append(ln)
                    if ln.startswith("Trial Time:"):
                        samples.append({key: slurp(mon / key) for key in
                                        ("llc_occupancy", "mbm_local_bytes",
                                         "mbm_total_bytes")})
                rc = proc.wait()
                text = "".join(lines)
                times = [float(x) for x in TRIAL.findall(text)]
                checks = sorted(set(re.findall(r"checksum:\s+([0-9.\-]+)", text)))
                rec = {"campaign": "hnsw_cat_sensitivity_gate", "host": host,
                       "hnswlib_commit": commit, "index": str(index),
                       "index_bytes": index.stat().st_size, "index_sha256": digest,
                       "n": n, "dim": dim, "queries": nq, "ef": ef, "k": k,
                       "mask_label": label, "invocation": inv, "command": cmd,
                       "cpu_requested": cpu, "l3_domain": domain,
                       "l3_bytes": l3_bytes, "l3_ways": ways, "way_bytes": way_bytes,
                       "shared_cpu_list": shared, "mask_requested": mask,
                       "mask_installed": got, "effective_bytes": eff,
                       "cbm_mask_full": full_mask,
                       "min_cbm_bits_reported": min_bits_reported,
                       "min_cbm_bits_used": min_bits,
                       "schemata_readback": slurp(group / "schemata"),
                       "returncode": rc, "trials_requested": trials,
                       "warmup_trials": 1, "trial_seconds_all": times,
                       "trial_seconds_measured": times[1:] if len(times) == trials else [],
                       "distinct_checksums": checks,
                       "cmt_samples_diagnostic": samples, "freeze_state": frozen,
                       "wall_seconds": time.time() - t0, "stdout": text,
                       "timestamp_unix": time.time()}
                # One distinct checksum across all trials means the same queries
                # hit the same graph; more than one means the index or query
                # stream is not what it claims to be.
                valid = rc == 0 and len(times) == trials and len(checks) == 1
                rec["valid"] = valid
                with out.open("a") as f:
                    f.write(json.dumps(rec, sort_keys=True) + "\n")
                meas = times[1:]
                med = sorted(meas)[len(meas) // 2] if valid else float("nan")
                print(f"{label:4s} inv{inv} eff={eff >> 20:4d} MiB median={med:.6f}s "
                      f"checksums={len(checks)} valid={valid}", flush=True)
                if not valid:
                    raise SystemExit(f"invalid {label}/{inv}; record retained")
            finally:
                if proc and proc.poll() is None:
                    proc.terminate()
                sudo(["sh", "-c", f"echo {cpu} > {RESCTRL}/cpus_list"], check=False)
                sudo(["rmdir", str(group)], check=False)


if __name__ == "__main__":
    main()
