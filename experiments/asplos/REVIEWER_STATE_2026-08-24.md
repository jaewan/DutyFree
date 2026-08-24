# The state of the STREAMING paper, written for an external reviewer

**Date:** 2026-08-24. **Audience:** someone outside the project who is willing
to tell us the paper is not viable. **Purpose:** to state what we can prove,
what we cannot, and the one problem that decides whether this is submittable —
without the framing that a paper's own authors apply by reflex.

Nothing here is new measurement. Every number is on disk in this repository
with a committed pre-registration and, where it matters, an analyzer committed
before the data landed. Provenance for each is named at the point of use.

**Read §4 first if you only read one section.** It is the objection, and it is
correct.

*Relation to earlier documents.* `SUBMISSION_READINESS_2026-08-19.md` and
`REVIEWER2_RESPONSE_2026-08-19.md` predate W1's replication, W2.1's
de-confound, W3.1's H3 null, W7's failure and W8's attribution result. Where
they and this memo disagree, **this memo is later**; where they carry detail
this one compresses (per-section edit ownership, the 17.8× data-array-write
pricing), they remain the reference. Neither is withdrawn.

---

## 1. The claim, in one paragraph

Immutable, read-once objects (column fragments, vector-index segments, sealed
SSTables) ask the memory system for two things at once: *prefetch me
aggressively* and *do not keep me*. On x86 no memory type grants both —
write-back prefetches well and allocates every clean line into the shared
cache; write-combining declines the allocation and forfeits the prefetching.
CXL makes the choice unavoidable because its latency makes the polluting mode
the only fast mode. We propose **Streaming**: the OS declares a region
immutable for a read epoch via `mprotect`, hardware sees the declaration in
the *translation* (PAT slot 6), prefetches as for write-back, and does not
allocate the region's clean lines in the shared cache (**H2**). Because the
declaration promises no writer exists, hardware may additionally skip coherence
enrolment (**H3**).

The intended contribution is not a speedup. It is that **the label belongs in
the translation** — every shipped enforcement mechanism (CAT, MPAM, CBQRI)
labels the *thread*, every shipped address-scoped mechanism (`PREFETCHNTA`,
Arm Transient, RISC-V `NTL.S1`) is *advisory*, and the combination that a
CXL stream needs is empty.

---

## 2. What is solidly established

| # | claim | number | instrument | arm |
|---|---|---|---|---|
| E1 | The tax follows **allocation**, not bytes | victim **+28%** under WB vs **+0.3%** under WC, *same byte stream, only the host memory type changed* | Intel silicon | CAT/MBA double dissociation corroborates |
| E2 | Way-partitioning does not substitute | WB **19.886×** → WB+CAT **7.225×** → WC **0.989×** (n=12); the 2026-08-08 rerun reads **20.545 / 9.867 / 1.006** (n=6). CAT removes **67%** on the first and **55%** on the second; WC removes 100% on both. | AMD EPYC 9754 silicon | same-L3 aggressor; victim's WSS fits its ways |
| | *Provenance warning* | the paper still prints a superseded **19.85 / 6.92 / 1.02** in five places, whose n=210 raw file is **gone**. **9.87× is the campaign's standard CAT residual.** Fixing this is queued (W4.2) and unstarted. | — | — |
| E3 | The two vendors disagree on *which structure* binds | AMD rate-class (MBA recovers), Intel capacity-class (CAT recovers); each knob useless on the other's machine | both platforms | — |
| E4 | H2 removes the capacity charge in simulation | WB **1.369×** → H2 **1.0337× ± 0.0005** (1 sd, n=3) = **90.9% removed** | gem5 CHI | infinite SF, CXL-resident aggressor, 5 MiB HNF |
| E5 | E4 is **not** "the aggressor got throttled" | victim L2 demand misses invariant to **−0.02%**; of those, misses reaching DRAM fall **−99.28%**; aggressor CXL bandwidth falls only 6.25% | same nine runs | address-split pools make attribution exact |
| E6 | E4 replicates | three measurements, two harnesses, two gem5 commits; WB agrees to four digits, H2 to 0.7% | gem5 | — |
| E7 | The mechanism is nearly free | **no new architectural state.** Existing PAT selector triple → slot 6, decoded in the walker; two fill-path predicates. Kernel prototype 447 lines | source audit + implementation | vs CAT's CPUID leaf + association register + MSR file + mask-contiguity rule + a write per context switch |
| E8 | The contract is OS-enforceable | `PROT_STREAMING` prototype; its kunit suite **ran in the guest** under full-system gem5; the write-back full-system arm gated clean | gem5 FS + Linux | — |

E1–E3 are on **real silicon**. E4–E6 are in **simulation**. E7 is a source-code
and ISA-manual argument. That division matters in §4.

---

## 3. What is established but unhelpful, or negative

| # | finding | number |
|---|---|---|
| N1 | **H3's charge is absent on every machine we can buy.** Private-L2-resident victims read **1.000×** on Sapphire Rapids and on Bergamo; a forced snoop-filter turnover reads **1.00×**. | H3 is a *capability* claim only |
| N2 | **H3 is not free.** At an infinite SF, where H3 has no enrolment charge to remove, H2+H3 costs **1.0345× relative to H2 alone** (+3.45%, n=3, ~3 sd). No-retention is *observed*, not inferred: L1D hit rate 0.3%, private-L2 11.7%, **+61.7%** fabric traffic per cycle. | — |
| N3 | **The convergence experiment failed.** A 2×2 built specifically to show necessity and benefit *at the same operating point*: 28 cells, 66 host-hours, 3 seeds, correctness-gated. Largest H2 effect anywhere **+1.23%**. One cell **−1.00%**, consistent across all three seeds. Pre-registered falsifier P2 **failed outright**. | this is the problem |
| N4 | **Real-application effect is small.** DuckDB co-run at matched bandwidth: 1.112× vs 1.049×; allocation-attributable difference **+0.058**. Six e2e workloads: direction confirmed, magnitude small. | — |
| N5 | The full-system `mprotect` arm is blocked by an **upstream gem5 defect** (proven today by a stock-protocol control that reproduces the hang bit-identically). Our 221-line CHI delta is exonerated, but the arm still has not run. | apparatus, not science |
| N6 | `[F9.4]` gem5 quantizes LLC sets to a power of two: a requested 32 MiB/20-way LLC simulates as **20 MiB**. Disclosed and labelled everywhere, but it is a surface a referee can pull on. | — |
| N7 | **Two published numbers have lost their raw data.** `tab:amdcat`'s n=210 source file is gone from both hosts; the paper's 6.92× CAT residual is superseded by a verified 9.87× (n=6) that has never been substituted. A RocksDB "2.33× / 54%" in the prose is **untraceable** — the nearest surviving file disagrees (2.29× / 47%). Per our own §6.6 these are *gone*, not reconcilable, and must be replaced or deleted before submission. | 5 places + 1 prose claim |

---

## 4. The objection, stated as a reviewer would state it

> You are asking for a change to the **page table format's interpretation**, the
> **cache fill path**, and the **operating system's memory-protection API** —
> three of the most conservative interfaces in computing, changed together. The
> benefit you measure at realistic operating points is **1.23%**, and one of
> your own cells is **negative**. Your headline 90.9% is at an *infinite snoop
> filter*, which is not a machine. Your real application moves **5.8
> percentage points**. Nobody adds a memory type for that. Reject.

This is not a strawman. It is the correct first reading of the evidence, and
we should assume every reviewer reaches it.

There is a sharper version, and it is the one that actually hurts:

> Your **harm** numbers are on silicon and they are enormous — a 20× tax, a
> ~9.9× residual after CAT. Your **benefit** numbers are in simulation and they are
> tiny — 1.03× in the good cell, 1.01× at realistic points. Those are not the
> same experiment, the same victim, or the same operating point. You have
> measured a large problem with one instrument and a small solution with
> another, and you are asking me to join them with an argument.

**That gap is the paper's actual condition.** It is not a presentation problem.

---

## 5. Why the magnitude is small — the part that is scientifically real

We understand the mechanism, and the understanding is measured, not assumed.

Denying a victim cache capacity changes two things: how much traffic it
generates, and how much time that traffic costs. The second is not proportional
to the first. From the HNSW capacity-sensitivity gate (real silicon, CMT
occupancy verified against the granted mask on every host, no aggressor —
a pure capacity gate):

| host | LLC grant | DRAM traffic ratio | runtime ratio | elasticity (runtime/traffic) |
|---|---|---:|---:|---:|
| **mos181 (8592+)** | **320 → 16 MiB** | **8.44×** | **1.543×** | **0.18** |
| mos182 (8462Y+) | 60 → 4 MiB | 1.84× | 1.325× | 0.72 |
| moscxl (9754) | 16 → 1 MiB | 1.20× | 1.257× | 1.05 |

*The bolded row is the claim.* The three points are **one per machine**, three
microarchitectures — the apparent ladder is confounded with host and W5.4 says
so explicitly; it must not be drawn as a curve. The single-host fact carries
the argument by itself:

**Capacity can remove 8.4× of a victim's DRAM traffic and return only 1.5× in
time.** The victim is not insensitive because the cache does nothing for it —
it demonstrably does a great deal, 122.7 GB down to 14.5 GB. It is insensitive
because its misses **overlap**: independent proximity-graph hops absorb the
extra misses in memory-level parallelism rather than paying for them in time.

Contrast the decisive cell, whose victim is a **pointer chase** — dependent
loads, MLP ≈ 1 by construction. There, removing 99.28% of the DRAM-reaching
misses buys 24.48% of time, and 90.9% of the measured tax.

So the honest general statement is:

> **The harm from shared-cache pollution, and therefore the benefit of any
> mechanism that removes it, is governed by the victim's memory-level
> parallelism. Streaming removes almost all of the harm it targets. That harm
> is large for latency-bound, low-MLP, LLC-resident victims and small for
> everything else.**

This is a real finding with silicon behind it. It is also a **cap on what the
paper may claim**, and the two halves have to travel together or the promotion
is dishonest.

---

## 6. Thought experiments

### TE-1 — "Just use CAT." Play it out.

Reviewer sets `resctrl`, partitions the streamer into 2 ways, walks away.

What actually happens: on AMD this leaves a **9.87× residual** at full aggressor
bandwidth — CAT removing only ~55% of a 20.5× tax — with the victim's working
set fitting its allocated ways, so it is not way capacity that is left over.
(A second, older estimate on the same platform puts the residual at 7.2× / 67%
removed; both are verified files, they disagree by 12 points, and the memo
reports the range rather than the friendlier end.) And the moment the stream
and the reused structure are in the *same thread* — which is the normal case for a fused scan-and-probe operator — CAT
has **no expressible policy at all**: one context label, two access classes.
That is not a tuning failure, it is a scope failure, and it is the strongest
single thing the paper owns.

**Verdict: we win this exchange, on silicon, decisively.** TE-1 is not the
threat.

### TE-2 — "What benefit *would* have been enough?"

Useful to answer honestly rather than aspirationally. Roughly:

- **≥15–20% on a named real application** → an ordinary accept-track ASPLOS
  performance paper. We are nowhere near this and no experiment we can run
  gets us there, because §5 says the elasticity is not available.
- **5–10% on a real application, plus a capability nothing else provides** →
  viable, contested, decided by how good the necessity argument is. **We are
  at the bottom edge of this band**: DuckDB moves 5.8 points.
- **~1% plus a capability** → this is what N3 says, and it is a reject as a
  performance paper.

The band we are in is real but narrow, and it means the paper cannot be sold
on the number. It has to be sold on E7 (cost ≈ 0) times the necessity argument
(E1–E3), with the magnitude *scoped* by §5 rather than hidden.

### TE-3 — "Is our operating point simply wrong? What would have to be true for the effect to be 10×?"

Work backwards. The effect scales with (i) the victim's dependence on shared
cache, (ii) the victim's MLP⁻¹, and (iii) the fraction of the shared cache the
stream can take. To get 10× more effect we would need a victim that is
LLC-resident, latency-bound, and *low-MLP*, co-located with a stream large
enough to evict it.

The 2×2 did not fail because we chose badly on (iii) — the stream was 40–80% of
the LLC. It failed on (ii): the batched-probe knob was supposed to lift the
victim's lines-in-flight, and it **lifted the victim out of the harmable
class** at the same time. Batching a probe *is* adding MLP, and adding MLP is
exactly what makes a victim immune. **The knob designed to make the cell
realistic is the knob that destroys the effect.** That is why P2 failed and why
one cell went negative.

This is worth stating plainly because it is not a null — it is a *structural*
result about the mechanism, and it says the harmable class is narrower than we
had assumed. It also means no re-tuning of that experiment recovers the number.

### TE-4 — "Can a capability argument carry an architecture paper with ~1%?"

Sometimes, and the precedent is worth naming: protection keys shipped as a
*capability* (cheap permission change) rather than a throughput win; MPAM and
CBQRI shipped as QoS *capabilities*. The bar for a capability paper is
different: the mechanism must be nearly free, the alternative must be
genuinely absent (not merely worse), and the need must be shown to be growing.

We satisfy the first two unusually well — **E7 is the strongest fact in the
paper and it is currently understated in the draft** (the text says "one PTE
bit"; the truth is *no new architectural state at all*, since PAT slot 6 and
its selector triple are already architectural). The third is the weak leg, and
it is where §5's characterization must do the work: we have to show the
harmable victim class is real, identifiable, and economically present, not
merely constructible.

### TE-5 — The strongest rejection we can write against ourselves

> The paper's own data show that the harm it targets is governed by victim MLP,
> that most real victims have MLP, and that the authors' one attempt to
> demonstrate benefit at a realistic operating point produced +1.23% and a
> negative cell. The large numbers are all *harm* numbers on silicon against a
> hand-built pointer-chase victim; the *benefit* numbers are all simulated. The
> coherence half of the contract has no measurable charge on any shipping
> machine and costs 3.45% where it has nothing to remove. What is left is a
> cheap mechanism for a problem the paper has itself shown to be narrow.

I cannot currently refute this. I can only scope it: the response is that the
narrow class is the *right* class, that no shipped control can address it at
any price, and that the cost of the fix is zero architectural state. Whether
that is an ASPLOS paper is a judgement call, and it is the judgement the lead
has to make.

### TE-6 — What single experiment would most change the verdict?

Not another 2×2. The decisive missing datum is: **does a real, named,
economically important workload contain a low-MLP victim that a co-resident
immutable stream measurably harms, on silicon, and does CAT fail to fix it?**

We have two-thirds of this already. E2 shows CAT failing on silicon against a
constructed victim. DuckDB shows a real application moving 5.8 points. What is
missing is one real workload where the victim is *demonstrably* low-MLP and the
harm is *large* — an OLTP index probe, a B-tree point-lookup service, or a
transaction chain co-located with a scan. That is a **silicon** experiment,
needs no simulator, and would convert §5 from a limitation into the paper's
scoping contribution.

If that experiment comes back small too, the honest conclusion is that the
paper is a characterization-plus-mechanism paper for a workshop or a
lower-tier venue, or that it needs the three months Plan B allocates to find
its class.

---

## 7. Where this leaves the paper — three options, with odds

**(A) Submit as a performance paper.** Requires numbers we do not have and
cannot get from the current apparatus. *Odds: reject.* Not recommended.

**(B) Submit as a scope-and-abstraction paper with a cheap mechanism.** Lead
with E1–E3 (silicon, necessity, cross-vendor non-coincidence), E7 (cost ≈ 0),
and §5 promoted from limitation to **contribution** — "here is exactly which
victims are harmable and why, and here is the only control that can name
them." E4–E6 become the existence proof that the mechanism does what the
contract says, explicitly at their stated operating point. H3 stated as a
bounded capability with its price disclosed. *Odds: contested but real.* This
is what the evidence supports and what the current draft is closest to.

**(C) Take the three months.** Run TE-6, find the harmable real workload, and
come back with a 5–15% application number plus everything above. *Odds:
substantially better, if TE-6 lands.* This is what Plan B already schedules.

**B and C are not exclusive** — B is what we would submit if forced to submit
now; C is B plus the one experiment that would make it comfortable.

---

## 8. What is now blocking, and it is not measurement

W1 passed, W2.1 answered, W3.1 closed, W6 complete, W7 adjudicated, W8's
attribution question closed today. **39 rows of adjudicated paper edits are
queued behind one unmade decision** — whether and how to tell the co-authors
the Sep 9 submission is being skipped — because the paper tree publishes on
write. Nothing measurable is on the critical path. Two lead decisions are:

1. **Venue and date.** Everything is sized to ~3 months; the target is unset.
2. **Co-author communication.** This gates the entire edit queue.

And one newly informed by today's result: the full-system capability
demonstration can be finished on a **classic-memory** restore (both gate
counters are arch-side, and the demonstration licenses no performance
comparison, so Ruby is not load-bearing). That is a cheap way to close E8
completely. It has not been started.

---

## 9. The one-sentence version

*We can prove the problem is real on silicon, that no shipped control can
express the fix, and that the fix costs no new architectural state — and we
can prove the fix works, in simulation, on exactly the victim class our own
data show is narrow. Whether that is an ASPLOS paper depends on whether the
narrow class can be shown to matter, and that is one silicon experiment away.*
