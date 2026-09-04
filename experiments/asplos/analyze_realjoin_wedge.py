#!/usr/bin/env python3
"""Fail-closed analysis of the real-hash-join wedge.

Pre-registration: H2H_REALJOIN_PREREG_2026-09-01.md
Usage: analyze_realjoin_wedge.py <rj_runs.jsonl> <runs-root-dir>

Metrics are computed by experiments/lib/archive_gem5_runs.py, identically to the
fused campaign (cyc_per_load = cpu0.numCycles / retired cpu0 loads in the
post-tenant-reset window, tenant_ipc = cpu1.ipc), so
the two results are directly comparable.  This script only gates and reduces.
"""
import json
import re
import statistics as st
import sys
from pathlib import Path

ARMS = ("qui", "wb", "cat4", "cat10", "h2")
EXPECT_MASK = {"qui": 0, "wb": 0, "cat4": 0xF, "cat10": 0x3FF, "h2": 0}
SEEDS = 3
VICTIM_ITERS = 12000000
# Addendum 2 of H2H_REALJOIN_PREREG_2026-09-01.md superseded the original
# 16 MiB object with this 8 MiB fact stream before metric-B arms launched.
# Keep the analyzer tied to the realized, registered correction rather than the
# obsolete original design.
FACT_BYTES = 8 * 1024 * 1024
HOT_BYTES = 4 * 1024 * 1024
# The tenant resets stats after its own setup, so the measured window covers
# FEWER than VICTIM_ITERS accesses.  Dividing by VICTIM_ITERS would be wrong;
# the denominator is the victim loads actually retired in the window.
# A contended arm whose victim_loads ~= VICTIM_ITERS means the tenant never
# reached its reset -- i.e. it died in setup, which is exactly the failure
# that voided the superseded campaign.
WINDOW_LOADS_MIN = 1_000_000
# Calibrated against measurement, not guessed.  Tenant setup is ~185M cycles and
# the victim is ~3.6x slower during it, so it consumes only ~1.2-1.5M of the 12M
# budget -- leaving ~90.1% (h2 10,810,055; wb 10,812,896; cat4 10,549,458).  A
# 0.90 cap rejected h2 and wb, the two arms the campaign exists to measure.  The
# gate must separate "reset fired" from "reset never fired", and the latter is
# unambiguous: it returns EXACTLY the tenant-free count (12,001,060).
WINDOW_LOADS_MAX_FRAC = 0.97
# Registered thresholds. Changing one after seeing the data invalidates the run.
PROT_MIN = 0.85          # each mechanism must protect at least this much
PROT_SPREAD_MAX = 0.05   # and they must be matched within 5 pp
WEDGE_MIN = 0.08         # P1: h2 tenant IPC over the better CAT arm
P2_TAX_MIN = 1.30        # WB must actually pollute
P3_BAND = 0.03           # P3: h2 within +-3% of wb tenant IPC

# Fused campaign, for comparison only -- never a gate (data/gem5/fh_runs.jsonl).
# The archived fused numbers (33.881 / 52.756 / IPC 0.3503 ...) are cyc_per_ACCESS
# over a window that INCLUDED the tenant's initialisation.  They are NOT
# comparable to cyc_per_load measured after a tenant-side reset, so this script
# does not compare against them.  fused.c carries the same confound the join did
# -- its own first-touch of 19 MB sat inside the old window -- so the published
# +17.1% fused wedge is itself diluted by an unmeasured amount.  The fused
# reference is re-run inside this campaign under the identical metric and window.
FUSED_REF_ARMS = ("fqui", "fwb", "fh2", "fcat4", "fcat10")


def logtext(root, run):
    p = Path(root) / f"{run}.log"
    return p.read_text(errors="replace") if p.exists() else ""


def guest_json(log):
    """The tenant's own JSON record, for realized (not requested) geometry."""
    for line in log.splitlines():
        line = line.strip()
        if line.startswith("{") and '"mode"' in line:
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
    return {}


def mark(name, ok, detail):
    print(f"  {name:38s} {'PASS' if ok else 'FAIL'}  {detail}")
    return ok


def mask_int(v):
    """requestor_masks is a space-separated vector; compare as ints, never text.

    Comparing these as strings produced a false ALARM on 24 of 36 cells once.
    """
    if v is None:
        return None
    toks = [t for t in str(v).replace(",", " ").split() if t]
    vals = []
    for t in toks:
        try:
            vals.append(int(t, 0))
        except ValueError:
            return None
    return max(vals) if vals else 0


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip())
        return 2
    rows = [json.loads(l) for l in Path(argv[1]).read_text().splitlines() if l.strip()]
    root = argv[2]
    by = {}
    for r in rows:
        m = re.match(r"r(?:j|[0-9])_([a-z0-9]+)_s(\d+)$", r["run"])
        if m:
            by.setdefault(m.group(1), []).append(r)

    gates = []
    # ---- A1/A2/A3/A4/A5, per arm ----
    for a in ARMS:
        g = by.get(a, [])
        print(f"===== {a} ({len(g)} runs) =====")
        gates.append(mark("A1 completed with stats", len(g) == SEEDS and all(x.get("completed") for x in g),
                          f"{sum(1 for x in g if x.get('completed'))}/{SEEDS} completed"))
        if a == "qui":
            gates.append(mark("A2 tenant ran", True, "n/a (dummy tenant by design)"))
        else:
            ins = [x.get("tenant_cycles") or 0 for x in g]
            gates.append(mark("A2 tenant ran and contended", all(v > 0 for v in ins),
                              f"cpu1 cycles min={min(ins) if ins else 0:,.0f}"))
        # `realized_table_mb` parses fused.c's "REALIZED n MB" line, which the
        # join never emits -- gating on it would be vacuously true (None).  The
        # join's JSON reports the REQUESTED hot_bytes, which is exactly the F9
        # trap.  So check the two things that are actually informative: the
        # request is what we intended, and the guest did NOT report quantizing
        # it.  4 MiB is 2^18 entries of 16 B, so silence means realized == 4 MiB.
        geo, bad = True, []
        for x in g:
            if a == "qui":
                continue
            log = logtext(root, x["run"])
            if "HOT_TABLE_ROUNDED" in log:
                geo = False; bad.append(f"{x['run']}: guest reported rounding")
            # The tenant runs --reps 100 and is truncated by the victim's
            # m5_exit, so it NEVER reaches emit_json_prefix.  Reading realized
            # geometry from its JSON is unimplementable by construction -- the
            # original A3 could not pass in this design.  Use what the guest
            # prints EARLY: BIND_POOL states the realized fact size at
            # allocation, and HOT_TABLE_ROUNDED appears iff the table was
            # quantized, so its silence establishes exactness.
            if f"bytes={FACT_BYTES}" not in log:
                geo = False; bad.append(f"{x['run']}: no BIND_POOL bytes={FACT_BYTES}")
            if f"--hot-bytes {HOT_BYTES}" not in log:
                geo = False; bad.append(f"{x['run']}: --hot-bytes != {HOT_BYTES}")
        gates.append(mark("A3 realized geometry as designed", geo,
                          "; ".join(bad) if bad
                          else ("n/a (dummy tenant)" if a == "qui"
                                else f"BIND_POOL fact={FACT_BYTES} realized; --hot-bytes {HOT_BYTES} "
                                     f"requested; no HOT_TABLE_ROUNDED")))
        masks = {mask_int(x.get("hnf_requestor_masks")) for x in g}
        gates.append(mark("A4 realized way mask matches arm", masks == {EXPECT_MASK[a]},
                          f"config.ini={masks} expected={{{EXPECT_MASK[a]:#x}}} (compared as ints)"))
        pol = {x.get("hnf_policy") for x in g}
        gates.append(mark("A4b LRU on every arm", pol == {"LRURP"},
                          f"replacement_policy={pol}"))
        vl = [x.get("victim_loads") for x in g]
        if a == "qui":
            ok = all(isinstance(v,(int,float)) and v >= WINDOW_LOADS_MIN for v in vl)
            det = f"victim_loads={[int(v) if v else None for v in vl]} (no tenant reset by design)"
        else:
            ok = all(isinstance(v,(int,float)) and WINDOW_LOADS_MIN <= v
                     <= WINDOW_LOADS_MAX_FRAC*VICTIM_ITERS for v in vl)
            det = (f"victim_loads={[int(v) if v else None for v in vl]} "
                   f"(need {WINDOW_LOADS_MIN:,}..{int(WINDOW_LOADS_MAX_FRAC*VICTIM_ITERS):,}; "
                   f"~={VICTIM_ITERS:,} would mean the tenant never reached its reset)")
        gates.append(mark("A6 tenant reset fired, window sane", ok, det))
        decl = {bool(x.get("declared_streaming")) for x in g}
        gates.append(mark("A5 streaming declared iff h2", decl == {a == "h2"},
                          f"declared={decl}"))
        # declared_streaming only proves the token reached argv.  This proves the
        # HNF actually declined an allocation it would otherwise have made.
        byp = [x.get("hnf_streaming_bypasses") for x in g]
        if a == "h2":
            ok = all(isinstance(v, (int, float)) and v > 0 for v in byp)
            det = f"bypasses={[None if v is None else int(v) for v in byp]} (each must be >0)"
        else:
            ok = all(v in (0, 0.0, None) for v in byp)
            det = f"bypasses={[None if v is None else int(v) for v in byp]} (each must be 0)"
        gates.append(mark("A5b mechanism engaged iff h2", ok, det))

    if not all(gates):
        print("===== VERDICT =====")
        print("FAIL: apparatus gates did not pass; no wedge is licensed")
        return 1

    # ---- reduction ----
    def mean(a, k):
        return st.mean([x[k] for x in by[a] if x.get(k) is not None])

    def spread(a, k):
        v = [x[k] for x in by[a] if x.get(k) is not None]
        return max(v) - min(v)

    q, w = mean("qui", "cyc_per_load"), mean("wb", "cyc_per_load")
    print("===== RESULTS =====")
    print(f"  {'arm':7s} {'victim cyc/load':>15s} {'spread':>8s} {'protection':>11s} "
          f"{'tenant IPC':>11s} {'vs wb':>9s}")
    prot, ipc = {}, {}
    for a in ARMS:
        c = mean(a, "cyc_per_load")
        p = (w - c) / (w - q) if a not in ("qui", "wb") else None
        ti = mean(a, "tenant_ipc") if a != "qui" else None
        if p is not None:
            prot[a] = p
        if ti is not None:
            ipc[a] = ti
        vs_wb = "--"
        if ti is not None and a != "wb":
            vs_wb = f"{(ti / mean('wb', 'tenant_ipc') - 1) * 100:+.2f}%"
        print(f"  {a:7s} {c:>15.3f} {spread(a,'cyc_per_load'):>8.3f} "
              f"{(f'{p*100:.2f}%' if p is not None else '--'):>11s} "
              f"{(f'{ti:.4f}' if ti is not None else '--'):>11s} "
              f"{vs_wb:>9s}")

    print("\n===== REGISTERED PREDICTIONS =====")
    tax = w / q
    p2 = mark("P2 WB actually pollutes", tax >= P2_TAX_MIN,
              f"tax={tax:.4f}x (need >={P2_TAX_MIN}x)")
    matched = (min(prot.values()) >= PROT_MIN
               and max(prot.values()) - min(prot.values()) <= PROT_SPREAD_MAX)
    mark("   protection matched across arms", matched,
         f"range {min(prot.values())*100:.2f}-{max(prot.values())*100:.2f}% "
         f"(need each >={PROT_MIN*100:.0f}%, spread <={PROT_SPREAD_MAX*100:.0f}pp)")
    best_cat = max(("cat4", "cat10"), key=lambda a: ipc[a])
    wedge = ipc["h2"] / ipc[best_cat] - 1
    p1 = mark("P1 WEDGE at matched protection", matched and wedge >= WEDGE_MIN,
              f"h2 {ipc['h2']:.4f} vs {best_cat} {ipc[best_cat]:.4f} = {wedge*100:+.2f}% "
              f"(need >=+{WEDGE_MIN*100:.0f}%)")
    p3 = mark("P3 H2 is free to the streamer", abs(ipc["h2"] / ipc["wb"] - 1) <= P3_BAND,
              f"h2/wb = {(ipc['h2']/ipc['wb']-1)*100:+.2f}% (need within +-{P3_BAND*100:.0f}%)")

    print("\n===== P4 (exploratory, not a gate): versus the fused tenant =====")
    have = [a for a in FUSED_REF_ARMS if by.get(a)]
    # Amendment 1 (A1.3) WITHDRAWS this comparison unless the two workloads
    # share a measurement window.  They do not: fused's initialisation is short
    # enough that the VICTIM's reset lands last (victim_loads == the tenant-free
    # 12,001,060), whereas the join's 185M-cycle setup means the TENANT's reset
    # lands last (~10.8M).  Refuse to print a ratio across different windows.
    if len(have) == len(FUSED_REF_ARMS):
        vl_f = mean("fh2", "victim_loads"); vl_j = mean("h2", "victim_loads")
        if not vl_f or not vl_j or abs(vl_f - vl_j) / max(vl_f, vl_j) > 0.02:
            print(f"  SUPPRESSED per prereg amendment A1.3: window mismatch -- "
                  f"fused victim_loads={vl_f:,.0f} vs real-join {vl_j:,.0f} "
                  f"({abs(vl_f-vl_j)/max(vl_f,vl_j)*100:.1f}% apart). The fused "
                  f"reference must be re-run phase-aligned before any ratio is quoted.")
            have = []
    if len(have) == len(FUSED_REF_ARMS):
        fq = mean("fqui", "cyc_per_load"); fwb = mean("fwb", "cyc_per_load")
        fh2_ipc = mean("fh2", "tenant_ipc")
        fcat = max(("fcat4", "fcat10"), key=lambda a: mean(a, "tenant_ipc"))
        fcat_ipc = mean(fcat, "tenant_ipc")
        fw = fh2_ipc / fcat_ipc - 1
        print(f"  fused wedge, same metric and window  {fw*100:+.2f}%  "
              f"(fh2 {fh2_ipc:.4f} vs {fcat} {fcat_ipc:.4f}; fused WB tax {fwb/fq:.4f}x)")
        print(f"  real-join wedge                      {wedge*100:+.2f}%  "
              f"(h2 {ipc['h2']:.4f} vs {best_cat} {ipc[best_cat]:.4f})")
        print(f"  direction: real join is "
              f"{'LARGER' if wedge > fw else 'SMALLER'} by {abs(wedge - fw)*100:.2f} pp"
              f" -- reported as measured; no direction was registered")
    else:
        print(f"  fused reference arms present: {have} -- incomplete, no comparison made.")
        print("  The archived fused numbers are cyc_per_access over a window that")
        print("  included tenant setup, and are NOT comparable to this metric.")
    print("\n===== VERDICT =====")
    ok = p1 and p2 and p3
    print("PASS: the wedge reproduces on a real hash join" if ok
          else "MIXED/FAIL: see refuted predictions above (report them as refuted)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
