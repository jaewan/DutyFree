#!/usr/bin/env python3
"""A6: stability checks for the AMD co-run re-run, fixed before the data.

Implements Amendment 6 of DUCKDB_JOIN_CORUN_PREREGISTRATION.md and nothing
else. `summarize_corun.py` remains the reducer for the taxes and the paired
differences themselves, unchanged and at its own seed; this script adds the
three bars, the Rule O trim, and the Rule O incidence count, and prints which
branch of A6.4 fires so the mapping is not left to the reader.

Rule O, restated because the whole point is that it was fixed in advance: no
repetition is excluded from the primary analysis for any reason relating to its
runtime, its occupancy, or its effect on any estimate. `valid: false` records
are voided by the protocol's pre-existing machinery, counted, and reported.
There is no other exclusion path, and in particular there is no threshold on
runtime that removes a repetition from anything below.

The trim is a declared SECONDARY and appears beside the untrimmed figure, never
in place of it. S3 is applied to the untrimmed figure only.
"""
import json, statistics as st, sys
from collections import defaultdict

# A6.3 clause 3: descriptive, no verdict rests on it. 1.25 sits between the
# 1.13x normal maximum and the 1.38x/1.43x events across 150 AMD invocations.
ANOM = 1.25
# A6.4. S3 is section 6's original bar, unweakened.
COV_BAR, LOO_RANGE_BAR = 0.05, 0.20
PRIMARY = ("FB0_match", "FB256_match")
PAIRS = [(("FB0_match", "FB256_match"), "within-binary, matched BW  [PRIMARY]"),
         (("WB_fbmatch", "FB256_match"), "cross-binary, matched BW"),
         (("WB_fbmatch", "FB0_match"), "instrument check (expect 0)")]


def load(path):
    by, void = defaultdict(dict), []
    for line in open(path):
        r = json.loads(line)
        if not r["valid"]:
            void.append((r["arm"], r["invocation"]))
            continue
        by[r["invocation"]][r["arm"]] = (st.median(r["trial_seconds_measured"]),
                                         r["timestamp_unix"])
    return by, void


def cov(xs):
    return st.stdev(xs) / st.mean(xs) if len(xs) > 1 else 0.0


def trim1(xs):
    """A6.3 clause 2: one from each end, symmetric, fixed count."""
    s = sorted(xs)
    return s[1:-1] if len(s) > 3 else s


def diffs(by, invs, wb, na):
    """Per-repetition de-confound difference, normalised by that repetition's
    own quiescent arm. Same estimator as summarize_corun.py; pairing is never
    broken, which is why the trim for a difference is taken on THIS series and
    not on the two arms separately."""
    return [(by[i][wb][0] - by[i][na][0]) / by[i]["quiescent"][0]
            for i in invs if all(k in by[i] for k in ("quiescent", wb, na))]


def main(path):
    by, void = load(path)
    invs = sorted(by)
    arms = list(dict.fromkeys(a for i in invs for a in by[i]))
    print(f"\n{path}   reps={len(invs)}   voided={len(void)}"
          + (f"  {void}" if void else ""))

    # ---- per-arm: S3 and the incidence count -------------------------------
    print(f"\n{'arm':<14}{'CoV_rep':>9}{'(trimmed)':>11}{'anomalies':>11}"
          f"{'  worst':>8}{'  1st/2nd half':>15}")
    span = [v[1] for i in invs for v in by[i].values()]
    mid = (min(span) + max(span)) / 2 if span else 0
    inc = {}
    for a in arms:
        ts = [by[i][a][0] for i in invs if a in by[i]]
        if len(ts) < 2:
            continue
        pool = st.median(ts)
        hits = [(i, by[i][a][0] / pool) for i in invs
                if a in by[i] and by[i][a][0] >= ANOM * pool]
        first = sum(1 for i, _ in hits if by[i][a][1] < mid)
        inc[a] = hits
        print(f"{a:<14}{cov(ts):>8.2%}{cov(trim1(ts)):>11.2%}{len(hits):>11}"
              f"{(max(r for _, r in hits) if hits else 0):>8.2f}"
              f"{f'{first}/{len(hits) - first}':>15}")
    tot = sum(len(v) for v in inc.values())
    n = sum(1 for a in arms for i in invs if a in by[i])
    print(f"\n  incidence {tot}/{n} = {100 * tot / n:.1f}%  "
          f"(A6.1 measured 2/150 = 1.3% on the existing AMD blocks)")

    # ---- per-pair: S1 and S2 ----------------------------------------------
    print(f"\n{'pair':<62}{'diff':>8}{'(trimmed)':>11}"
          f"{'LOO range':>20}{'span/|d|':>10}{'  S1':>5}{'  S2':>5}")
    s12 = {}
    for (wb, na), label in PAIRS:
        if wb not in arms or na not in arms:
            continue
        d = diffs(by, invs, wb, na)
        if len(d) < 3:
            continue
        pt = st.median(d)
        loo = [st.median(d[:k] + d[k + 1:]) for k in range(len(d))]
        s1 = len({x > 0 for x in loo}) == 1
        s2 = (max(loo) - min(loo)) / abs(pt) <= LOO_RANGE_BAR if pt else False
        s12[(wb, na)] = (s1, s2, pt, min(loo), max(loo))
        print(f"{wb + ' - ' + na + '  ' + label:<62}{pt:>+8.3f}"
              f"{st.median(trim1(d)):>+11.3f}"
              f"{f'[{min(loo):+.3f}, {max(loo):+.3f}]':>20}"
              f"{(max(loo) - min(loo)) / abs(pt):>9.1%}"
              f"{'  ok' if s1 else ' FAIL':>5}{'  ok' if s2 else ' FAIL':>5}")

    # ---- A6.4 branch -------------------------------------------------------
    covs = {a: cov([by[i][a][0] for i in invs if a in by[i]]) for a in PRIMARY
            if a in arms}
    if len(covs) < 2 or len(s12) < 2:
        print("\n  primary pair or a matched pair absent; no branch selected.")
        return
    s3 = all(c < COV_BAR for c in covs.values())
    matched = [v for k, v in s12.items() if k != ("WB_fbmatch", "FB0_match")]
    s1 = all(v[0] for v in matched)
    s2 = all(v[1] for v in matched)
    print(f"\n  S3 (CoV < {COV_BAR:.0%} untrimmed, both primary arms): "
          f"{'PASS' if s3 else 'FAIL'}  "
          + ", ".join(f"{a} {c:.2%}" for a, c in covs.items()))
    print(f"  S1 (sign stable under leave-one-out):  {'PASS' if s1 else 'FAIL'}")
    print(f"  S2 (LOO range <= {LOO_RANGE_BAR:.0%} of point): "
          f"{'PASS' if s2 else 'FAIL'}")

    print()
    if s3:
        print("  A6.4 branch 1. Outcome 5 is LIFTED for this host; a verdict may")
        print("  be drawn. It must be reported with A6.2's fixed sentence:")
        print("  nothing changed but n, so the n=10 CoV estimate was imprecise")
        print("  and the operating point was NOT repaired.")
    elif s1 and s2:
        print("  A6.4 branch 2. The host remains under section 6 outcome 5: NO")
        print("  VERDICT, and not a vendor null either. The difference is stable")
        print("  under resampling while its interval is not trustworthy. That is")
        print("  a bounded observation about a host that fails its stability")
        print("  bar. It is not a de-confound and does not enter the paper.")
    else:
        print("  A6.4 branch 3. The difference is NOT stable and the campaign's")
        print("  +0.263 does not survive replication. Report prominently and")
        print("  amend DUCKDB_JOIN_AMD_CORUN_OUTCOME.md at the point of use.")
    print("\n  Per A6.4 this is reported whichever branch fired, and per A6.2")
    print("  there is no third campaign at this operating point.")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
