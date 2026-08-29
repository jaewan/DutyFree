"""Shared helpers for DutyFree experiment analysis.

WHY THIS EXISTS
---------------
Every analyzer in experiments/asplos/ re-implements the same four things: parse a
gem5 stats.txt, parse a JSONL record set, compute median/IQR, and read an arm's
identity back out of its own artifact. That duplication is how two checkers ended
up broken in opposite directions on 2026-08-30 -- one silently never matched
(a false PASS), one compared hex strings instead of values (a false ALARM).

POLICY
------
Existing analyzers are NOT refactored onto this module. They are provenance: they
produced numbers that are cited in committed outcome documents, and editing them
would change the code behind a published result. This module is for new work.
"""
__all__ = ["stats", "gem5", "resctrl"]
__version__ = "0.1.0"
