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

## Follow-up link/device investigation (remote diagnosis, no BIOS access)

Per user direction, investigated further before deciding how to proceed.
Everything checkable over SSH without a reboot:

1. **Topology**: `lspci -tv` shows `27:00.0` hanging directly off root bus 27
   with **no intermediate switch/bridge** -- it is a genuine PCIe Root
   Complex Integrated Endpoint, wired straight to the CPU's on-die CXL root
   port. This rules out "a discrete switch/bridge downstream port is
   capping the link to x8" -- there is no such intermediate device to blame.
   The x8-vs-x16 gap is either the physical slot/riser wiring on this
   motherboard (Intel `M50FCP2SBSTD`, BIOS `SE5C741.86B.01.02.0005.2512081849`)
   or a link-training outcome on the direct CPU<->device link -- both are
   BIOS/hardware-level questions this session cannot resolve without a
   reboot into firmware setup or physical slot inspection.
2. **Kernel-side CXL bandwidth-QoS bug found, but appears unrelated to raw
   bandwidth**: `dmesg` shows a one-time (count=1) `WARN_ON` at boot
   (`drivers/cxl/core/port.c:604`, `to_cxl_port`), triggered by
   `cxl_acpi ACPI0017:00: not a cxl_port device` during
   `cxl_region_shared_upstream_bandwidth_update`. `cxl list -R -v` confirms
   the downstream effect: `decoder0.0` has `"qos_class": 0` and region0
   carries `"qos_class_mismatch": true`. This is Linux's CXL memory-tiering
   QoS-classification bookkeeping (used for promotion/demotion decisions,
   not a hardware bandwidth throttle) -- it's a real kernel-driver defect
   worth flagging (add to `PLATFORMS.md`), but there is no mechanism by
   which a QoS-*classification* bug would physically halve link bandwidth,
   so this is reported as a separate, probably-unrelated finding, not folded
   into the bandwidth explanation.
3. **No BIOS-level CXL/PCIe bifurcation setting is readable or changeable
   from this SSH session.** This is the hard stop for remote diagnosis.

**Conclusion of the investigation**: the x8-vs-x16 gap most likely traces to
motherboard slot wiring or a link-training outcome that requires physical
access or a BIOS-setup reboot to resolve -- neither of which is available in
this session. Recommend flagging to whoever has physical/BIOS access to this
host as a follow-up outside Phase 1's remote-session scope.

## Recommendation

Do not run the full n=12 MSR sweep or proceed to E2b/E3 on the assumption
that ~15.8 GB/s is the achievable ceiling here. Given the investigation above
hit a hard stop (BIOS/physical access required), this is left as an open
item pending that access, rather than resolved in this pass.
