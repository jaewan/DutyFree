# T3 pre-registration: is the fused same-thread tax stream-side TLB pressure?

Written **before any measurement**, per §6.6. Registers arms, metric, thresholds
and guards. Revisable only by dated addendum.

## 1. Why, and what is genuinely open

The 2026-07-29 decomposition (`results/mechanism_decomp/`) established that at
most 0.31 and possibly **0.00** of the fused same-thread tax lives in the
shared-LLC-residency channel H2 addresses — the pre-registered *"H2 story in
trouble"* band. It measured `Δ_L2fit` (the tax is essentially fully present at
L2-fit scale), `Δ_M5` (bandwidth-matched remote-socket queueing ≈ 0) and `Δ_M3`
(MSHR: `FB_FULL` grows 3.84×/11.68× but not convertible to cycles).

**It did not test page size.** That is the one mundane candidate left, and it is
cheap. The reviewer who proposed it cited "the campaign records the stream on
4 KiB pages (`AnonHugePages=0`)"; that string is not in this repository, but the
claim is nonetheless **correct by construction** and now verified by reading the
apparatus:

- `run_confirmatory_panel.py`'s three argument builders (`morsel_args`,
  `split_args`, `hotprobe_args`) pass **no `--huge2m`**.
- `cxl_join_bench.cpp:347-354` only applies `MAP_HUGETLB`/`MADV_HUGEPAGE` when
  `huge2m` is set; otherwise it is a plain anonymous `mmap`.
- The hosts run `transparent_hugepage=madvise`, under which a plain anonymous
  `mmap` receives **4 KiB pages**.

So every published fused number streamed a 256 MB–1 GB fact array through
4 KiB pages. At the 1-core operating point that is ~65,536 pages for a 256 MB
array, swept repeatedly, against an L2 TLB of order 2–3 K entries.

## 2. What `--huge2m` does and does not change

Verified by reading every caller: `alloc_bytes(..., c.huge2m, ...)` is used for
the **fact (stream)** array and a latency probe only — 7 + 1 call sites, no
others. The **hot table is a `std::vector<Entry>`** on the default allocator,
so it stays on 4 KiB pages in every arm.

`--huge2m` is therefore a **clean single-variable manipulation of the stream's
page size**, with the victim's page size held fixed. That is exactly the
hypothesis under test.

**Registered scope limit, stated now so a null cannot be overread:** a null
result excludes **stream-side** TLB/walk pressure only. The hot table is
~170 MB on 4 KiB pages (~43.5 K pages), which also exceeds L2 TLB capacity, so
victim-side walk pressure would remain untested and would need a code change
this task does not make.

## 3. Arms

Host **mos181** (EMR 8592+, CXL node 2), reproducing the panel's 1-core
operating point verbatim — `FACT_1C = "256m"`, `HOT_BYTES = 177838489`,
`MORSEL = "1m"`, `--warmups 2 --reps 1 --threads 1 --cpu-list 32`:

| arm | mode | stream pages | victim pages |
|---|---|---|---|
| **Q_4k** | `hot-probe` (no stream) | 4 KiB | 4 KiB |
| **A_4k** | `morsel` (fused) | 4 KiB | 4 KiB |
| **Q_2m** | `hot-probe` + `--huge2m` | 2 MiB (untouched) | 4 KiB |
| **A_2m** | `morsel` + `--huge2m` | **2 MiB** | 4 KiB |

n=5 per arm, **interleaved within each rep** (Q_4k, A_4k, Q_2m, A_2m; rep 2; …)
so drift spreads across arms. Per-rep values and CoV reported for every cell.

## 4. Metric

`active_cycles_per_access` from the benchmark's own JSON — the same quantity as
the decomposition's `Δ_total` and the published fused table.

    Δ_4k = A_4k − Q_4k        Δ_2m = A_2m − Q_2m        R = (Δ_4k − Δ_2m) / Δ_4k

`Δ_4k` is expected near the decomposition's 1-core `Δ_total` = **27.31 cyc**.

## 5. Pre-registered reading

| R (fraction of the fused tax removed by 2 MiB stream pages) | verdict |
|---|---|
| **R ≥ 0.25** | **Stream-side TLB is a material component.** Part of Branch B is software-fixable, the paper must say so before a referee finds it, and `Δ_M3`'s remaining share shrinks accordingly. |
| **R ≤ 0.10** | **Stream-side TLB excluded.** The private-cache + miss-tracking attribution strengthens, and the stream-buffer / MSHR-QoS fork stands as the live question. |
| 0.10 < R < 0.25 | inconclusive; report as such, do not round toward either. |

Reported alongside, not as gates: `Δ_4k`, `Δ_2m`, both taxes as ratios, and
(where the counters are available) `dtlb_load_misses.walk_completed` and
`walk_active`, which turn the result from a ratio into a mechanism.

## 6. F12 guards — a cell that fails one of these is void, not a result

1. **The manipulation must be shown to have taken.** `anon_huge_kb`, which
   `cxl_join_bench` already reports from `smaps`, must be materially higher in
   the `_2m` arms than in the `_4k` arms. A silently-failed hugepage allocation
   looks exactly like a null, and that is the one failure mode that would make
   T3 lie. (The clos_split raw records predate this field, which is why §1's
   page-size claim is established from the apparatus rather than from the data.)
2. **Internal control: Q_2m ≈ Q_4k within noise.** The quiescent arm never
   touches the fact array, so its page size must not matter. If Q moves, the
   manipulation is doing something other than what it says and the whole cell
   set is void.
3. **Operating-point check.** `Δ_4k` must land near 27.31 cyc. If it does not,
   the arms are not the decomposition's operating point and R is not comparable
   to it. Note the binary has changed since 2026-07-29, so absolute agreement is
   not required — **R is a within-T3 ratio and is the registered quantity**;
   a `Δ_4k` far from 27.31 is reported as a caveat, not silently accepted.

## 7. Out of scope

Victim-side page size (needs a code change); 1 GB pages; multi-core arms; local
vs CXL fact placement; any change to `cxl_join_bench.cpp` or to the panel
runner; converting `FB_FULL` to cycles (that is T4). No existing arm is edited —
`--huge2m` is a flag the binary already has.

---

# Addendum 1 — 2026-08-24: run 2, with the runner defects fixed

Registered **before run 2 executes**. Run 1's data and its runner (`v1`) are
retained unchanged; this is a new run with a new output path, not a revision of
run 1 (A6.19).

## Why run 2

`T3_CODE_AUDIT_2026-08-24.md` found three defects in `run_t3_hugepage.sh` that
bear on run 1's `R`:

- **D1** arm order was **fixed** (Q_4k always position 1, Q_2m always position 3),
  so a position effect cannot be separated from run-to-run variance.
- **D2** stderr was parsed then deleted, discarding every in-band diagnostic —
  including `HOT_TABLE_ROUNDED`, which is why the 256 MiB instantiated hot table
  was missed at the time.
- **D3** a failed sysfs read would make `hugetlb_pages_used` evaluate to `0`
  through bash arithmetic on the string `NA`, reading as *"the manipulation did
  not take"* — indistinguishable from a genuine negative.

## What changes, and what does not

**Changes (runner only, `run_t3_hugepage_v2.sh`):** arm order is a **randomized
Latin square** — 3 blocks of 4 reps, each block a randomly-labelled, randomly-ordered
4x4 square, from a recorded seed — so every arm occupies **every position exactly
3 times** over 12 reps and the order is reproducible.

*Why a Latin square rather than a simple per-rep shuffle.* A simple shuffle was
written first and checked before running: over 12 reps at the intended seed it put
`Q_4k` in position 1 **zero** times and in position 4 **six** times, while `A_4k`
took position 1 five times. That reproduces the very confound run 2 exists to
remove, merely relocating it. The Latin square guarantees position balance by
construction. This choice is made on design grounds, with no data in hand, and is
recorded here rather than silently substituted — it is not seed selection: the
seed is fixed at 20260824 and the balance property holds for any seed;
per-arm stderr is **archived**, not deleted; the hugepage guard emits `NA`
rather than a misleading `0` when a read fails; and the **instantiated** hot
table size is captured from the binary's own `HOT_TABLE` line, closing the gap
that produced the error in run 1's outcome document.

**n rises from 5 to 12 per arm.** Run 1 established that the quiescent arm is
bimodal with a 16.3% spread; at n=5 the mean depends heavily on how the modes
happen to split. n=12 roughly halves the standard error and samples both modes
more reliably. This is the only design parameter changed and it is changed
*because* run 1 characterised the variance, not because of where R landed.

**Unchanged:** arms, operating point, metric, thresholds, guards, and §7's scope
limits, all exactly as registered in the body above. `cxl_join_bench.cpp` and
`run_confirmatory_panel.py` remain untouched.

## Registered readings for run 2

`R` and its thresholds are as in §5 (R ≥ 0.25 material / R ≤ 0.10 excluded /
between inconclusive), with the disagreement rule fixed **now**:

| run 2 outcome | how it is reported |
|---|---|
| **R ≤ 0.10** | run 1's verdict confirmed, and R is now quotable |
| **R ≥ 0.25** | **run 1's verdict was wrong.** Report the reversal as the headline, prominently, and treat run 1's `R` as having been an artefact of the fixed arm order |
| 0.10 < R < 0.25 | inconclusive on R; the walk arithmetic below remains the primary evidence and is reported as such |

Two further registrations:

1. **The walk arithmetic is primary, not R.** The comparison of the stream's
   measured walk reduction against the ~99.8% its 512× page-count reduction
   predicts is independent of arm order and of timing. It is reported in every
   outcome regardless of what R does. Run 2 is a check on R, not on that.
2. **Q_4k vs Q_2m is now an honest same-configuration replicate pair.**
   `run_hot_probe()` never calls `alloc_bytes()`, so `--huge2m` is a no-op there
   and the two labels are the same execution; under randomized order their
   difference estimates pure run-to-run variance. **Registered check:** if the two
   Q labels differ by more than their pooled spread, something is order- or
   state-dependent and the whole cell set is suspect. In run 1 they differed by
   2.97 cyc against a pooled sd of ~3.5 — consistent with variance, but with the
   order confound unresolvable.

**No tuning.** If run 2 disagrees with run 1, the disagreement is the result.
Nothing about the arms, n, seed, or thresholds may be adjusted after seeing it.
