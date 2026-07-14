#!/usr/bin/env python3
import csv
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "build" / "cxl_join_bench"
ARTIFACTS = ROOT / "artifacts"
DOCS = ROOT / "docs"
STATE = ARTIFACTS / "state.json"
RESULTS = ARTIFACTS / "results.jsonl"
PROGRESS = DOCS / "PROGRESS.md"
LOGDIR = ARTIFACTS / "logs"
TIMEOUT = int(os.environ.get("BENCH_TIMEOUT", "600"))

FACT = os.environ.get("BENCH_FACT_BYTES", "1g")
REPS = os.environ.get("BENCH_REPS", "30")
WARMUPS = os.environ.get("BENCH_WARMUPS", "3")
CPU_LIST = "0-15"
LLC_SOCKET_BYTES = 320 * 1024 * 1024
HOT_SIZES = {
    "2MB": 2 * 1024 * 1024,
    "25pct": int(LLC_SOCKET_BYTES * 0.25),
    "53pct": int(LLC_SOCKET_BYTES * 0.53),
    "100pct": LLC_SOCKET_BYTES,
}
PF_DISTANCES = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
PERF_EVENTS = [
    "cycles",
    "instructions",
    "LLC-loads",
    "LLC-load-misses",
    "mem_load_l3_miss_retired.local_dram",
    "mem_load_l3_miss_retired.remote_dram",
    "offcore_requests.l3_miss_demand_data_rd",
]


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S %Z")


def progress(line):
    PROGRESS.parent.mkdir(exist_ok=True)
    with PROGRESS.open("a") as f:
        f.write(f"\n- {now()}: {line}\n")


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"done": {}, "failed": {}, "timeout": {}, "findings": []}


def save_state(st):
    STATE.parent.mkdir(exist_ok=True)
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(st, indent=2, sort_keys=True) + "\n")
    tmp.replace(STATE)


def append_result(obj):
    RESULTS.parent.mkdir(exist_ok=True)
    with RESULTS.open("a") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def key(phase, name):
    return f"{phase}:{name}"


def parse_perf(path):
    out = {}
    if not path.exists():
        return out
    for row in csv.reader(path.read_text(errors="replace").splitlines()):
        if len(row) < 3:
            continue
        val = row[0].strip()
        event = row[2].strip()
        if not event or val in ("<not supported>", "<not counted>"):
            out[event] = val
            continue
        try:
            out[event] = int(val.replace(",", ""))
        except ValueError:
            try:
                out[event] = float(val)
            except ValueError:
                out[event] = val
    return out


def run_cmd(phase, name, args, perf=False, hard_halt_codes=(10, 11), allow_deferred=False):
    st = load_state()
    k = key(phase, name)
    if k in st["done"]:
        return st["done"][k]
    LOGDIR.mkdir(parents=True, exist_ok=True)
    stdout_log = LOGDIR / f"{k.replace(':', '_').replace('/', '_')}.out"
    stderr_log = LOGDIR / f"{k.replace(':', '_').replace('/', '_')}.err"
    perf_log = LOGDIR / f"{k.replace(':', '_').replace('/', '_')}.perf"
    cmd = [str(BIN)] + args
    full = cmd
    if perf:
        full = ["perf", "stat", "-x,", "-o", str(perf_log), "-e", ",".join(PERF_EVENTS), "--"] + cmd
    progress(f"START {k}: {' '.join(args)}")
    t0 = time.time()
    try:
        proc = subprocess.run(full, cwd=ROOT, text=True, capture_output=True, timeout=TIMEOUT)
        elapsed = time.time() - t0
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - t0
        obj = {"phase": phase, "name": name, "status": "TIMED_OUT", "elapsed": elapsed,
               "cmd": full, "stdout": e.stdout or "", "stderr": e.stderr or ""}
        stdout_log.write_text(e.stdout or "")
        stderr_log.write_text(e.stderr or "")
        append_result(obj)
        st["timeout"][k] = obj
        save_state(st)
        progress(f"TIMEOUT {k} after {elapsed:.1f}s")
        return obj
    stdout_log.write_text(proc.stdout)
    stderr_log.write_text(proc.stderr)
    stdout = proc.stdout.strip().splitlines()
    rec = None
    for line in reversed(stdout):
        try:
            rec = json.loads(line)
            break
        except Exception:
            pass
    if rec is None:
        rec = {"raw_stdout": proc.stdout}
    rec.update({"phase": phase, "name": name, "returncode": proc.returncode, "elapsed_wall": elapsed,
                "cmd": full, "stderr": proc.stderr.strip(), "perf": parse_perf(perf_log) if perf else {}})
    if proc.returncode == 20 and allow_deferred:
        rec["status"] = "deferred"
        append_result(rec)
        st["done"][k] = rec
        save_state(st)
        progress(f"DEFERRED {k}: {proc.stderr.strip()}")
        return rec
    if proc.returncode != 0:
        append_result(rec)
        st["failed"][k] = rec
        save_state(st)
        progress(f"FAILED {k}: rc={proc.returncode} stderr={proc.stderr.strip()[:240]}")
        if proc.returncode in hard_halt_codes:
            progress(f"HARD-HALT {k}: return code {proc.returncode}")
            raise SystemExit(proc.returncode)
        return rec
    append_result(rec)
    st["done"][k] = rec
    save_state(st)
    progress(f"DONE {k}: status={rec.get('status')} cov={rec.get('cov')}")
    if isinstance(rec.get("cov"), (int, float)) and rec["cov"] > 0.02:
        finding = f"{k} CoV {rec['cov']:.4f} > 2%; accepted after fixed N={REPS} cap"
        st["findings"].append(finding)
        save_state(st)
        progress("FINDING " + finding)
    return rec


def build_and_tests():
    progress("Phase 2 build/tests starting")
    for i in range(5):
        p = subprocess.run(["make", "native", "test"], cwd=ROOT, text=True, capture_output=True, timeout=300)
        (LOGDIR / f"build_test_attempt_{i}.out").write_text(p.stdout)
        (LOGDIR / f"build_test_attempt_{i}.err").write_text(p.stderr)
        if p.returncode == 0:
            progress("Phase 2 build/tests passed")
            return
        progress(f"Phase 2 build/tests failed attempt {i+1}: {p.stderr.strip()[:240]}")
    progress("HARD-HALT unrecoverable build/test failure after 5 attempts")
    raise SystemExit(2)


def phase0():
    progress("Phase 3 phase-0 anchors starting")
    node2 = run_cmd("phase0", "node2_stream_wb", ["--mode", "stream-smoke", "--policy", "wb",
                    "--fact-node", "2", "--fact-bytes", FACT, "--threads", "1",
                    "--cpu-list", "0", "--warmups", WARMUPS, "--reps", REPS], perf=True)
    local = run_cmd("phase0", "local_stream_wb", ["--mode", "stream-smoke", "--policy", "wb",
                    "--fact-node", "0", "--fact-bytes", FACT, "--threads", "1",
                    "--cpu-list", "0", "--warmups", WARMUPS, "--reps", REPS], perf=True)
    n2 = float(node2.get("bandwidth_gbps", 0))
    lb = float(local.get("bandwidth_gbps", 0))
    st = load_state()
    if not (12.64 <= n2 <= 18.96):
        finding = f"node-2 WB read {n2:.2f} GB/s outside 15.8±20% anchor"
        st["findings"].append(finding); progress("FINDING " + finding)
    if lb and n2 >= 0.85 * lb:
        finding = f"HARD-HALT binding failure: node-2 {n2:.2f} GB/s is local-speed vs local {lb:.2f} GB/s"
        st["findings"].append(finding); save_state(st); progress(finding)
        raise SystemExit(10)
    save_state(st)


def main_matrix():
    progress("Phases 4-7 native matrix starting")
    run_cmd("correctness", "single_check", ["--mode", "single", "--policy", "wb",
            "--fact-node", "2", "--hot-node", "0", "--fact-bytes", "256m",
            "--hot-bytes", "2m", "--threads", "1", "--cpu-list", "0",
            "--warmups", "1", "--reps", "3", "--check"], perf=True)
    for pol in ["wb", "nta"]:
        distances = [0] if pol == "wb" else PF_DISTANCES
        for d in distances:
            run_cmd("nta_stream", f"{pol}_pf{d}", ["--mode", "stream-nta", "--policy", pol,
                    "--pf-distance", str(d), "--fact-node", "2", "--fact-bytes", FACT,
                    "--threads", "1", "--cpu-list", "0", "--warmups", WARMUPS, "--reps", REPS], perf=True)
    # Confirm the instruction exists before interpreting NTA.
    dis = subprocess.run(["objdump", "-d", str(BIN)], cwd=ROOT, text=True, capture_output=True, timeout=60)
    has_nta = "prefetchnta" in dis.stdout.lower()
    append_result({"phase": "nta_stream", "name": "disassembly_prefetchnta", "status": "ok" if has_nta else "missing",
                   "prefetchnta_present": has_nta})
    progress(f"PREFETCHNTA disassembly present={has_nta}")
    if not has_nta:
        st = load_state(); st["findings"].append("prefetchnta instruction not found in disassembly")
        save_state(st)
    for label, hot in HOT_SIZES.items():
        for pol in ["wb", "nta"]:
            d = "32" if pol == "nta" else "0"
            run_cmd("single", f"{label}_{pol}", ["--mode", "single", "--policy", pol,
                    "--pf-distance", d, "--fact-node", "2", "--hot-node", "0",
                    "--fact-bytes", FACT, "--hot-bytes", str(hot), "--threads", "1",
                    "--cpu-list", "0", "--warmups", WARMUPS, "--reps", REPS], perf=True)
    for label, hot in HOT_SIZES.items():
        for th in [1, 2, 4, 8, 16]:
            cpus = "0" if th == 1 else f"0-{th-1}"
            run_cmd("hot_probe", f"{label}_t{th}", ["--mode", "hot-probe", "--policy", "wb",
                    "--fact-bytes", FACT, "--hot-bytes", str(hot), "--threads", str(th),
                    "--cpu-list", cpus, "--warmups", WARMUPS, "--reps", REPS], perf=False)
            run_cmd("morsel", f"{label}_t{th}_wb", ["--mode", "morsel", "--policy", "wb",
                    "--fact-node", "2", "--hot-node", "0", "--fact-bytes", FACT,
                    "--hot-bytes", str(hot), "--threads", str(th), "--cpu-list", cpus,
                    "--morsel", "1m", "--warmups", WARMUPS, "--reps", REPS], perf=True)
    run_cmd("cat_stub", "single_cat", ["--mode", "single", "--policy", "cat"], allow_deferred=True)


def gem5_seam():
    progress("Phase 8 GEM5 seam build starting")
    p = subprocess.run(["make", "gem5"], cwd=ROOT, text=True, capture_output=True, timeout=300)
    (LOGDIR / "gem5_build.out").write_text(p.stdout)
    (LOGDIR / "gem5_build.err").write_text(p.stderr)
    append_result({"phase": "gem5", "name": "static_build", "status": "ok" if p.returncode == 0 else "failed",
                   "returncode": p.returncode, "stdout": p.stdout[-2000:], "stderr": p.stderr[-2000:]})
    if p.returncode != 0:
        progress("GEM5 seam static build failed; non-hard-halt unless unrecoverable native build fails")
        return
    p2 = subprocess.run([str(ROOT / "build" / "cxl_join_bench.gem5"), "--mode", "single",
                         "--policy", "wb", "--fact-bytes", "16m", "--hot-bytes", "2m",
                         "--reps", "1", "--warmups", "0"], cwd=ROOT, text=True,
                        capture_output=True, timeout=120)
    append_result({"phase": "gem5", "name": "static_sanity_run", "status": "ok" if p2.returncode == 0 else "failed",
                   "returncode": p2.returncode, "stdout": p2.stdout.strip(), "stderr": p2.stderr.strip()})
    progress(f"Phase 8 GEM5 seam sanity rc={p2.returncode}")


def read_results():
    out = []
    if RESULTS.exists():
        for line in RESULTS.read_text().splitlines():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def by_name(results, phase, name):
    for r in reversed(results):
        if r.get("phase") == phase and r.get("name") == name:
            return r
    return {}


def write_results_md():
    rs = read_results()
    st = load_state()
    node2 = by_name(rs, "phase0", "node2_stream_wb")
    local = by_name(rs, "phase0", "local_stream_wb")
    wb53 = by_name(rs, "single", "53pct_wb")
    nta53 = by_name(rs, "single", "53pct_nta")
    nta_rows = [r for r in rs if r.get("phase") == "nta_stream" and r.get("policy") == "nta"]
    wb_stream = by_name(rs, "nta_stream", "wb_pf0")
    best = None
    if nta_rows and wb_stream:
        base_miss = wb_stream.get("perf", {}).get("LLC-load-misses")
        nums = []
        for r in nta_rows:
            miss = r.get("perf", {}).get("LLC-load-misses")
            if isinstance(base_miss, int) and isinstance(miss, int) and base_miss:
                nums.append((1.0 - miss / base_miss, r))
        if nums:
            best = max(nums, key=lambda x: x[0])
    lines = []
    lines.append("# RESULTS\n")
    lines.append("## SUMMARY\n")
    lines.append(f"- Node-2 WB stream bandwidth: {node2.get('bandwidth_gbps', 'n/a')} GB/s; local node-0: {local.get('bandwidth_gbps', 'n/a')} GB/s.\n")
    lines.append(f"- Row-C 53% LLC `wb`: {wb53.get('join_mtuples_per_s', 'n/a')} MT/s, probe cycles/access {wb53.get('probe_cycles_per_access', 'n/a')}, stream BW {wb53.get('stream_bandwidth_gbps', 'n/a')} GB/s.\n")
    lines.append(f"- Row-C 53% LLC `nta`: {nta53.get('join_mtuples_per_s', 'n/a')} MT/s, probe cycles/access {nta53.get('probe_cycles_per_access', 'n/a')}, stream BW {nta53.get('stream_bandwidth_gbps', 'n/a')} GB/s.\n")
    if best:
        lines.append(f"- Best PREFETCHNTA LLC-load-miss reduction vs WB: {best[0]*100:.1f}% at pf-distance {best[1].get('pf_distance')}; BW {best[1].get('bandwidth_gbps')} GB/s.\n")
    lines.append("- Deferred: `cat` policy and CMT occupancy pending resctrl group creation privilege.\n")
    if st.get("findings"):
        lines.append("\n## Findings\n")
        for f in st["findings"]:
            lines.append(f"- {f}\n")
    lines.append("\n## Anchor Table\n")
    n2 = float(node2.get("bandwidth_gbps", 0) or 0)
    lb = float(local.get("bandwidth_gbps", 0) or 0)
    lines.append("| Check | Result | Status |\n|---|---:|---|\n")
    lines.append(f"| Node-2 WB read 15.8 GB/s ±20% | {n2:.3f} GB/s | {'PASS' if 12.64 <= n2 <= 18.96 else 'OUT_OF_BAND'} |\n")
    lines.append(f"| Local read higher than node-2 | local {lb:.3f}, node2 {n2:.3f} GB/s | {'PASS' if lb > n2 * 1.15 else 'FINDING'} |\n")
    neg_wb = by_name(rs, "single", "2MB_wb")
    neg_nta = by_name(rs, "single", "2MB_nta")
    lines.append(f"| L2 negative control 2MB | wb cycles/access {neg_wb.get('probe_cycles_per_access','n/a')}, nta {neg_nta.get('probe_cycles_per_access','n/a')} | MEASURED |\n")
    lines.append("\n## PREFETCHNTA Sweep\n")
    lines.append("| Policy | pf-distance | BW GB/s | LLC-loads | LLC-load-misses | remote L3 miss retired |\n|---|---:|---:|---:|---:|---:|\n")
    for r in [wb_stream] + sorted(nta_rows, key=lambda x: x.get("pf_distance", 0)):
        if not r: continue
        perf = r.get("perf", {})
        lines.append(f"| {r.get('policy')} | {r.get('pf_distance')} | {r.get('bandwidth_gbps')} | {perf.get('LLC-loads','n/a')} | {perf.get('LLC-load-misses','n/a')} | {perf.get('mem_load_l3_miss_retired.remote_dram','n/a')} |\n")
    lines.append("\n## Row-C Single Join\n")
    lines.append("| Hot size | Policy | MT/s | Stream BW GB/s | Probe cyc/access | CoV | LLC misses |\n|---|---|---:|---:|---:|---:|---:|\n")
    for label in HOT_SIZES:
        for pol in ["wb", "nta"]:
            r = by_name(rs, "single", f"{label}_{pol}")
            lines.append(f"| {label} | {pol} | {r.get('join_mtuples_per_s','n/a')} | {r.get('stream_bandwidth_gbps','n/a')} | {r.get('probe_cycles_per_access','n/a')} | {r.get('cov','n/a')} | {r.get('perf',{}).get('LLC-load-misses','n/a')} |\n")
    lines.append("\n## Morsel WB\n")
    lines.append("| Hot size | Threads | Join MT/s | Stream BW GB/s | Hot-probe Mops/s | Slowdown proxy | CoV |\n|---|---:|---:|---:|---:|---:|---:|\n")
    for label in HOT_SIZES:
        for th in [1, 2, 4, 8, 16]:
            m = by_name(rs, "morsel", f"{label}_t{th}_wb")
            h = by_name(rs, "hot_probe", f"{label}_t{th}")
            hp = h.get("probe_mops_per_s")
            jp = m.get("join_mtuples_per_s")
            slow = (hp / jp) if isinstance(hp, (int, float)) and isinstance(jp, (int, float)) and jp else "n/a"
            lines.append(f"| {label} | {th} | {jp} | {m.get('stream_bandwidth_gbps','n/a')} | {hp} | {slow} | {m.get('cov','n/a')} |\n")
    lines.append("\n## Config Dump\n")
    lines.append(f"- Fact bytes for unattended run: {FACT}\n")
    lines.append(f"- Reps: {REPS}; warmups: {WARMUPS}; timeout: {TIMEOUT}s\n")
    lines.append(f"- CPU list: {CPU_LIST}; SMT siblings avoided by using CPUs 0-15 for max 16 workers.\n")
    lines.append(f"- Fact region bounds are present per run in `artifacts/results.jsonl` as `fact_base` and `fact_end`.\n")
    lines.append(f"- `cat`/CMT: deferred because `/sys/fs/resctrl` group creation returned permission denied.\n")
    (DOCS / "RESULTS.md").write_text("".join(lines))
    progress("Phase 10 RESULTS.md written")


def main():
    LOGDIR.mkdir(parents=True, exist_ok=True)
    progress("Decision: unattended run uses 1 GiB fact regions by default to keep per-run timeout bounded; override with BENCH_FACT_BYTES.")
    build_and_tests()
    phase0()
    main_matrix()
    gem5_seam()
    write_results_md()
    progress("All phases complete")


if __name__ == "__main__":
    main()
