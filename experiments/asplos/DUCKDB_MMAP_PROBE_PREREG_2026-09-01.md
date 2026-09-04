# Pre-registration: DuckDB mmap-probe declaration site (native, c4)

Registered **2026-09-01, before any arm of this campaign produced a
number.** STREAMING datapath is **not** measured. This is the identity
gate the DuckDB tenant-CAT result does not provide: can the probe be an
OS object `mprotect` can name, while the hash table stays a different
mapping?

## Why

Silicon tenant CAT (`DUCKDB_TENANT_CAT_OUTCOME_2026-09-01.md`) showed
**+104.5% query seconds** at 55.4% R because CAT labels a PID. STREAMING
would answer that only if the probe scan’s LLC fills come from a VMA the
kernel can type, not from a buffer-pool copy of the same bytes.

gem5 + custom OS cannot show that until this gate passes **on native
silicon** (c4). Slot 6 still decodes as WB on the host; a successful
`mprotect(PROT_STREAMING)` here is a UAPI probe, not H2.

## What this is allowed to be

A **declaration-site** campaign. Two in-process DuckDB joins at the
tenant-CAT geometry (`N=838864`, `P=10M`, `chain=8`), same `hash(i)%k`
keys:

- **copy:** `CREATE TABLE p` then `p JOIN b` (engine-owned probe).
- **mmap:** probe keys live in a file-backed `mmap`; a table function
  `mmap_probe()` scans that mapping into DuckDB vectors (size 2048);
  `b` stays a DuckDB table.

Metric: `count(*), sum(b.payload)` equality, `/proc/self/smaps` RSS,
`mprotect` errno. **Not** query seconds vs CAT, **not** neighbour R,
**not** gem5, **not** H2 bypasses.

## Host

**mos182 / `ssh c4` only** for `--full`. Smoke (`--self-test`) may run
anywhere. Do **not** run on mos181 (FS r6b owns that host). No CAT, no
victim, no exclusive-host resctrl.

## Registered gates (fail-closed)

- **G-host.** `--full` hostname is `mos182` or `c4`.
- **G-lib.** DuckDB C library version contains `v1.1.3` (same family as
  tenant CAT).
- **G-match.** mmap join `count` and `sum(payload)` equal the copy
  control. Action on miss: **void** (different join).
- **G-vma.** After the mmap join, smaps shows a mapping whose pathname
  contains the probe file and `Rss >= 0.50 * P * 8`. Action on miss:
  **void** (probe was not the scanned object).
- **G-copy (the STREAMING-site kill).** On the mmap arm, anonymous RSS
  growth across the join (`[heap]` + nameless anon) is **≤ 0.25 × P × 8**.
  Action on miss: **VOID for STREAMING DuckDB** — the engine copied the
  probe into WB heap; `mprotect` on the file mapping would not name the
  fills. Do **not** start gem5 DuckDB, do **not** write an E5 STREAMING
  DuckDB sentence.
- **G-stream-uapi.** `mprotect(PROT_READ|PROT_STREAMING)` is attempted
  after the mmap is filled and sealed read-only. Success or `EINVAL` /
  `ENOSYS` is **recorded, not a kill**. Stock SPR is expected to refuse
  or treat slot 6 as WB. This campaign does not claim H2.

## What success licenses

Only: “the probe can be a distinct mapping DuckDB scans, and it did not
fully materialize into anonymous RSS.” That licenses a **later** gem5 SE
H2 kill-gate on a **shrunk** P, then FS `mprotect`, each with its own
prereg. It does **not** license quoting +104% as a STREAMING win, and it
does not license a silicon STREAMING DuckDB number.

## What has not happened

No JSONL, no outcome, no gem5, no paper sentence. This file is a gate
list, not a result.
