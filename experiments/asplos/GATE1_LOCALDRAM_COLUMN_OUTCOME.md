# Outcome: tab:gem5 local-DRAM WB column re-run

Adjudicates `GATE1_LOCALDRAM_COLUMN_PREREGISTRATION.md`. All twelve arms
landed; nothing here was decided after seeing the data.

**Bottom line: no configuration in the pre-registered space reproduces the
published column.** Aggressor placement moves the tax in the predicted
direction, by a consistent ~15%, and closes about a fifth of the gap. The
published 1.79/2.57/2.82 still has no reachable configuration behind it.

## Run health

12/12 arms `DONE_0 MANIFEST_0`. `ITERS=3000000` uniform (the ITERS gate — 3e5
is printf-contaminated). Single producing commit `b2c6499194`,
`dirty_tree: False` on every arm. Reproduce with
`python3 experiments/asplos/analyze_localdram_column.py`.

Placement verified from per-controller counters, not from the env the script
intended (deliverable 4). Every `ALL_LOCAL` arm is 100.00% on `mem_ctrls0`;
every loaded default arm splits across both. Manifest and counters agree on
all twelve.

## The column

Each cell is its own `wb` ÷ its own matched `alone` from the same config.
Victim is cpu0, cost is `numCycles/ITERS`. No ratio crosses a config boundary.

| WSS (% LLC) | alone c/i | CXL aggressor | local-DRAM aggressor | placement uplift | published | local vs published |
|---|---:|---:|---:|---:|---:|---:|
| 1280 (25%) | 16.31 | 1.000× | 1.000× | 1.000× | 1.79× | **−44.1%** |
| 2650 (52%) | 33.87 | 1.368× | 1.600× | 1.170× | 2.57× | **−37.7%** |
| 5120 (100%) | 62.48 | 1.960× | 2.249× | 1.147× | 2.82× | **−20.2%** |

## Predictions

**P1 — PARTIAL.** 53% local-DRAM = **1.600×**. The pre-registered `above`
test passes: 1.600 clears 1.2189 × 1.15 = 1.402, and it also clears the
in-run CXL arm (1.368×) by 17.0%, so the direction holds under both the
cross-commit comparison the prereg named and the same-run comparison that is
methodologically sounder. The `near_pub` test fails: 1.600 is 37.7% below
2.57, far outside ±15%.

Latency placement is real but small. It was asked to supply +1.202 and
supplied +0.232 — **19% of the gap**. This is the "P1 fails" branch of the
prereg's decision table in substance, reached with a measured alternative
rather than an absence: the column goes to the lead as drop-or-caveat, now
with a number to caveat it *to*.

The caption's own calibration claim does not survive. It reads *"calibrated
to the local-DRAM point (sim 2.57× vs. hw 2.61× at 53%)."* The simulated
local-DRAM point at 53% is 1.600×, which is 38.7% below the hardware point it
is said to be calibrated against.

**P2 — HOLDS, decisively.** The 25% row is **1.000×** under both placements
(1.00002× / 1.00001× before rounding) against a published 1.79×. This is not
a failed load: the local arm pushed 123.6 MB entirely through ctrl0 while the
CXL arm pushed 77.7 MB, i.e. **1.59× more traffic**, and the victim's cost
moved in the fifth decimal. A 1280 KiB victim is resident in the 2 MiB
private L2, so a shared-LLC capacity tax has nothing to act on.

**Withdraw the 25% row regardless of what happens to the other two.** It is
the fourth instance in this project of one modelling error — hot set sized
against shared LLC without first clearing private L2 (gem5 fused hash-join
null; exp41's first 4 MiB Intel attempt against EMR's 2 MiB private L2; this
row; and the same question one cache level up in the GAPBS sizing gate).
Write the hot/L2 finding up once and have both this and the fused null cite
it.

**P3 — HOLDS.** No self-thrash confound. `SnpCleanInvalid` into the
*victim's* L1D across the six loaded arms: 0, 0, 0, 1, 5, 9. The 53% local
arm — the one deciding P1 — took exactly **1** in 162M cycles. The bulk of
the counter sits on cpu1, the aggressor invalidating its own lines, which is
expected. The victim's slowdown is pure capacity with no snoop-filter
component confounding it.

## Secondary finding: the prose/table anomaly is an arm-identity failure

`GATE1_RECONCILIATION.md:96-119` recorded two undistinguished hypotheses for
the paper citing 1.34× at two sites while `tab:gem5` prints 2.57× for the row
being described: (a) the prose is stale, (b) the prose describes a different
run than the table.

This run supports **(b)**. The in-run CXL-aggressor arm at 53% measures
**1.368×**, within 2% of the prose's 1.34×, while no arm under either
placement reaches 2.57×. The prose figure is approximately reproducible and
the table figure is not, which is the signature of two different arms rather
than one stale number.

Reclassify the defect: not "stale number, update it" but **arm-identity
failure** — a CXL-aggressor operating point and a local-DRAM one presented as
if they were the same measurement. The fix is naming the arm at both sites,
which is the standing rule, not editing one number to match the other.

One caveat on the strength of this: the same nominal CXL 53% arm read
**1.2189×** at commit `a309523389` and **1.368×** here at `b2c6499194`, a 12%
move across commits. The CXL column is not perfectly stable either, so treat
the 1.368-vs-1.34 agreement as supporting evidence, not as an identification.

## The unexplained residual, and the test that would resolve it

The shortfall against published narrows monotonically with WSS: −44.1%,
−37.7%, −20.2%. That is a pattern, not noise, and it is not explained by
placement.

One hypothesis fits the shape: the published column was produced under
uniformly greater LLC pressure than ours — a smaller effective shared LLC
would inflate every row and would inflate the low-WSS rows most, because
those are the rows closest to fitting. Gate 2's pre-registered discriminating
re-run (10 MiB actual vs 5 MiB nominal behind the co-run pair) is the
existing instrument that tests the same family of question from the other
direction.

Stated as a hypothesis with a named test, not as a finding. Nothing in this
run measures the published configuration, because that configuration is not
recorded anywhere — which is the original Gate 1 defect and remains unfixed.

## Recommendation to the lead

1. **Withdraw the 25% row.** P2 is unambiguous and the mechanism is
   understood.
2. **Do not print 2.57× or 2.82× as-is.** Neither has a reachable
   configuration. Either drop the column or republish it at the measured
   1.600×/2.249× bound to this commit and manifest, with the aggressor
   placement stated in the caption — "local-4" currently describes the
   hardware column and is silently assumed of the gem5 one.
3. **Drop the calibration sentence** or restate it, since sim 1.600× against
   hw 2.61× is not a calibration.
4. **Name the arm at both 1.34× prose sites.**

## Scope

Settles one column's provenance. Does not touch the δ embargo, Build B,
anything H3, or `tab:h3sf`'s unresolved SF geometry.
