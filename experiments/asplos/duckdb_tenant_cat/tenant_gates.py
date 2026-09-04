"""Admission gates for the DuckDB tenant-CAT campaign.

Pure in the values they are given.  The runner calls self_test() before the
first arm.  Thresholds are the pre-registered ones in
DUCKDB_TENANT_CAT_PREREG_2026-09-01.md — changing one after seeing data is
visible in git.

Reuses silicon e2e mask/CLOS/victim parsers.  Does not import the silicon
tenant metric (tuples/s).  STREAMING / nta / flush-behind are identity
failures, not arms.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re

# Load silicon e2e gates by path.  Both packages are named `gates.py`; a
# sys.path insert would import *this* module instead.
_SIL_GATES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "silicon_e2e", "gates.py")
_spec = importlib.util.spec_from_file_location("silicon_e2e_gates", _SIL_GATES)
sil_gates = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sil_gates)

# Keep the silicon functions identical so a mask/CLOS regression here is
# the same bug class.
mask_check = sil_gates.mask_check
mask_held_check = sil_gates.mask_held_check
clos_check = sil_gates.clos_check
parse_victim_cycles = sil_gates.parse_victim_cycles
parse_cpu_list = sil_gates.parse_cpu_list

FOREIGN_COMM = frozenset(sil_gates.FOREIGN_COMM | {"duckdb"})
LOAD_MAX = sil_gates.LOAD_MAX  # 8.0; see silicon e2e operational pin

# --- registered geometry ------------------------------------------------------
WANT_N = 838_864
WANT_PROBE = 10_000_000
WANT_CHAIN = 8
WANT_R_BYTES = 40 * WANT_N          # 33,554,560
LLC_BYTES = 60 * 1024 * 1024        # 62,914,560
L2_BYTES = 2 * 1024 * 1024
OCC_MIN = 4 * L2_BYTES              # 8 MiB; not L2-resident
OCC_MAX = int(0.60 * LLC_BYTES)     # 36 MiB; 60% of socket LLC
WANT_VERSION_SUBSTR = "v1.1.3"
ALLOWED_HOSTS = frozenset({"mos182", "c4"})
CAMPAIGN = "duckdb_tenant_cat"

# --- registered kill / pass floors --------------------------------------------
S1_TAX_MIN = 1.30          # K1: wb / qui victim cyc
K2_SLOWDOWN_MIN = 0.05     # K2: cat01 vs wb and vs cat15, query seconds
K3_COST_MIN = 0.10         # K3: best-protection CAT vs wb, query seconds
JOINUNIQ_AGREE = 0.05      # diagnostic, not a kill
MIN_REPS = 5
CAT_WAYS = list(range(1, 16))
WARMUP_QUERIES = 1
MEASURED_QUERIES = 12

PREREG = "DUCKDB_TENANT_CAT_PREREG_2026-09-01.md"


def idle_check(load1: float, comms: list[str],
               load_max: float = LOAD_MAX) -> tuple[bool, str]:
    """G-idle.  `comms` are /proc/*/comm values, not command lines."""
    if load1 >= load_max:
        return False, f"load1={load1:.2f} >= {load_max}"
    foreign = sorted({c for c in comms if c in FOREIGN_COMM})
    if foreign:
        return False, f"foreign processes: {foreign}"
    return True, "ok"


def host_check(nodename: str, smoke: bool = False) -> tuple[bool, str]:
    """G-host.  Smoke is apparatus and may run anywhere."""
    if smoke:
        return True, "smoke"
    short = (nodename or "").split(".")[0].lower()
    if short in ALLOWED_HOSTS:
        return True, "ok"
    return False, f"host {nodename!r} is not mos182/c4"


def geom_check(n: int, probe: int, chain: int) -> tuple[bool, str]:
    """G-geom.  joinuniq is chain=1 at the same N and P."""
    if n != WANT_N:
        return False, f"N={n} want={WANT_N}"
    if probe != WANT_PROBE:
        return False, f"P={probe} want={WANT_PROBE}"
    if chain == 1:
        return True, "ok joinuniq"
    if chain != WANT_CHAIN:
        return False, f"chain={chain} want={WANT_CHAIN}"
    r = 40 * n
    if r <= OCC_MIN:
        return False, f"R(N)={r} <= {OCC_MIN} (L2-resident window)"
    if r > OCC_MAX:
        return False, f"R(N)={r} > {OCC_MAX} (60% LLC)"
    return True, "ok"


def version_check(ver: str | None) -> tuple[bool, str]:
    if not ver or WANT_VERSION_SUBSTR not in ver:
        return False, f"duckdb version {ver!r} want substring {WANT_VERSION_SUBSTR}"
    return True, "ok"


def threads_check(sql: str) -> tuple[bool, str]:
    if "SET threads=1" not in sql and "SET threads = 1" not in sql:
        return False, "measured SQL missing SET threads=1"
    if re.search(r"SET threads\s*=\s*(?!1\b)\d+", sql):
        return False, "measured SQL sets threads != 1"
    return True, "ok"


def identity_check(arm: str, policy: str | None = None,
                   join_path: str | None = None,
                   flush_distance: int = 0,
                   pf_distance: int = 0) -> tuple[bool, str]:
    """G-identity: nta / FB / STREAMING are not arms of this campaign."""
    if arm in ("nta",) or arm.startswith("fb"):
        return False, f"arm {arm} is not in the DuckDB tenant CAT campaign"
    pol = (policy or "wb").lower()
    if pol in ("nta", "stream", "streaming"):
        return False, f"arm {arm} policy={policy!r}"
    if (join_path or "") == "flushbehind" or flush_distance > 0:
        return False, f"arm {arm} flush-behind in the artifact"
    if pf_distance > 0:
        return False, f"arm {arm} pf_distance={pf_distance}"
    return True, "ok"


def live_check(query_seconds: float | None, matches: int | None,
               ref_matches: int | None,
               victim_n: int | None, arm: str) -> tuple[bool, str]:
    if arm == "qui":
        if victim_n is None or victim_n < 1:
            return False, f"qui victim_n_trials={victim_n}"
        return True, "ok"
    if query_seconds is None or query_seconds <= 0:
        return False, f"query_seconds={query_seconds}"
    if matches is None or matches <= 0:
        return False, f"matches={matches}"
    if ref_matches is not None and matches != ref_matches:
        return False, f"matches={matches} != reference {ref_matches}"
    if victim_n is None or victim_n < 1:
        return False, f"victim_n_trials={victim_n}"
    return True, "ok"


def pid_check(arm: str, ways: int, tenant_pid: int | None,
              pid_in_clos: bool | None) -> tuple[bool, str]:
    if ways <= 0:
        return True, "ok"
    if tenant_pid is None or tenant_pid <= 0:
        return False, f"arm {arm} CAT without tenant_pid"
    if not pid_in_clos:
        return False, f"arm {arm} pid {tenant_pid} not in clos_b/tasks"
    return True, "ok"


def query_cost(t_arm: float | None, t_wb: float | None) -> float | None:
    """Positive = arm slower than wb.  Seconds, not tuples/s."""
    if t_arm is None or t_wb is None or t_wb <= 0:
        return None
    return (t_arm / t_wb) - 1.0


RUNTIME_RE = re.compile(r"Run Time \(s\): real ([0-9.]+)")


def parse_duckdb_output(text: str) -> dict:
    """Parse `-json` + `.timer` output with BEGIN/END markers.

    Marker SELECTs must be issued with `.timer off` so their Run Time lines
    do not mix into the join times.
    """
    times = [float(x) for x in RUNTIME_RE.findall(text)]
    matches: list[int] = []
    sums: list[str] = []
    begin = False
    end = False
    after_begin = False
    meas_matches: list[int] = []
    meas_sums: list[str] = []
    meas_times: list[float] = []
    time_i = 0
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Run Time"):
            # already captured in `times`; advance pairing below via time_i
            continue
        if not (line.startswith("[") and line.endswith("]")):
            continue
        try:
            arr = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not arr or not isinstance(arr, list):
            continue
        obj = arr[0]
        if not isinstance(obj, dict):
            continue
        if obj.get("marker") == "DUCKDB_MEASURE_BEGIN":
            begin = True
            after_begin = True
            continue
        if obj.get("marker") == "DUCKDB_MEASURE_END":
            end = True
            after_begin = False
            continue
        if "count_star()" in obj:
            c = int(obj["count_star()"])
            s = str(obj.get("sum(b.payload)", obj.get("sum(payload)", "")))
            matches.append(c)
            sums.append(s)
            if after_begin:
                meas_matches.append(c)
                meas_sums.append(s)
    # Pair timer lines: warmup times first, then measured, in order.
    # With 1 warmup + N measured and timer off around markers, times has
    # warmup + measured entries in that order.
    n_meas_rows = len(meas_matches)
    n_all = len(matches)
    n_warm = n_all - n_meas_rows
    if n_warm < 0:
        n_warm = 0
    if len(times) >= n_warm + n_meas_rows and n_meas_rows:
        meas_times = times[n_warm:n_warm + n_meas_rows]
    elif n_meas_rows and len(times) >= n_meas_rows:
        meas_times = times[-n_meas_rows:]
    else:
        meas_times = times[1:] if len(times) > 1 else times[:]
    return dict(
        times_all=times,
        times_measured=meas_times,
        matches_all=matches,
        sums_all=sums,
        matches_measured=meas_matches,
        sums_measured=meas_sums,
        begin=begin,
        end=end,
    )


def checksum_of(parsed: dict) -> tuple[int | None, str | None]:
    ms = parsed.get("matches_measured") or parsed.get("matches_all") or []
    ss = parsed.get("sums_measured") or parsed.get("sums_all") or []
    if not ms:
        return None, None
    if len(set(ms)) != 1:
        return None, None
    return int(ms[0]), (ss[0] if ss else None)


def self_test() -> None:
    failures: list[str] = []

    def expect(ok: bool, pred: bool, label: str) -> None:
        if ok != pred:
            failures.append(label)

    r, _ = idle_check(16.97, ["bash", "ssh"])
    expect(r, False, "idle must fail on load 16.97")
    r, _ = idle_check(0.0, ["bash", "duckdb", "sshd"])
    expect(r, False, "idle must fail on duckdb in comm")
    r, _ = idle_check(0.0, ["bash", "gem5.opt"])
    expect(r, False, "idle must fail on gem5.opt")
    r, _ = idle_check(0.1, ["bash", "ssh", "tmux: server"])
    expect(r, True, "idle must pass on an empty host")

    r, _ = host_check("mos181")
    expect(r, False, "mos181 is not this campaign")
    r, _ = host_check("mos182")
    expect(r, True, "mos182 is the campaign host")
    r, _ = host_check("c4")
    expect(r, True, "c4 is the campaign host")
    r, _ = host_check("mos181", smoke=True)
    expect(r, True, "smoke may run on mos181")

    r, _ = geom_check(WANT_N, WANT_PROBE, WANT_CHAIN)
    expect(r, True, "registered N/P/chain")
    r, _ = geom_check(WANT_N, WANT_PROBE, 1)
    expect(r, True, "joinuniq at same N")
    r, _ = geom_check(750_000, WANT_PROBE, WANT_CHAIN)
    expect(r, False, "wrong N must fail")
    r, _ = geom_check(WANT_N, 1_000_000, WANT_CHAIN)
    expect(r, False, "A2 probe must fail (not the registered P)")

    r, _ = version_check("v1.1.3 19864453f7")
    expect(r, True, "v1.1.3")
    r, _ = version_check("v1.2.0")
    expect(r, False, "other duckdb version")

    r, _ = threads_check("SET threads=1;\n.timer on\n")
    expect(r, True, "threads=1")
    r, _ = threads_check("SET threads=8;\n")
    expect(r, False, "threads=8")

    r, _ = identity_check("wb")
    expect(r, True, "wb identity")
    r, _ = identity_check("nta", policy="nta", pf_distance=32)
    expect(r, False, "nta is not an arm")
    r, _ = identity_check("fb256k", join_path="flushbehind", flush_distance=262144)
    expect(r, False, "fb is not an arm")
    r, _ = identity_check("wb", policy="stream")
    expect(r, False, "STREAMING policy is not an arm")

    r, _ = live_check(0.4, 100, 100, 5, "wb")
    expect(r, True, "live matching checksum")
    r, _ = live_check(0.4, 99, 100, 5, "wb")
    expect(r, False, "live mismatched checksum")
    r, _ = live_check(0.0, 100, 100, 5, "wb")
    expect(r, False, "live zero query seconds")
    r, _ = live_check(0.4, 100, 100, 0, "wb")
    expect(r, False, "live zero victim trials")

    r, _ = pid_check("cat01", 1, 1234, True)
    expect(r, True, "pid in clos")
    r, _ = pid_check("cat01", 1, 1234, False)
    expect(r, False, "pid missing from clos")
    r, _ = pid_check("wb", 0, None, None)
    expect(r, True, "wb has no clos pid")

    fixture = (
        '[{"count_star()":256,"sum(b.payload)":"55552"}]\n'
        "Run Time (s): real 0.002 user 0.001 sys 0.000\n"
        '[{"marker":"DUCKDB_MEASURE_BEGIN"}]\n'
        '[{"count_star()":256,"sum(b.payload)":"55552"}]\n'
        "Run Time (s): real 0.010 user 0.009 sys 0.000\n"
        '[{"count_star()":256,"sum(b.payload)":"55552"}]\n'
        "Run Time (s): real 0.011 user 0.010 sys 0.000\n"
        '[{"marker":"DUCKDB_MEASURE_END"}]\n'
    )
    p = parse_duckdb_output(fixture)
    if not p["begin"] or not p["end"]:
        failures.append("parser missed BEGIN/END")
    if p["times_measured"] != [0.010, 0.011]:
        failures.append(f"measured times {p['times_measured']}")
    if p["matches_measured"] != [256, 256]:
        failures.append(f"measured matches {p['matches_measured']}")
    c, s = checksum_of(p)
    if c != 256 or s != "55552":
        failures.append(f"checksum {c} {s}")

    if abs((query_cost(1.10, 1.00) or 0) - 0.10) > 1e-12:
        failures.append("query_cost 10%")
    if query_cost(0.95, 1.00) >= 0:
        failures.append("query_cost faster than wb should be negative")

    # R(N)/LLC is the registered 0.53 ratio.
    ratio = WANT_R_BYTES / LLC_BYTES
    if abs(ratio - 32 / 60) > 1e-5:
        failures.append(f"R/LLC {ratio} != 32/60")

    if failures:
        raise SystemExit("GATES SELF-TEST FAILED:\n  " + "\n  ".join(failures))


if __name__ == "__main__":
    self_test()
    print("duckdb tenant-cat gates self-test: all negative and positive cases behaved")
