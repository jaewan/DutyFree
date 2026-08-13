# tab:h1bw re-run (#26) — reconstructed harness, direction confirmed, ordering NOT reproduced, cause unresolved

Written 2026-08-13. Per `PAPER_SESSION_PROMPT.md` #26 ("`tab:h1bw` re-run —
unbound provenance (date only), #26 before #25"). Read §8 (verification
protocol) and §6 (traps) before trusting any number below.

## Provenance

- `~/DutyFree-Gem5` HEAD: `b2c64991948e771e660041b17ef8c0265d835873`
  (2026-08-11 10:32:16 +0900) — same commit the Gate-1 `tab:gem5` local-DRAM
  column was re-instantiated at.
- New probe binary: `testcase/dutyfree/h1bw_stream.c` (committed alongside
  this doc). **No original harness survives** — the c3-session scripts that
  produced the published `tab:h1bw` numbers
  (`/tmp/run_arm.sh`, `/tmp/run_arm_mshr.sh` per `streaming-gem5-results`
  memory) lived only in `/tmp` on a session that is gone. This is therefore
  a **current-HEAD reconstruction from source**, not a historical
  reproduction — label it that way anywhere it's cited, exactly as pass 5
  labelled `tab:gem5`.

## Two real bugs found and fixed en route

1. **Stats-reset confound.** `testcase/dutyfree/aggressor.c` (the obvious
   first choice — it already calls `gem5_set_streaming`) never calls
   `gem5_reset_stats()` after its init-write pass. A `--maxinsts`-bounded
   run of it standalone measures the one-time read-for-ownership traffic of
   initializing the static array, not the intended steady-state read-only
   stream — confirmed directly: a 5,000,000-instruction probe came back
   with **zero** LLC data-array fills, because the whole budget was consumed
   by init. Fixed by writing `h1bw_stream.c`, identical to `aggressor.c`
   except it calls `gem5_reset_stats()` right after the (optional)
   `gem5_set_streaming()` call and before the read loop.
2. **Wrong memory pool.** `se.py`'s default CPU→pool assignment puts CPU 0
   on the local-DRAM pool (98 ns) and only CPU 1+ on the CXL pool (203 ns).
   A single-core run therefore lands on local DRAM unless `ALL_CXL=1` is
   set — and it must be, here: the paper's own stated formula for the
   "concurrency-capped" arm, `16×64B/203ns ≈ 5 GB/s`, only works out
   (5.045 GB/s) at the **CXL** latency, not the 98 ns local figure. Without
   `ALL_CXL=1`, WB/WC bandwidth came back flat across both MSHR settings
   (10.4 vs 31.3 GB/s ceilings — neither anywhere near either arm's actual
   single-core issue rate, so the "concurrency ceiling" the table is built
   around never engaged). `se.py:320-339` documents `ALL_CXL=1` for exactly
   this case ("single-core CXL bandwidth/latency calibration").

Both fixes are real and should be kept for any future attempt at this
table. Neither is sufficient — see below.

## What the corrected harness reproduces, and what it does not

Config: `num-cpus=1`, `l3_size=5MiB` (20-way), `--maxinsts=20000000`,
`ALL_CXL=1`, `HNF_SF_FINITE=0 HNF_H3=0 HNF_DMT=0`. Arms: WB = `h1bw_stream
16.0` (default L1_MSHR); +H2 = `h1bw_stream 16.0 stream`; WC = `h1bw_stream
16.0` with `PF_OFF_CORES=0`. Swept `L1_MSHR` ∈ {16, 48} (L2_MSHR was tried
first and made no difference at either value — see below).

| | WB (published) | WB (measured) | +H2 (published) | +H2 (measured) | WC (published) | WC (measured) |
|---|---:|---:|---:|---:|---:|---:|
| 16 MSHR | 4.24 GB/s | **3.19 GB/s** | 4.90 GB/s | **2.76 GB/s** | 4.60 GB/s | **2.41 GB/s** |
| 48 MSHR | 5.44 GB/s | **5.12 GB/s** | 5.82 GB/s | **4.04 GB/s** | 4.60 GB/s | **2.41 GB/s** |

**Reproduced, directionally:**
- WC is flat across MSHR settings in both published and measured data
  (matches: prefetch-off shouldn't benefit from more outstanding misses).
- WB and H2 both scale up with MSHR depth in the measured data — the
  "concurrency ceiling clears" shape is present.
- H2 measurably reduces LLC data-array fills relative to WB (HNF
  `DataArrayWriteOnFill`, the 4th/last histogram bucket = the HNF instance
  confirmed via `config.json`'s `CHI_Cache_Controller` version-to-object
  map): WB ≈ 812,450 fills at both MSHR settings; H2 = 32,810 (16 MSHR) /
  47,493 (48 MSHR) — H2 is clearly engaging its non-allocating path.

**Not reproduced, and not understood:**
- **The ordering is backwards.** Published: H2 ≥ WB > WC at every point.
  Measured: **WB > H2** at both MSHR settings (3.19 > 2.76; 5.12 > 4.04).
  H2 should never be *slower* than WB — H1 is a paper invariant
  ("prefetchers train and issue as for WB", `PAPER_SESSION_PROMPT.md`
  §4.1.5) that H2 is specifically supposed to not disturb.
- **The mechanism behind it is stranger than a simple slowdown.** For a
  fixed instruction count, WB and H2 execute the *same* number of load
  instructions (verified: `numLoadInsts` 7,310,919 vs 7,310,908 — within
  noise) and generate essentially the *same* total L2 miss count (WB
  812,639; H2 812,644 — demand + prefetch, matched). Yet at the HNF, H2
  reports a dramatically **higher** hit rate than WB (H2: 245,834 hits /
  812,641 accesses ≈ 30%; WB: 212 hits / 812,639 accesses ≈ 0.03%) despite
  H2 being the *non-allocating* arm — the one that is supposed to leave
  fewer usable copies sitting in the LLC to hit against, not more.
- **Leading hypothesis, not yet confirmed:** the generic `CacheMemory`-level
  `m_demand_hits`/`m_prefetch_hits` counters instrumented inside the HNF's
  `cache` object may not distinguish a true data-array hit from a tag/
  directory hit against a pure-R (`RU`/`RSC`/`RSD`/`RUSC`/`RUSD`,
  `AccessPermission:Invalid`, no data block) entry — exactly the class of
  entry H2 (H3 off) still allocates on every streaming line via
  `Allocate_DirEntry`'s unchanged path. If so, "hit" here means "tag
  present," not "data servable from this level," and the reduced
  `bytesRead` for H2 traces to something else the tag hit correlates with
  (line coalescing at the HNF request-issue stage, an artifact of
  `isStreaming`'s effect on the prefetcher's train/issue decision, or a
  Ruby MessageBuffer scheduling difference) rather than to the hit itself.
  **This needs a `.sm`-level trace of the HNF's hit-classification logic
  (the CHI-cache.sm cache-access path, per §6.1's own playbook — "trace the
  `.sm` semantics," not the stat name) to resolve. Not attempted here**:
  that is a different, deeper task than a config re-run, and guessing
  further at the config level risks exactly the "fishing for a match" this
  project's rules (§6.6) forbid.

## Verdict

**Do not cite these measured numbers as a replacement for tab:h1bw, and do
not treat the published tab:h1bw ordering as re-confirmed.** What this
re-run establishes: (a) two real, fixable methodological bugs existed in
any naive attempt to reconstruct this table, now fixed and documented for
whoever picks this up; (b) H2's non-allocation mechanism is measurably
engaging (fill counts drop as expected); (c) the actual WB-vs-H2 bandwidth
ordering this table's central claim rests on is **not reproduced** at
current HEAD with this reconstruction, for a reason that is identified in
outline (a likely hit/tag conflation at the HNF) but not confirmed. Per
§10 ("a negative result is reported as a result"): this is not a clean
re-run, and it should not be paraphrased into one.

**Recommendation:** treat `tab:h1bw` as still resting on its original,
unrecoverable provenance rather than on this attempt. If it needs to move
before submission, the next step is a `.sm`-level trace of one address
through the HNF's hit path under H2 (H3 off), not another config sweep.
