# Phase 2.3 — uncore-pinned re-baseline: RESULTS

Dated 2026-08-07.

## Intel: control found, applied, decisive correction confirmed

Officially-supported sysfs interface exists on this kernel:
`/sys/devices/system/cpu/intel_uncore_frequency/package_00_die_00/{min,max}_freq_khz`
(hardware range 800000-2400000 kHz on this SKU, matching exactly the
1500/2400 MHz quiescent/loaded values `turbostat` showed in E2b). Pinned
min=max=2400000 (the loaded arm's natural ceiling, so the loaded arms
aren't artificially slowed relative to the original data).

**Quick decisive check (n=3, manual)** before committing to a full re-run:
quiescent ~81.5 cyc/load, D=256KiB loaded ~80.9 cyc/load under pinned
uncore -- tax ~0.99x, not the original unpinned run's 0.90x. The panel's
prediction (pinning "turns a caveated 0.90x into a clean number") held on
first check.

**Full n=12 re-run**: `run_e2b_flushbehind_uncorepinned.py`, same D sweep,
same victim/aggressor setup as the original E2b, uncore pinned before and
restored after. See below for the corrected numbers once the run completes.
**Both the original (unpinned) and this corrected (pinned) dataset are kept
side by side** -- nothing overwritten, per the panel's instruction that
disclosure of both matters more than a single clean number.

## AMD: no software control path found -- documented gap, not fixed

Checked: no `fclk`/`uclk`/`dfclk` sysfs entries, no `amd_pstate` driver, no
`amd_hsmp` driver/device (`/dev/hsmp*` absent), `msr-tools`' `rdmsr`/`wrmsr`
CLI binaries aren't installed on `broker` (this session's own MSR
read/write, e.g. in the E1/E2a scripts, used direct file I/O on
`/dev/cpu/N/msr`, not this CLI). AMD's Data Fabric clock (FCLK) is normally
adjusted via SMU firmware commands, not a simple always-available MSR the
way Intel's uncore ratio-limit is -- without a verified MSR address (would
need the AMD PPR, already established as unreachable in this sandbox -- see
`e1_residual_decomp/RESULTS.md`'s L3-uncore-PMU caveat for the same root
cause) or the `amd_hsmp` driver, there is no read *or* write path available
here, not even a read-only check of whether AMD's fabric clock exhibits the
same quiescent-vs-loaded swing Intel's uncore does.

**This is the same class of gap as the EMR x8/x16 link question**:
genuinely out of reach from this session, not something to guess past.
Whether AMD's E1/A6 data (the same-CCX thread sweep, the superlinear knee)
carries an analogous fabric-clock confound is therefore an **open question,
not ruled out and not confirmed** -- flagged for whoever has BIOS/SMU-level
access to this host, alongside the existing `NEEDS_BIOS_ACCESS.md` item.
