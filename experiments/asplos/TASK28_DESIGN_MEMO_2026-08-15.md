# #28 predictor head-to-head — feasibility, a forced re-scope, and what the lead must decide

Written 2026-08-15. #28 is named by both review panels as the single most
likely rejection reason and is still unstarted. This memo exists to make it
startable with one decision instead of three, and to report a feasibility
fact that changes its shape.

## 1. The blocking feasibility fact: two of the three predictors do not exist

Checked in `~/DutyFree-Gem5` at the proposed canonical tree state:

| predictor | status in tree |
|---|---|
| **SHiP** | **present** — `src/mem/cache/replacement_policies/ship_rp.{hh,cc}`, exposed as `SHiPRP` (subclass of `BRRIPRP`), with `SHiPMemRP` and `SHiPPCRP` variants |
| **Hawkeye** | **absent** — no match anywhere in `src/` or `configs/` |
| **Mockingjay** | **absent** — no match anywhere in `src/` or `configs/` |

Hawkeye is OPTgen plus a PC-indexed predictor; Mockingjay is a further
reuse-distance predictor. Porting either into Ruby is a multi-week task, and
porting both is not reachable in the remaining schedule. **The
three-predictor head-to-head as chartered is not feasible.** Pretending
otherwise burns the schedule and still ends with no comparison.

The integration point for the one we do have is cheap: Ruby caches accept a
replacement policy (`src/mem/ruby/structures/RubyCache.py:40`,
`replacement_policy = Param.BaseReplacementPolicy(TreePLRURP(), "")`), and the
HNF's cache is constructed from an injectable `llcache_type`
(`configs/ruby/CHI_config_8592.py:763`). So SHiP at the LLC is a config-level
change, not a port.

Two details that will otherwise cost a day:

- The project's LLC currently runs **TreePLRU**, not LRU — that is the
  `RubyCache` default and `CHI_config_8592.py` never overrides it. The
  baseline in any head-to-head must be named as TreePLRU, not assumed LRU.
- Use **`SHiPMemRP`**, not `SHiPPCRP`. SHiP-PC needs a PC signature, and Ruby
  requests do not reliably carry one; SHiP-Mem signatures on the address and
  works in this path.

## 2. The re-scope this forces, and why it is defensible

Run **SHiP** as a real, measured head-to-head. Handle Hawkeye and Mockingjay
**by argument plus citation**, and say plainly in the paper that they were not
run and why.

This is defensible because the paper's claim against predictors is
*categorical*, not empirical: a reuse predictor observes that a line was not
re-*read* — a statement about loads — and therefore can never license
skipping a structure that tracks *stores*. That argument is untouched by
which predictor is measured, and it is the part H3 rests on. The empirical
half only needs to establish the *shape* of the difference — warm-up cost,
mispredict pollution, and the inability to offer a co-runner a guarantee —
and one competent predictor demonstrates all three.

Per the charter, and worth restating because it must not quietly change: **a
result where SHiP matches H2 on capacity is publishable and must be
reported.** The H3 argument survives it intact.

## 3. The regime correction — this is new, and it invalidates the obvious design

Established today (`GATE1_FUSED_NULL_CORRECTION_2026-08-15.md`): the fused
hash-join kernel **cannot discriminate any LLC-admission policy**. It is
MLP-limited by its own dependent probe chain (~59 cycles per 16 B tuple,
~1.3 lines in flight), reaching 0.52 GB/s against the same model's measured
4.17 GB/s (WB) / 4.78 GB/s (H2) pure-stream ceiling — roughly 8x below.

Consequence: a fused-kernel head-to-head between H2, SHiP and TreePLRU would
produce **three indistinguishable nulls**, consume the schedule, and prove
nothing. #28 must run in a configuration where the memory path is actually
loaded:

- the **cross-core victim/aggressor** harness (which already places correctly
  across pools — `h1bw3_m48_wb` reads 52 MB entirely from `mem_ctrls1`), or
- **`--mode stream-smoke`** for the pure bandwidth axis.

Sizing, if the victim is a hot table: the H2-protectable window is
(private L2 2 MiB, shared L3 5 MiB]. `--hot-bytes` is quantised to powers of
two, so **4 MiB is the only in-window point**. 2 MiB is L2-resident and
16 MiB is 3.2x the L3; both are null by construction.

## 4. The prerequisite that still stands

`CANONICAL_CONFIG_PROPOSAL.md` requires #28 to first resolve the h1bw counter
ambiguity, because a predictor comparison wants exactly that
allocation/bandwidth accounting. **That prerequisite is not discharged.**

I checked whether this session's data explains it. It does not. The anomaly is
H2 at ~30% HNF hit rate versus WB at ~0.03% (245,834 vs 212 hits) under
`HNF_DMT=0`. This session's arms show H2's hit rate consistently *above* WB's
(6.3->7.0%, 53.6->53.9%, 33.9->35.1%), which is the same direction and has a
clean mechanism — H2 keeps dead stream victims out of the L3, so non-streaming
residents survive and hit more — but it is **three orders of magnitude too
small**, and was measured with DMT enabled rather than disabled. Same
direction, different phenomenon. The `.sm`-level trace that
`GATE1_H1BW_RERUN_OUTCOME.md` recommends is still required.

## 5. One bias worth declaring up front

H2's fill suppression in this model is **under-enforced** in a
prefetch-mediated way (§7.1 of the correction): some prefetch-filled lines do
not carry the STREAMING attribute, so their clean victims allocate at the HNF.
The error direction is conservative — the model reports *less* H2 benefit than
a correct implementation would. In a head-to-head this biases **against** H2
and in favour of the predictor, so any H2 win is a lower bound and any
predictor win needs the bias stated before it is interpreted. Declare this in
the write-up rather than discovering it in review.

## 6. What the lead needs to decide (one sitting)

1. **Accept the re-scope**: SHiP measured; Hawkeye and Mockingjay argued and
   cited, with an explicit statement that they were not run. If the answer is
   "no, all three must be measured," that is a schedule decision, not a
   technical one, and it needs to displace something.
2. **Sign off the canonical config** (`CANONICAL_CONFIG_PROPOSAL.md`, gem5
   `b2c64991`), or say what to change. Note it is offered as provisional
   pending Eunji's reply, which only the lead can request.
3. **#15's Build B scope conflict** — still flagged, still yours; #28 does not
   need it resolved if #28 runs on the canonical config above.
4. **Whether to spend a day on the h1bw `.sm` trace first** (§4). My
   recommendation: yes, but time-boxed to one day — and if it does not resolve,
   report bandwidth from `mem_ctrls` byte counters and the HNF
   `DataArrayWriteOnFill` bucket, which are unambiguous and which this session
   used throughout, rather than the disputed `m_demand_hits`.

## 7. Estimated cost once decided

- SHiP arm wiring: config-level, hours not days.
- Runs: the cross-core arms are the same class as this session's sweeps
  (~40 min each, embarrassingly parallel on the 256-core host).
- The categorical argument for Hawkeye/Mockingjay: writing, and most of it
  already exists in §4.1.6 of `PAPER_SESSION_PROMPT.md`.

The expensive item is the h1bw trace, and it is the only one that should be
allowed to grow.
