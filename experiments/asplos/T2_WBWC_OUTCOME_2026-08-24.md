# T2 outcome: the intro's WB/WC bandwidth contrast is falsified

Pre-registration: `T2_WBWC_PREREG_2026-08-24.md`, committed at `d1a0c6b`
**before** any measurement. Analyzer `benchmarks/bench/t2_analyze.py`, committed
at `76eeea3` while the runs were still in flight, computes only the registered
readings. Runner `benchmarks/bench/run_t2_bandwidth.sh` (`d1a0c6b`). Raw data:
`benchmarks/data/t2_bandwidth/t2_*.jsonl`, host state as found in
`t2_*_state.txt`.

## Verdict

> **The pre-registered falsifier FIRED. A/C = 1.25 / 1.29 / 1.28 on three hosts
> across two vendors, against the ~3.76 the intro's claim implies. Per §6 R2 the
> intro's motivating contrast must be DELETED, not re-sourced.**

The WB half was roughly right; the WC half was wrong by about 3×, and the arm
was misnamed on top of that.

## The table

n=5 per cell, 2 GB region, one pinned core (cpu8), local DRAM node 0, 10 s per
rep, arms interleaved within each rep. Per-rep values are in the JSONL.

| host | A `stream_wb` | B `stream_wb_nopf` | C `stream_wc` | D `stream_nt` | C' `stream_wc_nopf` | E `stream_sw_prefetch` |
|---|---:|---:|---:|---:|---:|---:|
| mos181 EMR 8592+ | **14.755** ±0.193 | 13.921 ±0.114 | **11.789** ±0.082 | 11.810 ±0.028 | 8.044 ±0.054 | 14.005 ±0.113 |
| mos182 SPR 8462Y+ | **16.040** ±0.025 | 15.075 ±0.004 | **12.444** ±0.004 | 12.444 ±0.005 | 8.806 ±0.004 | 14.886 ±0.013 |
| moscxl EPYC 9754 | **37.594** ±0.097 | *unavailable* | **29.311** ±0.069 | 29.307 ±0.081 | *unavailable* | *unavailable* |

GB/s, mean ± 1 sd. CoV ≤ 1.31% everywhere and ≤ 0.28% on two of three hosts.
**No bimodality**: every cell's five reps lie within a fraction of a percent, so
unlike the W5.3 family these means are point estimates (Addendum 3 §C3).

Arms: **A** WB pages, regular loads, HW prefetch ON. **B** WB, regular, prefetch
OFF. **C** WB pages, `MOVNTDQA`, prefetch ON — *this is the arm the paper calls
"WC"*. **D** same program as C. **C'** WB pages, `MOVNTDQA`, prefetch OFF — new,
the honest WC proxy. **E** regular loads + software prefetch.

On moscxl, arms B, C' and E require MSR 0x1A4, which is Intel-only; all three
failed **loudly** (`exit 1` after a read-back verify), exactly as pre-registered.
`stream_sw_prefetch` also disables the hardware prefetchers, which the
pre-registration had not anticipated but which fails for the same recorded
reason. The registered AMD F12 cross-check is moot: arm B did not run at all,
so there is no silent no-op to mistake for a measurement.

## The pre-registered readings

| reading | mos181 | mos182 | moscxl | verdict |
|---|---:|---:|---:|---|
| **R1** A/C (claim implies 3.76) | 1.252 | 1.289 | 1.283 | **FALSIFIED (<2.0) on all three** |
| R1' A/C' (honest proxy) | 1.834 | 1.822 | n/a | still below 2.0 |
| **R4** \|C−D\| vs pooled sd | 0.020 / 0.055 | 0.000 / 0.005 | 0.003 / 0.075 | **same program, confirmed** |
| **R5** C/A at equal prefetch state | 0.799 | 0.776 | 0.780 | NT hint costs ~21%, consistently |
| **R6** C'/C | 0.682 | 0.708 | n/a | **the paper's "WC" arm was benefiting from prefetch** |
| **R7** B/A | 0.944 | 0.940 | n/a | HW prefetch contributes only **~6%** of WB stream bandwidth |

## What this means for the paper

1. **Delete the WB/WC contrast from the introduction.** Not re-source it — the
   registered falsifier fired on all three hosts, and the effect is 1.27×, not
   3.76×. The consistency across two vendors (1.25/1.29/1.28) makes this a
   robust null rather than a noisy one.
2. **The derived "five WC cores to match two WB cores" also falls.** At the
   measured 1.275× it takes ~2.6 cores, and at the honest proxy's 1.83× about
   3.7 — neither is five.
3. **Where "4.2 GB/s" came from.** No silicon arm reads near it; the lowest
   anywhere is C' at 8.04. gem5's SE model reports **4.17 GB/s** for its *WB*
   pure-stream ceiling. That is almost certainly the source, mislabelled as a
   silicon WC figure — the misattribution hypothesis in
   `REVIEWER_STATE_2026-08-24.md` §A6, now with measurement behind it.
4. **Rename the arm everywhere, independent of any number.** Arm C is
   `MOVNTDQA` loads on write-back pages with hardware prefetchers enabled. It is
   neither the WC memory type nor prefetch-free. Registered replacement wording:
   *"non-temporal (`MOVNTDQA`) loads on write-back pages"*. This matters to the
   taxonomy: the paper classifies NT loads as the **advisory** address-scoped
   mechanism and memory types as the **enforced** one, so evidence gathered with
   arm C is evidence about the advisory plane, not the enforced one.
5. **Every published "WC" bandwidth figure is an overestimate of WC**, by
   roughly 1/0.69 ≈ 1.4×, because the arm had prefetchers on (R6).
6. **The prefetch-bundling premise does not hold on local DRAM.** Disabling all
   four hardware prefetchers costs only ~6% of WB stream bandwidth (R7). The
   paper's "demand misses sustain only ~4–5 GB/s per core" is a *CXL-latency*
   claim, and §7 put CXL out of scope here, so this does not refute it — but the
   sentence must be scoped to far memory explicitly, because on local DRAM a
   sequential stream needs almost no prefetching to reach full rate.
7. **`stream_nt.c`'s H4 reading is void.** Its header pre-registers "if D ≈ C the
   NT hint is honored"; C and D are the same program, confirmed to three decimals
   on all three hosts. Nothing in the paper may cite that as an H4 test.
8. Single-core stream bandwidth on EPYC 9754 is **2.3–2.5× the Intel parts**
   (37.6 vs 16.0 / 14.8). Not a paper claim, but it bears on any cross-vendor
   core-count arithmetic.

## Apparatus findings, independent of the numbers

- **`stream_wc.c` and `stream_nt.c` are the same program.** Load loops are
  md5-identical after name normalisation; the only functional difference is that
  `stream_nt` reads MSR 0x1A4 and warns. Found by source inspection before the
  runs and confirmed by measurement after.
- **mos182 runs with MSR 0x1A4 = 0x20 machine-wide** (cpu8 and cpu9 both), i.e.
  a prefetcher beyond bits[3:0] is disabled on that host. `stream_wb` **refused
  to run** rather than measure a non-default machine — correct instrument
  behaviour, and an undocumented platform difference between our two Intel hosts
  that belongs in `tab:appplat`. It was normalised to 0x0 for the run and
  restored to 0x20 afterwards.
- **moscxl had `HugePages_Total: 0`**, and `hugepage_alloc` hard-requires
  `MAP_HUGETLB`, so every arm failed until 1536 pages were provisioned. This
  independently confirms the `tab:appplat` defect already on the ledger: the
  paper asserts pre-allocated 2 MB hugepages on that host and the machine
  reports none. Restored to 0 afterwards. The failed run is kept as
  `t2_*_FAILED_nohugepages.jsonl` rather than deleted.
- **`kill -9` defeats these binaries' `atexit` prefetcher restore.** Killing a
  `*_nopf` arm hard leaves MSR 0x1A4 = 0xF on that core — I did this to mos182
  during cleanup and had to repair it. Use SIGTERM, which the binaries handle.

## Data discarded, and why

One mos182 window is quarantined in the session scratchpad, not used: I
relaunched that host while its first run was still live, after renaming its
output file, so two processes were pinned to cpu8 concurrently. A partial
mos181 run (11 records, killed mid-rep2 when a wrapper shell timed out) is
likewise quarantined. Neither contributes to any number above. The two
`*_FAILED_nohugepages.jsonl` files are retained deliberately as evidence of the
hugepage defect.

## System state

All borrowed state restored to as-found and verified: mos182 MSR 0x1A4 cpu8 back
to 0x20 and node0 `nr_hugepages` back to 1024; moscxl node0 back to 0; mos181
untouched throughout (baseline 0x0, confirmed on an unmeasured core). The
`setup/*_freeze.sh` scripts were deliberately **not** run — mos182 and moscxl are
shared, arms were compared within-host and interleaved, and host state is
recorded rather than imposed.

---

# Addendum 1 — 2026-08-24: this document's verdict is RETRACTED

The body above concludes that the intro's WB/WC contrast is falsified and must be
deleted. **Withdrawn.** T2's `C` arm (`stream_wc`) is `MOVNTDQA` on **WB
anonymous pages**; the paper's WC arm is `wc_ntdqa` on a **WC-mapped device**
(`/dev/cxl_wc`, `pgprot_writecombine`) — a different memory type, and the same
aggressor implements `wb_ntdqa` separately for the arm T2 actually measured. The
registered falsifier fired against a claim it could not reach.

On the correct arms, from an audit that predates today
(`experiments/phase1/e4_hygiene/RESULTS.md`, n=12): WB 12.43, WC 3.20,
**ratio 3.882 against the implied 3.762 — `corroborated` (≥3.0), not
`falsified` (<2.0)**. The absolute scale is ~21–24% low, already documented
there with candidate causes.

What survives, correctly scoped: `stream_wc` ≡ `stream_nt` (so `stream_nt.c`'s
H4 reading is void); the new `stream_wc_nopf` arm and C′/C ≈ 0.69, as statements
about `MOVNTDQA`-on-WB; B/A ≈ 0.94 (prefetch contributes ~6% of WB stream
bandwidth on Intel local DRAM); and the cross-vendor single-core WB figures —
which, being Intel, do **not** corroborate the paper's AMD 15.8 either.

Full reasoning: `E1_ARM_IDENTITY_AUDIT_2026-08-24.md`.
