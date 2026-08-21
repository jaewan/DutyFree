#!/usr/bin/env python3
"""Summarise a DuckDB co-run artifact: per-arm tax with a rep-paired bootstrap.

CoV_rep is the coefficient of variation across the ten per-repetition medians,
not across all measured queries pooled. It is the dispersion the paired
bootstrap actually resamples, and it runs lower than the pooled figure quoted
in DUCKDB_JOIN_CORUN_OUTCOME.md because within-invocation query scatter is
already collapsed by the median.

Written so chain8 and the joinuniq control are reduced by identical code. The
bootstrap resamples *repetitions*, not queries: each repetition contributes one
(quiescent, loaded) pair measured under the same host conditions, so pairing is
what removes drift between arms. Percentile interval, B = 20000, seeded.
"""
import json, random, statistics as st, sys
from collections import defaultdict

B, SEED = 20000, 20260821


def med(xs):
    return st.median(xs)


def load(path):
    by = defaultdict(dict)          # invocation -> arm -> median query time
    meta = defaultdict(lambda: defaultdict(list))
    for line in open(path):
        r = json.loads(line)
        if not r["valid"]:
            print(f"  SKIP invalid: arm={r['arm']} inv={r['invocation']}", file=sys.stderr)
            continue
        by[r["invocation"]][r["arm"]] = med(r["trial_seconds_measured"])
        m = meta[r["arm"]]
        m["occ"].append(r["occupancy_bytes_steady"] or 0)
        if r.get("agg_bw_gbps"):
            m["bw"].append(r["agg_bw_gbps"])
        a, b = r.get("mbm_total_first"), r.get("mbm_total_last")
        if a is not None and b is not None:
            m["mbm"].append((int(b) - int(a)) / 1e9)
        m["t"].append(med(r["trial_seconds_measured"]))
        m["chain"].append(r["chain"])
        m["n"].append(r["build_rows"])
    return by, meta


def boot(pairs, stat):
    rng = random.Random(SEED)
    k = len(pairs)
    out = []
    for _ in range(B):
        s = [pairs[rng.randrange(k)] for _ in range(k)]
        out.append(stat(s))
    out.sort()
    return out[int(0.025 * B)], out[int(0.975 * B)]


def main(path):
    by, meta = load(path)
    invs = sorted(by)
    arms = [a for a in meta if a != "quiescent"]
    chain = meta[arms[0] if arms else "quiescent"]["chain"][0]
    n = meta[arms[0] if arms else "quiescent"]["n"][0]
    # From the record, not the filename: which declared pairs are meaningful
    # depends on the microarchitecture, and a renamed file must not change it.
    hosts = {json.loads(ln)["host"] for ln in open(path) if ln.strip()}
    if len(hosts) != 1:
        raise SystemExit(f"{path} mixes hosts {hosts}; refusing to summarise")
    host = hosts.pop()
    print(f"\n{path}  host={host}  chain={chain}  N={n}  reps={len(invs)}\n")
    q = [by[i]["quiescent"] for i in invs if "quiescent" in by[i]]
    print(f"{'arm':<14}{'GB/s':>7}{'MBM GB':>8}{'occ MiB':>9}{'median s':>10}"
          f"{'tax':>7}  {'95% CI':<18}{'CoV_rep':>8}")
    qcov = st.stdev(q) / st.mean(q) if len(q) > 1 else 0
    print(f"{'quiescent':<14}{'--':>7}{med(meta['quiescent']['mbm'] or [0]):>8.2f}"
          f"{med(meta['quiescent']['occ'])/2**20:>9.0f}{med(q):>10.4f}"
          f"{1.0:>7.3f}  {'--':<18}{qcov:>7.2%}")
    taxes = {}
    for a in sorted(arms, key=lambda x: -med(meta[x]["t"])):
        pr = [(by[i]["quiescent"], by[i][a]) for i in invs
              if "quiescent" in by[i] and a in by[i]]
        # An arm can be left with too few PAIRED repetitions to summarise even
        # though it has records: its quiescent partner may have been
        # invalidated, or the file may be a run still in progress. stdev raises
        # on a single point, which turned inspecting a partial artifact into a
        # traceback. Report the shortfall instead -- silently dropping the arm
        # would read as "this arm was not run".
        if len(pr) < 2:
            print(f"{a:<14}{'--':>7}{'--':>8}{'--':>9}{'--':>10}{'--':>7}"
                  f"  {'(only ' + str(len(pr)) + ' paired rep)':<18}{'--':>8}")
            continue
        tax = med([y / x for x, y in pr])
        lo, hi = boot(pr, lambda s: med([y / x for x, y in s]))
        cov = st.stdev([y for _, y in pr]) / st.mean([y for _, y in pr])
        taxes[a] = (tax, lo, hi, pr)
        print(f"{a:<14}{med(meta[a]['bw'] or [0]):>7.2f}"
              f"{med(meta[a]['mbm'] or [0]):>8.2f}"
              f"{med(meta[a]['occ'])/2**20:>9.0f}{med([y for _, y in pr]):>10.4f}"
              f"{tax:>7.3f}  [{lo:.3f}, {hi:.3f}]      {cov:>7.2%}")
    # paired differences between declared matched pairs, if both present
    print()
    # Left member allocates, right member is the candidate non-allocating arm.
    # The last entry is an instrument check, not a de-confound: two ALLOCATING
    # arms at the same bandwidth from different binaries should be equal, and
    # if they are not, the cross-binary pair above it is contaminated.
    # (left allocates, right is the candidate non-allocating arm, host, label).
    # Host-keyed because arm NAMES collide across vendors while their meanings
    # do not: WB_sat/NTA_sat exist on both, but on Intel they are 24.9 against
    # 17.7 GB/s -- not a matched pair and not a de-confound -- while on AMD
    # they are the declared negative control at 24.7 against 24.7. Printing the
    # AMD label over the Intel file, as this did, invites exactly the arm-
    # identity error section 5.1 exists to prevent.
    PAIRS = (
        ("WB_match_hi", "NTA_sat",     "intel", "Intel, ~18 GB/s"),
        ("WB_match_lo", "NTA_lo",      "intel", "Intel, ~10.8 GB/s"),
        ("FB0_match",   "FB256_match", "amd",   "AMD within-binary, matched BW"),
        ("FB0_sat",     "FB256_sat",   "amd",   "AMD within-binary, saturated (NOT bw-matched)"),
        ("WB_fbmatch",  "FB256_match", "amd",   "AMD cross-binary, matched BW"),
        ("WB_sat",      "NTA_sat",     "amd",   "AMD declared negative control"),
        ("WB_fbmatch",  "FB0_match",   "amd",   "AMD instrument check (expect 0)"),
    )
    vendor = "amd" if host.startswith("moscxl") else "intel"
    for wb, na, want, label in [p for p in PAIRS if p[2] == vendor]:
        if wb in taxes and na in taxes:
            pr = [(by[i]["quiescent"], by[i][wb], by[i][na]) for i in invs
                  if all(k in by[i] for k in ("quiescent", wb, na))]
            if not pr:
                print(f"{label:<30} {wb} - {na} = no repetition has both arms")
                continue
            d = med([(w - x) / q0 for q0, w, x in
                     [(a, b, c) for a, b, c in pr]])
            lo, hi = boot(pr, lambda s: med([(w - x) / q0 for q0, w, x in s]))
            print(f"{label:<30} {wb} - {na} = {d:+.3f}  [{lo:+.3f}, {hi:+.3f}]")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
