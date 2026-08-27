# E2B pre-registration: the victim decomposition on one stream size

Written 2026-08-28, **before any E2B data exists**.

**Naming.** This is the experiment `AGENDA_2026-08-28.md` calls **E2**. The name
`E2` was consumed by `E2_RECONCILE_PREREG_2026-08-28`, an unplanned run forced by
E1's P4 failure. To avoid two documents called E2, this is **E2B**. The agenda's
E3--E6 keep their numbers.

## Why

The paper's victim-decomposition table --- the exhibit for the two-component
account --- has three rows measured at **two different stream sizes**:

| tenant's own table | harm removed | stream | owner |
|---|--:|---|---|
| 4 MiB | 100.5% | **256 MiB** | `M5_OUTCOME_2026-08-26` |
| 128 MiB | 75.3% | **1 GiB** | `M12_OUTCOME_2026-08-28` |
| 256 MiB | 28.0% | **256 MiB** | `M3B_OUTCOME_2026-08-25` (data) |

The paper currently discloses this with a dagger rather than fixing it, and
`M11_OUTCOME_2026-08-28` established that stream size is worth 15--21 points on
the tenant's axis --- so a reviewer is right to ask whether it moves the victim's
axis too. `QUANTITY_INDEX_2026-08-28` lists it as gap 5.

E2B re-measures all rows at **one** stream size, and adds two intermediate points.

## Which stream size, and why 1 GiB

1 GiB, for a reason that is itself a measured result: `M11_OUTCOME` showed a
256 MiB fact array re-read across `--reps` is **partly LLC-resident** on a 320 MiB
cache, so it is not a one-pass stream. 1 GiB is 3.3x the LLC and cannot be. Every
other current result (M12, E1) uses 1 GiB, so this also puts the decomposition on
the same footing as the frontier.

The cost of that choice, stated: **M5's 100.5% and M3b's 28.0% will not be
directly reproduced**, because they were measured on a stream we now believe was
partly resident. E2B supersedes them rather than confirming them, and if it
disagrees that is a finding about stream size, not an inconsistency.

## Design

- Victim: `pointer_chase --cpu 8 --node 0 --wss 178257920` (170 MB), `--run-sec 1
  --trials 6` --- identical to M5, M12 and E1 pass B.
- Tenant: `cxl_join_bench --mode morsel --policy wb --fact-node 2 --hot-node 0
  --fact-bytes 1g --cpu-list 32-47 --threads 16 --morsel 1m --hit-rate 0.5
  --warmups 0 --reps 20000`.
- **No mask at any point.** This experiment is about the label alone; partitioning
  is E1's subject.
- Tenant footprint: **4, 16, 64, 128, 256 MiB** --- `4194304 / 16777216 /
  67108864 / 134217728 / 268435456`, all exact powers of two x 16 B, so
  `HOT_TABLE_ROUNDED` must never fire and the runner aborts if it does.
- Stream: {`retain` (`--flush-distance 0`), `flush` (`--flush-distance 262144`)}.
- Plus a victim-alone baseline.
- **11 cells, n=8, 88 runs, ~19 min.** Per-rep rotation; tenant liveness
  (`alive_at_end`, `HOT_TABLE_WARMED`) asserted in every co-run record; schemata
  captured; A6.19; resctrl torn down on exit (it is never set up, and the runner
  verifies zero groups before starting).

## Variance basis and the resolution it gives

From the matching arms --- E1 pass B's victim cells, same binary, same working
set, same trials --- **victim CoV is 0.03--0.66%**. At n=8 that is a two-sample
resolution of **~0.9%** on a harm ratio $H$.

The reported quantity is derived: fraction removed
$= (H_r - H_f)/(H_r - 1)$. With $H_r \approx 2.3$ and $H_f \approx 1.3$ each known
to ~0.6%, propagating gives **~2--3 points** on the fraction. **Every threshold
below is at least 8 points, i.e. >= 3x resolution.**

## Instrument check (registered, action on miss stated)

The victim-alone baseline must land within **+/-3%** of E1 pass B's 78.042
cyc/load, i.e. **[75.70, 80.38]**.

- **On miss:** E2B is void for comparison against M5, M12 or E1; the within-E2B
  sweep may still be reported as internally controlled.

## Registered predictions

Let $H_r(t)$, $H_f(t)$ be the victim's harm at tenant footprint $t$ with the
stream retained and non-allocating, and $F(t)$ the fraction removed.

- **P1 (monotone decline).** $F$ is non-increasing across 4 -> 256 MiB, with
  $F(4\,\text{MiB}) \ge 90\%$ and $F(256\,\text{MiB}) \le 50\%$.
- **P2 (the residue is the tenant's own footprint).** $H_f$ is non-decreasing in
  $t$, and $H_f(256\,\text{MiB}) \ge 1.8$.
- **P3 (arm identity, against the one row already on this stream size).** At
  128 MiB, $F$ is within **8 points** of M12's 75.3%.
- **P4 (the two-component account's strong form).** $H_f(4\,\text{MiB}) \le 1.10$
  --- with almost nothing of its own in the cache, non-allocating the tenant's
  stream returns the victim to near baseline.

## Registered consequences

- **P1--P4 hold** --- the decomposition becomes one clean sweep on one stream
  size. The dagger comes out of the paper, M5's and M3b's rows are superseded
  (not contradicted), and the two-component account gets the exhibit it has never
  had.
- **P4 fails** --- **this is the branch that matters most.** If a 1 GiB stream
  leaves the victim above 1.10x even when the tenant holds only 4 MiB, then there
  is a harm component that is *neither* stream residency *nor* the tenant's own
  footprint, and it scales with stream volume. That would **partly revive M3b's
  transport claim** --- the very claim `M5` retired and whose premature burial
  produced red-team S1-1. It would mean the two-component account is a
  three-component account, and it would change what the paper can say about how
  much any admission mechanism can buy. Registered explicitly so that this
  outcome cannot be read as noise.
- **P1 fails (non-monotone)** --- the two-component account's central mechanism is
  wrong; stop and investigate before any further writing.
- **P2 fails while P1 holds** --- $F$ declines but not because the residue grows;
  something else scales with the tenant's footprint. Report both and attribute
  neither.
- **P3 fails** --- arm identity against M12 is broken; quarantine the
  cross-comparison exactly as E1's P4 required, and do not supersede M5 or M3b on
  the strength of a run that cannot reproduce its own reference point.

## What this cannot show

Intel EMR only, one victim type and working set, one hit rate, one stream size ---
that being the point, but it means E2B cannot itself measure the stream-size
dependence it was created to eliminate. Establishing *that* would need the same
sweep at a second stream size, which is not registered here. The label remains
the flush-behind proxy, so what is measured is non-allocation-with-a-13--19%-charge
rather than the memory type.
