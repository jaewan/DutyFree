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
