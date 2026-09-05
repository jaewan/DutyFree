# Outcome: silicon IVF-Flat operator cell (CAT / nta / flush-behind)

Date: 2026-09-04 (project-local, UTC−7). *Dating note, as `BUILD_PROVENANCE.md`:
mos182's clock is KST (UTC+9), so this campaign's own timestamps and the JSONL
`ts` fields read `2026-09-05`.*

Judged against `IVF_FLAT_SILICON_PREREG_2026-09-01.md`, which was on disk and
sealed before any arm of this campaign produced a number. Host mos182 (`c4`),
Xeon Platinum 8462Y+, socket 0, L3 60 MiB / 15 ways. **STREAMING is not
measured and is not an arm.** No gem5 point is computed here.

104/105 records `status=ok`. Data:
`experiments/asplos/data/ivf_flat_silicon.jsonl` (105 records),
`data/ivf_flat_silicon_calib.jsonl` (8, apparatus validation),
`data/ivf_flat_silicon.log`. Analyzer:
`experiments/asplos/analyze_silicon_ivf.py`.

The analyzer's thresholds provably predate the verdict. It was committed as
`426d633` at **14:00:23 KST**, while these arms were still running — the last
record's `ts` is **16:31:24 KST** — so `CAT_TAX_MIN_REL = 0.10` and
`S1_TAX_MIN = 1.30` were in the repository before the CAT frontier they judge was
complete. Both are re-exports of constants already in
`silicon_e2e/ivf_gates.py`, which the sealed prereg's runner has used since
2026-09-01; the analyzer restates none of them.

Binaries **as run on mos182**, not as built here:

| | sha256 |
|---|---|
| `ivf_flat_bench` (tenant) | `1b63e006dcb4ad846b1482b615ee8fb9696e3e28dc906f065cbafbd5d1aff643` |
| `pointer_chase` (victim) | `026e357ae21a99717cae3ebf4ed05fa2cd146bda4f110afe4a2f7b829ef2db50` |

The victim binary is byte-identical to the one `SILICON_E2E_OUTCOME_2026-09-01.md`
used, so the two campaigns' victim numbers are directly comparable. The tenant
source is identical to this checkout's
(`ivf_flat_bench.cpp` = `e25278e04174f7509375f1a05a41167121066228287994d9ed07802f27d1888a`
on both hosts); only the compiled object differs, and mos182's is the one
recorded above because it is the one that ran.

## Verdicts — every registered gate, by its registered name

| id | registered condition | verdict |
|---|---|---|
| **G-ratio** (`--require-ratio`) | codebook/LLC ∈ [0.50, 0.55] | **PASS** — realized **0.533333** (33,554,432 B / 62,914,560 B). The small-codebook kill did **not** fire; IVF silicon was licensed to run. |
| **G-codebook** | `nlist=8192`, `dim=1024`, codebook = `nlist*dim*4` = 32 MiB | **PASS** — realized `nlist=8192 dim=1024 codebook_bytes=33,554,432` |
| **G-recall** (costume check) | `recall@k` ∈ (0, 1] | **PASS** — **0.5083** on **all 99** tenant records, spread exactly zero. The cell is **not void**. Independently anchored: see below. |
| **S1-void** | `wb` must tax the pointer chase (≥ 1.30×) | **PASS** — **2.094×** (153.698 / 73.406). There is something to protect. |
| **CAT-tax** | starving end of the CAT frontier vs `wb` must move tenant QPS materially (≥ 10%) | **KILL — FIRED.** cat01 recovers **91.5%** of the victim tax for a tenant QPS cost of **9.31%**, below the pre-registered 10% bar. **Do not run gem5 H2.** |
| **STREAMING** | not measured here | **not measured.** No arm, no `--policy stream`, no gem5. `streaming_arm=false` on all 105 records. |

**CERTIFY: NO.** The campaign is complete in arms and reps — all 21 arms × 5
reps were attempted, `arms_missing=none` — and the terminal registered kill
fired. One record was rejected by a provenance gate (below), so `cat05`'s
median rests on 4 reps rather than 5 and the analyzer's `complete` flag is
False. That does not change any verdict: `cat05` is not the arm any gate reads.

**The kill fired narrowly and that is stated rather than smoothed.** 9.31%
against a 10% bar is a 0.69 pp margin. The threshold was pre-registered as
`cat_tax_material(min_rel=0.10)` in `silicon_e2e/ivf_gates.py`, committed
before this campaign ran, and its self-test pins both sides of it ("5% CAT tax
is not material", "20% CAT tax is material"). It is not adjusted here. A reader
who prefers an 8% bar gets the opposite verdict on this one number, which is
exactly why §"Why the null does not depend on that margin" exists: three
further measurements refuse gem5 H2 without reference to any threshold.

## Realized configuration

Realized, from the tenant's own JSON on every record — never requested.

| | realized |
|---|---|
| `nlist` / `dim` | 8192 / 1024 |
| `codebook_bytes` | 33,554,432 (32 MiB) |
| `llc_bytes` | 62,914,560 (60 MiB) |
| `codebook_llc_ratio` | **0.533333…** |
| `lists_bytes` | 134,479,872 (128 MiB) |
| `nb` / `nq` / `nprobe` / `k` | 32,768 / 1000 / 16 / 10 |
| tenant cpu / victim cpu | 4 / 6 (both package 0, L3 `shared_cpu_list` `0-31,64-95`) |
| victim WSS | 33,554,432 B (32 MiB) |
| tenant inner reps / victim trials | 4 / 20 (search ≈ 18 s, victim window 20 × 1 s) |
| outer reps | 5, arm order rotated per rep |
| `sealed` | `true` on every tenant record |
| `id_sum` | 147,039,988 — **identical on all 99 tenant records** |

`id_sum` identical across every arm means each arm did the same search and
returned the same neighbours; `recall@k` identical to 16 digits says the same.
Nothing in the arm set changes the answer, only how it is fetched.

### G-recall is anchored, not merely in-band — and not by this campaign

`--require-recall` only asserts `recall@k` ∈ (0, 1], which 0.5083 passes
trivially, and the tenant grades itself against an exhaustive scan over the same
`vecs` array. Both are the `F20` shape: a reference derived from the input it is
meant to validate. That weakness was closed **independently of this campaign and
by another worker**, while these arms were running:
`IVF_RECALL_REFERENCE_2026-09-04.md` (commit `45956d4`) re-derives the
generator, quantizer, inverted lists, `nprobe` selection and both top-k paths in
NumPy without calling, linking or reading anything from the C++ tenant, at
**exactly this campaign's geometry** (`nlist 8192, dim 1024, nb 32768, nq 1000,
nprobe 16, k 10`). It reports `recall@k` = **exactly 5083/10000** and reproduces
`id_sum = 147039988` **bit for bit over all 10,000 returned ids**.

That is the same recall and the same `id_sum` this campaign's 99 tenant records
carry. So the costume check is satisfied against an external reference rather
than against the tenant's own arithmetic. **Credit belongs to that pass, not to
this one** — this campaign would have reported 0.5083 as a bare in-band value.

## Per-arm medians

Median of per-rep values. `R = (v_wb − v) / (v_wb − v_qui)`; tenant cost
`1 − qps/qps_wb`. `p99` is the median of the per-rep interpolated p99s, same
estimator as `SILICON_E2E_OUTCOME` addendum 1.

| arm | n | victim cyc/load | sd | p99 | R | qps | tenant cost | recall@k |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| qui | 5 | 73.406 | 0.004 | 73.53 | — | — | — | — |
| wb | 5 | 153.698 | 0.528 | 278.23 | 0 | 224.888 | 0 | 0.5083 |
| nta | 5 | 154.314 | 0.927 | 277.88 | −0.8% | 224.783 | 0.05% | 0.5083 |
| fb64k | 5 | 147.023 | 1.147 | 277.57 | **8.3%** | 223.251 | 0.73% | 0.5083 |
| fb256k | 5 | 153.634 | 0.924 | 277.74 | 0.1% | 224.821 | 0.03% | 0.5083 |
| fb1m | 5 | 155.040 | 1.301 | 277.74 | −1.7% | 224.865 | 0.01% | 0.5083 |
| **cat01** | 5 | **80.225** | 0.201 | **81.20** | **91.5%** | 203.952 | **9.31%** | 0.5083 |
| cat02 | 5 | 88.308 | 0.119 | 89.27 | 81.4% | 206.351 | 8.24% | 0.5083 |
| cat03 | 5 | 94.040 | 0.080 | 97.61 | 74.3% | 208.046 | 7.49% | 0.5083 |
| cat04 | 5 | 101.426 | 0.432 | 108.43 | 65.1% | 210.042 | 6.60% | 0.5083 |
| cat05 | **4** | 107.899 | 0.185 | 124.96 | 57.0% | 211.923 | 5.77% | 0.5083 |
| cat06 | 5 | 118.322 | 0.841 | 142.65 | 44.1% | 213.868 | 4.90% | 0.5083 |
| cat07 | 5 | 130.214 | 1.114 | 159.63 | 29.2% | 215.785 | 4.05% | 0.5083 |
| cat08 | 5 | 139.811 | 1.907 | 175.44 | 17.3% | 217.752 | 3.17% | 0.5083 |
| cat09 | 5 | 149.885 | 1.531 | 181.13 | 4.7% | 219.497 | 2.40% | 0.5083 |
| cat10 | 5 | 157.073 | 0.571 | 184.64 | −4.2% | 221.055 | 1.70% | 0.5083 |
| cat11 | 5 | 163.538 | 2.355 | 187.16 | −12.3% | 222.312 | 1.15% | 0.5083 |
| cat12 | 5 | 166.782 | 1.552 | 196.73 | −16.3% | 223.493 | 0.62% | 0.5083 |
| cat13 | 5 | 166.535 | 0.656 | 225.14 | −16.0% | 224.203 | 0.30% | 0.5083 |
| cat14 | 5 | 162.606 | 1.338 | 251.87 | −11.1% | 224.562 | 0.14% | 0.5083 |
| cat15 | 5 | 154.615 | 1.024 | 277.69 | −1.1% | 224.892 | −0.00% | 0.5083 |

Two controls hold. **`qui` = 73.406 (sd 0.004)** is the established 73.398 /
73.406 floor, reproduced on the same victim binary a campaign later. **cat15 ≈
wb** (R −1.1%, tenant cost −0.00%): confining the tenant to all 15 ways is a
no-op, so the CAT apparatus is not manufacturing an effect.

R(w) is monotone rising as the mask narrows, peaking at cat01 — the same shape
`SILICON_E2E` found, and the same reason applies: at 4.0 MiB per way this part
cannot express the model's narrow-mask starvation regime. That is not re-tested
here and no S2-style claim is made.

`cat10`–`cat14` show negative protection (−4% to −16%) at sd 0.6–2.4, i.e. the
victim is *slower* than under `wb`. `SILICON_E2E` recorded the same wide-mask
overshoot at cat12–14 and called it unregistered; it reproduces here on a
different tenant, which makes it more likely to be a real property of this
LLC's way-masking than of either workload. It is still unregistered and is not
a claim of this campaign.

## What actually happened: CAT protects a lot, and costs almost nothing

The headline is not the kill; it is *why* the kill fired.

**The tenant is nearly cache-insensitive.** Across a 15× change in granted LLC
capacity — cat01's 1 way (4.0 MiB) to cat15's 15 ways (60 MiB) — tenant QPS
moves from 203.952 to 224.892. That is a **9.31% total range**, monotone and
smooth, for a 15× capacity change, on an operator whose codebook is 32 MiB.
Meanwhile the victim moves 80.225 → 154.615, a 1.93× swing over the same masks.

The prereg anticipated two mechanisms for a small CAT tax and **neither is what
happened**:

- *"codebook still fits remaining ways"* — it does not. At cat01 the tenant has
  4.0 MiB for a 32 MiB codebook it rescans every query.
- *"the search is list-dominated so CAT does not starve centroids"* — it is not.
  Realized `list_dom_ratio = 0.0078125`; per query the codebook scan is
  33,554,432 B and the list scan 262,144 B, a ratio of **128:1**. The lists are
  **0.775%** of per-query bytes. This operator is codebook-**dominated**, and
  `g_list_dom=false` on every record.

The measured mechanism is a third one, and it is offered as a **hypothesis, not
a registered result**, because this campaign did not read a performance counter:
the codebook scan is a *pure sequential stream with no intra-query reuse* — 8192
centroids of 4096 B each, touched once per query. At `wb` the tenant's 32 MiB
codebook and the victim's 32 MiB chase already oversubscribe a 60 MiB LLC, so
the codebook is substantially streamed from DRAM even with the full mask;
narrowing the mask mostly removes a benefit the tenant was not getting. A
single-threaded sequential stream is prefetch-friendly and far from this
socket's bandwidth limit, so its throughput barely moves. The victim, a random
dependent-load pointer chase, is latency-bound and cache-sensitive, so
excluding the tenant's stream from 14 of 15 ways is worth 74 cycles/load to it.
**CAT is cheap here precisely because the tenant does not benefit from the cache
it was polluting.** Confirming that reading needs tenant LLC MPKI and DRAM
bandwidth, which are not in this JSONL; a campaign that wants to publish the
mechanism must measure them.

`cat01`'s tail is as tight as its median (p99 81.20 vs median 80.225), matching
the join cell's cat01 behaviour. `wb`'s p99 is 278.23 against a 153.698 median:
the unprotected co-run's tail is far worse than its median, and CAT at 1 way
removes essentially all of it.

### Against the hash join, in the same units

| cell | arm | R | tenant cost |
|---|---|--:|--:|
| IVF-Flat search (this campaign) | cat01 | 91.5% | **9.31%** |
| hash join (`SILICON_E2E`) | cat01 | 91.4% | **42.02%** |
| IVF-Flat search | best fb (`fb64k`) | 8.3% | 0.73% |
| hash join | best fb (`fb256k`) | 44.5% | 6.31% |
| IVF-Flat search | nta | −0.8% | 0.05% |
| hash join | nta | 15.3% | −2.95% |

At **the same 91.5% protection**, CAT costs this operator **4.51× less** than it
costs the join. The two cells agree on how much CAT protects and disagree by
4.5× on what it costs. This is a *contrast between two operators on one part*,
not a STREAMING result, and it is the most transferable number this campaign
produced.

## Why the null does not depend on the 0.69 pp margin

gem5 H2 is, by its own definition in `benchmarks/e2e/ivf_flat/README.md`, *"lists
declared STREAMING, codebook WB."* Three independent measurements say the
datapath H2 would tag has no protective headroom to win, and none of them is a
threshold comparison.

1. **The lists are 0.775% of per-query traffic** (262,144 B against 33,554,432
   B). A mechanism that perfectly handled the list scan would be operating on
   under 1% of the bytes the tenant moves.
2. **Flush-behind on the list scan is already a measured null.** `fb64k` /
   `fb256k` / `fb1m` recover **8.3% / 0.1% / −1.7%** of the victim tax at
   0.73% / 0.03% / 0.01% tenant cost. Flush-behind is the shipping software
   analogue of "do not let the streamed lists pollute the LLC" — the same thing
   H2 would do in hardware. On the join it recovered 44.5%; here it recovers
   essentially nothing.
3. **nta on the list scan is also a null** (R −0.8%). A second, independent
   non-temporal path over the same bytes, same answer.

If evicting or bypassing the lists in software buys 0–8% of the tax, declaring
those same lists STREAMING in a simulator cannot buy much more. **The CAT margin
is 0.69 pp; this argument has no margin in it at all.**

### The structural conflict, which is the durable finding

The operator cannot be made list-dominated *and* keep the registered
codebook/LLC ratio. `--require-ratio` at a 60 MiB LLC pins `nlist*dim*4` to
≈ 32 MiB. `--require-list-dom` needs `nprobe*nb ≥ 8*nlist²`. Solving both at
`nprobe=16`:

| geometry | `nb` required for list-dominance | resulting list file |
|---|--:|--:|
| `nlist=8192 dim=1024` (registered) | ≥ 33,554,432 vectors | ≈ **137.7 GB** |
| `nlist=16384 dim=512` (registered alt) | ≥ 134,217,728 vectors | ≈ **276.0 GB** |

The only other lever is raising `nprobe` to `nlist`, which scans every list —
brute-force exact search, not IVF, with `recall@k = 1.0` by construction. So the
two gates this project wrote for this kernel are **mutually unsatisfiable at any
feasible scale**:

- `IVF_LIST_DOM_PREREG` picked list-dominance (`nlist=128 dim=256 nb=262144`,
  `list_dom_ratio=512`) and its codebook is 131,072 B — 0.002 of the LLC, which
  fails `--require-ratio` and is exactly the TE-A costume that gate exists to
  refuse.
- This prereg picked the interesting codebook/LLC ratio and got
  `list_dom_ratio=0.0078`.

**IVF-Flat cannot be one cell that simultaneously has an interesting LLC
protection problem and a STREAMING datapath worth tagging.** `IVF_LIST_DOM_OUTCOME_2026-09-02.md`
already said the silicon costume "remains codebook-dominated
(`list_dom_ratio=0.0078` at `nlist=8192`)" and that it "does not license that
campaign." This campaign ran it anyway, as registered, and measured what that
sentence predicted.

## The one rejected record

`cat05` rep2, `status=gate_fail`. The mask was correct at setup
(`mask_got=001f`, `mask_ok=true`, `clos_cpus=4`), but the post-measurement
re-read found `clos_b_present_after=false` — **a foreign process deleted the
CLOS group during the ~19 s measurement window.**

The record's own numbers confirm the CAT was not in force for it: `qps
224.932` and `victim_cyc_per_load 155.5005`, both of which are `wb`'s values
(224.888 / 153.698), not cat05's (211.923 / 107.899). Had it been admitted it
would have dragged cat05 toward "no protection" — a false null in the
hypothesis-favouring direction.

This is the exact TOCTOU that `SILICON_E2E_OUTCOME` addendum 1 flagged as
unguarded ("the committed JSONL has no post-rep re-read — 'it didn't bite' is
luck") and added `mask_got_after` / `mask_held_ok` to catch. **It bit, on the
next campaign, and the guard caught it.** The check earned its place. It fired
once in 105 records and did not recur.

## Apparatus notes

An 8-record calibration pass (`data/ivf_flat_silicon_calib.jsonl`) ran before
the campaign and validated the runner end-to-end on this host: `qui`, `wb`,
`cat04`, `cat08`, `nta`, `fb256k`, all `status=ok`, all identity gates green,
20 victim trials per tenant arm. It found no bugs; unlike the join cell's
calibration it is reported for completeness rather than because it changed
anything. Its numbers agree with the campaign's to ~0.3% and it is **not** cited
as evidence above.

Two apparatus facts worth recording:

- **Index build dominates wall time and is outside the measured window.**
  k-means + invert take ≈ 3 m 46 s per arm at this geometry; the timed search
  is 17.8 s at `--reps 4`. `IVF_MEASURE_BEGIN` / `_END` bracket the search
  only, and the victim is started after `BEGIN`, so no victim trial overlaps
  index construction. Total campaign wall time ≈ 6 h 57 m for 105 records
  (first record `ts` 09:38:52 KST, last 16:31:24 plus that arm's runtime).
- **`--inner-reps 4`** was chosen so the tenant's timed search (≈18 s) covers
  the victim's 20 × 1 s window. At the runner's default of 1 the search is
  4.4 s and the victim would return ~4 trials. Every tenant record here has
  `victim_n_trials = 20`. This changes no registered quantity: `qps` is
  `nq*reps/total_sec`, a rate.

## What a paper may say from this campaign

- On a Xeon 8462Y+ with a 60 MiB / 15-way LLC, a sealed IVF-Flat search whose
  coarse-quantizer codebook is 0.533 of the LLC degrades a co-running
  latency-sensitive neighbour by **2.09×** (73.406 → 153.698 cycles/load).
- **CAT is a cheap and effective protection mechanism for this operator**: a
  1-way mask recovers **91.5%** of that degradation for a **9.31%** tenant QPS
  cost, and removes essentially the whole tail (p99 278.23 → 81.20).
- At matched protection (≈91.5%) that costs **4.51× less** than the same mask
  costs the hash join (9.31% vs 42.02%), measured on the same part with the same
  victim binary.
- Non-temporal hints and flush-behind on the inverted-list scan are **nulls** on
  this operator (R between −1.7% and +8.3%), in contrast to the join where
  flush-behind recovered 44.5%.
- Recall@k is 0.5083 at `nprobe=16` of `nlist=8192`, identical on all 99 tenant
  records: the cell is doing real approximate search.

## What a paper may not say from this campaign

- **Anything about STREAMING on IVF-Flat.** It was not measured. There is no
  arm, `--policy stream` is refused by the kernel, and `streaming_arm=false` on
  all 105 records. This campaign does not test STREAMING and cannot support or
  weaken any STREAMING claim.
- **That IVF-Flat is a second STREAMING workload family.** It is not. The
  paper's only controlled STREAMING-versus-alternative comparison remains the
  one gem5 hash join. This campaign does not add a second family; it tested
  whether a protection problem exists for this operator, and the answer does not
  license a STREAMING arm.
- **That IVF-Flat's sealed inverted lists are a clean instance of the paper's
  scope predicate.** Measured, at the registered geometry the lists are 0.775%
  of per-query traffic and the codebook — a reused write-back set — is 99.2%.
  That is the *opposite* of the predicate. The geometry where the lists do
  dominate (`IVF_LIST_DOM`) has a 128 KiB codebook and fails `--require-ratio`.
- **Any gem5 H2 IVF number.** Not run, and now unmotivated.
- **CAT's 9.31% here alongside a modelled H2 point in one unlabeled figure.**
  Forbidden by the prereg and not made less so by the null.
- **The hash join's speedup as this operator's evidence**, or this operator's
  cheap CAT as the join's.
- **The mechanism** ("the tenant is bandwidth-bound so CAT is free") as a
  measured result. It is a hypothesis consistent with the 9.31% QPS range over
  a 15× capacity change; no counter was read.

## Consequence for the conditional gem5 campaign

`ivf-gem5-conditional` (gem5 H2: lists STREAMING, codebook WB) is **not
motivated by this evidence** and should not be built. The prereg made it
conditional on a material silicon CAT tenant tax; that tax is 9.31% against a
10% bar, and independently the software analogues of H2's mechanism on the same
bytes recover 0–8% of the victim tax. One to two days of harness work is saved.

A null here is decisive in the useful direction: it says the paper's second
workload family should be looked for in an operator whose *streamed* set is
large relative to its reused set. IVF-Flat at an interesting codebook/LLC ratio
is structurally not that operator, and the table in §"structural conflict" shows
it cannot be made into one at feasible scale.

---

# Handback — the prereg's gem5 HNF geometry is invalid, and self-aborting

**Not acted on; recommended only.** No gem5 campaign is launched, amended or
built by this document. `IVF_FLAT_SILICON_PREREG_2026-09-01.md` receives a
short addendum recording this; nothing in its sealed body is deleted.

The prereg line

> Gem5 HNF target (not this campaign): 4 MiB codebook / 7680 KiB, same ratio,
> e.g. `--nlist 1024 --dim 1024`. Not launched from this prereg.

is invalid. `NONPOW2_SETS_MEASURED_2026-09-04.md` §1 **measured** that
`--l3_size 7680KiB --l3_assoc 20` yields 6144 sets, of which gem5's `floorLog2`
indexing reaches 4096, so realized HNF capacity is **5,242,880 B** — established
not by derivation but by cell B being bit-identical to a 5 MiB cell A on all
2,014 simulated quantities.

| | against requested 7,864,320 | against **realized 5,242,880** |
|---|--:|--:|
| 4 MiB codebook (`nlist 1024 dim 1024`) | 0.533333 — `--require-ratio` PASS | **0.800000 — `--require-ratio` ABORTS** |

So the error is not merely a misdescription. **The registered gem5 geometry
cannot start**: with `--llc-bytes 5242880` the kernel's own TE-A gate aborts it
at 0.800, outside [0.50, 0.55]. This was checked with the committed
`ivf_gates.ratio_check`, not by hand.

**Recommended corrected geometry.** To hit 0.5333 against a realized 5,242,880 B
the codebook must be ≈ 2,796,203 B (**2.667 MiB**), i.e. `nlist*dim` ∈
[655,360, 720,896].

| | recommended |
|---|---|
| gem5 launcher | `--l3_size=5MiB --l3_assoc=20` — **not** `7680KiB` |
| IVF kernel | `--nlist 683 --dim 1024 --llc-bytes 5242880` |
| realized codebook | 2,797,568 B (2.6683 MiB) |
| realized ratio | **0.533594** (silicon's is 0.533333; Δ 0.00026) |

`dim=1024` is kept so the gem5 cell walks the same vector width as the silicon
cell and exercises the same inner loop. Alternates in band, if a rounder
`nlist` is preferred: `nlist 680` → 0.531250; `nlist 2731 dim 256` → 0.533398.

Changing the launcher flag from `7680KiB` to `5MiB` changes the *description* of
the machine and not the machine — that is the whole content of `NONPOW2` §1 —
so it is free, and it is the same correction that document applied to
`FB_ORACLE_PREREG` in its §3.3.

**Two further inheritors of the invalid figure, reported not edited.** Both are
outside this campaign's paths.

- `silicon_e2e/ivf_gates.py:122` — the self-test asserts
  `ratio_check(4*1024*1024, 7680*1024)` is **True**, i.e. it certifies the
  4 MiB / 7680 KiB pair as in-band. It passes only because it compares against
  the *requested* LLC. This is a **requested-for-realized substitution embedded
  in a gate**, the same defect family as `F18` component (2) in `NONPOW2` §6 —
  a fail-closed check reading the artifact that carries the requested quantity.
  It should become `ratio_check(2797568, 5242880)`. Not edited here: this file
  is the running campaign's gate module and changing it mid-campaign would make
  the analyzer and the runner disagree about what was enforced.
- `benchmarks/e2e/ivf_flat/README.md` "gem5 (r5 HNF) | 1024 | 1024 | 4 MiB |
  7680 KiB | 0.533" and the binary's own `--help` text ("gem5 4 MiB on 7680 KiB")
  carry the same pair. That tree is another worker's uncommitted path and is
  left byte-for-byte.

Note this handback is a correction to a *registration that should not now be
executed at all* — the campaign it describes is unmotivated by the body of this
document. The geometry is corrected so that the record is right, not so that the
campaign can run.

## Host provenance

mos182's checkout was **not** fast-forwarded. It sits at commit
`33eaf07`, 389 commits behind this tree, with 33 dirty paths (437 with
`-uall`), and inspection found content that exists nowhere else:

- `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp`
  (`e8d104588c756baeb9c69d7d3bd28e32ea6f4da6a2a8952bd9e160e46da1a9ff`, 2367
  lines) and `benchmarks/e2e/hash_join/Makefile`
  (`8f1d5c0f5cf32242a4131e54399e948c4bcb2d53527b73757dd1933855d44081`) exist in
  **no commit reachable from any ref in this repository** — checked blob by blob
  over `git rev-list --all`, not inferred from HEAD. Re-verified *after* the 25
  commits other workers landed during this campaign, several of which
  (`abccb31`, `73da510`, `0d5c6a9`) modify those exact two paths; the mos182
  content is still unique. mos182's built
  `hash_join/build/cxl_join_bench` is
  `75e0af947243c49f5b2451e1268ee378588f20eafc42330f9ca4ff2edde893b6` — the exact
  binary `SILICON_E2E_OUTCOME_2026-09-01.md` cites. That source is therefore the
  **sole surviving source of the paper's published silicon hash-join campaign.**
- `experiments/asplos/data/duckdb_tenant_cat.jsonl.d/` — 48 MB, 355 raw per-arm
  files, uncommitted and present on no other host.

A checkout or pull would have had to overwrite the first two and clobber
untracked `data/*.jsonl` paths. Instead **three files were fetched by content
from this tree's HEAD** and written to their paths, leaving mos182's git state
and every one of its 33 dirty paths byte-for-byte unchanged (re-verified after
the copy):

| file | sha256 (identical here and on mos182) |
|---|---|
| `experiments/asplos/silicon_e2e/run_ivf.py` | `dcff2688e91d9933fe0509474fadfa6ed88e0bb6ea82eeb33bcf51c112b572da` |
| `experiments/asplos/silicon_e2e/ivf_gates.py` | `7f563d83435bc3813bc023afe0dadbb512430bb10d577c03d8b6c9ac845b362a` |
| `experiments/asplos/run_silicon_ivf.sh` | `79aaf1887c1b7210acd415fa841399f615819566fc3d25c8f07cfa2712f8849d` |

mos182's dirty-path count is 34 rather than 33 only because
`run_silicon_ivf.sh` is a new untracked file. The three shared dependencies the
runner needs — `silicon_e2e/gates.py`, `experiments/lib/dutyfree/resctrl.py`,
`hash_join/scripts/resctrl_clos.sh` — were already present and already
byte-identical to this tree's HEAD, so nothing was shipped for them. Nothing on
mos182 was deleted, reset, stashed or forced. Campaign outputs were written to
`/home/domin/ivf_run/` outside the repo tree.
