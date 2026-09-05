# Pre-registration: silicon hash-join e2e, clean re-run

Date: 2026-09-04, **before any measurement**.  Supersedes nothing; adds a second
dataset alongside `data/silicon_e2e_hashjoin.jsonl`, which is retained.

Parent registration: `SILICON_E2E_PREREGISTRATION_2026-09-01.md`.  Everything
in that document — apparatus, workload, arms, operational pinning, admission
gates, and its Amendment 1 — is carried over verbatim unless a section below
says otherwise.  This is a re-run of the *same* campaign with a *corrected
tenant*, not a new campaign, and it is registered separately only because a
new gate is added that the original could not have written.

## Why re-run

`data/silicon_e2e_hashjoin.jsonl` (105 records, 2026-09-01T15:47:18 ->
16:24:45, all `status=ok`, single `sha_join`
`75e0af947243c49f5b2451e1268ee378588f20eafc42330f9ca4ff2edde893b6`) was
produced by a tenant that **does not compute the join it reports**.

The arithmetic is in-band and needs no re-run to establish:

| quantity | value | source |
| --- | --- | --- |
| `fact_bytes` | 8,589,934,592 | every record |
| `sizeof(Fact)` | 16 B | `cxl_join_bench.cpp` |
| rows `n` = `fact_bytes/16` | **536,870,912** | derived |
| tenant `--reps` (inner) | 1 | runner, non-calib path |
| `hit_rate` | 1.0 | every record |
| required `matches` = `n × reps` | **536,870,912** | `run_single`, `out.matches += rr.matches` |
| reported `matches` | **534,773,760** | all 100 tenant records |
| deficit | **2,097,152** | derived |
| `fact_bytes / 4096` | **2,097,152** | derived — *equal* |
| deficit as a fraction | **0.390625 %** = 1/256 | derived |

At `hit_rate` 1.0 every row is built from `keys[...]` and must therefore probe
to a match.  A deficit is not a statistical shortfall; it is that many rows
whose key is not the key the generator wrote.  The deficit being *exactly*
one row per 4 KiB page identifies the mechanism uniquely: `prefault_region()`
does `q[off] = q[off] + 1` for `off` in steps of 4096, and it was called
**after** `fill_fact()` had populated the fact array.  One key per 4 KiB page
was incremented out from under the join.

That is fixed in committed source at `abccb31`
(`cxl_join_bench: four defect fixes and the FS e2e modes, in one commit`),
which is an ancestor of the `HEAD` this campaign builds from.  `prefault_region`
is now fail-closed — it scans for a nonzero byte and `exit(14)`s if the region
has already been written — and the seven post-`fill_fact` call sites are
deleted.  `run_single` carries the comment at the exact defect site:

> `// No prefault_region here.  fill_fact has written every tuple ...`
> `// Placed here it corrupted exactly one fact key per 4 KiB page.`

The same fraction, 0.390625 %, is what gem5's r5 suffered (2,048 of 524,288
rows) from different absolute numbers.  One defect, two platforms.

**No published figure moves.**  Both `fig:frontier`(b) axes are cross-arm
ratios — protection is normalised against `qui` and `wb`, tenant cost against
`wb` — and the corruption was bit-for-bit identical in all 21 arms, so it
cancels to first order.  This re-run is about the artifact being *sound*, not
about rescuing a number.  If it turns out to rescue a number, that is a
refutation of the mechanism above and is reported as such (see D1–D4).

## Precedence

Project convention: registration must precede the first emitted statistic, and
precedence must rest on **git or in-band evidence, never on a directory
mtime** — that error has already been made once in this project.

Accordingly:

- This file and the analyzer `silicon_e2e/rerun_analyze.py` are committed
  **before the tenant is executed even once on the measurement host**.
- The commit hash of this registration is quoted in the outcome document, and
  the campaign's own JSONL carries per-record `ts` fields that a reader can
  compare against the commit's author date.  Both are in-band.
- The positive control (below) is *also* held until after this commit, even
  though it is apparatus rather than result, so that no `matches` number of any
  kind predates the registration.  This is stricter than the parent
  registration, which allowed calibration records as "apparatus, not results".

## Tenant under test

Built from committed `HEAD` — **not** in place.

| | |
| --- | --- |
| source | `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp` at `HEAD` |
| source blob | `02217cf4702340af4b144619a578936b36f6864d` |
| source sha256 | `b843d46595873e14708b2fe585f3a1ca75a3a4f89f5c4bc920391415bf6c7263` |
| build | `make BUILD=/home/domin/sil_e2e_rerun/build native` on **c4** |
| compiler | `g++ (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0`, `-O3 -march=native` |
| **tenant sha256** | **`a677c52d05b75091057b5d9477fca99fef56e2087605457cfaf8f2b908a98431`** |
| victim | `benchmarks/bench/victim/pointer_chase`, **reused not rebuilt**, `026e357ae21a99717cae3ebf4ed05fa2cd146bda4f110afe4a2f7b829ef2db50` — byte-identical to the `sha_victim` of all 105 original records |

Built into a scratch tree, for the reason `BUILD_PROVENANCE.md` exists:
`benchmarks/e2e/hash_join/build/cxl_join_bench` **on c4** *is* `75e0af94…`,
the binary all 105 existing records name, and
`build/cxl_join_bench.gem5` **on mos181** is `cac9e27a…`, which 39 records
name and which `abccb31` records as not reproducible at all.  Neither is
overwritten.  A sha256 manifest of every pre-existing binary on both hosts was
taken before the build (`baseline_c4.sha256`, `baseline_mos181.sha256`,
`baseline_datasets.sha256`) and is re-verified with `sha256sum -c` after the
campaign; the result is reported either way.

`HEAD` also contains the `hit_rate` saturation fix (defect 2 of `abccb31`):
`(double)UINT64_MAX` rounds up to 2^64, so at `hit_rate` 1.0 the product is
unrepresentable and the conversion is undefined.  It now saturates explicitly.
**Scope note, stated before the control is run so it cannot be retrofitted:**
this campaign's host has AVX-512, where `vcvttsd2usi` saturates and the
pre-fix path was already *correct*.  The 0.390625 % deficit on this dataset is
therefore attributable to defect 1 alone.  Defect 2 mattered to the plain-SSE2
gem5 builds.  The control below passes only if both are right, but it does not
by itself prove defect 2 was ever live here, and the outcome must not claim it
does.

## Positive control (registered pre-flight, not a result)

Confirm the fix is in the binary that will actually run, by behaviour rather
than by inspection.

- Small geometry, `--mode single`, `--hit-rate 1.0`, `--reps 1`, same
  `--hot-bytes 33554432`, on **c4**, using the scratch binary above.
- **Pass** iff `matches == fact_bytes/16` exactly, deficit zero, and
  `"correct":true`.
- Run at more than one small `fact_bytes` so that "deficit == fact_bytes/4096"
  and "deficit == 0" cannot be confused by a coincidence of one size.
- A `prefault_region` regression would now `exit(14)` rather than corrupt
  silently; a nonzero exit is also a control failure.

If the control fails, **nothing is measured** and this registration is closed
unmet.

## Frozen design

Identical to the parent registration.  Restated so this file is self-contained
and so no parameter can drift silently.

- **Host: c4 / mos182** only.  Xeon Platinum 8462Y+, socket 0, 15 CLOS,
  `cbm_mask=7fff`.  **Never mos181** — the runner says so and the reason is in
  the parent file.
- **Harness**: `experiments/asplos/run_silicon_e2e.sh` ->
  `silicon_e2e/run_hashjoin.py`, unmodified, at `HEAD`
  (`run_hashjoin.py` sha256 `fd815c6c772cec03fd60fcd7055b4b763b770370bd02d428c39de61047ef6700`,
  `gates.py` `0e63ebdeae826f5f11e008596d540ccaf173e9b23d754db1091b9887cf303013`),
  with `JOIN=` pointing at the scratch tenant.
- **21 arms, frozen**: `qui`, `wb`, `nta`, `fb64k`, `fb256k`, `fb1m`,
  `cat01` … `cat15`.  **5 reps**, arm order rotated per rep.  105 records.
- **Geometry, frozen**: fact **8 GiB** (`--fact 8589934592`), hash table
  **32 MiB** (`--hot 33554432`, 2^21 entries exact), `--hit-rate 1.0`,
  `--huge2m`, tenant CPU **4**, victim CPU **6**, `--fact-node 0 --hot-node 0`,
  inner `--reps 1`, `--warmups 0`, victim WSS 32 MiB, 20 trials co-run / 8
  quiet, 1.0 s each.
- **Pages**: `silicon_e2e/setup_hugepages_node0.sh` (node 0 -> 8192 × 2 MiB =
  16 GiB) is run **after the predecessor campaign has finished**, not before.
  Node 2, the cpuless node, is left untouched.
- **CAT**: `resctrl_clos.sh setup_b` — confine the polluter; victim stays in
  the root CLOS at the full 15 ways.  `cat15` is the control that should match
  `wb`.
- **Output**: outside the repo, `/home/domin/sil_e2e_rerun/out/` — a sibling of
  the predecessor's `/home/domin/ivf_run/`.  No `data/*.jsonl` is written or
  modified by this campaign.  Whether the new dataset supersedes the old one in
  `make_eval_frontiers.py` is a **separate decision** and is not taken here.

## Admission gates

Carried over unchanged, enforced by the committed runner: **G-idle**
(`load1 < 8` and zero foreign `comm` names, re-checked before *each* arm),
**G-mask** (schemata read back and compared as integers), **G-clos** (tenant
CPU in the intended CLOS, victim not), **G-live** (nonzero
`join_mtuples_per_s` and `matches` equal to the `wb` reference),
**G-size** (`fact_bytes` and `instantiated_hot_bytes` exact,
`HOT_TABLE_ROUNDED` absent), **G-mask-after** (post-measure re-read, closing
the setup-then-measure TOCTOU).

### G-exact — NEW, the gate the original could not have

> **`matches` must equal the exact full row count, 536,870,912, in every
> non-`qui` record.  Any deficit, of any size, VOIDs the run.**

The original registration could not write this gate because it did not know
the tenant was wrong; its **G-live** checks only that every arm reports the
*same* `matches` as `wb`, which the corrupted dataset satisfies perfectly —
all 100 tenant records agree on 534,773,760.  A cross-arm consistency check
cannot detect an arm-identical defect.  That is the whole lesson, and G-exact
is its fix: an **absolute** correctness assertion, anchored to arithmetic
(`fact_bytes / sizeof(Fact) × reps`) rather than to another measurement.

Enforcement, stated honestly:

- G-exact is evaluated **post-hoc by the registered analyzer** over every
  record, not inside `run_hashjoin.py`.  The runner is committed, shared with
  the IVF campaign and with the 105 records already published from it, and is
  deliberately **not modified** by this work.
- The consequence is that G-exact cannot abort the campaign mid-flight, only
  void it.  For a re-run whose entire purpose is correctness, voiding is
  sufficient: a voided dataset is not analysed and not cited.
- To avoid burning a full campaign on a known-answer question, the control
  above tests G-exact's predicate *before* the campaign, and the first `wb`
  record is checked against 536,870,912 as soon as it lands.
- `qui` records are exempt: no tenant runs, `matches` is `null` by
  construction.

### G-pred — NEW, precondition on the predecessor campaign

c4 was running the IVF-Flat silicon campaign (`run_ivf.py`, PID 2619758, ->
`/home/domin/ivf_run/ivf_silicon.jsonl`) when this was written.  Both campaigns
manipulate CAT/CLOS way masks, pin **the same cores 4 and 6**, and need node-0
hugepages; overlapping would silently corrupt both.

> **No arm of this campaign starts until the predecessor has finished
> *clean*: 105 records, every record `status=ok`, and the runner process
> gone.  Fewer than 105 records, or any record not `ok`, is a STOP — report,
> do not measure.**

A contaminated predecessor is exactly the situation in which a fail-closed
gate earns its keep, and the temptation to start anyway is the reason this is
written down in advance rather than judged on the day.

Note also — established by reading the source, before the fact — that the
predecessor's own G-idle would treat this campaign's tenant as a foreign
process: `cxl_join_bench` is in `ivf_gates.FOREIGN_COMM`, and `run_ivf.py`
`return 3`s on `skip_busy`. Executing our tenant on c4 during the IVF window
would not merely perturb it, it would **abort it permanently**.  This is why
even the positive control waits.

### G-tenant — NEW

> Every record's `sha_join` must equal
> `a677c52d05b75091057b5d9477fca99fef56e2087605457cfaf8f2b908a98431`
> and must **not** equal `75e0af94…`.  `sha_victim` must equal `026e357a…`,
> the original victim, unchanged.

### G-clean — NEW

> `sha256sum -c` of the three baseline manifests must pass after the campaign:
> no pre-existing binary and no pre-existing `data/*.jsonl` changed.

## Registered predictions

The scientific content of a re-run whose numbers are expected not to move is
entirely in the *size* of the non-movement, so it is quantified here, before
the data exists.

Coordinates are the paper's own, matching `make_eval_frontiers.py:91-98`
exactly: with `q`, `w` the median `victim_cyc_per_load` of `qui`, `wb` and
`tw` the median `join_mtuples_per_s` of `wb`,

    protection(a)  = 100 * (w - v_a) / (w - q)
    tenant_cost(a) = 100 * (t_a / tw - 1)

Deltas are **percentage points** (pp) of these quantities, clean minus
corrupted.

**Reproducibility envelope.**  Because only one clean campaign is run, an
observed delta cannot be decomposed into "defect effect" and "ordinary
run-to-run noise".  The envelope is therefore fixed *now*, from the
**corrupted dataset's own 5 reps** — a bootstrap over reps within arm,
B = 4000, seed 20260904, reported as the p95 of `|delta|` — and frozen in the
analyzer as `ENVELOPE_P95`:

| arm | protection pp | cost pp | | arm | protection pp | cost pp |
| --- | --- | --- | --- | --- | --- | --- |
| `wb` | 0.00 | 0.00 | | `cat06` | 1.71 | 0.18 |
| `nta` | 4.03 | 0.15 | | `cat07` | 3.75 | 0.19 |
| `fb64k` | 1.92 | 0.14 | | `cat08` | 9.28 | 0.12 |
| `fb256k` | 1.88 | 0.13 | | `cat09` | 3.11 | 0.12 |
| `fb1m` | 0.46 | 0.43 | | `cat10` | 1.87 | 0.42 |
| `cat01` | 0.05 | 0.09 | | `cat11` | 4.54 | 0.17 |
| `cat02` | 0.13 | 0.08 | | `cat12` | 1.22 | 0.16 |
| `cat03` | 0.66 | 0.09 | | `cat13` | 2.93 | 0.13 |
| `cat04` | 0.93 | 0.10 | | `cat14` | 1.28 | 0.20 |
| `cat05` | 1.13 | 0.13 | | `cat15` | 3.14 | 0.70 |

Two things this table says out loud.  Tenant cost is *very* reproducible
(p95 <= 0.70 pp, mostly <= 0.2 pp).  Protection is not, and its noise is not
uniform across arms — `cat08`'s 9.28 pp comes from a single rep at
150.7 cyc/load against a 141.8 median.  A threshold flat in the arm index
would be simultaneously too tight at `cat08` and far too loose at `cat01`.

- **D1 (per-arm protection).**  For all 20 non-`qui` arms,
  `|Δ protection| <= max(2.0 pp, 2 × ENVELOPE_P95[arm])`.
- **D2 (per-arm tenant cost).**  For all 19 tenant arms (excludes `wb`, whose
  cost is 0 by definition),
  `|Δ tenant cost| <= max(1.0 pp, 2 × ENVELOPE_P95[arm])`.
- **D3 (common mode).**  The corruption was arm-identical, so a real effect
  would appear as a *systematic* shift rather than scatter.  Mean signed
  `Δ protection` over the 15 CAT arms within **±2.0 pp**; mean signed
  `Δ tenant cost` over the same arms within **±0.5 pp**.
- **D4 (absolute apparatus reproduction).**  The ratio coordinates are
  insensitive by construction, so the absolutes are checked too:
  median `qui` victim cyc/load, median `wb` victim cyc/load, and median `wb`
  `join_mtuples_per_s` each within **±3 %** of the corrupted dataset's.

**D1–D4 all hold** => the delta is negligible, the "arm-identical, cancels in
ratio" mechanism is confirmed, and no published number moves.

**Any of D1–D4 fails** => the mechanism is *not* understood.  Then the
required action is to **say so loudly** in the outcome — prominently, not in a
footnote — and to treat every silicon e2e number as open pending diagnosis.
It is explicitly *not* permitted to relabel a material shift as a correction
and move on: the corrupted dataset would have to have been wrong in a way this
registration failed to predict, which is a bigger finding than the re-run.

Direction, for the record: the mechanical expectation is that clean rows are
marginally *slower* per row, since a corrupted key misses and a miss under
linear probing walks to the first empty slot; but at 1/256 of rows and with
`t` and `tw` both affected, the ratio should move well under 0.1 pp.

The parent registration's S1–S5 are **not** re-tested.  S2 is `UNTESTABLE` per
Amendment 1 and nothing here changes that.  Predictions about mechanism
efficacy were settled on the corrupted dataset and, because they too are
cross-arm, are not reopened by this run; if D1–D4 hold they stand unchanged,
and if they do not, they are all reopened at once.

## The 4K sibling

`data/silicon_e2e_hashjoin_4k.jsonl` is a second 105-record dataset from the
same defective tenant — same `sha_join` `75e0af94…`, same `matches`
534,773,760, same 2,097,152 deficit — differing only in `huge2m=false`, run
15:01:37 -> 15:43:02, before the node-0 pool was grown.  It is a page-size
sensitivity, stored separately per A6.19.

It is **assessed, not re-run**, by this registration.  A recommendation is
recorded in the outcome document; re-running it requires asking first.

## What this campaign cannot show

STREAMING itself — unchanged from the parent registration.  It also cannot
show that the *corrupted* numbers were fit to publish; it can only show
whether the corrected ones agree with them.  And it cannot reproduce
`75e0af94…`: that binary's source is an uncommitted working-tree state on c4
(`e8d10458…`, matching no commit), so the corrupted dataset is not
regenerable, which is precisely why the original file is retained rather than
replaced.
