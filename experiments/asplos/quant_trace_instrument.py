#!/usr/bin/env python3
"""Apply / revert the requested-versus-realized trace hook in SimObject.py.

    quant_trace_instrument.py apply
    quant_trace_instrument.py revert

The hook dumps, for every parameter written to config.ini whose Python type is
quantised to an integer tick count by m5.ticks.fromSeconds (Latency, Clock,
Frequency, MemoryBandwidth, NetworkBandwidth), a TSV row of

    path <TAB> param <TAB> python_class <TAB> requested_si <TAB> realized_ini

so QUANTIZATION_AUDIT_2026-09-03.md's table can be regenerated mechanically
instead of by hand-reading SimObject defaults.  Hooking print_ini rather than
fromSeconds is what makes the enumeration complete: it sees every parameter
that reaches config.ini, including the ones that convert exactly, and it knows
each one's path and name, which fromSeconds does not.

This is a TEMPORARY audit hook.  It is applied and reverted inside
enumerate_quantized_params.sh; it is never left in the tree.  gem5 marshals
src/python/ into gem5.opt at build time, so it only takes effect under
M5_OVERRIDE_PY_SOURCE=true and never requires a rebuild.
"""

import subprocess
import sys
from pathlib import Path

TARGET = Path("/home/domin/DutyFree/gem5/src/python/m5/SimObject.py")

ANCHOR_DECL = "# dict to look up SimObjects based on path\ninstanceDict = {}"

HELPER = '''


# TEMPORARY AUDIT HOOK -- applied and reverted by
# experiments/asplos/enumerate_quantized_params.sh.  Inert unless
# DF_QUANT_TRACE names a destination.
def _df_quant_trace(path, param, value):
    import os

    dest = os.environ.get("DF_QUANT_TRACE")
    if not dest:
        return
    from .params.network_params import NetworkBandwidth
    from .params.param_types import MemoryBandwidth
    from .params.time_params import (
        Clock,
        Frequency,
        Latency,
    )

    items = value if isinstance(value, (list, tuple)) else [value]
    rows = []
    for v in items:
        if isinstance(v, (Latency, Clock)):
            req = f"{'ticks' if v.ticks else 's'}={v.value!r}"
        elif isinstance(v, Frequency):
            req = f"{'ticks' if v.ticks else 'Hz'}={v.value!r}"
        elif isinstance(v, MemoryBandwidth):
            req = f"Bps={float(v)!r}"
        elif isinstance(v, NetworkBandwidth):
            req = f"bps={float(v)!r}"
        else:
            continue
        rows.append(
            "\\t".join([path, param, type(v).__name__, req, str(v.ini_str())])
        )
    if rows:
        # one file per gem5 process: the runner launches three arms at once
        with open(f"{dest}.{os.getpid()}", "a") as f:
            f.write("\\n".join(rows) + "\\n")'''

ANCHOR_CALL = """                print(
                    f"{param}={self._values[param].ini_str()}",
                    file=ini_file,
                )
"""

CALL = "                _df_quant_trace(self.path(), param, value)\n"


def apply_hook():
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", str(TARGET)],
        cwd=TARGET.parent,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        sys.exit(f"refusing to patch: {TARGET} is already modified\n{dirty}")

    src = TARGET.read_text()
    for anchor in (ANCHOR_DECL, ANCHOR_CALL):
        if src.count(anchor) != 1:
            sys.exit(f"anchor not found exactly once in {TARGET}:\n{anchor}")
    src = src.replace(ANCHOR_DECL, ANCHOR_DECL + HELPER)
    src = src.replace(ANCHOR_CALL, ANCHOR_CALL + CALL)
    TARGET.write_text(src)
    print(f"applied audit hook to {TARGET}")


def revert_hook():
    subprocess.run(["git", "checkout", "--", str(TARGET)], cwd=TARGET.parent)
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", str(TARGET)],
        cwd=TARGET.parent,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        sys.exit(f"FAILED to revert {TARGET}:\n{dirty}")
    print(f"reverted {TARGET} (clean)")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("apply", "revert"):
        sys.exit(__doc__)
    (apply_hook if sys.argv[1] == "apply" else revert_hook)()
