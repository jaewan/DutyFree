# AMD cross-socket outcome: the apparatus reproduces exactly, the cross-socket tax is unmeasurable --- and my own equivalence rule returns INCONCLUSIVE by 3 parts in 10,000

Pre-registration `AMD_XSOCKET_PREREG_2026-09-04.md`, frozen at **`d65f768`**,
addendum 0 (pre-launch, gate G2 correction and the disclosed `n=1` peek) at
**`c7b8d1c`**. 400/400 runs usable, none dropped. Host `moscxl` (`ssh broker`).

**Read this document in this order**, because everything downstream depends on
the first section: the same-socket control, then the cross-socket result, then
the certification verdict, then the two gates that failed and why.

---

## 1. The same-socket control, first, because nothing else means anything without it

The published figure is **1.30×** (`Sec7_Evaluation.tex:313`, from
`BERGAMO_BACKINVAL_OUTCOME_2026-08-30.md`, `THP=always`, victim 4096 KB,
other-CCX same-socket). Gate **G0** required the re-measurement to land in
**[1.20, 1.40]**.

| cell | arm | this campaign | the record | agreement |
|---|---|--:|--:|---|
| `always`/4096 | `other` (**the published 1.30×**) | **1.3249×** | 1.305× | **+1.5%** |
| `always`/4096 | `same` | 31.154× | 30.823× | +1.1% |
| `never`/4096 | `other` | 1.3020× | 1.307× | **−0.4%** |
| `never`/4096 | `same` | 27.775× | 27.767× | **+0.03%** |
| `never`/512 | `same` | 2.7277× | 2.758× | −1.1% |
| `always`/512 | `same` | 1.8170× | 1.615× | +12.5% |

**G0 PASSES.** Every 4096 KB arm reproduces within **1.5%**, and the `never`/4096
same-CCX cell agrees to **0.03%**. This is a far better reproduction than this
project had any right to expect: `AMD_NARROWMASK_OUTCOME_2026-08-30.md`
established that on this rebuilt host the AMD *ratios* reproduce while the
*absolute* magnitudes do not (19.9× published against 27.6× re-measured), and
the pre-registration therefore set G0 and G10 on ratios and warned against
promising magnitudes. Here the magnitudes reproduced too. The reason is
visible in the provenance: this is not merely the same *kind* of machine but
**the same machine running the same unmodified binaries** —
`victim` and `aggressor` at mtime 2026-08-23 15:24, sha256 `90089579…` and
`583257f5…`, never rebuilt.

**This narrows `AMD_NARROWMASK_OUTCOME`'s standing `S6.6` instruction rather
than contradicting it, and the distinction is the host rebuild.** That document
compared figures published *before* the rebuild against a re-measurement
*after* it, and found the magnitudes gone. This campaign compares 2026-08-30
against 2026-09-04, both after the rebuild, on the same binaries and the same
platform state — and the magnitudes hold to ≤1.5%. So the honest scope is:
**absolute AMD magnitudes do not survive a host rebuild; within a fixed host
state and fixed binaries they reproduce tightly.** The paper's caveat should
keep saying the first thing; it is now known not to be a statement about the
apparatus's intrinsic repeatability. Handed back in §10 rather than written
into that document.

The one arm that does not reproduce tightly is `always`/512 same-CCX (+12.5%),
and that is the cell the record itself flagged: `BERGAMO_BACKINVAL_OUTCOME`
addendum 1 withdrew its "bimodality" reading and reported a stable ~1.9× when
re-run standalone. Measured here **inside a factorial**, that cell is again
wide — IQR **14.20** at `always` and **25.41** at `never`, against IQR 0.03–1.68
in every other cell in this campaign. So the addendum's diagnosis is
corroborated from the other side: **the spread is a property of the factorial
context, not of the workload**, and the 1.817× median sits close to the
addendum's ~1.9×. No claim here rests on that cell.

**Because G0 passes, the cross-socket number is worth reading.**

## 2. The cross-socket result

Victim on core 0 (package 0, L3 domain `0-7,256-263`) in every arm; only the
streamer moves. Medians of `cyc_per_access`, n=20 per cell.

| cell | arm | median | IQR | slowdown `S` | 95% CI | `p` vs quiescent | GB/s |
|---|---|--:|--:|--:|---|--:|--:|
| `always`/4096 | `quiescent_a` | 47.041 | 1.260 | 1.0000 | — | — | — |
| **(primary)** | `same` | 1465.486 | 4.677 | **31.154×** | [30.72, 31.60] | 7e−08 | 24.26 |
| | `other` | 62.323 | 0.278 | **1.3249×** | [1.306, 1.345] | 7e−08 | 24.26 |
| | **`xsock`** | 47.000 | 1.676 | **0.9991×** | [0.9729, 1.0261] | **0.239** | 24.38 |
| | `quiescent_b` | 47.654 | 1.273 | 1.0130× | [0.9737, 1.0268] | 0.787 | — |
| `never`/4096 | `quiescent_a` | 55.120 | 0.930 | 1.0000 | — | — | — |
| | `same` | 1530.969 | 7.463 | 27.775× | — | — | 24.78 |
| | `other` | 71.769 | 0.228 | 1.3020× | — | — | 24.80 |
| | **`xsock`** | 54.758 | 1.051 | **0.9934×** | [0.9825, 1.0032] | **0.209** | 24.91 |
| | `quiescent_b` | 54.765 | 0.956 | 0.9935× | [0.9847, 1.0073] | — | — |

Full four-cell table including the 512 KB cells is in `run.log` and reproducible
from `analyze_amd_xsocket.py`.

**There is no cross-socket tax to measure.** The point estimates are **0.9991×**
and **0.9934×** — both marginally *below* their uncontended baselines — and the
Mann–Whitney tests do not reject at α = 0.05 (`p` = 0.239 and 0.209) while the
same-CCX arm in the same cells rejects at `p` = 7×10⁻⁸.

The sharpest way to say it does not need statistics at all. In `never`/4096:

```
xsock       54.758 cyc/access
quiescent_b 54.765 cyc/access      <- the no-streamer negative control
```

**The victim with seven cross-socket streaming threads pulling 24.9 GB/s is
0.007 cyc/access from the victim with no streamer at all** — and in the primary
cell the cross-socket arm is *closer to `quiescent_a`* (0.9991×) than the
negative control is (1.0130×). The apparatus's own replicate-to-replicate drift
is larger than the entire effect of the cross-socket streamer.

## 3. The pre-registered verdict: **C --- INCONCLUSIVE**, and I am reporting it as registered

This is the uncomfortable part, and it is reported as registered rather than
argued around.

The frozen rule (§"What 'measurement noise' means", `d65f768`) required, for
Outcome **A — CONFIRMED**, that the whole bootstrap interval lie inside the
measured noise band **and** `p > 0.05`. In the primary cell:

| quantity | value |
|---|--:|
| noise band `NB`, from `quiescent_b`'s CI | **0.026787** |
| band | [0.973213, **1.026787**] |
| `xsock` CI | [**0.972931**, 1.026084] |
| upper edge | `H − (1+NB)` = **−0.000702** ✓ inside |
| lower edge | `L − (1−NB)` = **−0.000283** ✗ **outside** |
| `p` | 0.239 ✓ |

**Outcome A fails on the lower edge by 2.8×10⁻⁴.** The interval's *upper* bound —
the one that would indicate a residual tax — sits comfortably inside the band.
What falls outside is the *lower* bound, i.e. the possibility that the victim is
very slightly **faster** with a cross-socket streamer than without one. The rule
I froze is two-sided, because it had to be able to catch subcase C2 (an
anomalous speedup), and a two-sided rule is what I am held to.

So the registered verdict on the primary cell is **C — INCONCLUSIVE**, and
per the pre-registration **C does not license the phrase "measurement noise."**

Two things must be said alongside it, and neither is a reinterpretation:

- **The secondary 4096 KB cell returns Outcome A cleanly.** `never`/4096:
  `S` = 0.99344, CI [0.98247, 1.00320], entirely inside its band [0.98, 1.02],
  `p` = 0.209. The pre-registration designated `always`/4096 as primary
  *before any data existed*, and it is not open to me to relocate the primary
  cell now that the other one is more favourable. Recorded as a consistency
  check, **not pooled**, exactly as registered.
- **Neither 4096 KB cell shows a residual tax.** Outcome **B** required
  `L > 1 + NB` and `p ≤ 0.05`; the measured `L` is 0.973 and 0.982, and `p` is
  0.24 and 0.21. B is nowhere near firing. The C verdict is a verdict about the
  *resolution of the instrument*, not about the existence of a tax.

The 512 KB cells both return C as well, and should not be read as evidence
either way: `always`/512 has a noise band of **0.0538** (its own negative
control disagreeing with `quiescent_a` by 3.4%) and `never`/512's `xsock`
interval straddles the upper edge at `S` = 1.001. `AMD_L3OCC_PREREG_2026-08-30.md`
already recorded that at that working-set size the victim's quiescent spread is
large enough to swamp the signal; this campaign reproduces that.

## 4. Certification verdict: **NOT CERTIFIED**

Against my own frozen gate set: **10 of 12 pass, 2 fail.**

| gate | verdict | evidence |
|---|---|---|
| **G0** same-socket control | **PASS** | `other` = 1.3249× in [1.20, 1.40]; §1 |
| **G1** victim pinning | **PASS** | `Cpus_allowed_list == "0"` and every sampled realized CPU `== 0`, 400/400 runs |
| **G2** streamer placement | **PASS** | exactly 7 worker threads inside the requested list in 240/240 co-run runs; requested cores span exactly one L3 domain; that domain equals the victim's for `same` and is disjoint for `other`/`xsock` |
| **G3** socket | **PASS** | `xsock` cores all `physical_package_id == 1`, `same`/`other` all `== 0`, victim `== 0`, every run |
| **G4** realized NUMA placement | **FAIL — mis-specified** | see §5 |
| **G5** rate match | **PASS** | `xsock` 24.38 vs `same` 24.26 GB/s = **+0.49%**, against a ±10% tolerance |
| **G6** SMT / boost | **PASS** | `smt/control = on`, `smt/active = 1`, `boost = 1`, 400/400 runs |
| **G6b** frequency | **FAIL — mis-specified** | see §5 |
| **G7** noise band | **PASS** | `NB` = 0.0268 ≤ 0.10 in the primary cell |
| **G8** liveness | **PASS** | 400 runs, 0 without a `VICTIM` line, 20 per cell, 0 quiescent runs with nonzero streamer bandwidth |
| **G9** THP | **PASS** | `thp_readback == thp_requested`, 400/400 |
| **G10** positive control | **PASS** | `same` = 31.154× ≥ 10× |

Both blocking gates that failed are blocking, so **the campaign is NOT
CERTIFIED.** That is the answer, and it is a defect in my pre-registration
rather than in the measurement — which is a distinction this project records
rather than uses as an escape hatch (`BERGAMO_BACKINVAL_PREREG`'s P1 is the
precedent: "recorded as mis-specified", not converted into a pass).

**What the two failures do and do not touch.** Neither is a placement failure.
G2, G3 and G5 — the gates that actually establish that the streamer ran where it
was asked to, on the socket it was asked to, at the rate the other arms ran at —
all pass on all 240 co-run runs. The stream's memory placement passes
absolutely: **240/240 runs show `{"2": 114688}`**, i.e. all 448 MB on the CXL
node and nothing anywhere else, with zero `FATAL`s from the binary's own
`move_pages()` check.

## 5. The two mis-specified gates, diagnosed and answered with fresh instruments

Both remedial diagnostics are **post-hoc and disclosed as such**
(`broker/amd_xsocket_gatecheck.py`, `data/.../d23_gatecheck.jsonl`, n=5 per
cell). They answer the questions the gates asked. **They do not re-judge the
claim** — §3's verdict is fixed by the frozen rule on the frozen data and is not
revisited here.

### G4 — the instrument could not see a 512 KB working set

G4 required ≥99% of the victim's pages on node 0. The runner's histogram
ignores mappings smaller than 1024 pages, so that it reports the workload's own
mapping rather than library noise. A 4096 KB victim is 3073 pages and registers;
a **512 KB victim's working set is 384 pages** and is invisible to it. The split
is perfectly clean and confirms the diagnosis:

| WSS | `victim_numa_pages`, all 200 runs |
|---|---|
| 4096 KB | `{"0": 3073}` — **100% on node 0** |
| 512 KB | `{}` — nothing above the filter, scored 0% |

So **the primary cell passes G4 as registered, at 100%**, and the gate failed
only on the 512 KB cells, where it measured its own filter.

**D2 answers the question without the filter.** Unfiltered, the victim's pages
are `{0: 439, 1: 457}` at 512 KB and `{0: 3113, 1: 457}` at 4096 KB. The
node-1 component is **457 pages in every run at every size** — size-invariant,
therefore not the working set. Read out of `numa_maps` directly, it is
`libc.so.6` (~400 pages), `ld-linux-x86-64.so.2`, `libnuma.so.1`, the victim's
own text, heap and stack, all page-cache-resident on node 1 with `mapmax` 99–110
(i.e. shared with ~100 other processes on the host). It is read-only,
~1.8 MB, and **identical in all five arms**, so it cannot differentiate
placements. The victim's working set is on node 0 at both sizes.

A note against my own gate: ≥99% was the wrong threshold for an *unfiltered*
view, which would fail even the primary cell at 87.2%. The correct registered
quantity is "the working-set mapping is 100% on node 0", which is what the
filtered view reports and what the artifact shows.

### G6b — the gate compared its own sampling schedule

G6b required each arm's median core-0 frequency to be within ±10% of the
quiescent arm's. Measured:

| arm | median core-0 freq (pre-victim sample) |
|---|--:|
| `quiescent_a`, `quiescent_b` | **3.100 GHz** |
| `same`, `other`, `xsock` | **1.500 GHz** |

A 51.6% split, perfectly correlated with placement — which looks alarming until
you look at *when* the sample is taken. The runner reads it, as the parent
harness does, **before the victim starts**. In a co-run arm that read follows the
`SETTLE = 2 s` sleep, during which core 0 is idle and `schedutil` drops it to
its 1.5 GHz minimum. In a quiescent arm there is no sleep and core 0 is still
boosted from the previous run. The gate was comparing whether a 2-second sleep
had happened, not the frequency the victim ran at.

**D3 samples core-0 frequency during the victim's measured window**, in a
quiescent arm and an `xsock` arm, at both sizes:

> **3.100 GHz in every one of 20 samples, in every arm, at both working-set
> sizes.**

There is no frequency difference between the arms while the victim is being
measured. The confound G6b existed to exclude **is excluded by measurement.**
Two further reasons it could not have driven the result: the metric is
`cyc_per_access`, denominated in cycles rather than time, so a frequency shift
largely cancels; and the victim's first second is a warmup excluded from the
measurement (`-W 1`), which covers any ramp.

## 6. The CXL-node confound: measured, and it runs the *other* way

This was the design risk the pre-registration was required to address, because
"cross-socket" and "further from the CXL device" could have been one variable
wearing two names. On this machine they are not, and the reason is worth stating
precisely.

**The memory never moves.** `alloc_wb_cxl()` binds the stream buffer to node 2
with `mbind(MPOL_BIND | MPOL_MF_STRICT)` and verifies every 64 MB with
`move_pages()`. All three placements stream from the same node 2.
**240/240 runs verified from `/proc/<pid>/numa_maps`: `{"2": 114688}`.**
(Also confirmed: `-N 2` on the streamer command line is **inert** for `wb_load`
— the node comes from the compile-time `CXL_NUMA_NODE` — so it cannot drift.)

**What moves is the CPU-to-device path, and it favours the arm under test.**
The firmware advertises node 2 at distance **60 from node 0** and **50 from
node 1** (node 2's own `255 255 10` row is the ordinary SLIT artifact for a
memory-only node and carries no information). Diagnostic **D1** measured it
rather than trusting it — single-thread `wb_load` from node 2:

| core | package | GB/s (n=3) |
|---|---|--:|
| 1 | 0 | 12.856 |
| 9 | 0 | 12.844 |
| **129** | **1** | **16.176** |

**The other socket is 25.9% faster to the CXL device than the socket the
published arms streamed from.** The SLIT is telling the truth, and `common.h`
already knew it (`AGG_NUMA_NODE 1`, "closest to CXL"). So the two variables this
topology bundles point in **opposite** directions: `xsock` moves the streamer
out of the victim's L3 domain *and* moves it nearer its memory. The
cross-socket arm is therefore a **conservative** test — the streamer was not
starved into harmlessness, it was handed a shorter path and still did nothing
measurable.

Two more legs hold this up:

- **At seven threads the arms are rate-matched anyway.** `xsock` delivered
  24.38 GB/s against `same`'s 24.26 (**+0.49%**, gate G5, ±10% tolerance). The
  per-core path advantage does not show up in the aggregate because the device
  link saturates at ~24–25 GB/s from either socket, which is precisely why the
  placement comparison is clean: **identical bytes, identical rate, different L3
  domain.**
- **The `other` arm separates the variables by construction.** It changes the L3
  domain while holding socket *and* CXL distance fixed, and it lands at
  1.3249×. `xsock` changes L3 domain *and* socket *and* distance, and lands at
  0.9991×. The pre-registration named the entangled case in advance — `xsock`
  falling *materially below* `other` — and it did occur: 0.999 against 1.325.
  So, as registered, **the last 0.33× of reduction is reported but not
  attributed**: leaving the victim's L3 domain accounts for the great majority
  of the drop (31.15× → 1.32×), and this design cannot say whether the remaining
  1.32× → 1.00× is the socket boundary, the shorter CXL path, or both. Naming
  that limit is the honest end of this campaign; separating them needs a
  socket-1 streamer against a node-0-bound buffer, which is a different
  experiment.

## 7. What this settles for the paper

`PAPER_RECONCILIATION_2026-09-04.md` claim **U3** — `Sec3:152` asserting an AMD
cross-socket result no record contained — **is closed by measurement.** The arm
now exists: 400 runs, verified placement, a control reproducing the published
1.30× to +1.5%.

**The claim is neither confirmed nor refuted; it is narrowed.** The phrase
"reduces it to measurement noise" is **withdrawn**, and *not* because a tax was
found — none was, in either 4096 KB cell, by a wide margin — but because the
pre-registered equivalence rule returned **C** on the primary cell and C does
not license that phrase. Replacing a characterization with the measured value
and an explicit statement of the instrument's limit is a **narrowing**, which an
uncertified-but-sound measurement licenses; strengthening the claim would not
be, and is not done.

Wording applied to `Sec3_Measurement.tex:151–153` (before/after in §8):

> Moving the WB streamer from the victim's L3 domain to another L3 on the same
> socket reduces the slowdown substantially (1.30×); moving it to the other
> socket leaves the victim within 0.7% of its uncontended baseline
> (0.993–0.999×, n=20), inside this apparatus's own run-to-run spread.

The sentence that follows it in the draft — "The stream still traverses CXL in
these arms, so the sharp placement dependence rules out the fabric and
aggregate link bandwidth as the dominant source of the worst-case tax" —
**is now better supported than when it was written**, and is left unchanged for
page-budget reasons. D1 is why: the cross-socket streamer sat *nearer* the CXL
device, pulled the same 24.4 GB/s, and cost the victim nothing measurable. A
fabric-bandwidth mechanism cannot produce that.

## 8. Provenance

| | |
|---|---|
| host | `moscxl` (`ssh broker`), 2 sockets |
| kernel | `7.0.0-28-generic` |
| CPU | `AMD EPYC 9754 128-Core Processor`, family 25, model 160, stepping 2 |
| microcode | `0xaa00215` |
| L2 / L3 | 1024K per core (private) / 16384K per 8-core CCX |
| SMT | `control = on`, `active = 1`, 2 threads/core, 256 threads/socket |
| frequency | `schedutil`, `acpi-cpufreq`, `boost = 1`, 1.5–3.1 GHz; **measured, not pinned**, per registration |
| `perf_event_paranoid` | `-1` |
| NUMA | node 0 = socket 0 (CPUs 0–127, 256–383, 773632 MB); node 1 = socket 1 (128–255, 384–511, 774004 MB); **node 2 = CXL, no CPUs, 258020 MB** |
| node distances | `0: 10 32 60` / `1: 32 10 50` / `2: 255 255 10` |
| victim binary | `/home/domin/tmp_dutyfree_exp/bin/victim`, mtime **2026-08-23 15:24:03**, sha256 `90089579af329b44174ab35c486ee2faf5756b29cf2c18b8c3edfebddd92109c` |
| streamer binary | `…/bin/aggressor`, mtime **2026-08-23 15:24:03**, sha256 `583257f526e308b22a3a7c83004dd4059c832c37e5f02307c01a3e410645bc3a` |
| victim command | `victim -c 0 -w {512,4096} -P -d 3 -W 1` |
| streamer command | `aggressor -m wb_load -t 7 -c {1-7 \| 9-15 \| 129-135} -N 2 -s 64 -d 10` |
| runner | `broker/amd_xsocket.py 20 amd_xsocket.jsonl` |
| analyzer | `analyze_amd_xsocket.py`, thresholds as module constants, frozen at `d65f768` |
| start | 2026-09-04 16:34:20 UTC, load average 0.54 / 1.21 / 0.77 at launch |
| duration | 400 runs, ~52 min |
| machine state on exit | THP restored to `madvise`; governor, boost and `perf_event_paranoid` left as found; no module loaded, no memory offlined, no reboot |

**Artifacts** in `data/amd_xsocket_2026-09-04/`: `amd_xsocket.jsonl` (400 runs,
every record carrying its own realized placement), `…provenance.json`,
`d1_distance.jsonl` (D1), `d23_gatecheck.jsonl` (D2/D3), `run.log`,
`agg_logs.tar.gz` (all 240 streamer logs).

**Citizenship.** 8 of 512 threads at a time (1.6%); the runner refuses to start
above a 1-minute load average of 1.0; no other user was on the machine
(`who` empty, load 0.00 before launch).

## 9. Limits that must travel with this result

1. **The campaign is NOT CERTIFIED** (§4), on two mis-specified gates whose
   questions are separately answered (§5). Do not cite it as certified.
2. **The registered verdict is C — INCONCLUSIVE** (§3), by 2.8×10⁻⁴ on the
   lower edge of the noise band in the primary cell. The secondary 4096 KB cell
   returns A and is **not pooled** with it. Anyone quoting "0.993–0.999×" must
   also say that the pre-registered rule declined to call it noise.
3. **`n = 20`, one host, one microcode, unfrozen governor.** Matched to
   `bergamo_backinval.py` deliberately (`AMD_XSOCKET_PREREG` §"On n" — the AMD
   family uses n=6, n=10 and n=20 in different places, and this is the n of the
   harness that produced the number under test).
4. **The socket boundary and the CXL path length are not separated** (§6). The
   31.15× → 1.32× drop is attributed to leaving the victim's L3 domain; the
   1.32× → 1.00× remainder is reported unattributed.
5. **The 512 KB cells adjudicate nothing.** Noise band up to 0.0538, and the
   `same`-CCX cell is wide (IQR 14–25) in a way `BERGAMO_BACKINVAL_OUTCOME`
   addendum 1 already attributed to the factorial context.
6. **No mechanism is offered for why cross-socket is free.** This campaign
   measured a placement dependence; it did not instrument the L3, CAT or
   occupancy, deliberately (`AMD_XSOCKET_PREREG` §"What is deliberately not
   done"). `AMD_L3OCC_OUTCOME` and `AMD_CATOCC_OUTCOME` are where mechanism
   lives.
7. **`n=1` values were seen before the registered run**, during a plumbing
   check, and are disclosed in `AMD_XSOCKET_PREREG` addendum 0 along with the
   fact that the thresholds were already frozen in `d65f768` at that point.
   The plumbing data is not pooled, analyzed or cited.

## 10. Handed back --- index, ledger and reconciliation wording

`INDEX.md` and `A1_PROVENANCE_LEDGER_2026-08-28.md` were **not edited**; a
worker is active in both. No `*_PREREG_*` file other than this campaign's own
was touched. Nothing under `gem5/` was built, modified or launched, and no
simulation was started --- this is a silicon campaign.

**One disclosure.** The `linux` submodule gitlink was already staged in the
index by another worker when `c34305f` was made, so that commit swept it up
alongside this campaign's artifacts. No content of this campaign's is affected
and no other worker's work was lost --- the worktree state is unchanged and it is
the state they had staged. It was already noticed and registered independently
in `081bc3d`, and `c34305f` is no longer `HEAD`, so it is recorded here rather
than rewritten.

### For `INDEX.md`, the curated "Start here" table

| document | what it settles |
|---|---|
| `AMD_XSOCKET_OUTCOME_2026-09-04.md` | **NOT CERTIFIED (10/12 gates), registered verdict `C` --- INCONCLUSIVE.** Closes `PAPER_RECONCILIATION_2026-09-04.md`'s **U3** by measurement: the AMD **cross-socket** placement arm that `Sec3:152` asserted and no record contained now exists. 400 runs on `moscxl`, reusing `bergamo_backinval.py`'s **unmodified 2026-08-23 binaries**, command lines, metric and **n=20**. **Read the control first**: other-CCX same-socket reproduces at **1.3249×** against the published 1.305× (**+1.5%**), every 4096 KB arm within 1.5%, and `never`/4096 same-CCX to **0.03%** --- so the arms are comparable. **There is no cross-socket tax**: `0.9991×` (`always`/4096) and `0.9934×` (`never`/4096) of the uncontended baseline, `p` = 0.24 / 0.21 where the same-CCX arm rejects at 7e−08; in `never`/4096 the cross-socket victim sits **0.007 cyc/access** from the no-streamer negative control, and in the primary cell it is closer to `quiescent_a` than the negative control is. **But the registered verdict is `C`, not `A`, and must be quoted as such**: the primary cell's bootstrap interval missed the measured noise band's **lower** (faster-than-baseline) edge by **2.8e−4**, the rule was two-sided by design, and `C` does **not** license the phrase "measurement noise". Outcome `B` (a residual tax) is nowhere near firing. The secondary 4096 KB cell returns `A` cleanly and is **not pooled** --- the primary cell was designated before any data existed. **Two gates FAIL and are recorded as mis-specified, not as passes** (proposed `F17`): `G4`'s page histogram cannot see a 512 KB working set, so it scored the 512 KB cells 0% while the primary cell passes at **100% on node 0**; `G6b` sampled core-0 frequency *before* the victim started, so it compared its own 2-second settle sleep (1.5 GHz co-run vs 3.1 GHz quiescent). Both questions are answered by post-hoc diagnostics: the 512 KB working set **is** on node 0, with the size-invariant 457-page node-1 residue identified as `libc`/`ld.so`/`libnuma` text shared with ~100 processes, and core 0 runs at **3.100 GHz in every arm** during the measured window. **The CXL confound is measured, not assumed, and runs the *other* way**: socket 1 is **25.9% faster** to the CXL device (16.18 vs 12.85 GB/s single-thread, confirming the SLIT's 50-against-60), so the cross-socket streamer was **advantaged, not starved** --- a conservative test --- while at 7 threads the arms are rate-matched to **+0.49%** because the device link saturates from either socket. Stream memory verified on **node 2 in 240/240 runs**. **One limit is named rather than resolved**: `xsock` falls materially below `other` (0.999× against 1.325×), so leaving the victim's L3 domain accounts for 31.15× → 1.32× and the remaining **1.32× → 1.00× is reported unattributed** --- socket boundary and CXL path length are not separated by this design. Also narrows `AMD_NARROWMASK_OUTCOME`'s `S6.6` instruction: absolute AMD magnitudes do not survive a **host rebuild**, but within a fixed host state and fixed binaries they reproduce to ≤1.5% |
| `AMD_XSOCKET_PREREG_2026-09-04.md` | Frozen at `d65f768` before launch; addendum 0 at `c7b8d1c`, also **pre-launch**. **First document in this project to operationalize "measurement noise"**, which the corpus had left as a bare phrase: the noise band is *measured*, not chosen --- `NB = max(0.02, |CI95(quiescent_b) − 1|)`, i.e. the largest apparent slowdown the apparatus manufactures from **no effect at all** at n=20, obtained by adding a second, temporally separated quiescent cell as a negative control. Twelve fail-closed gates; three outcomes (confirmed / refuted-with-residual / inconclusive) each with its **licensed paper wording written in advance**, including an explicit refusal to search for a framing that preserves the claim. Records that the brief's recollection of "n=5 and n=30" matches no AMD record (the family uses n=6, n=10 and n=20) and that **n=20** is the n of the harness being reused. **Addendum 0 is worth reading as process**: it corrects gate `G2` before launch (`aggressor.c` runs 7 pinned workers **plus an unpinned coordinator**, so the gate as frozen would have failed all 240 co-run runs for an accounting reason) and **discloses that proving the plumbing meant seeing n=1 values across the factorial**, records them, and states that the thresholds were already frozen in git before the peek |

### For `INDEX.md`, "Withdrawn during 2026-09-03→04 (claims, not documents)"

| withdrawn | by | why |
|---|---|---|
| **"moving it to the other socket reduces it to measurement noise"** --- `Sec3_Measurement.tex:152`, the AMD cross-socket placement claim | `AMD_XSOCKET_OUTCOME_2026-09-04.md` | it had **no artifact behind it** (`PAPER_RECONCILIATION_2026-09-04.md` U3); the paper held a measured same-socket 1.30× at `Sec7:313` and an unmeasured cross-socket assertion in `Sec3`. Now measured on matched apparatus: **`0.993`--`0.999×` of baseline at n=20**, with the same-socket control reproducing at 1.3249×. **Withdrawn is not refuted** --- no residual tax was found, and Outcome `B` did not come close. The phrase goes because the **pre-registered equivalence rule returned `C`** (interval outside the noise band's lower edge by 2.8e−4) and `C` does not license it. Replaced in the draft by the measured value plus the instrument's limit. **Do not restore the phrase without a certified Outcome `A`** |
| **"the absolute AMD magnitudes are not reproducible while its argument is"** as a statement about the apparatus --- `AMD_NARROWMASK_OUTCOME_2026-08-30.md` §"Reproduction" | `AMD_XSOCKET_OUTCOME_2026-09-04.md` §1 | **narrowed, not withdrawn, and the `S6.6` instruction to the paper stands.** That document compared pre-rebuild published figures against a post-rebuild re-measurement. Measured across two post-rebuild dates on the same binaries and platform state, the magnitudes reproduce to **≤1.5%** and one cell to **0.03%**. Correct scope: magnitudes do not survive a **host rebuild**; they are not intrinsically irreproducible |

### For `INDEX.md`, housekeeping

- Document count **215 → 217** (this outcome and its pre-registration). It is
  derived, not authored --- re-derive rather than trusting either figure.
- **"Runners and analyzers … 17 pairs currently" → 18.** The new pair is
  `broker/amd_xsocket.py` + `analyze_amd_xsocket.py`, with thresholds as module
  constants per the stated convention. It **breaks the `run_*.sh` naming rule**
  and does so deliberately: it is a sibling of `broker/bergamo_backinval.py`,
  which is a Python runner living in `broker/` because it must be copied to the
  AMD host, and matching the parent harness mattered more than matching the
  filename convention. Two further scripts are diagnostics, not runners, and
  should not be counted as pairs: `broker/amd_xsocket_distance_probe.sh` (D1,
  pre-registered) and `broker/amd_xsocket_gatecheck.py` (D2/D3, post-hoc).
- The **`AMD_*` / `BERGAMO_*` family** line gains this campaign; it is the first
  addition to the AMD residual thread since 2026-08-30.
- `broker/README.md`'s table lists the four AMD runners and now under-reports;
  a row for `amd_xsocket.py` (produced
  `data/amd_xsocket_2026-09-04/amd_xsocket.jsonl`, the 5-placement sweep) is
  offered but **not applied**, that file being outside this campaign's remit to
  restructure.

### For `A1_PROVENANCE_LEDGER_2026-08-28.md`

**A binding row**, for "New numbers added to the paper this week, and their
bindings":

| number | binding | artifacts | recomputation | selection |
|---|---|---|---|---|
| `Sec3_Measurement.tex:151-155` --- AMD cross-socket `0.993`--`0.999×`, and the same-socket `1.30×` now cited in `Sec3` as well as `Sec7:313` | `data/amd_xsocket_2026-09-04/amd_xsocket.jsonl` (**400** records, 20 per cell over 2 THP × 2 WSS × 5 placements). Runner `broker/amd_xsocket.py`; judged by `analyze_amd_xsocket.py` against `AMD_XSOCKET_PREREG_2026-09-04.md` frozen at `d65f768`. Diagnostics `d1_distance.jsonl`, `d23_gatecheck.jsonl`; provenance `amd_xsocket.jsonl.provenance.json`; all 240 streamer logs in `agg_logs.tar.gz` | **all committed** (`c34305f`), runner and analyzer committed **before** launch (`d65f768`, `c7b8d1c`). Binaries **not** in-tree by design (`broker/README.md`): `victim` sha256 `90089579…` and `aggressor` sha256 `583257f5…`, both mtime 2026-08-23 15:24, recorded per run | reproducible by `analyze_amd_xsocket.py data/amd_xsocket_2026-09-04/amd_xsocket.jsonl`. Bootstrap is seeded (**20260904**), so the interval that decided the verdict is deterministic | **VERIFIED --- 400/400.** Every record emits a `VICTIM` line, 20 per cell, **none dropped**; 0 quiescent runs with nonzero streamer bandwidth; realized placement recorded **per run** and verified from the artifact rather than the launcher (`S5.1`). What this row does **not** certify: the campaign itself is **NOT CERTIFIED** on gates `G4` and `G6b` (proposed `F17`), and the number is a **`C`-verdict** number |

**A defect row**, proposed as **`F17`** --- the ledger states `F17` is the next
free number; if a worker has taken it since, renumber:

| # | defect | date | status |
|---|---|---|---|
| `F17` | **A fail-closed gate whose instrument cannot observe the quantity at one of the levels its own campaign sweeps, or whose sample is taken at a point in the schedule that differs by arm.** Two instances, both in `AMD_XSOCKET_PREREG_2026-09-04.md`, both caught **by the gate failing** rather than by review, and both leaving that campaign **NOT CERTIFIED**. (1) `G4` required ≥99% of the victim's pages on node 0 and read a histogram that filters mappings below 1024 pages; the campaign sweeps a **512 KB (384-page)** victim, which is invisible to it, so 200 of 400 runs scored 0% while the 4096 KB cells passed at 100%. The ≥99% threshold was **also** wrong for an unfiltered view, which fails even the primary cell at 87.2% because ~457 pages of `libc`/`ld.so` text are page-cache-resident on the other socket. (2) `G6b` required per-arm core-0 frequency to match the quiescent arm within 10% and sampled it **before the victim started** --- which in a co-run arm follows a 2-second settle sleep that lets core 0 drop to its 1.5 GHz minimum, and in a quiescent arm does not. It measured its own sampling schedule and split 3.1 GHz against 1.5 GHz with perfect correlation to placement. **Same root cause as two prior instances, which is why this is offered as a class rather than as two mistakes**: `BERGAMO_BACKINVAL_PREREG`'s `P1` was recorded as mis-specified for calibrating a threshold in one configuration and applying it in another, and `AMD_L3OCC_PREREG` opens by naming the recurring cause in as many words --- *"the instrument does not measure the quantity in the claim."* Distinct from **`F12`** (a criterion a crashed run could satisfy): `F12` is a gate too weak to fail, this is a gate that fails for a reason unrelated to what it tests. **Both questions were answered by post-hoc diagnostics** (`broker/amd_xsocket_gatecheck.py`) and both came back clean --- working set on node 0 at both sizes, 3.100 GHz in every arm during the measured window --- so **no measurement is impeached and no number moves.** What is impeached is the certification. **Prevention worth registering**: a gate should be dry-run against every level of its campaign's own sweep before the campaign is frozen, and any gate reading a point-in-time sample must state where in the run schedule the sample is taken. Logged **open**; the remedy is a convention, not a patch, and the affected campaign is closed | 09-04 | **open** |

### For the next reconciliation pass, on `PAPER_RECONCILIATION_2026-09-04.md`

`PAPER_RECONCILIATION_2026-09-04.md` was **not edited**. Its §7 `U3` row and its
"Unlocatable claims --- updated" list both stand to be revised:

> **`U3` --- resolved 2026-09-04** by `AMD_XSOCKET_OUTCOME_2026-09-04.md`, and
> resolved by the established response: an unbacked claim replaced by a
> measured campaign on matched apparatus. `Sec3:152` no longer asserts an
> unmeasured cross-socket result. **Five remain**: `U1`, `U2`, `U5`, `U6`,
> `U8`. Note for the count: `U3` is the item the earlier pass twice identified
> as the one where "the established response would apply", and it did apply ---
> though the campaign it produced is `NOT CERTIFIED` and its verdict is
> `INCONCLUSIVE`, so the draft now carries a **measured, narrowed** claim
> rather than a confirmed one.

Page budget for §8 of that document, re-measured after this edit:

| | Pages | Overfull `\hbox` | Overfull `\vbox` | Undefined refs |
|---|---:|---:|---:|---:|
| Baseline (verified here before editing) | 22 | 7 | 0 | 0 |
| After this edit | **22** | **7** | **0** | **0** |

The same seven boxes at **identical widths** (37.82, 95.45, 33.58, 65.03, 2.85,
42.86, 80.55 pt). No new overfull or underfull boxes, no page added at the
22-page limit, `latexmk` exit 0. Every percent sign in the new prose is `\%`,
and `Sec3_Measurement.tex` was re-checked for unescaped `%` in non-comment lines
after the edit: **none**.
