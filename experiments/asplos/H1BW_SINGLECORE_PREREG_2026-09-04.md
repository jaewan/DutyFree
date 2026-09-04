# Pre-registration — single-core H1 bandwidth and LLC footprint, certified replacement for `tab:h1bw`, 2026-09-04

## Why this campaign exists

`Appendix.tex`'s `tab:h1bw` publishes twelve numbers — three arms at two MSHR
depths, bandwidth and LLC data-array writes — from a single-core 16 MiB stream
against a 5 MiB LLC. `H1BW_ARM_IDENTITY_2026-09-04.md` established two things
about that table:

1. **Its artifacts do not exist.** All twelve figures survive only as a
   4,609-byte hand-written `REPORT.md` inside
   `experiments/asplos/preserved/gem5_streaming.tar.gz`. There is no
   `stats.txt`, no `config.ini`, no per-run JSON. Its runner is named at
   `gem5/scripts/run_se.sh:16-17` as `knee_sweep.sh` and **that file does not
   exist anywhere on this host**; neither does the binary
   (`benchmarks/e2e/hash_join_gem5se/build/cxl_join_bench.gem5se`) that
   `run_se.sh` itself names. `A1_PROVENANCE_LEDGER_2026-08-28.md` carries this
   as **F3, open**.
2. **Its third column was mislabelled `WC`, and no WC arm was ever
   constructible.** `gem5/src/arch/x86/pagetable_walker.cc:359-390` derives
   exactly `streaming` (PAT slot 6) and `uncacheable` from the PAT bits;
   there is no write-combining memory type in this model. The arm is
   `--policy stream` with that core's four prefetchers **not instantiated**,
   and it is now labelled `pf-off` in the paper.

This is the same treatment already applied to the multi-core bandwidth triple:
where a figure has no artifacts, it is **superseded by a pre-registered
measurement rather than defended**. `H1BW_MULTICORE_PREREG_2026-09-03.md` did
that for the 4- and 8-core aggregate rows. This document does it for the
single-core sweep.

**The question this campaign answers: on a binary that exists, with artifacts
that are retained, does a single-core MSHR sweep of `{wb, h2, pf-off}` over a
16 MiB stream against a 5 MiB LLC reproduce the ordering, the
MSHR-sensitivity and the footprint separation that `tab:h1bw` reports — and
does it reproduce its twelve magnitudes?**

It is registered as a **replacement** campaign, not a reproduction. The
archive is not reproducible: its runner, its binary and its per-run counters
are all gone, and its arm was mislabelled. **Magnitude disagreement is an
expected and acceptable outcome**, and §"What confirms and what refutes"
decides the interpretation of every case in advance.

## Two things this design gets for free, stated before launch

### 1. It is not exposed to the window-stagger limitation

`AGGBW_VALIDITY_2026-09-03.md` §Q2 is the limitation that bounds the
multi-core campaign. There is no cross-process barrier in gem5 SE mode
(`AGGBW_WINDOW_PREREG_2026-09-03.md` §"The barrier both prior documents
specify cannot be built": `MAP_SHARED|MAP_ANONYMOUS` writes are not
propagated, `shmget`/`shmat`/`memfd_create` all resolve to
`unimplementedFunc`), so the N per-instance measurement windows in a
multi-core cell have no enforced phase relationship. `agg_bw_sum` — the sum
over instances of each instance's own bytes over its own self-timed window —
is therefore only an upper end of a defensible interval `[R_union,
agg_bw_sum]`, and `AGGBW_VALIDITY` measures that interval at **2.4–16.7%**
wide, arm-dependently, having had to *reconstruct* the phases from per-CPU
`numCycles` under an assumption about epilogue cost that is validated to
~10 us but not proven.

**This campaign has one instance. There is no second window for it to have a
phase relationship with.** `bandwidth_gbps` = `fact_bytes * reps / total_sec`
is the rate over the one measured window, full stop. There is no union, no
intersection, no `R_disjoint` floor, no reconstruction and no
constant-epilogue assumption. **This campaign is explicitly not exposed to the
`AGGBW_VALIDITY` §Q2 limitation, and no bandwidth figure it reports is bounded
by an interval on that account.** The bandwidth figure is unambiguous.

Two consequences worth stating so they are not later claimed as more than they
are. First, this removes a *metric* ambiguity; it does not remove the
LLC-residency confound of `AGGBW_VALIDITY` §Q1/finding 4, which is a
*benchmark geometry* property and is discussed in §"What this campaign cannot
settle". Second, single-core is a different operating point, not a better
measurement of the multi-core one: nothing here licenses a multi-core number.

### 2. The counters and the bandwidth describe the same interval

**Achieved.** `AGGBW_WINDOW_PREREG_2026-09-03.md` §1 specifies
`m5_dump_reset_stats` bracketing of `run_stream()`'s measured loop, and
records that ops `0x40` (`M5OP_RESET_STATS`), `0x41` (`M5OP_DUMP_STATS`) and
`0x42` (`M5OP_DUMP_RESET_STATS`) are already decoded by the binary in use and
that `run_join()` already uses two of them
(`cxl_join_bench.cpp:211,218` and `:1407,1411`). That is correct, and it has
been adopted here **with no gem5 rebuild**: the ops are already in
`gem5.opt` `cb290444`, and `gem5/src/` was not touched.

It did require compiling the *benchmark*, which is a separate binary from the
simulator. That was done **to a separate name**:

| | path | sha256 |
|---|---|---|
| unchanged, published | `benchmarks/e2e/hash_join/build/cxl_join_bench.gem5` | `cac9e27ab42448a89c7c51e93749107357795ced6456babf2f51bfe625140f93` |
| **this campaign** | `benchmarks/e2e/hash_join/build/cxl_join_bench.gem5wbrk` | `2b9d67320ff86999b5e8e3d2cb98479043c3da62bbaa6135304a53ff48d9efad` |

`cac9e27a` is the provenance of all 24 `h1bw_mc_*` cells and of the
`h1bw_multicore`, `h1bw_cxlbw` and `h1bw_slice_bracket` campaigns.
**Overwriting a binary that published magnitudes are attributed to is exactly
the `F13` defect `BUILD_PROVENANCE.md` was written to stop**, and the
`Makefile` already carries this convention twice, for the same stated reason
(the `w7` and `gem5fs` targets, and the recorded pre-W7 hashes above them). A
new `gem5-window` target was added alongside them. `cac9e27a` was verified
byte-unchanged after the build.

The source change is three insertions in
`benchmarks/e2e/hash_join/src/cxl_join_bench.cpp`: a `bool window_brackets`
in `Config` defaulting **false**, a `--window-brackets` flag, and the bracket
itself in `run_stream()`, implemented exactly as `AGGBW_WINDOW_PREREG` §1
specifies including its `AGGBW_WINDOW_{OPEN,CLOSE}` marker text, so that
campaign's analyzer can consume it unchanged. With the flag off the code path
is the unbracketed one, so `cxl_join_bench.gem5` rebuilt from this source
still reproduces the runs that predate the option. **No `*_PREREG_*.md` other
than this file was edited, and `run_h1bw_multicore.sh` was not edited** — a
concurrent worker holds a pending patch to it (`BUILD_PROVENANCE.md` §5b).

**Validated before this document was frozen**, by a pilot at 2 MiB (a
throwaway apparatus check under `/tmp`, not a measurement, and not under
`gem5/logs/`):

- `stats.txt` contains exactly **3** `Begin Simulation Statistics` sections,
  i.e. `2N + 1` at `N = 1`;
- `console.log` contains exactly one `AGGBW_WINDOW_OPEN` and one
  `AGGBW_WINDOW_CLOSE`;
- section 1 (0-indexed) is the measured window: its `simTicks` is
  244,118,704 = 0.000244119 s against the guest's own reported
  `seconds` of 0.000243683 — **agreement to 0.18%**;
- the sections' counters are per-section, so section 1's
  `system.ruby.hnf.cntrl.cache.numDataArrayWrites` = 1,480 is a **windowed**
  LLC data-array write count, against 46,144 for the whole program.

**This is therefore the first campaign in this project whose LLC-write column
and whose bandwidth describe the same interval.** It is what makes the
footprint column a measurement of the measured pass rather than of the
program, and it is why §"Pre-declared outcomes" can state a *sharp*
prediction on that column where the archive could only state a
whole-program one.

The whole-program totals are also retained (they are the sum over the three
sections), because the archive's own footprint column is whole-program — its
WB figure of 529,330 is 2.02x the stream's 262,144 lines, i.e. a warm pass
plus a measured pass — and the archive comparison of §"Confirming or refuting
the archive's twelve numbers" must be made on the comparable quantity.

## Configuration

Frozen. Derived from three sources that do not agree, so every disagreement is
reconciled explicitly below rather than by silently preferring one.

| parameter | value | authority |
|---|---|---|
| CPU | O3CPU, 1 core, requested 1.9 GHz | `run_se.sh:31`, `run_h1bw_multicore.sh:148`, `tab:gem5cfg` |
| L1-I / L1-D | 32 KiB 8-way / 48 KiB 12-way | all three agree |
| L1 MSHRs (`L1_MSHR`) | **16 and 48 — the swept variable** | `tab:h1bw` rows; `tab:gem5cfg` states 16 |
| L1 replacement TBEs (`L1_REPL`) | **48 at both points — set explicitly** | this campaign; see §"L1_REPL" |
| L2 (private) | 2 MiB 16-way, `L2_MSHR` 48, `L2_REPL` 32 (defaults) | `CHI_config_8592.py:364,367`; `tab:gem5cfg` "48 MSHRs" |
| LLC / HNF | 5 MiB 20-way, non-inclusive victim, `HNF_MSHR` 32 (default) | `CHI_config_8592.py:435`; `tab:gem5cfg` "32 MSHRs" |
| LLC slices / directories | `--num-l3caches=1`, `--num-dirs=1` | `tab:gem5cfg` "1 LLC slice, 1 directory"; `run_se.sh:30` at `N=1` |
| Snoop filter | **NULL / infinite** (`HNF_SF_FINITE` unset) | `CHI_config_8592.py:411,866-872`; see reconciliation 5 |
| Line size | 64 B | default |
| Prefetchers, `wb` and `h2` | L1D Stride(4) + DCPT; L2 Stride(4) + Tagged | `CHI_config_8592.py:703-721`; see reconciliation 2 |
| `PF_PAGE` | 4KiB | `run_se.sh:24`, and the default |
| Coherence | CHI (Ruby), `--topology=Pt2Pt` | all three agree |
| Memory | `SimpleMemory`, 256 GiB DDR + 128 GiB CXL, DRAM 98 ns / CXL 203 ns, `latency_var=0` | all three agree |
| Memory bandwidth | **no cap requested**; realized 2 ticks/byte = 500 GB/s on both ranges | SimObject default, quantised by `m5.ticks.fromSeconds` |
| Stream | **16 MiB**, `--fact-bytes 16m`, `--fact-node 1` | `tab:h1bw` caption, `REPORT.md` §1 heading; see reconciliation 1 |
| `ALL_CXL` | 1 | `run_se.sh:41-45`, `run_h1bw_multicore.sh:142` |
| `--hot-node` | 0 (parsed, **inert** on this path) | `AGGBW_VALIDITY` §"Two knobs are parsed and never applied" |
| `--threads` | 1 (parsed, **inert**) | same |
| warmups / reps | **2 / 8** | this campaign; see §"warmups and reps" |
| `RUBY_RANDOMIZATION` | **unset** | this campaign; see reconciliation 4 |
| `SEED` | unset (gem5 default 5489) | — |
| gem5 | `build_Intel_8592/gem5.opt`, sha256 `cb2904444d5c5c4d31d9d8f07295209283d29e294ef1d885d789442d98e7bbe0`, tag `build-cb290444` | §"Binary and provenance" |
| benchmark | `build/cxl_join_bench.gem5wbrk`, sha256 `2b9d67320ff86999b5e8e3d2cb98479043c3da62bbaa6135304a53ff48d9efad` | §2 above |

The invocation is `experiments/asplos/run_h1bw_singlecore.sh`, committed before
launch. It is a sibling of `run_h1bw_multicore.sh` and copies rather than
refactors it, so that runner continues to certify its own campaign untouched.

### Reconciling the three sources

`run_se.sh:41-45` is the only committed definition of these three arms, and
`experiments/asplos/run_h1bw_multicore.sh` is the certified sibling harness.
Neither is the sweep, and they disagree with each other and with
`tab:gem5cfg` in five places. Each is resolved and the choice recorded.

**1. Stream size: `run_se.sh` says 1 GiB; the table says 16 MiB. The table
wins, and `run_se.sh` is not the sweep's runner.** `run_se.sh:27` passes
`--fact-bytes 1g` and `:16-17` says in terms: "Frozen config only
(`L1_MSHR=16`, PF 4/8, 4KiB). The one-off MSHR/prefetcher knee sweep lives in
a separate script (`knee_sweep.sh`), not here." So `run_se.sh` is *by its own
statement* not the runner for `tab:h1bw`; it is the runner for a different,
1 GiB, fixed-MSHR configuration, and `knee_sweep.sh` is gone. What
`run_se.sh:41-45` authoritatively supplies is the **arm construction** — three
arms, `wb` / `stream` / `stream`+`PF_OFF_CORES`, at `ALL_CXL=1`, one CPU, one
LLC slice — and nothing else. 16 MiB comes from `tab:h1bw`'s own caption
("single core, 16 MiB stream $>$ LLC"), from `REPORT.md` §1's heading, and it
is corroborated arithmetically: 16 MiB is 262,144 lines and the archive's WB
footprint of 529,330 is 2.02x that, which is a warm pass plus a measured pass
and could not be produced by a 1 GiB stream. `tab:gem5cfg`'s "Stream
footprint 16 MiB (H1) $>$ LLC" row agrees.

**2. L2 prefetch degree: `run_se.sh` says 8; the multi-core campaign and
`tab:gem5cfg` say 4. Four is used.** `run_se.sh:24` sets `PF_DEGREE_L1=4
PF_DEGREE_L2=8`; `run_h1bw_multicore.sh` sets neither, so both default to 4
(`CHI_config_8592.py:696-698`). `tab:gem5cfg`'s `Prefetch` row reads
"L1/L2 Stride(4) + DCPT". Choosing 4 makes this campaign consistent with the
model the paper discloses and with the certified multi-core cells. **Recorded
as a departure from `run_se.sh`, and pre-registered as a candidate explanation
if the H2 magnitudes disagree with the archive**, because L2 prefetch depth is
one of the two knobs that set how far the prefetcher runs ahead. Note
separately, and not fixed here, that `tab:gem5cfg`'s row is wrong in a second
way already logged by `H1BW_ARM_IDENTITY`: the L2 pair is Stride + **Tagged**,
not Stride + DCPT. That is a paper-text defect in a row this campaign does not
own; it is handed back in §"Handbacks", not edited.

**3. Benchmark binary: `run_se.sh`'s does not exist.** It names
`benchmarks/e2e/hash_join_gem5se/build/cxl_join_bench.gem5se`; that directory
is **absent from this host**. `run_h1bw_multicore.sh`'s
`hash_join/build/cxl_join_bench.gem5` exists and is the certified sibling's
binary. This campaign uses the `gem5wbrk` build of that same source (§2). This
is an unavoidable departure and it is the single largest reason the archive's
magnitudes may not reproduce: the archive ran a different program, compiled
from a tree that is not identified by any record.

**4. `RUBY_RANDOMIZATION`: `run_se.sh` sets it; the multi-core campaign does
not. Left unset.** `se.py:302-309` documents its purpose as breaking
"deterministic timing races that cause **per-CPU BW asymmetry**". With one CPU
there is no second CPU to be asymmetric with, so the knob addresses a
condition this campaign cannot exhibit. Leaving it unset keeps the cells
bit-reproducible, which is what makes a re-run of any cell a check rather than
a new sample. Recorded as a departure from `run_se.sh`.

**5. Snoop filter: `tab:gem5cfg` lists 65,536 entries; this campaign runs with
the directory unbounded.** `CHI_config_8592.py:411,866-872` instantiate a
finite SF only when `HNF_SF_FINITE=1`; neither `run_se.sh` nor
`run_h1bw_multicore.sh` sets it, so `sf = NULL` and `sf_finite = False`.
`tab:gem5cfg`'s own row is annotated "finite-SF runs", and those are the H3
runs of `tab:h3sf`, not `tab:h1bw`. **No disagreement in fact; the table's row
is scoped and this campaign is out of its scope.** The realized value is read
back from `config.ini` and recorded.

### `L1_REPL` — the decision, and why 48

`CHI_config_8592.py:313-322`:

```
:313   # Some reasonable default TBE params (env L1_MSHR, unset=16)
:314   self.number_of_TBEs = int(os.environ.get("L1_MSHR", 16))
:315   # Replacement-path depth (env L1_REPL). Default 16 so an unset
:316   # environment reproduces today's behavior exactly. Sweeping L1_MSHR
:317   # alone starves this path relative to the request path (64 vs 16),
:318   # and the STREAMING attribute has to survive the eviction path
:319   # (cache_entry.isStreaming -> TBE -> WriteEvictFull) to be honoured
:320   # at the HNF -- so this is a candidate cause of H2 fill-suppression
:321   # degrading at high L1_MSHR.
:322   self.number_of_repl_TBEs = int(os.environ.get("L1_REPL", 16))
```

This campaign sweeps `L1_MSHR` across a 3x range (16 to 48), which is exactly
the situation the comment names. `H1BW_MULTICORE_PREREG_2026-09-03.md` and
`AGGBW_WINDOW_PREREG_2026-09-03.md` both left it at the default and recorded it
as "a live confound, recorded not endorsed". Leaving it unset here would be
worse than in those campaigns, because they held `L1_MSHR` fixed at 48 while
this one moves it: at 16 MSHRs the default `L1_REPL=16` is matched to the
request path, and at 48 MSHRs it is starved 3:1. **Any difference in H2
engagement between the two MSHR points would then confound MSHR depth with
replacement-path starvation, and the sweep is the whole claim.**

**Decision: `L1_REPL = 48` at both MSHR points.**

Three reasons, in order:

1. **It keeps the sweep a one-variable sweep.** `L1_REPL` is held constant, so
   the only thing that differs between the 16- and 48-MSHR rows is the request
   MSHR pool. The alternative of tracking `L1_REPL = L1_MSHR` would move two
   coupled knobs and make "MSHR depth" ambiguous between them.
2. **48 >= max(`L1_MSHR`), so the replacement path is never the narrower of
   the two at either point.** It therefore cannot be the binding constraint in
   either cell, and no cell's result can be a replacement-path artifact. A
   fixed value *below* the maximum (e.g. the default 16) would have the
   replacement path bind in one cell and not the other, which is the confound.
3. **The eviction path is where H2 lives.** `number_of_repl_TBEs` sizes the
   pool a clean eviction must obtain to reach the HNF as a `WriteEvictFull`
   carrying `cache_entry.isStreaming`, and the HNF bypass is taken on exactly
   that transaction (`CHI-cache-actions.sm:291`,
   `H2_BYPASS_FIX_OUTCOME_2026-09-03.md` §1). Starving that pool suppresses
   the mechanism under test in a way that looks like the mechanism not
   working.

**This is a disclosed departure from the archive**, whose 48-MSHR row was
presumably taken at the default 16 (nothing records it, so this is an
inference from the default, and it is flagged as such). It is registered here
as a candidate explanation for a 48-MSHR magnitude disagreement, and
**diagnostic cell set D exists to test it** (§"Cells").

### `warmups` and `reps` — the decision, and why 2 and 8

`run_h1bw_multicore.sh` uses `--warmups 1 --reps 1`. The archive does not
record its reps at all. This campaign uses **`--warmups 2 --reps 8`**.

**Why more than one rep.** `AGGBW_VALIDITY_2026-09-03.md` §"What this licenses"
lists as not licensed: "`n = 1` per cell, `cov` identically 0, no seed
replication. **No effect below roughly 10% is interpretable.**" The claims
this table is cited for sit below that: `tab:h1bw`'s 48-MSHR H2-over-WB margin
is **+7.0%** and its 16-MSHR margin +15.6%. A +7% margin with no error bar is
not interpretable, and the current caption says so ("Single runs, no
interval"). Eight reps give eight samples and a `cov`, at a cost of ~9% of
simulated ticks: the pilot puts the measured pass at 244.1 Mticks of a
21.90 Gtick program, i.e. **1.11%**, so nine extra passes add ~10%.

**Why an even total.** `AGGBW_VALIDITY` §"Health findings" found nine of 120
instances reporting a non-zero `checksum` where warm and measured passes over
identical unmodified data must XOR to zero, recommended that
"`checksum != 0` in `stream-smoke` with `warmups + reps == 2` should be a
fail-closed condition in any successor analyzer", and recorded that "it is not
one today". It is one here (G11). The gate needs an **even** pass count, because
the checksum is an XOR over `warmups + reps` passes and an odd count leaves the
single-pass value rather than zero. `warmups=2, reps=8` gives 10, even.
`warmups=1, reps=8` would give 9 and would silently retire the gate, which is
the wrong trade.

**Consequence for the footprint column, and how it is handled.** The measured
window now contains eight passes, so its LLC data-array write count is eight
passes' worth. It is reported **per measured pass** (divided by `reps`), which
is exact and is the quantity comparable to a per-pass expectation of 262,144
lines. The whole-program column is reported unnormalised, because that is what
the archive's column is.

## Binary and provenance

`gem5/build_Intel_8592/gem5.opt`, sha256
`cb2904444d5c5c4d31d9d8f07295209283d29e294ef1d885d789442d98e7bbe0`, tag
`build-cb290444`, mtime 2026-09-04 12:47:48. **Not rebuilt; `gem5/src/` not
touched.** The runner refuses to start if the hash differs
(`run_h1bw_singlecore.sh`, `GEM5_SHA_EXPECT`).

This binary is required, not merely convenient. It carries
`b9c8714c93`, "CHI: carry `isStreaming` across the request retry path", the
fix for the defect `H2_BYPASS_COLLAPSE_2026-09-03.md` diagnosed: on
`cfd37207` a retried CHI request arrived at the home node with `isStreaming`
reset to its `false` field default, so the HNF allocated a line H2 would have
declined. Without the fix **the H2 arm silently under-engages** —
`H2_BYPASS_FIX_OUTCOME_2026-09-03.md` §4 measures the one-slice H2 cell moving
from 17,197 bypasses and 1.8% engagement to 853,853 and 97.6%. A single-slice
configuration is the high-retry regime (65% of writes retry there), and this
campaign runs one slice, so it is the configuration in which the defect bites
hardest.

Following `BUILD_PROVENANCE.md`, and its §4 finding in particular:

- **`configs/` is read from the working tree at run time**, not compiled into
  `gem5.opt`, so a cell's behaviour is a function of two states and
  `gem5_sha256` records only one. The runner therefore records
  `configs_git_describe` **taken at launch** (correct for a run-time input,
  per §4) alongside `gem5_git_describe` and `gem5_git_head` **copied from the
  build** (§5b). The config files that matter here are
  `configs/deprecated/example/se.py` and
  `configs/ruby/{Ruby.py,CHI_config_8592.py}`; all three are read, none is
  modified by this campaign, and `CXL_MEM_BW` is left unset so the `Ruby.py`
  per-range bandwidth path is inert.
- **§5b's fail-closed check against `<build-dir>/BUILD_PROVENANCE.json` cannot
  be applied.** No such file exists: the current binary was built by hand at
  12:47 and the build wrapper that writes it (`fa27f665db`,
  `gem5/scripts/build_gem5.sh`) landed *after* it. The runner records
  `gem5_build_provenance_json_present: false` rather than passing silently,
  and substitutes an equality test against the sha256 this document names.
  That substitution is stronger **here** — because this document names the
  hash — and is not a general substitute for the manifest.
- The five-commit delta `cfd37207..cb290444` is measured inert on these
  workloads except through `isStreaming` on retried requests
  (`BUILD_PROVENANCE.md` §"the delta is five commits, and is measured inert";
  the `wb` control came back bit-identical on all 11,166 simulated
  quantities). The flush-behind oracle op `0x57` is compiled in and the
  benchmark does contain a call site, but it sits behind `policy == "fbo"` and
  **no cell here passes `--policy fbo`**.
- Expect **`rounding error > tolerance` warnings** in `console.log`, from
  `a5f366456e`'s `abs()` guard on `SimpleMemory.bandwidth` tick quantization.
  These are new relative to the pre-fix cells, are **warning-only**
  (`config.ini` byte-identical, `wb` bit-identical), and **must not be treated
  as a gate failure**. The analyzer counts them and prints the count.

Nothing under `gem5/logs/` is read, written or enumerated by this campaign.
Cells land in `logs/se_chi_h1bw_sc/` at the repository root. That is a
departure from the sibling runner's `OUTROOT` and it is deliberate: the brief
forbids modifying anything under `gem5/logs/`, and three
`h1bw_mc_*_4c_l3x1_*fix` simulations were the reason. (Those three had in fact
exited — 14:11, 14:16 and 14:17, all `"exit":0` — before this campaign began,
and the host is idle. The separation is kept anyway, because a constraint that
is honoured only when it is costless is not a constraint.)

## Arms

Three. There is no fourth, and there is no WC arm, because none can be built.

| arm | `--policy` | prefetchers | mechanism |
|---|---|---|---|
| `wb` | `wb` | instantiated | the control: ordinary write-back, allocating |
| `h2` | `stream` | instantiated | non-allocating at the LLC via m5 op `0x55` |
| `pf-off` | `stream` | **not instantiated** (`PF_OFF_CORES=0`) | the same non-allocating policy with the prefetch path removed |

`h2` and `pf-off` **differ only in prefetcher instantiation**; their
`--policy` is identical. `PF_OFF_CORES=0` sets `l1Dprefetcher_type = None` and
passes `pf_type = None` to `addPrivL2Cache` for cpu 0
(`CHI_config_8592.py:723-751`), so the L1D pair (Stride(4) + DCPT) and the L2
pair (Stride(4) + Tagged) are **absent from the config**, not disabled at
runtime. The realized check is that `config.ini` carries zero sections whose
name contains `prefetcher` (G12), which is how the multi-core campaign
confirmed it (76/152 sections for `wb`/`h2` against exactly 0 for `pfoff`).

**`pf-off` is not write-combining, and this is why the arm is renamed.** The
model has no write-combining memory type: `pagetable_walker.cc:359-390`
derives `streaming` and `uncacheable` and nothing else, and
`grep -rIl 'write.combin\|WriteCombin\|WRITE_COMBIN'` returns nothing in
`src/mem/ruby/`, in `configs/`, or in the walker. The benchmark has no PAT-WC
policy to select either. The mislabel entered because `run_se.sh:45` *names
the output directory* `wc` while building the arm as `stream` +
`PF_OFF_CORES`. Restated here so it is not re-inherited.

## Cells

**Primary: six cells** = 3 arms x `L1_MSHR` in {16, 48}, all at
`L1_REPL = 48`. These are the six cells that replace `tab:h1bw`'s twelve
numbers.

**Diagnostic set D: three cells** = 3 arms at `L1_MSHR = 48`,
**`L1_REPL = 16`** — the archive's presumed replacement-path depth, at the one
MSHR point where the default departs from the request path. Set D exists so
that a 48-MSHR magnitude disagreement with the archive can be **attributed to,
or cleared of, replacement-path starvation**, which is otherwise an
uncontrolled difference between this campaign and the archive. It is a
diagnostic: **it contributes no number to `tab:h1bw`** and no certified
verdict, and it is reported separately. It is not run at 16 MSHRs because
there `L1_REPL = 16` equals the request path and the departure is a widening
of a pool that was already matched, which is predicted inert and is not worth
a cell.

Nine cells, all launched concurrently. All are single-core, so all nine are
single-threaded gem5 processes.

## Metrics

Two primary, per cell, both from the run's own artifacts and never from
`MANIFEST.json`:

| metric | definition | role |
|---|---|---|
| `bandwidth_gbps` | `fact_bytes * reps / total_sec`, from the instance's own JSON | the bandwidth column of `tab:h1bw`. Unambiguous: one instance, one window, no stagger |
| `llc_fills_window_per_pass` | section-1 `numDataArrayWrites` / `reps` | the footprint column, **windowed**, per measured pass |

and, for the archive comparison only, the whole-program `llc_fills_total` =
the sum over all three sections, which is the quantity the archive's column
is.

Also recorded per cell:

- `cov` across the 8 reps, and the min/max sample, so a 7% margin has an error
  bar for the first time in this family;
- realized `L1_MSHR` and `L1_REPL`, read back from `config.ini` — the swept
  knobs are gated, not trusted (G8);
- realized LLC bytes, slice count, associativity, CXL/DRAM latency,
  `latency_var`, `mem_type`, and both ranges' `bandwidth` in ticks/byte;
- HNF engagement: `streamingHnfFillBypasses`, `WriteEvictFull`/`WriteBackFull`
  RU->{I,UC,UD} transition counts, the derived clean-eviction residue and
  `E_clean`, and the HNF write-request retry fraction — all both windowed and
  whole-program;
- in-window `mem_ctrls1.bytesRead`/`bytesWritten` and controller bytes per
  useful byte, and the request-type decomposition
  (`ReadShared.I.RU` against `ReadUnique_PoC.I.RU`) that `AGGBW_VALIDITY` §Q1
  used to bound the CXL-served share. At one instance and with a windowed
  section this is a **measurement** rather than a whole-program bound;
- HNF read transaction latency and the `concurrency x 64 B / latency`
  decomposition, on windowed counters;
- `IPC` (the archive's third column, retained for comparison);
- `checksum`, `free(): invalid size` count, and the
  `rounding error > tolerance` count.

## Pre-declared outcomes

Encoded as module constants in `analyze_h1bw_singlecore.py` and checked
mechanically, so the result confirms or refutes them rather than being
narrated afterwards. Changing a threshold after seeing data is visible in git
(the W1 rule).

### Structural predictions — the sharp tests

These are mechanism predictions, they are the reason the archive's ordering is
believed, and they do not depend on any magnitude reproducing.

| # | prediction | mechanism | archive's value |
|---|---|---|---|
| **S1** | `pf-off` bandwidth is MSHR-insensitive: `\|bw(48) - bw(16)\| / bw(16) <= 0.10` | no prefetcher, so concurrency is set by how fast an O3 core generates demand misses, and that sits below even the 16-MSHR pool. 4.60 GB/s at 203 ns and 64 B/line is 14.6 lines in flight against a pool of 16 | 4.60 / 4.60, exactly flat |
| **S2** | `pf-off` windowed footprint is MSHR-insensitive to within 2% | no prefetch fills to add; the count is fixed by demand traffic and writebacks | 289,695 -> 289,698, 3 lines in 290,000 |
| **S3** | `h2` windowed footprint **rises** with MSHR depth | a deeper pool lets the prefetcher run further ahead, and a prefetched line arrives at the HNF **without** the STREAMING tag the demand path would have given it (`H2_BYPASS_FIX_OUTCOME` §4) | 300,238 -> 353,739, **+17.8%** |
| **S4** | `wb` footprint is MSHR-insensitive to within 5% | already saturated: every line of every pass is filled at either depth | 529,330 -> 529,309, -21 |
| **S5** | `h2` footprint < `wb` footprint at **both** depths | the fill suppression that is the mechanism under test | 0.57x and 0.67x |
| **S6** | ordering at 48 MSHRs: `h2 >= wb > pf-off` | the paper's H1 claim | 5.82 >= 5.44 > 4.60 |
| **S7** | at 16 MSHRs the ordering is **not** pre-declared | the archive has `wb` (4.24) **below** `pf-off` (4.60) at this depth. Both signs are admissible in advance | `h2 > pf-off > wb` |

**S7 is registered deliberately and is the second defect this campaign exists
not to reintroduce.** `H1BW_ARM_IDENTITY_2026-09-04.md` §"Question 3" records
that the appendix quoted a WB-over-`pf-off` ratio of 1.18x from the 48-MSHR
row without noting that the 16-MSHR row of the same two rows reads
**0.922x** — the sign flips inside the sweep the caption insists is the claim.
**This campaign commits in advance to reporting both MSHR points for every
arm, and forbids quoting a single pooled WB-over-`pf-off` ratio, an `n`, a
mean or a range over the two points.** They are two operating points of one
sweep, not two samples of one quantity. The analyzer prints both and prints no
pooled statistic; if the sign flips again, that is a result and it is reported
as one.

### The windowed footprint prediction — sharper than anything the archive could state

Bracketing buys a prediction the archive's whole-program column cannot make.
One measured pass over 16 MiB reads exactly **262,144 lines**. The HNF is a
non-inclusive victim cache with `alloc_on_read*` all false
(`CHI_config_8592.py:298-300`), so a read never allocates and the only
data-array writes come from evictions. Per measured pass:

| arm | windowed fills per pass, as a fraction of 262,144 | why |
|---|---|---|
| `wb` | **0.85–1.15** | every line read is filled into L1/L2 and evicted clean, and `wb` allocates on clean eviction |
| `h2` | **0.02–0.35** | clean evictions carry the STREAMING tag and are declined; what remains is the untagged-prefetch tail and the constant residue |
| `pf-off` | **0.02–0.20** | the same, with no prefetch tail at all, so it should sit at or below `h2` |

If `wb` comes in outside 0.85–1.15, the fill accounting above is wrong and the
footprint column must be re-derived before it is published. That is the
outcome this prediction is registered to expose.

### Magnitude predictions

Wide, because the archive's harness is gone and four inputs differ (§"Reconciling
the three sources"). Bands are stated as absolute GB/s.

| arm | 16 MSHRs | 48 MSHRs |
|---|---|---|
| `wb` | 3.0–5.5 | 4.0–11.0 |
| `h2` | 3.0–5.5 | 4.0–11.0 |
| `pf-off` | 2.0–5.2 | 2.0–5.2 |

The 16-MSHR bands are anchored on the concurrency ceiling the archive itself
names: 16 lines x 64 B / 203 ns = **5.04 GB/s**, and the archive's three
16-MSHR readings (4.24 / 4.90 / 4.60) all sit just under it. The 48-MSHR upper
bound of 11.0 is the HNF's own pool: 32 x 64 B / ~203 ns = 10.1 GB/s, plus
margin. `pf-off` gets the same band at both depths by S1.

### The one-slice hazard, declared in advance

`H2_BYPASS_FIX_OUTCOME_2026-09-03.md` §5 is the reason this is stated before
launch rather than discovered after. At **one LLC slice with four cores**, with
H2 fully engaged, the H2-over-WB ratio *collapsed* from 1.250x to 1.070x and
**the arm ordering inverted outright** to `pf-off > h2 > wb`, because the
binding constraint at one slice is the 32-entry HNF transaction-buffer pool
rather than LLC fill traffic — 65% of writes retried and HNF occupancy was
82.7%.

`tab:gem5cfg` specifies one slice, so this campaign runs one slice. **With one
core rather than four, the HNF pool faces roughly a quarter of the demand**, so
the regime is expected to be different: predicted HNF write-retry fraction
**below 20%** and predicted HNF TBE occupancy **below 60%**. Both are recorded
as primary observables rather than gates.

**If the retry fraction comes in above 50% and the ordering inverts, the
interpretation is fixed in advance: the cell is buffer-capped, not
fill-capped, S6 is refuted for a reason that is about the home node rather
than about H2, and `tab:h1bw` must then report the sweep with that stated
rather than report an ordering.** That is a publishable negative and it is not
a void.

## Gates

Fail-closed. A cell failing any gate is printed **VOID**, contributes no
number to the verdict and appears in the paper table not at all. Enforced by
`experiments/asplos/analyze_h1bw_singlecore.py`. `analyze_h1bw_bracket.py` and
`analyze_h1bw_multicore.py` are **left untouched** so they keep certifying the
completed campaigns.

- **G1** — the instance reports `status: "ok"`.
- **G2** — realized instance count is exactly 1, and realized workload count
  is exactly 1.
- **G3** — realized LLC is exactly `1 x 5 MiB` at associativity 20, over
  exactly one HNF slice, counted from `config.ini`. gem5 collapses a length-1
  `SimObjectVector` to an unindexed name, so the section is
  `system.ruby.hnf`, not `system.ruby.hnf0`; both spellings are matched.
- **G4** — realized `system.mem_ctrls1.bandwidth` and
  `system.mem_ctrls0.bandwidth` are both exactly 2 ticks/byte; realized CXL
  latency 203 ns, DRAM latency 98 ns, `latency_var` 0, `mem_type`
  `SimpleMemory`. Read back from `config.ini`, never from `MANIFEST.json`.
- **G5** — the declared policy measurably engaged. Re-derived for this binary;
  see §"G5 re-derived" below. A `wb` arm must record **exactly zero**
  bypasses.
- **G6** — `stats.txt` contains exactly **3** sections and `console.log`
  contains exactly one `AGGBW_WINDOW_OPEN` and one `AGGBW_WINDOW_CLOSE`. Any
  other count means the bracketing did not fire and the cell is VOID. **This
  gate must not be relaxed**; it is what makes the windowed column a
  measurement.
- **G7** — section 1's `simTicks / 1e12` agrees with the instance's own
  reported `seconds` to within **0.5%**, and the three sections' `simTicks`
  sum to the whole-program `simTicks`. A disagreement means the ops did not
  land where the source puts them. The pilot read 0.18%.
- **G8** — realized `L1_MSHR` and `L1_REPL` equal the cell's declared values,
  read back from the L1 controller section of `config.ini`. The swept knob is
  gated, not trusted: a silently-ignored `L1_MSHR` would turn the sweep into
  two replicates of one point, and reporting that as a sweep is the F9 defect
  class.
- **G9** — placement unchanged: `system.mem_ctrls0` carries no non-zero
  counter other than `power_state.pwrStateResidencyTicks`. With `ALL_CXL=1`
  there must be no local-DRAM traffic at all
  (`AGGBW_VALIDITY_2026-09-03.md` §"Two knobs are parsed and never applied",
  confirmed in all 21 completed cells). Any local traffic means the pool
  assignment moved and the cell is not measuring a far-memory stream.
- **G10** — useful bytes identical across arms: `fact_bytes == 16777216`,
  `warmups == 2`, `reps == 8`, `window_brackets == true`, `hit_rate == 0.5`,
  `line_stride` absent. The ratio argument requires that all three arms move
  the same bytes through their measured windows; this makes that a checked
  fact.
- **G11 (new to this family)** — `checksum == 0`.
  `AGGBW_VALIDITY_2026-09-03.md` §"Health findings" recommended this as
  fail-closed and recorded that no analyzer implements it. With
  `warmups + reps == 10` the field is an XOR over an even number of passes
  across identical unmodified data and must be exactly zero. A non-zero value
  is either memory corruption or a functional bug, and a footprint column
  taken from a run that did not read what it thought it read is not
  publishable. Nine of 120 instances in the multi-core campaign failed this.
- **G12** — prefetcher instantiation matches the arm: `config.ini` carries
  more than zero sections matching `prefetcher` for `wb` and `h2`, and
  **exactly zero** for `pf-off`. This is the realized check on the arm
  identity that `H1BW_ARM_IDENTITY_2026-09-04.md` had to establish from source
  because the archive's `config.ini` does not exist.

`rounding error > tolerance` is **not** a gate failure (§"Binary and
provenance"). `free(): invalid size` is counted and reported, and is not a
gate, matching the sibling campaigns.

### G5 re-derived — the thresholds are not inherited

`AGGBW_VALIDITY_2026-09-03.md` flags that `analyze_h1bw_bracket.py`'s G5
thresholds — `A1_MIN_FILL_SUPPRESSION = 0.20` and
`A1_MIN_BYPASS_PER_DECISION = 0.20` — **were derived from pre-fix cells and
must be re-derived for the fixed binary.** They are, below. Both move, and
they move in **opposite directions**, which is why inheriting them would have
been wrong in two ways at once rather than merely conservative.

**The measurement base.** The only post-fix cells that exist are the three
`gem5/logs/se_chi/h1bw_mc_*_4c_l3x1_bwdef_20260904fix` cells (read only;
nothing written). Computed from their own `stats.txt`:

| cell | clean decisions (`WriteEvictFull` RU->{I,UC,UD}) | bypassed (RU->I) | residue | per core | `E_clean` | bypass/decision (all writes) | fill suppression vs `wb` |
|---|--:|--:|--:|--:|--:|--:|--:|
| `wb` post-fix | 940,973 | 0 | — | — | 0.0% | 0.0000 | — |
| `h2` post-fix | 874,726 | 853,465 | 21,261 | **5,315** | **97.57%** | **0.5701** | **0.577** |
| `pfoff` post-fix | 869,701 | 851,968 | 17,733 | **4,433** | **97.96%** | **0.5707** | **0.562** |
| `h2` pre-fix (VOID) | 944,540 | 17,197 | 927,343 | 231,836 | 1.82% | 0.0110 | 0.012 |
| `pfoff` pre-fix | 888,484 | 734,590 | 153,894 | 38,474 | 82.65% | 0.4858 | 0.474 |

**Threshold 1 — the primary gate is a residue COUNT, not a fraction.**
`H2_BYPASS_FIX_OUTCOME_2026-09-03.md` §4's correction is the load-bearing
insight: the "96.0% engagement ceiling" is **not a fraction**, it is a
constant **~4,408 un-bypassable clean evictions per core**, and it reads 96.0%
only at the denominator the 4- and 8-slice cells happen to have. That document
measures it at 4,408/core at 4 slices / 4 cores, 4,408/core at 8 slices /
8 cores — agreeing to four significant figures across different core and slice
counts — and 4,433/core and 5,315/core in the two post-fix one-slice cells.

A residue that is a constant count is the right gate, because **the defect
signature is that the residue scales with traffic while the fixed behaviour
holds it constant.** So:

```
A1_MAX_UNBYPASSABLE_PER_CORE = 8000
gate:  (clean_decisions - clean_bypasses) / ncores  <=  8000
```

- **Margin: 1.51x** above the largest observation (5,315).
- **Discrimination: 33–54x.** This campaign's clean-decision denominator is
  predicted at ~437,000 (the post-fix 8 MiB cells give 218,682 per core; a
  16 MiB stream doubles it). A cell at the collapsed 1.8% engagement would
  read a residue of ~429,000, i.e. **54x the gate**; a cell at 40% engagement
  would read ~262,000, **33x the gate**. The gate therefore separates
  "fixed binary, engaged" from "retry leak present" by 1.5 orders of magnitude
  while carrying a 1.5x margin, and it is insensitive to where in that gap it
  sits.
- **Why the inherited 0.20 fraction fails here.** On the fixed binary
  engagement is pinned at its structural ceiling, 97.6–98.0%. A floor of 20%
  on `bypass/decision` would pass a cell that had lost **four fifths** of the
  policy — precisely the failure the fix removed. The old threshold was
  calibrated to separate a 37.5–48.6% pre-fix engaged population from a 1.1%
  collapsed one; the post-fix engaged population is 57.0–57.1% on that same
  measure, so the threshold has to move up with it. **The inherited gate is
  too loose by roughly a factor of three.**
- The residue gate is reported alongside `E_clean` and the **derived
  achievable ceiling** `1 - 5315 * ncores / clean_decisions`, so a cell that
  fails is diagnosed rather than merely voided.

**Threshold 2 — fill suppression against the matched `wb` arm, required by the
brief, re-derived DOWN to 0.25.**

```
A1_MIN_FILL_SUPPRESSION = 0.25     # was 0.20, on whole-program fills
```

This one moves the other way, and the reason is specific to this campaign
being an **MSHR sweep**:

- Post-fix observation is 0.562–0.577 (8 MiB, 4 cores, 1 slice, 48 MSHRs).
- **But the archive's own H2 rows imply suppression of 0.433 at 16 MSHRs and
  0.332 at 48 MSHRs** (1 - 300,238/529,330 and 1 - 353,739/529,309), and
  **there is a real mechanism for the fall**: a prefetched line arrives at the
  HNF without the STREAMING tag the demand path would have given it
  (`H2_BYPASS_FIX_OUTCOME` §4 measures this as the 0.39 pp gap between `h2`
  and `pfoff`, 882 evictions per core), and deeper MSHRs let the prefetcher
  run further ahead. Prediction S3 says this population **grows with the
  swept variable**.
- So a suppression floor above ~0.30 would void the 48-MSHR `h2` cell **for a
  reason unrelated to engagement** — it would void it for exhibiting the
  effect the sweep exists to measure. 0.25 sits 25% below the lowest
  archive-consistent expectation and **20x above** the collapsed cell's 0.012.
- Consequently: **fill suppression is the corroborating gate and the residue
  count is the primary one.** Suppression is sensitive to exactly the
  population this sweep varies; the residue is computed on RU-state clean
  evictions and is the sharper instrument. Both are checked; a cell failing
  the residue gate is VOID, and a cell failing suppression while passing the
  residue gate is VOID with the diagnosis printed, because the brief requires
  real fill suppression against the matched WB arm and this campaign has one.

**Threshold 3 — `wb` must record exactly zero bypasses.** Exact, not a
threshold, and it needs no re-derivation: `wb` never sets `isStreaming`, so a
single bypass would mean a STREAMING tag leaked into the control arm.
Confirmed structurally by the `wb` bit-identity across the fix
(`H2_BYPASS_FIX_OUTCOME` §3: 11,166 of 11,171 stat lines identical, the five
differing all host-side).

**Both thresholds are computed on WINDOWED counters and, separately, on
whole-program counters.** The windowed form is the gate, because the measured
pass is what the published number describes. The whole-program form is
reported so the gate can be compared with the sibling campaigns', which had no
choice.

## Confirming or refuting the archive's twelve numbers

Decided in advance, because the archive's arm was mislabelled and its
provenance is a hand-written summary, so the honest time to fix the
interpretation is before the data exists.

**Per-cell magnitude test.** Each of the twelve archived figures is compared
against its new counterpart on the comparable quantity — bandwidth against
`bandwidth_gbps`, footprint against **whole-program** `llc_fills_total`, since
the archive's column is whole-program. A cell **reproduces** if the new figure
is within **±20%**. The band is set at 20% because the one prior attempted
reproduction (`GATE1_H1BW_RERUN_OUTCOME.md`, gem5 `b2c6499`, a purpose-written
probe) had **no cell within 25%** and inverted the WB/H2 ordering, so 20% is
already a demanding test against that history and a lenient one against a
claim of reproduction.

Four outcomes, with the conclusion fixed for each:

**A. Structure holds (S1–S6) and >= 9 of 12 magnitudes reproduce.**
Conclusion: the archive is corroborated, and `tab:h1bw` is republished on the
new campaign's figures with the new provenance. F3 closes.

**B. Structure holds (S1–S6) and magnitudes do not reproduce.** *This is the
expected outcome.* Conclusion: **the archive's ordering and mechanism are
corroborated a third time — after `GATE1_H1BW_ANOMALY_RESOLVED_2026-08-18.md`
at matched work and the certified multi-core campaign — while its twelve
magnitudes are superseded, not reproduced.** The table carries the new
figures. The archived figures are not repaired, not averaged with the new
ones, and not cited again as measurements; they are cited only as the
historical record of a claim. F3 moves from "twelve magnitudes unbacked"
toward closed on the ground that the magnitudes now have artifacts, with the
disclosure that they are **new** magnitudes from a **new** harness rather than
a recovery of the old ones. **This is not a failure of this campaign and must
not be reported as one.** The archive ran a different binary, a different
benchmark from an unidentified tree, a different L2 prefetch degree and
(inferred) a different replacement-path depth; four uncontrolled differences
predict magnitude disagreement.

**C. A structural prediction fails.** Conclusion: the *mechanism* reading in
`H1BW_ARM_IDENTITY_2026-09-04.md` §"Question 1, evidence 5" is wrong or
incomplete, and that is the more consequential finding. Specifically: if S1 or
S2 fails, `pf-off`'s MSHR-insensitivity was not the prefetch-off signature it
was read as, and the arm-identity argument loses its fifth line of evidence
(it retains the four decisive ones, including that the model cannot express a
WC arm at all). If S3 fails, the untagged-prefetch mechanism is not what
raises H2's footprint with depth. Either is reported as a correction to that
document by addendum, and the appendix's mechanism sentences are restated on
what was measured.

**D. Ordering inverts at 48 MSHRs (S6 fails).** Conclusion is already fixed by
§"The one-slice hazard": if the HNF write-retry fraction is above 50%, the
cell is buffer-capped rather than fill-capped and the inversion is a home-node
result rather than an H2 result, exactly as at one slice with four cores; the
table then reports the sweep with that stated. If the retry fraction is below
20% and the ordering still inverts, that is a genuine refutation of `tab:h1bw`'s
bandwidth ordering at this operating point, it is reported as one, and the
paper's H1 appendix claim must be restated on the multi-reader rows of
§`sec:eval` alone.

**What is forbidden in every case.** No pooled WB-over-`pf-off` ratio, no `n`
over the two MSHR points, no mean and no range across them (S7). No quoting
`WB / pf-off` to three digits (`AGGBW_VALIDITY` §"What this licenses", and it
is already known not to transfer: 1.513 new against 1.109 archived at 4
cores). No extension of the multi-core campaign's two lower-bound arguments to
these cells, and no extension of these cells' arguments to the archive's:
`H1BW_ARM_IDENTITY` §"Question 4" is explicit that the archive's engagement
cannot be measured, and that remains true after this campaign.

## Expected runtime and cost

From observed wall times in this family, recorded in each cell's own
`MANIFEST.json` `started` and `DONE.json` `ended`: **4-core cells took
1.322–1.432 h** and **8-core cells 2.953–3.225 h**, at 8 MiB per instance.
Those are aggregate figures for 4 and 8 simulated CPUs in one process.

Single-core should be well under that, but a 16 MiB stream is larger than the
multi-core cells' 8 MiB per instance, so the two effects run in opposite
directions and the estimate is built from the pilot rather than from a ratio.
The pilot (2 MiB, 1 core, `--reps 1`) ran 10.47 M simulated instructions in
291 s of wall time = **36,000 instructions/s**. Scaling the fact array 8x
takes `fill_fact` and both passes with it; a 16 MiB working set against a
5 MiB LLC also misses far more per instruction than a 2 MiB one, which cuts
the host rate. Taking ~75 M instructions at ~25,000 instructions/s gives
**0.85 h**, and this cross-checks against the multi-core cells directly:
their 140 M instructions in 1.4 h is 27,800 instructions/s, and 75 M at that
rate is 0.75 h.

`--warmups 2 --reps 8` adds nine passes to the pilot's one. The measured pass
is 1.11% of simulated ticks, so that is **+10%**.

| set | cells | per-cell estimate | wall (concurrent) |
|---|---|---|---|
| primary | 6 | 0.85 x 1.10 = **1.0 h** | 1.0–2.0 h |
| diagnostic D | 3 | **1.0 h** | absorbed, wall unchanged |
| **all nine cells concurrent** | **9** | — | **1.0–2.0 h** |

**Budget 3 h wall for all nine cells**, launched in one batch. The host has
256 cores, load average 0.00, and the three `h1bw_mc_*_4c_l3x1_*fix`
simulations that the brief protects have exited (14:11–14:17, all
`"exit":0`). Nine concurrent single-threaded gem5 processes is not a resource
constraint and nothing needs serialisation.

Storage: `stats.txt` for a single-section 1-core cell is ~1 MB. At three
sections it is ~3 MB, so **~30 MB for nine cells**. Negligible; this is the
cheap end of the bracketing trade that cost the multi-core campaign 0.7 GB.

## What this campaign cannot settle

- **It does not fix the LLC-residency confound.** `fill_fact` writes the whole
  16 MiB working set immediately before the passes read it, and the STREAMING
  policy then prevents the read passes from displacing those dirty lines, so
  part of every arm's read stream is served from the 5 MiB LLC rather than
  from CXL — `AGGBW_VALIDITY_2026-09-03.md` §Q1 and its finding 4. At a
  3.2x working-set-to-LLC ratio the effect is smaller here than at the
  multi-core cells' 1.6x, and **the windowed counters measure the share
  directly instead of bounding it**, which is a genuine improvement. But it is
  not removed. **Nothing in this campaign licenses describing these figures
  as far-memory streaming bandwidth**; they are read bandwidth delivered to
  one core, with an arm-dependent share supplied by the LLC. Removing the
  confound needs a benchmark-geometry change and is a separate
  pre-registration.
- **It does not make `SimpleMemory` a CXL link model.** `latency_var` is 0; no
  flit protocol, no retry, no per-direction asymmetry, no cap.
- **It does not measure silicon.** In particular it cannot bound the modelled
  prefetcher against silicon's at CXL latency: `T2_WBWC_OUTCOME_2026-08-24.md`
  R7's 6% figure is local DRAM over a 2 GB region and §6 of that document is
  explicit that it does not transfer. The appendix's fidelity caveat must
  continue to assign **no direction** to that gap on the strength of anything
  here.
- **It does not recover the archive's runs.** `knee_sweep.sh` is gone, the
  binary is gone, and no `stats.txt` or `config.ini` ever survived. This
  campaign replaces them; it does not reconstruct them, and outcome B above is
  a supersession rather than a reproduction.
- **It does not license a multi-core number, and no multi-core number
  licenses these.** One core is a different operating point.
- **`n = 1` per cell in the sense of seed replication.** `--reps 8` gives an
  error bar on the measured pass within one run; it does not give
  across-run variance, and `RUBY_RANDOMIZATION` is unset so a re-run of a cell
  is expected to be bit-identical rather than an independent sample. Effects
  smaller than the reported `cov` are not interpretable, and no seed sweep is
  registered here.
- **Diagnostic set D isolates `L1_REPL` at 48 MSHRs only**, so it can clear or
  implicate replacement-path starvation as the explanation of a 48-MSHR
  disagreement. It cannot separate the other three uncontrolled differences
  from the archive (binary, benchmark, L2 prefetch degree), and no cell here
  can: two of the three no longer exist to run against.

## Deliverables of this campaign

1. This document, frozen before launch.
2. `experiments/asplos/run_h1bw_singlecore.sh` — the runner, committed before
   launch. `run_h1bw_multicore.sh` is not edited.
3. `experiments/asplos/analyze_h1bw_singlecore.py` — the analyzer, with every
   threshold above as a module constant.
   `analyze_h1bw_bracket.py` and `analyze_h1bw_multicore.py` are not edited.
4. `experiments/asplos/H1BW_SINGLECORE_OUTCOME_2026-09-04.md` — the
   certification verdict and the full results, including the archive
   comparison under whichever of A–D obtains.
5. `experiments/asplos/data/gem5/h1bw_singlecore_<stamp>.jsonl` — one record
   per cell, including void cells, which are reported and never silently
   dropped.
6. The replacement `tab:h1bw` in `STREAMING_Paper/ASPLOS27/Text/Appendix.tex`,
   with the `pf-off` label, both MSHR points and no pooled ratio, and the
   adjacent fidelity caveat restated on what was measured. The draft is at its
   22-page limit and the page count is confirmed after the edit.
7. Handbacks, not applied: `A1_PROVENANCE_LEDGER_2026-08-28.md` F3 wording and
   `INDEX.md` rows, quoted for central routing. `INDEX.md` is not edited (a
   concurrent worker owns it) and no `*_PREREG_*.md` other than this file is
   edited. `experiments/asplos/preserved/README.md` **is** corrected, since it
   is not in either set and it currently reads as provenance it does not have.

## Provenance of the numbers in this document

- Engagement thresholds, residues and `E_clean` values in §"G5 re-derived" are
  computed here from `gem5/logs/se_chi/h1bw_mc_{wb,h2,pfoff}_4c_l3x1_bwdef_20260904fix/stats.txt`
  and their pre-fix twins, **read only**. Nothing under `gem5/logs/` was
  written and no process was signalled.
- The 4,408/core residue constant, the 96.0%-is-a-count correction and the
  one-slice ordering inversion are from `H2_BYPASS_FIX_OUTCOME_2026-09-03.md`
  §§4-5. The retry-path defect is from `H2_BYPASS_COLLAPSE_2026-09-03.md`.
- The window-stagger limitation, the inert `--hot-node`/`--threads` knobs, the
  zero-`mem_ctrls0` finding, the LLC-residency confound and the `checksum`
  health finding are from `AGGBW_VALIDITY_2026-09-03.md`. The bracketing
  design, its op numbers and its marker text are from
  `AGGBW_WINDOW_PREREG_2026-09-03.md` §1.
- Arm identity, the absent WC memory type, the missing artifacts and the
  0.922x/1.183x sign flip are from `H1BW_ARM_IDENTITY_2026-09-04.md`.
- Binary provenance, the `configs/`-read-at-run-time finding and the §5b
  patch are from `BUILD_PROVENANCE.md`.
- Wall times are from the completed cells' own `MANIFEST.json`/`DONE.json`.
  The 36,000 instructions/s host rate is from the 2 MiB pilot under `/tmp`.
- Source citations are to the working tree at the time of writing:
  `gem5/scripts/run_se.sh`, `experiments/asplos/run_h1bw_multicore.sh`,
  `gem5/configs/ruby/CHI_config_8592.py`,
  `gem5/configs/deprecated/example/se.py`,
  `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp`,
  `benchmarks/e2e/hash_join/Makefile`, and — read only, not modified —
  `gem5/src/arch/x86/pagetable_walker.cc`,
  `gem5/src/mem/ruby/protocol/chi/CHI-cache-{funcs,actions}.sm`.
  **`gem5/src/` was not modified and `gem5.opt` was not rebuilt.**
