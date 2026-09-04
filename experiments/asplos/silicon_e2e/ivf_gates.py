"""Admission gates for the IVF-Flat silicon scaffold.

Pure functions.  The runner calls self_test() before any arm.  STREAMING is
not an arm.  Hash-join gates.py is not modified.
"""
from __future__ import annotations

RATIO_LO = 0.50
RATIO_HI = 0.55
WANT_CODEBOOK_BYTES = 32 * 1024 * 1024
WANT_LLC_BYTES = 60 * 1024 * 1024
WANT_NLIST = 8192
WANT_DIM = 1024

FOREIGN_COMM = frozenset({
    "gem5.opt", "gem5.debug", "gem5.fast",
    "cxl_join_bench", "ivf_flat_bench", "pointer_chase",
    "stream_wb", "stream_wc", "db_bench",
})
LOAD_MAX = 8.0


def idle_check(load1: float, comms: list[str], load_max: float = LOAD_MAX) -> tuple[bool, str]:
    if load1 >= load_max:
        return False, f"load1={load1:.2f} >= {load_max}"
    foreign = sorted({c for c in comms if c in FOREIGN_COMM})
    if foreign:
        return False, f"foreign processes: {foreign}"
    return True, "ok"


def ratio_check(codebook_bytes: int, llc_bytes: int,
                lo: float = RATIO_LO, hi: float = RATIO_HI) -> tuple[bool, str]:
    if llc_bytes <= 0:
        return False, "llc_bytes=0"
    r = codebook_bytes / llc_bytes
    if r < lo or r > hi:
        return False, (f"codebook/LLC={r:.6f} outside [{lo}, {hi}] "
                       f"(codebook_bytes={codebook_bytes} llc_bytes={llc_bytes})")
    return True, "ok"


def codebook_size_check(nlist: int, dim: int, codebook_bytes: int,
                        want: int = WANT_CODEBOOK_BYTES) -> tuple[bool, str]:
    expect = nlist * dim * 4
    if codebook_bytes != expect:
        return False, f"codebook_bytes={codebook_bytes} != nlist*dim*4={expect}"
    if codebook_bytes != want:
        return False, f"codebook_bytes={codebook_bytes} want={want} (32 MiB silicon)"
    return True, "ok"


def recall_check(recall: float | None) -> tuple[bool, str]:
    if recall is None:
        return False, "recall_at_k missing"
    if not (0.0 < float(recall) <= 1.0):
        return False, f"recall_at_k={recall} not in (0, 1]"
    return True, "ok"


def fb_identity_check(arm: str, list_path: str, flush_distance: int) -> tuple[bool, str]:
    if arm.startswith("fb"):
        if list_path != "flushbehind" or flush_distance <= 0:
            return False, (f"arm {arm} is not flush-behind "
                           f"(list_path={list_path!r} flush_distance={flush_distance})")
        return True, "ok"
    if list_path == "flushbehind" or flush_distance > 0:
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


def live_check(qps: float | None, id_sum: int | None,
               ref_id_sum: int | None) -> tuple[bool, str]:
    if qps is None or qps <= 0:
        return False, f"qps={qps}"
    if id_sum is None:
        return False, "id_sum missing"
    if ref_id_sum is not None and id_sum != ref_id_sum:
        return False, f"id_sum={id_sum} != reference {ref_id_sum}"
    return True, "ok"


def cat_tax_material(qps_wb: float, qps_cat: float, min_rel: float = 0.10) -> tuple[bool, str]:
    """Kill: CAT tenant QPS tax too small ⇒ do not run gem5 H2."""
    if qps_wb <= 0 or qps_cat <= 0:
        return False, f"qps_wb={qps_wb} qps_cat={qps_cat}"
    tax = (qps_wb - qps_cat) / qps_wb
    if tax < min_rel:
        return False, (f"CAT QPS tax {tax:.4f} < {min_rel} "
                       "(do not run gem5 H2)")
    return True, "ok"


def self_test() -> None:
    failures: list[str] = []

    def expect(ok: bool, pred: bool, label: str) -> None:
        if ok != pred:
            failures.append(label)

    r, _ = idle_check(16.97, ["bash"])
    expect(r, False, "idle must fail on load 16.97")
    r, _ = idle_check(0.0, ["ivf_flat_bench"])
    expect(r, False, "idle must fail on ivf_flat_bench")
    r, _ = idle_check(0.0, ["bash", "ssh"])
    expect(r, True, "idle must pass on empty host")

    r, _ = ratio_check(512, WANT_LLC_BYTES)
    expect(r, False, "tiny codebook must fail ratio")
    r, _ = ratio_check(WANT_CODEBOOK_BYTES, WANT_LLC_BYTES)
    expect(r, True, "32/60 must pass ratio")
    r, _ = ratio_check(4 * 1024 * 1024, 7680 * 1024)
    expect(r, True, "4 MiB / 7680 KiB must pass ratio")

    r, _ = codebook_size_check(WANT_NLIST, WANT_DIM, WANT_CODEBOOK_BYTES)
    expect(r, True, "8192*1024*4 is 32 MiB")
    r, _ = codebook_size_check(8, 16, 512)
    expect(r, False, "tiny size must fail silicon want")

    r, _ = recall_check(0.0)
    expect(r, False, "recall 0 must fail")
    r, _ = recall_check(1.0)
    expect(r, True, "recall 1 must pass")
    r, _ = recall_check(None)
    expect(r, False, "missing recall must fail")

    r, _ = fb_identity_check("fb256k", "flushbehind", 262144)
    expect(r, True, "fb identity pass")
    r, _ = fb_identity_check("wb", "flushbehind", 64)
    expect(r, False, "wb must not be flushbehind")
    r, _ = nta_identity_check("nta", "nta", 32)
    expect(r, True, "nta identity pass")
    r, _ = nta_identity_check("wb", "nta", 32)
    expect(r, False, "wb must not be nta")

    r, _ = cat_tax_material(100.0, 95.0, 0.10)
    expect(r, False, "5% CAT tax is not material")
    r, _ = cat_tax_material(100.0, 80.0, 0.10)
    expect(r, True, "20% CAT tax is material")

    if failures:
        raise SystemExit("ivf_gates self-test failed: " + "; ".join(failures))
