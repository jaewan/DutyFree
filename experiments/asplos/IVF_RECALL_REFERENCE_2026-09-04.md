# IVF-Flat: an independent correctness reference — 2026-09-04

**Verdict: `recall_at_k = 0.5083` at `--nq 1000 --nb 32768 --nprobe 16 --k 10` is
independently confirmed.** An implementation that shares no code with the C++
tenant, written from the tenant's documented behaviour, reproduces the figure and
also reproduces the tenant's `id_sum` — an exact 64-bit integer over all
`k*nq = 10 000` returned ids — bit for bit. The tenant's vector generator *is*
reproducible from outside the binary.

This closes the `F20` exposure on the IVF-Flat campaign. It does not fix the two
gates, which remain in the `F20` class; §7 proposes the wording for that.

---

## 1. Why the campaign needed this

`F20` is the class *"a correctness gate whose reference is derived from the same
input it is meant to validate."* IVF-Flat has two gates and both are in it:

| Gate | Location | Why it cannot fail |
| --- | --- | --- |
| `live_check` | `experiments/asplos/silicon_e2e/ivf_gates.py:82-89` | `ref_id_sum` is seeded from the **first arm** (`run_ivf.py:473-474`). It proves the arms agree with each other. The first arm is never compared to anything. |
| `recall_at_k` | `benchmarks/e2e/ivf_flat/src/ivf_flat_bench.cpp:648`, `:973-984` | The approximate search is graded against an exhaustive scan **over the same `vecs` array**. A corrupted array corrupts both sides equally. |
| `--require-recall` | `ivf_flat_bench.cpp:1014` | Asserts only `recall ∈ (0, 1]`. The observed `0.5083` passes trivially, and so would `0.05` or `0.99`. |

There is no realized defect here. I confirmed the tenant contains no
`prefault_region`-style mutation of the list object; the only writes to the
mapping are `memset` in `mmap_lists_into` (`:470`) and the payload copy in
`invert` (`:631-633`), both before `IVF_MEASURE_BEGIN`. This is a latent
weakness, and the campaign is about to become the paper's second workload with
no absolute anchor. §6 is the anchor.

## 2. What the reference is

`experiments/asplos/ivf_recall_reference.py` — Python/NumPy only.

It does not call, link, load, import, or parse anything from the C++ tenant, and
it does not read any file the tenant produced. Its entire input is the tuple
`(nlist, dim, nb, nq, nprobe, k, kmeans_iters, train_n, seed)`. Everything else
is re-derived from the behaviour documented in the source, which I read rather
than guessed:

| Reproduced | Source | Behaviour |
| --- | --- | --- |
| `SplitMix64` | `:142-153` | `x += 0x9e3779b97f4a7c15`, two xor-multiply rounds. `u01 = (next()>>11) * 2^-53` evaluated in **double** and then narrowed to float. `uniform(lo,hi) = lo + (hi-lo)*u01` in float32. |
| draw order | `:859-866` | one stream from `cfg.seed`: `nlist*dim` centres via `uniform(-1,1)`, then `nb*dim` db noise, then `nq*dim` query noise; `noise = 0.08f` for both. |
| `generate_clustered` | `:598-606` | `x[i][d] = centers[i % nlist][d] + uniform(-noise, noise)`, `i` outer / `d` inner. |
| `kmeans` | `:560-595` | separate stream seeded `seed ^ 0x6B6D65616E73` (`"kmeans"`); partial Fisher-Yates picks `nlist` distinct training rows; `iters` Lloyd steps accumulating in double and writing float32; empty clusters keep their previous centroid. |
| `nearest_centroid` | `:222-233` | strict `<`, so ties resolve to the **lowest** index. |
| `invert` | `:608-635` | every db row to its nearest centroid; payload ids are original db row indices. |
| `nprobe_lists` | `:235-247` | the `min(nprobe, nlist)` centroids nearest the query. |
| `TopK` | `:102-140` | `hit_less`/`better_than_worst` compare **dist then id**, so the heap result is the `k` smallest by `(dist, id)` lexicographically and is *independent of scan order*. The reference reproduces it with a lexicographic sort — see §5. |
| `exact_query` | `:552-558` | the same top-k over all `nb` rows. |
| `recall_at_k` | `:648-666` | mean over queries of `|ivf_k ∩ exact_k| / k`. |

Because SplitMix64's state update is a pure counter, the state before the `i`-th
call is `seed + i*GOLDEN mod 2^64`, so the stream is random-access and the whole
generator vectorises. That is what makes a NumPy reference feasible at campaign
scale: the silicon geometry's 42 967 040 draws cost under a second.

`experiments/asplos/ivf_recall_compare.py` is the only place the two meet. It
runs both over one configuration and diffs three quantities. The reference is
never shown the tenant's output and the tenant is never given the reference's.

## 3. Is the generator reproducible from outside the binary? — Yes, with one bounded caveat

Bit-exactly, with one ambiguity that I resolved rather than assumed.

`uniform` computes `lo + (hi-lo)*u01()`, which the compiler may contract into an
FMA, changing the result by up to one ulp. This does **not** affect the centres:
there `hi-lo = 2.0f`, so the product `2*u01` is exact and both forms agree —
confirmed, `centers_sha` is identical under both (`3c2ec66936a22dfe`). It *does*
affect the `±0.08` noise, where the span is not a power of two.

The reference implements both (`--contract nofma|fma`) and the ambiguity is
immaterial to every decision the search makes:

| silicon geometry | `db_sha` | `hits` | `id_sum` | `dist_sum` |
| --- | --- | --- | --- | --- |
| `--contract nofma` | `70ec9d2c3242061c` | 5083 | 147039988 | 3708791.656096697 |
| `--contract fma` | `3eed365af8e1a042` | 5083 | 147039988 | 3708791.658387661 |
| **tenant** | — | **5083** | **147039988** | **3708791.6586744785** |

The generated vectors genuinely differ in the last bit, and `hits`, `recall` and
`id_sum` are nevertheless identical. Incidentally the `fma` variant's
`dist_sum` lands ~9× closer to the tenant's (7.7e-11 vs 7.0e-10 relative),
which agrees with the disassembly: the live binary contains `vfmadd231ss`, so
GCC did contract. Nothing in the verdict rests on this.

## 4. Configurations compared

Both sides run the same `(geometry, seed)`; the tenant is invoked with
`--reps 1 --warmups 0`. Three quantities are diffed:

* **`recall_at_k`** — the number under audit. Compared as the integer hit count
  `recall * k * nq`, because both sides accumulate the same rational as a
  different double summation and the last bit is meaningless.
* **`id_sum`** — the sum of every returned top-k id, an exact 64-bit integer.
  Agreement is a `k*nq`-way exact match and cannot be produced by a coincidence
  of averages. This is the load-bearing comparison.
* **`dist_sum`** — the sum of returned top-k distances. The tenant sums float32
  in four lanes in an order the compiler chooses (§5), so this is compared as a
  relative residual, not exactly.

### 4.1 Validation ladder — bit-exact float32 back-end

`--backend f32strict` replays the tenant's `l2sq` exactly: four float32 lanes
strided by four, accumulated in increasing `i`, then `((s0+s1)+s2)+s3`, then the
scalar tail. Every `nprobe` row is paired with an `nprobe = nlist` row, which
degenerates `ivf_query` to a full scan so that the tenant's `id_sum` becomes the
`id_sum` of **its own exhaustive path** — that is how the exhaustive reference
the tenant grades itself against gets checked, rather than only the approximate
path.

| nlist | dim | nb | nq | nprobe | k | iters | train_n | hits t/r | recall | id_sum tenant | id_sum ref | agree | dist_sum rel |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: | ---: |
| 8 | 16 | 256 | 64 | 2 | 4 | 8 | 256 | 256/256 | 1.00000 | 34000 | 34000 | ✔ | 1.28e-09 |
| 8 | 16 | 256 | 64 | **8 = nlist** | 4 | 8 | 256 | 256/256 | 1.00000 | 34000 | 34000 | ✔ | 1.28e-09 |
| 256 | 64 | 1024 | 100 | 16 | 10 | 1 | 512 | 972/972 | 0.97200 | 477919 | 477919 | ✔ | 5.98e-10 |
| 256 | 64 | 1024 | 100 | **256 = nlist** | 10 | 1 | 512 | 1000/1000 | 1.00000 | 478615 | 478615 | ✔ | 7.12e-10 |
| 512 | 32 | 2048 | 150 | 3 | 10 | 2 | 1024 | 1213/1213 | 0.80867 | 1364235 | 1364235 | ✔ | 4.41e-10 |
| 512 | 32 | 2048 | 150 | **512 = nlist** | 10 | 2 | 1024 | 1500/1500 | 1.00000 | 1425042 | 1425042 | ✔ | 8.46e-11 |
| 1024 | 64 | 4096 | 200 | 4 | 10 | 1 | 2048 | 1332/1332 | 0.66600 | 3762767 | 3762767 | ✔ | 8.03e-10 |
| 1024 | 64 | 4096 | 200 | **1024 = nlist** | 10 | 1 | 2048 | 2000/2000 | 1.00000 | 3802844 | 3802844 | ✔ | 9.16e-10 |
| 1024 | 128 | 4096 | 200 | 8 | 10 | 1 | 2048 | 1304/1304 | 0.65200 | 3823957 | 3823957 | ✔ | 2.39e-09 |
| 1024 | 128 | 4096 | 200 | **1024 = nlist** | 10 | 1 | 2048 | 2000/2000 | 1.00000 | 3795847 | 3795847 | ✔ | 1.80e-09 |

10/10 cells: exact agreement on hit count and on `id_sum`. Largest `dist_sum`
residual 2.4e-09 relative, which is float32-summation-order noise.

Note that the exhaustive rows carry *different* `id_sum` values from their
approximate partners (e.g. 478615 vs 477919). The exhaustive check therefore has
teeth — it is not the approximate answer re-asserted.

### 4.2 Campaign geometry

`--preset silicon --require-ratio --require-recall --nq 1000 --nb 32768
--nprobe 16 --k 10 --llc-bytes 62914560`, i.e. the tenant command
`run_ivf.py:259-267` builds, minus the `--cpu-list` pin. `nlist = 8192`,
`dim = 1024`, `kmeans_iters = 1`, `train_n = 16384`,
`codebook_bytes = 33554432` (32 MiB, ratio 0.5333).

| cell | quantity | tenant | reference | agree |
| --- | --- | --- | --- | :---: |
| **campaign** (`nprobe 16`, seed `0x1F1FCAFE1234`) | `recall_at_k` | `0.50829999999999564` | `0.5083` (5083/10000) | ✔ |
| | `id_sum` | `147039988` | `147039988` | ✔ exact |
| | `dist_sum` | `3708791.6586744785` | `3708791.656096697` | 7.0e-10 rel |
| **exhaustive** (`nprobe = nlist = 8192`) | `recall_at_k` | `1` | `1.0` (10000/10000) | ✔ |
| | `id_sum` | `149070802` | `149070802` | ✔ exact |
| | `dist_sum` | `3622807.593549967` | `3622807.602263689` | 2.4e-09 rel |
| **alt seed** (`0xDEADBEEF`, `nprobe 16`) | `recall_at_k` | `0.5123999999999949` | `0.5124` (5124/10000) | ✔ |
| | `id_sum` | `144262486` | `144262486` | ✔ exact |

The alt-seed row matters: the reference predicts a *different* recall for a
different seed (0.5124, not 0.5083) and the tenant produces exactly that. The
agreement at the campaign seed is therefore not a coincidence of one
configuration, and the reference is demonstrably a function of its input.

`0.50829999999999564` is `5083/10000` accumulated as 1000 double additions of
`hits/10`. The reference computes the numerator as an integer: 5083 hits out of
10000. Same number.

### 4.3 Exhaustive path at campaign geometry

This is deliverable item 1 — *"brute-force nearest neighbours over the same
generated vectors, and check the tenant's exhaustive path agrees"* — done at the
campaign geometry rather than only in miniature.

Running the tenant with `--nprobe 8192` (`= nlist`) makes `nprobe_lists` select
every list, so `ivf_query` degenerates to a full scan of all 32768 vectors and
the reported `id_sum` is the `id_sum` of the tenant's own exhaustive top-10.
Compared against the reference's independent brute force over the same 32768
generated vectors:

| | tenant | reference |
| --- | --- | --- |
| `recall_at_k` | `1` | `1.0` (10000/10000) |
| `id_sum` | **`149070802`** | **`149070802`** |
| `dist_sum` | `3622807.593549967` | `3622807.602263689` (2.4e-09 rel) |

Exact agreement on all 10 000 returned ids. The tenant's exhaustive scan is
correct, and `149070802 ≠ 147039988` confirms this is a genuinely different
quantity from the approximate cell — the exhaustive check is not the approximate
answer restated.

Two consequences worth stating separately, because the campaign's `recall_at_k`
gate depends on both and neither was previously established:

1. The **denominator** of `recall_at_k` — the exhaustive top-k the tenant grades
   itself against (`:973-984`) — is independently correct at campaign geometry.
2. The **numerator** — the approximate top-k (§4.2) — is independently correct
   at campaign geometry.

`recall_at_k = 0.5083` is therefore the ratio of two independently verified
quantities, not a ratio of two views of one possibly-wrong quantity. That is
precisely the property `F20` says a gate must have and the tenant's own
construction cannot supply.

## 5. Precision: why float64 is allowed to arbitrate

At campaign geometry the bit-exact back-end is `O(pairs × dim)` in NumPy and
therefore infeasible, so §4.2 uses float64 Gram-matrix distances. Two things
justify that, both measured rather than assumed.

**The Gram identity is not losing anything.** Cross-checked against direct
float64 subtraction over the campaign geometry: max absolute error **5.8e-13**
on distances of order 10²–10³.

**Every decision had orders of magnitude more slack than float32 error.** The
reference reports the margin of each decision it makes. At campaign geometry:

| decision | min margin over all queries/rows |
| --- | --- |
| `invert` nearest-centroid argmin (best vs 2nd best) | 1.29e-04 |
| `nprobe` selection boundary (16th vs 17th centroid) | 2.48e-04 |
| exhaustive top-k boundary (10th vs 11th) | 8.67e-05 |
| IVF top-k boundary (10th vs 11th) | 1.32e-03 |
| exact ties anywhere (`n_exact_topk_ties`, `n_nprobe_ties`) | 0 |

Zero exact ties means no decision depended on the tie-break rule, and no
decision depended on `std::partial_sort`'s unspecified ordering of equal keys.

The geometry is why the margins are large: `nb = 4*nlist` with `i % nlist`
assignment puts exactly 4 db vectors at each true centre, ~4.4 away from a
co-located query, while every other cluster sits ~683 away. Top-10 is therefore
4 near neighbours plus 6 drawn from the extreme left tail of the far
distribution, where order-statistic gaps are ~10⁻⁴–10⁰ — far above the tenant's
float32 accumulation error (~10⁻⁴ worst case on a 1024-term sum).

That argument is an upper bound on risk, not a proof. The proof is empirical and
it is stronger: **`id_sum` matched exactly.** Had float32 arithmetic tipped any
of the ~10⁴ decisions the other way, that integer would have differed.

The reference also does not depend on reproducing the tenant's *scan order*.
`hit_less` compares `(dist, id)` lexicographically and ids are distinct, so the
maximum of the heap is always unique and the retained set is exactly the `k`
smallest `(dist, id)` pairs regardless of the order the lists were visited.
That is a property of the tenant's comparator, read at `:106-134`, and it is
what makes a sort-based reference legitimate.

## 6. The anchor is sensitive to its input — the F20 control

A reference that cannot move is the defect it is meant to remedy, so the
reference ships with a control that proves it moves. `--corrupt-frac F` zeroes
the leading fraction of the **list payload** after the codebook and the
assignment are fixed — what a stray `prefault_region`-style write to the mmap'd
list object would do, hitting the approximate scan and the exhaustive scan
equally. It then reports recall twice: self-referentially (the tenant's own
construction) and against the *uncorrupted* exhaustive top-k.

`nlist 1024 dim 64 nb 4096 nq 200 nprobe 4 k 10`, bit-exact back-end:

| `corrupt_frac` | rows zeroed | self-referential recall | recall vs clean truth | `id_sum` |
| ---: | ---: | ---: | ---: | ---: |
| 0.00 | 0 | 0.6660 | 0.6660 | 3762767 |
| 0.05 | 205 | 0.3945 | 0.6500 | 3738789 |
| 0.25 | 1024 | 0.3170 | 0.5540 | 3205553 |

Read this carefully, because the interesting part is not that the numbers move.

Under this corruption model the self-referential recall *does* move. It still
goes undetected, because **neither existing gate has an absolute threshold or an
external reference**:

* `--require-recall` asserts `recall ∈ (0, 1]`. `0.3945` passes. So would `0.02`.
* `live_check` compares arm to arm. Every arm builds the same corrupted index,
  so every arm reports the same `id_sum`, so `ref_id_sum` matches and the gate
  passes.

What catches it is the third column and the `id_sum` column: an absolute figure
computed from something other than the object under test. `3738789 ≠ 3762767`
fails immediately at 5 % corruption. That is the whole point of the exercise,
and it is why the `F20` remedy has to be an external reference rather than a
tighter bound on the existing one.

## 7. Proposed gate wording — handed back, not applied

I did not modify `ivf_gates.py`. The IVF campaign is mid-flight on `c4` and
changing a gate module while it runs would muddy the provenance of the records
it is writing. Recommended for after it lands:

1. **Give `live_check` an external `ref_id_sum`.** Replace the seed-from-first-arm
   in `run_ivf.py:473-474` with the pre-registered constant for the campaign
   geometry, from this document: `id_sum = 147039988` at
   `(nlist 8192, dim 1024, nb 32768, nq 1000, nprobe 16, k 10, kmeans_iters 1,
   train_n 16384, seed 0x1F1FCAFE1234)`. The gate then fails if the *first* arm
   is wrong, which today it cannot.
2. **Replace `--require-recall`'s `(0,1]` with a window.** `recall_at_k` for that
   geometry is `0.5083` and is deterministic — no timing dependence, `reps` and
   `warmups` do not enter it, and `--policy nta` / `--flush-distance` provably do
   not change it (`ivf_flat_bench.cpp:1089`, `:1095`). A window of
   `0.5083 ± 0.001` is defensible; anything looser is decoration.
3. Both numbers are only as good as the seed and geometry they are pinned to.
   The pre-registration must name the full tuple, not just `nprobe` and `k`.

These require a source change to `ivf_flat_bench.cpp` only for item 2, and only
if the window is to be enforced inside the tenant rather than in
`ivf_gates.recall_check`. Enforcing it in `ivf_gates.recall_check` needs no
tenant change and is the smaller move. **Neither is applied here.**

## 8. Reproducing this

```
python3 experiments/asplos/ivf_recall_reference.py --preset silicon --backend f64 --audit-gram
python3 experiments/asplos/ivf_recall_compare.py \
    --binary <scratch>/ivf_flat_bench --backend f32strict \
    --nlist 1024 --dim 64 --nb 4096 --nq 200 --nprobe 4 --k 10 \
    --kmeans-iters 1 --train-n 2048 --exhaustive-probe
```

NumPy 2.5.2 on CPython 3.14.4. The reference takes 9.7 s at campaign geometry
(3.4 s codebook, 3.3 s invert, 2.9 s search); the tenant takes ~6 min for the
same, almost all of it the single-threaded index build.

## 9. Machine and boundary compliance

* **`c4` was not used and not contacted.** No `ssh`, no reads of
  `/home/domin/ivf_run/`. All work ran on `mos181` (Xeon Platinum 8592+), where
  `/home` is local `ext4` — not shared with `c4` — and where
  `run_ivf.py:438-439` refuses to run the campaign at all. No campaign process
  or output of any kind exists on this host.
* **Nothing was built in place.** The build went to
  `/home/domin/ivf_ref_scratch/build_native` via
  `make BUILD=/home/domin/ivf_ref_scratch/build_native`.
* **The live binary is untouched.**
  `benchmarks/e2e/ivf_flat/build/ivf_flat_bench` was
  `sha256 b17ddd4c3ad166e20c442255bfe6d6647671e4368b2cd9776212530bf02c8e6c`,
  `size 104344`, `mtime 2026-09-02 16:20:47` before this work and identical
  after. The `build/` directory has no new entries.
* **Incidental provenance finding, worth keeping.** The scratch build is
  **bit-identical** to the live binary — same `sha256 b17ddd4c…`. So the live
  binary is byte-reproducible from the current untracked
  `src/ivf_flat_bench.cpp` (`sha256 e25278e0…`) with the committed `Makefile`
  flags on this host's toolchain, and every comparison above was made against
  the same machine code the campaign is executing.
* **`ivf_flat_bench.cpp` was read only.** Not modified, not committed, still
  untracked, `mtime 2026-09-02 16:20:05` unchanged. No check here needed a
  source change; item 2 of §7 might, and is described rather than done.
* No `CAT` masks, no hugepages, no quiet-machine requirement — this is a
  correctness check. Small geometries throughout except the campaign cell, which
  the deliverable required by name.
* Untouched: `A1_PROVENANCE_LEDGER_2026-08-28.md`, `INDEX.md`,
  `/home/domin/STREAMING_Paper/`, `gem5/`, every `data/*.jsonl`, and
  `ivf_gates.py`. Committed with `git commit --only` and explicit pathspecs;
  nothing left staged; not pushed.

## 10. Verdict

| Question | Answer |
| --- | --- |
| Is `0.5083` the correct recall for that configuration? | **Yes.** Independently computed as exactly 5083/10000. |
| Is the tenant's vector generation reproducible outside the binary? | **Yes**, bit-exactly, modulo a ≤1 ulp FMA contraction on the `±0.08` noise term that provably changes no decision (§3). |
| Does the tenant's exhaustive path agree with brute force? | **Yes**, in all 5 ladder geometries and at campaign geometry (§4.1, §4.3). |
| Does the tenant's IVF search agree with an independent IVF search? | **Yes** — exact `id_sum` match in **13 of 13** compared cells (10 ladder + 3 at campaign geometry). |
| Any disagreement, and its magnitude? | **None on any decision.** The only residual is `dist_sum`, ≤2.4e-09 relative, which is float32 summation order, not a difference in the answer. |
| Does the campaign now have an absolute anchor? | Yes: `recall_at_k = 0.5083` and `id_sum = 147039988` for the pinned tuple. Wiring it into the gates is §7, deliberately not done here. |
