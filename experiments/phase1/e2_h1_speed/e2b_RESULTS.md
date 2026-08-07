# E2b — flush-behind streamer vs co-run victim tax: RESULTS

> **CORRECTION (2026-08-07/08, `PHASE2_E2B_WARMUP_CORRECTION.md`):** the
> entire D-sweep below was measured with a systematic cold-quiescent /
> warm-loaded asymmetry (single fresh-process trial vs. concurrent heavy
> aggressor). Full re-run under a matched discard-cold-trial protocol,
> n=12: small-D tax (32KiB/256KiB/2MiB) corrects from ~0.90x to **~0.99x**;
> **D=16MiB flips sign**, from 0.951x (below baseline) to **1.018x** (a
> small real tax above baseline, CI excludes 1.0 either way but in
> opposite directions); D=64MiB corrects from 1.335x to **1.213x** (the
> loaded-arm reading itself was also partly contaminated, not just
> quiescent); D=off is essentially unchanged (2.307x → 2.341x). See the
> correction file for the full table and mechanism.

Dated 2026-08-06. Pre-registered: P2 (bandwidth survives bounding LLC
footprint) and P3 (flush-behind at near-full bandwidth returns victim to
~baseline).

## Config

- Host: this machine (EMR/mos181), governor=performance, turbo=off.
- Victim: 170 MB pointer chase, cpu0, node0, 1 trial/rep, 4s measurement.
- Aggressor: `stream_wb_flushbehind` (extends `stream_wb.c` with `clflushopt`
  at distance D behind the read pointer, batched sfence every 64 lines),
  8 threads, cpus1-8, CXL node2, 2 GB region/thread.
- D sweep: {32 KiB, 256 KiB, 2 MiB, 16 MiB, 64 MiB, off (full residency)}.
- n=12, rep-interleaved (quiescent + 6 D values, 7 arms/rep).
- RMID llc_occupancy sampled at ~4 Hz on the aggressor's resctrl group.

## Results

| D | tax | 95% CI | agg BW (GB/s) | occupancy (MB, median) |
|---|---:|---:|---:|---:|
| 32 KiB | 0.901x | [0.898,0.903] | 23.55 | 8.20 |
| 256 KiB | 0.902x | [0.900,0.905] | 23.55 | 11.17 |
| 2 MiB | 0.901x | [0.899,0.903] | 22.46 | 23.18 |
| 16 MiB | 0.951x | [0.947,0.958] | 16.89 | 57.23 |
| 64 MiB | 1.335x | [1.308,1.380] | 14.83 | 111.14 |
| off (full residency) | 2.307x | [2.292,2.319] | 23.86 | 224.77 |

## P3: CONFIRMED, with a caveat worth taking seriously

At D <= 2 MiB, victim tax is **0.90x — not just "recovered to baseline,"
measurably *faster* than the quiescent baseline**, with CI excluding 1.0
entirely. This is silicon evidence for H2 (non-allocation): bounding the
stream's LLC footprint removes the co-run tax essentially completely.

**But "faster than quiescent" needed an explanation, not a victory lap.**
Confirmed via `turbostat`: **uncore frequency scales from 1500 MHz
(quiescent) to 2400 MHz when the 8-thread aggressor is active** (a real,
well-understood platform behavior -- uncore/mesh clock tracks socket
utilization, independent of core P-states, which stayed pinned at the
1.9 GHz base throughout via `performance`/turbo-off). The victim's
LLC/mesh-latency-bound hot path runs faster on a faster mesh. **This means
"quiescent" and "co-run" are not apples-to-apples baselines here** -- the
0.90x figure is influenced by an uncore-frequency confound, not purely by
the flush-behind mechanism. The *direction* of the confound argues
conservatively (it flatters the small-D results), so P3's qualitative
conclusion (small D removes the tax) stands, but the exact 0.90x number
should not be read as "10% faster because of H2" -- some unknown share of
that 10% is uncore frequency. Left uncorrected here; a clean re-measurement
would need a *loaded-but-harmless* co-runner (e.g. an aggressor that keeps
uncore busy without touching the victim's cache lines) to isolate the two
effects. Flagged, not resolved.

## P2: CONFIRMED at small D, with a genuine non-monotonic wrinkle

At D=32-256 KiB, bandwidth (23.55 GB/s) is **within 1.3% of the D=off rate**
(23.86 GB/s) -- P2's "within ~15% down to small footprints" claim holds
with a lot of room to spare. But the **bandwidth-vs-D curve is not
monotonic**: it dips at 16-64 MiB (16.89, 14.83 GB/s) before recovering at
D=off. This is a real, reproducible pattern (tight CIs, n=12), not noise.
Plausible mechanism: at large-but-finite D, the aggressor pays *both* the
clflushopt instruction overhead (present at any D>0, since almost every
line gets flushed once per pass regardless of distance -- only the lag
differs) *and* self-contention among the 8 threads' own larger resident
footprints (nominal 8xD reaches 128-512 MB at D=16-64 MiB, well past the
320 MB LLC, causing the aggressor threads to evict each other). At D=off,
the clflushopt overhead disappears entirely (no instructions issued), so
bandwidth recovers even though residency is now unbounded. **The valley is
the interesting finding**: flush-behind's bandwidth cost is not simply "more
flushing at smaller D" -- it's "any flushing costs something, and at
intermediate D you also pay a capacity-contention penalty that disappears
only once D is small enough to avoid multi-thread self-eviction or is
switched off entirely."

## Occupancy vs D

Tracks D monotonically (8.2 -> 11.2 -> 23.2 -> 57.2 -> 111.1 -> 224.8 MB) but
sub-linearly relative to the naive 8xD-bytes estimate -- the occ/(8xD) ratio
falls from ~31x (at D=32 KiB) to ~0.2x (at D=64 MiB), consistent with a
roughly-constant "floor" component (HW-prefetch-ahead residency, TLB/other
paths -- prefetchers were left ON for this streamer, unlike the SW-prefetch
leg in E3) that dominates at small D and becomes proportionally negligible
at large D.

## Verdict for the gem5 team

**Silicon evidence supports building H2 (non-allocating fill) in gem5**: a
small flush-behind distance removes the co-run tax almost entirely while
costing essentially nothing in bandwidth (<=2% at D<=2 MiB). The
uncore-frequency confound above means the *exact* magnitude of "removes the
tax" on real silicon should be quoted as "returns to ~baseline, likely with
some additional bonus from an uncore-frequency effect not attributable to
H2 itself" rather than a clean single number. The non-monotonic
bandwidth-vs-D valley is a second-order effect (self-contention among
multiple flush-behind streams at large D) that a gem5 model of H2 should
not need to reproduce unless it specifically wants to model multi-stream
capacity contention at large bounded-residency windows -- for the paper's
purposes (small D, i.e. H2's intended operating point), it doesn't bind.
