# Gate 1: config reconciliation

Dated 2026-08-09, in progress. Deliverable per spec: one table, rows =
the five published tables, columns = producing commit / tab:gem5cfg claim
/ instantiated actual / verdict (match / text-fix / re-run).

## Tooling: `gate1_manifest.py`

Post-instantiation walk of `config.json` (never `config.ini`'s text form
or a script's stated intent) → JSON: LLC size/assoc, replacement policy
+ its actual parameters (not just class name — see the BRRIPRP/RRIPRP
lesson from Gate 0), prefetcher class+degree per level, MSHRs, HNF
controller `sf_finite` state, core count, memory-controller latencies,
cache line size — plus commit SHA, dirty-tree flag, command line, and
relevant env vars. Two type-name bugs found and fixed by checking
`config.json` directly rather than guessing gem5's internal class names
(`O3CPU` → actually `BaseO3CPU`; `CHI_HNFController` → actually
`CHI_Cache_Controller`) — the exact "verify, don't guess" discipline this
whole gate exists to enforce, applied to my own tooling before trusting
its output.

## First result (interim — one config, not yet tied to a specific
## published table's producing commit)

Ran `gate1_manifest.py` against `b4run.sh`'s `alone` config on the just-
unified `streaming` HEAD (`23f27375e9`). This is the same `COMMON` config
string shared by the `alone`/`wb`/`st` tags (only the aggressor/workload
differs), so it's informative for all three, though not yet validated
against whichever *older* commit actually produced each published number
— that's what commit archaeology (below) is for.

**LLC sizing**: exactly one `system.ruby.hnf.cntrl.cache` node, `size:
5242880` (= 5 MiB exactly), not duplicated per core. **Confirms the LLC
is genuinely shared at 5 MiB for a 2-core run on this config** — matching
the paper's `tab:gem5cfg` claim, not Eunji's "5 MiB per core / 10 MiB
total" description.

**Prefetchers**: `system.cpu0.l1d.prefetcher` is a `MultiPrefetcher`
containing `prefetchers0 = StridePrefetcher(degree=4)` and
`prefetchers1 = DCPTPrefetcher`. **This matches Eunji's "stride(4)+DCPT"
description exactly — not the paper's stated "L1/L2 stream" prefetcher.**

**This is not "paper right, Eunji wrong" or the reverse — it's a genuine
split.** LLC sizing tracks the paper's claim; prefetcher configuration
tracks Eunji's. Whatever produced the original published tables, it did
not match `tab:gem5cfg`'s prefetcher description on at least this
dimension, at least on this run's config/commit. This sharpens exactly
the question in the Eunji draft email (`EUNJI_QUESTION_DRAFT.md`) and
raises its stakes — her answer now needs to explain not just "which
config" but "why does the LLC-sizing claim and the prefetcher claim not
travel together."

**HNF `sf_finite`**: `False` for `system.ruby.hnf.cntrl`, matching the
`HNF_SF_FINITE=0` default — confirms this specific run used infinite SF,
as expected for the `alone`/`wb` baseline tags (not `h3sf`-specific).

**Memory latencies**: two `SimpleMemory` controllers, 98000 ps (98 ns,
local DRAM) and 203000 ps (203 ns, CXL) — both correctly instantiated
per the `--dram-latency`/`--cxl-latency` flags, confirming the
dual-latency-backend model is live at the memory-controller level, not
just requested on the command line.

## Streaming-path smoke-test (Gate 0 follow-up, in progress)

Per the panel's flag that Gate 0's smoke test only covered the
default/WB path, not the enforced `setstreaming` route behind the co-run
pair: running `b4run.sh <name> st 0 0` at both the pre-merge SHA
(`00fca787bd`, binary backed up at `/tmp/gem5_baseline_streaming.opt`)
and post-merge (`23f27375e9`) to diff `stats.txt` on this path
specifically. Result pending.

## Still to do

1. **Commit archaeology**: bind each of the five published tables
   (tab:h1bw, tab:gem5, tab:sens, tab:h3sf, co-run pair) to its actual
   producing commit, via run logs / scripts / shell history / margin
   notes (the h3sf margin note's `0102eee441` reference is the known
   pattern; need the equivalent for the other four). Any table whose
   producing commit can't be identified goes on the re-run list
   automatically.
2. **Re-instantiate each config at its producing commit**, run
   `gate1_manifest.py` against each, and fill in the actual
   reconciliation table (columns: producing commit / tab:gem5cfg claim /
   instantiated actual / verdict).
3. **Eunji's answer** on which checkout/commit her description came
   from — sent, pending reply (`EUNJI_QUESTION_DRAFT.md`).
4. Resolve the lineage question once (2) and (3) are in: one canonical
   config becomes the base for Build B and the head-to-head.

## Reconciliation table (skeleton, to be filled in)

| Table | Producing commit | tab:gem5cfg claim | Instantiated actual | Verdict |
|---|---|---|---|---|
| tab:h1bw | TBD | TBD | TBD | TBD |
| tab:gem5 (co-run pair) | TBD | 5 MiB shared LLC, L1/L2 stream PF | LLC: 5 MiB shared (confirmed, `alone` config); PF: stride(4)+DCPT (contradicts claim) — **pending confirmation this is the same commit that produced the published number** | pending |
| tab:sens | TBD | TBD | TBD | TBD |
| tab:h3sf | `0102eee441` (per existing margin note) | TBD | TBD | TBD |
| 2-core co-run pair | TBD | TBD | TBD | TBD |
