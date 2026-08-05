#!/usr/bin/env python3
"""
E2a: single-core WB CXL bandwidth vs MSR 0x1A4 prefetcher-bit sweep, plus
idle CXL/local-DRAM dependent-load latency for Little's-law columns.

Bit mapping (MSR_MISC_FEATURE_CONTROL, confirmed against public Intel
documentation -- bit order matches the mission's stated sweep order):
  bit0 = L2 hardware prefetcher ("L2 streamer")
  bit1 = L2 adjacent cache line prefetcher
  bit2 = DCU (L1) hardware prefetcher ("DCU streamer")
  bit3 = DCU IP prefetcher

Ground rule #6: rdmsr first, save, restore on exit (trap), scope to the one
core used. This script never touches any core's MSR other than STREAM_CPU.

Reuses benchmarks/bench/aggressor/stream_wb (--no-verify to bypass its
built-in "must be 0x0" check -- we're intentionally setting other masks) and
benchmarks/bench/victim/pointer_chase (dependent chase -> cycles_per_load).
"""
import json, os, subprocess, sys, time, signal

BENCH = "/home/domin/DutyFree/benchmarks/bench"
STREAM_WB = f"{BENCH}/aggressor/stream_wb"
PCHASE = f"{BENCH}/victim/pointer_chase"
MSR_PATH_FMT = "/dev/cpu/{cpu}/msr"

STREAM_CPU = 1
LAT_CPU = 2
CXL_NODE = 2
LOCAL_NODE = 0
REGION_GB = 16
STREAM_DUR = 8
REPS = 12

CONFIGS = [
    ("all_on", 0x0),
    ("l2hw_off", 0x1),
    ("l2adj_off", 0x2),
    ("dcu_off", 0x4),
    ("dcuip_off", 0x8),
    ("all_off", 0xF),
]


def msr_read(cpu, reg):
    with open(MSR_PATH_FMT.format(cpu=cpu), "rb") as f:
        f.seek(reg)
        return int.from_bytes(f.read(8), "little")


def msr_write(cpu, reg, val):
    with open(MSR_PATH_FMT.format(cpu=cpu), "wb") as f:
        f.seek(reg)
        f.write(val.to_bytes(8, "little"))


def run_stream(cpu, node, region_gb, dur):
    p = subprocess.run(
        f"{STREAM_WB} --cpu {cpu} --node {node} --region-gb {region_gb} "
        f"--duration-sec {dur} --no-verify",
        shell=True, capture_output=True, text=True, timeout=dur + 60)
    for line in p.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    return {"error": p.stdout + p.stderr}


def run_latency(cpu, node, wss_bytes, trials):
    p = subprocess.run(
        f"{PCHASE} --cpu {cpu} --node {node} --wss {wss_bytes} "
        f"--trials {trials} --run-sec 1.0",
        shell=True, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return {"error": p.stdout + p.stderr}


def main():
    saved_msr = msr_read(STREAM_CPU, 0x1A4)
    print(f"[E2a] saved MSR 0x1A4 on cpu{STREAM_CPU} = 0x{saved_msr:x}", flush=True)

    def restore(*_):
        try:
            msr_write(STREAM_CPU, 0x1A4, saved_msr)
            print(f"[E2a] restored MSR 0x1A4 on cpu{STREAM_CPU} = 0x{saved_msr:x}", flush=True)
        except Exception as e:
            print(f"[E2a] RESTORE FAILED: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
    signal.signal(signal.SIGTERM, restore)
    signal.signal(signal.SIGINT, restore)

    outpath = sys.argv[1] if len(sys.argv) > 1 else "/tmp/e2a_raw.jsonl"
    try:
        with open(outpath, "w") as outf:
            # --- prefetcher-bit sweep, rep-interleaved across configs ---
            for r in range(1, REPS + 1):
                for name, mask in CONFIGS:
                    pre = msr_read(STREAM_CPU, 0x1A4)
                    msr_write(STREAM_CPU, 0x1A4, mask)
                    post = msr_read(STREAM_CPU, 0x1A4)
                    if post != mask:
                        print(f"[E2a] WARNING: MSR write verify failed: wrote 0x{mask:x} read 0x{post:x}", flush=True)
                    result = run_stream(STREAM_CPU, CXL_NODE, REGION_GB, STREAM_DUR)
                    rec = {"phase": "bw_sweep", "config": name, "mask": mask, "rep": r,
                           "msr_before": pre, "msr_after_write": post, **result}
                    outf.write(json.dumps(rec) + "\n")
                    outf.flush()
                    print(f"  [bw] {name:10s} rep={r:2d} mask=0x{mask:x} "
                          f"avg_bw_gbps={result.get('avg_bw_gbps')}", flush=True)
            msr_write(STREAM_CPU, 0x1A4, saved_msr)

            # --- idle latency, CXL vs local, for Little's-law columns ---
            # WSS well above LLC (320 MB) so this is a genuine memory-latency chase.
            wss = 512 * 1024 * 1024
            for label, node in [("cxl_idle", CXL_NODE), ("local_idle", LOCAL_NODE)]:
                lat = run_latency(LAT_CPU, node, wss, REPS)
                if isinstance(lat, list):
                    for i, trial in enumerate(lat):
                        rec = {"phase": "latency", "label": label, "node": node,
                               "trial": i, **trial}
                        outf.write(json.dumps(rec) + "\n")
                    print(f"  [lat] {label}: n={len(lat)} trials, "
                          f"median cycles/load = "
                          f"{sorted(t['cycles_per_load'] for t in lat)[len(lat)//2]:.1f}",
                          flush=True)
                else:
                    outf.write(json.dumps({"phase": "latency", "label": label, "node": node, **lat}) + "\n")
                    print(f"  [lat] {label}: ERROR {lat}", flush=True)
                outf.flush()
    finally:
        msr_write(STREAM_CPU, 0x1A4, saved_msr)
        verify = msr_read(STREAM_CPU, 0x1A4)
        print(f"[E2a] final restore verify: MSR 0x1A4 on cpu{STREAM_CPU} = 0x{verify:x} "
              f"(expected 0x{saved_msr:x})", flush=True)
    print(f"DONE -> {outpath}")


if __name__ == "__main__":
    main()
