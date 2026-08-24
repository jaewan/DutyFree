# T4 rescoped: is the fused tax memory-side at all? (read-first outcome)

Registered **before any measurement**. T4 was specified as a `Δ_M3`
cycles-per-access conversion — fit an arrival × residence occupancy model, and
let it decide between a staging buffer and MSHR QoS. **Reading the existing
decomposition first says that is the wrong next step.**

## Why the original T4 is premature

`results/mechanism_decomp/MECHANISM_DECOMPOSITION_REPORT.md` §7, on what it
could not measure:

> "A validated cycles-per-access conversion for `Δ_M3` — the raw signals
> (`FB_FULL`, `PENDING_CYCLES`) are real but **not convertible to an additive
> cycle-cost term without a causal model this experiment does not have**."

And §3, on the per-load latency histogram:

> the histogram "accounts for roughly **12%** of the real tax. **Most of it is
> not explained**" by per-load memory latency.

§7's own most-defensible reading:

> "most of the tax is an **execution-level effect** (front-end/pipeline/
> dependency-chain interaction, or the same OoO-overlap phenomenon found while
> building the quiescent baseline), **not a per-load memory latency effect at
> all** — which is itself informative: it means the tax lives somewhere neither a
> pure cache-residency story nor H2 specifically was designed to reach."

An arrival × residence model presumes the contended resource is a **memory-side
occupancy**. If ~88% of the tax is not a per-load latency effect, that model
would be fitted to a term accounting for at most 31% — and possibly 0% — of the
thing being explained. Worse, **neither candidate mechanism it adjudicates
addresses an execution-level interaction**: a staging buffer relocates fills, and
MSHR reservation partitions miss slots; neither touches OoO overlap or a
dependency-chain interaction. The fork T4 was meant to settle may be a false
dichotomy.

Corroborating datum already in hand: the decomposition found that **removing the
stream made the probe slower** (91.5 vs 84.4 cyc/access), which it flagged as an
OoO-overlap hypothesis "not confirmed against outstanding-load counters". T3 run
2 then found the load-induced page walks are the victim's and invariant to the
stream's page size. Both point away from a simple memory-occupancy story.

## The prior question, and the instrument for it

**Split the fused tax into memory-bound, core-bound, front-end and bad-speculation
components.** Intel Top-Down does this directly and the events are present on
mos181 (verified: `topdown-retiring`, `topdown-bad-spec`, `topdown-fe-bound`,
`topdown-be-bound`, `topdown-mem-bound`).

## Arms and design

Two arms at the panel's 1-core operating point, identical to T3's:
`Q` = `--mode hot-probe` (no stream), `A` = `--mode morsel` (fused), with
`--fact-bytes 256m --hot-bytes 177838489 --morsel 1m --threads 1 --cpu-list 32`.
Note the hot table instantiates at **256 MiB (80% of LLC)**, not the requested
169.6 MiB.

n=12 per arm, **order balanced**: odd reps run `Q,A`, even reps run `A,Q`, so each
arm occupies each position exactly 6 times. Per-rep values, CoV, and archived
stderr, using the T3 v2 runner's fixed idioms (records validated as JSON before
being appended; no `grep -c` fallback; guards emit `NA` not `0`).

Metric: Top-Down slot fractions plus `active_cycles_per_access`. Multiplexing
percentage is recorded per event; **any arm whose events multiplex below 100% is
reported as such and not silently averaged.**

## Pre-registered readings

Let `Δ = A − Q` in cycles/access, and let each Top-Down category's contribution
be its slot-fraction change scaled by cycles.

| outcome | verdict |
|---|---|
| **memory-bound accounts for ≥60% of Δ** | the tax **is** memory-side. The original T4 occupancy fit becomes the right experiment, and the buffer-vs-MSHR-QoS fork is real. |
| **memory-bound accounts for ≤30% of Δ** | the tax is **not** memory-side. No memory-side mechanism — H2, staging buffer, or MSHR QoS — can address the fused case, and the paper's fused section must say so. The original T4 is **cancelled**, not deferred. |
| 30–60% | mixed; report the split and treat the fork as open on the memory-side share only. |

Registered independently of the above: **whichever category dominates Δ is
reported by name**, even if it is one this project has no mechanism for
(front-end, bad-speculation, core-bound). A dominant core-bound or
bad-speculation term would be the most informative possible outcome and must not
be buried as "unattributed".

**Falsifier for the instrument itself:** `topdown-retiring + bad-spec + fe-bound
+ be-bound` must sum to ≈1.0 slots in both arms. If it does not, the reading is
void rather than interpreted.

## Out of scope

The 16-core arms; any change to `cxl_join_bench.cpp`; the `Δ_M3` conversion
itself (this experiment decides whether to attempt it); and any mechanism design
study. No system state is changed and no hugepage pool is resized.

---

# Addendum 1 — 2026-08-24: the panel's four amendments, registered before the run

Adopted verbatim in substance; nothing below is revisable after data lands.

**A1 — the middle band is now registered.** 30–60% memory-bound → *mixed*: a
memory-side mechanism may be pursued **only** with a pre-stated recoverable
ceiling equal to the memory-bound share of Δ. It may not be reported as "the
mechanism applies".

**A2 — the registered quantity is DIFFERENTIAL, not a single run's fraction.**
TMA fractions of the loaded run overstate memory-boundedness because the
quiescent probe is itself memory-bound (it is a pointer-chase-like hot-table
probe). The gate quantity is

    Δcyc_mem = (MemBound_A · cyc_A − MemBound_Q · cyc_Q) / access
    share    = Δcyc_mem / (cyc_A − cyc_Q)

and `share` is what the §5 thresholds apply to. The single-run fractions are
reported alongside but are **not** the gate.

**A3 — sub-buckets registered, because "memory-bound" cannot pick the fork.**
Fill-buffer-full stalls land under Memory Bound → **L1 Bound** on Intel, so a
single ≥60% number cannot make a four-way call. Registered mapping of the
*dominant* sub-bucket of Δcyc_mem:

| dominant sub-bucket | verdict |
|---|---|
| L1-bound / FB-full | **MSHR/fill-buffer QoS** is the indicated structure |
| L2- or L3-bound | **staging buffer** is the indicated structure |
| DRAM-bound | **conflicts with the strict `Δ_LLC_upper = 0`** result — escalate, do not proceed |
| core-bound or front-end | **cancel all memory-side mechanisms** |

**A4 — TMA attributes, it does not establish cause.** Two dilution
interventions are registered as part of this campaign, and the strong negative
sentence in §5 may **not** be written on TMA alone:
- *instruction dilution* — replace the stream's loads with an equal-count
  instruction stream touching no memory. Tax persists ⇒ execution-level,
  causally.
- *memory dilution* — same bytes, fewer instructions (wider SIMD / unroll). Tax
  persists ⇒ memory-side, causally.

**A5 — the OoO-overlap anomaly is re-verified before anything rests on it.**
The 91.5-vs-84.4 observation is single-configuration, and T3 run 2 demonstrated
that quiescent arms in this kernel family are position-sensitive *via mode
selection*. It is re-run under the Latin-square/order-balanced protocol. If it
survives: the fused baseline is partly latency-hidden **by** the interleaving, so
the ~27–33 cyc net tax sits atop a gross displacement partly offset by an overlap
benefit — which changes what "recovery" can mean and must be stated.

**A6 — the SMT-sibling split arm, registered to run regardless of the gate.**
Post-decomposition this is the cheapest hostile configuration against Branch B's
inexpressibility claim: scan on one hyperthread, probe on its sibling, SPSC ring
in the shared L1/L2. It keeps the locality that cost the cross-core split 36%, it
creates **two TIDs** (so per-TID CLOS becomes expressible), and SMT's per-thread
resource partitioning is the shipped approximation of core-level QoS. On mos181,
cpu32's sibling is **cpu160** (verified). Registered readings: recovers the fused
tax cheaply ⇒ the missing-cell claim narrows and the derived requirement is
"already shipped as SMT partitioning"; fails ⇒ the last cheap hostile
configuration is closed by us rather than by a referee.

## This step

This addendum registers the whole campaign. **The step executed now is the TMA
gate only** (arms Q and A, n=12, order-balanced). A4's dilution arms and A6's
SMT-split need new kernel code and are registered here but not yet built; the
gate decides whether A4's memory-side branch is even worth building.

Instrument falsifier, restated: `topdown-retiring + bad-spec + fe-bound +
be-bound` must sum to ≈1.0 slots in both arms, and any arm whose events
multiplex below 100% is reported as multiplexed and not silently averaged.

## Instrument finding, recorded before the run: the gate and the sub-buckets cannot share one invocation

Smoke-tested on mos181 before launching. `-M TopdownL1,TopdownL2` counts with
**no multiplexing** (slots sum verified: 9.1 fe + 51.1 be + 18.1 retiring +
21.8 bad-spec = 100.1%). Adding A3's sub-buckets
(`tma_l1_bound,tma_l2_bound,tma_l3_bound,tma_dram_bound`) drives every counter
to **16.5–33.7% enabled**, which the registered falsifier forbids reporting.

So the campaign splits, and the split is registered here rather than decided
later:

- **Phase 1 (executed now):** `TopdownL1,TopdownL2` + `l1d_pend_miss.fb_full`,
  n=12, order-balanced. This yields exactly what **A2's differential gate**
  needs — `MemBound` and `CoreBound` fractions per arm with cycles — and it
  answers §5's ≥60 / 30–60 / ≤30 question.
- **Phase 2 (only if phase 1 returns ≥30% memory-bound):** the sub-buckets, as
  a separate n=12 campaign, either split across two non-multiplexed groups or
  with the multiplexing disclosed per arm. **A3's four-way fork call is deferred
  to phase 2 and may never be needed.**

The multiplexed sub-bucket numbers from the smoke are **not** recorded as data
and must not be quoted.

---

# Addendum 2 — 2026-08-24: a defect in my own gate, and the same-code-path re-run

Registered **before the re-run executes**. Phase 1 has already produced its
result and it is reported unchanged; this addendum states what it can and cannot
carry.

**The defect.** Phase 1's arms are `Q = --mode hot-probe` and `A = --mode
morsel`. Those are **different loops**. That is the correct pairing for measuring
the published *tax* (it is how the tax is defined, and it matches T3 and the
panel's operating point), but it is the **wrong pairing for a TMA attribution**:
a differential over pipeline-slot categories between two different code paths
conflates *interference* with *code-path difference*. A bad-speculation term is
exactly the kind of thing a different loop shape produces on its own.

**Why this matters most for the finding that actually surfaced.** Phase 1's
dominant category is bad speculation at 46.8% of Δ. That is the term least
defensible under this confound, and the paper must not carry it until the
confound is removed.

**The fix, available in the committed binary.** `--no-stream` runs `run_morsel`'s
**own loop** with the stream removed (`cxl_join_bench.cpp:1522,1570,1591`), which
is exactly a same-code-path quiescent baseline. The 2026-07-29 decomposition
already used it and recorded the anomaly this campaign's A5 exists to
re-verify — the no-stream variant was *slower* than the real fused case (91.5 vs
84.4 cyc/access).

**Registered arms for the re-run (phase 1b):** `Qs = --mode morsel --no-stream`
and `A = --mode morsel`, identical in every other argument, n=12,
order-balanced, same metrics, same falsifier.

**Registered readings, fixed now:**

| outcome | reading |
|---|---|
| bad-spec share of Δ stays ≥30% in 1b | the bad-speculation term is **real interference**, and it is the headline finding: the fused tax is largely a speculation effect |
| bad-spec share falls below 15% in 1b | phase 1's bad-spec term was a **code-path artifact** of the hot-probe/morsel pairing, and must be withdrawn |
| 15–30% | partially artifactual; report both pairings side by side and claim neither |

**The memory-side gate verdict is evaluated again on 1b, and 1b governs.** If the
two pairings disagree on the memory-bound share, 1b is the one with a controlled
code path and phase 1's is reported as superseded.

**A5 comes free.** Because `Qs` *is* the no-stream arm, this re-run also
re-verifies the OoO-overlap anomaly under order balancing at n=12: if
`cyc(Qs) > cyc(A)`, the anomaly survives, and the implication registered in A5
applies — the fused baseline is partly latency-hidden by the interleaving, so the
net tax sits atop a gross displacement partly offset by an overlap benefit.

**Unchanged:** A4's dilution arms are still required before any strong causal
sentence reaches the paper. TMA plus a controlled code path is still attribution,
not cause.

---

# Addendum 3 — 2026-08-24: A6's concrete arms, registered before the run

A6 was registered in principle in Addendum 1 and runs regardless of the gate
(the gate has since returned "not memory-side"; A6 is unaffected by that, since
it tests **expressibility**, not mechanism). No new code is needed: the committed
binary's `split` mode pins scan thread `tid` to `cpus[tid]` and probe thread
`pid` to `cpus[n_scan + pid]` (`cxl_join_bench.cpp:1389,1411`), so an SMT-sibling
split is just a two-entry cpu list. Verified: `cpu32`'s
`thread_siblings_list` is `32,160`, both report `core_id 32`, and cpu160 is
online.

## Arms (n=12, randomized Latin square, every arm in every position 3×)

| arm | configuration | physical cores | logical CPUs |
|---|---|--:|--:|
| **F** | `morsel --threads 1 --cpu-list 32` — fused, one thread | 1 | 1 |
| **Ssmt** | `split --scan-threads 1 --probe-threads 1 --cpu-list 32,160` — **SMT siblings**, SPSC ring in the shared L1/L2 | **1** | 2 |
| **Score** | `split --scan-threads 1 --probe-threads 1 --cpu-list 32,33` — distinct physical cores, same L3 | 2 | 2 |
| **Q** | `morsel --no-stream --threads 1 --cpu-list 32` — same-code-path probe reference | 1 | 1 |

All other arguments identical to the campaign's 1-core operating point
(`--fact-bytes 256m --hot-bytes 177838489 --morsel 1m --fact-node 2 --hot-node 0
--warmups 2 --reps 1`), `--queue-depth 16` for the split arms.

**The resource-matched comparison is F vs Ssmt: both occupy exactly one physical
core.** `Score` uses two physical cores and is therefore *not* resource-matched;
it is included as the reference for the cross-core split organization (the one
that cost 36% of throughput at 16 cores) and its throughput advantage must never
be reported without noting it has 2× the physical resources.

## Pre-registered readings

Primary — hot-table cyc/access and throughput, **F vs Ssmt**:

| outcome | verdict |
|---|---|
| Ssmt improves hot-table cyc/access by **≥10%** vs F **and** holds throughput **≥90%** of F | **SMT split recovers the fused cost cheaply.** The missing-cell claim narrows: two TIDs exist, per-TID CLOS becomes expressible, and the derived requirement is "already shipped as SMT resource partitioning". This is adverse to us and gets reported as the headline. |
| Ssmt's cyc/access is **no better** than F's, **or** throughput falls **below 80%** of F | **SMT split fails.** The last cheap hostile configuration against Branch B's inexpressibility is closed by us rather than by a referee. |
| anything between | partial; report both axes and claim neither |

Secondary — **Ssmt vs Score**: if they are within noise, SMT's shared L1/L2 buys
nothing and the ring is not the binding cost; if Ssmt is much worse, the ring's
locality is not what made the cross-core split expensive.

Registered caveat: this measures whether *splitting across SMT siblings*
recovers the cost. It does **not** measure whether CAT applied to the resulting
two TIDs helps — that needs a `resctrl` arm and is deliberately out of scope
here, because the first question is whether the split is viable at all. If Ssmt
fails, the CAT-on-two-TIDs question is moot.

---

# Addendum 4 — 2026-08-24: A4's memory-dilution arm already exists; the instruction arm is nearly a no-op; the real gap is code path

Registered before running, after reading `join_range_local`'s implementation.

**A4's memory-dilution arm has already run.** `join_range_local`
(`cxl_join_bench.cpp:596+`) is, in its own docstring, *"identical to join_range
except it indexes a small, cache-resident local buffer via wraparound
(`fact[i % local_n]`) instead of striding through the real (CXL) fact array"* —
and the modulus is masked, not divided. So it holds **instruction count and probe
count fixed** and moves only the stream's **bytes** from CXL to L1/L2. That is
precisely A4's memory dilution: same instructions, fewer/nearer bytes. It ran as
phase 1b, and gave **Δ = −0.795 cyc/access**.

This is a stronger control than the T4 outcome credited (which listed
`join_range_local` as a caveat, "a different inner join"). It is a different
inner join only in its *addressing*; the work is the same. **T4's outcome is
corrected by this addendum on that point**, and its conclusion strengthens:
holding instructions and probes fixed, replacing a 256 MiB CXL stream with a
cache-resident buffer changes the fused cost by ≈0. **The bytes do not cost.**

**A4's instruction-dilution arm, as specified, is nearly a no-op here.** To
"replace the stream's loads with an equal-count instruction stream touching no
memory" I would have to synthesize keys with the same table-hit distribution.
`fill_fact` draws them from a sequential RNG stream (`keys[rng.next() %
keys.size()]`), so they are not a closed form of `i`, and `keys` is far too large
to be resident — synthesizing from it would substitute one stream for another.
Against `--no-stream`, which already has the load hitting L1, the only thing left
to remove is a single L1-resident load (~1 uop). That cannot plausibly account
for a 30-cycle gap, and building it would produce a null that means nothing.
**Not built, and the reason is recorded rather than the arm quietly skipped.**

**What is actually unexplained, and the zero-code experiment for it.** Phase 1b
localises the 30.775 cyc/access "fused tax" to the difference between
`run_hot_probe`'s loop and `run_morsel`'s — not to the stream. `run_morsel`'s
driver does, per morsel, an atomic `next.fetch_add`, two `rdtsc`s, and a `Result`
aggregation, around a `join_range` over the morsel. If that driver is the gap,
**enlarging the morsel amortises it away**; if the gap survives at large morsels,
the driver is not the cause and the difference is in the inner loop itself.

Registered arms: `F` (`morsel`) and `Q` (`morsel --no-stream`) swept over
`--morsel` ∈ {256k, 1m, 4m, 16m}, n=6 each, order-balanced within each morsel
size, everything else at the campaign operating point. Reference: `hot-probe` at
the same n.

| outcome | reading |
|---|---|
| `F` cyc/access falls toward `hot-probe`'s ~60 as morsel grows | the "fused tax" is substantially **morsel-driver overhead**, and the published 1.47× is a harness artifact |
| `F` stays ~90 at every morsel size | the driver is **not** the cause; the gap is in `join_range` vs `run_hot_probe`'s inner loop, and remains to be explained |
| non-monotonic | report the curve, claim neither |

This does not rescue a memory-side mechanism either way — the gate already
returned 15.9% and 1b returned ≈0 for the stream. It determines **what the
published fused tax actually is**, which the paper needs regardless.
