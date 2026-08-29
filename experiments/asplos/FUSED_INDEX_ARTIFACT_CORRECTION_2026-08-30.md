# Correction: the fused-tenant results of 2026-08-29 were distorted by a power-of-two probe stride. Superseding numbers here.

**This document supersedes the numeric results of
`H2H_FUSED_OUTCOME_2026-08-29.md` and `FUSED_TABLESWEEP_OUTCOME_2026-08-29.md`.**
Their qualitative conclusions mostly survive; their magnitudes do not. Nothing
from either reached the paper --- the drafted paragraph was never applied --- so the
correction is confined to the record.

## The defect

`fused.c`'s probe index was `idx = (arr[i] * K) & (Tp - 1)`, using the **low**
bits of a multiply, which are badly mixed. With `arr[i] = i` and the loop
stepping by `UNROLL = 16`, consecutive probes landed a constant **64 elements =
512 bytes** apart --- a power-of-two stride.

In the 2 MiB/16-way L2 (2048 sets), a 512 B stride advances the set index by 8
every probe, so the sequence visits **only every 8th set**. The table saw **1/8
of the cache** and behaved like a table eight times larger. The same aliasing
applies at the 4096-set HNF.

This is the **fifth** power-of-two pathology in this campaign, after `--hot-bytes`
quantization, `CacheMemory`'s `floorLog2` set truncation, `TreePLRURP`'s
non-power-of-two bias, and this workload's own table-size rounding. Fixed
(`fused.c`, multiply-shift reduction): stride is now ~312 B, indices spread over
all sets, and probe distribution is uniform to 3.3% across 16 bins.

## How wrong the old numbers were

| quantity | as published 2026-08-29 | corrected |
|---|--:|--:|
| partitioning's tenant charge, 2 MB table | **+36.53%** | **+15.84%** |
| H2 recovery, 4 MB table | **51.92%** | **82.33%** |
| H2 recovery, 8 MB table | **27.95%** | **56.84%** |

## The corrected curve (7 points, realized sizes, n=3)

| table | `wb` tax | **h2 R%** | **cat4 R%** | h2 cost | cat4 cost | wedge |
|---|--:|--:|--:|--:|--:|--:|
| 2.0 MB | 1.4679 | 89.44 | 89.26 | -4.14% | +15.84% | 20.0 pp |
| 2.5 MB | 1.5012 | 87.69 | 88.19 | -7.07% | +23.54% | 30.6 pp |
| 3.0 MB | 1.5141 | 84.51 | 87.79 | -11.92% | +23.17% | 35.1 pp |
| 3.5 MB | 1.5186 | 81.95 | 87.45 | -12.03% | +24.22% | 36.2 pp |
| 4.0 MB | 1.5100 | 82.33 | 87.26 | -7.81% | +19.28% | 27.1 pp |
| 6.0 MB | 1.5223 | 67.14 | 86.25 | -11.38% | +18.95% | 30.3 pp |
| 8.0 MB | 1.5477 | 56.84 | 86.31 | -10.42% | +22.09% | 32.5 pp |

## What survives, what changes

**Survives --- the wedge, and it is now broader than the point estimate claimed.**
Partitioning charges the tenant **15.8--24.2%** across every table size; H2
charges nothing anywhere (it *gains* 4--12%). The wedge is **20--36 pp at every
point on the curve**, not at one configuration.

**Survives, softened --- H2's protection declines with the tenant's own footprint.**
89.4% -> 56.8% from a 2 MB to an 8 MB table, while partitioning holds a flat
86--89%. The direction and the mechanism (H2 removes only the *stream's* harm;
what remains is the tenant's own resident set, which M5 established is not the
mechanism's to remove) stand. **The word "collapses" does not.** In neighbour
slowdown at 8 MB: unprotected 1.55x, **H2 1.24x**, partitioning 1.07x --- H2 still
recovers more than half.

**Changes --- the headline magnitude.** "Partitioning charges 36.5%" becomes
**15.8%** at the same table size. Notably the corrected range, 15.8--24.2%, sits
much closer to silicon's **15.0--16.9%** (E1, E4) than the artifact did. The
model and the machine agree better after the fix than before it, which is weak
evidence the fix is right.

## The registered prediction it was meant to test, refuted

`FUSED_KNEE_PREREG_2026-08-29.md` registered the **whole-table** model:
`R(h2)` < 80% at a 2.5 MB table, on the reasoning that the stream evicts the
table from L2 continuously so the entire table competes for the LLC.

**Measured: 87.69%.** Above the 85% refutation threshold. **The whole-table
account is refuted and is withdrawn**, along with the sentence in
`FUSED_TABLESWEEP_PREREG_2026-08-29.md` that first asserted it. The decline is
gradual across 2--8 MB with no sharp knee at either candidate location, so the
question the experiment posed --- *where* is the knee --- was itself malformed:
there isn't one.

## Provenance

Corrected runs: `/tmp/kn_*` (2.0--4.0 MB) and `/tmp/kb_*` (6.0, 8.0 MB), 63 runs,
all reaching `Exiting @ tick`, each carrying its realized table size in its own
log. Superseded runs used the aliased index and are not comparable to these.
