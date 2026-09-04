# Pre-registration: the wedge on a real hash join (not `fused.c`)

Date: 2026-09-01.  Registered before any arm's outcome was inspected.

## Why

The fused wedge (`H2H_FUSED_PREREG_2026-08-29.md`, archived in
`data/gem5/fh_runs.jsonl`) established that at matched protection (~90%) H2
costs the tenant nothing while way partitioning costs it 13.7-36.5%:

| arm | victim cyc/acc | protection | tenant IPC | vs wb |
| --- | --- | --- | --- | --- |
| qui | 33.881 | -- | -- | -- |
| wb | 52.756 | -- | 0.3503 | -- |
| cat4 | 35.869 | 89.47% | 0.2223 | -36.53% |
| cat10 | 35.573 | 91.04% | 0.3025 | -13.65% |
| h2 | 35.653 | 90.61% | 0.3543 | +1.16% |

Wedge (h2 vs best CAT) = **+17.1%**.

The objection this cannot answer: `fused.c` is a microbenchmark we wrote, and a
reviewer may reasonably say we constructed the workload our mechanism wins on.
A hash join is *natively* the fused pattern -- a fact table scanned once
(the stream) probing a hash table that must stay resident (the reuse) -- so the
same wedge measured on a real join kernel answers the objection with the same
apparatus.

## Design

Identical to the fused harness except the tenant.  Victim, arms, replacement
policy, seeds, and every CHI pin are unchanged, so the two results are directly
comparable.

- Victim (cpu0): `victim 2650 3000000` -- 2650 KiB pointer chase, 3e6 dependent
  loads.  Unchanged from the fused campaign.
- Tenant (cpu1): `cxl_join_bench.gem5 --mode single` -- `build_table` +
  `fill_fact` + real `join_range` (hash64, linear probing, payload gather).
- Arms: `qui` (tenant replaced by `dummy`), `wb`, `cat4` (stream requestor
  confined to 4 of 20 LLC ways), `cat10` (10 of 20), `h2` (fact declared
  STREAMING via the SE m5op).  3 seeds each = 15 runs.
- `HNF_RP=lru` on **every** arm.  Non-negotiable: the way-mask path refuses
  TreePLRU, and letting only the masked arms run LRU is the confound that
  invalidated check 2.
- Mask target NodeID 5 = `cpu1.l2`, read from `config.ini`, not inferred.
- Pins: `HNF_SF_FINITE=0 HNF_SF_SETS=4096 HNF_SF_WAYS=16 HNF_H3=0 HNF_DMT=0
  HNF_FWD_UNIQUE=0 SEQ_OUT=1024 RUBY_RANDOMIZATION=1`.

### Sizing, and the one choice that decides whether the experiment means anything

`--fact-bytes 16777216` (16 MiB, matching the fused stream) and
`--hot-bytes 4194304` (4 MiB).

The hash table **must exceed the private L2 (2 MiB/16-way)**.  A 1 or 2 MiB
table is L2-resident, never reaches the LLC, and the CAT way mask therefore
masks nothing -- the campaign would report a null CAT cost for a reason that has
nothing to do with partitioning.  4 MiB is the smallest exactly-representable
size above L2.

`Entry` is 16 B and `probe()` masks rather than divides, so `--hot-bytes` is
quantized to a power of two times 16 B; 4 MiB = 2^18 entries is exact.  3 MiB
(the fused table size) is **not** representable, so this campaign cannot match
the fused table exactly and does not claim to.  Any rounding is self-reported by
the guest as `HOT_TABLE_ROUNDED`; a run emitting it at these settings is a
harness bug, not a result.

`--reps 3 --warmups 0`, sized so the tenant outlasts the victim's 3e6-access
window; if it does not, the victim's tail runs uncontended and every arm's
protection is understated.  Verified per run, not assumed (A2 below).

## Registered predictions

- **P1 (primary, the wedge).** At matched protection -- all of `cat4`, `cat10`,
  `h2` within 5 pp of each other and each >= 85% -- `h2` tenant IPC exceeds the
  better CAT arm's by **>= 8%**.  Refuted if the wedge is < 8%, or if protection
  is not matched (in which case no wedge is licensed at all).
- **P2.** WB tax on the victim is >= 1.30x quiet.  If the real join does not
  pollute, there is nothing to protect and the campaign is void.
- **P3.** `h2` tenant IPC is within +-3% of `wb` -- H2 is free to the streamer.
- **P4 (exploratory, no threshold).** Direction versus the fused wedge (+17.1%)
  is genuinely open and is NOT a registered claim.  Two effects oppose: the real
  join probes the table once per 16 B tuple rather than once per 128 B of
  stream, which is 8x more reuse per streamed byte and should make partitioning
  hurt *more*; but the hash, branch, and gather work per tuple lowers memory
  sensitivity overall, which compresses all IPC differences.  Reported as
  measured, either way.

## Analysis plan

Victim metric: `cyc_per_access` = cpu0 cycles / 3e6.  Tenant metric: cpu1 IPC.
Protection = (wb - arm) / (wb - qui).  Wedge = h2 IPC / best-CAT IPC - 1.
Mean of 3 seeds; report per-seed spread.  A run is admitted only if:

- A1: gem5 exit 0 and a stats dump exists.
- A2: the tenant's cpu1 instruction count is > 0 for every non-`qui` arm and the
  tenant did not exit before the victim (else contention is partial).
- A3: no `HOT_TABLE_ROUNDED` on stderr.
- A4: `hnf_requestor_masks` in `config.ini` matches the arm, compared as
  integers, never as strings.
- A5: `h2` shows HNF streaming-fill bypasses > 0 and every other arm exactly 0.

## Apparatus

- gem5: `build_Intel_8592/gem5.opt` sha256 cfd37207b9b7124a...
- tenant: `cxl_join_bench.gem5` sha256 9dadce49baf56b8d...
  (rebuilt 2026-09-01 with `-mclflushopt` added to the SE recipe, which had
  stopped compiling; this binary is not bit-identical to earlier SE campaigns)
- victim: `victim` sha256 1f6214b8cadb4513...

---

## Addendum, 2026-09-01: the way-mask frontier

Registered while **0 of the 15 runs above had finished**, so this is not a
response to an observed refutation.  It is registered now precisely because the
single-point comparison in P1 is foreseeably under-powered, and because an
ASPLOS reviewer will not accept one operating point regardless of how P1 lands.

### Why a single point cannot settle the claim

P1 compares H2 against CAT "at matched protection".  That is a chosen operating
point, and it invites the reply that CAT was tuned unfavourably.  It is also
fragile: `HNF_REQ_MASKS` confines a *requestor* (NodeID 5 = `cpu1.l2`), which is
the tenant's stream **and** its 4 MiB hash table together, whereas H2 confines
an *object* (the fact table only).  The two mechanisms therefore trace different
protection/cost curves, and there is no reason they should intersect at a width
that happens to be in {4, 10} ways.  If they do not, P1 is refuted on its
precondition while the underlying effect is untouched -- an outcome that would
say more about this design than about STREAMING.

### Design

Identical apparatus, victim, tenant, seeds, and CHI pins.  Only the mask width
varies:

- widths w in {1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20} of the 20-way LLC,
  mask = (1 << w) - 1 on NodeID 5; 3 seeds each = 36 runs.
- Reference points come from the campaign above (same apparatus): `qui`, `wb`,
  and `h2`.  w=20 is an unmasked control and must reproduce `wb`.
- Run names are uniform in length (`rj_wm01_s1` .. `rj_wm20_s3`) so the frontier
  is internally consistent.  Cross-checks against `rj_cat4_s1` / `rj_cat10_s1`
  carry a known ~0.038% argv-path-length artifact and are treated as
  approximate, not bit-identical.

### Registered prediction

- **P5 (dominance).** Plotting tenant IPC against victim protection, the
  STREAMING point lies **strictly outside** the CAT frontier: no way width
  achieves both protection >= H2's and tenant IPC >= H2's.
  Refuted if any single width matches or beats H2 on both axes simultaneously,
  in which case way partitioning is a sufficient substitute at that width and
  the cost argument for STREAMING fails at this workload and scale.
- **P6 (monotonicity, an apparatus check).** Protection is non-decreasing and
  tenant IPC non-increasing as w decreases.  A non-monotone curve means the mask
  is not doing what we think and the frontier is not interpretable.  w=20 must
  reproduce `wb` within seed spread.

### What the frontier does that the point cannot

If P5 holds, "why not just use CAT?" is answered for every CAT tuning, not one.
If P5 is refuted, the honest paper reports the width at which partitioning
suffices, and STREAMING's contribution narrows from cost to expressiveness
(object scope without per-requestor reconfiguration).  Either result is
publishable; only the single point is not.

---

## Addendum 2, 2026-09-01: corrected tenant lifetime (supersedes the sizing above)

Registered after the `qui` arm completed and **before any arm bearing on P1 or P5
had produced a number**.  The `qui` arm carries no outcome information about the
wedge -- its tenant is `dummy` -- so this correction is still blind.

### The defect

`fused.c` is `while (1)`: it never terminates.  gem5 ends an SE run when the
last *terminating* context exits, so in the fused campaign the victim always set
the window and the tenant was always truncated mid-stream.  That is why tenant
instruction counts differ per arm for identical tenant work (wb 55.4M, cat10
32.3M, cat4 23.9M) -- the truncation point moves with the window.

`cxl_join_bench --mode single --reps 3` **terminates**, and it front-loads
`build_table` + `fill_fact` + `prefault` + `probe_timing` before
`declare_streaming`.  Two consequences, both bad:

1. STREAMING is inactive for the first ~20-26M cycles of the window, during
   which the tenant writes 16 MiB sequentially and pollutes the LLC in *every*
   arm, h2 included.  The way mask, by contrast, applies from cycle zero.
2. The setup share is **arm-dependent**: protected arms end sooner (fused:
   106M cycles vs wb's 158M), so setup is ~21% of their window versus ~14% of
   wb's.  H2 is disabled for a larger fraction of exactly the arms where it is
   supposed to act.

Both effects push the same way -- CAT appears to protect more and cost more --
which is the shape of this paper's own claim.  A result carrying that bias is
not usable regardless of which way it lands.

### Corrected design

- `--reps 100`: the tenant becomes effectively unbounded, so it is always
  truncated by the victim, matching `fused.c`'s lifetime semantics exactly.
- `--fact-bytes 8388608` (8 MiB): still larger than the 5 MiB LLC, so it remains
  a true stream with no realizable reuse, but `fill_fact` and `prefault` halve.
- `--hot-bytes 4194304` unchanged, for the reason in the original prereg: the
  table must exceed the 2 MiB private L2 or the way mask is inert.
- Victim `2650 6000000` (6e6 accesses, up from 3e6): the window grows to roughly
  210-320M cycles, putting setup at ~5-7% instead of 14-21%.
- A **fused reference campaign at the same victim setting** (5 arms x 3 seeds) is
  run alongside, so "larger or smaller than the fused wedge" is a comparison at
  a matched window rather than across two different ones.

`cyc_per_access` becomes cycles/6e6; protection and tenant IPC are ratios and
remain directly comparable.

### Status of the superseded 51 runs

They keep running.  They are not discarded and not promoted: they quantify the
confound empirically (their setup share is ~3x larger), and their `qui` arm
already reproduced the archived fused campaign **bit-identically** across all
three seeds -- `cyc_per_access`, `simInsts`, and `simTicks` all exact -- which
verifies gem5, the CHI config, the victim, and every pin. Any result reported
from them will be labelled as carrying the setup confound.

---

## Outcome of the superseded 51: P2 refuted, campaign void

All 15 superseded wedge runs completed.  Recorded here rather than discarded
silently, because the failure is instructive.

| arm | cyc/acc | vs quiet | "protection" | tenant IPC | tenant instr |
| --- | --- | --- | --- | --- | --- |
| qui | 33.881 | +0.00% | -- | -- | 0 |
| wb | 34.086 | +0.60% | -- | 0.2043 | 20,894,850 |
| cat4 | 33.921 | +0.12% | 80.45% | 0.2031 | 20,672,069 |
| cat10 | 33.938 | +0.17% | 72.49% | 0.2035 | 20,721,461 |
| h2 | 34.085 | +0.60% | **0.76%** | 0.2044 | 20,900,353 |

**P2 is refuted: WB tax = 1.0060x against a registered floor of 1.30x**, so by
its own pre-registered criterion this campaign is void and licenses no wedge.

Cause.  The tenant retired **20.9M instructions** against a setup cost since
measured exactly at **43.4M instructions** (`ph_f8_r1`/`ph_f8_r2` decomposition:
setup 43,415,027 instr / 184,953,063 cycles; one join pass 17,791,220 instr /
40,817,233 cycles, for an 8 MiB fact -- the 16 MiB fact used here is larger
still).  The tenant therefore got at most ~48% of the way through
initialisation: it never reached `declare_streaming()` and never executed a
single join pass.

*Correction to an earlier draft of this section:* the absence of
`DECLARE_STREAMING` from the `h2` logs was cited as direct proof.  It is not.
`declare_streaming()` returns **silently** on the SE `--declare m5op` path
(`if (g_declare == DeclareVia::M5OP) { gem5_set_streaming(...); return; }`), so
that marker is absent whether or not the call happened.  The evidence that
stands is the instruction-count shortfall above, the 0.005% agreement between
`h2` and `wb`, and the refuted P2 floor.  The lesson is recorded in the gates:
positive proof of engagement comes from the HNF bypass counter (A5b), never from
a marker that a code path may not emit.  The `h2` arm is therefore a `wb` arm: the two differ by 0.005%.

What the contaminated campaign would have supported had its gates been trusted:
*"way partitioning protects the victim by 72-80%; STREAMING provides none
(0.76%); the fused wedge does not reproduce on a real hash join."*  That is
thesis-destroying and entirely an artifact of tenant-lifetime and phase
alignment.  Two independent guards caught it -- the registered P2 floor, and the
`DECLARE_STREAMING` marker count -- which is the argument for having both.

---

## Addendum 3, 2026-09-01: setup excluded by a tenant-side reset (metric B)

Registered before any metric-B arm produced a number.

### Why addendum 2 was not enough

`ph_f8_r1` (tenant alone, 8 MiB fact, one pass) measured **225.8M cycles and
61.2M instructions**.  A pass over 524288 tuples is ~13M instructions, so
**setup is ~48M instructions, ~79% of the tenant's work** -- roughly twice the
~23M that addendum 2 assumed.  At the superseded campaign's observed tenant IPC
of 0.204 that is ~177M cycles, i.e. 87% of a 6e6-access victim window.  Widening
the window cannot fix a confound that large without an absurd runtime, so the
66 runs of addendum 2 were stopped rather than reported.

### The change

`victim.c` already resets statistics before its own measurement pass and calls
`m5_exit` at the end -- which is why the victim always sets the window and the
tenant is truncated.  The missing half is the tenant's:

- `cxl_join_bench.cpp` (`run_single`) and `fused.c` now call the gem5
  reset-stats pseudo-op **after** initialisation and declaration, immediately
  before their measured loop.  Setup is excluded by construction, not diluted.
- Victim latency becomes **`cpu0.numCycles / cpu0.commitStats0.numLoadInsts`**
  (`cyc_per_load`).  The window now covers fewer than `VICTIM_ITERS` accesses, so
  dividing by `VICTIM_ITERS` would be wrong; the chase issues exactly one load
  per iteration, so retired loads *are* the access count.
- Victim raised to `2650 12000000`: setup consumes ~5.2M accesses, leaving ~6.8M
  inside the measured window with margin for arm-dependent setup duration.
- New gate **A6**: for a contended arm, `victim_loads` must fall in
  [1e6, 0.90 x VICTIM_ITERS].  A value near `VICTIM_ITERS` means the tenant never
  reached its reset -- precisely the failure that voided the superseded campaign.

### Comparability

The archived fused numbers (33.881 / 52.756 / IPC 0.3503) are `cyc_per_access`
over a window that **included** the tenant's initialisation, so they are not
comparable to `cyc_per_load` and the analyser no longer compares against them.
`fused.c` carries the same confound as the join did -- its own first-touch of
19 MB sits inside the old window -- so the published +17.1% fused wedge is itself
diluted by an unmeasured amount.  The fused reference is therefore re-run inside
this campaign (`fqui/fwb/fh2/fcat4/fcat10`) under the identical metric and
window, and P4's comparison is drawn from those arms.

---

## Amendment 1, 2026-09-01: three corrections made AFTER data existed

Recorded because all three change the analysis apparatus after outcomes were
visible.  Each is stated with what was changed, why, and whether it could have
altered a verdict in the paper's favour.

### A1.1 Run-name parser (analysis could not run at all)

Both analysers matched run names against `rj_<arm>_s<seed>`.  The metric-B
campaign names its runs `r3_<arm>_s<seed>` (addendum 3 renamed the output root).
Every arm therefore looked absent: the frontier analyser reported
`missing=[1,2,3,4,6,8,10,12,14,16,18,20]` on a **complete** frontier, and
refused to certify.

Corrected to `r(?:j|[0-9])_([a-z0-9]+)_s(\d+)$`, accepting `rj_`, `r2_`, `r3_`.

- **Could this favour the paper?**  No.  It is a total-failure bug: the analyser
  produced *no* result, not a wrong one.  The correction restores the ability to
  compute a verdict; it does not change any threshold or any measured value.
- Pinned by three regression tests (`TestAnalyzerRunNameMatching`), including one
  asserting both analysers carry the identical pattern so they cannot drift.

### A1.2 Gate A6 window cap, 0.90 -> 0.97 (the gate rejected the key arms)

A6 bounds `victim_loads` in `[1e6, MAX_FRAC x VICTIM_ITERS]` to prove the
tenant's reset fired.  `MAX_FRAC` was set to 0.90 from an *estimate* that setup
would consume ~5.4M of the 12M budget.

Measured: setup consumes only ~1.2-1.5M, because the victim runs ~3.6x slower
while the tenant initialises.  Realised values: `cat4` 10,549,458 (87.9%),
**`h2` 10,810,055 (90.08%)**, **`wb` 10,812,896 (90.11%)**.  The cap rejected
`h2` and `wb` -- the two arms the campaign exists to measure.

- **Could this favour the paper?**  It loosens a gate, so in principle yes, and
  it is recorded as such.  Mitigations: the failure mode A6 exists to catch is
  unambiguous and far away -- a reset that never fires returns *exactly* the
  tenant-free count, 12,001,060 (96.7% would be 11.6M) -- and the fused arms
  demonstrate this separately, returning precisely 12,001,060.  0.97 still
  separates the two populations by a wide margin.

### A1.3 The fused-vs-real "4.2x" comparison is WITHDRAWN

Claimed: `fcat4` +6.21% vs `cat4` +1.48%, therefore a synthetic stream pollutes
4.2x harder than a real join.  **Withdrawn: the two arms do not share a
measurement window.**

`victim_loads` is 12,001,060 for every fused arm -- identical to the tenant-free
`qui` arm -- and 10.5-10.8M for the real-join arms.  Cause: both tenants reset,
but fused's initialisation is short enough that the *victim's* own reset lands
last and defines the window, whereas the join's 185M-cycle setup means the
*tenant's* reset lands last.  Both windows are plausibly steady-state, but that
was argued after the fact rather than verified.

The ratio must not be quoted until the fused reference is re-run with a
phase-aligned barrier and gated by the same A6 check.  Raw per-arm numbers
remain valid *within* their own window and are reported as diagnostics only.

### Registered-prediction status at 62/66

- **P2 PASSES** -- WB tax 1.3168x (floor 1.30x).
- **P6a PASSES** -- `wm20` reproduces `wb` to +0.05% (victim) / -0.07% (IPC).
- **P1 REFUTED on its precondition** -- it required every compared arm at >=85%
  protection within 5 pp; measured `cat4` 95.33%, `cat10` 94.92%, `h2` 24.23%.
  This is the Scenario-B outcome pre-committed in addendum "the way-mask
  frontier": report the refutation, disclose the protection asymmetry, and make
  the frontier the primary result.
- **P6b REFUTED, and not as an apparatus fault** -- protection is non-monotone
  (rises to w=8, then falls), because way-starvation at narrow masks raises the
  tenant's miss traffic more than its occupancy would cost.  P6b was registered
  as a pure apparatus check; that framing was too narrow and is corrected here.
- **P5 not yet certified** -- awaiting `h2_s3` and the fused arms.

### A1.4 Gate A3 was unimplementable by construction (rewritten)

A3 verified realized geometry by parsing the tenant's JSON record.  The tenant
runs `--reps 100` and is truncated by the victim's `m5_exit`, so it **never
reaches `emit_json_prefix`**.  No JSON is ever emitted; A3 could not pass for any
arm in any campaign of this design.  It failed all 15 non-`qui` runs at 66/66
with `hot/fact=None/None`.

Rewritten to use output the guest prints *before* truncation:
`BIND_POOL ... bytes=8388608` (realized fact size, printed at allocation) and the
absence of `HOT_TABLE_ROUNDED` (which the guest prints iff the table was
quantized, so silence establishes exactness).  The requested table size is read
from the recorded command line.

- **Could this favour the paper?**  It converts a gate that always failed into
  one that can pass, so it must be treated as capable of doing so.  Mitigation:
  the replacement checks *realized* values from guest output, not requested ones
  -- `BIND_POOL` reports what was allocated, and `HOT_TABLE_ROUNDED` is the
  guest's own quantization alarm.  It is strictly more informative than parsing a
  record that never exists.

### A1.5 P4's fused comparison now refuses mismatched windows

P4 was still printing a fused-vs-real ratio (+24.33% vs +33.52%) after A1.3
withdrew exactly that comparison.  The analyser now checks `victim_loads`
equality first and suppresses with an explicit message when the windows differ.
Measured at 66/66: fused 12,001,060 vs real-join 10,811,710, **9.9% apart**.

## Final outcome at 66/66

**Frontier (registered instrument): PASS.**

    reference  quiet 33.890 | wb 44.628 (tax 1.3168x, tenant IPC 0.3604)
    STREAMING  victim 42.040, protection 24.11%, tenant IPC 0.3814

    P5  PASS  no way width matches H2 on both axes (12 widths tested)
    P6a PASS  w=20 reproduces wb to +0.000% on victim and IPC
    P6b FAIL  non-monotone -- way-starvation, not apparatus fault (see A1 above)
    P6c PASS  tenant IPC monotone in width

    WEDGE at equal-or-better protection = +11.76%
      cheapest CAT width protecting >= STREAMING's 24.11% is w=16 (24.84%),
      costing the tenant -5.32% IPC; STREAMING costs +5.82%.

**Per-arm predictions:** P2 PASS (1.3168x).  **P1 REFUTED on its precondition**
(protection 24.11-95.33%, not matched).  **P3 REFUTED in the paper's favour**:
H2 is not merely free to the streamer, it leaves the tenant **+5.82% faster than
unprotected**, because excluding the stream frees LLC for the tenant's own hash
table -- something no requestor-scoped mask can do.

**The number to quote is +11.76% at equal protection, read off the frontier.**
The `+33.52%` printed beside P1 is NOT a wedge: it compares `h2` against
`cat10`, which protects ~4x better.  That mismatch is why P1 carries a
precondition.

**Scope.** These are SE-mode m5op measurements.  r12's `mprotect` result
establishes mechanism engagement through the OS path; the two must not be merged
into one claim.

---

## Addendum 4, 2026-09-01: phase-aligned fused reference (campaign r4)

Registered before any r4 arm produced a number.  Addresses the withdrawal in
A1.3 rather than working around it.

### The defect being repaired

Both tenant and victim reset statistics; the **last** reset defines the measured
window.  `fused.c`'s initialisation is short, so the *victim's* reset landed
last and its window covered all 12e6 victim accesses (`victim_loads` =
12,001,060, identical to the tenant-free `qui` arm).  The hash join's 185M-cycle
setup means the *tenant's* reset landed last, giving ~10.8e6.  Two different
windows; the ratio between them was withdrawn.

### The change

`fused.c` takes a new `argv[4]` = warmup passes to stream **before** resetting.
The reset moves from before the loop into the loop tail, firing once after
`warm` passes.  `0` reproduces the previous behaviour exactly.

Sized from measurement, not guessed: the archived fused campaign
(`fh_wb_s1`) ran 55.4M tenant instructions over 158M cycles at ~2.6M
instructions per 16 MB pass, i.e. **~7.5M cycles per pass**.  Reaching the hash
join's measured 184,953,063-cycle reset point therefore needs **25 passes**.

Both campaigns now begin their measured window at the same logical point:
*after tenant initialisation and after victim warmup, at the tenant's reset*.

### Prediction

- **P7.** With `warm=25`, the fused arms' `victim_loads` fall in the same band as
  the real-join arms (roughly 7-11e6, and in any case < 0.97 x 12e6), so gate A6
  passes and P4's window-mismatch suppression no longer fires.
  Refuted if `victim_loads` returns 12,001,060 again -- which would mean 25
  passes still do not outlast the victim's warmup, and the count must rise.

Only once P7 holds may a fused-vs-real ratio be quoted.  Until then the
withdrawal in A1.3 stands.
