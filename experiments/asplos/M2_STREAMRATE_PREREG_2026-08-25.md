# M2 pre-registration: does the stream's contribution grow with its rate?

Written before measurement. M1b found that removing a fused tenant's entire
256 MiB CXL stream changed its neighbour's cost by **0.11%** — at the stream rate
F naturally produces (~5.4 GB/s at 16 workers, because F's own probe paces it).

**The open question this closes:** is 0.11% a property of *streams*, or only of
*slow* streams? If the stream's contribution grows with rate, then a faster
engine (DuckDB's vectorised probe, say) could push it into relevance and the
mechanism has a configuration after all. If it stays ~0 at double the rate, the
stream is irrelevant to neighbour harm across the range we can produce, and that
is the end of the line for a stream-scoped label.

**The lever, and why it is clean.** `--hit-rate 1.0` makes every probe a hit, so
F's probe costs 44.0 cyc/access instead of 88.3 — it runs ~2× faster and
therefore *streams ~2× faster* — with the same code, the same loop, the same
256 MiB fact array and the same 256 MiB table. Nothing about the stream itself
changes except how fast F consumes it.

## Arms

Victim `pointer_chase`, 170 MB, cpu8 (unchanged from M1b). F = 16 workers on
32–47, fact 256 MiB on CXL node 2, hot table 256 MiB. n=6, order rotated.

| arm | F's hit rate | F's stream | purpose |
|---|---|---|---|
| **V** | — | — | baseline |
| **V+F_hr05** | 0.5 | on | M1b's `V+F_big`, reproduced |
| **V+F_hr10** | 1.0 | on | F streams ~2× faster |
| **V+F_hr10_ns** | 1.0 | **off** (`--no-stream`) | isolates the stream *at the higher rate* |

## Pre-registered readings

The quantity is the stream's contribution at each rate, as a baseline-free ratio:

    contribution(hr) = 1 - [ V+F_<hr>_nostream / V+F_<hr> ]

M1b measured contribution(0.5) = 1 − 1.0011 = **−0.11%** (i.e. nothing).

| outcome | verdict |
|---|---|
| contribution(1.0) ≤ 2% | **the stream is irrelevant at double the rate too.** A stream-scoped label has no configuration in this family, and the DuckDB spike is not worth running — a faster engine would only move further along an axis that does not matter. |
| contribution(1.0) ≥ 10% | the stream matters once fast enough; the mechanism has a rate-conditional case, and the DuckDB spike becomes the priority |
| 2–10% | report the trend; claim a rate dependence only if it is monotone and outside noise |

**Recorded per arm to verify the lever worked:** F's own `active_cycles_per_access`
and `stream_bandwidth_gbps`. If `hr=1.0` does not actually raise F's stream rate
materially, the arm is void and the reading is not attempted.

**Caveat registered in advance:** `hr=1.0` also changes F's *probe* behaviour —
every probe hits, so no miss-chain walks. That makes F cheaper per tuple in ways
unrelated to streaming, so `V+F_hr10` is not directly comparable to `V+F_hr05` in
absolute harm. **Only the within-rate ratio is interpreted**, which is why the
`_ns` arm exists at the same hit rate.
