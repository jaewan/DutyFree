# Pre-registration: does a way mask restore the victim's L3 residency? And is the harm really L3-local?

Registered **before** the run. Two questions in one batch because they share an
apparatus and the machine is verified idle.

## Question 1 — the contradiction in our own results

Two committed findings cannot both be simple:

- `AMD_L3OCC_OUTCOME`: the harm is **L3 eviction**. Victim L3 occupancy under a
  same-CCX streamer falls **3568 KB -> 196 KB** (5.5% of quiescent).
- `AMD_NARROWMASK_OUTCOME`: confining that streamer from 8 of 16 ways down to
  **one** moves the residual only **12.8x -> 10.3x**, flat below four ways.

**If the streamer can allocate in only one way, it cannot evict the victim from
the other fifteen.** So either the mask restores residency and the residual is
something other than eviction, or the mask is not doing what we believe.

Nobody has measured occupancy *under* a mask. This does.

## Question 2 — P2 is provisional and should be settled before it is written down

`BERGAMO_BACKINVAL` P2 ("the harm is L3-domain-local") rests on other-CCX
= **1.31x** against same-CCX 27.8x. But `AMD_L3OCC`'s other-CCX cell read
**618.7** cyc/access against the factorial's **71.8** --- an 8.6x disagreement in
one cell, with the aggressor moving 26% fewer bytes. **P2 is a strong claim that
would be new to the paper; it should not be written down while one of two runs
contradicts it.**

## Design

Victim on core 0; aggressor 7 threads. Arms:

| arm | aggressor cores | victim mask | aggressor mask |
|---|---|---|---|
| `quiescent` | --- | --- | --- |
| `wb` | same-CCX 1--7 | --- | --- |
| `cat8` | same-CCX | `ff00` | `00ff` |
| `cat4` | same-CCX | `fff0` | `000f` |
| `cat1` | same-CCX | `fffe` | **`0001`** |
| `other` | **other-CCX 9--15** | --- | --- |

Victim WSS **4096 KB** (the geometry both prior results used) and **512 KB**.
n=10 -> 120 runs, ~35 min. `llc_occupancy` sampled every 250 ms during the
victim's run, warmup excluded, median as the statistic.

Platform as found; THP recorded per record rather than set, since `AMD_L3OCC`
ran under `madvise` and `BERGAMO_BACKINVAL` under `never`/`always`, and the
recorded value is what makes the two comparable.

## Registered predictions

**P1 --- what the mask does to residency.** Victim L3 occupancy under `cat1`,
as a fraction of quiescent:

- **>= 70%** -> the mask **restores residency**, and the surviving 10.3x residual
  is therefore **not** eviction. The paper's "a bitmask sheds none of it" becomes
  the sharper and more defensible *"a mask restores residency but not latency"*.
- **<= 30%** -> the mask does **not** protect residency even at one way, and our
  reading of AMD CAT is wrong; `tab:amdcat`'s mechanism story needs rebuilding.
- 30--70% -> partial; report the curve across `cat8/cat4/cat1`.

**P2 --- the other-CCX re-measure.** Median other-CCX slowdown at 4096 KB.
Registered as a **reproduction test of the factorial**, whose value was 1.31x:
within **1.0--2.0x** confirms P2 and the L3-locality claim may be written down;
**> 4x** means the factorial's other-CCX cell does not reproduce and **the
L3-locality claim must be withdrawn** pending explanation.

**No prediction is registered for Q1's direction.** I have twice today asserted a
mechanism from an instrument that could not see it, and been wrong both times.
The instrument is the contribution.

## Liveness assertions

1. **Every masked arm records its mask read back from `schemata` and compared by
   VALUE** (`mask_ok`); a record whose mask did not take is not an arm. Text
   comparison is forbidden --- the kernel normalises `00ff` -> `ff`, which
   false-alarmed on 24 of 36 records on 2026-08-30.
2. `llc_occupancy` must vary across arms; a constant reading voids the run rather
   than becoming a finding.
3. Aggressor bandwidth recorded per arm: a mask that throttles *rate* rather than
   *residency* would remove harm for the wrong reason.
4. Non-masked arms must record **no** CAT groups, so a leftover mask cannot
   silently apply to `wb` or `other`.
5. The machine was verified idle before launch (load 0.33, no workload
   processes) --- the first `l3occ` re-run was invalidated by exactly this
   omission.
