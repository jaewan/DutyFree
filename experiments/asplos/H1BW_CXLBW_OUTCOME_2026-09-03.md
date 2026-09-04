# Realistic CXL bandwidth (Campaign A) — outcome

Registered in `H1BW_CXLBW_PREREG_2026-09-03.md`. Twelve runs, all `exit: 0`,
all 72 instances `status: "ok"`, all five pre-registered gates passed on all
twelve. Analyzer `analyze_h1bw_bracket.py cxlbw 20260904`; machine-readable
record `data/gem5/h1bw_cxlbw.jsonl`. Follow-up to
`H1BW_MULTICORE_OUTCOME_2026-09-03.md` and continuous with it: the baseline
aggregates, the concurrency-over-latency identity and the `agg_bw_sum`
window-overlap caveat are all carried forward from that document rather than
re-derived.

The six 8-core cells finished 2026-09-04T12:12–12:25+09:00, at 3.01–3.23 h.
Runs are stamped `20260904` for the same reason as the baseline campaign: the
runner takes `STAMP=$(date +%Y%m%d)` in host-local time.

## The answer

**No published conclusion depends on the missing bandwidth limit.**

Every conclusion the gem5 SE bandwidth experiments license is a ratio or an
ordering, and both survive a physically realistic CXL cap intact. Imposing a
32.2581 GB/s ceiling — a real CXL 2.0 x16 link rate, 15.5x below the
unphysical 500 GB/s the model had been running at — moved no cell by more than
**3.3%**, left the ordering `H2 >= WB > prefetch-off` standing in all four
capped cells, and left the H2-over-WB ratio within **+2.8% / −1.6%** of its
uncapped value. The pre-registered alarm did not fire in any cell. This is a
clean negative and it is stated with the same confidence a positive would
have been: the campaign was run to find out, and the answer is that the
archive's absent CXL bandwidth limit is not load-bearing for anything the
paper claims.

Two things do change, and both are corrections to *mechanism and magnitude
statements*, not to conclusions:

1. **The archive's stated mechanism stays refuted, and is now refuted from the
   other side too.** The preserved REPORT explains its section-4 numbers as
   "Aggregate is CXL-path-limited (~6–8 GB/s regardless of cores)". The
   baseline campaign showed there was no CXL path limit to bind against. This
   campaign shows the stronger thing: **even when a realistic CXL limit is
   present, the aggregate is still not CXL-bandwidth-limited.** Throughput in
   this model is set by fabric concurrency and device latency, and a byte-rate
   throttle 15.5x tighter than the default costs it 0.3–3.3%. "CXL-bandwidth-
   limited" is not a description of this model with or without the limit.
2. **The 8-core H2 aggregate must not be quoted as a link rate.** The capped
   `h2_8c` cell reports 42.87 GB/s against its own realized 32.2581 GB/s
   ceiling — **132.9% of it** — which is arithmetically impossible for a
   serializing throttle. That cell is a valid certified measurement of the
   *policy comparison* and simultaneously a proof that `agg_bw_sum` is not a
   physically realizable concurrent rate at 8 cores. §"The cap as an audit of
   `agg_bw_sum`" derives the contradiction and bounds it. This does not
   disturb any ratio, because the inflation is common to the arms and, where
   it differs, it runs against H2.

The corrected statement to use wherever the 8-core magnitude appears is in
§"What this licenses, and what it does not".

## Certification verdict

**All twelve cells certified. No void cells.** `COMPLETE: 12/12 cells
certified against all four gates`, exit 0. The six 8-core cells are new; the
six 4-core cells were already certified and re-certify unchanged.

| gate | what it checks | result on the six 8-core cells |
|---|---|---|
| **G1** | every instance `status: "ok"` | PASS — 8/8 in all six, 48 instances total |
| **G2** | realized instance count == N | PASS — 8 vs N=8 in all six |
| **G3** | realized LLC == slices x 5 MiB, slice count == declared | PASS — 8 slices x 5,242,880 B = 40 MiB |
| **G4** | realized `mem_ctrls1.bandwidth` == pre-registered integer ticks/byte | PASS — **31.000000** and **16.000000**, read back from `config.ini` |
| **G5** | declared policy measurably engaged | PASS — `wb` exactly 0 bypasses; `h2` 39.7% bypass/decision, 47.4–47.6% fill suppression; `pfoff` 40.0% |

G4 is the gate this campaign exists for, and it is worth recording that it was
checkable before the runs finished: gem5 writes `config.ini` during
`m5.instantiate()`, so the realized caps were read back at 2h55m of a 3.2 h
run and did not have to be taken on trust from `MANIFEST.json`. The realized
values are exactly the two pre-registered integers, with no third value
anywhere:

- `system.mem_ctrls1.bandwidth = 31.000000` ticks/byte in the three `bwt31`
  cells -> **32.2581 GB/s**
- `system.mem_ctrls1.bandwidth = 16.000000` ticks/byte in the three `bwt16`
  cells -> **62.5000 GB/s**
- `system.mem_ctrls0.bandwidth = 2.000000` ticks/byte in **all six** ->
  500.00 GB/s, **the local DRAM range left untouched as pre-registered**

The DRAM check matters and is affirmative, not incidental: had the runner
leaked `CXL_MEM_BW` onto `mem_ctrls0`, every capped cell would be a
local-memory result wearing a CXL label, and the campaign's whole comparison
would be confounded. It did not. One line differs from the uncapped
configuration, and it is the intended one.

The base-10-to-base-2 cast warning that the pre-registration flagged as a trap
appears **32 times in the capped cells and 32 times in the uncapped ones** —
identical counts, all from cache-size parameters (`1kB`), none from the
bandwidth request. Writing the requests as bare `<integer>B/s` worked; no
warning mentions bandwidth at all.

## Results

`agg_bw_sum` is the sum of per-instance `bandwidth_gbps`, each instance's own
8 MiB over its own measured pass. `agg_bw_wall` remains retired. Ratios are
against the uncapped baseline from `H1BW_MULTICORE_OUTCOME_2026-09-03.md`
(WB/H2/pfoff = 20.09/25.11/13.27 at 4c, 31.00/43.14/26.98 at 8c).

### 32.2581 GB/s cap (31 ticks/byte)

| cell | `agg_bw_sum` | per core | vs uncapped | pre-registered band | in band? | of realized ceiling |
|---|---|---|---|---|---|---|
| `wb_4c` | 19.87 GB/s | 4.97 | 0.989x | unchanged, 0.95–1.05 | **inside** | 61.6% |
| `h2_4c` | 24.96 GB/s | 6.24 | 0.994x | unchanged, 0.95–1.05 | **inside** | 77.4% |
| `pfoff_4c` | 13.29 GB/s | 3.32 | 1.001x | unchanged, 0.95–1.05 | **inside** | 41.2% |
| `wb_8c` | 29.97 GB/s | 3.75 | 0.967x | clipped mildly, 0.75–1.00 | **inside** | 92.9% |
| `h2_8c` | 42.87 GB/s | 5.36 | 0.994x | clipped hard, 0.55–0.85 | **OUTSIDE** | **132.9%** |
| `pfoff_8c` | 26.89 GB/s | 3.36 | 0.997x | unchanged, 0.95–1.05 | **inside** | 83.4% |

### 62.5000 GB/s cap (16 ticks/byte)

| cell | `agg_bw_sum` | per core | vs uncapped | pre-registered band | in band? | of realized ceiling |
|---|---|---|---|---|---|---|
| `wb_4c` | 20.07 GB/s | 5.02 | 0.999x | unchanged, 0.95–1.05 | **inside** | 32.1% |
| `h2_4c` | 25.20 GB/s | 6.30 | 1.003x | unchanged, 0.95–1.05 | **inside** | 40.3% |
| `pfoff_4c` | 13.29 GB/s | 3.32 | 1.001x | unchanged, 0.95–1.05 | **inside** | 21.3% |
| `wb_8c` | 31.05 GB/s | 3.88 | 1.002x | unchanged, 0.90–1.05 | **inside** | 49.7% |
| `h2_8c` | 42.54 GB/s | 5.32 | 0.986x | unchanged, 0.85–1.05 | **inside** | 68.1% |
| `pfoff_8c` | 26.94 GB/s | 3.37 | 0.999x | unchanged, 0.95–1.05 | **inside** | 43.1% |

**Eleven of twelve pre-declared predictions confirmed.** The single failure is
`h2_8c` at the tight cap, and it failed in the *safe* direction — the cell did
not clip when the pre-registration said it must. §"The one failed prediction"
treats it as the substantive finding it is rather than a miss to be excused.

Inter-instance spread is 1.99–11.48% at 8 cores and window overlap floors are
79.2–96.3%, both in the same range as the baseline campaign. Slice request
balance is 1.003–1.011x. Wall times 3.01–3.23 h against the baseline's
2.95–3.16 h.

### H2 over WB, and the pre-registered alarm

The alarm fires if a capped `h2/wb` falls below 0.95x its uncapped value
(1.2500 at 4c, **1.3917 at 8c**) or inverts below 1.0. Note the 8-core
comparator is 1.3917, not 1.2500; 1.2500 is the 4-core figure and using it at
8 cores would compare against the wrong arm structure.

| cores | cap | `h2/wb` | uncapped | relative | alarm threshold | fired? |
|---|---|---|---|---|---|---|
| 4 | 32.26 GB/s | 1.2560 | 1.2500 | **+0.5%** | 1.1875 | no |
| 4 | 62.50 GB/s | 1.2557 | 1.2500 | **+0.5%** | 1.1875 | no |
| 8 | 32.26 GB/s | 1.4307 | 1.3917 | **+2.8%** | 1.3221 | no |
| 8 | 62.50 GB/s | 1.3700 | 1.3917 | **−1.6%** | 1.3221 | no |

**No alarm in any cell, and no inversion.** The ratio did not merely survive —
at the tight 8-core cap it *widened* by 2.8%, which is the direction the
competing traffic-per-useful-byte mechanism predicts, at a magnitude too small
to carry weight on its own (§"Mechanism discrimination"). `WB/pfoff` also
holds: 1.4949 and 1.5097 at 4c against 1.5132 uncapped, 1.1145 and 1.1524 at
8c against 1.1488. The ordering `H2 >= WB > pfoff` holds in all four capped
cells.

Per the pre-registration's own framing, this is the outcome that *strengthens*
H1: the ordering and the ratio have now been shown to hold both in the
unphysical 500 GB/s regime and at a realistic CXL 2.0 x16 link rate.

## Realized configuration, read back from `config.ini`

Every value from the run's own `config.ini` or `stats.txt`, never from
`MANIFEST.json` and never from the live filesystem (F9, S5.1). Provenance was
captured from the artifacts deliberately: a sibling worker holds a rebuild of
`gem5.opt` pending on these six runs, so the binary's mtime is not a stable
identifier.

| parameter | realized, 8-core cap cells | source |
|---|---|---|
| HNF (L3) slices | 8 | `system.ruby.hnf{i}.cntrl.cache` sections |
| per-slice size / assoc | 5,242,880 B / 20 | `size=`, `assoc=` |
| total LLC | 40 MiB | sum over slices |
| memory type | `SimpleMemory`, both ranges | `type=` |
| CXL latency / `latency_var` | 203 ns / 0 | `system.mem_ctrls1.latency=203000` |
| DRAM latency | 98 ns | `system.mem_ctrls0.latency=98000` |
| **CXL bandwidth** | **31.000000 / 16.000000 ticks/byte** | `system.mem_ctrls1.bandwidth` |
| **DRAM bandwidth** | **2.000000 ticks/byte (untouched)** | `system.mem_ctrls0.bandwidth` |
| CXL address range | `137438953472:274877906944` (128–256 GiB) | `range=` |
| memory controllers instantiated | exactly **two** | `[system.mem_ctrls0]`, `[system.mem_ctrls1]` |
| prefetcher sections | 152 (`wb`, `h2`) / **0** (`pfoff`) | count of `*prefetcher*` sections |
| `gem5_sha256` | `cfd37207b9b7124a…` in all six manifests | `MANIFEST.json`, and matches the live `gem5.opt` at the time of writing |
| `bench_sha256` | `cac9e27ab42448a8…` in all six | `MANIFEST.json` |

Three of these are load-bearing for what follows.

**There are exactly two memory controllers and only one of them carried
traffic.** `system.mem_ctrls0` emits **no non-zero statistics at all** in any
of the six cells — `ALL_CXL=1` routes every access to the CXL range — so the
32.2581 GB/s ceiling is not one of several parallel pipes that could be summed
into a larger aggregate. It is the whole memory system.

**The throttle is a strict serializer, confirmed from source.**
`src/mem/simple_mem.cc` computes `Tick duration = pkt->getSize() * bandwidth`,
schedules `releaseEvent` at `curTick() + duration`, sets `isBusy = true`, and
returns `false` with `retryReq = true` for any request arriving while busy. At
64-byte packets and 31 ticks/byte each packet occupies 1,984 ticks, so the
controller accepts at most one line per 1.984 ns — **32.2581 GB/s is a hard
ceiling on all reads and writes combined, not a target rate.** `simple_mem.cc`
is unmodified in the working tree, so the source read matches the binary that
produced these runs. The only modification anywhere on the memory path is
`src/python/m5/ticks.py`, which is uncommitted and dormant in this binary —
see §"Health".

**Packets are 64 B and nothing is coalesced.** `mem_ctrls1.numReads::total`
divided into `bytesRead::total` gives exactly 64.0 B per read in every cell,
so the per-packet occupancy above converts to a byte rate without residue.

## The one failed prediction, and why it is the result rather than a miss

The pre-registration declared that `h2_8c` at the 32.26 GB/s cap must clip to
0.55–0.85x, reasoning that 43.14 GB/s cannot pass through a 32.26 GB/s pipe so
the cell must fall to at most the cap. **It came in at 0.994x — 42.87 GB/s,
132.9% of its own realized ceiling.**

The prediction's arithmetic was not wrong; its premise was. It assumed that
43.14 GB/s was a rate something physical had to carry. The cell's job was to
test a claim about the paper, and it did that — but it also, unplanned, tested
the campaign's own metric, and the metric is what failed. Two readings are
available and the artifacts separate them.

*The cap did not bind.* Refuted below: it bound hard.

*`agg_bw_sum` is not a concurrent rate.* Supported, and provable from the
artifacts. §"The cap as an audit of `agg_bw_sum`".

## The cap bound hard, and the fabric absorbed it

The throttle was not inert. It applied large and monotone back-pressure at the
memory interface in every capped cell, scaling correctly with cap tightness.
All figures whole-program, from `stats.txt`, 8 cores:

| arm | quantity | uncapped | 62.50 GB/s | 32.26 GB/s |
|---|---|---|---|---|
| `wb` | SNF `datOut` mean stall (ticks/msg) | 24.9 | 765.9 (30.7x) | **2276.4 (91.4x)** |
| `h2` | | 11.6 | 426.4 (36.8x) | **1398.1 (120.5x)** |
| `pfoff` | | 0.018 | 0.6 (33.6x) | 1.9 (106.2x) |
| `wb` | SNF `requestToMemory` mean stall | 786.8 | 1593.7 (2.03x) | **2544.2 (3.23x)** |
| `h2` | | 461.3 | 1169.1 (2.53x) | **2078.6 (4.51x)** |
| `pfoff` | | 213.3 | 508.9 (2.39x) | 979.8 (4.59x) |
| `wb` | SNF `reqIn` messages (rises with retries) | 4,169,541 | 1.027x | 1.056x |
| `h2` | | 2,788,564 | 1.014x | 1.022x |
| `pfoff` | | 2,680,651 | 1.000x | 1.000x |
| `wb` | `simSeconds` | 0.085570 | 1.0052x | 1.0116x |
| `h2` | | 0.083896 | 1.0009x | 1.0030x |
| `pfoff` | | 0.090757 | 1.0003x | 1.0005x |

Queueing at the memory interface rose by up to **120x**. The throttle was
doing exactly what a byte-rate throttle does. And yet:

**The traffic volume did not change and the delivered rate barely did.** Total
CXL controller bytes are 0.996–1.001x their uncapped values in all six cells —
the cap changed the *timing* of the traffic and not one byte of its *volume* —
while `agg_bw_sum` moved 0.3–3.3%. The entire effect of a 15.5x tighter
interconnect landed in queues that had room for it.

### Why: the throttle barely moves per-transaction latency

The baseline campaign established that in this model aggregate throughput is
*identically* `concurrency x 64 B / latency`, with concurrency a fabric-budget
quantity and latency a policy quantity. The independently measured half of
that identity is the latency, from the HNF `inTransLatHist` histograms, and it
is the half that explains the result:

| cell | HNF read transaction latency | change | observed `vs uncapped` |
|---|---|---|---|
| `wb_8c` @ 32.26 | 224.7 -> 230.3 ns | **+2.5%** | 0.967x |
| `h2_8c` @ 32.26 | 163.5 -> 168.6 ns | **+3.1%** | 0.994x |
| `pfoff_8c` @ 32.26 | 134.3 -> 134.4 ns | +0.1% | 0.997x |
| `wb_8c` @ 62.50 | 224.7 -> 221.6 ns | −1.4% | 1.002x |
| `h2_8c` @ 62.50 | 163.5 -> 168.5 ns | +3.1% | 0.986x |
| `pfoff_8c` @ 62.50 | 134.3 -> 134.4 ns | +0.1% | 0.999x |

**A 15.5x tighter interconnect changed per-transaction home-node latency by at
most 3.1%.** That is the whole explanation, and the reason is scale: the
throttle's per-packet occupancy is 1.984 ns against a 203 ns device latency, a
factor of 102. A serializing throttle two orders of magnitude cheaper per
transaction than the latency it sits behind cannot move the latency term
unless it saturates, and the fabric has the slack to absorb the queueing it
does create — HNF transaction buffers sit at 42.0–44.1% occupancy and L1
MSHRs at 28.0–29.4%, unchanged from the baseline campaign's 42.5–43.0% and
28.3–28.7%. Nothing became a bottleneck, so nothing throttled.

**One caution on how not to present this.** The analyzer's `hnf_concurrency`
is *derived* from `agg_bw_sum` by Little's law
(`concurrency = agg_bw_sum / 64 B x latency`), so writing
`(concurrency / latency)` and comparing it against the observed ratio
reproduces the observed ratio to 0.00 pp in all six cells **by construction**.
That agreement is an identity, not a confirmation, and it must not be reported
as a predictive fit. What the decomposition legitimately does is attribute the
observed change between an independently measured latency term and an inferred
concurrency term: at the tight cap WB lost 3.3% while paying 2.5% more latency
(so its inferred concurrency fell 1.0%, 108.9 -> 107.8 lines), and H2 lost
0.6% while paying 3.1% more latency (so its inferred concurrency *rose* 2.5%,
110.2 -> 113.0 lines). The latency figures are measurements; the concurrency
figures are bookkeeping.

`pfoff` is the arm to which the identity applies least. The baseline campaign
showed it is not fabric-limited at all but core-limited, at 22% of the HNF
budget and 15% of the L1 MSHR budget, so its throughput is set by how fast an
O3 core generates demand misses without a prefetcher. Its 0.1% latency change
under a 15.5x tighter cap is consistent with that and is the cleanest control
in the campaign: the arm that touches the fewest shared structures notices the
cap least.

## The cap as an audit of `agg_bw_sum`

The `h2_8c` cap cell yields an inequality that the artifacts settle on their
own, and it is the most consequential thing in this document after the answer.

1. The measured pass delivers `8 x 8 MiB = 67,108,864` useful bytes. Each
   instance divides its own 8 MiB by its own window; `agg_bw_sum` sums those.
2. Every one of those bytes crossed `mem_ctrls1`. The baseline campaign's
   LLC-residency result establishes this and it reproduces here:
   `cxl_read_over_demand` is **1.016x** for `h2_8c` @ 32.26, so CXL reads are
   the two-pass demand plus 1.6%, and the 40 MiB LLC supplied none of it.
3. `mem_ctrls1` accepts at most one 64 B line per 1,984 ticks, and
   `mem_ctrls0` carried nothing.
4. Therefore delivering 67,108,864 bytes requires at least
   `67,108,864 x 31 = 2,080,374,784` ticks = **2.0804 ms** of controller time,
   before any writeback or over-fetch traffic is charged.
5. The **widest** single measured window in that cell is **1.5772 ms**.
6. `1.5772 ms < 2.0804 ms`. The eight measured passes therefore **cannot** all
   lie inside a common window; their union must span at least 2.0804 ms, which
   is 1.32x the widest single window.

**`agg_bw_sum` = 42.87 GB/s is consequently not a concurrent delivered rate in
this cell.** The rate averaged over the union of the windows is at most
32.2581 GB/s, so the reported figure is high by at least **1.329x**. The
corroborating metric the baseline campaign recommended in place of
`agg_bw_wall` — total bytes over the widest single instance window — gives
42.55 GB/s here and fails the same test. And the reported window overlap floor
of 90.7% is refuted directly: that bound is derived from per-CPU `numCycles`
skew, which measures *program-end* alignment, and this cell shows program-end
alignment does not bound measured-pass alignment as tightly as was assumed.

Three things follow, and the first is the reason this is not a retraction.

**Ratios are unaffected, and the bias runs against H2.** A common inflation
factor cancels in `h2/wb`. Where it is not common it favours the conservative
reading: `wb_8c`'s overlap floor is 79.2% against `h2_8c`'s 90.7%, so WB is
the *more* staggered arm and the more inflated one, which means the true
H2-over-WB advantage is at least the 1.4307 reported. Every ratio in this
document is safe; only the magnitudes are not.

**This is a positive result about the cap, not only a negative about the
metric.** A physically realistic ceiling functions as an independent audit that
an unphysical 500 GB/s ceiling could not perform. At 500 GB/s any reported
aggregate is admissible and the metric is unfalsifiable; at 32.2581 GB/s the
metric has to be consistent with the physics, and in exactly the one cell
where the arithmetic bites it is not. Running the cap bought a validity check
on the whole harness, which was not what it was registered to do.

**It generalises to a measured bound on the in-window traffic ratio**, below.

## Mechanism discrimination

The pre-registration required the outcome to discriminate between two
mechanisms rather than be read one way after the fact. The result is a clean
refutation of one, and an honest failure to establish the other.

- **Delivered-rate arithmetic** — a cap charges against delivered rate, so H2
  (43.14, above the 32.26 ceiling) must clip hard and WB (31.00, just below
  it) must clip mildly. **Refuted, decisively.** It predicted `h2_8c` at
  <=0.748x and the cell delivered 0.994x, a 33% miss and the campaign's only
  failed prediction. Its premise — that the reported aggregate is a rate the
  link must carry — is exactly what §"The cap as an audit" disproves.
- **Traffic-per-useful-byte** — a cap charges for controller traffic, and WB
  moves 1.990 controller bytes per useful byte against H2's 1.325 and
  prefetch-off's 1.278, so WB loads the link 1.50x harder per useful byte and
  should be penalised more. **Not established, and not refuted.**

The traffic mechanism is *visible*, in the one place that does not depend on
windowing. Back-pressure at the memory interface orders exactly as controller
traffic does, across all three arms and both caps:

| arm | controller bytes per useful byte | `datOut` stall @ 32.26 | rank |
|---|---|---|---|
| `wb` | 1.990 | 2276.4 ticks/msg | most loaded, most back-pressure |
| `h2` | 1.325 | 1398.1 | middle in both |
| `pfoff` | 1.278 | 1.9 | least in both |

WB pushes 1.50x H2's bytes and absorbs 1.63x its stall per message. That is
the traffic mechanism operating. **But it stops at the queues and never
reaches delivered bandwidth**, which is why it cannot be established from the
clip magnitudes:

| arm | clip @ 32.26 GB/s | clip @ 62.50 GB/s |
|---|---|---|
| `wb` | **−3.3%** | +0.2% |
| `h2` | −0.6% | **−1.4%** |
| `pfoff` | −0.3% | −0.1% |

At the tight cap WB is the most-clipped arm, which is the traffic mechanism's
direction. At the loose cap H2 is, which is not. **The ordering flips between
the two caps, and every figure is at most 3.3% against inter-instance spreads
of 2.0–11.5% and n = 1 per cell with no seed replication and no variance
estimate of any kind.** A −3.3% against a −0.6% cannot be separated from a
−1.4% against a +0.2% at that resolution. Reporting the 32.26 GB/s column
alone as confirmation of the traffic mechanism would be reading one cap and
ignoring the other.

**Verdict: the discrimination cannot be made cleanly from these artifacts.**
Delivered-rate arithmetic is refuted. Traffic-per-useful-byte is shown to
operate — it orders the back-pressure across all three arms and both caps —
but the bandwidth effect that would let it be measured is smaller than the
campaign's resolution, and its sign is not stable across the two caps.

There is also a reason to expect neither mechanism to be the governing one,
which the pre-registration did not consider: **both assume the cap binds, and
in a model whose throughput is `concurrency x 64 B / latency` a byte-rate
throttle acts only through the latency term.** §"Why: the throttle barely
moves per-transaction latency" measures that term at +2.5% to +3.1%. Until a
cap is tight enough to move it substantially, neither registered mechanism
has room to express itself, and the arm ordering will be set by the same
policy-latency difference that sets it uncapped. That is a prediction this
campaign cannot test — it would need a cap tight enough to saturate, which at
these concurrencies means single-digit GB/s — and it is offered as the reading
that best fits the six cells rather than as a result.

### The whole-program limitation, converted into a measured bound

The baseline campaign flagged that `stats.txt` counters are whole-program
while the measured pass is 1.6–2.8% of it, so traffic *rate during the
measured window* is not reconstructable. That limitation stands and none of
the 1.990 / 1.325 / 1.278 figures above is a windowed quantity. **Do not
present a whole-program traffic ratio as if it were a windowed one.**

The cap does, however, convert the caveat into a one-sided bound, which is new.
The controller cannot exceed its realized ceiling. So if a cell genuinely
delivered `agg_bw_sum` of useful bytes concurrently, then the controller
traffic it moved per useful byte during that window cannot have exceeded
`realized ceiling / agg_bw_sum` — otherwise the throttle would have stopped
it. The two readings of that one inequality are the two findings of this
document: where the bound comes out above 1.0 it is a genuine constraint on
in-window traffic, and where it comes out **below** 1.0 it is impossible,
because every useful byte must cross at least once, and the aggregate rather
than the traffic ratio must give way.

| cell @ 32.26 GB/s | `agg_bw_sum` | in-window ratio must be <= | whole-program ratio | verdict |
|---|---|---|---|---|
| `wb_4c` | 19.87 | 1.623 | 1.997 | whole-program overstates |
| `h2_4c` | 24.96 | 1.293 | 1.388 | whole-program overstates |
| `pfoff_4c` | 13.29 | 2.427 | 1.284 | no constraint |
| `wb_8c` | 29.97 | **1.076** | 1.990 | whole-program overstates by 1.85x |
| `h2_8c` | 42.87 | **0.752** | 1.325 | **< 1.0, impossible** |
| `pfoff_8c` | 26.89 | 1.200 | 1.278 | whole-program overstates |

Five of the six cells at the tight cap bound the in-window ratio strictly
below their own whole-program ratio, and `wb_8c` bounds it at 1.076 against a
whole-program 1.990. **WB's excess traffic — its writebacks and its
prefetch over-fetch — is therefore demonstrably not concentrated in the
measured window.** That is a real, artifact-backed windowed result, and it is
also the quantitative reason the traffic mechanism fails to bite: WB's
whole-program load of 1.990 controller bytes per useful byte — 1.50x H2's at
8 cores, 1.44x at 4 — is bounded at no more than 1.076 in the window where it
would have to act, so at most 7.6% of headroom separates it from the
irreducible one-byte-per-byte minimum. The sixth cell bounds the ratio
below 1.0, which is impossible, and that is the contradiction of the previous
section arriving by a second route.

### What would settle it

The measurement that discriminates is the one the baseline campaign already
specified and did not have: **window-scoped counters.** Specifically

- `m5_dump_reset_stats` immediately before and after the measured pass in
  `run_stream()`, so `mem_ctrls1.bytesRead`/`bytesWritten` and the HNF
  transition histograms are scoped to the window. This alone turns the bound
  above into a measured in-window traffic ratio per arm, at which point the
  traffic mechanism is either confirmed or refuted in one run per arm.
- A cross-process barrier before the measured pass — a shared anonymous
  mapping with an atomic arrival counter spinning on
  `__builtin_ia32_pause()`, **not** `sched_yield()` (the W8.7 two-core CHI
  queued-spinlock livelock) — which converts the overlap floor from a bound
  into a guarantee and makes `agg_bw_sum` a rate rather than a sum.
- Seed replication, `--reps > 1`, so that a 3.3% effect has an error bar. With
  n = 1 no clip magnitude below roughly 10% is interpretable.

The first two are the same two changes the baseline campaign recommended; this
campaign is the second independent argument for them, and the `h2_8c`
contradiction raises them from "would make it airtight" to "required before
any 8-core magnitude is published". They should be pre-registered together
with a re-run of the 8-core cells only, since the 4-core cells are internally
consistent.

## The H2 arm is partially engaged, and how that bears on this result

`H2_BYPASS_COLLAPSE_2026-09-03.md` established that
`prepareRequestRetry()` in `CHI-cache-funcs.sm` rebuilds a CHI request after a
`RetryAck` without copying `isStreaming`, whose field default is `false`. Every
retried request therefore reaches the HNF affirmatively marked non-streaming,
the victim line is allocated, and the bypass does not happen. **The six cells
certified here were produced by the pre-fix binary** — `gem5_sha256`
`cfd37207b9b7124a…`, matching the live `gem5.opt` — so H2 is partially engaged
in all of them and every H2 figure above must be read accordingly.

Measured on these cells, using that document's `E_clean` definition
(`WriteEvictFull.RU->I` over `WriteEvictFull.RU->{I,UC,UD}`):

| cell | bypasses | clean fill decisions | `E_clean` | HNF write-retry fraction |
|---|--:|--:|--:|--:|
| `wb_8c` @ 32.26 | 0 | 1,495,749 | 0.0% (correct) | 0.6% |
| `h2_8c` @ 32.26 | 860,934 | 905,915 | **91.3%** | 0.8% |
| `pfoff_8c` @ 32.26 | 848,294 | 883,425 | **96.0%** | 0.0% |
| `wb_8c` @ 62.50 | 0 | 1,489,756 | 0.0% (correct) | 1.4% |
| `h2_8c` @ 62.50 | 862,619 | 914,476 | **90.7%** | 1.4% |
| `pfoff_8c` @ 62.50 | 850,215 | 885,176 | **96.0%** | 0.0% |

The counter identity that document relies on —
`streamingHnfFillBypasses == WriteEvictFull.RU->I + WriteBackFull.RU->I` —
holds with **zero residual in all six new cells**, extending it from fifteen
runs to twenty-one. The `pfoff` cells sit at exactly 96.0%, reproducing the
zero-retry calibration to three significant figures and confirming that 96.0%
and not 100% is this workload's ceiling.

**The prediction that document recorded before these runs finished is
confirmed on every count.** It predicted `h2` engagement 88–92%, `pfoff`
96.0%, `wb` exactly 0 bypasses, and all six passing G5, with any `h2` cell
below 20% engagement voiding that cell. Observed: 91.3% and 90.7%, both inside
88–92%; `pfoff` at 96.0%; `wb` at exactly 0; all six G5 PASS; nothing near
void.

### Is the CXL-cap conclusion robust to the partial engagement?

**Yes, and it does not need re-running after the fix.** Four reasons, in
descending strength.

1. **The defect is cap-invariant.** At 8 cores engagement is 90.4% uncapped,
   91.3% at 32.26 GB/s and 90.7% at 62.50 GB/s — a **0.9 pp** spread across a
   15.5x change in interconnect bandwidth. At 4 cores it is 83.5% uncapped,
   84.8% and 83.9% capped, a 1.3 pp spread. The cap does not interact with the
   defect, so the *comparison* the campaign makes — capped against uncapped —
   is between two cells with the same partial engagement, and the defect
   cancels out of it. This is the decisive reason.
2. **The bias direction is favourable.** The defect *removes* bypasses that
   should have occurred, so a fully-engaged H2 would suppress more fills, pay
   less home-node latency and measure faster. The H2 figures are lower bounds.
   Since the conclusion is that H2's advantage *survives* the cap, and a fix
   would only widen that advantage, a fix cannot overturn it.
3. **The conclusion does not rest on H2's magnitude.** The answer is that no
   cell moved by more than 3.3% and no ratio moved by more than 2.8%. WB and
   `pfoff` — which are unaffected by the defect, at exactly 0 and exactly
   96.0% engagement — independently show clips of 3.3% and 0.3%. Delete the H2
   arm entirely and the answer is unchanged.
4. **Retry pressure is negligible in these cells.** The HNF write-retry
   fraction is 0.6–1.4% at eight slices, against the 64.8% that voided the
   one-slice H2 cell. There is no regime here in which the fabric rather than
   the policy decided the result.

What a post-fix re-run *would* change: H2's absolute aggregates would rise,
`h2/wb` would rise above 1.43 at 8 cores, and the `h2_8c` overshoot of its
ceiling would get *worse*, sharpening the metric contradiction rather than
resolving it. That is a strengthening, and it is lower priority than the
one-slice re-run, which is repairing a void cell rather than improving a sound
one. It is also lower priority than the window-scoped counters of the previous
section, which are what the 8-core magnitudes actually need.

**The one-slice H2 cell remains void** and nothing in this campaign changes
that. Its 7.72 GB/s must not be reported as an H2 number.

## Health

All six cells clean. `console.log` and `DONE.json` for each:

| check | result |
|---|---|
| `fatal` | **0** in all six |
| `panic` | **0** in all six |
| `assert` | **0** in all six |
| non-`ok` instance statuses | **0** — 48/48 instances `status: "ok"` |
| non-zero exits | **0** — `DONE.json` `exit: 0` in all six |
| reached `Exiting @ tick` | all six |
| instance JSON lines | 8 per cell, 48 total |
| realized policy | `wb` / `stream` / `stream`, matching each arm's label |
| `threads` echoed | 1 in all 48 instances |
| `samples` per instance / `cov` | 1 / 0 — `--reps 1`, so **n = 1 per cell** by construction |
| **`free(): invalid size`** | **5 of 6 cells emitted it exactly once; `wb_8c` @ 32.26 emitted it zero times** |
| **tick-rounding warning** | **0 in all six — `grep -ci 'rounding error'` returns 0, as expected** |
| other warnings | only the 32 base-10 cache-size casts, the `se.py` deprecation notice, and the missing-`pydot` notice — all benign and all present in the uncapped runs at identical counts |

**`free(): invalid size` is counted, not treated as fatal**, per the baseline
campaign's finding that it is glibc heap corruption in the benchmark's
teardown — `free_bytes(fact, …)` at the end of `run_stream()` — firing strictly
after every reported number is computed and printed. Counts across the whole
21-run `h1bw_mc_*_20260904` family: **14 runs emitted it once, 7 emitted it
zero times.** The non-determinism is confirmed again and, as before, is what
distinguishes it from a size-mismatched free, which would fire every time. It
cannot have affected any figure here. Note the coincidence that the zero-count
cell is again a WB 8-core run, as in the baseline campaign; with 7 zeros in 21
runs spread across all three arms and both core counts, this is not a pattern.

**The tick-rounding warning is correctly absent.** `src/python/m5/ticks.py`
carries an uncommitted fix that would report the silent `ROUND_HALF_UP`
quantisation, and it is dormant in this binary: `gem5_sha256` matches the
`gem5.opt` built 2026-08-31, before the fix was written, and `src/python/` is
marshalled into the binary rather than read at run time. Its absence is
therefore positive confirmation that these six runs were produced by the
pre-fix binary, which is what the H2 qualification above depends on.

## Deviations from the pre-registration

Recorded here; the pre-registration is frozen and has not been edited.

- **One prediction failed** (`h2_8c` @ 32.26, band 0.55–0.85x, observed
  0.994x). Reported as a failure and interpreted in §"The one failed
  prediction" rather than rationalised.
- **`cxl_bw_used_frac` exceeded 100% in one cell** (132.9%). The
  pre-registration named this quantity as "the direct evidence of whether the
  cap did anything" and expected a binding cap to push it toward 100%. A value
  above 100% was not anticipated as possible, and its interpretation —
  §"The cap as an audit of `agg_bw_sum`" — is therefore not pre-registered.
  It is presented as a validity finding about the metric, not as a result
  about bandwidth.
- **The pre-registration's competing-mechanism paragraph cites 1.350x and
  1.018x** as WB's and H2's controller traffic over two-pass demand at 8
  cores. Those are read-only figures; the read-plus-write ratios that a
  byte-rate cap actually charges against are 1.990 and 1.325. The
  discrimination in §"Mechanism discrimination" uses reads plus writes, which
  is what `SimpleMemory` throttles, and the pre-registration's own
  discriminating observable is stated as `bytesRead + bytesWritten`. No
  substantive change; the narrower figures would understate WB's load.
- **`MANIFEST.json` records `prereg: H1BW_MULTICORE_PREREG_2026-09-03.md`** in
  all six cells, the superseded pre-registration, because
  `run_h1bw_multicore.sh` hard-codes that path. The runs are governed by
  `H1BW_CXLBW_PREREG_2026-09-03.md` and were analyzed against it. No gate
  reads the field. Worth fixing in the runner before the next bracket, since
  a manifest that names the wrong pre-registration is a provenance hazard of
  exactly the class this project tracks.

## What this licenses, and what it does not

Licensed:

- **No conclusion drawn from the gem5 SE bandwidth experiments depends on the
  absence of a CXL bandwidth limit.** At a physically realistic 32.2581 GB/s
  CXL 2.0 x16 ceiling, and at 62.5000 GB/s, all twelve cells land within
  0.967–1.003x of their uncapped aggregates, the ordering
  `H2 >= WB > prefetch-off` holds in all four capped cells, and `h2/wb` holds
  within +2.8%/−1.6% of 1.2500 (4c) and 1.3917 (8c). The pre-registered alarm
  did not fire.
- **The H1 bandwidth-survival claim is strengthened, not merely preserved.**
  It now holds in both the unphysical 500 GB/s regime and at a realistic link
  rate. This is the outcome the pre-registration named as strengthening.
- **The cap moves per-transaction latency by at most 3.1%**, measured
  independently from the HNF `inTransLatHist` histograms, and that is why
  delivered bandwidth barely moves in a model whose throughput is
  concurrency x 64 B / latency. A byte-rate throttle whose per-packet
  occupancy is 1.984 ns cannot bind a 203 ns device latency while the fabric
  still has slack, and it had slack in every cell (HNF TBEs 42.0–44.1%, L1
  MSHRs 28.0–29.4%). Do not restate this as a predictive fit of the
  concurrency identity: concurrency is derived from `agg_bw_sum`, so that
  comparison is circular.
- **The realized caps, and the untouched local DRAM range.** 31.000000 and
  16.000000 ticks/byte on `mem_ctrls1`, 2.000000 on `mem_ctrls0`, all read
  back from `config.ini`.

Not licensed, and to be stated wherever these numbers appear:

- **Do not present the 8-core aggregates as CXL link throughput.** The
  corrected statement: *at 8 cores the H2 arm's summed per-instance read
  bandwidth is 42.5–43.1 GB/s; this is a sum over windows that are not proven
  concurrent, and in the 32.2581 GB/s cell it exceeds what the modelled link
  could physically deliver, so it must not be quoted as a link rate. The
  transferable quantity is the H2-over-WB ratio, 1.37–1.43 at 8 cores, which
  is cap-invariant.* The 4-core aggregates are internally consistent with both
  caps and are not subject to this restriction.
- **Do not describe this model as CXL-bandwidth-limited, with or without the
  cap.** The archive's "CXL-path-limited (~6–8 GB/s regardless of cores)"
  remains refuted, now from both directions.
- **`agg_bw_sum` at 8 cores is inflated by at least 1.329x in one cell** and
  its window-overlap floor is a weaker bound than the baseline campaign
  reported. Ratios are unaffected and the bias runs against H2.
- **The mechanism discrimination is unresolved.** Delivered-rate arithmetic is
  refuted; traffic-per-useful-byte is neither confirmed nor refuted. Do not
  cite the 32.26 GB/s column alone as confirming it.
- **No in-window traffic rate is reported here.** The 1.990 / 1.325 / 1.278
  ratios are whole-program. The only windowed statements are the one-sided
  bounds in §"The whole-program limitation, converted into a measured bound".
- **H2 is partially engaged** at 90.7–91.3% of a 96.0% ceiling, on the pre-fix
  binary. Every H2 figure is a lower bound. The cap conclusion is robust to
  this because engagement is cap-invariant to within 0.9 pp and because WB and
  `pfoff` carry the same answer independently.
- **n = 1 per cell**, `cov` identically 0, no seed replication. No clip
  magnitude below roughly 10% is interpretable.
- **This is still not a CXL link model.** `latency_var` remains 0; there is no
  flit-level protocol, no retry, no per-direction asymmetry and no queueing
  model beyond the throttle. It bounds the aggregate rate realistically and
  does only that.
- **Magnitudes remain non-comparable to the archived
  `preserved/gem5_streaming.tar.gz` REPORT**, whose harness is unrecoverable.

## Provenance

- Artifacts: twelve completed run directories
  `gem5/logs/se_chi/h1bw_mc_{wb,h2,pfoff}_{4c_l3x4,8c_l3x8}_bwt{31,16}_20260904`,
  all with `DONE.json` and `exit: 0`. **Nothing under `gem5/logs/` was
  written, and no run was signalled or killed.** The six 8-core processes were
  polled to exit and read only after `DONE.json` appeared.
- Provenance taken from the runs' own `config.ini` and `MANIFEST.json`, not
  from the live filesystem: `gem5_sha256 = cfd37207b9b7124a…`,
  `bench_sha256 = cac9e27ab42448a8…`, host `mos181`, all six identical. A
  sibling worker holds a `gem5.opt` rebuild pending on these runs, so the
  binary's mtime is not a stable identifier; the sha256 recorded at launch
  still matched the on-disk binary at the time of writing.
- Source read at `gem5/src/mem/simple_mem.{cc,hh}` (unmodified in the working
  tree, so it matches the binary). `gem5/src/` was **not** modified.
- Analyzer `experiments/asplos/analyze_h1bw_bracket.py`, unchanged, exit 0.
  `experiments/asplos/data/gem5/h1bw_cxlbw.jsonl` rewritten with all twelve
  records. `experiments/asplos/h2_engagement_table.py` reproduces the
  engagement figures for the cells in its list; the six 8-core cap cells post-
  date it and their `E_clean` was computed from `stats.txt` using its
  definition, with the counter identity checked at zero residual.
- Superseded by nothing. Supersedes no prior document; it is the follow-up to
  `H1BW_MULTICORE_OUTCOME_2026-09-03.md` and shares that document's
  Addendum 1 qualification of the H2 arm.

---

# Addendum 1 — 2026-09-03: the 132.9% reading does not prove stagger, and the metric audit is withdrawn

Added after `AGGBW_VALIDITY_2026-09-03.md`, which re-audited §"The cap as an
audit of `agg_bw_sum`" from the same twelve cells. The pre-registration
`H1BW_CXLBW_PREREG_2026-09-03.md` is frozen and unchanged; the body of this
document is unchanged.

**The campaign's answer is unaffected.** No published conclusion depends on
the missing bandwidth limit; the ordering and the ratio survive both caps; the
alarm did not fire. Every number in §Results, §"The cap bound hard",
§"Mechanism discrimination" and §"The H2 arm is partially engaged" stands.

**What is withdrawn is the unplanned metric audit** — the inference that the
`h2_8c` @32.26 GB/s cell's 132.9% of ceiling proves `agg_bw_sum` is not a
concurrent rate and is inflated by at least 1.329x. That inference has a false
premise, and the direction of the error is that the metric is *better* than
this document concluded.

## Step 2 of the inequality is false

**Current wording:**

> 2. Every one of those bytes crossed `mem_ctrls1`. The baseline campaign's
>    LLC-residency result establishes this and it reproduces here:
>    `cxl_read_over_demand` is **1.016x** for `h2_8c` @ 32.26, so CXL reads are
>    the two-pass demand plus 1.6%, and the 40 MiB LLC supplied none of it.

**Replacement:**

> 2. **At most 43.6% of those bytes crossed `mem_ctrls1`.**
>    `cxl_read_over_demand = 1.016x` is a whole-program ratio and says nothing
>    about the measured pass. Decomposed by request type at the home node —
>    where `HNF ReadMissPipe` equals `mem_ctrls1.numReads::total` exactly in
>    every cell — this cell's 2,131,136 CXL read lines are 1,211,903 setup
>    write-allocate fetches plus 919,233 read-pass fetches, against 2,097,152
>    line-touches the two read passes require. The setup figure is calibrated
>    on `pfoff_8c`, whose 1,215,867 `ReadUnique_PoC.I.RU` misses are
>    `fill_fact`'s and `build_table`'s first-touch fetches at 151,983 lines per
>    instance, and the two agree to 0.33%. The 40 MiB LLC finishes the run
>    **94% full of dirty fact lines** that `fill_fact` deposited and that the
>    STREAMING bypass prevents the read stream from displacing, and it supplies
>    the balance.

With that correction the inequality reverses. Delivering 67,108,864 useful
bytes at `f <= 0.436` costs `<= 0.907 ms` of controller read time; adding the
most write traffic attributable to the window (the read passes can displace at
most 98,108 resident lines, so `<= 0.094` write bytes per useful byte) brings
it to `<= 1.1024 ms`. The eight windows reconstruct to a union span of
**1.7210 ms**. **Feasible, with 36% headroom.** For the inequality to bite,
`f` would have to exceed 0.758.

## The conclusion drawn from it

**Current wording:**

> **`agg_bw_sum` = 42.87 GB/s is consequently not a concurrent delivered rate
> in this cell.** The rate averaged over the union of the windows is at most
> 32.2581 GB/s, so the reported figure is high by at least **1.329x**.

**Replacement:**

> `agg_bw_sum` = 42.87 GB/s is **not** shown to be non-concurrent by this cell.
> The reconstructed union average is **38.994 GB/s**, so the reported figure is
> high by **10.0%**. The largest useful aggregate the cell could physically
> sustain, given that fewer than half its bytes cross the capped path, is
> **60.9 GB/s**; 42.87 is 70% of that. 132.9% of the raw ceiling is what a
> delivered-to-core rate reads when it is compared against a ceiling on a path
> that carries 43.6% of it — not an impossibility.

The `< 1.0, impossible` verdict for `h2_8c` in §"The whole-program limitation,
converted into a measured bound" falls with it: the bound `realized ceiling /
agg_bw_sum = 0.752` is not impossible, because the in-window ratio it
constrains is a ratio of *controller* bytes to *useful* bytes and useful bytes
are not required to cross the controller once. The other five rows of that
table remain valid as one-sided bounds; only the impossibility reading of the
sixth is withdrawn. §"Deviations from the pre-registration"'s entry on
`cxl_bw_used_frac` exceeding 100% should record that a value above 100% is
*expected* whenever the cache hierarchy supplies part of the counted stream,
and is not by itself a validity finding.

## The overlap floor is confirmed, not refuted

**Current wording:**

> And the reported window overlap floor of 90.7% is refuted directly: that
> bound is derived from per-CPU `numCycles` skew, which measures *program-end*
> alignment, and this cell shows program-end alignment does not bound
> measured-pass alignment as tightly as was assumed.

**Replacement:**

> The reported window overlap floor of 90.7% is **confirmed**. Each instance's
> window reconstructs as `[T_i − eps − d_i, T_i − eps]`, where `T_i` is its
> program-end time from `numCycles x 526 ps` (a CPU halts at process exit, and
> the maximum `T_i` equals `simSeconds` to six decimal places), `d_i` is its
> own reported `seconds`, and the epilogue length `eps` **cancels** out of every
> span and overlap. That gives an actual minimum pairwise overlap of **90.84%**
> in this cell, and all fifteen cells checked land at or above their published
> floors. The reconstruction is validated against an independent signal — the
> order in which instances' JSON lines reach `console.log`, set by a different
> constant offset — which it reproduces exactly in nine of fifteen cells, every
> inversion being an adjacent pair separated by 0.11–9.84 us. Program-end
> alignment **does** bound measured-pass alignment, because the setup phase is
> the same instruction stream in every instance and consumes 97%+ of the
> program.

Reconstructed union-span rates against this document's `agg_bw_sum` figures:

| cell | `agg_bw_sum` | union-span rate | high by | intersection / narrowest window |
|---|--:|--:|--:|--:|
| `wb_8c` @32.26 | 29.967 | 26.442 | 13.3% | 88.2% |
| `h2_8c` @32.26 | 42.873 | 38.994 | 10.0% | 91.9% |
| `pfoff_8c` @32.26 | 26.890 | 23.818 | 12.9% | 92.6% |
| `wb_8c` @62.50 | 31.050 | 26.601 | 16.7% | 86.0% |
| `h2_8c` @62.50 | 42.537 | 40.686 | 4.6% | 96.8% |
| `pfoff_8c` @62.50 | 26.944 | 23.668 | 13.8% | 92.1% |

The all-N-concurrent intersection is non-empty in every cell. `h2/wb`
recomputed on the union-span rate is **1.4747** at the tight cap and
**1.5295** at the loose one, against the 1.4307 and 1.3700 reported here —
both **wider**, confirming this document's statement that the bias runs
against H2. `wb/pfoff` moves the other way, 1.1102 and 1.1239 against the
1.1145 and 1.1524 reported here, so it is a ceiling; the ordering
`H2 >= WB > pfoff` holds on both metrics in all six cells.

## What this addendum adds that the body could not

Two of the three "what would settle it" items in §"What would settle it" are
re-scoped:

- **`m5_dump_reset_stats` bracketing** is correct, needs no gem5 rebuild
  (0x40/0x41/0x42 are all decoded by this binary and 0x40/0x41 are already
  used by `run_join()`), and is the primary instrument of
  `AGGBW_WINDOW_PREREG_2026-09-03.md`.
- **The cross-process barrier cannot be built.** `mmapFunc`
  (`src/sim/syscall_emul.hh:2055`) does not propagate writes to shared
  mappings and `shmget`/`shmat`/`shmdt`/`memfd_create` have no handler and
  `fatal()`. The N instances are separate `Process` objects, not forks, so the
  prescribed atomic arrival counter is invisible across them and every
  instance would deadlock. `--reps 8` replaces it: the reconstructed start
  skew in these six cells is **83–309 us** and does not grow with reps, so an
  eight-times-longer window raises the overlap floor above 97%
  arithmetically.
- **Seed replication / `--reps > 1`** stands as written and is folded into the
  same campaign.

Consequently the escalation recorded here — that these two changes are
"required before any 8-core magnitude is published" — is **softened to
recommended**. The 8-core magnitudes are high by 4.6–16.7%, not by an
unbounded or 1.329x factor, and every ratio in this document is safe. What
does still bar describing these aggregates as CXL or far-memory bandwidth is
the residency finding above, and that is a benchmark-geometry problem which
neither the barrier nor the bracketing fixes.

## What this addendum does not change

- **"No published conclusion depends on the missing bandwidth limit."** The
  campaign's answer, unaffected.
- Every cell's `agg_bw_sum`, every clip magnitude, the certification of all
  twelve cells against all five gates, the realized caps read back from
  `config.ini`, the queueing and latency measurements, the mechanism
  discrimination verdict, and the H2 partial-engagement qualification.
- **The instruction not to present the 8-core aggregates as CXL link
  throughput.** It stands, and this addendum supplies a second and stronger
  reason for it: fewer than half of the bytes those aggregates count cross the
  CXL controller at all.
- **The transferable quantity is still the H2-over-WB ratio**, 1.37–1.43 at 8
  cores on `agg_bw_sum` and 1.47–1.53 on the union-span rate, cap-invariant on
  both.

---

# Addendum 2 — 2026-09-03: the four places the withdrawn stagger inference is still stated

Added after `AGGBW_VALIDITY_2026-09-03.md` and Addendum 1 above. The
pre-registration `H1BW_CXLBW_PREREG_2026-09-03.md` is frozen and unchanged;
the body of this document and Addendum 1 are unchanged.

Addendum 1 withdrew the inference of §"The cap as an audit of `agg_bw_sum`" by
quoting and replacing three passages inside that section and the overlap-floor
sentence. It did not quote the four places **elsewhere in the document** that
restate the same inference as an established result, and one of them is in
§"What this licenses, and what it does not" — the list a reader is instructed
to consult "wherever the 8-core magnitude appears". This addendum closes them.

**Nothing here changes the campaign's answer.** No published conclusion
depends on the missing bandwidth limit. That conclusion never rested on the
132.9% reading: it rests on twelve capped-versus-uncapped comparisons, and
whatever window stagger exists is shared by both sides of each comparison, so
it cancels. §Results, §"The cap bound hard", §"Mechanism discrimination" and
§"The H2 arm is partially engaged" stand entire.

## What falls and what survives, stated once

**Falls.** That the `h2_8c` @32.26 GB/s cell *proves* `agg_bw_sum` is not a
concurrent rate, and that it establishes a `>= 1.329x` lower bound on the
inflation. The premise was that every measured byte crossed the capped
controller. At most 43.6% of them did, and the LLC supplies the balance with a
factor of 1.9 in hand (`AGGBW_VALIDITY_2026-09-03.md` §Q1). 132.9% of a
ceiling is the expected reading, not an impossibility, whenever a
delivered-to-core rate is compared against a ceiling on a path that carries
fewer than half its bytes.

**Survives.** That the 8-core aggregates must not be quoted as a link or
far-memory rate — for a second and stronger reason than the one given here,
namely that fewer than half their bytes cross the controller at all. That
`agg_bw_sum` is high, by the reconstructed **4.6–16.7%** rather than by
`>= 32.9%`. That the delivered-rate mechanism is refuted, which is a direct
measurement (predicted `<= 0.748x`, observed 0.994x) and not an inference from
the ceiling arithmetic. And that the bias runs against H2, which Addendum 1
confirms on the union-span metric.

## §"The answer", item 2

**Current wording:**

> 2. **The 8-core H2 aggregate must not be quoted as a link rate.** The capped
>    `h2_8c` cell reports 42.87 GB/s against its own realized 32.2581 GB/s
>    ceiling — **132.9% of it** — which is arithmetically impossible for a
>    serializing throttle. That cell is a valid certified measurement of the
>    *policy comparison* and simultaneously a proof that `agg_bw_sum` is not a
>    physically realizable concurrent rate at 8 cores. §"The cap as an audit of
>    `agg_bw_sum`" derives the contradiction and bounds it. This does not
>    disturb any ratio, because the inflation is common to the arms and, where
>    it differs, it runs against H2.

**Replacement:**

> 2. **The 8-core H2 aggregate must not be quoted as a link rate.** The capped
>    `h2_8c` cell reports 42.87 GB/s against its own realized 32.2581 GB/s
>    ceiling — **132.9% of it**. That is not arithmetically impossible, and it
>    is not evidence of window stagger: **at most 43.6% of the bytes
>    `agg_bw_sum` counts cross `mem_ctrls1` at all**, the LLC supplying the
>    rest, so the largest useful aggregate this cell could physically sustain
>    is 60.9 GB/s and 42.87 is 70% of it. The reading is the expected
>    signature of a delivered-to-core rate measured against a ceiling on a
>    path that carries a minority of it. The prohibition stands and is
>    strengthened: the figure is not a link rate precisely because most of it
>    never reached the link. `agg_bw_sum` is separately high by
>    **4.6–16.7%** from window stagger, measured by reconstruction rather than
>    inferred from this cell (Addendum 1). No ratio is disturbed.

## §"The one failed prediction, and why it is the result rather than a miss"

**Current wording:**

> *`agg_bw_sum` is not a concurrent rate.* Supported, and provable from the
> artifacts. §"The cap as an audit of `agg_bw_sum`".

**Replacement:**

> *`agg_bw_sum` is not a concurrent rate.* **Not supported by this cell.** The
> reading it rests on is explained by LLC supply without any appeal to phase
> (`AGGBW_VALIDITY_2026-09-03.md` §Q1), and reconstructing the windows
> directly shows the eight measured passes do overlap — an all-eight
> concurrent intersection covering 91.9% of the narrowest window, and a union
> average of 38.994 GB/s against the reported 42.873 (Addendum 1). A third
> reading is the correct one and was not on this list: **`agg_bw_sum` is a
> concurrent rate of bytes delivered to cores, and the ceiling it was compared
> against governs only the fraction of those bytes that crosses the
> controller.** The prediction failed because it assumed that fraction was 1.

## §"Mechanism discrimination", the delivered-rate bullet

**Current wording:**

> Its premise — that the reported aggregate is a rate the link must carry — is
> exactly what §"The cap as an audit" disproves.

**Replacement:**

> Its premise — that the reported aggregate is a rate the link must carry — is
> false, and the reason is the residency finding rather than the windowing
> argument this document originally gave: at most 43.6% of the aggregate's
> bytes cross the controller in this cell. The **refutation itself is
> unaffected**, because it is a measurement and not an inference: the
> mechanism predicted `<= 0.748x` and the cell delivered 0.994x.

## §"What this licenses, and what it does not"

**Current wording:**

> - **`agg_bw_sum` at 8 cores is inflated by at least 1.329x in one cell** and
>   its window-overlap floor is a weaker bound than the baseline campaign
>   reported. Ratios are unaffected and the bias runs against H2.

**Replacement:**

> - **`agg_bw_sum` at 8 cores is high by 4.6–16.7%, cell-specific**, measured
>   by reconstructing each instance's window from per-CPU `numCycles` less its
>   own reported `seconds`. The "at least 1.329x" inflation and the claim that
>   the window-overlap floor is a weaker bound than the baseline campaign
>   reported are both **withdrawn**: the floors hold in all fifteen cells
>   checked, including this one at 90.84% against a published 90.7%. Ratios
>   are unaffected and the bias runs against H2, which Addendum 1 confirms
>   directly (`h2/wb` rises to 1.4747 and 1.5295 on the union-span metric).
>   See `AGGBW_VALIDITY_2026-09-03.md` §Q2, §Q3.

## Other conclusions drawn from the 132.9% reading — checked and accounted

A pass over every occurrence of `132.9`, `1.329` and `cxl_bw_used_frac` in this
document finds six, and all six are now addressed:

| location | conclusion drawn | status |
|---|---|---|
| §"The answer", item 2 | the reading proves non-concurrency | replaced above |
| §Results, 32.26 table, `h2_8c` row | cell marked **OUTSIDE** its pre-registered band at 132.9% of ceiling | **stands as recorded.** The band was missed; that is a fact about the prediction, and §"The one failed prediction" retains it. Only the *interpretation* moves |
| §"The one failed prediction" | one of two readings is "supported" | replaced above |
| §"The cap as an audit", steps 2, 5–6 and conclusion | `>= 1.329x` inflation; floor refuted | replaced in **Addendum 1** |
| §"The whole-program limitation", `h2_8c` row | in-window ratio `< 1.0`, "impossible" | withdrawn in **Addendum 1**; the other five rows stand as one-sided bounds |
| §"Deviations from the pre-registration", `cxl_bw_used_frac` entry | a value above 100% "was not anticipated as possible" | **Addendum 1** records that above 100% is *expected* whenever the cache hierarchy supplies part of the counted stream. Restated here for the record: the deviation is real and correctly logged as un-pre-registered, but it is a finding about what the metric measures, not a validity finding about the runs |
| §"What this licenses" | `>= 1.329x`; floor weaker | replaced above |

No other conclusion in this document is derived from the 132.9% reading. In
particular the certification of all twelve cells against all five gates, the
G4 read-back of the realized caps, the queueing and latency measurements, and
the H2 partial-engagement analysis are independent of it.

## What this addendum does not change

- **"No published conclusion depends on the missing bandwidth limit."** The
  campaign's answer, unaffected, for the reason given above: capped-versus-
  uncapped comparisons share whatever stagger exists.
- Every cell's `agg_bw_sum`, every clip magnitude, the certification, the
  realized caps, the mechanism-discrimination verdict, and the H2
  partial-engagement qualification.
- **The instruction not to present the 8-core aggregates as CXL link
  throughput**, which now has two independent reasons behind it and is the
  more important of the two corrections this document has taken.
