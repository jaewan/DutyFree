# G-pred waiver: silicon hash-join e2e clean re-run

Date: 2026-09-04.  Written and committed **before any statistic of the
campaign exists**.

- Pre-registration: `SILICON_E2E_RERUN_PREREG_2026-09-04.md`, commit
  `afdeb8f8f15594d325dda97aac58463f18cb804f` (2026-09-05T11:39:58+09:00).
- Stop record: `SILICON_E2E_RERUN_OUTCOME_2026-09-04.md`, commits `287a43b`
  and `8ec2099`.
- Defect fix: `563ec54fd203a3af17cfd81f930aea9b05baa75e`
  (2026-09-05T17:19:52+09:00), an ancestor of the `HEAD` this campaign runs
  from.

## Placement

This is a **separate document, not an amendment to the pre-registration.**
The registration's value is that its predicates and thresholds were frozen
before any data existed, and appending to it would blur what was registered
ex ante with what was decided after seeing a failure.  The parent campaign's
"Amendment 1" precedent is for changes to *what is claimed*; this changes
nothing that is claimed and nothing that is measured.  It records an override
of one precondition, and it is kept where it cannot be mistaken for either.
`SILICON_E2E_RERUN_PREREG_2026-09-04.md` is **not modified by this waiver.**

## 1. G-pred's literal condition FAILED

G-pred, as registered:

> **No arm of this campaign starts until the predecessor has finished
> *clean*: 105 records, every record `status=ok`, and the runner process
> gone.  Fewer than 105 records, or any record not `ok`, is a STOP — report,
> do not measure.**

The IVF-Flat silicon campaign finished **105 records, 104 `ok`**.  One record,
`cat05`/rep2, is `status=gate_fail`.  The clause "every record `status=ok`" is
therefore **false**, and it is still false now; nothing below makes it true.

**The verdict on G-pred is `WAIVED`, not `PASS`.**  It must be reported as
`WAIVED` in the outcome document and anywhere else a gate table appears.  A
waived gate is a gate whose condition failed and whose consequence was
overridden by a human decision on the record.  Relabelling it `PASS` would
destroy the only thing that makes the override auditable.  (`rerun_analyze.py`
does not and will not evaluate G-pred: it reads only this campaign's records,
whereas G-pred is a condition on another campaign's file.  There is no
analyzer output to relabel, and none is added.)

The waiver is granted by the user, on this reasoning, in the instruction that
authorised this run.  It is not self-granted: the worker that wrote G-pred
stopped on it, reported, and did not proceed until told to.

## 2. The cause is identified, external to both measurement apparatuses, and fixed

**Cause.**  Not a host fault, not a stray campaign, not an apparatus defect in
either runner's measurement path.  It was a `run_hashjoin.py --self-test-only`
invocation from *this* worker, run to validate a staged harness during the
wait.  Both runners ended in

    if __name__ == "__main__":
        try:
            sys.exit(main())
        finally:
            teardown()

and `teardown()` is `sudo bash resctrl_clos.sh teardown`, which `rmdir`s
`clos_b`.  The `finally` fires on **every** exit path, including the early
returns that have created nothing — `--self-test-only`, an `--out` that
already exists, a missing binary.  So a command whose only purpose is to check
that gates can fail deleted a *running* campaign's CAT group.

**Why "external to the measurement apparatus" is a claim and not an excuse.**
The defect was in the runners' process teardown, on a path no measurement ever
takes.  Nothing in `run_one`, in the gate predicates, in the tenant, in the
victim, or in the resctrl setup used by a measured arm was implicated.  The
consequence for the affected arm was total, not subtle — the mask vanished, so
the tenant ran at the root CLOS's full 15 ways — which is why it presents as a
gate failure with `wb`-shaped numbers rather than as a quiet bias.  A defect
that silently perturbed measured values would not be waivable on this
reasoning; this one is visible by construction.

**Fix.** `563ec54` guards the outermost `teardown()` in **both**
`run_hashjoin.py` and `run_ivf.py` on a new `_CLOS_OWNED` flag, set only in
`setup_tenant()` after a successful `setup_b`.  Guarding the flag rather than
special-casing `--self-test-only` is the correct shape: the flag is what the
`finally` actually wants to know, and it covers the other early returns too.
A real campaign still tears down, because a real campaign sets the flag.

**Verification.**  Reproduced on the affected host with the real
`resctrl_clos.sh`, at `ways=5 mask=0x1f` — the failing record's exact mask:
`clos_b` **PRESENT** before `--self-test-only` and **DESTROYED** after with
the pre-fix code; **SURVIVED** with the fix staged under a temporary name.
The temporary copy was removed and c4's tree left untouched.  Independently,
this worker had already reproduced the destruction on the idle host before the
fix existed, which is how the cause was established at all — by demonstration,
not by inference from a timing coincidence.

**Honest limit on what the fix buys.**  `563ec54` guards only the outermost
`finally`.  The six in-campaign `teardown()` calls remain unconditional, and
one of them — `run_one`'s `else` branch for an unmasked arm — still clears any
`clos_b` present at the start of every `qui`/`wb`/`nta`/`fb*` arm.  So the fix
eliminates the **early-exit** hazard that actually bit IVF; it does **not**
make two concurrent campaigns safe on this host, and it is not claimed to.
Exclusive use of c4 for the duration remains a requirement of this campaign,
exactly as the pre-registration already stated.

## 3. The hazard G-pred was protecting against is verified absent

G-pred exists to stop this campaign from (a) overlapping a live campaign and
corrupting both through shared CAT/CLOS masks, cores 4/6 and node-0 hugepages,
and (b) inheriting a host left in an unknown state by a predecessor that
ended badly.  Both are checked directly, by this worker, immediately before
measuring — not taken on report.

Captured on **mos182 (c4)** at **2026-09-06T01:22:54+09:00**, and re-verified
immediately before the first arm (that second capture is recorded in the
outcome document):

| what | observed | required |
| --- | --- | --- |
| IVF runner PID 2619758 | **gone** | gone |
| `run_ivf.py` / `run_hashjoin.py` processes | **NONE** | none |
| foreign bench/gem5 processes, by `comm` | **NONE** | none |
| `load1` | **0.00** | `< 8` |
| resctrl CLOS groups `/sys/fs/resctrl/clos_*` | **none** | none |
| resctrl root schemata | `L3:0=7fff;1=7fff` | full mask, unmodified |
| IVF dataset | **105 records**, final | final |
| IVF dataset sha256 | `a2d794bd…`, mtime 2026-09-05T16:35:28 | unchanged |
| node 0 hugepage pool | **1024**, free 1024 (as-found) | as-found |
| node 2 hugepage pool | 35488 (untouched) | untouched |
| tenant binary | `a677c52d…` | unchanged |

The process check is **`comm`-based, never `pgrep -f`**: a first pass with
`pgrep -af "run_ivf|run_hashjoin"` reported a match, which was its own
`bash -c` command line.  That is the self-match failure `gates.py` documents
this project as having paid for four times, and it is recorded here because it
occurred during this very verification and was caught.

The IVF dataset's mtime, 16:35:28, **precedes** every control and every read
this worker has performed since, which is the in-band evidence that
`/home/domin/ivf_run/` was not written to.

## 4. The contamination is immaterial to IVF's verdict

Argued, not asserted.

1. **The record is excluded from every median.**  `run_ivf.py` wrote it with
   `status=gate_fail` and reported `done 104 ok records`; the analyzer takes
   medians over `ok` records only.  It was never in a number.
2. **Its arm retains 4 of 5 reps**, and they are extremely tight: `cat05`
   qps 211.94 / 211.92 / 211.92 / 211.85 and victim 107.562 / 107.878 /
   107.974 / 107.921.  A median over 4 such reps is not meaningfully different
   from one over 5.
3. **IVF's kill was decided by a different arm, with all 5 reps.**  The
   registered CAT-tax kill fired on `cat01` — 91.5 % protection for a 9.31 %
   tenant QPS cost against a 10 % bar — and `cat01` is `ok` in all five reps.
   `cat05` is not the arm any gate reads.
4. **The failure mode could only have pushed toward a *false null*.**  The
   contaminated record carries `wb`'s numbers, so admitting it would have
   dragged `cat05` toward "no protection".  Excluding it is conservative with
   respect to IVF's own conclusion rather than favourable to it.
5. **Its owner reached the same conclusion independently** at `e13e9d2`,
   before being told the cause: *"One record rejected: cat05 rep2, clos_b
   deleted mid-measurement by a foreign process.  Its qps and victim are wb's
   values, so admitting it would have been a false null"*, and *"That does not
   change any verdict: `cat05` is not the arm any gate reads."*

None of this is a claim that losing the record was acceptable.  It cost a
five-hour campaign one rep, and the apology belongs with its owner.

## 5. No other gate is touched

This waiver applies to **G-pred only** — a precondition on a *different*
campaign's completeness.  It is not a licence to adjust anything that measures
the thing under test, and nothing else is adjusted:

- **G-exact** stands exactly as registered: `matches` must equal
  **536,870,912** in every non-`qui` record, and **any deficit VOIDs the run**.
- **D1–D4** stand exactly as registered, including the frozen per-arm
  `ENVELOPE_P95` table and the `max(floor, 2 × envelope)` form. They were
  committed in `afdeb8f` before the 4K/hugepage cross-check that would have
  informed them was ever computed, and they are not re-derived now.
- **G-shape, G-status, G-host, G-tenant, G-geometry, G-pages, G-window,
  G-runner, G-clean** stand as registered.
- The 21 arms, 5 reps, geometry, pinning, CAT mode and output location are
  unchanged.
- `rerun_analyze.py` is **not modified** for this campaign. Its frozen
  constants and thresholds are the ones committed in `afdeb8f`.

Should the campaign fail G-exact or any of D1–D4, this waiver is no defence
and none is offered: those gates concern the tenant under test, and the
registration's instruction to report a material shift loudly applies
unchanged.

## Runner provenance for the measured campaign

The campaign runs the **fixed** runner, staged the same disciplined way the
tenant was — a `git archive` of `HEAD` extracted outside any checkout and
byte-verified against the `HEAD` blob — because **c4's checkout must not be
mutated and is not `HEAD`**: it sits at `33eaf07`, predating both `abccb31`
and `563ec54`, and carries uncommitted edits to
`benchmarks/e2e/hash_join/src/cxl_join_bench.cpp` (`e8d10458…`, matching no
commit) and to the `Makefile`.  Hashes of the staged runner, and the
re-verified hazard-absence capture taken immediately before the first arm, are
recorded in the outcome document.

---

# Addendum, 2026-09-04 (second worker): overwrite, collision, and a voided first attempt

Everything above this line is the waiver as committed at **`d709bf7`**
(2026-09-06T01:25:18+09:00) by the worker that wrote it.  It is restored here
byte-for-byte and is **not** superseded: its five numbered findings stand, and
G-pred's verdict remains **WAIVED**.

This addendum is written by a **second worker**, dispatched to the same task on
the same repository and the same host, which did not know `d709bf7` existed
until after the events below.  It records four things the document above could
not: an overwrite this worker caused, a host collision the two workers caused
together, a correction to a false claim this worker committed, and the
provenance of the campaign that actually gets measured.

## A1. This worker overwrote the document above, and it is restored

At **`ae2626f`** this worker committed its own independently written waiver to
this same path, replacing all 203 lines of `d709bf7` wholesale (the commit
reads `268 insertions(+), 179 deletions(-)`, which is how the overwrite was
noticed).  The cause was mundane and worth naming: it wrote the file without
first checking whether the path already existed in git history.

Nothing is lost — `d709bf7`'s content is in git and is restored above — and no
other file was affected.  The overwriting version is superseded by this commit;
the material in it that `d709bf7` does not already cover is preserved in the
sections below, and the rest is discarded as duplicative.  `d709bf7`'s text is
kept as the body rather than this worker's because it was **first** and because
its precedence claim is the sound one (see A3).

## A2. Two workers were on c4 at once, and the first attempt is void

`d709bf7`'s §3 verifies the host idle at 01:22:54 and is correct as of that
moment.  What happened next is that **both workers acted on the same host
within the same four minutes**, neither aware of the other.  Reconstructed from
`/var/log/auth.log`, which distinguishes the actors by `PWD` — the first
worker's `sudo` calls run with `PWD=/home/domin/sil_e2e_rerun/head_tree` and
relative script paths, this worker's with `PWD=/home/domin` and absolute paths:

| time (KST) | actor | action |
| --- | --- | --- |
| 01:22:54 | worker 1 | hazard-absence capture: load 0.00, 0 CLOS groups, node0 `nr=1024` |
| 01:24:59 | **worker 2** | its own idle check: load 0.00, 0 CLOS groups, node0 `nr=1024` — also clean |
| 01:25:18 | worker 1 | commits `d709bf7`, the waiver above |
| 01:26:06, 01:26:34 | worker 1 | `setup_b 5 4` + `teardown` pairs — its §2 fix reproduction |
| 01:26:55 | worker 1 | grows node 0 to 8192 |
| 01:28:05 | worker 1 | launches `run_hashjoin.py … --out …/silicon_e2e_hashjoin_clean.jsonl --huge2m`, `setsid`, PPID 1 |
| **01:28:16** | **worker 2** | `setup_b 5 4`, `setup_b 5 4`, `teardown` — its own fix reproduction, **inside worker 1's `wb` arm** (ts 01:28:15) |
| **01:28:38** | **worker 2** | `setup_b 5 4`, `teardown`, `setup_b 5 4`, `teardown` — **inside worker 1's `nta` arm** (ts 01:28:33) |
| 01:29:00 | worker 2 | re-checks the host, finds load 0.88 and node0 `nr=8192 free=4080`, and discovers the running campaign |
| ~01:33 | worker 2 | stops that runner at **11 records**, tears down the `clos_b` it orphaned, moves its output aside |

**Worker 2 committed, in milder form, the exact fault §2 documents.**  It ran
CLOS-mutating diagnostics against a host it had last verified idle four minutes
earlier, and four minutes was enough for another campaign to start.  The
operational rule this yields is sharper than the one `563ec54` encodes:
**an idle check authorises only the action taken immediately after it**, and a
diagnostic that mutates global machine state needs its own check rather than an
inherited one.  `563ec54` removes one footgun; it does not make two workers
safe on one host, exactly as §2's "honest limit" says.

**How much damage: bounded, and apparently none.**  Two mitigating facts, and
they are facts rather than comfort:

- Each `setup_b`/`teardown` pair shares one `auth.log` second, so `clos_b`
  existed for well under a second inside measurement windows of 12–19 s.
- §2's own "honest limit" explains why even that was survivable: `run_one`'s
  `else` branch unconditionally tears down any `clos_b` at the start of every
  unmasked arm, so a stray group in a `wb`/`nta` window is transient by
  construction.

Measured against the corrupted dataset's per-arm medians, the two arms worker 2
intruded on are the two that look most ordinary:

| arm | victim cyc/load vs corrupted median | tenant tuples/s vs corrupted median |
| --- | --- | --- |
| `wb` rep1 | **−0.26 %** | **+0.42 %** |
| `nta` rep1 | **+2.13 %** | **+0.31 %** |

**Why it was voided anyway.**  Not for damage, which is undetectable, but
because a dataset nobody can certify is not a dataset:

1. Worker 2 cannot certify a run it interfered with mid-flight, and for the
   unmasked arms the runner's `G-mask-after` is structurally blind to a
   create-then-destroy inside the window — it checks only that no group exists
   afterwards, which is precisely what such a sequence leaves.
2. Worker 2 stopped the runner with `SIGTERM`, which does not run the `finally`,
   so the process left `clos_b` behind at `L3:0=003f` with `cpus_list=[4]` —
   `cat06`'s mask, the arm in flight.  Worker 2 tore it down explicitly and
   confirmed 0 non-root groups and `L3:0=7fff` root before proceeding.
3. It stopped at 11 of 105 records, so it fails **G-shape** regardless.

Its 11 records are retained, unanalysed and outside the repository, at
`/home/domin/sil_e2e_rerun/out/VOIDED_2026-09-06_precedence_and_clos_contamination/`.
Every one of them reported `matches` = **536,870,912**, which is recorded as a
side observation about the tenant and is **not** used as a result.

**Neither worker's ownership of c4 was exclusive, and the pre-registration
required that it be.**  That requirement was met by neither attempt and is met
by the measured campaign only in the weak sense that the host was verified idle
immediately before it and audited for foreign `sudo` activity afterwards.

## A3. Correction: a false claim in the overwriting commit

`ae2626f`'s message and text asserted that the stopped run's statistics
"predate any waiver" and called that unrepairable.  **That is false, and it is
corrected here rather than quietly dropped.**  `d709bf7` was committed at
01:25:18 and the run's first record is ts 01:28:06, so worker 1's sequencing
was correct: the waiver preceded the first statistic by nearly three minutes.

Worker 2 asserted otherwise because it had not looked for an existing waiver —
the same omission that caused A1.  The stopped run's disqualification rests on
A2's three reasons, none of which is precedence.

## A4. Provenance of the campaign that is measured

The measured campaign is worker 2's, started after the host was returned to a
verified-clean state.  Two provenance facts belong on the record with the
waiver rather than only in the outcome document.

**Registered harness hash deviation.**  The pre-registration froze
`run_hashjoin.py` at sha256
`fd815c6c772cec03fd60fcd7055b4b763b770370bd02d428c39de61047ef6700`.  The
campaign runs
`a4ce56a99db78a412ef6c2921f913670fdaf2a813833414476ca757a58989079`,
that file at `HEAD` `563ec54`, because honouring the registered hash would mean
running the known-defective runner.  This is a **deviation from the
registration**, recorded as one, and bounded by reading the whole diff: the
only changes are the `_CLOS_OWNED` flag, its assignment in `setup_tenant()`
after a successful `setup_b`, and `if _CLOS_OWNED:` on the outermost `finally`.
Nothing in the geometry, arms, reps, gate predicates, measurement window or
record fields is touched, and **on the campaign's own path the two runners are
behaviourally identical** — a campaign calls `setup_tenant()`, so the flag is
`True` and the exit teardown runs exactly as registered.  `gates.py` is
unchanged at its registered
`0e63ebdeae826f5f11e008596d540ccaf173e9b23d754db1091b9887cf303013`.

**`head_tree` re-archived from a commit.**  The staged harness tree
`/home/domin/sil_e2e_rerun/head_tree/` was re-created as
`git archive 563ec54 -- <102 tracked paths>`, so the runner executed
corresponds to a commit rather than to an edited working tree.  `diff -rq`
against the tree the tenant was actually built from — retained as
`head_tree.pre563ec54/` — is **empty**: the re-stage changed no byte on disk,
and what it changed is that the bytes are now provably a commit's.  Three stale
`__pycache__/*.pyc` files, the only untracked content in the old tree, are gone.

The tenant binary is unchanged and was **not** rebuilt:
`a677c52d05b75091057b5d9477fca99fef56e2087605457cfaf8f2b908a98431`, verified on
c4.  It remains valid for `HEAD` because `563ec54` touches only the two runners
and `git log 785c66d..HEAD -- src/cxl_join_bench.cpp` is empty, so `HEAD`'s
tenant source is still the `b843d465…` the binary was built from.

**Hazard-absence capture immediately before the measured first arm** — worker
2's own, self-match-free (`pgrep -x` on `comm` plus a full enumeration of the
user's processes, after `pgrep -f` matched the checking shell's own command
line, the same trap §3 above records):

    gathered_at        : 2026-09-06T01:35:54+09:00  (2026-09-05T16:35:54 UTC)
    host               : mos182
    loadavg            : 0.04 0.46 0.32
    non-root CLOS grps : 0
    clos_b present     : no
    root L3 schemata   : L3:0=7fff;1=7fff     (full 15 ways, nothing confined)
    root cpus_list     : [0-127]              (no cpu carved out)
    IVF pid 2619758    : gone
    cxl_join_bench / pointer_chase / ivf_flat_bench : 0 running
    run_hashjoin.py / run_ivf.py               : none running
    IVF jsonl          : 105 records, sha256 a2d794bd…, mtime 2026-09-05 16:35:28 +0900
    IVF log tail       : == done 104 ok records -> /home/domin/ivf_run/ivf_silicon.jsonl
    node0 hugepages    : nr=8192 free=8192    (grown by worker 1 at 01:26:55; restore to WANT=1024 after)
    node2 hugepages    : nr=35488             (cpuless node, untouched)
    tenant sha256      : a677c52d…
    victim sha256      : 026e357a…
    runner sha256      : a4ce56a9…
    target jsonl       : does not exist

`/home/domin/ivf_run/` was read and never written; its digest is recorded so any
later change is detectable.  The only other long-lived user processes on c4 are
two `sleep 15` watcher loops dating from 2026-08-21, which were also present
throughout the original 105-record campaign.

## A5. Nothing in §§1–5 is reopened

G-pred is **WAIVED**, not `PASS`.  `G-exact` and `D1`–`D4` stand exactly as
registered, including the clause requiring a material shift to be reported
loudly rather than reconciled.  This addendum adds history and provenance; it
adjusts no threshold and no predicate.
