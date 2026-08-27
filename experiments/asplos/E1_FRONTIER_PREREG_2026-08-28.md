# E1 pre-registration: the allocation frontier. Is there a static split that satisfies both parties?

Written 2026-08-28, **before any E1 data exists**. Per `AGENDA_2026-08-28.md` this
is the one outstanding item that can invalidate the paper's central claim, so it
runs first and its collapse condition is written down before its supporting one.

## Why

M12 measured the label-versus-partitioning trade-off at **one** way split (tenant
8 of 20, victim 12), one victim working set (170 MB), one tenant table (128 MiB).
Three of the resulting numbers are now in the abstract. The obvious reviewer
question --- *what happens at a different split?* --- is unanswerable from one point.

The underlying quantity is a **fixed capacity budget**: 20 ways x 16 MiB =
320 MiB, shared. The tenant's 128 MiB table needs >= 8 ways to fit at all; the
victim's ~162 MiB needs >= 11. Those sum to 19 of 20, leaving essentially no
headroom for either --- and M12 found both parties paying anyway (16.7% and 13.1%)
at exactly the split where both nominally fit. **Fitting is evidently not
sufficient.** The frontier is what settles whether that is a general property of
the budget or an artifact of the one split we happened to pick.

## Design

Two passes. mos181. Tenant = `cxl_join_bench --mode morsel`, 16 threads on
cpus 32-47, table **134217728 (128 MiB, exact power of two)**, fact 1 GiB on CXL
node 2, `--hit-rate 0.5`, `--reps 20`. Victim = `pointer_chase` on cpu 8, node 0.
Split $k$ means the tenant gets $k$ of 20 ways and the victim the complementary
$20-k$, enforced with `setup_c $k$ 32-47 8`.

- **Splits** $k \in \{2, 4, 8, 12, 16\}$.
- **Victim WSS** $\in \{32, 96, 170\}$ MB. The third is M12's; the first two test
  whether the victim's confinement cost is a **tight-fit** phenomenon --- 170 MB in
  12 ways is 84% full, and M8's lesson was that exactly this kind of tight fit
  produced an entire effect we had attributed to something else.

### Pass A --- the tenant's cost as a function of its own mask ($n{=}10$)

No victim. `mask` $\in \{$none, $k{=}2,4,8,12,16\}$. 6 cells, 60 runs, ~6 min.
Measured alone rather than co-running, as in M12 pass A, so the number is the
tenant's own confinement cost and not a co-run composite.

### Pass B --- the victim, all three quantities ($n{=}6$)

| cell family | mask | tenant | count |
|---|---|---|--:|
| victim unconfined baseline | none | absent | 3 (one per WSS) |
| **victim's own confinement cost** | split $k$ | **absent** | 15 |
| victim + tenant, stream retained | split $k$ | present | 15 |
| victim + tenant, stream non-allocating | split $k$ | present | 15 |
| | | | **48 cells, 288 runs** |

The second family is the control M12's P5 proved indispensable: without it, the
victim's slowdown conflates the tenant's interference with the victim's own loss
of ways, and P4 in M12 "failed" purely because I had used the wrong denominator.

Interleaved with a per-rep rotation; schemata captured per record; tenant liveness
(`alive_at_end`, `HOT_TABLE_WARMED`) asserted in every co-run record; aborts if the
table is silently rounded; A6.19; resctrl torn down on every exit path.
Estimated ~55 min for pass B.

## Variance basis and the sample sizes it implies

Stated because five thresholds this week were set finer than their instrument
resolves, and the red-team review made this mandatory.

| quantity | measured CoV | $n$ | two-sample resolution ($\alpha$ .05, power .80) |
|---|---|--:|---|
| victim cyc/load (M12 pass B, 6 arms) | 0.03--0.66% | **6** | **~1.1%** |
| tenant cyc/access at hit rate 0.5 (M10/M10b/M12a, 32+ cells) | median 0.3%, worst 3.7% | **10** | **~4.7%** |

**Every threshold below is at least 3x the relevant resolution.** No threshold is
set at a round number near an expected effect.

## Instrument check (registered, action on miss stated)

Victim unconfined at WSS 170 MB must land within **+/-3%** of M12 pass B's
`Vnone` median of 78.058 cyc/load, i.e. **[75.72, 80.40]**.

- **On miss:** E1 is void for comparison against M12; the within-E1 frontier may
  still be reported as internally controlled.

## Registered predictions

Define, at split $k$ and victim WSS $w$:
$C_V(k,w)$ = the victim's own confinement cost (family 2 against family 1);
$C_T(k)$ = the tenant's cost (pass A against its `none` cell);
$H(k,w)$ = the victim's harm while the tenant runs, measured **against family 2**.

"Cheap for both" is defined as $C_V \le 5\%$ **and** $C_T \le 10\%$ --- both
comfortably above resolution.

- **P1 (no free split --- the claim-supporting outcome).** At $w = 170$ MB there is
  **no** split $k$ that is cheap for both **while also** protecting the victim
  ($H \le 1.05$).
- **P2 (the collapse --- registered first as the outcome that would kill the
  claim).** Some split at $w = 170$ MB is cheap for both and protects the victim.
- **P3 (the confinement cost is a tight-fit effect).** $C_V \le 3\%$ wherever the
  victim's WSS is $\le 50\%$ of its partition's capacity, and $\ge 8\%$ wherever it
  is $\ge 80\%$.
- **P4 (consistency with M12).** At $k = 8$, $w = 170$: $C_T$ within +/-5 points
  of M12's 16.7%, and $C_V$ within +/-4 points of its 13.1%.
- **P5 (apparatus monotonicity).** With the stream retained, $H$ is
  non-increasing as the victim gains ways. If this fails, the frontier is not
  readable and P1/P2 are both void.

P1 and P2 are exhaustive and mutually exclusive: one of them will fire.

## Registered consequences

- **P1 holds** --- the claim is **stronger** than the paper currently states, and
  becomes: *no static partition of a shared cache satisfies a streaming tenant and
  its neighbour simultaneously, because their capacity demands sum to more than
  the cache; an object label removes one demand without partitioning at all.* The
  frontier becomes the paper's central figure and §5 is built on it.
- **P2 holds** --- **the trade-off claim collapses.** A well-chosen mask satisfies
  both parties, and the paper must say so. The label's case then rests on the
  three legs that do not depend on it: no calibration (MBA's knife edge), the
  fused tenant's inexpressibility, and H3. The abstract's two-sided pricing must
  be withdrawn.
- **P3 holds** --- the 13.1% is **conditional**, and the abstract must say "when
  the neighbour's own working set is a large fraction of its partition" rather
  than stating it flatly.
- **P3 fails** (cost persists at loose fit) --- associativity loss under way
  partitioning is **unconditional**, which is more surprising than the
  conditional version and deserves its own emphasis.
- **P4 fails** --- M12 and E1 disagree at their shared point; both are quarantined
  for cross-comparison until reconciled, exactly as M6/M8 were.
- **P5 fails** --- frontier void, investigate the apparatus before anything else.

## What this cannot show

Intel EMR only; one tenant benchmark; one victim type (a latency-bound pointer
chase, i.e. the most sensitive neighbour that exists); one tenant table size; one
stream size; one hit rate. It prices **static** partitions only --- a dynamically
reconfigured mask is a different mechanism and is not tested. And the label is
still the flush-behind software proxy, so the "$\sim$0 to the tenant" column
remains an idealisation the proxy cannot demonstrate (M12 pass A).
