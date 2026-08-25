# The panel's sequencing advice is built on a premise that has already read out — into a third branch

Their latest response says *"you are one kernel-scale result away"*, *"finish the
smoke + registered falsifier run"*, and *"the deciding experiment is registered
and running"*. **It has read out.** M1 ran and was withdrawn (my cleanup error),
M1b ran, and a diagnostic settled the baseline. The answer is in
`M1B_OUTCOME_2026-08-25.md`.

## Their fork had two branches. The result is neither.

| their branch | prediction | actual |
|---|---|---|
| premise holds | F harms V ⇒ containment paper, **H2 resurrected**, Pareto frontier as Figure 1 | **premise holds — 2.7×**, more strongly than they argued |
| falsifier fires | F too slow ⇒ no containment scenario, measurement paper | — |
| **(absent)** | — | **premise holds, remedy fails**: removing F's entire 256 MiB CXL stream changes V's cost by **0.11%** |

- V cold **78.08**; V + dedicated 23.3 GB/s streamer **164.56 (2.11×)**; V + fused
  tenant **209–212 (2.68–2.72×)**. The control passes; the stakeholder is real.
- `V+F_notstream / V+F_big = 1.0011`. `V+F_small / V+F_big = 0.8726`. Both
  baseline-independent.

So there **is** a containment scenario, and H2 is **not** its container. A
stream-scoped label addresses 0.11% of the harm. What harms V is F occupying the
cache at all — dominated by sixteen workers touching memory, plus 13% from a hot
table that is F's own working data and must stay write-back.

## What this does to their sequencing

**Their conclusion survives, and hardens: hold the e2e build.** But not as a
wait-for-the-fork. Their own doctrine decides it — *"if the frontier doesn't
exist at kernel scale with a hand-built F and the W5.3 victim, no amount of
DuckDB engineering will create it."* It does not exist: H2's advantage column is
empty in the three-party configuration. **The containment e2e is dead, not
deferred.**

Their fallback branch is closer to right, but its description undersells the
result. It is not "stream-is-free, knobs-suffice, no measured victim". There *is*
a measured victim, harmed **2.7×**, and CAT does contain it while charging F's
reuse structure +19–44%. The expressibility argument is intact and now has a
stakeholder with a number. What is absent is any advantage for a *page-scoped
stream* type over the shipped context-scoped knob — because the stream is not
what does the harm.

## What of their advice still holds, and is worth doing

1. **The rate sweep — keep it, and it matters more now.** Their reasoning was
   right that a point falsifier is weaker than a dose–response. But redesign it:
   M1b showed the metric **saturates** (V is LLC-resident at 78 or DRAM-bound at
   ~209, and any substantial co-runner flips it), so a co-runner-pressure sweep at
   this geometry will mostly read binary. The informative axis is **F's own stream
   rate with F's probe held fixed** — cheaply available via `--hit-rate 1.0`,
   which doubles F's probe speed and therefore its stream rate with everything
   else constant. That tests whether the 0.11% grows with rate.
2. **The DuckDB spike — keep it, repurposed.** No longer "where does DuckDB sit on
   the harm curve" for a containment headline; now "does a real engine's scan rate
   push the stream's contribution above 0.11%". Still premise-informing, still a
   day.
3. **The common trunk — unaffected, and one item is now done.** The RocksDB
   page-cache layer verifies, and is in the paper: `sst_file_writer.cc:291`
   `InvalidateCache` → `posix_fadvise(POSIX_FADV_DONTNEED)`
   (`io_posix.cc:892`) under the comment *"Tell the OS that we don't need this
   file in page cache"*, plus `use_direct_io_for_flush_and_compaction` for
   compaction I/O. Stated precisely: layer 1 is read-side (block cache), layer 2
   is write-side (page cache) — different paths, one policy. **Production software
   declines retention at every layer it can name and stops exactly at the
   hardware boundary.**
4. **The cover note.** Agreed, and their framing needs one amendment: the honest
   note can no longer say "the original zero-state mechanism is resurrected for
   the containment case". The containment case exists and the mechanism does not
   reach it. The note should say the deciding experiment ran, the stakeholder is
   real at 2.7×, and the stream is 0.11% of it.

## And one correction to my own record they should have

M1's withdrawal was **my** fault, not the instrument's: between two discarded
attempts I killed the runner, `pointer_chase` and `stream_wb`, but never
`cxl_join_bench`, whose `--reps 2000` co-runners run ~206 s at 16 threads.
Every M1 arm including its baseline was measured against that background, which
is why all its ratios compressed toward 1.0 and why a 23.3 GB/s streamer appeared
to cost 2.8%. Incomplete cleanup between attempts, and the same class of error as
the rest of the week: state I did not verify before measuring against it.
