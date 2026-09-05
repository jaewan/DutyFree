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
