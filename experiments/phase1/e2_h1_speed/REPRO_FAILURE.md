# E2a REPRO_FAILURE — single-core WB CXL bandwidth far below paper's 15.8 GB/s

Dated 2026-08-06. Per ground rule #7: stopping this experiment rather than
proceeding to new arms (E2b flush-behind, E3 sweeps) on top of a baseline
that doesn't match.

## What was measured

Single core (cpu1), WB, CXL node2, 16 GiB region, MSR 0x1A4 = 0x0 (all
prefetchers on, verified by rdmsr before each run), governor=performance,
turbo=off (verified via `turbostat` mid-run: 1892 MHz, 100% busy), n=2
(smoke, before scaling to n=12):

| kernel | node | median bw |
|---|---|---:|
| `stream_wb.c` (scalar, 1x 8B load/64B line, existing harness) | CXL (node2) | 8.86-8.90 GB/s |
| `mlp_probe.c` (AVX2, 4 registers/128B, written for this diagnostic) | CXL (node2) | 8.06-8.86 GB/s (single run 8.06) |
| `stream_wb.c` (scalar) | local DRAM (node0) | 14.21 GB/s |
| `mlp_probe.c` (AVX2) | local DRAM (node0) | 14.23 GB/s |

Paper's claim (`Sec2_DirectoryTax.tex:50-53`): single core reaches **15.8
GB/s** under WB (CXL). **Measured: 8.86-8.90 GB/s -- 44% below, far outside
the 15% gate.**

## What was ruled out

1. **CPU frequency/governor**: verified via `turbostat` *during* the run --
   cpu1 at 1892 MHz (full non-turbo base), 100% busy, `no_turbo=1`,
   `governor=performance`. Not a P-state issue (an idle-time
   `scaling_cur_freq` read of 800 MHz before this check was a red herring --
   that's intel_pstate/HWP letting an idle core clock down between runs, not
   its behavior under load).
2. **Software MLP/kernel choice**: `stream_wb.c`'s single-scalar-load loop
   and a purpose-built 4-register AVX2 unrolled kernel (`mlp_probe.c`, more
   outstanding loads per iteration) give the **same** ~8-9 GB/s on CXL. If
   the ceiling were an artifact of insufficient software-side memory-level
   parallelism, the wider kernel should have shown meaningfully higher
   bandwidth. It didn't.
3. **Measurement methodology**: the identical two kernels reach **14.2 GB/s**
   on local DRAM (node0) -- consistent with each other and with a
   sane single-core DDR bandwidth figure. The tools are not the problem;
   the CXL path specifically underperforms relative to local DRAM by ~1.6x,
   and relative to the paper's CXL figure by ~1.8x.

## Leading hypothesis, not yet confirmed

The CXL device in this host's slot 27:00.0 was physically swapped after the
paper's Intel data was collected: paper claims a Micron CXL 2.0 Device 6400;
live `lspci` now shows a Montage Technology M88MX5891 (Samsung-branded) --
see `../e4_hygiene/PLATFORMS.md`. That same PLATFORMS.md also notes this
device's PCIe link is currently negotiated at **x8, downgraded from its x16
capability**. Both facts point the same direction: **the currently-installed
CXL device/link most likely delivers materially lower single-stream
bandwidth than whatever hardware produced the paper's 15.8 GB/s figure.**
This is plausible but not proven here -- no measurement in this campaign
directly attributes the gap to device model vs. link width vs. some other
factor (e.g. a firmware/BIOS interleave setting); ground rule says not to
average away disagreement, so this is reported as a leading hypothesis, not
a conclusion.

## What this means for P2/P3 and the rest of E2/E3

- **P2** ("bounding LLC footprint keeps bandwidth within ~15% of unbounded
  WB") and **P3** (flush-behind recovery) can still be tested **relative to
  whatever this device's unbounded-WB ceiling actually is** (~8.9 GB/s) --
  the flush-behind sweep (E2b) and the calibration sweeps (E3) do not
  strictly require matching the paper's absolute 15.8 GB/s, only a
  self-consistent baseline on the hardware in hand. That is a defensible
  path forward, but it is a scope change from "reproduce the paper's
  number" to "characterize the currently-installed hardware," and should be
  called out as such in `PHASE1_FINDINGS.md`, not silently substituted.
- The prefetcher-bit sweep itself (all 6 configs clustering at 8.7-9.0 GB/s
  with almost no spread) is **also** an anomaly independent of the absolute-
  ceiling question: if HW prefetchers were doing substantial work on this
  access pattern, disabling them should have shown a much larger effect than
  the ~3% spread observed. This raises the possibility that on this specific
  device/link, single-core CXL bandwidth here is bound by something other
  than L2/DCU HW prefetch reach (e.g. core-side outstanding-request count
  against this device's response latency, or a device/link-side queue depth
  limit) -- worth keeping in mind when interpreting any future flush-behind
  or SW-prefetch-distance sweep on this same device.

## Recommendation

Do not run the full n=12 MSR sweep or proceed to E2b/E3 on the assumption
that ~15.8 GB/s is the achievable ceiling here. Awaiting direction on
whether to (a) proceed treating ~8.9 GB/s as this device's real ceiling and
characterize relative effects only, (b) investigate the device/link
question further first (e.g. checking BIOS CXL interleave/link settings,
comparing against SPR's device), or (c) pause the bandwidth-absolute parts
of E2/E3 entirely pending hardware investigation outside this campaign's
scope.
