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
