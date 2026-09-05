# The non-power-of-two Ruby set count costs real capacity — measured, not derived; blast radius; and a guard

Date: **2026-09-04** (project-local, UTC−7). *Dating note, as
`BUILD_PROVENANCE.md`: this host's clock is KST (UTC+9), so commit timestamps
and gem5 banners for this pass read `2026-09-05`. Records in this directory are
dated project-local.*

Host `mos181`. Binaries, launchers, run directories and diffs are all named
below; nothing here rests on recollection.

## 0. What was already known, and what this adds

The arithmetic is **not new**. `CacheMemory::init()` computing
`m_cache_num_sets = (size/assoc)/block` and then `floorLog2` is on record as
the **`[F9.4]`** power-of-two set-quantization class since
`W4.3_PROVENANCE_LEDGER_2026-08-23.md`, its LLC form was worked out in
`W7.2_A1_SIZING_2026-08-24.md`, its affected list was last enumerated in
`W8.1_M5OP_IS_SE_ONLY_2026-08-24.md` ("W7 A1, and the 8-way and 12-way rows of
`tab:sens`"), and the r5 cell was added to it by
`DUCKDB_MMAP_SE_H2_OUTCOME_2026-09-04.md` §3, which states the derivation in
full and hands it back in its §7.

Three things were missing, and this pass supplies them.

1. **It had never been measured.** `DUCKDB_MMAP_SE_H2_OUTCOME` §3 says so in as
   many words — *"derived from source, not measured"* — and its proposed `F9.4`
   wording repeats it: *"no run emits a set count"*. §1 below is the
   measurement.
2. **gem5 had no guard**, so the same arithmetic could hide again in the next
   campaign exactly as it hid in this one. §3.
3. **The records still carry the wrong ratio.** §4 and the two addenda this
   pass appends.

## 1. Empirical confirmation — the prediction and the measurement agree exactly

Source reading is not measurement. This project has been bitten twice this week
by inferring a quantity from an instrument that did not measure it, so the
arithmetic was put to a run before anything downstream of it was touched.

### The prediction, fixed before the runs

`run_npot_probe.sh` carries the four cells and the predictions in its own
header, written before it was first executed. All four request an LLC that
would hold a 6 MiB working set **if the requested size were realized**; they
differ only in whether `(size/assoc)/64` is a power of two.

| cell | `--l3_size` | `--l3_assoc` | sets | pow2? | predicted realized |
|---|---|--:|--:|---|---|
| A | `5MiB` | 20 | 4096 | yes | 5.00 MiB — floor control |
| B | `7680KiB` | 20 | **6144** | **no** | **5.00 MiB**, i.e. 66.7% |
| C | `10MiB` | 20 | 8192 | yes | 10.00 MiB — ceiling control |
| D | `7680KiB` | **15** | 8192 | yes | 7.50 MiB — **decisive control** |

**D is the cell that makes this an experiment rather than a demonstration.** It
requests *the same 7,864,320 B as r5* and differs from B only in set-count
arithmetic. If requested bytes were what mattered, B and D would agree.

The instrument is a cyclic sequential sweep of a 6 MiB working set
(`gem5/testcase/dutyfree/npot_probe.c`, 3 measured passes after an init touch,
stats reset between). Under LRU that is a step function in reachable capacity
`C`, not a slope: at `C >= 6 MiB` every line is still resident when the sweep
comes round, and at `C < 6 MiB` the line evicted to make room is always the one
wanted next. Set-index period is `2^(6+b)` bytes — 256 KiB at 12 bits, 512 KiB
at 13 — and 6 MiB is a whole multiple of both, so every reachable set receives
exactly the same number of lines (24 per set at 4096 sets against 20 ways;
12 per set at 8192 sets). `HNF_RP=lru` and `PF_OFF_CORES=0`: LRU because
TreePLRU at assoc 20 is 2×-biased (`GEM5_TREEPLRU_NONPOW2_BIAS_2026-08-28.md`),
prefetchers off because a capacity probe should not have to argue about what a
stream prefetcher did. `TimingSimpleCPU`, 1 core, 1 slice; minutes, not hours.

Binary `cb2904444d5c5c4d31d9d8f07295209283d29e294ef1d885d789442d98e7bbe0` —
the campaign binary, **not rebuilt for this**. Logs:
`gem5/logs/se_npot_probe/npot_{A,B,C,D}`.

### The measurement

| cell | HNF demand hits | misses | hit rate | `simTicks` | `simInsts` |
|---|--:|--:|--:|--:|--:|
| A `5MiB`/20 | 166,595 | 128,498 | 56.46% | 26,881,767,046 | 1,479,807 |
| **B `7680KiB`/20** | **166,595** | **128,498** | **56.46%** | **26,881,767,046** | 1,479,807 |
| C `10MiB`/20 | 294,970 | 123 | 99.96% | 17,184,977,560 | 1,479,807 |
| **D `7680KiB`/15** | **294,970** | **123** | **99.96%** | **17,184,977,560** | 1,479,807 |

And the stronger form of the same result, which is what settles it:

| comparison | differing lines in `stats.txt` | which |
|---|--:|---|
| **A vs B** | **5** | `hostSeconds`, `hostTickRate`, `hostMemory`, `hostInstRate`, `hostOpRate` — **all five host-side** |
| C vs D | 5 host-side + `m_allocsByWay::15`–`::19` | the five extra way buckets exist only because C is 20-way and D is 15-way |
| **A vs D** | **1,825** | including `simTicks`, `simSeconds`, `cpi`, `ipc` |

**B is not merely similar to A. On every one of the 2,014 simulated quantities
the two runs emit, B *is* A.** Same hits, same misses, same tick count, same
per-way allocation histogram. `--l3_size=7680KiB --l3_assoc=20` and
`--l3_size=5MiB --l3_assoc=20` are the same machine, and gem5 says so on 2,014
counters without being asked.

Meanwhile B and D request **identical bytes** and differ on 1,825 lines,
because D's set count is a power of two and B's is not. C and D — 10.00 MiB and
7.50 MiB, both reachable in full — are indistinguishable on this workload, as
they should be: both hold 6 MiB.

### Verdict

| | requested | predicted realized | measured realized |
|---|---|---|---|
| `7680KiB` @ 20 ways | 7,864,320 B (7.50 MiB) | 5,242,880 B (5.00 MiB), 66.7% | **5,242,880 B — B ≡ A on 2,014/2,014 simulated quantities** |

**Prediction and measurement agree, exactly rather than approximately.** The
source reading is confirmed and everything downstream of it may proceed.

Two honest notes on the instrument. (i) Cell A's hit rate is 56.5%, not the ~0%
a textbook cyclic LRU thrash would give; the CHI HNF also allocates on the L2's
clean evictions, which refreshes recency and breaks the perfect cycle. That
changes nothing here — the A/B versus C/D separation is what carries the
result, and the absolute floor is not a quantity this pass claims. (ii) The
probe measures the **HNF**. It says nothing about any other level, which is
what §2 is for.

## 2. Blast radius

Instrument: **`config.ini`**, the binary's own dump of what it actually
instantiated, read by `audit_nonpow2_sets.py` over every run directory under
`gem5/logs/` — 161 files. `config.ini` is the right authority because a
launcher's flags record what was asked for and `config.ini` records what was
built. Every Ruby structure that indexes with `floorLog2` set bits is covered,
not just the LLC: L1I, L1D, L2, the HNF LLC, and the snoop-filter / directory
structures. `PerfectCacheMemory` is deliberately excluded — it is an unbounded
map with no set index at all.

### Every distinct geometry in every committed run directory

```
role               type            size  as  blk sib    sets   reach   realized  short%  runs
HNF LLC            RubyCache    5242880  20   64   7    4096    4096    5242880    0.00    62
HNF LLC            RubyCache    5242880  20   64   8    4096    4096    5242880    0.00    58
HNF LLC            RubyCache    5242880  20   64   6    4096    4096    5242880    0.00     7
HNF LLC            RubyCache    5242880  20   64   9    4096    4096    5242880    0.00     9
HNF LLC            RubyCache    7864320  20   64   6    6144    4096    5242880   33.33     1   <== NOT POW2
HNF snoop filter   RubyCache       1024   1   64   6      16      16       1024    0.00   139
L1D                RubyCache      49152  12   64   6      64      64      49152    0.00   140
L1I                RubyCache      32768   8   64   6      64      64      32768    0.00   140
L2                 RubyCache    2097152  16   64   6    2048    2048    2097152    0.00   140
L1I/L1D/SF placeholders, RNI/DMA, MN (1024 B or 128 B, assoc 1)             0.00   139/61
```

(`sib` = `start_index_bit`; the four LLC rows differ only in slice count, 1/2/4/8
slices giving `sib` 6/7/8/9. Rows for the four probe cells this pass created are
omitted.)

**One affected run directory in the whole committed tree**, and it belongs to a
campaign that is already VOID:
`gem5/logs/se_duckdb_mmap_h2_smoke/h2_s1`.

### Campaign table

Realized figures for every gem5 campaign with committed data under
`experiments/asplos/data/gem5/`, plus the two never-run registrations. r5's run
directories were written to `/tmp` and are gone, so its row is established from
`l3_size_bytes` in all 45 committed records (all `7864320`, verified here) and
from `run_complete_join.sh`, which is committed.

| campaign | data | cache | requested B | sets | reachable | realized B | shortfall | published claim depends on requested? |
|---|---|---|--:|--:|--:|--:|--:|---|
| **`COMPLETE_JOIN` (r5)** | `r5_runs.jsonl` (45) | **HNF LLC** | **7,864,320** | **6144** | **4096** | **5,242,880** | **33.3%** | **YES — see §4.** `fig:frontier`(a) is built from this file |
| `COMPLETE_JOIN` (r5) | " | L1I / L1D / L2 | 32,768 / 49,152 / 2,097,152 | 64 / 64 / 2048 | = | = | 0 | no |
| `H2H_REALJOIN` (r3) | `rj3_runs.jsonl` (66) | HNF LLC | 5,242,880 | 4096 | 4096 | 5,242,880 | 0 | clean — and it is the source of the paper's 1–3 pp CAT claim (§5) |
| `FUSED_KNEE` | `kn_runs.jsonl` (45) | HNF LLC | 5,242,880 | 4096 | 4096 | 5,242,880 | 0 | clean |
| `FUSED_KNEE` big | `kb_runs.jsonl` (18) | HNF LLC | 5,242,880 | 4096 | 4096 | 5,242,880 | 0 | clean |
| `FUSED_TABLESWEEP` | `ts_runs.jsonl` (45) | HNF LLC | 5,242,880 | 4096 | 4096 | 5,242,880 | 0 | clean |
| `H2H_FUSED` | `fh_runs.jsonl` (15) | HNF LLC | 5,242,880 | 4096 | 4096 | 5,242,880 | 0 | clean |
| `H2H_PARTITION` | `hh_runs.jsonl` (15) | HNF LLC | 5,242,880 | 4096 | 4096 | 5,242,880 | 0 | clean |
| `HNFRP_ROBUSTNESS` | `rp_runs.jsonl` (19) | HNF LLC | 5,242,880 | 4096 | 4096 | 5,242,880 | 0 | clean |
| `HNFRP_REMAINING` | `rq_runs.jsonl` (30) | HNF LLC | 5,242,880 | 4096 | 4096 | 5,242,880 | 0 | clean |
| `HNFRP_*` | " | HNF snoop filter (finite) | 4,194,304 (4096×16×64) | 4096 | 4096 | 4,194,304 | 0 | clean |
| `H1BW_SINGLECORE` | `h1bw_singlecore.jsonl` (9) | HNF LLC ×1 | 5,242,880 | 4096 | 4096 | 5,242,880 | 0 | clean |
| **`H1BW_SLICE_BRACKET`** | `h1bw_slice_bracket*.jsonl` (9) | HNF LLC **per slice** | **5,242,880** | **4096** | **4096** | **5,242,880** | **0** | **clean — see below** |
| `H1BW_MULTICORE` | `h1bw_multicore.jsonl` (6) | HNF LLC ×4, ×8 | 5,242,880 each | 4096 | 4096 | 5,242,880 each | 0 | clean |
| `H1BW_CXLBW` | `h1bw_cxlbw*.jsonl` (24) | HNF LLC ×4, ×8 | 5,242,880 each | 4096 | 4096 | 5,242,880 each | 0 | clean |
| `FS_COMPLETE_JOIN` (r6b–r6e) | `gem5/logs/fs_restore_chi/` | HNF LLC ×2 | 5,242,880 each | 4096 | 4096 | 5,242,880 each | 0 | clean (confirms the premise given) |
| **`DUCKDB_MMAP_SE_H2`** | smoke cell only | **HNF LLC** | **7,864,320** | **6144** | **4096** | **5,242,880** | **33.3%** | **no — campaign VOID, no arm ran**; already recorded in its own §3 |
| **`FB_ORACLE`** (never run) | none | **HNF LLC** | **7,864,320** | **6144** | **4096** | **5,242,880** | **33.3%** | **no — fixed by amendment before it can run.** §3.3 |
| `FS_COMPLETE_JOIN_PREREG` | — | prose only | — | — | — | — | — | its "10 MiB here against 7.5 MiB there" is wrong; handback in §6 |

**`H1BW_SLICE_BRACKET` is clean, and the reason is worth stating because the
suspicion against it was reasonable.** Dividing a fixed total across a varying
slice count is exactly how this defect arises unseen — but that campaign does
not divide a total. `run_h1bw_multicore.sh` pins `L3_PER_SLICE=5MiB` and passes
`--l3_size=$L3_PER_SLICE --num-l3caches=$slices`, so each slice is
independently 5 MiB / 20 ways / 4096 sets and the *aggregate* varies (5, 20,
40 MiB) instead of the per-slice size. Confirmed three ways, not assumed: the
launcher; `l3_per_slice_realized = [5242880]` in all 42 `h1bw_*` records; and
the `l3x1`/`l3x4`/`l3x8` run directories' own `config.ini`, which differ only
in `start_index_bit` (6/8/9 for 1/4/8 slices). Had the campaign divided
40 MiB by 3 or 6 slices it would be squarely affected; it does not.

### Outside the two scopes above, for completeness

These are `[F9.4]`'s previously enumerated cells. They are named because the
question was "full blast radius", and re-derived here rather than copied:

| cell | requested | sets | reachable | realized | shortfall |
|---|--:|--:|--:|--:|--:|
| W7 A1 (`w7_campaign.sh`, `32MiB`/20) | 33,554,432 | 26,214 | 16,384 | 20,971,520 | **37.5%** |
| `tab:sens` 8-way row (`5MiB`/8) | 5,242,880 | 10,240 | 8,192 | 4,194,304 | **20.0%** |
| `tab:sens` 12-way row (`5MiB`/12) | 5,242,880 | 6,826 | 4,096 | 3,145,728 | **40.0%** |

The 12-way row is the worst case anywhere in the project. All three have no
committed data under `data/gem5/` and no surviving run directory under
`gem5/logs/`, and all three are already on record.

### And what the audit found clean that could have been affected

- **Every L1 and L2 in every campaign.** 48 KiB/12 = 64 sets, 32 KiB/8 = 64,
  2 MiB/16 = 2048, and W7 A1's 512 KiB/16 = 512. Non-power-of-two
  *associativity* does not imply a non-power-of-two *set count*, and the L1D at
  assoc 12 is the standing example: 12 ways, 64 sets, exact.
- **Every snoop filter.** The `HNF_SF_FINITE=1` cells use 4096 sets × 16 ways
  and 8192 × 8; the `sf` placeholder is 1 kB / assoc 1 = 16 sets; the default
  when finite is `1<<16` sets. All powers of two. The snoop filter is
  constructed from `sf_sets * sf_ways * 64` and so is *structurally* immune —
  the set count is supplied directly rather than back-derived from a size — and
  that is a design worth copying, not luck.
- **Every directory, RNI/DMA and MN placeholder** (128 B / assoc 1 = 2 sets).

## 3. Preventing recurrence in gem5

### 3.1 The guard

`gem5/src/mem/ruby/structures/CacheMemory.cc`, in `init()`, immediately after
`m_cache_num_set_bits` is computed and **before** `m_cache.resize()` allocates
the sets that will never be indexed:

```cpp
int64_t reachable_sets = int64_t{1} << m_cache_num_set_bits;
if (reachable_sets != m_cache_num_sets) {
    int64_t realized = reachable_sets * m_cache_assoc * m_block_size;
    warn("CacheMemory %s: %d sets is not a power of two, so only %d of "
         "them are reachable and %d are allocated but never indexed. "
         "Configured %d B (%d ways, %d B lines); REALIZED CAPACITY %d B "
         "(%.1f%% of configured). Pick a size/assoc/block whose "
         "(size/assoc)/block is a power of two.", ...);
}
```

Emitted for the r5 geometry, verbatim from cell B's console log:

```
src/mem/ruby/structures/CacheMemory.cc:137: warn: CacheMemory
system.ruby.hnf.cntrl.cache: 6144 sets is not a power of two, so only 4096 of
them are reachable and 2048 are allocated but never indexed. Configured
7864320 B (20 ways, 64 B lines); REALIZED CAPACITY 5242880 B (66.7% of
configured). Pick a size/assoc/block whose (size/assoc)/block is a power of two.
```

### 3.2 `warn()` and not `fatal_if()` — the trade-off, and the decision

The case for `fatal_if()` is real and should not be softened: **silently
simulating two-thirds of the requested capacity is arguably worse than refusing
to start**, because a refusal is discovered in seconds and a silent shortfall
was discovered here after 45 runs, a published ratio and four documents. Two of
this file's own `fatal_if`s exist on exactly that reasoning — refuse at
configuration time rather than crash, or mislead, mid-simulation.

It is nonetheless `warn()`, for three reasons, in increasing order of weight.

1. **A fatal would break existing configurations.** `run_complete_join.sh`,
   `run_duckdb_mmap_se.sh`, `w7_campaign.sh`'s A1 and `p1batch.sh`/`b4run2.sh`'s
   assoc sweep are all committed and all refuse to start under a fatal.
2. **It would break them at the worst possible moment.** The affected
   campaigns' realized geometry is exactly what now needs confirming — §1's
   cell B *is* the r5 geometry, and under a fatal that measurement could not
   have been taken. A defect-correction pass must not destroy the ability to
   re-run the configuration it is correcting.
3. **Warning-only is what makes inertness provable.** The precedent is
   explicit: the `ticks.py` rounding guard (`a5f366456e`) earlier this week was
   made warning-only *because it must not change any computed value*, and a
   separate script proved the default path unaffected
   (`prove_default_unchanged.sh`, `QUANTIZATION_AUDIT_2026-09-03.md`: 0
   differing `config.ini` lines in 42,789). Here the guard's entire effect is a
   branch that a power-of-two set count does not take, so the class of runs
   that must not move **cannot** move. A `fatal_if` would have the same
   property; a *repair* of the indexing would not, and is not attempted here.

The price of `warn()` is that somebody has to read it, so the warning is not a
diagnosis to be worked out later — it prints the realized capacity and the
percentage outright. **That has a second effect worth more than the guard
itself: a run's console log now records reachable capacity, which is a quantity
no gem5 output carried before.** `DUCKDB_MMAP_SE_H2_OUTCOME` §3 and its
proposed `F9.4` wording both rest on "no run emits a set count"; from this
build forward, one does. `config.ini` continues to record the requested size,
so the two artifacts together now name both numbers — which is precisely what
`G0` could not distinguish (§4).

What the guard deliberately does **not** do: fire on a power-of-two set count,
even informationally. An unconditional `inform()` would add a line to every
existing campaign's console log — no computed value would change, but the
artifact would, and console logs are load-bearing provenance in this project
(`BUILD_PROVENANCE.md` §2 makes the startup banner the authority for
binary-to-cell attribution). Silence on the good path keeps that artifact
byte-identical.

### 3.3 `FB_ORACLE_PREREG_2026-09-03.md` — amended before it can run

It registers `--l3_size=7680KiB --l3_assoc=20` as "r5's machine, exactly" and
has never run, so it is fixed now rather than corrected later. **The fix costs
nothing, and §1 is why:** `--l3_size=5MiB --l3_assoc=20` is bit-identical to
`--l3_size=7680KiB --l3_assoc=20` on all 2,014 simulated quantities, so
amending the flag changes the *description* of the machine and not the machine.
`P-O2` (that `qui`/`wb`/`h2` reproduce r5 within noise) is therefore preserved
exactly rather than approximately — it is strengthened, since the registration
now names the geometry r5 actually ran. Amendment appended to that document; its
superseded wording is quoted in place, per `A6.19`.

### 3.4 Build provenance for this pass

Per the convention in `BUILD_PROVENANCE.md`.

| | sha256 |
|---|---|
| pre-guard (the binary three `*_20260904fix` cells were attributed to) | `cb2904444d5c5c4d31d9d8f07295209283d29e294ef1d885d789442d98e7bbe0` |
| post-guard | `d4e798601e7205c526868c8bdefbb75c4dde4f05f2b6b6a54a802df0b9c74a83` |

Recorded **before** the rebuild, as required. Two things beyond the requirement:
the pre-guard bytes were **preserved on disk** at
`gem5/build_Intel_8592/gem5.opt.pre-npot-guard.cb290444` — this is the exact
failure `BUILD_PROVENANCE.md` exists to record, and copying 984 MB is cheaper
than another archaeology pass — and the rebuild went through
`gem5/scripts/build_gem5.sh` (§5(a) of that document), which wrote
`build_Intel_8592/BUILD_PROVENANCE.json` and `BUILD_SOURCE.diff` next to the
binary: `gem5_git_head fa27f665db`, `gem5_git_describe
build-cb290444-1-gfa27f665db-dirty`, `gem5_source_fingerprint
a2f261684dfa6c79812036b2e7e186a63db070d107979a6333f3dc82fc2b4546`, built
`2026-09-05T08:38:06+09:00` on `mos181`. No simulation was running at rebuild
time (checked, not assumed) and nothing under `gem5/logs/` was modified.

### 3.5 Proof that the guard is inert

All four probe cells were re-run on the post-guard binary into a separate
output root (`gem5/logs/se_npot_probe_postguard/`) so the pre-guard artifacts
survive for comparison. Same launcher, same options, same environment.

| cell | pow2? | differing `stats.txt` lines, pre vs post | which | `config.ini` | guard fired? |
|---|---|--:|---|---|---|
| A `5MiB`/20 | yes | **5** of 2,019 | all five host-side | identical | **no** |
| B `7680KiB`/20 | **no** | **5** of 2,019 | all five host-side | identical | **yes, once** |
| C `10MiB`/20 | yes | **5** of 2,021 | all five host-side | identical | **no** |
| D `7680KiB`/15 | yes | **5** of 2,016 | all five host-side | identical | **no** |

The five are `hostSeconds`, `hostTickRate`, `hostMemory`, `hostInstRate` and
`hostOpRate` in every cell — wall-clock and host-memory measurements of the
simulator, which differ between any two invocations. **Every simulated quantity
is bit-identical in all four cells.** `config.ini` is byte-identical apart from
three `host_paths` lines that name the different `--outdir`, which is an artifact
of running into a separate directory and not of the guard.

This is the same standard, and the same evidence shape, that
`BUILD_PROVENANCE.md` used to license the `isStreaming` re-run comparison
("bit-identical on all 11,166 simulated quantities (5 differing lines, all five
host-side)").

Two things this establishes that a power-of-two-only check would not:

- the guard is inert on the **affected** geometry too. Cell B, the one that
  fires, produces byte-identical simulated output before and after. The guard
  reports; it does not repair, and it is not mistaken for a repair.
- the guard fires **once per affected structure and nowhere else**: 1 warning
  in B, 0 in A, C and D. Nothing in the L1/L2/SF/directory set trips it.

## 4. The records this corrects

`COMPLETE_JOIN_OUTCOME_2026-09-01.md` and its pre-registration are wrong
wherever they treat 7,864,320 B as the realized capacity. The task named three
places; there are **six**, and the sixth is the most consequential because a
causal explanation rests on it. Both documents receive addenda that quote the
superseded wording in place, per `A6.19`; nothing is deleted and no verdict
moves.

| # | where | as written | realized |
|---|---|---|---|
| 1 | `OUTCOME` title | "at table/LLC ≈ 0.53" | **0.800** |
| 2 | `OUTCOME` line 21 | "HNF 7680KiB (realized 7,864,320)" | requested 7,864,320; **realized 5,242,880** |
| 3 | `OUTCOME` `G0` gate | "4,194,304 / 7,864,320 = 0.5333 \| PASS" | 4,194,304 / 5,242,880 = **0.800** |
| 4 | `OUTCOME` "What this does not do" | "Growing the HNF from 5 MiB to 7.5 MiB" | **the HNF did not grow** |
| 5 | `OUTCOME` add. 1 table | "table/LLC \| 0.800 \| **0.533** \| 0.533" | r5 realized **0.800** — identical to r3's |
| 6 | `OUTCOME` add. 1 table + its explanation | "victim/LLC \| 0.518 \| **0.345** \| 0.533", and "That is why total tax fell 10.74 → 6.29 cyc" | r5 realized **0.518** — **also identical to r3's**, so the stated cause is void |
| 7 | `PREREG` line 28 | "4/7.5 = 0.5333… = 32/60" | the origin of the error |
| 8 | `PREREG` `P2` and add. 1 | "the LLC is 1.5× larger" | **the LLC is the same size** |

Item 6 is the one that changes an argument rather than a number. Addendum 1
attributes r5's fallen victim tax to a shrunken `victim/LLC`; realized
`victim/LLC` is 2,713,600 / 5,242,880 = **0.518**, which is r3's value to three
digits, so that explanation is unavailable and the fall must be explained by
what actually differed — a complete pass reporting tuples/s against a truncated
pass reporting IPC. The same document contains the tell, one line below its own
7.5 MiB claim: *"2650 KiB already fit in the 5 MiB LLC."*

**What survives, stated plainly.** All 45 runs — 15 arms, 13 of them plotted as
points in `fig:frontier`(a), with `r5_wb` and `r5_qui` as the normalizers — ran
at **one and the same realized geometry**, verified from `l3_size_bytes =
7864320` in all 45 committed records. A ratio common to every arm cannot
distort a comparison between arms, so **`fig:frontier`(a) is internally valid
and its magnitudes stand as measured**: P5, the +9.97% wedge, the +8.42%
matched-R wedge, `R(h2) = 22.59%`, the 1.185× WB tax. None of them is
recomputed and none moves.

**What is void** is the claim that the model's tenant pressure was matched to
silicon's. r5's entire reason for existing was to move `table/LLC` from r3's
0.800 to silicon's 0.533. It moved it to **0.800**. r5 is not "r3 with one knob
fixed" — it is r3's cache geometry exactly, and the ratio the campaign was
built to change is the one ratio it did not change. The campaign's own
Addendum 1 already conceded that r5 "is not 'r3 with one knob fixed'" for a
different reason; the sentence is true for a stronger one.

That is a **correction to a description, not a retraction of a result**, and the
distinction holds because of §1: cells A and B prove the two flags name one
machine, so r5 measured something real, at a geometry it named wrongly.

## 5. The paper — reported, not edited

Nothing under `/home/domin/STREAMING_Paper/` was modified.

### 5.1 `Sec7_Evaluation.tex:42-44` — the 1–3 pp CAT claim is **unaffected**

> "Normalized by the cache fraction assigned to the tenant, its CAT
> tenant-cost curve is within 1--3 percentage points of silicon at the
> comparable widths."

**Which figure it used:** `MODEL_SILICON_CAT_CALIBRATION_2026-09-01.md`, which
names its inputs — "the 12-point gem5 CAT sweep (`data/gem5/rj3_runs.jsonl`)
and the 15-point SPR CAT sweep (`data/silicon_e2e_hashjoin.jsonl`)" — and lists
the seven comparable points (41.1/42.0, 36.2/38.9, 34.1/35.9, 25.6/25.2,
15.3/13.6, 5.3/4.4, 0/0). `rj3_runs.jsonl` is **r3**, not r5.

**Two independent reasons the 7.5 → 5.0 correction cannot move it.**

1. **The campaign it rests on was never affected.** r3 requests `5MiB` at
   20 ways = 4096 sets exactly; realized 5,242,880 B, shortfall 0.
2. **The normalization is not a capacity in bytes.** "The cache fraction
   assigned to the tenant" is a CAT way fraction — `w/20` on the model, `w/15`
   on silicon. Way masking is untouched by this defect: the quantization is in
   the *set* count, so a `w`-way mask grants exactly `4096 × w × 64` B for
   every `w`. The x-axis is exact for all 12 widths.

The record's own derived quantities are also exact as written, because they were
computed against 5 MiB: "0.25 MiB per way (5 MiB / 20)" and "2.59 MiB victim /
5 MiB LLC = 51.8%".

**The corrected sentence would need to say nothing different.** No edit is
required at `Sec7:42-44`, and the "optimistic by as much as 57 points"
protection clause in the same sentence is from the same unaffected table.

### 5.2 The paper's geometry statements — reading **verified**

The reading offered was that `Sec7:33-37` is correct *precisely because* 5 MiB
is the realized figure, and that the paper never cites 0.533, 7680 or 7.5 MiB.
Both halves check out.

- **`Sec7:33-37`** — "an O3+CHI model with 5~MiB of shared cache per home
  node", "the frontier and single-core sweeps use two cores and one home node",
  "20~MiB at four readers and 40~MiB at eight". All three are **realized**
  values. The frontier sentence is the one that matters: `fig:frontier`(a) is
  built from r5, which *requested* 7.5 MiB, and the paper says 5 MiB — which is
  right. It reads as a slip and is a fact.
- **Never cited:** `grep` over `ASPLOS27/Text/*.tex` for `0.533`, `7680`,
  `7864320`, `7.5 MiB` and `table/LLC` returns **nothing**. The five `5 MiB`
  mentions (`Sec7` lines 33, 58, 223, 272, 330) are each correct as realized,
  including line 272's "against a fixed 5~MiB shared cache" — the r5 sweep —
  and line 330's "the model's 5~MiB" in the silicon comparison.
- **`Appendix.tex` already discloses the one `[F9.4]` instance it does
  contain**, and this was not expected. Its LLC-associativity sensitivity table
  labels the column "LLC assoc. (realized" and gives "8-way, 4 MiB (66%)" and
  "20-way, 5 MiB (53%)", with the surrounding text stating outright that "from
  a requested 5 MiB the 8- and 12-way rows realize only **4 MiB** and [3 MiB]"
  and that the row "therefore spans a joint associativity *and* capacity
  change". `tab:gem5cfg` gives "LLC / HNF (shared) 5 MiB, 20-way" and "5 MiB =
  320 MiB/64". So the paper reports realized capacity for the affected rows and
  requested-equals-realized capacity everywhere else.
- The paper states its own discipline at `Sec7:29-31`: "We report realized
  cache geometry and verified placement rather than requested values." On this
  quantity it does, including where the shortfall is real. **The paper is the
  only artifact in the chain that got this right**; the error is confined to
  this directory's records.

**Refuted, in one place, and in the paper's favour.** The claim "the paper never
cites 7.5 MiB" is true of the paper and *not* of the repository:
`FB_ORACLE_PREREG_2026-09-03.md` writes "different LLC (7.5 MiB vs 320 MiB per
socket)" in a section governing how its results may be used, and
`FS_COMPLETE_JOIN_PREREG_2026-09-02.md` writes "10 MiB here against 7.5 MiB
there". Both are corrected or handed back below. Neither is paper text.

## 6. Handbacks — proposed, not applied

`A1_PROVENANCE_LEDGER_2026-08-28.md` and `INDEX.md` are **not edited by this
pass**; another worker owns them.

### `F18` — proposed wording

Registering the arithmetic itself as `F18` would duplicate `[F9.4]`, which
already covers it and already lists the r5 cell (added by
`DUCKDB_MMAP_SE_H2_OUTCOME_2026-09-04.md` §7). `F18` is therefore proposed for
what is genuinely new — the *class*, not the instance — and `F9.4`'s r5 cell
should be closed by measurement at the same time.

> **`F18` — a simulator that quantizes a configured quantity and reports the
> unquantized one, with no output naming the difference; and records that then
> quote the requested figure as though it were realized.** Registered
> 2026-09-04 from `NONPOW2_SETS_MEASURED_2026-09-04.md`. Distinct from
> **`F9.4`**, which is the *arithmetic* (`(size/assoc)/block` then `floorLog2`,
> so a non-power-of-two set count silently loses capacity) and which this pass
> does not re-register: `F9.4` is a defect in a computation, `F18` is a defect
> in **observability plus record-keeping**, and it is why `F9.4` survived four
> separate enumerations of its own affected list and still reached a published
> ratio. Three components. *(1) The simulator was silent.* `CacheMemory::init()`
> allocated 6,144 sets, indexed 4,096, and emitted no warning, no assertion and
> no stat; `config.ini` faithfully recorded the **requested** `size=7864320`,
> so every instrument the harness had reported the number that was wrong.
> **Repaired**: a `warn()` in `CacheMemory::init()` naming the realized
> capacity, so a run's console log now carries reachable capacity — a quantity
> no gem5 output carried before, and whose absence is cited verbatim in
> `F9.4`'s own r5 wording ("no run emits a set count"). Warning-only and
> **proved inert**: four cells, pre- and post-guard, byte-identical on every
> simulated quantity, 5 differing lines per cell and all five host-side.
> *(2) A fail-closed gate read the wrong artifact and passed.* r5's `G0`
> required `l3_size_bytes == 7864320` and a `table/LLC` band computed against
> that same number, both from `config.ini`'s `size=` field — a gate written to
> catch requested-for-realized substitution, reading a requested value. **Same
> family as `F17`** (an instrument that cannot observe the quantity in its own
> claim), and the prevention is the same shape: a gate must name the artifact
> that carries the *realized* quantity, and where none exists the gate is not
> yet implementable and should say so. *(3) The records propagated it.*
> `COMPLETE_JOIN_OUTCOME_2026-09-01.md` is wrong in **six** places including
> its title, and `COMPLETE_JOIN_PREREG_2026-09-01.md` line 28 is the origin
> (`4/7.5 = 0.5333… = 32/60`). Both corrected by addendum, superseded wording
> quoted per `A6.19`. **`F9.4`'s r5 cell is closed by measurement**, and this
> is the substantive upgrade: it was on record as "derived from source, not
> measured", and it is now measured — `--l3_size=7680KiB --l3_assoc=20` is
> **bit-identical to `--l3_size=5MiB --l3_assoc=20` on all 2,014 simulated
> quantities**, while `--l3_size=7680KiB --l3_assoc=15` (same requested bytes,
> power-of-two set count) differs on 1,825 lines. **No published magnitude
> moves.** All 45 r5 runs share one realized geometry, so `fig:frontier`(a)'s
> comparison is internally valid and P5, the +9.97% wedge and `R(h2) = 22.59%`
> stand as measured. What is void is the claim that r5 matched the model's
> tenant pressure to silicon's: realized `table/LLC` is **0.800**, identical to
> r3's, and realized `victim/LLC` is **0.518**, also identical to r3's — so r5
> is r3's cache geometry exactly, and Addendum 1's attribution of r5's fallen
> victim tax to a shrunken `victim/LLC` is void with it. **Blast radius is
> bounded and was audited rather than assumed**: `audit_nonpow2_sets.py` over
> all 161 `config.ini` under `gem5/logs/` finds **one** affected run directory
> (`se_duckdb_mmap_h2_smoke/h2_s1`, a VOID campaign) and every L1, L2, snoop
> filter and directory clean at every slice count. `H1BW_SLICE_BRACKET` is
> **clean** — it pins 5 MiB *per slice* rather than dividing a total.
> **`FB_ORACLE_PREREG_2026-09-03.md` is amended before it can run**, at zero
> cost to its `P-O2` reproduction check, since the two flags name one machine.
> Paper exposure: **none.** `Sec7:42-44`'s 1–3 pp CAT claim rests on r3
> (`rj3_runs.jsonl`, 4,096 sets exactly) and normalizes by way fraction, which
> this defect does not touch; the paper's own geometry statements cite 5 MiB
> throughout and are correct as realized; `0.533`, `7680` and `7.5 MiB` appear
> nowhere in it. Logged **closed on repair** for component (1) and **open** for
> (2) — no artifact yet carries realized capacity for a completed run, and the
> guard supplies it only from this build forward.

### Other handbacks, for their owners

- **`DUCKDB_MMAP_SE_H2_PREREG_2026-09-02.md` and `run_duckdb_mmap_se.sh`** still
  specify `7680KiB`. That campaign is VOID and its own outcome document already
  hands the finding back in its §7, so nothing is edited here — but if it is
  relaunched, `--l3_size=5MiB` is the correction, and it is free (§1). Its
  registered `table/LLC` and `probe/LLC` bands must be recomputed against
  5,242,880 first; the outcome document already gives 0.800 and 1.600.
- **`FS_COMPLETE_JOIN_PREREG_2026-09-02.md`** says "What differs is the LLC —
  10 MiB here against 7.5 MiB there". r6e's own `config.ini` gives 2 × 5,242,880
  = 10 MiB realized (4,096 sets per slice, clean — the premise given to this
  pass, verified), and r5's realized is 5,242,880. The correct statement is
  **10 MiB here against 5 MiB there**, i.e. exactly 2×, which is a cleaner fact
  than the 1.33× it currently asserts. Not edited: that campaign is another
  pass's.
- **`STATE_2026-09-01.md`** line 61 — "r5 grew the HNF to 7680KiB to fix
  table/LLC (32 MiB / 60 MiB = 0.533)" — inherits the same reading.
- **`run_complete_join.sh` must NOT be corrected.** It is the committed record
  of what r5 ran, and `F13`'s whole lesson is that a launcher's value is that it
  reproduces the run. Changing `7680KiB` there would make it reproduce a
  different one — bit-identically, as it happens, but the record would then be
  a claim rather than a transcript.

## 7. Artifacts

| path | what |
|---|---|
| `gem5/src/mem/ruby/structures/CacheMemory.cc` | the guard (§3.1) |
| `gem5/testcase/dutyfree/npot_probe.c` | the probe (§1) |
| `experiments/asplos/run_npot_probe.sh` | the four cells, predictions in its header |
| `experiments/asplos/audit_nonpow2_sets.py` | the blast-radius audit (§2); `--geometry SIZE ASSOC [BLOCK]` for one-off arithmetic |
| `gem5/logs/se_npot_probe/npot_{A,B,C,D}` | pre-guard runs (ignored by `logs/`; not committed) |
| `gem5/logs/se_npot_probe_postguard/npot_{A,B,C,D}` | post-guard runs, for §3.5 |
| `gem5/build_Intel_8592/gem5.opt.pre-npot-guard.cb290444` | the preserved pre-guard binary |
| `gem5/build_Intel_8592/BUILD_PROVENANCE.json`, `BUILD_SOURCE.diff` | written by `scripts/build_gem5.sh` |

Probe provenance, so the four cells are reproducible from the commit rather
than from this host: `npot_probe.c` sha256
`402cf9cab44c6e598c3c012add8d9bf8d09ad454d019d6123dc56ba6accd1ce7`, and
`gcc -O1 -static -march=x86-64` (the `CFLAGS` the committed `Makefile` rule
uses) produces `npot_probe` sha256
`b554bda348c6051a740cdbaad2f2930529e1ce2b8d951e70dc200842fec1ec4a`
**byte-reproducibly** — compiled twice here and compared, since a run whose
binary is not recoverable is the `F10`/`F13` failure and this probe is now
load-bearing for `F9.4`'s r5 cell.

`gem5/logs/` and `build_*/` are already covered by existing `.gitignore` rules,
so no run output, object file or 984 MB binary is staged. Nothing needed adding
to `.gitignore`.

## 8. What this pass did not do

- **No repair of the indexing.** Making `addressToCacheSet()` reach all 6,144
  sets would change every affected number and is not a correction to a record;
  it is a new simulator with a different cache. The guard reports and does not
  repair, and §3.5 proves it.
- **No re-run of r5.** Unnecessary: cells A and B establish that the geometry
  r5 ran is the geometry `--l3_size=5MiB` produces, so r5's 45 runs need no
  repetition to be understood — only to be described correctly.
- **No paper edit**, and none needed (§5).
- **No edit to `A1_PROVENANCE_LEDGER_2026-08-28.md` or `INDEX.md`.**
- **No claim about which direction the shortfall moved any result.** The
  shortfall is common-mode across all 45 r5 arms, which is why the comparison
  survives; what a *genuinely* 7.5 MiB LLC would have measured is unknown and
  is not asserted. Asserting a direction without measuring it is the error this
  campaign has made more than once.

---

## Addendum 1 — 2026-09-04, ~35 minutes after §2's audit: the guard has a field observation, and §2's count is superseded

Two corrections, both from re-running `audit_nonpow2_sets.py` after this pass's
commit rather than from any new reasoning.

**§2's count moves from one affected run directory to two** (excluding this
pass's own probe cells). Superseded wording quoted rather than deleted, per
`A6.19`:

> **One affected run directory in the whole committed tree**, and it belongs to
> a campaign that is already VOID: `gem5/logs/se_duckdb_mmap_h2_smoke/h2_s1`.

The second is `gem5/logs/diag_duckdb_store_localize/h2_s1_diag`, created at
**2026-09-05 08:42:29 KST** — i.e. *after* the audit in §2 ran, by another
worker, while this pass was writing its records. It is at
`--l3_size=7680KiB --l3_assoc=20`, the r5 geometry. Two things bound it: its own
launcher labels it `DIAGNOSTIC_RUN not_an_arm campaign=NONE
purpose=localize_streaming_store` and states "NOT AN ARM OF
DUCKDB_MMAP_SE_H2. Debug-flag run; output stays out of `data/`"; and
`gem5/logs/` is covered by `.gitignore`, so **no run directory under it is
committed and no published claim depends on this one.** The §2 phrase "in the
whole committed tree" was loose for that reason and is corrected here.

**The more useful half: this is the guard's first observation in the field, and
it is stronger evidence than §3.5's proof.** That run's `console.log` reports
`gem5 compiled Sep  5 2026 08:34:41` and its launcher recorded
`DIAG_GEM5 d4e798601e7205c526868c8bdefbb75c4dde4f05f2b6b6a54a802df0b9c74a83`,
so it is executing the guarded binary — four minutes after that binary was
linked, unprompted, by a worker who knew nothing about this pass. The guard
fired:

```
src/mem/ruby/structures/CacheMemory.cc:137: warn: CacheMemory
system.ruby.hnf.cntrl.cache: 6144 sets is not a power of two, so only 4096 of
them are reachable and 2048 are allocated but never indexed. Configured
7864320 B (20 ways, 64 B lines); REALIZED CAPACITY 5242880 B (66.7% of
configured). Pick a size/assoc/block whose (size/assoc)/block is a power of two.
```

§3.5 proved the guard inert on cells constructed to test it. This is a run
nobody constructed for the purpose, at the affected geometry, whose console log
now carries its realized capacity — which is exactly the property §3.2 argued
the warning buys and `F9.4`'s r5 wording cites as missing. **It also
demonstrates the failure mode was live, not historical**: absent the guard,
this run would have inherited the 7.5 MiB reading silently, as the four
documents corrected in §4 did.

Nothing was done to that run. It was in flight when this was written and was
not signalled; the guard is warning-only and byte-identical on every simulated
quantity (§3.5), so its diagnostic output is unaffected by the rebuild it
happens to have picked up. Whoever owns it should read the warning as
information and not as a regression — the same standing instruction
`BUILD_PROVENANCE.md` gives for the `ticks.py` rounding warnings.

**Standing consequence for the audit.** `audit_nonpow2_sets.py` reads run
directories that are not under version control, so its count is a measurement
at a point in time and not a property of a commit. Re-run it rather than
quoting §2's table; §2's *campaign* table, which rests on committed `.jsonl`
and committed launchers, does not have this weakness.
