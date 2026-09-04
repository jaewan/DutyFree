# Outcome: DuckDB mmap-probe declaration site (native, c4)

Date: 2026-09-02. Judged against `DUCKDB_MMAP_PROBE_PREREG_2026-09-01.md`
(on disk before this run). Host mos182 (`c4`). DuckDB C library **v1.1.3**.
Wall 2.36 s. Data: `experiments/asplos/data/duckdb_mmap_probe.jsonl`.

**STREAMING is not measured.** Slot 6 is not a datapath on this kernel.
`mprotect(PROT_STREAMING)` returned **EINVAL (22)** and the harness fell
back to `PROT_READ`. That is a UAPI result, not H2.

## Verdicts

| id | prediction | verdict |
|---|---|---|
| G-lib | C library version contains v1.1.3 | **PASS** `v1.1.3` |
| G-match | mmap join equals `CREATE TABLE p` copy control | **PASS** count=80,000,000 and sum identical |
| G-vma | smaps probe-file Rss ≥ 0.50 × 80 MiB | **PASS** 80,003,072 B, 1 VMA |
| G-copy | anon RSS growth ≤ 0.25 × 80 MiB | **PASS** **+139,264 B** (0.17% of probe) |
| G-stream-uapi | record STREAMING mprotect | **recorded** EINVAL; not a kill |

CERTIFY: YES. VERDICT: **declaration site is live.**
`void_streaming_duckdb=false`.

The table function `mmap_probe()` scanned a file-backed mapping of the
same `hash(i)%k` keys as tenant CAT (`N=838864`, `P=10M`, `chain=8`).
Anonymous RSS moved by **136 KiB** while the probe VMA held **80 MiB**.
DuckDB did **not** fully materialize the probe into the heap. Vector
chunks (size 2048) are the expected WB residue; they are not a copy of P.

## What this licenses

A later gem5 campaign may tag **this mapping** (SE m5op, then FS
`mprotect` on a custom kernel that accepts `PROT_STREAMING`). Each of
those is a new prereg. Shrink P for FS time. Do not start them on
mos181 while r6b is in flight.

## What this does not show

STREAMING addressing the **+104.5%** CAT tax. H2. Neighbour R. Query
seconds. A silicon STREAMING DuckDB cell. Vanilla `CREATE TABLE p`
(that path is the copy control, not the STREAMING site).

## Addendum — not an E5 STREAMING DuckDB sentence

Keep DuckDB tenant CAT as the coupling control. This outcome only
retracts “DuckDB cannot expose a probe VMA.” It does not retract “no
STREAMING arm in DuckDB on silicon.”
