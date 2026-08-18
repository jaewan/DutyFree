# #28 — the predictor head-to-head, run. The predictor matches on capacity; the difference is admission.

Written 2026-08-18. #28 was named by both review panels as the single most
likely rejection reason and had never been run. It is now run, and the result
is the one the charter pre-committed to reporting honestly.

## Feasibility, corrected

`TASK28_DESIGN_MEMO_2026-08-15.md` said SHiP was in-tree and "config-level,
hours not days." The first half is right; the second was wrong.

**SHiP cannot be attached to a Ruby cache without porting gem5 core.**
`ship_rp.cc:141` panics with *"Cant train SHiP's predictor without access
information"*: SHiP derives its signature from a `PacketPtr`, while Ruby's
`CacheMemory` calls the **packet-less** `reset()`/`touch()` overloads
(`CacheMemory.cc:326` and the touch sites). Both packet-less hooks panic. This
is an interface mismatch, not a configuration gap, and it is presumably why no
prior gem5+CHI study reports this comparison.

A faithful port is possible for **SHiPMem** specifically — its signature is
defined as `addr % SHCT.size()`, and Ruby has the address, so no approximation
is needed (SHiPPC would need a PC Ruby cannot supply). Ruby already has
precedent for the shape: `CacheMemory::setMRU` static_casts `WeightedLRU` to
reach a policy-specific `touch()`. It spans ~6 call sites in core gem5.
**Not done here** — a self-ported predictor invites fidelity questions on a
paper whose credibility is its principal asset, and a measured in-tree
alternative exists.

**Measured predictor: BRRIP** (bimodal RRIP) — in-tree, works under Ruby, and
literally the "tuned RRIP" the paper's own placeholder names
(`Sec5_Evaluation.tex:259`). Hawkeye and Mockingjay remain absent from the tree
and are argued, not measured.

## The arms

Single-core bandwidth-survival probe (`h1bw_stream`, 16 MiB stream > 5 MiB
LLC), the same harness and config as `tab:h1bw`: `num-cpus=1`,
`l3_size=5MiB`/20-way, `--maxinsts=20000000`, `ALL_CXL=1`,
`HNF_SF_FINITE=0 HNF_H3=0 HNF_DMT=0`. gem5 `0f37c28` (adds the `HNF_RP` knob;
defaults preserved). LLC policy verified from `config.json` per arm.

`simInsts` is identical across all six arms (14,621,894 vs 14,621,818, a
0.0005% spread), so cycles are directly comparable — the work-normalised metric
established in `GATE1_H1BW_ANOMALY_RESOLVED_2026-08-18.md`.

| L1_MSHR | arm | cycles | memory read | **HNF fills** | L3 hit% |
|---:|---|---:|---:|---:|---:|
| 16 | WB + TreePLRU | 31,284,372 | 52.0 MB | 812,465 | 0.1% |
| 16 | WB + BRRIP | **25,047,407** | 36.2 MB | **584,189** | 27.7% |
| 16 | H2 (declared) | 25,259,240 | 36.3 MB | **32,814** | 26.6% |
| 48 | WB + TreePLRU | 19,234,071 | 52.0 MB | 812,457 | 0.7% |
| 48 | WB + BRRIP | **17,139,348** | 36.2 MB | **584,327** | 27.6% |
| 48 | H2 (declared) | 17,442,433 | 36.8 MB | **55,245** | 33.6% |

## What it says

**1. The predictor matches the declaration on everything the paper measured.**
BRRIP is 0.8% faster than H2 at 16 MSHRs and 1.7% faster at 48, with
indistinguishable memory traffic (36.2 vs 36.3 MB) and an equivalent LLC hit
rate. Both recover the same ~20% of cycles that TreePLRU loses to stream
thrash. **Report this. It is not a defeat** — it is the comparison the paper was
asserting instead of running, and asserting it was the rejection risk.

**2. The difference is admission, and it is structural.** BRRIP reaches that
result while still writing **584k lines into the L3 data array against H2's
33k — 17.8x more**. A replacement policy acts *after* admission by
construction: it can decline to *retain* a line but cannot decline to *write*
it. Every stream line still costs a tag update, a data-array write, and the
fill bandwidth to perform it. H2 declines the write. No amount of predictor
tuning closes that gap, because it is not a prediction-accuracy problem.

**3. The two claims a predictor still cannot make** are untouched by this
result and are what H3 rests on:
   - **No guarantee.** A co-runner cannot size its working set against a
     predictor's future behaviour. Not measured here — this probe is
     single-core, so the guarantee axis remains an argument, correctly.
   - **No coherence exemption.** A reuse predictor observes that a line was not
     re-*read*; coherence tracks *writes*. No load-side observation can license
     skipping a structure that exists to find writers. Only a declaration can.
     This is categorical and unrunnable, which is why #29's model-checking is
     the right evidence for it.

## Honest limits

- One predictor, in one regime, on one core. BRRIP is a competent thrash-resistant
  policy but is weaker than SHiP/Hawkeye/Mockingjay by design; a signature- or
  OPT-based predictor might beat H2 on cycles rather than tie it. **That would
  not change conclusion 2**, which is about admission, not accuracy.
- The fill-count gap is an energy/bandwidth argument this paper does not price
  in joules. It is reported as a count, not converted.
- Single runs, no interval — the same variance gap that applies to every gem5
  number here.

## Consequence for the paper

Two printed placeholders can now be replaced with a measured result:
`Sec3_5_DeclarationVsPrediction.tex:65` and `Sec5_Evaluation.tex:259`. The
honest headline is **not** "declaration beats prediction on capacity" — it is
"a tuned predictor matches it on capacity, and the separation is admission
cost, the guarantee, and the coherence exemption." That is a stronger paper
than the assertion it replaces, and it is defensible under questioning.
