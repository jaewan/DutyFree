# Pre-registration: gem5 FS OS-to-hardware Streaming contract

Dated 2026-08-23, before any new measured gem5 run in this session.

## Objective

Test the OS-declared, page-granular STREAMING contract in gem5 FS mode:
the guest kernel must encode `PROT_STREAMING` as PAT slot 6 in ordinary page
tables, the x86 page-table walker must classify the translated pages as
streaming, and CHI must apply H2 (no LLC fill) and, when enabled, H3 (no
snoop-filter enrolment). This is a capability demonstration, not a new
quantitative calibration claim: the frozen FS cache ratio is known not to
support one.

## Frozen apparatus and ordering

| item | value |
|---|---|
| gem5 source | `356e7b7d0e` detached HEAD |
| gem5 build variant | `Intel_8592`: Ruby/CHI, `NUMBER_BITS_PER_SET=256`, x86 ISA |
| guest kernel source | `b9f60fafda72` detached HEAD, with `CONFIG_PAT_STREAMING=y` |
| FS checkpoint boot | 2 AtomicSimpleCPUs via `scripts/fs_boot_checkpoint.sh 2` |
| restore cache geometry | L2 = 2 MiB; LLC = 5 MiB (L2:LLC = 40%) |
| workload | installed static `cxl_join_bench.gem5fs`, one fixed geometry and 2 CPUs |
| arms | quiescent, WB (no declaration), H2 (declaration/H3 off), H2+H3 (declaration/H3 on) |

The fact region is populated while writable, then declared with
`mprotect(PROT_READ | PROT_STREAMING)`, then only read. Any `mprotect` failure
aborts the workload. No SE geometry changes beyond the designated 4-CPU
reference sweep are authorized.

## Falsifiable predictions and decision rules

| task | prediction | result interpretation |
|---|---|---|
| T1 build | the resolved SCons config retains CHI, 256 set bits, x86, and the emitted controller exposes `enable_H3_streaming_bypass` | otherwise no later result is valid |
| T2 SE sweep | WB (`with_agg`) taxes the larger WSS points versus its own `alone` baseline; m5op H2 (`with_streaming`) reduces LLC fills and recovers visible tax | no tax anywhere is the known fused-null geometry outcome; stop rather than tune |
| T3 kernel | `PAT_STREAMING=y`, streaming symbols exist, and KUnit support is compiled | otherwise do not boot this kernel for the contract test |
| T4 image | an appropriately named image boots and `cxl_join_bench.gem5fs --help` runs | image unavailable/reconstruction exceeds one session: stop at acceptance branch 3 |
| T5 FS | walker streaming count is non-zero for H2/H2+H3 and zero for WB; H2 lowers LLC fills versus WB; H2+H3 lowers snoop-filter back-invalidations versus H2 | non-zero/zero walker split closes the loop even if benefit is unquantifiable; PTE bits present but walker count zero refutes the integration |

Every loaded arm will have a quiescent baseline from the same configuration.
The run will be stopped and documented if a single simulation reaches 90
minutes with a zero-byte `stats.txt`.
