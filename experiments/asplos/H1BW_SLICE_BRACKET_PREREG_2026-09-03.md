# Pre-registration — LLC slice-count bracket (Campaign B), 2026-09-03

## Why this campaign exists

`H1BW_MULTICORE_OUTCOME_2026-09-03.md` measured 20.09 / 25.11 / 13.27 GB/s at
4 cores for WB / H2 / prefetch-off. The archived
`preserved/gem5_streaming.tar.gz` REPORT gives 6.23 / 7.73 / 5.62 for the same
three arms at the same core count. The H2/WB **ratio** agrees to 0.7% (1.2500
new against 1.2408 archived) while the **magnitude** differs by 3.2x. A ratio
that reproduces under a magnitude that does not is the signature of two
different regimes, and the outcome document could not determine from artifacts
alone which regime the archive measured.

**The question this campaign answers: does a single shared home node reproduce
the archived magnitudes?**

### Why the slice count is the discriminating variable

The outcome document ruled out every other candidate from the runs' own
`stats.txt`:

- Memory bandwidth is not it. Both controllers sit at 2 ticks/byte = 500 GB/s
  and the runs consumed 2.65–8.63% of it.
- The single SNF is not it: 3.85% whole-run and at most 53.5% window
  occupancy against 256 TBEs.
- Capacity is not it. Every arm pulled at least the entire two-pass working
  set across the CXL controller (1.007x–1.356x), so **the LLC supplied none of
  the measured pass** and a smaller LLC simply thrashes harder.
- Data-array throughput is not it: the HNF cache is `dataArrayBanks=1` with
  `resourceStalls=false`, so bank conflicts are counted and never enforced.
- No slice is a hot spot: counting demand plus prefetch accesses, which is
  what the stream generates, the slices are balanced to 1.010x.

What remains is a **structural** quantity. `HNF_MSHR` defaults to 32
(`CHI_config_8592.py:435`), so the home-node transaction-buffer budget is
`32 x slices`: 128 at four slices, 256 at eight, and **32 at one**. The
measured window occupied roughly **60** of those buffers at 4 cores and 109 at
8 cores. At one slice the pool supplies less than the 4-core runs demonstrably
needed, and it becomes the only structure that binds.

If the archive's platform line — a single "L3(HNF) 5MiB/20" — describes
`--num-l3caches=1`, this is the configuration it ran. This bracket was
recommended, and explicitly **not launched**, in the outcome document's
"Recommended bracketing run" section; this pre-registration launches it.

## Scope

**4 cores only, three arms, `--num-l3caches=1`. Three runs, launched
concurrently.**

8 cores is deliberately excluded: the archive has no artifact-backed 8-core
row to bracket against, and adding it roughly triples the cost for no
comparison. This is the same trim the outcome document recommended, carried
forward deliberately rather than by omission.

One consequence must be stated in advance, because it is a real limitation of
a 4-core-only bracket. The outcome document registered two falsifiable
consequences of the buffer-cap hypothesis; this campaign can test only the
first. **The prediction that the 4-core and 8-core aggregates converge, both
capped by the same 32 buffers, is not tested here.** If the magnitudes land in
the predicted band, that is consistent with but not proof of the saturation
reading, and the convergence test remains open.

## Harness

Unchanged from `H1BW_MULTICORE_PREREG_2026-09-03.md` except for the slice
count. Runner `experiments/asplos/run_h1bw_multicore.sh` with `L3_SLICES=1`,
which replaces `--num-l3caches=$n` with `--num-l3caches=$L3_SLICES` and
records the value in `MANIFEST.json` and in the output directory name
(`h1bw_mc_<arm>_4c_l3x1_bwdef_<stamp>`), so nothing collides with the six
completed `h1bw_mc_*_20260904` runs.

`L3_SLICES` defaults to the core count, preserving today's behaviour exactly.
**Proof**, executed before this document was frozen: with `L3_SLICES` and
`CXL_MEM_BW` unset, `prove_default_unchanged.sh` regenerates `config.ini`
through the real runner and it is identical to
`gem5/logs/se_chi/h1bw_mc_wb_4c_20260904/config.ini` in all 38,803 lines, once
each file's three self-referential `host_paths=<outdir>/fs/{proc,sys,tmp}`
entries are canonicalised.

The single-slice configuration was separately generated and inspected before
launch: exactly one `system.ruby.hnf.cntrl.cache` section, `size=5242880`,
`assoc=20`, four CPUs, `MANIFEST.json` `num_l3caches: 1`.

## Frozen configuration

Everything except the slice count is held at the superseded campaign's values.
That is what makes this a clean bracket: `--num-dirs=1`, the per-slice
`--l3_size=5MiB --l3_assoc=20`, `L1_MSHR=48`, `PF_OFF_CORES`, the 98/203 ns
latencies and `ALL_CXL=1` all stay frozen.

| parameter | value |
|---|---|
| CPU | O3CPU, 1.9 GHz, `--num-cpus=4` |
| L1d / L1i | 48 KiB 12-way / 32 KiB 8-way |
| L2 | 2 MiB / 16-way |
| **L3 (HNF)** | **5 MiB / 20-way, `--num-l3caches=1` — total LLC 5 MiB, not 20 MiB** |
| HNF transaction buffers | **32 total**, down from 128 |
| directories | `--num-dirs=1`, 256 SNF TBEs |
| memory | `SimpleMemory`, DRAM 98 ns, CXL 203 ns, `latency_var=0` |
| CXL bandwidth | **untouched**: 2 ticks/byte = 500 GB/s |
| `L1_MSHR` | 48 |
| `L1_REPL` | 16 (default, left unset; a live confound, recorded not endorsed) |
| stream size | 8 MiB per instance, 32 MiB total |
| `ALL_CXL` | 1 |
| warmups / reps | 1 / 1 |

The CXL bandwidth is deliberately **not** capped here. Campaign A
(`H1BW_CXLBW_PREREG_2026-09-03.md`) varies bandwidth; this campaign varies
slice count. Varying both at once would make neither interpretable. G4 below
consequently gates this campaign at the default 2 ticks/byte, which is a real
gate and not a formality: it certifies that Campaign A's environment variable
did not leak into Campaign B's runs.

## Arms

| arm | policy | prefetch |
|---|---|---|
| `wb` | `wb` | on |
| `h2` | `stream` | on |
| `pfoff` | `stream` | **off** (`PF_OFF_CORES=0,1,2,3`) |

**`pfoff` is not write-combining.** It is `policy=stream` with the prefetchers
disabled. Restated here for the same reason as in Campaign A.

## Metrics

`agg_bw_sum` with its window-overlap floor. `agg_bw_wall` is retired and not
computed as a result.

The mechanistic quantities that make this bracket interpretable, all read back
from the artifacts: HNF read transaction latency, home-node concurrency by
Little's law, and **HNF TBE occupancy against the now-32-buffer budget**. The
hypothesis is specifically that this last number pins at or near 100%, in
contrast to the 47.3% (WB) and 47.8% (H2) of the 128-buffer 4-core baseline.
If aggregates fall but TBE occupancy does not approach its budget, the buffer
pool is **not** the mechanism and the result must be reported as such.

## Pre-declared outcomes

Encoded as `SLICE_PREDICTION` in `analyze_h1bw_bracket.py` and checked
mechanically.

| arm | 4-slice baseline | **predicted band at 1 slice** |
|---|---|---|
| `wb` | 20.09 GB/s | **6–11 GB/s** |
| `h2` | 25.11 GB/s | **6–11 GB/s** |
| `pfoff` | 13.27 GB/s | **10–15 GB/s** (least affected) |

Derivation, declared in advance. Little's law at the baseline
per-transaction latencies puts a 32-buffer ceiling at 10.6 GB/s for WB, 13.2
for H2 and 14.2 for prefetch-off. Those are optimistic in two ways: a binding
buffer pool inflates the very latency in the denominator, and a 5 MiB LLC
raises the miss share above what the 20 MiB configuration saw. Hence a band
running below them, 6–11 GB/s for WB and H2, **overlapping the archive's 6.23
and 7.73**. Prefetch-off is predicted least affected because it needed only
~30 of the 128 buffers at baseline (23.4% occupancy), so a 32-buffer pool is
close to sufficient for it.

### The ordering may invert, and that is registered as informative

The superseded campaign's ordering is `h2 >= wb > pfoff`. A buffer-capped WB
near 8 GB/s against a largely unaffected prefetch-off near 13 GB/s **breaks
`wb > pfoff`**. That is pre-declared as a possible and informative outcome,
not a failure: it would show the archive's ordering was not itself measured in
a buffer-capped regime, and it would mean neither configuration reproduces the
archive's full arm structure — consistent with the WB/prefetch-off ratio
already failing to transfer (1.513 new against 1.109 archived at 4 cores).

### Interpretation table, fixed in advance

| result | reading |
|---|---|
| WB and H2 land in 6–11 GB/s **and** HNF TBE occupancy approaches 100% | The archive measured a buffer-capped single-home-node regime. The 3.2x magnitude gap is explained by slice count, and the archive's "CXL-path-limited" label was wrong about the mechanism but right that something saturated. |
| WB and H2 land in 6–11 GB/s **but** TBE occupancy stays well below budget | Magnitudes match for a reason that is not the buffer pool. Report the coincidence and do not claim the mechanism. |
| WB and H2 stay well above 11 GB/s | The slice count is not the explanation. The archive's number is then most likely a metric-definition artifact — its "aggregate BW = 32MiB/total_sec" divided by a span wider than the concurrent window — which is the second reading the outcome document could not exclude. |

No outcome here licenses a paper sentence on its own. This campaign
discriminates between two readings of an unrecoverable archive; it does not
supersede anything. `H1BW_MULTICORE_OUTCOME_2026-09-03.md` remains the citable
source for 4- and 8-core aggregates.

## Gates

Fail-closed, identical machinery to Campaign A. A run failing any gate is
printed VOID and contributes no number. Enforced by
`analyze_h1bw_bracket.py slice`.

- **G1** — every instance reports `status: "ok"`.
- **G2** — realized instance count equals 4.
- **G3** — realized LLC equals **`slices x 5 MiB` = 5,242,880 B**, and the
  realized slice count equals the declared bracket of 1.
- **G4** — realized CXL bandwidth from `config.ini` equals **2 ticks/byte**,
  the untouched default. This certifies that Campaign A's `CXL_MEM_BW` did not
  leak into these runs.

G3 required a fix without which this campaign would have been voided for the
wrong reason. gem5 collapses a length-1 `SimObjectVector` to an unindexed
name, so at `--num-l3caches=1` the `config.ini` section is
`system.ruby.hnf.cntrl.cache`, **not** `system.ruby.hnf0.cntrl.cache`. The
superseded analyzer's `^system\.ruby\.hnf(\d+)\.cntrl\.cache$` matches zero
sections there and would report a 0-byte realized LLC, voiding all three runs.
`analyze_h1bw_bracket.py` matches both spellings and uses the matched prefix
when reading `stats.txt`, whose keys follow the same naming. This was found by
generating the single-slice `config.ini` before launch, not after.

## Budget

2–4 h for three concurrent 4-core arms, against the 1.32–1.38 h the 4-core
baseline arms took. Longer because a buffer-capped configuration burns more
simulated cycles for the same 34.9M instructions per instance.

## What this campaign cannot settle

- The 4c/8c convergence test is not run, so the saturation reading cannot be
  confirmed, only made consistent. See "Scope".
- **n = 1 per cell.** No seed replication, no within-instance repetition.
- No cross-process barrier; `agg_bw_sum` carries an overlap floor, not a
  guarantee.
- The archive's harness is gone, so agreement in magnitude would still not be
  a reproduction — it would be a demonstration that a nearby configuration
  produces nearby numbers.
