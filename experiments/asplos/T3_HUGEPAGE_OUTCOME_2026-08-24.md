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

---

# Addendum 1 — 2026-08-24, same day: two corrections from the code audit

The body above is left verbatim. `T3_CODE_AUDIT_2026-08-24.md` has the full
review; two things in the text above are wrong and are corrected here.

**1. The hot table is 256 MiB, not "~170 MB", and 65,536 pages, not "~43,500".**
`table_capacity()` rounds entries up to a power of two, so `--hot-bytes
177838489` (169.6 MiB) instantiates 16,777,216 × 16 B = **268,435,456 B**, a
1.509× inflation — **80.0%** of the 8592+'s 320 MiB LLC, not 53.0%. Every "170
MB / ~43,500 pages" figure above describes the *requested* size. The conclusion
is unchanged and in fact strengthened: a larger victim footprint makes the
victim-side walk explanation more compelling, not less. This is F9's second
instance and it also affects `Sec3_Mitigation.tex:48` and `tab:fused`'s stated
operating point — see the audit.

**2. `R = −0.088` is withdrawn as a quotable number; its verdict stands.** Two
reasons. `run_hot_probe()` never calls `alloc_bytes()`, so `--huge2m` is a
**no-op** in the Q arm — `Q_4k` and `Q_2m` are the same execution, and R's
denominator is one bimodal configuration sampled n=5 twice. And arm order was
**fixed, not randomized**, so a position effect cannot be separated from
bistability. Report the verdict (stream-side TLB excluded) and the two
statistics that do not depend on Q or on arm order:

- paired A-arm: cyc/access **−0.38%**, page walks **−0.45%**;
- the fact array's pages went 65,536 → 128 (512×, confirmed by 128 consumed
  hugetlb pages) while the stream's apparent walk contribution fell **1.8%**
  against an arithmetic prediction of ~99.8%. A measured-vs-predicted contrast,
  immune to arm order and thermal drift.

Guard 2 is also restated correctly: since Q_2m ≡ Q_4k, it was never a test of the
manipulation. It is a **10-sample variance estimate of one configuration** —
range 55.46–64.48, 16.3% spread, 4 low (~55.6) / 6 high (~63.2) — which is why
the `tab:fused` bimodality finding is stronger than the body states, not weaker.

---

# Addendum 2 — 2026-08-24: run 2, balanced design. Verdict confirmed; the position confound found and quantified.

Pre-registration Addendum 1 (`671a62c`), runner `run_t3_hugepage_v2.sh`
(`671a62c`, defect-fixed at `6a194fb`), analyzer `t3_v2_analyze.py` committed at
`722694e` **before run 2's data existed**. Raw:
`benchmarks/e2e/hash_join/artifacts/t3_hugepage_v2/`, 48/48 records parseable,
per-arm stderr archived. n=12, randomized Latin square, **every arm in every
position exactly 3 times** (verified).

## Verdict: confirmed

> **R = +0.0897, inside the registered "excluded" band (R ≤ 0.10). Stream-side
> TLB pressure is excluded, now under a design in which arm position cannot
> confound the estimate.**

| arm | n | cyc/access | sd | walks (M) | CoV% | hugetlb |
|---|--:|--:|--:|--:|--:|--:|
| Q_4k | 12 | 57.807 | 3.514 | 23.340 | 0.10 | 0 |
| A_4k | 12 | 91.208 | 2.319 | 31.281 | 0.10 | 0 |
| Q_2m | 12 | 60.656 | 4.119 | 23.338 | 0.09 | 0 |
| A_2m | 12 | 91.061 | 1.869 | 31.205 | 0.11 | **128** |

`Δ_4k = 33.401`, `Δ_2m = 30.405`, **R = +0.0897**.

**Primary evidence, and it agrees with run 1:** A-arm cyc/access **−0.16%**,
walks **−0.24%**, and the stream's apparent walk contribution falls **1.0%**
(run 1: 1.8%) against the ~99.8% its 512× page-count reduction predicts. Guard 1
holds — 128 hugetlb pages in every A_2m rep, 0 elsewhere. **The load-induced
page walks are the victim's, in both runs.**

## R's verdict is stable; R's value is noise

Run 1 gave **R = −0.0877**; run 2 gives **R = +0.0897**. Both sit inside the
excluded band and they **straddle zero** — which is what a true-zero effect looks
like when the estimator's denominator is dominated by a noisy quantity. This
retroactively justifies withdrawing run 1's `R` as a point estimate rather than
defending it, and it applies equally to run 2's: **report the verdict, not the
number.**

## The position confound was real, and it explains run 1's sign

Run 2 can test what run 1 could not. The effect exists, and it is **confined to
the quiescent arm, acting through mode selection rather than as a slowdown**:

| | pos 1 | pos 2 | pos 3 | pos 4 |
|---|--:|--:|--:|--:|
| Q arms in the **high** (slow, ~64.1) mode | **4/6** | 3/6 | 2/6 | **1/6** |
| Q arms in the low (~55.8) mode | 2/6 | 3/6 | 4/6 | 5/6 |
| A arms, mean cyc/access | 91.21 | 91.46 | 91.00 | 90.87 |
| A arms, page walks (M) | 31.267 | 31.240 | 31.223 | 31.243 |

The earlier an arm runs in a rep, the more likely the quiescent configuration
lands in its slow mode — monotone across all four positions. The **A arms are
position-insensitive** (means within 0.59 cyc, walks within 0.14%), so this is
not a general warm-up drift affecting everything.

**This quantitatively explains run 1's negative R.** There, `Q_4k` was *always*
position 1 (mode-inflated) and `Q_2m` *always* position 3 (less so), giving
Q_4k 61.645 > Q_2m 58.672. That understates `Δ_4k`, overstates `Δ_2m`, and
drives R negative — exactly what was observed. The audit predicted the confound;
run 2 measured it; it accounts for the sign.

## The bimodality is confirmed, and n=12 is still not enough

Pooled Q (n=24, both labels being the same execution): **14 low (mean 55.79) /
10 high (mean 64.05), spread 16.8%** — run 1 gave 16.3% on 10 samples. Even
under a balanced design at n=12 the two Q labels differ by 2.85 cyc, because
their mode splits differ (Q_4k 3 high / 9 low; Q_2m 7 high / 5 low). The
registered replicate check passes — 2.849 ≤ pooled sd 3.817 — but the lesson for
anyone sizing future runs is that **averaging a bimodal variable needs far more
than 12 samples**, and reporting its mean without the mode split hides the
structure.

This sharpens the `tab:fused` finding rather than softening it. The published
quiescent **61.71** falls in the *sparse region between* the two modes observed
here (55.4–56.2 and 62.9–64.7), matching neither cleanly. With `--reps 1` there
is no way to know which state it sampled — and it is the denominator of the
1.4737× same-core tax.

## F9 confirmed in-band, with a residual gap

`hot_table_instantiated_bytes = 268,435,456` = **256 MiB = 80.0%** of the
8592+'s 320 MiB LLC, recorded in this experiment's own data for the first time.
`HOT_TABLE_ROUNDED` warnings: **0** — because the built binary predates the
commit that added the warning (audit Addendum 1, D8).

Residual gap: the **Q arms report `NA`**. With stderr now archived it is possible
to say why — `run_hot_probe()` emits no `HOT_TABLE` line at all, so the mode that
measures the victim in isolation is the one mode that does not record the
victim's instantiated size. The size is nonetheless known: same `--hot-bytes`,
same `table_capacity()`, and the A arms confirm it.

---

# Addendum 3 — 2026-08-24: the `tab:fused` n=1 claim in this document is RETRACTED

Both the body and Addenda 1–2 above assert that `run_confirmatory_panel.py` runs
each label once and that the published quiescent 61.71 is a single sample. **That
is false.** The panel's `N_REPS = 30` invokes each label 30 times in a shuffled
order, and `results/clos_split/summary.csv` has carried n, CoV and bootstrap CI95
since 2026-07-29: Q16 is a **median of 30, CoV 4.39%, CI95 [60.65, 62.05]**.

Everything else above stands — the stream-side TLB exclusion, the walk arithmetic,
the position-effect measurement, and the observation that this host's quiescent
arm is bimodal *today*. What changes is the inference drawn from that bimodality:
it is a **current property of `mos181`** (July's `panel_Q_1c` was unimodal at CoV
1.64%), not a defect in the published table. Authoritative record and the full
n/CoV tables: `TAB_FUSED_N_COV_2026-08-24.md`.
