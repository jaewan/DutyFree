"""gem5 artifact readers.

Every function here reads a run's OWN artifact. Nothing takes the launcher's
intent on trust -- rule S5.1, which exists because a 'partitioned' arm that was
never actually masked would otherwise look like a free lunch.
"""
from __future__ import annotations
import os, re


def read_stats(outdir: str) -> dict[str, float]:
    """Parse gem5 stats.txt into {name: value}. Empty dict if absent/empty."""
    p = os.path.join(outdir, "stats.txt")
    if not (os.path.exists(p) and os.path.getsize(p)):
        return {}
    out = {}
    with open(p) as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and not parts[0].startswith("-"):
                try:
                    out[parts[0]] = float(parts[1])
                except ValueError:
                    pass
    return out


def completed(outdir: str) -> tuple[bool, str]:
    """Did the run reach its exit instruction? Returns (ok, reason).

    A truncated run that still wrote a stats.txt is the F12 failure mode: a
    criterion a crashed run can satisfy.
    """
    log = outdir + ".log"
    if not os.path.exists(log):
        log = os.path.join(outdir, "run.log")
    if not os.path.exists(log):
        return False, "no log"
    txt = open(log, errors="replace").read()
    if "Exiting @ tick" not in txt:
        return False, "no 'Exiting @ tick' -- truncated or died"
    m = re.search(r"^DONE_(\d+) ", txt, re.M)
    if m and m.group(1) != "0":
        return False, f"exit code {m.group(1)}"
    return True, "ok"


def config_section(outdir: str, section: str) -> str:
    """Return the body of one [section] of config.ini, or ''."""
    p = os.path.join(outdir, "config.ini")
    if not os.path.exists(p):
        return ""
    c = open(p).read()
    m = re.search(r"\[" + re.escape(section) + r"\]\n((?:[^\[]*\n)*)", c)
    return m.group(1) if m else ""


def config_value(outdir: str, section: str, key: str) -> str | None:
    body = config_section(outdir, section)
    m = re.search(rf"^{re.escape(key)}=(.*)$", body, re.M)
    return m.group(1).strip() if m else None


def cmd_lines(outdir: str) -> list[str]:
    p = os.path.join(outdir, "config.ini")
    if not os.path.exists(p):
        return []
    return re.findall(r"^cmd=(.*)$", open(p).read(), re.M)


def declared_streaming(outdir: str) -> bool:
    """Did any workload carry the streaming declaration token?"""
    return any("stream" in c for c in cmd_lines(outdir))


def realized_table_mb(outdir: str) -> float | None:
    """The fused workload's REALIZED table size, from its own stderr line.

    Never infer this from the command line: sizes quantize, and reporting a
    requested rather than a realized size is F9 -- five instances so far.
    """
    for cand in (outdir + ".log", os.path.join(outdir, "run.log")):
        if os.path.exists(cand):
            m = re.search(r"REALIZED ([\d.]+) MB", open(cand, errors="replace").read())
            if m:
                return float(m.group(1))
    return None
