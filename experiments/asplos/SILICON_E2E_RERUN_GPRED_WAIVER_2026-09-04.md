# Waiver: G-pred, silicon hash-join e2e clean re-run

Date: 2026-09-04.  Committed **before any statistic of the waived campaign
exists**, for the same reason the pre-registration was: a waiver written after
seeing the numbers it unblocks is not a waiver, it is a rationalisation.

Instruments this modifies:
`SILICON_E2E_RERUN_PREREG_2026-09-04.md` (commit `afdeb8f`), gate **G-pred**
only.  Outcome document: `SILICON_E2E_RERUN_OUTCOME_2026-09-04.md`.

Authority: the campaign's owner, who holds the resources G-pred sequences, has
authorised waiving this gate after the predecessor's owner closed and published
the predecessor campaign.  This document records what is being waived, on what
evidence, and — explicitly — what is *not* being waived.

## 1. G-pred's literal condition FAILED.  It is WAIVED, not passed.

G-pred, as registered:

> **No arm of this campaign starts until the predecessor has finished
> *clean*: 105 records, every record `status=ok`, and the runner process
> gone.  Fewer than 105 records, or any record not `ok`, is a STOP — report,
> do not measure.**

The predecessor produced **105 records, 104 `ok`, 1 `gate_fail`**.  Verified
first-hand for this document, not taken from prose, over the published
`experiments/asplos/data/ivf_flat_silicon.jsonl`:

    records 105   status tally {'ok': 104, 'gate_fail': 1}
    the one failure: cat05 rep 2
      mask_held_why = 'post-rep mask: mask got=None want=0x1f (ways=5)'

The predicate "every record `status=ok`" is therefore **false**, and G-pred's
literal condition **FAILED**.

**The verdict recorded for G-pred, everywhere, is `WAIVED`.**  It is not
`PASS`.  No document produced by this campaign may relabel it `PASS`, and the
outcome document's gate table carries `WAIVED` with a pointer here.  A gate
whose failure can be renamed into a pass on the day it fires is not a gate, and
the point of writing G-pred down in advance was to make that rename impossible
rather than merely unattractive.

What a waiver changes is *who decides* and *on what evidence*, not what
happened.  The measurement that follows is admitted with a known, named,
bounded defect in its precondition, and a reader who disagrees with the
judgement below can discount the campaign on that basis without having to
reconstruct anything.

## 2. The cause is identified, external to both campaigns' measurement
apparatus, and fixed.

The predecessor's `cat05`/rep2 lost its CAT mask because a **concurrent
`run_hashjoin.py --self-test-only`, run as preparation for this very
campaign**, tore down `clos_b` mid-arm.  Both silicon runners ended in

    if __name__ == "__main__":
        try:
            sys.exit(main())
        finally:
            teardown()

where `teardown()` `rmdir`s `clos_b`.  The `finally` fires on **every** exit
path, including `main()`'s early returns — `--self-test-only`, an `--out` that
already exists, a missing binary — none of which have created anything.  So a
diagnostic whose entire purpose is to check that gates *can* fail deleted a
different campaign's CAT group, and that campaign's tenant fell back to the
root CLOS at the full 15 ways.

Fixed at **`563ec54`** (`silicon_e2e: don't tear down a CLOS group this process
never created`), which guards the outermost teardown on a `_CLOS_OWNED` flag
set only in `setup_tenant()`.

**Verified by reproduction on c4 by this worker, first-hand, on the idle host
before the waived campaign started** — not accepted from the fixing commit's
message.  Matched pair at `ways=5 mask=0x1f`, which is `cat05`/rep2's exact
recorded mask, with the two runners differing only in that commit:

| step | runner | `clos_b` before | `clos_b` after |
| --- | --- | --- | --- |
| pre-fix | `fd815c6c…` (the runner G-pred's campaign registered) | PRESENT, `L3:0=001f`, `cpus_list=[4]` | **ABSENT — destroyed** |
| fixed | `a4ce56a9…` (at `HEAD` `563ec54`) | PRESENT, `L3:0=001f`, `cpus_list=[4]` | **PRESENT, `L3:0=001f`, `cpus_list=[4]` — survives** |

Both invocations printed `gates self-test passed`, so the diagnostic's own
function is unchanged; only its side effect on foreign CLOS state is removed.
The host was returned to zero CLOS groups afterwards.

Why this matters to the waiver: the failure was **not** a property of the host,
the resctrl subsystem, the CAT masks, the pinning, the victim, the tenant, or
either runner's measurement path.  It was a foreign process — identified, and
identified as *ours* — mutating global machine state.  A predecessor failure
with an environmental or apparatus cause would leave residual doubt that the
same cause is still present and would contaminate this campaign too.  This one
does not: the cause is a specific line of Python, it is removed at `HEAD`, and
its removal is demonstrated above.

### Registered deviation this fix forces, stated here rather than buried

The pre-registration froze the harness at `run_hashjoin.py` sha256
`fd815c6c772cec03fd60fcd7055b4b763b770370bd02d428c39de61047ef6700`.  The
campaign will run **`a4ce56a99db78a412ef6c2921f913670fdaf2a813833414476ca757a58989079`**,
that file at `HEAD` `563ec54`, because running the known-defective runner to
honour a hash would be absurd.  This is a deviation from the registration and
is recorded as one.  Its scope is bounded by inspection of the whole diff:

- the only changes are a module flag `_CLOS_OWNED`, its assignment inside
  `setup_tenant()` after a successful `setup_b`, and `if _CLOS_OWNED:` on the
  outermost `finally`;
- nothing in the geometry, arm list, rep count, gate predicates, measurement
  window, timing, or record fields is touched;
- **on the campaign's own execution path the two runners are behaviourally
  identical**: the campaign calls `setup_tenant()`, so `_CLOS_OWNED` is `True`
  and the exit teardown still runs exactly as registered.  The change alters
  only early-return paths, which a 105-record campaign does not take.

`gates.py` is unchanged and still matches its registered
`0e63ebdeae826f5f11e008596d540ccaf173e9b23d754db1091b9887cf303013`.

The staged harness tree `/home/domin/sil_e2e_rerun/head_tree/` was re-archived
from `HEAD` (`git archive 563ec54`, 102 tracked files) so that the runner
executed corresponds to a commit rather than to an edited working tree.  A
`diff -rq` against the tree the tenant was built from — retained as
`head_tree.pre563ec54/` — is **empty**, so the re-stage changed no byte on
disk; what it changed is that the bytes are now provably a commit's.

## 3. The hazard G-pred protects against is verified absent.

G-pred exists because the two campaigns share cores 4 and 6, the CAT/CLOS
masks, and node-0 hugepages, so overlap would silently corrupt both.  The
hazard is *concurrency*, not the predecessor's record count.  Evidence
gathered by this worker on c4 immediately before measuring:

    gathered_at        : 2026-09-06T01:35:54+09:00  (2026-09-05T16:35:54 UTC)
    host               : mos182
    loadavg            : 0.04 0.46 0.32
    non-root CLOS grps : 0
    clos_b present     : no
    root L3 schemata   : L3:0=7fff;1=7fff        (full 15 ways, nothing confined)
    root cpus_list     : [0-127]                 (no cpu carved out)
    IVF pid 2619758    : gone
    cxl_join_bench     : 0 running
    pointer_chase      : 0 running
    ivf_flat_bench     : 0 running
    run_hashjoin.py / run_ivf.py : none running
    IVF jsonl records  : 105
    IVF jsonl sha256   : a2d794bde1340080ce1a3347f3f8ad54b0c86628aa0d89d54fc6448341cbcbeb
    IVF jsonl mtime    : 2026-09-05 16:35:28 +0900   (final; ~9 h before this)
    IVF log tail       : == done 104 ok records -> /home/domin/ivf_run/ivf_silicon.jsonl
    node0 hugepages    : nr=8192 free=8192
    node2 hugepages    : nr=35488  (cpuless node, untouched)
    tenant sha256      : a677c52d05b75091057b5d9477fca99fef56e2087605457cfaf8f2b908a98431
    victim sha256      : 026e357ae21a99717cae3ebf4ed05fa2cd146bda4f110afe4a2f7b829ef2db50
    runner sha256      : a4ce56a99db78a412ef6c2921f913670fdaf2a813833414476ca757a58989079

The process check is self-match-free: `pgrep -f` on these patterns matches the
checking shell's own command line, which produced a spurious non-zero count on
the first attempt; the numbers above come from `pgrep -x` on `comm` plus a full
enumeration of the user's processes.  The only long-lived user processes on c4
are two `sleep 15` watcher loops dating from 2026-08-21, which were also
present throughout the original 105-record campaign.

`/home/domin/ivf_run/` was read and not written.  Its JSONL digest is recorded
above so that any later change to it is detectable.

### The hazard was NOT absent an hour earlier, and that is recorded here too

This section would be dishonest if it reported only the clean snapshot.
Between 01:26 and 01:33 on 2026-09-06, **c4 was not idle**, and the first
attempt at this campaign was destroyed and discarded as a result.  The
sequence, reconstructed from `/var/log/auth.log`'s `sudo` records, which
distinguish actors by `PWD`:

| time | actor | action |
| --- | --- | --- |
| 01:24:59 | this worker | idle check: load 0.00, 0 CLOS groups, node0 `nr=1024` — **clean** |
| 01:26:06, 01:26:34 | **a third actor** (`PWD=…/head_tree`, relative paths, ssh from 192.168.60.181) | its own `setup_b 5 4` + `teardown` pairs |
| 01:26:55 | that actor | `tee …/node0/…/nr_hugepages` — grew node 0 to 8192 |
| 01:28:05 | that actor | launched `run_hashjoin.py … --out …/silicon_e2e_hashjoin_clean.jsonl --huge2m` via `setsid`, PPID 1 |
| 01:28:16 | **this worker** | `setup_b 5 4`, `setup_b 5 4`, `teardown` — the §2 reproduction, during that run's `wb` arm (ts 01:28:15) |
| 01:28:38 | **this worker** | `setup_b 5 4`, `teardown`, `setup_b 5 4`, `teardown` — during its `nta` arm (ts 01:28:33) |
| 01:29:00 | this worker | second idle check — discovers load 0.88 and node0 `nr=8192 free=4080` |
| ~01:33 | this worker | stopped that runner at 11 records, tore down the `clos_b` it orphaned, moved its output aside |

So this worker committed, in a milder form, the very fault §2 documents: it ran
CLOS-mutating diagnostics without re-verifying immediately beforehand that
nothing else held the host.  The idle check at 01:24:59 was four minutes stale
by 01:28:16, and four minutes was enough.  The operational lesson, which is
stronger than the one `563ec54` fixes: **an idle check authorises only the
action taken immediately after it**, and a diagnostic that mutates global state
needs its own check, not an inherited one.

Two honest qualifications on the damage, because overstating it would be as
bad as hiding it:

- **The exposure was sub-second.** Each `setup_b`/`teardown` pair carries the
  same `auth.log` timestamp, so `clos_b` existed for well under a second inside
  measurement windows of 12–19 s.
- **No damage is detectable in the discarded records.** Against the corrupted
  dataset's per-arm medians, that run's `wb` rep1 was **−0.26 %** on victim
  cyc/load and **+0.42 %** on tenant tuples/s, and its `nta` rep1 **+2.13 %** /
  **+0.31 %** — the two arms this worker's mutations overlapped are the two that
  look most ordinary.

That run was nevertheless **voided and not used**, for reasons that do not
depend on whether it was damaged:

1. **Its statistics predate any waiver.**  Its first record is
   ts 2026-09-06T01:28:06; this waiver was not committed.  The campaign's whole
   claim to precedence is that no statistic exists before the instrument that
   admits it, and for that run the claim is simply false and cannot be repaired.
2. **Its provenance cannot be vouched for.**  This worker did not launch it,
   does not know what authorised it, and cannot certify what else that actor
   did to the host during it.
3. **Sub-second CLOS exposure inside a measurement window is unquantifiable
   from the record.**  For the non-CAT arms the runner's `G-mask-after` checks
   only that no CLOS group exists afterwards, which is exactly what a
   create-then-destroy leaves behind; the gate cannot see it. "Probably
   harmless" is not a gate verdict.

Its 11 records are retained, unanalysed, at
`/home/domin/sil_e2e_rerun/out/VOIDED_2026-09-06_precedence_and_clos_contamination/`
— outside the repository, and named so that nothing mistakes them for results.
They are cited nowhere as evidence about the tenant.

## 4. The contamination is immaterial to the predecessor's verdict.

Not asserted — the reasoning, and the arithmetic it rests on, computed
first-hand from the published `data/ivf_flat_silicon.jsonl`:

- **The bad record is excluded, not merely flagged.**  `cat05` has all 5 reps
  present but 4 `ok`; the runner's own ok-count and every median are taken over
  the `ok` records, so `cat05`/rep2's numbers enter nothing.
- **Its arm retains 4 reps, and they are tight.**  `cat05` clean reps are
  211.85, 211.92, 211.92, 211.94 qps — a spread of 0.09 qps, 0.04 % — median
  211.923.  A fifth rep drawn from that distribution could not move the median
  materially, so the loss costs `min_reps=5` shape, not the value.
- **The verdict was decided by a different arm, with all 5 reps.**  IVF's
  terminal gate is **CAT-tax**, and it fired on **`cat01`**: 91.5 % of the
  victim tax recovered for a 9.31 % tenant QPS cost against a pre-registered
  10 % bar.  `cat01` has 5 `ok` reps.  `cat05` is read by no gate.
- **The contaminated record's direction is known and would not have helped
  either.**  `cat05`/rep2 reports `wb`'s values (224.93 qps / 155.500
  cyc/load) rather than `cat05`'s (211.92 / 107.899), because removing cpu 4
  from `clos_b` returned the tenant to the root CLOS at 15 ways.  Admitting it
  would have been a false null, which is what the predecessor's `G-mask-after`
  was added to prevent, and it did.

The predecessor's owner reached the same conclusion independently at
**`e13e9d2`**: *"That does not change any verdict: `cat05` is not the arm any
gate reads."*  Two workers agreeing is not proof, but the agreement is on the
arithmetic above rather than on each other.

Note what this bullet list does **not** claim: it does not claim the
predecessor is unblemished, and it does not decide whether `cat05`/rep2 should
be re-run.  That decision belongs to the predecessor's owner and is unaffected
by this waiver; if it is re-run it will need cores 4/6 and the CLOS groups, and
must be sequenced against this campaign by whoever owns them.

## 5. No other gate is touched.

A waiver on a *predecessor* gate is not a licence to adjust anything that
measures the thing under test.  Explicitly, and for the avoidance of any doubt
when the results are read:

- **`G-exact`** stands exactly as registered: `matches` must equal
  **536,870,912** in every non-`qui` record; any deficit, of any size, VOIDs
  the run.  It is not relaxed, not made advisory, and not re-anchored to the
  corrupted dataset's 534,773,760.
- **`D1`–`D4`** stand exactly as registered, with the `ENVELOPE_P95` table and
  the 2.0 pp / 1.0 pp / ±2.0 pp / ±0.5 pp / ±3 % thresholds frozen at
  `afdeb8f`.  In particular the D1–D4 escape clause stands: **if any of them
  fails, the required action is to say so loudly and treat every silicon e2e
  number as open pending diagnosis**, and it is *not* permitted to relabel a
  material shift as a correction and move on.
- **`G-tenant`, `G-clean`, `G-shape`, `G-status`, `G-host`, `G-geometry`,
  `G-pages`, `G-window`, `G-runner`** stand as registered, as do the runner's
  in-flight admission gates **G-idle, G-mask, G-clos, G-live, G-size,
  G-mask-after**.
- The analyzer `silicon_e2e/rerun_analyze.py` is **not** edited by this waiver.
  Its thresholds and gate predicates remain those committed at `afdeb8f`.

The only registered text this document alters is G-pred's status, from
`FAIL — STOP` to `WAIVED`, and the harness hash deviation recorded in §2.

## 6. What a reader should take from this

The campaign that follows measures a corrected tenant against a corrupted one
on a host whose predecessor campaign lost one record of 105 to a
now-fixed footgun in a sibling runner, and whose idleness was verified — after
one failed and discarded attempt — immediately before the first arm.  If
`G-exact` passes and `D1`–`D4` hold, the artifact is sound and no published
number moves.  If they do not, this waiver is not the reason, and the
pre-registration says what to do instead.
