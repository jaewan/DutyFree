# PHASE 1 FINDINGS — hardware-profiling campaign, 2026-08-06

> **CORRECTION (2026-08-07, `e2_h1_speed/PHASE2_E2B_WARMUP_CORRECTION.md`):**
> E2b's small-D "faster than baseline" recovery figure (~0.90-0.905x) is
> retracted as a quiescent-baseline measurement artifact. Corrected: ~0.99x.

One page, per the mission brief. Full detail and raw data throughout
`experiments/phase1/`. Pre-registered predictions and outcomes in
`HYPOTHESES.md` / `OUTCOMES.md`. **See `PHASE2_FINDINGS.md` and
`PHASE2_ADDENDUM.md` for material updates**, including the retraction of
the "~3.55x CXL-path-specific multiplier" below and the decisive
cross-vendor result (H2 does not port to AMD by analogy from Intel).

## G1 verdicts

**E1 (AMD residual mechanism, P1) — RESOLVED.** The 6.92x post-CAT residual
is a **composite**, not one mechanism:
- A2 (CAT): victim LLC occupancy stays ~intact (92% of quiescent); L2 miss
  rate barely moves (+5.6pp) against a 7.2x tax. Rules against
  probe-filter/back-invalidation occupancy collapse (hypothesis a).
- A4 (lookups-only, near-zero memory traffic): substantial 1.25-1.30x tax
  from coherence lookups alone (CI excludes 1.0). Confirms shared
  lookup/queue occupancy (hypothesis b) is real, but this component's
  *magnitude* is modest relative to the full 7.2x residual.
- A6 (thread sweep): superlinear knee between t=2 and t=3 (tax nearly
  triples while bandwidth moves +2%) — a saturating shared resource, not a
  bandwidth-linear effect.
- A1-vs-A5 at matched ~24 GB/s: CXL fills tax 19.89x vs local DRAM's 5.60x —
  a further ~3.55x **CXL-path-specific** component that A4's idle-bandwidth
  traffic does not capture.

**What the gem5 team should build**: model port/queue contention on the
shared lookup/miss path (H3-style type-licensed lookup/enrollment skip) —
H2's allocation-bypass alone would not be expected to remove this residual,
which is now measurement-backed rather than assumed. But **a single
mechanism (e.g. finite-SF-as-probe-filter alone) is unlikely to reproduce
both the lookup-occupancy component (A4, modest magnitude) and the
CXL-path-specific component (A1-vs-A5, large magnitude)** — the model likely
needs both a lookup/enrollment cost on the miss path *and* something
specific to the CXL fill path (elevated occupancy/latency on the home-side
XI/fill queue when the source is the CXL controller, not just "any remote
fill"). See `e1_residual_decomp/RESULTS.md` for the full evidence chain.

**E2 (Intel bandwidth mechanism, P2/P3) — RESOLVED, both confirmed, plus a
correction and a real caveat.** The "~15.8 GB/s single-core WB" figure P2
was pre-registered against turned out to be **AMD's** number, not Intel's
(`Sec2_DirectoryTax.tex:43-53` is one paragraph opening "On AMD..."; no
Intel-specific single-core WB figure exists in the paper). Underneath that
misattribution, a real, still-open hardware question: Intel single-core WB
CXL bandwidth measures ~8.9 GB/s, capped regardless of MSR 0x1A4
prefetcher-bit state or kernel choice, vs ~14.2 GB/s on local DRAM with the
same tools. Root-caused as far as remotely possible: the CXL device
(Montage M88MX5891, swapped in after the paper's Micron-6400-era data) is a
Root Complex Integrated Endpoint with no intermediate switch, negotiating
PCIe x8 instead of its x16 capability — resolving *why* needs BIOS-setup or
physical access not available in this session
(`e2_h1_speed/NEEDS_BIOS_ACCESS.md`, still open).

**But that single-core question turned out not to gate anything**: the
genuine Intel reproduction gate (8-thread aggregate bandwidth and the
2.03x/0.99x tax family in `tab:catmba`) was run in full via the existing
`cat_mba_driver.sh` and **PASSES across all 11 conditions** — baseline tax
(1.946x vs 2.03x), CAT sweep (0.993x vs 0.99x, both way-counts), MBA sweep
(4 points, all within the gate, reproducing the whole rate-throttle curve
including the paper's "never reaches baseline" claim), and both negative
controls. Tax ratios ran a consistent ~4-8% below the paper throughout —
the same pattern as AMD (E1/E4): mechanism reproduces tightly, some
absolute figures drift (`e2_h1_speed/intel_repro_gate_RESULTS.md`).

With that gate passed, **E2b (flush-behind) and E3 (calibration) were both
completed**: P3 (flush-behind at near-full bandwidth returns victim to
~baseline) is confirmed — at D<=2 MiB, tax=0.90x [0.898,0.905], though a
real uncore-frequency confound (1500->2400 MHz when the aggressor is active)
means the exact "faster than quiescent" magnitude isn't purely attributable
to H2; the qualitative conclusion stands regardless. P2 (bandwidth survives
bounding the footprint) is confirmed at small D (within 1.3% of unbounded)
but with a genuine non-monotonic wrinkle — bandwidth dips at 16-64 MiB
before recovering at D=off, from self-contention among the 8 streams' own
larger resident footprints, a second-order effect that doesn't bind at H2's
intended small-D operating point (`e2_h1_speed/e2b_RESULTS.md`).

E3's `calibration_targets.csv` (n=12, 48 config rows) delivers a clean,
textbook-quality prefetch-hint calibration target: T0 and NTA dip below the
no-prefetch baseline at small SW-prefetch distances (insufficient lead time
to hide latency) but then **diverge sharply** — T0 keeps improving with
distance, NTA collapses (consistent with NTA's low-priority/first-evict
semantics: a far-ahead NTA prefetch can be evicted before the demand load
needs it). gem5's prefetch model should not treat T0/NTA as the same curve
with different endpoints. The idle-latency CXL/local ratio (1.95x) closely
matches the paper's own gem5 config table (2.07x) even though absolute
latencies differ (`e3_calibration/RESULTS.md`).

## Anomalies (flagged, not smoothed over)

1. **AMD absolute single-core bandwidth runs systematically ~21-27% below
   the paper's numbers, while every tax/ratio number reproduces almost
   exactly.** E1's A0-A3 gate: within 0.2-4.4%. The matched-bandwidth pair:
   tax within <1% of the paper (1.288x vs 1.28x; 0.9996x vs 1.003x). But
   single-core WB=12.43 (paper 15.8), WC=3.20 (paper 4.2) — on the *same*
   machine, same session. Mechanism/physics is robustly reproducible;
   absolute bandwidth scale is not. Not disambiguated here (candidates:
   unspecified original buffer-size/duration, thermal/background drift on a
   79-day-uptime shared box, or genuine hardware drift).
2. **Fleet-wide CXL device swap, not just the EMR host.** All three
   machines (AMD, EMR, SPR) currently carry the identical Montage
   M88MX5891/Samsung part. The EMR swap (from a Micron 6400) is confirmed
   via a dated cached file; whether AMD/SPR ever had different hardware is
   unknown — this table describes *current* hardware only, not a backfill
   for old datasets (`e4_hygiene/PLATFORMS.md`).
3. **AMD's l3_lookup_state/l3_xi_sampled_latency perf events are CCX-wide
   uncore counters, not victim-scoped** — confirmed empirically (A1 and A2
   show near-identical multi-billion miss counts matching the *aggressor's*
   fill volume, not anything victim-specific). Cannot isolate victim-only L3
   behavior in a same-CCX layout with these counters. No probe-filter/
   back-invalidation-specific event exists in this platform's perf list
   either; the one reachable AMD PPR page didn't yield the full PDF (no
   download tooling in this sandbox).
4. **A6 non-monotonicity**: tax *decreases* slightly from t=5 (21.82x) to
   t=7 (20.01x) even as bandwidth ticks up — CIs don't overlap, so it's real,
   not noise. Left unexplained (self-contention among aggressor threads?
   scheduling effect at 7-of-8 CCX cores occupied?).
5. **Multi-domain MBM summing is unreliable on the AMD box**: summing
   `mbm_total_bytes` across several simultaneous CCX domains for one RMID
   under-reports by roughly half, or intermittently reads "Unavailable" —
   reproduced independently in two different experiments. Platform/kernel
   limitation, not a script bug; self-reported aggregate bandwidth used as
   the trusted metric wherever this occurred.
6. **A kernel CXL bandwidth-QoS `WARN_ON` at EMR boot** (`drivers/cxl/core/
   port.c`, `to_cxl_port`), correlating with `qos_class_mismatch: true` on
   the CXL region — a real kernel driver defect, but no plausible mechanism
   ties a QoS-*classification* bug to the observed ~40% single-core
   bandwidth gap, so reported separately rather than as the explanation.
7. **The AMD headline numbers' original raw dataset no longer exists** on
   any machine (`H3_GATE_RESULT.md`'s cited `/tmp/task1_raw.jsonl` is gone;
   a rougher n=3 precursor survives with numbers in the same ballpark). This
   campaign's E1 gate is a fresh measurement, not a check against the
   original file.
8. **This EMR host's governor/turbo was `powersave`/turbo-on at session
   start**, contradicting the paper's stated methodology. Fixed with user
   confirmation; prior state saved (`e4_hygiene/emr_prior_power_state.txt`)
   for restoration.
9. **Uncore frequency scales with socket utilization independent of core
   P-states** (1500 MHz quiescent -> 2400 MHz with an 8-thread aggressor
   active, confirmed via `turbostat`, core frequency pinned at 1.9 GHz
   throughout via `performance`/turbo-off). This means any co-run-vs-
   quiescent comparison on this platform has a built-in confound unless
   corrected for — found while investigating why E2b's flush-behind arms
   measured *faster than quiescent*, not fabricated after the fact.
10. **Flush-behind bandwidth-vs-D is non-monotonic**: high at small D
    (32-256 KiB), dips at 16-64 MiB, recovers at D=off. Real (n=12, tight
    CIs), attributed to a combination of per-flush instruction overhead
    (present at any D>0, roughly D-independent) and self-contention among
    the 8 aggressor threads' own larger resident footprints at large D —
    not disambiguated further between those two contributions.
11. **SW-prefetch bandwidth dips below the no-prefetch baseline at very
    small distances** (d=1-8 lines) for both T0 and NTA hints, before T0
    recovers and NTA collapses at large distances. The small-distance dip
    is consistent with insufficient lead time to hide round-trip latency —
    the prefetch adds issue overhead without buying real latency-hiding at
    that range.

## What's done vs. open

Done, committed, n>=12 throughout: E1 (A0-A6, full mechanism verdict), E2
(full 11-condition repro gate, flush-behind P2/P3, calibration_targets.csv),
E4 (PLATFORMS.md, AMD WC/WB reconciliation, matched-bandwidth pair). Open:
the EMR CXL link's x8-vs-x16 question (needs BIOS/physical access, tracked
in `e2_h1_speed/NEEDS_BIOS_ACCESS.md`); the systematic AMD/Intel absolute-
bandwidth gap (anomaly 1) isn't explained; SPR per-core WC reconciliation
was not attempted (this campaign scoped AMD/EMR work as higher-value given
time). EMR governor/turbo and hugepage reservations remain in the
"frozen for measurement" state set this session — `e4_hygiene/
emr_prior_power_state.txt` has what to restore when Phase 1 fully closes
out.
