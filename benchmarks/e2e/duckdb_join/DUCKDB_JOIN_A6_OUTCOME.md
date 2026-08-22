# Outcome: A6, the 30-repetition stability block on `moscxl` (EPYC 9754)

Dated 2026-08-23. Implements `DUCKDB_JOIN_CORUN_PREREGISTRATION.md` A6.0--A6.17.
Nine arms x 30 repetitions, **270/270 valid, 0 invalid, 0 aborts**, exactly 30
repetitions of each arm, `mbm_monotonic` true on all 270. One contiguous block,
2026-08-22 23:24:37 -- 2026-08-23 04:23:12 local, host frozen at `d8eda44` and
verified against it in the log before the first arm.

Nothing was changed from the campaign except **n**, per A6.2.

## Verdict: A6.4 branch 2. S3 fails, S1 and S2 pass.

|  | result |
|---|---|
| **S3** CoV_rep < 5% untrimmed, both primary arms | **FAIL** — `FB0_match` 9.13%, `FB256_match` 30.50% |
| **S1** sign stable under all 30 leave-one-out | **PASS** |
| **S2** LOO range <= 20% of point estimate | **PASS** — 7.0% and 0.0% |

The declared sentence for this branch, fixed in advance in A6.4 and reproduced
here with `D` and `R` filled in:

> The AMD host remains under §6 outcome 5 and yields **no verdict**. It may not
> be quoted as a vendor null either. What 30 repetitions add is that the
> within-binary difference is *stable* under resampling at this operating point
> while its interval is not trustworthy: the point estimate is **+0.333** with a
> leave-one-out range of **[+0.321, +0.345]**, and the sign does not turn. That
> is a bounded observation about a host that fails its stability bar, it is not
> a de-confound, and it does not enter the paper as a result.

Per A6.2, **there is no third campaign at this operating point.**

Per A6.2's fixed sentence, the CoV moved and the only available explanation is
stated in advance: nothing was changed except n. Here the CoV moved *up*
(13.10% -> 30.50% on `FB256_match`), which is the same fact in the other
direction — the n = 10 estimate was imprecise, in both directions, because the
quantity being estimated is the incidence of a rare tail.

## The measurements

| arm | GB/s | MBM GB | occ MiB | median s | tax | 95% CI | CoV_rep |
|---|---:|---:|---:|---:|---:|---|---:|
| `quiescent` | -- | 1.44 | 9 | 0.0290 | 1.000 | -- | 3.95% |
| `WB_sat` | 24.24 | 56.24 | 0 | 0.2340 | 8.195 | [8.069, 8.339] | 2.81% |
| `FB0_sat` | 24.21 | 56.23 | 0 | 0.2340 | 8.212 | [8.069, 8.357] | 2.80% |
| `WB_local` | 24.25 | 56.39 | 0 | 0.2340 | 8.330 | [8.069, 8.357] | 4.09% |
| `NTA_sat` | 24.53 | 14.07 | 2 | 0.1490 | 5.281 | [5.112, 5.321] | 3.84% |
| `FB256_sat` | 16.95 | 6.42 | 5 | 0.0740 | 2.625 | [2.562, 2.655] | 2.83% |
| `WB_fbmatch` | 12.71 | 9.38 | 2 | 0.0430 | 1.500 | [1.448, 1.526] | 16.73% |
| `FB0_match` | 12.73 | 9.30 | 2 | 0.0420 | 1.464 | [1.448, 1.526] | 9.13% |
| `FB256_match` | 15.41 | 3.45 | 7 | 0.0330 | 1.158 | [1.121, 1.193] | 30.50% |

Declared pairs, rep-paired percentile bootstrap, B = 20000, seed 20260821:

| pair | difference | 95% CI | LOO range | status |
|---|---:|---|---|---|
| `FB0_match` - `FB256_match` (within-binary, matched) | +0.333 | [+0.298, +0.377] | [+0.321, +0.345] | **no verdict** |
| `WB_fbmatch` - `FB256_match` (cross-binary, matched) | +0.321 | [+0.276, +0.357] | [+0.321, +0.321] | **no verdict** |
| `WB_fbmatch` - `FB0_match` (instrument check, expect 0) | **+0.000** | [-0.069, +0.052] | -- | **passes** |
| `FB0_sat` - `FB256_sat` (NOT bandwidth-matched) | +5.552 | [+5.509, +5.696] | -- | anti-conservative, not quotable alone |
| `WB_sat` - `NTA_sat` (declared negative control) | +2.974 | [+2.931, +3.018] | -- | outcome 3 fires, as in the campaign |

**§5's bandwidth assertion passes cleanly, per repetition, on all 270 arms** —
worst deviation from the A4.5 declared value −2.2%.

## What reproduced

Every point estimate reproduced at 3x the repetitions, on a frozen host, six
weeks of apparatus work later:

| quantity | campaign (n=10) | A6 (n=30) |
|---|---:|---:|
| `WB_sat` tax | 8.175 | 8.195 |
| `NTA_sat` tax | 5.281 | 5.281 |
| `WB_sat` - `NTA_sat` | +2.897 | +2.974 |
| primary difference | +0.263 | +0.333 |
| instrument check | +0.034 | +0.000 |
| anomaly incidence | 2/150 = 1.3% (A6.1) | 3/270 = 1.1% |

The instrument check landing at **exactly** +0.000 is worth one sentence,
because it is the one pair declared to be zero: two allocating arms at 12.71 and
12.73 GB/s from *different binaries* differ by nothing at all, with an interval
spanning zero. The cross-binary pairing is not contaminated.

The anomaly incidence reproducing at 1.1% against A6.1's 1.3% is the substantive
replication here. **The tail is a real, stable property of this operating point
at roughly 1 invocation in 90.** What it is not is stationary within a block:
all three anomalies fell in the first half (1st/2nd half = 1/0 in each of the
three arms), and the seven arms with no anomaly have none in either half.

## A6.15 is refuted, and is reported as refuted

A6.15 declared, before the CoV was known:

> If the overlapping invocations are NOT the slow ones, A6.15's hypothesis is
> refuted and must be reported as refuted.

They are not. **None of the three anomalies overlaps any foreign burst.**

| anomaly | window (local) | foreign bursts inside | nearest |
|---|---|---:|---|
| `FB0_match` inv1, 1.45x | 23:42:53--23:43:11 | **0** | `v3agent` −1015 s |
| `FB256_match` inv5, 2.76x | 00:15:14--00:15:41 | **0** | `v3agent` **+17 s** (after the window closed) |
| `WB_fbmatch` inv9, 1.84x | 01:04:20--01:04:41 | **0** | `v3agent` −2903 s |

`FB256_match` inv5 is the near-miss and is stated explicitly because it is the
one that could be narrated the wrong way: the burst is 17 seconds *after* that
invocation's measured window ended. It did not touch it.

The converse test is equally clean. Eight of 270 invocations do overlap a
genuine foreign transient, and **not one of them is slow**:

| arm | inv | ratio to arm median | overlapping burst |
|---|---|---:|---|
| `WB_local` | 19 | 1.004 | `v3agent` @ 1150% |
| `WB_sat` | 29 | 0.996 | `v3agent` @ 1100% |
| `FB0_sat` | 24 | 0.991 | `v3agent` @ 400% |
| `NTA_sat` | 4 | 0.987 | `sar.sysstat` @ 253% |
| `FB256_sat` | 0 | 0.986 | `v3agent` @ 242% |
| `NTA_sat` | 18 | 1.000 | `v3agent` @ 58% |
| `WB_sat` | 3 | 1.000 | `suarez` @ 1% |
| `WB_sat` | 4 | 1.000 | `v3agent` @ 44% |

Median ratio 0.998, range 0.986--1.004, none within reach of the 1.4x threshold.
Per A6.16 the 1150% burst was at least 11 concurrent threads — the widest event
in the block — and it cost `WB_local` inv19 four parts in a thousand.

Three limitations of this test are stated before it is relied on.

1. **The "601 foreign bursts" headline figure is misleading and I am correcting
   my own instrument.** 585 of the 601 lines are a *single resident process*
   (`v3metricd`, pid 6448) re-logged at the watcher's 30 s dedup interval. It is
   a constant, not a burst. The genuine transients number **16**, and the
   arms-overlapping figure is **8/270 = 3.0%**, not the 178/270 that
   `overlap_bursts.py` prints in its `hits` column. A6.14 predicted "~15 bursts
   touching ~5% of arms" in advance; 16 bursts touching 3.0% is a good
   calibration of the prediction and a bad reflection on the summary column,
   which counts the resident daemon as a hit and is therefore saturated at 30/30
   on the long arms. The `overlap_bursts.py` attribution table's ratios
   (0.987--1.024) are dominated by that constant and carry much less than they
   appear to; the eight-invocation table above is the test that has content.
2. **The three dispersed arms have zero overlapping invocations.** All eight
   overlaps fall in saturated arms, which are also the least sensitive arms in
   the campaign. So there is no within-arm hit/miss comparison available for
   `FB0_match`, `WB_fbmatch` or `FB256_match`. This cuts *toward* the
   refutation rather than against it — bursts cannot explain dispersion in arms
   that never overlapped one — but it means the refutation rests on the absence
   of overlap, not on a matched contrast inside the dispersed arms.
3. Per A6.15 item 9 and Rule O, **nothing here licenses an exclusion.** No
   repetition has been excluded, reweighted or adjusted, and none may be. All
   30 enter every figure above.

## What the anomaly is, and what is now excluded

The A6.13--A6.17 apparatus investigation was undertaken to find the independent
marker A6.1 could not find. It did not find one. What it did do is close doors,
and the doors are worth listing because each was open when the block started:

- **Not foreign CPU bursts.** Refuted above.
- **Not a competing cache experiment.** The resctrl-group check in
  `assert_quiescent` has no age exemption and never fired in 270 arms; a
  foreign resctrl group would have aborted the block. This is a positive
  exclusion, not an absence of observation.
- **Not page placement.** A5.2, hugepages: 5.69% against a contemporaneous
  5.90%, needing < 3%.
- **Not the timer quantum.** The half-quantum floor is 1.2--1.4% against
  5.7--30.5% observed.
- **Not within-invocation sampling noise.** 4.5x--12x too small (campaign
  outcome document, variance decomposition).
- **Not a warm-up transient.** Occupancy reaches its level by the first 0.25 s
  sample.
- **Not co-run at all.** A5.2's fresh *quiescent* arm — no streamer, idle
  frozen host — produced CoV_rep 13.40% with one invocation at 0.0400 s against
  0.0280. The excursion happens with the aggressor absent.

The correlation with victim residency is real and reproduces (r = −0.856,
−0.605, −0.830 across blocks) but is a description of the anomaly, not a cause
of it: less cache retained, slower, with nothing yet identified that decides how
much cache a given invocation retains.

**The finding A5.1 clause 3 anticipated is the one that stands.** A 16 MiB CCX
cannot host this victim at a stable operating point, the instability is a
property of the operating point rather than of any contaminant found so far, and
per A6.4 that is reported as the result rather than retuned around.

## The exposure asymmetry, declared in A6.14 before the data

Arm duration is not equal across arms, so exposure to any time-homogeneous
external process is not equal either. Measured over the block: `WB_local`,
`FB0_sat` and `WB_sat` windows run ~71 s against `FB256_match`'s ~11 s and
`quiescent`'s ~9 s — a 6.9x spread.

**In both matched pairs the allocating arm is the longer and more exposed one.**
Any external perturbation therefore inflates the allocating arm preferentially,
which inflates the measured difference. This asymmetry is **anti-conservative**,
opposite in direction to A4.4's two conservative asymmetries, and was declared
as items 5 and 6 before the block. It does not bite here — the refutation above
shows external bursts moved nothing — but it is recorded because it would bite
in any future block at this operating point, and because it was declared in
advance and must be answered in either direction.

## The aborted partial, reported as A6.2 requires

The first attempt aborted at 96/270 on a `v3agent` burst at 73.9% (A6.9). The
partial is retained at `artifacts/join_corun30_moscxl.ABORTED_96.jsonl`, 96
records, all valid, 20:47--22:30 local on 2026-08-22, 10--11 repetitions per arm.
Per A6.2 it is **not merged** into anything and no figure above uses it.

Reported because A6.2 requires it, and because it does not say what the block
says:

| arm | aborted partial CoV (n=10--11) | A6 CoV (n=30) |
|---|---:|---:|
| `FB256_match` | 2.35% | 30.50% |
| `FB0_match` | 5.96% | 9.13% |
| `WB_fbmatch` | 7.04% | 16.73% |

Its medians match the block's to the millisecond (`FB256_match` 0.0335 vs
0.0330, `FB0_match` 0.0420 vs 0.0420, `WB_sat` 0.2340 vs 0.2340), and it
contains no anomaly at all. That is exactly what a ~1% tail looks like sampled
96 times, and it is the clearest available demonstration of A6.2's point that
the n = 10 CoV estimate is imprecise in both directions. It is **not** evidence
that the operating point is stable, and may not be cited as such.

## Apparatus defects found during the block, all recorded before the outcome

Recorded here by reference; each is written up at the cited section, and each
was written *before* any outcome quantity was known.

- **A6.13** — the A6.10 age exemption, deployed to stop ssh logins aborting
  blocks, silenced the guard against `v3agent`, the specific process that ended
  the previous attempt. I did not see that when I deployed it. Not reverted
  mid-block, per the apparatus rule.
- **A6.13, the deeper point** — `assert_quiescent` runs *between* arms only
  (`run_join_campaign.py:462`), so a mid-arm burst is invisible under **any**
  guard rule. This corrects A6.9's stated mechanism.
- **A6.14** — the exempt bursters are a class, not one process.
- **A6.14 addendum, corrected by A6.17** — my `<5 s` burst-duration bound was
  wrong by 6x; the watcher dedups per (pid, comm) for 30 s, so one line is one
  *event* and the correct bound is < 30 s. This makes the median-of-300
  reassurance weaker, not stronger.
- **A6.16** — pcpu > 100% cannot be a lifetime-averaging artifact and lower-
  bounds concurrent thread count. This corrects the A6.14 addendum's
  over-broad dismissal of pcpu.
- **A6.17** — I asserted to the lead that there was no watcher log on the host.
  There is, at `artifacts/contention_watch.log`; I had searched `/tmp` only. The
  monitor stream is lossy and begins at 30/270; the analysis above uses the
  on-host log, which is complete. Also: `suarez` was already in the watcher's
  `AV_COMM` set on my own disk, so one interrupting login was avoidable.
- **A6.12** — `wait_for_streamer` times out silently on the f256 arms. A
  `streamer_settle_timeout` boolean is still to be added. A churn-appropriate
  settle criterion for those arms is a §9 lead-only decision.
- **`summarize_stability.py`** divided by a zero point estimate when the
  instrument-check pair landed at exactly +0.000. Fixed in the reporter only
  (span `--`, S1/S2 `n/a`), because that pair's declared criterion is an
  interval spanning zero, not this ratio. No declared quantity changed.

## Provenance

- `artifacts/join_corun30_moscxl.jsonl` — 270 records, the block
- `artifacts/corun30_moscxl.log` — run log; **appended across both attempts**,
  lines 121--130 are the first attempt's abort
- `artifacts/join_corun30_moscxl.ABORTED_96.jsonl` / `.ABORTED_96.log` — the
  retained partial, never merged
- `artifacts/contention_watch.log` — 4806 lines, the complete on-host watcher
  record; `/tmp/contention_watch.py` is its source, pinned to cpu200 on the
  other socket
- `summarize_corun.py`, `check_bandwidth_assertion.py` — unchanged, per A6.6
- `summarize_stability.py` — S1/S2/S3, Rule O trim and incidence; committed
  before the first record existed
- `overlap_bursts.py` — A6.14 items 5/6 and A6.15 item 7; written and tested
  blind at ~151/270 against a synthetic fixture, before any outcome was known.
  Read its `hits` column with limitation 1 above in hand.

Reproduce with, from this directory:

```
python3 summarize_corun.py            artifacts/join_corun30_moscxl.jsonl
python3 check_bandwidth_assertion.py  artifacts/join_corun30_moscxl.jsonl
python3 summarize_stability.py        artifacts/join_corun30_moscxl.jsonl
python3 overlap_bursts.py             artifacts/join_corun30_moscxl.jsonl \
                                      artifacts/contention_watch.log
```

## What is now open, and to whom

`DUCKDB_JOIN_AMD_CORUN_OUTCOME.md` is **not** amended: A6.4 directs amendment
only in the S1-or-S2-fails branch, and both passed. The campaign's +0.263 is
neither retracted nor promoted.

Any consequence for **L5**, for the paper's page-1 evidentiary posture, or for
whether an AMD number appears at all remains a **§9 lead-only decision** and is
not taken here.
