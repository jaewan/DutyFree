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

A5.4 applies the identical instrument to Intel, where the same blind spot was
never closed, with its own threshold of 0.25 and its own pairs.

**The pairing is host-dependent and getting it wrong is a section 5.1 error
committed inside the reducer.** On AMD, WB_sat and NTA_sat are a matched pair
at 24.3 against 24.5 GB/s. On Intel those same two arm names are 24.9 against
17.8 GB/s across 8 and 8 cores and are not a matched pair at all; the Intel
partners are WB_match_hi (18.0 GB/s, 2 cores) and WB_match_lo (10.7, 1 core).
So the pair table is keyed by vendor, read from the record rather than the
filename, exactly as summarize_corun.py does and for the same reason.

The threshold is on the ratio of steady medians. Reported with a rep-paired
bootstrap so the reader can see whether the ratio is anywhere near the line.
"""
import json, random, statistics as st, sys
from collections import defaultdict

B, SEED = 20000, 20260822
MIB = 2 ** 20

# (allocating reference, candidate, threshold, amendment, label). The candidate
# must come in BELOW the threshold for the non-allocating reading to survive;
# A5.3 inverted that sense because on AMD the declared expectation was that NTA
# would look like wb_load, so read each rule from its own amendment text.
PAIRS_BY_VENDOR = {
    "amd":   [("WB_sat", "NTA_sat", 0.50, "A5.3", "AMD, saturated, matched BW")],
    "intel": [("WB_match_hi", "NTA_sat", 0.25, "A5.4", "Intel, ~18 GB/s"),
              ("WB_match_lo", "NTA_lo",  0.25, "A5.4", "Intel, ~10.8 GB/s")],
}


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


def vendor_of(path):
    hosts = {json.loads(l)["host"] for l in open(path) if l.strip()}
    if len(hosts) != 1:
        raise SystemExit(f"{path} mixes hosts {hosts}; refusing to summarise")
    host = hosts.pop()
    return ("amd" if host.startswith("moscxl") else "intel"), host


def main(path):
    by = load(path)
    invs = sorted(by)
    vendor, host = vendor_of(path)
    pairs = PAIRS_BY_VENDOR[vendor]
    print(f"\n{path}  host={host}  vendor={vendor}  reps={len(invs)}\n")

    arms = [a for a in dict.fromkeys(x for i in invs for x in by[i])]
    print(f"{'arm':<13}{'GB/s':>7}{'victim s':>10}{'tax':>7}{'victim occ':>12}"
          f"{'STREAMER occ':>14}{'% of CCX':>10}")
    ccx = None
    for a in sorted(arms, key=lambda x: (x == "quiescent",)):
        rs = [by[i][a] for i in invs if a in by[i]]
        ccx = rs[0]["l3_bytes"]
        t = st.median([st.median(r["trial_seconds_measured"]) for r in rs])
        # Tax is rep-paired against that repetition's own quiescent arm, never
        # a ratio of two independently-pooled medians.
        tx = [st.median(by[i][a]["trial_seconds_measured"])
              / st.median(by[i]["quiescent"]["trial_seconds_measured"])
              for i in invs if a in by[i] and "quiescent" in by[i]]
        ao = [r["agg_occupancy_bytes_steady"] for r in rs
              if r.get("agg_occupancy_bytes_steady") is not None]
        bw = [r["agg_bw_gbps"] for r in rs if r.get("agg_bw_gbps")]
        print(f"{a:<13}{(st.median(bw) if bw else 0):>7.2f}{t:>10.4f}"
              f"{(f'{st.median(tx):.3f}' if tx else '--'):>7}"
              f"{st.median([r['occupancy_bytes_steady'] for r in rs])/MIB:>11.1f}M"
              f"{(f'{st.median(ao)/MIB:.2f}M' if ao else '--'):>14}"
              f"{(f'{100*st.median(ao)/ccx:.1f}%' if ao else '--'):>10}")

    verdicts = []
    for wb, na, thr, amd, label in pairs:
        if wb not in arms or na not in arms:
            print(f"\n{label}: {wb} or {na} absent; skipped")
            continue
        pr = [(by[i][wb]["agg_occupancy_bytes_steady"],
               by[i][na]["agg_occupancy_bytes_steady"])
              for i in invs if wb in by[i] and na in by[i]]
        if len(pr) < 2:
            raise SystemExit(f"{path}: only {len(pr)} paired reps for {label}")
        ratio = st.median([n / w for w, n in pr])
        lo, hi = boot(pr, lambda s_: st.median([n / w for w, n in s_]))
        rng = sorted(n / w for w, n in pr)
        print(f"\n{amd}  {label}:  {na} streamer occupancy / {wb}'s, rep-paired")
        print(f"  {ratio:.3f}  95% CI [{lo:.3f}, {hi:.3f}]   ({len(pr)} reps, "
              f"per-rep {rng[0]:.3f}-{rng[-1]:.3f})")
        print(f"  threshold: {thr:.2f}")
        verdicts.append((label, ratio, lo, hi, thr, amd))

    print()
    if vendor == "amd":
        for label, ratio, lo, hi, thr, amd in verdicts:
            if lo > thr:
                print("  >= threshold, and the whole interval is above it.")
                print("  A4.1's premise HOLDS under competition: PREFETCHNTA allocates.")
                print("  It recovered anyway. THE MECHANISM AS STATED IS WRONG.")
            elif hi < thr:
                print("  < threshold, and the whole interval is below it.")
                print("  A4.1's victimless sweep did not measure what it was taken to")
                print("  measure. Outcome 3's inference does not go through, and every")
                print("  other victimless-occupancy conclusion must be re-examined.")
            else:
                print("  The interval straddles the threshold. A5.3 declared that an")
                print("  ambiguous diagnostic licenses nothing. No conclusion.")
        return 0

    # A5.4: BOTH pairs must clear, and the rule is ">= 25% in either pair".
    if any(lo <= thr <= hi for _, _, lo, hi, thr, _ in verdicts):
        print("  An interval straddles the threshold. A5.4's rule is stated on the")
        print("  ratio, not on an interval that contains it: no conclusion here")
        print("  either, and the Intel de-confound keeps whatever standing it had.")
        return 0
    failed = [v for v in verdicts if v[1] >= v[4]]
    if failed:
        print("  >= threshold in " + ("both pairs" if len(failed) == len(verdicts)
                                      else f"{len(failed)} of {len(verdicts)} pairs")
              + ": " + ", ".join(v[0] for v in failed) + ".")
        print("  The Intel arms differ from the AMD ones in DEGREE, NOT IN KIND.")
        print("  The de-confound contrasts less allocation against more, not")
        print("  allocation against none. Every recovery and de-confound figure in")
        print("  DUCKDB_JOIN_CORUN_OUTCOME.md must be relabelled on that basis.")
        return 0
    print("  < threshold in both pairs, whole intervals below.")
    print("  The Intel non-allocating arm IS non-allocating under competition.")
    print("  The Intel de-confound stands as reported, and A5.3 is a Zen4c")
    print("  insertion-policy divergence, not a defect in the de-confound design.")
    return 0


def posthoc(path):
    """Not declared in A5.3. Reported because it is in the same artifact and it
    bears on WHY the negative control fired -- it does not alter the verdict
    above, which is fixed by the declared threshold.

    Each invocation carries its own victimless reading: the sampler's FIRST
    sample is taken while the victim is still starting (numactl + duckdb open),
    with the streamer already settled. So `idle` reproduces A4.1's measurement
    inside every repetition and `competed` is the same streamer with the victim
    live; the difference is what the streamer gives up under pressure, which is
    the quantity a victimless sweep structurally cannot see.

    Only the first sample is used, never the last. On AMD the last sample also
    reads idle -- a 16 MiB CCX refills between the victim exiting and the
    sampler stopping -- and an earlier version of this function averaged the
    two. On Intel that is wrong: a 320 MiB LLC does not refill in the <0.25 s
    before the sampler stops, so the last sample still reads the competed
    level, and averaging it with the first silently splits the difference
    between an idle and a competed reading. The AMD numbers are unchanged by
    the fix; the Intel ones were nonsense before it.

    `idle spread` is the min-max of the per-invocation idle readings. It is
    printed because on Intel it is not small: WB_match_hi settles into two
    distinct states across repetitions, and an arm that does that has no single
    idle level to report.

    The victim fill rate is the reverse-causation check. If the occupancy split
    were caused by the faster victim demanding harder rather than by the
    streamer yielding, the arm with the higher victim fill rate would hold the
    most cache. Print it so the sign can be read off directly.
    """
    by = load(path)
    invs = sorted(by)
    print("\n-- post-hoc, not declared in A5.3 --\n")
    print(f"{'arm':<13}{'idle':>8}{'competed':>10}{'yield':>8}"
          f"{'idle spread':>14}{'victim occ':>12}{'victim GB/s':>13}")
    arms = [a for a in dict.fromkeys(x for i in invs for x in by[i])
            if a != "quiescent"]
    for a in arms:
        rs = [by[i][a] for i in invs if a in by[i]]
        idle, comp, vocc, rate = [], [], [], []
        for r in rs:
            ser = [int(x[1]) / MIB for x in (r.get("agg_occupancy_series") or [])]
            if len(ser) < 3:
                continue
            idle.append(ser[0])
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
        print(f"{a:<13}{st.median(idle):>8.2f}{st.median(comp):>10.2f}"
              f"{st.median(idle) - st.median(comp):>8.2f}"
              f"{f'{min(idle):.0f}-{max(idle):.0f}':>14}"
              f"{st.median(vocc):>12.2f}{st.median(rate):>13.2f}")
    print("\n  idle/competed/yield are MiB of the CCX L3 held by the STREAMER.")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
        posthoc(p)
