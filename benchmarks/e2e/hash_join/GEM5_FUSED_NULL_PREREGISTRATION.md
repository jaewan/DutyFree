# Pre-registration: gem5 fused-null geometry discriminator

Dated 2026-08-10. Written before any new fused-null gem5 run in this
session. This is an H2-only audit; no H3 claims or paper repo files are in
scope.

## Objective

Determine whether gem5's null STREAMING/H2 result on the fused morsel hash
join is caused by the scaled model preserving hot/LLC while collapsing
hot/private-L2. The prior null is interpreted as "there is no tax to
remove," not as "H2 fails": quiescent 79.97 cycles/access versus loaded
WB 80.10, with H2 LLC fills reduced but no measurable WB tax.

## T1 Geometry

Cheap discriminator geometry:

| knob | value |
|---|---|
| CPU model | O3CPU, SE Ruby/CHI |
| threads | 1 fused worker, plus one extra CPU for SE harness symmetry |
| fact stream | 16 MiB CXL-mode fact region |
| hot set | 2.65 MiB, 53% of a 5 MiB LLC slice |
| L1D | 48 KiB, 12-way |
| L2 | 256 KiB, 8-way |
| LLC | 5 MiB, 20-way |
| memory latencies | DRAM 98 ns, CXL 203 ns |
| reps | 3 per arm |

Ratios:

| ratio | old geometry | T1 geometry | hardware reference |
|---|---:|---:|---:|
| L2/LLC | 40% | 5% | 0.625% |
| hot/L2 | 1.3x | 10.6x | about 85x |
| hot/LLC | 53% | 53% | 53% |

Arms:

| arm | command-level mode/policy | meaning |
|---|---|---|
| quiescent | `probe-workload`, `wb` | hot-table baseline, no fact stream |
| WB loaded | `morsel`, `wb` | fused stream+probe with allocating fact fills |
| H2 loaded | `morsel`, `stream` | same, with gem5 STREAMING tagging of fact region |

## Prediction

If the hot/L2 collapse explains the prior null, reducing L2 to 256 KiB
should open a measurable quiescent-to-WB gap from the prior 0.2% level.
H2 should recover some of the opened gap by reducing LLC insertion/fill
pressure, but full recovery is not required and would be suspicious for
the fused hardware analogy because real-hardware decomposition assigns at
most 31% of the 1.47x fused tax to shared-LLC effects.

Decision rule:

| outcome | meaning |
|---|---|
| WB tax opens measurably at hot/L2 ~= 10x | L2-residency hypothesis confirmed; proceed to a calibrated 40 MiB LLC / 256 KiB L2 geometry if runtime is acceptable |
| WB tax remains approximately zero | L2-residency hypothesis refuted; next suspect is insufficient fused stream fill rate |
| WB tax opens but calibrated 40 MiB geometry is too expensive | Report hypothesis confirmed but not economically fixable; paper keeps hardware authority with a mechanism for the gem5 null |

Every loaded arm must be reported against its own quiescent baseline from
the same geometry.
