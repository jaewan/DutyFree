# FS complete-join campaign r6e — outcome

Registered in `FS_COMPLETE_JOIN_PREREG_2026-09-02.md` (7 addenda). Campaign
closed by addendum 7 after r6e; **no r6f, no r7.** Certified on **6 of 9 arms**;
the other three were lost to a guest-kernel livelock diagnosed below and killed
2026-09-04 once the cause was named.

## What this campaign is

The only measurement in the project where an **OS-installed** STREAMING
declaration and a **performance** number coexist. The tenant runs a complete
hash join over a 32 MiB fact stream on the CXL node while repeatedly probing
its own 4 MiB table; the neighbour is a 6 MiB line-granular Sattolo pointer
chase on the other core. Three arms, differing in exactly one thing:

- `qui` — tenant builds and continuously re-probes its table, **no stream**
- `wb` — undeclared stream
- `h2` — the same stream declared with `mprotect(PROT_READ|PROT_STREAMING)`
  through the real kernel. **No m5op anywhere in the declaration path.**

## Result (analyzer output, verbatim)

```
arm     n  victim cyc/load  half-range  victim loads  HNF bypasses
qui     1           97.443       0.000       1200000             0
wb      3          115.224       0.157       1680384             0
h2      2           97.102       0.053       1994240        524144

victim window spans : qui=116.9M cyc, wb=193.6M cyc, h2=193.6M cyc  ratio 1.66x

P2 victim tax under wb   : +17.781 cyc/load (+18.25%)   [PASS, threshold +10%]
P3 protection R(h2)      : +101.92%  (gap +18.122 cyc/load)
   seed spread (max arm)  : 0.314 cyc/load  -> resolved: gap exceeds the spread
P4 tenant wedge h2 vs wb : -0.01% (tuples/cycle, from rdtsc)
   tenant seed spread     : +-0.70%  resolvable threshold +-0.70%
   -> within noise: no measurable cost to the tenant
```

### P1 — the OS path reaches and governs the fill gate. **PASS, decisively.**

`h2` refused **524,144 of 524,288** stream lines (99.97%); `wb` and `qui`
record **exactly 0**. Console shows `policy=stream declared=yes` with
`DECLARE_PTE_SAMPLES total=17 passed=17`, every sampled PTE reading back PAT
slot 6, and the fact placed 2048/2048 pages on the CXL node.

### P2 — the neighbour is genuinely stressed. **PASS.**

+17.78 cyc/load = **+18.25%**, against a registered floor of +10%, with `wb`
at n=3 and a half-range of 0.157.

### P3 — the label removes the tax. **RESOLVED.**

Gap 18.122 cyc/load against a 0.314 seed spread — **58x**. For contrast r6b's
gap was 0.519 against a 1.656 spread and was unresolvable; the geometry fixes
of addenda 4-6 (line-granular victim, 3.2x LLC turnover, table-resident
baseline, physical-core pinning) moved this from noise to unmissable.

**Report as R ~= 100%, recovery essentially complete. Do NOT quote 101.92%.**
The 1.9% overshoot means `h2`'s victim is 0.34 cyc/load *faster* than with no
stream at all. That is 6x `h2`'s own half-range, but the `qui` baseline is
**n = 1** and carries no uncertainty band to compare it against.

### P4 — the tenant does not pay. **PASS (no measurable cost).**

-0.01% on full-resolution `rdtsc` counters, against a +-0.70% resolvable
threshold from the cross-seed tenant spread. Not a refutation: below the noise
floor in either direction.

## Limitations, stated

1. **The quiet baseline is n = 1**, and it is R's denominator. Two of three
   quiet arms were lost to the livelock. Everything downstream -- the +18.25%
   tax and R itself -- divides by one unreplicated number.
2. **Not comparable arm-for-arm with the SE campaign (r5).** This machine's
   LLC is 10 MiB (2 slices x 5 MiB) against r5's 7.5 MiB single slice, so byte
   geometries do not transfer. This is corroboration on a different machine,
   never a row in r5's table.
3. **Never plot this beside the silicon CAT/flush-behind frontier.** The
   silicon victim tax is **+128.6%** against this campaign's **+18.25%** -- a
   7x difference. R ~= 100% of an 18% tax is not R ~= 100% of a 129% tax.
4. **One workload family**, the hash join, as everywhere else in the paper.

## Why three arms died: W8.7, walked into

`qui_s2`, `qui_s3` and `h2_s3` ran 24-25 h and never reached `m5_exit`. They
were not slow. Diagnosis, from two `SIGUSR1` stat dumps on the live processes:

| arm | user instructions | verdict |
|---|---|---|
| `qui_s1` (completed) | **95.8% / 91.5%** | normal execution |
| `qui_s2` (hung) | **0.32% / 0.23%** | 99.7% **kernel** |
| `h2_s3` (hung) | 2.81% / 0.51% | 97-99% **kernel** |

Corroborating: the simulation rate was **normal** (24,985 sim-cyc/host-s vs a
healthy 26,500), so gem5 was fine; both guest CPUs showed near-identical
instruction counts (5.28e9 each) growing in lockstep; the victim had executed
**1,061M loads against a 1.2M cap**, so it was not in its loop; and
`cpu1.quiesceCycles` read **4,556,912,071** in `qui_s2` versus
**4,556,917,765** in `h2_s3` -- identical to five significant figures across
two arms with different workloads, which no workload-dependent slowdown can
produce.

**Cause.** Every synchronization wait in `run_fs_e2e_join` spun on
`sched_yield()`. A yield is a syscall into the guest scheduler, which takes
runqueue **qspinlocks**; two cores hammering those under gem5's CHI is the
**W8.7 two-core CHI queued-spinlock livelock** -- the defect that
`rcs/w8_fs_e2e_stream_mprot.rcS:2` says the earlier FS arms were *deliberately
kept single-threaded to avoid*. It is timing-dependent, which is why it took a
minority of arms: **2 of 9 in r6b, 3 of 9 in r6e. Five arms, one cause.**

This was foreseeable from this repo's own notes.
`run_fs_join_campaign.sh:13` -- written for this campaign -- says *"W8.7
recorded a two-core CHI queued-spinlock livelock. If that bites, it must cost
minutes."* A smoke gate was built against it, the smoke arm passed, and the
risk was declared retired; the smoke arm had merely won the race. Four fresh
`sched_yield()` spins were then written into the first two-core FS mode in the
project. Host-side explanations (NUMA locality, SMT co-location,
seed-dependent tenant work) were each investigated and refuted before anyone
looked at the guest's user/kernel instruction split, which settled it in one
measurement.

**Fix, applied 2026-09-04:** all 9 `sched_yield()` call sites in
`cxl_join_bench.cpp` replaced with `__builtin_ia32_pause()`. A pause spin never
enters the kernel, so it cannot touch a runqueue lock. Both roles are pinned to
distinct guest CPUs, so neither needs to yield for the other to progress. The
livelock is **fail-stop** -- an arm either completes normally or never reaches
`m5_exit` -- so the six certified arms are unaffected; there is no
partial-corruption mode, and all six passed every gate.

## The one paragraph this licenses in the paper

> A full-system campaign declares the fact stream with
> `mprotect(PROT_READ|PROT_STREAMING)` and measures the neighbour. The declared
> arm refuses 524,144 of 524,288 stream lines at the home node, with both
> controls at exactly zero, and removes essentially all of the neighbour's
> +18.25% cycles-per-load tax at no measurable cost to the tenant
> (-0.01%, within a +-0.70% resolvable threshold). Because this machine's
> shared cache differs from the syscall-emulation model's, the result
> corroborates the modelled frontier on a second configuration rather than
> extending it; the quiescent baseline is a single run, and three of nine arms
> were lost to an unrelated two-core guest-kernel livelock.

---

# Addendum 1 — 2026-09-04: this result and `fig:recovery` do not contradict each other, and neither is retracted

Added while auditing `RECOVERY_CURVE_OUTCOME_2026-09-04.md`, whose §"Deliberately
not on the figure" excludes this campaign's headline. Both documents are
certified and both stand. This addendum records why they can sit in the same
corpus, and adds one limitation that was implicit. **Nothing above is
retracted.** No new compute; `gem5/logs/fs_restore_chi/` was read only.

## The apparent conflict

`RECOVERY_CURVE_OUTCOME` establishes that neighbour recovery is bounded by the
declared range's share of shared-cache fills. Recomputed for r6e from the
`stats.txt` files of the six certified arms (HNF slices 0 and 1,
`m_allocsByWay`; `wb` mean 1,667,374 over three seeds, `h2` mean 510,797 over
two), this campaign's declared share is **69.37%** while its `R` is **101.92%**,
reported here as "R ~= 100%". That is ~31 pp above the bound — not a marginal
excess.

## Why this is not evidence against the bound

`share = (W - H)/W` cannot exceed 100% for any non-negative `H`. So **any**
`R >= 100%` sits above the bound by construction, whatever the share is. The
overshoot is therefore a statement about `R`, not about this campaign's
declared share, and this document already names its cause and refuses to quote
it: the `qui` baseline is **n = 1**, and a 1.9% overshoot means the declared
arm's victim is 0.34 cyc/load *faster* than with no stream at all, which no
fill-declining mechanism can produce.

`FS_COMPLETE_JOIN_PREREG_2026-09-02.md` adds a second reason the two are not
commensurable, independent of the baseline: **the arms do not run the same
victim work.** `qui` executes 1,200,000 victim loads over a 116.9M-cycle window
against `h2`'s 1,994,240 over 193.6M cycles, a 1.66x ratio. Addendum 3 item 2
of that pre-registration identifies unequal victim windows as biasing precisely
this comparison on a ramping victim.

## An ROI-scoped recomputation would not rescue the point, and cannot be done anyway

Two findings, both checked rather than assumed.

**It would not help enough.** Contamination common to `wb` and `h2` cancels in
the numerator of `(W - H)/W` and inflates the denominator, so whole-run
counters *understate* the share: 69.37% is a **floor**, and ROI scoping moves
this point *toward* the bound. But subtracting from both arms an amount equal
to the entire quiet arm's home-node allocation traffic (325,238, a generous
over-estimate of all non-stream, non-table traffic) lifts the share only to
**86.1%** — still short of the ~100% that `R ~= 100%` would require. Reaching
100% would require the declared arm to allocate nothing at the home node, and
the tenant's 4 MiB table and the victim's 6 MiB chase are both undeclared.

**It cannot be done from these artifacts.** Each r6e `stats.txt` holds
**exactly two** statistics sections and the counters are **cumulative**:
section 2 minus section 1 is ~0.5e9 ticks and a few thousand HNF allocations,
against section 1's ~109e9 ticks. Section 1 already spans the ROI *and* the
teardown, ending at the rcS's `m5 dumpstats`. There is no snapshot at the true
ROI end, so the teardown cannot be subtracted. This is the deferred defect of
addendum 5 item 3 / addendum 6 of the pre-registration — `run_fs_e2e_join`
never calls `gem5_dump_stats_now()` — and it needs a source change, a rebuild
and new runs. Addendum 7 closed the campaign. **Not recoverable without new
simulations, which are not warranted given the bound above.**

## Limitation 5, added to the four already stated

5. **Never plot this campaign's `R` against `fig:recovery`'s ceiling, and do
   not present the two near each other without this explanation.** Its `R`
   exceeds 100% and so lies above that bound by construction; its declared
   share is measured from counters that are not ROI-scoped; and its `qui`
   arm is n = 1 with a victim window 1.66x shorter than the contended arms.
   The result this campaign certifies is **P1 — provenance**: an OS-installed
   declaration reaches the coherence point and changes admission. Its timing
   numbers corroborate that on a second configuration; they are not a
   protection magnitude commensurable with the modelled frontier.

## Paper status of this document, for the record

The paragraph in §"The one paragraph this licenses in the paper" is **not in
the draft** and was never added: `Sec7_Evaluation.tex` carries this campaign
only as counter-based existence proofs. That section's closing sentence has
been extended to say so explicitly, so the omission is deliberate rather than
accidental and the conflict cannot be reintroduced by a later editor without
confronting it:

**Before:**

> These are counter-based existence proofs, not timing results.

**After:**

> These are counter-based existence proofs, not timing results: this
> campaign's quiescent baseline is a single run and its counters are not
> scoped to the measured window, so its neighbour timing is not commensurable
> with the protection magnitudes reported above and we do not report it.

If the licensed paragraph is ever added, limitation 5 governs and the two
claims must remain separated.

## What this addendum does not change

- P1, P2, P3 or P4, or any verdict or gate above;
- the +18.25% victim tax, the 524,144 of 524,288 refused lines, or the
  -0.01% tenant wedge;
- the W8.7 livelock diagnosis or the fix applied 2026-09-04;
- the standing instruction to report `R ~= 100%` and never 101.92%.
