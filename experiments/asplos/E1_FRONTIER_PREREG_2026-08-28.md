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

---

# Amendment 1, 2026-08-28: pass A's tenant-cost column is void, and the redesign

Written after E2 completed and **before any pass A2 data exists**.

## What happened

E1's P4 fired --- E1a read the tenant at +8.7% where M12a read +16.7% --- and I
attributed it to the resctrl helper. E2 tested that and a second candidate I had
missed (M12a's occupancy sampler polling inside its own measured window). **Both
candidates are refuted**, at n=40 with a passing instrument check:

| helper | sampler | tenant's cost |
|---|---|--:|
| `setup_b` | off | +17.1% |
| `setup_b` | on | +16.7% |
| `setup_c` | off | **+17.1%** |
| `setup_c` | on | +16.8% |

All four agree. The sampler is worth −0.4 points and the helper +0.0 points, both
inside the registered 4-point band, so **P1 and P2 are unresolved, not failed**,
and P4 (no-mask sampler effect +0.1) holds. A fresh interleaved measurement taken
immediately afterwards, n=10 each arm, reads **none 78.138 / 8-way 91.397 =
+17.0%**, CoV 0.19% and 0.20%.

So **+17.0% is the correct value, established three independent ways, and E1a's
+8.7% is the outlier.**

## Why E1a was wrong, as far as I can establish it

E1a's `b8` samples are **bimodal**: 84.929, 85.091, **91.580**, 84.863,
**91.724**, 84.982, 84.992, 84.831, 84.845, 85.151. Eight of ten sit in a fast
mode that does not reproduce; the two slow ones are correct.

Hypotheses tested and rejected:

- **the group's mask was wrong** --- no. E1a captured `schemata` in every record and
  they are correct at every width (`b8` -> tenant `L3:0=ff`, victim `L3:0=fff00`).
- **the tenant's CPUs were not associated with the group** --- would produce an
  intermediate value, which fits, but `setup_c 8 32-47 8` writes `cpus_list =
  32-47` correctly on three consecutive standalone attempts.
- **the preceding arm leaked** --- `b8` was preceded by `b4` in all six reps, fast
  and slow alike, so the predecessor does not separate them.
- **thermal drift across the session** --- no. The unmasked baseline is stable
  everywhere: 78.178 (E1a), 78.131 (E2), 78.138 (fresh). Only E1a's *masked* arm
  moved.

**I do not have the mechanism.** This is the same situation the paper already
discloses for `tab:amdcat`'s CAT arm --- enforcement verifiable, cause
unidentified --- and it gets the same treatment: reported, not explained away.

## Consequences, applied

- **E1 pass A's entire $C_T$ column is void.** Every tenant-cost number in
  `E1_OUTCOME_2026-08-28.md` (+32.7 / +24.7 / +8.7 / +1.3 / +0.0%) is withdrawn,
  and so is the free-split condition derived from it.
- **Pass B is unaffected.** It used a different runner, and its $C_V = 13.1\%$ at
  $k{=}8$ reproduces M12's 13.1% exactly. The victim-side frontier, the
  occupancy curve, and $H \approx 0.99$ at every split all stand.
- **P1's conclusion survives and is strengthened, but must be re-derived.** At the
  corrected +17.0%, the tenant is *not* cheap at 8 ways either, so the cheap
  regions are further apart than E1 reported, not closer.
- The tenant-cost figures already in the paper (§5's 16.7%, the abstract's
  17--41%) are **no longer under suspicion**: E2 vindicates them. The
  quarantine E1 imposed on them is lifted.

## Pass A2 design --- built so that drift of any cause cannot survive it

The defect's cause is unknown, so the redesign removes the class of error rather
than the hypothesised mechanism: **every masked measurement is paired with an
unmasked one taken immediately beside it**, and the reported quantity is the
**median of per-pair ratios**, not a ratio of campaign-wide medians. Whatever made
E1a's masked arm drift, a ratio computed from adjacent runs cannot inherit it
unless the drift is instantaneous and mask-selective.

- Arms: for each width $w \in \{2,4,8,12,16\}$, a pair (`none`, $w$) run
  back-to-back, order alternating between reps.
- $n{=}10$ pairs per width. 100 runs, ~11 min.
- **`cpus_list` captured per record alongside `schemata`**, and the runner aborts
  if the tenant's CPU list is not exactly `32-47` --- closing the gap that made the
  defect invisible even though the data was being recorded.
- Registered check: the per-pair ratio at $w{=}8$ must be within **+/-3%** of
  1.1697 (the fresh interleaved measurement). On miss, pass A2 is void and the
  tenant axis is quoted from E2's single point only.
- Registered expectation, stated so bimodality cannot hide again: **per-pair
  ratio CoV at each width must be under 3%**; if any width exceeds it, that
  width's samples are printed individually in the outcome rather than summarised.
