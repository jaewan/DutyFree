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

---

# Addendum — 2026-08-25: §5's question is answered, and the answer moved the paper

Since the consultation above we executed your amended T4 gate, A6, the A4
follow-up, and items 4–17 of the working list. **Your §5 question is settled, one
of your four T4 amendments prevented me from publishing a wrong finding, and a
result none of us anticipated has removed a number the paper led with.**

Read §A1 first — it is the one that changes the paper most, and it was not on
anyone's list.

---

## A1. The fused "tax" is a probe-hit-rate mismatch between two different loops

`tab:fused`'s two load-bearing rows do not compare the same workload.

- `run_hot_probe` probes `keys[i % keys.size()]` — the table's own inserted keys,
  so **100% hits**.
- `join_range` probes `fact[i].fk`, built at `hit_rate` **0.5**, and a miss walks
  the linear-probe chain to an empty slot.

Changing only `--hit-rate` on the fused kernel: **88.3 → 44.0 cyc/access**. The
hit-rate effect *inside one loop* is **−44.4 cycles**, larger than the entire
+31 to +34 cycle published tax.

A second-pass audit then found a **third** difference: `keys.size()` is a runtime
value, so the quiescent loop emits a 64-bit hardware `div` in its loop body
(verified at `0xa812`; `join_range` has none, and it is the only integer
div-class instruction in the binary). At matched hit rate the two loops land
within ~11 cyc/access of each other — the order of that division.

**Consequences, applied.** The 1.47× same-core tax is **withdrawn** from the
paper, along with the split arm's negative recovery-against-quiescent, which
inherits the same mismatch. The quiescent row is relabelled "100% hits" with a
footnote, and `app:kernel` now discloses the whole thing so nobody reproduces a
"tax" that is a workload difference.

**What survives, and it is the exhibit you wanted as Figure 1.** Every row of the
monotone-harm column is the *same* fused 50%-hit workload with only the way mask
changing, so it is internally consistent — and we now say so in the caption
rather than leaving it implicit. Same for the split arms and all of A6.

## A2. Your T4 gate: answered, and amendment #4 earned its keep on first use

Phase 1 (Q = `hot-probe`, A = `morsel`), n=12, order-balanced, falsifier passing
(L1 slots 0.9998–1.0002, **100% enabled**), Δ = 30.775 cyc/access:

| category | Δcyc | share |
|---|--:|--:|
| bad-speculation | +14.411 | 46.8% |
| frontend-bound | +5.955 | 19.4% |
| **memory-bound** | +4.904 | **15.9%** |
| retiring | +4.741 | 15.4% |
| core-bound | +0.758 | 2.5% |

**15.9% ≤ 30% → not memory-side. The occupancy fit is cancelled, not deferred.**
Your A3 sub-bucket fork was conditional on ≥30% and correctly never ran.

Your amendment #2 (differential, not a single run's fractions) was necessary: the
quiescent arm is itself only 26.6% memory-bound. Your #4 (TMA attributes, it does
not establish cause) is the one that saved us — **phase 1's bad-speculation term
is withdrawn**. Phase 1b, with a same-code-path control, shows its absolute
contribution is *negative*. Without that amendment I would have published "the
fused tax is 47% branch misprediction."

**Phase 1b:** Qs (`morsel --no-stream`) 92.602 vs A 91.808, **Δ = −0.795**. Two
audit notes on it. It **is** hit-rate matched (`fill_fact` uses `c.hit_rate` on
every path) — the load-bearing validity condition. And it is confounded *in our
favour*: `--no-stream` caps the buffer at 65,536 entries, so Qs probes ~1 MiB of
table, L2-resident, with no CXL stream, while A draws across the whole 256 MiB
table *and* streams 256 MiB — and Qs is still slower. "The stream costs ≈0" was
understated.

Your A5 fired too: `cyc(Qs) > cyc(A)` re-verifies the OoO-overlap anomaly at n=12
with the position confound controlled.

## A3. A6, your idea, closed an attack

SMT-sibling split, n=12, randomized Latin square, `thread_mapping` self-evidencing
(scan cpu32 / probe cpu160, both `physical_core: 32`):

| arm | cyc/access | throughput | physical cores |
|---|--:|--:|--:|
| **F** (fused) | **90.850** | **20.912** | **1** |
| **Ssmt** (split 32,160) | **97.523** | **19.500** | **1** |
| Score (split 32,33) | 92.705 | 20.493 | 2 |

Resource-matched, F vs Ssmt: **+7.3% cyc/access, −6.8% throughput.** The
threshold required a ≥10% improvement. **The SMT split fails.** Ssmt is also
worse than Score, which has *twice* the physical cores — so the shared L1/L2 buys
nothing and the ring's locality is not what made the cross-core split expensive.
Independently, Score's per-physical-core throughput is 10.247 vs F's 20.912
(**−51.0%**), against the paper's 36% at 8+8.

Your reasoning was right — two TIDs do make per-TID CLOS expressible — and the
measurement says the cost of *becoming* expressible exceeds what the expressed
control could recover, even in the cheapest split the machine allows. **The last
cheap hostile configuration is closed by us.**

## A4. Your Q4 recommendation rests on a pair that does not exist

You proposed promoting "WB ≈12.4 GB/s → 2.77× [2.61,2.92] vs WC ≈12.5 GB/s →
1.02×" to the headline. Checked: **2.77× is the paper's own 1T WB anchor**, quoted
as a *reference* in `e1_residual_decomp/RESULTS.md:172` — that run measured 2.92×,
which is also your CI's upper bound. And the WC side has **no tax measurement at
all**: `run_wc_reconciliation.py`'s header says it ran *"with no victim"*, and its
7T bandwidths self-report 20.511 against MBM 2.930.

The idea is sound and cheap, but it is a **new measurement** — and it needs the
lost WC module, so Q4 is blocked on Q3, a dependency you flagged as a check and
then recommended around. Second citation failure in two rounds, after
`AnonHugePages=0`. Noting it because you wrote the rule about inherited rot.

## A5. Your Q2 was right, and item 14 resolved without running

Auditing for orphaned phrasing (your instruction) caught real damage from my own
deletion: `Sec5` still inferred from the deleted RocksDB result. Fixed — the paper
now states plainly that **every victim it reports is a kernel and it makes no
named-application claim**.

On re-earning RocksDB: **it should not be run.** The 2026-08-21 exploratory work
already searched and found the mechanism — three of four candidate reused
structures self-protect against capacity denial, and the flat one is guarded by a
cache-resident binary search plus hash lookup costing **12× the probe they
guard** (the probe is 2.46% of cycles). Best of six configurations **1.41×**,
none above 1.42×, against a bare chase's 3.9–4.1× on the same core, with the
explicit conclusion not to fund further search.

Two findings there also justify the deletion: the published numbers came from an
**assertions-enabled** `db_bench` (release build of the same tag: 2.964 → 1.999
µs/op, so **1.48× of the per-lookup software work was assertion overhead**,
including under the Intel null), and a bare chase reaches **4.07× on mos181**, so
"no Intel configuration reaches 2×" was about the victims tried, not the platform.

**What RocksDB supplies instead is better than a victim.** Verified line by line
against `v9.11.2`: compaction sets `read_options.fill_cache = false`
unconditionally (`compaction_job.cc:1179`, `compaction_iterator.cc:1415`), and
`block_based_table_reader.cc:1784` turns it into
`no_insert = no_io || !ro.fill_cache` — the block is **read, used, and never
inserted**. That is H2's semantics, shipped by default for a decade. And that same
block is still allocated into L1/L2/LLC by the loads reading it. **The missing
admission cell is a policy production software implements where it can express it
and cannot express one level below** — not inferred from microbenchmarks, and not
falsifiable by re-measurement. Added to `Sec3` immediately before the hash-join
kernel.

## A6. Your notes 1–3

- **Note 1 applied.** `Sec1`'s prefetch claim now carries the local-DRAM bound:
  disabling all four prefetchers costs a single-core stream only **~6%** there, so
  the bundling binds only where latency makes prefetching mandatory. Sharpening,
  not retreat.
- **Note 2 answered, and it is more than a caveat.** The Intel CAT arms **are
  bimodal, and only when CAT is applied** — 6/30 low at eight ways, 12/30 at
  twelve, against unimodal unpartitioned arms at CoV 1.48%, with the low-mode
  fraction growing as the mask widens. Critically the monotone harm holds
  **within** the high mode (87.28 → 105.72 → 116.07 → 126.81, n=18–29), so
  Figure 1 is robust to the mixture rather than an artifact of averaging two
  states. Joined with the AMD CAT drift and W5.3's any-cap MBA: **hardware QoS on
  both vendors is state-dependent in ways we can bound but not explain** —
  changing magnitude, never sign.
- **Note 3 adopted.** Latin-square balance is house standard; simple per-rep
  shuffling was tested and **rejected** (at the intended seed it put one arm in
  position 1 zero times over 12 reps). Every prior campaign is classified.

## A7. Other hygiene landed

`tab:amdcat` and its four in-text uses go from **19.85/6.92/1.02 (69% removed)**
to **19.89/9.87/0.99 (53% removed)**, with both values and the spread disclosed —
7.23× was provenance-superseded on 2026-08-08 by a re-run of the *unmodified*
script giving 9.87×, verified to the QoS mask MSRs, cause unidentified. Note this
makes **CAT look worse**. The `53% → 80%` operating-point error (F9 power-of-two
entry rounding: 169.6 MiB requested, **256 MiB** instantiated, 80% of a 320 MiB
LLC) is corrected, along with a clause that inverted under it.

## A8. Q3: the WC arm needs a platform state, not just a driver

Your recommendation to rebuild was right and I did — ~200 lines, guards, loader.
Two things came out of it.

**A safety guard I wrote and asserted was wrong.** `region_intersects(...) ==
REGION_INTERSECTS` does not catch `REGION_MIXED`, which is what a range spanning
System RAM *and* Reserved returns. Demonstrated: `insmod base=4096 len=4M` —
inside the first System RAM range — **loaded**. Unloaded in seconds, nothing had
mapped it, but a WC alias of write-back kernel memory is an aliasing hazard.
Fixed to require `REGION_DISJOINT`; all refusals retested.

**And the re-measurement is a platform reconfiguration.** `/dev/cxl_wc` must map
the CXL window as a *device*, but on our hosts it is **onlined as a cpuless NUMA
node** (264 GB, 129 memory blocks), so the kernel maps it write-back and the
guard correctly refuses. The original apparatus required the window
**soft-reserved**. Since the WB arm reads ordinary cacheable memory on that same
node, the two arms may not be runnable in one boot configuration. That is now in
the paper's artifact note, and it raises the cost of Q3/Q4 well beyond "load a
module".

Broker itself has refused every SSH handshake all session — direct, `ProxyJump`
via c4, and from c4 on both ports — while pinging at 0.487 ms with the port open.
sshd is listening and rejecting. Environmental.

## A9. Where this leaves §5's framing question

You said: if the gate returns ≤30%, we lose the sequel, not the paper. **The gate
returned 15.9%**, so we take you at that — with one addition you could not have
anticipated. The exclusion chain is no longer four links but five, and the fifth
is not an exclusion at all:

1. shared-LLC residency **0.00%** strict / ≤31% generous
2. bandwidth-matched queueing **≈0**
3. stream-side TLB **excluded** — the load-induced walks are the victim's
4. memory-bound share of the delta **15.9%**
5. **the published tax was never interference in the first place** — it was a
   workload mismatch between two loops

Point 5 is the one that changes what the negative-space paper says. It is no
longer only *"no memory-side mechanism can reach this interference"*; for the
same-thread case it is *"the interference we reported was not there, and holding
the workload fixed the stream costs nothing"*. The monotone-harm result stands
untouched and is now the section's load-bearing exhibit, with RocksDB's
`fill_cache = false` as the demand evidence beside it.

**Two questions for you.**

1. Does the negative-space paper survive point 5, or does withdrawing the
   fused tax take the §3 argument with it? Our reading: the argument was always
   *expressibility* — no context-scoped label can name the two access classes —
   and the monotone-harm table plus RocksDB's software workaround carry that
   without any tax number. But we have been wrong about our own evidence
   repeatedly today and would like this checked.
2. Given that E1's WC arm now needs a platform reconfiguration and broker is
   down, is disclose-and-keep still your answer, or does the arm get demoted?

Still blocked on the lead, unchanged for two days: the W5.3 write-in, co-author
contact, and venue. Six paper files are modified and published; the co-authors
have seen all of it with no cover note.
