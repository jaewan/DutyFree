# Outcome: silicon hash-join e2e (application units)

Date: 2026-09-01.  Judged against `SILICON_E2E_PREREGISTRATION_2026-09-01.md`.
Host mos182 (`c4`), Xeon Platinum 8462Y+, socket 0, L3 60 MiB / 15 ways.
**STREAMING is not measured.**  105/105 records `status=ok`.

Registered campaign: 8 GiB fact + 32 MiB table, `--huge2m`, `--hit-rate 1.0`,
tenant cpu 4 / victim cpu 6, CAT via `setup_b` (tenant confined, victim in
root CLOS with the full mask).  Data:
`experiments/asplos/data/silicon_e2e_hashjoin.jsonl`.  Binaries
`join=75e0af947243` `victim=026e357ae21a`.

Analyzer: `experiments/asplos/analyze_silicon_e2e.py`.  S2's implementation
was tightened after the 4K sensitivity (below) produced a false PASS from a
4 pp wiggle at cat12–14 while the peak was at 1 way.  That change cannot
favour the hypothesis: it turned a rubber-stamp PASS into the refutation the
prereg text required ("peaking at an intermediate width").

## Verdicts

| id | prediction | verdict |
|---|---|---|
| S1 | wb degrades victim ≥ 1.30× over quiet | **PASS** 2.287× (167.875 / 73.406) |
| S2 | CAT protection non-monotone, peak at intermediate width | **FAIL — refuted.** Peak at cat01 (91.4%). Protection *rises* as the mask narrows. |
| S3 | nta protects ≤ 10% of best CAT | **FAIL — refuted.** nta_R=15.3%, best CAT=91.4%, frac=0.168 |
| S4 | best-protection CAT costs tenant ≥ 10% tuples/s | **PASS** cat01 costs **42.02%** of `join_mtuples_per_s` |
| S5 | flush-behind's best setting costs tenant ≥ 10% | **FAIL — refuted.** fb256k costs **6.31%** |

CERTIFY: NO.  Complete; three of five predictions fail.  Failures are
refutations, not discoveries.

## What it costs to protect the neighbour

Quiet victim 73.406 cycles/load (sd 0.006) — the established 73.398 floor
reproduced.  Unprotected co-run (wb) 167.875 (sd 0.326), tenant 42.08
Mtuples/s.

Protection \(R = (v_{wb}-v)/(v_{wb}-v_{qui})\).  Tenant cost
\(1 - t/t_{wb}\).

| arm | victim cyc/load | R | tuples/s | tenant cost |
|---|---|---|---|---|
| qui | 73.406 | — | — | — |
| wb | 167.875 | 0 | 42.08 | 0 |
| cat01 | 81.536 | **91.4%** | 24.40 | **42.0%** |
| cat04 | 107.212 | 64.2% | 28.38 | 32.6% |
| cat08 | 141.849 | 27.5% | 34.74 | 17.4% |
| cat10 | 158.238 | 10.2% | 37.80 | 10.2% |
| cat15 | 167.713 | 0.2% | 42.10 | −0.05% |
| nta | 153.411 | 15.3% | 43.32 | −2.9% |
| fb64k | 124.277 | 46.1% | 39.60 | 5.9% |
| fb256k | 125.815 | 44.5% | 39.43 | 6.3% |
| fb1m | 137.871 | 31.8% | 39.50 | 6.1% |

cat15 matches wb: the control that "tenant confined to all 15 ways" is a no-op
holds.  Match counts identical across every tenant arm (534773760).

**The paper's application-unit number, on this part, is: the CAT width that
actually protects the neighbour (1 of 15 ways, 91% recovery) costs the join
42% of its tuples/s.**  At the 10% tenant-cost contour the mask is ~10 ways
and recovery is also ~10% — CAT is paying 1:1 in this unit.  That is the
opposite of "CAT works, it just costs 16.7%": 16.7% cost is cat08, and
recovery there is 27.5%, not the 91% the 1-way mask buys.

## S2, reported as a refutation

The model (20-way HNF) had protection peak at 8 ways and fall at narrower
masks, because way-starvation raised the tenant's miss traffic more than its
occupancy cost.  On this 15-way SPR LLC, in application units, that did not
happen.  R(w) is monotone from w=15 (~0) to w=1 (91.4%).  A ~5 pp overshoot
at cat12–14 (victim slightly *slower* than wb) is a wide-end wiggle, not a
narrow-mask starvation peak; the analyzer is pinned to reject that as S2.

This is Intel-specific until the same sweep exists on Bergamo.  It does not
licence writing the model's non-monotone curve as a silicon result.

## S3 and S5, also refutations

- **nta** is not a null on this part (unlike Zen 4c, where the victim stayed
  at 100% L2 miss).  It recovers 15.3% of the wb tax and the tenant is 3%
  *faster*.  That is more than the registered 10%-of-best-CAT bar (which was
  9.1 pp; nta delivered 15.3 pp).  It is still not a substitute for CAT
  (15% vs 91%).  Do not upgrade the miss into "nta works".
- **flush-behind** costs 6.3%, below the registered 10%.  It also recovers
  ~45% of the victim harm.  An unregistered iso-protection reading — fb256k
  ≈ cat06 on R, at a quarter of cat06's tenant cost — is noted here and is
  **not** a registered claim.  S5 is FAIL.

## Page-size sensitivity (not the registered campaign)

Before the user authorized growing node 0's hugepage pool, the same 8 GiB
geometry ran on 4K pages
(`data/silicon_e2e_hashjoin_4k.jsonl`, 105/105 ok).  Node 0 as-found had
only 1024 × 2 MiB pages; 8 GiB `MAP_HUGETLB` SIGBUS'd.  Pool grown to 8192
on node 0, node 2 left at 35488.

| | 4K | huge2m |
|---|---|---|
| qui | 73.403 | 73.406 |
| wb tax | 2.310× | 2.287× |
| cat01 R | 91.4% | 91.4% |
| cat01 tenant cost | 41.93% | 42.02% |
| nta R | 16.7% | 15.3% |
| fb256k tenant cost | 6.22% | 6.31% |
| S2 | FAIL (peak at 1 way) | FAIL (peak at 1 way) |

TLB was not the mechanism.  Every verdict agrees.  The registered numbers
are the hugepage column.

## Apparatus notes (already in the calibration record)

Calibration found four bugs before any 8 GiB result was taken: wrong resctrl
group name in the staged runner, `--cpu-list` vs `taskset`,
`--flush-distance` a silent no-op in `--mode single`, victim window shorter
than one trial, then SIGBUS on 8 GiB hugepages.  None of those records are
cited above.

## What this does not show

STREAMING.  Combining cat01's 42% silicon cost with a modelled STREAMING
point in one figure without labelling the platform of each is forbidden by
the pre-registration.

---

# Addendum 1 — 2026-09-01: S2 is untestable, not refuted. Flush-behind is the finding.

The verdict table above is left verbatim (A6.19).  Two of its readings are
wrong.  This addendum withdraws them.  S1 and S4 stand.  S3 and S5 remain
refutations.  CERTIFY remains NO.

## S2 withdrawn as a refutation

The model's non-monotonicity was way-starvation between 1 and 6 of 20 HNF
ways:

| | capacity per way | 1-way mask | model's peak (8/20) |
|---|---|---|---|
| gem5 HNF | 5 MiB / 20 = 0.25 MiB | 0.25 MiB | 2.0 MiB |
| SPR socket 0 | 60 MiB / 15 = 4.0 MiB | **4.0 MiB** | — |
| Bergamo (not measured) | 16 MiB / 16 = 1.0 MiB | 1.0 MiB | — |

Silicon's tightest CAT slice is 16× the model's floor and 2× its peak.  The
starvation regime is not expressible with 15-way CAT on a 60 MiB LLC.  R(w)
rising monotonically to 91.4% at 1 way is exactly what the model predicts
*in that capacity range*.  The sweep never entered the regime where the
model bent.  Framing that as "did not reproduce on this part… Intel-specific
until Bergamo" attributed to the microarchitecture what is a range-coverage
limitation.  Bergamo will not settle it either: 1.0 MiB/way is still 4× the
model's tightest.

**Withdrawn:** S2 FAIL — refuted.  **Restated:** S2 is **UNTESTABLE** at this
granularity.  Testing it requires a much smaller LLC slice, or sub-way
control CAT cannot express.  The analyzer now emits `UNTESTABLE` and does
not let S2 fail certify.  The curve is kept as a description, not a test.

This statement is more interesting than the refutation it replaces: the
model's regime is one CAT cannot reach.

The 4K sensitivity table's "S2 FAIL (peak at 1 way)" row is withdrawn on
the same ground.  TLB-was-not-the-mechanism still holds; every *testable*
verdict still agrees.

## F-fb is the finding.  STREAMING's bar moved.

The headline was framed against CAT's 42% tenant cost at 91% protection.
At equal protection the shipping competitor is flush-behind, and nta
dominates the weak-CAT end outright:

| | R | tenant cost | |
|---|---|---|---|
| cat06 | 44.1% | 25.18% | |
| fb256k | 44.5% | 6.31% | **4.0× cheaper** |
| cat09 | 18.2% | 13.59% | |
| nta | 15.3% | −2.95% | faster than baseline |

S5 FAIL (fb costs 6.3%, bar was ≥10%) was reported as a refutation and
filed as an "unregistered iso-protection reading."  That reading is the
most consequential number in the campaign.  The gem5 wedge is +11.76% over
CAT — but CAT is no longer the relevant baseline on silicon.

**STREAMING's silicon bar is no longer "beat 42%."**  It is beat 6.3%
tenant cost at 44% protection, and beat free at 15%.  Whether STREAMING
beats flush-behind is an open question the paper must answer.  Promoting
this cannot favour STREAMING: it raises the bar.

S5 remains FAIL against its registered threshold.  F-fb is a finding
registered after seeing that miss (prereg amendment 1).

## Smaller points, now on the record

**hit_rate 0.5 → 1.0.**  Justified (M3: 0.5 miss-scatter saturates the
victim and masks the stream).  Silicon and the model now differ in two
dimensions, not one — hit rate and the CAT capacity range above.  Any
side-by-side has to carry both.

**p99, which the brief allowed and the report omitted.**  Estimator:
linear interpolation at rank `(n−1)·0.99` of the sorted per-trial
cycles/load, then the median of those five per-rep p99s.  Pooled is the
same interpolator on the concatenation.  Sidecar
`data/silicon_e2e_hashjoin_victim_p99.jsonl` (105 records, derived from
`hashjoin_huge.jsonl.d`; the committed JSONL is not rewritten).

| arm | median | med p99 | pooled p99 |
|---|---|---|---|
| qui | 73.406 | 73.45 | 73.47 |
| wb | 167.875 | 175.43 | 176.55 |
| nta | 153.411 | 157.41 | 158.06 |
| fb256k | 125.815 | **126.43** | 128.79 |
| cat01 | 81.536 | **81.61** | 81.67 |
| cat06 | 126.198 | **155.63** | 161.62 |
| cat08 | 141.849 | 179.09 | 185.31 |
| cat13 | 172.785 | 203.86 | 207.85 |

cat01's tail is as tight as its median.  Intermediate CAT widths are not:
cat06 matches fb256k on median R (44%) and then has a p99 29 cycles worse.
Protection at the p99, using the same formula against wb/qui p99:
fb256k **48%**, cat06 **19%**.  Equal-median-protection is not
equal-tail-protection.  A latency-sensitive neighbour is characterised by
its tail; flush-behind wins that comparison too.

**cat08 sd = 4.089** against 0.6–2.2 for its neighbours.  Per-rep medians
141.43, 141.85, **150.73**, 140.89, 144.87.  Tenant tuples/s 34.73 on every
rep (sd 0.030) — this is not a tenant-cost wiggle.  r3's trials start at
182 then 160, 150, 144… and the series stays high (min 141.9 vs ~138 on
the other reps).  One dirty victim-side rep, on the arm nearest the
model's peak width.  Median still 141.85; dropping r3 would not change S4
or the monotone shape.  Recorded rather than shrugged.

**cat12–14 negative protection is not a wiggle.**  R = −2.8%, −5.2%, −5.4%
at sd 0.6–1.5.  Every paired rep is slower than the same-rep wb (cat13
deltas +4.4 to +8.5 cycles/load).  cat15 ≈ wb (the null control still
holds).  Unregistered; might be real wide-mask overshoot.  It is not S2 —
S2 was a *narrow-mask* starvation peak, and this part cannot express that
regime.

**Host hugepage pool.**  Node 0 was grown 1024 → 8192 for the registered
`--huge2m` campaign and **restored to 1024** afterwards.  Verified
2026-09-01 on mos182: node0 nr=1024 free=1024; node2 left at 35488.
`setup_hugepages_node0.sh` still grows to 8192 for reproduction.

**TOCTOU on the mask.**  G-mask ran at setup; a ~20 s join then ran; a
foreign process did delete CLOS groups during that window.  The committed
JSONL has no post-rep re-read — "it didn't bite" is luck.  The runner now
snapshots `clos_b` after the measurement and before teardown
(`mask_got_after`, `mask_held_ok`).  Analyzer: if the field is present it
is required; if absent (this JSONL) the check is skipped.

## Amended verdicts

| id | prediction | verdict |
|---|---|---|
| S1 | wb degrades victim ≥ 1.30× over quiet | **PASS** 2.287× (unchanged) |
| S2 | CAT protection non-monotone in mask width | **UNTESTABLE** — CAT cannot reach the model's starvation regime |
| S3 | nta protects ≤ 10% of best CAT | **FAIL — refuted** (unchanged) |
| S4 | best-protection CAT costs tenant ≥ 10% | **PASS** 42.02% (unchanged) |
| S5 | flush-behind costs tenant ≥ 10% | **FAIL — refuted** (unchanged) |
| F-fb | (not a prediction) | **finding:** fb256k matches cat06 at 4.0× lower tenant cost; p99 is worse for CAT |
| F-nta | (not a prediction) | **finding:** nta recovers 15% and the tenant is faster |

CERTIFY: NO.  Complete; two testable predictions fail; S2 is not a test.
The paper's application-unit number on this part is no longer "CAT that
protects costs 42%."  It is: **flush-behind delivers CAT's mid-curve
protection at a quarter of the cost, and nta gives 15% recovery for
free.**  STREAMING has to beat those, on silicon, or the wedge is against
the wrong baseline.

