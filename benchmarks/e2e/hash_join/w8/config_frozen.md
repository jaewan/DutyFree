# W8 -- frozen configuration

Written 2026-08-24, before the first restore produced a number. Every hash here
was taken from the artifact that will actually be run, not from a build recipe.
A W8 row that cannot be matched to this table is not a W8 row.

## Simulator

| item | value |
|---|---|
| gem5 | 25.1.0.1, `build_Intel_8592/gem5.opt`, compiled 2026-08-24 01:24 |
| gem5 sha256 | `95912bc322c5d132c092c669e36af704c9e93e8e6a008299cc827a57a7239679` |
| gem5 source | submodule `gem5`, local branch `w8-streaming-counters`, `a02a1ac713` |
| base revision | `356e7b7d0e` (the revision every SE campaign used) |
| local delta | two stats only -- `streamingTranslations`, `tlb.streamingAccesses`. Patch committed at `w8/gem5_patches/0001-x86-streaming-counters.patch` because the submodule pointer is deliberately not moved to a commit that exists on one machine. |

The delta is stats-only: no timing path, no cache policy, no walker behaviour
is changed by it. It cannot move a cycle count.

## Guest kernel

| item | value |
|---|---|
| tree | submodule `linux`, `b9f60fafda72` ("Merge pull request #3 from jaewan/streaming-ranged-drain") |
| version | 6.8.0 |
| compiler | gcc-13.4.0 (the host default, 15.2, is newer than 6.8 accepts) |
| config | `x86_64_defconfig` + `w8/streaming_gem5.fragment`, then `olddefconfig` |
| `.config` sha256 | `f794692a32ede6d1...` |
| vmlinux sha256 | `fea3ef710f5f83c55213f7f2b0da973ed0a162565b9ac1c75e957f50cf6a49b2` |

Verified in the linked image, not just in the config: 53 `streaming` symbols in
`nm vmlinux`, including `streaming_apply_cache_bits`, `streaming_validate_entry`,
`streaming_drain_range`, the KUnit cases, and the debugfs `pte_query` entry.

`CONFIG_PAT_STREAMING=y`, `CONFIG_X86_PAT=y`,
`CONFIG_PAT_STREAMING_KUNIT_TEST=y` -- all three checked after `olddefconfig`
and before a minute was spent compiling, because `default n` plus an unmet
dependency drops a symbol silently and that is the highest-probability way this
task produces a confidently-wrong null.

## Guest image

| item | value |
|---|---|
| path | `~/.cache/gem5/w8-busybox-streaming-r1.img` |
| sha256 | `e33255ee01473c5274c3aa82c0eb51075cbe295021d568c2c3b2f00ee3a89c97` |
| size | 257 MiB; MBR, one 0x83 partition at 1 MiB, ext2, label `w8root` |
| built by | `w8/build_rootfs_t4.sh`, unprivileged (`mke2fs -d` under `fakeroot`) |
| userland | busybox 1.37.0 (Ubuntu 1:1.37.0-7ubuntu1), static |
| `/sbin/m5` | `w8/guest/m5mini.c` + `m5ops.S`, static, sha256 `f5bab85522f79d04...` |
| `/root/cxl_join_bench.gem5fs` | sha256 `270df6dd72abb24ef13a7fe62647af57ab1b23a0f4cdaf738770138cc94c7a06` |

**RECONSTRUCTED, NOT RECOVERED.** This is not
`x86-ubuntu-18.04-img-hashjoin-v2`. That image is absent from all three hosts
(`~/.cache/gem5` did not exist here), and its binary carried a `--line-stride`
option that no revision in this repository contains -- so it was built from a
source tree that is gone. The reconstruction is a different userland
(busybox, not Ubuntu 18.04), has no `--line-stride`, and **cannot reproduce a
v2-image row**. The image says so about itself in `/etc/W8-PROVENANCE`.

## Machine

Boot: `AtomicSimpleCPU`, 2 CPUs, `--caches`, mem 256 GiB, CXL 128 GiB,
cmdline `earlyprintk=ttyS0 console=ttyS0 lpj=7999923 root=/dev/sda1`. The
cmdline is the committed one, unchanged -- which is why the image was given a
real partition table rather than being handed a new `root=`.

Restore: `fs_restore_chi_8592.sh` -- O3 @ 1.9 GHz, Ruby/CHI `CHI_config_8592.py`,
L1d 48 KiB/12, L1i 32 KiB/8, L2 2 MiB/16, L3 5 MiB/20, `num-l3caches = num-cpus`,
SimpleMemory, DRAM 97 ns / CXL 198 ns. Identical to the SE 8592 reference by
construction; **this does not make FS and SE numbers comparable.** The FS arms
carry a guest kernel, a page cache, and a boot's worth of resident state that
the SE arms do not. Nothing in W8 compares across the two.

## Workload arms

`w8/rcs/w8_{wb,stream_m5op,stream_mprot}.rcS`, each:
`--mode morsel --fact-bytes 16777216 --hot-bytes 4194304 --reps 1 --warmups 0
--probe-batch 0 --json`, differing only in `--policy` and `--declare`.

`reps 1 --warmups 0` differs from the SE cells (`reps 3 --warmups 1`) and is
deliberate: a cold single pass is the honest case for a gate that asks whether
the walker ever classifies at all. It is also the reason no timing from these
arms may be reported.
