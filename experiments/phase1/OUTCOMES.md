# Phase 1 — Outcomes vs pre-registered hypotheses

Per ground rule #5, `HYPOTHESES.md` is frozen as written 2026-08-05, before any
run. This file records actual outcomes against those pre-registered predictions.

## P1 (E1, AMD residual mechanism) — RESOLVED, favors hypothesis (b)

> "The AMD 6.92x post-CAT residual is dominated by coherence machinery, not
> LLC capacity: either (a) probe-filter/back-invalidation churn (victim LLC
> occupancy collapses despite dedicated ways) or (b) shared lookup/queue
> occupancy (victim occupancy intact, hit/miss latency inflates). H2
> (allocation-bypass) alone would NOT remove it; a type-licensed
> lookup/enrollment skip (H3+) would."

**Outcome: hypothesis (b), corroborated three ways** — see
`e1_residual_decomp/RESULTS.md` "Overall E1 verdict" for full detail:

1. A2 (CAT): victim occupancy intact (92% of quiescent), L2 miss rate barely
   moves (+5.6pp) against a 7.2x tax.
2. A4 (lookups-only, near-zero memory traffic): substantial 1.25-1.30x tax
   from coherence lookups alone (CI excludes 1.0).
3. A6 (concurrency sweep): superlinear knee in tax vs thread count between
   t=2 and t=3 that a flat bandwidth curve does not explain.

The "H2 alone would not remove it" half of P1 is not directly tested here
(that requires the gem5 H2 model, out of scope for this hardware campaign)
but is consistent with everything measured: A4 shows the lookup path itself
levies a real tax with essentially zero fill traffic, which is exactly the
component H2 (an allocation/fill-time bypass) would not touch.

**Second-order finding beyond the pre-registered P1 statement**: the 7.2x
residual looks like a composite, not a single mechanism — A4's lookup-only
tax (1.25-1.30x) is real but modest; the A1-vs-A5 matched-bandwidth
comparison (not itself part of the pre-registered A4 verdict logic, but
directly requested by the mission's E1 arm design) shows a further ~3.55x
CXL-path-specific multiplier. This composite structure was not anticipated
in the P1 statement as written and should inform how the gem5 team scopes
the H3 model (see RESULTS.md).

## P2 (E2, Intel bandwidth mechanism) — CONFIRMED at small D, plus a correction to the pre-registered framing

> "Single-core WB CXL bandwidth (~15.8 GB/s) does NOT depend on the LLC as a
> prefetch staging buffer: bounding the stream's LLC footprint (flush-behind)
> keeps bandwidth within ~15% of unbounded WB down to small footprints."

**Correction discovered while investigating the E2a result**: the "~15.8
GB/s" figure in this pre-registered P2 statement is not an Intel number.
`Sec2_DirectoryTax.tex:43-53` is one paragraph, opening "On AMD we hold the
CXL byte stream fixed..." — the 15.8/4.2 GB/s single-core WB/WC figures sit
inside that same AMD paragraph. No Intel-specific single-core WB bandwidth
figure exists anywhere in the paper; the real Intel numbers are 8-thread
*aggregate* (34 GB/s unpartitioned, 32-33 GB/s under CAT). This does not
retroactively change what P2 is *asking* (whether bounding LLC footprint
preserves bandwidth) — it only means E2a's baseline-matching framing was
against the wrong platform's number. See `e2_h1_speed/REPRO_FAILURE.md` for
the full correction.

**Separately, and still true regardless of the correction**: measured Intel
single-core WB CXL bandwidth is ~8.9 GB/s, capped regardless of MSR 0x1A4
prefetcher-bit state (6 configs cluster within ~3%) or kernel choice (scalar
vs. AVX2-unrolled probe kernel agree), while both kernels reach ~14.2 GB/s on
local DRAM. CPU frequency/governor and software MLP were ruled out as
causes. Leading hypothesis: the CXL device swap (Micron->Montage, see
`e4_hygiene/PLATFORMS.md`) plus a PCIe link negotiated at x8 instead of its
x16 capability. Root-caused as far as remotely possible: the device is a
Root Complex Integrated Endpoint with no intermediate switch to blame, and
resolving the x8/x16 question needs BIOS-setup or physical access not
available in this session. **Genuinely blocked** on that access.

**Follow-up completed later this session**: the real Intel reproduction gate
(8-thread aggregate ~34 GB/s WB, 2.03x/0.99x tax family) was run via the
existing `cat_mba_driver.sh` (n=30/condition) and **PASSES across all 11
conditions** -- baseline tax 1.946x (paper 2.03x), CAT sweep 0.993x for both
way-counts (paper 0.99x), full MBA rate-throttle curve (4 points, all within
gate), both negative controls. See `e2_h1_speed/intel_repro_gate_RESULTS.md`.
This confirmed the hypothesis above: the single-core bandwidth gap did NOT
propagate to the aggregate/tax-ratio numbers.

With the gate passed, **P2 itself was tested directly** (E2b,
`stream_wb_flushbehind.c` + `run_e2b_flushbehind.py`, n=12): at D<=2 MiB,
aggregate bandwidth is within 1.3% of the D=off (unbounded) rate — P2
CONFIRMED, with a lot of margin versus the pre-registered "~15%" threshold.
A genuine non-monotonic wrinkle showed up at 16-64 MiB (bandwidth dips
before recovering at D=off) — see `e2_h1_speed/e2b_RESULTS.md`.

The EMR host's governor/turbo state was also found mismatched to the
paper's methodology (powersave/turbo-on vs required performance/turbo-off)
and corrected mid-session with user confirmation
(`e4_hygiene/emr_prior_power_state.txt` records the prior state for
restoration).

## P3 (E2, Intel silicon H2 emulation) — CONFIRMED, with a real confound flagged

> "A flush-behind stream at near-full bandwidth returns the Intel co-run
> victim to ~baseline (silicon emulation of H2)."

Tested directly (E2b, n=12): at D<=2 MiB, victim tax is 0.90x
[0.898,0.905] -- not just "recovered to baseline," measurably *faster*,
CI excluding 1.0 entirely. **Investigated rather than taken at face value**:
`turbostat` confirms uncore frequency scales from 1500 MHz (quiescent) to
2400 MHz when the 8-thread aggressor is active (core P-states stayed
pinned at 1.9 GHz throughout) -- quiescent and co-run are not
apples-to-apples baselines here, so the exact 0.90x figure is confounded by
an uncore-frequency effect distinct from H2. The confound flatters the
result (argues the same direction as the hypothesis), so P3's qualitative
conclusion stands, but the precise magnitude should not be quoted as "10%
faster because of H2." See `e2_h1_speed/e2b_RESULTS.md` for the full
writeup and what a cleaner re-measurement would need.
