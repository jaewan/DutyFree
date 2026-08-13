# Canonical config proposal for #15 (Build B) and #28 (predictor head-to-head)

Written 2026-08-13, for the lead's sign-off per `PAPER_SESSION_PROMPT.md`
§9 ("Spending on #15" and, transitively, #28 both require this). Per
`GATE1_RECONCILIATION.md`'s own plan ("Still to do" #5): "Resolve the
lineage question once (2)-(4) are in: one canonical config becomes the
base for Build B and the head-to-head." Status of (2)-(4):

- **(2) h1bw/sens re-runs:** done this session. `tab:sens` re-ran clean
  (`GATE1_SENS_RERUN_OUTCOME.md`). `tab:h1bw` did **not** — the
  reconstruction surfaced an unresolved anomaly in the HNF's hit
  accounting under H2 (`GATE1_H1BW_RERUN_OUTCOME.md`). See the caveat
  below — this matters for #28 specifically.
- **(3) `tab:h3sf` re-instantiation at its producing commit `0102eee441`:**
  already done (pre-dates this session; see `GATE1_RECONCILIATION.md`'s
  `tab:h3sf` row — 2/4 rows match exactly, 2/4 off ~18% with an
  unresolved SF-geometry assumption, flagged there as open).
- **(4) Eunji's answer** on which checkout her description came from:
  **still outstanding.** `EUNJI_QUESTION_DRAFT.md` is drafted but, per
  §11, only you can send it. This proposal does not wait on it, but is
  offered as **provisional pending her reply** — if her answer changes
  the assumed lineage, this config gets revised, not silently kept.

## The proposed canonical config

Base: the config already used, unmodified, across `tab:gem5`'s local-DRAM
column re-run, `tab:h3sf`'s de-confound, and this session's `tab:sens`
re-run — i.e. **not a new config**, but a decision to stop treating each
table's harness as independently sourced and instead pin all three
(`tab:gem5`, `tab:sens`, and everything #15/#28 do) to one tree state.

- **Commit:** `~/DutyFree-Gem5` `b2c64991948e771e660041b17ef8c0265d835873`
  (`streaming` branch) — the most recently, most thoroughly scrutinized
  commit in the project (12/12 clean arms on the Gate-1 local-DRAM column,
  the `tab:sens` re-run this session). Anything #15/#28 needs beyond this
  commit is a new, documented change on top of it, not a different base.
- **Topology/host model:** `configs/deprecated/example/se.py --ruby
  --topology=Pt2Pt --chi-config=CHI_config_8592.py --num-l3caches=1
  --num-dirs=1 --cpu-type=O3CPU --cpu-clock=1.9GHz`, L1d 48 KiB/12-way, L1i
  32 KiB/8-way, L2 2 MiB/16-way, L3 5 MiB/20-way (the anchor host's L3 —
  5 MiB = 320 MiB/64, per `app:gem5`), `--mem-type=SimpleMemory
  --mem-size=256GiB --cxl-mem-size=128GiB --dram-latency=98ns
  --cxl-latency=203ns`.
- **ITERS:** `3,000,000` always (§5.3's gate). No script in this repo
  should default to `3e5` for anything that reaches the paper again;
  `p1batch.sh`'s own comment ("ITERS=3e5 exploratory") should be read as a
  standing warning, not a default to inherit.
- **Memory pool placement:** be explicit about `ALL_CXL` / `ALL_LOCAL` /
  `CPU_POOLS` (`se.py:320-339`) in every #15/#28 script from the start —
  do not rely on the default (CPU 0 → local DRAM, CPU 1+ → CXL), which
  this session's `tab:h1bw` attempt got wrong for a single-core run before
  finding the override. Whatever placement #15/#28 chooses, name it
  explicitly per §5.1 (arm identity includes host/placement, not just WSS
  and aggressor type).
- **SF geometry (only relevant once H3 is in scope):** `HNF_SF_FINITE=1
  HNF_SF_SETS=4096 HNF_SF_WAYS=16` (65,536 entries) — `tab:h3sf`'s own
  de-confound geometry, the one condition in the whole project with a
  clean, reproduced, geometry-robust H2-vs-H3 comparison
  (`streaming-gem5-results` memory, "#17 DE-CONFOUND"). Do not re-derive a
  different SF size without a documented reason; sweeping to find a nicer
  number is the exact failure §6.6 names.
- **Prefetch/MSHR knobs:** leave at CHI_config_8592.py's defaults
  (`PF_DEGREE=4`, `L1_MSHR=16`, `L2_MSHR=48`, `HNF_MSHR=32`) unless a task
  has a specific, documented reason to sweep one — and if it does, name
  the swept knob explicitly in the arm identity, not just "MSHR."

## The one caveat #28 needs before it can trust any bandwidth number

This session's `tab:h1bw` reconstruction found the HNF's generic
`CacheMemory` hit/miss counters behaving in a way inconsistent with H2's
own non-allocating definition — H2 showing a *far higher* hit rate than
WB despite being the arm that isn't supposed to leave data in the LLC at
all (`GATE1_H1BW_RERUN_OUTCOME.md`, unresolved, leading hypothesis: a
tag/directory hit against a pure-R entry may be getting counted the same
as a true data hit). **#28's predictor head-to-head is going to want
exactly this kind of allocation/bandwidth accounting** to characterize a
predictor's mispredict pollution and warm-up cost. Recommend the first
thing #28 does — before comparing against SHiP/Hawkeye/Mockingjay — is
resolve or route around this counter ambiguity (the `.sm`-level trace
`GATE1_H1BW_RERUN_OUTCOME.md` recommends), so #28's own numbers don't
inherit an unexamined confound from day one.

## What this does not resolve

The #15 "Build B" scope conflict itself — this proposal fixes *which tree
state* both tasks build on, not the substantive design question Build B
was flagged over. That determination is still yours to make; this
document only removes the "which commit" excuse for not starting once you
decide to.
