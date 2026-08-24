# tab:fused's n and CoV — already established since 2026-07-29, and my claims today were wrong

Asked to establish n and CoV for `tab:fused`. **They were already established.**
The task reduced to reading committed artifacts, closing one narrow real gap, and
retracting a false claim I propagated into four documents today.

## 1. The retraction, stated plainly

| what I said today | what is true |
|---|---|
| "`run_confirmatory_panel.py` passes `--reps 1` and runs each label **once**" | `--reps 1` is the *benchmark's internal* rep count. The panel's own `N_REPS = 30` (`run_confirmatory_panel.py:41`) invokes **each label 30 times**. |
| "`tab:fused` has **no n and no CoV**" | `results/clos_split/summary.csv` has carried `n`, `*_cov` and bootstrap `*_ci95_lo/hi` for **both** metrics, for every label, since **2026-07-29**. |
| "the published quiescent **61.71 is a single sample** from a bimodal distribution" | It is the **median of n=30**, CoV **4.39%**, CI95 **[60.65, 62.05]**. |
| "±7% uncertainty from the denominator alone" | The denominator's CI95 is **±1.1%**. |
| "arm order was fixed in the panel" | `run_sequence()` builds all `(label, rep)` pairs and **`rng.shuffle`s them** under a fixed seed — the panel was order-randomized from the start. |
| "establishing n/CoV is a hygiene blocker" | It was never open. |

Every raw label carries exactly 30 files (22 labels × 30 = the 660 in
`results/clos_split/raw/`), which corroborates `N_REPS` independently of the code.

**This is F11 again, by me, for the third time today** — after the unread
2026-07-29 decomposition and the stale ledger F1 entry. The mechanism was the
same each time: I read one part of an artifact (`--reps 1` in the argument
builders), inferred the rest, and did not read the function that actually
executes the sequence. The rule I wrote this morning — *before declaring anything
open, read what is already there* — would have caught all three.

## 2. What `tab:fused` actually is

Medians of n=30, order-randomized, with CoV and bootstrap CI95 (cyc/access):

| row | label | n | median | CoV | CI95 |
|---|---|--:|--:|--:|---|
| Quiescent (16c) | `Q16` | 30 | 61.711 | 4.39% | [60.65, 62.05] |
| Fused, unrestricted | `A3_16` | 30 | 88.454 | 1.48% | [88.18, 88.92] |
| Fused + `PREFETCHNTA` | `E16` | 30 | 98.365 | 1.31% | [97.62, 98.83] |
| Split, no CAT | `Dref` | 30 | 95.688 | 2.11% | [95.45, 96.13] |
| Split + CAT 1-way | `C_1way` | 30 | 95.369 | 2.03% | [94.65, 95.96] |
| Fused + CAT 4/20 | `B16` | 30 | 126.861 | 2.99% | [126.50, 127.07] |
| Quiescent (1c) | `Q_1c` | 30 | 60.710 | 1.64% | [60.33, 60.77] |
| Fused (1c) | `A_1c` | 30 | 89.468 | 0.89% | [89.30, 89.85] |

The ledger's same-core 1.4737× is `A_1c/Q_1c` = 89.468/60.710 — both n=30.

## 3. The one genuine gap, now closed

The three `bsweep_*` cells are in `raw/` but **not** in `summary.csv` (their runner
is the one the ledger records as absent), so they had n but no published
dispersion. Computed here from their 30 raw files each:

| row | label | n | cyc median | CoV | thr median | CoV |
|---|---|--:|--:|--:|--:|--:|
| Fused + CAT 20/20 | `bsweep_A_bsweep` | 30 | 87.653 | **1.48%** | 336.993 | 1.40% |
| Fused + CAT 12/20 | `bsweep_B_12way` | 30 | 105.123 | **5.29%** | 281.024 | 5.29% |
| Fused + CAT 8/20 | `bsweep_B_8way` | 30 | 115.814 | **5.24%** | 253.356 | 5.68% |

## 4. The monotone-harm column is statistically solid

This is what the question was really for. Comparing medians at n=30, the
standard error is roughly `sd/√30`, so each CAT step is many SEs wide:

| step | Δ cyc/access | pooled SE | Δ/SE |
|---|--:|--:|--:|
| 20/20 → 12/20 | +17.47 | ≈1.05 | **≈17** |
| 12/20 → 8/20 | +10.69 | ≈1.50 | **≈7** |
| 8/20 → 4/20 | +11.05 | ≈1.31 | **≈8** |

Every step in "tightening CAT makes the fused victim monotonically worse" is far
outside sampling noise. `PREFETCHNTA` (98.365, CoV 1.31%) versus unrestricted
(88.454, CoV 1.48%) is likewise ≈27 SE. **The proposed Figure 1 is sound on its
statistics.** Its outstanding defects are the other ones already on record — the
missing bsweep runner, the way count carried by filename, and the 53%→80%
operating-point misstatement — not n or CoV.

## 5. A real finding that came out of the comparison

`panel_Q_1c` in July: n=30, **unimodal**, 58.0–62.0, CoV 1.64%. The *same
configuration* measured today in T3 run 2: **bimodal**, 55.4–64.7, 16.8% spread.
And `panel_Q16` in July already showed a low cluster (55.1–57.4, 8 of 30) beside
a high one (59.3–63.3, 22 of 30), CoV 4.39%.

So the two-state behaviour existed at 16 cores in July and has since **appeared
at 1 core**. That is a change in `mos181`'s state between 2026-07-29 and today,
not a property of the benchmark. Two consequences:

1. **T3's absolute cyc/access values are not comparable to the panel's.** T3's
   internal comparisons (4 KiB vs 2 MiB, same session, balanced order) are
   unaffected — which is why its verdict stands.
2. **Anyone re-running the panel today will measure different variance than
   July's CoV column reports.** If the panel is ever re-run, that must be stated
   rather than presented as a replication.

The bimodality is therefore still worth reporting — but as a *current host*
property that a future re-run must contend with, **not** as a defect in the
published table.
