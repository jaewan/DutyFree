# `tab:h3sf` re-measured at a documented geometry — H3's separation holds, with intervals

Written 2026-08-20. TODO item 6. **Not** an attempt to reconcile the old
numbers: §6.6 forbids hunting for the geometry that reproduces them. All rows
were re-measured at one documented setting and the table is replaced.

## Config, stated once and applied to every row

`HNF_SF_FINITE=1 HNF_SF_SETS=4096 HNF_SF_WAYS=16` (65,536 entries — the
canonical proposal's documented geometry), `HNF_DMT=0`, victim = 2650 KiB
pointer chase (53% of the 5 MiB LLC), aggressor = 16 MiB CXL stream,
`iters=3e6`, gem5 `0f37c28`. Three randomisation seeds per row. Verified from
`config.json`: `sf_finite`, entry count, `enable_H3_streaming_bypass` and
`enable_DMT` on every arm.

**A confound caught during setup.** The first launch failed with
`AssertionError: finite SF (HNF_SF_FINITE=1) requires DMT off (HNF_DMT=0)`. All
twelve finite-SF runs died; the six infinite-SF runs started normally. Had I
relaunched only the failures, the table would have compared finite-SF rows at
DMT-off against infinite-SF rows at DMT-on — the same defect as the original
`tab:h3sf`, rows sharing a table without sharing a config. Everything was
relaunched with `HNF_DMT=0`.

## Results

| row | victim cyc/access | tax | victim L1 `SnpCleanInvalid` |
|---|---:|---:|---:|
| victim alone, infinite SF | 33.88 ± 0.01 | 1.000x | 2 |
| victim alone, finite SF | 33.88 ± 0.01 | 1.000x | 2 |
| WB aggressor, infinite SF (capacity only) | 46.38 ± 0.04 | 1.369x | 1 |
| WB aggressor, finite SF | 84.75 ± 0.07 | **2.501x** | 36,800 |
| H2 (LLC-data bypass), finite SF | 85.10 ± 0.02 | **2.512x** | 37,109 |
| H2+H3 (also skips SF enrolment), finite SF | 35.95 ± 0.01 | **1.061x** | **25** |

Interval is the half-range over three randomisation seeds.

## What it establishes

**The control holds.** Victim alone is *identical* at infinite and finite SF
(33.88 both, ±0.01), so 65,536 entries is the knee for this victim and the
filter costs the victim nothing on its own. The original caption asserted this;
it is now measured.

**The two charges separate cleanly.** Capacity alone costs 1.369x. Making the
filter finite takes it to 2.501x — the back-invalidation charge is the larger
of the two. H2 pays down capacity and leaves that charge exactly where
write-back left it (2.512x against 2.501x, indistinguishable at ±0.07). Only
H3 removes it (1.061x).

**The mechanism is visible in the snoops.** Back-invalidations reaching the
victim's L1 are 36,800 and 37,109 without H3 and **25** with it, against 2 for
the victim alone. H2's streaming lines still enrol and still back-invalidate;
H3's do not.

So the claim `tab:h3sf` is cited for — *neither way partitioning nor H2 can
provide this* — is reproduced at a documented geometry, with intervals, on
every row.

## What reproduced, and what did not

**The taxes reproduce the published values closely.** Measured 2.501x / 2.512x
against published 2.53x / 2.55x — within 1.5%. The earlier re-instantiation's
"+18% high" (2.98x / 3.02x) does **not** appear here. So that discrepancy was
most likely a configuration difference in that attempt rather than an unknown
SF geometry. I am not going to reconstruct which difference; the point is that a
documented config reproduces the ordering *and* the magnitudes.

**The back-invalidation counts do not reproduce**: 37,109 against the published
3,683, a 10x gap. Those counts are **superseded, not reconciled**. No
speculation offered about the original's counting window.

## A stat that must not be trusted

`system.ruby.hnf.cntrl.sf.m_demand_accesses` and `..._misses` read **zero on
every row**, including rows where the filter is demonstrably thrashing 37k
back-invalidations. They are not wired through the SLICC path. The evidence that
the filter is finite and evicting is the `SnpCleanInvalid` count at the victim's
L1 — which is also exactly what the caption claims. This is another instance of
§6.1: the stat whose name fits is not necessarily the stat that is counting.

## Consequence for the paper

`tab:h3sf` can drop its "the two middle rows are indicative rather than settled"
caveat, because every row is now re-measured at one documented geometry with an
interval. `Sec5`'s body sentence "The two middle magnitudes are indicative; the
claim is the ordering" — added by me two days ago — can be removed for the same
reason. H3's quantitative support moves from one caveated table to a clean
measurement.
