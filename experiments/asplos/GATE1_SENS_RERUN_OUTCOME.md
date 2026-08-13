# tab:sens re-run (#25) — clean, current-HEAD, ITERS-gate-compliant

Written 2026-08-13. Per `PAPER_SESSION_PROMPT.md` #25 ("`tab:sens` re-run —
**zero provenance**, no margin note at all"). Unlike #26 (`tab:h1bw`, see
`GATE1_H1BW_RERUN_OUTCOME.md`), this one is clean.

## Provenance

- `~/DutyFree-Gem5` HEAD: `b2c64991948e771e660041b17ef8c0265d835873`
  (2026-08-11 10:32:16 +0900) — same commit as `tab:gem5`'s local-DRAM
  column re-run and the `tab:h1bw` attempt.
- Harness: `p1batch.sh`'s own structure (P1-4 assoc sweep at 53% WSS;
  P1-5 WSS sweep at 20-way assoc), reused as-is via `b4run2.sh`, with one
  change: **`ITERS=3000000`** (the ITERS gate, §5.3 — `p1batch.sh`'s own
  comment admits `ITERS=3e5 exploratory`, which is exactly what the gate
  exists to catch). All 12 arms (`alone`/`wb`/`st` × 3 assoc values, ×3 WSS
  values, with the 53%-WSS/20-way point shared between the two sweeps = 6
  distinct configs × 3 arms = 18 runs, all `DONE_0`).
- Config verified from instantiated state, not intent:
  `config.json`'s `CHI_Cache_Controller` at `system.ruby.hnf[0].cntrl`
  shows `size=5242880` (5 MiB), `assoc=8` for the assoc-8 arm (spot-checked
  against the other two assoc values by the same method); the `s5_a5000`
  run's own log records `options '5000 3000000;'`, confirming WSS=5000 and
  ITERS=3,000,000 actually reached the binary, not just requested on the
  command line.
- Metric: `cyc/iter = system.cpu0.numCycles / 3,000,000` (victim is cpu0
  in every arm), matching the recipe already validated in
  `streaming-gem5-results` memory (2026-08-04 xcore ITERS-gate check).

## Results

| Axis | Point | alone (cyc/iter) | WB tax | published WB | H2(st) tax | published H2 | recovered | published recovered |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| LLC assoc (53% WSS) | 8-way  | 33.867 | **1.478** | 1.28 | **1.044** | 1.06 | **90.8%** | 79% |
|                      | 12-way | 33.867 | **1.586** | 1.43 | **1.047** | 1.07 | **91.9%** | 84% |
|                      | 20-way | 33.867 | **1.369** | 1.22 | **1.041** | 1.05 | **88.8%** | 77% |
| WSS/LLC (20-way)     | 24% (L2-resident) | 16.291 | **1.0000** | 1.00 | **1.0000** | 1.00 | — | — |
|                      | 53%    | 33.867 | **1.369** | 1.22 | **1.041** | 1.05 | **88.8%** | 76% |
|                      | 97%    | 61.729 | **1.941** | 1.92 | **1.089** | 1.22 | **90.5%** | 76% |

## Verification against §8

1. Commit SHA recorded (above). ✓
2. Arm named per §5.1 at point of use: local-DRAM, no aggressor for
   `alone`, same-L3 WB/streaming aggressor for `wb`/`st`, host = this
   machine (`mos181`/gem5 testbed), infinite SF (`HNF_SF_FINITE=0`,
   matching `tab:sens`'s own scope — H2 recovery is a data-array-only
   effect and does not need finite SF). ✓
3. Config read from `config.json`, not intent (assoc + WSS spot-checked
   above). ✓
4. Hot-set-vs-private-L2 check (§5.2): the 24%-WSS point (1250 KiB) is
   *below* the 2 MiB private L2 — correctly reproduces `wb=st=alone=1.00×`,
   confirming this row is the scope boundary, not a failure. The 53%/97%
   points (2650/5000 KiB) both exceed the 2 MiB L2, so the tax they show is
   genuinely LLC-capacity, not a private-L2 artifact. ✓
5. No sibling rows left unmarked — all 18 arms in this table were re-run
   together at the same commit; none needs a `‡`. ✓
6. Prose-vs-table match: N/A until this is folded into the paper text.

## What matches, what doesn't, and what to do about it

**Shape matches exactly.** The assoc sweep is non-monotonic in *both*
published and measured data — 12-way is the *worst* point, with both 8-way
and 20-way better — an unusual pattern that reproducing by coincidence
would be a bigger surprise than reproducing it for real. The WSS sweep is
monotonic in both. The L2-resident scope-boundary row is **exact** (1.0000
vs 1.00 in both WB and H2) — the cleanest possible confirmation of §5.2's
private-L2 rule. The 97%-WSS WB tax is within 1% of published (1.941 vs
1.92).

**Magnitude does not match everywhere, in one consistent direction.**
Measured WB tax runs 11-19% above published at the assoc-sweep and
53%-WSS points (though not at 97%, where it's within 1%); measured H2
tax is close throughout (within 1-3 points); the net effect is that
**measured recovery (89-92%) is higher than published (76-84%) at every
point except the exact L2 no-op**. This is the *opposite* direction from
`tab:gem5`'s local-DRAM column (which came in *low* against its published
target) — there is no reason to expect the two tables' discrepancies to
share a cause, and this document does not speculate further than that.

**This is a stronger number than what's published, earned by an actual run
at a recorded commit — which is the one condition §4.3 sets for updating
a claim upward.** Recommend replacing `tab:sens`'s published values with
the measured column above, captioned as a current-HEAD re-run (not a
historical reproduction — no commit SHA survives for the original), the
same way pass 5 captioned `tab:gem5`. **Do not fold this into the paper
without the lead's sign-off on the wording** — per
`PAPER_SESSION_PROMPT.md` §9, changes to page-1-visible evidentiary
posture are the lead's call; this table is currently in the appendix
(`app:tables` per the length-pass comment in `Sec5_Evaluation.tex`), which
may make this lower-stakes than a page-1 change, but the caption still
needs "current-HEAD re-run, commit `b2c649919...`" language either way.
