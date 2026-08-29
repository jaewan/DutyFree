#!/usr/bin/env python3
"""Archive the load-bearing values of gem5 run directories into durable JSONL.

gem5 writes ~250 KB of stats.txt per run into /tmp, which does not survive a
reboot (an F10-adjacent hazard: the apparatus is committed but its output is
not). Archiving raw stats for 187 runs would be ~375 MB; archiving the values
the outcome documents actually cite is ~1 KB per run.

Identity fields are read back from each run's own config.ini (S5.1) and the
realized table size from its own log (F9), never inferred from the directory
name.

Usage:  python3 experiments/lib/archive_gem5_runs.py '/tmp/fh_*_s*' out.jsonl
"""
import glob, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dutyfree import gem5

ITERS = 3_000_000
HNF = "system.ruby.hnf.cntrl.cache"


def one(d: str) -> dict | None:
    if d.endswith(".log") or not os.path.isdir(d):
        return None
    ok, why = gem5.completed(d)
    s = gem5.read_stats(d)
    if not s:
        return dict(run=os.path.basename(d), completed=False, reason=why or "no stats")
    c0 = s.get("system.cpu0.numCycles")
    c1 = s.get("system.cpu1.numCycles", 0.0)
    t = (s.get("system.cpu1.l2.cache.m_demand_misses", 0.0)
         + s.get("system.cpu1.l2.cache.m_prefetch_misses", 0.0))
    rp = gem5.config_value(d, HNF + ".replacement_policy", "type")
    rec = dict(
        run=os.path.basename(d), completed=ok, reason=why,
        cyc_per_access=(c0 / ITERS) if c0 else None,
        simTicks=s.get("simTicks"), simInsts=s.get("simInsts"),
        tenant_cycles=c1 or None, tenant_ipc=s.get("system.cpu1.ipc"),
        tenant_l2_misses_total=t or None,
        tenant_misses_per_kcyc=(1000 * t / c1) if c1 else None,
        hnf_policy=rp,
        hnf_requestor_masks=gem5.config_value(d, HNF, "requestor_masks"),
        fwd_unique=gem5.config_value(d, "system.ruby.hnf.cntrl", "fwd_unique_on_readshared"),
        declared_streaming=gem5.declared_streaming(d),
        realized_table_mb=gem5.realized_table_mb(d),
        hnf_allocs_by_way=[s.get(f"{HNF}.m_allocsByWay::{w}") for w in range(20)]
                          if f"{HNF}.m_allocsByWay::0" in s else None,
    )
    return rec


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    pattern, out = sys.argv[1], sys.argv[2]
    recs = [r for r in (one(d) for d in sorted(glob.glob(pattern))) if r]
    if not recs:
        print(f"  no runs matched {pattern}", file=sys.stderr)
        return 1
    with open(out, "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    done = sum(1 for r in recs if r.get("completed"))
    print(f"  {out}: {len(recs)} runs ({done} completed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
