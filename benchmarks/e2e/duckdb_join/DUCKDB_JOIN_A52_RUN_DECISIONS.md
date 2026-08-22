# A5.2 run decisions, written before the measurement

`moscxl`, 2026-08-22. Implements A5.2 of `DUCKDB_JOIN_CORUN_PREREGISTRATION.md`.
Written and committed **before** any 10-repetition data exists, per §6.6.

## What A5.2 declared

> Repeat one arm (`FB256_match`, the worst) with the victim's build arena
> pre-faulted from hugepages, 10 repetitions, everything else identical.
>
> - Between-invocation occupancy spread falls below 3% (against 6.2% measured
>   here) **and** CoV_rep falls below 5% -> page placement is the driver and is
>   controllable.
> - Spread and CoV both essentially unchanged -> not the driver; the
>   instability is reported as physical.
> - Anything between -> no conclusion, and no re-run.

## Decision 1: how the manipulation is applied, and the proof that it took

The frozen host runs `transparent_hugepage=madvise`, `defrag=madvise`. So an
`LD_PRELOAD` shim (`tools/thp_arena.c`) that marks the victim's large anonymous
mappings `MADV_HUGEPAGE` and pre-faults them with `MADV_POPULATE_WRITE` obtains
2 MiB backing **without changing one byte of host state**. The freeze at
`d8eda44` stands untouched, which it would not if I had written `always` to the
THP knob.

The shim is applied **to the victim only** -- `LD_PRELOAD` goes into the
victim's `subprocess.run` environment, never the aggressor's -- so the
streamer's page placement is held fixed and hugepage backing is the single
thing that differs.

Pre-faulting is capped at 512 MiB per mapping. DuckDB reserves far more address
space than it touches, and populating a multi-gigabyte reservation would change
the workload rather than its page backing. Above the cap a region still gets
`MADV_HUGEPAGE` and faults in as huge pages on demand.

**The shim reports what it actually obtained, per invocation, into the record
as `victim_thp`.** This is not decoration. A shim that silently failed to get
hugepages would produce a null result identical in every respect to a genuine
one, and that is the only way this diagnostic could lie. A single-repetition
smoke test already confirms it works: 11 mappings marked over 37 MiB, all
populated, **24 MiB of `AnonHugePages`** in `smaps_rollup`, against 0 kB
host-wide before. Any repetition reporting `anonhuge_kb = 0` invalidates that
repetition rather than contributing a null.

The smoke test also shows the manipulation does not move the operating point:
median 0.0340 s against the campaign's 0.0340, occupancy 6.77 MiB inside the
campaign's 6.4--7.3 band, streamer 15.39 GB/s against 15.42.

## Decision 2: the comparator estimator is pinned now

A5.2 names "6.2%" without an estimator. Recomputing from
`artifacts/join_corun_moscxl.jsonl`, three candidate definitions give:

| estimator | value |
|---|---:|
| CoV of per-invocation **mean** occupancy | **5.95%** |
| CoV of per-invocation median occupancy | 7.08% |
| CoV of per-invocation steady occupancy | 5.77% |

The AMD outcome document says "the invocation's *mean* victim occupancy" where
it discusses this quantity, so **the mean is the declared estimator and the
comparator is 5.95%**. The pre-registration's 6.2% is not reproduced exactly;
the 0.25-point difference is an estimator detail from the earlier session. The
threshold is 3%, far from every candidate, so nothing about the verdict turns
on this choice -- which is precisely why it is safe to pin it now and why it
would not have been safe to pin it afterwards.

`CoV_rep` reproduces exactly: **13.10%**, from raw per-repetition medians of
`trial_seconds_measured`.

## Decision 3: two arms are added, and neither can create a pass

**A contemporaneous no-shim control**, `FB256_match` with `VICTIM_PRELOAD`
unset, 10 repetitions, run in the same session. A5.2's comparator is historical
(2026-08-21). A same-day control removes the possibility that any change is
attributed to hugepages when it belongs to something that drifted since. **If
the control does not reproduce the historical 13.10% / 5.95%, the diagnostic is
inconclusive whatever the shim arm does**, because the comparator itself would
be unstable. Declared as a validity condition, not as an outcome.

**The quiescent arm**, 10 repetitions, both with and without the shim, to see
whether hugepages move the victim's baseline at all. Its campaign CoV_rep is
1.74%, at the timer's half-quantum floor.

Neither addition can convert a null into a pass: the decision rule is stated on
`FB256_match`'s spread and CoV_rep alone, and both thresholds were fixed in
advance.

## Decision 4: order is a disclosed limitation

The runner takes `VICTIM_PRELOAD` process-globally, so the shim and no-shim
arms cannot be interleaved within one invocation of it, as the campaign
interleaves its arms. They run as two consecutive blocks, control first,
roughly 12 minutes each. Time-ordered drift over ~25 minutes on a frozen idle
host is the residual confound and is disclosed rather than corrected. If the
two blocks differ, the quiescent arm in each block is the check on whether
something drifted between them.

## What a pass would and would not establish

Restated from A5.2 because it is easy to lose: hugepages change the victim's
TLB behaviour as well as its page colouring. A pass identifies a **controllable**
cause. It does not identify colouring specifically, and nothing written from
this may say that it does.
