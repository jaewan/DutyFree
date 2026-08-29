"""resctrl helpers for the silicon (CAT/CMT) experiments."""
from __future__ import annotations
import os

RESCTRL = "/sys/fs/resctrl"


def schemata_l3(group: str) -> str | None:
    """Read back the L3 mask of a resctrl group, domain 0, as a lowercase hex
    string with no leading zeros.

    The kernel NORMALISES masks ('00ff' -> 'ff') and INDENTS schemata lines.
    Both bit a checker on 2026-08-30: one never matched the line at all, the
    other compared strings and false-alarmed on 24 of 36 valid records.
    Compare with mask_equal(), not with ==.
    """
    p = os.path.join(group, "schemata")
    if not os.path.exists(p):
        return None
    for line in open(p):
        t = line.strip()
        if t.startswith("L3:"):
            return t.split(";")[0].split("=")[1].strip().lower()
    return None


def mask_equal(a: str | None, b: str | None) -> bool:
    """Compare two CBM masks by VALUE, never by text."""
    if a is None or b is None:
        return False
    try:
        return int(a, 16) == int(b, 16)
    except ValueError:
        return False


def llc_occupancy(group: str, domain: str = "00") -> int | None:
    p = os.path.join(group, "mon_data", f"mon_L3_{domain}", "llc_occupancy")
    try:
        return int(open(p).read().strip())
    except (OSError, ValueError):
        return None
