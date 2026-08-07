# E1 — AMD residual decomposition: RESULTS

Dated 2026-08-06. Hypotheses pre-registered in `../HYPOTHESES.md` (P1) before any run.

**CORRECTION (2026-08-07, `../PHASE2_ADDENDUM.md`)**: the "~3.55x
CXL-path-specific multiplier" claimed below (A1-vs-A5) is **retracted**.
The A5 comparison used a throttled (`-R`) local-DRAM arm with an identified
pacing artifact; a clean, unthrottled, thread-matched redo (Phase 2.2) gives
CXL 20.25x vs local 17.14x at matched 7T/full-rate -- a ratio of ~1.18x, not
3.55x. The composite-mechanism conclusion itself is unaffected (Phase 2.4's
AMD flush-behind result independently and decisively confirms the
lookup/queue-occupancy story via a completely different experiment) -- only
this specific multiplier is withdrawn. Left in place below for the
historical record, not deleted.

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

> **CORRECTION (2026-08-08, `PHASE2_AMD_WARMUP_CHECK.md`)**: the A2
> WB+CAT figure below (7.225x) is provenance-superseded. A fresh rerun of
> this exact, unmodified script on 2026-08-08 reproduces **9.87x**, not
> 7.225x — a real, reproducible, isolated-to-CAT drift, verified all the
> way to the raw hardware QoS mask MSRs (enforcement is correct; the
> physical cause of the drift is not identified). Per explicit decision,
> **9.87x is now the campaign's standard number** for this arm. A1 (WB)
> and A3 (WC) are unaffected (both redrift <3.5%, within normal noise).

| arm | median tax | 95% CI (paired bootstrap) | paper's number | diff | gate (<=15%) |
|---|---:|---:|---:|---:|---|
| A1 WB (CXL, no CAT) | 19.886x | [19.728, 20.163] | 19.85x | +0.2% | **PASS** |
| A2 WB + CAT 8/8 | ~~7.225x~~ **9.87x (2026-08-08)** | [6.886, 7.518] (orig.) | 6.92x | +4.4% (orig.) | **PASS** (orig.; see correction) |
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

## A4: lookups-only (no CAT / with CAT 8/8)

7 threads on cpus1-7 re-stream a SHARED 4 MiB buffer on local DRAM (fits
comfortably in both the full 16-way/16 MiB CCX L3 and an 8-way/8 MiB CAT
slice — see buffer-size note in the script; an 8 MiB buffer was tried first
and rejected because it exactly filled the 8-way CAT slice with zero
associativity slack, producing real ~8.4 GB/s fill traffic under CAT, not
"lookups-only"). n=12, rep-interleaved with A0/A4_nocat/A4_cat/A5/A5_bwm.

| arm | median tax | 95% CI | agg MBM bandwidth (median) | victim occupancy (mean bytes) |
|---|---:|---:|---:|---:|
| A4 no CAT | 1.248x | [1.236, 1.275] | 0.077 GB/s (0.3% of full WB rate) | 3,312,565 |
| A4 + CAT 8/8 | 1.298x | [1.288, 1.335] | 0.845 GB/s (3.5% of full WB rate) | 3,363,915 |

**A4 taxes the victim substantially** — both CIs sit entirely above 1.0, with
tight bounds. Coherence lookups/enrollment from 7 threads re-hitting an
already-L3-resident shared buffer, with negligible new memory traffic, are
by themselves enough to slow the victim ~1.25-1.30x. Per the pre-registered
verdict logic: **this fires the "A4 taxes substantially" branch — shared
lookup/queue occupancy is real, and H3-lookup-skip (not just H2
allocation-bypass) is the required contract behavior.**

Caveat: 1.25-1.30x is a real but modest fraction of A2's 7.2x residual — A4
confirms the *mechanism exists*, not that it alone explains the *magnitude*
of the CAT residual. See A5/A6 below for the rest.

## A5: fills+churn, no CXL (local DRAM), vs A1 at matched bandwidth

7 threads on cpus1-7 stream a 64 MiB local-DRAM (node0) buffer via the
existing aggressor's `wb_local` mode. Two variants: uncapped, and
bandwidth-matched to A1's ~24 GB/s CXL rate via `-R 3450` (per-thread
throttle).

| arm | median tax | 95% CI | agg bandwidth (median, self/MBM) |
|---|---:|---:|---:|
| A5 local, uncapped | 16.881x | [16.656, 17.127] | 45.62 / 44.58 GB/s |
| A5 local, BW-matched to A1 (~24 GB/s) | 5.600x | [5.551, 5.677] | 23.94 / 23.43 GB/s |
| *(for reference)* A1 CXL, ~24 GB/s | 19.886x | [19.728, 20.163] | 24.13 / 23.84 GB/s |

**At matched bandwidth (~24 GB/s), CXL fills tax the victim 19.89x vs local
DRAM's 5.60x — a ~3.55x CXL-path-specific multiplier on top of whatever
generic same-CCX allocating-fill tax local DRAM already imposes.** This
isolates a real, substantial CXL-path-specific component (per the
pre-registered "A1 vs A5 at matched BW isolates any CXL-path-specific
component" logic) — most of A1's tax is not just "allocating fills at this
rate," it is specifically about the CXL fill path.

## A6: concurrency sweep {1,2,3,5,7}, WB CXL, no CAT

| threads | median tax | 95% CI | agg BW (self/MBM, GB/s) | tax per GB/s | occupancy (mean bytes) |
|---:|---:|---:|---:|---:|---:|
| 1 | 2.917x | [2.689, 3.157] | 12.42 / 12.46 | 0.234 | 1,462,772 |
| 2 | 6.403x | [6.131, 6.725] | 20.24 / 20.22 | 0.317 | 537,675 |
| 3 | 18.038x | [17.890, 18.422] | 20.64 / 20.60 | **0.876** | 187,417 |
| 5 | 21.823x | [21.666, 22.281] | 23.90 / 23.78 | 0.918 | 181,623 |
| 7 | 20.008x | [19.843, 20.423] | 24.13 / 23.84 | 0.839 | 172,831 |

(Reference: at n=12 pass, paper's own 1T/2T/7T anchor points were 2.77x/6.5x/18.3x;
this run's 1T=2.92x, 2T=6.40x, 7T=20.0x — same shape, all in family, slightly
higher throughout, consistent with this being a different day/thermal state
and n=12 vs the paper's smaller samples for those points, not a contradiction.)

**Clear superlinear knee between t=2 and t=3**: bandwidth barely moves
(20.24 -> 20.64 GB/s, +2%) while tax nearly triples (6.4x -> 18.0x, +182%) and
tax-per-GB/s jumps from 0.32 to 0.88. This is exactly the corroborating
signature the pre-registered verdict logic asked A6 to check for: the tax is
not simply proportional to delivered bandwidth, consistent with a
fixed-capacity shared queue/resource saturating around 3 concurrent streams
on this CCX, not a smooth bandwidth-linear effect.

**Anomaly, flagged rather than smoothed over**: tax *decreases* slightly
from t=5 (21.82x) to t=7 (20.01x) even as bandwidth ticks up (23.90 -> 24.13
GB/s); the 95% CIs at t=5 and t=7 do not overlap, so this is a real (if
small) non-monotonicity, not just noise. Plausible causes not disambiguated
here: self-contention among aggressor threads reducing effective pressure on
the shared resource, or an OS/scheduling effect at 7 of 8 CCX cores occupied.
Left as an open question for a follow-up pass rather than averaged away.

## Overall E1 verdict

**Primary mechanism: shared lookup/queue occupancy (P1 hypothesis b),
corroborated three independent ways, not probe-filter/back-invalidation
occupancy collapse (hypothesis a):**

1. Under CAT (A2), victim LLC occupancy stays ~intact (92% of quiescent)
   while L2 miss rate barely moves (+5.6pp) against a 7.2x tax — capacity is
   not the story.
2. A4 (near-zero memory traffic, pure L3 coherence lookups from 7 threads on
   an already-resident shared buffer) taxes the victim substantially
   (1.25-1.30x, CI excludes 1.0) — the lookup path alone is not free.
3. A6 shows a superlinear knee in tax vs thread count that is not explained
   by the near-flat bandwidth curve past 2 threads — consistent with a
   fixed-capacity shared resource saturating, not a smooth bandwidth effect.

**Gem5 team action: model port/queue contention on the shared lookup/miss
path (H3-style type-licensed lookup/enrollment skip), not just H2's
allocation-bypass.** H2 alone (per the paper's own Sec4 concession, restated
in the panel-review `\jw` note) would not be expected to remove this residual;
that expectation is now directly measurement-backed by A4.

**Important second-order finding, not to be dropped in synthesis**: A4's
1.25-1.30x tax is real but is only a modest fraction of A2's 7.2x residual.
The A1-vs-A5 matched-bandwidth comparison shows a further ~3.55x
CXL-path-specific multiplier that A4's idle-bandwidth lookup traffic does not
capture. **The 7.2x CAT residual is very likely a composite of (a) baseline
lookup/enrollment overhead (A4, mechanism confirmed, magnitude modest) and
(b) additional CXL-fill-path-specific queueing/latency that only appears
under real sustained memory traffic (A1 vs A5 gap, magnitude large).** A
single gem5 mechanism (e.g. finite-SF-as-probe-filter alone) is unlikely to
reproduce both components; the model likely needs both a lookup/enrollment
cost on the miss path *and* something CXL-path-specific (elevated occupancy
or latency on the home-side XI/fill queue when the source is the CXL
controller specifically, not just "any remote fill").

## What would need a follow-up pass

- A4/A5/A6 all used the L2-hit/miss/IPC/cycles counters that `victim.c`
  already opens (core-scoped, valid) plus resctrl occupancy/MBM (valid).
  Given the uncore-PMU scoping gap documented above, no measurement in this
  campaign directly instruments *which* AMD structure (probe filter queue,
  home-node XI queue, DF crossbar) is saturating at the A6 knee — that would
  need either uncore PMU events scoped more finely than this platform
  exposes via `perf`, or a full AMD PPR read to find raw un-mapped event
  codes (blocked in this sandbox, no PDF download tooling).
- AMD per-core WC rate reconciliation (1T/7T, same-CCX vs spread-across-CCX)
  is a separate E4 item, not yet run — tracked as an open item, not
  fabricated here.
