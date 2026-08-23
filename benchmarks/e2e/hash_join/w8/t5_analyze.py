#!/usr/bin/env python3
"""W8 / T5 analysis. Written before the data exists, for the same reason
w7_analyze.py was: once numbers are on disk, choosing between two defensible
readings stops being a methods decision and becomes Sec6.6's "fishing".

Usage: t5_analyze.py <restore-outdir> [<restore-outdir> ...]

Each outdir is one arm. The arm's identity comes from its directory name, and
every line printed carries it -- Sec5.1 applies to full-system rows too.

THE GATES, fixed here in advance
--------------------------------
G0 (the arm table, fixed here because inferring it from the directory name
    is how the first version of this file got the m5op arm backwards).

      arm             declares via          expected streamingTranslations
      wb              nothing               == 0
      stream_mprot    PROT_STREAMING        >  0
      stream_m5op     m5op 0x55             == 0   <-- NOT a typo

    The m5op arm expects ZERO in full system, and this is the single most
    useful fact W8 has. `pseudo_inst::setstreaming` (src/sim/pseudo_inst.cc:622)
    marks pages in `process->pTable`, the SE-mode EmulationPageTable. In FS
    `tc->getProcessPtr()` is null, so it warns "called outside SE mode,
    ignored" and returns. There is no FS branch.

    Every gem5 STREAMING number this project owns was produced by that
    pseudo-instruction. The m5op arm is therefore a negative control that
    cannot be faked: identical binary, identical flags, one different
    --declare, and it produces no classifications at all, while the mprotect
    arm produces them through a real kernel and a real page table. That is the
    cleanest evidence available that the OS path is doing the work rather than
    the simulator harness.

    If this arm ever comes back non-zero, the gate FAILS and must not be waved
    through as good news -- it would mean setstreaming grew an FS path, and
    every reading below would need redoing.

G1 (primary, the reason W8 exists). Walker classifications, per G0's table.
    This is the only counter that separates "the guest kernel installed a
    slot-6 PTE and the x86 walker read it off an ordinary translation" from
    "the workload touched a lot of memory". A non-zero count in the wb arm
    falsifies the whole measurement, not just that arm: it would mean
    something other than the declaration is setting the bit.

G2 (independent corroboration, from inside the guest). The benchmark's own
    readback of /sys/kernel/debug/streaming/pte_query must print
    GATE=PASS(slot6=Streaming) in the mprotect arm. G1 is the simulator's
    view of the PTE; G2 is the kernel's. Both or neither.

G3 (consumption, not declaration). tlb streamingAccesses follows G0's table:
    > 0 in the mprotect arm, == 0 in the wb and m5op arms. Expected to track
    G1, and reported separately precisely so it cannot be quietly substituted
    for it.

G5 (the negative control is the known no-op, not an unexplained zero).
    m5op arm only: gem5's own "called outside SE mode, ignored" warning must
    appear in the run log. A zero with the warning is a demonstration; a zero
    without it is an unexplained zero, and the two must not be confused.

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

# gem5 emits this on every setstreaming call in FS mode; see G0.
M5OP_SE_ONLY_WARN = "setstreaming called outside SE mode"

# Expectation per arm, matched as a suffix of the run directory name. Explicit
# because the substring test this replaced ("stream" in arm) scored the m5op
# arm as expecting a non-zero count, which is the opposite of what the
# simulator is built to do. Suffix rather than substring so a run directory may
# be prefixed freely (w8_t5_wb, rerun_w8_t5_wb) without changing its gate.
ARMS = {
    "wb":            dict(expect_stream=False, m5op=False),
    "stream_mprot":  dict(expect_stream=True,  m5op=False),
    "stream_m5op":   dict(expect_stream=False, m5op=True),
}


def arm_spec(name):
    """Return (key, spec) for a run directory name, or (None, None)."""
    hits = sorted((k for k in ARMS if name.endswith(k)), key=len, reverse=True)
    return (hits[0], ARMS[hits[0]]) if hits else (None, None)


def gem5_log(outdir):
    """gem5's own stdout/stderr, where warn() lands. run_t5.sh tees it here."""
    p = outdir / "gem5.log"
    return p.read_text(errors="replace") if p.exists() else ""


def stat_sum(outdir, needle):
    """Sum every stat line whose name contains `needle`. Returns (total, rows).

    Summed across cores on purpose: the gate is about whether the declaration
    reached the walker at all, and pinning is not part of this arm's identity.
    """
    f = outdir / "stats.txt"
    if not f.exists() or f.stat().st_size == 0:
        return None, []
    total, rows = 0.0, []
    # errors="replace": gem5 has been observed emitting non-UTF-8 into its own
    # output files (T4's console is ISO-8859), so a strict decode here is a
    # crash mode in the analyzer, on the artifact it exists to read.
    for line in f.read_text(errors="replace").splitlines():
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

        key, spec = arm_spec(arm)
        if spec is None:
            print(f"  UNKNOWN ARM -- '{arm}' matches no entry in ARMS; not gated.")
            verdicts.append((arm, "UNKNOWN ARM"))
            print()
            continue
        expect_stream = spec["expect_stream"]
        g1 = (trans > 0) if expect_stream else (trans == 0)
        g2 = any("GATE=PASS" in l for l in readback) if key == "stream_mprot" else None
        g3 = ((acc or 0) > 0) if expect_stream else ((acc or 0) == 0)
        g4 = exits == ["0"] and rec is not None and rec.get("status") == "ok"
        # G5: the m5op arm's zero must be the documented no-op, not silence.
        g5 = (M5OP_SE_ONLY_WARN in gem5_log(out)) if spec["m5op"] else None
        def mark(v):
            return "n/a " if v is None else ("PASS" if v else "FAIL")
        note = "  <-- negative control, SE-only m5op" if spec["m5op"] else ""
        print(f"  G1 walker classification  {mark(g1)}   "
              f"(expected {'>0' if expect_stream else '==0'}){note}")
        print(f"  G2 in-guest PTE readback  {mark(g2)}")
        print(f"  G3 tagged accesses        {mark(g3)}")
        print(f"  G4 run completed          {mark(g4)}")
        print(f"  G5 SE-only warning seen   {mark(g5)}")
        allg = [g for g in (g1, g2, g3, g4, g5) if g is not None]
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
