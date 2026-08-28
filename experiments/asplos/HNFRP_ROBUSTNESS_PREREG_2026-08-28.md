# Pre-registration: is the H2 bound an artifact of gem5's biased TreePLRU?

Registered **before** the run. Thresholds, the action on each outcome, and the
action-on-instrument-miss are fixed here and are not arguments to the analyzer.

## The question

`GEM5_TREEPLRU_NONPOW2_BIAS_2026-08-28.md` establishes that gem5's `TreePLRURP`
is 2x biased at non-power-of-two associativity: it allocates `L-1` internal nodes
and descends while `index < L-1`, so leaves land at two depths and the shallow
group is evicted twice as often. Predicted 2.00x, measured 2.06x on the L1D
(assoc 12), uniform to 0.9% under LRU on the same cache.

**The HNF is associativity 20 and is therefore affected**, and the HNF is where
H2 acts. Every gem5 number this project has published --- W1's H2 bound above all
--- was measured on an LLC that behaves as a PLRU with a structurally protected
way group rather than a uniform 20-way PLRU. The config's own comment already
warned that "TreePLRURP ... is what every published number in this project was
produced with -- so any comparison must name TreePLRU rather than assume LRU."
That warning has never been acted on.

**Question:** does W1's headline --- H2 removes **90.9%** of the WB/infinite-SF
capacity charge --- survive an unbiased replacement policy at the HNF?

## Apparatus, pinned as a triple (per W4.5)

Run in `~/DutyFree-Gem5`, **not** the `DutyFree/gem5` submodule, so this is W1's
apparatus and not a new one.

| component | pin |
|---|---|
| binary | `build_Intel_8592/gem5.opt`, built 2026-08-09, src/ as of `56874f1d42` |
| config tree | `configs/` at `356e7b7d0e`; **no `configs/` commit since 2026-08-19**, i.e. no drift since the W1 runs of 08-22/23 |
| workloads | `testcase/dutyfree/{victim,aggressor}` at `356e7b7d0e` |

`HNF_RP` is read at run time from the Python config, so **no rebuild is
required** and the binary under test is bit-identical to W1's.

Fixed: `--cpu-type=O3CPU --num-cpus=2 --cpu-clock=1.9GHz`, L1D 48 KiB/12-way,
L1I 32 KiB/8-way, L2 2 MiB/16-way, **HNF 5 MiB/20-way**, `SimpleMemory`,
`--dram-latency=98ns --cxl-latency=203ns`, `HNF_SF_FINITE=0` (infinite SF),
`HNF_DMT=0`, `RUBY_RANDOMIZATION=1`, seeds 1..3.

## Design: 3 arms x 2 policies x 3 seeds = 18 runs

| arm | workloads | argv |
|---|---|---|
| `qui` | victim alone | `2650 3000000` |
| `wb` | victim + aggressor, **no** declaration | `2650 3000000;16.0` |
| `h2` | victim + aggressor, **declared** | `2650 3000000;16.0 stream` |

`argv[2]=="stream"` is the H2 declaration (gated at gem5 `356e7b7d0e`); the WB
and H2 arms run the same binary and differ only in that token.

Policies: `HNF_RP=treeplru` (explicit, = the default) and `HNF_RP=lru`.

**The TreePLRU arms are re-run rather than taken from the surviving archived
outdirs**, even though those outdirs exist and reproduce W1's published means
exactly. Reason: reusing them would assume the archived batch and this one share
an environment, and that assumption is exactly what F10/F11 punished this project
for. Both policies are measured in one batch, same host, same hour.

## Metric

`cyc/access = system.cpu0.numCycles / 3,000,000` --- cpu0 is the victim. This is
the metric `analyze_sf_inf.py` uses and the one W1's numbers are in.

Derived: `tax_x = mean(x) / mean(qui)`, and the **primary quantity**

    R = (tax_wb - tax_h2) / (tax_wb - 1)

the fraction of the WB capacity charge that H2 removes. Archived TreePLRU value:
**R = 90.85%** (`tax_wb` 1.3689, `tax_h2` 1.0337).

## Primary test and pre-registered thresholds

On `dR = R_lru - R_treeplru`, **both measured in this batch**:

| `abs(dR)` | verdict | action |
|---|---|---|
| **<= 2 pp** | **ROBUST** | The bound is insensitive to the policy bias. Existing gem5 figures stand and gain a robustness citation. Report both values in the appendix. |
| **2--10 pp** | **SENSITIVE** | `HNF_RP=lru` becomes the reporting configuration; the TreePLRU figures are superseded but the qualitative claim ("H2 removes most of the capacity charge") survives. Re-run the gem5 figures that quote a magnitude. |
| **> 10 pp** | **MATERIAL** | Every gem5 figure must be re-measured under `HNF_RP=lru` before the paper cites any of them. **Escalate to the lead before further work.** |

### Why these thresholds clear instrument resolution

Propagated 1-sd on `R` from the archived per-arm sds at n=3 is **0.078
percentage points**. So 2 pp = **26 sd** and 10 pp = **128 sd**. Neither can be
tripped by measurement noise. This is stated explicitly because six earlier
specifications in this campaign set thresholds finer than the instrument could
resolve, and one criterion was satisfiable by a crashed run.

## Predicted direction: none, deliberately

Two mechanisms act in opposite directions and I cannot rank them a priori:

1. TreePLRU's protected way group (8 of 20 ways evicted at half rate) **shelters
   victim lines** from the WB aggressor, which would make `tax_wb` too low and so
   understate H2's benefit --- `dR > 0`.
2. The same protected group **shelters aggressor lines**, which lingers stream
   data that a uniform policy would evict, making `tax_wb` too high and
   overstating H2's benefit --- `dR < 0`.

The test is therefore **two-sided**. Registering a sign here would let either
outcome be rationalised after the fact, which is the failure this document
format exists to prevent.

## Instrument check, and the action if it misses

The `treeplru` re-run must reproduce the archived means within a band of
`max(4 sd, 0.5% of mean)`:

| arm | archived mean | band | window |
|---|--:|--:|---|
| `qui` | 33.8814 | +/- 0.169 | [33.712, 34.051] |
| `wb` | 46.3800 | +/- 0.232 | [46.148, 46.612] |
| `h2` | 35.0247 | +/- 0.175 | [34.850, 35.200] |

The band is `0.5%` rather than `4 sd` for all three arms because `4 sd` on `h2`
is 0.029 --- finer than any plausible environment difference, and the check exists
to catch apparatus drift, not to re-测 the sd.

**Action on miss, fixed now:** a miss does **not** void the primary test, because
`dR` is an internal comparison between two arms measured in the same batch. It
voids only the claim that this batch validates the *archived* figures. If any
`treeplru` arm falls outside its window, the drift is reported as a finding in
its own right and the archived numbers are marked unreproduced, but `dR` is still
computed and still governs.

## Liveness assertions (preflight, before any measurement is believed)

1. Each of the 18 runs must reach `Exiting @ tick` --- a truncated run must not
   contribute. Runs that die are reported as dead, not dropped silently.
2. `system.cpu0.numCycles` must be present and the victim must have executed
   3,000,000 iterations; a victim that exits early makes `cyc/access` meaningless.
3. `config.ini` of every `lru` run must show `LRURP` at
   `system.ruby.hnf.cntrl.cache.replacement_policy`, and every `treeplru` run
   must show `TreePLRURP`. **The arm's identity is read from its own artifact,
   not from the launcher's intent** (S5.1).
4. The `wb` and `h2` arms must differ in the aggressor's argv and nothing else.

## Cost

Archived runtimes: `qui` ~740 s, `wb` ~2710 s, `h2` ~2300 s. 18 runs on a
256-core host, two waves of 9. Expected wall clock ~1.6 h. No silicon time.

## What this cannot answer

The per-way HNF allocation histogram would confirm the 2x bias directly at
assoc 20, but `m_allocsByWay` exists only in the submodule binary
(`056d8b2054`), not in W1's Aug-9 binary. Adding it would change the apparatus
and defeat the point of this run. **The bias at assoc 20 therefore rests on the
traversal arithmetic plus its confirmation at assoc 12, not on a direct HNF
measurement.** Recorded as a limitation, not resolved.
