#!/usr/bin/env python3
"""Independent correctness reference for the IVF-Flat search cell (remedy for F20).

F20 is the defect class "a correctness gate whose reference is derived from the
same input it is meant to validate".  The IVF-Flat campaign has two gates and
both are in the class:

  * ivf_gates.live_check() seeds ref_id_sum from the first arm, so it proves the
    arms agree and never checks the first arm against anything.
  * the tenant's own recall_at_k() compares the approximate search against an
    exhaustive scan over the *same* mmap'd list array, so a corrupted array
    corrupts both sides equally and recall stays plausible.

This file is the absolute anchor those gates lack.  It re-derives the vectors,
the coarse quantizer, the inverted lists, the nprobe selection, the approximate
top-k, the exhaustive top-k and recall@k from the *documented behaviour* of
benchmarks/e2e/ivf_flat/src/ivf_flat_bench.cpp, in Python/NumPy only.  It does
not call, link, load, or import the C++ tenant, and it does not read anything
the tenant produced.  Its only inputs are (nlist, dim, nb, nq, nprobe, k,
kmeans_iters, train_n, seed).  Comparison against the tenant happens outside
this module, by running the tenant and diffing the JSON it prints.

Behaviour reproduced (ivf_flat_bench.cpp, read 2026-09-04):

  SplitMix64            :142-153   x += 0x9e3779b97f4a7c15; two xor-multiply
                                   rounds; u01 = (next()>>11) * 2^-53 evaluated
                                   in double then narrowed to float; uniform =
                                   lo + (hi-lo)*u01 in float32.
  generate_clustered    :598-606   x[i][d] = centers[i % nlist][d] +
                                   uniform(-noise, noise), i outer / d inner.
  draw order            :859-866   nlist*dim centers with uniform(-1,1), then
                                   nb*dim db noise, then nq*dim query noise,
                                   all from one stream seeded with cfg.seed;
                                   noise = 0.08f for both db and queries.
  kmeans                :560-595   separate stream seeded seed ^ 0x6B6D65616E73
                                   ("kmeans"); partial Fisher-Yates picks nlist
                                   distinct training rows as initial centroids;
                                   `iters` Lloyd steps accumulating in double,
                                   writing float32; empty clusters keep their
                                   previous centroid.
  nearest_centroid      :222-233   strict `<`, so ties go to the lowest index.
  invert                :608-635   every db row assigned to its nearest
                                   centroid; list payload ids are the original
                                   db row indices.
  nprobe_lists          :235-247   the min(nprobe, nlist) centroids with the
                                   smallest distance to the query.
  TopK                  :102-140   k smallest by (dist, id) lexicographically --
                                   hit_less/better_than_worst compare dist then
                                   id, so the result is independent of scan
                                   order and the reference can reproduce it with
                                   a lexicographic sort.
  exact_query           :552-558   the same top-k over all nb rows.
  recall_at_k           :648-666   mean over queries of |ivf_k n exact_k| / k.
  id_sum / dist_sum     :909-929   sum of top-k ids and of top-k distances over
                                   the final measured batch.

Two distance back-ends, because the tenant's l2sq (:201-220) sums float32 in
four lanes strided by four and the compiler is free to contract and to widen
that reduction:

  f32strict  bit-faithful replay of the four-lane float32 accumulation, with
             --contract nofma (fl32(s + fl32(d*d))) or --contract fma
             (fl32(s + d*d), one rounding).  Exact, but O(pairs*dim) in NumPy,
             so it is for small geometries where it validates the pipeline.
  f64        float64 Gram-matrix distances, ~1e-13 absolute error at silicon
             geometry.  Used for the silicon configuration, together with a
             decision-margin report that shows how much slack every argmin /
             top-k / nprobe decision had, so that "float64 and float32 agree"
             is demonstrated rather than assumed.

Usage:
  ivf_recall_reference.py --preset silicon --backend f64 --json
  ivf_recall_reference.py --preset tiny --backend f32strict --contract nofma
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np

U64 = np.uint64
F32 = np.float32
F64 = np.float64

GOLDEN = U64(0x9E3779B97F4A7C15)
MIX1 = U64(0xBF58476D1CE4E5B9)
MIX2 = U64(0x94D049BB133111EB)
KMEANS_SALT = U64(0x6B6D65616E73)  # "kmeans"
DEFAULT_SEED = 0x1F1FCAFE1234
NOISE = 0.08

# Presets, transcribed from apply_preset() (:759-810).  `silicon` leaves nb at
# the struct default of 256, which is < nlist, so the preset raises it to
# nlist*4 = 32768 -- the same value run_ivf.py passes explicitly.
PRESETS = {
    "tiny": dict(nlist=8, dim=16, nb=256, nq=64, nprobe=2, k=4,
                 kmeans_iters=8, train_n=0),
    "silicon": dict(nlist=8192, dim=1024, nb=32768, nq=1000, nprobe=16, k=10,
                    kmeans_iters=1, train_n=16384),
    "gem5": dict(nlist=1024, dim=1024, nb=4096, nq=64, nprobe=8, k=10,
                 kmeans_iters=2, train_n=8192),
    "list_dom": dict(nlist=128, dim=256, nb=262144, nq=48, nprobe=32, k=10,
                     kmeans_iters=3, train_n=16384),
}


# ---------------------------------------------------------------------------
# SplitMix64
# ---------------------------------------------------------------------------
def splitmix64(seed: int, count: int, offset: int = 0) -> np.ndarray:
    """The `count` outputs of SplitMix64(seed) starting at call `offset`.

    The state update is a pure counter (x += GOLDEN), so the state before the
    i-th call (1-based) is seed + i*GOLDEN mod 2**64 and the stream is random
    access -- no need to walk it.
    """
    i = np.arange(offset + 1, offset + count + 1, dtype=U64)
    with np.errstate(over="ignore"):
        z = U64(seed & 0xFFFFFFFFFFFFFFFF) + i * GOLDEN
        z = (z ^ (z >> U64(30))) * MIX1
        z = (z ^ (z >> U64(27))) * MIX2
    return z ^ (z >> U64(31))


def u01(z: np.ndarray) -> np.ndarray:
    """(next() >> 11) * 0x1.0p-53 in double, narrowed to float.

    next()>>11 < 2**53 so the widening is exact and the scale is a power of two,
    hence the float64 product is exact and only the narrowing rounds.
    """
    return ((z >> U64(11)).astype(F64) * (2.0**-53)).astype(F32)


def uniform(z: np.ndarray, lo: float, hi: float, contract: str) -> np.ndarray:
    """lo + (hi-lo)*u01() in float32.

    `contract` selects whether the multiply-add is contracted into an FMA.  The
    two differ by at most one ulp, and not at all when (hi-lo) is a power of two
    -- which is the case for the centres, uniform(-1, 1), where the product
    2*u01 is exact.  Only the +-0.08 noise is affected.
    """
    lo32, hi32 = F32(lo), F32(hi)
    span = F32(hi32 - lo32)
    u = u01(z)
    if contract == "fma":
        # one rounding: the float32 product is exact in float64
        return (F64(span) * u.astype(F64) + F64(lo32)).astype(F32)
    return (lo32 + (span * u).astype(F32)).astype(F32)


# ---------------------------------------------------------------------------
# Vector generation
# ---------------------------------------------------------------------------
def generate(cfg: dict, contract: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """true_centers, db, queries -- one stream, in the tenant's draw order."""
    nlist, dim, nb, nq = cfg["nlist"], cfg["dim"], cfg["nb"], cfg["nq"]
    seed = cfg["seed"]

    n_ctr = nlist * dim
    centers = uniform(splitmix64(seed, n_ctr), -1.0, 1.0, contract)
    centers = centers.reshape(nlist, dim)

    def clustered(n: int, offset: int) -> np.ndarray:
        noise = uniform(splitmix64(seed, n * dim, offset), -NOISE, NOISE, contract)
        out = centers[np.arange(n) % nlist] + noise.reshape(n, dim)
        return out.astype(F32)

    db = clustered(nb, n_ctr)
    queries = clustered(nq, n_ctr + nb * dim)
    return centers, db, queries


# ---------------------------------------------------------------------------
# Distance back-ends
# ---------------------------------------------------------------------------
def l2sq_f64(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """|a_i - b_j|^2 for every pair, float64 via the Gram identity."""
    a64, b64 = a.astype(F64), b.astype(F64)
    d = (a64 * a64).sum(1)[:, None] + (b64 * b64).sum(1)[None, :]
    d -= 2.0 * (a64 @ b64.T)
    np.maximum(d, 0.0, out=d)
    return d


def l2sq_f64_direct(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Same thing without the Gram identity, to audit its cancellation."""
    out = np.empty((a.shape[0], b.shape[0]), dtype=F64)
    b64 = b.astype(F64)
    for i in range(a.shape[0]):
        diff = a[i].astype(F64) - b64
        out[i] = (diff * diff).sum(1)
    return out


def l2sq_f32strict(a: np.ndarray, b: np.ndarray, contract: str) -> np.ndarray:
    """Bit-faithful replay of the tenant's l2sq (:201-220).

    Four float32 lanes strided by four, accumulated in increasing i, then
    s = ((s0+s1)+s2)+s3 in float32, then the scalar tail.  Vectorised across
    pairs, sequential across the dim so that every intermediate rounds exactly
    where the C++ rounds.
    """
    na, nb_, dim = a.shape[0], b.shape[0], a.shape[1]
    body = (dim // 4) * 4
    out = np.empty((na, nb_), dtype=F32)
    for i in range(na):
        diff = (a[i][None, :] - b).astype(F32)          # float32 subtract, exact op
        lanes = np.zeros((nb_, 4), dtype=F32)
        for t in range(0, body, 4):
            d = diff[:, t:t + 4]
            if contract == "fma":
                lanes = (lanes.astype(F64) + d.astype(F64) ** 2).astype(F32)
            else:
                lanes = (lanes + (d * d).astype(F32)).astype(F32)
        s = (lanes[:, 0] + lanes[:, 1]).astype(F32)
        s = (s + lanes[:, 2]).astype(F32)
        s = (s + lanes[:, 3]).astype(F32)
        for t in range(body, dim):                       # tail, scalar in C++
            d = diff[:, t]
            if contract == "fma":
                s = (s.astype(F64) + d.astype(F64) ** 2).astype(F32)
            else:
                s = (s + (d * d).astype(F32)).astype(F32)
        out[i] = s
    return out.astype(F64)


class Distances:
    """Chunked pairwise-distance provider for the chosen back-end."""

    def __init__(self, backend: str, contract: str, chunk: int = 2048):
        self.backend = backend
        self.contract = contract
        self.chunk = chunk

    def rows(self, a: np.ndarray, b: np.ndarray):
        """Yield (start, block) so callers never hold the full matrix."""
        step = max(1, self.chunk if self.backend == "f64" else 64)
        for s in range(0, a.shape[0], step):
            blk = a[s:s + step]
            if self.backend == "f64":
                yield s, l2sq_f64(blk, b)
            else:
                yield s, l2sq_f32strict(blk, b, self.contract)


# ---------------------------------------------------------------------------
# Argmin / top-k with the tenant's tie rules
# ---------------------------------------------------------------------------
def assign_nearest(dist: Distances, x: np.ndarray, centroids: np.ndarray):
    """Nearest centroid per row, ties to the lowest index (strict `<`).

    Also returns, per row, the gap between the best and second-best centroid,
    which is the slack the float32 tenant needs in order to make the same call.
    """
    n = x.shape[0]
    best = np.empty(n, dtype=np.int64)
    gap = np.empty(n, dtype=F64)
    for s, blk in dist.rows(x, centroids):
        idx = np.argmin(blk, axis=1)                     # first minimum: ties low
        best[s:s + blk.shape[0]] = idx
        part = np.partition(blk, 1, axis=1)[:, :2]
        gap[s:s + blk.shape[0]] = part[:, 1] - part[:, 0]
    return best, gap


def topk_lex(d: np.ndarray, ids: np.ndarray, k: int) -> np.ndarray:
    """The k smallest by (dist, id) lexicographically -- the TopK heap result.

    Takes every candidate whose distance is <= the k-th smallest distance (so
    exact ties cannot be dropped before the id tie-break is applied) and then
    lexsorts that shortlist.
    """
    if d.size <= k:
        return ids[np.lexsort((ids, d))]
    cut = np.partition(d, k - 1)[k - 1]
    sel = np.flatnonzero(d <= cut)
    order = np.lexsort((ids[sel], d[sel]))[:k]
    return ids[sel[order]]


def topk_lex_with_dist(d: np.ndarray, ids: np.ndarray, k: int):
    if d.size <= k:
        o = np.lexsort((ids, d))
        return ids[o], d[o]
    cut = np.partition(d, k - 1)[k - 1]
    sel = np.flatnonzero(d <= cut)
    order = np.lexsort((ids[sel], d[sel]))[:k]
    return ids[sel[order]], d[sel[order]]


def kth_gap(d: np.ndarray, k: int) -> float:
    """Distance between the k-th and (k+1)-th smallest: the top-k slack."""
    if d.size <= k:
        return float("inf")
    part = np.partition(d, k)[: k + 1]
    part.sort()
    return float(part[k] - part[k - 1])


# ---------------------------------------------------------------------------
# Coarse quantizer
# ---------------------------------------------------------------------------
def kmeans_codebook(dist: Distances, train: np.ndarray, nlist: int,
                    iters: int, seed: int):
    """Reproduce kmeans() (:560-595).  Returns (codebook, diagnostics)."""
    nt, dim = train.shape
    if nt < nlist:
        raise SystemExit(f"k-means needs nt >= nlist (nt={nt} nlist={nlist})")

    # Partial Fisher-Yates over its own stream; nlist next() draws, in order.
    draws = splitmix64(int(seed) ^ int(KMEANS_SALT), nlist)
    pick = np.arange(nt, dtype=np.int64)
    chosen = np.empty(nlist, dtype=np.int64)
    for i in range(nlist):
        j = i + int(draws[i] % U64(nt - i))
        pick[i], pick[j] = pick[j], pick[i]
        chosen[i] = pick[i]
    codebook = train[chosen].copy()

    diag = {"lloyd_min_gap": [], "lloyd_empty": []}
    for _ in range(max(0, iters)):
        assign, gap = assign_nearest(dist, train, codebook)
        acc = np.zeros((nlist, dim), dtype=F64)
        np.add.at(acc, assign, train.astype(F64))
        cnt = np.bincount(assign, minlength=nlist)
        live = cnt > 0
        codebook[live] = (acc[live] / cnt[live][:, None]).astype(F32)
        diag["lloyd_min_gap"].append(float(gap.min()))
        diag["lloyd_empty"].append(int((~live).sum()))
    return codebook, diag


# ---------------------------------------------------------------------------
# The reference run
# ---------------------------------------------------------------------------
def run(cfg: dict, backend: str, contract: str, audit_gram: bool = False,
        corrupt_frac: float = 0.0) -> dict:
    """Compute the reference.  `corrupt_frac` is the F20 sensitivity control.

    With corrupt_frac > 0 the leading fraction of the *list payload* is zeroed
    after the codebook and the list assignment are fixed -- i.e. exactly what a
    prefault_region-style mutation of the mmap'd list object would do, hitting
    the approximate scan and the exhaustive scan equally.  The run then reports
    recall two ways:

      recall_at_k      approximate vs exhaustive over the *same* corrupted array.
                       This is the tenant's own construction (:973-984), and it
                       is the number that stays plausible under corruption.
      recall_vs_clean  approximate over the corrupted array vs the exhaustive
                       top-k of the *uncorrupted* vectors -- an absolute measure,
                       which collapses.

    The gap between the two is the size of the blind spot F20 names, and it is
    also this reference's proof that it is not itself invariant to its input.
    """
    t0 = time.time()
    dist = Distances(backend, contract)
    nlist, dim, nb, nq = cfg["nlist"], cfg["dim"], cfg["nb"], cfg["nq"]
    nprobe, k = min(cfg["nprobe"], nlist), cfg["k"]

    centers, db, queries = generate(cfg, contract)
    gen_fp = {
        "centers_sha": _sha(centers),
        "db_sha": _sha(db),
        "queries_sha": _sha(queries),
        "db_sum_f64": float(db.astype(F64).sum()),
    }

    nt = min(cfg["train_n"], nb) if cfg["train_n"] > 0 else nb
    codebook, kdiag = kmeans_codebook(dist, db[:nt], nlist, cfg["kmeans_iters"],
                                      cfg["seed"])
    t_cb = time.time()

    # invert(): every db row to its nearest centroid, ids are db row indices.
    assign, assign_gap = assign_nearest(dist, db, codebook)
    counts = np.bincount(assign, minlength=nlist)
    order = np.argsort(assign, kind="stable")            # list payload order
    starts = np.concatenate(([0], np.cumsum(counts)))
    t_inv = time.time()

    # F20 sensitivity control: mutate the list payload the way a stray
    # prefault/mmap write would, after the index is already built.
    db_clean = db
    n_corrupt = 0
    if corrupt_frac > 0.0:
        n_corrupt = int(round(corrupt_frac * nb))
        db = db.copy()
        db[order[:n_corrupt]] = F32(0.0)

    # Coarse distances query -> codebook, for the nprobe selection.
    q_cb = np.empty((nq, nlist), dtype=F64)
    for s, blk in dist.rows(queries, codebook):
        q_cb[s:s + blk.shape[0]] = blk

    ivf_ids = np.zeros((nq, k), dtype=np.int64)
    exact_ids = np.zeros((nq, k), dtype=np.int64)
    exact_ids_clean = np.zeros((nq, k), dtype=np.int64)
    ivf_d = np.zeros((nq, k), dtype=F64)
    probe_gaps = np.empty(nq, dtype=F64)
    ivf_gaps = np.empty(nq, dtype=F64)
    exact_gaps = np.empty(nq, dtype=F64)
    cand_counts = np.empty(nq, dtype=np.int64)

    # Exhaustive distances query -> db, chunked over queries.
    qstep = 64 if backend == "f64" else 8
    for s in range(0, nq, qstep):
        qblk = queries[s:s + qstep]
        if backend == "f64":
            dq = l2sq_f64(qblk, db)
            dq_clean = l2sq_f64(qblk, db_clean) if n_corrupt else None
        else:
            dq = l2sq_f32strict(qblk, db, contract)
            dq_clean = l2sq_f32strict(qblk, db_clean, contract) if n_corrupt else None
        for r in range(qblk.shape[0]):
            q = s + r
            row = dq[r]
            all_ids = np.arange(nb, dtype=np.int64)
            exact_ids[q] = topk_lex(row, all_ids, k)
            exact_gaps[q] = kth_gap(row, k)
            exact_ids_clean[q] = (topk_lex(dq_clean[r], all_ids, k)
                                  if n_corrupt else exact_ids[q])

            cd = q_cb[q]
            probe = np.argpartition(cd, nprobe - 1)[:nprobe] if nprobe < nlist \
                else np.arange(nlist)
            if nprobe < nlist:
                srt = np.partition(cd, nprobe)[: nprobe + 1]
                srt.sort()
                probe_gaps[q] = srt[nprobe] - srt[nprobe - 1]
            else:
                probe_gaps[q] = float("inf")
            cand = np.concatenate([order[starts[c]:starts[c + 1]] for c in probe]) \
                if nprobe else np.empty(0, dtype=np.int64)
            cand_counts[q] = cand.size
            if cand.size == 0:
                ivf_gaps[q] = float("inf")
                continue
            sub = row[cand]
            ids_k, d_k = topk_lex_with_dist(sub, cand, k)
            ivf_ids[q, :ids_k.size] = ids_k
            ivf_d[q, :d_k.size] = d_k
            ivf_gaps[q] = kth_gap(sub, k)
    t_search = time.time()

    hits = np.array([np.intersect1d(ivf_ids[q], exact_ids[q]).size for q in range(nq)])
    recall = float(hits.sum() / (k * nq))
    hits_clean = np.array([np.intersect1d(ivf_ids[q], exact_ids_clean[q]).size
                           for q in range(nq)])
    recall_vs_clean = float(hits_clean.sum() / (k * nq))
    id_sum = int(ivf_ids.sum())
    dist_sum = float(ivf_d.astype(F32).astype(F64).sum())

    out = {
        "reference": "ivf_recall_reference.py",
        "independent_of_tenant": True,
        "backend": backend,
        "contract": contract,
        "config": dict(cfg, nprobe_eff=nprobe),
        "recall_at_k": recall,
        "hits_total": int(hits.sum()),
        "hits_denominator": int(k * nq),
        "id_sum": id_sum,
        "dist_sum": dist_sum,
        "corruption_control": {
            "corrupt_frac": corrupt_frac,
            "rows_zeroed": n_corrupt,
            "recall_at_k_self_referential": recall,
            "recall_at_k_vs_clean_truth": recall_vs_clean,
        },
        "generation_fingerprint": gen_fp,
        "list_stats": {
            "nonempty_lists": int((counts > 0).sum()),
            "max_list": int(counts.max()),
            "min_list": int(counts.min()),
            "mean_candidates_per_query": float(cand_counts.mean()),
        },
        "kmeans": kdiag,
        "decision_margins": {
            "min_invert_argmin_gap": float(assign_gap.min()),
            "min_nprobe_boundary_gap": float(probe_gaps.min()),
            "min_exact_topk_gap": float(exact_gaps.min()),
            "min_ivf_topk_gap": float(ivf_gaps.min()),
            "n_exact_topk_ties": int((exact_gaps == 0).sum()),
            "n_nprobe_ties": int((probe_gaps == 0).sum()),
        },
        "timing_sec": {
            "codebook": t_cb - t0,
            "invert": t_inv - t_cb,
            "search": t_search - t_inv,
            "total": time.time() - t0,
        },
    }

    if audit_gram:
        m = min(8, nq)
        g = l2sq_f64(queries[:m], db)
        dd = l2sq_f64_direct(queries[:m], db)
        out["gram_audit_max_abs_err"] = float(np.abs(g - dd).max())

    return out


def _sha(a: np.ndarray) -> str:
    import hashlib
    return hashlib.sha256(np.ascontiguousarray(a, dtype=F32).tobytes()).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--preset", choices=sorted(PRESETS), default=None)
    for name, default in (("nlist", 8), ("dim", 16), ("nb", 256), ("nq", 64),
                          ("nprobe", 2), ("k", 4), ("kmeans_iters", 8),
                          ("train_n", 0)):
        ap.add_argument("--" + name.replace("_", "-"), type=int, default=None,
                        dest=name, help=f"default {default}")
    ap.add_argument("--seed", type=lambda s: int(s, 0), default=DEFAULT_SEED)
    ap.add_argument("--backend", choices=("f64", "f32strict"), default="f64")
    ap.add_argument("--contract", choices=("nofma", "fma"), default="nofma")
    ap.add_argument("--audit-gram", action="store_true",
                    help="cross-check the Gram identity against direct float64")
    ap.add_argument("--corrupt-frac", type=float, default=0.0, dest="corrupt_frac",
                    help="F20 control: zero this fraction of the list payload "
                         "after the index is built, and report recall both "
                         "self-referentially and against clean ground truth")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cfg = dict(nlist=8, dim=16, nb=256, nq=64, nprobe=2, k=4, kmeans_iters=8,
               train_n=0)
    if args.preset:
        cfg.update(PRESETS[args.preset])
        cfg["preset"] = args.preset
    for name in ("nlist", "dim", "nb", "nq", "nprobe", "k", "kmeans_iters",
                 "train_n"):
        if getattr(args, name) is not None:
            cfg[name] = getattr(args, name)
    if cfg["nb"] < cfg["nlist"]:                          # preset rule (:780)
        cfg["nb"] = cfg["nlist"] * 4
    cfg["seed"] = args.seed

    res = run(cfg, args.backend, args.contract, args.audit_gram, args.corrupt_frac)
    if args.json:
        print(json.dumps(res))
    else:
        print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
