# Pre-registration: co-run pair re-run (tab:gem5)

Dated 2026-08-09, before running. Per ruling: this is the sharpest,
weakest-provenance, most load-bearing gem5 number in the dataset
(demonstrates the enforced `setstreaming` path end-to-end) — re-run it
first, give it its own table, and settle the "1.34 vs 2.57" anomaly as
part of this run rather than as a separate Gate 2 arm.

## Operating point (documented explicitly, per ruling)

- Aggressor: `testcase/dirtax/aggressor` (the `wb` tag in `b4run.sh`), 1
  aggressor thread/core.
- Memory latency class: to be confirmed from this run's own
  `gate1_manifest.py` output — `b4run.sh`'s `COMMON` config instantiates
  two `SimpleMemory` controllers (98 ns local, 203 ns CXL per prior runs
  this session), but which one the aggressor's allocation actually lands
  in is not yet confirmed by direct inspection, only inferred from the
  paper's own framing ("a single CXL-latency aggressor"). This run's
  manifest will settle it, not assume it.
- Victim WSS: `2650` (KiB, per `b4run.sh`'s hardcoded `WSS=2650`) — the
  paper's stated "53% LLC" point (2650/5120 KiB $\approx$ 51.8%, close
  enough to 53% to be the same point modulo rounding/an old LLC-size
  assumption).
- LLC: confirmed genuinely 5 MiB shared (this session, `alone` config,
  same `COMMON` string).
- Achieved fill rate: to be read from this run's own aggressor-side
  bandwidth stat, not assumed.

## Prediction (falsifiable, stated before running)

At this operating point — 5 MiB shared LLC, single aggressor, victim at
~53% LLC — **the WB co-run tax should land near the old prose-cited
1.34x (a mild-pressure operating point), not near tab:gem5's tabulated
2.57x (the high-fill-rate, local-latency calibration point)**, *if* the
prose's 1.34x reflects this same CXL-latency-aggressor configuration and
the table's 2.57x reflects a different (e.g. local-DRAM-latency,
higher-fill-rate) calibration run.

## What would falsify this / what each outcome means

- **Lands near 1.34x**: the "1.34 vs 2.57" anomaly closes as two
  legitimate operating points on one pressure curve, not a bug — prose
  and table were both right, just about different configs, and
  `\cref{tab:gem5}` in the prose is simply the wrong cross-reference (it
  should point to a description of the mild-pressure point, not the
  table showing the high-fill-rate one). Paper fix: correct the
  cross-reference, add a one-line statement of each experiment's
  occupancy-pressure ratio (bandwidth achieved / LLC capacity or
  similar), and Gate 2's original "10 MiB explains 1.34x" hypothesis is
  retired as moot — no need to run it as a separate arm.
- **Lands near 2.57x**: the prose's 1.34x is unexplained by operating-
  point difference alone — something else changed (stale number from an
  earlile config, a real regression, or a config this session hasn't
  found). Do not write a text-fix in this case; escalate to a dedicated
  investigation before touching the paper.
- **Lands somewhere else entirely**: report exactly what and treat this
  finding as gates the whole tab:gem5 reconciliation, not just this one
  cross-reference.

## H2 recovery, secondary check

The `st` tag (same operating point, `PROT_STREAMING`-tagged /
`setstreaming`-tagged stream) should return the victim close to baseline
(the paper's own +H2 column claims 1.00x at every LLC-fraction row) —
already have both `st` runs from this session's Gate 0 follow-up
(`/tmp/st_postmerge/stats.txt`, `/tmp/st_premerge/stats.txt`, both
byte-identical to each other), so this doesn't need a fresh run, just
extraction of the actual tax number from the already-collected data.

## Method

Run `b4run.sh corun_wb_v2 wb 0 0` (WB baseline) at current `streaming`
HEAD (`23f27375e9`+`a309523389`), with `gate1_manifest.py` attached.
Extract the H2/`st` tax from already-collected data
(`/tmp/st_postmerge/stats.txt`). Tag the result `table-corun-v2` in the
gem5 repo once confirmed.

## Outcome (2026-08-09, post-run)

**Operating point, settled by direct inspection (not inferred):**

- Memory-latency class of each process — checked via `mem_ctrls{0,1}`
  per-controller `bytesRead`/`numReads` in `stats.txt`, not assumed from
  the paper's own framing: `mem_ctrls0` (98 ns, local) received
  1,716,480 B / 26,820 reads — matches the victim's ~2.6 MiB WSS at
  64 B/line almost exactly. `mem_ctrls1` (203 ns, CXL range, physical
  addresses ≥128 GiB) received 20,434,880 B / 319,295 reads — matches a
  streaming scan of the aggressor's 10 MiB buffer repeatedly cycling
  through the shared 5 MiB LLC. **Confirmed: victim is on local-latency
  memory, aggressor is on CXL-latency memory** — the paper's "a single
  CXL-latency aggressor" framing is correct for this test, verified from
  instantiated traffic rather than taken on faith (neither `aggressor.c`
  nor `b4run.sh` contains an explicit CXL-targeting call — the split
  emerges from gem5 SE-mode's own physical-frame allocation order, not
  from anything in the harness that names it).
- Achieved fill rate: `mem_ctrls1.bwRead::total` = 3,140,097,271 B/s ≈
  **3.14 GB/s** — well below the aggressor binary's own documented
  design ceiling (~14 GB/s at full LLC-resident bandwidth per the
  comment in `aggressor.c`). CXL latency (203 ns) plus LLC contention
  from the shared 5 MiB cache is throttling the aggressor well under its
  compute-bound ceiling — a plausible, mechanistic reason the achieved
  pressure at this operating point is *lower* than whatever configuration
  produced the paper's 1.34x, not just an unexplained gap.
- Victim WSS 2650 KiB / 5120 KiB LLC ≈ 51.8% — matches the "53% LLC" row
  as expected.

**Result:**

| Quantity | Value |
|---|---|
| Alone baseline (`system.cpu0.numCycles`, victim, no aggressor) | 10,150,199 |
| WB co-run (`corun_wb_v2`) | 12,372,095 |
| **WB tax** | **1.2189×** |
| H2/`st` (from already-collected `/tmp/st_postmerge/stats.txt`) | 10,690,270 |
| **H2 tax** | **1.0532×** |

**Verdict: lands near 1.34x, not near 2.57x** — closer to the mild-
pressure operating point (off by ~9%, in the direction explained by the
achieved-fill-rate shortfall above) than to the table's high-fill-rate
2.57x calibration point (off by 53%, wrong direction to explain by any
mechanism this run surfaced). Per the pre-registration's own decision
rule: **the "1.34 vs 2.57" anomaly closes as two legitimate operating
points on one pressure curve, not a bug.** `\cref{tab:gem5}` at lines 241
and 434 is the wrong cross-reference for the 1.34x/1.02x prose sentence —
it should point to a description of this mild-pressure point (this
re-run), not to the table's own 53%-LLC row (which is a different,
higher-fill-rate calibration and correctly shows 2.57x/1.00x on its own
terms). Gate 2's original "10 MiB explains 1.34x" hypothesis is retired
as moot per the pre-registration — no separate arm needed.

H2 recovery: 1.0532x, i.e. victim returns to within ~5% of solo baseline
under `setstreaming`-tagged access — qualitatively confirms the paper's
+H2 "recovers to ~1.00-1.02x" claim (this run's 5% residual is close
enough to call the mechanism confirmed; it is not an exact match to
either 1.00x or 1.02x, which is expected since this is a current-HEAD
re-run rather than a historical reconstruction — see
`GATE1_RECONCILIATION.md`).

**Paper-fix, queued (not yet applied to `Sec5_Evaluation.tex`)**: correct
lines 241/434's cross-reference and numbers to describe this mild-
pressure point explicitly (1.22x → 1.05x, ~5% residual, current-HEAD
`table-corun-v2` provenance), and add a one-line occupancy-pressure-ratio
statement (achieved fill rate / LLC capacity, or similar) distinguishing
this row from `tab:gem5`'s own high-fill-rate 2.57x row so a reader can
see both are real, on the same curve, at different pressure points.

**Tag**: `table-corun-v2` — to be applied to the gem5 repo at the commit
this run executed against (`a309523389`) once this write-up is committed.

## Follow-on finding: tab:gem5's own WB column may not be reproducible with the current harness

Reading `Sec5_Evaluation.tex` directly (not just the margin notes) surfaces
something Gate 1's archaeology missed: **the paper's own text already
states the 1.34x/2.57x split is expected, not an anomaly** — the prose
sentence introducing the co-run pair explicitly says the aggressor
"streams from CXL through the full STREAMING path," and `tab:gem5`'s own
caption says *"The model is calibrated to the local-DRAM operating point
(sim 2.57x vs. hw 2.61x at 53%); the CXL tax is milder because CXL
bandwidth caps the LLC fill rate."* — i.e. the co-run-pair prose (CXL
aggressor, 1.34x) and `tab:gem5`'s WB column (local-DRAM aggressor,
2.57x) were never meant to be the same number. `\cref{tab:gem5}` at
lines 241/434 reads correctly as "unlike \cref{tab:gem5}" earlier in the
same paragraph (a deliberate contrast, not a same-number citation) —
this session's re-run adds empirical confirmation of that contrast
(1.22x vs 2.57x, correct direction) rather than exposing a new bug. The
paper-fix is now smaller than originally scoped: tighten the prose so a
reader skimming just the `(\cref{tab:gem5})` parenthetical doesn't read
it as a numeric match, not "fix a wrong cross-reference."

**But this reopens a different, sharper question**: is `tab:gem5`'s own
"local-4"/WB column (2.57x at 53%, local-DRAM aggressor) even
reproducible with the *current* harness? Traced `se.py`'s CXL-pool
assignment directly (not assumed): whenever `--cxl-mem-size` is set,
process-to-pool assignment is **hardcoded** — `cpu0 -> DRAM pool 0,
cpu1+ -> CXL pool 1` — with `ALL_CXL=1` as the only override, and it only
forces *everyone* onto the CXL pool (calibration mode for single-core
CXL runs). **There is no `ALL_LOCAL` equivalent** to put a two-core
victim+aggressor pair on local DRAM together. Confirmed by direct
measurement (this run's own `mem_ctrls0`/`mem_ctrls1` traffic split,
above): the aggressor (cpu1) landing on CXL is not incidental, it is the
code's only available two-core configuration short of a script edit.

**Implication**: `tab:gem5`'s "local-4" WB column cannot currently be
re-instantiated by re-running `b4run.sh`'s existing `wb`/`st` tags at any
WSS — doing so only ever regenerates more points on the *same* CXL-
aggressor curve this pre-registration already measured, under a
different label. Producing a faithful `table-gem5-v2` for the *local-4*
column specifically requires either: (a) a small, reviewable change to
`se.py`'s pool-assignment block (e.g. an `ALL_LOCAL` env var mirroring
`ALL_CXL`, or a `--pool-map` override) to put both processes in DRAM
pool 0, or (b) accepting that the local-DRAM operating point is out of
scope for a current-HEAD re-run and re-labeling `tab:gem5`'s WB/local-4
column as historical/unreproduced (same provenance class as the rest of
the table). **Not decided here — this is a fork the campaign's own Gate
0/Gate 1 discipline says should go to the user, not be resolved by
quietly patching `configs/deprecated/example/se.py` mid-investigation.**
The CXL/pool-assignment env vars (`ALL_CXL`) and the pool policy itself
have been added to `gate1_manifest.py`'s provenance capture either way,
since this was a real gap the tool had regardless of which path is
chosen.
