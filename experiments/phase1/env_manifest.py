#!/usr/bin/env python3
"""
Environment manifest preflight, per panel instruction: the campaign's
existing preflights check the knobs we control (governor, boost,
hugepages, resctrl mounts); this checks the ones the distribution
controls, which have now twice cost data mid-campaign without any
intervening reboot -- once as a full host reboot losing in-flight data,
once as a silent linux-tools-common alias removal that broke run_e1_gate.py
and its siblings four hours after a data collection run. Call this before
any measurement session and diff its output against the previous session's
manifest; a delta here is exactly the kind of thing that should be
investigated BEFORE trusting new numbers, not four sessions later.

Usage: python3 env_manifest.py [output.json]
Prints a human-readable summary to stdout and writes full JSON to the
given path (default: env_manifest_<hostname>_<unix-epoch-arg-not-used>.json
in cwd -- pass an explicit path with a real timestamp from the caller,
since this script cannot call time.time() itself per campaign convention
in some contexts; here it's fine, this is a standalone tool, not a
Workflow script).
"""
import json, subprocess, sys, time, os


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip()


def dpkg_version(pkg):
    out = sh(f"dpkg-query -W -f='${{Version}}' {pkg} 2>/dev/null")
    return out if out else None


def dpkg_hold_status(pkg):
    out = sh(f"apt-mark showhold 2>/dev/null | grep -x {pkg}")
    return "held" if out else "not held"


def read_first_line(path):
    try:
        with open(path) as f:
            return f.readline().strip()
    except (FileNotFoundError, PermissionError):
        return None


def governor_snapshot():
    govs = set()
    for i in range(0, 256):
        v = read_first_line(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor")
        if v is None:
            break
        govs.add(v)
    return sorted(govs) if govs else None


def resctrl_info():
    base = "/sys/fs/resctrl/info"
    if not os.path.isdir(base):
        return {"mounted": False}
    info = {"mounted": True}
    for sub, files in [
        ("L3", ["cbm_mask", "min_cbm_bits", "num_closids"]),
        ("MB", ["min_bandwidth", "bandwidth_gran", "num_rmids"]),
        ("L3_MON", ["mon_features", "num_rmids"]),
    ]:
        d = f"{base}/{sub}"
        if os.path.isdir(d):
            info[sub] = {f: read_first_line(f"{d}/{f}") for f in files
                         if os.path.exists(f"{d}/{f}")}
    return info


def perf_l3_events_alive():
    """Cheap capability probe: does perf still recognize the AMD Zen4
    l3_lookup_state alias? If not, downstream scripts MUST use raw
    encodings (rfe04 etc, see run_e1_gate.py) and this should be flagged
    loudly, not discovered via a crash four hours into a session."""
    out = sh("perf list 2>/dev/null | grep -c 'l3_lookup_state'")
    try:
        return int(out) > 0
    except ValueError:
        return None


def main():
    outpath = sys.argv[1] if len(sys.argv) > 1 else None

    manifest = {
        "hostname": sh("hostname"),
        "kernel": sh("uname -r"),
        "cpu_model": sh("grep -m1 'model name' /proc/cpuinfo").split(":", 1)[-1].strip(),
        "microcode": sh("grep -m1 microcode /proc/cpuinfo").split(":", 1)[-1].strip(),
        "governor": governor_snapshot(),
        # Two incompatible conventions exist and must not be collapsed into
        # one ambiguous field: cpufreq/boost is 1=turbo-ENABLED (AMD-style),
        # intel_pstate/no_turbo is 1=turbo-DISABLED (Intel-style, INVERTED).
        # Report both raw, plus one normalized boolean.
        "turbo_boost_amd_style": read_first_line("/sys/devices/system/cpu/cpufreq/boost"),
        "turbo_no_turbo_intel_style": read_first_line("/sys/devices/system/cpu/intel_pstate/no_turbo"),
        "turbo_enabled": (
            (read_first_line("/sys/devices/system/cpu/cpufreq/boost") == "1")
            if os.path.exists("/sys/devices/system/cpu/cpufreq/boost")
            else (read_first_line("/sys/devices/system/cpu/intel_pstate/no_turbo") == "0")
            if os.path.exists("/sys/devices/system/cpu/intel_pstate/no_turbo")
            else None
        ),
        "thp_mode": read_first_line("/sys/kernel/mm/transparent_hugepage/enabled"),
        "resctrl": resctrl_info(),
        "perf_version": sh("perf --version"),
        "perf_l3_lookup_state_alive": perf_l3_events_alive(),
        "package_versions": {
            pkg: {"version": dpkg_version(pkg), "hold": dpkg_hold_status(pkg)}
            for pkg in ["linux-tools-common", "linux-libc-dev", "amd64-microcode",
                        "intel-microcode"]
        },
        "logged_in_users": sh("who | awk '{print $1}' | sort -u | tr '\\n' ',' "),
        "load_average": sh("uptime | grep -oE 'load average.*'"),
        "uptime": sh("uptime -p"),
    }

    print(json.dumps(manifest, indent=2))

    if outpath:
        with open(outpath, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"\nwritten to {outpath}", file=sys.stderr)

    # loud, not silent: flag the specific hazard that already bit this
    # campaign twice
    if manifest["perf_l3_lookup_state_alive"] is False:
        print("\n*** WARNING: perf's l3_lookup_state alias is NOT present. ***",
              file=sys.stderr)
        print("Any script still using the alias name (not raw r<umask><code> "
              "encoding) will crash. See PHASE2_AMD_WARMUP_CHECK.md.",
              file=sys.stderr)
    if manifest["logged_in_users"] and manifest["logged_in_users"].count(",") > 1:
        print(f"\n*** NOTE: multiple users logged in ({manifest['logged_in_users']}) "
              f"-- co-tenancy confound, record this alongside any measurement "
              f"taken now. ***", file=sys.stderr)


if __name__ == "__main__":
    main()
