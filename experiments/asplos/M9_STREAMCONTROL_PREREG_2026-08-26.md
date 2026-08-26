# M9 pre-registration: does `tab:fused`'s penalty need the stream at all?

Written 2026-08-26 while M8 is still running (n=5 of 8 in hand) and **before any
M9 data exists**. Registered now precisely because M8's shape is already clear
and I do not want to choose this control after seeing M8's final numbers.

## What M8 has established so far

Restriction penalty R = median(`b4`)/median(`none`) on hot-table cyc/access, by
hot-table size, at a 4-of-20-way mask that holds **64 MiB** on mos181:

| table | fits 64 MiB? | R @ hr 0.5 | R @ hr 1.0 |
|--:|:--|--:|--:|
| 4 MiB | yes | 1.000 | 1.000 |
| 16 MiB | yes | 1.006 | 1.004 |
| 32 MiB | yes | 1.056 | 1.016 |
| 64 MiB | boundary | 1.170 | 1.097 |
| 128 MiB | **no** | 1.320 | 1.303 |
| **169.6 MiB** (`tab:fused`) | **no** | 1.303 | 1.244 |
| 256 MiB | **no** | 1.409 | 1.339 |

**Restricting the fused class costs nothing when its reused table fits inside the
mask.** The entire penalty appears as the table crosses the mask's capacity.

## The question M8 cannot answer

That result is compatible with two readings, and they have opposite consequences
for the paper.

- **H\_capacity.** The penalty is the table not fitting 64 MiB, full stop. It
  would appear with no stream present. Then `tab:fused`'s 1.43x is a statement
  about table geometry versus mask capacity and says **nothing** about streams,
  labels, or scope --- and §3's central exhibit is disqualified as evidence, even
  though its claim may still be true.
- **H\_stream.** The penalty is the table competing *with the stream* inside a
  64 MiB mask. Remove the stream's allocation and the table fits again. Then
  `tab:fused`'s evidence is about the stream after all, and the argument stands
  under a stated scope condition.

M8 cannot separate these because the stream is present in every M8 cell.

## Why the control is flush-behind and not `--no-stream`

`--no-stream` is unusable here and I want the reason on the record. Reading
`cxl_join_bench.cpp:1560-1569`: it rounds the fact array down to
`min(n, 65536)` entries **and** reallocates it on `hot_node`. The stream's
footprint collapses from 1 GiB on CXL to ~1 MiB on local DRAM. That is the same
footprint-collapse confound that voided M1b and M2, and using it here would
manufacture H\_stream.

The honest control is `--flush-distance` (M3's flush-behind proxy, committed in
`cxl_join_bench.cpp`): the stream still reads all 1 GiB from CXL node 2 through
the same loop, but each line is `clflushopt`-ed behind the read, so it does not
accumulate in the mask. Footprint, node, loop, and byte count are unchanged; only
the stream's *residency* changes. That is exactly the variable in question.

Its known cost: the proxy itself costs the tenant 14--19% in absolute cyc/access
(M3). That cost lands on both the `none` and `b4` arms at the same table size, so
the comparison is made **within** a stream condition and never across one.

## Design

- Fixed: `--mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g
  --cpu-list 32-47 --morsel 1m --warmups 2 --reps 1 --threads 16`.
- `cat` in {`none` (torn down, 20 ways), `b4` (`setup_b 4 32-47`, `L3:0=f`)}.
- `stream` in {`retain` (`--flush-distance 0`, dispatching to the untouched
  `join_range`), `flush` (`--flush-distance 262144`)}.
- `table` in {33554432 (32 MiB, **fits** the mask), 177838489 (169.6 MiB,
  `tab:fused`'s value, **does not fit**)}.
- `--hit-rate` in {0.5, 1.0}.
- 16 cells, n=10, 160 runs. Interleaved and rotated per rep, schemata captured
  per record, per-record JSON validation, A6.19 refusal to append, resctrl torn
  down on every exit path.

The 32 MiB row is the internal positive control: R must stay near 1.0 there in
**both** stream conditions, since a table that fits the mask has nothing to lose.

## Instrument check (registered, action on miss stated)

The cell `none`/`retain`/169.6 MiB/hr 0.5 is `tab:fused`'s unrestricted fused arm,
M7's `none`/0.5 cell, and M8's instrument cell. It must land within **+/-5% of
M7's 89.326 cyc/access, i.e. [84.86, 93.79]**.

- **On miss:** M9 is void for comparison against `tab:fused`, M7, or M8. The
  within-M9 2x2 may still be reported as internally controlled.

## Registered predictions

Let R(table, stream, hr) = median(`b4`)/median(`none`).

- **P1 (H\_capacity).** R(169.6, flush, hr) >= 1.20 at both hit rates --- the
  penalty survives with a non-allocating stream.
- **P2 (H\_stream).** R(169.6, flush, hr) <= 1.10 at both hit rates while
  R(169.6, retain, hr) >= 1.20 --- the penalty needs the stream's residency.
- **P3 (control).** R(32, retain) and R(32, flush) are both <= 1.10 at both hit
  rates.
- **P4.** The flush proxy raises absolute cyc/access by 10--25% in the `none`/
  169.6 MiB cell, reproducing M3's 14--19% band at this table size.

P1 and P2 are mutually exclusive. An intermediate outcome
(1.10 < R(169.6, flush) < 1.20) is possible and will be reported as partial
attribution with both components sized, not rounded to whichever reading is
more convenient.

## Registered consequences

- **P1 holds (H\_capacity).** `tab:fused`'s 1.43x is withdrawn as evidence for
  label scope. §3's fused exhibit must be rebuilt around a table that fits the
  mask, where any surviving penalty is attributable to the stream, or the
  monotone way sweep must be presented as a table-geometry result. Sec1
  contribution (2), already rewritten once today, narrows again: the surviving
  claim would be expressibility supported by the taxonomy, with **no** hardware
  exhibit sizing it on Intel.
- **P2 holds (H\_stream).** `tab:fused`'s evidence stands, scoped explicitly to
  "the tenant's reused structure is larger than the mask its stream needs" --- a
  condition the paper must state, because M8 shows the penalty is zero below it.
  The hit-rate caveat is removed as wrong (M7) and replaced by this table-size
  scope condition.
- **Intermediate.** Report both components. `tab:fused` may not present 1.43x
  without the table size and the capacity share stated alongside it.

## What this cannot show

Intel EMR only, one mask width (4 of 20), one fact size (1 GiB), no victim. The
label is represented by a software flush proxy with a known 14--19% cost, not by
the memory type; a zero-cost type would change the absolute numbers but not which
component the ratio attributes. Nothing here bears on M6's neighbour result or on
AMD, where the deciding cell remains unrun and the host unreachable for four days.
