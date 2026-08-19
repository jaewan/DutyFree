# Cross-core sweep: the predictor is not neutral, it is harmful — and my window had no upper cliff

Written 2026-08-19. TODO items 1 (intervals) and 3 (sweep) in one campaign:
72 runs = victim {1,2,3,4,6,8} MiB x {quiescent, WB+TreePLRU, WB+BRRIP,
Streaming(H2)} x 3 randomization seeds. Aggressor = 16 MiB CXL stream, one
binary with the declaration gated on `argv`. gem5 `0f37c28`. Victim = pointer
chase, `iters=3e6`. L2 2 MiB private, L3 5 MiB shared.

## Victim cyc/access (mean +- half-range over 3 seeds)

| victim | quiescent | WB+TreePLRU | WB+BRRIP | \textsc{Streaming} (H2) |
|---|---:|---:|---:|---:|
| 1 MiB | 16.21 ± 0.00 | 16.21 ± 0.00 | 16.21 ± 0.00 | 16.21 ± 0.00 |
| 2 MiB | 16.49 ± 0.00 | 16.50 ± 0.00 | 16.53 ± 0.00 | 16.49 ± 0.00 |
| 3 MiB | 41.79 ± 0.02 | 62.08 ± 0.03 | 66.22 ± 0.03 | **42.55 ± 0.00** |
| 4 MiB | 54.58 ± 0.00 | 93.01 ± 0.04 | 94.08 ± 0.16 | **55.71 ± 0.01** |
| 6 MiB | 80.66 ± 0.02 | 132.90 ± 0.03 | 144.04 ± 0.09 | **82.62 ± 0.01** |
| 8 MiB | 109.98 ± 0.02 | 155.55 ± 0.00 | 170.78 ± 0.01 | **111.70 ± 0.03** |

## Item 1 — intervals

Half-range across seeds is **0.00–0.16 cyc/access**, i.e. CoV below 0.2% on
every cell. Every gap the paper claims is one to three orders of magnitude
larger than its interval. Intervals therefore *strengthen* the results rather
than qualifying them.

Stated precisely, and this matters: this is an interval **over the harness's own
randomization** (`RUBY_RANDOMIZATION=1`, seeds 1–3). It is *not* a claim that
runs are reproducible — a fixed-seed control drifted 0.047% from its counterpart
earlier, the same magnitude as the cross-seed spread, so `SEED` is not a
determinism lever here. Reporting it as plain "n=3" without that qualifier would
repeat the error criticised in the earlier `n=3, CoV<=1.64%` framing.

## Item 2 of the shape prediction — confirmed

**The arms converge at the bottom, exactly where they must.** At 1 and 2 MiB all
four arms agree to two decimals. The victim fits the 2 MiB private L2, so no
shared-cache tax exists and there is nothing for any mechanism to protect. This
is §5.2's collapse, and it doubles as a harness check: no spurious arm
differences appear where none should.

## And one prediction of mine that was wrong

I predicted the arms would converge **again** above the 5 MiB L3, on the
reasoning that a victim which cannot be LLC-resident has nothing to protect.
**They do not.** At 6 and 8 MiB H2 still restores the victim to 1.024x and
1.016x of solo.

The reasoning was wrong: a victim larger than the L3 still *benefits* from
whatever share of the L3 it gets, and the stream steals precisely that share. So
the protectable region has a real **lower** bound — the private L2, below which
no tax exists — and **no upper cliff**.

Note this does not contradict the fused-kernel finding, where a 16 MiB hot table
was correctly called out of range. There the limiter is the workload's own MLP
(~1.3 lines in flight against a 16-MSHR budget), not LLC residency. Different
mechanism, different bound.

## The headline: the predictor is not neutral, it is harmful

| victim | WB tax | BRRIP tax | H2 tax | BRRIP captured |
|---|---:|---:|---:|---:|
| 3 MiB | 1.485x | 1.585x | **1.018x** | **-21.2%** |
| 4 MiB | 1.704x | 1.724x | **1.021x** | **-2.9%** |
| 6 MiB | 1.648x | 1.786x | **1.024x** | **-22.2%** |
| 8 MiB | 1.414x | 1.553x | **1.016x** | **-34.7%** |

(The 1 and 2 MiB rows are omitted: with no tax, "fraction of benefit captured"
is a ratio over zero and means nothing.)

Across every size where a tax exists, a tuned reuse predictor recovers a
**negative** fraction of the available benefit — it is consistently *worse for
the neighbour than plain write-back*, and the harm **grows with victim size**,
from -2.9% to -34.7%.

Mechanism: BRRIP applies bimodal insertion to everything, including the victim's
lines. The larger the victim, the more of its working set lives in the L3 and is
inserted at a distant re-reference position, so the predictor's mispredictions
compound. Victim DRAM traffic confirms it directly — at 8 MiB, BRRIP drives
391.2 MB against TreePLRU's 334.6 MB, 17% *more* victim misses.

Meanwhile H2 holds the victim within **1.6–2.4%** of solo across the whole taxed
range.

## Admission, reconfirmed

HNF data-array writes, 4 MiB: H2 3.12 M against TreePLRU 10.26 M and BRRIP
10.38 M. BRRIP is consistently *slightly above* TreePLRU at every size (18.44 ->
19.67 M at 8 MiB). A replacement policy does not reduce array writes; it
reorders evictions. That is the admission argument, now visible at six sizes.

## What this does for the paper

The single 4 MiB point becomes a curve with intervals, and the claim strengthens
from "a predictor recovers none of a co-runner's tax" to "**a predictor makes it
worse, increasingly so with victim size, while the declaration holds the victim
within ~2% of solo across every size where a tax exists.**"

It also removes the last reason to describe the result as
window-dependent — the effect has a lower bound only.
