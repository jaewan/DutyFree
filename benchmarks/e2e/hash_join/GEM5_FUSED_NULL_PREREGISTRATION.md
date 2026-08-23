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
| hot set | 2.65 MiB, 53% of a 5 MiB LLC slice | `[F9.4]`
| L1D | 48 KiB, 12-way |
| L2 | 256 KiB, 8-way |
| LLC | 5 MiB, 20-way |
| memory latencies | DRAM 98 ns, CXL 203 ns |
| reps | 3 per arm |

Ratios:

| ratio | old geometry | T1 geometry | hardware reference |
|---|---:|---:|---:|
| L2/LLC | 40% | 5% | 0.625% |
| hot/L2 | 1.3x | 10.6x | about 85x | `[F9.4]`
| hot/LLC | 53% | 53% | 53% | `[F9.4]`

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
