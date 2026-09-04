# Complete pre-submission TODO, with reasons, expected results, and what each proves

Written 2026-08-19. Every item states *why* it is needed, *what we expect*, and
*what the evaluation would establish* — because several of these can come back
negative, and that has to be planned for rather than discovered.

Ownership: **[OS]** kernel team, **[G5]** gem5 team, **[E2E]** benchmark team,
**[LEAD]** decision rather than work.

---

# P0 — Blocking. Each one is a named reviewer objection.

## 1. Intervals on every cited gem5 magnitude **[G5]**

**Reason.** No gem5 number in the paper has a variance estimate, and
`tab:gem5`'s caption now says so explicitly while the hardware column beside it
says $n{=}30$. That asymmetry is visible on the page. Critically, the obvious
mechanism does not work: `SEED` is **not** the lever. A fixed-seed control run
drifted 0.047% from its counterpart — the same magnitude as the cross-seed
spread (0.043%) — so the variation is run-to-run nondeterminism, not a
seed-controlled quantity. The mechanism is **repeated identical runs**.

**Expected result.** Tight. Observed spreads are 0.02–0.34% on bandwidth and
~0.05% on fill counts, so intervals should be small enough to *strengthen* every
ordering the paper claims. Low risk of a surprise.

**What it proves.** That the reported orderings — H2 vs WB vs WC, predictor vs
declaration, the MSHR sweep — are not single-run artifacts. It converts "single
runs, no interval" from an admitted weakness into a bounded one, and lets four
tables carry $\pm$ figures. This is the cheapest credibility purchase available:
pure compute, embarrassingly parallel.

## 2. Measure the ranged drain on real hardware **[OS]**

> **CLOSED 2026-09-04 — and this item's own prediction is CONFIRMED.** "Entry
> should collapse from ~48 ms to microseconds" is exactly what happened:
> baseline H2 entry is measured at **72–90 µs** (QEMU/KVM, four boots) and
> **124 µs** (gem5 r12). Nobody recorded the closure at the time, so this item
> sat open under **P0 — Blocking** for sixteen days after the evidence for it
> landed. See "Closure — 2026-09-04" at the end of this file. The text below is
> left verbatim per `A6.19`; read its present tenses as "as of 2026-08-19".

> **The "124 µs (gem5 r12)" above is corrected — see "Correction to the closure
> — 2026-09-04" at the end of this file.** It is a clock-quantisation artifact,
> not a measurement. The citable figure is **72–90 µs on QEMU/KVM**; the
> closure itself stands and its prediction is still confirmed.

**Reason.** The ~48 ms machine-wide, size-independent, unprivileged epoch-entry
stall is the single most quotable objection in the paper — a DoS primitive in a
multi-tenant pooled-memory proposal. The mitigation is now merged and
boot-tested (PR #3), but QEMU cannot reproduce WBNOINVD cost, so its **benefit
is unmeasured**. Requires the patched kernel booted on the measurement host.

**Expected result.** Entry should collapse from ~48 ms to microseconds, because
the broadcast is simply gone. Exit becomes $O(\text{object})$: a 1 GB object is
~16.7M lines, and since epoch-exit lines are *clean* (invalidate-only), a few ms
is the plausible band — a 10–40x improvement at the evaluated size.

**Honest risk, pre-registered.** Exit cost now *scales with object size*, so
there must be a crossover where a large enough object costs more to drain by
line than to flush wholesale. If that crossover sits below realistic CXL object
sizes, the result is **negative** and the paper must say the relocation helps
small epochs and not large ones. Measure the curve, not a point.

**What it proves.** That the transition cost is an artifact of x86 exposing
memory-type change only as a machine-wide event, not something intrinsic to
object-scoped memory types — which is exactly the claim `Sec5` makes and
currently cannot support. It also restores the figure deleted from `Sec5` as a
TBD, and turns the DoS from a disclosed weakness into a solved problem.

## 3. Sweep the cross-core predictor result **[G5]**

**Reason.** The paper's strongest new result — a tuned predictor recovers
**none** of a co-runner's tax (1.671x against a 1.655x baseline where H2 reaches
1.012x) — is currently **one point**: one victim size, one stream size, one
predictor, one run. A reviewer will ask whether it is an artifact of that
sizing, and they should.

**Expected result.** A characteristic curve. Inside the protectable window
(victim larger than the private L2, smaller than the shared LLC) H2 should track
quiescent and the predictor should track write-back. Outside it the arms should
converge — below the L2 there is nothing at risk, above the LLC there is nothing
to protect. The gap should be widest mid-window.

**What it proves.** That "prediction is self-serving, declaration is
other-serving" is a property of the *mechanism* rather than of one operating
point. This is the difference between an anecdote and a finding, and it is the
paper's main empirical edge.

---

# P1 — Closes a promise the paper currently makes and cannot keep.

## 4. Object-scoped I0: multi-mapper sealed memfd **[OS]**

**Reason.** The abstract motivates with sealed SSTables, Parquet fragments and
Ray Plasma objects. The artifact accepts anonymous memory, hugetlb, and a sealed
memfd **with a single mapper**. Plasma's entire purpose is *multiple* readers.
This is the last place the paper promises something the artifact cannot do.

**Expected result.** N readers of a sealed memfd each receive slot-6 PTEs on
first `mmap`, inherited from the object rather than chosen per mapping, so I0
holds by construction with no cross-`mm` rewrite. A selftest with two or more
mappers passes where today it returns `EINVAL`.

**Where the work actually is.** Not the hook — `shmem_mmap()` already has the
inode, seals and vma, and `seal_check_write()` refuses writable shared mappings
for free. The work is the **object lifecycle**: per-mapping revocation would
violate I0, so the type must persist for the object's life, which moves the
drain to inode eviction where there is no mapping to walk. The flush must
iterate the `address_space`'s folios, with THP and swap in scope.

**What it proves.** That the contract composes with a lifecycle a deployed
system already implements — Plasma's create/write/**seal**/share *is* the epoch
at application level. It converts the motivation from aspiration into
demonstration, and it is the strongest available answer to "can you run what you
motivate with?"

## 5. Real-application streamer cost for the flush-behind anchor **[E2E]**

**Reason.** Flush-behind is the paper's only silicon bridge from *label* to
*benefit* — software-emulated H2 recovering 76.3% of a 6.484x tax on real AMD
silicon. Its streamer cost (31.3%) currently comes from a **synthetic**
aggressor's self-cost, and the repo itself states this is not the
real-application number the frontier table wants.

**Expected result.** GAPBS and DuckDB streamer cost under flush-behind,
plausibly in the same 20–40% band.

**What it proves.** That "retention control charges the streamer" holds for real
applications and not only for a microbenchmark. Since the paper's argument is
that a declaration charges the streamer *nothing*, the contrast is only as
credible as the measured cost it is contrasted against.

---

# P2 — Provenance debt. Protects existing claims rather than adding new ones.

## 6. `tab:h3sf` archaeology **[G5]**

**Reason.** Two of four rows re-instantiate ~18% high, and no counter reproduces
the claimed 3,683 back-invalidations; the documented 65,536-entry SF geometry
likely does not apply to them. The caption discloses this honestly — but H3's
*quantitative* support rests on exactly those rows.

**Expected result.** Either the true geometry is recovered and the rows
re-derive, or they are replaced with re-measured values at a documented setting.

**What it proves.** That C9 — H3 removes snoop-filter pressure H2 cannot — is a
measurement rather than an unreproducible artifact. Without it, H3's only solid
evidence is the TLA+ soundness check and the argument.

## 7. RocksDB provenance, or withdrawal **[E2E]**

**Reason.** The 2.33x is AMD-only, 1.00x on Intel at matched geometry, and no
raw data survives. An artifact evaluator asking for it gets nothing.

**Expected result.** A re-run with a recorded manifest, or the number removed.

**What it proves.** Nothing new — it prevents an existing application-level
claim from being struck, which is the whole value.

## 8. Complete `tab:appplat` **[E2E]**

**Reason.** Missing microcode/stepping and the AMD CXL device attribution.
Platform tables are the first thing an artifact evaluator reads.

**What it proves.** Reproducibility of every silicon measurement in the paper.

## 9. Fix or bound H2's under-enforcement in the model **[G5]**

**Reason.** Fill suppression is prefetch-mediated and degrades 77.3% -> 57.2% as
`L1_MSHR` goes 16 -> 64; with prefetchers off it is invariant at 44.0%. The
direction is conservative — the model *understates* H2 — so nothing published is
invalid, and all paper numbers sit at the well-behaved default. But an artifact
evaluator running at a different MSHR setting sees a different H2.

**Expected result.** Localise the fill path that fails to carry the STREAMING
attribute into the private-cache entry (a protocol trace will name it), then fix
it or document the bound.

**What it proves.** That gem5's H2 faithfully implements the contract it is named
after — which matters because every simulation claim in the paper rests on it.

---

# P3 — Needs a resource or a decision, not effort.

## 10. Arm / Neoverse outer-non-cacheable measurement **[LEAD]**

**Reason.** `Sec5_5:148` names this as "the strongest available portability
evidence for *H2*; we have not run it." Needs hardware the project does not have.

**What it proves.** C11 — that the missing admission cell is an x86 accident
rather than a universal law, and that the mechanism is not vendor-specific. This
is the difference between "an x86 fix" and "an abstraction."

## 11. One full-system gem5 run **[G5]**

**Reason.** The OS and hardware halves are never exercised together: the OS side
is silicon-only, the hardware side SE-mode-only. The paper's own margin note
calls for one FS demo as an integration existence proof.

**What it proves.** That the label path survives end to end — `mprotect` through
PTE through fill decision — rather than being two half-systems argued to join.

---

# P4 — Lead decisions, no work attached

12. **Abstract length.** Now 342 words against the 316 pass 4 cut it to. Going
    lower means removing content the lead chose to keep.
13. **Conclusion wording on the drain.** Blocked on item 2: once measured, "we
    implement the ranged variant" can replace "a production ISA wants one."
14. **The δ embargo.** Whether the 3.6 figure and the residual attribution move
    is a posture call, not a measurement.
15. **Push `DutyFree` and `DutyFree-Gem5`.** Neither has been pushed;
    `DutyFree-Linux` now is.
16. **Send `EUNJI_QUESTION_DRAFT.md`** — the canonical-config lineage question
    only the lead can ask.

---

# Explicitly NOT to do

- **Port SHiP into Ruby** (~6 core call sites) unless a reviewer demands a
  signature-based predictor. The admission argument is structural and BRRIP
  already demonstrates it.
- **RTL or FPGA.** Review 2 ruled it out as a poor use of remaining time.
- **More fused-kernel sizings.** The window is measured end to end and the
  limiter is the workload's own MLP.
- **Re-running deterministic arms for confidence.** With `SEED` unset, re-runs
  are bit-identical and yield nothing.

---

# Critical path

Items 1 and 3 are compute and can run concurrently today. Item 2 needs one
machine reboot and is the highest-value single experiment on the list. Item 4 is
days of kernel work and is the only item that closes a promise rather than
strengthening a claim. Everything in P2 is bookkeeping that protects claims
already made.

**Nothing on this list requires a new idea.** The one gap that will *not* close
before submission — that H2's benefit cannot be shown on silicon, because the
repurposed PAT slot decodes to WB — is structural, is now stated at the claim
site, and is bridged by flush-behind as an acknowledged proxy.

---

## Closure — 2026-09-04: item 2's prediction is confirmed, and the item was never marked closed

**The prediction was right, and it is the entry half that is closed.** Per
`A6.19` the two superseded passages are quoted rather than deleted:

> **Reason.** The ~48 ms machine-wide, size-independent, unprivileged epoch-entry
> stall is the single most quotable objection in the paper — a DoS primitive in a
> multi-tenant pooled-memory proposal.

> **Expected result.** Entry should collapse from ~48 ms to microseconds, because
> the broadcast is simply gone.

**Replacement:**

> **Entry is closed, as predicted.** At the kernel tip (`linux` `pr4-work`, tip
> `ae43f80e67`) baseline H2 entry performs no writeback and no machine-wide
> clean: the global clean is reached only through
> `IS_ENABLED(CONFIG_PAT_STREAMING_H3_SEAL_ORACLE)` at `mm/mprotect.c:900`, and
> that symbol is **`default n`**. Measured entry cost is **72–90 µs** across
> four committed QEMU/KVM guest boots (`data/kernel/`) and **124 µs** in gem5
> r12. "Microseconds" was the prediction; microseconds is the result — a
> ~500–670× reduction against the 48 ms figure. **There is consequently no DoS
> primitive in baseline H2**, so the framing above ("a DoS primitive in a
> multi-tenant pooled-memory proposal") describes a default-off oracle rather
> than the proposed mechanism.

**The "124 µs in gem5 r12" in that replacement is corrected — see "Correction
to the closure — 2026-09-04" below.** It is a clock-quantisation artifact, not
a measurement; the citable figure is **72–90 µs on QEMU/KVM**. The replacement
above is left verbatim per `A6.19`, and **the closure it records still
stands**: the prediction was microseconds and the result is microseconds.

**What is *not* closed, and it is the more interesting half.** This item asked
for two curves, and only one exists:

1. **Entry** — closed by *removal*, not by measurement. The broadcast is gone,
   so there is no entry curve to sweep. The µs figures above are what remains.
2. **Exit** — **still unmeasured, and now unmeasurable without a code change.**
   The item's pre-registered honest risk ("Exit cost now *scales with object
   size*, so there must be a crossover … Measure the curve, not a point") cannot
   be run at the tip. Commit `888060f6a66e` removed the `drain_at_exit` debugfs
   knob **and the `streaming_drain_range()` call site**; the function is still
   defined (`mm/streaming.c:383`) and declared (`mm/internal.h`) with **no
   caller anywhere in the tree**. No configuration reaches the ranged exit
   drain, so the crossover sweep requires *reverting code*, not building two
   kernels. `RANGED_DRAIN_IMPLEMENTED_2026-08-19.md`'s forward pointer of the
   same date records this.

**So "What it proves" is now half-earned.** The claim that the transition cost
is an x86 exposure artifact rather than something intrinsic to object-scoped
memory types **is** supported at entry, and the paper states it that way
(`Sec5_Streaming.tex:156`, `Sec6_Implementation.tex:55`). The last sentence,
"turns the DoS from a disclosed weakness into a solved problem", is right about
entry and premature about exit: the exit-side drain is designed
(`RANGED_DRAIN_DOS_WRITEUP.md`) and, at the tip, unreachable.

**The process failure worth naming.** The mitigation merged via PR #3
(`b9f60fa`, `eccecc49e0ff` "ranged exit drain, replacing the machine-wide entry
writeback") and the confirming logs were committed, yet this P0 item was never
annotated. Three separate later records (`STATE_2026-08-30.md`,
`STATE_2026-09-01.md`, `PAPER_SESSION_PROMPT.md` #32) went on quoting 48 ms as
a live cost, all corrected on 2026-09-04. **The instrument was not the problem
here; the bookkeeping was.** An item whose prediction has been confirmed by
committed evidence should be closed in the same commit that lands the evidence.

---

## Correction to the closure — 2026-09-04: the gem5 124 µs is a clock artifact, not a measurement

The closure above cites baseline H2 entry as "**72–90 µs** … and **124 µs** in
gem5 r12", presenting both as measured. **The closure stands and its verdict is
unchanged** — the prediction was that entry would "collapse from ~48 ms to
microseconds", and it did, on both families. What is wrong is the **status of
the second figure**: 124 µs is not a measurement. Per `A6.19` the passages
above are left verbatim and the superseded clause is quoted rather than
deleted:

> Measured entry cost is **72–90 µs** across four committed QEMU/KVM guest
> boots (`data/kernel/`) and **124 µs** in gem5 r12.

**Replacement:**

> Measured entry cost is **72–90 µs on QEMU/KVM**, across four committed guest
> boots (`data/kernel/`) — the only resolved measurement of the quantity. The
> gem5 r12 figure is **resolution-limited**, "below the guest clock's ~1 ms
> resolution", and must not be quoted as 124 µs.

**The arithmetic.** The gem5 guest marks its TSC unstable and switches to
`clocksource: refined-jiffies`
(`gem5/logs/fs_boot_ckpt/atomic_2cpu_os_validation_h2_r1_16g/system.pc.com_1.device:107,190`).
At `CONFIG_HZ=1000` one tick is **999 848 ns** — re-derived from
`kernel/time/jiffies.c:78-104` with `CLOCK_TICK_RATE = PIT_TICK_RATE = 1193182`,
not read off a log. `streaming_lifecycle.c:175-178` prints integer-truncated
microseconds over `GENERATIONS 8`, so `enter_max` = one tick = **999 µs**,
`enter_avg` = 999 848 / 8 / 1000 = **124 µs**, and `os_validation`'s `exit_avg`
= two ticks / 8 = **249 µs**. `enter_max=999 us` is byte-identical across all
four lifecycle logs, which a genuine maximum over independent runs would not
be: **seven of the eight samples returned a 0 ns delta**, each transition being
below the resolution of the clock timing it. The QEMU/KVM family runs on
`kvm-clock` at nanosecond resolution and behaves like data — maxima 85, 156,
156, 168 µs; means 90, 90, 72, 87 µs.

**The ~500–670× above still holds**, because it was computed against 72–90 µs,
not against the gem5 figure.

**A distinction this item is the right place to record.** Neither family
measures a `WBNOINVD` broadcast, so **neither is comparable to the ~48 ms**.
That came from a third platform — the 64-logical-CPU silicon host
(`SUBMISSION_READINESS_2026-08-19.md` C10). This item's own **Reason** section
anticipated exactly that ("QEMU cannot reproduce WBNOINVD cost, so its benefit
is unmeasured"), and it is still true: the ~48 ms → µs collapse is a
**mechanism** change (`888060f6a66e`, `eccecc49e0ff`) — the oracle build issues
a machine-wide clean, the baseline issues none — and only secondarily a
platform difference. So item 2's request for bare metal was never satisfied and
was never *needed* for the entry half, which closed by removal rather than by
measurement.

**Source.** `KERNEL_TEST_AGGREGATE_OUTCOME_2026-09-03.md`, addendum 2026-09-04.
No measurement was launched; this is arithmetic over already-committed logs and
kernel source.
