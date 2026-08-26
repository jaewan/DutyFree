# M8 pre-registration: is `tab:fused`'s 1.43x a label-scope effect or a mask-capacity cliff?

Written 2026-08-26 after M7 completed and **before any M8 data exists**.

## What M7 found, and the question it raises

M7 (`M7_HITRATE_PREREG_2026-08-26.md`, runner `d9425d7`, n=15, instrument check
passed) swept probe hit rate against `tab:fused`'s decisive pair. All four
registered predictions failed:

| hit rate | none | b4 (4/20) | R |
|--:|--:|--:|--:|
| 0.0 | 84.71 | 97.79 | 1.155 |
| 0.1 | 85.24 | 103.61 | 1.216 |
| 0.25 | 89.89 | 124.36 | 1.383 |
| 0.5 | 89.33 | 123.15 | **1.379** |
| 0.75 | 64.48 | 80.47 | 1.248 |
| 0.9 | 52.61 | 77.02 | 1.464 |
| 1.0 | 44.62 | 65.37 | **1.465** |

The penalty **does not collapse at high hit rate** --- it is largest there. So the
caveat I wrote into `tab:fused`'s caption and the co-author cover note this
morning ("the +19--44% penalty is specific to the 50% hit rate; the same class of
restriction costs 7.5% at 100%") is **contradicted by a direct sweep of exactly
that variable** and has to come out. M6 pass A's +7.5% is now the anomaly, not
the rule.

But the shape of M7 raises a worse possibility, and it is about the paper's
strongest experiment rather than about a caveat.

**mos181's LLC is 20 ways x 16 MiB = 320 MiB. `tab:fused`'s hot table is
`HOT_BYTES=177838489` = 169.6 MiB. Four of twenty ways is 64 MiB.** So the
`b4` arm does not merely restrict the fused class --- it moves the hot table from
a mask it fits inside (320 MiB) to one it **cannot** fit inside (64 MiB). A
single-class workload with a 169.6 MiB working set would suffer from a 64 MiB
mask with no stream present at all.

If that is the mechanism, then `tab:fused`'s 1.43x is a **property of the table
size we happened to choose**, not evidence about label scope, and §3's central
argument --- "any mask narrow enough to constrain the stream constrains the reused
structure with it" --- is being carried by a number that would appear without a
stream.

The paper's claim can still be true. It is the *evidence* that would be
disqualified. This is the F9 family again (a quantization/geometry artifact
setting a headline), and it is worth finding out ourselves.

## Design

Hold everything at `tab:fused`'s arm and sweep **table size** across the 4-way
capacity boundary.

- Arms: `none` (resctrl torn down, 20 ways) and `b4`
  (`resctrl_clos.sh setup_b 4 32-47`, verified `L3:0=f` in domain 0, domain 1
  full). These are exactly the arms M7 used and `tab:fused`'s `A3_16`/`B16`.
- Fixed: `--mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g
  --cpu-list 32-47 --morsel 1m --warmups 2 --reps 1 --threads 16`.
- `--hot-bytes` in {4194304 (4 MiB), 16777216 (16), 33554432 (32), 67108864 (64),
  134217728 (128), 177838489 (**169.6 --- `tab:fused`'s value**), 268435456 (256)}.
- `--hit-rate` in {0.5, 1.0} --- the published operating point and the one where
  M7 found the penalty largest.
- **The 4-way mask holds 64 MiB.** Tables at 4/16/32 MiB fit with room; 64 MiB is
  exactly at the boundary; 128/169.6/256 MiB cannot fit.
- n=8 per cell, 28 cells, 224 runs. Cells interleaved with a per-rep rotation, CAT
  reconfigured only on arm change, schemata captured per record, per-record JSON
  validation, refuses to append (A6.19).

## Instrument check (registered, action on miss stated)

The cell `none` / 169.6 MiB / hit-rate 0.5 is `tab:fused`'s unrestricted fused
arm and M7's `none`/0.5 cell. It must land within +/-5% of M7's 89.326
cyc/access, i.e. **[84.86, 93.79]**.

- **On miss:** M8 is reported as void for cross-experiment comparison. The
  within-M8 table sweep may still be reported, since it is internally
  controlled, but no M8 number may be compared to `tab:fused` or M7.

## Registered predictions

- **P1 (capacity-cliff hypothesis).** R = median(b4)/median(none) on cyc/access
  is **<= 1.10 for every table of 32 MiB or less**, and **>= 1.30 for 169.6 MiB**,
  at both hit rates. If this holds, `tab:fused`'s headline is a table-fit
  artifact.
- **P2 (stream-interference hypothesis).** R is **flat in table size** ---
  max(R)/min(R) <= 1.15 across the seven sizes at fixed hit rate. If this holds,
  the restriction penalty is not about whether the table fits the mask, and
  `tab:fused`'s evidence stands as published.
- **P3.** R at 169.6 MiB / hit-rate 0.5 reproduces M7's 1.379 within +/-5%
  (i.e. [1.310, 1.448]). This is the arm-identity control; note that I set M7's
  equivalent window at +/-0.05 absolute, which was tighter than the +/-5% I
  allowed the instrument check, and M7's P2 then failed by 0.005. **That
  inconsistency was my error, not the data's**; +/-5% is used here for both.
- **P4.** The 64 MiB cell (exactly at the mask boundary) gives an R **between**
  the 32 MiB and 128 MiB cells at both hit rates.

P1 and P2 are mutually exclusive and both may fail; that outcome is informative
and will be reported as such rather than forced into one of them.

## Registered consequences

- **P1 holds** --- `tab:fused`'s 1.43x is disqualified as evidence for label
  scope. §3's fused argument must be rebuilt on a table that fits inside the
  restricted mask, where any surviving penalty is attributable to the stream.
  Sec1 contribution (2), rewritten this morning, must be narrowed again: the
  monotone way sweep would then be a statement about table geometry.
- **P2 holds** --- the published evidence stands, the hit-rate caveat is removed
  as wrong rather than softened, and the e2e gate (M7, registered GO on
  direction) is re-drawn cleanly.
- **Neither holds** (R varies with table size but not as a clean cliff) ---
  `tab:fused` must report the table size as a stated scope condition and the
  paper may not present 1.43x as the fused penalty without it.

## What this cannot show

Intel EMR only, one mask width, one fact size, no victim. It does not revisit
M6's neighbour result, which stands. It also does not by itself explain M6 pass
A's +7.5% at a *narrower* (2-way) mask; that reconciliation needs M6's own fact
size (256 MiB) and `setup_c`, and is deliberately not folded in here so that M8
moves exactly one variable.
