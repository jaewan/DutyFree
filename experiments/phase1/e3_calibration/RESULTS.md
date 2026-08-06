# E3 — calibration_targets.csv: RESULTS

Dated 2026-08-06. n=12 throughout (`calibration_targets_raw_n12.csv` has all
576 raw per-rep rows; `calibration_targets.csv` is the aggregated
one-row-per-config deliverable with median + 95% bootstrap CI).

## Config

- Host: this machine (EMR/mos181), governor=performance, turbo=off.
- Leg 1 (thread sweep): `stream_wb`/`stream_wc`, cpus1-8, 1 GB region/thread,
  4s/rep.
- Leg 2 (SW-prefetch sweep): `stream_sw_prefetch` (new; HW prefetchers
  disabled via MSR 0x1A4=0xF, restored on exit), cpu1, 1 GB region, 4s/rep.
- Leg 3 (idle latency): `pointer_chase` dependent chase, 512 MB WSS, cpu1,
  n=12 trials in one invocation.

## Leg 1: thread-count sweep, WB/WC x CXL/local

| config | t=1 | t=2 | t=4 | t=8 |
|---|---:|---:|---:|---:|
| WB, CXL | 8.91 | 17.35 | 24.10 | 24.25 |
| WB, local | 14.23 | 28.75 | 56.63 | 107.41 |
| WC, CXL | 6.38 | 12.92 | 23.20 | 24.22 |
| WC, local | 10.93 | 22.20 | 43.97 | 84.56 |

**CXL saturates by 4 threads (~24 GB/s regardless of WB/WC beyond that
point) — link/device-bound.** Local DRAM scales near-linearly all the way
to 8 threads (107 GB/s WB, 85 GB/s WC) — not remotely link-bound on this
multi-channel platform at this thread count. This is a clean, direct
calibration target: gem5's CXL link-bandwidth ceiling should saturate
aggregate throughput around 4 threads' worth of demand, not 8.

## Leg 2: SW-prefetch distance x T0/NTA, HW prefetch off

**T0 hint**: dips *below* the no-prefetch baseline (d=0) at small distances
(d=1: 6.06 GB/s vs d=0's 9.57 GB/s on CXL), then climbs back up and exceeds
baseline by d=32-64. Mechanism: at small distances the prefetch is issued
too close to the demand load to hide the round-trip latency, so the core
pays prefetch-issue overhead without buying meaningful latency-hiding; once
distance is large enough to cover the latency, prefetch starts paying off.

**NTA hint**: also dips at small distances, but then **collapses at large
distances** (CXL: 5.60 GB/s at d=16 -> 3.29 GB/s at d=64; local: 8.93 -> 5.62)
— the opposite trend from T0 at the same distances. Mechanism: NTA lines
are hinted low-priority/first-evict; at large lead times, an NTA-prefetched
line can be evicted before the demand load actually needs it, wasting the
prefetch bandwidth *and* still paying the full round-trip latency on the
subsequent demand miss. This reproduces identically in shape on both CXL and
local DRAM (n=12, tight CIs on both), confirming it's a hint-semantics
effect, not CXL-specific.

**This is a clean, textbook-quality calibration target for gem5's prefetch
model**: T0 and NTA should NOT be modeled as "the same prefetch, different
cache-residency flag" if the model wants distance-sensitivity to reproduce
correctly -- they have qualitatively different bandwidth-vs-distance curves,
not just different endpoints.

## Leg 3: idle load latency (Little's-law anchor)

| memory | median cyc/load | latency (ns) |
|---|---:|---:|
| CXL | 312.8 | 164.63 |
| local | 160.6 | 84.55 |

**Ratio 1.947x** — closely matches the paper's own gem5 config table
(local/CXL latency 98/203 ns, ratio 2.07x, `Sec5_Evaluation.tex` `tab:gem5cfg`).
Absolute values differ somewhat from the paper's (higher local latency here,
84.55 vs 98ns is actually *lower*; CXL 164.63 vs 203ns also lower) but the
*ratio* — the thing that actually matters for a scaled gem5 model — is in
close agreement. Consistent with this campaign's broader pattern (AMD and
Intel alike): relative/ratio quantities reproduce tightly; some absolute
figures drift.

## Deliverable

`calibration_targets.csv` — 48 rows, columns `platform, leg, config,
threads, node, n, bw_gbps_median, bw_gbps_ci_lo, bw_gbps_ci_hi, latency_ns,
implied_mlp_lines` (Little's-law: `bw_gbps * latency_ns / 64`). Raw per-rep
data in `calibration_targets_raw_n12.csv` (576 rows) for anyone who wants to
recompute statistics differently.
