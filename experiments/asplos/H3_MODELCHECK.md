# Task #29 — model-checking H3, and the soundness taxonomy

Written 2026-08-13. Answers Review 2's structural point: **H3's burden is
correctness, not benefit.** Simulation (tab:h3sf, the de-confound run) can
show H3 recovers bandwidth and removes a back-invalidation tax; it can never
establish the *absence* of a race, because a simulation only samples the
schedules it happens to generate. This is what a model checker is for.

## What was checked, and where

TLA+ / TLC (`tla2tools.jar` 2.19, `java -cp tla2tools.jar tlc2.TLC`).
Model: `experiments/asplos/model_check/H3Coherence.tla`. Five configs
(`variantA/B/C.cfg`, `variantD_unsound.cfg`, `h3off_baseline.cfg`), 2 CPUs ×
2 lines, `version` bounded to ≤2 via a `StateConstraint` (unbounded
otherwise — TLC does not terminate on it, see the false start below).

**This is not a transcription of the CHI SLICC state machine.** It is an
abstraction grounded in `H3_IMPL_SPEC.md`'s actual mechanism — the
`Allocate_DirEntry` H3 gate (`if (enable_H3_streaming_bypass && is_HN &&
tbe.isStreaming) { tbe.updateDirOnCompAck := false; return; }`), the
`dir_sharers` set `Initiate_SF_Eviction` back-invalidates, and the pure-R
states (RU/RSC/RSD/RUSC/RUSD) that carry no local data block — but it drops
per-message transport, TBE bookkeeping, and the snoop-response accounting
that `H3_IMPL_SPEC.md`'s deadlock analysis already covers separately. What
it keeps is exactly what the three properties depend on: per-line epoch
state, per-CPU cache occupancy, directory enrollment, and a version counter
standing in for "the data." **Scope claim, precisely:** this checks the
*coherence argument* for H3 (can a stale, directory-invisible copy survive
an epoch), not liveness/deadlock-freedom of the SLICC implementation (that
risk register is §(b) of `H3_IMPL_SPEC.md` and is a different question).

## The three properties, and what TLC found

| # | Property (session-prompt wording) | Formalized as | A (ReadOnce) | B (bulk-clear) | C (self-inval) | D (retain-unenrolled) | H3 off |
|---|---|---|---|---|---|---|---|
| 1 | No stale read reachable while I1 holds | `Inv1_NoStaleReadDuringEpoch`: any cached copy of a line under epoch/drain has seen the line's current version | ✓ | ✓ | ✓ | **✓** | ✓ |
| 2 | Epoch-exit drain restores full coherence | `Inv2_CoherenceRestoredAtExit`: once a line is open for writes, every cached copy of it is directory-visible | ✓ | ✓ | ✓ | **✗ VIOLATED** | ✓ |
| 3 | I1 violation with H3 off still faults via the PTE | `Inv3_WriteFaultsDuringEpoch`: version cannot move while the epoch/drain is open (write's guard never inspects the H3 knob) | ✓ | ✓ | ✓ | ✓ | ✓ |

`TypeOK` holds in all five configs (3,136 / 10,201 / 22,801 / — / 3,136
distinct states respectively; D fails at depth 5 before full exploration).

**The one honest surprise, worth stating plainly:** Variant D does **not**
violate Property 1. Its epoch is never incoherent *while open* — the bug is
invisible to a checker that only looks during the epoch, which is exactly
why "run the workload and see if anything breaks" (simulation) would not
have caught it either. It violates Property 2, at the exact instant the
epoch closes: TLC's counterexample (state 5, `variantD_unsound`) shows
`epoch[l1] = "NotStreaming"` while `cache[c1][l1] = "S"` and
`dirSharers[l1] = {}` — a retained copy that the directory has never heard
of, sitting in a line now legally open for writes. That is the coherence
hole: the next write to `l1` invalidates every *enrolled* sharer and
believes the job done, while c1's copy survives, stale, indefinitely.

Property 3 held in **every** configuration, including D — confirming the
PTE gate is architecturally independent of the H3 knob: `Write(l)`'s guard
(`epoch[l] = "NotStreaming"`) never references `Variant` or `H3Enabled` at
all, so nothing about enabling H3 on the read side can weaken the
write-side fault. This is the intended shape of the argument in
`PAPER_SESSION_PROMPT.md` §4.1.6: coherence enrollment is what H3 skips;
the immutability *enforcement* is a completely separate mechanism (the
read-only PTE) that does not depend on the directory at all.

## The soundness taxonomy

**(a) ReadOnce / no-retention — what we actually model and measure
(tab:h3sf's H3 arm).** A streaming read is never retained past its own use;
`StreamingRead` under Variant A leaves `cache` untouched. There is nothing
left to reconcile at epoch exit because there is nothing left, period. This
is the cheapest possible soundness argument (vacuous — you cannot go stale
holding a copy you don't hold) and it is also, per the honest caveat
already on record, the reason H3-via-ReadOnce measurably costs the
*streamer's own* bandwidth (WB 4.34 / H2 5.12 / **H3 1.22 GB/s** — no L1/L2
retention means no prefetch MLP). Sound and cheap to build; expensive to
run.

**(b) Epoch-tagged retention, bulk-cleared at exit.** Lines are retained
(so the streamer keeps its MLP) but tagged with the epoch that produced
them; `EndEpoch` performs one atomic sweep invalidating every
unenrolled/tagged copy before reopening the line for writes. Sound (TLC:
no violation) because the exit is a single indivisible step — no window
exists where the line is writable and a stale copy still lives. Costs a
broadcast (or an HN-driven sweep) at every epoch boundary, which is exactly
the drain-cost measurement task #30 wants (`[STREAMER COST]`, not
embargoed).

**(c) DeNovo-style self-invalidation.** Same retention as (b), but no
central broadcast: `EndEpoch` only *opens* the drain (`epoch := "Draining"`)
and each holder of an unenrolled copy independently self-invalidates
(`SelfInvalidate`) at the epoch boundary it observes; the line only becomes
writable once every holder has done so (`FinishDrain`). Sound for the same
reason as (b) — the model still enforces zero window between "some
unenrolled copy survives" and "the line accepts writes," it just
distributes who does the clearing. This is the shape a software/hardware
co-designed scheme (compiler-inserted self-invalidation at a known epoch
boundary) would take, trading a broadcast for a synchronization barrier.

**(d) Retain-but-unenrolled — UNSOUND, and now TLC-confirmed, not just
internally rated.** Retention like (b)/(c), but `EndEpoch` reopens the line
immediately with no reconciliation step at all. This is the "tolerate" fix
recorded as rejected in `streaming-gem5-results` memory (2026-07-30): keep
the bandwidth benefit of retention without paying for either a broadcast or
a self-invalidation barrier. **A taxonomy that only lists the sound options
reads as marketing — this is why (d) is here, with its counterexample,
not just a sentence saying it's bad.**

## What this does and doesn't buy the paper

It buys an actual formal-methods answer to "how do you know H3 doesn't
race," independent of and stronger than any simulated number the δ embargo
currently restricts (§3 of `PAPER_SESSION_PROMPT.md` — this task is
explicitly *not* embargoed; it's the argument side of H3, not an attributed
measurement). It does **not** model liveness/deadlock — that risk register
already lives in `H3_IMPL_SPEC.md` §(b) and stays there; conflating the two
would overclaim what five small TLC runs on a 2×2 abstraction can support.
It does not model variant (b)'s or (c)'s actual hardware cost — that's
task #30's job, on real silicon or gem5, not a model checker's.

## Reproduction

```
cd experiments/asplos/model_check
java -cp ~/tools/tla/tla2tools.jar tlc2.TLC -config variantA.cfg H3Coherence.tla
java -cp ~/tools/tla/tla2tools.jar tlc2.TLC -config variantB.cfg H3Coherence.tla
java -cp ~/tools/tla/tla2tools.jar tlc2.TLC -config variantC.cfg H3Coherence.tla
java -cp ~/tools/tla/tla2tools.jar tlc2.TLC -config variantD_unsound.cfg H3Coherence.tla   # expect Inv2 violation
java -cp ~/tools/tla/tla2tools.jar tlc2.TLC -config h3off_baseline.cfg H3Coherence.tla
```
`tla2tools.jar` is not vendored in this repo (2.2 MB, third-party) — fetch
from `github.com/tlaplus/tlaplus/releases/latest/download/tla2tools.jar`.

**False start, recorded so it isn't repeated:** the first run (no
`StateConstraint`) hung — `version` is incremented without bound by `Write`
and nothing else in the model bounds it, so TLC's state space is genuinely
infinite. `StateConstraint` (`version[l] <= 2`) fixes this; 2 is already
enough depth to exercise every action at least once per line and is not
load-bearing for any property (the D counterexample above is found at
`version[l1] = 1`, i.e. before any write has even happened).
