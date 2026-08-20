# The tax inconsistencies: one stale table, one unreconciled arm difference

Written 2026-08-20. Investigating why the paper reports different WB taxes for
what a reader will take to be the same condition.

## The inventory

Three values coexist for "the model's WB victim tax at 53% WSS":

| source | value | arm as recorded |
|---|---:|---|
| `tab:gem5` (Sec5) | 1.60$\times$ | matched **local-DRAM** aggressor, Gate-1 harness, commit `b2c6499` |
| `tab:sens` (Appendix) | **1.22$\times$** | 53% WSS, 20-way, infinite SF — aggressor not named in the caption |
| `tab:h3sf` (Appendix, mine, 2026-08-20) | 1.369$\times$ | 16 MiB **CXL** aggressor, DMT off, 65,536-entry SF row set |

## Finding 1 — `tab:sens` carries superseded values, and this is documented

`GATE1_SENS_RERUN_OUTCOME.md` (task #25, commit `528a84f`) re-ran the whole
table at a recorded commit and measured, at 53% WSS / 20-way:

- victim alone 33.867 cyc/iter
- WB tax **1.369** against published 1.22
- H2 tax **1.041** against published 1.05
- recovery **88.8%** against published 77%

and across the assoc sweep found measured WB running **11–19% above published**
in one consistent direction, with recovery **89–92%** against published 76–84%.
Its own recommendation: *"Recommend replacing `tab:sens`'s published values with
the measured column above, captioned as a current-HEAD re-run."*

**That recommendation was never acted on.** The paper still carries 1.22 / 1.05
/ 77%.

**My run independently confirms it.** The `tab:h3sf` re-measurement — a
different harness, a different aggressor placement, a different commit, run for
an unrelated purpose — lands on victim-alone **33.88** against its 33.867, and
WB tax **1.369** against its 1.369. Two independent measurements agree to three
decimals; the published number does not.

So this is not an inconsistency to explain. It is a stale table with a
documented, now doubly-confirmed replacement, and the replacement moves the
paper's numbers **up** (recovery 77% → 88.8%), which §4.3 permits precisely
because it is earned by a run at a recorded commit.

## Finding 2 — `tab:gem5` vs `tab:sens` is a real arm difference the paper never reconciles

1.60$\times$ and 1.369$\times$ are both "the model's WB tax at 53% WSS", and
they differ because the aggressors differ: `tab:gem5`'s is the Gate-1
local-DRAM arm, `tab:sens`'s is the p1batch same-L3 arm. Both are legitimate.
Neither table tells the reader the other exists.

Under §5.1 — *every tax figure names its arm and its operating point at the
point of use* — that is a defect even though both numbers are correct. It is
the same failure mode pass 5 caught when a CXL-latency co-run pair was
described as "a milder point on the same pressure curve" as a local-DRAM arm.

**Pending measurement.** A DMT $\times$ aggressor-placement decomposition is
running (victim 2650 KiB, WB aggressor, {DMT on, off} $\times$ {CXL, local-DRAM},
3 seeds) to establish how much of the 1.369$\rightarrow$1.60 gap is placement
and how much is DMT. Note the sens re-run reached 1.369 with a *local-DRAM*
aggressor while I reached 1.369 with a *CXL* one, which already hints that
placement is not the dominant term at this victim size — the decomposition will
settle it.

## Finding 3 — the tax-vs-WSS *shape* is consistent, and should not be read as a conflict

`tab:gem5` shows the tax rising with WSS (1.60$\times$ at 53%, 2.25$\times$ at
100%). My cross-core sweep shows it **peaking and then falling**: 1.485$\times$
at 3 MiB, 1.704$\times$ at 4 MiB, 1.648$\times$ at 6 MiB, 1.414$\times$ at
8 MiB.

These agree. The tax is a *ratio*, and once the victim outgrows the LLC its solo
baseline degrades too (quiescent goes 41.79 → 54.58 → 80.66 → 109.98
cyc/access), so the denominator grows faster than the numerator and the ratio
declines. `tab:gem5` samples only up to 100% of LLC, which is at or just past
the peak. Both datasets show the tax rising through that region.

Worth stating explicitly somewhere, because a reviewer comparing the two will
otherwise see a monotone table beside a non-monotone one.

## Recommended actions

1. **Update `tab:sens`** to task #25's measured column, captioned as a
   current-HEAD re-run, now citing two independent confirmations of the
   53%/20-way point. This also removes the internal clash my `tab:h3sf` update
   created — which was useful, since it is what surfaced the stale table.
2. **Name the aggressor arm in both `tab:gem5` and `tab:sens` captions**, so
   1.60$\times$ and 1.369$\times$ stop looking contradictory.
3. **Say once** that the tax-vs-WSS ratio peaks near 100% of LLC and declines
   beyond it, so the two shapes read as one story.
