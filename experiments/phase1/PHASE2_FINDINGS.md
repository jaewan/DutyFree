# PHASE 2 FINDINGS — panel-directed follow-up, 2026-08-07

> **CORRECTION (2026-08-07/08, `e2_h1_speed/PHASE2_E2B_WARMUP_CORRECTION.md`):**
> wherever this file cites E2b's D-sweep taxes, they were measured under a
> systematic cold-quiescent/warm-loaded asymmetry. Corrected (matched
> protocol, n=12): small-D (32KiB/256KiB/2MiB) ~0.90x → **~0.99x**; D=16MiB
> **sign-flips** 0.951x → **1.018x** (small real tax, not sub-baseline);
> D=64MiB 1.335x → **1.213x**; D=off ~unchanged (2.307x → 2.341x). The
> "large-D unaffected" claim in an earlier version of this banner was
> itself wrong for D=16MiB/64MiB — see the correction file.

Addendum to `PHASE1_FINDINGS.md`. Written in response to a technical panel
review of the Phase 1 report, which issued two corrections to its own prior
analysis, a major reinterpretation (occupancy, not capacity, as the binding
AMD resource), a named confound to close before writing anything down, and
an ordered Phase 2 work list. This file reports what that work list found.

## Headline result: H2 does not port to AMD by analogy from Intel

**Phase 2.4** built and ran the AMD flush-behind cross-vendor discriminator,
pre-registered before any measurement
(`e1_residual_decomp/PHASE2_AMD_FLUSHBEHIND_PREREGISTRATION.md`): occupancy
model predicted residual >=5x at small D; capacity model predicted
collapse to ~0.9-1.0x, matching Intel's E2b. **Outcome: occupancy model
confirmed, capacity model refuted.** Best-case AMD recovery (D=256 KiB):
tax=5.94x [5.82,5.99] -- a 71.5% reduction from D=off's 20.84x, essentially
matching CAT's own 69% reduction and landing at a comparable residual. The
identical flush-behind mechanism that returns Intel's victim to ~baseline
(E2b: 0.90-0.905x) leaves AMD's victim at ~6x. **This is measurement-backed,
not inferred**: a gem5 model that implements H2 as "bound residency" and
expects Intel-like recovery on an AMD-analog config would be wrong. The
AMD-analog model needs a transaction-pool/queue mechanism H2 does not
touch -- consistent with A4's independent finding (Phase 1) that lookups
alone, with near-zero memory traffic, already tax the victim.

This directly answers the panel's "hole" in the Phase 1 report (was A5's
CXL-specific multiplier real, or a thread-count artifact?) via a different
and more decisive route than the redo itself gave: Phase 2.4 didn't need to
resolve whether CXL and local share one occupancy curve to establish that
**AMD's residual, regardless of its exact decomposition, does not respond
to non-allocation the way Intel's does.** That conclusion stands on its own
evidence, independent of the inconclusive occupancy-collapse question below.

## What else Phase 2 found, in the order it was run

**2.1 (local-DRAM MSR control)**: neither CXL nor local DRAM bandwidth
craters when all four L1/L2 prefetcher bits are disabled (CXL: all 6
configs within ~2.3%; local: a real but modest ~4.5% drop tied to the L2
streamer specifically). Asymmetric, not symmetric -- rules out "one hidden
prefetcher explains both floors equally," doesn't crater either. Separately,
verified against the paper's exact text (`Sec5_Evaluation.tex:87`): the
"LLC prefetcher disabled, matching the machines" claim is about a different,
untested prefetcher than the L1/L2 bits this experiment toggled -- neither
confirmed nor falsified here.

**2.2 (A5 redo, thread-matched, unthrottled)**: caught and fixed a real bug
from the first draft (wrong aggressor mode string silently ran "local" arms
on CXL). Cross-validated A6's original superlinear knee closely on
re-measurement. New finding: AMD local DRAM single-thread bandwidth
(~43 GB/s) is already flat through 7 threads -- saturated at 1 thread.
The occupancy-collapse test (tax vs. BW x idle-latency) does **not** unify
CXL and local onto one curve, but inconclusively so: local's flat bandwidth
at 1 thread means its *true* loaded service time is almost certainly far
above the idle latency used, invalidating the cross-comparison. Revised
honest framing: both paths show occupancy-like (bandwidth-insensitive) tax
curves; whether they share one mechanism or two remains open.

**2.3 (uncore-pinned re-baseline)**: **self-correction.** An initial quick
check seemed to confirm the panel's hypothesis that uncore frequency
scaling (1500->2400 MHz) explained E2b's "faster than quiescent" result.
The full n=12 re-run contradicted it (tax unchanged, ~0.905 either way).
Direct `turbostat` verification confirmed uncore stays pinned throughout
even during "slow" runs, and three independent single-trial quiescent
invocations (zero aggressor, zero uncore change) gave bimodal results
(88.47, 81.86, 81.93) -- the same noise the quick check happened to sample
favorably. **Uncore frequency is ruled out; the true cause of E2b's
sub-1.0x result remains unidentified.** E2b's original numbers stand
un-corrected (they were never wrong; the explanation attempt was). No AMD
software control path exists for the analogous fabric-clock question
(no `hsmp`/`rdmsr` tooling, SMU-only control) -- documented as an open gap,
not elevated in priority given the Intel hypothesis didn't survive anyway.

**2.5 (gem5 finite-transaction-pool model)**: not attempted. The original
mission brief was explicit that gem5 is out of scope for this hardware
campaign. Flagged for explicit confirmation rather than executed on the
panel's instruction alone, since it directly conflicts with a boundary the
user set earlier. Phase 2.4's result gives the gem5 team a concrete,
falsifiable target (a transaction-pool mechanism that reproduces both
Intel's near-total flush-behind recovery and AMD's ~6x residual under the
identical mechanism) whenever that work is picked up.

## What this changes about how to read Phase 1

- The "composite mechanism" conclusion from Phase 1 (lookup-occupancy real
  but modest, CXL-path-specific component large) is **not undermined** by
  Phase 2.2's inconclusive occupancy-collapse test -- Phase 2.4 gives an
  independent, decisive confirmation that AMD's residual is occupancy-type
  and doesn't respond to non-allocation, via a completely different
  experiment (flush-behind) than the one that came back inconclusive
  (thread-matched CXL/local unification).
- One methodological lesson worth carrying forward explicitly: a quick,
  low-n "decisive" check (Phase 2.3's first pass) can look confirmatory and
  still be wrong. The full n=12 protocol this campaign has used throughout
  caught it. Don't skip the full run because a quick check looked clean.
