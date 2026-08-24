# T4 gate outcome: not memory-side — and the fused "tax" is not the stream

Pre-registration `T4_SCOPING_PREREG_2026-08-24.md` + Addenda 1–2, all committed
before their respective runs (`8e147ef`, `82b0af1`, `717e4c6`). Runners
`run_t4_tma.sh` / `run_t4_tma_1b.sh`. Data
`benchmarks/e2e/hash_join/artifacts/t4_tma{,_1b}/`, 24/24 records each, stderr
archived. mos181, 1 core (cpu32), n=12 per arm, order-balanced.

## Verdict

> **The fused same-thread tax is NOT memory-side. The original T4 occupancy fit
> is CANCELLED, not deferred — no memory-side mechanism is indicated: not H2,
> not a staging buffer, not MSHR QoS.**
>
> **And phase 1b says something stronger: holding the fused loop fixed, adding a
> 256 MiB CXL stream costs ≈0 cycles per access.** The published 1.47× fused tax
> is dominated by the difference between the `hot-probe` loop and the `morsel`
> loop — not by the stream's interference.

Instrument falsifier passed in both phases: L1 slots sum to 0.9998–1.0002 and
every counter read at **100% enabled** (no multiplexing).

## Phase 1 — the registered gate (Q = `hot-probe`, A = `morsel`)

| arm | n | cyc/acc | frontend | bad-spec | retiring | backend | memory | core |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Q | 12 | 59.761 | 10.13% | 28.34% | 14.87% | 46.64% | 21.13% | 25.51% |
| A | 12 | 90.536 | 13.27% | 34.62% | 15.05% | 37.06% | 19.37% | 17.68% |

Registered differential (A2) over Δ = **30.775 cyc/access**:

| category | Δcyc | share of Δ |
|---|--:|--:|
| bad-speculation | +14.411 | **46.8%** |
| frontend-bound | +5.955 | 19.4% |
| **memory-bound** | +4.904 | **15.9%** |
| retiring | +4.741 | 15.4% |
| core-bound | +0.758 | 2.5% |

**Memory-bound share = 15.9%, inside the registered ≤30% band.** Gate: not
memory-side.

## Phase 1b — the same-code-path control, and it governs

Addendum 2 registered this because phase 1's arms are *different loops*, and a
TMA differential across different code paths conflates interference with
code-path difference.

| arm | n | cyc/acc | frontend | bad-spec | retiring | backend | memory | core |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| Qs (`morsel --no-stream`) | 12 | 92.602 | 18.45% | 36.88% | 11.47% | 33.22% | 15.88% | 17.33% |
| A (`morsel`) | 12 | 91.808 | 12.06% | 34.92% | 14.77% | 38.27% | 20.42% | 17.85% |

**Δ = 91.808 − 92.602 = −0.795 cyc/access.** Adding the stream makes the fused
loop *very slightly faster*.

**The registered share arithmetic is undefined here** and its output must not be
quoted: A2's formula divides by Δ, and at Δ ≈ 0 it produces meaningless
magnitudes (the analyzer prints −508.8% for memory and +756.9% for frontend).
Reported as undefined, not as numbers. What *is* meaningful are the absolute
per-access cycle changes: memory-bound **+4.04**, frontend-bound **−6.02**,
bad-spec **−2.10**, retiring **+2.94**, core-bound **+0.34**. The stream shifts
where the bottleneck sits and nets out slightly negative.

### Two registered readings fire

**1. Phase 1's bad-speculation finding is WITHDRAWN.** Addendum 2 registered:
*"bad-spec share falls below 15% in 1b ⇒ phase 1's bad-spec term was a code-path
artifact and must be withdrawn."* In 1b bad-spec's absolute contribution is
**negative** (−2.10 cyc). So phase 1's 46.8% was an artifact of pairing
`hot-probe` against `morsel`. **It must not appear anywhere.** This is the
amendment the panel added earning its keep on its first use.

**2. A5's OoO-overlap anomaly is re-verified, at n=12 under order balancing.**
`cyc(Qs) = 92.602 > cyc(A) = 91.808`. Same sign as the 2026-07-29 incidental
observation (91.5 vs 84.4), now with the position confound controlled. The
registered implication applies: **the fused baseline is partly latency-hidden by
the interleaving**, so any "net tax" sits atop a gross displacement partly offset
by an overlap benefit — which constrains what "recovery" can even mean.

## What this does to the fused case

Both phases agree on the gate, and 1b sharpens it into a causal statement about
the *stream*:

- shared-LLC residency: **0.00%** strict / ≤31% generous (2026-07-29)
- bandwidth-matched remote-socket queueing: **≈0** (2026-07-29)
- stream-side TLB / page walks: **excluded**, walks are the victim's (T3)
- memory-bound share of the tax: **15.9%** (phase 1)
- **the stream's own marginal cost, fused loop held fixed: ≈0, sign negative** (1b)

The exclusion chain is now five links. The honest statement: **the fused
same-thread cost is real and large, `tab:fused` shows every deployed control makes
it worse at 7–17 SE, and essentially none of it is attributable to the stream's
memory behaviour.** L2 (context scope cannot name the two classes) is an
*expressibility* claim and is untouched. What is undercut is the fused case's role
as *the interference a memory-type mechanism would remove* — there is nothing
there for H2, a buffer, or MSHR QoS to remove.

## What this may NOT yet carry

`--no-stream` is **not a perfect same-code-path control**, and the strong causal
sentence must wait for A4. Read at `cxl_join_bench.cpp:1518-1535,1591`: it shares
`run_morsel`'s driver and morsel dispatch with A, but it calls
**`join_range_local`** rather than `join_range`, and it works on a **1 MiB
node-0** array (`local_n` capped at 65536 entries, `alloc_node = hot_node`)
instead of the 256 MiB CXL array. So Δ(A − Qs) mixes "no stream" with "different
inner join, local, smaller".

That makes 1b strong evidence and not proof — exactly why A4 registered the two
dilution interventions as **required** before any strong negative claim reaches
the paper. They remain the gating work:
- *instruction dilution*: replace the stream's loads with an equal-count
  instruction stream touching no memory. Tax persists ⇒ execution-level, causally.
- *memory dilution*: same bytes, fewer instructions. Tax persists ⇒ memory-side.

Both need new kernel code and are not built.

## Phase 2 is not needed

A3's sub-bucket fork call was registered as conditional on phase 1 returning
≥30% memory-bound. It returned 15.9%. **Phase 2 is not run**, and the
buffer-vs-MSHR-QoS fork is not adjudicated because nothing indicates a
memory-side mechanism to adjudicate between.

## Still open on this campaign

A6's SMT-sibling split (registered to run **regardless** of the gate; cpu32's
sibling is cpu160), A4's two dilution arms, and — on the AMD side, blocked all
session by broker refusing SSH — the reconstructed `/dev/cxl_wc` module (written
and verified to compile, `4fb2cd3`) and the RocksDB re-earn.
