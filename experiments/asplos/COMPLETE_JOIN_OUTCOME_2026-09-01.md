# Outcome: complete join at table/LLC ≈ 0.53, tuples/s

Date: 2026-09-01 (sweep finished 2026-09-02 04:32 KST).
Pre-registration: `COMPLETE_JOIN_PREREG_2026-09-01.md`.
Archive: `data/gem5/r5_runs.jsonl` (45/45 `completed=true`).
Analyzer: `analyze_complete_join.py` (exit 0).

## Verdict

**P5 PASS.** STREAMING lies outside the CAT frontier in **tuples/s**. No way
width matches H2 on both protection and tenant throughput.

Wedge at equal-or-better protection: **+9.97% tuples/s**. Cheapest CAT that
protects at least as well as H2 is w=16 (R=35.93%, −4.20% tuples/s vs wb);
H2 is +5.35% vs wb at R=22.59%.

This is SE m5op, not FS `mprotect`. Do not merge with r12.

## What ran

8 MiB fact, 4 MiB table, HNF 7680KiB (realized 7,864,320), `--reps 1`,
victim `2650 12000000`, tenant `m5_exit` after JSON. 15 arms × 3 seeds.
Mean hostSeconds 1994 s (~33 min/arm); 15-wide; wall ~4.6 h.

## Gates

| gate | result |
|---|---|
| G0 table/LLC = 4,194,304 / 7,864,320 = 0.5333 | PASS |
| P2 WB tax 1.1855× (≥ 1.15) | PASS |
| P_complete JOIN_M5_EXIT + JSON; qui loads 12,001,060; contended ~1.31e6 | PASS |
| P_bypass h2 129,545–129,613; all others 0 | PASS |
| A4 node-5 mask matches arm | PASS |
| P6a w=20 = wb bit-identical on reported means | PASS |
| P6c tuples/s monotone in width | PASS |
| JSON vs cycles tuples/s | max relative error 0.44% |

## Headline numbers (mean of 3 seeds)

| arm | victim cyc/load | R | tuples/s | vs wb |
|---|---:|---:|---:|---:|
| qui | 33.890 | — | — | — |
| wb | 40.176 | 0% | 18.985 | — |
| h2 | 38.756 | **22.59%** | **20.001** | **+5.35%** |
| wm16 (cheapest CAT ≥ H2 R) | 37.918 | 35.93% | 18.187 | −4.20% |
| wm08 (peak R) | 34.260 | 94.12% | 14.810 | −21.99% |
| wm01 | 34.652 | 87.89% | 11.526 | −39.29% |

## What this does *not* do

Growing the HNF from 5 MiB to 7.5 MiB **did not raise H2's protection
ceiling**. r3 (table/LLC=0.80, truncated, IPC) had H2 R=**24.11%**. This
campaign (0.53, complete, tuples/s) has H2 R=**22.59%**. The comparability
defect in r3 is real; it is not why H2 recovers only ~23% of the join's
victim tax. Fused.c's ~82% remains a different tenant.

Quiet victim latency is **33.890**, identical to r3's quiet to three
decimals — 2650 KiB already fit in the 5 MiB LLC.

Not flush-behind. Not silicon. Not FS `mprotect`.

## Addendum 1 — 2026-09-02. Audit of the r5 write-up.

Keep P5. Three corrections before any paper table. The verdict table
above is unchanged.

### The ratio r5 broke

G0 matched **table/LLC** (0.800 → 0.533 = silicon). It broke **victim/LLC**:

| | r3 | r5 | silicon |
|---|---:|---:|---:|
| table/LLC | 0.800 | **0.533** | 0.533 (32/60 MiB) |
| victim/LLC | **0.518** | **0.345** | 0.533 (32 MiB chase / 60 MiB) |

r3's victim occupied 52% of the LLC, matching silicon. r5 moved it to 34%.
The victim is less vulnerable. That is why total tax fell 10.74 → 6.29 cyc
and why P2 landed at 1.185×. Matching both ratios at this HNF would need a
~4 MiB chase (4096 KiB for silicon's 0.533; 3975 KiB for r3's 0.518), not
2650 KiB. That run does not exist. Do not start it to chase H2 R.

The autopsy (stream-removable 2.59 → 1.42 and residual 8.15 → 4.87, both
~40%) is the description. The cause is the shrunken victim/LLC. r5 is not
"r3 with one knob fixed."

### Quote both wedges

Registered P5 framing is cheapest CAT with R ≥ H2: **w=16, +9.97%**.
wm16 protects 35.93% against H2's 22.59% — it over-protects by 13.34 pp,
so it costs more, so the wedge is 1.55 pp generous.

Linear interpolation in R between wm16 (35.931%, 18.187 MT/s) and wm18
(13.639%, 18.622 MT/s) at H2's 22.591% gives 18.448 MT/s.

| framing | CAT comparator | wedge |
|---|---|---:|
| registered (R ≥ H2) | wm16 | **+9.97%** |
| matched R (post-hoc) | interpolated | **+8.42%** |

"Cheapest width that protects at least as well" is defensible. It is not
matched protection, and it errs toward the thesis. Quote both. The
iso-R number is labelled post-hoc; it does not change P5.

### Do not put "~1.07×" in the paper

r5 tuples/s vs silicon tuples/s at matched **mask fraction** (20-way vs
15-way; not matched R):

| % LLC | pair | ΔR (silicon − r5) | Δcost |
|---|---|---:|---:|
| 5% | wm01 vs cat01 | +3.5 pp | +2.8 pp |
| 10% | wm02 vs cat02 | −7.2 pp | +2.6 pp |
| 20% | wm04 vs cat03 | −18.1 pp | +4.5 pp |
| 40% | wm08 vs cat06 | −50.2 pp | +3.3 pp |

Cost tracks (2.6–4.5 pp). Protection diverges to 50 pp at mid-widths —
exactly the finding r5 was said to repair. tuples/s fixed the cost axis.
It did not fix the protection axis. 1.07× is the 1-way cost point only
(r5 wm01 −39.3% vs silicon cat01 −42.0%). Keep 1.64× as the r3-IPC vs
silicon-tuples/s calibration, labelled as such.

### wm20 is not a mask-path control

P6a passed: wm20 is bit-identical to wb on every seed. That is because
`requestor_masks=''` on both — the same empty-mask config as `rj3.sh`.
Bit-identity is tautological. A real full-width control sets `0xfffff`
and checks it behaves like unmasked. Inherited; do not write "if wm20
drifts from wb, the mask path is broken."

### P2's floor moved

r3 registered ≥1.30×. r5 registered ≥1.15× (prereg: LLC 1.5× larger)
and measured 1.185×. Pre-registered, not a violation. A floor that
relaxes between campaigns, in the direction that lets a marginal result
pass, is stated here next to the number.
