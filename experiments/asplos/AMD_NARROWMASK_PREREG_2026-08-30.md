# Pre-registration: can way partitioning reach the AMD residual when the mask is *aimed*?

Registered **before** the run. `broker` (moscxl) returned 2026-08-30 after nine
days down.

## The claim under test

`tab:amdcat` is captioned **"Real-hardware AMD refutation of way-partitioning"**
and rests on a **9.87x** residual surviving CAT. But that CAT arm is an
**8/8 split** --- the aggressor was given **half** of the L3's 16 ways. On Intel,
`E1` found partitioning protects fully at *every* split; if AMD's failure is
simply that the mask was not aimed, the caption claims something the data does
not support.

The paper already discloses two weaknesses in this row: the CAT arm is
**unstable** (7.23x on 2026-08-01, 9.87x on 2026-08-08, "physical cause
unidentified"), and per `AMD_PLATFORM_STATE_PROVENANCE_2026-08-21.md` the host's
governor/turbo/hugepage state was **never frozen or recorded** for those runs.
**A third weakness --- that the mask was never narrowed --- would be ours to find,
not a referee's.**

## Apparatus --- the campaign's own, unchanged

The original tree survived the rebuild: `/home/domin/tmp_dutyfree_exp/bin`,
`victim` and `aggressor` both dated 2026-08-23. **These are the binaries that
produced the published numbers**, not rebuilds, so the comparison is not
confounded by a recompile.

- CCX0: **victim on core 0, aggressor 7 threads on cores 1--7** --- same L3 domain,
  16 MiB, **16 CAT ways** (`cbm_mask=ffff`), 16 CLOSIDs, 32 L3 domains on the box.
- victim `-w 4096 -P -d 5 -W 2` (4 MB working set); aggressor
  `-m wb_load -t 7 -N 2 -s 64` (CXL node 2).
- Arm order **rotated per rep** so drift cannot align with one arm.

**Platform: as-found, with `perf_event_paranoid` lowered to -1 only** --- the
victim cannot open its PMU counters otherwise. Governor stays `schedutil` and
boost stays on, i.e. the same unfrozen state the published runs used. Freezing
would improve the measurement but change it relative to the number being
reproduced; the frozen arm is a separate follow-on, not this experiment.

## Arms: the mask is the variable

| arm | victim mask | aggressor mask | aggressor ways |
|---|---|---|--:|
| `quiescent` | `ffff` | `ffff` | --- |
| `wb` | `ffff` | `ffff` | 16 (unpartitioned) |
| `cat8` | `ff00` | `00ff` | 8 (**the published split**) |
| `cat4` | `fff0` | `000f` | 4 |
| `cat2` | `fffc` | `0003` | 2 |
| `cat1` | `fffe` | `0001` | **1** |

n=6. Masks are **read back from `schemata` on every run** and recorded per
record: an arm whose mask did not take is not an arm.

## Registered decision rule

Let `tax(arm) = cyc_per_access(arm) / cyc_per_access(quiescent)` and
`removed(arm) = (tax(wb) - tax(arm)) / (tax(wb) - 1)`.

**P1 --- the test.** On the tightest mask, `cat1`:

- `removed(cat1)` >= **80%** -> **way partitioning CAN reach this harm when
  aimed.** `tab:amdcat`'s caption is then an aiming artifact and must be
  restated: the honest claim becomes "an 8/8 split leaves a large residual",
  which is a much weaker statement and is *not* a refutation of way
  partitioning.
- `removed(cat1)` <= **50%** -> **the refutation survives even at one way**, and
  the caption is safe. This is the outcome that helps the paper.
- 50--80% -> partial; report the curve and restate the caption quantitatively.

**P2 --- monotonicity as an enforcement check.** `tax` must not *increase* as the
aggressor's mask narrows: `tax(cat8) >= tax(cat4) >= tax(cat2) >= tax(cat1)`
within noise. A non-monotone curve means the mask is not doing what the schemata
say, and the run is diagnostic rather than conclusive.

**P3 --- reproduction, reported but not gating.** `tax(wb)` against the published
19.89x / 20.55x. A single unfrozen smoke rep today read **28.05x**, so a miss is
expected and is a *provenance* finding, not a void: it would show the published
AMD magnitudes are not reproducible on the rebuilt host under the same unfrozen
conditions. The mask comparison is internal to this batch and stands regardless.

## Why no prediction on P1

I am not registering which way P1 goes. The Intel evidence (E1: partitioning
protects fully at every split) points one way; AMD's harm being **rate-class
rather than capacity-class** (E3) points the other, and a rate-class harm is
exactly what a capacity mask should fail to reach at *any* width. Both arguments
are good and they disagree. **This is the case where a registered guess would be
rationalisable whichever way it landed.**

## Liveness assertions

1. Every record carries its mask read back from `schemata`; a mismatch voids that
   record, it is not silently kept.
2. `quiescent` must show no aggressor bandwidth; `wb` must show ~24 GB/s (the
   published write-back rate is 24.1).
3. The aggressor must sustain comparable bandwidth in every CAT arm --- a mask
   that throttles the aggressor's *rate* rather than its *residency* would remove
   harm for the wrong reason, and the published CAT arm ran at 99.8% of
   write-back's bandwidth. **Bandwidth per arm is recorded so this is checkable.**
4. No `-R` throttle anywhere: it carries a known confound and is not used.
