# Phase 2.3 follow-up — PM-QoS and keep-awake-ticker tests: RESULTS

Dated 2026-08-07. Direct follow-up to the panel's proposed tests for E2b's
bimodal quiescent baseline (uncore frequency already ruled out; C6-disable
on cpu0 already tested and didn't fix it).

## Test 1: does either intervention eliminate the bimodal outlier? YES, decisively.

n=12 independent single-trial quiescent invocations (matching E2b's own
methodology exactly: fresh process, `--trials 1`, no aggressor) under three
conditions:

| Condition | median | min | max | spread |
|---|---:|---:|---:|---:|
| baseline (nothing held) | 81.99 | 81.63 | **87.85** | 6.22 |
| PM-QoS held at 0us (`/dev/cpu_dma_latency`) | 82.29 | 82.18 | 82.41 | 0.23 |
| keep-awake ticker (busy-spin on cpu20) | 81.59 | 81.48 | 81.78 | 0.30 |

Baseline shows the expected pattern: 11 tightly-clustered values plus one
~6 cyc/load outlier. **Both interventions show zero outliers across 12
trials**, spreads 20-25x tighter than baseline's. This is a real,
reproducible effect -- confirms *something* about idle-power-state
transitions (broader than the single C6 state tested earlier, since PM-QoS
blocks ALL deep C-states system-wide, not just C6 on cpu0) is the source of
the occasional large individual outlier.

## Test 2: does eliminating the outlier change E2b's tax RATIO? No -- medians barely move.

Quiescent medians across the three conditions: 81.99 (baseline, with its
outlier) / 82.29 (PM-QoS) / 81.59 (ticker) -- a ~0.7 cyc/load spread between
conditions, similar in size to ordinary run-to-run drift already seen
elsewhere in this campaign. **The median is already robust to the rare
single outlier** (that's what medians are for, and why this campaign uses
them) -- fixing the outlier changes the *tail risk* of any individual
single-trial measurement, not the *central tendency* the actual tax ratios
are computed from. This means the outlier-elimination result, while real
and worth understanding, is very likely **not** the explanation for E2b's
0.90-0.905x "faster than quiescent" finding.

## Test 3: rerun the actual quiescent-vs-D=256KiB comparison under PM-QoS -- messier than expected, not decisive

n=12 each arm, PM-QoS held throughout both. Quiescent behaved as expected
(median 82.41, one outlier at 88.90, otherwise tight 82.24-82.70). **The
D=256KiB loaded arm did not**: 5 of 12 trials showed large excursions
(89.26, 99.19, 108.44, 115.69, 126.38 cyc/load) far outside anything seen
for this exact condition in any prior measurement (original: tight
80-88 range; uncore-pinned: tight 81-87 range). Resulting median: 84.05,
giving **tax = 1.02x** -- qualitatively different from every prior
measurement of this same condition (0.90-0.905x).

**Investigated rather than accepted at face value**: checked for thermal or
power-limit throttling directly via `turbostat` during a matching 8-thread
D=256KiB load with PM-QoS held. **Ruled out**: core frequency stayed pinned
at 1894 MHz throughout (no DVFS throttling), core/package temperatures were
moderate (52C/57C, nowhere near thermal limits), package power (223 W) showed
no sign of hitting a cap. Whatever is causing the loaded arm's excess noise
under PM-QoS, it is not thermal or power-limit throttling.

**Not resolved. Leading candidates, untested**: PM-QoS forcing idle cores
into a `POLL` busy-wait state (confirmed via `turbostat`: 99% POLL on an
otherwise-idle cpu0 during the load) rather than a true halt could interact
with the 8 concurrently-launching aggressor processes' own scheduling in a
way a normal idle state wouldn't; or the per-rep overhead of launching and
tearing down 8 fresh processes every repetition (this script relaunches all
8 aggressors from scratch each rep, unlike the steadier persistent-aggressor
designs used elsewhere in this campaign) may itself be a source of timing
jitter that PM-QoS's forced-active idle state happens to amplify rather
than suppress.

## Verdict

**Do not use this result to revise E2b's original 0.90-0.905x finding.**
The PM-QoS/ticker interventions cleanly and reproducibly fix a real,
separate phenomenon (occasional large single-trial outliers in isolated
quiescent measurements) that does not explain the median-level tax ratio,
and attempting to extend the fix to the full co-run comparison introduced a
*different*, larger, and not-yet-understood noise source in the loaded arm
specifically -- one that was checked against the most likely candidate
(thermal/power throttling) and ruled out, rather than left as an untested
assumption. E2b's original numbers stand as measured. The true cause of the
median-level "faster than quiescent" effect remains open, now with two
more ruled-out candidates (C6 specifically; PM-QoS-fixable idle-outlier
noise) and one new, real, unexplained observation (PM-QoS's specific
interaction with an actively-launching multi-process aggressor load) worth
a dedicated follow-up rather than folding into this one.
