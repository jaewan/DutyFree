# Pre-registration: where does H2's protection collapse, and which mechanism explains it?

Registered **before** the run.

## The question this answers

`FUSED_TABLESWEEP_OUTCOME_2026-08-29.md` found H2's recovery falls
**90.6% -> 51.9%** between a 2 MB and a 4 MB tenant table, while partitioning's
stays flat at 85--89%. The sweep could not say *where* the collapse happens,
because `fused.c` quantized the table to powers of two. That restriction is now
removed (multiply-shift index, `realized == requested` verified at 1/2/2.5/3/3.5/
4/6/8 MB, probe distribution uniform to 3.3% across 16 bins).

**The knee is the boundary of the paper's claim.** Left of it, a page-scoped
label and a way mask protect equally and only the label is free. Right of it, the
label stops protecting and only the mask works. The paper needs to state which
regime it is claiming, so the knee has to be located, not bracketed by a factor
of two.

## Two competing models, and the point that separates them

Private L2 = 2 MiB, LLC = 5 MiB, victim resident set = 2.59 MiB.

| model | what competes for the LLC | predicted knee |
|---|---|---|
| **B --- spill-only** | only `table - L2` | `(t - 2) + 2.59 = 5` -> **t = 4.41 MB** |
| **A --- whole-table** | the *entire* table, because the 16 MB stream evicts it from L2 continuously | `t + 2.59 = 5` -> **t = 2.41 MB** |

**2.5 MB discriminates.** Model A puts it just past the knee; model B puts it far
before.

## Registered prediction

**Model A.** `R(h2)` at a **2.5 MB** table is **< 80%**.

If `R(h2, 2.5 MB)` is **> 85%**, model A is refuted, the collapse is governed by
the spill above L2, and my account of the mechanism --- stated in
`FUSED_TABLESWEEP_PREREG` and repeated in the outcome --- is wrong and must be
withdrawn. Between 80% and 85% the point is inconclusive and the 3.0/3.5 MB
points decide.

Registering a single number here matters: I have already seen the 2 MB and 4 MB
endpoints, so an unregistered "the knee is somewhere in between" would be
unfalsifiable. **The claim is the mechanism, and 2.41 vs 4.41 MB is where the two
mechanisms visibly disagree.**

## Secondary, registered without a threshold

- `R(cat4)` stays flat (85--90%) across all five sizes --- partitioning confines
  the whole footprint, so the tenant's table size should not matter to it.
- `cost(cat4)` stays large (>= 15%) wherever protection is matched.
- `cost(h2)` <= 3% (one-sided; the two-sided form was a specification defect in
  the previous prereg and is not repeated).

## Design

Table **2.0, 2.5, 3.0, 3.5, 4.0 MB** x arms `wb`, `h2`, `cat4` x seeds 1--3 =
**45 runs**. Apparatus as before (`HNF_FWD_UNIQUE=0`, `SEQ_OUT=1024`, infinite
SF, DMT off, LRU at the HNF, stream 16 MB, mask on requestor 5 only).

**The 2 MB and 4 MB anchors are re-run, not reused.** The probe index changed
from a mask to a multiply-shift, which alters the instruction mix; comparing new
intermediate points against old anchors would confound the knee with a code
change. Re-running them also gives a direct check on the index change: the new
2 MB and 4 MB points should reproduce the old ones closely, and any large
deviation is the code change, not the table size.

## Liveness assertions

1. All 45 runs reach `Exiting @ tick`; dead runs reported, not dropped.
2. **Realized table size read from each run's own log line**, not from the
   directory name and not from the command line --- the F9 failure this campaign
   has now committed four times, most recently in the sweep this experiment
   exists to repair.
3. Arm identity from each run's own `config.ini`, as before.
4. Tenant L2 misses non-zero; `streamingAccesses` > 0 on `h2` only.
