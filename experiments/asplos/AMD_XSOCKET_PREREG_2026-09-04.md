# Pre-registration: does moving the AMD streamer to the other socket reduce the tax to measurement noise?

Registered **before** the run. Nothing in this campaign had been launched when
this file was frozen; the only prior contact with the host was a connectivity
check and a two-command smoke test, recorded in §"Smoke, which is not an arm".

## Why this exists

`Sec3_Measurement.tex:152` states that moving the write-back streamer to the
other socket "reduces it to measurement noise." The draft-wide reconciliation
(`PAPER_RECONCILIATION_2026-09-04.md`, claim **U3**) found that **no record in
this project contains any AMD cross-socket measurement.** The claim is unbacked.

The neighbouring arm *is* backed. `BERGAMO_BACKINVAL_OUTCOME_2026-08-30.md`
measured an **other-CCX, same-socket** streamer at **1.30×** (`THP=always`,
victim 4096 KB) and **1.31×** (`THP=never`), and `Sec7_Evaluation.tex:313`
cites the 1.30× correctly. So the paper holds one measured same-socket number
and one unmeasured cross-socket assertion, on the same axis, in two different
sections.

This campaign measures the missing arm on the same apparatus, with one variable
changed, and pre-commits to what "measurement noise" means numerically. That
phrase is operationalized nowhere in the corpus. Deciding after the fact what
counts as noise is precisely the degree of freedom pre-registration exists to
remove, and this project has already been bitten once by a threshold
"calibrated in one configuration and applied in another"
(`BERGAMO_BACKINVAL_PREREG` P1, recorded as mis-specified).

## The apparatus is located, and it is reused, not rebuilt

| element | what is reused | source |
|---|---|---|
| runner | `broker/bergamo_backinval.py`, as the sibling `broker/amd_xsocket.py` | `broker/README.md` |
| victim | `/home/domin/tmp_dutyfree_exp/bin/victim`, mtime **2026-08-23 15:24** | unmodified, not rebuilt |
| streamer | `/home/domin/tmp_dutyfree_exp/bin/aggressor`, mtime **2026-08-23 15:24** | unmodified, not rebuilt |
| victim command | `victim -c 0 -w <WSS> -P -d 3 -W 1` | byte-identical to the parent harness |
| streamer command | `aggressor -m wb_load -t 7 -c <CORES> -N 2 -s 64 -d 10` | byte-identical to the parent harness |
| metric | `cyc_per_access` from the victim's own `VICTIM` line; **median** per cell | identical |
| statistic | slowdown = median(arm) / median(quiescent), within a `(THP, WSS)` cell | identical |
| **n** | **20 per cell** | `bergamo_backinval.py` argv[1]; 240/240 runs in `data/amd_backinval.jsonl`, 20 per cell verified |

**On n.** The task brief recalled the AMD records as using n=5 and n=30. Neither
figure appears in this family: `AMD_NARROWMASK_OUTCOME` used **n=6**,
`AMD_L3OCC_PREREG` **n=10**, and the harness being reused here —
`bergamo_backinval.py`, the one that produced the 1.30× — used **n=20**. The
instruction is to match the record rather than choose, so **n=20** it is, and
this note records that the brief's recollection was checked rather than adopted.

**It is the same machine.** `ssh broker` resolves to `moscxl`, an AMD EPYC 9754,
microcode `0xaa00215`, kernel `7.0.0-28-generic`, two sockets, SMT on, 1 MiB L2
per core, 8-core L3 domains — and the surviving `tmp_dutyfree_exp/bin` tree
holds the *same binaries, at the same mtimes*, that produced the published AMD
numbers. `/sys/kernel/mm/transparent_hugepage/enabled` was last written
**2026-08-30 07:49**, which is when `bergamo_backinval.py` restored it to
`madvise` on its way out. The apparatus matches; this is not a look-alike host.
(The earlier failure to reach `mos181` on host-key verification is unrelated:
`broker` is a different host and verified clean here.)

**Two deviations from the parent harness, both disclosed.**

1. Victim and streamer are launched with argv **lists** rather than through a
   shell, so the parent holds their real pids and can read realized placement
   out of `/proc` during the run. The argv each process receives is unchanged.
2. A **second quiescent cell** (`quiescent_b`) is added per condition, run after
   all three co-run arms. It is the negative control that defines the noise
   band (below). Nothing about the co-run arms changes.

Neither deviation touches a measured command line. Gate **G0** exists so that
if either has nevertheless perturbed the instrument, the failure is visible as
the published control not reproducing, and no cross-socket verdict is certified.

## Design: one axis, three placements, plus two controls

The victim never moves: core **0**, package **0**, L3 domain `0-7,256-263`,
memory local to node 0. Only the streamer moves.

| arm | streamer cores | L3 domain | package | what changes |
|---|---|---|---|---|
| `quiescent_a` | — | — | — | baseline, no streamer |
| `same` | 1–7 | `0-7,256-263` (victim's) | 0 | positive control |
| `other` | 9–15 | `8-15,264-271` | 0 | **the published 1.30× arm** |
| `xsock` | 129–135 | `128-135,384-391` | **1** | **the arm under test** |
| `quiescent_b` | — | — | — | negative control, defines the noise band |

`xsock` is the exact structural analog of `other`: seven threads on one 8-core
L3 domain, skipping that domain's first core, just as `other` uses 9–15 within
`8-15` and `same` uses 1–7 within `0-7`. Thread count, bytes per thread, mode,
duration and memory node are all held fixed.

Factorial as inherited: **THP** {`never`, `always`} × **victim WSS** {512 KB
(fits the 1 MiB private L2), 4096 KB (does not)} × **5 placements** × **n=20**
= **400 runs**, roughly 70 minutes.

**Primary cell:** `THP=always`, `WSS=4096 KB`. That is the cell whose `other`
value is the published **1.30×** and whose `same` value is 30.82×, so it is
where the control is sharpest and the effect largest. All four cells are
reported; the verdict is taken on the primary cell and the other three are
reported as consistency checks, not pooled.

## What "measurement noise" means — committed here, in advance

The phrase is operationalized against the **measured run-to-run spread of this
apparatus at n=20**, not against a number I like.

Let, within one `(THP, WSS)` cell:

- `S(arm) = median(cyc_per_access | arm) / median(cyc_per_access | quiescent_a)`
- `CI95(arm)` = two-sided percentile bootstrap 95% interval of that ratio,
  10,000 resamples, both cells resampled independently, **seed 20260904**.

**The noise band `NB` is measured from the negative control, not chosen:**

```
NB = max( 0.02 , |CI95_lo(quiescent_b) - 1| , |CI95_hi(quiescent_b) - 1| )
```

That is: *the largest apparent slowdown this apparatus can manufacture out of no
effect at all, at n=20, with 95% confidence.* `quiescent_b` is an independent
replicate of the no-streamer condition, taken after the co-run arms in the same
cell, so it also absorbs any within-cell drift. The `0.02` floor keeps a
freakishly tight control from making the test unfalsifiable in practice.

`NB` is a **fitted-from-control** quantity, so it needs a ceiling, which is gate
G7: **if `NB > 0.10` the apparatus is declared unfit to adjudicate this claim at
n=20 and the outcome is INCONCLUSIVE.** A 10%-wide noise band cannot
meaningfully test a claim about a 1.30×-scale effect.

## The three outcomes, pre-declared, with the paper wording each licenses

Judged on `xsock` in the primary cell. `S`, `[L, H] = CI95(xsock)`, and
`p` = two-sided Mann–Whitney U of the 20 `xsock` samples against the 20
`quiescent_a` samples, α = 0.05.

### Outcome A — CONFIRMED. Requires **both**:
- `L ≥ 1 − NB` **and** `H ≤ 1 + NB` — the entire interval lies inside the band;
- `p > 0.05`.

*Licensed wording (the current sentence survives, now with a citation):*

> Moving the WB streamer from the victim's L3 domain to another L3 on the same
> socket reduces the slowdown substantially; moving it to the other socket
> reduces it to measurement noise ($S\times$, 95\% CI $[L, H]$, against a
> measured noise band of $\pm NB\%$ at $n{=}20$).

### Outcome B — REFUTED, with a measurable residual tax. Requires **both**:
- `L > 1 + NB` — the entire interval lies above the band;
- `p ≤ 0.05`.

*Licensed wording (the claim is withdrawn and replaced by the measurement; the
number goes in, the phrase comes out):*

> Moving the WB streamer from the victim's L3 domain to another L3 on the same
> socket reduces the slowdown substantially, and moving it to the other socket
> reduces it further but **not** to zero: a residual $S\times$ survives
> (95\% CI $[L, H]$, noise band $\pm NB\%$, $n{=}20$).

**No framing that preserves "measurement noise" is to be searched for.** If B
fires, the phrase is deleted and the residual is stated.

### Outcome C — INCONCLUSIVE. Anything else. Named subcases:
- **C1** — `L ≥ 1 − NB` and `H ≤ 1 + NB` but `p ≤ 0.05`: a *statistically
  detectable* effect that is nonetheless *inside the apparatus's own noise band*.
  This is a real possibility at n=20 against a tight instrument and is named in
  advance so it cannot be quietly resolved either way.
- **C2** — `H < 1 − NB`: the victim measures *faster* with a cross-socket
  streamer than with none. Reported as an anomaly and an apparatus concern, not
  as support for the claim.
- **C** — the interval straddles a band edge, or any blocking gate fails.

*Licensed wording for every C subcase (qualitative only, number disclosed):*

> Moving the WB streamer from the victim's L3 domain to another L3 on the same
> socket reduces the slowdown substantially; moving it to the other socket
> reduces it further, to within $S\times$ of baseline, which this apparatus
> cannot separate from its own run-to-run spread at $n{=}20$.

The phrase "measurement noise" is **not** licensed by C. Under C the draft
sentence is narrowed to the measured value and the ambiguity is stated.

## Fail-closed gates

A placement experiment whose placement is not verified from the artifact is
worthless, so every one of these is read back **from the running processes**,
not inferred from the launcher's intent (`S5.1`). All are blocking: any failure
leaves the campaign **UNCERTIFIED** regardless of the verdict arithmetic.

| gate | condition |
|---|---|
| **G0** control | `S(other)` in the primary cell lies in **[1.20, 1.40]**, bracketing the published 1.30×. **If G0 fails, the apparatus does not reproduce the record and the cross-socket number means nothing** — it is reported, uncertified, and the campaign becomes a reproduction failure rather than a new arm |
| **G1** victim pinning | `Cpus_allowed_list == "0"` and every sampled realized CPU `== 0`, in all 400 runs |
| **G2** streamer placement | every sampled streamer-thread CPU lies inside the requested core list; the requested cores span **exactly one** L3 domain; that domain equals the victim's for `same` and is disjoint from it for `other` and `xsock` — in all 240 co-run runs |
| **G3** socket | streamer cores all report `physical_package_id == 1` for `xsock` and `== 0` for `same`/`other`; the victim's is `0`, in every run |
| **G4** realized NUMA placement | ≥99% of the victim's pages on **node 0** and ≥99% of the streamer's on **node 2**, read from `/proc/<pid>/numa_maps` during the run, with no `FATAL` in any streamer log |
| **G5** rate match | median streamer bandwidth in `other` and `xsock` within **±10%** of `same` in the same cell. If the cross-socket streamer cannot sustain the rate, the comparison is confounded by rate and is reported as such, not as a placement effect (inherited from `BERGAMO_BACKINVAL_PREREG` liveness assertion 5) |
| **G6** SMT / boost | `smt/control == on`, `smt/active == 1`, `cpufreq/boost == 1` in every run |
| **G6b** frequency | median core-0 frequency in each arm within **±10%** of `quiescent_a` in the same cell, so a placement result cannot be a frequency result. Frequency is **measured, not pinned** — the governor is deliberately left as found (`schedutil`, boost on), because changing it would alter a shared machine *and* move conditions away from the published figure this campaign must reproduce |
| **G7** noise band | `NB ≤ 0.10` |
| **G8** liveness | every run emits a `VICTIM` line; 20 runs per cell, none dropped; quiescent cells record **zero** streamer bandwidth. Runs that fail are reported, not dropped |
| **G9** THP | `thp_readback == thp_requested` in every run |
| **G10** positive control | `S(same)` in the primary cell **≥ 10×**. If the harm does not reproduce at all, nothing about its absence elsewhere is informative |

Thresholds live as **module constants** in `analyze_amd_xsocket.py`, frozen with
this file, so moving one after seeing data is visible in git.

## The CXL node, stated explicitly, because this topology bundles two variables

`numactl --hardware` on `moscxl` reports three nodes: node 0 = socket 0
(CPUs 0–127, 256–383), node 1 = socket 1 (CPUs 128–255, 384–511), and **node 2 =
CXL memory with no CPUs** (258 GB). Node distances as the firmware advertises
them:

```
node   0   1   2
  0:  10  32  60
  1:  32  10  50
  2: 255 255  10
```

The streamer streams **from node 2** in every arm. Node 2's own row reading
`255 255 10` is the ordinary SLIT artifact for a memory-only node and carries no
information; the load-bearing entries are the initiator-to-target ones:
**0→2 = 60** and **1→2 = 50**.

So the confound is real, and it is worth being precise about which way it runs.

1. **The memory variable does not move.** `alloc_wb_cxl()` binds the buffer to
   node 2 with `mbind(MPOL_BIND | MPOL_MF_STRICT)` and then verifies placement
   with `move_pages()` every 64 MB, aborting if any page landed elsewhere. The
   stream's memory node is *identical* in all three placements. G4 re-checks
   this from `/proc/<pid>/numa_maps` independently of the binary's own check.
   (Incidentally: `-N 2` on the streamer's command line is **inert** for
   `wb_load` — `mem_node` is only consulted for `wb_local` — so the CXL binding
   comes from `CXL_NUMA_NODE`, a compile-time constant, and cannot drift with an
   argument. Recorded because the parent harness passes `-N 2` and a reader
   would reasonably assume it is what selects the node.)
2. **What does move is the CPU-to-device path, and it moves in the direction
   that makes the test harder, not easier.** Socket 1 is **nearer** the CXL
   device than socket 0 (50 against 60) — `common.h` says so in as many words
   (`AGG_NUMA_NODE 1`, "closest to CXL"), and the published arms streamed from
   the *far* socket. So `xsock` does not handicap the streamer; if anything it
   lets it pull harder. A cross-socket arm that still shows no harm is therefore
   a **conservative** test of the claim, and one that shows harm cannot be
   dismissed as the streamer having been starved.
3. **The disambiguator is the `other` arm, which is why it is in the design.**
   `other` changes the L3 domain while holding socket *and* CXL distance fixed.
   If `S(xsock) ≈ S(other)`, then leaving the victim's L3 domain accounts for
   the whole effect and the extra socket/distance change contributes nothing —
   the CXL-distance variable is shown inert by measurement rather than assumed.
   **Only if `S(xsock)` falls materially below `S(other)` are the two variables
   entangled**, and that case is pre-registered as reportable-but-unattributed:
   the residual would be stated, and "cross-socket" and "nearer the CXL device"
   would be declared not separated by this design.
4. **G5 tests it empirically.** If the socket-1 streamer's bandwidth differs
   from socket 0's by more than 10%, the arms are not rate-matched and the cell
   is inconclusive by gate rather than by argument.

**Diagnostic D1, reported without a threshold.** Single-thread `wb_load`
bandwidth from node 2, measured from core 1 (pkg 0), core 9 (pkg 0) and core 129
(pkg 1), three reps each — `broker/amd_xsocket_distance_probe.sh`. This measures
the asymmetry the SLIT advertises instead of trusting a firmware table. It is a
diagnostic, not an arm, and no verdict turns on it.

## Smoke, which is not an arm

Before this file was written, two commands were run on `broker` to establish
that the located harness still runs at all — because if it did not, this would
be a request to rebuild an apparatus, which is a different campaign and not mine
to authorize:

```
victim -c 0 -w 4096 -P -d 3 -W 1        -> cyc_per_access = 54.6251
aggressor -m wb_load -t 7 -c 129,...,135 -N 2 -s 64 -d 3  -> 25.02 GB/s aggregate
```

The quiescent value lands on the record's 54.96 (`THP=never`, 4096 KB
quiescent), and the socket-1 streamer sustains the record's 24.2–24.8 GB/s. Both
are **smoke, not data**: n=1, outside the factorial, and no verdict may cite
them. They are recorded here so that the pre-registration cannot be accused of
having been written after a peek at the answer — the answer requires the
contrast, and neither number is a contrast.

## Citizenship on a shared machine

The runner refuses to start if the 1-minute load average exceeds 1.0. Every
process is explicitly pinned; the campaign uses 8 of 512 threads at a time
(1.6%) and never more. THP is set and **restored to `madvise` on every exit
path including failure**, exactly as the parent harness does. The governor,
boost state and `perf_event_paranoid` are left as found. No module is loaded, no
memory is offlined, no reboot.

## What is deliberately not done

- The platform is **not** frozen and the governor is **not** changed. Same
  reasoning as `BERGAMO_BACKINVAL_PREREG`: this is a shared host, and freezing
  would move conditions away from the published figure G0 has to reproduce.
  Frequency is measured instead (G6b).
- The binaries are **not** rebuilt. `broker/README.md` is explicit that the
  2026-08-23 binaries are kept precisely so that a comparison against published
  AMD figures is not confounded with a recompile.
- **No new metric is introduced.** L3 occupancy (`AMD_L3OCC`) and CAT
  (`AMD_CATOCC`) would both be informative about *why* a residual exists, and
  neither is in scope: this campaign answers whether the cross-socket number is
  what the paper says it is, on the instrument that produced its neighbour.
- **No absolute magnitude is promised to reproduce.** `AMD_NARROWMASK_OUTCOME`
  established that on this rebuilt host the AMD *ratios* reproduce and the
  *absolute* taxes do not (19.9× published against 27.6× re-measured), and per
  `S6.6` that is stated rather than hidden. G0 and G10 are therefore both set on
  ratios, and G10's 10× floor is deliberately far below the record's 30.82× for
  exactly this reason.


---

# Addendum 0 --- 2026-09-04, before launch: one gate was mis-specified, and I saw n=1 values while finding out

The body above was frozen at **`d65f768`** with the runner and the analyzer.
**Then**, and only then, the runner was exercised end-to-end at `reps=1` against
a throwaway path (`/tmp/plumb.jsonl`) to prove the plumbing before committing a
70-minute run to it. This addendum records both consequences. It is written
**before** the registered `n=20` campaign starts.

## 1. Gate G2 was mis-specified, and is corrected here rather than allowed to fail spuriously

`aggressor.c` runs **eight** threads, not seven: seven pinned workers plus the
coordinator, which allocates the buffer, starts the workers, sleeps for the
duration and joins. The coordinator is deliberately never pinned. G2 as frozen
compared *all* `/proc/<pid>/task/*` CPUs against the requested core list, so it
would have failed on all 240 co-run runs — the plumbing check recorded
`[129,130,131,132,133,134,135,274]`, where `274` is the coordinator sitting
wherever the scheduler put it.

That is a gate that fails for an apparatus-accounting reason rather than a
placement reason, which is exactly the defect
`BERGAMO_BACKINVAL_PREREG`'s P1 was recorded as ("a threshold calibrated in one
configuration and applied in another"). Launching into a gate known in advance
to fail would make the campaign uncertifiable for no scientific reason.

**Correction, applied before launch.** The runner now records
`agg_worker_cpus` (tids ≠ pid) and `agg_main_cpu` separately, and **G2 is judged
on the worker threads only**, additionally requiring that there be exactly
**7** of them. The gate therefore became *stricter*, not looser: it now also
catches a run in which a worker thread failed to start.

**Why this cannot move the verdict.** G2 is a placement-verification gate. It
takes no threshold on the effect, appears in no verdict arithmetic, and its
correction changes which *runs* are admissible, not what any number means. No
threshold, band, α, seed, primary cell or decision rule in the body above is
touched. Those remain as frozen at `d65f768`.

## 2. I saw n=1 numbers, and here they are, because concealing them would be worse

The plumbing check is a full pass of the factorial at one rep, so proving the
plumbing meant seeing twenty single-sample values. **The registered thresholds
were already frozen and public in git before that happened**, so the peek could
not have shaped them — but it did tell me the likely direction of the answer,
and this project's rule is that a researcher degree of freedom is disclosed
rather than argued away.

Primary cell (`THP=always`, 4096 KB), single samples, **discarded and not
carried into the campaign**:

| arm | cyc/access | ratio to `quiescent_a` |
|---|--:|--:|
| `quiescent_a` | 47.47 | 1.00 |
| `same` | 1458.78 | 30.7 |
| `other` | 61.99 | 1.31 |
| `xsock` | 46.37 | **0.98** |
| `quiescent_b` | 47.46 | 1.00 |

So I go into the registered run expecting the apparatus to reproduce (`other`
1.31 against the published 1.30×, `same` 30.7 against 30.82×) and expecting
Outcome **A**. Three commitments follow from saying so out loud:

1. `/tmp/plumb.jsonl` is **not** an artifact of this campaign. It is not
   analyzed, not pooled, not cited by the outcome, and the registered run writes
   to a fresh path that the runner refuses to overwrite (`A6.19`).
2. The verdict is taken by `analyze_amd_xsocket.py` on the `n=20` data against
   the constants frozen at `d65f768`. **Expecting A is not permission to
   deliver A**: if the `n=20` interval crosses a band edge the answer is C, and
   C does not license the phrase "measurement noise".
3. The 512 KB cells look noisy at `n=1` (`quiescent_b/quiescent_a` = 21.03/17.65
   = **1.19**), consistent with `AMD_L3OCC_PREREG`'s finding that at that size
   the victim's own quiescent spread is large. That is what gate **G7** is for,
   and if the 512 KB noise band exceeds 0.10 those cells are unfit to adjudicate
   anything and will be reported as such. **The primary cell was designated as
   4096 KB in the frozen body, before any of this was known**, so this
   observation does not get to relocate it.
