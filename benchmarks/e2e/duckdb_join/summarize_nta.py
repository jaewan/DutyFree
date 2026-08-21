#!/usr/bin/env python3
"""A5.3: does PREFETCHNTA still hold the CCX L3 when a victim is competing?

A4.1 measured `wb_prefetchnta` holding the entire 16 MiB CCX on Zen4c and
concluded it allocates, which made NTA_sat a declared negative control. That
sweep ran with no victim present. An idle cache fills to capacity under either
insertion policy, so victimless occupancy cannot distinguish a stream inserted
at MRU from one inserted at LRU -- the two differ only under competition, where
LRU-inserted lines are evicted first. This reduces the streamer-side occupancy
measured DURING the co-run, which can.

Decision rule, fixed in Amendment 5 (A5.3) before the measurement:

  NTA streamer occupancy >= 50% of wb_load's -> A4.1's premise holds, NTA
      allocates under competition and recovered anyway, and the mechanism as
      stated is wrong.
  NTA streamer occupancy <  50% of wb_load's -> A4.1 did not measure what it
      was taken to measure; outcome 3's inference does not go through, and
      every other conclusion drawn from a victimless sweep must be re-examined.

The threshold is on the ratio of steady medians. Reported with a rep-paired
bootstrap so the reader can see whether the ratio is anywhere near the line.
"""
import json, random, statistics as st, sys
from collections import defaultdict

B, SEED, THRESHOLD = 20000, 20260822, 0.50
MIB = 2 ** 20


def load(path):
    by = defaultdict(dict)
    for line in open(path):
        r = json.loads(line)
        if not r["valid"]:
            print(f"  SKIP invalid: {r['arm']} inv{r['invocation']}", file=sys.stderr)
            continue
        by[r["invocation"]][r["arm"]] = r
    return by


def boot(pairs, stat):
    rng = random.Random(SEED)
    k = len(pairs)
    out = sorted(stat([pairs[rng.randrange(k)] for _ in range(k)])
                 for _ in range(B))
    return out[int(0.025 * B)], out[int(0.975 * B)]


def main(path):
    by = load(path)
    invs = sorted(by)
    print(f"\n{path}  reps={len(invs)}\n")
    print(f"{'arm':<10}{'GB/s':>7}{'victim s':>10}{'victim occ':>12}"
          f"{'STREAMER occ':>14}{'% of CCX':>10}")
    ccx = None
    for a in ("WB_sat", "NTA_sat"):
        rs = [by[i][a] for i in invs if a in by[i]]
        if not rs:
            raise SystemExit(f"{path}: arm {a} absent; A5.3 needs both")
        ccx = rs[0]["l3_bytes"]
        print(f"{a:<10}{st.median([r['agg_bw_gbps'] for r in rs]):>7.2f}"
              f"{st.median([st.median(r['trial_seconds_measured']) for r in rs]):>10.4f}"
              f"{st.median([r['occupancy_bytes_steady'] for r in rs])/MIB:>11.2f}M"
              f"{st.median([r['agg_occupancy_bytes_steady'] for r in rs])/MIB:>13.2f}M"
              f"{100*st.median([r['agg_occupancy_bytes_steady'] for r in rs])/ccx:>9.1f}%")

    # Paired per repetition: both arms ran under the same host conditions in
    # that repetition, so the ratio is taken within a repetition and then
    # summarised, never as a ratio of two independently-pooled medians.
    pr = [(by[i]["WB_sat"]["agg_occupancy_bytes_steady"],
           by[i]["NTA_sat"]["agg_occupancy_bytes_steady"])
          for i in invs if "WB_sat" in by[i] and "NTA_sat" in by[i]]
    if len(pr) < 2:
        raise SystemExit(f"{path}: only {len(pr)} paired reps")
    ratio = st.median([n / w for w, n in pr])
    lo, hi = boot(pr, lambda s: st.median([n / w for w, n in s]))
    print(f"\nNTA streamer occupancy as a fraction of wb_load's, rep-paired:")
    print(f"  {ratio:.3f}  95% CI [{lo:.3f}, {hi:.3f}]   ({len(pr)} reps)")
    print(f"  A5.3 threshold: {THRESHOLD:.2f}")

    if lo > THRESHOLD:
        print(f"\n  >= threshold, and the whole interval is above it.")
        print(f"  A4.1's premise HOLDS under competition: PREFETCHNTA allocates.")
        print(f"  It recovered anyway. THE MECHANISM AS STATED IS WRONG.")
        return 0
    if hi < THRESHOLD:
        print(f"\n  < threshold, and the whole interval is below it.")
        print(f"  A4.1's victimless sweep did not measure what it was taken to")
        print(f"  measure. Outcome 3's inference does not go through, and every")
        print(f"  other victimless-occupancy conclusion must be re-examined.")
        return 0
    print(f"\n  The interval straddles the threshold. A5.3 declared that an")
    print(f"  ambiguous diagnostic licenses nothing. No conclusion.")
    return 0


def posthoc(path):
    """Not declared in A5.3. Reported because it is in the same artifact and it
    bears on WHY the negative control fired -- it does not alter the verdict
    above, which is fixed by the declared threshold.

    Each invocation carries its own victimless reading: the sampler's first
    sample is taken while the victim is still starting (numactl + duckdb open)
    and its last after the queries have finished, with the streamer running
    throughout both. So `idle` reproduces A4.1's measurement inside every
    repetition, and `competed` is the same streamer with the victim live. The
    difference is what the streamer gives up under pressure, which is the
    quantity a victimless sweep structurally cannot see.

    The victim fill rate is the reverse-causation check. If the occupancy split
    were caused by the faster victim demanding harder rather than by the
    streamer yielding, the arm with the higher victim fill rate would hold the
    most cache. Print it so the sign can be read off directly.
    """
    by = load(path)
    invs = sorted(by)
    print("\n-- post-hoc, not declared in A5.3 --\n")
    print(f"{'arm':<10}{'idle':>8}{'competed':>10}{'yield':>8}{'victim occ':>12}"
          f"{'victim GB/s':>13}")
    for a in ("WB_sat", "NTA_sat"):
        rs = [by[i][a] for i in invs if a in by[i]]
        idle, comp, vocc, rate = [], [], [], []
        for r in rs:
            ser = [int(x[1]) / MIB for x in (r.get("agg_occupancy_series") or [])]
            if len(ser) < 3:
                continue
            idle.append(st.median([ser[0], ser[-1]]))
            comp.append(st.median(ser[1:-1]))
            vocc.append(r["occupancy_bytes_steady"] / MIB)
            t = r["trial_seconds_measured"]
            gb = (int(r["mbm_total_last"]) - int(r["mbm_total_first"])) / 1e9
            # Over the measured queries only, not the whole invocation: the
            # invocation also contains the build, which is not the steady state
            # the occupancy figures describe.
            rate.append(gb / (st.median(t) * len(t)))
        if not idle:
            continue
        print(f"{a:<10}{st.median(idle):>8.2f}{st.median(comp):>10.2f}"
              f"{st.median(idle) - st.median(comp):>8.2f}"
              f"{st.median(vocc):>12.2f}{st.median(rate):>13.2f}")
    print("\n  idle/competed/yield are MiB of the CCX L3 held by the STREAMER.")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
        posthoc(p)
