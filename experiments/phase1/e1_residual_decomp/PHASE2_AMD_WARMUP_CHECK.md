# AMD matched-warmup check: the WC quadrilateration anchor holds up

Dated 2026-08-08. Direct response to the panel's warning that "AMD's
retained quiescent data showed no bimodality on inspection" is invalid by
the same failure mode that hid Intel's ~10% artifact: per-arm distributions
can be tight and unimodal while still uniformly biased. This runs the
actual matched-warmup test AMD never got, rather than relying on
inspection.

## Background: AMD's victim already has a built-in warmup, unlike Intel's

`victim.c` (the AMD-side binary) takes a first-class `-W <warmup_sec>` flag
and runs an internal, unreported warmup phase before the measured window
begins — a real warmup mechanism, unlike Intel's `pointer_chase_nocap`
which had none. The campaign's existing AMD scripts (`run_e1_gate.py`,
`run_p24_amd_flushbehind.py`) already pass `-W 2` uniformly to every arm.
The open question was whether 2s is *enough*, given Intel's own finding
that ~2s of self-generated dose alone was insufficient (only partially
warm) and it took a full ~4-8s cumulative window to saturate.

## v1: a false alarm caused by a new confound, not by warmup duration

The first attempt (`run_amd_matched_warmup.py`) tried to save wall-clock
time by sharing one aggressor launch across two back-to-back victim calls
per arm (`W=2` then `W=10`). This surfaced an enormous, highly reproducible
anomaly: **WC's `W=2` call read ~12-15M cyc/iter — a ~3.3-4x tax — against
quiescent's ~3.6M, while `W=10` read ~3.6M (parity), across two independent
full runs.** Read naively, this would have overturned the WC=0.989x
quadrilateration anchor entirely.

It was investigated rather than trusted. In order:

1. An exact single-victim-call replica of `run_e1_gate.py`'s protocol
   (fresh aggressor launch per measurement, `AGG_DUR=16`) reproduced the
   *original* clean result (~3.6-3.7M) regardless of `W=2` or whether
   preceded by a `wb_cat` arm — ruling out warmup duration and
   single-arm carryover as the cause.
2. Raising the isolated test's `AGG_DUR` from 16 to 40 (matching v1's
   longer aggressor lifetime) alone did not reproduce the anomaly.
3. Two back-to-back `W=2` calls sharing one aggressor (isolating *call
   order* from *warmup value*) did not reproduce it either — both calls
   read clean.
4. Replicating the *full* `quiescent → wb → wb_cat → wc` sequence with
   every arm double-called (matching v1's exact structure) **did**
   reproduce it (WC `W=2` ~14.5-14.7M, `W=10` ~3.6M) — confirming the
   effect requires the accumulated depth of multiple preceding
   heavily-loaded double-called arms, not any single variable tested
   alone.
5. The original retained `e1gate_raw_n12.jsonl`'s `A3_wc` values, read in
   rep order (not sorted), show **no monotonic drift across 12 reps**
   (~10 minutes of wall-clock time): 3659563, 3658998, 3595471, 3676236,
   3586711, 3657911, 3647858, 3631127, 3610396, 3572206, 3571752, 3585517
   — a tight, non-drifting band. This rules out the original 12-rep
   protocol having quietly accumulated the same effect.

**Conclusion: v1's shared-aggressor-across-two-calls design tripled each
arm's aggressor lifetime relative to the original protocol, and that
extended lifetime — not warmup duration — is what produced the anomaly.**
This is a real methodology finding worth keeping in mind (sustained
multi-thread aggressor load, sustained for tens of seconds longer than the
original protocol ever holds it, measurably changes WC's interaction with
a short-warmup victim) but it does not implicate the original campaign
data, which never runs aggressors that long per arm.

## v2: corrected design — two full separate passes, original lifecycle preserved

`run_amd_matched_warmup_v2.py`: every arm gets its own fresh aggressor
launch per single victim call (`AGG_DUR` scaled tightly to
settle+warmup+measure+margin, never shared across two calls) — structurally
identical to `run_e1_gate.py` / `run_p24_amd_flushbehind.py`. Two full,
separate n=12 sweeps: one at `W=2` (an in-session control, replicating the
original protocol) and one at `W=10` (clearly past Intel's observed
dose-saturation point). Arms: quiescent, wb, wb_cat, wc,
`flush_d256kb` (Phase 2.4's best-case/lowest-tax D point).

| arm | W=2 tax | W=2 95% CI | W=10 tax | W=10 95% CI |
|---|---:|---:|---:|---:|
| wb | 20.438 | [20.348, 20.756] | 20.267 | [20.101, 20.513] |
| wb_cat | 9.917 | [9.846, 10.065] | 9.768 | [9.673, 9.902] |
| **wc** | **1.001** | **[0.985, 1.028]** | **0.983** | **[0.974, 1.009]** |
| flush_d256kb | 5.899 | [5.869, 5.991] | 5.857 | [5.815, 5.928] |

**Every arm's W=2 and W=10 confidence intervals overlap heavily.** Warmup
duration makes no material difference to any AMD tax number under the
corrected, original-lifecycle-preserving design.

## Verdict

**The WC quadrilateration anchor holds up under direct testing.** Both
warmup durations put it at parity (1.001x, 0.983x — both statistically
indistinguishable from 1.0, and from each other). AMD's victim binary's
built-in 2s warmup, despite being shorter than what Intel's ad-hoc
protocol needed, is evidently sufficient for AMD's hardware — AMD does not
reproduce Intel's dose-response sensitivity. This is a real, positive
answer to the panel's challenge, not a repeat of the "no bimodality on
inspection" failure mode: the check that was actually missing has now been
run, at n=12, with a proper control replica in the same session, and it
clears.

`flush_d256kb` sits at 5.86-5.90x, comfortably matching the previously
reported 5.94x — the convergent-floor claim holds there. **`wb_cat`
(CAT) does NOT comfortably match its previous number** — see below, this
is now a confirmed, real, and as-yet-unexplained drift, not a warmup
artifact.

## Secondary finding, unrelated to warmup: `wb_cat` session drift, investigated

The W=2 control-replica's `wb_cat` tax (9.92x) is notably higher than the
original gate's `A2_wb_cat` (7.23x) — a ~37% relative difference. This was
followed up rather than just flagged.

**Confirmed real, not a v2/warmup artifact.** Re-ran the *literal,
unmodified* `run_e1_gate.py` (byte-identical to the committed file, diffed
to confirm), fresh, n=6, right now. It crashed on a `perf stat` failure
(see below) before completing, but the victim/aggressor measurements
before the crash are fully valid — patched a copy
(`run_e1_gate_noperf.py`, only change: catch the now-missing perf output
file instead of crashing) and reran clean:

| arm | now (n=6) | original (n=12) | relative drift |
|---|---:|---:|---:|
| A1_wb | 20.545 | 19.886 | +3.3% |
| A2_wb_cat | **9.867** | **7.225** | **+36.6%** |
| A3_wc | 1.006 | 0.989 | +1.7% |

**The drift is specific to the CAT-partitioned arm.** `wb` and `wc` sit
well within normal session-to-session noise (1.7-3.3%); only `wb_cat`
shows a large, real shift. This rules out general thermal/hardware drift
(which would move all three) and points at something specific to CAT
enforcement.

**Investigated directly, several mechanisms ruled out:**
- **Not a schemata-write failure.** `last_cmd_status` reads `ok` both
  before and during a live run; schemata reads back exactly as written
  (`ff00`/`00ff`) and stays stable throughout.
- **Not a domain-mapping shift.** The box has 32 L3 domains (one per CCX;
  16 CCX × 2 sockets), and both scripts only ever write `L3:0=...`
  (domain 0). Verified directly: ran the victim alone in a fresh
  monitoring-only group and checked `llc_occupancy` across all 32
  `mon_L3_NN` domains — only `mon_L3_00` showed nonzero occupancy,
  confirming domain 0 is still correctly mapped to CCX0 (cores 0-7,
  matching `cpu0`'s `shared_cpu_list`). The partition is being applied to
  the right physical cache slice.
- **Not resctrl capability drift.** `cbm_mask=ffff`, `num_closids=16`,
  group `mode=shareable` all read as expected, matching a normal 16-way
  CAT-capable configuration.
- **Not a hardware CAT enforcement failure — verified at the MSR level,
  bypassing resctrl's sysfs abstraction entirely.** `check_cat_msr.py`
  reads `IA32_PQR_ASSOC` (0xC8F) directly via `/dev/cpu/N/msr` for cpu0
  and cpu1 during a live run, then reads the actual programmed
  `IA32_L3_QOS_MASK_n` (0xC90+n) for whatever CLOSID each core is
  assigned. Result: **cpu0 → CLOSID 1 → mask 0xff00 (top 8 ways); cpu1/2/7
  → CLOSID 2 → mask 0x00ff (bottom 8 ways)** — an exact, disjoint,
  correctly-programmed 8-way split, matching the intended schemata
  precisely. The hardware is doing exactly what it was told. Whatever is
  causing the increased interference, it is not a CAT configuration or
  enforcement bug at any level checked (sysfs schemata, domain mapping,
  or now the raw QoS mask MSRs themselves).

## Bounded follow-up investigation (2026-08-08, panel-directed, timeboxed)

Five items were pursued, cheapest first, per explicit direction. The
result reframes the whole question.

**(i) Aggressor bandwidth and within-session CI, both epochs, from data
already on disk.** Aggressor self-report and MBM-verified bandwidth are
essentially identical and extremely tight in *both* epochs (~24 GB/s,
<1% spread) — the aggressor's own output never changed. The victim tax
itself: original epoch (n=12) ranges 6.59–8.22x internally (22.6% spread,
wider than one might assume for a "clean" session); rerun epoch (n=6)
ranges 9.20–9.91x (7.25% spread, tighter). **The two epochs'
ranges do not overlap at all.** This is a genuine step change between
sessions, not two draws from one noisy distribution.

**(ii) Kernel/microcode diff across epochs.** Kernel unchanged
(`7.0.0-28-generic` since 2026-07-18, weeks before either epoch). No
`amd64-microcode` package update in `dpkg.log` at any point. The full apt
transaction at 06:32:46 touched exactly two packages: `linux-libc-dev`
(kernel UAPI headers, compile-time only, cannot affect already-compiled
binaries) and `linux-tools-common` (perf tooling). **Neither has a
plausible mechanism for changing real hardware CAT-partition enforcement
behavior.** This specific, confirmed package churn is ruled out as a
mechanistic cause — the timing correlation noted below is exactly that:
correlation, not a lead worth pursuing further.

**(iii) Co-tenancy records, both epochs.** `last -F` shows **zero**
other logins during the original epoch (nearest prior/following session
boundary: `domin` alone, ending Aug 4; next login `seungjun` starting Aug
7 09:12, continuously present through the rerun and every AMD
measurement in this document). The rerun epoch was measured under
confirmed multi-tenancy; the original was not. Process-level inspection
during the rerun showed the other user's own load as negligible (desktop
session, <1% CPU, no affinity to cores 0-7) — this doesn't prove a causal
link, but it's a real, documented, confirmed environmental difference
between epochs that the original single-tenant measurement never had.

**(iv) Direct gain/sensitivity characterization — superseded by a bigger
finding.** The plan was a thread-count or bandwidth sweep around the
wb_cat operating point. Instead, testing whether the effect was
CCX0-specific (a cheaper, more diagnostic first move) produced a result
that makes the planned sweep secondary:

### The dominant finding: CCX0 is a stark, quadruple-replicated outlier — in both directions

`check_ccx_comparison.py`: quiescent / WB (no CAT) / WB+CAT, matched
script, matched session, n=6 per CCX, run back-to-back on CCX0-3:

| CCX | quiescent | wb_tax | wb_cat_tax | cat_benefit (wb_tax / wb_cat_tax) |
|---|---:|---:|---:|---:|
| **0** | 3,631,121 | **20.457** | **9.848** | **2.077x** |
| 1 | 3,673,052 | 13.220 | 13.411 | 0.986x |
| 2 | 3,603,033 | 13.483 | 13.498 | 0.999x |
| 3 | 3,643,197 | 13.465 | 13.239 | 1.017x |

**CCX0 is not just where wb_cat drifted — it is categorically different
from every other CCX tested, in both the endpoint and the mechanism.**
Its uncontended WB tax (20.5x) is ~52% higher than CCX1-3's tight cluster
(~13.2-13.5x, all mutually consistent). And CAT partitioning provides a
real, roughly 2x benefit **only on CCX0**; on CCX1, CCX2, and CCX3, CAT's
benefit is statistically zero (0.986x, 0.999x, 1.017x — all within noise
of 1.0). Quiescent baselines are identical across all four CCXes
(3.60-3.67M, no meaningful difference) — this is specifically an
*interference-under-contention* property, not a baseline-speed property.

**This changes the shape of the question.** It is not "wb_cat's residual
drifted at a high-gain operating point while stable endpoints held
still" — the WB endpoint itself is not CCX-independent (20.5x vs ~13.4x
is a large difference at the *uncontended* comparison point, the thing
that was assumed stable). The campaign's AMD numbers have, from the
start, been measured exclusively on CCX0 (`cpus 0-7`, matching every
prior script's hardcoded core list). **If CCX0 is atypical of the chip
as a whole, "CAT recovers most of WB's tax" may describe CCX0
specifically, not AMD's cache-partitioning mechanism in general** — on
3 of the 4 CCXes tested, CAT provided no measurable recovery at all.

One candidate, consistent with but not proven to cause this: cpu0 carries
substantially more IRQ load than other cores (10.5M vs 4.4M cumulative
interrupts against cpu8, confirmed via `/proc/interrupts`) — a
well-known reason core/CCX0 behaves differently from the rest of a chip
in careful benchmarking. This is plausible but unconfirmed; it does not
explain the *direction* of the effect (why would extra IRQ load make CAT
*more* effective specifically) without further, more speculative
reasoning than the evidence currently supports.

**(v) Observer-effect check**: obtained for free by the CCX comparison
itself — running the identical script on 4 different CCXes with no
special instrumentation reproduces the same qualitative pattern each
time (tight clusters on CCX1-3, outlier on CCX0), so the measurement
apparatus itself is not the source of the CCX0 divergence.

**One timing-consistent but mechanistically-ruled-out-by-(ii) candidate**:
`dpkg.log` shows `linux-tools-common` upgraded (6.8.0-136.136 →
6.8.0-137.137) at **2026-08-06 06:32:46** — about 4 hours *after* the
original gate data was collected (committed at 2026-08-06 02:31-02:40,
same day). This same package area plausibly explains a fully separate
observation made along the way: `perf list` no longer recognizes the
`l3_lookup_state.*` / `l3_xi_sampled_latency.*` AMD uncore PMU event
aliases that `run_e1_gate.py` depends on for its supplementary L3 counters
(confirmed missing; the gate script now crashes on this unless patched —
**fixed**, see "Perf alias loss" section below). As established in (ii)
above, this package has no plausible mechanism for changing hardware CAT
enforcement — recorded for completeness, not as a live lead.

**Bottom line, updated: this is no longer just "an unexplained CAT
drift."** Every configuration/enforcement mechanism checked at the
CCX0-only level — including the raw hardware QoS mask MSRs — comes back
correct, so it is not a resctrl, schemata, domain-mapping, or
CAT-programming problem at any layer from sysfs down to the MSRs. But
the CCX comparison shows the drift sits inside a much larger, structural
fact: **CCX0 behaves differently from the rest of this chip, in both its
baseline contention level and CAT's effectiveness against it.** Whether
CCX0's *own* time-varying behavior (the 7.23→9.87x drift) and CCX0's
*cross-sectional* divergence from CCX1-3 (20.5x/9.85x vs ~13.4x/~13.4x)
share one root cause, or are two separate CCX0-specific phenomena, is not
resolved — but the practical consequence is the same either way: **a
single-CCX measurement convention is not safe to generalize to "AMD's
CAT mechanism" without saying which CCX, and CCX0 (the one used
throughout this campaign) is the least representative of the four
tested.** Diagnostic scripts kept: `check_cat_live.py`, `check_cat_msr.py`,
`check_ccx_comparison.py`, `check_wb_ccx1.py`.

**Decision (2026-08-08, explicit user call, not inferred)**: standardize
on **9.87x** — the current, reproducible measurement — for paper tables
and as gem5's CAT validation target going forward, **as CCX0's number
specifically**. Given the CCX comparison, this should now be labeled as
such in any table it appears in, not presented as "the" AMD CAT tax.
7.23x is now
provenance-superseded, same convention as the earlier EMR device-swap
issue: not deleted, but no longer the number in active use. Phase 2.5
(gem5) remains on hold specifically because "resolved" was read as
*root-caused*, not merely *numerically decided* — picking 9.87x unblocks
which number gem5 targets, but the campaign has not explained *why* the
number changed, and that explanation was the actual gate for proceeding.

## Provenance

Scripts: `run_amd_matched_warmup.py` (v1, superseded — kept for the
methodology note above, not for its numbers), `run_amd_matched_warmup_v2.py`
(the valid design), `run_wc_isolation_check.py` and the ad-hoc depth-check
script (isolation diagnostics, not committed as they were throwaway
verification, results captured above). Data: `amd_v2_W2_n12.jsonl`,
`amd_v2_W10_n12.jsonl`. Host: broker (AMD EPYC 9754), re-frozen to
`performance` governor / boost off before this check (found drifted to
`schedutil`/boost-on since the last documented freeze — the same drift
pattern noted after the earlier mid-run reboot incident; worth adding a
freeze-state check to the top of every AMD session, not just after
reboots).

## Perf alias loss: fixed, raw encodings now in use

`perf list` no longer recognizes `l3_lookup_state.*` /
`l3_xi_sampled_latency*.*` — confirmed missing entirely, not renamed.
This is load-bearing: `run_e1_a4a5.py` (the A4/A5 lookup-vs-occupancy
decomposition) and `run_p22_thread_matched.py` (the 2T/3T concurrency-cap
sweep, computing `xi_cycles_per_request`) depend on these events, not
just `run_e1_gate.py`'s supplementary counters.

Fixed by going to raw PMU encodings instead of alias names, sourced
directly from AMD's own `pmu-events` JSON (found on disk at
`CoherenceTest/APSys/sources/linux-ubuntu-6.8.0-111/tools/perf/pmu-events/arch/x86/amdzen4/cache.json`
— the exact family for this box), verified end-to-end against real load
(`hit + miss == all_coherent` exactly: 2,098,968 + 42 = 2,099,010):

| alias (now gone) | EventCode | UMask | raw encoding |
|---|---|---|---|
| `l3_lookup_state.l3_hit` | 0x04 | 0xfe | `rfe04` |
| `l3_lookup_state.l3_miss` | 0x04 | 0x01 | `r0104` |
| `l3_lookup_state.all_coherent_accesses_to_l3` | 0x04 | 0xff | `rff04` |
| `l3_xi_sampled_latency.near_cache` | 0xac | 0x04 | `r04ac` |
| `l3_xi_sampled_latency.dram_near` | 0xac | 0x01 | `r01ac` |
| `l3_xi_sampled_latency.ext_near` | 0xac | 0x10 | `r10ac` |
| `l3_xi_sampled_latency_requests.dram_near` | 0xad | 0x01 | `r01ad` |
| `l3_xi_sampled_latency_requests.ext_near` | 0xad | 0x10 | `r10ad` |

Patched `run_e1_gate.py`, `run_e1_a4a5.py`, `run_p22_thread_matched.py`
to use these directly — no dependency on whatever alias set happens to
be installed at run time. `run_p22_thread_matched.py` also had real
downstream key-based lookups (`perf_data.get(f"l3_xi_sampled_latency.{src}")`)
that would have silently returned `None` after switching the event
string without also fixing the lookup — found and fixed, not just the
`PERF_EVENTS` constant.

**Preflight/hygiene, done**: `env_manifest.py` added at the phase1 root —
snapshots kernel, microcode, tool versions + hold status, governor,
boost/turbo (both conventions, unambiguous), THP mode, resctrl
capabilities, and a live capability probe for the `l3_lookup_state` alias
specifically (so its disappearance is a loud warning at session start,
not a crash four hours into a run). `linux-tools-common`, `linux-libc-dev`,
the running kernel image, and `amd64-microcode`/`intel-microcode` are now
`apt-mark hold`'d on both hosts (broker and mos181) to stop further
mid-campaign package churn.

## What still needs doing

- **[REFRAMED — CCX0 is the finding, not just the drift]** The wb_cat
  session drift (7.23x → 9.87x) sits inside a much larger fact: CCX0
  diverges from CCX1/2/3 in both uncontended WB tax (20.5x vs ~13.4x)
  and CAT's benefit (2.08x reduction vs ~1.0x/no benefit). **This needs
  to reach the paper's AMD section, not stay a methodology footnote** —
  it bears directly on whether "CAT recovers most of WB's tax" is a
  general claim or a CCX0-specific one.
- **9.87x remains the standard number, but must now be labeled "CCX0"
  explicitly** wherever it's quoted, not presented as *the* AMD CAT tax.
  Whether the paper should report a CCX0 number, a cross-CCX range/mean,
  or a different CCX entirely is a decision item, not something to
  resolve unilaterally here.
- **The CCX0-vs-rest mechanism is not identified.** The IRQ-load
  difference (10.5M vs 4.4M cumulative interrupts, cpu0 vs cpu8) is a
  plausible contributing factor but doesn't explain the *direction* of
  the effect (why extra IRQ load would make CAT specifically more
  effective) without more speculation than the evidence supports. Package
  churn (linux-libc-dev, linux-tools-common) and microcode are both ruled
  out mechanistically (item ii above). Kernel/AMD errata research or
  vendor engagement would be the next step if pursued further.
- **gem5 (Phase 2.5) stays on hold**, per explicit instruction, pending
  this mechanism — now understood to be broader (CCX0 divergence) than
  originally framed (a single-number drift), which if anything raises
  rather than lowers the bar for what "resolved" should mean here.
- Add a governor/boost/hugepade/THP freeze-state check to the start of
  every AMD session — now implemented as `env_manifest.py`, should be run
  and diffed against the previous session at the start of every future
  measurement session on either host.
- **New, not previously scoped**: decide whether to re-measure other
  campaign AMD numbers (WB, WC, flush-behind, A4/A5/A6) across multiple
  CCXes too, given CCX0's demonstrated non-representativeness. WC/WB's
  own CCX0-vs-CCX1 comparison is already done here (WB) and via the v2
  warmup check (WC, though not cross-CCX) — flush-behind and the
  lookup-only/concurrency-cap arms have not been cross-CCX tested at all.
