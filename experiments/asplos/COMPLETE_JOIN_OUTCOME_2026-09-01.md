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

---

## Addendum 2 — 2026-09-04. The realized LLC is 5.00 MiB, so realized table/LLC is 0.800 — this document's title, its `G0` cell and four other statements report a requested figure as a realized one

Full record: `NONPOW2_SETS_MEASURED_2026-09-04.md`. Superseded wording is
quoted here rather than deleted, per `A6.19`. **The verdict table is unchanged
and no magnitude in this document moves.**

### The finding

`--l3_size=7680KiB --l3_assoc=20` at 64 B lines gives
`(7864320 / 20) / 64 = 6144` sets. `CacheMemory::init()` then takes
`m_cache_num_set_bits = floorLog2(6144) = 12`, and `addressToCacheSet()`
selects exactly 12 index bits — so **4,096 of the 6,144 sets are ever
addressed** and the HNF simulates

    4096 sets x 20 ways x 64 B = 5,242,880 B = 5.00 MiB

which is 66.7% of the configured 7,864,320 B. This is the `[F9.4]`
set-quantization class; it is proposed as the record-keeping component of `F18`.

**It is now measured, not derived.** Previously on record as "derived from
source, not measured — no run emits a set count"
(`DUCKDB_MMAP_SE_H2_OUTCOME_2026-09-04.md` §3). Four SE cells,
`run_npot_probe.sh`, a 6 MiB cyclic sweep at `HNF_RP=lru` with prefetchers off,
on the campaign binary `cb290444` unmodified:

| cell | `--l3_size` | assoc | sets | HNF hits | misses | `simTicks` |
|---|---|--:|--:|--:|--:|--:|
| A | `5MiB` | 20 | 4096 | 166,595 | 128,498 | 26,881,767,046 |
| **B** | **`7680KiB`** | **20** | **6144** | **166,595** | **128,498** | **26,881,767,046** |
| C | `10MiB` | 20 | 8192 | 294,970 | 123 | 17,184,977,560 |
| **D** | **`7680KiB`** | **15** | **8192** | **294,970** | **123** | **17,184,977,560** |

**B is bit-identical to A on all 2,014 simulated quantities** (5 differing
lines, all five host-side). D requests the identical 7,864,320 B at an assoc
that makes the set count a power of two, and differs from B on 1,825 lines.
So `--l3_size=7680KiB --l3_assoc=20` and `--l3_size=5MiB --l3_assoc=20` are one
machine, and it is the 5 MiB one.

### The six statements this corrects

Quoted as written; the realized value follows.

1. **Title.** "*Outcome: complete join at table/LLC ≈ 0.53, tuples/s*" —
   realized table/LLC is **0.800**.
2. **"What ran", line 21.** "*8 MiB fact, 4 MiB table, HNF 7680KiB (realized
   7,864,320)*" — 7,864,320 is the **configured** size, correctly read back
   from `config.ini`. Realized is **5,242,880**.
3. **`G0` gate row.** "*G0 table/LLC = 4,194,304 / 7,864,320 = 0.5333 | PASS*"
   — realized is 4,194,304 / 5,242,880 = **0.800**. `G0` passed on a gate that
   tested `config.ini`'s `size=` field against a band computed from that same
   field, so it could not have failed; it is a requested-versus-realized gate
   reading a requested value on both sides.
4. **"What this does *not* do".** "*Growing the HNF from 5 MiB to 7.5 MiB did
   not raise H2's protection ceiling*" — **the HNF did not grow.** The
   observation that the ceiling did not move is correct and now has a simpler
   explanation: the cache was the same size. One line below, this document
   already contains the tell — "*2650 KiB already fit in the 5 MiB LLC*".
5. **Addendum 1, "The ratio r5 broke", `table/LLC` row.** "*table/LLC | 0.800 |
   **0.533** | 0.533*" — r5 realized **0.800**, identical to r3's. The ratio
   this campaign existed to change is the one ratio it did not change.
6. **Addendum 1, same table, `victim/LLC` row and the paragraph that reads
   it.** "*victim/LLC | **0.518** | **0.345** | 0.533*" and "*r3's victim
   occupied 52% of the LLC, matching silicon. r5 moved it to 34%. The victim is
   less vulnerable. That is why total tax fell 10.74 → 6.29 cyc and why P2
   landed at 1.185×.*" — realized r5 `victim/LLC` is 2,713,600 / 5,242,880 =
   **0.518**, which is r3's value to three digits. **The victim did not move,
   so it cannot be why the tax fell**, and this correction voids an
   explanation rather than a number. The fall must be attributed to what
   actually differed between r3 and r5 — a complete pass reporting tuples/s
   against a truncated pass reporting IPC — and the honest position is that no
   geometric account of it is available from this campaign. The next paragraph's
   conclusion survives and strengthens: "*r5 is not 'r3 with one knob fixed'*"
   is true because **r5 is r3's cache geometry exactly**.

Also inherited, and corrected by this addendum rather than rewritten:
Addendum 1's "*Matching both ratios at this HNF would need a ~4 MiB chase (4096
KiB for silicon's 0.533; 3975 KiB for r3's 0.518)*" is arithmetic against
7.5 MiB. Against the realized 5.00 MiB, silicon's 0.533 needs a **2,731 KiB**
chase (0.5333 × 5,242,880 = 2,796,203 B), i.e. r5's 2,650 KiB is already within
**3.0%** of it — realized `victim/LLC` is 0.5176 against silicon's 0.5333 — so
the standing instruction that follows ("*That run does not exist. Do not start
it to chase H2 R.*") is unchanged in force but no longer describes a ~50%
larger victim. The victim ratio this campaign reported as its broken one is in
fact its closest match to silicon.

The "Do not put ~1.07× in the paper" table is **unaffected**: it is indexed by
mask fraction (ways), and way masking is exact at every width because the
quantization is in the set count, not the way count.

### What survives, and what is void

**Survives — measured and unchanged.** All 45 runs, 15 arms, ran at **one and
the same realized geometry**: `l3_size_bytes = 7864320` in every committed
record, hence 5,242,880 B realized in every one. A ratio common to every arm
cannot distort a comparison between arms, so `fig:frontier`(a) — 12 CAT widths
plus `h2` as points, `wb` and `qui` as normalizers — **is internally valid and
its magnitudes stand as measured**. P5 PASS, the +9.97% registered wedge, the
+8.42% matched-R wedge, `R(h2) = 22.59%`, `R(wm16) = 35.93%`, the 1.185× WB
tax, tuples/s at every width: none is recomputed and none moves. The apparatus
gates other than `G0` are untouched.

**Void — the campaign's stated purpose.** The claim that r5 matched the model's
tenant pressure to silicon's. Realized `table/LLC` is 0.800 against silicon's
0.533, and realized `victim/LLC` is 0.518 against silicon's 0.533 — so this
campaign is r3's machine measured with a better metric, and the pre-registered
capacity correction never took effect. Nothing that compares r5 arms *to each
other* is affected. Anything that compares r5's tenant pressure *to silicon's*
is.

**The qualitative premise strengthens rather than breaks**, as
`DUCKDB_MMAP_SE_H2_OUTCOME_2026-09-04.md` §3 observed of the same geometry: the
table is 80% of the LLC rather than 53%, and the 8 MiB fact is 1.60× the LLC
rather than 1.07×. The design intent — a table large in the LLC and a fact
larger than it — holds more firmly at the realized geometry than at the
requested one.

### `P2`'s floor

"*r5 registered ≥1.15× (prereg: LLC 1.5× larger)*" — the LLC is **not** 1.5×
larger; it is the same size. So the floor was relaxed from r3's 1.30 to 1.15 on
a premise that did not obtain. `P2` was pre-registered before any arm ran and
measured 1.185×, so this is **not** a violation and the gate stands as
registered; but this document's own standing note — "*A floor that relaxes
between campaigns, in the direction that lets a marginal result pass, is stated
here next to the number*" — now applies without its justification. Recorded
here so the 1.185× is never quoted with "the LLC is 1.5× larger" attached.
