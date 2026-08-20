# Pre-registration: HNSW CAT capacity-sensitivity gate

Dated 2026-08-21, written before any HNSW measurement exists. This is the same
gate, with the same decision rule, that GAPBS PageRank has just been run
through; only the victim changes.

## Why HNSW is being gated at all

PageRank passed the CAT capacity-sensitivity gate on `moscxl` (AMD EPYC 9754,
16 MiB L3 per CCX) at g21, and failed on both Intel hosts at every scale
measured -- `mos181` (320 MB LLC) at 1.10--1.31x and `mos182` (60 MB LLC) at
1.34--1.43x, with CoV at or below 0.25%. Under
`GAPBS_DUCKDB_CORUN_PREREGISTRATION.md`'s falsifiable outcome 1 that is a
failure of the cross-vendor bar for PageRank.

`benchmarks/e2e/E2E_SESSION_PROMPT.md` §4.2 already names the alternative and
the reason: "IVF was structurally the wrong ANN algorithm: it scans posting
lists. HNSW traverses a proximity graph with dependent hops and reuses its
upper layers heavily." `hnswlib` is header-only, so the gate is cheap relative
to the campaign it would inform.

Note what this does **not** rescue. The paper's cross-vendor claim does not
depend on this campaign: §2 rests it on CAT/MBA on Intel plus a way sweep and
a non-allocating aggressor on AMD. What is at stake is whether the
*real-application* arm is single-vendor.

## Victim

`hnswlib` at a pinned commit. One index, built once and byte-identical across
hosts, is used everywhere: 1,000,000 random float32 vectors of dimension 128
(`M=16`, `efConstruction=100`), giving roughly 640 MB of vectors plus links,
comparable to the Kronecker g22 graph the sizing gate selected. Vectors and
queries are drawn from a fixed seed, and the index is built once and copied,
not rebuilt per host, so no host can differ by construction order.

Each measured trial is a fixed batch of 10,000 `searchKnn` queries at `k=10`,
`ef=64`, single-threaded and pinned, on the same CPU each host used for the
PageRank gate. Trials are reported as `Trial Time: <seconds>` so the existing
runner consumes them unchanged. Index load happens once per invocation, before
any trial, and is not timed.

## Method and decision rule

Unchanged from `../gapbs/GAPBS_CAT_SENSITIVITY_PREREGISTRATION.md`: per host, a
CPU-based resctrl CAT group at the full mask and at the minimum legal
contiguous mask (floored at one way -- see
`../gapbs/GAPBS_CAT_SENSITIVITY_RUN_DECISIONS.md` §1 for why AMD's reported
floor of 0 cannot be taken literally); L3 domain, installed mask and effective
capacity all read back from sysfs; **pass requires a minimum-way median at
least 2x the same-configuration full-mask median, with CoV at or below 5% in
both.**

Because PageRank's trials were found to alternate by about 9% on `moscxl`
(`GAPBS_CAT_SENSITIVITY_RUN_DECISIONS.md` §9), the trial count here is **7,
first discarded, six measured** -- an even measured count, so a two-phase
signal cannot bias the median by sampling parity. Three independent
invocations per host and mask.

The index size is a single operating point rather than a sweep: unlike a
Kronecker scale there is no cheap ladder, and the point of this gate is a
go/no-go on one configuration chosen to match the graph the sizing gate
selected.

## Falsifiable outcomes, declared now

1. **HNSW passes on at least one Intel host and on AMD.** The campaign's victim
   becomes HNSW and the real-application arm is cross-vendor.
2. **HNSW passes on AMD only.** Then two unrelated victims -- one graph
   analytics, one vector search -- are capacity-sensitive on a 16 MiB-per-CCX
   LLC and not on 320 MB or 60 MB Intel LLCs. That is a stronger and more
   general statement than the PageRank result alone, and it makes an AMD-only
   real-application arm a measured conclusion rather than a fallback.
3. **HNSW fails everywhere, including AMD.** PageRank at g21 on `moscxl`
   remains the only viable configuration, and the campaign proceeds there.
4. **HNSW passes on Intel but not AMD.** Reported as such; it would invert the
   PageRank result and require its own explanation before either is used.

No tax, recovery, or frontier claim is made by this gate. No streamer and no
aggressor is launched. CoV above 5% on any arm makes that arm unreportable
until a cause is declared, exactly as in the GAPBS gate.
