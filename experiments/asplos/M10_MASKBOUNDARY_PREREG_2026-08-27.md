# M10 pre-registration: is the boundary the *mask*, or the private L2?

Written 2026-08-27 during a red-team review of M6--M9, **before any M10 data
exists**.

## The defect this addresses

M8/M9 concluded that `tab:fused`'s restriction penalty is a capacity effect, and
§3 now asserts the mechanism in the paper: *"a four-way mask holds 64 MiB on this
part and the instantiated reused table is 256 MiB, so the restricted arm moves
the table from a mask it fits into one it cannot."*

**That mechanism is not established by M8.** M8 varied table size at a **single**
mask width. Its control cells (4, 16, 32 MiB, all R ~1.00--1.04) are equally
explained by a second boundary that M8 never varied:

> 16 fused cores x 2 MiB private L2 = **32 MiB of aggregate private L2**.

A table of 32 MiB or less can live largely in private L2 and never depend on L3
allocation at all, so R ~ 1.0 there is explained by "never reaches the L3" just
as well as by "fits inside the mask." The 64 MiB cell (R = 1.22 at hr 0.5) sits
between the two candidate boundaries and cannot separate them either.

This is **standing rule S5.2** --- check the hot set against the private L2 before
believing a null --- applied to our own conclusion. The rule exists because we
have violated it before; M6b's runner comment records the last time.

## Design

Sweep the **mask width** as well as the table. If the boundary is the mask, the
knee moves with the mask. If it is private L2, the knee stays at ~32 MiB for
every mask.

- Fixed: `--mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g
  --cpu-list 32-47 --morsel 1m --warmups 2 --reps 1 --threads 16
  --hit-rate 0.5`.
- `--hit-rate 0.5` **only**. It is `tab:fused`'s published operating point, and
  M8's accidental duplicate cell showed its R estimates reproduce to 0.4% at n=8
  while hr 1.0 reproduced only to 17.5%. Spending the budget where the
  instrument is precise is the point.
- Masks: `none` (20 ways, 320 MiB), `b2` (2 ways, **32 MiB**), `b4` (4 ways,
  **64 MiB**), `b8` (8 ways, **128 MiB**).
- Tables, all exact powers of two so nothing is silently rounded (the F9 trap
  that produced M8's duplicate): 16777216 (16 MiB), 33554432 (32), 67108864
  (64), 134217728 (128), 268435456 (256).
- n=6. 20 cells, 120 runs. Interleaved with a per-rep rotation, mask
  reconfigured only on arm change, L3 schemata captured per record, per-record
  JSON validation, A6.19 refusal to append, resctrl torn down on every exit path.
- **Every table size is a power of two times 16 B**, so `HOT_TABLE_ROUNDED`
  must never fire. The runner asserts this by capturing the instantiated size
  from stderr into each record --- a gap in M7/M8/M9, which discarded stderr and
  therefore could not have caught the rounding from their own data.

## Instrument check (registered, action on miss stated)

The cell `none`/256 MiB is `tab:fused`'s unrestricted fused arm and M8's own
256 MiB cell. It must land within **+/-5% of M8's 90.558 cyc/access, i.e.
[86.03, 95.09]**.

- **On miss:** M10 is void for comparison against `tab:fused`, M7 or M8; the
  within-M10 mask x table matrix may still be reported as internally controlled.

## Registered predictions

Define the **knee** as the smallest swept table at which R = median(masked)/
median(`none`) first exceeds 1.15.

- **P1 (mask-capacity).** The knee tracks the mask: `b2` knees at <= 32 MiB,
  `b4` at 64 MiB, `b8` at 128 MiB. Equivalently R is approximately a function of
  table/mask, and R(table = mask) is similar across the three masks.
- **P2 (private-L2).** The knee is at 32--64 MiB for **all three** masks, i.e.
  R(64 MiB) > 1.15 under `b8` as well as under `b2`, and the three curves lie on
  top of each other in absolute table size rather than in table/mask.
- **P3.** R(16 MiB) <= 1.10 under **all three** masks. 16 MiB is inside
  aggregate private L2 and inside every mask, so nothing should move it. This is
  the apparatus control; if it fails, something other than capacity is acting and
  P1/P2 are both unreadable.
- **P4.** Under `b8` (128 MiB mask), R(256 MiB) >= 1.15 --- a table twice its mask
  is still penalised, so the effect is not confined to the one width we
  happened to test.

P1 and P2 are mutually exclusive. A mixed outcome (the knee moves, but less than
proportionally to the mask) is likely if **both** boundaries act, and will be
reported as such with both sized, not resolved to whichever is tidier.

## Registered consequences

- **P1 holds** --- §3's mask-capacity sentence is supported and stays as written,
  with M10 cited for the mechanism rather than M8 alone.
- **P2 holds** --- §3's mechanism sentence is **wrong** and must be replaced. The
  finding would become "the penalty appears once the reused structure exceeds
  aggregate private L2, whatever the mask," which is a statement about the
  cache hierarchy and not about masks or labels at all. M8's and M9's *headline*
  (the penalty is capacity, not stream) survives either way; only the named
  mechanism changes.
- **Mixed** --- §3 states both boundaries and attributes neither exclusively.

## What this cannot show

Intel EMR only, one benchmark, one fact size, one hit rate, no victim. It does
not revisit M6's neighbour result, M9's stream control, or anything on AMD. It
tests one mechanism sentence that I put into the paper yesterday on evidence that
does not support it.
