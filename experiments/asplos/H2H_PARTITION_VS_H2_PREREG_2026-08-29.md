# Pre-registration: way partitioning vs H2, same model, same workload, both sides measured

Registered **before** the run. This is the paper's central comparison and it has
never been made in one apparatus.

## Why this experiment exists

The paper's thesis is a **wedge**: partitioning protects the neighbour but charges
the streaming tenant; a page-scoped label protects the neighbour and charges the
tenant nothing. Today those two halves come from **different platforms**:

| half | source | platform |
|---|---|---|
| partitioning costs the tenant 15.0--16.9% | E1, E4 | Intel silicon |
| H2 costs the tenant +0.00% per instruction (throughput $+$10.4%) | `H2_TENANT_COST_2026-08-29.md` | gem5 |

A referee is entitled to say the comparison is unsupported: two mechanisms, two
platforms, two workloads. **This experiment puts both mechanisms in one model, on
one workload, with one variable changed, and measures both the neighbour's
recovery and the tenant's own cost for each.**

## Apparatus

Run in `DutyFree/gem5` at the way-partitioning tip, **not** `~/DutyFree-Gem5`,
because only this tree has the partitioning implementation. Two defaults changed
between the W1 apparatus (`356e7b7d0e`) and this tip, and both are pinned back:

| knob | W1 value | tip default | pinned to |
|---|--:|--:|--:|
| `HNF_FWD_UNIQUE` | 0 | **1** | **0** |
| `SEQ_OUT` | 1024 | **32** | **1024** |

Everything else between the two commits is the way-partitioning work, which
**check 1 proved bit-identical to the pre-change binary when no mask is set**
(1,869 counters, 1,864 identical, the five differing ones host wall-clock).

Workload is W1's, absolute paths: victim `dutyfree/victim 2650 3000000` on cpu0,
aggressor `dutyfree/aggressor 16.0 [stream]` on cpu1. Infinite SF
(`HNF_SF_FINITE=0`), `HNF_DMT=0`, `RUBY_RANDOMIZATION=1`, seeds 1--3, HNF
5 MiB/20-way, **LRU** throughout (the reporting configuration, and mandatory on a
masked cache since `CacheMemory::init()` refuses TreePLRU).

### Requestor identity, read from the artifact

Per-requestor masks are the CAT/MPAM shape and need the requestor NodeID. Read
from `config.ini` rather than inferred --- the assignment is **not**
creation-order-per-CPU, which a guess would have got wrong:

| controller | NodeID |
|---|--:|
| cpu0.l1i / cpu0.l1d | 0 / 1 |
| cpu1.l1i / cpu1.l1d | 2 / 3 |
| **cpu0.l2** (victim's requestor at the HNF) | **4** |
| **cpu1.l2** (stream's requestor at the HNF) | **5** |
| hnf | 6 |

## Arms: 5 x 3 seeds = 15 runs

| arm | mechanism | `HNF_REQ_MASKS` | declaration |
|---|---|---|---|
| `qui` | victim alone (`dummy` on cpu1) | --- | --- |
| `wb` | no protection | --- | no |
| `h2` | **STREAMING** | --- | **yes** |
| `cat4` | **partitioning, tenant in 4/20 ways** | `5:0xf` | no |
| `cat10` | **partitioning, tenant in 10/20 ways** | `5:0x3ff` | no |

`cat4` and `cat10` confine **only** the stream's requestor; the victim keeps all
20 ways, exactly as the silicon arms did (`setup_c`). Two splits because E1 found
partitioning's protection is flat across splits while its cost is not --- one
split could be dismissed as a lucky point.

## Metrics --- both sides, which is the point

**Neighbour:** `cyc/access = system.cpu0.numCycles / 3e6`; tax = arm/qui;
recovery `R = (tax_wb - tax_arm)/(tax_wb - 1)`.

**Tenant:** `system.cpu1` total L2 misses per instruction (demand **+** prefetch,
normalised by IPC) and throughput (total L2 misses per cycle). Per-instruction is
the primary tenant metric: it is invariant to how long the tenant was allowed to
run, and it is the metric on which H2 reads **+0.00%**. Demand-only miss rates are
**not** used --- that error is what made H2's tenant cost look like $-$3.9% when it
is a gain.

## Registered predictions and thresholds

**P1 --- partitioning protects.** `R(cat4)` and `R(cat10)` both $\ge$ **80%**.
E1 found way partitioning fully protects on silicon (H$\approx$0.99); if it does
not protect in this model, the model cannot host the comparison at all and the
experiment is void rather than informative.

**P2 --- partitioning charges the tenant, H2 does not.** The registered wedge:

    W = (tenant misses/instruction, cat) - (tenant misses/instruction, h2)

with `W >= 5%` at **both** splits. This is the paper's claim in one number. If
`W < 5%`, **the wedge does not reproduce in the model** and the paper's central
argument rests on silicon alone --- which must then be said plainly.

**P3 --- H2's tenant cost stays at zero.** `abs(tenant misses/instruction, h2)`
$\le$ **1%** against `wb`. Registered as a reproduction check on
`H2_TENANT_COST_2026-08-29.md` in a tree whose defaults differ; a miss means that
result does not survive `HNF_FWD_UNIQUE=0`/`SEQ_OUT=1024` in this tree and is
apparatus-specific.

**P4 --- the mask is enforced.** Zero HNF allocations in ways outside the union of
the configured masks, from `m_allocsByWay`. A structural check: without it a
partitioning arm that silently did nothing would look like a free lunch. **This is
the check that the L1D verification exists to make trustworthy, applied for the
first time at the LLC.**

### Resolution

Prior seed-level sd on `cyc/access` is $\le$0.05 (CoV $\le$0.1%), giving
$\approx$0.1 pp on `R` at n=3, so an 80% threshold is $\sim$200 sd clear.
Tenant misses/instruction reproduced to **+0.00%** across two policies in the
previous batch, so a 5% wedge and a 1% null are both far above resolution.
Thresholds are round numbers chosen for interpretability, not tuned to the
instrument's edge.

## Directions I am **not** predicting

Whether partitioning's tenant charge in the model matches silicon's 15--17%. The
model has no congestion latency (`SimpleMemory`, `latency_var = 0`), so its
charge could differ in either direction, and a registered guess here would be
rationalisable afterwards either way. **The registered claim is only that the
charge is positive and $\ge$5%, not that it matches silicon.**

## Liveness assertions

1. All 15 runs reach `Exiting @ tick`; dead runs are reported, not dropped.
2. Each arm's identity is read from its own `config.ini` (S5.1): HNF replacement
   policy, `requestor_masks`, presence of the streaming declaration, `HNF_H3`,
   SF geometry, `fwd_unique_on_readshared=false`, sequencer
   `max_outstanding_requests=1024`.
3. `qui` must show `cpu1.numCycles = 0`.
4. The `cat` arms must show a **non-empty** `requestor_masks` and the `wb`/`h2`
   arms an **empty** one. An unmasked "partitioned" arm is the vacuous pass this
   campaign has already produced once.
5. Instrument check: `wb` and `h2` should land within 0.5% of the W1 values
   re-measured under LRU (45.2764 and 35.1905). A miss does **not** void the
   internal comparison; it voids the link to the W1 numbers, and is reported.
