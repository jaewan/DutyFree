# The fused "tax" is a probe-hit-rate mismatch between two different loops

Found while executing A4's registered morsel sweep (Addendum 4). This is the
session's most consequential result and it requires a paper change.

## What `tab:fused`'s two load-bearing rows actually compare

`run_hot_probe`'s inner loop (`cxl_join_bench.cpp:1685`):

    probe(table, keys[i % keys.size()], &payload);

`keys` is the vector of keys **inserted into the table**, so this probes at a
**100% hit rate**.

`join_range`'s inner loop (`:551-566`):

    if (probe(table, fact[i].fk, &payload)) { r.matches++; r.sum += fact[i].measure; }

`fill_fact` builds the fact array at `hit_rate` (0.5 by default and in every
panel arm): with probability `hit_rate` a real key, otherwise a synthesized
negative key. So this probes at a **50% hit rate** — and a miss in this
open-addressing table walks the linear-probe chain to an empty slot
(`if (e.key == 0) return false;`), which is strictly more work than a hit.

**The quiescent baseline is not "the fused probe without the stream". It is a
different, easier probe workload.**

## The measurement

Changing only `--hit-rate` on the fused kernel, everything else at the campaign
operating point (256 MiB CXL fact, 256 MiB hot table, 1 core, cpu32, n=3):

| configuration | cyc/access |
|---|--:|
| `morsel` (fused), `--hit-rate 0.5` | 88.32, 89.30, 88.42 |
| `morsel` (fused), `--hit-rate 1.0` | **44.13, 44.07, 43.94** |
| `hot-probe` (100% hits by construction) | 55.44, 55.21, 55.06 |

- The hit-rate effect inside one loop is **−44.4 cyc/access (−50%)**.
- The published "tax" is **+31 to +34 cyc/access**, measured across the loops.
- **The hit-rate effect is larger than the entire tax.**
- At a matched hit rate the fused kernel runs at **44.0** against the quiescent
  baseline's **55.2** — the fused arm is **faster**, *while streaming 256 MiB
  from CXL*. **The sign of the "tax" reverses.**

## Why every earlier result now coheres

| result | reading |
|---|---|
| shared-LLC residency 0.00% strict / ≤31% generous | nothing to remove, because the gap is not memory |
| bandwidth-matched queueing ≈ 0 | same |
| stream-side TLB excluded; walks are the victim's | same |
| TMA gate: memory-bound only **15.9%** of Δ | same |
| TMA phase 1: **bad speculation 46.8%** of Δ | **correct in substance.** A 50% hit rate is maximally unpredictable for the branch on `probe`'s return. I withdrew this as "a code-path artifact"; it *is* a code-path artifact, and its cause is now identified rather than dismissed. |
| phase 1b (same workload both arms): Δ = **−0.795** | with the hit rate matched, the stream costs ≈0 — and slightly less than zero |
| morsel sweep flat over 64× (this campaign) | the driver was never the cause |

Two independent routes now agree: **at matched workload, the stream's cost in the
fused organization is ≈0.**

## What this does and does not break

**Breaks — `tab:fused`'s Quiescent row as a baseline, and the 1.47× same-core
tax that derives from it.** Also the sentence that "the effect survives at a
single core, removing every cross-core confound": the single-core effect is the
hit-rate difference. The 1-core pair (`Q_1c` 60.710 → `A_1c` 89.468) is the same
mismatch.

**Does not break — the monotone-harm column, which is the exhibit the panel
wanted as Figure 1.** Every arm in it (`Fused unrestricted` 87.65 → `+CAT 12/20`
105.12 → `8/20` 115.81 → `4/20` 126.86, and `PREFETCHNTA` 98.37) is the *same*
fused 50%-hit workload; only the way mask changes. It remains internally
consistent and statistically solid at 7–17 SE. Likewise the split arms (95.69,
95.37) and all of A6's SMT arms are the same workload throughout.

So the finding removes a *number* the paper leads with and leaves the *argument*
that the panel identified as the paper's strongest exhibit intact.

## Required paper changes

1. **Withdraw the 1.47× same-core fused tax** and the Quiescent row's use as a
   baseline. `Sec3_Mitigation.tex` states it twice (the 88.5/61.7 table row and
   the "60.7→89.5 (1.47×)" single-core sentence); `Appendix.tex` and
   `Sec3_5_DeclarationVsPrediction.tex` refer to it.
2. **Re-baseline the fused claim on a matched-workload comparison.** The correct
   within-workload statement already measured is phase 1b: with the fused loop
   and hit rate held fixed, adding a 256 MiB CXL stream changes cost by
   **−0.795 cyc/access**.
3. **Keep the monotone-harm table**, with a caption noting all its arms share one
   workload, so the comparison across way masks is sound.
4. Disclose the hit-rate asymmetry between the two modes in `app:kernel`, since
   any reader reproducing the "tax" will hit it.

## Provenance

Zero code changed. `--hit-rate` is a committed flag
(`cxl_join_bench.cpp:1771`); the two inner loops were read, not inferred. The
morsel sweep that led here is `run_a4_morsel.sh` with data in
`artifacts/a4_morsel/` (72/72 records): F stays 88.4–90.9 across morsel sizes
256k→16m while hot-probe stays 55.2–58.3, so the gap is +31 to +34 cyc/access at
every size and the driver is excluded.
