# Intel 8-thread aggregate reproduction gate — RESULTS

Dated 2026-08-06. This is the genuine Intel repro gate flagged as untested
(and NOT blocked by the x8/x16 CXL-link question) in `REPRO_FAILURE.md` and
`PHASE1_FINDINGS.md`. Run via the existing, previously-validated harness
(`benchmarks/experiments/cat_mba_driver.sh` + `cat_mba.py`), n=30 trials per
condition (exceeds the n>=12 floor) — reused, not rewritten, per the mission's
own instruction. One bug fixed to get it running: the driver's `mkdir -p
"$OUTBASE"` runs as root while the actual measurement runs via `runuser -u
domin`, so a fresh `results/` directory needs an explicit chown before the
first run (not a semantics change, just a permission fix to make the
existing script work).

## Config

- Host: this machine (mos181/c3, Intel Xeon 8592+), governor=performance,
  turbo=off (fixed earlier this session, confirmed still in effect).
- Victim: 170 MB pointer chase (53.1% of 320 MB LLC), cpu0, node0.
- Aggressor: 8 threads (`stream_wb`), cpus1-8, CXL node2, 5 GB region/thread.
- n=30 trials/condition (10s measure, 8s warmup each).

## Step 2 — baseline tax (the actual gate)

| condition | Q median (cyc/load) | A median (cyc/load) | slowdown | agg BW | paper | diff |
|---|---:|---:|---:|---:|---:|---:|
| s2_quiescent | 81.550 | 81.617 | 1.001x | 0.00 GB/s | (n/a, sanity check) | -- |
| s2_cxl8_baseline | 81.618 | 158.816 | **1.946x** | **30.82 GB/s** | 2.03x @ 34 GB/s | **-4.1% tax, -9.4% BW, both within gate** |

**GATE: PASS.** 1.946x is within 15% of the paper's 2.03x (only 4.1% off).
The quiescent baseline (81.55-81.62 cyc/load) also matches the paper's
stated 81.7 cyc/load almost exactly.

**Notable contrast with the single-core WB finding** (`REPRO_FAILURE.md`):
single-core CXL WB bandwidth measured ~8.9 GB/s vs no valid paper baseline
(that number turned out to be AMD's, not Intel's) with local DRAM at ~14.2 --
a ~37% gap by that comparison. Here, the genuine Intel *aggregate* 8-thread
bandwidth (30.82 GB/s) is only ~9.4% below the paper's real Intel figure
(34 GB/s). This supports the hypothesis floated in `REPRO_FAILURE.md`: the
CXL link/device's aggregate throughput ceiling is not automatically bounded
by one thread's core-side outstanding-request limit -- whatever is capping
single-core streams doesn't cap the 8-thread aggregate anywhere near as hard.
The x8-vs-x16 link question (still open, needs BIOS access) may explain
some of the remaining ~9.4% aggregate gap, or may not -- not disambiguated
here.

## Step 3 — CAT sweep

*(appended once s3_cat_full / s3_cat_3ways / s3_cat_1way land)*
