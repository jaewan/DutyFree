# Items 9 & 10: hardware QoS enforcement is state-dependent on both vendors — and the monotone exhibit survives it

Item 9 asked whether the AMD CAT-residual instability and W5.3's any-cap MBA
behaviour are one observation, and whether the Intel CAT arms are bimodal. Both
answered from committed data; no machine used.

## The Intel CAT arms are bimodal, and the unpartitioned arms are not

From `results/clos_split/raw/`, n=30 per label, sorted per-rep values, split
detected where the largest gap exceeds 8× the median gap:

| arm | n | mean | CoV | low mode | high mode |
|---|--:|--:|--:|---|---|
| CAT 4/20 (`panel_B16`) | 30 | 126.129 | 2.99% | **1 rep** @ 106.38 — a single outlier, *not* a mode | 29 @ 126.81 |
| CAT 8/20 (`bsweep_B_8way`) | 30 | 113.165 | 5.24% | **6 @ 101.56** | 24 @ 116.07 |
| CAT 12/20 (`bsweep_B_12way`) | 30 | 101.433 | 5.29% | **12 @ 95.01** | 18 @ 105.72 |
| CAT 20/20 = unrestricted | 30 | 87.283 | 1.48% | — **unimodal** | — |
| fused unrestricted (control) | 30 | 88.083 | 1.48% | — unimodal (max gap 0.88 cyc) | — |

Two things follow. **The bimodality appears only when CAT is applied** — both
unpartitioned arms are unimodal at CoV 1.48%. And **the low-mode fraction grows
as the mask widens**: 1/30 at four ways, 6/30 at eight, 12/30 at twelve. The
looser the partition, the more often a run lands in a state where it costs less.

## The monotone harm survives, within each mode separately

| | 20/20 | 12/20 | 8/20 | 4/20 | monotone? |
|---|--:|--:|--:|--:|---|
| low mode | 87.28 | 95.01 (n=12) | 101.56 (n=6) | 106.38 (**n=1**) | yes |
| high mode | 87.28 | 105.72 (n=18) | 116.07 (n=24) | 126.81 (n=29) | **yes** |

**Corrected on audit:** the low-mode row's 4/20 entry is a *single sample*, so
the low-mode sequence is well supported only across 20/20 → 12/20 → 8/20 and its
final step should not be leaned on. The high-mode sequence is populated
throughout (n=18–29) and is the one that carries the claim. Both are monotone;
only the second is well sampled.

Tightening CAT makes the fused victim monotonically worse **in both states**. So
the exhibit the panel wants as Figure 1 is robust to the bimodality: it is not an
artifact of averaging two states, because the ordering holds inside each. What
the bimodality does mean is that its CoV column (5.2–5.3% at eight and twelve
ways) reports the width of a *mixture*, not of one distribution, and that should
be said rather than left for a referee.

## This is one observation with the AMD findings, not two

Three separate results, now readable as one:

1. **Intel CAT, mos181** — bimodal exactly when the partition is applied (above).
2. **AMD CAT, moscxl** — the same unmodified script gave 7.23× and then 9.87× on
   re-run, "a real, reproducible, isolated-to-CAT drift, verified all the way to
   the raw hardware QoS mask MSRs — enforcement is correct; the physical cause of
   the drift is not identified" (`e1_residual_decomp/RESULTS.md`).
3. **AMD MBA, moscxl** — recovery appears discontinuously where the cap begins to
   bind (24.5 → 23.6 GB/s) and is then flat from 96% of bandwidth down to 8%
   (`W5.3_L5_EVIDENCE_2026-08-23.md`), with arming-without-binding doing nothing.

The honest joint statement, which pre-empts a referee assembling it
adversarially: **hardware QoS enforcement on both vendors exhibits
state-dependent behaviour we can bound but not explain.** Masks are verified
correct at the MSR level in every case; what varies is the effect at a fixed
mask. This is a property of the platforms, not of our instrumentation, and it is
worth one paragraph rather than three scattered caveats.

Note it is *not* a wash for the argument. In every instance the QoS control
either fails to help or actively harms; the state-dependence changes the
magnitude, never the sign.

## Item 10 — Latin-square ordering as house standard

Adopted, with the retrospective note the panel asked for.

**Standard:** every arm-comparative campaign uses a randomized balanced design —
a Latin square when arms ≥ 3, alternation when arms = 2 — so each arm occupies
each position within a repetition block an equal number of times. Simple per-rep
shuffling is **not** sufficient: checked before use, at the intended seed it put
one arm in position 1 zero times and position 4 six times over 12 reps
(`T3_HUGEPAGE_PREREG` Addendum 1), which relocates a position confound rather
than removing it.

**Why:** T3 run 2 measured a position effect confined to the quiescent arm,
acting by mode selection — slow-mode frequency 4/6, 3/6, 2/6, 1/6 across
positions 1→4, monotone — while the loaded arms were position-insensitive. Under
the fixed order of T3 run 1 that effect alone flipped the sign of the registered
statistic.

**Retrospective status of existing results:**

| campaign | ordering | status |
|---|---|---|
| `clos_split` / `tab:fused` (n=30) | `run_sequence()` shuffles all `(label, rep)` pairs under a fixed seed | **already protected**; state it in the caption |
| T3 run 1 | fixed | superseded by run 2; `R` withdrawn as a point estimate |
| T3 run 2, T4 phase 1/1b, A6, A4 morsel sweep | balanced | compliant |
| E1 / `e4_hygiene` matched-bw pair (n=12) | "rep-interleaved with quiescent baseline" | interleaved, not balanced; adequate for a two-arm pair, flagged |
| W5.3 / GPROBE (n=3) | not stated | **flagged**; n=3 with documented bistability, per-rep values still owed |
