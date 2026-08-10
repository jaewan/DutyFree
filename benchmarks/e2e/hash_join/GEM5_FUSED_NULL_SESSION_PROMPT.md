# Session prompt: why gem5 shows no STREAMING benefit on the fused hash join

Paste below the rule into a fresh session. Written 2026-08-10. OSTA structure
(Objective / Scope / Task / Acceptance).

---

## O — Objective

gem5 reports **no STREAMING/H2 benefit** on the fused (`--mode morsel`)
hash-join workload. Establish whether that null is a model artifact with a
fixable cause, and if so fix it.

**Start from the conclusion already on file, because it reframes the
question.** The null is not "H2 fails to help." It is **"there is no tax to
remove"**:

| fused arm, gem5 SE, 16 MiB CXL fact + 2.6 MB hot set | cyc/access |
|---|---:|
| `m2_q` quiescent (no stream) | 79.97 |
| loaded WB | 80.10 |
| loaded H2 | 78.06 |

Quiescent 79.97 vs loaded WB 80.10 is **~0% fused tax**, against **1.47× on
real EMR hardware**. H2 engages correctly — LLC fills drop 1,178,728 →
742,046 (−37%) — it simply has nothing to recover. The −2.5% cycle movement is
run noise.

So the real question is: **why does the gem5 SE model exhibit no fused tax
where hardware exhibits 1.47×?**

### The leading hypothesis, with the arithmetic

The frozen config is `--l1d_size=48KiB --l2_size=2MiB --l3_size=5MiB`
(`gem5/scripts/intel_8592_8cpu_dirtax_streaming.sh:27-30`).

**The private L2 is 40% of the shared LLC.** On real EMR it is 0.6% (2 MB of a
320 MiB LLC domain). The scaling applied to build this model shrank the LLC by
~64× and left L1/L2 at native size, which preserves the *hot ÷ LLC* ratio and
destroys the *hot ÷ L2* ratio:

| | hardware EMR | gem5 SE |
|---|---:|---:|
| hot set at the "53% LLC" point | 169.6 MiB | 2.6 MB |
| hot ÷ LLC | 53% | 52% ✅ |
| **hot ÷ private L2** | **≈85×** | **≈1.3×** ❌ |
| fraction of hot set L2-resident | ~1% | **~77%** |

H2 acts only at the L2→LLC boundary. If ~77% of the probe stream never leaves
the private L2, there is almost nothing at that boundary to protect, so the
loaded and quiescent arms coincide — exactly what was measured.

**Independent corroboration already in hand (P1-5, 2026-08-04):** at
WSS = 1250 KiB (below the 2 MiB L2) the model gives `wb = st = 1.00×` — H2 a
clean no-op, confirmed through the real `setstreaming` path. 2650 KiB sits at
only 1.3× L2, i.e. barely outside that no-op regime.

**Why the cross-core arm works in the same model.** The cross-core victim is a
2650 KiB pointer chase at MLP≈1: the ~22% that spills past L2 is serialized
full-latency misses, so a small spill is a sensitive detector (WB 1.22×, H2
recovers 94%). The fused morsel probe has MLP and its cost is dominated by the
77% that hits in L2. Same config, opposite sensitivity. This is consistent, not
contradictory.

---

## S — Scope

### Do not re-litigate these — they are verified

The three historical bugs that made H2 a silent no-op are **all fixed and
present in the tracked source.** Do not go hunting for them again:

1. `gem5_set_streaming()` exists — `src/cxl_join_bench.cpp:183-185`
   (`.byte 0x0f,0x04,0x55,0x00`, `M5OP_SET_STREAMING=0x55`).
2. The `run_morsel` `phys_bytes`-vs-`fact_bytes` mismatch is fixed —
   `src/cxl_join_bench.cpp:1283-1284` prefaults and tags **the same**
   `phys_bytes` extent.
3. The `setstreaming` TLB flush in `src/sim/pseudo_inst.cc` is in.

Evidence they work: H2 changes LLC fills by −37% in this very run. A no-op
patch would show 0%.

### In scope

- gem5 cache-geometry config changes and re-runs of the fused arm.
- The quiescent/loaded/H2 triple at each new geometry.

### Out of scope

- **Anything H3.** This is an H2-only question. The H3 material (§4.2, ReadOnce
  re-derivation, spec upgrade, two-tier framing, `tab:h3sf` supersession) is
  under embargo pending the δ audit — see
  `experiments/phase1/e1_residual_decomp/DELTA_AUDIT_SESSION_PROMPT.md`. Do not
  touch it, and do not consume the δ audit's machine time.
- Modifying `cxl_join_bench.cpp`. The workload is not the problem.
- `--fact-bytes 1g`. Infeasible under O3+CHI; runs are 10–30 min at 8–16 MiB.
- `~/STREAMING_Paper/` — it autocommits and **pushes to Overleaf** unattended.

---

## T — Task

### T1 — Cheap discriminator: shrink the private L2 (do this first)

Preserving the hardware L2:LLC ratio of 1:160 at a 5 MiB LLC would demand a
32 KiB L2 — smaller than the 48 KiB L1d, so unphysical. It cannot be preserved
at this LLC size. Get an order of magnitude back instead:

```
--l1d_size=48KiB --l1d_assoc=12
--l2_size=256KiB  --l2_assoc=8      # was 2MiB/16
--l3_size=5MiB    --l3_assoc=20
```

256 KiB is a real private-L2 size (Skylake-server generation), so this is a
defensible configuration rather than a contrivance. It puts the 2.6 MB hot set
at **~10× L2** instead of 1.3×, at unchanged simulation cost.

Run the triple at the 53% point: quiescent (`--no-stream` / `m2_q`), loaded WB,
loaded H2. Same iteration counts, same reps, ≥3 reps.

**Falsifiable prediction, state it before running:** the quiescent-vs-loaded
gap opens measurably from its current 0.2% (79.97 → 80.10). If it stays ~0 at
hot/L2 ≈ 10×, the L2-residency hypothesis is **refuted** — go to T3.

### T2 — If T1 shows a tax: calibrate at the real ratio

With a nonzero tax established, buy the calibrated number:

```
--l2_size=256KiB --l3_size=40MiB    # restores the 1:160 hardware ratio
hot set at 53% = ~21 MiB            # = ~85x L2, the hardware regime
```

Keep the fact stream short to bound runtime; it is the hot set that has to be
correctly sized, not the stream. Expect maybe 2–4× current wall-clock. Report
WB tax and H2 recovery.

**Ceiling to expect, so nobody reads a partial recovery as a failure.**
Hardware's own mechanism decomposition puts **≤31%** of the fused 1.47× in the
shared LLC; the rest is private-cache/MSHR/execution overlap that H2 cannot
reach *by construction*. So a correctly-scaled model should show H2 taking
roughly 1.47× → ~1.32×, not → 1.00×. **Full recovery here would be evidence of
a modelling error, not a triumph.**

### T3 — If T1 refutes the hypothesis: the fill-rate suspect

Next candidate is stream fill pressure. The gem5 aggressor sustains
**3.14 GB/s** against hardware's **9.405 GB/s** single-core CXL anchor — ~3×
short, and in fused mode one thread does both jobs, so it is worse still. Too
little fill pressure produces too little LLC turnover to tax anything.

Measure the fused arm's actual achieved stream bandwidth and compare to
9.405 GB/s. If it is ≪, sweep MSHR depth and prefetcher distance (the
`tab:h1bw` result already showed the verdict there is MSHR-depth-sensitive:
at L1_MSHR=16 all arms cap at ~5 GB/s; at 48, H2=5.82 ≈ WB=5.44 ≫ WC=4.60).

### T4 — Fix the handoff contract that let this through

`gem5_handoff.md` §4's frozen-config table requires disclosing a *"Proportional
scaling factor for LLC, victim WSS, stream size."* **It never requires scaling
L1/L2, and §11's escalation conditions never flag a private L2 that is a large
fraction of the shared LLC.** That gap is the process defect behind this null.

Add to §4: the L2:LLC ratio and the hot÷L2 ratio as required disclosures.
Add to §11: escalate if hot÷L2 < 10× while the hardware reference is ≫10×.

---

## A — Acceptance

### Done means one of these three is established, with numbers

1. **Hypothesis confirmed and fixed** — a geometry exists where the fused arm
   shows a WB tax and H2 recovers a share of it consistent with the ≤31%
   LLC-attributable ceiling. Paper gains a fused gem5 row.
2. **Hypothesis confirmed, not economically fixable** — the tax only appears at
   a geometry too expensive to simulate. Then the paper's existing statement
   ("gem5 cannot host the fused workload; hardware decomposition is the
   authority") **stays, but gains a mechanism**: it is the hot÷L2 collapse, with
   the 85× vs 1.3× table as the evidence. That is a better sentence than the
   bare assertion currently standing.
3. **Hypothesis refuted** — hot÷L2 ≈ 10× still yields ~0 tax. Report the
   refutation and whatever T3 found.

All three are acceptable outcomes. **Outcome 2 is the most likely and is not a
failure** — it converts an unexplained null into an explained one.

### Deliverables

- Pre-registration written **before** running, per house format
  (`experiments/asplos/GATE1_CORUN_PAIR_PREREGISTRATION.md`): geometry stated,
  falsifiable prediction, meaning of each outcome.
- The quiescent / WB / H2 triple at every geometry tried — **never report a
  loaded number without its own quiescent baseline from the same config.**
  Omitting it is precisely what made the original −2.5% look like a result.
- `config_frozen.md` per `gem5_handoff.md` §8, including the two new ratio
  disclosures from T4.
- An outcome doc naming which of the three acceptance branches was reached.

### What does not change regardless of outcome

The paper's fused claim rests on **real hardware**, where the 1.47× and its
≤31%-LLC decomposition are measured. This work can strengthen §5 with a
simulated corroboration or explain why one is unavailable. It cannot weaken the
hardware result, and nothing here is a submission gate.

---

## Context appendix

| what | where |
|---|---|
| workload source | `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp` |
| handoff contract | `benchmarks/e2e/hash_join/gem5_handoff.md` |
| real-HW findings | `benchmarks/e2e/hash_join/docs/RESULTS.md` |
| gem5 geometry | `gem5/scripts/intel_8592_8cpu_dirtax_streaming.sh:27-30` |
| CHI config | `gem5/configs/ruby/CHI_config_8592_nopf.py` |
| H2 gate in CHI | `CHI-cache-actions.sm`, `CheckCacheFill`: `!(is_HN && tbe.isStreaming)` |

Build notes: gem5 needs Python ≤3.12 (Ubuntu 26.04 ships 3.14); use the
standalone venv at `~/gem5-venv`. `scons` has an interactive git-hook prompt —
pipe `yes '' |` or the build hangs. Launch each run as **its own tmux session**
(`tmux new-session -d -s X "cmd"`); loop-with-`&` over ssh does not spawn
reliably.

Metric recipe: `cyc/iter = system.cpu0.numCycles / iters`. For the pointer-chase
regressions `iters` must be 3e6 — small iteration counts are printf-dominated.
