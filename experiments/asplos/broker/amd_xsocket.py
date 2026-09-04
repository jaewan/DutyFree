#!/usr/bin/env python3
"""AMD cross-socket placement sweep.
Pre-registration: AMD_XSOCKET_PREREG_2026-09-04.md

Sibling of bergamo_backinval.py. Same binaries, same victim and aggressor
command lines, same durations, same metric, same n=20. One variable is added:
a third streamer placement, on the other socket.

Two additions to the parent harness, both required by the pre-registration and
neither touching the measured command lines:

  * a second, temporally separated quiescent cell (`quiescent_b`) as the
    negative control that defines the noise band;
  * per-run readback of *realized* placement -- the victim's and every streamer
    thread's actual CPU, the L3 domain and package of every requested core, and
    the NUMA node histogram of both processes' pages -- because a placement
    experiment whose placement is not verified from the artifact is worthless.

Victim and aggressor are launched with argv lists rather than through a shell,
so the parent holds their real pids and can sample /proc during the run. The
argv they receive is identical to the parent harness's.
"""
import json, os, re, subprocess, sys, time, glob

V = "/home/domin/tmp_dutyfree_exp/bin/victim"
A = "/home/domin/tmp_dutyfree_exp/bin/aggressor"
SAME  = "1,2,3,4,5,6,7"              # CCX0, with the victim on core 0
OTHER = "9,10,11,12,13,14,15"        # CCX1, same socket
XSOCK = "129,130,131,132,133,134,135"  # socket 1, first CCX, same 7-of-8 shape
VDUR, VWARM, SETTLE, ADUR = 3, 1, 2, 10

PLACES = ("quiescent_a", "same", "other", "xsock", "quiescent_b")
CORES  = {"same": SAME, "other": OTHER, "xsock": XSOCK}


def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True).stdout.strip()


def rd(p):
    try:
        with open(p) as f:
            return f.read().strip()
    except OSError:
        return None


def l3_domain(cpu):
    return rd(f"/sys/devices/system/cpu/cpu{cpu}/cache/index3/shared_cpu_list")


def pkg(cpu):
    return rd(f"/sys/devices/system/cpu/cpu{cpu}/topology/physical_package_id")


def thp_state():
    s = rd("/sys/kernel/mm/transparent_hugepage/enabled") or ""
    for tok in s.replace("[", " [").split():
        if tok.startswith("["):
            return tok.strip("[]")
    return s


def set_thp(mode):
    subprocess.run(f"echo {mode} | sudo tee /sys/kernel/mm/transparent_hugepage/enabled",
                   shell=True, capture_output=True)
    return thp_state()


def freq(cpu):
    f = rd(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_cur_freq")
    try:
        return int(f)
    except (TypeError, ValueError):
        return None


def task_cpu(pid, tid=None):
    """Realized CPU of a task, /proc/<pid>/stat field 39 (1-indexed)."""
    st = rd(f"/proc/{pid}/task/{tid}/stat" if tid else f"/proc/{pid}/stat")
    if not st:
        return None
    tail = st[st.rfind(")") + 2:].split()
    try:
        return int(tail[36])          # field 39 overall = 37th after state
    except (IndexError, ValueError):
        return None


def cpus_allowed(pid):
    st = rd(f"/proc/{pid}/status") or ""
    m = re.search(r"^Cpus_allowed_list:\s*(\S+)", st, re.M)
    return m.group(1) if m else None


def thread_cpus(pid):
    """tid -> realized CPU. The coordinator thread (tid == pid) is included and
    must be separated by the caller: it is deliberately unpinned in
    aggressor.c -- it allocates, starts the workers and sleeps -- so it does no
    streaming and its CPU carries no placement meaning."""
    out = {}
    for d in glob.glob(f"/proc/{pid}/task/*"):
        tid = os.path.basename(d)
        c = task_cpu(pid, tid)
        if c is not None:
            out[tid] = c
    return out


def numa_hist(pid, min_pages=1024):
    """node -> pages, over mappings large enough to be the workload's own."""
    hist = {}
    try:
        with open(f"/proc/{pid}/numa_maps") as f:
            lines = f.readlines()
    except OSError:
        return None
    for ln in lines:
        per = {int(k): int(v) for k, v in re.findall(r"\bN(\d+)=(\d+)", ln)}
        if sum(per.values()) < min_pages:
            continue
        for k, v in per.items():
            hist[k] = hist.get(k, 0) + v
    return hist


def comm(pid):
    return rd(f"/proc/{pid}/comm")


def one(place, wss, thp, rep, logdir):
    cores = CORES.get(place)
    agg = agg_log = None
    bw = None
    agg_threads = []
    agg_workers = []
    agg_main_cpu = None
    agg_hist = agg_allowed = agg_comm = None
    agg_fatal = False

    if cores:
        agg_log = os.path.join(logdir, f"agg_{place}_{wss}_{thp}_r{rep}.log")
        with open(agg_log, "w") as lf:
            agg = subprocess.Popen(
                [A, "-m", "wb_load", "-t", "7", "-c", cores,
                 "-N", "2", "-s", "64", "-d", str(ADUR)],
                stdout=lf, stderr=subprocess.STDOUT)
        time.sleep(SETTLE)
        agg_comm = comm(agg.pid)
        agg_allowed = cpus_allowed(agg.pid)

    f_mid = freq(0)
    f_str = freq(int(cores.split(",")[0])) if cores else None

    vic = subprocess.Popen([V, "-c", "0", "-w", str(wss), "-P",
                            "-d", str(VDUR), "-W", str(VWARM)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Sample realized placement of both processes while the victim measures.
    vic_cpus, vic_allowed, vic_comm, vic_hist = [], None, None, None
    for i in range(6):
        time.sleep(0.5)
        if vic.poll() is not None:
            break
        if vic_comm is None:
            vic_comm = comm(vic.pid)
            vic_allowed = cpus_allowed(vic.pid)
        c = task_cpu(vic.pid)
        if c is not None:
            vic_cpus.append(c)
        if i == 2:
            vic_hist = numa_hist(vic.pid)
            if agg is not None and agg.poll() is None:
                tc = thread_cpus(agg.pid)
                agg_threads = sorted(tc.values())
                agg_main_cpu = tc.get(str(agg.pid))
                agg_workers = sorted(v for k, v in tc.items() if k != str(agg.pid))
                agg_hist = numa_hist(agg.pid)

    out, _ = vic.communicate(timeout=VDUR + VWARM + 60)
    line = next((l for l in out.splitlines() if l.startswith("VICTIM")), "")
    d = {}
    for t in line.split():
        if "=" in t:
            k, v = t.split("=", 1)
            try:
                d[k] = float(v)
            except ValueError:
                d[k] = v

    if agg is not None:
        agg.wait(timeout=ADUR + 30)
        for l in open(agg_log, errors="replace"):
            if l.startswith("aggregate:"):
                bw = float(l.split()[1])
            if "FATAL" in l:
                agg_fatal = True

    hit, miss = d.get("l2_hit"), d.get("l2_miss")
    hr = 100 * hit / (hit + miss) if hit is not None and (hit + miss) else None
    clist = [int(x) for x in cores.split(",")] if cores else []

    rec = dict(
        place=place, wss_kb=wss, thp_requested=thp, thp_readback=thp_state(),
        rep=rep, cyc_per_access=d.get("cyc_per_access"),
        l2_hit=hit, l2_miss=miss, hit_rate=hr, agg_gbps=bw,
        freq_khz=f_mid, freq_streamer_khz=f_str, ok=bool(line),
        agg_cores=cores,
        agg_l3_domain=(l3_domain(clist[0]) if clist else None),
        victim_l3_domain=l3_domain(0),
        # --- placement verification, read back from the running processes ---
        agg_l3_domains_all=sorted({l3_domain(c) for c in clist}) if clist else None,
        agg_pkgs_all=sorted({pkg(c) for c in clist}) if clist else None,
        victim_pkg=pkg(0),
        agg_realized_cpus=agg_threads or None,
        agg_worker_cpus=agg_workers or None,      # the 7 pinned streaming threads
        agg_main_cpu=agg_main_cpu,                # unpinned coordinator; no placement meaning
        agg_cpus_allowed=agg_allowed, agg_comm=agg_comm,
        agg_numa_pages=agg_hist, agg_fatal=agg_fatal, agg_log=agg_log,
        victim_realized_cpus=vic_cpus or None,
        victim_cpus_allowed=vic_allowed, victim_comm=vic_comm,
        victim_numa_pages=vic_hist,
        smt_control=rd("/sys/devices/system/cpu/smt/control"),
        smt_active=rd("/sys/devices/system/cpu/smt/active"),
        boost=rd("/sys/devices/system/cpu/cpufreq/boost"),
        governor=rd("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
    )
    print(f"  {place:11s} wss={wss:5d} thp={rec['thp_readback']:6s} rep{rep:2d} "
          f"cyc/acc={rec['cyc_per_access'] or 0:8.2f} "
          f"hit%={hr or 0:6.2f} bw={bw or 0:6.2f} "
          f"vcpu={sorted(set(vic_cpus))} aw={len(agg_workers)}t{sorted(set(agg_workers))}",
          flush=True)
    return rec


def provenance():
    return dict(
        hostname=sh("hostname"), kernel=sh("uname -r"),
        cpu_model=sh("grep -m1 'model name' /proc/cpuinfo | cut -d: -f2-").strip(),
        microcode=sh("grep -m1 microcode /proc/cpuinfo | cut -d: -f2-").strip(),
        numactl_hardware=sh("numactl --hardware"),
        node_distances={os.path.basename(os.path.dirname(p)): rd(p)
                        for p in sorted(glob.glob("/sys/devices/system/node/node*/distance"))},
        smt_control=rd("/sys/devices/system/cpu/smt/control"),
        smt_active=rd("/sys/devices/system/cpu/smt/active"),
        boost=rd("/sys/devices/system/cpu/cpufreq/boost"),
        governor=rd("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
        scaling_driver=rd("/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver"),
        perf_event_paranoid=rd("/proc/sys/kernel/perf_event_paranoid"),
        l2_size_cpu0=rd("/sys/devices/system/cpu/cpu0/cache/index2/size"),
        l3_size_cpu0=rd("/sys/devices/system/cpu/cpu0/cache/index3/size"),
        victim_bin_mtime=sh(f"stat -c %y {V}"), aggressor_bin_mtime=sh(f"stat -c %y {A}"),
        victim_sha256=sh(f"sha256sum {V}").split()[0] if os.path.exists(V) else None,
        aggressor_sha256=sh(f"sha256sum {A}").split()[0] if os.path.exists(A) else None,
        uptime=sh("uptime"), date_utc=sh("date -u"),
        cmd_victim=f"{V} -c 0 -w <WSS> -P -d {VDUR} -W {VWARM}",
        cmd_aggressor=f"{A} -m wb_load -t 7 -c <CORES> -N 2 -s 64 -d {ADUR}",
        cores={"same": SAME, "other": OTHER, "xsock": XSOCK},
    )


def main():
    reps = int(sys.argv[1]); out = sys.argv[2]
    if os.path.exists(out):
        print("FAIL exists (A6.19)", file=sys.stderr); return 2
    logdir = out + ".logs"
    os.makedirs(logdir, exist_ok=True)

    # Fail closed if the machine is not ours to use.
    la1 = float(sh("cut -d' ' -f1 /proc/loadavg"))
    if la1 > 1.0:
        print(f"FAIL load average {la1} > 1.0; not starting on a busy machine",
              file=sys.stderr)
        return 3

    prov = provenance()
    with open(out + ".provenance.json", "w") as f:
        json.dump(prov, f, indent=2)
    print(json.dumps({k: v for k, v in prov.items() if k != "numactl_hardware"}, indent=2),
          flush=True)

    recs = []
    try:
        for thp in ("never", "always"):
            got = set_thp(thp)
            print(f"== THP requested={thp} readback={got} ==", flush=True)
            for wss in (512, 4096):
                for place in PLACES:
                    for r in range(1, reps + 1):
                        recs.append(one(place, wss, thp, r, logdir))
    finally:
        set_thp("madvise")   # restore the kernel default, as the parent harness does
        with open(out, "w") as f:
            for x in recs:
                f.write(json.dumps(x) + "\n")
        print(f"wrote {len(recs)} -> {out}; THP restored to {thp_state()}")
    return 0


sys.exit(main())
