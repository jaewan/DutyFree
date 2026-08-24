# T2 pre-registration: the single-core WB vs "WC" bandwidth pair

Written **before any measurement**, per §6.6. Registers the arms, the metric,
the readings, and the falsifier. Nothing below may be revised after data lands
except by a dated addendum.

## 1. Why

The paper's introduction motivates the whole mechanism with a single-core
bandwidth contrast — approximately **15.8 GB/s (WB) vs 4.2 GB/s (WC)** — and a
derived "five WC cores to match two WB cores" claim. Neither number is in this
repository (`REVIEWER_STATE_2026-08-24.md` §A6): "15.8" appears nowhere, and
"4.17 GB/s" exists but is our **WB** pure-stream figure in the *gem5 SE model*,
not a silicon WC figure. The pair is therefore N7-class and on the W4.2 repair
list. It is also cheap to earn honestly: a single-core microbenchmark on
hardware we have.

## 2. The apparatus defect this must also fix

`benchmarks/bench/aggressor/` already implements the arms. Reading it first
(rather than writing a new benchmark) surfaced a defect that changes what the
paper may say, independent of any number:

- `stream_wc.c` is **MOVNTDQA on write-back pages**, and its own header says so:
  *"We implement the MOVNTDQA-on-WB approach here and note the limitation."*
  It does **not** set the WC memory type, and it does **not** disable the
  hardware prefetcher.
- `stream_nt.c` is the **same program**. Diffed with names normalised, the only
  functional difference is that `stream_nt` *reads* MSR 0x1A4 and warns if the
  prefetchers are off. The inner loops are identical.
- Consequently `stream_nt.c`'s own pre-registered reading — *"If D ≈ A: NT hint
  ignored → H4 supported. If D ≈ C: NT hint honored → H4 rejected"* — is
  **circular**: D ≈ C holds by construction. That test can neither support nor
  reject H4.

So the arm the paper calls "WC" is *MOVNTDQA-on-WB with prefetchers enabled*.
The intro's story — "WC declines the allocation and forfeits the prefetching" —
is **not what was measured.** Fixing the label is the primary deliverable here;
the number is secondary.

## 3. Arms

All arms: one pinned core, local-DRAM node, 2 GB region (exceeds every LLC on
these hosts, including EMR's 320 MB), hugepage-backed, identical inner-loop
structure per arm family.

| arm | binary | pages | loads | HW prefetch | what it is |
|---|---|---|---|---|---|
| **A** | `stream_wb` | WB | regular | **ON** | the honest "WB" number |
| **B** | `stream_wb_nopf` | WB | regular | **OFF** (MSR 0x1A4=0xF, verified) | isolates prefetch's contribution to WB |
| **C** | `stream_wc` | WB | MOVNTDQA | **ON** | *the paper's current "WC" arm, unmodified* |
| **D** | `stream_nt` | WB | MOVNTDQA | **ON** | run to demonstrate C≡D by measurement |
| **C'** | `stream_wc_nopf` | WB | MOVNTDQA | **OFF** | **NEW.** The honest proxy for WC: no allocation *and* no prefetch |
| **E** | `stream_sw_prefetch` | WB | regular + SW PF | ON | advisory-mechanism datapoint |

**C' is additive.** No existing arm is edited — the apparatus rule is preserved,
and A/B/C/D/E stay byte-identical to what produced every published number.

**True WC is still not measured.** It needs PAT manipulation from the kernel.
C' is a documented proxy and will be labelled a proxy wherever it appears. This
pre-registration does not claim otherwise.

## 4. Hosts

mos181 (local, Xeon 8592+ EMR, 320 MB LLC), mos182 (`ssh c4`, Xeon 8462Y+ SPR,
60 MB), moscxl (`ssh broker`, EPYC 9754 Bergamo, 16 MB/CCX). Run in parallel.

**MSR 0x1A4 is Intel-specific.** On moscxl, arms B and C' are expected to fail.
`msr_pf_disable` read-back-verifies and `exit(1)`s on mismatch, so a failure is
loud. **If the write instead appears to succeed on AMD, that is an F12 risk, not
a result**: registered cross-check — if B ≈ A on moscxl while B ≪ A on both
Intel hosts, the AMD prefetch-disable did not take effect and arms B/C' must be
reported **UNAVAILABLE on AMD**, never as measurements. No AMD prefetch register
will be guessed at.

## 5. Design

n=5 reps per arm per host, 10 s per rep. **Arms are interleaved within each rep**
(rep 1: A,B,C,D,C',E; rep 2: A,B,...) so thermal or frequency drift is spread
across arms instead of confounding one. Metric is the binary's own
`avg_bw_gbps`.

**Per-rep values are reported for every cell, with CoV** — per Addendum 3 §C3,
this project has published 3-rep means over a distribution documented as bimodal,
and that will not be repeated here.

Host state is **recorded as found, not changed.** The `setup/*_freeze.sh` scripts
are deliberately *not* run: mos182 and moscxl are shared, and changing governor
or turbo on them to suit this measurement would disturb other users for a
benchmark whose arms are compared within-host and interleaved. Governor, turbo,
and THP state are captured alongside the data.

## 6. Pre-registered readings

1. **The intro's magnitude.** Report A and C per host with per-rep values. The
   unsourced claim implies A/C ≈ 3.76. **Corroborated** if A/C ∈ [3.0, 4.5] on
   EMR; **weakened** if A/C ∈ [2.0, 3.0); **falsified** if A/C < 2.0.
2. **FALSIFIER.** If A/C < 2.0 on **all three** hosts, the intro's motivating
   contrast does not survive and must be **deleted, not re-sourced**.
3. **The label, which changes regardless of the number.** Arm C may not be
   called "write-combining" in the paper. Registered replacement wording:
   *"non-temporal (`MOVNTDQA`) loads on write-back pages"*.
4. **C ≡ D.** Expect |C − D| within pooled noise, confirming by measurement what
   source inspection showed and voiding `stream_nt.c`'s H4 test.
5. **Is the NT hint honored?** If C ≪ A while both have prefetchers ON, the hint
   is at least partly honored and it costs bandwidth — the bundling claim,
   measured correctly for the first time.
6. **C' vs C.** If C' ≈ C, the prefetcher was already ineffective under
   MOVNTDQA, and "forfeits prefetching" is a property of the NT hint rather than
   of prefetch state. If C' ≪ C, then the paper's WC arm was *benefiting* from
   prefetch, and **every published "WC" bandwidth number is an overestimate of
   WC**. Either outcome is reportable; the second is adverse to us and will be
   printed if it occurs.
7. **B vs A.** The prefetch contribution to WB bandwidth. This, not C, is what
   supports "prefetching well and polluting the shared cache are the same
   decision."

## 7. Out of scope

True PAT-based WC; any victim/co-run measurement; CXL-resident streams (the
intro's claim is about host memory type on local DRAM); any change to arms
A/B/C/D/E; the "five WC cores to match two WB cores" arithmetic, which is a
*derived* claim and will be recomputed from these numbers only after they land.
