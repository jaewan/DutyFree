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
| hot set | 2,778,726 bytes, 53% of a 5 MiB LLC |
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
| hot/L2 | 10.6x |
| hardware-reference hot/L2 | about 85x |
| hot/LLC | 53% |

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

