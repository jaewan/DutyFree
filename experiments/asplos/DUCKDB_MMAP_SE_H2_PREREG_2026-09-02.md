# Pre-registration: DuckDB mmap-probe SE H2 kill-gate

Registered **2026-09-02, before any arm of this campaign produced a
number.** Engine-boot smoke (`--preset gem5-smoke`) is **not** an arm:
wrong geometry (table fits in L2), wrong claim. Compiling the `-DGEM5`
binary is not an arm.

## Why

Native mmap-probe (`DUCKDB_MMAP_PROBE_OUTCOME_2026-09-02.md`) showed the
probe can be a VMA DuckDB scans (G-copy PASS, +136 KiB anon vs 80 MiB
probe). Stock SPR `mprotect(PROT_STREAMING)` is EINVAL. That licenses an
H2 test **on that mapping**, not an E5 STREAMING-DuckDB sentence.

r5 already showed STREAMING helping a complete join in SE m5op. This
campaign asks a different question: does H2 still engage, and still
move application units, when the tenant is DuckDB scanning that mmap
rather than `cxl_join_bench`'s fact stream?

It is a **kill-gate**, not a second STREAMING family for the paper.
FS `mprotect` DuckDB is not this campaign (guest image +
`CONFIG_PAT_STREAMING`; stock c4 is EINVAL).

## What this is allowed to be

SE m5op (`SET_STREAMING` 0x55) on the probe mmap only. Hash table `b`
stays a DuckDB table (WB DRAM). Infinite SF, `HNF_H3=0`, labelled SE,
not OS-path. Metric: mmap join `count(*)` identity plus **query
seconds** (chrono, same caveat as r5) and neighbour `cyc_per_load`.

**Not** CAT. **Not** flush-behind. **Not** comparable to r5 tuples/s
unlabelled. **Not** the tenant-CAT +104.5% cell.

## Host / lock

**mos181 only**, and **only after r6b is judged**. The launcher refuses
to start any `gem5.opt` while a process command line contains
`atomic_2cpu_w8_fs_e2e_r6b_16g_join`. Do not write under
`gem5/logs/fs_restore_chi/`.

## Geometry (the arm)

Same HNF and victim as r5, so the variable is the tenant.

| knob | r5 | this campaign | why |
|---|---|---|---|
| LLC | 7680KiB | **7680KiB** | r5 machine |
| victim | `2650 12000000` | **`2650 12000000`** | r5 machine; victim/LLC stays 0.345, same limitation |
| table | 4,194,304 B (`--hot-bytes`) | **40 × N = 4,194,240 B** | DuckDB `b` is `(k, payload)` ≈ 40 B/row. N=**104856** (divisible by chain=8). table/LLC = **0.5333** |
| probe / fact | 8,388,608 B | **P=1,048,576 keys = 8,388,608 B** | STREAMING object; larger than LLC |
| keys | `hash` mix in the join | **`i % k` (`--keys mod`)** | skip a DuckDB `hash()` fill in SE; labelled. Native identity used `hash(i)%k` |
| `--reps` | 1 | 1 | tenant `m5_exit` |
| `--declare` | m5op | m5op | labelled SE |
| SF / H3 | infinite / 0 | infinite / 0 | match r5; not an H3 cell |

`--l3_size` is `7680KiB`, not `7.5MiB`.

`gem5-smoke` (`N=1024`, `P=8192`) may run after the r6b lock lifts to
see whether DuckDB syscalls survive SE. A successful smoke licenses the
full geometry; a failed smoke is **VOID** (engine not SE-viable), not a
STREAMING negative.

## Arms

`qui` / `wb` / `h2` × seeds `{1,2,3}`. No CAT sweep.

- qui: victim + dummy
- wb: victim + `mmap_probe.gem5 --preset gem5 --policy wb`
- h2: victim + `mmap_probe.gem5 --preset gem5 --policy stream`

Probe mapping: anonymous, `bind_pool` CXL (pool 1) before first touch,
then fill, then (h2 only) `gem5_set_streaming`. Table `b` is not marked.

## Registered gates (fail-closed)

- **G-lock.** No full or smoke `gem5.opt` while r6b's join restore is
  running. Action: launcher exit 2.
- **G0.** `l3_size_bytes=7864320`. Tenant JSON `n=104856`,
  `probe=1048576`, `table_bytes=4194240`, `probe_bytes=8388608`,
  `keys=mod`. table/LLC in [0.530, 0.537].
- **P_complete.** Every non-quiet arm: `JOIN_MEASURE_END`, `JOIN_M5_EXIT`,
  JSON `status=ok`, `mmap_count>0`, `query_seconds>0`, `victim_loads` in
  [1e5, 6e6]. Quiet: no JSON, `victim_loads` in [1.1e7, 1.21e7].
- **P_match.** `mmap_count` and `mmap_sum` identical across wb and h2
  (same join). Action on miss: **void**.
- **P1 (H2 engagement).** h2 `streamingHnfFillBypasses > 0`; qui and wb
  exactly 0. Action on miss: **VOID** — m5op did not reach the HNF
  (DuckDB never loaded the marked mapping, or SE dropped the op). Not a
  STREAMING-doesn't-help result.
- **P2 (contention).** wb `cyc_per_load` / qui ≥ **1.15**. Same floor as
  r5. Action on miss: **VOID** (DuckDB heap did not contend; no
  protection experiment).
- **P3 (protection).** R = `(wb - h2) / (wb - qui)` on `cyc_per_load`.
  If P1 holds and R ≤ 0: **reportable negative** (engine working set is
  not the probe). If R > 0: directional pass; **do not** quote as r5's
  22.59%.
- **P4 (tenant).** h2 mean `query_seconds` ≤ wb mean (DuckDB is not
  slower when the probe is STREAMING). Vs unprotected, **not vs CAT**.

Wedge vs CAT is **not** this campaign. Do not start a CAT sweep on
DuckDB in gem5 to chase a paper figure.

## Analysis plan

Archive via `experiments/lib/archive_gem5_runs.py` (extended to parse
this JSON) → `data/gem5/duckdb_mmap_se_h2.jsonl` after 9/9, not
incrementally (A6.19). Analyzer:
`experiments/asplos/analyze_duckdb_mmap_se.py`. Launcher:
`experiments/asplos/run_duckdb_mmap_se.sh`.

Tenant primary: JSON `query_seconds`. Cross-check: `mmap_count /
(cpu1.numCycles / 1.9e9)` as rows/s; if chrono and cycles disagree by
>8%, prefer cycles and label it.

## Apparatus (filled after rebuild, before first arm)

- gem5: `build_Intel_8592/gem5.opt` sha256 `cfd37207b9b7124ae88af7192178518b21c89b44a84d582efa69960ce19b9ed1` (same as r5)
- tenant: `benchmarks/e2e/duckdb_mmap_probe/build/mmap_probe.gem5` sha256 `2139aa85efb386692b14c561df27eeb6ac257d89c9acb5b6c60aa8dc636fd84b`.
  Dynamically linked against `~/duckdb-1.1.3/libduckdb.so` with rpath.
  Official `libduckdb_static.a` is not a closed archive (utf8proc/re2/mbedtls
  unresolved). gem5 SE uses the host loader. Labelled before any arm.
- victim: sha256 `1f6214b8cadb451371665e73a08ee584f5a3efb062b8ced0f9cef6fb08f6a7fd` (same as r5)

Native identity, **not an arm**: `--preset gem5 --policy wb --keys mod` on
mos181 returned `mmap_count=8388608` (= P×chain). Anon RSS grew ~5.0 MiB
on an 8 MiB probe (`g_copy` false at this P). The c4 80 MiB G-copy PASS
(+136 KiB) remains the declaration-site license. SE engagement is P1
(HNF bypasses), not native RSS.

## Do not

- Launch while r6b is in flight.
- Overlay this on silicon CAT +104.5% or r5 +9.97% tuples/s.
- Quote smoke as H2.
- Call this FS `mprotect` DuckDB.
- Produce a gem5 flush-behind arm.
- Compare query seconds to r5 tuples/s.
- Write an E5 STREAMING-DuckDB sentence from this kill-gate unless P1–P4
  all pass **and** a later FS campaign exists. This file licenses the
  SE question only.

## What has not happened

No JSONL, no outcome, no gem5 arm, no paper sentence. This file is a
gate list, not a result.

---

# Addendum 1 — 2026-09-04: the simulator binary is not the one registered. Declared before the smoke run, appended not edited (`A6.19`).

**Nothing above is retracted, reworded or deleted.** The Apparatus section's
`gem5.opt` line is superseded by this addendum and is quoted here rather than
changed:

> - gem5: `build_Intel_8592/gem5.opt` sha256 `cfd37207b9b7124ae88af7192178518b21c89b44a84d582efa69960ce19b9ed1` (same as r5)

## The two digests, verified on mos181 before any arm

| | sha256 | provenance |
|---|---|---|
| registered (r5 build) | `cfd37207b9b7124ae88af7192178518b21c89b44a84d582efa69960ce19b9ed1` | the line quoted above |
| **realized (this campaign)** | **`cb2904444d5c5c4d31d9d8f07295209283d29e294ef1d885d789442d98e7bbe0`** | `sha256sum gem5/build_Intel_8592/gem5.opt`, mtime 2026-09-04 12:51:05, 984,361,288 B, `git describe` `build-cb290444-1-gfa27f665db` |

The tenant and victim are **unchanged from the registration**: tenant
`mmap_probe.gem5` `2139aa85efb386692b14c561df27eeb6ac257d89c9acb5b6c60aa8dc636fd84b`,
victim `1f6214b8cadb451371665e73a08ee584f5a3efb062b8ced0f9cef6fb08f6a7fd`. Only
the simulator moved.

## The delta: three changes compiled into `gem5.opt`

`git log build-cfd37207..build-cb290444` in `gem5/` lists five commits. Two do
not reach this binary and are named so the count is not silently reconciled:
`3bd36a0061` touches only `scripts/fs_*.sh` (FS restore, not SE, not compiled),
and `f3c2c84949` touches only `testcase/dutyfree/fused.c`, a guest binary this
campaign does not run — our `victim` and `dummy` hash unchanged. The three that
are compiled in:

| commit | change | bearing here |
|---|---|---|
| `b9c8714c93` | `prepareRequestRetry()` now copies `isStreaming` | **material — see below** |
| `1bb6418e01` | m5op `0x57` `flush_range`, an idealised flush-behind oracle (`pseudo_inst.{cc,hh}`, `sim_object.{cc,hh}`, `m5ops.h`) | inert, measured |
| `a5f366456e` | `ticks.py` rounding guard: `err = abs(...)` | warning-only |

Records: `H2_BYPASS_COLLAPSE_2026-09-03.md` (diagnosis) and
`H2_BYPASS_FIX_OUTCOME_2026-09-03.md` (patch, rebuild, re-run). One correction
to the latter's §2 table, handed back rather than applied: it attributes
`sim_object.{cc,hh}` to `3bd36a0061`; those two files are `1bb6418e01`'s, and
`3bd36a0061` is shell scripts only. The count of compiled changes is unaffected.

## Why the fix is load-bearing for `P1`, and why it is not a free choice

`P1` is `streamingHnfFillBypasses > 0` on `h2`, and it is a **VOID** gate: a
miss says the m5op never reached the HNF, not that STREAMING failed to help.
The pre-fix binary contains exactly the defect that manufactures that miss.
`prepareRequestRetry()` omitted one field assignment, so every CHI request that
took a `RetryAck` was re-sent with `isStreaming` at its `false` field default —
affirmatively marked non-streaming, not merely unmarked — and the HNF then
allocated the line H2 was supposed to decline. The measured consequence, from
`H2_BYPASS_FIX_OUTCOME_2026-09-03.md` §4: the one-slice H2 cell went from
17,197 bypasses and 1.8% engagement to 853,853 and 97.6% on the same
configuration with only the simulator changed.

This campaign runs **one** LLC slice (`--num-l3caches=1`), which is the
geometry in which the defect was worst — a 32-entry HNF transaction pool, 64.8%
write-request retry, and H2 reduced to a writeback arm wearing an H2 label. So
running `cfd37207` here would have put a known VOID-generator directly on the
gate that decides whether this campaign is interpretable at all, and a `P1`
miss would have been uninterpretable between "DuckDB never loaded the marked
mapping" and "the fabric stripped the tag". That is the whole reason for the
deviation and it is recorded before any arm.

The other two are declared inert rather than assumed so. The flush-behind
oracle: the registration forbids a flush-behind arm, and the opcode is not
merely unused but **absent** — the byte sequence `0f 04 57 00` does not occur
in `mmap_probe.gem5`, `victim` or `dummy`, and the tenant source contains no
`gem5_flush_range` call site. There is no runtime branch to take, unlike
`cxl_join_bench.gem5` where the byte is present behind `--policy fbo`. The
`ticks.py` guard feeds a `warn()` and no computed value; it will emit
`rounding error > tolerance` lines in every run's log from `SimpleMemory`'s
bandwidth tick quantization. **Those lines are expected and are not a gate
failure.** They are also the only way to tell the two binaries apart from a
console log alone.

## The honest cost

The geometry table above still matches r5. **The build no longer does.** This
campaign was designed as an only-the-tenant-changed contrast against r5 — same
HNF, same victim, same simulator, DuckDB substituted for `cxl_join_bench` — and
after this deviation the simulator is a second changed variable. r5's arms were
measured on `cfd37207` and cannot be re-measured on `cb290444` without spending
those runs again, which this campaign is not registered to do.

So: **no r5 comparison is licensed from this campaign, on two independent
grounds.** The registration already forbade one — "Not comparable to r5
tuples/s unlabelled", "Compare query seconds to r5 tuples/s" on the Do-not
list — because the tenant's unit changed from tuples/s to query seconds. This
addendum adds a second, which is narrower in one way and broader in another:
it holds even for quantities that *are* commensurable across the two campaigns,
including `cyc_per_load`, the bypass counts and the `P2` contention ratio. A
difference between r5 and this campaign cannot be attributed to the tenant,
because the simulator also moved.

The direction of the bias is known and does not rescue the comparison. The
defect only ever *removed* bypasses, so r5's H2 figures are lower bounds and
this campaign's are not. That makes any r5-versus-DuckDB delta on an
H2-sensitive quantity biased in a known direction of unknown size — enough to
know the comparison is unsound, not enough to correct it.

Nothing else in this registration moves: the geometry, the nine arms, `G-lock`,
`G0`, `P_complete`, `P_match`, `P1`–`P4`, the analysis plan and the Do-not list
all stand exactly as written, and the smoke run has not yet been launched at
the time this addendum is committed.
