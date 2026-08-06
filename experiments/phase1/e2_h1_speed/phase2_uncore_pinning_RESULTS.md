# Phase 2.3 — uncore-pinned re-baseline: RESULTS

Dated 2026-08-07. **Correction to my own initial "decisive" finding below --
read the full section, not just the first check.** This is exactly the kind
of self-correction the panel's review modeled; reporting it plainly rather
than quietly keeping the earlier framing.

## Intel: control found and applied -- but it does NOT explain the anomaly

Officially-supported sysfs interface exists on this kernel:
`/sys/devices/system/cpu/intel_uncore_frequency/package_00_die_00/{min,max}_freq_khz`
(hardware range 800000-2400000 kHz on this SKU, matching exactly the
1500/2400 MHz quiescent/loaded values `turbostat` showed in E2b). Pinned
min=max=2400000.

**First check (n=3, manual) looked decisive**: quiescent ~81.5 cyc/load,
D=256KiB loaded ~80.9 cyc/load under pinned uncore -- tax ~0.99x, seemingly
not the original 0.90x. I reported this as confirming the panel's
hypothesis.

**Full n=12 re-run contradicted it**: `run_e2b_flushbehind_uncorepinned.py`,
same D sweep, uncore pinned throughout. Result: **tax at D=32/256KiB/2MiB
came back at ~0.905 [0.898,0.908]-ish -- essentially identical to the
original unpinned run's 0.901-0.902.** Pinning changed nothing once
measured properly at n=12.

| D | tax, pinned (n=12) | tax, original unpinned |
|---|---:|---:|
| 32 KiB | 0.905 | 0.901 |
| 256 KiB | 0.905 | 0.902 |
| 2 MiB | 0.905 | 0.901 |
| 16 MiB | 0.964 | 0.951 |
| 64 MiB | 1.358 | 1.335 |
| off | 2.354 | 2.307 |

**Direct verification of why the first check was misleading**: ran
`turbostat` wrapping single victim invocations. Confirmed uncore genuinely
stays pinned at 2400 MHz throughout, including during "slow" quiescent-style
runs -- ruling out uncore frequency as the cause. Then ran three
back-to-back, fully independent single-trial quiescent invocations (no
aggressor, no change in anything): **88.47, 81.86, 81.93 cyc/load** --
bimodal, not a smooth distribution, occurring with *zero* aggressor present
and *zero* uncore variation. My first "decisive" check (which happened to
draw two "fast" outcomes for the pinned quiescent baseline) was itself just
a sample from this same bimodal noise, not evidence that pinning fixed
anything.

**Corrected conclusion**: the "faster than quiescent" effect in the
original E2b result is **real and robust** (now independently reproduced a
third time, under a different uncore-pinning regime, landing at the same
~0.90-0.905). P3's headline finding stands as originally measured -- it was
never actually explained by uncore frequency; that was my own overreach
from a too-quick check, corrected here before it went into anything final.
**The true cause of the bimodal quiescent-vs-loaded difference remains
unidentified.** Ruled out: uncore frequency (directly verified). Not yet
tested: core-level C-state/P-state transition dynamics possibly affected by
whole-package activity (a single core's ramp-from-idle behavior could
differ when 7 siblings are already active vs when the whole package is
idle, independent of the "performance" governor's steady-state target);
DRAM refresh-cycle phase alignment; scheduler/interrupt artifacts specific
to a freshly-launched single-trial process. Flagged as a genuinely open
question, not resolved by this pass -- do not cite uncore frequency as the
explanation for E2b's sub-1.0x results in any write-up; that framing did
not survive its own verification.

## AMD: no software control path found -- documented gap, not fixed

Checked: no `fclk`/`uclk`/`dfclk` sysfs entries, no `amd_pstate` driver, no
`amd_hsmp` driver/device (`/dev/hsmp*` absent), `msr-tools`' `rdmsr`/`wrmsr`
CLI binaries aren't installed on `broker` (this session's own MSR
read/write, e.g. in the E1/E2a scripts, used direct file I/O on
`/dev/cpu/N/msr`, not this CLI). AMD's Data Fabric clock (FCLK) is normally
adjusted via SMU firmware commands, not a simple always-available MSR the
way Intel's uncore ratio-limit is -- without a verified MSR address (would
need the AMD PPR, already established as unreachable in this sandbox) or
the `amd_hsmp` driver, there is no read *or* write path available here.

**Given the Intel result above, this matters less than it first
appeared**: since Intel's uncore-frequency hypothesis for E2b's anomaly
didn't survive verification, there's now less specific reason to suspect
an analogous AMD fabric-clock effect explains anything in the AMD data
either -- though it remains genuinely unchecked, same as before. Flagged
alongside `NEEDS_BIOS_ACCESS.md`, not elevated in priority by this result.
