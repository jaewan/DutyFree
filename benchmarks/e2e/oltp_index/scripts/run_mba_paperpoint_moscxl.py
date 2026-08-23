#!/usr/bin/env python3
"""Does MBA recover the paper's 6.92x AMD residual at the paper's own point?

Sec5's portability paragraph reports, on this part (EPYC 9754): a 4 MiB
L3-resident pointer-chase victim sharing its CCX with a seven-thread CXL
aggressor runs 19.85x unpartitioned, and an eight/eight way split recovers only
69%, leaving 6.92x "at full aggressor bandwidth". Contribution (2) on page 1
cites that residual as the evidence that capacity control is insufficient.

GPROBE_OUTCOME.md 5.6 measured the same class of arm on the same part and found
MBA192 takes CAT12 from 13.05x to 1.07x for 4% of streamer bandwidth. If that
carries to the paper's point, the page-1 claim is refuted by a shipping knob,
and we should be the ones to say so.

But 5.6 is NOT the paper's point. Three things differ, and this script closes
all three at once rather than one at a time, because the only question that
matters is whether the published cell falls:

    victim working set   8 MiB   ->  4 MiB      (paper: "4 MiB", fits its 8 MiB of ways)
    way split            12/4    ->  8/8        (paper: "eight exclusive ... a disjoint eight")
    streamer source      node 0  ->  node 2     (paper: "streaming from CXL"; 5.6 was local DDR)

The local-DRAM twins at the bottom are kept so the result connects to 5.6
instead of floating free: on this host the two source nodes are bandwidth-
matched (~24.7 GB/s either way), so a divergence between them is about the
source, not about bytes.

WHAT EACH OUTCOME MEANS -- pre-registered, because the arm that flatters this
project and the arm that kills it are the same arm read two ways.

  CAT8_cxl ~ 6.92x and CAT8_cxl_MBA192 ~ 1.1x at >= 95% bandwidth
      The published residual is recovered by a deployed control at its own
      operating point. Contribution (2)'s AMD half does not survive as written.
  CAT8_cxl ~ 6.92x and CAT8_cxl_MBA192 still high
      The paper's point is genuinely unlike 5.6's and the residual stands.
      Then, and only then, is it worth splitting the three deltas apart.
  MBA192_cxl alone recovers the victim
      CAT contributes nothing here and the story is MBA alone -- a worse
      outcome for the claim than the first, not a better one.
  CAT8_cxl does not land near 6.92x
      A provenance problem, reported as one. Section 6.6 forbids hunting for
      the configuration that reproduces a published number; if it does not
      reproduce here, that is the finding.

The two non-binding caps (256, 224) are the arm's own control. MBA at a setting
above what seven cores can pull must cost nothing; if the victim moves under
them, then arming MBA is doing something other than capping bandwidth and every
knee arm below is uninterpretable. 5.6 needed this control and did not have it
on the first pass.

MBA on a CXL-sourced stream has never been exercised on this host -- the
calibration ladder and every arm in 5.6 were local DDR. If the delivered
bandwidth under MBA192_cxl does not fall by roughly the 4% it costs locally,
then MBA does not bind on this path, and that is the result, not a bug.

n=12 to match the paper's n. Arms and plumbing are run_mba_moscxl's, overridden
only in the list, so placement, victim-first arrival, occupancy sampling, the
foreign-load check and the D1 l2_counters gate are literally the same code.
"""
import os
import run_mba_moscxl as M

CAT_V, CAT_S = "00ff", "ff00"      # eight exclusive ways each, disjoint

M.ARMS = [
    ("quiescent",         None, M.P.FULL, M.P.FULL, M.MB_MAX),
    ("CAT8_nostream",     None, CAT_V,    CAT_S,    M.MB_MAX),  # cost of the split alone
    ("WB_cxl",            2,    M.P.FULL, M.P.FULL, M.MB_MAX),  # paper: 19.85x
    ("CAT8_cxl",          2,    CAT_V,    CAT_S,    M.MB_MAX),  # paper: 6.92x
    ("CAT8_cxl_MBA256",   2,    CAT_V,    CAT_S,    256),       # non-binding control
    ("CAT8_cxl_MBA224",   2,    CAT_V,    CAT_S,    224),       # non-binding control
    ("CAT8_cxl_MBA192",   2,    CAT_V,    CAT_S,    192),       # the knee from 5.6
    ("CAT8_cxl_MBA176",   2,    CAT_V,    CAT_S,    176),
    ("MBA192_cxl",        2,    M.P.FULL, M.P.FULL, 192),       # MBA with no partition
    ("WB_local",          0,    M.P.FULL, M.P.FULL, M.MB_MAX),  # 5.6 continuity
    ("CAT8_local",        0,    CAT_V,    CAT_S,    M.MB_MAX),
    ("CAT8_local_MBA192", 0,    CAT_V,    CAT_S,    192),
]
M.WS_LIST = [4096]                 # the paper's 4 MiB victim, nothing else
os.environ.setdefault("OUT", "probe_moscxl_mba_paperpoint.jsonl")

if __name__ == "__main__":
    try:
        M.main()
    finally:
        M.P.cat_teardown()
