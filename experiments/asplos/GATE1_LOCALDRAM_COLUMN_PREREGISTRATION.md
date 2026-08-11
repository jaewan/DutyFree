# Pre-registration: tab:gem5 local-DRAM WB column re-run

Dated 2026-08-11, before running. Closes the Gate 1 escalation on
`tab:gem5` ("escalate, not re-run" — the column was unreachable without a
script change). Project lead's call on 2026-08-11: **patch `se.py`, then
re-run.**

## What the paper claims

`tab:gem5` (Sec5_Evaluation.tex:154-177) puts a gem5 WB column beside an
EMR hardware column and calibrates one to the other:

| Victim WSS | hw CXL-8 | hw local-4 | gem5 WB | gem5 +H2 |
|---|---:|---:|---:|---:|
| 25% LLC | 1.27x | 2.36x | **1.79x** | 1.00x |
| 53% LLC | 2.03x | 2.61x | **2.57x** | 1.00x |
| 100% LLC | 2.11x | 2.48x | **2.82x** | 1.00x |

The caption states the calibration explicitly: *"The model is calibrated to
the local-DRAM point (sim 2.57x vs. hw 2.61x at 53%)."*

## Why the column was unreachable, and what changed

For the gem5 WB column to be the local-DRAM comparison the caption says it
is, the **simulated aggressor** must allocate from the local-DRAM pool.
Before today it could not: `se.py` hardcoded cpu0 -> DRAM pool 0 and
cpu1+ -> CXL pool 1, and the only override (`ALL_CXL=1`) moved everyone
the *other* way. A victim+aggressor pair could not be co-placed on local
DRAM without editing the file.

Patched 2026-08-11 in `gem5/configs/deprecated/example/se.py` (mirrored
into the `~/DutyFree-Gem5` build clone, which is the copy `b4run*.sh`
actually executes after its `cd`): three overrides in descending
precedence — `CPU_POOLS="0,0"` > `ALL_CXL=1` > `ALL_LOCAL=1` > default.
`ALL_CXL`+`ALL_LOCAL` together is a `fatal`, not a silent winner.
`gate1_manifest.py` records all three, so a placement-overridden run no
longer produces a manifest indistinguishable from a default run.

Note what `ALL_LOCAL=1` does and does not move here: cpu0 (victim) is
already on pool 0 by default, so **only the aggressor's placement
changes** (203 ns CXL -> 98 ns local DRAM). The victim's quiescent
baseline should therefore be unchanged. We measure it per-config anyway
rather than assuming it — omitting the matched quiescent arm is exactly
what made the fused hash-join null misread once already.

## Operating point

- Harness `experiments/asplos/b4run2.sh`, tags `alone` (quiescent) and
  `wb` (loaded), at gem5 `a309523389` + the uncommitted `se.py` patch.
- 2 cores, O3CPU @1.9 GHz, L1d 48 KiB/12, **L2 2 MiB/16 private**, LLC
  5 MiB/20 shared non-inclusive, CHI Pt2Pt, SimpleMemory 98 ns local /
  203 ns CXL.
- `HNF_SF_FINITE=0` (infinite SF): `tab:gem5` is the capacity table; the
  finite-SF charge is `tab:h3sf`'s subject, not this one.
- Aggressor `testcase/dirtax/aggressor`, 1 thread, `AGG=10.0`.
- Victim WSS at 25/53/100% of 5120 KiB = **1280 / 2650 / 5120 KiB**.
  2650 is the established 53% point (`b4run.sh`'s hardcoded default).
- `ITERS=3000000` per the ITERS gate — 3e5 is printf-contaminated.
- Placement arms: default (aggressor on CXL) and `ALL_LOCAL=1`
  (aggressor on local DRAM), so this run also re-derives the CXL column
  under identical conditions instead of citing the older `table-corun-v2`
  figure across a config boundary.

## Predictions (falsifiable, stated before running)

**P1 — the main one.** Moving the aggressor from 203 ns to 98 ns raises
its achievable fill rate, so LLC pressure rises and the WB tax rises with
it. At the 53% point the CXL-aggressor arm re-ran clean at **1.2189x**
(`table-corun-v2`, `a309523389`). Prediction: **the `ALL_LOCAL` arm lands
materially above 1.2189x, and near the tabulated 2.57x**, if latency
placement is what separates the published column from the Gate 1 re-run.

**P2 — the 25% row is separately at risk, for a reason that has bitten
this project before.** The private L2 is 2 MiB. A victim at 1280 KiB is
**L2-resident**, so a shared-LLC capacity tax has almost nothing to act
on. P1-5 already measured `wb = st = 1.00x` at WSS=1250 KiB through the
real `setstreaming` path. Prediction: **the 25% row reproduces near
1.00x, not 1.79x, under any aggressor placement.** If so the defect in
that row is not placement at all but hot-set-versus-private-L2 sizing —
the same pathology as the fused hash-join null
(`GEM5_FUSED_NULL_SESSION_PROMPT.md`), which would make it the second
instance of one modelling error rather than two unrelated ones.

**P3.** The 100% row (5120 KiB = 80k lines) exceeds a 65,536-entry SF,
but at `HNF_SF_FINITE=0` that is inert. Prediction: no self-thrash
confound in this configuration. Stated so that a surprise here is
recognized as a surprise.

## What each outcome means

- **P1 holds (53% lands near 2.57x).** The column is vindicated and its
  lost configuration recovered. Paper fix is provenance only: bind the
  column to this commit + manifest and state the aggressor placement in
  the caption, since "local-4" currently describes the hardware column
  and is silently assumed of the gem5 one.
- **P1 fails (53% stays near 1.22x).** Latency placement does not explain
  the gap, and the published 2.57x has no reachable configuration behind
  it. The column then goes to the lead as a drop-or-caveat decision with
  evidence, which is a materially stronger position than today's
  "suspected unreproducible".
- **P2 holds (25% near 1.00x).** That row is withdrawn regardless of what
  P1 does, and the hot/L2 finding gets written up once and cited by both
  this and the fused null.
- **P1 holds but P2 also holds.** Most likely mixed outcome: the column is
  real at 53/100% and wrong at 25%. Report as such; do not let a
  vindicated 53% carry the 25% row across the line with it.

## Deliverables

1. This file, committed before the first measurement run.
2. Six arms minimum: {1280, 2650, 5120 KiB} x {default, ALL_LOCAL}, each
   with its own matched `alone` quiescent baseline from the same config.
3. `gate1_manifest.py` output per arm, with `mem_pool_policy` showing the
   placement actually used.
4. Per-controller `stats.txt` traffic confirming where each process's
   bytes landed — the manifest records intent, the controller counters
   record fact. These must agree; if they disagree the manifest is wrong,
   not the counters.
5. An outcome doc naming which predictions held, and the updated Gate 1
   reconciliation row.

## Out of scope

Build B, anything H3, `tab:h3sf`'s unresolved SF size, and the paper's
prose. This run settles one column's provenance. It does not touch the
delta embargo.
