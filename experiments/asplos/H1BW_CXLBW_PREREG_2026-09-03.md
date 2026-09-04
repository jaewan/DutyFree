# Pre-registration — realistic CXL bandwidth (Campaign A), 2026-09-03

## Why this campaign exists

`H1BW_MULTICORE_OUTCOME_2026-09-03.md` established, from the runs' own
artifacts, that the CXL device in this model has **no bandwidth
differentiation at all**:

| | `mem_ctrls0` (local DRAM range) | `mem_ctrls1` (CXL range) |
|---|---|---|
| `type` | `SimpleMemory` | `SimpleMemory` |
| `latency` | 98000 ticks = 98 ns | 203000 ticks = 203 ns |
| `latency_var` | 0 | 0 |
| `bandwidth` | 2.000000 ticks/byte = 500 GB/s | 2.000000 ticks/byte = 500 GB/s |

"CXL" in this model is therefore DRAM with 2.07x the latency and an identical,
effectively unlimited, 500 GB/s ceiling. The highest aggregate any of the six
completed runs achieved was 43.14 GB/s, 11.6x below that ceiling, which is why
the outcome document could report that **no shared structure exceeded 54% of
any budget** and that throughput in this model is identically
`concurrency x 64 B / latency`.

Real CXL is roughly 32–64 GB/s per x16 link. The paper's own abstract argues
about "a 34 GB/s stream" turning over a last-level cache. A model with an
effectively unlimited interconnect may not support the conclusions the paper
draws about far-memory streaming.

**The question this campaign answers: does any conclusion from the gem5 SE
bandwidth experiments depend on the absence of a CXL bandwidth limit?**

### Where the 500 GB/s comes from — closed

The outcome document left this open, noting that gem5 commit `44b7eb7470`
raised the `SimpleMemory.bandwidth` default from `12.8GiB/s` to `512GiB/s`
(listed `[minor]`, with the comment above it still reading "12.8GiB/s which is
representative of a x64 DDR3-1600 channel"), but that 512 GiB/s converts to
1.819 ticks/byte, not the 2.000000 actually realized.

The gap is **integer quantisation, and it is silent**:

1. `MemoryBandwidth.getValue()` (`src/python/m5/params/param_types.py`)
   converts bytes/s to seconds/byte and then calls `ticks.fromSeconds()`.
2. `ticks.fromSeconds()` (`src/python/m5/ticks.py`) returns
   `int(Decimal(value).to_integral_value(ROUND_HALF_UP))` — **an integer
   number of ticks**.
3. `512 GiB/s = 549,755,813,888 B/s` -> `1.81899` ticks/byte ->
   **rounds up to 2** -> `simFreq / 2 = 500 GB/s` exactly.
4. `fromSeconds()` warns only when `err > frequency_tolerance`, and
   `err = (1.81899 - 2) / 1.81899` is **negative**. Rounding *up* never warns.
   `grep -ci 'rounding error' console.log` returns 0 on all six completed runs,
   which is consistent with this and not with any other explanation.

No config file, environment variable, `--mem-type` construction path,
`testcase/` file or working-tree-versus-`HEAD` difference sets this value.
`configs/` and `src/mem/` contain no assignment to `SimpleMemory.bandwidth`
outside the class default; the gem5 working tree is clean in `configs/`,
`src/python/` and the memory path (its only modifications are to
`src/mem/ruby/protocol/` and `src/mem/ruby/structures/`, neither of which
touches bandwidth). **The realized value 2.000000 ticks/byte = 500 GB/s is
authoritative and its provenance is the class default plus this rounding.**

### The consequence that reshapes this campaign

Only `simFreq / k` for **integer k** is realizable. The values named in the
design brief are not attainable:

| nominal target | ticks/byte | realizable? |
|---|---|---|
| 32 GB/s | 31.25 | **no** |
| 64 GB/s | 15.625 | **no** |

Requesting `32 GB/s` would silently realize 31 ticks/byte and a gate written
against 31.25 would void every run. This campaign therefore **freezes the two
settings at realizable points**, chosen as the integer tick count whose
realized bandwidth is closest to the nominal target:

| setting | request (`CXL_MEM_BW`) | realized `bandwidth` | realized ceiling | vs nominal |
|---|---|---|---|---|
| `bwt31` | `32258064516B/s` | **31.000000** ticks/byte | **32.2581 GB/s** | +0.81% of 32 |
| `bwt16` | `62500000000B/s` | **16.000000** ticks/byte | **62.5000 GB/s** | −2.34% of 64 |

Both were **verified end-to-end before this document was frozen** by generating
`config.ini` and reading the value back (`prove_default_unchanged.sh`, phase
B); neither is a calculation. The 31-tick point required a non-round request
because `1e12/31` is not a terminating decimal; `32258064516B/s` gives
`31.000000000124` ticks/byte, which rounds to 31 with 8 orders of magnitude of
margin.

A second trap, also verified: `m5.util.convert.toMemoryBandwidth` uses
**binary** prefixes, so `"32GB/s"` means 32 **GiB**/s and additionally emits a
base-10-to-base-2 cast warning. Requests are therefore written as bare
`<integer>B/s`, and the runner rejects any other form.

**The local DRAM range is deliberately left at 500 GB/s.** It is not the
device under test, and 500 GB/s is defensible for a multi-channel server
socket (eight channels of DDR5-6400 is ~410 GB/s peak; 500 GB/s is the right
order). Capping it would confound the CXL result with a local-memory result.
`DRAM_MEM_BW` exists and is left unset; the analyzer prints the realized local
ceiling for every run so this stays visible rather than assumed.

## Harness

Unchanged from `H1BW_MULTICORE_PREREG_2026-09-03.md`: `se.py` multi-program
mode, N independent single-threaded `stream-smoke` instances, one per simulated
CPU, each streaming its own private 8 MiB. Runner
`experiments/asplos/run_h1bw_multicore.sh`.

Two additive changes, both inert when unset:

- `configs/ruby/Ruby.py` reads `CXL_MEM_BW` and `DRAM_MEM_BW` and, only on the
  CXL-emulation path and only when the variable is non-empty, assigns
  `mem_ctrl.bandwidth` beside the existing per-range `mem_ctrl.latency`
  assignment. This matches the tree's existing environment idiom (`ALL_CXL`,
  `PF_OFF_CORES`, `L1_MSHR`, `HNF_*`, `SNF_MSHR`).
- The runner threads `CXL_MEM_BW` and `L3_SLICES` through, records both in
  `MANIFEST.json` as **requested**, and puts both in the output directory name
  (`h1bw_mc_<arm>_<n>c_l3x<slices>_bw<tag>_<stamp>`) so no bracket can collide
  with another or with the six completed `h1bw_mc_*_20260904` runs.

**Proof that the default is inert**, executed before this document was frozen:
`prove_default_unchanged.sh` runs the real runner with both variables unset,
captures the `config.ini` gem5 writes during `m5.instantiate()`, and diffs it
against `gem5/logs/se_chi/h1bw_mc_wb_4c_20260904/config.ini`. Result: **all
38,803 lines identical** once each file's three self-referential
`host_paths=<outdir>/fs/{proc,sys,tmp}` lines are canonicalised — those record
the output directory itself and cannot match between any two runs. With
`CXL_MEM_BW` set, the canonicalised diff is **exactly one line**,
`system.mem_ctrls1.bandwidth`, with `system.mem_ctrls0` confirmed still at
2.000000.

## Frozen configuration

Identical to the superseded campaign in every respect except the CXL
bandwidth. Restated so this document stands alone.

| parameter | value |
|---|---|
| CPU | O3CPU, 1.9 GHz |
| L1d / L1i | 48 KiB 12-way / 32 KiB 8-way |
| L2 | 2 MiB / 16-way |
| L3 (HNF) | 5 MiB / 20-way per slice, `--num-l3caches=N` (20 MiB at 4c, 40 MiB at 8c) |
| directories | `--num-dirs=1` |
| memory | `SimpleMemory`, DRAM 98 ns, CXL 203 ns, `latency_var=0` |
| DRAM range bandwidth | untouched: 2 ticks/byte = 500 GB/s |
| **CXL range bandwidth** | **31 or 16 ticks/byte (32.2581 or 62.5000 GB/s)** |
| `L1_MSHR` | 48 |
| `L1_REPL` | 16 (default, left unset; a live confound, recorded not endorsed) |
| stream size | 8 MiB per instance |
| `ALL_CXL` | 1 |
| warmups / reps | 1 / 1 |

## Arms

| arm | policy | prefetch |
|---|---|---|
| `wb` | `wb` | on |
| `h2` | `stream` | on |
| `pfoff` | `stream` | **off** (`PF_OFF_CORES=0..N-1`) |

**`pfoff` is not write-combining**, despite the historical "WC" naming in
`run_se.sh` and in the archived REPORT. It is `policy=stream` with the L1D/L2
prefetchers disabled. No arm in this campaign or any predecessor uses the WC
memory type, and `Appendix.tex:568-572`'s "model WB-versus-WC ratio" is
mislabelled at the source. Restated here so the mislabel is not re-inherited.

## Scope

2 bandwidths x 3 arms x 2 core counts = **12 runs**, all launched
concurrently.

The 8-core arms carry the load and are **not** trimmed: they are the only
cells where a realistic cap can bind (WB 31.00 and H2 43.14 GB/s uncapped
against a 32.26 GB/s cap), and the 4-core cells exist as the control in which
the cap sits above every uncapped aggregate. Twelve concurrent single-threaded
gem5 processes on a 256-core, 1.1 TiB host is not a resource constraint; no
trim is warranted and none is made.

## Metrics

`agg_bw_sum`, the sum of per-instance `bandwidth_gbps`, reported with its
window-overlap floor. `agg_bw_wall` is **retired** and not computed as a
result: the superseded campaign showed it divides the measured pass's bytes by
the whole program's simulated time and is 36–62x low. The reconstructable
corroboration is total bytes over the widest single instance window.

Additionally recorded per run, all read back from `config.ini` or `stats.txt`:
realized CXL and DRAM bandwidth ceilings, realized CXL/DRAM latency and
`latency_var`, realized slice count and LLC bytes, HNF read transaction
latency, home-node concurrency by Little's law and its occupancy against the
HNF/L1-MSHR/SNF budgets, CXL bytes read and written, and
**`cxl_bw_used_frac` = `agg_bw_sum` / realized ceiling**. That last quantity
was 2.65–8.63% in the superseded campaign; a cap that actually binds must push
it toward 100%, and it is the direct evidence of whether the cap did anything.

## Pre-declared outcomes

Predictions are bands on `agg_bw_sum` divided by the same cell's uncapped
`agg_bw_sum` from `H1BW_MULTICORE_OUTCOME_2026-09-03.md` (WB/H2/pfoff = 20.09/
25.11/13.27 at 4c and 31.00/43.14/26.98 at 8c). They are encoded as
`CXLBW_PREDICTION` in `analyze_h1bw_bracket.py` and checked mechanically, so
the result confirms or refutes them rather than being narrated after the fact.

| cap | cores | `wb` | `h2` | `pfoff` |
|---|---|---|---|---|
| 32.26 GB/s | 4 | unchanged, 0.95–1.05x | unchanged, 0.95–1.05x | unchanged, 0.95–1.05x |
| 32.26 GB/s | 8 | **clipped mildly, 0.75–1.00x** | **clipped hard, 0.55–0.85x** | unchanged, 0.95–1.05x |
| 62.50 GB/s | 4 | unchanged, 0.95–1.05x | unchanged, 0.95–1.05x | unchanged, 0.95–1.05x |
| 62.50 GB/s | 8 | unchanged, 0.90–1.05x | unchanged, 0.85–1.05x | unchanged, 0.95–1.05x |

The reasoning, declared in advance: at 4 cores the 32.26 GB/s cap sits above
all three uncapped aggregates and should change little, which is the control.
At 8 cores it sits **below** H2 (43.14) and only 4% **above** WB (31.00), so
H2 must clip to at most the cap (43.14 -> <=32.26 is <=0.748x, hence the
0.55–0.85 band) while WB clips mildly through queueing as it approaches its
own ceiling.

**A competing mechanism is registered here so the outcome discriminates
between the two rather than being read one way after the fact.** A byte-rate
cap charges for *controller* traffic, not for useful delivered bytes, and the
two arms differ sharply in that ratio: at 8 cores WB pulled 172.8 MiB across
the CXL controller against a 128.0 MiB two-pass demand (1.350x) plus its
writebacks, while H2 pulled 130.2 MiB (1.018x) with roughly half the writeback
volume. **Per useful byte, WB loads the link substantially harder than H2.** A
bandwidth cap should therefore penalise WB more than the delivered-rate
arithmetic above suggests, and could *widen* rather than narrow the H2-over-WB
gap. The discriminating observable is `mem_ctrls1` `bytesRead + bytesWritten`
per useful byte, recorded for every run.

### The alarming outcome, pre-declared

**If the H2-over-WB advantage shrinks (capped `h2/wb` below 0.95x the uncapped
`h2/wb` of 1.2500 at 4c and 1.3917 at 8c) or inverts (`h2/wb < 1`) in any
capped cell, then the paper's H1 bandwidth-survival claim is contingent on an
unphysical model and must be rescoped.** The analyzer prints this test
explicitly for every cell and prints the word ALARM when it fires. That is a
publishable negative and it is the reason this campaign is worth 12 runs.

Conversely, if the ordering and the ratio survive both caps, the H1 claim is
strengthened: it will have been shown to hold both in the unphysical
500 GB/s regime and at a realistic CXL 2.0 x16 link rate.

## Gates

Fail-closed. A run failing any gate is printed VOID and contributes no number.
Enforced by `analyze_h1bw_bracket.py`; `analyze_h1bw_multicore.py` is left
untouched and continues to certify the superseded campaign.

- **G1** — every instance reports `status: "ok"`.
- **G2** — realized instance count equals N (guards against `se.py` silently
  dropping a workload).
- **G3** — realized LLC equals **`slices x 5 MiB`**, and the realized slice
  count equals the declared bracket. Generalised from the superseded
  campaign's `N x 5 MiB` so it is correct for a deliberate slice change and
  still voids an accidental one.
- **G4 — the realized CXL bandwidth, read back from `config.ini`, must equal
  the pre-registered integer ticks per byte for the cell (31 or 16). A run
  whose realized bandwidth does not match its request is VOID, not reported.**

G4 is the whole point of this campaign. This project treats reporting a
requested value as though it were realized as a distinct defect class (F9),
and this campaign exists precisely because that happened with bandwidth: six
completed runs were interpreted for weeks against a "CXL" ceiling that was
never a CXL ceiling. The gate compares the realized integer and nothing else.
`MANIFEST.json` records the request; no gate reads it.

Note that G3 required a fix that would otherwise have voided the sibling slice
campaign for the wrong reason: gem5 collapses a length-1 `SimObjectVector`, so
at `--num-l3caches=1` the section is `system.ruby.hnf`, not `system.ruby.hnf0`.
The superseded analyzer's `hnf(\d+)` regex matches zero sections there and
reports a 0-byte LLC. `analyze_h1bw_bracket.py` matches both spellings and
uses the same prefix when reading `stats.txt`.

## What this campaign cannot settle

- It does not make `SimpleMemory` a CXL link model. `latency_var` remains 0
  and the device remains fixed-latency with a byte-rate throttle; there is no
  flit-level protocol, no retry, no per-direction asymmetry and no queueing
  model beyond the throttle. It bounds the *aggregate* rate realistically, and
  that is all it does.
- **n = 1 per cell.** `--reps 1`, no seed replication, no within-instance
  variance estimate. `cov` is identically 0 by construction.
- The cross-process barrier is still absent, so `agg_bw_sum` is reported with
  its window-overlap floor as a bound, not a guarantee.
- Magnitudes remain non-comparable to the archived
  `preserved/gem5_streaming.tar.gz` REPORT, whose harness is unrecoverable.
