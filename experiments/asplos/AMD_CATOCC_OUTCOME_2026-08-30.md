# A way mask **restores** the victim's L3 residency and it is **still 9.2x slower**. The AMD residual is not eviction.

Pre-registration `AMD_CATOCC_PREREG_2026-08-30.md` (`9eda41d`). 120 runs, all 120
passing the by-value mask check. Machine verified idle before launch.

## The result (victim 4096 KB; quiescent 55.34 cyc/access, 3292 KB resident in L3)

| arm | aggressor ways | slowdown | **victim L3 occupancy** | **% of quiescent** | victim L2 hit% | agg GB/s |
|---|--:|--:|--:|--:|--:|--:|
| `wb` | 16 (unmasked) | 27.61x | 180 KB | **5.5%** | 0.00 | 24.78 |
| `cat8` | 8 | 12.37x | 2820 KB | **85.7%** | 1.13 | 24.82 |
| `cat4` | 4 | 9.20x | 2920 KB | **88.7%** | 12.33 | 24.63 |
| `cat1` | **1** | **9.24x** | **3008 KB** | **91.4%** | 11.58 | 24.66 |
| `other`-CCX | 16 | 1.30x | (void, see below) | --- | 0.00 | 24.79 |

## P1 --- the mask restores residency; the residual is something else

Registered: `>= 70%` means the mask restores residency and the surviving residual
is **not** eviction; `<= 30%` would have meant the mask does not protect
residency at all.

**Measured 91.4%.** Not near the boundary, and monotone in the right direction
(85.7% -> 88.7% -> 91.4% as the mask tightens from 8 ways to 1).

> **A way mask gives the victim back 91% of its L3 residency, and the victim is
> still 9.2x slower than quiescent.** Whatever the AMD residual is, it is not the
> victim being evicted from the shared cache.

This resolves the contradiction that motivated the experiment. `AMD_L3OCC`
found the *unmasked* harm is eviction (occupancy 5.5%); `AMD_NARROWMASK` found
narrowing the mask from 8 ways to 1 barely moves the residual. Both are true, and
they are not in tension: **the mask fixes the eviction, and the eviction was
never the whole harm.** The plateau below four ways is exactly what should happen
once a capacity mechanism has recovered all the capacity there is to recover.

The L2 hit rate tells the same story from the other side: 0.00% unmasked,
restored to 11.6--12.3% under `cat4`/`cat1` against a 15.0% quiescent baseline.
Residency comes back at both levels; performance does not.

**What the paper may now say**, which is sharper than the current text and
forecloses the obvious objection:

> On EPYC 9754 a way mask **does** restore the neighbour's cache residency ---
> 91% of its quiescent L3 occupancy even when the streamer is confined to a
> single way --- and the neighbour is still **9.2x** slower. The residual is on
> the fill path, not in shared capacity, which is why no mask width reaches it.

## P2 --- the L3-locality claim reproduces and may be written down

`other`-CCX = **1.30x**, against a registered confirmation band of 1.0--2.0x and
the factorial's 1.31x. Aggressor bandwidth is matched (24.79 vs 24.78).

The `AMD_L3OCC` run's outlying 618.7x in this cell is now the odd one out, two
runs to one. **`BERGAMO_BACKINVAL`'s P2 is no longer provisional.**

## An instrument failure caught by an enforced assertion --- and one that was not

**First attempt (`cat_occ.jsonl`, discarded).** Occupancy read **exactly 0.0 KB
in every CAT arm**. That resembles the registered `<= 30%` branch and would have
supported the dramatic conclusion that a mask does not protect residency at all.

It was an artifact. Verified on the machine: **a CPU placed in a CTRL_MON group
takes that group's RMID**, so a monitoring group under root reads zero for it ---
root read `0` while the CTRL_MON group's own `mon_data` read `1,376,256` B.
Applying a mask silently moved the victim out from under the monitor. Fixed by
reading occupancy from whichever group owns cpu0.

**A second, narrower instance survives in this run and is voided rather than
reported.** A `mon_group` **permanently loses** a CPU once a CTRL_MON group
claims it --- confirmed directly: `[0]` -> `[]` -> `[]` after the CTRL_MON group
is removed. So every occupancy reading taken *after* the first CAT arm is
invalid:

- **valid:** `quiescent` and `wb` at 4096 KB (before any CAT group existed) and
  all three CAT arms (read from the CTRL_MON group).
- **void:** the `other` arm's occupancy, and **every occupancy reading in the
  512 KB block**, which ran after the CAT arms.

The 512 KB block's *timing* data is unaffected and consistent with earlier runs;
only its occupancy is discarded. **P1 rests entirely on readings from the valid
set.**

### The process failure worth recording

Liveness assertion 2 --- *"`llc_occupancy` must vary across arms; a constant
reading voids the run rather than becoming a finding"* --- was written into the
pre-registration and **not implemented in the first analysis**. It was
constant-zero across four arms and I printed it as data. In the second analysis
the check is executed, and it did its job: it voided the 512 KB occupancy block
automatically.

**Writing an assertion is not the same as enforcing one.** Three checkers failed
today; this is the only one that was already correctly specified and simply not
run.
