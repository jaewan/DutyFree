# Phase 2.1 — local-DRAM MSR 0x1A4 control: RESULTS

Dated 2026-08-07. Answers the panel's question about E2a's flat prefetcher-
bit response on CXL: does the same toggle crater local DRAM bandwidth?

## Config

Identical to E2a: `stream_wb --no-verify`, cpu1, 16 GiB region, 8s/rep,
n=12, rep-interleaved across {cxl, local} x 6 MSR configs (12 arms/rep).
Governor=performance, turbo=off (re-frozen this session).

## Results

| config | CXL median (GB/s) | 95% CI | local median (GB/s) | 95% CI |
|---|---:|---:|---:|---:|
| all_on | 8.890 | [8.887,8.894] | 14.139 | [14.127,14.143] |
| l2hw_off | 8.762 | [8.759,8.764] | 13.485 | [13.473,13.489] |
| l2adj_off | 8.896 | [8.893,8.896] | 14.145 | [14.136,14.148] |
| dcu_off | 8.896 | [8.893,8.898] | 14.143 | [14.140,14.150] |
| dcuip_off | 8.964 | [8.959,8.967] | 14.166 | [14.160,14.172] |
| all_off | 8.863 | [8.860,8.864] | 13.506 | [13.500,13.508] |

## Verdict: asymmetric, not symmetric -- neither branch cleanly, a third answer

Neither of the panel's two clean branches holds exactly:

- **Not "local craters, CXL doesn't"**: local drops only ~4.5%
  (14.14 -> 13.51 GB/s), not a crater.
- **Not "neither craters, so a hidden prefetcher explains both equally"**:
  the two memory types respond *differently*. Local shows a small but real,
  reproducible effect (n=12, tight non-overlapping CIs) tied specifically to
  configs that disable the L2 HW streamer (`l2hw_off` and `all_off` both land
  at ~13.5 GB/s; every config that leaves the L2 streamer on lands at
  ~14.14-14.17 GB/s, regardless of the other three bits). **CXL shows no such
  pattern at all** -- all six configs cluster within ~2.3% of each other,
  with no config standing out as the "prefetcher on" cluster the way local's
  does.

**Reading**: on local DRAM, the L2 HW streamer contributes a real, small,
reproducible ~4.5% of achieved bandwidth for this scalar sequential-read
kernel; on CXL, that same mechanism contributes nothing measurable. This is
consistent with the panel's second branch in spirit (prefetchers engaging
less, or not at all, on CXL-backed memory specifically) but the magnitude on
local is far too small to call it a "crater," and the local result rules out
one clean alternative explanation (that a single hidden, always-on prefetcher
independent of 0x1A4 accounts for ~all of the bandwidth on both memory
types) -- if that were the whole story, local's ~4.5% dependence on the L2
streamer bit specifically wouldn't appear at all.

**What this does NOT rule out, still open**: whether the *majority* of
bandwidth on both memory types (the ~8.9 GB/s CXL floor, the ~13.5 GB/s local
floor that persists even at all_off) comes from the core's own
out-of-order/load-buffer-depth MLP rather than any prefetcher at all. This
kernel (`stream_wb.c`) issues one independent 8-byte load per 64B line with
no data dependency between iterations -- a modern OOO core can sustain many
such loads concurrently purely from reorder-buffer/load-queue depth,
independent of HW prefetch, for exactly this access pattern. Disentangling
"OOO-derived MLP" from "an uncontrolled prefetcher outside 0x1A4" would need
either a dependency-chained variant of this kernel (removing OOO-derived MLP
entirely, isolating whatever prefetch contribution remains) or a direct
occupancy/outstanding-request PMU count, neither of which was run in this
pass. Flagged as the next diagnostic step, not resolved here.

## Correction to my own first draft of this section

I initially wrote that the panel's "matching the machines" framing wasn't a
verified quote. **That was wrong -- it is a direct quote, I had the wrong
prefetcher.** `Sec5_Evaluation.tex:87` states exactly: *"L1/L2 stream/stride
prefetchers enabled (LLC prefetcher disabled, matching the machines)."*

But re-reading it precisely changes which experiment it bears on. MSR 0x1A4
(what E2a/Phase 2.1 toggled) controls four **L1/L2-level** prefetchers (L2
streamer, L2 adjacent, DCU streamer, DCU IP). The paper's gem5 model keeps
*those* **enabled**, claiming that matches the real machines -- consistent
with this campaign never disabling them either (E2a/E2b/E3 all ran with
0x1A4=0x0, all-on, except this specific control experiment). The claim this
note actually makes is about a **separate LLC-level prefetcher**, which
0x1A4 does not control and which this experiment never touched. So:

- **This experiment neither confirms nor falsifies the paper's "LLC
  prefetcher disabled, matching the machines" claim.** It answers a related
  but different question (does L1/L2 prefetch state affect bandwidth) that
  this campaign happened to need answered for its own reasons (the flat
  MSR-sweep anomaly in E2a).
- **No correction to the paper's text is warranted from this experiment.**
  The claim about the LLC prefetcher stands untested by anything in Phase 1
  or Phase 2 so far.
- **Open, not attempted here**: verifying "LLC prefetcher disabled" on the
  real EMR machine would need identifying whatever control actually governs
  it -- not obviously exposed via MSR 0x1A4, and not identified in this
  pass. If it matters enough to verify, that's a distinct follow-up, not
  something this experiment's data can be stretched to cover.
