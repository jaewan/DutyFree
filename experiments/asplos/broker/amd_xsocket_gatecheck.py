#!/usr/bin/env python3
"""Remedial diagnostics D2 and D3 of AMD_XSOCKET_PREREG_2026-09-04.md.

POST-HOC, and disclosed as such. These were written AFTER the n=20 campaign,
because two of its frozen gates turned out to be mis-specified. They answer the
questions those gates asked; they do not re-judge the claim, whose verdict is
fixed by the frozen decision rule on the frozen data.

D2 -- G4's question for the 512 KB victim. G4 required >=99% of the victim's
pages on node 0. It read a histogram that filters out mappings smaller than
1024 pages, so a 512 KB (128-page) working set is invisible to it and every
512 KB run scored 0%. The 4096 KB cells -- including the primary cell -- pass
G4 as registered at 100%. This re-reads the 512 KB victim's placement with no
size filter.

D3 -- G6b's question. G6b required core-0 frequency in each arm to match the
quiescent arm within 10%. It read ONE sample taken before the victim starts,
and in a co-run arm that sample follows a 2-second settle sleep during which
core 0 is idle and drops to its 1.5 GHz minimum, while in a quiescent arm there
is no sleep and core 0 is still boosted from the previous run. The gate compared
its own sampling schedule. This samples core-0 frequency *during* the victim's
measured window, in a quiescent arm and an xsock arm, which is what the gate
meant to compare.
"""
import json, os, re, subprocess, sys, time

V = "/home/domin/tmp_dutyfree_exp/bin/victim"
A = "/home/domin/tmp_dutyfree_exp/bin/aggressor"
XSOCK = "129,130,131,132,133,134,135"
VDUR, VWARM, SETTLE, ADUR = 3, 1, 2, 10
REPS = 5


def rd(p):
    try:
        with open(p) as f:
            return f.read().strip()
    except OSError:
        return None


def numa_hist(pid, min_pages):
    hist = {}
    try:
        lines = open(f"/proc/{pid}/numa_maps").readlines()
    except OSError:
        return None
    for ln in lines:
        per = {int(k): int(v) for k, v in re.findall(r"\bN(\d+)=(\d+)", ln)}
        if sum(per.values()) < min_pages:
            continue
        for k, v in per.items():
            hist[k] = hist.get(k, 0) + v
    return hist


def run_cell(place, wss):
    """Launch the arm and sample frequency + numa placement DURING the victim run."""
    agg = None
    if place == "xsock":
        agg = subprocess.Popen([A, "-m", "wb_load", "-t", "7", "-c", XSOCK,
                                "-N", "2", "-s", "64", "-d", str(ADUR)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(SETTLE)

    vic = subprocess.Popen([V, "-c", "0", "-w", str(wss), "-P",
                            "-d", str(VDUR), "-W", str(VWARM)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    freqs, h_unf, h_flt = [], None, None
    # The victim warms up for VWARM then measures for VDUR; sample across the
    # measured window only.
    time.sleep(VWARM + 0.3)
    for i in range(10):
        if vic.poll() is not None:
            break
        f = rd("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
        if f:
            freqs.append(int(f))
        if i == 2:
            h_unf = numa_hist(vic.pid, 1)
            h_flt = numa_hist(vic.pid, 1024)
        time.sleep(0.25)

    out, _ = vic.communicate(timeout=60)
    line = next((l for l in out.splitlines() if l.startswith("VICTIM")), "")
    cpa = None
    for t in line.split():
        if t.startswith("cyc_per_access="):
            cpa = float(t.split("=", 1)[1])
    if agg is not None:
        agg.wait(timeout=ADUR + 30)

    return dict(place=place, wss_kb=wss, cyc_per_access=cpa,
                freq_in_run_khz=freqs,
                freq_in_run_median_khz=(sorted(freqs)[len(freqs) // 2] if freqs else None),
                victim_numa_unfiltered=h_unf, victim_numa_filtered_1024=h_flt,
                thp_readback=(rd("/sys/kernel/mm/transparent_hugepage/enabled") or ""))


def main():
    out = sys.argv[1]
    if os.path.exists(out):
        print("FAIL exists (A6.19)", file=sys.stderr); return 2
    recs = []
    for wss in (512, 4096):
        for place in ("quiescent", "xsock"):
            for r in range(REPS):
                rec = run_cell(place, wss)
                rec["rep"] = r + 1
                recs.append(rec)
                print(f"  {place:9s} wss={wss:5d} rep{r+1} cyc/acc={rec['cyc_per_access']:8.2f} "
                      f"f_in_run={(rec['freq_in_run_median_khz'] or 0)/1e6:.3f}GHz "
                      f"numa_unf={rec['victim_numa_unfiltered']} "
                      f"numa_flt={rec['victim_numa_filtered_1024']}", flush=True)
    with open(out, "w") as f:
        for x in recs:
            f.write(json.dumps(x) + "\n")
    print(f"wrote {len(recs)} -> {out}")
    return 0


sys.exit(main())
