# Pre-registration: complete join at gem5 geometry, table/LLC ≈ 0.53

Date: 2026-09-01. Registered **before any arm of this campaign produced a
number.** Smoke of the config parser (`7680KiB` vs `7.5MiB`) is not an arm.

## Why

We have priced shipping mechanisms in application units on silicon. We have
not shown STREAMING helping an application. The r3 real-join frontier is SE,
truncated (`--reps 100`, victim `m5_exit`), and reports tenant **IPC**, with
table/LLC = 4 MiB / 5 MiB = **0.80**. Silicon is 32/60 = **0.53**. Truncation
was a window-ownership choice, not a tractability constraint.

This campaign is the single run that closes Q1: a **completed** 8 MiB join at
matched table/LLC, reporting `join_mtuples_per_s` and victim `cyc_per_load`,
arms WB / CAT-sweep / STREAMING.

It does **not** instantiate flush-behind (CHI `CLFLUSH` is a no-op). It does
**not** use FS `mprotect` (r12 is mechanism; OS-path performance is a second
cell). SE m5op is the H2 predicate, labelled as such.

## Geometry

| knob | r3 | this campaign | why |
|---|---|---|---|
| `--fact-bytes` | 8388608 | 8388608 | one complete pass; larger than LLC |
| `--hot-bytes` | 4194304 | 4194304 | smallest power-of-two×16 B above L2; 2 MiB is L2-resident and makes CAT inert |
| `--l3_size` | 5MiB (5242880) | **7680KiB (7864320)** | 4/7.5 = 0.5333… = 32/60. `7.5MiB` **does not parse** in gem5 `toMemorySize` |
| `--l3_assoc` | 20 | 20 | unchanged; this is a capacity correction, not an assoc change |
| `--reps` | 100 (truncated) | **1** (complete) | tenant emits JSON and calls `m5_exit` |
| `--warmups` | 0 | 0 | |
| `--hit-rate` | default 0.5 | **0.5** (pinned) | isolates table/LLC from r3; silicon e2e used 1.0 and is labelled |
| victim | `2650 12000000` | `2650 12000000` | outlasts one pass (~0.9e6 loads); tenant `m5_exit` ends the sim |
| `--declare` | m5op | m5op | labelled SE, not OS-path |

Victim working set is **not** scaled with the LLC. The defect being repaired
is table/LLC, not victim/LLC. 2650 KiB remains above the 2 MiB L2.

## Design, otherwise identical to r3

- Victim cpu0, tenant cpu1. Quiet replaces the tenant with `dummy`.
- CAT: `HNF_REQ_MASKS` on NodeID 5 = `cpu1.l2`, read back from `config.ini`.
  Widths w in {1,2,3,4,6,8,10,12,14,16,18,20}; mask = `(1<<w)-1`; w=20 is the
  unmasked control and must reproduce `wb`.
- STREAMING: `--policy stream` (SE m5op on the fact only).
- `HNF_RP=lru` on every arm. Pins: `HNF_SF_FINITE=0 HNF_SF_SETS=4096
  HNF_SF_WAYS=16 HNF_H3=0 HNF_DMT=0 HNF_FWD_UNIQUE=0 SEQ_OUT=1024
  RUBY_RANDOMIZATION=1`.
- 3 seeds. Run names `r5_<arm>_s<seed>` with zero-padded widths (`r5_wm01_s1`).
- Host: mos181 (gem5 tree and `gem5.opt` live here). c4 (mos182) has no
  `gem5.opt`; it is the silicon host and is left idle.

## What the tenant does at the end of a complete pass

`run_single` already resets stats after setup and declaration. After one pass
it emits JSON (so `join_mtuples_per_s` exists) and, under SE, calls
`m5_exit`. Truncated campaigns never reach that call, so r3's lifetime
semantics are unchanged.

Quiet: `dummy` exits immediately; the victim completes 12e6 accesses and
`m5_exit`s. Window length differs from contended arms by construction;
`cyc_per_load` is a rate and remains the protection metric.

## Registered predictions

- **G0 (geometry).** Every admitted run has realized HNF size 7864320 and
  instantiated hot 4194304, hence table/LLC in [0.530, 0.537]. Refuted if any
  admitted run is outside; that run is not a result, it is a harness bug.
- **P2 (pollution).** WB tax on the victim (`cyc_per_load` wb/qui) >= **1.15x**.
  Floor is below r3's 1.30 because the LLC is 1.5× larger; if tax < 1.15 the
  campaign is void for a *cost* claim (nothing to protect) and still reports
  the geometry gate.
- **P5 (dominance, primary).** Plotting tenant `join_mtuples_per_s` against
  victim protection, STREAMING lies strictly outside the CAT frontier: no way
  width achieves both protection >= H2's and tuples/s >= H2's.
  Refuted if any width matches or beats H2 on both axes.
- **P6a.** w=20 reproduces wb within 1% on victim `cyc_per_load` and on
  tuples/s.
- **P6c.** Tenant tuples/s is non-decreasing as ways are added (tolerance 0.5%
  of wb). Protection monotonicity is **not** a pass/fail apparatus check
  (r3 P6b: way-starvation is real).
- **P_complete.** Every non-quiet arm's log contains `JOIN_MEASURE_END`,
  `JOIN_M5_EXIT`, a JSON record with `status=ok` and `join_mtuples_per_s > 0`,
  and `victim_loads` in [1e5, 6e6] (tenant ended the sim; 12e6 would mean the
  victim did). Quiet has no JSON and `victim_loads` in [1.1e7, 1.21e7].
- **P_bypass.** `h2` HNF streaming-fill bypasses > 0; every other arm exactly 0.

No 85% matched-protection precondition (r3 P1). H2's ceiling is the quantity
this geometry is designed to move; requiring 85% would void a success.

Wedge, if P5 holds: cheapest CAT width with protection >= H2, then
`h2_tuples / that_cat_tuples - 1`.

## Analysis plan

Victim: `cyc_per_load` = cpu0 cycles / cpu0 load insts. Protection =
`(wb - arm) / (wb - qui)`. Tenant primary: JSON `join_mtuples_per_s`
(chrono, gem5 `clock_gettime` is simulated time). Cross-check: `n_tuples /
(cpu1.numCycles / 1.9e9) / 1e6` with `n_tuples = fact_bytes/16`; must agree
within 8% or the chrono path is untrusted and the stats-derived number is
reported instead, labelled.

A run is admitted only if A1 (gem5 exit 0, stats dump), G0, P_complete's
per-arm clause, A4 (`hnf_requestor_masks` matches the arm as integers), and
P_bypass.

## Apparatus (filled after rebuild, before first arm)

- gem5: `build_Intel_8592/gem5.opt` sha256 `cfd37207b9b7124ae88af7192178518b21c89b44a84d582efa69960ce19b9ed1` (same as r3)
- tenant: `cxl_join_bench.gem5` sha256 `401373ce94799ec6b00a814f310243e902f0118197cca2999506a51dbf25c864` (JOIN_M5_EXIT rebuild)
- victim: `1f6214b8cadb451371665e73a08ee584f5a3efb062b8ced0f9cef6fb08f6a7fd` (unchanged)

Launcher: `experiments/asplos/run_complete_join.sh`. Analyzer:
`experiments/asplos/analyze_complete_join.py`. Archive:
`experiments/lib/archive_gem5_runs.py` → `data/gem5/r5_runs.jsonl` after
66/66, not incrementally (A6.19).

## Do not

- Draw these tuples/s onto the silicon CAT/flush-behind figure unlabelled.
- Quote this as FS `mprotect` performance.
- Produce a gem5 flush-behind arm.
- Change `--hot-bytes` to 2 MiB to "match" 0.53 (L2-resident, CAT inert).
- Pass `--l3_size=7.5MiB` (ValueError).

## Addendum 1 — 2026-09-02. Two apparatus notes after the audit.

P6a's w=20 arm is `requestor_masks=''`, byte-identical to wb.  Passing
P6a shows the empty-mask config is deterministic.  It does not test the
mask path.  A full-width control would set `0xfffff`.  Inherited from
`rj3.sh`.

P2's floor is 1.15, not r3's 1.30, because the LLC is 1.5× larger.  That
justification is in the P2 bullet above; it belongs next to the measured
1.185× wherever that number is quoted.

The registered geometry knob is table/LLC.  Growing the HNF with a fixed
2650 KiB victim necessarily lowers victim/LLC (0.518 → 0.345).  That
trade is a limitation of this campaign, not a later surprise.

---

## Addendum 2 — 2026-09-04. Line 28's justification is the origin of a capacity error: `7680KiB` at 20 ways realizes 5.00 MiB, so this registration's own capacity correction never took effect

This document is **sealed**; nothing above is rewritten. This addendum records
what the registered geometry realizes, quoting the superseded reasoning in
place per `A6.19`. Full record: `NONPOW2_SETS_MEASURED_2026-09-04.md`. The
outcome document carries the matching Addendum 2. **No registered prediction is
withdrawn and no measured value moves.**

### The line

The geometry table's `--l3_size` row, and its justification, read:

> | `--l3_size` | 5MiB (5242880) | **7680KiB (7864320)** | 4/7.5 = 0.5333… = 32/60. `7.5MiB` **does not parse** in gem5 `toMemorySize` |

The second sentence is right and remains useful: `7.5MiB` genuinely does not
parse, and `7680KiB` is the correct way to spell 7,864,320 B to gem5. The
**first** sentence is where the error enters. `4/7.5 = 0.5333` is arithmetic
against a capacity the simulator does not provide.

`(7864320 / 20) / 64 = 6144` sets; `CacheMemory::init()` takes
`floorLog2(6144) = 12`; `addressToCacheSet()` selects 12 index bits. So 4,096 of
6,144 sets are reachable and the HNF realizes

    4096 x 20 x 64 = 5,242,880 B = 5.00 MiB   (66.7% of configured)

**Realized `table/LLC` is 4,194,304 / 5,242,880 = 0.800** — the r3 value this
campaign was designed to move away from — **not 0.5333**.

**Measured, not derived.** `--l3_size=7680KiB --l3_assoc=20` is bit-identical
to `--l3_size=5MiB --l3_assoc=20` on all 2,014 simulated quantities (four SE
cells, `run_npot_probe.sh`, campaign binary `cb290444` unmodified), while
`--l3_size=7680KiB --l3_assoc=15` — the same requested bytes at a power-of-two
set count — differs on 1,825 lines.

### The three consequences for this registration

1. **`G0` could not have failed.** As registered: "*Every admitted run has
   realized HNF size 7864320 and instantiated hot 4194304, hence table/LLC in
   [0.530, 0.537]*". Both sides of that test come from `config.ini`'s `size=`
   field, which records the **requested** size faithfully. A gate written to
   catch requested-for-realized substitution was reading a requested value, so
   it passed on the geometry it was meant to police. Registered in advance and
   measured honestly — but not the check it was intended to be. This is the
   `F17` shape (an instrument that cannot observe the quantity in its own
   claim) and is proposed as component (2) of `F18`.
2. **`P2`'s floor rests on a premise that does not obtain.** As registered:
   "*Floor is below r3's 1.30 because the LLC is 1.5× larger*". The LLC is
   **the same size as r3's**. `P2` was fixed before any arm produced a number
   and measured 1.185×, so the gate stands exactly as registered and this is
   **not** a post-hoc relaxation; what is void is the reason given for the
   relaxation. The 1.185× must never be quoted with "the LLC is 1.5× larger"
   attached.
3. **Addendum 1's third paragraph is void, and it is the sharpest instance.**
   As written: "*The registered geometry knob is table/LLC. Growing the HNF
   with a fixed 2650 KiB victim necessarily lowers victim/LLC (0.518 →
   0.345). That trade is a limitation of this campaign, not a later
   surprise.*" The HNF did not grow, so **no trade was made**: realized
   `victim/LLC` is 2,713,600 / 5,242,880 = **0.518**, identical to r3's. The
   paragraph was written to pre-empt a later surprise and instead names one
   that did not happen, while the real one — that `table/LLC` never moved —
   went unnamed.

### What this registration still licenses

Everything it registered about **arms, seeds, metrics and thresholds**, all of
which were fixed before any number existed and all of which were met. The
design is intact: victim `2650 12000000` on cpu0, tenant on cpu1, `HNF_RP=lru`
with the pins listed above, 12 CAT widths plus `wb`/`qui`/`h2`, 3 seeds,
`join_mtuples_per_s` primary with the cycles-derived cross-check. **P5's
verdict stands as measured**, because all 45 runs share one realized geometry
and a comparison between arms is unaffected by a ratio common to all of them.

What it does **not** license is the sentence its "Why" section opens with:
"*table/LLC = 4 MiB / 5 MiB = 0.80. Silicon is 32/60 = 0.53*", followed by
this campaign being "*the single run that closes Q1: a completed 8 MiB join at
matched table/LLC*". **The join was completed and the table/LLC was not
matched.** The correct description of what ran is: r3's cache geometry, exactly,
with a complete pass and tuples/s instead of a truncated pass and IPC. That is
still a result worth having — it is the change this registration made that had
an effect — but it is not a matched-pressure comparison to silicon, and must
not be quoted as one.

### If this campaign is ever re-run at genuinely matched pressure

The registration's own "Do not" list already forbids the two wrong fixes
(`--l3_size=7.5MiB`, which does not parse; `--hot-bytes 2MiB`, which is
L2-resident). A third is now needed: **do not respell 7,864,320 B.** No
`--l3_size` value reaches 7.5 MiB at 20 ways — the attainable capacities are
`2^k x 20 x 64`, i.e. 5 MiB then 10 MiB. Matching 0.533 requires either an
assoc whose set count is a power of two at the wanted size
(`--l3_size=7680KiB --l3_assoc=15` gives 8,192 sets and a genuine 7.50 MiB, at
the cost of the pinned associativity), or a different `--hot-bytes` against the
realized 5.00 MiB (2,796,203 B for 0.533, which is not a power of two and
conflicts with the `--hot-bytes` row's own justification). Either is a
pre-registration amendment, not an analysis decision — the same conclusion
`W7.2_A1_SIZING_2026-08-24.md` reached for W7's A1 at 32 MiB.
