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

## P2 (E2, Intel bandwidth mechanism) — BLOCKED, plus a correction to the pre-registered framing

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

**Not actually blocked, and not yet tested**: whether the real Intel
reproduction gate (8-thread aggregate ~34 GB/s, 2.03x/0.99x tax) holds on
this hardware. That doesn't depend on the single-core question and should
be tested directly in a follow-up rather than assumed to be broken.

The EMR host's governor/turbo state was also found mismatched to the
paper's methodology (powersave/turbo-on vs required performance/turbo-off)
and corrected mid-session with user confirmation
(`e4_hygiene/emr_prior_power_state.txt` records the prior state for
restoration).

## P3 (E2, Intel silicon H2 emulation) — NOT YET TESTED, not blocked by the above

> "A flush-behind stream at near-full bandwidth returns the Intel co-run
> victim to ~baseline (silicon emulation of H2)."

Not run in this pass; depends on the flush-behind streamer (clflushopt at
distance D), which has not been implemented yet. Unlike P2's single-core
framing, P3's reproduction gate ("reproduce 2.03x at D=off first") is a
tax *ratio*, not an absolute bandwidth figure, so it is not automatically
invalidated by the single-core bandwidth question above -- it should be
tested directly in a follow-up. Tracked as open work, not attempted in this
pass.
