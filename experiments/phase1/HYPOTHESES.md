# Phase 1 Hardware Profiling — Pre-registered Hypotheses

**Dated: 2026-08-05, before any Phase 1 run.** Per ground rule #5 this file is
frozen once runs start; outcomes go in `OUTCOMES.md` files per experiment, not here.

## Path/scope deviations from the mission spec (recorded here, not silently applied)

- The mission spec references `[[REPO]]/bench/phase1/<exp>/`. No `bench/` directory
  exists in this repo. The actual harness lives at `benchmarks/bench/` (Intel
  EMR/SPR: `pointer_chase.c`, `stream_wb.c`, `stream_wc.c`, driven by
  `benchmarks/experiments/cat_mba.py` / `cat_mba_driver.sh`) and at
  `~/tmp_dutyfree_exp/src/{victim,aggressor}.c` on `broker` (AMD). Deliverables for
  this campaign are placed at `experiments/phase1/<exp>/` instead, matching the
  existing `experiments/asplos/` convention. Nothing under `benchmarks/` or
  `experiments/asplos/` is modified.
- `[[AMD_HOST]]`=`broker` (192.168.60.180), `[[VCORE]]`=cpu0, `[[ACORES]]`=cpus1-7
  (same CCX0), `[[AMD_CXL_NODE]]`=2. `[[EMR_HOST]]` = the local machine this session
  runs on (`mos181`, aka "c3"), `[[EMR_CXL_NODE]]`=2. `[[SPR_HOST]]`=`c4`
  (192.168.60.182, aka `mos182`), added to `~/.ssh/config` this session — hygiene
  tasks (E4) only, per user direction. `[[IDLE_THRESHOLD]]` = load average 1.0 on
  both AMD and EMR, confirmed with the user.
- **Known pre-existing data-provenance issues, recorded here for context (not an
  outcome of this campaign):**
  1. The AMD `tab:amdcat` headline numbers (19.85x / 6.92x / 1.02x) in the paper
     have no surviving raw dataset on disk (`H3_GATE_RESULT.md` /
     `/tmp/task1_raw.jsonl` are gone). Per user direction, E1's A0-A3 arms are a
     **fresh n>=12 reproduction**, treated as the new gate, not a check against an
     existing file.
  2. The Intel host's CXL device was physically swapped after some paper data was
     collected: paper claims Micron CXL 2.0 Device 6400; live `lspci` on this same
     host/slot (27:00.0) now shows a Montage Technology M88MX5891 (Samsung-branded).
     Per user direction, this is documented in `PLATFORMS.md` (E4) and flagged in
     `PHASE1_FINDINGS.md`; old Intel CSVs are treated as provenance-uncertain but
     E2/E3 proceed on the currently-installed device.

## Pre-registered hypotheses

**P1 (E1, AMD residual mechanism).** The AMD 6.92x post-CAT residual is dominated
by coherence machinery, not LLC capacity: either (a) probe-filter/back-invalidation
churn (victim LLC occupancy collapses despite dedicated ways) or (b) shared
lookup/queue occupancy (victim occupancy intact, hit/miss latency inflates). H2
(allocation-bypass) alone would NOT remove it; a type-licensed lookup/enrollment
skip (H3+) would.

**P2 (E2, Intel bandwidth mechanism).** On Intel, single-core WB CXL bandwidth
(~15.8 GB/s) does NOT depend on the LLC as a prefetch staging buffer: bounding the
stream's LLC footprint (flush-behind) keeps bandwidth within ~15% of unbounded WB
down to small footprints.

**P3 (E2, Intel silicon H2 emulation).** A flush-behind stream at near-full
bandwidth returns the Intel co-run victim to ~baseline (silicon emulation of H2).

## Verdict logic pre-registered for E1 (from mission spec, copied verbatim)

- A4 taxes victim substantially => lookup/queue occupancy is real => H3-lookup-skip
  is the required contract behavior; gem5 team models port/queue contention.
- A4 clean AND victim llc_occupancy collapses in A2 => back-invalidation/probe-filter
  churn => gem5 team re-skins existing finite-SF machinery as home-side probe filter.
- A4 clean AND occupancy intact in A2 => queue/XI occupancy at the miss path; check
  A6 superlinearity as corroboration.
- A1 vs A5 at matched BW isolates any CXL-path-specific component.
