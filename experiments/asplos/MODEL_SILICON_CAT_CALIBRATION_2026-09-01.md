# The model reproduces CAT's cost almost exactly and over-predicts its protection

Date: 2026-09-01.  No new runs: this compares two frontiers already archived --
the 12-point gem5 CAT sweep (`data/gem5/rj3_runs.jsonl`) and the 15-point SPR
CAT sweep (`data/silicon_e2e_hashjoin.jsonl`).

## Normalisation

Absolute capacity is the wrong axis.  The model grants 0.25 MiB per way (5 MiB /
20) and SPR grants 4.0 MiB per way (60 MiB / 15), so matching on MiB pairs the
model's *near-full* mask with silicon's *tightest* -- opposite ends of the curve.

The right axis is **fraction of the LLC granted to the tenant**, because the
victim's working set is the same share of the LLC on both platforms:

    model:   2.59 MiB victim / 5 MiB LLC  = 51.8%
    silicon: 32 MiB victim / 60 MiB LLC   = 53.3%

## Result

| % LLC to tenant | model R | model cost | silicon R | silicon cost | dR |
| --- | --- | --- | --- | --- | --- |
| 5.0 | 93.4% | 41.1% | 91.4% | 42.0% | -2.0 pp |
| 13.3 | 94.9% | 36.2% | 82.3% | 38.9% | -12.5 pp |
| 20.0 | 95.3% | 34.1% | 73.9% | 35.9% | -21.5 pp |
| 40.0 | 96.7% | 25.6% | 44.1% | 25.2% | **-52.6 pp** |
| 60.0 | 75.3% | 15.3% | 18.2% | 13.6% | **-57.2 pp** |
| 80.0 | 24.8% | 5.3% | -2.8% | 4.4% | -27.7 pp |
| 100.0 | 0.0% | 0.0% | 0.2% | -0.0% | +0.2 pp |

**Tenant cost calibrates almost exactly.**  Across all seven comparable points
the model's predicted cost is within ~1-3 pp of silicon: 41.1/42.0, 36.2/38.9,
34.1/35.9, 25.6/25.2, 15.3/13.6, 5.3/4.4, 0/0.  This is a far stronger
calibration statement than the single-point claim currently in the draft, and it
covers the whole operating range rather than one width.

**Protection does not.**  The model's R is nearly flat and high (93-97%) from 5%
to 40% of the LLC and only then falls; silicon's declines steadily from 91% to
zero.  Mean |dR| across the comparable points is **24.8 pp**, peaking at 57 pp.

## Why this matters, and which way it cuts

The divergence is in the paper's favour, and that is worth stating explicitly.

The model makes CAT look *better at protecting* than it is.  P5 ("no way width
matches H2 on both axes") was therefore established against an inflated
opponent.  Concretely: at ~24% protection the model's cheapest sufficient width
is `wm16`, costing the tenant 5.3%, giving a wedge of +11.76%.  On silicon, 24%
protection sits near `cat08` at roughly 15.5% tenant cost -- so the same
comparison on real hardware would yield a **larger** wedge, not a smaller one.

**The model under-claims H2's advantage.**  A simulator that errs against its
author's thesis is the strongest available answer to "why should we believe
gem5", and this now rests on seven points rather than one.

## Secondary consequence

The model's protection curve being flat-high across most of its range is a
small-LLC artifact: with only 5 MiB and a victim occupying 52% of it, almost any
mask keeps the tenant out of the victim's way.  That is also why the model's
non-monotone dip appears at 8/20 ways (2.0 MiB) -- a capacity region 15-way CAT
on a 60 MiB LLC cannot express (its tightest mask is 4.0 MiB).  The silicon
sweep therefore neither confirms nor refutes the model's non-monotonicity; it
does not cover that regime.
