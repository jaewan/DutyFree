#!/usr/bin/env python3
"""Host ceiling calibration: the CAT capacity-sensitivity gate applied to a
PURE dependent-load pointer chase (tmp_dutyfree_exp/bin/victim -P).

Purpose. Every real-engine victim adds software work per access and some
memory-level parallelism, and both only *reduce* the full/min ratio. So the
ratio a bare pointer chase achieves on a host, at the working-set size that
maximises it, is an upper bound on what ANY victim can achieve on that host
through the capacity channel. Measuring it costs minutes and tells the panel
whether a 2x bar is reachable at all before anyone builds another victim.

Reports IPC (higher is better), so the sensitivity ratio is full/min.
"""
import importlib.util, json, os, platform, re, statistics, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve()
RDB = HERE.parents[1]
_spec = importlib.util.spec_from_file_location(
    "gapbs_gate", RDB.parent / "gapbs/scripts/run_cat_sensitivity_gate.py")
_g = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_g)
RESCTRL, CFG = _g.RESCTRL, _g.CFG
sudo, slurp, cpu_l3, l3_domains, freeze_state = (
    _g.sudo, _g.slurp, _g.cpu_l3, _g.l3_domains, _g.freeze_state)
VICTIM = os.environ.get("PTR_BIN", "/home/domin/tmp_dutyfree_exp/bin/victim")
IPC = re.compile(r"^VICTIM .*ipc=([0-9.]+)", re.M)
OUT = RDB / "artifacts"


def main():
    host = platform.node().split(".")[0]
    cpu = os.environ.get("RDB_CPU") or CFG[host]
    ws_list = [int(x) for x in os.environ.get(
        "PTR_WS_KB", "8192,32768,131072,262144,524288").split(",")]
    dur = int(os.environ.get("PTR_DUR", "5"))
    inv = int(os.environ.get("PTR_INVOCATIONS", "3"))
    domain, l3_bytes, ways, shared = cpu_l3(cpu)
    domains = l3_domains()
    full_mask = slurp(RESCTRL / "info/L3/cbm_mask")
    min_mask = format((1 << max(int(slurp(RESCTRL/"info/L3/min_cbm_bits")), 1)) - 1, "x")
    way_bytes = l3_bytes // ways
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"ptr_cat_ceiling_{host}.jsonl"
    print(f"{host}: cpu{cpu} L3 dom {domain} {l3_bytes>>20}MiB/{ways}ways="
          f"{way_bytes>>20}MiB per way; full={full_mask} min={min_mask}", flush=True)
    for ws in ws_list:
        med = {}
        for label, mask in (("full", full_mask), ("min", min_mask)):
            vals, occs = [], []
            for i in range(inv):
                group = RESCTRL / f"ptr_{os.getpid()}_{label}_{i}"
                sudo(["mkdir", str(group)])
                try:
                    line = "L3:" + ";".join(
                        f"{d}={mask if d == domain else full_mask}" for d in domains)
                    sudo(["sh", "-c", f"echo '{line}' > {group}/schemata"])
                    sudo(["sh", "-c", f"echo {cpu} > {group}/cpus_list"])
                    got = None
                    for ln in slurp(group / "schemata").splitlines():
                        if ln.strip().startswith("L3:"):
                            got = dict(p.split("=") for p in ln.strip()[3:].split(";"))[str(domain)]
                    eff = bin(int(got, 16)).count("1") * way_bytes
                    r = subprocess.run(
                        ["taskset", "-c", cpu, VICTIM, "-c", cpu, "-P",
                         "-w", str(ws), "-d", str(dur), "-W", "2"],
                        text=True, capture_output=True)
                    mon = group / "mon_data" / f"mon_L3_{domain:02d}"
                    o = slurp(mon / "llc_occupancy")
                    m = IPC.search(r.stdout)
                    ipc = float(m.group(1)) if m else None
                    rec = {"campaign": "ptr_cat_ceiling", "host": host, "cpu": cpu,
                           "ws_kb": ws, "mask_label": label, "invocation": i,
                           "mask_installed": got, "effective_bytes": eff,
                           "l3_bytes": l3_bytes, "l3_ways": ways,
                           "ipc": ipc, "llc_occupancy_end": o,
                           "returncode": r.returncode, "stdout": r.stdout,
                           "freeze_state": freeze_state(cpu),
                           "timestamp_unix": time.time()}
                    with out.open("a") as f:
                        f.write(json.dumps(rec, sort_keys=True) + "\n")
                    if ipc:
                        vals.append(ipc); occs.append(int(o) if o else 0)
                    print(f"  ws={ws>>10}MiB {label:4s} inv{i} eff={eff>>20:4d}MiB "
                          f"ipc={ipc} occ={(int(o)>>20) if o else '?'}MiB", flush=True)
                finally:
                    sudo(["sh", "-c", f"echo {cpu} > {RESCTRL}/cpus_list"], check=False)
                    sudo(["rmdir", str(group)], check=False)
            med[label] = statistics.median(vals) if vals else None
        if med["full"] and med["min"]:
            print(f"== ptr ws={ws>>10}MiB: full ipc {med['full']:.4f} min ipc "
                  f"{med['min']:.4f} -> SENSITIVITY {med['full']/med['min']:.3f}x",
                  flush=True)


if __name__ == "__main__":
    main()
