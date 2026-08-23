#!/usr/bin/env python3
"""W8 / T5: report a stat PER DUMP SECTION, because t5_analyze.py sums across them.

Written 2026-08-24 while arm 2 (stream_mprot) was still running and before any
non-zero classification count existed, for the same reason t5_analyze.py was
written before the data: a number chosen after seeing the result is not a
measurement (Sec6.6).

WHY THIS EXISTS, and why t5_analyze.py was NOT edited instead
-------------------------------------------------------------
Each T5 arm's rcS calls `m5 dumpstats` and then `m5 exit`, and gem5 dumps again
on exit. Both dumps are cumulative from the single `m5 resetstats` at the top of
the arm, so stats.txt holds TWO full stat sections and the second CONTAINS the
first. Arm 1 (`wb`) shows this plainly: simSeconds 0.233184 then 0.233720.

t5_analyze.py's stat_sum() sums every line matching a needle, so it adds the two
sections together. Its GATES are unaffected -- they are presence tests (0 sums to
0; >0 stays >0) -- but any COUNT it prints is roughly doubled. See
W8.6_T5_WB_GATE_2026-08-24.md qualification C.

t5_analyze.py is pre-registered apparatus and the campaign is mid-flight, so it
is deliberately left untouched (apparatus rule). This is a separate reader; it
computes no gate and overrides no verdict. Use t5_analyze.py for the gates and
this for any number that will be written down.

WHICH SECTION TO QUOTE. The LAST section is the whole arm, cumulative from
resetstats to m5_exit. Quote that one, and name it. The first section is the
state at the benchmark's own dumpstats, before teardown; the delta between them
is teardown activity, not workload.

Usage: t5_sections.py <outdir> [needle ...]     (default needles: the T5 stats)
"""
import re
import sys
from pathlib import Path

BEGIN = "Begin Simulation Statistics"
END = "End Simulation Statistics"
DEFAULT_NEEDLES = ["streamingTranslations", "streamingAccesses", "simSeconds"]


def sections(path):
    """Split stats.txt into a list of [(statname, value), ...] lists, one per dump."""
    secs, cur = [], None
    for line in path.read_text(errors="replace").splitlines():
        if BEGIN in line:
            cur = []
            continue
        if END in line:
            if cur is not None:
                secs.append(cur)
            cur = None
            continue
        if cur is None:
            continue
        m = re.match(r"^(\S+)\s+([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)(?:\s|$)", line)
        if m:
            # A list, not a dict. Ruby legitimately emits repeated names within
            # one section (avg_reserved / avg_size / avg_util appear once per
            # cache partition), so a dict would silently keep the first and drop
            # the rest. Corrected 2026-08-24 after the first version flagged 33
            # of those as anomalies on arm 1 -- a false alarm loud enough to hide
            # a real duplicate.
            cur.append((m.group(1), float(m.group(2))))
    return secs


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    out = Path(argv[1])
    needles = argv[2:] or DEFAULT_NEEDLES
    f = out / "stats.txt"
    if not f.exists() or f.stat().st_size == 0:
        print(f"{out.name}: stats.txt empty or missing -- no dump.")
        return 1
    secs = sections(f)

    def fmt(x):
        """Integers as integers; everything else at 6 significant digits.

        The first version formatted every value with ".0f", which rendered
        simSeconds 0.233184 as "0". A reader that silently truncates the
        quantity it exists to report is the failure this file warns about.
        """
        return f"{int(round(x))}" if abs(x - round(x)) < 1e-9 else f"{x:.6g}"

    def rows_for(sec, needle):
        return sorted((k, v) for k, v in sec if needle in k)

    print(f"===== {out.name}: {len(secs)} dump section(s) =====")
    if len(secs) != 2:
        print(f"  NOTE: expected 2 (m5 dumpstats, then m5 exit); found {len(secs)}.")
    for i, s in enumerate(secs):
        tag = "  <-- QUOTE THIS ONE (whole arm, resetstats -> m5_exit)" if i == len(secs) - 1 else ""
        print(f"\n  -- section {i + 1} of {len(secs)}{tag}")
        for needle in needles:
            rows = rows_for(s, needle)
            if not rows:
                print(f"     {needle:<26} (absent)")
                continue
            tot = sum(v for _, v in rows)
            print(f"     {needle:<26} total {fmt(tot):>16}   across {len(rows)} row(s)")
            for k, v in rows:
                print(f"        {k} = {fmt(v)}")
    if len(secs) >= 2:
        print("\n  -- section 2 minus section 1 (teardown only; NOT the workload) --")
        a, b = secs[0], secs[-1]
        adict = {}
        for k, v in a:
            adict[k] = adict.get(k, 0.0) + v
        for needle in needles:
            rows = rows_for(b, needle)
            if rows:
                bsum = {}
                for k, v in rows:
                    bsum[k] = bsum.get(k, 0.0) + v
                d = sum(bsum[k] - adict.get(k, 0.0) for k in bsum)
                print(f"     {needle:<26} delta {fmt(d):>16}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
