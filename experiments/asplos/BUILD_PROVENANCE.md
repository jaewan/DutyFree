# Build provenance: which `gem5.opt` produced which cell, and how to rebuild it

Living document, like `INDEX.md`. Append a row when a binary is built; never
edit a row once cells have been attributed to it.

This exists because on 2026-09-04 at 12:51 `gem5/build_Intel_8592/gem5.opt` was
replaced in place. The binary it replaced, `cfd37207...`, had produced **every
published magnitude** in the `h1bw_multicore`, `h1bw_cxlbw` and
`h1bw_slice_bracket` campaigns, and at the moment of replacement its source
state was captured by no commit and existed only in a chat transcript. A
transcript is not an artifact. This is a new provenance defect in the sense of
`A1_PROVENANCE_LEDGER_2026-08-28.md`, and it is the same family as `F10` (a
result whose launcher was never committed) applied to the simulator itself
rather than to the harness. It is proposed as **`F13`** — next free number;
`F10`/`F11`/`F12` are taken and `F16` in `M1_OUTCOME` is a workload name, not a
defect.

## 1. The binaries

Three binaries are involved. All three are now recoverable from the repository.

| ref | sha256 | compiled | on disk | cells |
|---|---|---|---|---|
| `build-cfd37207` | `cfd37207b9b7124ae88af7192178518b21c89b44a84d582efa69960ce19b9ed1` | 2026-08-31 12:40:39 | **gone** (overwritten 09-04 12:51) | 21 |
| `build-481d7e12` | `481d7e123f407e9ff6d3f94ba89b6ef2db795a3154785863c37b82025493b81b` | 2026-09-03 ~11:53 | `gem5/build_Intel_8592_FBO/gem5.opt` | **0** |
| `build-cb290444` | `cb2904444d5c5c4d31d9d8f07295209283d29e294ef1d885d789442d98e7bbe0` | 2026-09-04 12:47:48 | `gem5/build_Intel_8592/gem5.opt` | 3 (in flight) |

Tags are annotated; `git show <tag>` carries the same statement as this section.
Commits, oldest first:

```
831b994d27  Ruby/CHI: count the LLC fill opportunities H2 actually declines
289809c73f  CHI: refuse a STREAMING request that is not a load or instruction fetch
9b57294b94  CHI: materialize the retained TBE data block when ReadOnce hits upstream
830905739a  Ruby.py: per-range SimpleMemory bandwidth ceilings   <- tag build-cfd37207
1bb6418e01  m5 op 0x57 flush_range: an idealised flush-behind oracle  <- tag build-481d7e12
3bd36a0061  fs checkpoint: bind a checkpoint to the kernel, image and simulator
f3c2c84949  fused: reset stats after the tenant's own init
b9c8714c93  CHI: carry isStreaming across the request retry path
a5f366456e  ticks: compare the magnitude of the rounding error       <- tag build-cb290444
```

All nine sit on `pr4-work` above `b0eea53b5b`. The chain reproduces the working
tree that built `cb290444` file for file:

```
git diff build-cb290444 -- $(git diff --name-only b0eea53b5b..build-cb290444)
```

is empty across all fifteen files that were uncommitted. One commit was added
*after* the tag — `fa27f665db`, `scripts/build_gem5.sh`, the §5 prevention — so
`build-cb290444` is no longer the branch tip. That file is a shell script, is
not compiled or marshalled into `gem5.opt`, and cannot affect the three cells
in flight.

**Rebuild:** `git checkout <ref>` then `scons build_Intel_8592/gem5.opt`.

**What a rebuild will not do.** It will not reproduce these sha256 values. gem5
embeds its own compile timestamp (`base/date.cc`) and embeds build-directory
paths into generated sources — the generated
`mem/ruby/protocol/CHI/Cache_Controller.cc` header comment differs between
`build_Intel_8592` and `build_Intel_8592_FBO` for that reason alone. Only
**behavioural** equivalence is claimed, and the claim is that the compiled and
marshalled sources are the same, not that the bytes are.

## 2. Binary-to-cell mapping

Authority for this table is the binary's own startup banner, `gem5 compiled
<date>`, present in each run's `console.log`. It is emitted by the binary that
actually ran, so it cannot drift from `MANIFEST.json`'s `gem5_sha256` the way a
hash recorded by the launcher can. The two agree in all 24 directories.

All directories are under `gem5/logs/se_chi/`. All 21 completed cells have
`DONE.json` with `"exit":0`.

### Produced by `cfd37207` — tag `build-cfd37207` (21 cells, all published)

| cell | arm | cores | slices | CXL bw |
|---|---|--:|--:|---|
| `h1bw_mc_{wb,h2,pfoff}_4c_20260904` | wb / h2 / pfoff | 4 | 4 | default |
| `h1bw_mc_{wb,h2,pfoff}_8c_20260904` | wb / h2 / pfoff | 8 | 8 | default |
| `h1bw_mc_{wb,h2,pfoff}_4c_l3x4_bwt31_20260904` | wb / h2 / pfoff | 4 | 4 | 31 ticks/B |
| `h1bw_mc_{wb,h2,pfoff}_4c_l3x4_bwt16_20260904` | wb / h2 / pfoff | 4 | 4 | 16 ticks/B |
| `h1bw_mc_{wb,h2,pfoff}_8c_l3x8_bwt31_20260904` | wb / h2 / pfoff | 8 | 8 | 31 ticks/B |
| `h1bw_mc_{wb,h2,pfoff}_8c_l3x8_bwt16_20260904` | wb / h2 / pfoff | 8 | 8 | 16 ticks/B |
| `h1bw_mc_{wb,h2,pfoff}_4c_l3x1_bwdef_20260904` | wb / h2 / pfoff | 4 | **1** | default |

Verdicts for these cells are **not** restated here; they live in
`H1BW_MULTICORE_OUTCOME_2026-09-03.md`, `AGGBW_VALIDITY_2026-09-03.md` and
`H2_BYPASS_COLLAPSE_2026-09-03.md`, and the last of those voids
`h1bw_mc_h2_4c_l3x1_bwdef_20260904`. This document attributes cells to
binaries and does not judge them.

### Produced by `cb290444` — tag `build-cb290444` (3 cells, in flight)

| cell | arm | cores | slices | started | pid |
|---|---|--:|--:|---|--:|
| `h1bw_mc_wb_4c_l3x1_bwdef_20260904fix` | wb | 4 | 1 | 12:52:44 | 1354716 |
| `h1bw_mc_h2_4c_l3x1_bwdef_20260904fix` | h2 | 4 | 1 | 12:52:46 | 1354789 |
| `h1bw_mc_pfoff_4c_l3x1_bwdef_20260904fix` | pfoff | 4 | 1 | 12:52:48 | 1354852 |

**These three are the first cells in the project produced by a binary whose
STREAMING attribute survives a CHI `RetryAck`.** They are not additional
samples of the twelve-name one-slice condition and must never be pooled with
their pre-fix twins — the same three names without the `fix` suffix, one row up.
The comparison *across* the two binaries is the entire purpose of the re-run:
`h2_4c_l3x1` is predicted to move from 17,197 bypasses and 1.8% engagement to
750–820k and 83–90%, and `wb_4c_l3x1` is predicted to be **unchanged**, which
makes the WB pair a free correctness check on the fix itself.

The `fix` suffix is the only thing in the directory name that distinguishes the
two binaries, and it is not self-describing. Read `gem5_sha256`, or the
`gem5 compiled` line, not the suffix.

### Produced by `481d7e12` — tag `build-481d7e12` (0 cells)

No `console.log` anywhere under `gem5/logs/` reports `gem5 compiled Sep  3
2026`. This binary was built in a separate variant directory so that adding the
flush-behind oracle would not displace `cfd37207` while the `h1bw` campaigns
were running — which worked, and is why the 21 cells above are homogeneous. It
is tagged because it exists on disk and is citable, not because anything
depends on it.

### Earlier binaries, not reconstructed

Four further compile dates appear in older `gem5/logs/` console logs and are
**not** covered by any tag: `Aug 23 2026 14:38:35` (18 runs), `Aug 24 2026
01:24:49` (5), `Aug 24 2026 13:19:13` (1), `Aug 30 2026 15:23:21` (5). Their
`MANIFEST.json` files, where they exist, record a `gem5_sha256` for a binary
that no longer exists, and their source states were not investigated here.
Anything still cited from those runs carries the `F13` defect unrepaired.

## 3. The pre-fix state differs from the current tree by THREE things, not two

This is the finding that matters most, and it contradicts the premise the task
was set with.

`git diff build-cfd37207 build-cb290444` touches ten files. Of those, five are
not compiled or marshalled into `gem5.opt` and cannot affect a binary
(`scripts/fs_boot_checkpoint.sh`, `scripts/fs_restore_chi_8592.sh`,
`testcase/dutyfree/fused.c`) or are read from the working tree at run time
(§4). The remaining **binary-relevant** delta is:

| # | change | files | status |
|---|---|---|---|
| 1 | `isStreaming` copied in `prepareRequestRetry()` | `CHI-cache-funcs.sm` | known, expected |
| 2 | `abs()` on the `fromSeconds` rounding error | `src/python/m5/ticks.py` | known, expected |
| 3 | **the flush-behind oracle, m5 op `0x57`** | `m5ops.h`, `pseudo_inst.{cc,hh}`, `sim_object.{cc,hh}` | **NOT accounted for** |

Items 1 and 2 are byte-for-byte what was expected: a four-line addition to
`prepareRequestRetry` (one assignment, three comment lines) and a four-line
change in `fromSeconds` (one expression, three comment lines). Neither is
larger or smaller than described.

Item 3 was not known. `cb290444` contains the flush-behind oracle and
`cfd37207` does not, so the two binaries differ by a compiled-in code path in
addition to the two fixes. **This was not known when the three-cell re-run was
launched at 12:52.**

### Why this is safe for the re-run anyway

The oracle is unreachable unless a guest executes m5 op `0x57`. The three
in-flight cells run `cxl_join_bench.gem5` with `--mode stream-smoke --policy
{wb,stream}`; no `--policy fbo` arm exists in this campaign, so nothing issues
the op. `pseudo_inst::flushrange` is dead code in these three runs, and
`SimObject::getSimObjectList()` is a read-only accessor called from nowhere
else. The pre/post comparison in §2 therefore still isolates the two fixes.

That is an argument, not a measurement, and it is the honest limit of what can
be said without a rebuild. What would settle it is rebuilding
`build-cfd37207`, re-running one cell, and checking it against the archived
pre-fix cell — `wb_4c_l3x1` is the natural choice since the fix is predicted
not to touch it.

### How each attribution was established

Every claim below rests on an artifact on disk, not on recollection.

**`cfd37207` was compiled 2026-08-31 12:40:39.** From its own banner in the
console log of all 21 cells. Corroborated in the build tree: the only surviving
object files with that timestamp are the three
`mem/ruby/protocol/CHI/CHI_*_Controller.py.o`, i.e. SLICC did run that day.

**The HNF bypass counter IS in `cfd37207`.** `stats.txt` in the `h2` cells
carries `streamingHnfFillBypasses` with its exact registered description
string, at 106,653 / 107,953 / 104,744 / 102,082 across the four HNF slices of
`h2_4c`. A stat cannot appear in output from a binary that was not built with
it. This dates commits `831b994d27` and, transitively, the `CacheMemory` and
`RubySlicc_Types.sm` changes to on-or-before 2026-08-31.

**The `isStreaming` retry fix is NOT in `cfd37207`.** Its absence is the
measured subject of `H2_BYPASS_COLLAPSE_2026-09-03.md`: 64.8% write-request
retry fraction and 1.8% engagement in the one-slice `h2` cell, against 83.5% at
four slices, with five independent aggregate identities agreeing.

**The `ticks.py` `abs()` fix is NOT in `cfd37207`.** The pre-fix cells' console
logs contain no `rounding error > tolerance` line. The three `cb290444` cells
each emit it immediately after `Global frequency set at 1000000000000`:

```
warn: rounding error > tolerance
    1.818989 rounded to 2
```

This is the cleanest discriminator available for these two binaries and needs
neither binary to be present. It also confirms the fix is warning-only: both
binaries realize 2 ticks/byte, and `QUANTIZATION_AUDIT_2026-09-03.md` measured
0 differing `config.ini` lines in 42,789.

**The oracle is NOT in `cfd37207`.** Three independent lines, agreeing:

1. *Record.* `FB_ORACLE_PREREG_2026-09-03.md` (2026-09-03) specifies
   `M5OP_FLUSH_RANGE` (0x57), `pseudo_inst::flushrange` and
   `SimObject::getSimObjectList()` as work to be done, and
   `GEM5_RUBY_CLFLUSH_NOOP_2026-09-01.md` (2026-09-01) is the finding that
   motivated it. Both postdate 2026-08-31 12:40.
2. *Symbols.* `nm` finds `gem5::pseudo_inst::flushrange` and
   `gem5::SimObject::getSimObjectList()` in `build_Intel_8592_FBO`, the
   2026-09-03 build — so the oracle was in the tree by then, and the separate
   variant directory is itself evidence it was added after the campaign binary
   was fixed.
3. *Rebuild fan-out.* The 2026-09-04 build recompiled 917 of 1,875 objects,
   including ~436 `python/_m5/param_*.o`. `param_IdeDisk.cc` `#include`s
   `sim/sim_object.hh` directly, and nothing in `CHI-cache-funcs.sm` or
   `ticks.py` reaches an IDE disk parameter wrapper. A change to
   `sim/sim_object.hh` is the only member of the modified set with that
   fan-out, and `sim_object.hh` is modified by exactly one commit — the
   oracle. Had the tree differed from `cfd37207` only by the two fixes, that
   rebuild would have been confined to the CHI protocol and the marshalled
   Python.

**`CHI-cache-actions.sm` is identical in `481d7e12` and `cb290444`.** The
complete diff of the generated `Cache_Controller.cc` between those two builds
is: the one line `(param_out_msg).m_isStreaming = (*param_tbe).m_isStreaming;`
in `prepareRequestRetry`; the `CHI-cache-funcs.sm` line numbers embedded in
`panic`/`DPRINTF` strings, shifted by exactly the four added lines; and one
build-directory path in a generated header comment. Nothing else. So the
counter, the non-load guard and the ReadOnce repair were all in place by
2026-09-03, and the entire CHI source delta over that window is the fix.

**One item could not be dated: the STREAMING non-load guard**
(`289809c73f`). It is provably present by 2026-09-03 (its `error()` string is
in `481d7e12`'s generated protocol) but nothing on disk places it before
2026-08-31 12:40. Its position in the chain before `build-cfd37207` is
therefore a judgement, not a measurement. It adds an `error()` on a condition
no workload in these campaigns can reach — Linux rejects
`PROT_WRITE|PROT_STREAMING`, and a tagged store would have to exist for the
branch to be taken — so whichever side of the tag it truly belongs on, it
cannot have altered any measured value. Flagged rather than hidden.

**The ReadOnce repair is dated by record**, not by artifact:
`FS_R6_CHI_ASSERT_ROOT_CAUSE_2026-08-31.md` (2026-08-31) documents the repair
and states that "the rebuilt simulator passed a randomized diagnostic restore",
and the only 2026-08-31 build is 12:40:39 — i.e. `cfd37207`.

## 4. `gem5_sha256` is not sufficient provenance, for a second reason

`configs/` is **not** compiled into `gem5.opt`. gem5 reads `se.py` and
`configs/ruby/{Ruby.py,CHI_config_8592.py}` from the working tree at run time.
So a cell's behaviour is a function of *two* states, and `MANIFEST.json`
records only one of them.

This is not hypothetical either. The six `bwt16` / `bwt31` cells ran the
**2026-08-31** binary against a `configs/ruby/Ruby.py` carrying the
`CXL_MEM_BW` knobs that `H1BW_CXLBW_PREREG_2026-09-03.md` registered on
**2026-09-03**. Without that file's change, `CXL_MEM_BW` is ignored and those
six cells silently become six more default-bandwidth cells. The knobs are
therefore committed *before* `build-cfd37207` (commit `830905739a`) even though
they postdate that build, so that a single checkout reproduces both the binary
and the run-time configuration for all 21 cells. They are inert when the
environment is unset, so this costs the six default-bandwidth cells nothing —
`prove_default_unchanged.sh` is the existing check for that.

Consequence for the tag's meaning: `build-cfd37207` is a **reproduction point
for the 21 cells**, not a photograph of the tree as it stood on 2026-08-31.
§3 states exactly where it departs from one.

## 5. Preventing recurrence (`F13`)

The failure is not that someone rebuilt carelessly. It is that **the build
recorded nothing about its own inputs**, so once the file was overwritten the
information was gone. Three mechanisms were considered.

| option | catches it? | why not / why |
|---|---|---|
| `git describe` in `MANIFEST.json` | **no** | Records the tree at *launch*, not at *build*. Here it would have written a 2026-09-03 tree against a 2026-08-31 binary for the `bwt` cells — actively misleading, worse than silence. |
| pre-run check that the tree is clean | no | These trees are never clean. A check that always fires is a check that gets disabled. |
| **build wrapper that records source identity next to the binary** | **yes** | The only point where source and binary provably coexist. |

**Recommended, and the reason it is the lightest thing that works:** the repo
already contains the mechanism. `scripts/fs_boot_checkpoint.sh` grew a
`source_identity()` function (commit `3bd36a0061`) that hashes `HEAD` plus
`git diff --binary HEAD` plus every untracked file's contents into one
`SOURCE_FINGERPRINT`. That identifies *which* dirty tree, not merely that the
tree was dirty, which is the property needed here. It needs to be moved to
build time and reused.

Two parts.

**(a) `gem5/scripts/build_gem5.sh` — implemented.** Computes the source
identity, runs the build, and writes `<build-dir>/BUILD_PROVENANCE.json`
alongside `gem5.opt`, containing the binary's sha256, `git describe --tags
--long --dirty`, `HEAD`, the tree fingerprint, and — when the tree is dirty —
the full diff saved to `<build-dir>/BUILD_SOURCE.diff`. It refuses to build a
dirty tree unless that diff can be written, and it deletes the manifest if the
build fails, so a stale manifest can never be trusted. It does not refuse a
dirty tree outright, because in this project that would mean refusing every
build.

**(b) `experiments/asplos/run_h1bw_multicore.sh` — specified, NOT applied.**
The runner is being executed right now: `bash` holds it open on fd 255
(`/proc/1354573/fd/255`) and reads it incrementally, so editing it in place can
make the shell resume at a stale byte offset. It must not be touched until the
three cells exit. Exact patch, to apply after that:

```diff
@@ after: OUTROOT=...  STAMP=...
+# gem5_sha256 names a binary, and a binary gets replaced in place.  Carry the
+# source identity recorded at BUILD time; fail closed if it does not describe
+# the binary we are about to run (i.e. someone bypassed scripts/build_gem5.sh).
+GEM5_PROV=$(dirname "$GEM5")/BUILD_PROVENANCE.json
+GEM5_SHA=$(sha256sum "$GEM5" | cut -d' ' -f1)
+[ -s "$GEM5_PROV" ] || { echo "FATAL: no $GEM5_PROV; rebuild with gem5/scripts/build_gem5.sh"; exit 1; }
+grep -q "\"gem5_sha256\": \"$GEM5_SHA\"" "$GEM5_PROV" || {
+  echo "FATAL: $GEM5_PROV does not describe $GEM5 ($GEM5_SHA)"; exit 1; }
+GEM5_DESCRIBE=$(sed -n 's/.*"gem5_git_describe": "\([^"]*\)".*/\1/p' "$GEM5_PROV")
+GEM5_HEAD=$(sed -n 's/.*"gem5_git_head": "\([^"]*\)".*/\1/p' "$GEM5_PROV")
+GEM5_FINGERPRINT=$(sed -n 's/.*"gem5_source_fingerprint": "\([^"]*\)".*/\1/p' "$GEM5_PROV")
```

```diff
@@ in run_arm's MANIFEST.json heredoc, next to bench_sha256
-  "gem5_sha256": "$(sha256sum "$GEM5" | cut -d' ' -f1)",
+  "gem5_sha256": "$GEM5_SHA",
+  "gem5_git_describe": "$GEM5_DESCRIBE",
+  "gem5_git_head": "$GEM5_HEAD",
+  "gem5_source_fingerprint": "$GEM5_FINGERPRINT",
+  "configs_git_describe": "$(git -C "$ROOT/gem5" describe --tags --long --dirty --always)",
```

`configs_git_describe` is separate and is taken at launch, deliberately: per §4
the config tree is read at run time and genuinely is a launch-time input, so
recording it at launch is correct rather than misleading. The three
`gem5_*` fields are build-time inputs and are copied, never recomputed.

The fail-closed cross-check in (a)+(b) is what makes the wrapper effective
without being mandatory: a hand-rolled `scons` leaves a `BUILD_PROVENANCE.json`
whose `gem5_sha256` no longer matches, and the next run refuses to start rather
than recording provenance that has quietly gone stale.

## 6. Not committed, and why

Nothing was found that needed adding to `.gitignore`. `git status
--untracked-files=all` reported no untracked files in `gem5/` at all, and
`build_Intel_8592/`, `build_Intel_8592_FBO/` and `logs/` are already ignored by
existing rules (`build_*/`, `logs/`). No build output, generated SLICC output,
object file, large binary, local path or secret was staged; the nine commits
touch exactly the fifteen modified files and nothing else.

`gem5/build_Intel_8592/` was not committed and was not written to. The three
in-flight simulations were not signalled and nothing under `gem5/logs/` was
modified.

## 7. Follow-ups this created

- **`configs/ruby/Ruby.py` now carries a stale comment.** It states that
  `fromSeconds` "only warns when it rounds *down*, so rounding up is silent" —
  true of `cfd37207`, false of `cb290444`, whose console log proves it by
  warning on exactly that case. Not corrected here: `Ruby.py` is read at run
  time and the three cells in flight are reading it. Correct after they exit,
  in its own commit.
- **A rebuild of `build-cfd37207` would upgrade §3 from argument to
  measurement.** One cell, `wb_4c_l3x1`, ~1.4 h.
- **`F13` needs registering** in `A1_PROVENANCE_LEDGER_2026-08-28.md`'s open
  defects table, and the four earlier compile dates in §2 need a decision on
  whether anything still cited depends on them.

## 2026-09-04 — the `cfd37207` → `cb290444` delta is five commits, and is measured inert

This document's earlier note said the two campaign binaries differ by **three**
diffs and flagged the flush-behind oracle as *argued* unreachable, **not
measured**. Both halves are now corrected by
`H2_BYPASS_FIX_OUTCOME_2026-09-03.md` §2.

`git log build-cfd37207..build-cb290444` is **five** commits:

| commit | subject | compiled in? |
|---|---|---|
| `b9c8714c93` | CHI: carry isStreaming across the request retry path | yes |
| `a5f366456e` | ticks: compare the magnitude of the rounding error | yes |
| `1bb6418e01` | m5 op 0x57 `flush_range`: an idealised flush-behind oracle | yes |
| `3bd36a0061` | fs checkpoint: bind a checkpoint to kernel/image/simulator | yes (`sim_object.{cc,hh}`) |
| `f3c2c84949` | fused: reset stats after the tenant's own init | no (`testcase/`, not this benchmark) |

The oracle's reachability question was **not vacuous**, which is worth
recording: `cxl_join_bench.cpp` does call `gem5_flush_range()`, and the
`0f 04 57 00` opcode **is present in the compiled** `cxl_join_bench.gem5`
(`bench_sha256 cac9e27a...`, unchanged across both campaigns). It sits behind a
runtime `policy == "fbo"` branch. No `h1bw_mc_*` cell passes `--policy fbo`, so
the byte never executes.

It is now **measured** rather than argued. `h1bw_mc_wb_4c_l3x1_bwdef_20260904fix`
is bit-identical to its `cfd37207` twin on all **11,166** simulated quantities
(5 differing lines, all five host-side: `hostSeconds`, `hostTickRate`,
`hostMemory`, `hostInstRate`, `hostOpRate`). Every commit above except the
`isStreaming` fix touches code the `wb` arm exercises identically, so had any of
them perturbed this workload, `wb` could not have matched. **The whole delta is
inert on these cells except through `isStreaming` on retried requests** — which
is what licenses comparing the `h2` and `pfoff` re-runs against their pre-fix
twins at all.

Provenance note that survives this: the re-run cells emit **six**
`rounding error > tolerance` warnings each (from `a5f366456e`, on
`SimpleMemory.bandwidth` tick quantization) that the pre-fix cells do not. The
guard is warning-only — `config.ini` byte-identical, and `wb` bit-identical —
so **this is not a regression**, and should not later be read as one.
