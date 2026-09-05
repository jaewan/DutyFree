#!/usr/bin/env python3
"""Diff the IVF-Flat tenant against the independent reference (F20 anchor).

Runs benchmarks/e2e/ivf_flat/build/ivf_flat_bench (or any copy of it) and
ivf_recall_reference.py over the same (nlist, dim, nb, nq, nprobe, k,
kmeans_iters, train_n, seed), then compares the three quantities the tenant
exposes that depend on the whole search:

  recall_at_k  the number under audit
  id_sum       sum of every returned top-k id -- an exact 64-bit integer, so
               agreement here is an exact k*nq-way match and cannot be
               satisfied by a coincidence of averages
  dist_sum     sum of the returned top-k distances; float32 summed in an order
               the compiler chooses, so this is compared as a relative residual
               rather than exactly

The reference never sees the tenant's output, and the tenant is never given the
reference's.  This script is the only place the two meet.

  --exhaustive-probe additionally runs the tenant with nprobe = nlist, which
  makes ivf_query degenerate to a full scan; the tenant's id_sum is then the
  id_sum of its own exhaustive path, so the comparison checks the exhaustive
  reference the tenant grades itself against (ivf_flat_bench.cpp:973-984)
  instead of only the approximate path.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

REF = __file__.replace("ivf_recall_compare.py", "ivf_recall_reference.py")


def run_tenant(binary: str, cfg: dict, extra: list[str]) -> dict:
    cmd = [binary, "--json", "--reps", "1", "--warmups", "0",
           "--nlist", str(cfg["nlist"]), "--dim", str(cfg["dim"]),
           "--nb", str(cfg["nb"]), "--nq", str(cfg["nq"]),
           "--nprobe", str(cfg["nprobe"]), "--k", str(cfg["k"]),
           "--kmeans-iters", str(cfg["kmeans_iters"]),
           "--train-n", str(cfg["train_n"]),
           "--seed", str(cfg["seed"])] + extra
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"tenant failed rc={p.returncode}\n{p.stderr[-2000:]}")
    return {"json": json.loads(p.stdout.strip().splitlines()[-1]), "cmd": cmd}


def run_reference(python: str, cfg: dict, backend: str, contract: str) -> dict:
    cmd = [python, REF, "--json", "--backend", backend, "--contract", contract,
           "--nlist", str(cfg["nlist"]), "--dim", str(cfg["dim"]),
           "--nb", str(cfg["nb"]), "--nq", str(cfg["nq"]),
           "--nprobe", str(cfg["nprobe"]), "--k", str(cfg["k"]),
           "--kmeans-iters", str(cfg["kmeans_iters"]),
           "--train-n", str(cfg["train_n"]),
           "--seed", str(cfg["seed"])]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"reference failed rc={p.returncode}\n{p.stderr[-4000:]}")
    return {"json": json.loads(p.stdout.strip().splitlines()[-1]), "cmd": cmd}


def compare(cfg: dict, binary: str, python: str, backend: str, contract: str,
            extra: list[str]) -> dict:
    t = run_tenant(binary, cfg, extra)
    r = run_reference(python, cfg, backend, contract)
    tj, rj = t["json"], r["json"]
    d_t, d_r = float(tj["dist_sum"]), float(rj["dist_sum"])
    rel = abs(d_t - d_r) / max(abs(d_t), 1e-300)

    # recall is hits/(k*nq); both sides accumulate that quotient in double in a
    # different order, so the doubles can differ in the last bit while denoting
    # the same rational.  Recover the integer numerator and compare that.
    denom = cfg["k"] * cfg["nq"]
    hits_t = round(float(tj["recall_at_k"]) * denom)
    hits_r = int(rj["hits_total"])
    return {
        "config": cfg,
        "backend": backend,
        "contract": contract,
        "tenant_extra": extra,
        "tenant": {"recall_at_k": tj["recall_at_k"], "id_sum": tj["id_sum"],
                   "dist_sum": d_t, "hits_implied": hits_t},
        "reference": {"recall_at_k": rj["recall_at_k"], "id_sum": rj["id_sum"],
                      "dist_sum": d_r, "hits_total": hits_r},
        "id_sum_exact_match": int(tj["id_sum"]) == int(rj["id_sum"]),
        "hits_exact_match": hits_t == hits_r,
        "hits_denominator": denom,
        "recall_abs_diff": abs(float(tj["recall_at_k"]) - float(rj["recall_at_k"])),
        "dist_sum_rel_diff": rel,
        "reference_margins": rj["decision_margins"],
        "reference_seconds": rj["timing_sec"]["total"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--binary", required=True)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--backend", choices=("f64", "f32strict"), default="f64")
    ap.add_argument("--contract", choices=("nofma", "fma"), default="nofma")
    ap.add_argument("--nlist", type=int, default=8)
    ap.add_argument("--dim", type=int, default=16)
    ap.add_argument("--nb", type=int, default=256)
    ap.add_argument("--nq", type=int, default=64)
    ap.add_argument("--nprobe", type=int, default=2)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--kmeans-iters", type=int, default=8, dest="kmeans_iters")
    ap.add_argument("--train-n", type=int, default=0, dest="train_n")
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=0x1F1FCAFE1234)
    ap.add_argument("--policy", default="wb")
    ap.add_argument("--flush-distance", type=int, default=0)
    ap.add_argument("--pf-distance", type=int, default=0)
    ap.add_argument("--exhaustive-probe", action="store_true",
                    help="also compare with nprobe=nlist (tenant's exact path)")
    args = ap.parse_args()

    cfg = {kk: getattr(args, kk) for kk in
           ("nlist", "dim", "nb", "nq", "nprobe", "k", "kmeans_iters",
            "train_n", "seed")}
    extra = ["--policy", args.policy]
    if args.flush_distance:
        extra += ["--flush-distance", str(args.flush_distance)]
    if args.pf_distance:
        extra += ["--pf-distance", str(args.pf_distance)]

    out = [compare(cfg, args.binary, args.python, args.backend, args.contract, extra)]
    if args.exhaustive_probe:
        ecfg = dict(cfg, nprobe=cfg["nlist"])
        out.append(compare(ecfg, args.binary, args.python, args.backend,
                           args.contract, extra))
    print(json.dumps(out, indent=2))
    bad = [c for c in out if not c["id_sum_exact_match"]
           or not c["hits_exact_match"]]
    print(("DISAGREEMENT in %d/%d cell(s)" % (len(bad), len(out))) if bad
          else "AGREE on hit count and id_sum in all %d cell(s)" % len(out),
          file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
