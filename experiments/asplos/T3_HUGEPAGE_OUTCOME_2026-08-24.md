# T3 outcome: stream-side TLB pressure is excluded — and the walk counters say why

Pre-registration `T3_HUGEPAGE_PREREG_2026-08-24.md` (`5070dbe`) and runner
`benchmarks/e2e/hash_join/scripts/run_t3_hugepage.sh` (`30e60fd`), both committed
**before** the run. Raw: `benchmarks/e2e/hash_join/artifacts/t3_hugepage/t3.jsonl`,
host state in `t3_state.txt`. mos181 (EMR 8592+), 1 core, panel-verbatim
operating point (`--fact-bytes 256m --hot-bytes 177838489 --morsel 1m --threads 1
--cpu-list 32`), n=5, arms interleaved within each rep.

## Verdict

> **R = −0.088. Stream-side TLB/walk pressure is EXCLUDED (registered threshold
> R ≤ 0.10).** Putting the 256 MB stream on 2 MiB pages does not shrink the fused
> same-thread tax. The private-cache + miss-tracking attribution from the
> 2026-07-29 decomposition stands, and the stream-buffer / MSHR-QoS fork remains
> the live question for T4.

## The data

| arm | n | cyc/access | sd | CoV% | page walks (M) | sd | CoV% | hugetlb pages |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Q_4k | 5 | 61.645 | 3.193 | 5.18 | 23.341 | 0.028 | 0.12 | 0 |
| A_4k | 5 | 91.536 | 2.418 | 2.64 | 31.294 | 0.017 | 0.05 | 0 |
| Q_2m | 5 | 58.672 | 3.837 | 6.54 | 23.329 | 0.012 | 0.05 | 0 |
| A_2m | 5 | 91.185 | 2.491 | 2.73 | 31.152 | 0.072 | 0.23 | **128** |

`Δ_4k = 29.891` cyc, `Δ_2m = 32.512` cyc, **R = −0.0877**.

## The guards

**Guard 1 — the manipulation took, decisively.** All five A_2m reps consumed
exactly **128** node-2 hugetlb pages = 256 MB / 2 MiB; all other arms consumed 0.
So `MAP_HUGETLB` succeeded and the fact array really was on 2 MiB pages — no
silent fallback to `mmap`+`MADV_HUGEPAGE`. This had to be measured externally,
by sampling `node2/.../free_hugepages` during each arm, because `alloc_bytes()`
falls back silently and prints nothing either way, and the JSON's
`anon_huge_kb`/`table_*` fields describe the **hot table**, not the fact array.
`table_kernel_page_kb = 4` in every arm confirms the victim stayed on 4 KiB
pages throughout, as intended.

**Guard 2 — the control holds on the invariant quantity.** Q's page walks are
identical across page-size conditions (23.341 M vs 23.329 M, −0.05%), which is
the control working: the quiescent arm never touches the fact array
(hugetlb_used = 0 there). Its *cyc/access* differs by 2.97 cyc, but that is
bistability, not an effect — see below.

**Guard 3 — operating point.** `Δ_4k = 29.89` cyc against the decomposition's
1-core `Δ_total = 27.31`, i.e. 9.5% higher. The binary has changed since
2026-07-29, so this is reported as a caveat, not silently accepted. R is a
within-T3 ratio and is unaffected.

## Why the null is informative rather than merely negative

The registered R uses Q as a denominator and Q is noisy. The **paired A-arm
comparison** avoids that entirely and says the same thing much more tightly:

| quantity | A_4k | A_2m | change |
|---|--:|--:|--:|
| cyc/access | 91.536 | 91.185 | **−0.38%** |
| page walks | 31.294 M | 31.152 M | **−0.45%** |

And here is the part that matters. The stream's pages went from **65,536 to
128** — a 512× reduction in its translation footprint. Its apparent walk
contribution (A minus Q) went from 7.953 M to 7.811 M: **1.8% removed.**

Those two facts cannot both be true of the stream's *own* translations. At ~121
sweeps of a 256 MB array, 4 KiB pages predict ~7.9 M stream walks and 2 MiB
pages predict ~15 K — a 99.8% reduction. We measured 1.8%. **Therefore the
~8 M extra walks under load are not the stream's translations at all; they are
the victim's**, and they are invariant to the stream's page size.

That is a mechanism, not a null: the load-induced page-walk increase is
**victim-side**, driven by a 170 MB hot table sitting on ~43,500 4 KiB pages —
a footprint that exceeds L2 TLB capacity whatever the stream does.

**The motivated follow-up, now specific rather than speculative:** put the
*victim's* table on 2 MiB pages. T3 could not — the hot table is a
`std::vector<Entry>` on the default allocator, and the pre-registration barred
editing `cxl_join_bench.cpp`. This does not reopen the stream-side question,
which is closed; it opens a different one that the walk counters just pointed
at. It is also cheap (an arena allocator or an `LD_PRELOAD` like the existing
`duckdb_join/tools/thp_arena.c`).

## An incidental finding about `tab:fused` that is not incidental

**The quiescent arm is bimodal.** Sorted per-rep cyc/access:

- Q_4k: 55.62, 61.17, 63.28, 64.05, 64.09
- Q_2m: 55.46, 55.56, 55.79, 62.07, 64.48

Two clusters, near **~55.5** and **~63.5**. Q_2m happened to land in the low mode
3 of 5 times and Q_4k 1 of 5 — which is the entire 2.97 cyc "difference" in
`Δ`, and why R is negative rather than zero.

`run_confirmatory_panel.py` passes `--warmups 2 --reps 1` and runs each label
**once**. So the published `tab:fused` quiescent value of **61.71 is a single
sample from this bimodal distribution**, and it is the denominator of the
1.4737× same-core tax the paper calls its decisive case. The denominator alone
carries roughly ±7% depending on which mode it sampled. Combined with the
ledger's "18/18 cells reproduce exactly" — which is *recomputation from the same
raw files*, not replication — this means **`tab:fused` has no n and no CoV, and
at least one of its two load-bearing cells is bimodal.** That belongs on the
hygiene list beside the runner reconstruction and the way-count caption, and it
raises the priority of establishing n/CoV before that table leads anything.

Note also that the walk counters are extremely stable (CoV 0.05–0.23%) while
cyc/access swings 2.6–6.5%. The bistability is therefore **not** in the memory
access pattern or the translation work — it is in timing. Cause unidentified;
reported as observed, not resolved.

## System state

Nothing was changed. No hugepage pool was resized (node 2 already held 22,000
pages, of which 128 were borrowed by the allocator and returned), no MSR was
written, `setup/*_freeze.sh` was not run, and no source file was edited —
`--huge2m` is a flag `cxl_join_bench` already had. Host state as found is
recorded in `t3_state.txt`.
