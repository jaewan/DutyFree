# Demoting gem5 from magnitude to mechanism — what changed in the paper, and why

Written 2026-08-15. The lead's decision, this session: **demote the simulator.**
gem5 is used for mechanism existence ("H2 is implementable and behaves as
specified"), never for magnitude; quantitative weight sits on silicon. This
records the one paper edit that decision required today, its verification, and
what was deliberately left alone.

## Why the decision was taken

Accumulated, all verified from instantiated state rather than from documents:

- Gate 1: the model reads **39% low** against the hardware point it was said to
  be calibrated to; the calibration claim was already withdrawn (pass 5).
- Placement was a **silent no-op** until 2026-08-15 (`mbind` is `ignoreFunc`
  under gem5 SE). Pre-fix single-process runs recorded **zero** traffic on the
  203 ns controller — see `GATE1_FUSED_NULL_CORRECTION_2026-08-15.md`.
- `check_pages_on_node` is a `return true` stub under `GEM5`, so the benchmark
  cannot detect its own placement failures.
- `--stream-count` is **inert** under gem5 (the multi-stream loop is inside
  `#ifdef __AVX2__`; the gem5 target compiles without `-march=native`).
- No gem5 number has a variance estimate, and runs are **not bit-reproducible**
  at fixed seed once randomisation is on (§6.1 of the correction).
- H2's victim-path fill suppression degrades 77.3% -> 57.2% with MSHR depth,
  cause unresolved after three refuted hypotheses.

Individually ordinary. Collectively they mean an artifact evaluator reproduces
a day's worth of defects. The paper's credibility is its principal asset, so
the simulator stops carrying quantitative claims.

## The edit — `Sec5_Evaluation.tex`, the fused-null sentence

**Removed** (cited as support for "not where H2 pays off"):

> and our model, which reproduces the capacity tax, shows essentially *no*
> same-thread tax (80.1 loaded vs. 80.0 quiescent cycles/access) even though H2
> provably engages (37% fewer LLC fills)

Two independent defects. **(1) Mislabelled arm:** those runs placed the fact
stream on DRAM, not CXL — `mem_ctrls1` (203 ns) recorded zero traffic — so the
numbers are not from the configuration the sentence implies. **(2) Unsupported
inference:** the fused kernel is MLP-limited by its own dependent probe chain
(~59 cycles per 16 B tuple, ~1.3 lines in flight), reaching 0.52 GB/s against
the *same model's* measured 4.17 GB/s (WB) / 4.78 GB/s (H2) pure-stream
ceiling. An LLC-admission fix has nothing to convert there, so the null cannot
distinguish "the tax lives outside the shared-LLC channel" from "this kernel
was never in the regime where admission matters."

**Replaced with** text that (a) declines to use the simulator to arbitrate the
case and says why, (b) reports what gem5 *can* legitimately show — that H2
engages as specified, 59.6% fewer LLC fills and 16.9% fewer victim misses to
memory at a shared-cache-dependent victim — and (c) names the hardware
decomposition as the authority. The conclusion the paragraph argues ("the fused
kernel is necessity, not the H2 payoff") is **unchanged**; only its support is.
That conclusion is now better grounded than before.

The margin note was rewritten to mark the old numbers WITHDRAWN with the reason,
carry the new arms' full provenance, and forbid two reversions: reinstating
"H2 recovers the fused tax," and citing the fused null as evidence about *where*
the tax lives.

### Provenance of the replacement numbers

gem5 `3d0d1ca2` (clean), DutyFree `88d8edf`, bench sha256 `917413d5...`,
`--reps 3`, fact 16 MiB on pool 1 (CXL 203 ns; `bindpool 4096/4096` and
`setstreaming 4096/4096` verified in the run log), hot table on pool 0 (DRAM
98 ns). H2-protectable window is (private L2 2 MiB, shared L3 5 MiB]; the 4 MiB
in-window arm gives HNF fills 1,340,360 -> 542,011 (-59.6%), victim DRAM reads
12.09 -> 10.05 MB (-16.9%), cyc/acc 72.428 -> 71.993 (-0.6%). Bandwidth ceiling
from the same binary and config, `--mode stream-smoke`.

No H2/H3 attribution is made; the §3 embargo is untouched.

## Verification

`latexmk -pdf -g` (exit 12 is the documented quirk; judged by `main.log`):
**0 lines matching `^!`, 0 `undefined`**, PDF regenerated.

Page discipline: the first edit pushed References from p12 to p13, i.e. the body
past the 11-page limit. Tightened the addition ~38 words; References returned to
**p12** (body ends p11), matching the established baseline. Total is 18 pages;
the extra page is past the body boundary, where space is free.

## What was deliberately not changed

- **`tab:gem5` itself.** Demotion is about the weight the prose puts on the
  model. Re-framing or re-running the table is a larger edit and the lead's
  call; pass 5's `‡` marking and lower-bound framing already point the right
  way.
- **`Sec3_Mitigation.tex`'s flush-behind paragraph.** Already landed by a prior
  session, complete with recovery 76.3% [76.1,76.4], streamer cost 31.3%
  (24.7->17.0 GB/s), full inline arm identity and a provenance margin note.
  `PAPER_SESSION_PROMPT.md` §7 #30 says flush-behind "is currently buried" —
  **that is out of date**; verify against `Sec3_Mitigation.tex:165` before
  planning work against it. What remains of #30 is the Streaming-proxy arm and
  the §4.4 end-to-end suite, which is a measurement campaign, not writing.
- **The δ embargo's edges**, the ABI/motivation mismatch, and #28's canonical
  config — all standing lead decisions (§9).
