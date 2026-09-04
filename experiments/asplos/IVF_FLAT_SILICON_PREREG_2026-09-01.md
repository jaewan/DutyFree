# Pre-registration: IVF-Flat silicon operator cell

Date: 2026-09-01. Registered **before any arm of this campaign produced a
number.** The C kernel and this stub exist. **No IVF silicon campaign has
been run. Do not treat this file as an outcome.**

## What this is allowed to be

Sealed IVF-Flat **search** (coarse quantizer + contiguous float32 inverted
lists + nprobe + max-heap) as a second mixed-tenant **operator cell**. Not
“vector DB e2e”, not FAISS e2e, not HNSW. STREAMING is **not** measured on
silicon and is not an arm of the runner.

The hash-join STREAMING cell is unchanged (`COMPLETE_JOIN_OUTCOME_2026-09-01.md`,
`SILICON_E2E_OUTCOME_2026-09-01.md`). Do not quote that join, or any other
kernel, as this operator’s evidence.

## Host and reuse

- **Exclusive host: mos182 / `c4`.** Not mos181.
- Tenant: `benchmarks/e2e/ivf_flat/build/ivf_flat_bench` (`--preset silicon
  --require-ratio`).
- Victim and CAT, **by reference, not copied**:
  `benchmarks/bench/victim/pointer_chase`,
  `benchmarks/e2e/hash_join/scripts/resctrl_clos.sh`.
- Runner scaffold: `experiments/asplos/run_silicon_ivf.sh` →
  `experiments/asplos/silicon_e2e/run_ivf.py`. A6.19: refuse an existing OUT.

## Geometry (register before first arm)

`codebook_bytes = nlist * dim * 4`. Silicon target **32 MiB codebook on 60 MiB
LLC**: `--nlist 8192 --dim 1024` (alt: 16384 × 512). Ratio 32/60 = 0.533… ∈
`[0.50, 0.55]`.

`--require-ratio` **aborts** if codebook/LLC is outside that window (TE-A:
a few-MiB RAG codebook makes CAT cheap). That abort is a kernel gate, not a
measured result.

Gem5 HNF target (not this campaign): 4 MiB codebook / 7680 KiB, same ratio,
e.g. `--nlist 1024 --dim 1024`. Not launched from this prereg.

## Arms (silicon only)

`qui`, `wb`, `nta` (`--policy nta --pf-distance 32` on the **list scan**),
`fb64k` / `fb256k` / `fb1m` (`--flush-distance` on the list scan), CAT width
sweep `cat01`–`cat15` on the whole process. No STREAMING arm. No gem5 in this
campaign.

Metric: median **QPS** + **recall@k** (held-out queries vs exact) + victim
`cyc_per_load`. Recall is a costume check: if it is missing or not in (0, 1],
the cell is void.

## Kill / pass (action on miss)

- **Small codebook.** If `--require-ratio` would abort, **do not run** IVF
  silicon. A costume quantizer is worse than omitting RAG.
- **S1-style void.** If `wb` does not tax the chase, nothing to protect; stop.
- **CAT tax too small.** If 1-way (or the starving end of the CAT frontier)
  vs `wb` does not move tenant QPS by a material amount — codebook still fits
  remaining ways, or the search is list-dominated so CAT does not starve
  centroids — **do not run gem5 H2.** Publishing a near-null IVF cell is worse
  than omitting it. gem5 H2 is conditional on this tax, and is a later
  campaign (`ivf-gem5-conditional`), not this one.
- **STREAMING** is not measured here. Do not draw silicon CAT and a modelled
  H2 point in one unlabeled figure.

## What has not happened

No exclusive mos182 IVF run, no JSONL, no gem5 H2, no paper E5 second-domain
sentence from this operator. This file is a gate and a kill list, not a
result.
