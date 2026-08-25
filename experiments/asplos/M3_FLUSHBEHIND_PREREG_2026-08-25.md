# M3 pre-registration: does *non-allocation* remove the neighbour's harm?

Written before measurement. **This is the experiment the project has been trying
to reach for three days.**

## The question, and why M2 could not answer it

M2 showed that a fused tenant's stream, on its own, degrades a latency-critical
neighbour **2.77×**, and that removing the stream returns the neighbour to
**0.99×**. But M2 removed the **bytes**. H2 does not remove bytes — it reads every
byte at full prefetch aggressiveness and merely declines to *retain* them in the
shared cache.

So M2 measured an **upper bound** on H2, not H2. The two possibilities it cannot
separate:

- the harm is **cache residency** — the stream's lines evicting the neighbour's.
  Then declining to retain them fixes it, and H2 is the right mechanism.
- the harm is **bytes in flight** — memory-system and fabric occupancy on the way
  in. Then it does not matter whether the lines are kept, no admission-control
  mechanism helps, and STREAMING has no configuration.

## The instrument

`--flush-distance D` (added today, additive: `D = 0` dispatches to the untouched
`join_range`, so every prior number stands). With `D > 0` the fused loop issues
`clflushopt` on fact lines more than `D` bytes behind its read pointer, batching
`sfence` every 64 flushes — mirroring
`benchmarks/bench/aggressor/stream_wb_flushbehind.c`, the same design that
produced the paper's 76.3% AMD recovery figure.

**It reads every byte and keeps almost none.** Residency is bounded to ~D. That
is a silicon proxy for H2 — coherent, no exotic memory type, no lost kernel
module.

Verified engaged before registering: at 64 MiB fact, F's cost rises 58.32 → 68.22
cyc/access and its stream rate falls 2.024 → 1.733 GB/s. Flushing is real and it
costs the streamer, in the same direction as the published AMD arm's 31.34%.

## Arms

All at **hit rate 1.0**, because M2 established that at 0.5 the table's
miss-scatter independently saturates the victim and masks everything. Victim
`pointer_chase` 170 MB on cpu8; F = 16 workers on 32–47, fact 256 MiB on CXL
node 2, hot table 256 MiB. n=6, order rotated.

| arm | F's stream | purpose |
|---|---|---|
| **V** | — | baseline |
| **V+F_alloc** | read + **allocate** (`D=0`) | M2's `V+F_hr10`, reproduced |
| **V+F_fb** | read + **flush behind** (`D=256 KiB`) | **the arm** — H2 proxy |
| **V+F_ns** | not read (`--no-stream`) | M2's floor |

## Pre-registered reading

    recovery = (harm_alloc - harm_fb) / (harm_alloc - harm_ns)

the fraction of the stream-attributable harm that non-allocation removes.

| outcome | verdict |
|---|---|
| **recovery ≥ 70%** | **the harm is cache residency, and H2 removes it.** STREAMING has a measured configuration where it uniquely helps: no context-scoped label can express it (one thread, two access classes) and the shipped alternatives were shown to charge F's own reuse structure. This would be the paper's central result. |
| **recovery ≤ 20%** | the harm is bytes in flight, not residency. **No admission-control mechanism helps**, H2 included, and the mechanism has no configuration. Reported as the headline. |
| 20–70% | partial; report the fraction and claim only that. |

For reference, the published AMD flush-behind arm recovered **76.3% [76.1, 76.4]**
of a *cross-process* tax. This is a different configuration (fused tenant,
neighbour victim, Intel), so agreement is informative but not required.

**Also recorded, because it is the price:** F's own cyc/access and stream rate in
the `_fb` arm versus `_alloc`. Flush-behind is per-core work the streamer pays;
H2 in hardware would not. That gap is precisely the argument for putting the
policy in the memory type rather than in software, so it is reported alongside
the recovery whatever the recovery turns out to be.

## Registered caveats

- `clflushopt` is a proxy, not H2. It evicts lines already allocated, rather than
  never allocating them; the transient residency is ~D bytes. A hardware H2 would
  do strictly better, so a positive result here is a **lower bound** on H2.
- Everything is mos181 (Intel EMR, 320 MiB LLC). AMD is unreachable.
- The victim metric saturates (78 → ~209, little in between), so a partial
  recovery may read as all-or-nothing. If `recovery` lands mid-range, that is a
  reason to sweep `D` before interpreting it, not to interpolate.

---

# Addendum 1 — the registered sweep, specified before it runs

M3 returned **recovery = 27.4%**, inside the 20–70% band, whose registered
consequence is *"sweep the flush distance before interpreting, not
interpolate."* This specifies that sweep.

**The question it separates:** is 27.4% low because the proxy under-flushes at
16 threads and ~8 GB/s (in which case hardware H2 does better and 27.4% is a
loose lower bound), or because most of the harm is bytes in flight rather than
residency (in which case 27.4% is the residency share and the rest is
unreachable)?

**Arms.** Same victim and same F as M3, hit rate 1.0. Flush distance swept over a
32× range plus both anchors:

`V` · `V+F_alloc` (D=0) · `V+F_fb32k` · `V+F_fb64k` · `V+F_fb256k` ·
`V+F_fb1m` · `V+F_ns`

Seven arms, **n=7** so that rotation puts each arm in each position exactly once.

**Registered readings.**

| outcome | verdict |
|---|---|
| recovery **rises monotonically** as D shrinks, and exceeds **60%** at 32 KiB | the proxy was leaky; residency is the dominant mechanism and hardware H2 would recover most of the harm. 27.4% at 256 KiB is a lower bound. |
| recovery **flat within ±10 points** across 32 KiB–1 MiB | 27.4% is the real residency share. **~73% of the harm is bytes in flight and unreachable by any admission-control mechanism**, H2 included. |
| rises but stays below 60% at 32 KiB | residency matters more than 27.4% suggests but cannot account for the majority; report the curve and the ceiling it implies. |

**Also recorded:** F's own cost and stream rate at each D, since the proxy's price
grows as D shrinks and the trade-off is part of the result.

**Caveat carried forward:** at 16 threads a 32 KiB distance means the flush
pointer trails the read pointer by only 512 cache lines per thread, so
`clflushopt` back-pressure may begin to distort F's own behaviour. If F's stream
rate collapses at the smallest D, that arm reports the proxy's limit rather than
the mechanism's.
