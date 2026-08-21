# Compaction as the streamer, and the frontier claim

Written 2026-08-21 for the ASPLOS'27 panel, as the answer to bar (c). Contains
one result the paper needs to know about before a reviewer finds it.

## 1 Why compaction is the best streamer available

A leveled compaction reads a set of sealed SSTables it will never re-read,
merges them, and writes new sealed SSTables. The inputs are immutable by
construction — an SSTable is never modified after close, which is the whole
basis of the LSM design — so the "no writer exists" premise the paper needs for
its `mprotect` declaration is not an assumption an application has to be
trusted for; it is enforced by the storage engine's file lifecycle and is
checkable from the MANIFEST. Compaction runs continuously, at high bandwidth,
in the same process as the foreground reads it damages. Of the paper's three
named objects it is the only one that streams *by itself, on a schedule,
forever*.

And it is the object the abstract already names. So the paper is already
committed to this example; the question is only whether it survives scrutiny.

## 2 RocksDB already declares non-allocation — for its own cache

`db/compaction/compaction_job.cc:1179` and
`db/compaction/compaction_iterator.cc:1415` set `read_options.fill_cache =
false`; `table/block_based/block_based_table_reader.cc:1784` turns it into
`no_insert`. Compaction's blocks are read, used, and never admitted to the block
cache. That is *H2*, in software, shipped, on by default, for exactly this
object — because letting compaction evict the foreground's index and filter
blocks was unacceptable in production.

Use this. It is the strongest available evidence that the contract the paper
proposes is one that real systems want, and it costs the paper nothing to cite:
the same block that RocksDB refuses to admit to its software cache is
unavoidably admitted to L1, L2 and the LLC by the loads that read it. Software
has the knob at its layer; hardware does not have it at the layer below.

## 3 The existential problem: for disk-based compaction, O_DIRECT already wins

The panel asked me to say so plainly if a storage-world answer already solves
this. For compaction reading from a block device, **it does**, and there is a
public, quantified result:

*"Direct I/O for Cassandra Compaction: Cutting p99 Read Latency by 5x"*
(lightfoot.dev). Compaction floods the page cache with single-use data and
evicts the read path's hot pages; the kernel's reclaimer then stalls readers.
With O_DIRECT for compaction, on a 100 MB hot set: victim **p99 6.88 ms ->
1.33 ms (5.2x)**, p50 0.42 -> 0.31 ms, memory-stall time down 54%. And the cost
to the streamer's own end-to-end metric — the exact cell bar (c) requires — is
**negative**: compaction throughput went *up*, 265 -> 273 MiB/s at 12 GB of
memory and 254 -> 273 MiB/s at 6 GB, because bypassing the page cache
"eliminates the kernel-side memory copy that buffered reads incur."

That is a deployed alternative that recovers the victim *and pays nothing*. If
the paper's frontier table has a row for a disk-based compaction streamer, this
result falsifies it. A storage reviewer will know this post or will reconstruct
it in ten minutes.

The same source disposes of `posix_fadvise(POSIX_FADV_DONTNEED)` for the
opposite reason and in the paper's favour: it was adopted for this purpose in
2010 and is insufficient because **"the hint arrives too late"** — the pollution
happens while the data is being processed, and DONTNEED only evicts afterwards.
That is a quotable, independent instance of the paper's own "every
address-scoped control that ships is either advisory or bundled" claim, and it
is worth citing on those grounds.

For the record, in RocksDB specifically: `use_direct_reads` and
`use_direct_io_for_flush_and_compaction` both default to `false`
(`include/rocksdb/options.h:980,984`), and the internal flush/compaction path
does **not** call `InvalidateCache`/`fadvise(DONTNEED)` on its inputs or
outputs at all — the only `DONTNEED` callers are `table/sst_file_writer.cc:291`
(external file ingestion) and `file/sequence_file_reader.cc:250` (WAL replay).
So RocksDB out of the box *does* pollute the page cache during compaction, and
the fix operators reach for is the O_DIRECT flag above.

## 4 Why the paper still has a frontier, and the one sentence it must add

`fadvise` and `O_DIRECT` name **page-cache residency in DRAM**. They do not
name **cache-line allocation**. They win in the disk case for a reason that is
specific to that case: with O_DIRECT there is no kernel copy, so the bytes land
in DRAM by DMA and the core touches each line once, and on Intel inbound DMA is
capped by DDIO at a small subset of LLC ways (default 2). The LLC is protected
as a *side effect* of there being no second toucher.

Remove the device and the effect disappears. When the sealed SSTable is
**memory-resident** — on CXL, on DAX/pmem, on tmpfs, or in a memory-mapped
table — there is no page cache to advise, no DMA, no `O_DIRECT` (tmpfs and DAX
reject it or make it meaningless), and the core *must* issue loads for every
byte. Every one of those loads allocates. There is no flag, in any shipping
kernel or ISA, that makes them not allocate while still prefetching. That is
the missing cell, and it is the regime the paper's own abstract says is the one
that matters: *"CXL makes the choice unavoidable, because its latency makes the
polluting mode the only fast mode."*

Two consequences, and I would treat both as blocking:

1. **Qualify the abstract's named object.** "Sealed SSTables" unqualified
   invites the O_DIRECT rebuttal, because the reader's default mental model of
   an SSTable is a file on an SSD. Say *memory-resident* sealed SSTables — on
   CXL, DAX, or tmpfs — or say nothing about SSTables.
2. **Do not build the frontier table around a disk-based compaction streamer.**
   Build it around a compaction whose inputs are on CXL node 2, mapped and read
   with loads. Then `posix_fadvise` and `O_DIRECT` are not "costly
   alternatives", they are **inapplicable**, which is a stronger and more honest
   row than a contested cost. The frontier table should say so explicitly
   rather than leaving those cells blank: an inapplicable control is evidence,
   an unmeasured one is not.

Related mechanism the paper should name in its near-miss matrix, since a
reviewer who knows Intel platforms will raise it: **DDIO** already implements
capacity-limited allocation for inbound DMA writes, way-restricted and
tunable via the IIO LLC WAYS MSR. It is allocation control that is neither
context-scoped nor advisory — but it is *device*-scoped, and it cannot be
applied to core loads. That is a genuine near-miss and a good one: it shows the
hardware community already accepted that some fills should be allocation-limited
by *what they are* rather than *who issued them*, and only ever built it for
DMA.

## 5 What to measure, and the cost

Streamer arm: a RocksDB compaction over CXL-node-2-resident sealed SSTables,
`--mmap_read=1`, `compression_type=none`, driven by
`db_bench --benchmarks=compact` or `compact0`/`compact1` on a pre-built DB.
Report **compaction wall time and MiB/s** — its own end-to-end metric — in each
of: WB (default), `movntdqa` NT loads (needs a patch to `FilePrefetchBuffer` or
to the mmap read path; say so if not done), `clflushopt` flush-behind
(reuse `amd_flushbehind_aggressor`'s trailing-flush idea inside the read loop),
and `PROT_STREAMING` in gem5. Rows 1-3 are silicon-measurable today.

Honest setup cost, from the state I found the machines in:

| item | hours |
|---|---:|
| release RocksDB build, all three hosts (recipe in `README.md`; gcc 15 needs `-include cstdint`) | 1 |
| DB build + placement on CXL node 2, verified from `numastat` not from the flag | 2 |
| compaction-throughput harness with the LSM shape frozen and asserted | 4 |
| NT-load patch to the mmap read path, or the honest "not done" row | 6-10 |
| flush-behind variant of the same read loop | 3 |
| n>=10 x 4 arms x 2 hosts, interleaved, with CMT occupancy | 4 |
| **total** | **20-24** |

The victim-side search that would have been the other half of this — see
`ROCKSDB_LSM_PANEL_FINDINGS.md` §7 — I would not fund. Ten more engineer-hours
of RocksDB victim tuning buys a number between 1.3x and 1.8x.
