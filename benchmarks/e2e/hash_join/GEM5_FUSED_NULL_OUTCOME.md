# Outcome: gem5 fused-null T1 discriminator

Dated 2026-08-10. Scope: H2 only. No H3 files, paper repo files, or
`cxl_join_bench.cpp` were changed.

## Summary

T1 was attempted as preregistered, but did not produce usable cycle/access or
cache-fill numbers. The intended cheap discriminator was not cheap on the
available gem5 setup: after 1:11:28 wall time all three arms were still running
at 99.9% CPU, and all three `stats.txt` files were still zero bytes. The tmux
sessions were stopped and the launch logs/config artifacts were preserved.

Therefore none of the three acceptance branches is established yet:

| branch | status |
|---|---|
| 1. Hypothesis confirmed and fixed | not established; no T1 metrics |
| 2. Hypothesis confirmed, not economically fixable | not established; T1 itself did not finish |
| 3. Hypothesis refuted | not established; no T1 metrics |

The concrete result is a blocked/uneconomic T1 attempt, not a scientific
verdict about the hot/private-L2 hypothesis.

## Preregistered T1 Geometry

| knob | value |
|---|---|
| CPU model | O3CPU, SE Ruby/CHI |
| fact stream | 16 MiB CXL-mode fact region |
| hot set | 2,778,726 bytes, 53% of a 5 MiB LLC | `[F9.4]`
| workers | 1 fused worker, `--cpu-list 0`, plus `--num-cpus=2` |
| L1D | 48 KiB, 12-way |
| L2 | 256 KiB, 8-way |
| LLC | 5 MiB, 20-way |
| memory latencies | DRAM 98 ns, CXL 203 ns |
| reps | 1 warmup, 3 measured reps per arm |

Ratios disclosed by the updated handoff contract:

| ratio | value |
|---|---:|
| L2/LLC | 5% |
| hot/L2 | 10.6x | `[F9.4]`
| hardware-reference hot/L2 | about 85x |
| hot/LLC | 53% | `[F9.4]`

## Arms Launched

| arm | workload options | status |
|---|---|---|
| quiescent | `--mode probe-workload --policy wb` | stopped after 1:11:28, no final stats |
| WB loaded | `--mode morsel --policy wb --morsel 1m --check` | stopped after 1:11:28, no final stats |
| H2 loaded | `--mode morsel --policy stream --morsel 1m --check` | stopped after 1:11:28, no final stats |

All three runs reached `**** REAL SIMULATION ****` and remained CPU-bound, but
none reached workload completion or emitted final gem5 statistics.

## Preserved Artifacts

| artifact | path |
|---|---|
| preregistration | `benchmarks/e2e/hash_join/GEM5_FUSED_NULL_PREREGISTRATION.md` |
| frozen config | `results/gem5/hash_join_fused_null/config_frozen.md` |
| launcher | `benchmarks/e2e/hash_join/scripts/run_gem5_fused_null.py` |
| launch manifest | `results/gem5/hash_join_fused_null/t1_launch_manifest.json` |
| launch logs | `results/gem5/hash_join_fused_null/t1_{q,wb,h2}.launch.log` |
| generated run scripts | `results/gem5/hash_join_fused_null/t1_{q,wb,h2}.sh` |
| zero-byte final stats | `results/gem5/hash_join_fused_null/stats/t1_{q,wb,h2}/stats.txt` |

## Next Step

Do not report a loaded WB or H2 number without a same-geometry quiescent
baseline. The next defensible step is either:

1. run the same T1 triple on a faster gem5 host with enough wall-clock budget to
   complete all three arms; or
2. preregister a smaller smoke discriminator with fewer iterations/reps as an
   exploratory fill-rate/runtime diagnostic, explicitly separate from the
   branch-acceptance T1 result.


---

# Correction F9.4 --- appended 2026-08-23, geometry only

Found by the W4.3 provenance ledger, not by re-running anything. The rows
tagged `[F9.4]` above state the hot table's **requested** size. They do not
state its **resident** size, and the two differ here.

`scripts/run_gem5_fused_null.py:40` computes `5 * 1024 * 1024 * 53 // 100` =
2,778,726 B, intending 53% of the 5 MiB modelled LLC. But
`src/cxl_join_bench.cpp:369` `table_capacity` rounds the entry count up to a
power of two --- 173,670 -> 2^18 = 262,144 --- and `build_table` instantiates
every entry. The table T1 actually built was therefore:

| quantity | as documented (requested) | as instantiated (resident) |
|---|---:|---:|
| hot table | 2.65 MiB | **4 MiB** |
| hot/LLC | 53% | **80.0%** |
| hot/L2 | 10.6x | **16.0x** |

**Nothing measured changes, because nothing was measured.** T1 was stopped
after 1:11:28 with zero-byte `stats.txt` for all three arms. The error is
confined to these two documents describing a campaign that did not finish.

**The discriminator's design is affected, though, and a re-run must confront
it.** T1's whole purpose was to place the hot set far above the private L2
while holding hot/LLC fixed at 53% so that the LLC ratio was not a confound.
The instantiated geometry does not hold it fixed: it moves hot/LLC from 53% to
80% at the same time. And 53% of 5 MiB is **unreachable** by this kernel --- the
achievable neighbours are 2 MiB (40%) and 4 MiB (80%). A re-run must either
pick an achievable ratio and re-derive the comparison, or change the LLC size
so that 53% lands on a power of two.

**Not re-derived here:** the `old geometry` column of the prereg's ratio table
(L2/LLC 40%, hot/L2 1.3x). Its `hot_bytes` was not recovered, so whether it is
subject to the same rounding is unknown. It is not asserted either way.

Scope: this correction is confined to T1. It does **not** apply to the task #22
gem5 fused null (`GATE1_FUSED_NULL_OUTCOME.md`), which ran the source default
`hot_bytes = 2 << 20` = exactly 2 MiB = 2^17 entries --- a power of two, which
`table_capacity` returns unchanged. See F9.5 in
`experiments/asplos/W4.3_PROVENANCE_LEDGER_2026-08-23.md`.
