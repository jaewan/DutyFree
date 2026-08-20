#!/usr/bin/env python3
"""Quiescent PageRank CAT capacity-sensitivity gate.

Implements GAPBS_CAT_SENSITIVITY_PREREGISTRATION.md. No streamer and no
aggressor is ever launched: the only manipulated variable is the LLC way mask
granted to the pinned victim CPU. Per host and scale, PageRank runs in a
CPU-based resctrl CAT group at the full mask and at the minimum legal
contiguous mask; the L3 domain, the mask actually installed, and the effective
capacity are all read back from sysfs rather than assumed.
"""
import json, os, platform, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GAPBS = ROOT / "benchmarks/e2e/gapbs/third_party/gapbs"
OUT = ROOT / "benchmarks/e2e/gapbs/artifacts"
RESCTRL = Path("/sys/fs/resctrl")
# Pinned victim CPU per host, identical to the sizing gate that selected g22.
CFG = {"mos181": "32", "moscxl": "8"}
TRIAL = re.compile(r"Trial Time:\s+([0-9.]+)")


def sh(cmd, check=True):
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def sudo(cmd, check=True):
    return sh(["sudo", "-n"] + cmd, check=check)


def slurp(path, default=None):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return default


def cpu_l3(cpu):
    """L3 domain id, total bytes and ways for a CPU, read from sysfs."""
    base = Path(f"/sys/devices/system/cpu/cpu{cpu}/cache/index3")
    size = slurp(base / "size")
    assert size.endswith("K"), f"unexpected L3 size unit: {size}"
    return (int(slurp(base / "id")), int(size[:-1]) * 1024,
            int(slurp(base / "ways_of_associativity")),
            slurp(base / "shared_cpu_list"))


def l3_domains():
    """Domain ids present on the L3 schemata line."""
    for line in slurp(RESCTRL / "schemata").splitlines():
        line = line.strip()
        if line.startswith("L3:"):
            return [int(part.split("=")[0]) for part in line[3:].split(";")]
    raise SystemExit("no L3 line in schemata; is L3 CAT available?")


def freeze_state(cpu):
    """Record, without changing, whatever frequency policy the host is under."""
    return {
        "governor": slurp(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor"),
        "intel_no_turbo": slurp("/sys/devices/system/cpu/intel_pstate/no_turbo"),
        "cpufreq_boost": slurp("/sys/devices/system/cpu/cpufreq/boost"),
        "loadavg": slurp("/proc/loadavg"),
    }


def main():
    host = platform.node().split(".")[0]
    if host not in CFG:
        raise SystemExit(f"unsupported host {host}")
    cpu = CFG[host]
    if not (RESCTRL / "info" / "L3").is_dir():
        raise SystemExit("resctrl not mounted, or L3 CAT unavailable: "
                         "mount -t resctrl resctrl /sys/fs/resctrl")
    if not (GAPBS / "pr").is_file():
        raise SystemExit("run setup_gapbs.sh first")

    domain, l3_bytes, ways, shared = cpu_l3(cpu)
    domains = l3_domains()
    if domain not in domains:
        raise SystemExit(f"cpu{cpu} L3 id {domain} not among schemata domains {domains}")
    full_mask = slurp(RESCTRL / "info/L3/cbm_mask")
    min_bits_reported = int(slurp(RESCTRL / "info/L3/min_cbm_bits"))
    # AMD reports min_cbm_bits=0 and the driver accepts a zero mask, which
    # allocates no L3 at all rather than the minimum capacity this gate wants
    # to probe. Floor the mask at one way on every host.
    min_bits = max(min_bits_reported, 1)
    min_mask = format((1 << min_bits) - 1, "x")
    sparse = slurp(RESCTRL / "info/L3/sparse_masks", "unavailable")
    way_bytes = l3_bytes // ways

    # Ascending scales: the decision rule selects the *smallest* passing scale,
    # so the answer is visible as soon as the low scales land.
    scales = [int(x) for x in os.environ.get("GAPBS_CAT_SCALES", "21,22,23,24,25").split(",")]
    invocations = int(os.environ.get("GAPBS_CAT_INVOCATIONS", "3"))
    trials = int(os.environ.get("GAPBS_CAT_TRIALS", "4"))

    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"cat_sensitivity_gate_{host}.jsonl"
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OMP_PROC_BIND": "true",
           "OMP_PLACES": "cores"}
    frozen = freeze_state(cpu)
    print(f"{host}: cpu{cpu} L3 domain {domain} ({shared}), {l3_bytes >> 20} MiB / "
          f"{ways} ways = {way_bytes >> 20} MiB per way; full={full_mask} "
          f"min={min_mask} ({min_bits} way(s), reported floor "
          f"{min_bits_reported}, sparse_masks={sparse}); freeze={frozen}",
          flush=True)

    for scale in scales:
        for label, mask in (("full", full_mask), ("min", min_mask)):
            for inv in range(invocations):
                group = RESCTRL / f"gapbs_cat_{os.getpid()}_{scale}_{label}_{inv}"
                sudo(["mkdir", str(group)])
                proc = None
                try:
                    # Target domain constrained; every other domain left at full.
                    line = "L3:" + ";".join(
                        f"{d}={mask if d == domain else full_mask}" for d in domains)
                    sudo(["sh", "-c", f"echo '{line}' > {group}/schemata"])
                    sudo(["sh", "-c", f"echo {cpu} > {group}/cpus_list"])
                    installed = None
                    for ln in slurp(group / "schemata").splitlines():
                        if ln.strip().startswith("L3:"):
                            installed = dict(p.split("=") for p in ln.strip()[3:].split(";"))
                    got = installed[str(domain)]
                    eff_bytes = bin(int(got, 16)).count("1") * way_bytes
                    cmd = ["taskset", "-c", cpu, str(GAPBS / "pr"), "-g", str(scale),
                           "-n", str(trials), "-r", "1", "-l"]
                    t0 = time.time()
                    proc = subprocess.Popen(cmd, cwd=GAPBS, env=env, text=True,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
                    lines, samples = [], []
                    mon = group / "mon_data" / f"mon_L3_{domain:02d}"
                    for ln in proc.stdout:
                        lines.append(ln)
                        if ln.startswith("Trial Time:"):
                            samples.append({k: slurp(mon / k) for k in
                                            ("llc_occupancy", "mbm_local_bytes",
                                             "mbm_total_bytes")})
                    rc = proc.wait()
                    times = [float(x) for x in TRIAL.findall("".join(lines))]
                    rec = {"campaign": "gapbs_cat_sensitivity_gate", "host": host,
                           "scale": scale, "mask_label": label, "invocation": inv,
                           "command": cmd, "cpu_requested": cpu,
                           "l3_domain": domain, "l3_bytes": l3_bytes, "l3_ways": ways,
                           "way_bytes": way_bytes, "shared_cpu_list": shared,
                           "mask_requested": mask, "mask_installed": got,
                           "effective_bytes": eff_bytes,
                           "cbm_mask_full": full_mask,
                           "min_cbm_bits_reported": min_bits_reported,
                           "min_cbm_bits_used": min_bits,
                           "sparse_masks": sparse,
                           "schemata_readback": slurp(group / "schemata"),
                           "cpus_list_readback": slurp(group / "cpus_list"),
                           "returncode": rc, "trial_seconds_all": times,
                           "trials_requested": trials,
                           "warmup_trials": 1,
                           "trial_seconds_measured": times[1:] if len(times) == trials else [],
                           "cmt_samples_diagnostic": samples,
                           "freeze_state": frozen,
                           "wall_seconds": time.time() - t0,
                           "stdout": "".join(lines), "timestamp_unix": time.time()}
                    valid = rc == 0 and len(times) == trials
                    rec["valid"] = valid
                    with out.open("a") as f:
                        f.write(json.dumps(rec, sort_keys=True) + "\n")
                    med = sorted(times[1:])[len(times[1:]) // 2] if valid else float("nan")
                    print(f"g{scale} {label:4s} inv{inv} eff={eff_bytes >> 20:4d} MiB "
                          f"median={med:.6f}s valid={valid}", flush=True)
                    if not valid:
                        raise SystemExit(f"invalid g{scale}/{label}/{inv}; record retained")
                finally:
                    if proc and proc.poll() is None:
                        proc.terminate()
                    sudo(["sh", "-c", f"echo {cpu} > {RESCTRL}/cpus_list"], check=False)
                    sudo(["rmdir", str(group)], check=False)


if __name__ == "__main__":
    main()
