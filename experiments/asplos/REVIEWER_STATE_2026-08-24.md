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

---

# Addendum 1 — 2026-08-24, after three rounds of external review

The body above is left verbatim. **Its §4 is wrong as written and §7's options B
and C are dead.** This addendum states what replaced them. Everything here was
verified against committed artifacts; where a reviewer's citation did not
survive that check, it is said so.

## A1. §4's sharp form is retracted

§4 claimed the harm and the benefit "are not the same experiment, the same
victim, or the same operating point." That is false, and the counter-evidence
was already in the draft. `GATE1_STREAMER_COST_OUTCOME.md`: flush-behind on
AMD Bergamo, hash-join cross-process, victim-first, 256 KiB distance, **n=12,
frozen at DutyFree `0628e0d`**, recovers **76.3% [76.1, 76.4]** of a **6.484×**
tax at full prefetch bandwidth — victim **406.25 → 144.21 cyc/access, 2.82×
faster** — at a measured, non-embargoed streamer cost of **31.34% [31.28,
31.39]**. Same arm, same provenance record. Silicon, real workload, at the
operating point of the harm.

So the defensible chain is: **silicon** — non-allocation removes most of a large
tax; **silicon** — every deployed *single* knob pays for it; **simulation** — a
translation-carried type achieves it without the self-cost. Only the last link
is simulated, which is the ordinary condition of an architecture proposal.

Two notes that matter. GATE1 withheld the "H2 does this without the self-cost"
sentence pending the h1bw anomaly; **that anomaly was resolved 2026-08-18**
("two misreadings, no model defect"), so the sentence is now writable. And the
publishable magnitude is **2.82×, not 2.33×** — 2.33× is the untraceable
RocksDB number (N7), and 2.82× is better *and* sound.

## A2. The scissors — the finding that replaced options B and C

`W5.3_L5_EVIDENCE_2026-08-23.md`, cross-process, with the no-co-runner control
the 2×2 lacked: Intel SPR 1.62× → **1.00× under CAT12 alone at 0.7%** streamer
cost; AMD Bergamo 18.73× → **1.07× under CAT12+MBA192 at 96%** of full stream
bandwidth. Deployed knobs *in combination* occupy the corner for cross-process
colocation on both vendors. L5 ("no deployed alternative occupies the corner")
is dead there, and the project's own document says so in its title.

Now set that beside the same-thread evidence, and the two branches invert:

| | deployed knobs | STREAMING's measured payoff |
|---|---|---|
| **reuse thread never touches stream data** | CAT12 → 1.00× @ 0.7% (Intel); CAT12+MBA192 → 1.07× @ 96% BW (AMD) | large — 76.3% of 6.484×, silicon |
| **reuse thread also touches stream data** | **every deployed control makes it worse** (A3) | **≤0.6% measured; ≤31% attributable ceiling** |

**The case where STREAMING is uniquely expressible is the case where its
measured payoff is smallest. The case where its payoff is large is the case
shipping knobs already handle at ≤4% cost.** Everything the paper can uniquely
claim now funnels through one aperture: **the OS thread.**

**Second blade — stated as an inference, not a result.** H1's bandwidth survival
*depends* on the stream occupying private L1/L2 and MSHRs, which is the same
occupancy that displaces a hot set sharing that thread. If that is the whole
story, the same-thread case is reachable only by a **stream-buffer** realization
(staging outside the private caches), which forfeits "zero new architectural
state" — our single best fact. Those two cannot headline the same paper. **But
~69% of the fused tax is undecomposed**, and two mundane causes have never been
excluded (A5), so "requires new hardware" is not yet earned.

**Do not attempt to reopen the cross-process branch.** It reads as motivated
reasoning to anyone with a Bergamo box, which is how W5.3 was produced.

## A3. The lead exhibit — and why it cannot lead yet

`results/clos_split/raw/`, silicon, same-thread fused kernel (throughput /
cyc-per-access):

| arm | thr / cyc-acc | vs unmitigated |
|---|---|---|
| Quiescent | 391.93 / 61.71 | — |
| **Fused, unrestricted** | **336.58 / 88.45** | 1.4737× tax |
| Fused + CAT 20/20 | 336.99 / 87.65 | no partition applied |
| Fused + CAT 12/20 | 281.02 / 105.12 | **worse** |
| Fused + CAT 8/20 | 253.36 / 115.81 | **worse** |
| Fused + CAT 4/20 | 234.44 / 126.86 | **1.43× worse** |
| Fused + `PREFETCHNTA` | 298.06 / 98.37 | **worse** |
| Split threads, no CAT | 214.58 / 95.69 | **worse**, at 0.6375× throughput |
| Split + CAT 1-way scan | 214.98 / 95.37 | CAT changes nothing |

Read the CAT column downward: **the harm is monotone in how hard the mitigation
is applied.** The enforced context-scoped control, the advisory address-scoped
control, and the software restructuring all make the victim worse; tightening
makes it worse faster. This is L2 — the missing admission cell — on silicon,
and it is the strongest exhibit the project owns.

**It cannot be Figure 1 today.** Ledger finding F1: this is `tab:fused`, "the
paper's strongest experiment and its raw data is **not in git**" —
`.gitignore:3 results/`, 660 files, no commit binds it, the bsweep runner is
**absent**, and the records carry no `cmd` field and no CAT/way field, so **the
applied way count is asserted by the filename, not recorded by the instrument.**
One `/tmp` sweep or disk loss from being the next N7. Mitigation is cheap and
listed: `git add -f results/clos_split/`, write the runner retrospectively and
label it a reconstruction, and state in the caption that the way count is
carried by the filename. **Do this before the exhibit is asked to carry
anything.**

Also precise: "all 18 cells reproduce exactly" means *recomputed from the same
raw files matches published* — provenance verification, **not** re-measurement.
No n or CoV has been established. Both are required before it leads.

## A4. The expressibility boundary is the OS thread, not the process

`resctrl` assigns CLOS **per task** (`IA32_PQR_ASSOC` is context-switched; the
`tasks` file takes TIDs). So "compaction and serving share a process, therefore
CAT is structurally inexpressible" — the stated rationale for the RocksDB
anchor, and a claim of ours, not only a reviewer's — is **false**. Only
*intra-thread* is inexpressible. Consequences: the LSM shape sits in the
*expressible* branch, so its argument is operational fragility (per-thread CLOS
management, vendor-specific knobs), not capability; and any same-thread anchor
must register **expressibility** as its endpoint, never magnitude.

**Branch B's candidate population, unmeasured but architecturally exact:**
thread-per-core runtimes (Seastar/ScyllaDB, Redpanda) multiplex compaction,
streaming and serving on one OS thread per core *by design*, are therefore
unreachable by per-TID CLOS, and cannot "just split threads" without
re-imposing the 36.2% our own split measured. Plus fused query engines. That is
the anchor candidate.

## A5. The new critical path: decompose the fused tax

≤31% of the 1.4737× fused tax is attributed to shared-LLC residency; in
simulation H2 engaged exactly as specified (HNF fills 1,340,360 → 542,011,
−59.6%; victim DRAM 12.09 → 10.05 MB, −16.9%) and moved cost **72.428 → 71.993,
−0.6%**. W7's null, the ≤31% silicon ceiling, and that gem5 result are **three
instruments agreeing on one cap** — present that convergence as evidence, not
as three disappointments.

The other ~69% is unknown, and it decides which paper exists:

- **TLB.** A reviewer cited "the campaign records the stream on 4 KiB pages
  (`AnonHugePages=0`)." **That string is not in this repo** — the citation does
  not survive checking. The hypothesis survives on better grounds: the hosts run
  `THP: madvise`, so a plainly-`mmap`ed stream buffer *is* on 4 KiB pages, and
  separately `tab:appplat` carries a defect where the paper asserts
  pre-allocated 2 MB hugepages that the live readout reports as **0/0/0 on all
  three nodes**. A hugepage arm is a one-line change and must run first.
- **MSHR/LFB occupancy.** If the contended resource is miss-tracking slots
  rather than lines, a staging buffer does not help — fills into it still
  consume MSHRs — and the honest mechanism is per-thread MSHR reservation, a
  different structure with different prior art. `offcore_requests_outstanding`
  decides it in days. Note this build has **no** MSHR-occupancy stat
  (`lqAvgOccupancy` is a load-queue ratio and is barred as a substitute), so
  this is a silicon measurement.
- Plus the hot-set sweep across the L2/LLC boundary and level-wise hit
  distribution, both already open in the §3 margin notes.

**Building a buffer model before running this risks a quarter on the wrong
structure.** The consume-in-place experiment is absorbed here; post-W5.3 its
"just use more cores" target is moot.

**End-to-end headroom, stated up front:** quiescent 391.93 vs fused 336.58 caps
pipeline recovery at **~16.4%** even for a perfect fix, and only when the probe
is on the critical path.

## A6. Corrections owed to the reviewers' own numbers

Three reviewer citations did not survive verification, and the pattern is worth
more than the corrections:

1. **"15.8 GB/s (WB) / 4.2 GB/s (WC)" per core.** "15.8" appears nowhere in the
   repo; "4.17 GB/s" exists but is our **WB** pure-stream figure in the gem5 SE
   model, not WC. The reviewer took the pair from the draft's own prose — so the
   intro's motivating single-core WB/WC contrast, and the "five WC cores to
   match two WB cores" claim in the same family, are **N7-class and join the
   W4.2 repair list.** The qualitative argument survives (MSHRs are
   timing-critical CAMs stuck in the tens; prefetch-queue depth is cheap SRAM);
   the arithmetic must be re-derived or dropped.
2. **"the non-enrolling stream is faster, 3.8 vs 2.5 GB/s."** Unsourced here.
3. **The `AnonHugePages=0` citation** (A5).

**A review inherits provenance rot from the text it reviews.** That is how N7
propagates outward, and it is the strongest practical argument for doing the
hygiene pass before anyone else reads the draft.

**One comparison to pre-empt rather than concede.** A referee will set the
deployed combination's 1.07× residual against our own non-allocation proxy's
2.30× and conclude CAT+MBA beats flush-behind. Those are **different victims,
different workloads, different taxes** (18.73× index-probe vs 6.484× hash-join)
— comparing their residuals is precisely the arm-identity violation §5.1
forbids. Name both arms at the point of use and the comparison dissolves;
concede it and it is fatal.

**W5.3's own reporting obligations, before it carries any argument:** its 18.73×
is in the *pointer-chase* family, not the hash-join family; victim identity,
arrival protocol and n must travel with every cell; and the Intel 1.62× sits at
a different operating point from the earlier 2.03× (CXL-8, 170 MB) — say which.

## A7. The provenance list, complete

This is the honest answer to "is it submittable": no, and not close, before any
framing question. From `W4.3_PROVENANCE_LEDGER_2026-08-23.md`:

| item | state |
|---|---|
| `tab:amdcat` | **UNTRACEABLE** (n=210 file gone); verified replacements exist, unsubstituted in 5 places |
| RocksDB 2.33% / 54% prose | **UNTRACEABLE**; nearest survivor disagrees (2.29× / 47%) |
| `tab:fused` | **raw not in git**, runner absent, way count carried by filename (F1) |
| `tab:h1bw` | artifact found, **ordering not reproduced** (F3) |
| `tab:h3sf` | data verified, **annotation wrong** — cited commit predates the required one (F4) |
| `tab:gem5` +H2 column | **declared gap** — not re-instantiated at the WB column's commit |
| intro WB/WC single-core bandwidth pair | **newly suspected N7** (A6) |
| `tab:gem5cfg` | verified 13/15; 1 defect, 1 imprecision |
| `tab:appplat` | verified except 1 defect (hugepages 0/0/0) + 1 unit inconsistency |

## A8. Revised order, and one decision I am not taking

1. **Hygiene** — W4.2's substitution, the RocksDB prose, and the intro
   bandwidth pair. Days. Unarguable.
2. **Pin `results/clos_split/`** (`git add -f`), write the runner as a labelled
   reconstruction, establish n/CoV. Before the exhibit leads anything.
3. **The fused-tax decomposition** — hugepage arm, `offcore_requests_
   outstanding`, hot-set sweep, level-wise hits. Days to two weeks, hardware in
   hand. **This is the new critical path and it replaces every previously
   proposed anchor**; it decides whether the Branch-B fix is software, a
   staging buffer, MSHR QoS, or nothing reachable.
4. Assemble the A1 chain re-scoped to *mechanism attribution*, with W5.3 printed
   beside it.
5. Fork on the decomposition. If a mechanism paper: pre-register victim-side
   endpoints **and** the ~16.4% headroom bound; thread-per-core runtime as the
   anchor, expressibility registered.
6. Deferred: the service census, the SHiP port, standalone virtualization and
   security sections, and the standalone consume-in-place run (absorbed into 3).

**The rule this addendum earns, as process rather than hindsight:** *before
adopting any spine, enumerate the least expensive configuration a hostile
referee could run against its central sentence, and run that first.* Three
rounds, three spines, and each died to a cheap adversarial configuration — the
knob **combination** (W5.3), the per-TID **scope check** (A4), and next the
**hugepage arm**. Each was affordable at any point and was run late or not yet.

**The decision I am not taking.** W5.3 is written into this memo, which is
`~/DutyFree` and authorized. Writing it into `~/STREAMING_Paper/` sets page-1
evidentiary posture and W5.3 itself records that as a §9 lead-only decision.
The reviewers argue it can no longer wait, and I think they are right — three
documents' spines die on it. **It is still the lead's call, and the co-author
conversation should lead with it.**

---

# Addendum 2 — 2026-08-24, same day: A5 is wrong; the decomposition already ran

Addendum 1's §A5 declared the fused-tax decomposition "the new critical path,"
said "~69% of the fused tax is undecomposed," and called the second blade "an
inference, not a result." **All three are wrong.** The decomposition ran on
**2026-07-29**, pre-registered, three instruments, n=30 per point, with a
committed 18 KB report (`results/mechanism_decomp/
MECHANISM_DECOMPOSITION_REPORT.md`) and three committed runners
(`run_m2_sweep.py`, `run_m3_m4.py`, `run_m5_remote_stream.py`). I did not read
it before writing A5. That is F11 committed by the person who wrote the F11
fixes, and the fix that would have caught it — `ls` the results tree before
writing a memo about the plan item — is fix #5, in my own list.

## B1. What it found

Pre-registered decomposition `Δ_LLC_upper ≈ max(0, Δ_total − Δ_L2fit − Δ_M5 −
Δ_M3)`, at the 170 MB operating point:

| | 1 core | 16 cores |
|---|---:|---:|
| `Δ_total` | 27.31 cyc | 27.63 cyc |
| `Δ_L2fit` (strict, 256K — unambiguously L2-resident) | 27.80 | 27.32 |
| `Δ_L2fit` (generous, 1M — minimum of the M2 curve) | 19.25 | 19.31 |
| `Δ_M5` (bandwidth-matched remote-socket residual) | −0.44 | +0.80 |
| `Δ_M3` (MSHR/outstanding-miss) | unattributed | unattributed |
| **`Δ_LLC_upper` strict** | **0.00 (0%)** | **0.00 (0%)** |
| **`Δ_LLC_upper` generous** | **8.51 (31%)** | **7.52 (27%)** |

> **Verdict, in the report's own words: "`Δ_LLC_upper/Δ_total` is at most ≈0.31
> and could be as low as 0 … both readings fall at or below the pre-registered
> 'H2 story in trouble' threshold (≤0.30), and neither approaches the 'sound'
> threshold (≥0.60)."**

Almost the entire fused tax is **already present at L2-fit scale, with no LLC
involvement at all.** Memory-path queueing explains essentially nothing
(`Δ_M5` ≈ 0, mixed sign). `Δ_M3` was set to 0 deliberately — the
generous-to-H2 choice, since crediting it would push `Δ_LLC_upper` lower still.

Three further findings that bear directly on this discussion:

- **The MSHR candidate has positive evidence, not merely plausibility.**
  `L1D_PEND_MISS.FB_FULL` grows **3.84×** (1c) and **11.68×** (16c) under load,
  while *average* outstanding depth is flat (1.01×) / slightly down (0.90×,
  CoV 14.9%). The report refuses to reconcile them into a cycle cost without a
  causal model it does not have, and says so.
- **CHA TOR latency to the hot table's own destination rises +14.2% (1c) /
  +31.4% (16c)** — misses become more expensive, not just more frequent.
- A checked microarchitectural aside: removing the stream made the probe
  *slower* (91.5 vs 84.4 cyc/access), consistent with the real CXL load's
  latency overlapping the probe's via out-of-order execution. Flagged as a
  hypothesis, not converted into a number.

## B2. What this does to the scissors, and to the paper

**The second blade is measured, not inferred.** The same-thread tax lives where
H2 explicitly does not reach — private-cache displacement plus unattributed
miss-tracking pressure. A2's inference is upgraded to a result, and the panel's
"not yet earned" is withdrawn on this point.

**And the paper already says so.** `Sec5_Evaluation.tex:382-389`: "\emph{not}
where H2 pays off: the hardware decomposition attributes $\le$31\% of the
1.47$\times$ same-thread tax to shared-LLC residency … the hardware
decomposition is the authority here. The fused kernel is necessity."
`Abstract.tex:48` carries the same note. **The draft is more honest than this
memo credited it with being.** What has not propagated is narrower and still
matters:

1. **Only the generous bound travels.** The paper prints "≤31%"; the strict
   L2-fit reference reads **0.00%**. Under §5.1 both belong at the point of use,
   or the sentence must name which reference it is using.
2. **The pre-registered verdict appears nowhere outside the report** — the
   string "H2 story in trouble" is absent from every other file in the repo and
   from the paper. A pre-registered threshold that is crossed and not reported
   is the same defect as a falsifier that fails and is not printed.
3. **The report and its 1,402 raw files were not in git** (`.gitignore:3
   results/`), so the paper's stated *authority* for its fused claim had the
   same exposure `tab:fused` used to have. Fixed in this commit (B3).

## B3. Done in this commit — and a correction to A3

`git add -f results/mechanism_decomp/` (1,402 files, 24 MB): the report that is
the paper's stated authority for its fused-case scoping is now pinned in git
instead of surviving on one host's working tree.

**A3 is out of date and this corrects it.** A3 said `tab:fused`'s raw data is
"not in git", quoting ledger finding F1. It *was* pinned, at commit `a41df38`
("F1.1: pin tab:fused's raw data in git, with its four known provenance defects
stated alongside") — 1,177 files, already tracked. The W4.3 ledger entry that
A3 quoted was written before that fix and was never amended, so I read a stale
finding and repeated it. **`tab:fused`'s exposure is closed; only the second
artifact needed pinning.** Still owed on `tab:fused`: the bsweep runner as a
labelled reconstruction, the caption stating that the applied way count is
carried by the filename, and n/CoV. Note `results/` remains in `.gitignore`, so
both trees are pinned by `-f` and future runs are still unversioned by default.

## B4. Revised order, replacing A8

1. **Hygiene** — W4.2's substitution, the RocksDB prose, the intro WB/WC
   bandwidth pair. Unchanged, unarguable, days.
2. **Propagate the decomposition properly** — the strict 0% reading beside the
   generous 31%, and the pre-registered verdict in the text. Hours, and it is a
   §5.1 obligation, not a choice.
3. **The hugepage/TLB arm** — the one candidate the 2026-07-29 decomposition did
   *not* cover, and still genuinely unexcluded. One-line change. This is what
   survives of A5's "critical path", and it is now a small task rather than a
   campaign.
4. Assemble the A1 chain re-scoped to mechanism attribution, with W5.3 printed
   beside it.
5. Fork. Note the fork is better posed than A5 said: the dominant measured term
   is L2-fit-scale private displacement (which a staging buffer would address)
   while `FB_FULL` points at miss-tracking pressure (which it would not). The
   report declines to separate them and names exactly what is missing — "a
   validated cycles-per-access conversion for `Δ_M3`". That conversion, not a
   new campaign, is the gate on which structure a mechanism paper would propose.
6. Deferred as before.

## B5. The process finding, which is worth more than the datapoint

Three rounds of external review, a 550-line memo, and a rebuilt project plan all
treated the fused decomposition as open. It had been closed for four weeks, by a
pre-registered experiment with committed runners, and its verdict was harsher
than anything the reviewers proposed. The number that escaped the report (≤31%)
reached the paper; the **reference it was conditioned on** (generous, not strict)
and the **verdict it triggered** ("in trouble") did not. That is §5.1's rule —
every figure names its arm and operating point — applied to a *threshold*, and
it is the same failure mode as premise 1's overturn in `PLAN_B_REBUILD.md`:
not a missing measurement, but a measurement that was never read against the
document that needed it.

A5's rule stands and now has a fourth instance. It gains a clause:
**before declaring any experiment the critical path, `ls` the results tree and
read what is already there.**

---

# Addendum 3 — 2026-08-24: two objections to the execution plan, and A2's table corrected

## C1. A2's scissors table, corrected to print both readings

A2's Branch-B cell reads "≤0.6% measured; ≤31% attributable ceiling." That
prints only the generous bound, which is the defect T1 exists to fix. Corrected:

| | deployed knobs | STREAMING's measured payoff |
|---|---|---|
| reuse thread never touches stream data | CAT12 → 1.00× @ 0.7% (Intel); CAT12+MBA192 → 1.07× @ 96% BW (AMD) | large — 76.3% of 6.484×, silicon |
| reuse thread also touches stream data | every deployed control makes it worse | **0.00% of the fused tax on the strict L2-fit reference, ≤31% on the generous one** (pre-registered verdict: *"H2 story in trouble"*); **−0.6% measured** in the gem5 fused arm |

## C2. T4's proposed calibration knob is barred by a standing rule of this project

T4 proposes fitting an arrival × residence occupancy model against variation
induced by "prefetch-distance MSRs, streamer thread count, and MBA caps, which
W5.3 conveniently just validated as a clean rate knob." Two of the three are
wrong:

- **MBA is a pacing throttle, and pacing throttles are barred here.**
  `W3.1_CLOSED_2026-08-23.md:16` and `GPROBE_OUTCOME.md:211` both state the
  standing rule verbatim: *"Thread count is the honest way to vary this; the
  `-R` pacing throttle carries a known confound and was not used."* MBA is the
  same class of intervention — inject delay to reduce rate — and the confound is
  the same: it perturbs the arrival *distribution*, not only the arrival *rate*.
  Using it to identify the arrival term of an arrival × residence model is
  circular.
- **W5.3 did not validate MBA as a clean knob; it demonstrated the opposite.**
  Arming without binding does nothing (24.52 GB/s → 13.35×; 24.54 → 12.44×),
  then recovery appears discontinuously where the cap begins to bind (23.56 →
  **1.08×**) and stays flat from 96% of bandwidth down to 8%. That is a step
  function with an unexplained mechanism — the worst available choice for a
  continuous calibration variable. A fit against it would fit the artifact.
- **"Prefetch-distance MSRs" need to be shown to exist before they are
  budgeted.** The documented Intel prefetch-control MSR (`0x1A4`) carries
  enable/disable bits for four prefetchers, not distance; no architectural
  prefetch-*distance* control is documented for SPR/EMR. If a knob is intended
  here, name the register and verify it on the host first.

**Use thread count as the primary lever**, per the standing rule, and add
hot-set size (the M2 curve already sweeps it) as the second axis. Both vary
occupancy without touching the arrival distribution. If a rate knob is genuinely
required to separate the terms, that is a finding to report, not a knob to
reach for.

## C3. T5 is required, not conditional, and it is larger than "a small n-boost"

T5 says an n-boost rerun is needed "only if the existing n is thin." **It is
thin: W5.3's family runs n=3 per cell**, and the surrounding campaign documents
bistability rather than noise — `GPROBE_OUTCOME.md` records per-rep sequences
like `20.42 / 20.42 / 20.42` beside `22.69 / 20.42 / 22.70` in adjacent arms,
notes one matrix "happened to sample only the clean state," and elsewhere
reports three reps of **[166.8, 435.5, 219.8]** — a 2.6× spread. A 3-rep mean
over a bimodal distribution is not a point estimate.

This matters because W5.3 is now load-bearing *against* us: it is the evidence
that killed L5 cross-process and closed options B and C. It survived our attack;
it has not yet survived a statistical one. Before it leads: per-rep values and
CoV for every cell that carries the argument, an explicit statement of the
bistability and which state each cell sampled, and enough repetitions to
characterize a mixture rather than average across it. **If the AMD 1.07× turns
out to be a mixture, the scissors' Branch-A blade is blunter than A2 states** —
which would be good news, arrived at honestly, and must not be gone looking for
selectively. Pre-register the rep count and the mixture test before running.

## C4. What the plan is missing

The 39 adjudicated rows in `W4_PAPER_EDIT_QUEUE_2026-08-23.md` were adjudicated
under the pre-scissors spine. Some are now wrong rather than merely stale, and
no item in the plan re-adjudicates them. Add that to T6, before the restructure
consumes them.

## C5. Done here

T1's non-publishing half: this addendum, and a dated correction appended to
`W4.3_PROVENANCE_LEDGER_2026-08-23.md` recording that F1 is stale (`tab:fused`
pinned at `a41df38`), adding the missing `results/mechanism_decomp/` row, and
stating the decomposition's two reporting defects. T1's publishing half — Sec5
and the abstract's framing — is held: it is a paper-tree write and the plan
itself gates those on T0.
