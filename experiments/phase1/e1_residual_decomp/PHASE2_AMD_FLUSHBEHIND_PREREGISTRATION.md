# Pre-registration: AMD flush-behind (Phase 2.4)

Dated 2026-08-07, before any AMD flush-behind run. Per the panel's
instruction: pre-register both models' predictions before running, since
either outcome is publishable but running it after committing to a model in
the paper text is not.

## The two models

**Occupancy model** (this session's E1 finding: the binding resource is the
CCX's shared coherent-transaction machinery -- L3/XI request-entry
occupancy, not LLC data-array capacity). An H2-style non-allocating fill is
still a coherent read: it enters the same lookup/transaction pool and holds
an entry for the same CXL-latency duration as an allocating fill: it merely
declines to install into the data array at completion. Flush-behind (which
emulates non-allocation via post-hoc `clflushopt` eviction of the *data
array* entry) does nothing to shorten how long the *transaction-pool* entry
is held while the fill is in flight -- that duration is set by CXL latency
and pool depth, not by what happens to the line afterward.

**Prediction under the occupancy model: WEAK recovery. Residual tax >=5x
at small flush distance D**, on the same same-CCX victim/aggressor
placement as A0-A6 (victim cpu0, aggressor cpus1-7, CXL node2). Should look
qualitatively like A2 (CAT recovers 69%, residual 7.2x) or worse, not like
Intel's E2b result (tax -> ~0.90-1.0x at small D) -- because CAT and
flush-behind both leave the transaction-pool machinery untouched; neither
should differ much from the other under this model.

**Capacity model** (the naive cross-vendor H2-portability assumption --
stated for completeness, though this session's own E1 data already argues
against it via CAT-immunity, A4's real lookups-only tax, and A6's
superlinear knee). If the residual were actually LLC-capacity-driven,
bounding the *resident footprint* via flush-behind should recover the
victim much like it does on Intel.

**Prediction under the capacity model: STRONG recovery. Tax -> ~0.9-1.0x
at small D**, similar in shape to Intel's E2b curve.

## What decides between them

Sweep D in the same range as Intel's E2b ({32 KiB, 256 KiB, 2 MiB, 16 MiB,
64 MiB, off}) with the AMD flush-behind streamer (`amd_flushbehind_aggressor.c`,
extends `lookups_aggressor.c`'s buffer-allocation conventions with a
`clflushopt`-at-distance-D kernel per thread, mirroring
`stream_wb_flushbehind.c`'s design on the Intel side), 7 threads on cpus1-7,
same victim as A0-A6. n>=12, rep-interleaved, same statistical protocol as
every other arm this campaign.

- If tax at D<=256 KiB lands near or above 5x (occupancy model): H2 does
  NOT port to AMD by analogy from Intel; the AMD-analog gem5 model needs a
  transaction-pool/queue mechanism, and non-allocation alone will not
  recover this residual on AMD hardware.
- If tax at D<=256 KiB collapses toward ~1.0x (capacity model): the A1-vs-A5
  CXL-path-specific multiplier and A4's lookup-only tax would need
  reinterpretation -- occupancy of *something* still matters (A4's tax is
  real), but it would mean flush-behind's mechanism (bounding residency) is
  sufficient to relieve it, contrary to this session's own composite-
  mechanism conclusion in `e1_residual_decomp/RESULTS.md`. That would be a
  major revision to Phase 1's headline finding, not a footnote -- worth
  running exactly because of how much it would overturn if it happened.

This file is written before the first AMD flush-behind measurement of any
kind. Outcomes go in a separate file, not edited into this one, per the
same discipline as `HYPOTHESES.md`/`OUTCOMES.md`.
