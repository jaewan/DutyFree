# Pre-registration: is the 36.5% wedge a point or a regime?

Registered **before** the run.

## Why

`H2H_FUSED_OUTCOME_2026-08-29.md` established the wedge --- partitioning charges
the fused tenant **36.53%** at a 4/20 mask while the label charges **-1.16%**, at
equal neighbour protection. That number rests on **one configuration**: a 3 MB
table and a 16 MB stream.

This project has already been burned by single-point claims, and `E1`'s
contribution was mapping a frontier rather than quoting a point. A referee will
ask whether 36.5% is a knife edge. **A headline that cannot be shown as a curve
should not be a headline.**

## Design

Table sizes **1, 2, 4, 6 MB** x arms **`wb`, `h2`, `cat4`** x seeds 1--3 = **36
runs**. The **3 MB** point is already measured at n=3 and is not re-run; `qui`
does not involve the tenant and has been bit-identical (33.8814) in every batch
today, so it is reused as the denominator. Five table sizes in total.

Apparatus identical to the fused head-to-head: `HNF_FWD_UNIQUE=0`,
`SEQ_OUT=1024`, infinite SF, `HNF_DMT=0`, LRU at the HNF, stream fixed at 16 MB,
masks confining only the stream's requestor (NodeID 5).

## The mechanism, stated correctly

A naive reading of the geometry says the table's LLC spill (`table - 2 MiB L2`)
"fits" the tenant's 1 MiB share at 3 MB, and therefore should not be hurt. **That
reading is wrong, and the measured 36.53% is why.** The tenant's 4 ways are not a
private reserve for the table: **the 16 MB stream flows through the same 4 ways
continuously**, so whatever the table spills into that partition is evicted
almost immediately. Confinement hurts when the table needs the LLC *at all*, not
when its spill exceeds the partition.

That gives the shape to expect: cost is small while the table is L2-resident, and
turns on once the table needs the LLC.

## Registered predictions

**P1 --- the wedge has an onset.** `cost(cat4)` at a **1 MB** table $\le$ **10%**,
and `cost(cat4)` at **4 MB** $\ge$ **25%**. A 1 MB table is L2-resident, so the
tenant has nothing in the LLC for a mask to take; a 4 MB table cannot be.

**P2 --- the label is free at every table size.** `abs(cost(h2))` $\le$ **3%** at
**all five** sizes. This is the robustness claim that matters: if STREAMING's zero
cost depended on the tenant's table size, the mechanism would be a coincidence of
one configuration rather than a property.

**P3 --- protection holds throughout.** `R` $\ge$ 80% for `h2` and `cat4` at every
size. If protection collapses somewhere, the cost figures at that size are not
comparable and are reported as void.

**Explicitly NOT predicted --- the shape at the top end.** At 6 MB the table
exceeds the entire 5 MiB LLC, so it thrashes even unconfined. Two mechanisms then
act in opposite directions: more table to lose, but less left to lose it from.
`cost(cat4)` at 6 MB may rise or fall against 4 MB. **The curve is the result;
registering its top end would be rationalisable either way.**

## Resolution

Tenant throughput sd was $\le$0.010 on 30--48 misses/kcyc at n=3 (CoV $\le$0.04%),
so 10% and 25% thresholds are orders of magnitude above noise.

## Liveness assertions

1. All 36 runs reach `Exiting @ tick`; dead runs reported, not dropped.
2. Arm identity from each run's own `config.ini`: `LRURP` at the HNF,
   `requestor_masks` non-empty **only** on `cat4`, declaration **only** on `h2`,
   `fwd_unique_on_readshared=false`, `max_outstanding_requests=1024`.
3. **Each run's table size is read back from its own `cmd=` line**, not assumed
   from the output directory name. A sweep that silently ran one size four times
   would produce a flat curve and look like a finding.
4. Tenant L2 misses non-zero in every arm; `streamingAccesses` > 0 on `h2` only.
