# Pre-registration: DuckDB as CAT tenant on silicon (named-engine join)

Date: 2026-09-01, **before any measurement**. No silicon arm of this
campaign has run. A local SQL/JSON parser smoke is apparatus, not a result.

This file licenses a campaign. It is not an outcome. Do not quote query
seconds, victim cycles, or CAT costs from it.

## Why this campaign exists

The silicon hash-join e2e (`SILICON_E2E_OUTCOME_2026-09-01.md`) priced CAT /
flush-behind / `prefetchnta` on `cxl_join_bench` in application units. A
reviewer can still call that binary a costume. This campaign puts the **same
CAT question** on the join operator **inside DuckDB v1.1.3**: CAT on the
DuckDB PID (and a pointer-chase neighbour), metric = **query seconds**.

It answers Reviewer #2’s costume objection for **this operator in this
engine**. It does **not** put STREAMING in DuckDB. It does **not** add
`prefetchnta` or flush-behind on DuckDB’s probe scan (do not patch DuckDB).
nta/FB stay priced on `cxl_join_bench`. STREAMING stays model-only on the
kernel.

## What this is not

- **Not** the mos181 70-arm campaign in
  `benchmarks/e2e/duckdb_join/DUCKDB_JOIN_CORUN_OUTCOME.md`. That campaign
  measured DuckDB as the **victim of a streamer** (wrong polarity). It must
  not share a table with this tenant CAT sweep and is not this campaign.
- **Not** a STREAMING result. STREAMING is not an arm. Any figure that later
  combines these silicon numbers with a modelled STREAMING point must label
  platforms.
- **Not** an amendment of any prior DuckDB JSONL or outcome. New files only
  (A6.19).

## Apparatus (clone silicon hash-join e2e, swap tenant)

- **Host: mos182 / `ssh c4` only.** Same rule as silicon e2e: not mos181
  (gem5 host). Exclusive. The runner refuses any other hostname.
- Xeon Platinum 8462Y+, socket-0 L3 **60 MiB**, 15-way `cbm_mask=7fff`.
- Pinned to **socket 0**: tenant CPU **4**, victim CPU **6** (distinct
  physical cores, not SMT siblings). `numactl --physcpubind` + `--membind=0`.
  Node 2 is the cpuless 256 GiB node and is **not** used (same pin as
  `SILICON_E2E_PREREGISTRATION_2026-09-01.md`). This is **not** the old
  DuckDB campaign’s CXL node-2 placement.
- CAT: `benchmarks/e2e/hash_join/scripts/resctrl_clos.sh setup_b` — tenant
  CPU only in `clos_b`, victim left in the root CLOS with the full 15-way
  mask (“confine the polluter”). After DuckDB starts, its **PID is written
  to `clos_b/tasks`**. `cat15` under `setup_b` is the full-mask CLOS control
  and should match `wb`.
- Victim: `benchmarks/bench/victim/pointer_chase`, 32 MiB WSS, node 0.
  Window starts at `DUCKDB_MEASURE_BEGIN` (after warmup query) and ends at
  `DUCKDB_MEASURE_END`. Refuse `status=ok` when `victim_n_trials < 1`.
- Tenant: DuckDB **v1.1.3** (`19864453f7`), binary from
  `scripts_setup_duckdb.sh` / `$HOME/duckdb-1.1.3/duckdb`. `SET threads=1`
  for generation and for the measured query. Record `--version` and sha256
  per arm. Rebuild nothing on a stale c4 tree without recording sha.
- Reused: `experiments/lib/dutyfree/resctrl.py` (schemata / occupancy),
  silicon e2e idle/mask/CLOS gates.

## Geometry (registered now, not chosen later)

DuckDB’s reused set is analytic, from
`benchmarks/e2e/duckdb_join/DUCKDB_JOIN_CORUN_PREREGISTRATION.md` amendment
A1:

    R(N) = 8N + 32N = 40N bytes

Target the silicon join’s ratio: **~32 MiB reused set on 60 MiB LLC (0.53)**.

| knob | value | why |
|---|---|---|
| build rows **N** | **838864** | divisible by 8; `40N = 33,554,560 B = 32.000122 MiB` |
| **R(N)** | 33,554,560 B | codebook-equivalent reused set |
| **R / LLC** | 33,554,560 / 62,914,560 = **0.5333** | same 32/60 as the join |
| chain8 **K** | N/8 = **104858** | ~8 matches per probe key |
| joinuniq **K** | **N** | unique keys, same N (within-engine control) |
| probe rows **P** | **10,000,000** | `8P = 80e6 B > 60 MiB LLC` → one-pass scan |
| threads | **1** | `SET threads=1` |
| L2 (per core) | 2 MiB | 4×L2 = 8 MiB (not L2-resident floor) |
| occupancy window on **R(N)** | **(8 MiB, 36 MiB]** | not L2-resident; ≤ 60% of 60 MiB LLC |
| victim WSS | 32 MiB | same as silicon e2e |
| query count | 1 warmup + **12** measured (even) | median of measured real seconds |

`N = 838864` is the nearest multiple of 8 to `32 MiB / 40`. The old DuckDB
A1 window for mos182 listed N ≤ 750K so that `R < 0.5 × LLC`. This campaign
**deliberately** matches the join’s 0.53 ratio; 32 MiB is still under the
60% occupancy ceiling (36 MiB).

**Occupancy validity** applies to the **analytic reused set R(N)**, which
sits in (8 MiB, 36 MiB]. Process CMT while a >LLC probe is in flight is
expected to fill the LLC under `wb` — that is the pollution K1 needs. Do
**not** apply the 60% ceiling to process CMT during the stream. CMT of the
DuckDB CLOS is still recorded every arm (median after `MEASURE_BEGIN`).
**G-cat-occ:** median CMT at `cat01` must be < median CMT at `wb` (the mask
constrained capacity). If that fails, the CAT arm is not an arm.

Probe **P = 10M** is larger than A2’s mos182 P = 1M. A2 shrank the probe
because DuckDB was then the **victim** competing with its own scan. Here
DuckDB is the **tenant**; the probe is the polluting stream (join-analog of
the 8 GiB fact). P > LLC so a single scan is one-pass relative to the LLC.

joinuniq is run at the **same N and P**, `wb` only (arm `wb_joinuniq`), not
a second CAT frontier. If chain8 and joinuniq median query seconds under
`wb` agree within 5%, the duplicate chain is not the mechanism and the
claim narrows to hash-table reuse. That diagnostic does not void K1–K3.

Tables are built **once** per (N, chain, P) into a persistent database,
opened `-readonly` for measurement, generation `SET threads=1`. Build is
apparatus, not an arm.

## Arms

| arm | mechanism | how |
|---|---|---|
| `qui` | quiet victim | pointer-chase only; no DuckDB |
| `wb` | none (baseline) | DuckDB chain8 + victim, no CLOS |
| `wb_joinuniq` | within-engine control | same N/P, unique keys, no CLOS |
| `cat01` … `cat15` | CAT capacity mask | DuckDB confined to w of 15 ways |

A **full CAT frontier**, not two points. No `nta`. No `fb*`. No STREAMING.
An artifact that carries those identities is not this campaign (G-identity).

`cat15` is the full-mask CLOS control. Complementary `setup_c` is not used
(`cat15` would be inexpressible).

## Metrics

Per (arm, rep), median across reps of ≥ 5:

- DuckDB **query seconds** (median of the 12 measured `.timer` real times)
- victim **`cyc_per_load`** (and p99)
- CMT **`occupancy_bytes_steady`** of the DuckDB group (CLOS or mon group)

Checksum: `count(*)` and `sum(payload)` must match across chain8 arms
(G-live). joinuniq has its own checksum.

## Kill / pass (written before data)

- **K1 (void if no pollution).** `wb` degrades the chase by **≥ 1.30×**
  over `qui` on median `cyc_per_load`. Same floor as silicon hash-join S1.
  If the engine does not tax the neighbour at this scale, there is nothing
  to protect and the campaign is **void**.
- **K2 (void if 1-way CAT does not move query time).** Median query seconds
  at `cat01` must exceed **both** `wb` (no CLOS) **and** `cat15` (full-mask
  CLOS) by **≥ 5%**. If 1-way CAT does not slow the engine, the reused set
  was never starved: the costume-killer **fails** and the campaign is
  **void**.
- **K3 (success; named-application claim).** At the CAT width with best
  victim protection R, the engine’s median query-second cost vs `wb` is
  **≥ 10%** (same qualitative floor as silicon S4; magnitude will differ
  from the join’s 42% tuples/s). Then E5 may retract “no named-application
  claim” for **this operator in DuckDB**, still one family. Paper sentence
  if it fires: shipping CAT cannot name the probe scan vs the hash table
  inside DuckDB; the tax is in query seconds. STREAMING remains model-only
  on the kernel.

**Void** (K1 or K2 fail, or a gate failure, or incomplete): not a result.
**Null** (K1 and K2 pass, K3 fails): valid measurement; keep the hash-join
kernel as the e2e cell; do **not** force IVF to save the named-app claim.
**Success** (K3): the named-engine sentence is licensed for this operator
only.

## Admission gates

- **G-host:** hostname is `mos182` or `c4`. Any other host is not this
  campaign. mos181 is refused in the runner.
- **G-idle:** `load1 < 8` and zero foreign `comm` names (`gem5.*`,
  `cxl_join_bench`, `pointer_chase`, `duckdb`, …) **before each arm**. Same
  operational load ceiling as silicon e2e (0.5 is unreachable in the
  inter-arm gap on this 128-core host).
- **G-mask:** read `schemata` back and compare **as integers**.
- **G-clos:** tenant CPU in `clos_b`; victim CPU is not (RMID collision).
- **G-pid:** DuckDB PID is in `clos_b/tasks` on every CAT arm.
- **G-mask-after:** re-read schemata and `cpus_list` after the measurement,
  before teardown.
- **G-live:** nonzero query seconds, `victim_n_trials ≥ 1`, checksum matches
  the `wb` chain8 (or `wb_joinuniq`) reference.
- **G-geom:** every chain8 record has N=838864, P=10,000,000, chain=8;
  `R(N)=40N` in the occupancy window. joinuniq: same N/P, chain=1.
- **G-threads:** measured SQL contains `SET threads=1`.
- **G-ver:** `duckdb --version` is v1.1.3.
- **G-identity:** no nta / flush-behind / STREAMING fields on any arm.
- **G-cat-occ:** median CMT `cat01` < median CMT `wb`.
- Medians of ≥ 5 reps; teardown of all CLOS / mon groups on exit via
  `finally`. Existing JSONL is refused (A6.19).

## What this campaign cannot show

STREAMING itself. CAT naming probe vs hash table *inside* DuckDB (the
engine has one PID). nta/FB on a DuckDB probe. A named-application claim
for any other operator or engine. Anything about the 70-arm victim
campaign.

## Launch (after exclusivity on mos182; not in this pass)

```bash
# registered campaign — mos182 / c4 only, idle host, this prereg already on disk
experiments/asplos/run_duckdb_tenant_cat.sh \
  --out experiments/asplos/data/duckdb_tenant_cat.jsonl \
  --duckdb "$HOME/duckdb-1.1.3/duckdb"

# judge (after data exist)
python3 experiments/asplos/analyze_duckdb_tenant_cat.py \
  experiments/asplos/data/duckdb_tenant_cat.jsonl
```

Do not start the 15-wide frontier unless the host is exclusive/idle. A
`--smoke` SQL+JSON parse on any machine is not an arm.
