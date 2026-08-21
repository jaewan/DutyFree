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
    print(f"\n{path}  chain={chain}  N={n}  reps={len(invs)}\n")
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
    for wb, na, label in (("WB_match_hi", "NTA_sat", "~18 GB/s"),
                          ("WB_match_lo", "NTA_lo", "~10.8 GB/s"),
                          ("FB0_sat", "FB256_sat", "flush-behind, within-binary"),
                          ("WB_fbmatch", "FB256_match", "flush-behind, matched BW")):
        if wb in taxes and na in taxes:
            pr = [(by[i]["quiescent"], by[i][wb], by[i][na]) for i in invs
                  if all(k in by[i] for k in ("quiescent", wb, na))]
            d = med([(w - x) / q0 for q0, w, x in
                     [(a, b, c) for a, b, c in pr]])
            lo, hi = boot(pr, lambda s: med([(w - x) / q0 for q0, w, x in s]))
            print(f"{label:<30} {wb} - {na} = {d:+.3f}  [{lo:+.3f}, {hi:+.3f}]")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
