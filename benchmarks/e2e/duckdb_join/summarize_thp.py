#!/usr/bin/env python3
"""A5.2: is the between-invocation spread on moscxl page placement, or physical?

The AMD co-run campaign yields no verdict because three arms exceed the 5%
CoV_rep bar, `FB256_match` worst at 13.10%. The variance is between invocations,
not within them, and within an arm the invocation's mean victim occupancy
predicts its median runtime at r = -0.82. One candidate: each repetition is a
fresh DuckDB process, the L3 is physically indexed, and the physical pages an
invocation happens to receive fix how well its reused set coexists with the
streamer for that invocation's lifetime.

A5.2's rule, fixed before the measurement:

  spread < 3% AND CoV_rep < 5%  -> page placement is the driver and is
      controllable; the A5.1 re-run proceeds with hugepages in the operating
      point and the change is named in the result.
  both essentially unchanged    -> not the driver; A5.1 clause 4 applies and
      the instability is reported as physical.
  anything between              -> no conclusion, and no re-run.

Estimators pinned in DUCKDB_JOIN_A52_RUN_DECISIONS.md before any data existed:
spread is the CoV of per-invocation MEAN occupancy (5.95% historically, the
preregistration's "6.2%"), CoV_rep is the CoV of per-invocation medians of
`trial_seconds_measured` (13.10% historically).

Two things can void the run before the rule is applied, and both are checked
here rather than left to the reader:

  * any repetition whose shim reported no huge pages -- a silently no-op shim
    produces a null indistinguishable from a real one;
  * a contemporaneous no-shim control that fails to reproduce the historical
    comparator -- if the comparator itself moved, nothing can be attributed.
"""
import json, statistics as st, sys
from collections import defaultdict

MIB = 2 ** 20
HIST = {"spread": 5.95, "cov_rep": 13.10}   # FB256_match, join_corun_moscxl.jsonl
SPREAD_THR, COV_THR = 3.0, 5.0
# "Essentially unchanged" needs a number or it is decided after the fact. The
# campaign's own tightest arm reproduces to 0.3% between independent sweeps, so
# a relative move of under 15% in both statistics is unchanged; this is stated
# in units of the historical value, not of the threshold.
UNCHANGED_REL = 0.15


def cov(v):
    return 100 * st.stdev(v) / st.mean(v) if len(v) > 1 else 0.0


def load(path):
    by = defaultdict(dict)
    for line in open(path):
        r = json.loads(line)
        by[r["arm"]][r["invocation"]] = r
    return by


def stats(recs):
    invs = sorted(recs)
    occ = [st.mean([int(x[1]) / MIB for x in recs[i]["occupancy_series"]]) for i in invs]
    med = [st.median(recs[i]["trial_seconds_measured"]) for i in invs]
    return occ, med, invs


def block(path, label):
    by = load(path)
    print(f"\n=== {label}  ({path}) ===")
    out = {}
    for arm in ("quiescent", "FB256_match"):
        if arm not in by:
            continue
        recs = by[arm]
        bad = [i for i in sorted(recs) if not recs[i]["valid"]]
        occ, med, invs = stats(recs)
        thp = [recs[i].get("victim_thp") for i in invs]
        huge = [t["anonhuge_kb"] // 1024 if t else 0 for t in thp]
        print(f"\n  {arm}   n={len(invs)}" + (f"   INVALID: {bad}" if bad else ""))
        print(f"    {'inv':<5}{'mean occ':>10}{'median s':>11}{'AnonHuge':>11}")
        for i, o, m, h in zip(invs, occ, med, huge):
            print(f"    {i:<5}{o:>9.3f}M{m:>11.4f}{(f'{h}M' if h else '--'):>11}")
        s, c = cov(occ), cov(med)
        print(f"    spread (CoV of mean occ) = {s:6.2f}%    "
              f"CoV_rep (runtime)  = {c:6.2f}%")
        print(f"    occ {min(occ):.2f}-{max(occ):.2f} MiB    "
              f"median {min(med):.4f}-{max(med):.4f} s")
        out[arm] = dict(spread=s, cov_rep=c, huge=huge, n=len(invs), bad=bad)
    return out


def main(ctl_path, thp_path):
    ctl = block(ctl_path, "BLOCK 1: no shim (contemporaneous control)")
    thp = block(thp_path, "BLOCK 2: hugepage-backed victim arena")

    print("\n" + "=" * 68)
    print("VALIDITY, checked before the rule is applied")
    print("=" * 68)
    ok = True

    zero = [i for i, h in enumerate(thp["FB256_match"]["huge"]) if h == 0]
    if zero:
        print(f"  FAIL  the shim reported no huge pages in reps {zero}.")
        print("        A no-op shim is indistinguishable from a real null.")
        ok = False
    else:
        h = thp["FB256_match"]["huge"]
        print(f"  pass  every shim repetition obtained huge pages "
              f"({min(h)}-{max(h)} MiB AnonHugePages)")
    ctl_h = [x for x in ctl["FB256_match"]["huge"] if x]
    print(f"  {'pass' if not ctl_h else 'FAIL'}  control repetitions obtained "
          f"none, as they must ({len(ctl_h)} did)")
    ok = ok and not ctl_h

    for k, name in (("spread", "spread"), ("cov_rep", "CoV_rep")):
        got, want = ctl["FB256_match"][k], HIST[k]
        rel = abs(got - want) / want
        verdict = "pass" if rel <= 0.30 else "FAIL"
        print(f"  {verdict}  control {name:8} {got:6.2f}% against the historical "
              f"{want:5.2f}%  ({100*rel:.0f}% relative)")
        ok = ok and rel <= 0.30

    if not ok:
        print("\n  The comparator is not reproduced, or the manipulation is not")
        print("  evidenced. A5.2 yields NO CONCLUSION and licenses no re-run.")
        return

    print("\n" + "=" * 68)
    print("A5.2 DECISION RULE")
    print("=" * 68)
    s, c = thp["FB256_match"]["spread"], thp["FB256_match"]["cov_rep"]
    print(f"  hugepage arm:  spread {s:.2f}% (threshold < {SPREAD_THR})   "
          f"CoV_rep {c:.2f}% (threshold < {COV_THR})")
    print(f"  control arm:   spread {ctl['FB256_match']['spread']:.2f}%          "
          f"        CoV_rep {ctl['FB256_match']['cov_rep']:.2f}%")

    passed = s < SPREAD_THR and c < COV_THR
    ds = abs(s - ctl["FB256_match"]["spread"]) / ctl["FB256_match"]["spread"]
    dc = abs(c - ctl["FB256_match"]["cov_rep"]) / ctl["FB256_match"]["cov_rep"]
    unchanged = ds <= UNCHANGED_REL and dc <= UNCHANGED_REL

    print()
    if passed:
        print("  BOTH thresholds cleared. PAGE PLACEMENT IS THE DRIVER and is")
        print("  controllable. The A5.1 re-run may proceed with hugepages")
        print("  declared as part of the operating point, and the change must be")
        print("  named in the result. Note this identifies a CONTROLLABLE cause:")
        print("  hugepages change TLB behaviour as well as page colouring, and")
        print("  nothing written from this may say colouring specifically.")
    elif unchanged:
        print(f"  Both statistics essentially unchanged (spread {100*ds:.0f}%, "
              f"CoV_rep {100*dc:.0f}%, bar {100*UNCHANGED_REL:.0f}%).")
        print("  PAGE PLACEMENT IS NOT THE DRIVER. No further tuning. A5.1")
        print("  clause 4 applies: a 16 MiB CCX cannot host this victim at a")
        print("  stable operating point, and that is reported as a result.")
    else:
        print("  Moved, but not across both thresholds. A5.2 declared that an")
        print("  ambiguous diagnostic licenses nothing: NO CONCLUSION, NO RE-RUN.")

    if "quiescent" in thp and "quiescent" in ctl:
        print(f"\n  quiescent baseline, shim {thp['quiescent']['cov_rep']:.2f}% "
              f"against control {ctl['quiescent']['cov_rep']:.2f}% CoV_rep "
              f"(campaign 1.74%, at the 1 ms timer's half-quantum floor)")


if __name__ == "__main__":
    main(*sys.argv[1:3])
