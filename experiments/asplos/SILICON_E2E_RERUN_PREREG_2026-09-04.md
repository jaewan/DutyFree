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

---

# Addendum 1 — the apparatus is changed after results were seen

Date: 2026-09-04 (project-local).  Written and committed **after** the first
clean campaign produced a verdict and **before** the second campaign emits any
statistic.  This is a disclosure, not an absorption: the registration above is
not edited, the thresholds are not moved, and the reason for touching the
tenant at all is recorded here so a reader can judge it rather than discover
it.

## A1.1  What happened, and why this addendum exists

The clean re-run registered above **ran, and returned a split verdict**:

- **`G-exact` PASSED.**  All 100 tenant records reported `matches` exactly
  536,870,912, deficit 0.  The purpose of the re-run was met.
- **`D1` and `D2` FAILED**, on the three flush-behind arms.  `fb64k`,
  `fb256k` and `fb1m` moved **−26.0, −26.2, −26.4 pp** in tenant cost against
  a D2 limit of 1.0 pp, and **+12.2, +13.6, +16.1 pp** in protection.  `D3`
  and `D4` passed; the fifteen CAT arms and `nta` moved as predicted.

Per the D1–D4 clause above, that failure was reported loudly rather than
relabelled, and every silicon e2e flush-behind number was declared open
pending diagnosis.  Full record: `SILICON_E2E_RERUN_OUTCOME_2026-09-04.md`,
commit `7a72050`, with the localisation in its "material shift" section and a
first diagnosis in its §C (commit `49ffecb`).

The diagnosis has now been **verified independently** and a **repair made**.
Because that repair changes the measuring instrument after a result was seen,
it is registered here before it is used.

## A1.2  The diagnosis, verified rather than inherited

`abccb31` — the same commit that fixed the `prefault_region` corruption —
added the `--policy fbo` oracle arm as a `policy == "fbo"` test **inside**
`join_range_flushbehind`'s per-element loop.  `policy` is a
`const std::string &`, and `_mm_clflushopt`'s memory clobber prevents the
compiler proving the string's buffer is unmodified across an iteration, so the
predicate was re-evaluated as an out-of-line PLT call to
`std::string::compare(char const*)` **once per fact row — 536,870,912 times
per arm** — for an oracle that only functions under gem5.

Three checks were run against the two binaries themselves, not taken on trust
from the outcome document:

1. **Source.**  `join_range_flushbehind` in `HEAD`'s `b843d465…` differs from
   c4's uncommitted `e8d10458…` — the source `75e0af94…` was built from — by
   the added `fbo` branch and nothing else.  The `policy == "nta"` compare in
   the same loop is present in both.
2. **Call-site census, per function.**  Counting
   `std::string::compare(char const*)@plt` call sites inside each `join_range*`
   function:

   | function | `75e0af94…` | `a677c52d…` |
   | --- | --- | --- |
   | `join_range` (`wb`, `nta`, all `cat*`) | 1 | 1 |
   | `join_range_batched` | 1 | 1 |
   | `join_range_flushbehind` (`fb*` only) | **1** | **2** |

3. **Loop structure.**  In `a677c52d…` both calls are inside the loop body
   (`0x9388`–`0x946d`), against the `'nta'` literal at `0x17b73` and the
   `'fbo'` literal at `0x17070`.  In `75e0af94…` the single call is the `nta`
   one; the flush guard is reached with three ALU operations.

**This refines the account in the outcome document's §C**, which reads the
delta as "a `call` where the defective tenant does three ALU operations".
That is true at the point in the loop §C's excerpt starts, but the excerpt
begins *after* the `nta` call site, and so omits that `75e0af94…` also pays
one string compare per tuple.  The correct statement is that the regression is
**exactly one added compare per tuple**: the `nta` compare is in both binaries
and in *both* functions, so it cancels when flush-behind is differenced
against the plain join, and the `fbo` compare — which exists only in
`join_range_flushbehind` — does not cancel and is the entire delta.  The
quantitative accounting in §C is unaffected: the ≈8.44 ns/tuple it attributes
to the added call is the cost of one compare, which is what was added.

The four independently-measured symptoms all follow, and none of them
discriminate against this cause: confined to the flush-behind path
(`join_range` unchanged at one compare in both, and it is the path all
eighteen non-`fb` tenant arms take); flat across flush distances from 16 B to
1 MiB (the cost is per tuple, not per flush); independent of `hit_rate`
(the predicate is evaluated regardless of the probe result, and the gap
survives at `hit_rate` 0.0); and invisible to a flush-instruction census
(`clflushopt` 1, `clflush` 0, `sfence` 2, `prefetchnta` 17 in both — re-run
here and confirmed identical).  Blast radius re-verified against all 105
records of the clean run: exactly `fb64k`/`fb256k`/`fb1m` carry
`join_path=flushbehind`; `wb`, `nta` and all fifteen `cat*` carry
`join_path=join_range`.

## A1.3  The repair, and the fact that it is a repair

**Commit `77e06b66fd5756bf73b768ae7635a9d54c1751cf`**, one file, 8 insertions
and 1 deletion:

    const bool fbo = (policy == "fbo");   // once, before the loop
    ...
    if (fbo) { /* oracle */ } else if (/* flush guard, unchanged */) { ... }

**Exactly one thing is hoisted.**  The `policy == "nta"` compare in the same
loop has the same shape, and hoisting it would be faster, but it is present in
`75e0af94…` too — removing it would make this tenant non-comparable to the
archived dataset in a second, new way.  It is deliberately left alone.  After
the change the loop contains one string compare, as `75e0af94…`'s does.

**This removes an unintended regression; it does not tune toward a desired
number.**  Three things distinguish the two, and all three are checkable:

- The predicate is **loop-invariant by construction** — `policy` is a `const`
  reference the loop never writes — so the transformation is semantics-
  preserving and its result cannot depend on the data. `matches` and `sum` are
  bit-identical by inspection of the change.
- It was chosen from the **mechanism**, before the repaired binary was ever
  timed, not from the direction of a discrepancy.  Nothing about it can be
  adjusted to move a number: there is no parameter in it.
- The target it restores is the **archived** binary's behaviour, which is the
  reference D1/D2 are defined against.  It is not the direction that would
  make the paper's flush-behind claim more attractive; as the outcome document
  records, whichever way this lands, the ≈5–6 % figure means flush-behind's
  measured cost is what the *corrupted* dataset already reported, and the
  clean dataset's ≈32 % was an artefact of the measuring tenant.

## A1.4  The new tenant

| | |
| --- | --- |
| source | `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp` at `77e06b6` |
| source sha256 | `d197cf846b3bcc5c9fcf4984c301a4eb88b422a46a232d7f46daba66afe386ff` |
| build | `make BUILD=/home/domin/sil_e2e_fix/build native`, on c4, g++ 11.4.0, `-O3 -march=native`, no warnings |
| **tenant sha256** | **`344846d22b6c4d5fb2f73290dbaa861c8a53205a5791a7965aa7194e5a781209`** |
| victim | `026e357ae21a99717cae3ebf4ed05fa2cd146bda4f110afe4a2f7b829ef2db50`, reused not rebuilt, unchanged since the original 105 |
| runner | `run_hashjoin.py` `a4ce56a99db78a412ef6c2921f913670fdaf2a813833414476ca757a58989079` |
| `gates.py` | `0e63ebdeae826f5f11e008596d540ccaf173e9b23d754db1091b9887cf303013`, unchanged from the registration above |

Built from a `git archive` of `77e06b6` into `/home/domin/sil_e2e_fix/head_tree`
(the same 102 tracked paths the previous campaign staged), so the binary
corresponds to a commit.  That matters more than usual here: the *reason*
`75e0af94…` could not be bisected is that its source is in no commit, and
repeating that mistake on the binary sent to fix it would be worse than the
original.

**`G-tenant` is amended, and only in its target value.**  Every record's
`sha_join` must equal `344846d2…`, and must not equal `75e0af94…` or
`a677c52d…`.  `sha_victim` is unchanged at `026e357a…`.  Nothing else about
the gate changes.

## A1.5  A/B parity evidence, taken before this commit

Apparatus qualification, the analogue of the registered positive control:
`silicon_e2e/fb_parity_ab.py`, committed with this addendum.  Three binaries
run head to head, interleaved round-robin with the binary order rotated per
rep so host drift cannot alias onto one of them.  1 GiB fact, 32 MiB hash
table, `--huge2m`, tenant cpu 4, `hit_rate` 1.0, `--policy wb`, node 0 at its
as-found 1024 hugepages; 7 reps × 4 flush distances × 3 binaries = 84 runs, on
the idle host.  Raw: `/home/domin/sil_e2e_fix/out/fb_parity_ab.jsonl`.

Throughput, Mt/s, median over 7 reps:

    binary                          fd=0     fd=64 KiB    fd=256 KiB    fd=1 MiB
    75e0af94...  (published)      42.538        40.436        40.367      40.299
    a677c52d...  (regressed)      42.748        30.306        30.270      30.247
    344846d2...  (repaired)       42.737        40.475        40.439      40.370

Flush-behind cost, `100*(t_fd/t_fd0 - 1)`, each binary against its own `fd=0`,
medians of the per-rep ratio:

    binary                     fd=64 KiB    fd=256 KiB      fd=1 MiB
    75e0af94...  (published)     -5.015        -5.088        -5.201
    a677c52d...  (regressed)    -29.104       -29.154       -29.145
    344846d2...  (repaired)      -5.229        -5.419        -5.474

**The 1.34× gap is gone.**  `a677c52d…`/`75e0af94…` on the flush-behind path
was 0.7495 / 0.7499 / 0.7506 — a factor of 1.334.  `344846d2…`/`75e0af94…` is
**1.0010 / 1.0018 / 1.0018**, i.e. the repaired tenant is **+0.12 / +0.12 /
+0.18 %** *faster* than the published one on the very path that regressed,
against a within-binary spread of 0.15–0.54 % across reps.

**The residual, stated rather than rounded away.**  In the D2 coordinate the
repaired tenant sits **−0.21 / −0.33 / −0.27 pp** from `75e0af94…`, against a
pooled run-to-run standard deviation of 0.17 / 0.22 / 0.20 pp — about 1.2–1.5
sd, and 3–5× inside D2's 1.0 pp limit.  A second, independent 5-rep run put it
at −0.15 / −0.14 / −0.11 pp, so it is not stable in magnitude and is
consistent with noise.  Its sign is also accounted for without reference to
the `fbo` branch: on the **plain join** at `fd=0`, a path this change does not
touch and where both binaries emit one compare, the repaired tenant is
**+0.50 %** faster than `75e0af94…`, and the regressed build is +0.49 % faster
— i.e. the `fd=0` baseline difference between the archived binary and *either*
`HEAD` build is larger than the flush-behind difference, and it is that
baseline, not the flush-behind path, that makes the derived ratio ≈0.3 pp more
negative.  The flush-behind paths now agree with each other better than the
plain-join paths do.

**Whether a bool test was enough was measured, not assumed.**  A bool is still
a branch.  A fourth binary was built with the loop **split**, so the non-`fbo`
path carries no `fbo` test at all
(`c47dde3101873dc19281f5120a3300b339a4f6c3dcd760996f789cc205da482f`, a
throwaway probe outside the repository, not committed and not used for any
campaign), and A/B'd the same way over 5 reps.  Its flush-behind cost is
−4.89 / −5.02 / −5.11 %, i.e. **+0.08 / +0.13 / +0.16 pp** from `75e0af94…`,
where the committed one-line hoist is −0.15 / −0.14 / −0.11 pp in the same
run.  Both sit inside run-to-run spread and the split is not systematically
closer.  **The one-line hoist is therefore what is used**, and the minimal
change is kept.

**Correctness, at the same time and not traded against parity.**  `--mode
single --hit-rate 1.0 --reps 1 --warmups 0 --hot-bytes 33554432 --fact-node 0
--hot-node 0 --cpu-list 4 --policy wb`, at two `fact_bytes` a factor of 4
apart, on both page paths and both join paths, exit status 0 throughout:

    tenant       fact_bytes       pages    fd       matches       deficit
    344846d2...   268,435,456        4K     0    16,777,216             0
    344846d2...   268,435,456        4K   64K    16,777,216             0
    344846d2...   268,435,456   MAP_HUGETLB  0   16,777,216             0
    344846d2...   268,435,456   MAP_HUGETLB 64K  16,777,216             0
    344846d2... 1,073,741,824        4K     0    67,108,864             0
    344846d2... 1,073,741,824        4K   64K    67,108,864             0
    344846d2... 1,073,741,824  MAP_HUGETLB  0    67,108,864             0
    344846d2... 1,073,741,824  MAP_HUGETLB 64K   67,108,864             0
    75e0af94...   268,435,456   MAP_HUGETLB 64K  16,711,680        65,536 = fact/4096
    75e0af94... 1,073,741,824  MAP_HUGETLB 64K  66,846,720       262,144 = fact/4096

Deficit is exactly 0 for the repaired tenant on the `MAP_HUGETLB` path the
campaign uses, at both sizes, on the flush-behind path as well as the plain
one — and all 28 of its flush-behind runs in the 84-run A/B above also
reported deficit 0.  The archived binary reproduces `fact_bytes/4096` on
demand in the same conditions.  Both required properties hold simultaneously.

## A1.6  What is *not* amended

Stated explicitly, because the temptation after a gate fires is to widen it.

- **`G-exact` keeps its threshold.**  `matches` = 536,870,912 exactly, any
  deficit voids.
- **`D1`–`D4` keep their registered thresholds and the frozen
  `ENVELOPE_P95` table above, unchanged.**  `D1` is **not** loosened because
  it is now known what it caught.  If the flush-behind arms fail `D1`/`D2`
  again, that is a second uncontrolled difference between the binaries and is
  to be reported as a finding, in the terms the D1–D4 clause already requires.
- **`G-pred` remains `WAIVED`.**  Its condition FAILED; it was waived by the
  campaign owner at `d709bf7`, restored at `34f478a`.  It is not relabelled
  `PASS` here or anywhere.
- All other gates, the 21 arms, the 5 reps, the geometry, the operational
  pinning and the output-outside-the-repo rule are unchanged.
- The previous campaign's output is **preserved, not overwritten**: the clean
  105-record run stays at
  `/home/domin/sil_e2e_rerun/out/silicon_e2e_hashjoin_clean.jsonl`
  (`40f15aea…`) and this campaign writes a new file.

## A1.7  Precedence, checkable

- The repair is commit `77e06b6`; this addendum and `fb_parity_ab.py` are
  committed **after** it and **before** the campaign is launched.
- The A/B and correctness numbers quoted in A1.5 necessarily predate this
  commit — they are the evidence *for* it, and they are apparatus
  qualification at a geometry the campaign does not use (1 GiB, no victim, no
  CAT), not a campaign statistic.  This is the same standing the registered
  positive control has above.
- **No statistic from the second campaign predates this commit.**  The
  campaign's JSONL carries a per-record `ts`; the first record's `ts` is to be
  compared against this commit's author date, in-band and in git, never
  against a directory mtime.
