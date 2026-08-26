# M7 pre-registration: price the surviving claim across hit rate

Written 2026-08-26, **before any M7 data exists**. Registered before the runner
is written.

## Why this, now

M6 killed the neighbour-protection claim on Intel (`M6_OUTCOME_2026-08-26.md`).
What survives is claim (b) from `CLAIM_REWRITE_2026-08-26.md`: a context-scoped
mask cannot let one thread keep its own reused structure resident while denying
residency to its own stream. That claim's *expressibility* is settled by the
taxonomy. Its *magnitude* is not, and the two measurements we have disagree by a
factor of six:

| restriction on the fused class | hit rate | hot-table penalty |
|---|--:|--:|
| `tab:fused`, 4 of 20 ways | 0.5 | **+43%** |
| M6 pass A, 2 of 20 ways, 256 MiB | 1.0 | **+7.5%** |

The tighter mask at the higher hit rate hurt six times less. Hit rate has now
silently set three headlines in this benchmark (it withdrew the 1.47x fused tax,
it withdrew the split's negative recovery, and it is the stated caveat on
`tab:fused`). It has never been swept.

This also decides the panel's next queued item. The e2e (`host_block_gather`,
`~/STREAMING_Paper/e2e_design.md`, 5--8 engineer-days) exists to produce a
*second instance of claim (b)* in a gather shape. Whether that is worth five to
eight days depends entirely on how big claim (b) is at a hit rate a real join
would run at. So M7 gates the e2e go/no-go, and the gate is registered below
rather than decided after seeing the numbers.

## Design

Reproduce `tab:fused`'s decisive pair exactly and vary **only** `--hit-rate`.

- Arm `none` = the panel's `A3_16`: `--mode morsel --policy wb --fact-node 2
  --hot-node 0 --fact-bytes 1g --hot-bytes 177838489 --cpu-list 32-47
  --morsel 1m --warmups 2 --reps 1 --threads 16`, resctrl torn down.
- Arm `b4` = the panel's `B16`: identical, with `resctrl_clos.sh setup_b 4 32-47`
  (4 of 20 ways to the fused class, CPU-based CLOS).
- Hit rate in {0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0}. 14 cells.
- n=15 per cell. **Cells are interleaved within each rep and the cell list is
  rotated by rep index**, so no arm occupies a fixed position in wall-clock
  order. This is the F10 discipline; CAT is reconfigured per run rather than
  batched, precisely to avoid the all-none-then-all-narrow ordering.
- Metric per run: `active_cycles_per_access` (hot-table cost) and
  `join_mtuples_per_s`. The reported quantity is the **within-hit-rate ratio**
  median(b4)/median(none). Absolute cyc/access is *not* comparable across hit
  rates by construction --- a missing probe walks a linear-probe chain --- and no
  cross-hit-rate absolute comparison will be made.
- The L3 schemata string is captured into every record.
- One host: mos181 (EMR 8592+, 20 ways x 16 MiB). No victim process; this
  experiment is about the tenant's own two axes only.

## Instrument check (registered, action on miss stated)

`tab:fused` reports the unrestricted fused arm at 336.6 Mtuple/s and 88.5
cyc/access at hit rate 0.5. The `none`/0.5 cell must land within +/-5% of 88.5,
i.e. **[84.08, 92.93]** cyc/access.

- **On miss:** the run is not silently reported. Arm identity is stated as
  broken, and `tab:fused`'s provenance status is escalated from *declared gap*
  (F1: raw data not in git, way-sweep runner absent) to *defect*, because the
  published cells would then not be reproducible from any surviving runner.

## Registered predictions

- **P1.** The ratio median(b4)/median(none) on cyc/access is **monotone
  non-increasing in hit rate** over the seven points (allowing 0.02 of noise per
  step).
- **P2.** At hit rate 0.5 the ratio reproduces `tab:fused`'s **1.434x within
  +/-0.05**, i.e. in [1.384, 1.484]. This is the positive control on arm
  identity, independent of the instrument check above.
- **P3.** At hit rate 1.0 the ratio is **<= 1.10**, consistent with M6's +7.5% at
  a tighter mask.
- **P4.** At hit rate 0.0 the ratio is the **largest** of the seven.

P1 and P4 are the ones I expect to be told I got wrong: it is equally plausible
that a 100%-miss probe is so memory-bound that the mask stops mattering, which
would make the ratio non-monotone with a peak in the middle.

## Registered gate on the e2e

Let R(hr) be the cyc/access ratio.

- **If the instrument check or P2 fails** --- void. No e2e decision is drawn from
  a run whose arm identity is not established.
- **If R(0.75) and R(0.9) are both <= 1.10** --- claim (b)'s magnitude is
  miss-driven. **e2e = NO-GO.** Five to eight engineer-days would buy a second
  instance of an effect worth under ten percent, while the experiment that
  actually decides the paper (the narrow-aggressor cell on the 9754) is blocked
  on a host. In that case `tab:fused` must additionally be re-anchored: either
  the paper leads on a realistic hit rate, or it argues explicitly why 0.5 is the
  realistic one, and it may not present the 1.43x as the headline of the fused
  case.
- **If R(0.75) or R(0.9) is >= 1.25** --- claim (b) is robust across the regime a
  real join occupies. **e2e = GO**, queued behind the AMD cell, and `tab:fused`'s
  caveat softens to a scope note rather than a headline correction.
- **If both land in (1.10, 1.25)** --- **e2e = DEFER**, and the paper states the
  fused penalty as a range over hit rate rather than a single figure. No further
  experiment is run to break the tie; that would be reading the tea leaves.

## What this cannot show

Intel EMR only. One mask width (4 of 20) and one table size (169.6 MiB), because
the point is to reproduce `tab:fused` and move one knob. A hit-rate sweep at a
second mask width would be a better experiment and is not what is registered
here. Nothing here bears on the neighbour question --- M6 settled that --- or on
AMD, where the deciding cell remains unrun and the host unreachable for four
days.
