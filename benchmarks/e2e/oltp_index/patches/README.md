# D1/D2: two silent-wrong-number defects in `tmp_dutyfree_exp`

`d1d2_pmu_and_l2size.patch` applies to `github.com/jaewan/tmp_dutyfree_exp`
(HEAD `481115c`) and fixes two defects found on 2026-08-23.

**D1 — the victim reported Intel L2 hit/miss from AMD event codes.**
`common.h` defined `RAW_L2_HIT`/`RAW_L2_MISS` as `0x7064`/`0x0864`
(`ls_dc_accesses` family, AMD) with no vendor conditional.
`perf_event_open()` accepts an arbitrary `PERF_TYPE_RAW` config without
erroring, so on the Intel hosts these programmed events that do not exist and
returned near-zero counts. **Every Intel L2 hit/miss and `l2_miss_rate` figure
this binary has ever printed is void.** Fixed with a `PMU_INTEL`/`PMU_AMD`
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

## Deployment status (2026-08-23)

- **mos182** — applied and rebuilt (`PMU_INTEL`, `L2_SIZE_BYTES=2097152`).
- **moscxl** — applied and rebuilt (`PMU_AMD`, `L2_SIZE_BYTES=1048576`).
  D1 and D2 are both no-ops numerically there (AMD codes were the correct
  ones; L2 really is 1 MiB), but the rebuild is required for the new
  `cyc_per_access` / `l2_counters` fields the probe runners depend on.
- **mos181 — NOT applied.** It was running twelve gem5 simulations under tmux
  (`ld_*`) and was left alone. Its Intel L2 numbers remain void until it is
  patched and rebuilt.

Extract with `git diff -- src/common.h src/victim.c Makefile`, but note that a
raw diff of those hosts also carries unrelated pre-existing local work (e.g.
`alloc_wb_node` in `common.h`); this patch has that hunk stripped out.
