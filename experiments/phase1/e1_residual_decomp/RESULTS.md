# E1 — AMD residual decomposition: RESULTS

Dated 2026-08-06. Hypotheses pre-registered in `../HYPOTHESES.md` (P1) before any run.

## Config

- Host: `broker` (moscxl), AMD EPYC 9754 (Bergamo, Zen4c), 2 sockets x 128 cores,
  16 MiB/CCX L3 (16-way), governor=performance, turbo=disabled, SMT=on (pinned
  to physical cores only: victim=cpu0, aggressor=cpus1-7, all within CCX0).
- Victim: 4 MiB pointer-chase, cpu0, local DRAM (node0), `-w 4096 -P -d 8 -W 2`.
- Aggressor: 7 threads, cpus1-7 (same CCX as victim), 64 MB/thread, `-d 16`,
  CXL node2 unless noted.
- resctrl groups `h3v` (victim, cpu0) / `h3a` (aggressor, cpus1-7); CAT 8/8 =
  `L3:0=ff00` (victim) / `L3:0=00ff` (aggressor); SMBA left at max (2048, no
  bandwidth cap) throughout E1 — this experiment isolates allocation/lookup
  effects, not the SMBA bandwidth knob (that's `exp35`, pre-existing, not part
  of this campaign).
- n=12 reps per arm/config, **rep-interleaved** (not blocked): loop is
  `for rep in 1..12: for arm in [...]: run`.
- Tax = median(cycles/iteration under load) / median(cycles/iteration,
  quiescent, same rep-loop). CI = paired bootstrap (B=20000) resampling reps
  with replacement, computing the ratio-of-medians each draw.
- Aggressor bandwidth verified two ways every run: (a) aggressor's own
  self-reported `bw_gbps`, (b) independent resctrl MBM
  (`mbm_total_bytes` delta / elapsed) on the aggressor group.
- Victim RMID `llc_occupancy` (resctrl CMT) sampled at ~4 Hz throughout each
  run; reported as the mean over samples.
- L3 uncore PMU (`l3_lookup_state.*`, `l3_xi_sampled_latency.*`) collected via
  `perf stat -C 0` wrapping the victim's full process lifetime (warmup+meas,
  not measurement-only — see caveat below).
- Scripts: `run_e1_gate.py` (A0-A3), `run_e1_a4a5.py` (A4/A5),
  `run_e1_a6.py` (A6). Raw JSONL per run in this directory.

## A0-A3: reproduction gate

**Why this is a fresh run, not a check against an old file:** the paper's
`tab:amdcat` source data (`H3_GATE_RESULT.md` bootstrap dataset,
`/tmp/task1_raw.jsonl`, n=210) is no longer on disk. A related, rougher
precursor file (`~/tmp_dutyfree_exp/H3_GATE_RESULT.md`, n=3, dated Jul 30)
*does* survive and reports WB=19.2x, CAT=7.47x, WC=0.98x — in the same
ballpark as the paper's numbers but not the same run. Per user direction,
this n=12 run is the new gate.

| arm | median tax | 95% CI (paired bootstrap) | paper's number | diff | gate (<=15%) |
|---|---:|---:|---:|---:|---|
| A1 WB (CXL, no CAT) | 19.886x | [19.728, 20.163] | 19.85x | +0.2% | **PASS** |
| A2 WB + CAT 8/8 | 7.225x | [6.886, 7.518] | 6.92x | +4.4% | **PASS** |
| A3 WC (CXL, no CAT) | 0.989x | [0.980, 0.999] | 1.02x | -3.0% | **PASS** |

Aggressor bandwidth (median, self-report / independent MBM):
WB 24.13 / 23.84 GB/s; WC 13.84 / 14.20 GB/s. Self-report and MBM agree to
within ~2.6% in every arm — no counter/timing disagreement to flag here.

**Gate verdict: PASS on all three arms.** Proceeding to A4-A6.

## Victim-side counters, A0-A3 (median across n=12)

| arm | victim IPC | victim L2 miss rate | victim LLC occupancy (mean bytes) |
|---|---:|---:|---:|
| A0 quiescent | 0.0448 | 86.02% | 3,246,030 |
| A1 WB | 0.0023 | 100.00% | 176,028 |
| A2 WB+CAT | 0.0062 | 90.81% | 2,976,493 |
| A3 WC | 0.0453 | 85.19% | 3,373,306 |

**Key early signal (P1 disambiguation):** under CAT (A2), victim LLC occupancy
stays at ~92% of the quiescent value (2.98M vs 3.25M bytes) — it does **not**
collapse — while L2 miss rate rises only modestly (86.0% -> 90.8%, +5.6pp)
against a 7.2x IPC/cycle tax. Capacity/occupancy is essentially intact; the
tax is not proportional to any hit-rate change. This is the same qualitative
pattern the paper's own `\jw` margin note flagged for the fused-kernel tax
("cycles/access rise far out of proportion to the miss-rate rise") — here it
recurs, more starkly, in the pointer-chase/CAT setting.

## L3 uncore PMU — methodology caveat (important, discovered during this run)

`l3_lookup_state.*` and `l3_xi_sampled_latency.*` are **uncore** events
(`Unit: amd_l3` in `perf list`), scoped to the whole L3 slice shared by all 8
cores in a CCX — not to core0/the victim alone. Confirmed empirically: A1 and
A2 both show ~4.17-4.23 **billion** `l3_miss` events over the ~11s perf
window, which matches the *aggressor's* own fill volume almost exactly
(24 GB/s x 11s / 64B $\approx$ 4.1 billion lines), not anything victim-scoped.
**These particular counters cannot isolate the victim's own L3 lookup/miss
behavior when the aggressor shares the same CCX** — documented here rather
than silently treated as victim-specific, per ground rule #6/"do not
substitute a similar event silently." Only the core-scoped counters opened by
`victim.c` itself (IPC, L2 hit/miss, cycles, instructions) are validly
victim-isolated in this same-CCX configuration. No probe-filter/back-
invalidation-specific PMC event was found in this platform's perf event list
either (Zen4c/Bergamo, perf 6.17.13) or in the one AMD PPR page reachable in
this environment (document #57228, Family 19h Model A0h — the viewer only
exposed a header page; no download tooling was available in this sandbox to
fetch the full PDF and check for un-mapped raw event codes). Both gaps are
left open rather than papered over.

## A4/A5/A6

*(to be appended after the n=12 runs complete)*
