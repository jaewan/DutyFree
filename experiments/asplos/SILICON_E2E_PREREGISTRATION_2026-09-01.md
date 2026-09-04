# Pre-registration: application-level e2e on silicon

Date: 2026-09-01, before any measurement.

## Why this campaign exists

Every STREAMING result so far reports *architectural* metrics -- tenant IPC and
victim cycles-per-load.  No application quantity is measured, no unit of work
completes, and the gem5 tenant is truncated by design.  That is the one gap left
after the 66-run wedge campaign, and it cannot be closed in gem5: a complete
join is 40.8M cycles per pass, so a real engine with a co-tenant is 1-2e9 cycles
= 12-25 h per run, times arms times seeds.

The resolution is to split by what each platform can actually do:

- **Silicon** measures every mechanism that *exists* -- WB, CAT, flush-behind,
  `prefetchnta` -- at native speed, at realistic scale, in application units.
- **The model** supplies STREAMING alone, bridged by the calibration argument
  (the model predicts CAT at 15.8-24.2% against silicon's 16.7%).

STREAMING is **not measurable here** and no attempt is made to fake it.  This
campaign's contribution is an application-level number for the off-the-shelf
alternatives, which is exactly what a reviewer asks for when told "CAT can
already do this".

## Apparatus

- **Host: mos182 (`c4`)**, Xeon Platinum 8462Y+, 2 sockets x 32 cores x 2 SMT,
  L3 **120 MiB across 2 instances (60 MiB/socket)**, resctrl with **15 CLOS** and
  a **15-way** capacity mask (`cbm_mask=7fff`).  Chosen because it is idle
  (load 0.00); mos181 is running 17 gem5 processes and measuring silicon there
  would repeat a mistake this project already made.
- Pinned to **socket 0** (`node0` = cores 0-31, 64-95) to avoid crossing the two
  L3 instances.  Tenant and victim on distinct physical cores, same socket.
- Reused, not rebuilt: `benchmarks/bench/victim/pointer_chase` (victim),
  `benchmarks/e2e/hash_join/scripts/resctrl_clos.sh` (CLOS setup/teardown),
  `experiments/lib/dutyfree/resctrl.py` (schemata / occupancy helpers).
- **c4's checkout is stale** (native binary dated 2026-08-28, sha `01f80921`, vs
  mos181's `198fb858`) and the filesystem is **not** shared (`/dev/sda2` local).
  The binary must be rebuilt on c4 and its sha recorded per arm.

## Workload

- **Tenant**: `cxl_join_bench --mode single` -- the same real hash join the wedge
  campaign used (hash64, linear probing, payload gather), now run **to
  completion** at native speed so it reports `join_mtuples_per_s`, an
  application metric rather than IPC.
- **Sizing** (to be confirmed by a calibration run, not assumed):
  fact **8 GiB** (>> the 60 MiB LLC, so a true stream with no realizable reuse);
  hash table **32 MiB** -- above the 2 MiB private L2 so it must live in the LLC,
  and ~53% of it so its residency actually matters.  Table sizes are quantized
  to a power of two times 16 B; 32 MiB = 2^21 entries is exact.
- **Victim**: `pointer_chase` on a separate core of the same socket, reporting
  cycles per dependent load.

## Arms

| arm | mechanism | how |
| --- | --- | --- |
| `wb` | none (baseline) | no CLOS |
| `cat01`..`cat15` | CAT capacity mask | tenant confined to w of 15 ways |
| `fb<D>` | flush-behind | `--flush-distance D`, swept |
| `nta` | non-temporal hint | `--policy nta` (`prefetchnta`) |

A **full CAT frontier**, not two points.  The wedge campaign showed protection
is *non-monotone* in mask width -- it peaked at 8 of 20 ways and fell at
narrower masks because way-starvation raises the tenant's miss traffic more than
its occupancy costs.  Two points cannot see that, and the project's earlier
belief that "CAT works, it just costs 16.7%" came from sampling exactly two
points inside the starvation region.

## Registered predictions

- **S1.** `wb` degrades the victim by >= 1.30x over quiet.  If the join does not
  pollute at this scale there is nothing to protect and the campaign is void.
- **S2.** The CAT protection curve is **non-monotone** in mask width, peaking at
  an intermediate width, reproducing on silicon what the model showed.  Refuted
  if protection rises monotonically as the mask narrows.
- **S3.** `prefetchnta` does not avoid LLC allocation: the `nta` arm protects the
  victim by <= 10% of what the best CAT width achieves.  This replicates the
  Zen 4c finding on an Intel part.
- **S4.** At its best protection setting, CAT costs the tenant >= 10% of its
  `join_mtuples_per_s` relative to `wb`.  This is the number the paper needs in
  application units.
- **S5.** Flush-behind's best setting costs the tenant >= 10% of tuples/s.

## Admission gates

- **G-idle**: verify `load1 < 0.5` and zero foreign gem5/bench processes
  immediately **before each arm**, not once at campaign start.  A diagnostic run
  on a busy machine already produced chaotic values once in this project.
- **G-mask**: read `schemata` back from resctrl and compare **as integers**, never
  as strings -- string comparison produced a false alarm on 24 of 36 cells once.
- **G-clos**: confirm the tenant's CPU is in the intended CLOS.  A CPU in a
  CTRL_MON group silently takes that group's RMID; a first attempt at
  CAT-occupancy measurement read 0.0 KB for every masked arm because of this and
  would have supported a dramatic wrong conclusion.
- **G-live**: the tenant must report a nonzero `join_mtuples_per_s` and a
  checksum matching the `wb` arm.  Identical offered work, verified.
- **G-size**: the guest's own `HOT_TABLE_ROUNDED` line must be **absent**, and the
  realized fact size echoed back, so no requested size is reported as a fact.
- Medians of >= 5 reps per arm, with teardown of all CLOS on exit via `trap`.

## Operational pinning (2026-09-01, still before measurement)

A staged runner on c4 (`/tmp/domin_silicon_e2e/sil_e2e.sh`) produced two
calibration records that are **apparatus, not results**: `cat04` wrote
`mask_got=-1` (wrong resctrl group name), and the tenant was launched with
`taskset -c 4` against the binary's default `--cpu-list 0`.  `pin_cpu` either
exits or migrates off the CLOS CPU.  Those records must not be cited.  The
committed runner (`experiments/asplos/silicon_e2e/run_hashjoin.py`) is pinned
as follows.

- **CPUs.** Tenant 4, victim 6.  Both package 0, L3 id 0, distinct physical
  cores, not SMT siblings.  `--cpu-list` equals the tenant CPU.  G-clos reads
  that CPU back from the tenant JSON `thread_mapping`.
- **Placement.** `--fact-node 0 --hot-node 0`.  Node 2 on this host is the
  cpuless 256 GiB node and is not used.
- **Hit rate.** `--hit-rate 1.0` so the 32 MiB table is a stable working set.
  M3 found that 0.5 miss-scatter independently saturates the victim and masks
  the stream.
- **Pages.** `--huge2m` for the fact stream **once node 0's pool can back 8 GiB**.
  As-found, node 0 had 1024 × 2 MiB pages (2 GiB) and node 2 (cpuless) had
  35488; an 8 GiB `MAP_HUGETLB` SIGBUS'd (signal 7).  On 2026-09-01 the user
  authorized passwordless sudo to grow the pool.  `setup_hugepages_node0.sh`
  sets node 0 to **8192** pages (16 GiB) and leaves node 2 untouched.  The
  registered 8 GiB campaign is `--huge2m` against that pool.  A 4K-page
  campaign that was already in flight when the pool was grown is a page-size
  sensitivity, stored separately, not mixed into the hugepage JSONL (A6.19).
  Victim `pointer_chase` hugepage-allocates its 32 MiB WSS.  The hash table
  remains a `std::vector`.
- **CAT.** `resctrl_clos.sh setup_b`: tenant CPU only in `clos_b`, victim left
  in the root CLOS with the full 15-way mask.  This is "confine the polluter",
  the question whose answer was non-monotone in the model.  Complementary
  `setup_c` makes `cat15` inexpressible (victim would have zero ways) and
  answers a different question.  `cat15` under `setup_b` is the control that
  should match `wb`.
- **Window.** Victim starts at `JOIN_MEASURE_BEGIN` (after fill and warmup)
  and is stopped at `JOIN_MEASURE_END`.  The staged runner started the victim
  2 s before the tenant, so the median mixed quiet, fill, join, and tail.
  Calibration v3 (`256 MiB` fact, `--reps 1`) produced `victim_cyc_per_load:
  null` on every co-run: the join lasted 0.40 s and `pointer_chase` was
  SIGTERM'd before finishing its first 1 s trial (stdout 0 bytes).  That is
  an apparatus miss, not a result.  The committed runner uses `--inner-reps 12`
  on calibration (join ~5 s) and `--inner-reps 1` at 8 GiB (join ~13 s at the
  observed 42 Mtuples/s), and refuses `status=ok` when `victim_n_trials < 1`.
- **nta.** `--policy nta --pf-distance 32`.  An `nta` record with
  `pf_distance=0` is not an nta arm.
- **flush-behind.** D ∈ {65536, 262144, 1048576} (`fb64k`, `fb256k`, `fb1m`).
  `--mode single` dispatches to `join_range_flushbehind` when D>0.  The JSON
  field `join_path` must read `flushbehind` or the arm is not an arm.
- **wc.** Not run.  A read-only fact table cannot be write-combining without a
  PAT slot this host does not give to user pages.
- **G-idle load ceiling.** The written threshold was `load1 < 0.5`.  On this
  128-core host a single-core tenant leaves `load1` around 1 for the decay
  window of loadavg, so 0.5 is unreachable in the inter-arm gap and would skip
  every arm after the first on an idle machine.  The operational gate is
  **foreign gem5/bench `comm` names = 0** and `load1 < 8`.  Relaxing the load
  number cannot favour the hypothesis: it only prevents a self-false-busy.
  mos181 at the time of writing was load 16.97 with gem5 processes; that still
  fails both clauses.

Workload-family choice: `SILICON_E2E_WORKLOAD_CHOICE_2026-09-01.md`.  Hash join
only; LSM is the planned second family and is not run until this one has an
outcome.

## What this campaign cannot show

STREAMING itself.  Any figure combining these silicon numbers with a modelled
STREAMING point must label which platform each came from, and must not present
the combination as a single measured comparison.

## Amendment 1 — 2026-09-01, after the registered campaign

Written after seeing the hugepage JSONL.  Analyzer constants `S2_TESTABLE` and
the F-fb/F-nta printer changed in the same commit.  Each clause states whether
it could favour STREAMING.

**S2 restated as untestable, not refuted.**  The registered prediction assumed
15-way CAT on a 60 MiB LLC could express the model's way-starvation regime
(1–6 of 20 HNF ways at 0.25 MiB/way = 0.25–1.5 MiB, peaking at 8/20 = 2.0 MiB).
It cannot: silicon's tightest mask is 60/15 = **4.0 MiB**, 16× the model's
floor and 2× its peak.  Bergamo (16 MiB / 16 ways = 1.0 MiB/way) is still 4×
the floor.  Testing S2 needs a slice CAT cannot express.  The monotone R(w) we
measured is what the model also predicts in the capacity range CAT can grant.
Action: the analyzer emits `UNTESTABLE` for S2; `cat_nonmonotone` remains as a
shape diagnostic only.  Could this favour STREAMING?  No.  It stops counting
S2 as a silicon refutation of the *model*.  It does not confirm S2, and it
does not move any STREAMING number.

**Finding F-fb, promoted after S5.**  At matched median protection, fb256k
(R=44.5%, tenant cost 6.31%) versus cat06 (R=44.1%, 25.18%) — 4.0× cheaper.
nta (R=15.3%, cost −2.95%) versus cat09 (R=18.2%, 13.59%) dominates outright.
STREAMING's silicon bar is no longer "beat CAT's 42%."  It is beat 6.3% at
44% protection, and beat free at 15%.  Could this favour STREAMING?  **No —
it raises the bar the paper has to clear.**  STREAMING itself is still not
measured here; whether it beats flush-behind is an open question the paper
must answer, not a footnote.

**G-mask-after.**  The runner now re-reads `clos_b` schemata and `cpus_list`
after the measurement, before teardown, and fails the arm if the mask
dropped.  Closes the setup-then-measure TOCTOU (a foreign process did delete
CLOS groups during this campaign's window; the pre-rep check not seeing it
was luck).  Legacy JSONL without `mask_got_after` is not a gate failure.
Could this favour STREAMING?  No.

