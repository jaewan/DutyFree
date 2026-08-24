# Item 14 resolved without running it: RocksDB does not supply the victim, and supplies something better

Item 14 was "re-earn the RocksDB victim under the current provenance standard".
**It should not be run**, and the reason is already in the repository. Reading
first — the rule that caught five of my own errors today — prevented a campaign
this time instead of correcting one.

## Why not to run it

`benchmarks/e2e/rocksdb/ROCKSDB_LSM_PANEL_FINDINGS.md` (2026-08-21, exploratory
and labelled not-pre-registered) already searched for the victim and found a
mechanism for its absence:

> "Of the four candidate reused structures — memtable skiplist, block cache,
> index blocks, filter pool — three are hierarchical or sequentially walked and
> self-protect against capacity denial. The one that is flat, the filter pool, is
> reached through a cache-resident binary search and a hash-table lookup that
> together are twelve times the cost of the probe they guard: the probe is 2.46%
> of cycles."
>
> "Measured best across six configurations … **1.41×**, against a bare pointer
> chase's 3.9–4.1× on the same core in the same minutes. Six configurations, none
> above 1.42×… **I would not fund further RocksDB victim search**; ten more
> engineer-hours buys a number between 1.1× and 1.5×."

A pre-registered re-run would spend real host time to confirm a documented null
whose cause is understood. That is not what the panel's recommendation was for —
they wanted a *named-application victim*, and this evidence says RocksDB is not
one, for a structural reason rather than a measurement accident.

Two further robust findings there bear on the deleted claim:

1. **The published RocksDB numbers were taken on an assertions-enabled binary.**
   `/usr/bin/db_bench` is Ubuntu `rocksdb-tools` 9.11.2-1 and prints
   *"Assertions are enabled; benchmarks unnecessarily slow"*. Against a release
   build of the identical tag, `readrandom` goes 2.964 → **1.999 µs/op**: **1.48×
   of the per-lookup software work was assertion overhead.** So the "software
   cost dilutes the memory tax" diagnosis rested on a figure ~32%
   instrumentation. Its direction survives; the figure must not be requoted, and
   any future RocksDB arm must state its `DEBUG_LEVEL`. This also means the
   *Intel null* that the paper reported alongside the 2.33× was measured on the
   slow binary — a further reason the deletion was right.
2. **The host was not the problem.** A bare dependent-load chase reaches **4.07×**
   on mos181, so `E2E_STATUS.md`'s "no Intel configuration reaches 2×" is a
   statement about the victims tried, not the platform.

## What RocksDB does supply, and it is better than a victim

**Production code already enforces H2, one level up, and cannot express it one
level down.** Verified line by line against the `v9.11.2` tree:

| location | code |
|---|---|
| `db/compaction/compaction_job.cc:1179` | `read_options.fill_cache = false;` |
| `db/compaction/compaction_iterator.cc:1415` | `read_options.fill_cache = false;` |
| `table/block_based/block_based_table_reader.cc:1784` | `bool no_insert = no_io \|\| !ro.fill_cache;` |

The block is **read, used, and never inserted** — fetch at full aggressiveness,
decline the admission. That is H2's semantics, shipped by default for over a
decade, because letting a compaction's one-shot blocks evict the foreground's
index and filter blocks was unacceptable in production.

And the block RocksDB *refuses* to insert into its own cache is still allocated
into L1, L2 and the LLC by the loads that read it. **The missing admission cell
is a policy that production software implements where it can express it, and
cannot express one level below.**

This is strictly stronger than the microbenchmark it replaces: the demand is not
inferred, the software workaround is not speculative, and neither can be
falsified by a re-measurement. Added to `Sec3_Mitigation` as its own heading
immediately before the hash-join kernel, which is where the scope objection is
then measured.

## Status

Item 14 is **closed as resolved-without-running**, not blocked. Broker is
irrelevant to it. What replaces it in the paper is a source-level exhibit; what
the paper still lacks is a named-application *victim*, and this evidence argues
that LSM read paths are the wrong place to look for one — the panel's own
candidate, ruled out with a mechanism.
