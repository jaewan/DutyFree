#!/usr/bin/env python3
"""A/B the repaired tenant against the binary that produced the published dataset.

Step 2 of the flush-behind repair (see SILICON_E2E_RERUN_PREREG_2026-09-04.md's
addendum).  Runs three binaries -- the published 75e0af94..., the regressed
HEAD build a677c52d..., and the repaired build -- head to head at the campaign's
geometry on the flush-behind path, interleaved round-robin so host drift cannot
alias onto a binary.

Reports, per binary, the flush-behind cost 100*(t_fd/t_fd0 - 1) against that
binary's own --flush-distance 0 median, and the residual FIX-vs-OLD gap against
run-to-run spread.  Also asserts matches == fact_bytes/16 on every run.

Emits no campaign statistic: this is apparatus qualification, the analogue of
the registered positive control.
"""
import argparse, json, os, statistics, subprocess, sys, time

HOT = 33554432
CPU = 4


def run(binary, fact, fd, huge2m=True, hit_rate=1.0):
    cmd = [binary, "--mode", "single",
           "--fact-bytes", str(fact), "--hot-bytes", str(HOT),
           "--fact-node", "0", "--hot-node", "0",
           "--cpu-list", str(CPU),
           "--reps", "1", "--warmups", "0",
           "--hit-rate", str(hit_rate)]
    if huge2m:
        cmd.append("--huge2m")
    cmd += ["--policy", "wb"]
    if fd:
        cmd += ["--flush-distance", str(fd)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise SystemExit(f"tenant exit {p.returncode} for {cmd}\n{p.stderr[-2000:]}")
    for line in reversed(p.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise SystemExit(f"no JSON from {cmd}")


def sha(path):
    return subprocess.run(["sha256sum", path], capture_output=True,
                          text=True).stdout.split()[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--regressed", required=True)
    ap.add_argument("--fixed", required=True)
    ap.add_argument("--fact", type=int, default=1073741824)
    ap.add_argument("--reps", type=int, default=7)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    bins = [("OLD", a.old), ("REG", a.regressed), ("FIX", a.fixed)]
    dists = [0, 65536, 262144, 1048576]          # fb64k / fb256k / fb1m
    want = a.fact // 16

    shas = {n: sha(p) for n, p in bins}
    for n, p in bins:
        print(f"  {n:4s} {shas[n][:16]}...  {p}")
    print(f"  fact={a.fact} hot={HOT} cpu={CPU} huge2m=True hit_rate=1.0 "
          f"reps={a.reps} required matches={want}", flush=True)

    recs = []
    t0 = time.time()
    for rep in range(1, a.reps + 1):
        # rotate binary order per rep, as the campaign rotates arm order
        order = bins[rep % len(bins):] + bins[:rep % len(bins)]
        for fd in dists:
            for name, path in order:
                j = run(path, a.fact, fd)
                rec = {"rep": rep, "binary": name, "sha": shas[name],
                       "flush_distance": fd,
                       "mtuples_per_s": j["join_mtuples_per_s"],
                       "seconds": j["seconds"], "matches": j["matches"],
                       "deficit": want - j["matches"],
                       "join_path": j["join_path"], "huge2m": j["huge2m"],
                       "correct": j["correct"],
                       "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
                recs.append(rec)
                print(f"  rep{rep} {name} fd={fd:<8d} "
                      f"{j['join_mtuples_per_s']:8.3f} Mt/s  "
                      f"matches={j['matches']} deficit={rec['deficit']}",
                      flush=True)
    print(f"  {len(recs)} runs in {time.time()-t0:.0f}s", flush=True)

    with open(a.out, "w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")

    med = {}
    for name, _ in bins:
        for fd in dists:
            v = [r["mtuples_per_s"] for r in recs
                 if r["binary"] == name and r["flush_distance"] == fd]
            med[(name, fd)] = (statistics.median(v), min(v), max(v), v)

    print("\n== throughput, Mt/s (median [min-max] over "
          f"{a.reps} reps) ==")
    print(f"  {'binary':6s} " + "".join(f"{('fd=' + str(d)):>26s}" for d in dists))
    for name, _ in bins:
        row = f"  {name:6s} "
        for fd in dists:
            m, lo, hi, _ = med[(name, fd)]
            row += f"{m:10.3f} [{lo:7.3f}-{hi:7.3f}]"
        print(row)

    print("\n== flush-behind cost, 100*(t_fd/t_fd0 - 1), each binary against "
          "its own fd=0 ==")
    cost = {}
    for name, _ in bins:
        base = med[(name, 0)][0]
        row = f"  {name:6s} "
        for fd in dists[1:]:
            c = 100.0 * (med[(name, fd)][0] / base - 1.0)
            cost[(name, fd)] = c
            row += f"  fd={fd}: {c:+7.2f} %"
        print(row)

    print("\n== residual: FIX vs OLD ==")
    print(f"  {'fd':>9s} {'OLD Mt/s':>10s} {'FIX Mt/s':>10s} {'ratio':>8s} "
          f"{'FIX-OLD':>9s} {'OLD spread':>11s} {'FIX spread':>11s}")
    worst = 0.0
    for fd in dists:
        o, olo, ohi, _ = med[("OLD", fd)]
        f, flo, fhi, _ = med[("FIX", fd)]
        d = 100.0 * (f / o - 1.0)
        osp = 100.0 * (ohi - olo) / o
        fsp = 100.0 * (fhi - flo) / f
        worst = max(worst, abs(d))
        print(f"  {fd:>9d} {o:10.3f} {f:10.3f} {f/o:8.4f} {d:+8.2f} % "
              f"{osp:10.2f} % {fsp:10.2f} %")
    print(f"\n  worst |FIX-OLD| across all four distances: {worst:.2f} %")

    print("\n== the regression, for scale: REG vs OLD ==")
    for fd in dists:
        o = med[("OLD", fd)][0]
        r = med[("REG", fd)][0]
        print(f"  fd={fd:<8d} REG/OLD = {r/o:.4f}  ({100*(r/o-1):+.2f} %)")

    bad = [r for r in recs if r["deficit"] != 0 and r["binary"] != "OLD"]
    oldbad = [r for r in recs if r["binary"] == "OLD"
              and r["deficit"] != a.fact // 4096]
    print("\n== correctness ==")
    print(f"  FIX/REG runs with deficit != 0 : {len(bad)}")
    print(f"  OLD  runs with deficit != fact/4096 ({a.fact//4096}) : {len(oldbad)}")
    print(f"  all runs huge2m=True           : "
          f"{all(r['huge2m'] for r in recs)}")
    print(f"  all fd>0 runs join_path=flushbehind : "
          f"{all(r['join_path'] == 'flushbehind' for r in recs if r['flush_distance'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
