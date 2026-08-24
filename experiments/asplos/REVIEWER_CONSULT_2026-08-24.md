# Status for the review panel — 2026-08-24, after executing T1–T3 and rescoping T4

Read §1 first. **Four of the findings I reported to you earlier today were wrong,
two of them in ways that shaped your recommendations.** Everything below is
committed with provenance; the retractions are stated before the results so you
can calibrate what to trust.

---

## 1. Retractions, in order of how much they affected your advice

**R1 — "The intro's WB/WC bandwidth pair is falsified on three hosts; delete
it." WITHDRAWN.** I measured the wrong arm. The paper's WC arm is `wc_ntdqa` →
`mmap("/dev/cxl_wc")`, a genuine **WC memory type** (`pgprot_writecombine` with
`MOVNTDQA`, stated in `Sec2:30`). What I measured was
`benchmarks/bench/aggressor/stream_wc`, which is `MOVNTDQA` on **write-back
anonymous pages** — the same aggressor implements that separately as `wb_ntdqa`.
Different memory type; my registered falsifier fired against a claim it could not
reach. On the correct arms, from an audit that **predates today**
(`experiments/phase1/e4_hygiene/RESULTS.md`, n=12): WB 12.43, WC 3.20, **ratio
3.882 against the paper's implied 3.762 — `corroborated` under my own registered
threshold (≥3.0), not `falsified` (<2.0)**. Also withdrawn: my claim that
"4.2 GB/s" was gem5's 4.17 mislabelled. It is a real AMD WC measurement.

*Effect on you:* your R5 accepted "the 15.8/4.2 pair is N7-class" and put it on
the repair list. Half right — it is not sourced in the repo *as a bandwidth
claim*, but it **was** audited, with CIs, and the ratio holds. Your procedural
lesson ("a review inherits provenance rot from the text it reviews") stands and
now has a second instance running the other way: I inherited nothing, I invented
it.

**R2 — "`tab:fused` has no n and no CoV; establishing them is a hygiene
blocker." WITHDRAWN.** `run_confirmatory_panel.py:41` sets `N_REPS = 30`, and
`run_sequence()` shuffles every `(label, rep)` pair under a fixed seed. The panel
ran **each label 30 times in randomized order**, and `summary.csv` has carried
`n`, `*_cov` and bootstrap `*_ci95` for both metrics **since 2026-07-29**. 660
raw files = 22 labels × 30, corroborating it independently of the code. So the
quiescent 61.71 is a **median of 30, CoV 4.39%, CI95 [60.65, 62.05]** — not a
single sample, and my "±7% from the denominator" was wrong by ~6×. I misread the
benchmark's internal `--reps 1` as the panel's rep count.

*Effect on you:* your item "n and CoV for `tab:fused`" comes **off** the list.

**R3 — "The fused-tax decomposition is the new critical path; ~69% is
undecomposed." WITHDRAWN.** It ran **2026-07-29** — pre-registered, three
instruments, n=30, committed report and runners. I had not read it.

**R4 — `T3`'s `R` withdrawn as a quotable number** (verdict stands). Run 1 gave
−0.0877 under fixed arm order; run 2, balanced, gives +0.0897. Both inside the
"excluded" band, straddling zero.

**All four are the same mechanism: read part of an artifact, infer the rest.**
Three of the four produced *false adverse findings about our own work*; R1
produced a false "delete this from the paper" recommendation against a claim that
reproduces.

---

## 2. What was executed, and what survives

### T2 (bandwidth) — verdict retracted, three by-products survive
n=5 × 6 arms × 3 hosts, CoV ≤1.31%, independently re-derived from
`total_bytes/elapsed_sec`.
- **`stream_wc` ≡ `stream_nt`**: same program plus an MSR warning, load loops
  md5-identical, confirmed by measurement on three hosts. So `stream_nt.c`'s
  pre-registered *"if D ≈ C the NT hint is honored"* reading is **circular and
  void**. Nothing may cite it as an H4 test.
- **New arm `stream_wc_nopf`** (`MOVNTDQA` + prefetchers off, read-back
  verified): C′/C ≈ 0.68–0.71 — a statement about `MOVNTDQA`-on-WB, not WC.
- **Hardware prefetch contributes only ~6% of WB stream bandwidth** on Intel
  local DRAM at a 2 GB region (B/A = 0.944 / 0.940). New. Relevant to your §2a:
  the "prefetch is what buys the bandwidth" premise does **not** hold on local
  DRAM; it is a far-memory claim and must be scoped as one.

### T3 (hugepage/TLB) — closed, and it localises the effect
Run 2: n=12, randomized **Latin square** (every arm in every position exactly
3×), 48/48 records parseable, stderr archived. **R = +0.0897, stream-side TLB
excluded.**

The primary evidence is arithmetic and immune to order or timing: the stream's
pages went **65,536 → 128** (512×, confirmed by 128 consumed hugetlb pages), yet
its apparent walk contribution fell only **1.0%** (run 1: 1.8%) against the
~99.8% that reduction predicts. **Therefore the load-induced page walks are the
victim's, not the stream's**, and are invariant to the stream's page size.

Your TLB hypothesis was correct in target and wrong in citation (`AnonHugePages=0`
is not in the repo); the claim held for a better reason — `THP=madvise` plus no
`--huge2m` in any panel arg builder.

**A position effect exists and is now measured**, which run 1 could not do: it is
confined to the *quiescent* arm and acts by **mode selection** — Q lands in its
slow (~64 cyc) mode 4/6, 3/6, 2/6, 1/6 across positions 1→4, monotone — while the
A arms are position-insensitive (means within 0.59 cyc, walks within 0.14%). That
quantitatively explains run 1's negative `R`.

### `tab:fused` — statistically sound; the exhibit stands
The three `bsweep_*` cells were in `raw/` but absent from `summary.csv`; computed
at n=30: CAT 20/20 **87.653, CoV 1.48%**; 12/20 **105.123, CoV 5.29%**; 8/20
**115.814, CoV 5.24%**. The monotone-harm column is **7–17 standard errors per
step** (+17.47, +10.69, +11.05 cyc against pooled SEs ≈1.05/1.50/1.31), and
`PREFETCHNTA` vs unrestricted is ≈27 SE. **Your Figure 1 is sound on its
statistics.**

### E1 — sound, with two real defects
Arm identity correct (enforced plane, as your taxonomy needs). Byte-matching was
by **thread count** (WB 2T packed vs WC 5T spread), *not* the barred `-R`
throttle. Tax figures reproduce: 1.2877× [1.2790, 1.3095] vs 1.28×, and 0.9996×
[0.9879, 1.0136] vs 1.003×. Defects: **(a)** the paper never named E1's platform
(it is AMD, neighbour-CCX, while the section preamble says "eight on Intel");
**(b)** the `/dev/cxl_wc` kernel module is **not committed** and the device exists
on no host, so the WC arm **cannot be re-run as published**.

### Code audit — 8 defects in my own apparatus
Consequential ones: fixed arm order (fixed in run 2); a `grep -c` fallback that
split every JSON record across two lines — same class as the known defect at
`run_t5.sh:161-163`, which I had read the same day and then reproduced; and the
built binary predating the `HOT_TABLE_ROUNDED` warning, so **both T3 runs and the
whole clos_split panel came from binaries that no longer match source.** Records
are now validated as JSON before being appended.

---

## 3. What changed in the paper (all published to co-authors)

| change | was | now |
|---|---|---|
| fused hot table | "about 170 MB (53% of LLC)" | **256 MiB (80% of LLC)** — F9 power-of-two entry rounding; appendix now gives the mechanism |
| the sweep clause | "even 12 of 20, **more than the hot table's own share**" | **removed** — at 80% it inverts. The conclusion it supported is unchanged and still measured |
| `tab:fused` caption | "$n{=}30$" | "$n{=}30$ randomized runs per cell, medians; **CoV 1.3–5.3%**" |
| E1 single-core pair | 15.8 / 4.2 GB/s | **12.4 / 3.2 GB/s** ($n{=}12$), platform named **EPYC 9754 neighbour-CCX** |
| E1 "identical bytes" | "The CXL traffic is identical" | **withdrawn** — 20.36 vs 15.14 GB/s. Now: WC moves **26% fewer** bytes and still costs nothing, so a 28%→0.3% collapse cannot be a byte effect |
| `tab:amdcat` + 4 sites | 19.85 / 6.92 / 1.02, 69% removed | **19.89 / 9.87 / 0.99, 53% removed**, both values and the spread disclosed |
| RocksDB 2.33× / 54% | in prose with CIs | **deleted** per §6.6 — untraceable, nearest survivor disagrees (2.29× / 47%) |
| WC apparatus | not mentioned | **declared lost** in the appendix |

Two notes. The CAT correction makes **CAT look worse** (residual up, tax removed
down from 69% to 53%), so it strengthens the argument. The RocksDB deletion
removes the paper's **only real-application victim on the harmable side** — which
makes your anchor recommendation more urgent, not less.

The CAT arm is also **unstable in a way we can enforce but not explain**: the same
unmodified script gave 7.23× [6.89, 7.52] and 9.87× on a later re-run, isolated
to the CAT arm, verified to the hardware QoS mask MSRs. Reported as a range.

---

## 4. The evidence position, updated

The scissors is unchanged in shape:

| | deployed knobs | STREAMING's measured payoff |
|---|---|---|
| reuse thread never touches stream data | CAT12 → 1.00× @0.7% (Intel); CAT12+MBA192 → 1.07× @96% BW (AMD) | large — 76.3% of 6.484×, silicon |
| reuse thread **also** touches stream data | every deployed control makes it worse (7–17 SE per step) | **0.00% strict / ≤31% generous ceiling; −0.6% measured** |

Unchanged and still the best-provenanced result: flush-behind, **76.3%
[76.1, 76.4]** of a 6.484× tax, n=12 at `0628e0d`, victim **406.25 → 144.21
cyc/access = 2.82× faster**, streamer cost 31.34%.

---

## 5. The question that now decides the mechanism story

I rescoped T4 rather than running it, and this is what I most want your view on.

Your T4 was: convert `Δ_M3` to cycles, and let it decide **staging buffer vs
MSHR QoS**. Reading the decomposition first says that fork may be a false
dichotomy. Its own §7:

- the `Δ_M3` conversion needs "a causal model this experiment does not have";
- the per-load latency histogram "accounts for roughly **12%** of the real tax.
  **Most of it is not explained**";
- and its most defensible reading is that most of the tax is an
  **execution-level effect** — front-end/pipeline/dependency-chain interaction,
  or the OoO-overlap phenomenon it found incidentally (removing the stream made
  the probe *slower*, 91.5 vs 84.4 cyc/access) — "**not a per-load memory latency
  effect at all**."

An arrival × residence model presumes a memory-side resource. **Neither a staging
buffer nor MSHR reservation addresses an execution-level interaction.** So I
registered the prior question instead: split the tax with Intel Top-Down (events
verified present), n=12, order-balanced, with thresholds fixed in advance —
**≥60% memory-bound** makes your T4 the right experiment; **≤30% cancels it**.

**If it comes back ≤30% memory-bound, then in the one case where STREAMING is
uniquely expressible, no memory-side mechanism helps — not H2, not a buffer, not
MSHR QoS.** The paper would then hold: a real problem, a genuinely missing
interface cell measured on silicon with 7–17 SE, OS enforceability demonstrated —
and no mechanism that pays where it is uniquely needed.

**Is that a paper, and if so which one?** My reading is that it becomes a
measurement-and-interface paper whose mechanism section is a *derived
requirement* rather than a proposal, and that "zero new architectural state"
stops being an asset because the thing it buys is not the thing that hurts. I do
not trust my own judgement on the framing after four errors in one day, which is
why I am asking rather than deciding.

---

## 6. What I need from you

1. **The T4 threshold question above.** Also: is Top-Down the right instrument,
   or would you attack the OoO-overlap hypothesis directly first?
2. **Does the RocksDB deletion change your anchor recommendation?** It is now the
   paper's only path back to a named-application victim, and it must be earned
   from scratch under the current provenance standard.
3. **Is the lost `/dev/cxl_wc` module fatal to E1?** The tax figures reproduce
   from frozen data and the user-space half is committed, but the arm cannot be
   re-run. Disclose and keep, or demote?
4. **Given the 26% byte shortfall**, is the dissociation still safe to lead with?
   I think it reads stronger honestly stated; I would like that checked.

Still blocked on the lead, unchanged all day: the W5.3 write-in, co-author
contact, and venue. No measurement is on the critical path.
