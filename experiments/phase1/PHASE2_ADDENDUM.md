# Phase 2 addendum — panel round 2: retraction, synthesis, hole-closing, new gap found

Dated 2026-08-07.

## A5's ×3.55 CXL-specific multiplier: retracted

Checked directly against the actual scripts (not memory): Phase 1's A5
compared CXL WB at ~24 GB/s (7T, natural rate) against local WB throttled
via `-R` to the same ~24 GB/s (also 7T) -- giving 19.89x vs 5.60x, hence
"×3.55 CXL-specific." Phase 2.2's unthrottled, thread-matched redo (bug
fixed: first draft's wrong aggressor mode string had silently run "local"
on CXL too) gives, at matched 7T and each source's own natural full rate:
**CXL 20.25x @ 24.14 GB/s vs local 17.14x @ 45.60 GB/s -- a ratio of ~1.18x,
not 3.55x.** The original number's confound (the `-R` throttle paces via
bursty 64 KB-chunk-then-spin cycles, plausibly distorting occupancy
dynamics) is real and sufficient to explain the gap between 3.55x and 1.18x.
**Retracting the ×3.55 CXL-path-specific-multiplier claim.**

What survives, and is better: the pathology is **source-agnostic
shared-path queueing** -- both CXL and local show tax climbing with thread
count while bandwidth is comparatively flat (local's 1T-to-7T bandwidth
barely moves, 43.4->45.6 GB/s, while tax climbs 4.15x->17.14x). CXL's
distinguishing feature is reaching its saturation knee (the 2T->3T jump,
6.4x->18.3x) at roughly half the bandwidth local needs to show comparable
tax -- consistent with occupancy N = BW x latency: CXL's ~2.76x higher
measured idle latency (401.8 ns vs 145.7 ns) means proportionally less
bandwidth fills the same occupancy.

## The convergent floor: adopted

Four numbers, all measured this campaign, n>=12 or cross-validated:

| Mechanism | Tax | Source |
|---|---:|---|
| CAT, 8/8 way split | 7.23x [6.89,7.52] | E1 A2 |
| Flush-behind, best D (256 KiB) | 5.94x [5.82,5.99] | Phase 2.4 |
| Concurrency cap (2T, 98% of 3T's bandwidth) | 6.40x [6.13,6.73] | A6 / Phase 2.2 |
| WC (path-exempt by memory type) | 0.99x [0.98,1.00] | E1 A0-A3 gate |

Three orthogonal, deployable-class mechanisms (capacity partitioning,
residency bounding, concurrency reduction) converge on a ~6-7x floor; only
the mechanism that is exempt from the coherent path *by memory type*
(WC) gets below it. Adopted as the paper's AMD figure. Two-level thesis:
at the LLC, write-back bundles prefetching with *allocation* (Intel; H2
fixes it, E2b is the silicon evidence); at the fabric, cacheable-coherent
bundles prefetching with *transaction-pool enrollment* (AMD; no deployed or
emulated residency/capacity/concurrency knob reaches it -- only
type-licensed exemption does).

## The Phase 2.4 hole: closed using data already in hand

Compared flush-behind@256KiB against the A6 2-thread point directly:

| | bw self / mbm (GB/s) | victim occupancy | tax |
|---|---:|---:|---:|
| Flush-behind @ 256 KiB | 17.04 / 33.05 | 2.93 MB | 5.94x |
| A6, 2 threads | 20.24 / 20.22 | 0.54 MB | 6.40x |

**Occupancy differs by ~5.4x (flush retains far more resident data than 2T
naturally would), yet tax is comparable (flush is if anything slightly
lower).** If flush-behind@256KiB were just disguised concurrency throttling
to a 2T-like profile, its own occupancy should resemble 2T's low value; it
doesn't. This is a clean, decisive answer to the panel's stated concern
using data already collected -- **not** a re-run. Confirms the MBM
mismatch flagged in the original writeup is real (33.05 vs self-report's
17.04, ~94% high) and MBM cannot serve as this arm's bandwidth verifier;
self-report (closer to but still below the true rate, per the eviction-
traffic hypothesis) is the only usable number here, another reason
per-arm bandwidth *and* occupancy both matter, exactly as the panel argued.

## The D-structure / L2-size architectural point: panel was right, repo's own comment was stale

Checked Bergamo's actual per-core L2 size directly on the hardware rather
than trusting the repo's internal documentation: `lscpu` and
`/sys/.../cache/index2/size` both report **1024K (1 MiB)** per core. The
`common.h` comment claiming "Bergamo 512KB L2" is itself a stale
placeholder (its own text says "Default only... FILL THIS IN after Step 0
characterization" -- never updated). The panel's D-vs-L2 framing is
therefore correct as stated: D=256 KiB sits well inside the 1 MiB L2 (lines
die before ever threatening L3 entry -- the true H2 analog), while D=2 MiB
is 2x the L2 size (allocate-then-remove plus churn) -- which matches this
campaign's own data exactly: D=2MiB is the noisiest, worst point in the
sweep (8.13x [7.40,9.16], the widest CI of any D value), consistent with
straddling the L2/L3 boundary rather than staying cleanly within or beyond
it.

## The paper's own §2 local-vs-CXL comparison: verified as cited, and now a flagged risk

Checked directly against the paper text (not the panel's paraphrase):
`Sec2_DirectoryTax.tex:70-80` states exactly "a same-L3 WB stream from local
DDR at 22.6 GB/s imposes a 4.1x slowdown... a same-L3 WB stream from CXL at
23.1 GB/s imposes a 9.6x slowdown" -- correctly cited. But given this
campaign's own finding (AMD local-DRAM single-thread bandwidth is already
~43 GB/s and stays flat through 7 threads), **the paper's own 22.6 GB/s
local point cannot have been reached by a natural, unthrottled
configuration** -- some thread-count choice or rate-limiting must have been
used to bring local down to ~22.6 GB/s, and this campaign has now
demonstrated that at least one such mechanism (the `-R` pacing throttle)
carries a real, identified confound. **This is a newly-identified risk to
the paper's own headline §2 comparison, not just to this campaign's
reproduction of a similar one.** Not resolved here -- the original
experiment's exact configuration is not recoverable (consistent with this
campaign's earlier finding that the AMD headline numbers' raw dataset no
longer exists) -- but worth flagging to whoever owns that paragraph before
submission.

## New gap found and tested: AMD hugepage reservation was never set up, but doesn't matter

While evaluating the panel's THP/page-boundary-serialization hypothesis for
the single-core bandwidth anomaly (arithmetic: ~536 ns/4KiB-page-boundary
predicts ~7.6 GB/s CXL, ~14 GB/s local, close to measured 8.9/14.1 on
Intel), checked the actual AMD harness code and host state:

- `alloc_wb_cxl` (CXL aggressor path) attempts `MAP_HUGETLB` with a
  **silent fallback** to plain 4 KiB pages if unavailable.
- `alloc_wb_node` (local-DRAM aggressor path) **never attempts hugetlbfs at
  all, by explicit design** (`common.h` comment: "Local DDR experiments do
  not require hugetlbfs backing... attempting MAP_HUGETLB on nodes without
  reserved huge pages can SIGBUS on first touch").
- `victim.c` uses plain `mmap()`, no hugetlbfs request, ever.
- THP is set to `madvise` on `broker`; nothing in this harness calls
  `madvise(MADV_HUGEPAGE)`, so THP never silently helps either.
- **`broker` currently has zero hugepages reserved on any node**, and a
  historical `hugepage_network.sh` script reserves them on node1 -- the
  stale, unused aggressor-node default this campaign already flagged weeks
  ago, not node2 (CXL), which is what `alloc_wb_cxl` actually needs. As far
  as this session can determine, **the CXL aggressor path has been running
  on plain 4 KiB pages for this entire campaign**, silently.

**Tested directly rather than left as a guess**: reserved 500x 2MiB
hugepages on node2 (confirmed node2 supports reservation), then re-ran the
exact single-thread and 7-thread CXL WB spot checks. Single-thread: 12.65
GB/s with hugepages vs the historical ~12.42-12.44 GB/s without --
**~1.7% difference**. Seven-thread: 24.27 GB/s vs historical ~24.1-24.4 --
**no material difference**. Reservation released back to 0 after the check.

**Verdict: the specific page-boundary-serialization hypothesis does not
hold**, on two independent lines of evidence: (1) local DRAM, which *never*
uses hugepages by design, already reaches ~43 GB/s on plain 4 KiB pages --
if 4 KiB boundaries capped bandwidth at ~14 GB/s as the arithmetic
predicted, local couldn't be 3x over that ceiling using the exact same
page size; (2) giving the CXL path its intended hugepage backing changes
its bandwidth by ~2%, not the large jump the hypothesis predicted. The
missing-hugepage state is a real, previously-undiscovered hygiene gap
(worth fixing properly for future AMD work, and for correctness relative to
what the code was clearly written to assume), but it does not explain any
number this campaign has collected, and does not need any AMD result
re-run. The underlying single-core absolute-bandwidth anomaly (on both
platforms) remains genuinely unexplained.

## E2b's bimodal quiescent baseline: one more candidate ruled out

Quick test on the C6 idle state specifically (290 us transition latency,
the deepest state exposed on this EMR host): disabled it on cpu0
(`/sys/devices/system/cpu/cpu0/cpuidle/state3/disable`), then ran four
independent single-trial quiescent invocations. Result: still bimodal
(88.5, 82.1, 82.0, 82.2 cyc/load) -- C6 was not the (sole) cause. State
restored (re-enabled) after the test. The PM-QoS (`/dev/cpu_dma_latency`)
and keep-awake-ticker tests the panel proposed were not attempted this pass
(more involved to implement correctly -- a held-open background process
each) -- tracked as the next things to try, not ruled out.

## Phase 2.5 (gem5): scope lift acknowledged

The panel's message explicitly lifts the scope boundary the original
mission set. Treating that as the user's own direct override, not
executing on inference. Not started this pass given the size of the
remaining work (the validation contract itself -- six silicon signature
points the model must reproduce, including the requirement that an H2 arm
on the AMD-analog *must fail* to recover -- is a substantial modeling task
in its own right) -- tracked as the next major work item, with the
six-point contract as its acceptance criteria.
