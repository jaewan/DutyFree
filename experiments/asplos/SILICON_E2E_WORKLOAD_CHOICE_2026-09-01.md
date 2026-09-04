# Workload choice: silicon application e2e

Date: 2026-09-01, before measurement.  Required by
`AGENT_BRIEF_SILICON_E2E_2026-09-01.md` §4 and §10.

The invariant: every workload contains, in one process, an immutable stream
and a co-resident working set that benefits from cache.  Against a pure stream
CAT and STREAMING are already known to be equivalent (0.55% model / 0.7%
silicon).

## Selected for this campaign: hash join

`cxl_join_bench --mode single`.  Fact table streamed once; hash table resident.
Native instance of the fused pattern the wedge already measured in gem5, now
run to completion so the tenant reports `join_mtuples_per_s`.  Flush-behind
and `prefetchnta` already exist in the kernel.  Lowest apparatus risk.

One workload measured properly, not three measured loosely.

## Ranked and not run yet

| family | invariant | decision |
|---|---|---|
| LSM compaction (RocksDB) | SSTables immutable and read-once; block cache / index / filter co-resident | **Second family**, not this campaign.  Strongest natural fit, and RocksDB already declines to insert compaction blocks into its *own* cache (`fill_cache=false`).  That is the software-level H2 the paper wants; the missing cell is the same policy one level down, against a neighbour.  Setup cost (engine, `DEBUG_LEVEL`, dataset) is a campaign of its own.  `ITEM14` closed RocksDB as a *victim*; this would use it as a *tenant*. |
| Columnar scan / DuckDB | fact streamed, hash table resident | Same pattern as the in-repo join, less control over nta/flush-behind, and earlier DuckDB numbers on this host mixed node-2 (CXL-less) placement.  Rejected as a duplicate with worse levers. |
| Vector search, IVF-Flat | posting lists streamed; centroids and top-k resident | Good fit, no in-repo engine.  Would spend the week on ANN correctness. |
| LLM decode + KV cache | KV immutable within a step; weights co-resident | Topical, but attention is usually bandwidth-bound.  The brief requires verifying the LLC actually matters at the chosen batch/context before committing.  That verification is itself a campaign. |
| RecSys / DLRM | sparse embedding is random, not streaming | Rejected.  Only viable by streaming the training feed and keeping hot rows resident, which is a constructed fused pattern we already have in the join. |

## What this document does not authorise

Measuring STREAMING.  Combining a silicon CAT number and a modelled STREAMING
number in one figure without labelling the platform of each point.
