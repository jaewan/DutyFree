# Outcome — single-core H1 bandwidth and LLC footprint, the certified replacement for `tab:h1bw`, 2026-09-04

**Verdict: CERTIFIED. 6/6 primary cells pass all twelve pre-registered gates.
3/3 diagnostic cells pass. 15/19 pre-declared predictions confirmed.
Pre-registered outcome B obtains: the archive's ordering and mechanism are
corroborated, its twelve magnitudes are superseded rather than reproduced.**

Pre-registration: `H1BW_SINGLECORE_PREREG_2026-09-04.md`, frozen at commit
`b4ac57c` before any cell emitted a statistic.
Runner: `run_h1bw_singlecore.sh`. Analyzer: `analyze_h1bw_singlecore.py`.
Per-cell records: `data/gem5/h1bw_singlecore.jsonl` (nine records, including
diagnostics; no cell is dropped).

---

## 1. The six certified cells

Bandwidth is one instance's own 16 MiB x 8 reps over its own measured window.
LLC writes are **windowed and per measured pass** — the counters and the
bandwidth describe the same interval, which is new in this project.

### 16 MSHRs (concurrency ceiling 16 x 64 B / 203 ns = 5.04 GB/s)

| arm | bandwidth | cov | IPC | LLC data-array writes / pass | of 262,144 |
|---|--:|--:|--:|--:|--:|
| WB | 3.271 GB/s | 0.073% | 0.3025 | 262,245 | 1.000x |
| +H2 | **4.046 GB/s** | 0.079% | 0.3741 | 136 | 0.001x |
| pf-off | 2.527 GB/s | 0.050% | 0.2337 | 83 | 0.000x |

### 48 MSHRs (ceiling 15.13 GB/s)

| arm | bandwidth | cov | IPC | LLC data-array writes / pass | of 262,144 |
|---|--:|--:|--:|--:|--:|
| WB | 4.099 GB/s | 0.077% | 0.3790 | 262,244 | 1.000x |
| +H2 | **4.852 GB/s** | 0.110% | 0.4486 | 137 | 0.001x |
| pf-off | 2.527 GB/s | 0.050% | 0.2337 | 83 | 0.000x |

`cov` is over the eight measured reps within the run. It is 0.05–0.11%, so
every difference discussed below is three orders of magnitude larger than the
run-internal noise. This is the first time this family of claims has carried
an error bar at all; the superseded caption said "single runs, no interval".

**It is not an across-run interval.** `RUBY_RANDOMIZATION` is unset and the
cells are bit-reproducible, so `cov` bounds within-run variation of the
measured pass and nothing else. No seed replication is registered or claimed.

### Ratios, reported at each MSHR point separately and never pooled

| MSHRs | H2 / WB | WB / pf-off | H2 / pf-off |
|--:|--:|--:|--:|
| 16 | 1.2369 | 1.2945 | 1.6012 |
| 48 | 1.1837 | 1.6220 | 1.9200 |

No mean, no range and no `n` is computed across the two points. They are two
operating points of one sweep, not two samples of one quantity — the
pre-registration forbade pooling them and the analyzer prints no pooled
statistic. This is the second defect the campaign existed not to reintroduce
(`H1BW_ARM_IDENTITY_2026-09-04.md` §Q3).

**The sign flip does not recur.** The archive's `WB / pf-off` was 1.183x at
48 MSHRs and **0.922x** at 16 — the appendix quoted only the first. Here it is
1.2945x and 1.6220x: above 1.0 at both depths, same direction. That is a
result about this campaign and is not a repair of the archive's.

---

## 2. Gates

All twelve pass on all nine cells. Full per-gate output is reproducible with
`python3 experiments/asplos/analyze_h1bw_singlecore.py`.

| gate | result |
|---|---|
| G1 instance `status == ok` | PASS x9 |
| G2 realized instance/workload count == 1 | PASS x9 |
| G3 LLC == 1 x 5 MiB, 20-way, 1 slice | PASS x9 |
| G4 memory model frozen (2 tk/B, 203/98 ns, `latency_var` 0, `SimpleMemory`) | PASS x9 |
| G5 policy engaged, **thresholds re-derived** | PASS x9 |
| G6 bracketing fired (3 sections, 1 OPEN, 1 CLOSE) | PASS x9 |
| G7 window fidelity (section-1 `simTicks` vs guest `seconds`, ≤0.5%) | PASS x9 |
| G8 realized `L1_MSHR`/`L1_REPL` == declared | PASS x9 *(after a parser correction — §7)* |
| G9 no local-DRAM traffic (`ALL_CXL=1`) | PASS x9 |
| G10 workload identical across arms | PASS x9 |
| G11 `checksum == 0` over 10 passes | PASS x9 |
| G12 prefetcher instantiation matches arm | PASS x9 |

`gem5_exit` is 0 for all nine. `free(): invalid size` count is **0** on all
nine — the corruption `AGGBW_VALIDITY` found in nine of 120 multi-core
instances does not appear here, and G11 confirms it independently.

`rounding error > tolerance` appears 6 times per cell and is **not** a gate
failure, as pre-registered: it is `a5f366456e`'s `abs()` guard on
`SimpleMemory.bandwidth` tick quantization, warning-only.

### G5 as re-derived, and what it measured

The pre-registration re-derived the engagement thresholds from the three
post-fix cells rather than inheriting `analyze_h1bw_bracket.py`'s
`A1_MIN_FILL_SUPPRESSION = 0.20` / `A1_MIN_BYPASS_PER_DECISION = 0.20`, which
were calibrated on pre-fix cells. The primary gate became a **residue count
per core** (`A1_MAX_UNBYPASSABLE_PER_CORE = 8000`) rather than a fraction,
because `H2_BYPASS_FIX_OUTCOME_2026-09-03.md` §4 established that the
"96% engagement ceiling" is a constant ~4,408 un-bypassable clean evictions
per core, not a ratio. Fill suppression against the matched WB arm was
re-derived **down** to 0.25 and kept as the corroborating gate, because
suppression is sensitive to exactly the untagged-prefetch population this
sweep varies.

Realized:

| cell | bypasses | E_clean | residue/core | suppression vs matched WB | HNF write retry |
|---|--:|--:|--:|--:|--:|
| wb@16 | 0 | 0.00% | — | n/a | 0.0% |
| h2@16 | 1,498,264 | 99.98% | **229** | 99.9% | 0.0% |
| pf-off@16 | 1,498,604 | 99.99% | **125** | 100.0% | 0.0% |
| wb@48 | 0 | 0.00% | — | n/a | 1.7% |
| h2@48 | 1,498,456 | 99.98% | **229** | 99.9% | 10.2% |
| pf-off@48 | 1,498,604 | 99.99% | **125** | 100.0% | 0.0% |

The residue is **229 and 125 per core against a gate of 8,000** — a margin of
35x and 64x, and 1.5 orders of magnitude clear of the ~429,000 a
retry-leaking cell would read. Both `wb` cells record **exactly zero**
bypasses, so no STREAMING tag leaked into the control arm.

**The re-derivation was necessary and the direction was right.** The inherited
0.20 suppression floor would have passed a cell that had lost four fifths of
the policy; observed suppression is 0.999. Had the inherited fraction-based
`A1_MIN_BYPASS_PER_DECISION` been used as the primary gate it would also have
passed, but it would not have discriminated: `bypass/decision` reads 1.000
here against 0.570 in the post-fix multi-core cells and 0.011 in the collapsed
one, so its useful range moves with the configuration in a way the residue
count does not. The residue count is the sharper instrument and this campaign
is evidence for that, not merely an assertion of it.

### The one-slice hazard did not materialise

Pre-registered as the live risk: at one slice with **four** cores the ordering
inverted outright to `pf-off > h2 > wb` because the 32-entry HNF pool bound
rather than LLC fill traffic (65% write retry, 82.7% occupancy).

Realized at one core: HNF write retry peaks at **10.2%** (h2@48) against a
pre-registered threshold of 20%, and HNF TBE occupancy peaks at **48.0%**
against 60%. Both predictions hold, so **the ordering results below are about
H2 and not about the home node.** This was the correct thing to have declared
in advance, and it is the reason the 48-MSHR ordering can be reported as a
mechanism result at all.

---

## 3. Window-bracketed counters: achieved

**Yes, and without rebuilding `gem5.opt`.** The ops (`0x40`/`0x41`/`0x42`) were
already decoded by `cb290444`; what needed compiling was the *benchmark*, a
different binary from the simulator. `gem5/src/` was not touched and
`gem5.opt` was not rebuilt (hash verified equal to `cb290444…` by the runner
before launch, and again after).

To avoid the F13 defect, the bracketed benchmark was built to a **separate
name**:

| | path | sha256 |
|---|---|---|
| unchanged, published | `build/cxl_join_bench.gem5` | `cac9e27ab42448a89c7c51e93749107357795ced6456babf2f51bfe625140f93` |
| this campaign | `build/cxl_join_bench.gem5wbrk` | `2b9d67320ff86999b5e8e3d2cb98479043c3da62bbaa6135304a53ff48d9efad` |

`cac9e27a` is the provenance of all 24 `h1bw_mc_*` cells and was verified
byte-unchanged after the build. `--window-brackets` defaults **off**, so the
unbracketed path is bit-for-bit what predates the option.

Realized in every cell: exactly 3 stats sections, exactly one
`AGGBW_WINDOW_OPEN` and one `AGGBW_WINDOW_CLOSE` (G6), and section-1
`simTicks` agreeing with the guest's own reported `seconds` to within 0.5%
(G7). So the LLC-write column above is a count over the same eight passes the
bandwidth is a rate over.

**What this bought, concretely.** It converted the footprint column from a
whole-program total into a per-pass measurement, which is what makes the
262,144-line fill accounting testable at all — and the WB arm lands at
262,245 and 262,244 lines per pass, i.e. **1.0004x one full pass at both MSHR
depths**. The `config.ini` readback explains why that is the right
expectation: `alloc_on_readshared`, `alloc_on_readunique` and
`alloc_on_readonce` are all `false` while `alloc_on_writeback` is `true`, so a
read never allocates in this non-inclusive victim LLC and every data-array
write is an eviction. The accounting is confirmed, not assumed.

---

## 4. Pre-declared predictions: 15/19

### Structural — all six hold

| # | prediction | realized | verdict |
|---|---|---|---|
| S1 | pf-off bandwidth MSHR-insensitive (≤10%) | 2.527 → 2.527 GB/s, **+0.00%** | PASS |
| S2 | pf-off windowed footprint MSHR-insensitive (≤2%) | 83 → 83 lines/pass, +0.000% | PASS |
| S3 | h2 windowed footprint **rises** with depth | 136 → 137 lines/pass, +0.74% | PASS |
| S4 | wb footprint MSHR-insensitive (≤5%) | 262,245 → 262,244, +0.000% | PASS |
| S5 | h2 footprint < wb footprint at both depths | 136 vs 262,245; 137 vs 262,244 | PASS |
| S6 | ordering `h2 ≥ wb > pf-off` at 48 MSHRs | 4.852 / 4.099 / 2.527 GB/s | PASS |
| S7 | 16-MSHR ordering deliberately **not** pre-declared | observed `+H2 > WB > pf-off` | (as registered) |

S1 is exact to four significant figures — pf-off delivers 2.527 GB/s at both
16 and 48 MSHRs, and its footprint is 83 lines/pass at both. Tripling the
request pool changes nothing measurable, which is the prefetch-off signature
`H1BW_ARM_IDENTITY` read the archive's flat 4.60/4.60 as. **That reading is
confirmed on artifacts that exist.** It is the fifth line of evidence in that
document's arm-identity argument, and it now stands on measurement.

S3 holds but **barely, and much more weakly than the archive implied**: +0.74%
here against +17.8% there. The mechanism (a prefetched line reaching the HNF
without the STREAMING tag the demand path would have given it) is present and
has the predicted sign, but at one core it moves one line per pass out of
262,144 rather than 53,501. Reported as a directional confirmation whose
magnitude does not carry the archive's weight; see §5.

S7 is where the archive and this campaign genuinely differ in *ordering*
rather than magnitude: the archive had WB (4.24) **below** pf-off (4.60) at
16 MSHRs, and here WB (3.271) is **above** pf-off (2.527). Both signs were
admissible in advance precisely so this could be reported rather than
explained away.

### The windowed footprint bands — four failures, all in the same direction

| band | realized | verdict |
|---|---|---|
| WB@16 in [0.85, 1.15]x | 1.0004x | PASS |
| WB@48 in [0.85, 1.15]x | 1.0004x | PASS |
| +H2@16 in [0.02, 0.35]x | **0.0005x** | **FAIL (below floor)** |
| +H2@48 in [0.02, 0.35]x | **0.0005x** | **FAIL (below floor)** |
| pf-off@16 in [0.02, 0.20]x | **0.0003x** | **FAIL (below floor)** |
| pf-off@48 in [0.02, 0.20]x | **0.0003x** | **FAIL (below floor)** |

**These are the four failed predictions of the 19, and they failed because
suppression is roughly 40x more complete than predicted, not less.** The
floors of 0.02 were set on the expectation of a residue in the low thousands
per core, extrapolated from the post-fix multi-core cells' 4,433–5,315. At one
core the residue is 125–229, so H2 and pf-off retire essentially the entire
fill stream: 136 and 83 lines per pass against 262,144.

This is recorded as a **failed prediction**, not quietly reinterpreted as a
success. The pre-registration's stated purpose for these bands was to expose a
wrong fill accounting, and the accounting is in fact confirmed by the two WB
cells that bracket 1.0x. What the failure exposes is that the residue floor
was mis-extrapolated across core count — the un-bypassable population does not
scale down to a per-core constant as cleanly as `H2_BYPASS_FIX_OUTCOME` §4's
4,408/core suggested. That is a small correction to that document's
constant-per-core reading and is handed back as an addendum item (§8), not
applied to it here.

### Magnitude bands — all six hold

| band | realized |
|---|---|
| WB@16 in 3.0–5.5 GB/s | 3.271 (64.9% of the 16-MSHR ceiling) |
| WB@48 in 4.0–11.0 GB/s | 4.099 (27.1% of the 48-MSHR ceiling) |
| +H2@16 in 3.0–5.5 GB/s | 4.046 (80.2%) |
| +H2@48 in 4.0–11.0 GB/s | 4.852 (32.1%) |
| pf-off@16 in 2.0–5.2 GB/s | 2.527 (50.1%) |
| pf-off@48 in 2.0–5.2 GB/s | 2.527 (16.7%) |

At 48 MSHRs no arm reaches a third of the request-pool ceiling, so the
48-MSHR cells are **not** MSHR-capped: something else binds. The 16-MSHR cells
sit at 50–80% of theirs, so that depth is much closer to the pool being the
constraint. That is consistent with the archive's own reading ("at MSHR=16 all
arms are MSHR-capped") and it is what makes the sweep informative rather than
two replicates.

---

## 5. The archive's twelve numbers

`results/gem5_streaming/REPORT.md` §1 is the only surviving record: a
4,609-byte hand-written summary, no `stats.txt`, no `config.ini`, no per-run
JSON, and its runner (`knee_sweep.sh`) absent from this host. It does not
record its reps, its warmups, its binary, its commit or its `L1_REPL`.

### The pre-registered comparison, as specified

Bandwidth against `bandwidth_gbps`; footprint against **whole-program**
`llc_fills_total`, because the archive's column is whole-program. Reproduces
within ±20%.

| quantity | archive | new | delta | within 20% |
|---|--:|--:|--:|:--:|
| WB@16 bandwidth | 4.24 | 3.271 | −22.8% | no |
| WB@16 LLC writes | 529,330 | 2,877,871 | +443.7% | no |
| +H2@16 bandwidth | 4.90 | 4.046 | −17.4% | **YES** |
| +H2@16 LLC writes | 300,238 | 287,796 | −4.1% | **YES** |
| pf-off@16 bandwidth | 4.60 | 2.527 | −45.1% | no |
| pf-off@16 LLC writes | 289,695 | 286,607 | −1.1% | **YES** |
| WB@48 bandwidth | 5.44 | 4.099 | −24.7% | no |
| WB@48 LLC writes | 529,309 | 2,877,855 | +443.7% | no |
| +H2@48 bandwidth | 5.82 | 4.852 | −16.6% | **YES** |
| +H2@48 LLC writes | 353,739 | 287,817 | −18.6% | **YES** |
| pf-off@48 bandwidth | 4.60 | 2.527 | −45.1% | no |
| pf-off@48 LLC writes | 289,698 | 286,607 | −1.1% | **YES** |

**6 of 12 reproduce.** Fewer than the 9 the pre-registration set for outcome
A, so **outcome B obtains**, as expected.

### A confound the pre-registration did not anticipate, disclosed

The footprint rows of that table are **not a like-for-like comparison**, and
the pre-registration was wrong to specify them as one. Whole-program LLC
writes scale with the number of passes, and the two campaigns do not share
one: the archive's WB column of 529,330 is 2.019x the stream's 262,144 lines,
i.e. `warmups + reps == 2`, while this campaign runs 10. The +443.7% on the WB
rows measures that units mismatch and nothing physical. Bandwidth is a rate
and is unaffected.

Normalised to one measured pass — **post-hoc, labelled as such in the analyzer
output, and certifying nothing**:

| quantity | archive / pass | new / pass | delta |
|---|--:|--:|--:|
| WB@16 | 264,665 | 262,245 | **−0.9%** |
| +H2@16 | 150,119 | 136 | −99.9% |
| pf-off@16 | 144,848 | 83 | −99.9% |
| WB@48 | 264,654 | 262,244 | **−0.9%** |
| +H2@48 | 176,870 | 137 | −99.9% |
| pf-off@48 | 144,849 | 83 | −99.9% |

**WB reproduces to within 1% at both depths.** That is a meaningful
corroboration: the geometry, the line size, the fill accounting and the stream
size all agree between the two campaigns, because a full pass of 262,144 lines
is filled and evicted at either MSHR depth in both. It also independently
confirms the 16 MiB stream size that had to be inferred (§"Reconciling the
three sources", reconciliation 1) from the caption and from arithmetic rather
than read from a runner.

**H2 and pf-off do not reproduce, by three orders of magnitude, and there is a
specific and economical explanation.** The archive's own rows imply suppression
of 43% (h2@16) and 33% (h2@48). The fixed binary reads 99.9%. Pre-fix
one-slice cells read 47.4% for pf-off and 1.2% for h2
(`H2_BYPASS_COLLAPSE_2026-09-03.md`, `H2_BYPASS_FIX_OUTCOME_2026-09-03.md`
§4). The archive sits **inside the pre-fix range and nowhere near the
post-fix one.** The most economical reading is that the archive's footprint
column was taken on a binary whose STREAMING attribute did not survive the
request retry path — the defect `cb290444` fixes.

**This is an inference and is labelled one.** The archive's binary is gone and
its engagement cannot be measured; `H1BW_ARM_IDENTITY_2026-09-04.md` §Q4 is
explicit on that point and this campaign does not change it.

### What is concluded, per the pre-registered decision table

Outcome B, decided in advance: **the archive's ordering and mechanism are
corroborated — a third time, after `GATE1_H1BW_ANOMALY_RESOLVED_2026-08-18.md`
at matched work and the certified multi-core campaign — while its twelve
magnitudes are superseded, not reproduced.**

The table carries the new figures. The archived figures are not repaired, not
averaged with the new ones and not cited again as measurements; they are cited
only as the historical record of a claim. **This is not a failure of this
campaign and is not reported as one.** Four inputs differ and were disclosed
before launch: a different simulator binary, a different benchmark compiled
from a tree no record identifies, an L2 prefetch degree of 4 against
`run_se.sh`'s 8, and an inferred replacement-path depth.

One of those four is now **cleared** — see §6.

Two caveats on the ordering corroboration, both of which limit it:

1. **The 16-MSHR ordering does not reproduce.** The archive has
   `+H2 > pf-off > WB`; this campaign has `+H2 > WB > pf-off`. The corroborated
   ordering is the 48-MSHR one (S6), plus the MSHR-insensitivity of pf-off
   (S1/S2) and the fill separation (S5) at both depths.
2. **S3's magnitude is 24x smaller** than the archive's, so the
   "footprint rises with depth" mechanism is confirmed in sign and refuted as
   a *quantity* of the size the archive reports.

---

## 6. Diagnostic set D — `L1_REPL` is cleared

Three cells at `L1_MSHR = 48`, `L1_REPL = 16` (the archive's presumed default),
against the primary cells' `L1_REPL = 48`. Contributes no number to
`tab:h1bw`.

| arm | `L1_REPL`=48 | `L1_REPL`=16 | delta | E_clean 48 | E_clean 16 |
|---|--:|--:|--:|--:|--:|
| WB | 4.099 GB/s | 4.220 GB/s | +2.95% | 0.00% | 0.00% |
| +H2 | 4.852 GB/s | 4.938 GB/s | +1.76% | 99.98% | 99.99% |
| pf-off | 2.527 GB/s | 2.527 GB/s | −0.00% | 99.99% | 99.99% |

**Result: replacement-path starvation is not the explanation of the archive's
48-MSHR figures, and it is not a confound in this campaign's sweep.** The h2
row moves 1.76% — smaller than WB's 2.95%, so it is not even an H2-specific
effect — and `E_clean` is unchanged to four significant figures at
99.98%/99.99%. Starving the replacement path 3:1 against the request path does
**not** degrade H2 fill suppression at 48 MSHRs.

That is a **negative result against the hypothesis in
`CHI_config_8592.py:315-321`**, which named this as "a candidate cause of H2
fill-suppression degrading at high `L1_MSHR`". At one core it is not a cause.
The comment is not wrong to warn — the warning is what motivated setting the
knob explicitly — but the effect it anticipates does not appear at this
operating point, and that is worth recording because two prior
pre-registrations left the knob at its default and logged it as "a live
confound, recorded not endorsed". It can now be logged as measured-inert at
one core.

The decision to run the primary cells at `L1_REPL = 48` is unaffected and
remains the right one: it keeps the sweep a one-variable sweep, and the
diagnostic is what establishes that the choice did not manufacture the result
rather than merely asserting it. Note the direction — the *narrower*
replacement pool is marginally *faster* in both prefetching arms, which is the
opposite of starvation and is consistent with a small queueing effect rather
than a capacity one.

Remaining uncontrolled differences from the archive: the simulator binary, the
benchmark, and the L2 prefetch degree. **Two of the three no longer exist to
run against**, so they cannot be cleared by any experiment.

---

## 7. Departures, corrections and things that went wrong

Recorded because a certification is worth what its disclosures are worth.

**1. G8's parser was wrong and the gate fail-closed all nine cells.** G8 was
written against `^system\.ruby\.rnf(\d+)\.cntrl$` on the assumption that CHI
realizes L1 controllers under the `rnf` node. It does not: the realized names
are `system.cpu.l1d` and `system.cpu.l1i`. The pattern matched nothing, G8 read
an empty realized set, and the first analyzer run printed **VOID on all nine
cells** with "the SWEPT knob was not realized".

That is the gate behaving exactly as designed on an unreadable knob, and it is
the reason to have written it. The knob was realized as declared all along —
verified by hand in `config.ini` (16/48, 48/48, 48/16) **before** the line was
changed. The fix moves where the gate looks and changes neither its semantics
nor its declared values, and it is committed separately (`9bedc39`) from the
pre-registration (`b4ac57c`) so the sequence is visible in git. `system.cpu.l2`
is deliberately excluded from the pattern: `L2_MSHR` is a separate knob at 48,
so matching it would fail the 16-MSHR cells for the wrong reason.

**2. The pre-registration was rewritten seven minutes after launch by a
no-op cleanup pass.** Cell launch was 21:00:20–21:00:28; the file's mtime is
21:07:00, from a script run against it and the analyzer to strip suspected
line-number artifacts. It stripped none (verified: no line in either file
matches the artifact pattern). **No threshold or prediction could have been
tuned to data at that time, because no cell had produced a single byte of
`stats.txt` until well after it** — all nine `stats.txt` were still 0 bytes at
21:22, and the first stats section appeared at 21:36. The content was
committed at `b4ac57c` before any statistic existed. Recorded rather than
glossed, because "frozen before launch" is the claim the campaign rests on and
the mtime does not by itself support it.

**3. `hnf_sf_present` recorded the wrong thing.** It tested whether an `.sf`
section exists, which is always true: `CHI_config_8592.py` always attaches an
`sf` `RubyCache` to the HNF, as a placeholder (`assoc=1`, `block_size=0`,
`size=1024`) unless `HNF_SF_FINITE=1`. The flag that decides whether directory
capacity is enforced is `sf_finite`, realized **`false`** in every cell. The
analyzer now records that directly. **Reconciliation 5 of the
pre-registration stands**: this campaign runs with the directory unbounded,
and `tab:gem5cfg`'s 65,536-entry row is scoped to the finite-SF H3 runs of
`tab:h3sf`, not to `tab:h1bw`.

**4. A commit briefly captured another worker's uncommitted work.** The first
commit attempt added `cxl_join_bench.cpp` and the `Makefile`, which carry this
campaign's `--window-brackets` addition but also ~1,100 lines of unrelated
in-flight W8 full-system work. It was reset (`--soft`, worktree verified
byte-identical by sha256 before and after) and re-made with only this
campaign's three files. **The benchmark source and `Makefile` are deliberately
left uncommitted**, as their owner's state, and this campaign's dependency on
them is pinned by the `gem5wbrk` binary sha256 instead.

**5. Departures from `run_se.sh`**, all pre-registered: stream 16 MiB not 1 GiB
(`run_se.sh:16-17` states in terms that it is not the sweep's runner);
`PF_DEGREE_L2` 4 not 8 (matching `tab:gem5cfg` and the certified multi-core
cells); `RUBY_RANDOMIZATION` unset (it addresses per-CPU bandwidth asymmetry,
which one CPU cannot exhibit); benchmark `gem5wbrk` because `run_se.sh`'s
named binary does not exist on this host.

**6. `BUILD_PROVENANCE.md` §5b's fail-closed manifest check could not be
applied.** No `BUILD_PROVENANCE.json` exists in the build directory — the
binary was built by hand before the wrapper that writes it landed. The runner
records `gem5_build_provenance_json_present: false` rather than passing
silently, and substitutes an equality test against the sha256 the
pre-registration names.

**7. Realized provenance**, per cell `MANIFEST.json`:
`gem5_sha256 = cb2904444d5c5c4d31d9d8f07295209283d29e294ef1d885d789442d98e7bbe0`;
`gem5_git_describe = build-cb290444-1-gfa27f665db`;
`configs_git_describe = build-cb290444-1-gfa27f665db`, taken **at launch**
because `configs/` is a run-time input read from the working tree
(`BUILD_PROVENANCE.md` §4), not compiled in;
`bench_sha256 = 2b9d67320ff86999b5e8e3d2cb98479043c3da62bbaa6135304a53ff48d9efad`.
`gem5/src/` was not modified and `gem5.opt` was not rebuilt.

**8. Nothing under `gem5/logs/` was written.** Cells landed in
`logs/se_chi_h1bw_sc/` at the repository root. The three
`h1bw_mc_*_4c_l3x1_*fix` simulations the brief protects had in fact exited
(14:11–14:17, all `"exit":0`) before this campaign began; the separation was
kept regardless. Their `stats.txt` were read, read-only, to derive the G5
thresholds.

**9. Runtime.** Nine cells launched concurrently at 21:00, all complete by
21:54: **0.80–0.85 h per cell, 0.9 h wall**, against a pre-registered estimate
of 1.0 h per cell and a 3 h budget. Storage ~30 MB. The estimate was good to
about 15%.

---

## 8. What this campaign does not license

Unchanged from the pre-registration, and restated because the table is about
to be published on it.

- **These are not far-memory streaming bandwidth figures.** The LLC-residency
  confound of `AGGBW_VALIDITY_2026-09-03.md` §Q1/finding 4 is *measured* here
  rather than bounded, and it is large: in-window CXL reads per useful byte are
  1.0002 for WB but **0.7144 for +H2 and 0.7146 for pf-off**, so **28.5% of
  the streaming arms' read traffic is served by the LLC, not by CXL.**
  `fill_fact` writes the whole 16 MiB set immediately before the passes read
  it, and the STREAMING policy then declines to displace those dirty lines, so
  they survive to be hit. WB's own stream evicts them and it reads 0% from the
  LLC.

  **This is a material qualification of the H2-over-WB bandwidth ratio, not a
  footnote.** Part of the 1.24x/1.18x is a residency advantage the geometry
  hands to the non-allocating arms, and this campaign cannot separate that
  part from the fill-path-contention part. Measuring the share is an
  improvement over bounding it; removing it needs a benchmark-geometry change
  and a separate pre-registration.
- **It does not license a multi-core number**, and no multi-core number
  licenses these. One core is a different operating point.
- **It does not measure silicon**, and in particular cannot bound the modelled
  prefetcher against silicon's at CXL latency.
- **It does not recover the archive's runs.** Outcome B is supersession.
- **No across-run interval.** `cov` is within-run over eight reps.
- **Diagnostic D clears `L1_REPL` at 48 MSHRs only**, at one core.

---

## 9. Handbacks — not applied here

### `A1_PROVENANCE_LEDGER_2026-08-28.md`, F3

Proposed replacement wording, for central routing (the ledger is not edited by
this campaign):

> **F3 — `tab:h1bw`, twelve magnitudes: CLOSED on replacement, 2026-09-04.**
> The original twelve figures remain unbacked and are now unpublished: their
> artifacts never existed beyond a 4,609-byte hand-written `REPORT.md` in
> `preserved/gem5_streaming.tar.gz`, and their runner (`knee_sweep.sh`) and
> binary are absent from this host. They are superseded rather than repaired.
> `tab:h1bw` now carries six certified cells from
> `H1BW_SINGLECORE_OUTCOME_2026-09-04.md` — 3 arms x `L1_MSHR` {16, 48} at
> `L1_REPL = 48`, pre-registered at commit `b4ac57c` before any cell emitted a
> statistic, 6/6 passing all twelve fail-closed gates, with retained
> `stats.txt`, `config.ini`, per-cell `MANIFEST.json`/`DONE.json` and
> `data/gem5/h1bw_singlecore.jsonl`. Counters are window-bracketed, so the
> footprint column and the bandwidth column describe the same interval.
> Provenance: `gem5.opt` `cb290444…` (not rebuilt), benchmark
> `cxl_join_bench.gem5wbrk` `2b9d6732…`, `configs_git_describe`
> `build-cb290444-1-gfa27f665db` recorded at launch.
> **Disclosure: these are new magnitudes from a new harness, not a recovery of
> the old ones.** 6 of the archive's 12 figures reproduce within 20%
> (pre-registered outcome B). The archive's ordering is corroborated at
> 48 MSHRs and its 16-MSHR ordering is not: it had WB below `pf-off`, and the
> certified sweep has WB above at both depths. The archive's third arm was
> mislabelled `WC`; gem5 has no write-combining memory type
> (`H1BW_ARM_IDENTITY_2026-09-04.md`), and the arm is labelled `pf-off`.

### `INDEX.md` rows

Proposed rows, for central routing (`INDEX.md` is not edited):

> `H1BW_SINGLECORE_PREREG_2026-09-04.md` — Pre-registration: single-core MSHR
> sweep `{wb, h2, pf-off}` x `L1_MSHR` {16, 48} at `L1_REPL = 48`, 16 MiB
> stream against 5 MiB LLC, as the certified replacement for `tab:h1bw`'s
> twelve unbacked magnitudes. Twelve fail-closed gates; G5 engagement
> thresholds re-derived for `cb290444` as a residue **count** per core
> (8,000) rather than an inherited fraction. Frozen at `b4ac57c` before
> launch. First campaign in this project with window-bracketed counters.
>
> `H1BW_SINGLECORE_OUTCOME_2026-09-04.md` — **CERTIFIED, 6/6 primary cells,
> 15/19 pre-declared predictions.** 16 MSHRs: WB 3.271 / +H2 4.046 / `pf-off`
> 2.527 GB/s. 48 MSHRs: WB 4.099 / +H2 4.852 / `pf-off` 2.527 GB/s; LLC
> data-array writes per measured pass 262,245 / 136 / 83 and 262,244 / 137 /
> 83. `cov` 0.05–0.11%. Both MSHR points reported, never pooled. Outcome B:
> the archive's ordering and mechanism corroborated at 48 MSHRs, its twelve
> magnitudes superseded (6/12 within 20%). Diagnostic set D clears
> replacement-path starvation as a confound. 28.5% of the streaming arms'
> reads are LLC-served, measured not bounded — these are not far-memory
> bandwidth figures.
>
> `run_h1bw_singlecore.sh`, `analyze_h1bw_singlecore.py` — runner and analyzer
> for the above. Siblings of the `h1bw_multicore` pair, which are not edited.

### Addendum items for other documents, not applied

- **`H2_BYPASS_FIX_OUTCOME_2026-09-03.md` §4**, the ~4,408 un-bypassable clean
  evictions **per core**: measured here at **125–229 per core** at one core,
  so the quantity is not a per-core constant across core counts. Its central
  correction — that the "96% ceiling" is a count and not a fraction — is
  confirmed and strengthened; only the constant's transferability across core
  count needs qualifying.
- **`CHI_config_8592.py:315-321`**, replacement-path starvation as "a
  candidate cause of H2 fill-suppression degrading at high `L1_MSHR`":
  measured inert at one core (§6). A source comment, not a certified outcome;
  noted for whoever owns that file.
- **`tab:gem5cfg`'s `Prefetch` row** reads "L1/L2 Stride(4) + DCPT". The L2
  pair is Stride + **Tagged**, not Stride + DCPT
  (`CHI_config_8592.py:703-721`), as `H1BW_ARM_IDENTITY_2026-09-04.md` already
  logged. A paper-text defect in a row this campaign does not own.

### `preserved/README.md`

Already corrected in the working tree — the `gem5_streaming.tar.gz` row now
states that the tarball holds a hand-written summary and **no per-run
artifacts**, so it records what was claimed and is not provenance for it. One
further clause is appropriate now that the table is certified: the tarball
backs a **superseded** claim, and `tab:h1bw` no longer rests on it.
