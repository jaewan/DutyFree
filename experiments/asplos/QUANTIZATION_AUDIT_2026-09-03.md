# Tick-quantisation audit of the SE CHI configuration path — outcome

Motivated by `H1BW_MULTICORE_OUTCOME_2026-09-03.md` §"Realized configuration",
which established that `SimpleMemory.bandwidth` is silently quantised from a
requested `512GiB/s` to a realized 500.00 GB/s, and that the guard in
`m5.ticks.fromSeconds` that should have reported it is unable to fire on a
value that rounds *up*. This document fixes the guard and audits every other
parameter the same defect could have reached.

Everything below is read back from a real `config.ini` or from a
config-generation run, never from a request. Nothing under `gem5/logs/` was
modified, nothing was rebuilt, and no simulation was launched: every gem5
started here was killed as soon as it had written `config.ini`, before it
entered the C++ event loop, and wrote only into a scratch directory under
`/tmp`. The fifteen `h1bw_mc_*l3x*_20260904` processes were running throughout
and were still running at the end.

## Verdict

**Nothing besides `SimpleMemory.bandwidth` carries material error. The blast
radius of the original defect is exactly one parameter.**

Across all five configurations this project has run — baseline 4c, baseline 8c,
the single-slice bracket, and both CXL-bandwidth brackets — **3,252 parameter
instances** reduce to **61 distinct (path, parameter, value) rows** whose type
is quantised to an integer tick count. Of those 61, **exactly one has an error
above 0.1%**, and it is the already-known one:

| parameter | requested | realized | rel. error | material? |
|---|---|---|---|---|
| `system.mem_ctrls{0,1}.bandwidth` | 512 GiB/s = 549.7558 GB/s | **2 ticks/byte = 500.0000 GB/s** | **−9.0505%** | **yes** |
| `system.cpu_clk_domain.clock` | 1.9 GHz | 526 ticks = 1.9011407 GHz | +0.0600% | no |
| *every other row* | — | — | **exactly 0** | no |

There is no second finding. The 59 remaining distinct rows realize their
requested value **exactly**: they are latencies in whole nanoseconds or whole
microseconds, the 1 GHz system clock, the 2 GHz Ruby clock, and the
`power_state.clk_gate_{min,max}` pairs at 1 ns and 1 s (90 pairs per 4-core
configuration, which is what makes the pooled instance count large). At
`simFreq = 1e12` all of those land on integer ticks with no residue. Two of the
59 are zero-valued (`latency_var` and `progress_interval`) and take
`fromSeconds`'s `if value == 0: return 0` short-circuit, so they are never
converted at all.

The second-largest error in the entire configuration is the CPU clock at
0.060%, which is **151x smaller** than the bandwidth error and 15x smaller
than the smallest effect the H1 campaigns claim (a 25% H2-over-WB gap). It is
reported here only so the judgement is visible rather than buried.

**The in-flight campaigns are sound.** All fifteen were verified individually
against their pre-registrations; see §"The in-flight campaigns".

## The guard fix

`gem5/src/python/m5/ticks.py`, in `fromSeconds`:

```
-    err = (value - int_value) / value
+    # Magnitude, not signed difference: rounding up makes (value - int_value)
+    # negative, which no positive tolerance can ever exceed, so the signed
+    # form silently passed every value that rounded up.
+    err = abs(value - int_value) / value
     if err > frequency_tolerance:
```

That is the whole change. `ROUND_HALF_UP` is untouched, `frequency_tolerance`
is untouched at 0.001, and `err` feeds nothing but the `warn()` predicate, so
the returned integer cannot move.

### Inertness proof

Same technique as the prior campaign's `prove_default_unchanged.sh`, extended
with a positive control. Script:
`experiments/asplos/prove_ticks_guard_inert.sh`.

**Result: 0 differing lines out of 42,789 compared (38,803 non-blank).**

The comparison is `config.ini` generated through the real runner with the
patched code, against `gem5/logs/se_chi/h1bw_mc_wb_4c_20260904/config.ini`,
after canonicalising each file's three self-referential
`host_paths=<outdir>/fs/{proc,sys,tmp}` entries, which record the output
directory itself and can never match between two runs. The raw diff is printed
by the script so the substitution is auditable: it contains those three lines
and nothing else. 38,803 is the same line count the prior proof reported, so
the two proofs are comparing the same reference in the same way.

Two further checks in the same script:

- **Control against patched** is also empty. This isolates the patch from every
  other property of the invocation.
- **The positive control fires.** With the patch loaded, six
  `rounding error > tolerance` lines appear; without it, zero. Without this the
  inertness result would be vacuous — an edit that never executed would
  trivially change nothing.

One incidental discovery while building the proof, worth recording because it
would otherwise look like a failure of the patch: `se.py` records the
*launching shell's* working directory in each `Process`'s `cwd=`, four lines at
4 cores. The completed campaign was launched from
`/home/domin/DutyFree/experiments/asplos`, so the proof script `cd`s there
rather than canonicalising the difference away. Those four lines are an
invocation property, not a configured value.

### The fix is source-only until gem5 is rebuilt — this is load-bearing

**gem5 marshals `src/python/` into `gem5.opt` at build time**
(`src/python/importer.py:CodeImporter`), so the existing binary still carries
the old bytecode. An edit to `src/python/m5/ticks.py` has **no effect on any
run using the current `gem5.opt`** unless `M5_OVERRIDE_PY_SOURCE=true` is set,
which makes the embedded importer recompile each module from the absolute path
recorded at build time.

This is why the fix could be verified at all under the no-rebuild constraint,
and it is also the operational caveat: **the guard will not protect a future
run until `gem5.opt` is rebuilt.** Until then, either rebuild or set
`M5_OVERRIDE_PY_SOURCE=true`. Note the difference from the prior campaign's
precedent, whose change was to `configs/ruby/Ruby.py` — `configs/` is read
from disk at run time and is not embedded.

The override is safe to use as a proof vehicle here because the on-disk
`src/python/` tree is clean at HEAD apart from this one hunk: the last commit
touching `src/python/` is 2025-12-30 and `gem5.opt` was built 2026-08-31, so
the override introduces exactly one difference from what the binary embedded.

### What the new warning fires on

**Exactly one parameter: `SimpleMemory.bandwidth` at its class default.**

| configuration | `mem_ctrls0` | `mem_ctrls1` | warning lines |
|---|---|---|---|
| baseline 4c | 2 (default) | 2 (default) | **6** (measured) |
| baseline 8c, single-slice bracket | 2 (default) | 2 (default) | 6 |
| `bwt31` bracket | 2 (default) | 31 (requested) | **3** (measured) |
| `bwt16` bracket | 2 (default) | 16 (requested) | 3 |

Every line is identical: `1.818989 rounded to 2`. The count is three per
`SimpleMemory` instance still sitting at the class default, not three
parameters — `MemoryBandwidth.getValue()` is called once for the `config.ini`
dump, once for the `config.json` dump, and once when the C++ parameter object
is constructed. The two rows marked *measured* were counted directly from an
uninstrumented `console.log`; they establish the three-per-instance rate, and
the other two rows follow from it (their instrumented runs, which add one
`ini_str()` call per parameter, came out at 8 and 4 as that rate predicts).

Two things this table says beyond the headline. First, the **local DRAM range
carries the same 9.05% quantisation as the CXL range**, and always has — it is
the same class default. That is not a new defect: `H1BW_CXLBW_PREREG` states
the DRAM range's realized value as 500 GB/s and defends 500 GB/s on its own
merits, so the pre-registered figure is the realized one. Second, the
bracket requests `32258064516B/s` and `62500000000B/s` **produce no warning**,
which independently confirms the pre-registration's claim that they were chosen
to land on integer ticks with margin (31.000000000124 and 16.000000000000).

The guard measures relative error in **tick space**, so its 0.1% threshold is
not quite the threshold on the quantity a reader cares about. For the
bandwidth default the two differ: 9.9512% in ticks per byte against 9.0505% in
bytes per second. Both are far above any threshold, so nothing turns on it
here, but a parameter sitting between the two would be reported or not
depending on which domain the tolerance is applied in. The audit table below
reports error in the **requested** domain, which is the one the configuration
author reasons in.

## The audit

### Scope and method

The five conversion paths into `fromSeconds`, all of which return an integer:

| Python type | conversion | grid |
|---|---|---|
| `Latency` | `fromSeconds(seconds)` | integer ticks |
| `Clock` | delegates to `.period`, i.e. `Latency` | integer ticks |
| `Frequency` | `fromSeconds(1/Hz)` | integer ticks of period |
| `MemoryBandwidth` | `fromSeconds(1/bytes_per_s)` | integer ticks **per byte** |
| `NetworkBandwidth` | `fromSeconds(8/bits_per_s)` | integer ticks per byte |

**`Frequency` and `Clock` are affected.** This was checked rather than
assumed. `Clock.getValue()` returns `self.period.getValue()`, which is
`Latency.getValue()`, which calls `fromSeconds`; `Frequency.getValue()` calls
`fromSeconds(1.0 / self.value)` directly. `Clock` is where it bites in
practice, because `SrcClockDomain.clock` is a `VectorParam.Clock` and every
clock domain in the system is one. `Frequency` is affected in principle but
inert in this configuration path: the only `Frequency` parameter instantiated
anywhere is `BaseCPU.progress_interval`, which is 0 on all cores and takes
`fromSeconds`'s `if value == 0: return 0` short-circuit. `DerivedClockDomain`
adds nothing — it divides an already-quantised parent period by an integer
`clk_divider`.

**`NetworkBandwidth` is not instantiated at all** in this configuration path.
Zero instances across all five configurations. Garnet is not used; the
`Pt2Pt`/`SimpleNetwork` path expresses link bandwidth as integers (below).

Enumeration was mechanical rather than by hand-reading defaults. A temporary
hook in `SimObject.print_ini` (`experiments/asplos/quant_trace_instrument.py`,
applied and reverted by `experiments/asplos/enumerate_quantized_params.sh`)
records path, parameter, Python class, requested SI value and realized integer
for **every parameter that reaches `config.ini`** whose type is one of the five
above. Hooking the `.ini` dump rather than `fromSeconds` is what makes the
enumeration complete: it sees the parameters that convert exactly as well as
the ones that do not, and it knows each one's path and name, which
`fromSeconds` does not. `experiments/asplos/audit_quantized_params.py` then
computes the relative error in the requested domain. The tree is left clean;
only the `ticks.py` hunk remains.

The fixed guard's own output is the independent cross-check: the set it reports
must equal the set the table computes as above 0.1%. It does — one parameter,
both ways.

Coverage: `configs/deprecated/example/se.py`, `configs/ruby/Ruby.py`,
`configs/ruby/CHI_config_8592.py`, `configs/common/MemConfig.py`,
`configs/common/Options.py`, `src/mem/SimpleMemory.py`, and every Ruby
controller, cache and network SimObject these instantiate — by construction,
since anything they instantiate appears in `config.ini`.

### Bandwidths

| parameter | requested | realized (`config.ini`) | realized value | rel. error | material |
|---|---|---|---|---|---|
| `mem_ctrls0.bandwidth` (local DRAM) | `512GiB/s` class default | `bandwidth=2.000000` | 500.0000 GB/s | **−9.0505%** | **yes** |
| `mem_ctrls1.bandwidth` (CXL), baseline | `512GiB/s` class default | `bandwidth=2.000000` | 500.0000 GB/s | **−9.0505%** | **yes** |
| `mem_ctrls1.bandwidth`, `bwt31` | `32258064516B/s` | `bandwidth=31.000000` | 32.2581 GB/s | +4e-10 % | no |
| `mem_ctrls1.bandwidth`, `bwt16` | `62500000000B/s` | `bandwidth=16.000000` | 62.5000 GB/s | 0 | no |
| Ruby link `bandwidth_factor` (324 links) | `16` (`Param.Int`, bytes/cycle) | `bandwidth_factor=16` | 32.0 GB/s per link | **0, not applicable** | no |
| `SimpleNetwork.endpoint_bandwidth` | `1000` (`Param.Int`) | `endpoint_bandwidth=1000` | scaling factor | **0, not applicable** | no |

**Ruby link and network bandwidth is not subject to this quantisation at all,**
which was the most likely additional candidate and is a clean negative.
`BasicLink.bandwidth_factor` is `Param.Int(16, "generic bandwidth factor,
usually in bytes")` and `SimpleNetwork.endpoint_bandwidth` is
`Param.Int(1000)`. `Throttle::getLinkBandwidth` returns
`endpoint_bandwidth * bandwidth_factor` against a
`MESSAGE_SIZE_MULTIPLIER = 1000`, i.e. **16 bytes per Ruby cycle**, entirely in
integer arithmetic with no call into `fromSeconds`. The grid is coarse — a link
is an integer number of bytes per cycle — but it is not *silent*: the
configuration author writes an integer and gets that integer. At the Ruby
clock's exactly-realized 2 GHz this is exactly 32.0 GB/s per link. The
superseded campaign measured link utilisation below 0.51%, so nothing here
binds; the point is that the ceiling is exactly what was asked for.

### Latencies

Every latency in the configuration path realizes **exactly**.

| parameter | requested | realized | rel. error |
|---|---|---|---|
| `mem_ctrls0.latency` (DRAM) | `98ns` | `98000` | 0 |
| `mem_ctrls1.latency` (CXL) | `203ns` | `203000` | 0 |
| `mem_ctrls{0,1}.latency_var` | `0ns` | `0` | 0 (short-circuit) |
| `cpuN.interrupts.pio_latency` | `100ns` | `100000` | 0 |
| `cpuN.interrupts.int_latency` | `1ns` | `1000` | 0 |
| `dvfs_handler.transition_latency` | `100us` | `100000000` | 0 |
| `root.time_sync_period` | `0.1s` | `100000000000` | 0 |
| `root.time_sync_spin_threshold` | `100us` | `100000000` | 0 |
| `*.power_state.clk_gate_min` (90 per 4c config) | `1ns` | `1000` | 0 |
| `*.power_state.clk_gate_max` (90 per 4c config) | `1s` | `1000000000000` | 0 |

`MemConfig.py` contributes no inexact conversion: its only latency assignment
is `dram_intf.latency = "1ns"` under `--elastic-trace-en`, which these runs do
not set and which would be exact regardless.

This is the expected result and the reason to state it: at `simFreq = 1e12`
one tick is 1 ps, so any latency expressed in whole nanoseconds is exact, and
the campaign expresses all of them that way. The interesting cases were always
going to be the bandwidths.

### Latencies expressed in cycles — why they are not subject to this

**Every latency in the Ruby/CHI hierarchy is `Param.Cycles`, an integer count
of cycles. None of them passes through `fromSeconds`.** The full set,
confirmed by grepping `Param.Cycles` across `src/mem/ruby/` and read back from
the reference `config.ini`:

| parameter | class | realized in `h1bw_mc_wb_4c_20260904` |
|---|---|---|
| `RubyCache.dataAccessLatency` | `Cycles` | 0 (x16 SF/DMA), 1 (x12 L1I/L1D/L2), 64 (x4 HNF) |
| `RubyCache.tagAccessLatency` | `Cycles` | 1 (x24), 2 (x8 L2/HNF) |
| `Controller.response_latency` | `Cycles` | 1 (x17), 2 (x2) |
| `Controller.recycle_latency` | `Cycles` | 10 (x18) |
| `Controller.mandatory_queue_latency` | `Cycles` | 1 (x18) |
| `to_memory_controller_latency` | `Cycles` | 1 |
| `BasicLink.latency`, `BasicRouter.latency` | `Cycles` | 1 (x342) |
| `SimpleNetwork.{int,ext}_routing_latency` | `Cycles` | 1 (x18 each) |

A `Cycles` parameter is an integer by type, so there is nothing for
`ROUND_HALF_UP` to discard. Its realized *time* is `cycles x clock period`,
and the clock period is itself an integer number of ticks — so a cycle-denominated
latency inherits its clock domain's quantisation error and adds none of its
own. For everything in the Ruby hierarchy that error is **zero**, because
`system.ruby.clk_domain.clock` realizes 2 GHz exactly as 500 ticks. Ruby cycles
are exactly 500 ps and the whole CHI hierarchy's timing is exact.

**The L1D/L2/L3 latencies that commit `44b7eb7470` describes itself as
calibrating are therefore exactly realized.** They are:

| cache | `dataAccessLatency` | `tagAccessLatency` | calibration comment in `CHI_config_8592.py` |
|---|---|---|---|
| L1I | 1 | 1 | — |
| L1D | 1 | 1 | "measured 2.6ns load-to-use (EMR)" |
| L2 | 1 | 2 | "measured 8.4ns incl. L1-miss path" |
| HNF (L3) | 64 | 2 | "measured 38.4ns load-to-use (EMR)" |
| snoop filter | 0 | 1 | — |

At 500 ps per Ruby cycle these are 0.5/0.5, 0.5/0.5, 0.5/1.0 and 32.0/1.0 ns,
all exact. Whether 66 cycles is the right calibration for a measured 38.4 ns
load-to-use is a separate question this audit does not address; what it
establishes is that the calibration is **not corrupted by tick quantisation**.
The model's latency grid here is 0.5 ns, coarse but explicit — the author
writes cycles and gets cycles.

### Clocks

| clock domain | requested | realized | realized value | rel. error |
|---|---|---|---|---|
| `system.clk_domain` (`--sys-clock`) | `1GHz` default | `clock=1000` | 1.0000000 GHz | 0 |
| `system.ruby.clk_domain` (`--ruby-clock`) | `2GHz` default | `clock=500` | 2.0000000 GHz | 0 |
| `system.cpu_clk_domain` (`--cpu-clock`) | **`1.9GHz`** | **`clock=526`** | **1.9011407 GHz** | **+0.0600%** |

The CPU clock is the only inexact clock and the only non-bandwidth
quantisation anywhere in the configuration. `1/1.9e9 s` is 526.3157894737
ticks, which rounds **down** to 526, so the realized CPU is 0.060% *faster*
than requested. It does not trip the 0.1% guard and it never will at this
tolerance.

**Judgement: not material, and disclose it as a footnote rather than correct
anything.** 0.060% is 151x below the bandwidth error, 15x below the smallest
claimed effect, and far below the campaigns' own n = 1 measurement noise (the
inter-instance spread alone is 1.8–9.99%). It is common to every arm and every
core count, so it cannot affect a ratio. It does propagate to everything
denominated in CPU cycles, including `numCycles` and the O3 pipeline's own
timing, but uniformly and at 0.060%.

Where it does need saying: all three H1BW documents' frozen-configuration
tables read "CPU | O3CPU, 1.9 GHz", which is the *requested* value presented
as configuration. Under this project's own F9 discipline the realized figure
is 1.9011407 GHz. Recommended action is a footnote in any successor
pre-registration, not a correction to the existing ones — no number in them
moves.

Only `simFreq / k` for integer `k` is representable, so the two clocks nearest
1.9 GHz are 1e12/526 = 1.9011407 GHz and 1e12/527 = 1.8975332 GHz. **There is
no way to request either exactly through `--cpu-clock` on this path**, and this
was tested rather than assumed. `Clock.__init__` does accept a bare tick count
via its `value.endswith("t")` branch, so `--cpu-clock=526t` looks like the
obvious answer, but it aborts before `m5.instantiate()`:

```
ValueError: cannot convert '526t' to frequency
  configs/common/FileSystemConfig.py(116): config_filesystem
```

`FileSystemConfig.config_filesystem` calls `toFrequency(options.cpu_clock)` on
the raw option string to populate the simulated `/proc/cpuinfo`, and
`convert.toFrequency` has no tick unit. The tick form reaches the
`SrcClockDomain` fine; it is this second, unrelated consumer of the same string
that rejects it. So a successor has three choices, none of them free: accept
the 0.060%, request a frequency whose period is near-integral in ticks
(`--cpu-clock=1901140684Hz` gives 526.0000001 ticks), or raise `simFreq`. Given
the size of the error, accept it and disclose it.

## The in-flight campaigns

**Sound. Verified, not assumed.** All fifteen `h1bw_mc_*l3x*_20260904` runs
were read back from their own `config.ini` and `MANIFEST.json` while running:

| bracket | runs | realized `mem_ctrls1.bandwidth` | pre-registered expectation | match |
|---|---|---|---|---|
| `bwt31` (4c and 8c, three arms) | 6 | **31.000000** | 31 (`H1BW_CXLBW_PREREG`) | yes |
| `bwt16` (4c and 8c, three arms) | 6 | **16.000000** | 16 (`H1BW_CXLBW_PREREG`) | yes |
| `l3x1_bwdef` (4c, three arms) | 3 | **2.000000** | 2 (`H1BW_SLICE_BRACKET_PREREG` G4) | yes |

All fifteen also report `mem_ctrls0.bandwidth=2.000000`, the untouched class
default, which is what `H1BW_CXLBW_PREREG` §"The local DRAM range is
deliberately left at 500 GB/s" says it should be. **Gate G4 will pass on all
fifteen.**

The reason they are sound is structural, not lucky: both pre-registrations were
written against the **realized integer ticks per byte** rather than against a
nominal GB/s figure, precisely because the earlier defect had been diagnosed
first. `H1BW_CXLBW_PREREG` says so explicitly — it rejects 32 and 64 GB/s as
unrealizable (31.25 and 15.625 ticks/byte), freezes the two settings at 31 and
16 ticks/byte, and gates on the realized integer while recording the request in
`MANIFEST.json` where no gate reads it. The audit confirms the arithmetic:
`32258064516B/s` converts to 31.000000000124 ticks/byte and
`62500000000B/s` to exactly 16, so neither request is anywhere near a rounding
boundary, and neither trips the fixed guard.

`grep -ci 'rounding error'` returns 0 on all fifteen consoles, as expected —
they are running the unpatched embedded bytecode, and would return 0 even with
a rebuilt binary for the `mem_ctrls1` value. A rebuilt binary would report the
`mem_ctrls0` default three times per run.

## Which published or pre-registered figures are affected

**None require correction.** Checked against every document in
`experiments/asplos/` that states a bandwidth or clock figure.

| document | figure | status |
|---|---|---|
| `H1BW_MULTICORE_OUTCOME_2026-09-03.md` | "memory bandwidth ceiling ~500 GB/s per controller", `bandwidth=2.000000` | **correct** — already the realized value; this audit confirms its diagnosis and adds nothing to it |
| `H1BW_CXLBW_PREREG_2026-09-03.md` | 2 ticks/byte = 500 GB/s; 31 and 16 ticks/byte = 32.2581 and 62.5000 GB/s | **correct** — realized values, verified against all twelve in-flight runs |
| `H1BW_SLICE_BRACKET_PREREG_2026-09-03.md` | "CXL bandwidth untouched: 2 ticks/byte = 500 GB/s" | **correct** — verified against all three in-flight runs |
| `GATE1_FUSED_NULL_CORRECTION_2026-08-15.md:131` | "`SimpleMemory.bandwidth` is 2.0 ticks/byte (~500 GB/s)" | **correct** — realized value |
| all three H1BW documents | frozen-config row `CPU` = "O3CPU, 1.9 GHz" | **requested, not realized**; realized is 1.9011407 GHz (+0.060%). Immaterial; footnote in successors, no correction |

The paper sources (`Appendix.tex` and siblings, cited by
`H1BW_MULTICORE_OUTCOME`) are not in this tree, so this audit cannot check
them. **Any paper text that quotes a memory or CXL bandwidth must quote 500
GB/s, 32.2581 GB/s or 62.5000 GB/s — never 512 GiB/s, 32 GB/s or 64 GB/s.**
That is the one instruction this document carries into the write-up.

One source-level wart, already noted in `H1BW_MULTICORE_OUTCOME` and not
duplicated as a finding: the comment in `src/mem/SimpleMemory.py` immediately
above the `512GiB/s` default still reads "The memory bandwidth limit default is
set to 12.8GiB/s which is representative of a x64 DDR3-1600 channel." It is
upstream's, it is stale, and it is what made the value hard to find. Fixing it
would be a comment-only change and is left to a successor because it is not
this document's obligation.

## What this licenses, and what it does not

Licensed:

- **The blast radius of the quantisation defect is one parameter**,
  `SimpleMemory.bandwidth`, on both memory controllers, at 9.05%. Every other
  tick-quantised parameter in this configuration path is exact except the CPU
  clock at 0.060%.
- **Ruby link and network bandwidth, and every Ruby/CHI latency, are not
  subject to silent tick quantisation** — the former are `Param.Int` in
  bytes/cycle, the latter `Param.Cycles`.
- **The fifteen in-flight runs realize their pre-registered bandwidths
  exactly** and will pass G4.
- **The guard now reports rounding error in both directions, and does not
  change a single computed value** — 0 differing lines in 42,789.

Not licensed, and to be stated wherever this is relied on:

- **The fix does not protect anything until `gem5.opt` is rebuilt.**
  `src/python/` is marshalled into the binary. Until a rebuild, the guard is
  live only under `M5_OVERRIDE_PY_SOURCE=true`.
- **This audits the configuration path these runs instantiate, not all of
  gem5.** A different `--mem-type` (`DRAMInterface` and friends), Garnet
  instead of `SimpleNetwork`, or an FS configuration would introduce
  `Latency`, `Frequency` and `NetworkBandwidth` parameters not exercised here.
  The enumeration is complete for what appears in these `config.ini` files and
  makes no claim beyond that.
- **The guard's tolerance is applied in tick space, not in the requested
  domain.** For a bandwidth the two relative errors differ (9.9512% against
  9.0505% here). Nothing in this audit turns on the difference, but a parameter
  falling between the two thresholds would be reported or not depending on it.
- **This audit says nothing about whether the realized values are the right
  physics.** That 500 GB/s is exactly realized as 2 ticks/byte does not make it
  a CXL link, and `H1BW_MULTICORE_OUTCOME`'s finding that `SimpleMemory` with
  `latency_var=0` models no link at all is untouched by anything here.
- **The 0.5 ns Ruby-cycle grid and the integer-bytes-per-cycle link grid are
  real coarseness**, merely not *silent* coarseness. A successor wanting
  sub-nanosecond CHI latency resolution would have to raise `--ruby-clock`, and
  that is a modelling decision, not a rounding bug.

## Reproducing this

```
experiments/asplos/prove_ticks_guard_inert.sh          # the inertness proof
experiments/asplos/enumerate_quantized_params.sh       # the audit table
```

The second applies its `SimObject.print_ini` hook on entry and reverts it on
exit, so the tree is left carrying only the `ticks.py` hunk. Both are
config-generation only, kill each gem5 as soon as `config.ini` exists, and
write nothing under `gem5/logs/`.

Use the scripts rather than an ad-hoc command line. One incident to record:
a hand-typed one-off verification of the warning count backgrounded its whole
`&&` chain, so its scratch variable was unset and its cleanup `kill` missed;
three throwaway gem5 processes were left running against `/tmp/warncount.*` and
were killed by PID after confirming each one's `--outdir` was under `/tmp`. The
fifteen campaign processes were never signalled, remained in their original
three process groups throughout, and were all fifteen present and running
afterwards. The scripts do this correctly via `setsid` plus a process-group
kill in an `EXIT` trap, which is why they should be used.
