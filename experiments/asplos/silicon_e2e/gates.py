"""Admission gates for the silicon hash-join e2e campaign.

Every function here is pure in the values it is given, so a check can be fed
input that *should* fail -- a gate that cannot fail is not a gate.  The runner
calls self_test() before the first arm.

G-idle looks at /proc/*/comm, never at the full command line: `pgrep -f gem5`
matching the invoking shell is a failure this project has paid for four times.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "lib"))
from dutyfree import resctrl  # noqa: E402

FOREIGN_COMM = frozenset({
    "gem5.opt", "gem5.debug", "gem5.fast",
    "cxl_join_bench", "pointer_chase", "stream_wb", "stream_wc",
    "db_bench",
})

# Operational pin: see SILICON_E2E_PREREGISTRATION operational section.
# 0.5 is unreachable in the inter-arm gap after our own tenant.
LOAD_MAX = 8.0

WANT_FACT_BYTES = 8 * 1024 * 1024 * 1024
WANT_HOT_BYTES = 32 * 1024 * 1024
CALIB_FACT_BYTES = 256 * 1024 * 1024


def idle_check(load1: float, comms: list[str], load_max: float = LOAD_MAX) -> tuple[bool, str]:
    """G-idle.  `comms` are /proc/*/comm values, not command lines."""
    if load1 >= load_max:
        return False, f"load1={load1:.2f} >= {load_max}"
    foreign = sorted({c for c in comms if c in FOREIGN_COMM})
    if foreign:
        return False, f"foreign processes: {foreign}"
    return True, "ok"


def mask_check(got_hex: str | None, ways: int) -> tuple[bool, str]:
    """G-mask: compare as integers.  ways=0 means no CLOS, got must be None."""
    if ways <= 0:
        if got_hex is None:
            return True, "ok"
        return False, f"unmasked arm recorded a mask: {got_hex}"
    want = hex((1 << ways) - 1)
    if not resctrl.mask_equal(got_hex, want):
        return False, f"mask got={got_hex!r} want={want} (ways={ways})"
    return True, "ok"


def mask_held_check(mask_got, mask_got_after, ways,
                    clos_cpus_after=None, tenant_cpu=None, victim_cpu=None,
                    clos_b_present_after=None) -> tuple[bool, str]:
    """G-mask-after: post-rep re-read.  Closes the setup-then-measure TOCTOU.

    A missing field is not this function's concern — the analyzer skips the
    check when the key is absent (legacy JSONL).  Callers that *did* re-read
    must pass the values they got.
    """
    if ways <= 0:
        if mask_got_after is not None:
            return False, (f"unmasked arm had clos mask after measure: "
                           f"{mask_got_after}")
        if clos_b_present_after:
            return False, "unmasked arm: clos_b present after measure"
        return True, "ok"
    ok, why = mask_check(mask_got_after, ways)
    if not ok:
        return False, f"post-rep mask: {why}"
    if mask_got is not None and not resctrl.mask_equal(mask_got, mask_got_after):
        return False, (f"mask changed during measure before={mask_got!r} "
                       f"after={mask_got_after!r}")
    if (clos_cpus_after is not None and tenant_cpu is not None
            and victim_cpu is not None):
        ok, why = clos_check(str(clos_cpus_after), int(tenant_cpu),
                             int(victim_cpu))
        if not ok:
            return False, f"post-rep clos: {why}"
    return True, "ok"


def parse_cpu_list(spec: str) -> set[int]:
    cpus: set[int] = set()
    spec = (spec or "").strip()
    if not spec:
        return cpus
    for tok in spec.split(","):
        tok = tok.strip()
        if not tok:
            continue
        if "-" in tok:
            a, b = tok.split("-", 1)
            cpus.update(range(int(a), int(b) + 1))
        else:
            cpus.add(int(tok))
    return cpus


def clos_check(tenant_cpus_list: str, tenant_cpu: int, victim_cpu: int) -> tuple[bool, str]:
    """G-clos: tenant CPU is in the tenant CLOS; victim is not.

    A CPU in a CTRL_MON group silently adopts that group's RMID.  Putting the
    victim in the tenant group made every occupancy sample read 0.0 KB once.
    """
    members = parse_cpu_list(tenant_cpus_list)
    if tenant_cpu not in members:
        return False, f"tenant cpu {tenant_cpu} not in clos cpus_list={tenant_cpus_list!r}"
    if victim_cpu in members:
        return False, (f"victim cpu {victim_cpu} is in the tenant CLOS "
                       f"{tenant_cpus_list!r} (RMID collision)")
    return True, "ok"


def parse_victim_cycles(text: str) -> list[float]:
    """Incremental parse.  Killing pointer_chase truncates its JSON array;
    a whole-document json.loads then returns nothing and every reading is null.
    """
    return [float(m) for m in re.findall(r'"cycles_per_load":\s*([0-9.]+)', text)]


def hot_table_rounded(stderr_text: str) -> bool:
    return "HOT_TABLE_ROUNDED" in stderr_text


def size_check(fact_bytes: int, instantiated_hot: int, stderr_text: str,
               want_fact: int = WANT_FACT_BYTES,
               want_hot: int = WANT_HOT_BYTES) -> tuple[bool, str]:
    """G-size: realized sizes, and the rounding warning must be absent."""
    if hot_table_rounded(stderr_text):
        return False, "HOT_TABLE_ROUNDED present"
    if fact_bytes != want_fact:
        return False, f"fact_bytes={fact_bytes} want={want_fact}"
    if instantiated_hot != want_hot:
        return False, f"instantiated_hot_bytes={instantiated_hot} want={want_hot}"
    return True, "ok"


def fb_identity_check(arm: str, join_path: str, flush_distance: int) -> tuple[bool, str]:
    """S5.1: an fb arm's identity comes from the artifact, not the launcher."""
    if arm.startswith("fb"):
        if join_path != "flushbehind" or flush_distance <= 0:
            return False, (f"arm {arm} is not flush-behind in the artifact "
                           f"(join_path={join_path!r} flush_distance={flush_distance})")
        return True, "ok"
    if join_path == "flushbehind" or flush_distance > 0:
        return False, f"arm {arm} unexpectedly flush-behind"
    return True, "ok"


def nta_identity_check(arm: str, policy: str, pf_distance: int) -> tuple[bool, str]:
    if arm == "nta":
        if policy != "nta" or pf_distance <= 0:
            return False, f"arm nta policy={policy!r} pf_distance={pf_distance}"
        return True, "ok"
    if policy == "nta":
        return False, f"arm {arm} has policy nta"
    return True, "ok"


def live_check(mtuples: float | None, matches: int | None,
               ref_matches: int | None) -> tuple[bool, str]:
    """G-live: tenant produced work, and the checksum matches the reference arm."""
    if mtuples is None or mtuples <= 0:
        return False, f"join_mtuples_per_s={mtuples}"
    if matches is None or matches <= 0:
        return False, f"matches={matches}"
    if ref_matches is not None and matches != ref_matches:
        return False, f"matches={matches} != reference {ref_matches}"
    return True, "ok"


def self_test() -> None:
    """Feed each gate a case that must fail, then a case that must pass.

    Called by the runner before any arm.  If a check cannot fail, we find out
    here rather than in the JSONL.
    """
    failures: list[str] = []

    def expect(ok: bool, pred: bool, label: str) -> None:
        if ok != pred:
            failures.append(label)

    r, _ = idle_check(16.97, ["bash", "ssh"])
    expect(r, False, "idle must fail on load 16.97")
    r, _ = idle_check(0.0, ["bash", "gem5.opt", "sshd"])
    expect(r, False, "idle must fail on gem5.opt in comm")
    r, _ = idle_check(0.0, ["bash", "ssh", "tmux: server"])
    expect(r, True, "idle must pass on an empty host")
    # The pgrep-self-match case: a command line containing the word is irrelevant
    # because we look at comm, not argv.
    r, _ = idle_check(0.1, ["bash", "ssh"])
    expect(r, True, "idle must ignore ssh argv")

    r, _ = mask_check("00ff", 8)
    expect(r, True, "mask 00ff == 8 ways (kernel normalisation)")
    r, _ = mask_check("ff", 4)
    expect(r, False, "mask ff is not 4 ways")
    r, _ = mask_check(None, 4)
    expect(r, False, "missing mask on a CAT arm")
    r, _ = mask_check(None, 0)
    expect(r, True, "no mask on wb")
    r, _ = mask_check("7fff", 15)
    expect(r, True, "mask 7fff == 15 ways")

    r, _ = mask_held_check("f", "f", 4, "4", 4, 6, True)
    expect(r, True, "mask held through the measure")
    r, _ = mask_held_check("f", None, 4, "", 4, 6, False)
    expect(r, False, "mask deleted after setup must fail")
    r, _ = mask_held_check("f", "7", 4, "4", 4, 6, True)
    expect(r, False, "mask mutated during measure must fail")
    r, _ = mask_held_check(None, None, 0, "", 4, 6, False)
    expect(r, True, "unmasked arm still has no clos")
    r, _ = mask_held_check(None, "f", 0, "4", 4, 6, True)
    expect(r, False, "unmasked arm must not grow a clos")

    r, _ = clos_check("4", 4, 6)
    expect(r, True, "clos tenant=4 victim=6")
    r, _ = clos_check("4,6", 4, 6)
    expect(r, False, "clos must fail when victim shares the tenant group")
    r, _ = clos_check("0", 4, 6)
    expect(r, False, "clos must fail when tenant CPU is not in the group")

    truncated = '[\n  {"trial": 0, "cycles_per_load": 73.398,\n'
    v = parse_victim_cycles(truncated)
    if v != [73.398]:
        failures.append(f"truncated victim parse got {v}")
    if parse_victim_cycles("") != []:
        failures.append("empty victim parse")

    r, _ = size_check(WANT_FACT_BYTES, WANT_HOT_BYTES, "JOIN_MEASURE_BEGIN\n")
    expect(r, True, "size exact 8GiB/32MiB")
    r, _ = size_check(WANT_FACT_BYTES, WANT_HOT_BYTES,
                      "HOT_TABLE_ROUNDED requested_bytes=1 instantiated_bytes=2\n")
    expect(r, False, "size must fail on HOT_TABLE_ROUNDED")
    r, _ = size_check(1 << 30, WANT_HOT_BYTES, "")
    expect(r, False, "size must fail on a 1GiB fact reported as 8GiB")

    r, _ = fb_identity_check("fb256k", "flushbehind", 262144)
    expect(r, True, "fb identity")
    r, _ = fb_identity_check("fb256k", "join_range", 262144)
    expect(r, False, "fb must fail when join_path is join_range")
    r, _ = fb_identity_check("wb", "join_range", 0)
    expect(r, True, "wb is not fb")

    r, _ = nta_identity_check("nta", "nta", 32)
    expect(r, True, "nta identity")
    r, _ = nta_identity_check("nta", "nta", 0)
    expect(r, False, "nta with pf_distance 0 is not nta")
    r, _ = nta_identity_check("wb", "wb", 0)
    expect(r, True, "wb is not nta")

    r, _ = live_check(25.0, 100, 100)
    expect(r, True, "live matching checksum")
    r, _ = live_check(25.0, 100, 99)
    expect(r, False, "live mismatched checksum")
    r, _ = live_check(0.0, 100, 100)
    expect(r, False, "live zero throughput")

    if failures:
        raise SystemExit("GATES SELF-TEST FAILED:\n  " + "\n  ".join(failures))


if __name__ == "__main__":
    self_test()
    print("gates self-test: all negative and positive cases behaved")
