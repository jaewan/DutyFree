# E1 arm-identity audit: the dissociation is sound — and it retracts T2's headline

Question: E1 is the paper's cleanest silicon fact (interference follows
allocation, not bytes). Its "WC" arm — is it the taxonomy's **enforced**
memory-type plane, or the **advisory** non-temporal-hint plane? If advisory, the
paper's strongest evidence is about the wrong plane.

## Verdict: the arm identity is sound

**The WC arm is a genuine WC memory type.** `Sec2_DirectoryTax.tex:30`: *"the WC
path uses `pgprot_writecombine` with `MOVNTDQA`."* Traced to apparatus:
`benchmarks/e2e/instrument/src/aggressor.c` mode **`wc_ntdqa`** →
`map_cxl_device(DEV_CXL_WC, …)` → `mmap("/dev/cxl_wc")`, a character device whose
module applies the WC page protection. `MOVNTDQA` on WC memory is the
architecturally-defined read path for that type, so hint plus type is correct,
not a substitute for it.

Decisively, the same aggressor implements **`wb_ntdqa` as a separate mode** —
`MOVNTDQA` on ordinary WB memory. Its author drew exactly the distinction I later
collapsed. E1 measures the enforced plane. **The concern is closed.**

## Two further checks, both clean

**No `-R` confound.** The paper says "a *matched* 20.9 GB/s stream", and this
aggressor's matching knob `-R` is the one the project bars
(`E2E_SESSION_PROMPT.md:100`, *"carries a known confound. Do not use it."*).
The matching was **by thread count**: WB 2 threads packed into CCX1 vs WC 5
threads spread one-per-CCX (`run_matched_bw_pair.py`), n=12, rep-interleaved
against a quiescent baseline. That is also precisely the paper's "matching the
two-core WB byte rate takes five WC cores". **The confound does not apply.**

**The tax numbers reproduce tightly** (`experiments/phase1/e4_hygiene/RESULTS.md`):

| arm | median tax | 95% CI | paper | agg bandwidth |
|---|--:|--:|--:|--:|
| WB, 2T, diff-CCX | 1.2877× | [1.2790, 1.3095] | 1.28× (+28%) | 20.363 GB/s |
| WC, 5T, spread | 0.9996× | [0.9879, 1.0136] | 1.003× (+0.3%) | 15.137 GB/s |

## Two real defects, neither fatal

**1. The paper never names E1's platform.** This pair is **AMD**, aggressor on a
neighbour **CCX** (EPYC 9754). `Sec1_Introduction.tex:35` and
`Sec2_DirectoryTax.tex:61` state the numbers with no platform, and Sec2's
preamble says the aggressor is "eight on Intel", which actively invites the
reader to place the dissociation on Intel. §5.1 requires every figure to name
its arm at the point of use. **Fix: say AMD, diff-CCX.**

**2. F10: the `/dev/cxl_wc` driver is not committed.** Only the path `#define`
in `common.h` references it. No module source, no `.ko`, and the device is absent
on mos181 and mos182 today with no module loaded. **E1's WC arm is not
reproducible from this repository or on any live host.** That gap sits under the
paper's best silicon fact and belongs on the provenance ledger beside
`tab:fused`'s missing runner.

## The 15.8 / 4.2 GB/s pair was already audited — and it corroborates

`RESULTS.md` §"Single-core WB/WC bandwidth vs the paper's 15.8/4.2 GB/s",
n=12, on the same AMD host that reproduced the tax numbers:

| | paper | measured | ratio |
|---|--:|--:|--:|
| WB single core | 15.8 GB/s | **12.43** [12.43, 12.44] | |
| WC single core | 4.2 GB/s | **3.20** [3.20, 3.20] | |
| **WB/WC** | **3.762** | **3.882** | **corroborated** |

Both placements (same-CCX, spread) agree to 0.2%, so it is not a placement
artifact. The **ratio reproduces**; the **absolute scale is ~21–24% low**, and
that document already records the candidate explanations (unspecified buffer
size/duration in the original, drift on a 79-day-uptime shared host, or a
changed CXL path) without disambiguating them. It also records the coherent
pattern: *every* AMD tax/ratio reproduces tightly while *every* AMD absolute
single-core bandwidth runs 21–27% low.

## Consequence: T2's headline is RETRACTED

`T2_WBWC_OUTCOME_2026-08-24.md` concluded that the intro's WB/WC contrast is
"falsified on three hosts" and "must be DELETED, not re-sourced". **That is
withdrawn.**

The error is in T2's own pre-registration, §2, which asserted that the arm the
paper calls "WC" is `benchmarks/bench/aggressor/stream_wc` — `MOVNTDQA` on WB
anonymous pages. It is not; the paper's arm is `wc_ntdqa` on a WC-mapped device.
T2's `C` arm corresponds to the aggressor's **`wb_ntdqa`**, a different memory
type. So T2's registered falsifier fired against a claim it structurally could
not reach — and the same pre-registration said so in §3 (*"True WC is still not
measured. It needs PAT manipulation from the kernel."*) without my drawing the
inference.

**On the correct arms the registered reading is `corroborated` (≥3.0), not
`falsified` (<2.0): 3.882 against an implied 3.762.**

Also withdrawn: T2's suggestion that "4.2 GB/s" was gem5's 4.17 GB/s WB figure
mislabelled. It is an AMD silicon WC measurement that reproduces at 3.20.

**And my Intel numbers do not bear on it either way.** T2 measured single-core
WB at 14.755 (EMR) / 16.040 (SPR); the paper's 15.8 is an **AMD** figure. Those
must not be presented as corroboration — different platform.

### What T2 does still establish, correctly scoped

- **`stream_wc` ≡ `stream_nt`** in `benchmarks/bench/` — same program plus an MSR
  warning, load loops md5-identical, confirmed by measurement on three hosts. So
  `stream_nt.c`'s pre-registered "if D ≈ C the NT hint is honored" reading is
  **circular and void**. Stands.
- **`stream_wc_nopf`** (new arm) gives C′/C ≈ 0.68–0.71 — a true statement about
  `MOVNTDQA`-on-WB with and without prefetch, **not** about WC.
- **B/A ≈ 0.94**: hardware prefetch contributes only ~6% of WB stream bandwidth
  on Intel local DRAM at a 2 GB region. New, and it stands.
- Cross-vendor single-core WB on Intel and AMD-Bergamo under this proxy — new
  data, previously absent from the repo.

## This is the fourth F11 of the day, and the worst

The other three produced false adverse findings about internal artifacts. This
one produced a **"delete this from the paper" recommendation against a
load-bearing motivational claim that in fact reproduces.** Same mechanism every
time: read one part of an artifact, infer the rest. Here I inferred the paper's
arm from a directory name in `benchmarks/bench/` without reading the paper's own
methods sentence — which is nine words long and says exactly what the arm is.

Had I run the ordering the rule prescribes — read what exists, then measure — the
whole T2 campaign would have been unnecessary: `e4_hygiene/RESULTS.md` already
contained the audit, with n=12 and CIs, before today.

## Hygiene-list changes from this audit

1. **REMOVE** "delete the intro WB/WC bandwidth pair". It is corroborated in
   ratio.
2. **ADD** restate the absolutes at the measured 12.43 / 3.20, or keep 15.8 / 4.2
   with the ~21–24% scale caveat that `RESULTS.md` already documents.
3. **ADD** name E1's platform (AMD, diff-CCX) at both use sites, per §5.1.
4. **ADD** commit the `/dev/cxl_wc` driver, or record it as lost per §6.6.
5. **ADD** rename `benchmarks/bench/aggressor/stream_wc.c`. Its name caused this
   error and will cause it again; it is `MOVNTDQA`-on-WB, and the neighbouring
   `instrument` aggressor already uses the correct label `wb_ntdqa`.
