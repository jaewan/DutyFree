# D1/D2: two silent-wrong-number defects in `tmp_dutyfree_exp`

`d1d2_pmu_and_l2size.patch` applies to `github.com/jaewan/tmp_dutyfree_exp`
(HEAD `481115c`) and fixes two defects found on 2026-08-23.

**D1 — the victim reported Intel L2 hit/miss from AMD event codes.**
`common.h` defined `RAW_L2_HIT`/`RAW_L2_MISS` as `0x7064`/`0x0864`
(`ls_dc_accesses` family, AMD) with no vendor conditional.
`perf_event_open()` accepts an arbitrary `PERF_TYPE_RAW` config without
erroring, so on the Intel hosts these programmed events that do not exist.
**Corrected 2026-08-23 (W4.4):** they return *identically zero*, not
"near-zero" — measured on both Intel parts, and cross-checked with `perf stat
-e r7064,r0864`. Every Intel L2 figure this binary prints is void, but the
audit found that **no published number was ever printed by it**: the campaign
binary was a third, uncommitted source state that already had the Intel codes.
See `W4.4_AUDIT_2026-08-23.md` — the live defect is apparatus provenance, not
wrong numbers. Fixed with a `PMU_INTEL`/`PMU_AMD`
conditional (Intel: `MEM_LOAD_RETIRED.L2_HIT` `0x02D1`,
`MEM_LOAD_RETIRED.L2_MISS` `0x10D1`), an `#error` when neither is defined, and
Makefile autodetection from `/proc/cpuinfo`.

Caveat carried in the source: the Intel codes count *retired load
instructions*, so they exclude prefetches and stores. That is the right
semantics for the pointer chase and the wrong semantics for a STREAM triad.

**D2 — `VICTIM_ARRAY_KB` defaulted to 1 MiB on every host** regardless of the
actual L2, including the 2 MiB Intel parts. Fixed by removing the default
(`#error`) and having the Makefile read
`/sys/devices/system/cpu/cpu0/cache/index2/size`.

**D2 never bit any published run** (W4.4): `victim.c:99` lets `-w` override
`DEFAULT_WS_KB`, and every runner passes `-w` explicitly (`run_probe.py:128`,
`run_probe_moscxl.py:131`, `run_sfpressure.py:50`).

Both defects are now self-reporting rather than silent: the victim prints
`pmu=` and `l2_compiled=`, and emits `l2_counters=SUSPECT` with a loud warning
if the L2 counters total under 1000 events over the measured window. The probe
runners treat `l2_counters != ok` as an invalid arm.

## Verification

Not by trusting the constant — by sweeping the working set past L2 and
checking for a capacity curve a wrong event code cannot produce.

mos182 (SPR, 2 MiB L2): 0.00% miss at 128-1024 KB, 4.27% at 1536, 30.17% at
2048, 99.29% at 4096, 100% at 32768.
moscxl (Bergamo, 1 MiB L2): 0.02% at 256 KB, 3.03% at 512, 11.99% at 768,
33.75% at 1024, 73.37% at 2048, 92.44% at 8192, 99.38% at 65536.
mos181 (EMR, 2 MiB L2): 0.00% at 128-1024 KB, 11.35% at 1536, 26.72% at 2048,
99.42% at 4096, 100% at 32768.

## Deployment status (2026-08-23)

- **mos182** — applied and rebuilt (`PMU_INTEL`, `L2_SIZE_BYTES=2097152`).
- **moscxl** — applied and rebuilt (`PMU_AMD`, `L2_SIZE_BYTES=1048576`).
  D1 and D2 are both no-ops numerically there (AMD codes were the correct
  ones; L2 really is 1 MiB), but the rebuild is required for the new
  `cyc_per_access` / `l2_counters` fields the probe runners depend on.
- **mos181 — applied and rebuilt 2026-08-23** (`PMU_INTEL`,
  `L2_SIZE_BYTES=2097152`), once the `ld_*` sims had finished. Pre-fix `bin/`
  kept at `bin.bak.pre_d1d2_20260823`. Verified by sweep (see below). mos181
  never published an L2 number: its only `victim` run is
  `rocksdb/scripts/run_ptr_cat_ceiling.py`, which records `ipc` only.

Extract with `git diff -- src/common.h src/victim.c Makefile`, but note that a
raw diff of those hosts also carries unrelated pre-existing local work (e.g.
`alloc_wb_node` in `common.h`); this patch has that hunk stripped out.
