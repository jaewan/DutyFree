# DuckDB many-to-many hash join responds, on both vendors

**Provenance warning, read first.** These measurements were taken by a panel
investigation that was **terminated mid-campaign** by an API session limit,
while **other panel investigations were running on the same hosts**. There is
no pre-registration, the Intel sizing sweep the protocol requires was not
finished, and no arm was taken under host exclusivity. Nothing here may be
cited. It is committed because the effect it reports is large, mechanistically
corroborated, and cheap to re-establish cleanly -- and because the binary and
queries would otherwise have been lost with a session scratchpad.

## What was found

DuckDB v1.1.3 (`19864453f7`), single query thread pinned, victim tables on the
CXL node, aggressor 8 threads on the same socket. The victim is a **many-to-many
equi-join**: the build table carries N rows over N/8 distinct keys, so every
probe key matches about eight build rows and the probe walks a duplicate chain
inside DuckDB's hash table. `queries/`, `query_chain8_b*.sql`.

**This is the same engine that has been a null in this project since exp40 --
DuckDB scan, 0.99x.** The difference is the operator, not the engine: a scan
has no reuse, a chained join probe has both reuse and a dependent chain.

### CAT capacity-sensitivity gate, quiescent, full mask vs one way

| host | config | victim node | occupancy full/1-way | ratio |
|---|---|---|---:|---:|
| `moscxl` | chain8 b256K | node 2 | 14 / 0 MiB | **5.726** |
| `moscxl` | joinuniq b256K | node 2 | 14 / 0 MiB | **4.125** |
| `mos181` | chain8 b4M | node 2 | 204 / 24 MiB | **2.432** |
| `mos181` | chain32 b4M | node 2 | 180 / 36 MiB | **2.045** |
| `mos182` | chain8 b1M | node 0 | 56 / 11 MiB | **2.035** |
| `mos182` | chain8 b250K | node 2 | 32 / 8 MiB | 1.975 |
| `mos181` | groupby 4M groups | node 2 | 212 / 16 MiB | 1.727 |
| `mos181` | star 3-join 1.5M dim | node 2 | 261 / 17 MiB | 1.652 |
| `mos181` | joinuniq b2M | node 2 | 181 / 20 MiB | 1.641 |

**All three hosts clear 2x on at least one configuration**, and every row
satisfies the validity condition the panel's referee demanded (reused set well
above the minimum expressible mask; occupancy tracks the granted mask). Note
`joinuniq` -- unique build keys, no duplicate chain -- lands at 1.64 where
`chain8` lands at 2.43 on the same host and build size. **The chain is the
variable**, which is the mechanism claim stated as a within-engine control.

### Real co-run: tax, and recovery

| host | config | arm | aggressor | BW | victim occ | median s | tax |
|---|---|---|---|---:|---:|---:|---:|
| `mos181` | chain8 b6M | quiescent | -- | -- | 305 MiB | 2.030 | 1.000 |
| | | WB local DRAM | wb_local x8 | 108 | 16 MiB | 4.100 | **2.020** |
| | | WB CXL | wb_load x8 | 23.9 | 94 MiB | 7.810 | **3.847** |
| | | NTA CXL | wb_prefetchnta x8 | 17.4 | 267 MiB | 2.930 | **1.443** |
| `mos181` | chain8 b4M | quiescent (x2) | -- | -- | 225/235 MiB | 1.771/1.780 | 1.000 |
| | | WB local DRAM | wb_local x8 | 108.3 | 33 MiB | 3.428 | **1.935** |
| | | NTA local DRAM | wb_prefetchnta x8 | 17.4 | 214 MiB | 1.923 | **1.086** |
| `moscxl` | chain8 b256K | quiescent (x2) | -- | -- | 12/14 MiB | 0.721/0.733 | 1.000 |
| | | WB CXL | wb_load x7 | 24.25 | 0 MiB | 11.070 | **15.35** |
| | | WB local DRAM | wb_local x7 | 47.5 | 0 MiB | 8.614 | **11.95** |
| | | NTA CXL | wb_prefetchnta x7 | 14.2 | 0 MiB | 9.160 | **12.70** |
| | | flush-behind 256 KiB | amd_flushbehind x7 | 17.1 | 12 MiB | 2.535 | **3.51** |

Recovery fractions: `mos181` b6M **84.4%** via PREFETCHNTA; `mos181` b4M
**90.8%**; `moscxl` **82.5%** via flush-behind, which is within a point of the
76.3% the hand-rolled hash join already reports.

**The occupancy column is the mechanism, measured.** The victim holds 305 MiB
quiescent, is stripped to 16-94 MiB by a write-back streamer, and is restored
to 267 MiB by a non-allocating one. On AMD it is stripped to *zero* and
restored to its full 12 MiB by flush-behind. This is the abstract's claim --
interference follows allocation -- as a directly observed cache-occupancy
transfer rather than an inference from runtime.

### An unplanned result about advisory controls

PREFETCHNTA recovers **84-91% on Intel** and **18.5% on AMD** (15.35x -> 12.70x),
where flush-behind on the same AMD host recovers 82.5%. Same instruction, same
intent, opposite outcome by vendor. That is the paper's "every address-scoped
control that ships is either advisory or bundled" argument turning up as a
measurement instead of a specification reading, and it is the strongest single
piece of support for L2 that this project has produced.

### MLP=1 latency ladder, same session (`cxl_join_bench --mode latency`, ns)

Quiescent: 2 MiB 13.72, 8 MiB 36.25, 32 MiB 48.53, 128 MiB 54.41, 512 MiB 87.79
(node 0); 512 MiB node 2 127.01.
Loaded at 128 MiB node 2: `wb_load` CXL **7.61x**, `wb_prefetchnta` CXL
**1.32x** -- a *lower*-bandwidth aggressor (17.5 vs 24.5 GB/s) causing almost no
tax. At 512 MiB the same WB aggressor gives 6.33x.

## The control this campaign is missing, and it is the important one

Every recovery arm above moves **less bandwidth** than the write-back arm it is
compared against (17.4 vs 23.9 GB/s on Intel; 17.1 vs 24.25 on AMD). So the
recovery is not yet attributable to non-allocation rather than to reduced
bandwidth. The paper's own de-confound is to hold the byte stream fixed and
change only the memory type; that was not done here.

**Required before any of this is cited: a write-back aggressor throttled by
thread count to the NTA arm's achieved bandwidth.** If the tax persists at
matched bandwidth under write-back, allocation is the cause. If it collapses,
these numbers are a bandwidth result and the campaign is void. The `-R` pacing
flag must NOT be used for this -- the E2E prompt records it as carrying a known
confound -- so vary thread count.

## What a clean campaign needs

1. Host exclusivity. Concurrent panel work invalidated at least one other
   agent's gate and may have perturbed these numbers.
2. Pre-registration naming the victim, build size per host, arms, and the
   matched-bandwidth control, before the first arm.
3. `bergamo_freeze.sh` applied and captured on `moscxl` -- it is still
   `schedutil` with boost on and no AMD platform state has ever been recorded.
4. n >= 10 rep-interleaved with matched quiescent baselines from the same run,
   CoV <= 5%, 95% rep-paired bootstrap intervals.
5. An even measured trial count, per the GAPBS parity defect.
6. Per-host build sizing declared in advance: the reused hash table must sit
   above the minimum expressible CAT mask and below about half the LLC. That is
   why `moscxl` uses b256K where `mos181` uses b6M, and it is legitimate only
   because it is declared.

## Reproducing

`bash scripts_setup_duckdb.sh` fetches DuckDB v1.1.3 to `~/duckdb-1.1.3`
(already present there). Queries in `queries/` and `query_chain8_b*.sql`;
runners `runner_corun_mos181.sh`, `runner_cat_gate_{amd,mos182}.sh`,
`amd_corun.sh`, `amd_fb.sh`. Aggressor is the existing
`~/tmp_dutyfree_exp/bin/aggressor`.
