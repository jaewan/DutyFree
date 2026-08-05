# PLATFORMS.md — Phase 1 hardware inventory (E4 hygiene)

Collected 2026-08-05. Re-verification of the paper's `\jw` device-attribution
margin note (`Sec2_DirectoryTax.tex:26-32`), which warned that AMD and 8462Y+
device attributions were never independently confirmed and that a blanket
"all platforms use device X" claim should not be restored without checking.

## Headline finding: all three hosts currently carry the same CXL device

| Host | Role | PCI addr | Device | Subsystem | NUMA node (device) |
|---|---|---|---|---|---|
| mos181 (c3, EMR host) | Intel 8592+ | 27:00.0 | Montage Technology M88MX5891 CXL Memory Expander (rev 01), PCI ID 1b00:c001 | Samsung Electronics, Device 0103 | 0 (same-socket) |
| moscxl (broker, AMD host) | AMD EPYC 9754 | bf:00.0 | Montage Technology M88MX5891 CXL Memory Expander (rev 01), PCI ID 1b00:c001 | Samsung Electronics, Device 0103 | (RCiEP, no discrete NUMA-node line reported by lspci) |
| mos182 (c4, SPR host) | Intel 8462Y+ | bd:00.0 | Device 1b00:c001 (same PCI ID as above; vendor string not resolved by this lspci's ID database) rev 01 | Samsung Electronics, Device 0103 | 1 (cross-socket relative to node0) |

**This directly bears on the paper's `\jw` note:** the note was right to warn against
assuming uniformity — the EMR host's device was in fact swapped (see below) — but
empirically, as of 2026-08-05, all three machines *do* carry the identical
Montage M88MX5891/Samsung part. This is a fleet-wide hardware refresh, not
confirmation that this was true when any specific paper dataset was collected.
**Do not use this table to backfill device attribution for old CSVs/results** —
only to describe currently-installed hardware for any new Phase 1 data.

## EMR host (mos181/c3): confirmed device swap since paper submission

- Paper claim (`Sec2_DirectoryTax.tex:15`): "Micron CXL 2.0 Device 6400 Type 3
  expander."
- A cached file on this host, `~/micron.lspci.txt` (dated May), records at PCI slot
  27:00.0: `Micron Technology Inc Device 6400 (rev 02)`.
- Live `lspci -s 27:00.0` on this same host/slot, right now: `Montage Technology
  Co., Ltd. CXL Memory Expander Controller M88MX5891 (rev 01)`, Samsung subsystem.
- **Conclusion: the physical card in that slot was swapped between May 2026 and
  now.** Any Intel dataset collected before the swap (bundled CSVs under
  `benchmarks/data/catmba_*.csv`, kernel `7.0.0-22-generic`, one point release
  behind this host's current `7.0.0-28-generic`) should be treated as
  **provenance-uncertain for device attribution** — the qualitative
  allocation-vs-bandwidth mechanism claims are very unlikely to be
  device-specific, but exact BW/latency numbers should not be assumed to
  transfer across the swap without re-measurement (E2/E3 in this campaign
  re-measure on the currently-installed device).

## Link details (from `lspci -vvv`, sudo)

| Host | Device | Link capability | Link status | Notes |
|---|---|---|---|---|
| EMR (mos181) | 27:00.0 | 32 GT/s, x16 | 32 GT/s, **x8 (downgraded)** | Root Complex Integrated Endpoint; region0 16 MiB registers, RAM region 256 GiB (274877906944 B); `cxl list` reports `qos_class_mismatch: true` (flagged, not otherwise explained by tooling — worth follow-up but out of scope for this pass); firmware 14.40.1.060f.46. |
| AMD (broker) | bf:00.0 | not reported by `lspci -vvv` for this RCiEP (no LnkCap/LnkSta block) | — | `cxl list` on this host returns "no matching devices found" — the AMD platform does not expose this card through the Linux `cxl` subsystem's usual enumeration (ACPI CFMWS-based fixed window instead), even though the memory is usable via NUMA node 2 / `mbind`. Region: `Range1 0000010080000000-000001407fffffff` (256 GiB) CDAT-class, Active. |
| SPR (c4) | bd:00.0 | not reported by `lspci -vvv` for this RCiEP (no LnkCap/LnkSta block) | — | `cxl list -M -u` (this platform requires explicit `-M`) reports `ram_size: 256.00 GiB`. Device sits at NUMA node 1 (socket 1), while the cpuless CXL NUMA node is node 2, and node distances (`0:24, 1:14`) confirm node1 is physically closer — i.e. **the CXL card is attached to socket 1**; the harness's cross-socket control runs the victim on node0/cpu0 and streams from node2, making that a genuinely cross-socket path relative to the victim. |

## CPU / topology summary

| Host | CPU | Sockets | Cores/socket | Threads/core | L3 | Microcode | Governor (as found) | Turbo (as found) | SMT | Load avg (as found) |
|---|---|---|---|---|---|---|---|---|---|---|
| EMR (mos181) | Xeon Platinum 8592+ | 2 | 64 | 2 | 320 MB total (20-way, 16 MB/way) | 0x210002d3 (matches paper) | **powersave** | **on** (`no_turbo=0`) | on | 0.07/0.04/0.06 |
| AMD (broker) | EPYC 9754 (Bergamo, Zen4c) | 2 | 128 (16 CCX x 8c) | 2 | 512 MB total (32 x 16 MiB/CCX, 16-way) | n/a (not queried; AMD doesn't expose via `microcode` the same way) | performance | off (`Frequency boost: disabled`) | on | 0.00/0.00/0.00 |
| SPR (c4) | Xeon Platinum 8462Y+ | 2 | 32 | 2 | 60 MB | 0x2b000661 | performance | off (`no_turbo=1`) | on | 0.29/0.39/0.52 |

**Flag for the record:** the EMR host (mos181/c3) — the machine this whole
session runs on, and the source of every Intel number in the paper — is
**currently in `powersave` governor with turbo enabled**, contradicting both
the paper's stated methodology ("`performance` governor, turbo off",
`Sec2_DirectoryTax.tex:94`) and this campaign's ground rule #1. This was left
unchanged pending explicit confirmation before E2/E3 (see PHASE1_FINDINGS.md) —
flipping governor/turbo is a machine-wide setting on a shared, multi-user host
(other active sessions were observed: tmux sessions under `domin`, an
interactive login from user `seungjunn`), not scoped to the cores this
campaign uses.

## AMD per-core WC rate reconciliation (same-CCX vs spread-across-CCX)

Deferred to the A6/hygiene follow-up pass — requires two additional aggressor
placements (WC 1T/7T same-CCX vs spread-across-CCX) not yet run as of this
snapshot. Tracked as an open item, not fabricated here.

## SPR cross-socket topology (for the paper's cross-socket control)

- Victim pinned to NUMA node 0 (per `benchmarks/experiments/cat_mba.py`
  convention, `VICTIM_CPU=0`, `VICTIM_NODE=0`).
- CXL device physically attached at NUMA node 1 (socket 1), exposed as cpuless
  node 2. Node distances: 0->2 = 24, 1->2 = 14, 0->1 = 21.
- This makes the "cross-socket control" concretely: victim on socket 0's local
  DRAM, contending aggressor traffic crossing from socket 0 into the CXL device
  physically hanging off socket 1 -- a genuinely different (longer, cross-die)
  path than the same-socket EMR configuration (EMR's CXL device sits at node 0,
  same socket as the victim).
