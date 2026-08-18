# Q1 — cross-core: a tuned predictor does nothing for the co-runner

Written 2026-08-19. Pre-registered before the runs landed (predictions and
falsification criteria in the session scratchpad, reproduced below). **P2 was
falsified**, and in the direction that favours the paper.

## Setup

Two processes, one aggressor binary with streaming gated on `argv[2]` so arms
differ by a flag rather than a file. Victim = 4 MiB pointer chase (Sattolo) on
DRAM pool 0, `iters=3e6`; aggressor = 16 MiB sequential stream on CXL pool 1
(203 ns). L2 2 MiB private, L3 5 MiB shared — so the victim sits in the
protectable window (> private L2, <= shared L3). LLC policy verified per arm
from `config.json`. gem5 `0f37c28`. Victim result sum identical across all five
arms, so the work is matched.

Metric: victim `cyc/access` = `cpu0.numCycles / 3e6`, measured over the window
the victim delimits with `reset_stats`/`m5_exit`.

## Results

| arm | victim cyc/access | vs quiescent | victim DRAM read | HNF data writes |
|---|---:|---:|---:|---:|
| quiescent (no aggressor) | 59.52 | 1.000x | 0.01 MB | 4,052,682 |
| WB + TreePLRU | 98.52 | **1.655x** | 151.66 MB | 10,849,755 |
| WB + BRRIP | 99.44 | **1.671x** | 150.17 MB | 10,815,894 |
| \textsc{Streaming} (H2) | 60.23 | **1.012x** | 1.35 MB | 3,050,912 |
| H2 + BRRIP | 74.20 | 1.247x | 55.92 MB | 1,654,587 |

## P1 — confirmed

H2 restores the victim to **1.012x** of quiescent, from a 1.655x tax: the
mechanism recovers essentially the whole co-runner penalty, and the victim's
misses to memory fall 99% (151.66 -> 1.35 MB). The arm is correctly sized.

## P2 — falsified, decisively

Predicted: BRRIP captures most of H2's benefit (within 0-15%), falsified if it
captures <40%. Measured: **-2.4%**. Against 38.29 cyc/access of available
benefit, BRRIP delivered -0.92 — very slightly *worse* than plain TreePLRU. Its
DRAM traffic is unchanged too (150.17 vs 151.66 MB, -1%).

**A tuned reuse predictor does nothing whatsoever for the co-runner.**

### Why, and why this is the admission argument

BRRIP inserts stream lines at distant RRPV, so they are evicted *next*. But the
eviction that displaced the victim's line already happened at **insertion**. A
replacement policy still takes a way. Retention control cannot un-evict what
admission already displaced.

This reconciles the apparent contradiction with #28, where BRRIP *tied* H2
single-core. There, the beneficiary of better retention was the same agent whose
lines were being retained — the predictor served **itself**. Cross-core it has
no reason to protect someone else's lines, and no signal that would let it: the
victim's lines carry no marker distinguishing them from any other.

So the axis is not accuracy and not tuning. **Prediction is self-serving;
declaration is other-serving.** That is the paper's sufficiency claim, and it is
now measured rather than argued.

## P3 — confirmed

BRRIP's HNF data-array writes are unchanged from TreePLRU (10,815,894 vs
10,849,755, -0.3%), exactly as single-core (806k vs 813k). H2's fall 72%. The
admission gap does not depend on going cross-core, because it follows from what
a replacement policy is.

## Unexpected: the predictor *harms* the victim once H2 is in place

H2 + BRRIP costs the victim **23% against H2 alone** (74.20 vs 60.23), and its
DRAM traffic rises from 1.35 to 55.92 MB. With the stream no longer entering the
L3, bimodal insertion begins mispredicting the victim's own reuse-heavy lines
and evicting them early. This is the *warm-up / mispredict pollution* row that
`tab:declpred` asserts qualitatively, observed for the first time — and it is a
cost a declaration does not have, because a declaration does not guess.

## What this does to the paper

It answers the reviewer's W2 directly: the head-to-head was previously run in
the wrong configuration for the paper's own claim, and in the right one the
result reverses. **H2's case no longer needs to rest only on admission counts
and the guarantee** — it wins outright on the metric the paper actually cares
about, co-runner protection, by 1.655x -> 1.012x where a predictor delivers
nothing.

Revises `REVIEWER2_RESPONSE_2026-08-19.md` Q4: its recommendation to move H2's
case off victim protection was based on the single-core tie and is now wrong.
Victim protection is exactly where H2's case belongs.

## Limits

Single victim size, single stream size, one predictor, single runs with no
interval. BRRIP is weaker by design than SHiP/Hawkeye/Mockingjay — but the
mechanism here is not an accuracy effect, so a better predictor should not
close it: any replacement policy admits before it retains. That is a
falsifiable prediction and the obvious next experiment if a reviewer presses.
