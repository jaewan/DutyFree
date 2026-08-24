# Second-pass audit: are today's interpretations right, and were the runs done correctly?

Re-examined the day's highest-consequence claims against the artifacts rather
than against my own summaries. **Three corrections, one of which changes a
sentence already published; two conclusions strengthened; the rest confirmed.**

---

## Corrections

### C1 — The quiescent loop executes a hardware division per probe. I attributed its cost to nothing.

`run_hot_probe` indexes `keys[i % keys.size()]`. `keys.size()` is
`table_capacity/2 = 8,388,608` — a power of two, but a **runtime** value, so the
compiler cannot strength-reduce it. Verified in the disassembly: a 64-bit
`div %r9` at `0xa812`, inside hot-probe's worker (entry `0xa6c0`), and inside the
loop body (the enclosing backward branch is `jb a800` at `0xa883`). `join_range`
(`0x9e40`) contains **no** divide; there is exactly one integer `divq`-class
instruction in the whole binary and it is this one.

So the two loops differ in **three** ways, not one: probe hit rate (100% vs 50%),
key source, and a per-iteration hardware division.

**What this changes.** My published sentence read *"At a matched hit rate the
fused kernel is faster than the quiescent one (44.0 vs. 55.2) while still
streaming 256 MiB from CXL."* True, but it left the 11.2 cyc/access gap
unexplained, inviting the reader to credit it to the stream being free. Corrected
in `Appendix.tex` to name the division and state that the two land *within about
11 cycles of each other, which is the order of that division*, and in
`Sec3_Mitigation.tex` to say the comparison spanned **two different loops**
rather than two workloads.

**What it does not change.** The headline — that `tab:fused`'s quiescent row is
not a baseline for the fused rows — is *strengthened*: there are now three
independent code-path differences instead of one.

### C2 — `panel_B16`'s "low mode" is a single sample, not a mode.

My bimodality table listed CAT 4/20 as `1 rep @ 106.38 / 29 @ 126.81`. One
outlier out of thirty is not a second mode, and I should not have put it in a
column headed "low mode". The genuinely bimodal arms are **CAT 8/20 (6/24)** and
**CAT 12/20 (12/18)**.

Consequently the monotone-within-mode claim needs splitting: the **high-mode**
sequence is populated throughout (n = 18–29) and carries the claim; the low-mode
sequence is well supported only across 20/20 → 12/20 → 8/20, and its 4/20 entry
(n=1) must not be leaned on. Both are monotone; only one is well sampled.
`QOS_STATE_DEPENDENCE_2026-08-24.md` corrected.

### C3 — Phase 1b's control is confounded, in our favour, and I did not say so.

`--no-stream` does more than remove the stream. `local_n` is capped at 65,536
entries, so `Qs` probes only ~65k distinct keys — about **1 MiB of the table**,
L2-resident — while `A` draws 16.7M times across the whole **256 MiB** table
*and* streams 256 MiB from CXL.

So `Qs` enjoys two large advantages and is still **slower** (92.602 vs 91.808).
That makes "the stream costs ≈0" *understated*: the arm with no stream and a
1 MiB probe footprint loses to the arm with a 256 MiB stream and a 256 MiB probe
footprint. A referee will notice `Qs` is not a pure control, so the asymmetry
should be stated rather than discovered.

It also explains the magnitude of the TMA result: if `A`'s probes were dominated
by memory, a 256× larger footprint could not come out ahead. The hot table at
256 MiB sits inside a 320 MiB LLC, so those probes are largely LLC hits — and the
loop's cost is elsewhere, which is what the 15.9% memory-bound share says.

---

## Verified correct

- **Phase 1b is hit-rate matched.** `fill_fact(fact, n, keys, c.hit_rate, ...)`
  is called on every path including `--no-stream`, so both arms probe at 50%.
  This was the load-bearing validity condition for 1b and it holds.
- **The TMA differential arithmetic.** Frac × cycles is proportional to a
  category's cycle-equivalent contribution (slots = width × cycles, width
  constant, so it cancels in the share). Independently confirmed by the data:
  phase 1's four L1 shares sum to **exactly 100.0%** (19.4 + 46.8 + 15.4 + 18.4).
- **The TMA falsifier.** Slots summed to 0.9998–1.0002 with every counter at
  **100% enabled** in both phases; the sub-bucket set was correctly excluded for
  multiplexing at 16–34%.
- **T3's walk arithmetic.** Stream pages 65,536 → 128 (confirmed by 128 consumed
  hugetlb pages) against a 1.0–1.8% measured drop versus ~99.8% predicted. A
  measured-vs-predicted contrast, independent of arm order and timing. The
  alternative reading — that reducing the stream's TLB footprint should also have
  relieved the hot table's walks by competition — is contradicted by the same
  1.8%, which supports the conclusion rather than weakening it.
- **A6's resource matching.** `F` and `Ssmt` each occupy one physical core
  (`thread_mapping` reports `physical_core: 32` for both cpu32 and cpu160), and
  `Score`'s two-core advantage is disclosed everywhere its throughput appears.
- **The RocksDB source exhibit.** All three references checked line by line
  against the `v9.11.2` tree before being written into the paper.
- **Item 14's closure.** The decision not to run rests on a documented null with
  a mechanism, not on convenience; the doc's own recommendation is explicit.

---

## Pattern

Every correction here is the same shape as the day's five retractions: a property
asserted from reading part of an artifact instead of testing it end to end. C1
required a disassembly, C2 required looking at the sample counts behind a
summary, C3 required reading what a flag does beyond its name. None of them was
visible from the numbers alone.

Two of the three corrections **strengthen** the conclusions they touch. That is
worth noting against the day's earlier pattern, where four of five retractions ran
self-damaging: the direction of an error is not evidence about its cause, and
both directions come from the same failure to read.
