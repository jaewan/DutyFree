#!/usr/bin/env python3
"""
Phase 2.1: local-DRAM MSR 0x1A4 control, mirroring E2a's CXL sweep exactly.

Question: E2a found single-core CXL WB bandwidth flat (~8.7-9.0 GB/s)
across all 6 prefetcher-bit configs -- barely above the naive demand-only
floor. Does the SAME toggle crater local DRAM bandwidth? If local also
doesn't crater, an uncontrolled prefetcher outside 0x1A4 is live on this
part (which would also bear on the paper's gem5 note that assumes "LLC
prefetcher disabled, matching the machines"). If local craters and CXL
doesn't, prefetchers specifically aren't engaging on CXL-backed memory here.

Reuses stream_wb (--no-verify) + external MSR writes, same pattern as
run_e2a_prefetch_sweep.py. n=12, rep-interleaved across configs x node.
"""
import json, subprocess, sys, time, signal

BENCH = "/home/domin/DutyFree/benchmarks/bench"
STREAM_WB = f"{BENCH}/aggressor/stream_wb"
STREAM_CPU = 1
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
NODES = [("cxl", 2), ("local", 0)]


def msr_read(cpu, reg):
    with open(f"/dev/cpu/{cpu}/msr", "rb") as f:
        f.seek(reg)
        return int.from_bytes(f.read(8), "little")


def msr_write(cpu, reg, val):
    with open(f"/dev/cpu/{cpu}/msr", "wb") as f:
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


def main():
    saved_msr = msr_read(STREAM_CPU, 0x1A4)
    print(f"[E2c] saved MSR 0x1A4 on cpu{STREAM_CPU} = 0x{saved_msr:x}", flush=True)

    def restore(*_):
        msr_write(STREAM_CPU, 0x1A4, saved_msr)
        print(f"[E2c] restored MSR 0x1A4 = 0x{saved_msr:x}", flush=True)
        sys.exit(1)
    signal.signal(signal.SIGTERM, restore)
    signal.signal(signal.SIGINT, restore)

    outpath = sys.argv[1] if len(sys.argv) > 1 else "/tmp/e2c_raw.jsonl"
    try:
        with open(outpath, "w") as outf:
            for r in range(1, REPS + 1):
                for node_label, node in NODES:
                    for name, mask in CONFIGS:
                        msr_write(STREAM_CPU, 0x1A4, mask)
                        post = msr_read(STREAM_CPU, 0x1A4)
                        if post != mask:
                            print(f"[E2c] WARNING: MSR write verify failed", flush=True)
                        result = run_stream(STREAM_CPU, node, REGION_GB, STREAM_DUR)
                        rec = {"node": node_label, "config": name, "mask": mask,
                               "rep": r, **result}
                        outf.write(json.dumps(rec) + "\n")
                        outf.flush()
                        print(f"  [{node_label:5s}] {name:10s} rep={r:2d} "
                              f"avg_bw_gbps={result.get('avg_bw_gbps')}", flush=True)
            msr_write(STREAM_CPU, 0x1A4, saved_msr)
    finally:
        msr_write(STREAM_CPU, 0x1A4, saved_msr)
        verify = msr_read(STREAM_CPU, 0x1A4)
        print(f"[E2c] final restore verify: 0x{verify:x} (expected 0x{saved_msr:x})", flush=True)
    print(f"DONE -> {outpath}")


if __name__ == "__main__":
    main()
