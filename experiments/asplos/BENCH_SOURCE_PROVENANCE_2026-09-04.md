# Benchmark tenant sources: what is now committed, and which campaign binaries it cannot rebuild

**2026-09-04.** `BUILD_PROVENANCE.md` is the precedent for this document's
format and conventions; it does for `gem5.opt` what this does for the **tenant**
binaries. Where that record tracks which simulator produced which cell, this one
tracks which *benchmark source state* produced which tenant binary — and, mostly,
records that the answer is no longer knowable.

*Dating note: this host's clock is KST (UTC+9), so commit timestamps for this
pass read `2026-09-05`; records in this directory are dated by project-local
time (UTC−7) and so are dated `2026-09-04`. Consistent with
`M5OP_RAX_CLOBBER_AUDIT_2026-09-04.md` and `BUILD_PROVENANCE.md`.*

`A1_PROVENANCE_LEDGER_2026-08-28.md` and `INDEX.md` are **not edited here**;
proposed wording for both is handed back in §9. Nothing under
`/home/domin/STREAMING_Paper/`, `gem5/src/` or `gem5.opt` was touched. **No arm
ran and no simulation was launched.** Host `c4` was not contacted and nothing
under `benchmarks/e2e/ivf_flat/` or the `silicon_e2e` paths was read, built or
committed. Work was done on `mos181`.

---

## 1. The statement this document exists to make

**Checking out any of these commits does not reproduce r5, and does not
reproduce any other campaign except one.**

The single exception is stated precisely in §5: `cxl_join_bench.gem5wbrk`
`2b9d6732…`, the `H1BW_SINGLECORE` tenant, is byte-reproducible from the state
committed here **minus one hunk** — today's `%rax` fix — and that is
demonstrated by rebuild, not asserted.

Everything else in the table is either gone, or survives as bytes whose source
state does not.

The sharpest way to put the r5 case: r5's binary was `401373ce…`, known only
because `run_complete_join.sh` wrote an `R5_JOIN` line into each launch log.
`bench_sha256` **was never populated in `r5_runs.jsonl`** — it is not a null
field, the key is absent from all 45 records — and an exhaustive host search
already recorded in the m5op audit found no file with that hash. The commits
here **post-date r5 and fix defects r5's binary contained**. §4 establishes by
measurement which, and §6 states what a reviewer can and cannot conclude.

---

## 2. The audit: every unversioned benchmark source

`git status --porcelain --untracked-files=all benchmarks/` filtered to
`.c/.cpp/.cc/.h/.hpp/.S`, cross-checked against
`git ls-files --others --ignored` so that a source hidden by an ignore rule
could not be missed. **Five files, and that is the complete set.**

| file | state | lines | committed here? |
|---|---|--:|---|
| `e2e/hash_join/src/cxl_join_bench.cpp` | tracked, **+1,103 / −29** | 2,974 | **yes** |
| `e2e/hash_join/w8/guest/m5mini.c` | tracked, **+8 / −0** | — | **yes** |
| `e2e/hash_join/src/streaming_h3_dirty_owner.cpp` | **untracked** | 170 | **yes** |
| `e2e/duckdb_mmap_probe/src/mmap_probe.cpp` | **untracked** | 519 | **yes** |
| `e2e/ivf_flat/src/ivf_flat_bench.cpp` | **untracked** | 1,252 | **no — out of bounds** |

`ivf_flat` is left untouched deliberately: a campaign is running on host `c4`
and the `ivf_flat`/`silicon_e2e` paths are excluded from this pass. It is
reported so the gap is on the record and not merely unnoticed — **it remains
unversioned, and three committed files name it**: `IVF_FLAT_SILICON_PREREG_2026-09-01.md`,
`run_silicon_ivf.sh` and `run_ivf_list_dom.sh`. That is an open `F13`-family debt
on the tenant side and is handed back in §9.3, not closed here. (`IVF_LIST_DOM_OUTCOME_2026-09-02.md`
itself does not name the source; the citation chain runs through the prereg and
the two runners.)

`benchmarks/bench/` is clean: its `.gitignore` whitelists `*.c`/`*.h` against
the binary-ignoring rule precisely so a new source cannot be silently ignored,
and no source under it is modified or untracked. `benchmarks/e2e/hnsw/` is
fully tracked.

### 2.1 Does any record cite the two untracked tenants?

Asked because the answer changes how load-bearing each is.

- **`mmap_probe.cpp` — yes, on the record twice.** `DUCKDB_MMAP_PROBE_OUTCOME_2026-09-02.md`
  (a **VOID** outcome, committed at `5f29346`), `DUCKDB_MMAP_SE_H2_HANDBACK_2026-09-04.md`
  (committed at `8da6499`), plus `run_duckdb_mmap_probe.sh`, `run_duckdb_mmap_se.sh`,
  `data/duckdb_mmap_probe.jsonl`, two committed artifact directories, and two
  untracked tests. Its registered tenant pin `2139aa85…` is named in the
  handback. **A committed record has been citing a source in no commit.**
- **`streaming_h3_dirty_owner.cpp` — cited, but no campaign.** Referenced by two
  `hash_join/Makefile` targets, by the untracked `w8/rcs/os_h3_dirty_owner.rcS`,
  and by `M5OP_RAX_CLOBBER_AUDIT_2026-09-04.md` §7.1/§7.2. **No outcome,
  prereg, `.jsonl` or run directory anywhere cites a result from it**, and its
  two binaries are attributed to nothing. It is committed because the Makefile
  already referenced a file that did not exist in any commit — `make
  h3-dirty-owner` was a target no clone could build.

### 2.2 Build directories

`benchmarks/e2e/hash_join/build/` **is** gitignored, by
`benchmarks/e2e/hash_join/.gitignore:2` (`/build/`). No binary from it is
tracked and none is proposed for tracking.

`benchmarks/e2e/duckdb_mmap_probe/build/` was **not** ignored by anything, so
committing that tenant as a directory would have swept two ELF binaries —
including the registered pin `2139aa85…` — into the history. A four-line
`benchmarks/e2e/duckdb_mmap_probe/.gitignore` is added alongside the source,
mirroring the hash_join one. The root `.gitignore` is **not** touched: it
carries another worker's uncommitted line and editing it would entangle this
pass with theirs.

---

## 3. How the diff was grouped, and what could not be separated

### 3.1 The constraint, measured rather than assumed

`git commit --only <pathspec>` is **file-atomic**. Verified in a scratch
repository rather than taken from the manual: with one hunk of a two-hunk change
staged via `update-index`, `git commit --only f.txt` committed the **whole
working-tree file** and discarded the partial staging. The documented behaviour
— "taking the updated working tree contents of the paths specified" — is the
observed behaviour.

So under the mandated commit form, **a file is the smallest possible commit**.
Splitting one file across commits would require either abandoning `--only` for
index-based partial staging, or writing intermediate versions of the file that
never existed. The second is exactly the "do not rewrite the code to make the
history prettier" prohibition, so neither was done.

### 3.2 What that costs, stated honestly

`cxl_join_bench.cpp` is **one commit containing four separate defect fixes plus
a large feature addition**, and no honest per-defect split of it is available.
That is not only a tooling limit — the hunks are genuinely interdependent, and
the dependency runs in the direction that prevents separation:

| # | change in the file | independent? |
|---|---|---|
| A | `%rax` as an output operand on the m5op wrappers | **only 2 of the 6 wrappers exist at `HEAD`**; the other 4 are new in this diff and are born with the fix applied |
| B | `prefault_region()` fail-closed guard + `what` parameter | self-contained |
| C | removal of the 7 `prefault_region` calls that ran after `fill_fact` | self-contained; one is coupled to the `prefault_seconds`→`declare_seconds` JSON rename |
| D | `hit_rate` threshold saturated at `UINT64_MAX` | **fully self-contained** — the one change that could have been its own commit |
| E | +846 lines: the `fs-e2e-calibrate` / `fs-e2e-join` / h2-admission modes, incl. the line-strided Sattolo shuffle | **calls** the 3-argument `prefault_region` from B and the new wrappers from A |
| F | `GEM5_FS` conditionals, multi-sample fail-closed PTE readback, `--window-brackets`, `fbo` policy | F's `fbo` arm calls `gem5_flush_range`, new in A |

E and F cannot compile without A and B. D could have been separated and, under
`--only`, was not. **That is the honest cost and it is not disguised**: the
commit message for that file names all four defects rather than claiming a
single subject.

### 3.3 One correction to the brief's description of the diff

The brief describes the Sattolo shuffle as "replacing an arithmetic stride".
**Relative to `HEAD` it replaces nothing**: the entire `fs-e2e-calibrate` mode
is new in this diff, so the arithmetic-stride version it replaced existed only
within the uncommitted session and is not in any commit. The same is true of
four of the six m5op wrappers. What is committed is the end state; the
intermediate states the session passed through are **not recoverable from this
history**, and no commit message here implies otherwise.

### 3.4 The commits

Ordered so that **every intermediate state builds** — verified, not assumed
(§7.3).

| # | commit | pathspec | subject |
|---|---|---|---|
| 1 | `c0527e5` | `w8/guest/m5mini.c` | fault in the `readfile` buffer before gem5's VM proxy writes it |
| 2 | `0d5c6a9` | `src/streaming_h3_dirty_owner.cpp` | track the H3 dirty-owner tenant (new file) |
| 3 | `73da510` | `hash_join/Makefile` | restore the buildable gem5 targets; add the h3 and separate-name window targets |
| 4 | `abccb31` | `src/cxl_join_bench.cpp` | the tenant: four defect fixes and the FS e2e modes |
| 5 | `f3b94f8` | `hash_join/README.md` | name the official STREAMING cell |
| 6 | `20d2fc7` | `w8/build_rootfs_t4.sh` | `EXTRA_BINS`, and an image-provenance sidecar |
| 7 | `a2e79f1` | `duckdb_mmap_probe/` (4 files) | track the DuckDB mmap-probe tenant (new) |
| 8 | *this record* | `experiments/asplos/BENCH_SOURCE_PROVENANCE_2026-09-04.md` | |

All eight sit on `main` above `58b7558`, another worker's `F19` registration,
which landed while this pass was running. **11 files, 0 binaries.**

Commit 3 is separated from commit 4 because it is a **defect in its own right**,
not packaging: see §7.2.

---

## 4. The `prefault_region` corruption, and whether r5's arms were affected

### 4.1 What the record already establishes, cited rather than re-derived

`FS_COMPLETE_JOIN_PREREG_2026-09-02.md` addendum 5 (deferred item 1) and
addendum 6 already identify and **measure** this defect. Quoting addendum 6
rather than restating it:

> `prefault_region(fact, ...)` ran immediately after `fill_fact` had already
> written every byte of the object, so it was redundant — and it mutates:
> `q[off] = q[off] + 1` on the first byte of every page and on the last. […]
> tuples in a 32 MiB fact 2,097,152 | keys altered by prefault **8,192
> (0.391%)** | pages in 32 MiB **8,192** — one corrupted key per page […] It is
> symmetric across arms at a seed, so the `matches` cross-check passed and the
> measurement was not materially moved — but the tenant was not computing the
> join it reported.

That record scopes the finding to the **FS r6 path and the silicon campaign**.
**It does not address r5**, and no other record in this directory does: a search
for `r5` and `prefault` jointly across `experiments/asplos/*.md` returns
nothing. So the r5 question was open, and is settled below.

### 4.2 r5 was affected, and this is measured, not inferred

r5 ran `--mode single` (`run_complete_join.sh:37-38`), and at `HEAD`
`run_single` calls `fill_fact()` at `cxl_join_bench.cpp:1162` and
`prefault_region(fact, c.fact_bytes)` at **`:1163`** — immediately after. So the
call was on r5's executed path, structurally.

It is better than structural. The corruption leaves an **in-band fingerprint**:
the reported `matches` count. Both tenant states were built native and run at
r5's exact geometry (`--mode single --policy wb --fact-bytes 8388608
--hot-bytes 4194304 --reps 1 --warmups 0 --hit-rate 0.5`, default seed
`13835551735702238294`):

| source state | `matches` | `correct` |
|---|--:|---|
| `HEAD` (`prefault_region` runs after `fill_fact`) | **260,875** | `true` |
| the m5op audit's independent r5-era reconstruction (`/tmp/m5audit/r5era.cpp`) | **260,875** | `true` |
| committed here (call removed) | **261,864** | `true` |

**260,875 is exactly the count every one of r5's 42 join cells reported**
(`M5OP_RAX_CLOBBER_AUDIT_2026-09-04.md` §3.2, from the r5 launch logs). Two
independent pre-fix source states reproduce it; the fixed state does not.

**r5's binary ran the corrupting prefault.** The arithmetic matches the FS
measurement exactly: an 8 MiB fact is 2,048 pages and 524,288 tuples of 16 B, so
**2,048 keys were corrupted — 0.391%**, the same rate addendum 6 measured at
32 MiB. The cost is 989 matches, against ~1,024 expected at `hit_rate 0.5` and a
Bernoulli σ of ~362.

**Note what `correct: true` did *not* catch.** It is `true` in every row above,
including the corrupted ones, because the reference is computed over the same
corrupted array. The cross-check cannot see this defect — which is the point
addendum 6 made and this is independent confirmation of it.

### 4.3 What this does and does not do to r5's published numbers

**It does not move them, and the reason is structural rather than lucky.** The
mutation is a deterministic function of the fact region's size and page layout,
both identical across every r5 arm at a seed. Every r5 cell reports the same
260,875. r5's claims — `R(h2) = 22.59%`, `+5.35%`, `+9.97%`, `+8.42%`, the
1.185× WB tax — are **all cross-arm comparisons**, and a defect common to
every arm cannot distort a comparison between arms. This is the same argument
`F18` used for r5's realized L3 geometry, and it holds here for the same reason.

**What is damaged is the description, not the magnitude**: r5's tenant was not
computing the join it reported, and 0.391% of its probes missed for a reason
that has nothing to do with the workload. That belongs in the record and is why
it is here.

**Not claimed:** that `HEAD` is r5's source. Reproducing `matches` proves the
defect was present and that `fill_fact`/`build_table`/`prefault_region` behaved
identically at this geometry. Many source states satisfy that. It is a
**necessary, not sufficient** condition, and §5 shows that neither `HEAD` nor
the r5-era reconstruction rebuilds `401373ce…`.

### 4.4 The other three fixes, scoped against r5

| fix | did r5's binary contain the defect? | did it affect r5? |
|---|---|---|
| `prefault_region` mutation | **yes** | yes, 2,048 keys — §4.2/§4.3 |
| `hit_rate` saturation at `UINT64_MAX` | **yes** | **no.** The UB is reached only at `hit_rate = 1.0`; r5 ran `--hit-rate 0.5`, well inside the representable range |
| m5op `%rax` under-declaration | **yes** | **no** — already settled, and not re-derived. `M5OP_RAX_CLOBBER_AUDIT_2026-09-04.md` §1/§3.2 records r5 as **CLEAN** on in-band run evidence |
| line-strided Sattolo shuffle | **n/a** | the `fs-e2e-calibrate` mode did not exist at r5 (§3.3) |

---

## 5. The provenance table

Bytes were verified on disk by `sha256sum` in this pass. "Rebuildable from this
commit" was established by **actually rebuilding** each candidate source state
with the Makefile's exact flags and comparing digests — not by argument.

| tenant binary | sha256 | campaigns that used it | bytes survive? | hash ever recorded? | rebuildable from this commit? |
|---|---|---|---|---|---|
| `cxl_join_bench.gem5` **as r5 ran it** | `401373ce…` | **`COMPLETE_JOIN` / r5** — `fig:frontier`(a), 45 cells | **NO** — overwritten in place | **only in `/tmp/r5` launch logs** (`R5_JOIN`). **Absent from `r5_runs.jsonl`** | **NO** |
| `build/cxl_join_bench.gem5` | `cac9e27a…` | `H1BW_MULTICORE`, `H1BW_CXLBW`, `H1BW_SLICE_BRACKET` — 39 records | yes | **yes**, `bench_sha256` ×39 | **NO** — rebuilds to `ff982918…` |
| `build/cxl_join_bench.gem5wbrk` | `2b9d6732…` | `H1BW_SINGLECORE` — 19 records | yes | **yes**, `bench_sha256` ×19 | **YES, minus one hunk** — see §5.1 |
| `build/cxl_join_bench.gem5fs` | `6216571a…` | none attributed | yes | no | **NO** — rebuilds to `fb79f834…` |
| `build/cxl_join_bench_w7.gem5` | `9dadce49…` | none; cited as r5's nearest surviving relative | yes | no | **NO** |
| `build/cxl_join_bench` (native) | `75813707…` | none attributed | yes | no | **NO** — rebuilds to `5808803a…` |
| r6b guest `cxl_join_bench.gem5fs` | `9bd3d1e3…` | `FS_COMPLETE_JOIN` r6b | **yes, inside the committed disk image** | **yes**, `guest_bench_sha256` in the run manifest | **NO** |
| r6e guest `cxl_join_bench.gem5fs` | `db41495d…` | `FS_COMPLETE_JOIN` r6e | **yes, inside the committed disk image** | **yes**, `guest_bench_sha256` | **NO** |
| `duckdb_mmap_probe/build/mmap_probe.gem5` | `2139aa85…` | `DUCKDB_MMAP_SE_H2` registered pin; campaign **VOID**, no arm ran | yes | **yes**, in the handback | **NO** — rebuilds to `c730f5fe…`, exactly as the m5op audit §7.3 predicted |
| `duckdb_mmap_probe/build/mmap_probe` (native) | `8a77be74…` | `DUCKDB_MMAP_PROBE` (VOID outcome, `5f29346`) | yes | **yes**, in the handback | **YES, byte-identical** — the `%rax` fix is inert without `-DGEM5` |
| `build/streaming_h3_dirty_owner.gem5` | `b6a2434f…` | **none** | yes | no | **YES, minus one hunk** (§5.1) |
| `build/streaming_h3_dirty_owner.gem5fs` | `9bf4a9f5…` | **none** | yes | no | **YES, byte-identical** — the fix is codegen-neutral in the FS build |

Which of today's fixes each binary **predates**: every binary in this table was
built before this pass, so **all of them predate all four fixes**. The FS/r6
guest binaries additionally predate the fixes that landed between r6e and r6f,
which `FS_COMPLETE_JOIN_PREREG_2026-09-02.md` addendum 6 already records.

### 5.1 The one genuine recovery, and its limit

`/tmp/m5audit/cxl_join_bench.cpp.before` — the working tree as it stood before
the m5op audit's `%rax` edit — rebuilds under the Makefile's `gem5` flags to:

```
2b9d67320ff86999b5e8e3d2cb98479043c3da62bbaa6135304a53ff48d9efad
```

which is **byte-identical to `build/cxl_join_bench.gem5wbrk`**, the
`H1BW_SINGLECORE` tenant named by 19 recorded `bench_sha256` values. Because
that pre-edit state is exactly the committed state minus one reviewable hunk,
committing this file makes `H1BW_SINGLECORE`'s tenant **reconstructible for the
first time**. Before this commit its source existed in no commit at all.

Two limits, stated so this is not read as more than it is. It is a
reconstruction *recipe* — revert the `%rax` hunk from commit 4 — not a checkout;
no single commit in this history builds `2b9d6732…`. And it says nothing about
`cac9e27a…`, the binary behind 39 records, whose source state remains lost.

### 5.2 Reproducibility caveat found while doing this

These builds embed the **source file's basename**. Compiling identical content
as `now.cpp` rather than `streaming_h3_dirty_owner.cpp` yields a different
digest; the containing directory does not matter (verified both ways). So every
digest above was produced by compiling from the real filename under a `src/`
directory, as the Makefile does. A future check that ignores this will get
spurious mismatches.

---

## 6. What a reviewer checking out these commits can and cannot reproduce

Stated plainly, because it is the point of the record.

**Can:**

- Build every target the Makefile offers, on all three configurations
  (`native`, `gem5`, `gem5fs`, `gem5-window`, `w7`, `h3-dirty-owner`,
  `h3-dirty-owner-fs`) — which, as §7.2 records, **no previously committed state
  of this repository could do**.
- Pass both `cxl_join_bench` self-tests.
- Read the source of the tenant behind `COMPLETE_JOIN`/r5, every `H1BW_*`
  campaign, the Intel silicon campaigns and the r6 FS generation — for the first
  time from a commit.
- Reconstruct `H1BW_SINGLECORE`'s tenant binary `2b9d6732…` by reverting one
  hunk (§5.1).
- Rebuild the DuckDB probe's native binary `8a77be74…` byte-identically, and the
  h3 FS binary `9bf4a9f5…` byte-identically.

**Cannot:**

- **Reproduce r5.** Its binary `401373ce…` no longer exists, its bytes were
  never preserved, `bench_sha256` was never populated in `r5_runs.jsonl`, and
  the source state that built it was never committed. Nothing in this history
  builds it and nothing here should be read as claiming otherwise.
- **Reproduce `cac9e27a…`**, and therefore the 39 records of
  `H1BW_MULTICORE` / `H1BW_CXLBW` / `H1BW_SLICE_BRACKET` from source. The bytes
  survive on disk and are hash-matched to their archives; the source state does
  not survive.
- **Reproduce any of the four defects as r5 experienced them by checking out
  these commits** — they are *fixed* here. The corrupting `prefault_region`
  calls are deleted, so a checkout computes a **different join** from r5's:
  261,864 matches against r5's 260,875 (§4.2). A reviewer who runs this source
  at r5's geometry and gets r5's number has made an error.
- **Recover the intermediate states of the session** that produced this diff —
  including the arithmetic stride the Sattolo shuffle replaced (§3.3).

---

## 7. Verification

### 7.1 No campaign binary was overwritten

Digests of all 15 binaries under `benchmarks/e2e/hash_join/build/` and
`benchmarks/e2e/duckdb_mmap_probe/build/` were recorded **before** any build and
`sha256sum -c`'d after. **All 15 OK.**

Every build in this pass went to `/tmp/bench_verify/`, `/tmp/cjbctl/` or
`/tmp/h3ctl/`, via `make BUILD=<scratch>`. This mattered concretely and was not
a formality: **`make gem5` writes `build/cxl_join_bench.gem5`, which is
`cac9e27a…`** — the binary 39 records name. Running the Makefile's own target in
place would have destroyed it, which is the `F13` failure exactly, and the
`gem5.opt.pre-npot-guard.cb290444` precedent applied to the tenant side.

The duckdb `gem5` target hardcodes `build/mmap_probe.gem5` rather than taking a
variable, so it **cannot** be redirected; that one compile was hand-replicated
with the Makefile's exact command line into scratch. Flagged as a follow-up in
§9.3 — a target that cannot be redirected is a target that will eventually
overwrite the pin.

**Binaries that must not be overwritten**, consolidated: `cac9e27a…`
(`build/cxl_join_bench.gem5`, 39 records), `2b9d6732…` (`.gem5wbrk`, 19
records), `2139aa85…` (`mmap_probe.gem5`, registered pin), `8a77be74…`
(`mmap_probe`, recorded in the handback), and — from the m5op audit, not
rechecked here — `gem5/testcase/dutyfree/victim` `1f6214b8…`, which is byte-identical
to the `R5_VICTIM` in r5's own logs. `9dadce49…` and `6216571a…` carry no
attribution but are the last surviving relatives of lost binaries and should be
treated the same way.

### 7.2 `HEAD` does not build, and commit 3 is the fix

Attempting `make gem5` at `HEAD` — `HEAD`'s source with `HEAD`'s flags — fails:

```
clflushoptintrin.h:39:1: error: inlining failed in call to 'always_inline'
  'void _mm_clflushopt(void*)': target specific option mismatch
```

`HEAD`'s `join_range_flushbehind` calls `_mm_clflushopt` while `HEAD`'s Makefile
omits `-mclflushopt` from the `gem5`, `gem5fs` and `w7` recipes. The `native`
target survives only because `-march=native` happens to enable the feature on
this host.

**So no committed state of this repository has ever been able to build the gem5
tenant**, and every gem5 tenant binary in §5 was necessarily built from an
uncommitted tree. That is a large part of why so few of them are reproducible,
and it is a distinct defect from the missing sources — which is why the Makefile
is commit 3 and not folded into commit 4.

### 7.3 Builds

All seven `hash_join` targets, built to scratch, **exit 0**. Warnings only:
`-Wunused-parameter` on `huge2m`/`stream_count` and one `-Wunused-function` on
`flush_cache_region` in the FS configuration — all pre-existing in kind, none
introduced by the grouping.

`duckdb_mmap_probe`: `all` and `gem5` both build.

Every intermediate commit state was checked, not just the tip: `HEAD`'s source
compiled against commit 3's Makefile builds both `gem5` and `gem5fs` cleanly, so
the tree is buildable at commit 3 as well as at commit 8.

### 7.4 Tests

| suite | result |
|---|---|
| `cxl_join_bench --self-test reference` | **ok** — `matches 262262`, `sum −9012` |
| `cxl_join_bench --self-test numa --fact-node 2 --fact-bytes 268435456` | **ok** — `sampled_pages=4096 node2=4096` |
| `make test` (repo, 138 tests) | **1 failure**, 1 skipped — see below |

The failure is `test_fs_join_analyze.TestFsJoinAnalyzeDryRun.test_p1_zero_bypass_is_void_not_negative`.
It is **pre-existing and outside this pass's scope**, and both halves of it are
another worker's in-flight work: the test file `tests/test_fs_join_analyze.py`
is **untracked**, and its subject `benchmarks/e2e/hash_join/w8/fs_join_analyze.py`
is **untracked**. The test asserts the literal string `arm == "h2" and byp <= 0`
appears in the analyzer; the analyzer has since been restructured and expresses
the same fail-closed rule differently. Neither file is in any pathspec committed
here, and no file committed here is imported by that test. It was failing before
this pass began — nothing was edited to make it so, and nothing was edited to
hide it.

Note for whoever owns it: `make test` runs `unittest discover`, which picks up
**untracked** test files, so this failure is invisible to a clone and appears
only in a dirty tree. That is worth fixing in the same pass as the assertion.

### 7.5 Hygiene

- **No binary, build output, log or large artifact was committed.** The eight
  commits touch exactly the eleven files listed in §3.4.
- `git commit --only` with explicit pathspecs throughout; the index was
  confirmed empty after every commit and after the last.
- **Not pushed.**
- `.gitignore` (root), `A1_PROVENANCE_LEDGER_2026-08-28.md`, `INDEX.md`,
  `gem5/src/`, `gem5.opt` and `/home/domin/STREAMING_Paper/` are unmodified.
  The many other modified and untracked files in this working tree —
  `AUDIT.md`, the root `Makefile`, `tests/`, `experiments/`, the whole
  `w8/rcs/` and `w8/run_*.sh` harness — are **left exactly as they were**.

---

## 8. What this pass deliberately did not do

- **`ivf_flat` is still unversioned** (§2). Out of bounds this pass.
- **`/tmp/r5` is still load-bearing and still in `/tmp`.** The m5op audit
  flagged this; it is repeated because §4.2 now depends on it too — the 45 r5
  launch logs are the only surviving record of `R5_JOIN 401373ce…`, and they
  sit in exactly the kind of location that lost the binary in the first place.
  Not committed here: they are another campaign's artifacts and this record is
  not their owner.
- **`/tmp/m5audit/` is now load-bearing as well**, which was not true this
  morning. It holds `cxl_join_bench.cpp.before` — the only copy of the source
  state that builds `H1BW_SINGLECORE`'s `2b9d6732…` (§5.1) — and the extracted
  r6b/r6e guest binaries. §5.1's recipe survives this (revert one hunk from
  commit 4), but the r6 extractions do not.
- **No arm was re-run and no binary was rebuilt in place**, so no apparatus
  deviation is created by this pass. The `DUCKDB_MMAP_SE_H2` pin `2139aa85…` is
  still intact on disk; §5 records that the committed source no longer builds
  it, which is the deviation the m5op audit §7.3 already said must be declared
  before any future arm.

---

## 9. Handed back, not applied

### 9.1 Proposed `A1_PROVENANCE_LEDGER_2026-08-28.md` wording

**This is an extension of `F13`, not a new number.** `F19` (the m5op `%rax`
under-declaration) was registered by another worker at `58b7558` while this pass
was running; it was read here and it covers the clobber only — not tenant source
tracking, not r5's `prefault_region`, not `ivf_flat`. So nothing below
duplicates it and nothing here needs a new class. Proposed as an append to the
existing `F13` row:

> **`F13` extends to the tenant side, and the tenant side is worse.** Registered
> for the simulator on 2026-09-04. `BENCH_SOURCE_PROVENANCE_2026-09-04.md`
> establishes the same defect for the **benchmark tenants**, where it had gone
> unregistered: `cxl_join_bench.cpp` was **1,103 insertions ahead of `HEAD`**,
> and `mmap_probe.cpp` — cited by a committed VOID outcome (`5f29346`) and a
> committed handback (`8da6499`) — was **untracked entirely**. The aggravating
> finding is structural rather than procedural: **`HEAD` could not build the
> gem5 tenant at all**, because `join_range_flushbehind` calls `_mm_clflushopt`
> while the Makefile omitted `-mclflushopt`, so *every* gem5 tenant binary this
> project has ever produced was necessarily built from an uncommitted tree. Of
> the twelve tenant binaries tabulated, **one** is byte-reproducible from the
> now-committed source minus a single reviewable hunk (`2b9d6732…`,
> `H1BW_SINGLECORE`, 19 records — recovered here, previously in no commit);
> `cac9e27a…` (39 records) is **not** reproducible and its source state is lost;
> r5's `401373ce…` is **gone**, was never preserved, and `bench_sha256` **was
> never populated in `r5_runs.jsonl`** — the key is absent from all 45 records,
> so unlike `cac9e27a` it cannot even be hash-matched. **A new measured fact
> about r5, not previously recorded anywhere:** r5 ran `--mode single`, whose
> `HEAD` path calls `prefault_region()` immediately after `fill_fact()`, so
> **r5's binary corrupted 2,048 of its 524,288 fact keys (0.391%)** — the defect
> `FS_COMPLETE_JOIN_PREREG_2026-09-02.md` add. 6 measured on the FS path and
> scoped only there. This is proven, not inferred: `HEAD`'s source and the m5op
> audit's independent r5-era reconstruction both reproduce **260,875** matches
> at r5's exact geometry — the count all 42 r5 join cells reported — while the
> fixed source gives 261,864. **No published magnitude moves**, for the same
> structural reason `F18` gave for r5's realized L3 geometry: the mutation is
> identical in every arm at a seed and every r5 claim is a cross-arm comparison.
> What is damaged is the description — r5's tenant was not computing the join it
> reported — and `correct: true` could never have caught it, because the
> reference is computed over the same corrupted array. **Still open on the
> tenant side:** `ivf_flat_bench.cpp` remains untracked while three committed files name it
> (`IVF_FLAT_SILICON_PREREG_2026-09-01.md`, `run_silicon_ivf.sh`,
> `run_ivf_list_dom.sh`); a campaign on `c4` put it out of bounds this pass.

### 9.2 Proposed `INDEX.md` row

> | `BENCH_SOURCE_PROVENANCE_2026-09-04.md` | **`PROVENANCE`** — the tenant-side
> counterpart to `BUILD_PROVENANCE.md`, and the close-out of the benchmark half
> of `F13`. Commits the sources behind `COMPLETE_JOIN`/r5, every `H1BW_*`
> campaign, the silicon campaigns and the r6 FS generation, which were
> **1,103 insertions ahead of `HEAD`**, plus two tenants that were **untracked**
> while committed records cited them. Tabulates twelve tenant binaries against
> campaign, byte survival, whether the hash was ever recorded, and
> rebuildability. **`H1BW_SINGLECORE`'s `2b9d6732…` is recovered** — byte-identical
> from the committed source minus one hunk, previously in no commit — while
> `cac9e27a…` (39 records) is not reproducible and **r5's `401373ce…` is gone,
> unpreserved, and was never hashed into `r5_runs.jsonl`**. Establishes by
> measurement, for the first time, that **r5's binary ran the corrupting
> `prefault_region`**: `HEAD` reproduces r5's own 260,875 matches and the fix
> gives 261,864, so 2,048 fact keys (0.391%) were corrupted in every r5 cell —
> **no published magnitude moves**, the defect being common to all arms of a
> cross-arm comparison. Finds that **`HEAD` could not build the gem5 tenant**
> (`_mm_clflushopt` without `-mclflushopt`), so every gem5 tenant binary ever
> produced came from an uncommitted tree. States that **checking out these
> commits does not reproduce r5** and that a reviewer who obtains r5's match
> count from this source has erred. No arm ran; no campaign binary overwritten
> (15 verified byte-identical); `ivf_flat` left unversioned, out of bounds |

### 9.3 Follow-ups for other owners

1. **`benchmarks/e2e/ivf_flat/` needs committing** once `c4` is idle, with the
   same table treatment. `IVF_FLAT_SILICON_PREREG_2026-09-01.md`,
   `run_silicon_ivf.sh` and `run_ivf_list_dom.sh` — all committed — name it.
2. **`duckdb_mmap_probe/Makefile`'s `gem5` target hardcodes its output path** and
   cannot be redirected to scratch, so the next person to run it will overwrite
   the registered pin `2139aa85…`. It should take `BUILD`/`BIN` like the
   hash_join Makefile does. Not changed here — it is the duckdb campaign's file
   and the change deserves its owner's review.
3. **`tests/test_fs_join_analyze.py` and `w8/fs_join_analyze.py`** are an
   untracked test failing against an untracked subject (§7.4), and the failure
   is invisible to a clone. Handed to the fs-e2e harness owner, along with
   `tests/test_duckdb_mmap_probe.py`, `test_duckdb_mmap_se_h2.py`,
   `test_duckdb_tenant_cat.py`, `test_ivf_list_dom.py` and `test_silicon_e2e.py`,
   all untracked.
4. **`/tmp/r5` and `/tmp/m5audit/cxl_join_bench.cpp.before` should be preserved
   into the repository** (§8). Both are now cited by committed records.
5. **The `w8/` harness is still almost entirely untracked** — 40+ `rcS` files,
   nine `run_*.sh` campaign launchers and four analyzers — which is `F10`
   (a result whose launcher was never committed) waiting to happen for the
   FS e2e generation. Out of scope here; this pass committed only the two `w8`
   files that are build inputs rather than launchers.
