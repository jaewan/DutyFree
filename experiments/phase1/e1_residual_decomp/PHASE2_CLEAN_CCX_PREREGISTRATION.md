# Pre-registration: clean-CCX co-measured session

Dated 2026-08-09, before running. Per panel direction, following the
CCX0-outlier discovery (`PHASE2_AMD_WARMUP_CHECK.md`): a single co-measured
session, on one representative clean CCX (CCX1, `cpus 8-15`), covering WB,
CAT, flush-behind best-D (256 KiB), WC, and the 2T/3T concurrency-knee
points — closing the "lower urgency" cross-CCX item for the non-CAT arms,
resolving the convergent-floor table's epoch/CCX mixing (CAT's leg is
now new-epoch/all-CCX; flush-behind and 2T are still old-epoch/CCX0-only),
and producing the numbers gem5's validation contract actually needs.

## Why this matters beyond hygiene

The corrected cross-CCX table showed something specific: the CAT-protected
*residual* is chip-wide invariant (9.66-10.03x) while the *uncontended*
WB endpoint is not (13.3-13.7x on CCX1-3 vs 20.8x on CCX0). If this
decomposition — invariant floor, placement-dependent ceiling — holds for
the *other* control mechanisms too (flush-behind, the concurrency knee),
that is direct, measured evidence for the paper's central claim: what a
control mechanism cannot remove is structural and chip-wide; what it can
remove is contingent on where you happen to be measuring.

## Predictions (falsifiable, stated before running)

1. **Flush-behind (256 KiB) converges to the same ~9.9x invariant band on
   CCX1 that CAT converges to everywhere** — i.e., flush-behind and CAT
   are in the same "large, un-partitionable/un-boundable residual"
   equivalence class, and flush-behind's originally-reported 5.94x
   (old epoch, CCX0-only) was itself sitting on the CCX0-anomalous WB
   ceiling, not below the true invariant floor. **Falsified if**
   flush-behind on CCX1 lands meaningfully below ~9x (i.e., if residency
   bounding genuinely removes something way-masking cannot, making the
   "single un-partitionable floor" story wrong and requiring a
   mechanism-specific decomposition instead of one shared invariant).
2. **WC stays at parity (≈1.0x) on CCX1**, matching its CCX0 result and
   its already-adversarially-confirmed status. **Falsified if** WC shows
   any material tax on CCX1 — would mean WC's parity was itself partly a
   CCX0 property, which would be a serious, separate finding.
3. **The A6 2-thread/3-thread concurrency knee replicates on CCX1, with
   the WB ceiling at ~13.4x (CCX1's own uncontended endpoint) rather than
   CCX0's ~20.8x** — i.e., the knee's *existence* and *shape* (2T capturing
   ~98% of 3T's bandwidth) is a chip-wide property, but its *absolute
   tax scale* tracks whichever CCX's WB ceiling applies, exactly like CAT
   and (per prediction 1) flush-behind. **Falsified if** the knee's shape
   itself changes on CCX1 (e.g., 2T no longer captures ~98% of 3T's
   bandwidth), which would mean the concurrency-cap mechanism is also
   CCX0-contingent, not just its absolute scale.

## Method

One session, one CCX (CCX1, `victim=cpu8`, `aggressors=cpus 9-15`),
n=12 per arm, rep-interleaved where the existing per-arm scripts support
it: quiescent, WB (no CAT), WB+CAT (8/8 way split), flush-behind@256KiB,
WC, A6-style 2-thread and 3-thread concurrency points. Bandwidth
(self-report + MBM) and occupancy captured per arm, matching the
convention `check_ccx_comparison_v2.py` and `run_p24_amd_flushbehind.py`
already use. MSR verification (`IA32_PQR_ASSOC`/`IA32_L3_QOS_MASK_n` on
the actual CCX1 cores) performed once per CAT-using arm, per the lesson
from the domain-index bug.

## What happens after

- All three predictions confirmed: floor table gets a single clean-epoch,
  clean-CCX row set; the epoch/CCX mixing problem is resolved in one
  shot; gem5's validation contract gets its numbers from one coherent
  session rather than three different sessions/CCXes.
- Any prediction falsified: written up as its own finding, same
  discipline as the CCX0 discovery itself — investigated before being
  trusted, not forced to fit the invariant-floor story just because it
  would be convenient.
