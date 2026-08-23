#!/usr/bin/env python3
"""W8 / T5 analysis. Written before the data exists, for the same reason
w7_analyze.py was: once numbers are on disk, choosing between two defensible
readings stops being a methods decision and becomes Sec6.6's "fishing".

Usage: t5_analyze.py <restore-outdir> [<restore-outdir> ...]

Each outdir is one arm. The arm's identity comes from its directory name, and
every line printed carries it -- Sec5.1 applies to full-system rows too.

THE GATES, fixed here in advance
--------------------------------
G1 (primary, the reason W8 exists). Walker classifications:
      wb arm        streamingTranslations == 0
      mprotect arm  streamingTranslations >  0
    This is the only counter that separates "the guest kernel installed a
    slot-6 PTE and the x86 walker read it off an ordinary translation" from
    "the workload touched a lot of memory". A non-zero count in the wb arm
    falsifies the whole measurement, not just that arm: it would mean
    something other than the declaration is setting the bit.

G2 (independent corroboration, from inside the guest). The benchmark's own
    readback of /sys/kernel/debug/streaming/pte_query must print
    GATE=PASS(slot6=Streaming) in the mprotect arm. G1 is the simulator's
    view of the PTE; G2 is the kernel's. Both or neither.

G3 (consumption, not declaration). tlb streamingAccesses > 0 in the mprotect
    arm and == 0 in the wb arm. Expected to follow G1, and reported separately
    precisely so it cannot be quietly substituted for it.

G4 (the run is real). W8-RCS-BENCH-EXIT 0, and a parsed JSON record.

NOT A GATE, and not to be reported as one: any performance difference between
these arms. The FS geometry has never been calibrated against the SE arms, the
runs are single-rep and cold, and W8 is pre-registered as a capability
demonstration. A speedup here is not evidence for L3.
"""
import json
import re
import sys
from pathlib import Path

STAT_TRANS = "streamingTranslations"
STAT_ACC = "streamingAccesses"


def stat_sum(outdir, needle):
    """Sum every stat line whose name contains `needle`. Returns (total, rows).

    Summed across cores on purpose: the gate is about whether the declaration
    reached the walker at all, and pinning is not part of this arm's identity.
    """
    f = outdir / "stats.txt"
    if not f.exists() or f.stat().st_size == 0:
        return None, []
    total, rows = 0.0, []
    for line in f.read_text().splitlines():
        if needle not in line:
            continue
        m = re.match(r"^(\S+)\s+([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)(?:\s|$)", line)
        if m:
            total += float(m.group(2))
            rows.append((m.group(1), float(m.group(2))))
    return total, rows


def console(outdir):
    for name in ("system.pc.com_1.device", "system.pc.com_1.terminal"):
        p = outdir / name
        if p.exists():
            return p.read_text(errors="replace")
    return ""


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    verdicts = []
    for d in argv[1:]:
        out = Path(d)
        arm = out.name
        txt = console(out)
        trans, trows = stat_sum(out, STAT_TRANS)
        acc, arows = stat_sum(out, STAT_ACC)

        readback = [l.strip() for l in txt.splitlines() if "DECLARE_PTE_READBACK" in l]
        declared = [l.strip() for l in txt.splitlines() if "DECLARE_STREAMING" in l]
        exits = re.findall(r"W8-RCS-BENCH-EXIT (\d+)", txt)
        warns = [l.strip() for l in txt.splitlines() if "W8-WARN" in l]
        rec = None
        for line in txt.splitlines():
            s = line.strip()
            if s.startswith("{") and '"status"' in s:
                try:
                    rec = json.loads(s)
                except Exception:
                    pass

        print(f"===== arm {arm} =====")
        if trans is None:
            print("  stats.txt is empty or missing -- the run did not reach a dump.")
            verdicts.append((arm, "NO DATA"))
            print()
            continue
        print(f"  walker {STAT_TRANS:24s} = {trans:.0f}")
        for n, v in trows:
            print(f"      {n} = {v:.0f}")
        print(f"  tlb    {STAT_ACC:24s} = {acc:.0f}" if acc is not None else "  tlb stat absent")
        for line in declared:
            print(f"  guest: {line}")
        for line in readback:
            print(f"  guest: {line}")
        for line in warns:
            print(f"  guest: {line}")
        print(f"  bench exit codes seen: {exits or 'NONE'}")
        if rec:
            keys = [k for k in ("mode", "policy", "declare", "probe_batch", "fact_bytes",
                                "hot_bytes", "status") if k in rec]
            print("  record: " + ", ".join(f"{k}={rec[k]}" for k in keys))
        else:
            print("  record: no JSON line on the console")

        expect_stream = "mprot" in arm or "stream" in arm
        g1 = (trans > 0) if expect_stream else (trans == 0)
        g2 = any("GATE=PASS" in l for l in readback) if "mprot" in arm else None
        g3 = ((acc or 0) > 0) if expect_stream else ((acc or 0) == 0)
        g4 = exits == ["0"] and rec is not None and rec.get("status") == "ok"
        def mark(v):
            return "n/a " if v is None else ("PASS" if v else "FAIL")
        print(f"  G1 walker classification  {mark(g1)}   (expected {'>0' if expect_stream else '==0'})")
        print(f"  G2 in-guest PTE readback  {mark(g2)}")
        print(f"  G3 tagged accesses        {mark(g3)}")
        print(f"  G4 run completed          {mark(g4)}")
        allg = [g for g in (g1, g2, g3, g4) if g is not None]
        verdicts.append((arm, "PASS" if all(allg) else "FAIL"))
        print()

    print("===== summary =====")
    for arm, v in verdicts:
        print(f"  {arm:24s} {v}")
    print()
    print("Reminder: no performance comparison is licensed by these arms.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
