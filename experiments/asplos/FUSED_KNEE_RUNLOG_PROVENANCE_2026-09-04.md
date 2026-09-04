# FUSED_KNEE run logs: the in-band launch and completion evidence, tracked

Date: 2026-09-04. **No new compute**: nothing launched, no rebuild, no gem5
invocation, nothing deleted from `/tmp`. This pass moves bytes into git and
writes this record; it changes no measured value anywhere in the repository.

Campaign: `FUSED_KNEE_PREREG_2026-08-29.md`, closed by
`FUSED_KNEE_CLOSED_2026-09-04.md`, verdict in
`FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md`, current use in
`RECOVERY_CURVE_OUTCOME_2026-09-04.md`.

## Why this exists

The campaign's *numbers* have been in the repository since `acc722a`
(`data/gem5/kn_runs.jsonl`, 45 records; `data/gem5/kb_runs.jsonl`, 18). What was
never in the repository is the campaign's *timing* evidence. Every statement
about when these runs started — including the one the paper leans on hardest,
that the five registered table sizes were fixed before the runs — rested either
on a document's own attestation or on filesystem timestamps of directories that
existed only in `/tmp`.

`/tmp` here is **tmpfs** (630 GB, `df -T`). A reboot destroys it. And even if it
survived, **no filesystem timestamp survives a clone**: git records no mtime, no
ctime and no birth time. A reviewer with a clone could therefore check
registration-before-*data-commit* (both are commits) but not
registration-before-*run*, which is the stronger and more interesting ordering.

Each gem5 process wrote its own startup banner into a sibling log file, and the
runner appended its own completion stamp to the same file. Those two lines are
the ordering evidence, they are 3.6 KB apart in a 3.7 KB file, and committing
that file closes the gap without an excerpt of any kind.

## Inventory: all 63 run directories, by file class

Measured 2026-09-04 over `/tmp/kn_*` (45, the registered sweep, 2.0–4.0 MB) and
`/tmp/kb_*` (18, the unregistered extension, 6.0/8.0 MB). Regular files only.

| class | where | `kn_*` (45) | `kb_*` (18) | total | committed here |
|---|---|--:|--:|--:|---|
| `<run>.log` | **sibling of the dir** | 45 files, 163,425 B | 18 files, 65,379 B | **228,804 B (223.4 KiB)** | **yes, in full** |
| `<grp>_sweep.done` | `/tmp` | 1 file, 21 B | 1 file, 21 B | **42 B** | **yes, in full** |
| `stats.txt` | in dir | 36,271,538 B | 14,459,689 B | 50,731,227 B (48.4 MiB) | no |
| `config.json` | in dir | 42,499,185 B | 16,999,674 B | 59,498,859 B (56.7 MiB) | no |
| `config.ini` | in dir | 14,510,400 B | 5,804,160 B | 20,314,560 B (19.4 MiB) | no |
| `citations.bib` | in dir | 177,795 B | 71,118 B | 248,913 B (243.1 KiB) | no |
| `fs/**` | in dir | 180 files, 38,340 B | 72 files, 15,336 B | 53,676 B (52.4 KiB) | no |

Committed: **65 files, 228,846 B (223.5 KiB)**. Not committed: **504 files,
130,847,235 B (124.79 MiB)**, every one of them SHA-256'd into
`artifacts/fused_knee/UNCOMMITTED_ORIGINALS.sha256`.

Individual logs run 3,569–3,751 B. There is no `console.log` and no
`MANIFEST.json`/`DONE.json` in this campaign — it is SE mode driven by a bash
runner, not the FS-mode harness that `7606f84` dealt with, so the equivalent
evidence lives in the sibling `.log` rather than inside the output directory.

## What is committed is the original, not an extract

This is the point worth being explicit about, because the alternative was
considered and rejected. The banner-bearing file is 3.7 KB. There is no size
argument for excerpting it, so nothing was excerpted, reformatted, filtered or
regenerated: all 65 files are byte-for-byte what was on tmpfs. A hand-made
excerpt would have been strictly weaker evidence than the file it came from, and
here it would also have been pointless.

## How the keep set was chosen

Following `7606f84`, which the user approved for exactly this class of decision:
let the *consuming tool's* requirements define the keep set rather than a generic
stats-versus-logs rule, keep the small files the evidence actually depends on,
and drop redundant bulk with the sizes and the principle disclosed.

The consuming tool is `experiments/lib/archive_gem5_runs.py`. For a `kn_`/`kb_`
run it reads exactly three things: `stats.txt` for the values, `config.ini` for
arm identity (the `S5.1` rule: identity from the run's own config, never the
directory name), and **`<dir>.log`** at line 65 for the realized table size (the
`F9` rule). Its output is `kn_runs.jsonl` + `kb_runs.jsonl`, **already committed
at `acc722a`**, and `analyze_archives.py` re-derives every headline number from
those archives under `make test`.

So the numeric chain is already closed from a clone, and the one input class the
archiver reads that carries information found nowhere in its output is the
`.log`: the archiver extracts `realized_table_mb` from it and discards the
banner and the completion stamp. That is precisely the gap, and it is why the
`.log` class is the keep set.

Excluded, with the principle in each case:

- **`stats.txt`, 48.4 MiB.** The values it holds are what `acc722a` archived to
  JSONL, deliberately and with the trade-off documented in that commit ("archiving
  raw stats for 187 runs would be ~375 MB; archiving the values the outcome
  documents actually cite is ~1 KB per run"). It carries no timestamp. Committing
  it now would reverse a documented architectural decision to solve a problem it
  does not solve, so it is out of scope for this pass rather than merely large.
  Noted as a hand-back below.
- **`config.json`, 56.7 MiB, the largest class.** The same SimObject tree as
  `config.ini` in a second serialization, cited by no record and read by no code
  — the identical finding `7606f84` recorded, at 14x the size.
- **`config.ini`, 19.4 MiB.** Read by the archiver for arm identity, and that
  identity is already in the committed JSONL (`hnf_policy`, `hnf_requestor_masks`,
  `fwd_unique`, verified 63/63 in `FUSED_KNEE_CLOSED`). No timestamp.
- **`citations.bib`, 243.1 KiB.** The upstream gem5 bibliography, byte-identical
  across all 63 runs (one distinct digest in the manifest).
- **`fs/**`, 52.4 KiB.** Synthetic SE-mode `/proc` and `/sys` stubs: gem5 inputs,
  not outputs.

Nothing was force-added. `git check-ignore` reports no rule matching any of these
paths, and `.gitignore` was not touched.

## The evidentiary chain, end to end

All times +0900 (host clock is KST); project-local date of this pass is
2026-09-04.

| when | what | source, and whether it survives a clone |
|---|---|---|
| 2026-08-29 03:29:25 | `gem5.opt` compiled | `gem5 compiled` banner, identical in all 63 logs — **yes, now** |
| **2026-08-29 22:58:37** | **`eb20d93`** registers the design: 5 sizes × 3 arms × 3 seeds = 45 runs | commit author = committer date — yes |
| **2026-08-29 22:58:38** | **all 45 `kn_*` runs start, +1 s** | `gem5 started Aug 29 2026 22:58:38`, **identical in all 45** — **yes, now** |
| 2026-08-30 00:51:48 – 01:30:39 | the 45 runs finish, all `DONE_0` | runner's `date +%s` appended per run — **yes, now** |
| 2026-08-30 01:30:39 | `kn` sweep closes | `kn_sweep.done`: `KNEE_DONE 1788021039` — **yes, now** |
| 2026-08-30 01:33:02 | the 18 `kb_*` runs start, +2 h 34 m 25 s | `gem5 started Aug 30 2026 01:33:02`, identical in all 18 — **yes, now** |
| 2026-08-30 03:26:09 – 03:58:17 | the 18 runs finish, all `DONE_0` | as above — **yes, now** |
| 2026-08-30 03:58:17 | `kb` sweep closes | `kb_sweep.done`: `KNEE_DONE 1788029897` — **yes, now** |
| **2026-08-30 08:21:03** | **`acc722a`** commits the archives, +9 h 22 m 26 s from registration | commit date — yes |

`FUSED_KNEE_PREREG_2026-08-29.md` has **exactly one commit in its file history**
— `eb20d93` introduced it and nothing has modified it since, so the registered
prediction cannot have been edited after the fact. (Stated precisely because it
is easy to garble: it is the *file* that has one commit. `eb20d93` itself has 503
ancestors.)

### What this proves, and what it does not

It is worth being exact, because the value of the evidence is in its limits.

**Strengthened.** Run start is now checkable from a clone, at one-second
resolution, against a registration commit — for the 45 registered runs, the
ordering that `Sec7_Evaluation.tex:238` asserts. Forty-five independent gem5
processes each wrote the same start second; the runner's own stamps close each
run's span; `stats.txt` and `config.ini` (digested here, uncommitted) would have
to agree with all of it. Falsifying this now means forging a coherent set, not
adjusting one number.

**Not established.** This is **in-band, tool-generated, mutually corroborating**
evidence — it is *not* third-party attestation. Both the commit date and the
banner come from the same host clock, and a git author date is settable by
whoever makes the commit. Anyone inclined to describe this chain as "externally
witnessed" should say instead that it is *independently generated by the
simulator rather than asserted by the author*, which is what is actually true and
is the property that matters. The one genuinely external element is that
`eb20d93` is an ancestor of `origin/main`, i.e. it was published; but the clone
carries no push time, and the commit is unsigned (`%G?` = `N`).

## The `kb_*` extension: a different banner, and it is cited

Two findings, both worth stating because the campaign is easy to treat as one
block of 63 runs.

**The 18 `kb_*` directories do *not* carry the same banner.** They read
`gem5 started Aug 30 2026 01:33:02` — a separate launch 2 h 34 m 25 s after the
registration commit and 2 m 23 s after the `kn` sweep closed at 01:30:39. The
+1 s precedence result is a property of the 45 `kn_*` runs only. Both banners
are after `eb20d93`, so registration-before-run holds for all 63; it is only the
one-second tightness that is `kn`-specific.

**They are cited, and heavily.** `run_fused_knee_big.sh` is a copy-paste of the
`kn` runner with `/tmp/kb_` and sizes 6.0/8.0, and it carries this
pre-registration's header verbatim although those sizes are not in its design.
`kb_runs.jsonl` is named in the `fig:recovery` row of
`A1_PROVENANCE_LEDGER_2026-08-28.md`, in `FUSED_KNEE_CLOSED_2026-09-04.md`, in
`FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` and in `RECOVERY_CURVE_OUTCOME_2026-09-04.md`;
`make_recovery_curve.py` plots it. Most consequentially, **the 8.0 MB point that
terminates the paper's headline range ("falls from 89.4% to 56.8%") is a `kb_*`
point**, and per open defect `F15` it is in no pre-registration's design at all.

So committing the `kb` logs is not symmetry for its own sake: it puts the launch
evidence for the least-registered point on the curve into the repository next to
the evidence for the most-registered ones, where the distinction the paper draws
between them can be checked rather than taken on trust.

## Correction to the prior reasoning, and it is a method correction

`A1_PROVENANCE_LEDGER_2026-08-28.md` (the `Sec7_Evaluation.tex:238…` bullet)
reads:

> the first run directory, `/tmp/kn_cat4_t2.0_s1`, was created at
> **22:58:38.53 — one second after the registration commit**

`22:58:38.53` is that directory's **mtime**, not its creation time. Its birth
time is **22:58:38.127**. Measured across all 45:

| | range |
|---|---|
| birth (`stat %w`) | 22:58:38.124770845 – 22:58:38.155105689 |
| mtime (`stat %y`) | 22:58:38.530770947 – 22:58:38.560770954 |

**The verdict was right and the reasoning was not.** mtime sits ~0.41 s after
birth here, both land in the same second, and the conclusion survives unchanged.
But it survives by luck: mtime is last-write, and for a directory gem5 writes
into for the whole run it normally tracks *completion*. The identical inference
applied to the H1BW single-core harness was wrong by 48 minutes — `7606f84`
records that its `21:48–21:50` mtimes were completion times and the runs actually
began at 21:00, about 22 minutes *before* their registration rather than 26
minutes after it. Here the runs happen to create their output directory and
finish writing its metadata within half a second, which is why the same mistake
is harmless. A method that gives the right answer for a reason unrelated to the
question should not be reused.

Which is the whole argument for this commit: **no filesystem timestamp survives a
clone at all** — not mtime, not birth time — so neither the wrong reasoning nor
the right version of it is available to a reviewer. The in-band banner is.

Note that the ledger's own wording "has never been modified since (one commit in
its whole history)" is accurate as written — the subject is the pre-registration
*file*. Recorded here only because it is easily misread as a claim about
`eb20d93`'s ancestry, which is 503 commits.

## Paper passages this supports

The six `Sec7_Evaluation.tex` passages the ledger identifies as resting on this
campaign's registration claim, all of which are now backed by committed launch
evidence rather than by tmpfs metadata:

| line | what it asserts |
|---|---|
| **238** | `fig:recovery` caption: "In panels~(a) and~(b) the five table sizes" |
| **239** | "from 2.0 to 4.0~MB were registered before the runs ($45$ runs) and are what" — the strongest-worded of the six |
| **274** | "…falls no further by 4.0~MB (82.3\%), across the five sizes" (+275, "registered in advance") |
| **276** | "…89.3\% to 87.3\%. Seed-to-seed spread is below" |
| **277** | "0.25~pp at every registered size, so both declines are far outside run-to-run" |
| **280** | "we report it as exploratory and rest the claim on the registered range" |

Line 280 is the load-bearing one for the `kb` finding above: it is the sentence
that rests the claim on the registered range and reports 6.0/8.0 MB as
exploratory. The two distinct banners are the artifact that makes that
registered/unregistered split independently checkable, which is the distinction
`F15` deliberately narrowed the `fig:recovery` claim onto.

Nothing in `Text/` was edited. The paper draft is owned by the reconciliation
pass.

## Byte-identity

All 65 files were SHA-256'd on tmpfs before being copied, `cmp`'d individually
against their originals after copying, and SHA-256'd again after committing. The
manifest digest — the SHA-256 of the sorted list of the 65 file digests — is

```
0f2df651adc6042b697452a7676375d1176db520620a526f0e656812cda170b4
```

unchanged across all three points. No file's content was modified by this pass.
The 504 uncommitted originals were digested before the copy and re-verified
after; their digests are in `artifacts/fused_knee/UNCOMMITTED_ORIGINALS.sha256`.

## Content scan

This repository is public. All 228,846 committed bytes were scanned: no
passwords, tokens, API keys, private keys, bearer credentials or email addresses.
The only host identifier is `executing on mos181` and the only absolute user path
is `/home/domin`, both within the accepted convention. The one IPv4-shaped match
is `25.1.0.1`, which is gem5's own version string.

Each log does contain the full gem5 command line — binary path, CHI config path,
cache geometry, `--options`, and the `HNF_*` environment. That is apparatus
detail the runner already publishes verbatim, and it is the reason the logs are
worth having.

## Handed back, not applied

`A1_PROVENANCE_LEDGER_2026-08-28.md` and `INDEX.md` are owned by another worker
and were **not edited**. Suggested wording is in the commit message and reproduced
here.

That owner committed twice while this pass was running (`f425779`, `5584644`,
both registering `F17` and the publication paragraph for the AMD cross-socket
campaign, no overlap with this subject), and `origin/main` advanced from
`a0cfe30` to include the eleven previously-unpushed commits. Item 4 below is
struck through as a result: it was accurate when this pass began and was fixed by
`f425779` before this pass committed. Items 1–3 were re-checked against `HEAD`
after those commits and remain live — the ledger's mtime figure still stands at
line 264.

1. **Ledger, the `Sec7_Evaluation.tex:238…` bullet.** Replace "the first run
   directory, `/tmp/kn_cat4_t2.0_s1`, was created at **22:58:38.53**" with the
   in-band banner, which is now committed and survives a clone:

   > all 45 runs report `gem5 started Aug 29 2026 22:58:38` in their own logs —
   > one second after the registration commit — and the runner's completion
   > stamps close the sweep at 01:30:39 (`artifacts/fused_knee/`)

   `22:58:38.53` is an mtime; the birth time is `22:58:38.127`. Either figure
   supports the same verdict, and neither is obtainable from a clone.

2. **Ledger, same bullet, the corroboration claim.** "externally corroborated"
   overstates what exists. Suggested: "corroborated by the simulator's own
   startup banner in all 45 run logs, which is independently generated rather
   than authored, and is committed as of this pass". See the limits section above.

3. **Ledger, `fig:recovery` row, artifact list.** It names the two JSONL archives
   and the two runners; it could now also name `artifacts/fused_knee/` as the
   raw launch and completion evidence for all 63 runs, and note that the 504
   larger originals are digested rather than committed.

4. **`INDEX.md`.** ~~`FUSED_KNEE_PREREG` is still absent entirely, per
   `FUSED_KNEE_CLOSED` §"Why this record exists" item 2.~~ **Superseded while
   this pass was running** — `f425779` added it at `INDEX.md:149`, so the gap
   `FUSED_KNEE_CLOSED` item 2 identified is closed. Two smaller things remain in
   that new entry: it ends "Its runs went to `/tmp/kn_*` and `/tmp/kb_*` rather
   than `gem5/logs/`, which is the other reason the campaign looked unexecuted",
   which is still true of the bulk output but no longer true of the launch and
   completion evidence — that is now `artifacts/fused_knee/`; and the entry could
   name this record.

5. **Optional, a real decision rather than wording.** If a reviewer must be able
   to *rebuild* `kn_runs.jsonl`/`kb_runs.jsonl` from raw gem5 output rather than
   trust `acc722a`'s extraction, the 48.4 MiB of `stats.txt` plus 19.4 MiB of
   `config.ini` is what that costs — about 6–8 MiB of object store gzipped, and
   there is precedent for the shape in
   `artifacts/localdram_column/*/stats.txt.gz`. That reverses a documented
   decision in `acc722a`, so it is not this pass's call. The digests are recorded
   so the choice stays open and checkable either way.
