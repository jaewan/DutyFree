#!/usr/bin/env python3
"""A6.14 item 5 / A6.15 item 7: intersect measured arm windows with the
contention watcher's foreign-burst log.

Written 2026-08-23 02:20, while the A6 block was at ~151/270 and no outcome
was known, so that no threshold or grouping in it can have been chosen against
a result. Reports only. It performs no exclusion, no reweighting and no
duration-normalised adjustment, per Rule O and A6.15 item 9.

Usage:
    python3 overlap_bursts.py <records.jsonl> <watcher.log> [--tz-offset-min N]

The watcher log lines look like:
    2026-08-23T00:15:58  WOULD-ABORT  pid=428999 comm=v3agent pcpu=300.0 age=0s
        argv   : ...
        ppid   : ...
and carry two tags. WOULD-ABORT is pcpu >= 20 off the BENIGN list; av-activity
is an AhnLab component at pcpu >= 1.0, below the abort threshold. The second
series is the one A6.1's missing marker would live in -- "a scan burst too
small to trip hostguard but large enough to perturb a 30 ms query" -- so both
are reported, separately.

The watcher dedups per (pid, comm) for 30 s, so one line is one *event*, not
one 5 s sample, and a burst persisting under 30 s appears exactly once. Event
counts are therefore not durations, and a repeated pid is the only evidence of
a burst outstaying 30 s.

A record's measured window is reconstructed as
    end   = timestamp_unix                       (written just after the arm)
    start = end - sum(trial_seconds_measured)
which excludes the warm-up query and the settle period. Both are reported
separately, because a burst during settle perturbs the streamer's ramp rather
than the victim's queries and is a different claim.
"""
import json, sys, time, calendar
from datetime import datetime

# A6.11's self-match set: the campaign's own binaries and the monitoring that
# samples the host. comm truncates to 15 chars, so match on prefix.
HARNESS = ("duckdb", "aggressor", "amd_flushbehind", "flushbehind", "wb_load",
           "pgrep", "ps", "python3", "sshd", "bash", "sh", "sleep", "awk",
           "grep", "tail", "ssh")


def parse_watcher(path, tz_offset_min=0):
    bursts, harness_hits = [], {}
    for line in open(path, errors="replace"):
        # The monitor's notification stream prefixes "watcher: "; the on-host
        # log does not. Accept both so either source parses.
        line = line.strip()
        if line.startswith("watcher:"):
            line = line[len("watcher:"):].strip()
        if "WOULD-ABORT" in line:
            tag = "abort"
        elif "av-activity" in line:
            tag = "av"
        else:
            continue
        try:
            stamp = line.split()[0]
            t = calendar.timegm(datetime.strptime(
                stamp, "%Y-%m-%dT%H:%M:%S").timetuple()) - tz_offset_min * 60
        except Exception:
            continue
        comm = pid = None
        pcpu = 0.0
        for tok in line.split():
            if tok.startswith("comm="):
                comm = tok[5:]
            elif tok.startswith("pid="):
                pid = tok[4:]
            elif tok.startswith("pcpu="):
                try:
                    pcpu = float(tok[5:])
                except ValueError:
                    pcpu = 0.0
        if comm is None:
            continue
        if any(comm == h or comm.startswith(h) for h in HARNESS):
            harness_hits[comm] = harness_hits.get(comm, 0) + 1
            continue
        # A6.16: pcpu/100 lower-bounds concurrent threads. Unlike total work,
        # this survives the near-zero-lifetime artifact, because no single
        # thread exceeds 100%. Width decides whether temporal overlap means
        # actual contact with the pinned victim core.
        bursts.append({"t": t, "comm": comm, "pid": pid, "pcpu": pcpu,
                       "tag": tag,
                       "min_threads": max(1, int(pcpu // 100))})
    bursts.sort(key=lambda b: b["t"])
    return bursts, harness_hits


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    recs_path, watch_path = sys.argv[1], sys.argv[2]
    tz = 0
    if "--tz-offset-min" in sys.argv:
        tz = int(sys.argv[sys.argv.index("--tz-offset-min") + 1])

    # The watcher writes local time; time.time() is epoch. Derive the local
    # offset the same way the watcher's host would have, unless overridden.
    if tz == 0:
        tz = -(time.altzone if time.daylight and time.localtime().tm_isdst
               else time.timezone) // 60

    recs = [json.loads(l) for l in open(recs_path) if l.strip()]
    bursts, harness_hits = parse_watcher(watch_path, tz)

    wins = []
    for r in recs:
        end = r.get("timestamp_unix")
        meas = r.get("trial_seconds_measured") or []
        settle = r.get("streamer_settle_seconds") or 0.0
        if end is None or not meas:
            continue
        m_start = end - sum(meas)
        wins.append({"arm": r["arm"], "valid": r.get("valid"),
                     "m_start": m_start, "m_end": end,
                     "m_dur": sum(meas),
                     "s_start": m_start - settle, "s_end": m_start,
                     "median": sorted(meas)[len(meas) // 2]})

    if not wins:
        print("no usable records"); sys.exit(1)
    if not bursts:
        print("no foreign bursts parsed from watcher log -- check the path "
              "and the timestamp format before believing this is a null")
        sys.exit(1)

    # --- clock sanity. A skew between the two sources produces zero overlaps,
    # which reads exactly like a clean result. Refuse rather than mislead.
    r_lo, r_hi = min(w["s_start"] for w in wins), max(w["m_end"] for w in wins)
    b_lo, b_hi = bursts[0]["t"], bursts[-1]["t"]
    fmt = lambda t: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
    print(f"records span : {fmt(r_lo)} .. {fmt(r_hi)}  ({len(wins)} arms)")
    print(f"watcher span : {fmt(b_lo)} .. {fmt(b_hi)}  ({len(bursts)} foreign bursts)")
    inter = min(r_hi, b_hi) - max(r_lo, b_lo)
    if inter <= 0:
        print(f"\nFATAL: the two spans do not overlap (gap {-inter/60:.1f} min). "
              "This is clock skew or a wrong --tz-offset-min, NOT a null result.")
        sys.exit(1)
    cov = inter / (r_hi - r_lo)
    print(f"overlap      : {inter/60:.1f} min, covering {cov*100:.1f}% of the block")
    if cov < 0.90:
        print("WARNING: the watcher does not cover the whole block. Per-arm "
              "counts below are undercounts for the uncovered stretch.")

    # --- burst arrival structure (A6.14 item 6: period read from the log)
    gaps = [(bursts[i + 1]["t"] - bursts[i]["t"]) / 60.0
            for i in range(len(bursts) - 1)]
    if gaps:
        gs = sorted(gaps)
        print(f"\ninter-arrival (min): n={len(gaps)} min={gs[0]:.1f} "
              f"median={gs[len(gs)//2]:.1f} max={gs[-1]:.1f} "
              f"mean={sum(gaps)/len(gaps):.1f}")
        print("  a mean far from the median is the non-stationarity A6.14's "
              "addendum records; the mean alone is not a host property.")
    nab = sum(1 for b in bursts if b["tag"] == "abort")
    print(f"  tags: WOULD-ABORT={nab}  av-activity={len(bursts)-nab}"
          "   (av-activity is below the abort threshold and is where A6.1's "
          "missing marker would live)")
    reps = {}
    for b in bursts:
        reps[b["pid"]] = reps.get(b["pid"], 0) + 1
    multi = {p: n for p, n in reps.items() if n > 1}
    print(f"  bursts outlasting the 30 s dedup window (repeated pid): "
          f"{len(multi)}"
          + (f" -> {sorted(multi.items(), key=lambda x:-x[1])[:5]}" if multi else ""))
    by_comm = {}
    for b in bursts:
        by_comm[b["comm"]] = by_comm.get(b["comm"], 0) + 1
    print("  by comm: " + ", ".join(f"{c}={n}" for c, n in
                                    sorted(by_comm.items(), key=lambda x: -x[1])))
    widths = sorted(b["min_threads"] for b in bursts)
    wide = sum(1 for w in widths if w >= 6)
    print(f"  width (A6.16, min concurrent threads from pcpu/100): "
          f"median={widths[len(widths)//2]} max={widths[-1]}  "
          f"{wide}/{len(widths)} at >=6 threads")
    print("    narrow bursts usually miss the pinned victim core, so hits below "
          "over-count contact; wide bursts do not, so hits are then tight.")
    if harness_hits:
        print("  (harness self-matches excluded: " +
              ", ".join(f"{c}={n}" for c, n in
                        sorted(harness_hits.items(), key=lambda x: -x[1])) + ")")

    # --- per-arm exposure and overlap
    bt = [b["t"] for b in bursts]
    bt_abort = [b["t"] for b in bursts if b["tag"] == "abort"]
    bt_av = [b["t"] for b in bursts if b["tag"] == "av"]
    arms = {}
    for w in wins:
        a = arms.setdefault(w["arm"], {"n": 0, "exp": 0.0, "hit": 0,
                                       "settle_hit": 0, "hit_meds": [],
                                       "miss_meds": []})
        a["n"] += 1
        a["exp"] += w["m_dur"]
        hit = any(w["m_start"] <= t <= w["m_end"] for t in bt)
        a["hit"] += hit
        a["hit_abort"] = a.get("hit_abort", 0) + any(
            w["m_start"] <= t <= w["m_end"] for t in bt_abort)
        a["hit_av"] = a.get("hit_av", 0) + any(
            w["m_start"] <= t <= w["m_end"] for t in bt_av)
        a["settle_hit"] += any(w["s_start"] <= t < w["s_end"] for t in bt)
        (a["hit_meds"] if hit else a["miss_meds"]).append(w["median"])

    total_exp = sum(a["exp"] for a in arms.values())
    rate = len(bursts) / (b_hi - b_lo) if b_hi > b_lo else 0.0  # bursts/sec

    print(f"\nper-arm exposure and overlap  (uniform-rate expectation uses "
          f"{rate*3600:.1f} bursts/h)")
    print(f"{'arm':<14}{'reps':>5}{'win s':>8}{'exposure s':>12}"
          f"{'hits':>6}{'abort':>7}{'av':>5}{'exp.':>7}{'settle':>8}")
    for name in sorted(arms, key=lambda k: -arms[k]["exp"]):
        a = arms[name]
        print(f"{name:<14}{a['n']:>5}{a['exp']/a['n']:>8.1f}{a['exp']:>12.1f}"
              f"{a['hit']:>6}{a.get('hit_abort',0):>7}{a.get('hit_av',0):>5}"
              f"{a['exp']*rate:>7.2f}{a['settle_hit']:>8}")
    tot_hit = sum(a["hit"] for a in arms.values())
    print(f"{'ALL':<14}{sum(a['n'] for a in arms.values()):>5}{'':>8}"
          f"{total_exp:>12.1f}{tot_hit:>6}"
          f"{sum(a.get('hit_abort',0) for a in arms.values()):>7}"
          f"{sum(a.get('hit_av',0) for a in arms.values()):>5}"
          f"{total_exp*rate:>7.2f}")
    print("  hits counts an arm once if ANY burst overlaps it. Because the "
          "watcher dedups 30 s per (pid, comm), one burst may span a window "
          "entirely and still contribute one event.")

    # --- A6.15 item 7: are the overlapping invocations the dispersed ones?
    print("\nA6.15 item 7 -- attribution test. For each arm, the median of the")
    print("invocations that overlap a burst against those that do not. If the")
    print("overlapping invocations are NOT the slow ones, A6.15's hypothesis is")
    print("refuted and must be reported as refuted.")
    print(f"{'arm':<14}{'n hit':>6}{'med hit':>10}{'n miss':>8}{'med miss':>10}"
          f"{'ratio':>8}")
    for name in sorted(arms):
        a = arms[name]
        h, m = a["hit_meds"], a["miss_meds"]
        mh = sorted(h)[len(h) // 2] if h else None
        mm = sorted(m)[len(m) // 2] if m else None
        ratio = f"{mh/mm:.3f}" if (mh and mm) else "--"
        print(f"{name:<14}{len(h):>6}{(f'{mh:.4f}' if mh else '--'):>10}"
              f"{len(m):>8}{(f'{mm:.4f}' if mm else '--'):>10}{ratio:>8}")

    print("\nNo repetition has been excluded, reweighted or adjusted by this "
          "script, and none may be on the strength of its output (Rule O, "
          "A6.9, A6.15 item 9).")


if __name__ == "__main__":
    main()
