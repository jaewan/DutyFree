# LSM / KV-engine panel findings

Written 2026-08-21 for the ASPLOS'27 panel. Exploratory, **not pre-registered**
(`REPO_DISCIPLINE.md` §1), and taken on a host that was **not quiescent** —
four other panel investigations were running `aggressor`, `duckdb`,
`latency_chase` and their own `db_bench` on `mos181` throughout. Every number
below carries that disclosure. The three findings that do not depend on
absolute timing are marked **[robust]**; the rest are indicative and name the
experiment that would settle them.

---

## 1 [robust] The published RocksDB null was measured on an assertions-enabled binary

`/usr/bin/db_bench` on `mos181` is Ubuntu `rocksdb-tools` 9.11.2-1, and it
prints `WARNING: Assertions are enabled; benchmarks unnecessarily slow` on
every invocation. `exp40`/`exp41`/`exp40b` all record RocksDB 9.11.2, i.e. this
binary. No release build existed on any of the three hosts.

Against a release build of the **identical upstream tag** `v9.11.2`
(`DEBUG_LEVEL=0`), differing in nothing but `-DNDEBUG`, on the same core and
the same configuration:

| binary | `readrandom` | `fillrandom` |
|---|---:|---:|
| distro 9.11.2 (assertions on) | 2.964 us/op | 6.747 us/op |
| upstream v9.11.2, `DEBUG_LEVEL=0` | **1.999 us/op** | 4.369 us/op |

**1.48x of the software work per lookup was assertion overhead.** The E2E
prompt's §3.2 diagnosis — "RocksDB `readrandom` spends ~3 us/op ~= 7000 cycles
of software per lookup, so a few hundred cycles of extra miss latency dissolves
into it" — is therefore built on a number that is ~32% instrumentation. The
diagnosis' *direction* survives (2.0 us/op is still a lot of software), but the
specific figure should not be quoted again, and any future RocksDB arm must
state its `DEBUG_LEVEL`. `InlineSkipList::FindGreaterOrEqual` and
`MemTable::Get` both carry asserts in their hot loops, so the dilution falls
exactly on the path a memory tax would have to show up in.

Reproduction recipe is in `README.md`; the build needs `-include cstdint` under
gcc 15.

## 2 [robust] `mos181` is not the problem. A bare pointer chase reaches 4.07x on it.

`E2E_STATUS.md` concludes "no Intel configuration reaches 2x", from two victims
(PageRank, HNSW) at five scales. Applying the *same* gate to
`~/tmp_dutyfree_exp/bin/victim -P` — a bare dependent-load chase, no software
work, MLP 1 — across a working-set sweep on `mos181` cpu96
(`artifacts/ptr_cat_ceiling_mos181.jsonl`, 3 invocations, 5 s each):

| chase working set | full ipc | min ipc | sensitivity |
|---:|---:|---:|---:|
| 8 MiB | 0.0315 | 0.0168 | 1.875x |
| **32 MiB** | 0.0270 | 0.0069 | **3.913x** |
| **128 MiB** | 0.0244 | 0.0060 | **4.067x** |
| 256 MiB | 0.0090 | 0.0060 | 1.500x |
| 512 MiB | 0.0059 | 0.0058 | 1.017x |

Two things follow, and the second is the more useful.

**(a) The host has headroom.** Even after discounting for contention — the
8 MiB row is a clean internal control, because there the working set fits
inside the 16 MiB minimum mask so *no capacity is denied* and its 1.875x is
pure interference through the shared minimum way — the capacity-only component
at 128 MiB is roughly 4.067 / 1.875 ~= **2.2x**. That is above the bar. The
Intel null is a victim-selection result, not a host property, and the campaign's
summary sentence overstates what its two victims established.

**(b) There is a sensitivity window, and both prior victims missed it.**
Sensitivity peaks between **32 and 128 MiB** and collapses on both sides: below
~16 MiB the minimum mask still holds the working set, and above ~200 MiB the
*full* mask stops holding it (note the full-arm occupancy: 133-140 MiB at
ws=128 MiB, but only 134-152 MiB at ws=256 MiB — the full arm has already
stopped fitting). PageRank at g21 has a ~268 MB CSR: past the top. HNSW's index
is 630 MB with a few hundred KB of hot upper layers: past the top *and* below
the bottom, which is exactly the split its own outcome file describes. Neither
was ever sized into the window.

**The cheapest useful experiment in this whole area is to re-run
`scripts/run_ptr_cat_ceiling.py` on a quiescent `mos181`.** It takes about five
minutes, it needs no new victim, and it decides whether the 2x bar on Intel is
reachable at all. If a bare chase clears 2x quiescent at 32-128 MiB, keep
searching for victims and size them into that window; if it does not, the bar
is what needs revisiting, not the victim list.

## 3 [robust] RocksDB already ships the paper's contract — for its own cache

`db/compaction/compaction_job.cc:1179` and
`db/compaction/compaction_iterator.cc:1415` both set
`read_options.fill_cache = false` unconditionally, and
`table/block_based/block_based_table_reader.cc:1784` turns that into
`bool no_insert = no_io || !ro.fill_cache;` — the block is **read, used, and
never inserted**. That is precisely *H2*: fetch at full aggressiveness, decline
the admission. RocksDB has enforced it for compaction reads of sealed SSTables,
in software, for over a decade, because the alternative — letting a compaction's
one-shot blocks evict the foreground's reusable index and filter blocks — was
unacceptable in production.

Nothing analogous exists one level down. The block RocksDB *refuses* to insert
into its own block cache is still allocated into L1, L2 and the LLC by the very
loads that read it. This is the paper's missing-admission-cell argument,
instantiated in shipped production code, with a file and a line number, and it
is a better §3 exhibit than any microbenchmark: the demand is not hypothetical
and the software workaround is not speculative — it is the default.

---

## 4 Configurations tried, and why the LSM read path resists capacity denial

All on `mos181` cpu96 (L3 domain 1, 320 MiB / 20 ways, 16 MiB per way),
release `db_bench` v9.11.2, single thread, uncompressed, DB on tmpfs, full mask
vs one way, 5 invocations each. Contaminated host; the `ptr` rows above were
taken on the same core in the same window, so the *comparison* between them is
much sounder than any absolute value.

| config | reused structure | size | full | min | ratio |
|---|---|---:|---:|---:|---:|
| `ptr` (reference) | flat chase | 32 MiB | — | — | **3.913x** |
| `ptr` (reference) | flat chase | 128 MiB | — | — | **4.067x** |
| `M_memtable_64M` | memtable skiplist arena | ~63 MB | 1.662 us | 2.214 us | 1.332x |
| `M_memtable_200M` | memtable skiplist arena | ~210 MB | 2.162 us | 3.056 us | 1.414x |
| `T_mmap_tmpfs_200M` | mmap'd SSTable bytes | ~180 MB | 1.938 us | 2.161 us | 1.115x |
| `S_seek_mmap_tmpfs_200M` | mmap'd index + data blocks | ~180 MB | 3.773 us | 4.015 us | 1.064x |
| `B_readmissing_31M` | bloom filter pool, partitioned | ~31 MB | 5.999 us | 6.556 us | 1.093x |
| `B_lean_hyperclock_31M` | same, unpartitioned + HyperClockCache | ~31 MB | 6.463 us | 7.084 us | 1.096x |

The memtable row is the important one. `M_memtable_64M` puts a ~63 MB
`InlineSkipList` arena squarely inside the window where a flat chase does
3.9x, on the same core, in the same minutes — and returns **1.33x**. The gap is
not software dilution alone. Three internals reasons, in decreasing order of
size:

1. **A skiplist is hierarchical, and hierarchy self-protects.** With RocksDB's
   defaults (`kMaxHeight=12`, `kBranching=4`) level *k* holds N/4^k nodes. For
   N = 450,000 that is 63 MB at level 0, 16 MB at level 1, 4 MB at level 2,
   1 MB at level 3, and below a page above that. Confining to 16 MiB turns
   *only levels 0 and 1* cold. Of the ~16 node visits in a search, about 3
   change from hit to miss. A flat chase changes *all* of them. **This is the
   same mechanism as HNSW's "reuse is real and in the wrong size range"** —
   and it generalises: any hierarchical index (skiplist, B-tree, HNSW, LSM
   level metadata) has a geometrically small hot apex that survives capacity
   denial. A capacity-sensitive victim needs a **flat** structure accessed
   uniformly at random.
2. **RocksDB software-prefetches the chase.**
   `memtable/inlineskiplist.h:548` (and `:589`) issue
   `PREFETCH(next->Next(level), 0, 1)` inside `FindGreaterOrEqual` — one hop of
   lookahead on the horizontal walk, which converts part of the serial chain
   into overlap. `--skip_list_lookahead` widens this further.
3. Per-`Get` software: `DBImpl::GetImpl` SuperVersion acquire/release,
   `LookupKey` construction, `PinnableSlice`, statistics. ~1 us even at
   `DEBUG_LEVEL=0`.

`T` and `S` are worse still (1.12x, 1.06x) and for an instructive reason: with
`--mmap_read=1` over a fully compacted DB, `Version::Get` finds the single
last-level file covering the key, so the chain is one filter probe, one index
binary search and one data block — and the data block is 4 KB of *sequential*
bytes, which the hardware prefetcher and the restart-array walk absorb at high
MLP. Shortening the LSM shortens the chain.

### Two traps a future RocksDB arm must avoid, both hit here

- **An unpartitioned filter block is megabytes, and mmap re-verifies its
  checksum on every probe.** A 70 MB SST at 10 bits/key with `value_size=8`
  holds ~2M keys, so its filter block is ~2.5 MB. With `--mmap_read=1` the
  parsed block is not retained, so every probe re-CRC32s it: measured
  **237 us/op**, which is 2.5 MB at ~11 GB/s. Real deployments at scale use
  `partition_index_and_filters=true` for exactly this reason; a gate that does
  not is measuring checksum bandwidth, not memory latency.
- **`taskset -c N db_bench` pins the background compaction threads to core N
  too**, and an LSM's read cost depends on its compaction state, which mutates
  across invocations. The first attempt showed the min arm *faster* than the
  full arm (5.94 vs 11.65 us/op) with 43% CoV, because the LSM was still
  settling. Freeze the shape: `fillrandom,waitforcompaction` to build, then
  `--disable_auto_compactions=1` to measure, and assert the per-level file
  count is identical across invocations.

## 5 Honest MLP per core on the LSM read path

| path | serial cold accesses per op | MLP | why |
|---|---:|---:|---|
| `Get` on memtable skiplist | ~16 visits, ~3 cold | ~1.3 | hierarchy; `inlineskiplist.h:548` prefetch |
| `Get`, filter-negative per level | 1 line per level, ~4-12 levels | **~1** | levels probed in order, no lookahead across levels |
| `Get`, filter-positive | + index binsearch + block-cache probe + 4 KB restart walk | 2-4 | the 4 KB walk is sequential and prefetched |
| `MultiGet` / `multireadrandom` | same misses | **up to 32** | `MultiGetContext::MAX_BATCH_SIZE = 32`; `FastLocalBloomImpl::PrepareHash` issues `PREFETCH` (`util/bloom_impl.h:220-221`) for *all* keys in the batch before probing any |
| iterator scan, `async_io` | — | high | `FilePrefetchBuffer`, `compaction_readahead_size` 2 MiB |

So the panel's question is answered concretely and the answer is favourable:
**single `Get` does avoid the batching MLP, and the code that creates it is
opt-in.** `MultiGet` is the wrong benchmark for this paper and `readrandom`
(single `Get`) is the right one. Add client threads and request-level
parallelism recovers the MLP at the socket level even if each thread is serial,
so any RocksDB victim arm must be **single-threaded**, and must say so.

## 6 The flat-structure hypothesis, tested and falsified

Section 4 argues the victim needs a **flat** structure uniformly probed, and in
an LSM exactly one qualifies: the **bloom filter pool**. Its size depends only
on key count (`N x bits/8`, +~10% for keys resident at more than one level),
each probe is one cache line by construction (`FastLocalBloomImpl` confines all
probes for a key to a single 512-bit block), and the probes per operation equal
the number of sorted runs. Sizes at 10 bits/key: 25M keys -> 31 MB; 100M ->
125 MB; 200M -> 250 MB; a 200 GB dataset at 116 B/KV is 1.67e9 keys -> **2.09 GB**,
far outside the window, which is why a *large* RocksDB is the wrong place to
look. Index blocks are ~28 B per data block: 147 MB for a 20 GB DB at 4 KB
blocks, 1.47 GB for 200 GB. Same conclusion.

`readmissing` is the right benchmark because a filter-negative answer returns
from `BlockBasedTable::Get` **before the index block is touched**, so nothing
sequential (no data block, no restart-array walk, no decompression) is left to
absorb the latency. I predicted 1.5-1.8x.

**Measured 1.093x.** The chain length was as designed — statistics confirm
`rocksdb.block.cache.filter.hit` = 1,134,732 over 200,000 reads, i.e. **5.7
filter-partition lookups per operation**, at a 1% miss rate. The chain is there.
It just is not where the cycles are.

`perf record` on that exact configuration (`artifacts/` has the gate records;
profile taken separately, 2K samples, 4.76e9 cycles):

| role | share of cycles | functions |
|---|---:|---|
| index / partition binary search | **30.5%** | `IndexBlockIter::SeekImpl` 16.4, `BlockIter<IndexValue>::CompareCurrentKey` 5.0, `BytewiseComparatorImpl::Compare` 3.3, `ParseNextKey` 2.1, `GetVarint64Ptr` 1.8, `GetFilterPartitionHandle` 2.0 |
| block cache machinery | **20.1%** | `LRUHandleTable::FindPointer` 6.9, `pthread_mutex_unlock` 4.3, `pthread_mutex_lock` 3.5, `CachableEntry` thunks 5.5 |
| key comparison | 6.6% | `__memcmp_evex_movbe` |
| LSM version / file picking | 5.0% | `Version::Get` 1.9, `TableCache::Get` 1.7, `FilePicker::GetNextFile` 1.4 |
| **the bloom probe itself** | **2.46%** | `FastLocalBloomBitsReader::MayMatch` |

**The single structure this paper needs on the critical path is 2.5% of the
cycles.** That is the answer to the panel's question, and it is a factor of
forty, not a factor of two. The dominant cost is a *cache-resident* binary
search: partitioned filters — what every large deployment uses, and the setting
that makes the filter pool addressable at all — insert a top-level index seek in
front of every probe. Those top-level index blocks total 2.3 MB
(`rocksdb.block.cache.index.bytes.insert` = 2,325,776), so they are LLC-resident
under *any* mask; capacity denial cannot touch them, while their software cost
sits in front of the one access it could.

Two escapes were tested and both failed. Unpartitioned filters with the lock-free
`auto_hyper_clock_cache`, which removes both the top-level seek and the
`LRUCacheShard::Lookup` shard mutex (`cache/lru_cache.cc:430`), gave **1.096x**
at a *slower* 6.46 us/op. `--mmap_read=1` over unpartitioned filters is worse
still and for a reason worth recording: a 70 MB SST at 10 bits/key with
`value_size=8` holds ~2M keys, so its filter block is ~2.5 MB, and with mmap the
parsed block is not retained, so every probe re-CRC32s it — **237 us/op**, which
is 2.5 MB at ~11 GB/s.

I record the failed prediction rather than the tuning path that might have
rescued it. The mechanism is not a tuning artefact: it is that an LSM point
lookup reaches its one flat structure through several cache-resident indirections
whose cost is comparable to a DRAM miss.

## 7 Verdict

My domain does not supply the victim, and I now have the profile that says why
rather than an argument. Of the four candidate reused structures — memtable
skiplist, block cache, index blocks, filter pool — three are hierarchical or
sequentially walked and self-protect against capacity denial. The one that is
flat, the filter pool, is reached through a cache-resident binary search and a
hash-table lookup that together are twelve times the cost of the probe they
guard: the probe is 2.46% of cycles.

Measured best across six configurations spanning the memtable, the mmap'd table,
the iterator seek path and the filter pool: **1.41x**, against a bare pointer
chase's 3.9-4.1x on the same core in the same minutes. Six configurations, none
above 1.42x, three of them inside the host's own sensitivity window. I would
not fund further RocksDB victim search; ten more engineer-hours buys a number
between 1.1x and 1.5x.

It does supply the **streamer**, and the best one available — see
`ROCKSDB_COMPACTION_STREAMER.md` for the frontier analysis, including the
public result that already defeats the disk-based version of the paper's
frontier claim.

## 8 H3 (coherence-enrolment bypass): the LSM instance is weak, LMDB's is excellent

The panel asked whether many readers mapping the same sealed SSTable across
processes is a natural LSM instance. In RocksDB it is a **stretch**, and the
paper should not lean on it:

- The overwhelmingly common deployment is one process per DB (MyRocks, TiKV,
  CockroachDB/Pebble, Kafka Streams). Sharing is across *threads* of one
  address space, so the lines are already shared within one process and the
  directory sees the same sharer set either way — H3 buys nothing extra.
- RocksDB does have `OpenAsSecondary`, a shipped read-only secondary instance
  that opens the primary's files, and multiple secondaries in separate
  processes over a tmpfs/DAX-resident SSTable set with `--mmap_read=1` would
  give N address spaces mapping the same immutable pages. It is real but it is
  a niche feature, and a reviewer will read it as the example being chosen to
  fit the mechanism.
- The strongest RocksDB-adjacent version is not RocksDB at all but the **OS
  page cache**: many independent reader processes doing buffered reads of the
  same sealed SSTable share one set of physical pages, read-only, with a sharer
  set as wide as the reader count.

The clean instance in my domain is **LMDB**, and it is worth the paper's
attention because it satisfies the premise *by design rather than by
coincidence*:

1. LMDB is a single memory-mapped B+tree file. Readers map it directly; there is
   no buffer pool and no copy.
2. Its concurrency model is explicitly **many reader processes, one writer** —
   the canonical deployment (OpenLDAP with a worker-process pool) has N
   processes mapping the same file simultaneously.
3. A read transaction **is** a declared immutable read epoch. LMDB's
   copy-on-write / free-list discipline guarantees that every page a reader
   reaches through its snapshot root is not modified for the transaction's
   duration — enforced by the engine, provable from the meta page, and already
   the semantics the application asked for. The paper's `mprotect` declaration
   would be re-stating a promise LMDB already keeps.

So: **"no writer exists for this region for this epoch" is not a new contract
the paper has to talk applications into. LMDB's read transaction already is
that contract, and it is 15 years old.** That is a much better H3 motivation
than a hypothetical multi-process RocksDB, and BerkeleyDB's shared-region
model is a second instance. If the paper wants an H3 application anchor from
storage, this is where to get it.

Caveat, stated because it cuts against the above: H3's benefit is snoop-filter
and directory *capacity*, so it needs the sharer count and the footprint to be
large enough for enrolment pressure to bind. A handful of LMDB readers on a
16 MiB CCX will not show it. The claim above is about the *contract* being
natural, not about the magnitude being demonstrated.
