# Outcome: silicon hash-join e2e clean re-run

Date: 2026-09-04.
Pre-registration: `SILICON_E2E_RERUN_PREREG_2026-09-04.md`, commit
**`afdeb8f8f15594d325dda97aac58463f18cb804f`**, authored 2026-09-05T11:39:58+09:00.

## Verdict: NOT RUN — G-pred STOP

**No arm of this campaign was measured.**  The registered precondition on the
predecessor campaign failed, and the registration makes that an unconditional
stop.  What was prepared is complete and verified; what was measured is
nothing.  The remaining sections say exactly which registered gates were
evaluated, which could not be, and what a follow-up needs.

| registered gate | verdict | note |
| --- | --- | --- |
| **G-pred** (predecessor clean) | **FAIL — STOP** | IVF finished 105 records but **104 ok, 1 `gate_fail`** |
| **Positive control** | **PASS** | deficit exactly 0 at two sizes and on the hugepage path |
| **G-tenant** | PASS (pre-flight) | HEAD-built tenant `a677c52d…`, victim `026e357a…` unchanged |
| **G-clean** | PASS | 17 pre-existing artifacts, `sha256sum -c` OK on both hosts |
| G-shape, G-status, G-host, G-geometry, G-pages, G-window, G-runner, **G-exact** | **NOT EVALUATED** | require campaign records that do not exist |
| **D1–D4** (frontier delta) | **NOT EVALUATED** | require the clean dataset |

## G-pred: what happened, and that it was self-inflicted

The IVF-Flat silicon campaign (`run_ivf.py`, PID 2619758) ran to the end of
its arm list — 105 records, runner exited at 16:36 — but its own log says
`== done 104 ok records`.  One record is `status=gate_fail`:

    arm cat05, rep 2, ts 2026-09-05T11:40:02
      mask_ok ok / clos_ok ok / idle_ok ok / ratio_ok / codebook_ok /
      recall_ok / live_ok / fb_ok / nta_ok    -- every measurement gate passed
      mask_got        001f          (5 ways, correct)
      mask_got_after  None
      clos_cpus_after ''
      clos_b_present_after  False
      mask_held_ok    False
      mask_held_why   'post-rep mask: mask got=None want=0x1f (ways=5)'

**The cause was this worker.**  While preparing, I validated the staged
harness with what I believed was a read-only invocation:

    python3 .../silicon_e2e/run_hashjoin.py --join ... --victim ... \
            --out ... --self-test-only

`run_hashjoin.py` ends with

    if __name__ == "__main__":
        try:
            sys.exit(main())
        finally:
            teardown()

and `teardown()` is `sudo bash resctrl_clos.sh teardown`, which `rmdir`s
`clos_b`.  The `finally` runs on **every** exit path, including the
`--self-test-only` early `return 0`.  So a command whose entire purpose is to
check that gates can fail deleted the predecessor's CAT group mid-arm.

This is demonstrated, not inferred.  On the now-idle host:

    sudo resctrl_clos.sh setup_b 5 4   -> clos_b present, L3:0=001f, cpus_list=4
    run_hashjoin.py --self-test-only   -> "gates self-test passed"
    after                              -> clos_b present: no

which is bit-for-bit the failure signature of `cat05`/rep2
(`mask_got_after=None`, `clos_b_present_after=False`, `clos_cpus_after=''`).
The timing corroborates it: `cat05`/rep2 opened at 11:40:02, my invocation ran
within the following minute, and `cat05`'s other four reps all recorded
`mask_after=001f, held=ok`.

**The damaged record is contaminated, not merely un-audited.**  Its numbers are
`wb`'s, not `cat05`'s:

| | qps | victim cyc/load |
| --- | --- | --- |
| `cat05`/rep2 (failed) | 224.93 | 155.500 |
| `cat05` median of the 4 clean reps | 211.92 | 107.899 |
| `wb` median (unconstrained) | 224.89 | 153.698 |

Removing cpu 4 from `clos_b` returned it to the root CLOS at the full 15 ways,
so the arm was measured with no mask at all.  IVF's **G-mask-after** — added
after an earlier campaign in which "a foreign process did delete CLOS groups
during this campaign's window; the pre-rep check not seeing it was luck" —
caught it exactly as designed, and the runner correctly excluded it from its
ok count.

Impact on IVF, for its owner to judge, not me: the other 104 records are
unaffected, each having verified its mask before *and* after; `cat05` retains
4 clean reps whose spread is 211.85–211.94 qps, so its median is unlikely to
move; but the campaign is one rep short of its `min_reps=5` shape on that arm.
**I did not touch `/home/domin/ivf_run/`**; its JSONL mtime is 16:35:28, before
any control here ran.

### Why the campaign was not started anyway

The host is, at the time of writing, idle and clean — no processes, no CLOS
groups, load 0.00 — and IVF is over, so nothing about its one bad record could
contaminate this campaign.  That argument was available and was **refused**,
for three reasons.

1. The registration is unconditional and anticipated exactly this moment:
   *"the temptation to start anyway is the reason this is written down in
   advance rather than judged on the day."*  A gate overridden the first time
   it fires, by a rationalisation built after seeing the failure, is not a
   gate.
2. The instruction that authorised this work says the same: fewer than 105
   records **or any record not `ok`** is a stop-and-report.
3. There is now a decision that is not mine: whether `cat05`/rep2 must be
   re-run.  If it must, that re-run needs cores 4/6 and the CLOS groups — the
   same resources as this campaign — so the two have to be sequenced by
   whoever owns them.

### Addendum, same day: the predecessor's owner has closed it

Recorded after this document's first commit.  `e13e9d2` publishes
`IVF_FLAT_SILICON_OUTCOME_2026-09-04.md` and
`data/ivf_flat_silicon.jsonl` (105 records), and reaches the same reading of
the same record independently:

> One record rejected: cat05 rep2, clos_b deleted mid-measurement by a foreign
> process.  Its qps and victim are wb's values, so admitting it would have
> been a false null; the mask_held guard that SILICON_E2E addendum 1 added for
> exactly this TOCTOU caught it on the next campaign.

and *"That does not change any verdict: `cat05` is not the arm any gate
reads."*  So the predecessor is closed, published, and its owner judges the
loss immaterial — and the "foreign process" is named here.

This does **not** clear G-pred, and the campaign is still not started.  The
gate's predicate is "every record `status=ok`", which remains false, and it is
not this worker's place to reinterpret a predicate it wrote yesterday because
today's news is reassuring.  What the addendum changes is the *cost* of
waiving it: the one failure has a fully identified, non-environmental cause,
so a waiver now carries no residual doubt about the host or the apparatus.
That waiver is the user's to give.

## Positive control: PASS

Registered as pre-flight, not a result.  Run after the registration commit and
after IVF had exited, so it can affect neither.  `--mode single --hit-rate 1.0
--reps 1 --warmups 0 --hot-bytes 33554432 --fact-node 0 --hot-node 0
--cpu-list 4 --policy wb`.

| tenant | fact_bytes | rows | `matches` | deficit | verdict |
| --- | --- | --- | --- | --- | --- |
| **`a677c52d…` (HEAD)** | 268,435,456 | 16,777,216 | **16,777,216** | **0** | EXACT |
| **`a677c52d…` (HEAD)** | 1,073,741,824 | 67,108,864 | **67,108,864** | **0** | EXACT |
| **`a677c52d…` (HEAD)**, `--huge2m` | 1,073,741,824 | 67,108,864 | **67,108,864** | **0** | EXACT |
| `75e0af94…` (defective) | 268,435,456 | 16,777,216 | 16,711,680 | 65,536 | = fact/4096 |
| `75e0af94…` (defective) | 1,073,741,824 | 67,108,864 | 66,846,720 | 262,144 | = fact/4096 |

The last two rows are a **negative** control the registration did not
explicitly require; they are reported as a diagnostic, not as a registered
result.  They matter because they turn the diagnosis into a matched-pair
experiment: at identical geometry, the defective binary reproduces a deficit of
exactly `fact_bytes/4096` on demand across a 4× size range, and the HEAD
binary's deficit is exactly zero — including on the `MAP_HUGETLB` path the
campaign actually uses.  The fix is in the binary that would run.

Two honest scope notes.

- **This does not prove the `hit_rate` saturation fix was ever live here.**
  As the registration said in advance, c4 has AVX-512, where `vcvttsd2usi`
  saturates and the pre-fix conversion was already correct.  The 0.390625 %
  deficit on the published dataset is attributable to the `prefault_region`
  defect alone.  The control passes both fixes at once; it isolates only the
  first.
- **The tenant's own `correct` field could not have caught this.**  Every row
  above, defective ones included, reports `"correct":true`, because `ok` is
  `!c.check || …` and `--check` is off in this mode.  That is precisely why
  G-exact is an external, arithmetic assertion rather than a reading of the
  artifact's self-report.

## Tenant provenance

| | |
| --- | --- |
| source | `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp` at `HEAD` (`785c66d`) |
| source sha256 | `b843d46595873e14708b2fe585f3a1ca75a3a4f89f5c4bc920391415bf6c7263` |
| fix commit | `abccb31`, verified an ancestor of `HEAD` |
| build | `make BUILD=/home/domin/sil_e2e_rerun/build native`, on c4, g++ 11.4.0, `-O3 -march=native`, no warnings |
| **tenant sha256** | **`a677c52d05b75091057b5d9477fca99fef56e2087605457cfaf8f2b908a98431`** |
| victim | `026e357ae21a99717cae3ebf4ed05fa2cd146bda4f110afe4a2f7b829ef2db50`, reused not rebuilt, identical to all 105 original records |

The build used a `git archive` of `HEAD` extracted to
`/home/domin/sil_e2e_rerun/head_tree`, byte-verified against the `HEAD` blob,
because **c4's checkout is not a copy of `HEAD`**: it sits at `33eaf07` (an
ancestor, predating `abccb31`) and carries *uncommitted* modifications to both
`benchmarks/e2e/hash_join/Makefile` and `src/cxl_join_bench.cpp`, the latter
hashing `e8d10458…` and matching no commit.  Nothing in c4's checkout was
read-modified or written.

Worth recording for `F13`: `build/cxl_join_bench` **on c4** *is* `75e0af94…`,
the binary all 105 published records name.  The A1 ledger notes that
`75e0af94…` "is not on this host" — true of mos181, whose copy is
`75813707…`; the bytes are on **c4**.  That is a strict improvement in
provenance and is offered as a correction for whoever owns that ledger (see
hand-back below).

## Precedence

Registration precedes every statistic, and the evidence is in git, not a
directory mtime:

- prereg + analyzer committed `afdeb8f`, 2026-09-05T11:39:58+09:00, containing
  only those two files (825 insertions, nothing else touched, nothing staged).
- The tenant was built at 11:31 — before the commit — but a build emits no
  statistic; the first `matches` of any kind, the positive control's, was
  produced at ~16:45, **five hours after** the commit.
- The frozen `ENVELOPE_P95` table and the D1–D4 thresholds were committed in
  `afdeb8f` **before** the 4K/hugepage cross-check below was ever computed, so
  they cannot have been tuned to it.

## Frontier delta: NOT EVALUATED

The registered comparison needs the clean dataset and there is none.  For
reference, the analyzer reproduces `make_eval_frontiers.py:91-98` and is
verified **bit-identical** to its `silicon_frontier()` on the existing dataset
(all 15 CAT points, all 3 fb points, the nta point), and it correctly returns
`VOID` on the corrupted dataset — G-exact firing on all 100 tenant records,
G-tenant refusing `75e0af94…`.

The nearest available proxy is the **4K-vs-hugepage pair**: two independent
105-record campaigns of the *same* defective tenant, differing in a real
physical variable (page size). Against the registered thresholds they give

    max |d protection| 2.674 pp, max |d tenant cost| 0.260 pp
    D1 PASS, D2 PASS, D3 PASS (mean signed -0.168 pp / +0.067 pp), D4 PASS

This is **not** a substitute for the registered comparison — it changes page
size rather than the tenant, and both arms are corrupted. It is evidence that
the thresholds are not so tight that campaign-to-campaign variation on this
apparatus would trip them spuriously.

## The 4K sibling: recommendation — do not re-run yet

`data/silicon_e2e_hashjoin_4k.jsonl` carries the same defect: same `sha_join`
`75e0af94…`, same `matches` 534,773,760, same 2,097,152 deficit, differing only
in `huge2m=false`.

**Recommendation: leave it in place, annotate its provenance, and do not
re-run it.**  Reasons, in order of weight.

1. **It feeds no figure.**  `make_eval_frontiers.py` reads only the hugepage
   dataset.  The 4K file supports one negative claim in
   `SILICON_E2E_OUTCOME_2026-09-01.md` — "TLB was not the mechanism.  Every
   verdict agrees" — and that claim is a corrupted-vs-corrupted comparison,
   which is *internally valid* precisely because the defect is identical on
   both sides.
2. **Re-running it would destroy evidence currently in use.**  A1 uses this
   dataset as *independent confirmation of the corruption mechanism*: the
   1/256 rate is identical at 4K and 2 MiB pages, "which is exactly what a
   hardcoded 4096 B stride in `prefault_region` predicts and what a
   fault-driven mechanism would not."  That argument needs the defective 4K
   data to keep existing.  Retention, not replacement, is the right handling —
   the same reason the hugepage original is retained rather than overwritten.
3. **A test pins its headline.**  `tests/test_silicon_e2e.py`
   (`TestSiliconE2E4kArchive`) asserts 105 records, all `ok`, all
   `huge2m is False`, "so a silent rewrite of the archive fails in make
   check."  Any re-run must write a *new* file.
4. **The decision is cheap to defer and better informed later.**  The whole
   question is whether an arm-identical 0.390625 % defect moves ratio
   coordinates.  The hugepage re-run answers that directly and, because the
   defect is bit-for-bit the same in both datasets, its answer transfers.  If
   D1–D4 pass there, the 4K file needs a provenance line and nothing more; if
   they fail, both need re-running and that is the least of the problems.

If it is later re-run: it needs explicit authorisation, must write a new file
rather than touch the existing one, and — for fidelity to the original
condition — should run with node 0's pool at its as-found 1024 pages, which is
where it is now.

Also in scope and needing no action: `data/silicon_e2e_calib_v4.jsonl`
(12 records, same `sha_join`) is apparatus, already documented as such.

## Nothing pre-existing changed

`sha256sum -c` passes on all three manifests, taken before the build and
re-checked after the controls:

- **c4** (3 entries): `build/cxl_join_bench` = `75e0af94…` **OK**,
  `pointer_chase` **OK**, `ivf_flat_bench` **OK**.
- **mos181** (14 entries): every binary under `benchmarks/e2e/hash_join/build`
  including `cxl_join_bench.gem5` = `cac9e27a…` **OK**, plus `pointer_chase`
  **OK**.
- **datasets** (2 entries): `silicon_e2e_hashjoin.jsonl` **OK**,
  `silicon_e2e_hashjoin_4k.jsonl` **OK**.

c4 is left as found: node 0 at **1024** × 2 MiB (never grown — the campaign
did not run), node 2 at 35488, **no** CLOS groups, load 0.00.  No `data/*.jsonl`
was written or modified.  `gem5/`, `/home/domin/STREAMING_Paper/`,
`A1_PROVENANCE_LEDGER_2026-08-28.md` and `INDEX.md` were not touched.

## To resume, once authorised

Everything is staged; the campaign is one command and about 40 minutes (the
original 105 records took 15:47:18 -> 16:24:45).

1. Settle `cat05`/rep2 with IVF's owner, and confirm no IVF re-run will
   overlap.
2. `bash /home/domin/sil_e2e_rerun/head_tree/experiments/asplos/silicon_e2e/setup_hugepages_node0.sh`
   (node 0 -> 8192; restore to `WANT=1024` afterwards).
3. Campaign — note `JOIN=`/`VIC=` and that the output is outside the repo:

       JOIN=/home/domin/sil_e2e_rerun/build/cxl_join_bench \
       VIC=/home/domin/DutyFree/benchmarks/bench/victim/pointer_chase \
       bash /home/domin/sil_e2e_rerun/head_tree/experiments/asplos/run_silicon_e2e.sh \
         --out /home/domin/sil_e2e_rerun/out/silicon_e2e_hashjoin_clean.jsonl --huge2m

4. Check the first `wb` record reports `matches` 536,870,912 before letting it
   run on.
5. `python3 experiments/asplos/silicon_e2e/rerun_analyze.py --clean <out> --corrupt experiments/asplos/data/silicon_e2e_hashjoin.jsonl`
6. Re-verify the three manifests and replace this document's NOT-RUN sections.

**Do not** use `--self-test-only` (or any `run_hashjoin.py` invocation) while
another campaign holds a CLOS group.  The gates self-test alone is safe;
`gates.py` is importable and `python3 experiments/asplos/silicon_e2e/gates.py`
runs the same self-test **without** the `finally: teardown()`.  Fixing the
runner so that `--self-test-only` does not tear down is a one-line change to a
file shared with published campaigns and is **not** made here; it is proposed
in the hand-back.

## Hand-back: proposed wording for docs this worker does not own

Not applied — `A1_PROVENANCE_LEDGER_2026-08-28.md` and `INDEX.md` are held by
another worker.

**For A1, correcting the location of `75e0af94…`:**

> `75e0af94…` **is on disk, on c4**: it is
> `benchmarks/e2e/hash_join/build/cxl_join_bench` in c4's checkout (verified
> 2026-09-04). The earlier note that it "is not on this host" was true of
> mos181, whose copy is `75813707…`. Silicon's `F13` position is therefore
> better than `cac9e27a…`'s: digest recorded 105 times *and* bytes present.
> The bytes are still not *reproducible* — c4's `src/cxl_join_bench.cpp` is an
> uncommitted working-tree state, sha256 `e8d10458…`, matching no commit — so
> the dataset remains non-regenerable and is retained rather than replaced.

**For A1 / `INDEX.md`, on the corrected tenant:**

> A tenant built from committed `HEAD` (`abccb31` inclusive), sha256
> `a677c52d…`, computes the join exactly: `matches` equals `fact_bytes/16`
> with zero deficit at 256 MiB and 1 GiB and on the `MAP_HUGETLB` path, while
> the defective `75e0af94…` reproduces a deficit of exactly `fact_bytes/4096`
> at the same geometries. Registered in
> `SILICON_E2E_RERUN_PREREG_2026-09-04.md` (`afdeb8f`); the 105-record
> re-run itself is **not yet measured**, blocked on G-pred.

**For `IVF_FLAT_SILICON_OUTCOME_2026-09-04.md`, naming the "foreign process":**

> The process that deleted `clos_b` during `cat05`/rep2 (ts 11:40:02) is
> identified: a concurrent `run_hashjoin.py --self-test-only` from the
> silicon-e2e re-run worker, whose module-level `finally: teardown()` fires on
> every exit path including that early return.  Reproduced on the idle host
> afterwards. It was not a stray campaign and not a host fault, so it carries
> no implication for the other 104 records, each of which verified its mask
> before and after. Apologies for the lost rep.

**Proposed runner fix, for whoever owns `run_hashjoin.py`:**

> Return from `main()` before the `finally: teardown()` can fire on the
> `--self-test-only` path — e.g. run `self_test()` and `os._exit(0)`, or hoist
> the self-test ahead of the `try`. A diagnostic that mutates global machine
> state is a footgun, and it has now cost one record of a five-hour campaign.
