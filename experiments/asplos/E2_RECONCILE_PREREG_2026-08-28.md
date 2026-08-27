# E2 pre-registration: separating two candidate causes of the tenant-cost disagreement

Written 2026-08-28, **before any E2 data exists**. Required by E1's P4 failure,
whose registered consequence was to quarantine the cross-comparison and reconcile
before any tenant-cost number is written up.

## The disagreement

The same cell --- 128 MiB table, 1 GiB stream, hit rate 0.5, `--reps 20`, 16
threads on cpus 32-47, 8 of 20 ways --- has been measured three times:

| campaign | resctrl helper | occupancy sampler running? | tenant's cost |
|---|---|---|--:|
| M12a | `setup_b` | **yes** | **+16.7%** |
| M10b | `setup_b` | no | **+11.6%** |
| E1a | `setup_c` | no | **+8.7%** |

**Two variables move together across those rows**, so E1's P4 conclusion ("the
helper explains it") was under-determined. I named the helper because that is what
I had varied deliberately; the sampler I had not thought of as a variable at all.

## The second candidate, which is my own instrument

`run_m12a_isocost.sh` polls `llc_occupancy` every 150 ms **inside the measured
window**, and each poll spawns a `python3` interpreter for the elapsed-time check
plus a `cat` of the sysfs file. Over a ~6 s run that is roughly forty interpreter
launches per measurement. Those processes are unpinned and sit in the **root**
resctrl group, which retains the full 20-way mask --- so they can allocate
**inside the tenant's 8 ways** while the tenant is being measured.

That is a plausible mechanism for a 5-point inflation, and it is the third time in
this campaign that the occupancy instrument has damaged the thing it was pointed
at (the duration bias of amendment 1, the total-versus-component error of
amendment 2, and now this).

The helper remains a plausible *second* mechanism, though its story is weaker than
I implied in E1: `setup_c` only moves **cpu 8** into a complement group, and cpu 8
is idle in these arms. Something subtler than "confining an idle CPU" would have
to be at work --- different CLOS ids landing in different hardware MSR slots, or
the root group's overlap being resolved differently when a second group exists.
**I do not have a mechanism for the helper effect, and E2 is designed so that a
null there is a real answer rather than an embarrassment.**

## Design

A 2x2 at the disputed point, plus unmasked controls.

- Fixed: `--mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g
  --hot-bytes 134217728 --cpu-list 32-47 --morsel 1m --warmups 2 --reps 20
  --threads 16 --hit-rate 0.5`, stream retained.
- `helper` in {`setup_b 8 32-47`, `setup_c 8 32-47 8`}.
- `sampler` in {off, **on** --- replicating M12a's loop byte-for-byte, including
  the per-sample `python3` launches, because the hypothesis is about that
  loop's cost and a cheaper reimplementation would not test it}.
- Controls: no mask, sampler off and on.
- **6 cells, n=40, 240 runs, ~25 min.**
- Interleaved with a per-rep rotation, schemata per record, aborts on silent table
  rounding, A6.19, resctrl torn down on every exit path.

## Variance basis --- taken from cells matching these arms

E1's sixth recorded registration defect was calibrating n on cells that did not
match the arms being run. So: the matching cell is E1a's 8-way arm, **CoV 3.27%**
($n{=}10$). At $n{=}40$ the two-sample resolution ($\alpha$ .05, power .80) is
**~2.05%** of the measured cyc/access.

**Every threshold below is 4 percentage points, i.e. ~2x resolution.** Stated
plainly: **this design cannot resolve an effect smaller than about 4 points**, and
an effect below that will be reported as *unresolved*, not as absent.

## Instrument check (registered, action on miss stated)

The unmasked, sampler-off cell must land within **+/-3%** of E1a's `none` median
of 78.178 cyc/access, i.e. **[75.83, 80.52]**.

- **On miss:** E2 is void for comparison against E1a, M10b or M12a; the
  within-E2 2x2 may still be read as internally controlled.

## Registered predictions

Let $C(h,s)$ be the tenant's cost under helper $h$ and sampler state $s$.

- **P1 (the sampler inflates).** $C(\text{setup\_b}, \text{on}) -
  C(\text{setup\_b}, \text{off}) \ge 4$ points.
- **P2 (the helper matters).** $C(\text{setup\_b}, \text{off}) -
  C(\text{setup\_c}, \text{off}) \ge 4$ points.
- **P3 (the two reproduce the endpoints).** $C(\text{setup\_b}, \text{on})$ is
  within 4 points of M12a's +16.7%, and $C(\text{setup\_c}, \text{off})$ within 4
  points of E1a's +8.7%.
- **P4 (no mask, no sampler effect).** With no mask the sampler changes the
  tenant's cost by **< 4 points** --- with all twenty ways available there is
  nothing for the sampler to displace. If this fails, the sampler is perturbing
  the tenant by some route other than cache allocation and the whole
  decomposition is unreadable.

P1 and P2 are independent; either, both, or neither may fire.

## Registered consequences

- **P1 holds** --- **M12a's and M12c's tenant-cost numbers are withdrawn** as
  contaminated by their own instrumentation. That includes §5's 16.7% and the
  0.9-of-16.7-points sentence, both of which are currently in the paper. The
  occupancy sampler is removed from any runner that also reports cost, and cost
  and occupancy are never again collected in the same run.
- **P2 holds** --- `setup_b` inflates relative to a fully partitioned machine, so
  **M10, M10b and `tab:catmba`'s 17--41% range are inflated too**, and every
  tenant-cost figure in the paper is re-sourced to E1a's sweep
  (+32.7 / +24.7 / +8.7 / +1.3 / +0.0% at 2/4/8/12/16 ways).
- **Both hold** --- both of the above, and the paper's tenant-cost story is rebuilt
  from E1a alone.
- **Neither holds** --- the three-way disagreement has a cause not tested here.
  All three campaigns' tenant-cost numbers stay quarantined and the paper quotes
  none of them until it is found. This is the outcome that costs the most and it
  is why the sampler is replicated exactly rather than approximated.
- **P4 fails** --- decomposition void; investigate the sampler's route before
  reading P1 or P2.

## What this cannot show

One mask width (8 of 20), one table, one stream size, one hit rate, Intel EMR,
no victim. It prices the tenant's own cost only. It does not revisit E1's
frontier, whose victim-side measurements used `setup_c` throughout and carried no
sampler, and are therefore unaffected by either candidate.
