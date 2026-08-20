# The AMD host's platform state has no recorded provenance

Found 2026-08-21 while staging the GAPBS CAT capacity-sensitivity gate. This
is a provenance finding, not a refutation: no published number is shown to be
wrong. But `tab:appplat`'s platform-state claim cannot presently be
substantiated for the AMD host, and per §6.6 the correct response is to say so.

## The claim

`Appendix.tex` (`app:platforms`): "All hosts run the `performance` governor
with turbo disabled unless a row says otherwise; C-states deeper than C1 are
disabled". `tab:appplat` states "Governor / turbo: performance / off" for the
AMD EPYC 9754 column. `benchmarks/README.md:114` calls this "the **frozen
protocol**" and adds "NUMA balancing: off, THP: `madvise`" and
"Pre-allocated 2 MB hugepages on victim and CXL nodes".

## What is actually on disk, and on the machine

`benchmarks/setup/` contained `emr_freeze.sh` and `spr_freeze.sh` (both
2026-07-15) and one capture, `state/emr_system_state.txt` (Intel 8592+,
2026-08-07). **There was no AMD freeze script and no AMD state capture.**
Repo-wide, no campaign artifact of any kind records governor, turbo, or
`numa_balancing`: a grep for those keys across every `.json`/`.jsonl` in
`benchmarks/` and `experiments/` matches only files created today.

An as-found capture of `moscxl` (new `bergamo_freeze.sh`, `VERIFY_ONLY=1`,
2026-08-21T01:19+09:00) reports:

| knob | frozen protocol | as found |
|---|---|---|
| governor (`cpu8`) | `performance` | **`schedutil`** |
| turbo | off | **`cpufreq/boost = 1`** |
| `perf_event_paranoid` | −1 | **4** |
| 2 MB hugepages, nodes 0/1/2 | pre-allocated | **0 / 0 / 0** |
| microcode / stepping | `0xaa00215` / 2 | `0xaa00215` / 2 (matches) |

The host rebooted on 2026-08-19 (uptime 1 d 13 h at capture; a desktop login
by another user dates from 2026-08-19 12:03). The most likely history is that
the AMD host was frozen by hand for the campaigns and lost that state at the
reboot. Two facts are consistent with a hand freeze rather than a scripted
one: no script existed to apply it, and the 2026-08-11 sizing gate measured
CoV 1.387% on this host against 0.109% on the scripted Intel host.

Also noted: `moscxl` has **no git checkout** of `DutyFree` at all -- its
`~/DutyFree` is a hand-staged `benchmarks/e2e/gapbs` tree -- so AMD-side
artifacts have been produced outside version control and copied in.

## What this does and does not affect

It does **not** invalidate anything published. The microcode and stepping row
re-verifies; the AMD numbers use RDTSC-based cycles/load and resctrl, neither
of which needs `perf_event_paranoid`; and a frequency policy applied by hand
is still applied.

It does mean two things:

1. **No AMD result in the paper can be re-measured under the stated protocol
   until `moscxl` is re-frozen.** That includes `tab:amdcat`, whose 6.92x
   CAT residual is under the §3 embargo, and the AMD hash-join arms.
2. **The `tab:appplat` platform-state row is, for the AMD column, an
   unverifiable claim.** It is very probably true. Nothing in the repository
   demonstrates it.

## What was done about it

`benchmarks/setup/bergamo_freeze.sh` is new and mirrors `emr_freeze.sh`, with
the AMD differences handled: turbo is `cpufreq/boost` rather than
`intel_pstate/no_turbo`; this host runs `acpi-cpufreq`, so there is no
`energy_performance_preference`; and `min_cbm_bits=0` is called out because
this driver accepts the mask `0`. It has a `VERIFY_ONLY=1` mode that captures
without writing, and it always writes
`state/bergamo_system_state.txt`. Hugepage provisioning is opt-in rather than
silent, because hugepage placement is an experimental variable on this host.

## Two decisions for the lead

1. **Re-freezing `moscxl` requires degrading another user's live desktop
   session** (`performance` governor, boost off). Every AMD number destined
   for the paper should be taken frozen; the GAPBS gate arm now running is a
   self-contained ratio between two back-to-back arms and is disclosed as
   unfrozen instead. Its CoV is in fact excellent -- g22 full trials of
   1.749230 / 1.749400 / 1.750630 s -- because on this part the L3 is
   per-CCX, so the desktop occupies different L3 domains entirely and cannot
   contend for the victim's ways.
2. **Whether `tab:appplat` should soften the AMD platform-state row.** The
   honest form is a footnote that the Intel hosts' state is scripted and
   captured while the AMD host's was applied by hand and is not recorded.
   That is a page-1-adjacent evidentiary posture question, hence §9.
