# Pre-registration: the discriminating head-to-head --- partitioning vs H2 against a tenant that streams AND computes

Registered **before** the run. This is the experiment the paper's central claim
needs and has never had.

## Why the first head-to-head could not decide

`H2H_PARTITION_VS_H2_OUTCOME_2026-08-29.md` put both mechanisms in one model and
found them **equivalent**: partitioning recovered 89.47%/88.62% against H2's
88.51%, and partitioning charged the tenant **0.55%** against H2's `-10.4%`
(a gain). The registered wedge failed at 0.00%.

The reason is not a modelling artifact. **The tenant was a pure stream.**
Confining a no-reuse stream to 4 of 20 ways costs it nothing, because it had no
residency to lose --- and silicon agrees: `W5.3` measured Intel CAT at **0.7%**
against a table-less streamer. E1/E4's **15--17%** came from a *fused* tenant
whose own hot table the mask destroyed.

A way mask is indexed by **agent**. A page-scoped label is indexed by
**address**. When the stream and the reuse structure belong to the same agent,
only the label can separate them. **That difference is the paper's thesis and it
is structurally invisible to a pure stream.**

## The workload

`testcase/dutyfree/fused.c`, new, 95 lines, built with the aggressor's flags.
One binary for every arm, gated on `argv[3]`, so no arm differs in code.

    fused <stream_mb> <table_mb> [stream]

- streams `arr` (16 MB), read-only after init;
- probes a hot table `tbl` (3 MB) once per 128 B of stream, index
  multiply-scrambled so it is spread rather than a linear walk;
- declares **only** `arr`. The table is written at init and only read after, and
  is **never** declared: it is the tenant's own resident state.

Sizing against the real geometry, not round numbers: the table is **3 MB > the
2 MiB private L2**, so ~1 MB of it must live in the LLC to stay hot; the victim's
chase is 2650 KiB, so table spill + victim is about 3.6 MB, **< 5 MiB LLC** ---
both fit once the stream stops allocating; under a 4/20 mask the tenant's entire
LLC share is **1 MiB** and the stream shares it, so the table's spill is evicted
continuously.

### Verified before registering

- **Gating works.** `streamingAccesses` = **0** on both cores without the flag;
  **91,305** on the tenant's dTLB with it, **0** on the victim's.
- **Scope is provably clean.** From the symbol table, `tbl` occupies
  `[0x4bcac0, 0x44bcac0)` and `arr` starts at `0x44bcac0`; the declaration covers
  `[arr, arr+16 MB)`, and the table's used region sits ~64 MB below it. **The
  table cannot be declared**, by address arithmetic rather than by assumption.
- Builds and runs correctly natively and in gem5; both smoke arms exited normally.

## Arms and apparatus

Identical to `H2H_PARTITION_VS_H2_PREREG` except the tenant binary and its args.
5 arms x 3 seeds = **15 runs**. `HNF_FWD_UNIQUE=0`, `SEQ_OUT=1024` (pinned to the
W1 apparatus), infinite SF, `HNF_DMT=0`, LRU at the HNF, seeds 1--3.

| arm | tenant | `HNF_REQ_MASKS` | declaration |
|---|---|---|---|
| `qui` | `dummy` | --- | --- |
| `wb` | fused | --- | no |
| `h2` | fused | --- | **yes** |
| `cat4` | fused | `5:0xf` | no |
| `cat10` | fused | `5:0x3ff` | no |

Masks confine only the stream's requestor (NodeID 5 = cpu1.l2, read from
`config.ini`); the victim keeps all 20 ways, as in the silicon `setup_c` arms.

## Metrics --- corrected from the first attempt

Tenant cost is **throughput**: total L2 misses (demand **+** prefetch) per cycle.

The first head-to-head registered misses **per instruction** as primary. That was
wrong and the run proved it: the value was `0.16668` in **every** arm, identical
to five decimals, because it is invariant to cache policy for a stream that
re-reads nothing. It detects **re-fetch** cost (it caught H3 at +163%) and is
blind to **confinement** cost. Per-instruction is retained as a **secondary**
diagnostic --- for a fused tenant it should now move, because a destroyed table
*does* force re-fetching --- but it decides nothing.

Neighbour: `cyc/access`, tax vs `qui`, recovery
`R = (tax_wb - tax_arm)/(tax_wb - 1)`.

## Registered predictions

**P1 --- both mechanisms still protect.** `R` >= 80% for `h2`, `cat4`, `cat10`.
If partitioning stops protecting, the comparison is void, not informative.

**P2 --- THE WEDGE.** Tenant throughput cost relative to `wb`:

- `cost(cat4)` >= **5%**, and
- `cost(cat4)` > `cost(cat10)` (a tighter mask hurts more), and
- `cost(h2)` <= **1%**.

**All three must hold.** This is the paper's central claim stated so it can fail.
**If `cost(cat4)` < 5%, the wedge does not exist in the model even with a tenant
that has reuse to lose, and the paper's unconditional claim in Sec1 is not
supported by our own simulator.** That outcome must be reported as such and the
claim scoped to silicon.

**P3 --- the mechanism, not the magnitude.** I do **not** predict that the model
reproduces silicon's 15--17%. `SimpleMemory` has no congestion latency and the
table is 3 MB rather than 256 MB, so the magnitude may differ in either
direction. Registering a magnitude would be rationalisable afterwards; the
registered claim is the **sign and the ordering**.

**P4 --- mask enforced**, per-way HNF allocations concentrated inside the mask,
as in the pure-stream run (346x at `cat4`).

### Resolution

Tenant throughput sd was <= 0.010 on 27--30 misses/kcyc at n=3 (CoV <= 0.04%),
so a 5% threshold is far above noise. `R` resolves to about 0.1 pp.

## Liveness assertions

1. All 15 runs reach `Exiting @ tick`; dead runs reported, not dropped.
2. Arm identity from each run's own `config.ini`: HNF policy `LRURP`,
   `requestor_masks` non-empty **only** on `cat` arms, declaration **only** on
   `h2`, `fwd_unique_on_readshared=false`, `max_outstanding_requests=1024`.
3. `qui` shows `cpu1.numCycles = 0`.
4. **The tenant must actually use its table.** `h2` and `wb` must show a non-zero
   tenant L2 miss rate, and `streamingAccesses > 0` on `h2` only. A fused tenant
   whose table fell out of the working set would silently reduce to the pure
   stream and reproduce the previous null --- the vacuous-pass failure mode this
   campaign has already committed once.
