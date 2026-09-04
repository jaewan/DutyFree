# Outcome: IVF-Flat list-dominated declaration site (native, c4)

Date: 2026-09-02. Judged against `IVF_LIST_DOM_PREREG_2026-09-02.md`
(on disk before this run). Host mos182 (`c4`). Wall 9.52 s (k-means +
invert dominate; timed search 0.820 s). Data:
`experiments/asplos/data/ivf_list_dom.jsonl`.

**STREAMING is not measured.** Slot 6 is not a datapath on this kernel.
`mprotect(PROT_STREAMING)` returned **EINVAL (22)** and the harness fell
back to `PROT_READ`. That is a UAPI result, not H2.

`--preset silicon` was **not** run. `run_silicon_ivf.sh` was **not**
invoked. QPS is recorded on the JSON line and is not a campaign metric.

## Verdicts

| id | prediction | verdict |
|---|---|---|
| G-list-dom | `nprobe×nb/nlist² ≥ 8` | **PASS** **512** (32×262144/128²). Per-query list bytes 64 MiB vs codebook 128 KiB |
| G-recall | `recall_at_k ∈ (0, 1]` | **PASS** **1.0** |
| G-vma | smaps lists-file Rss ≥ 0.50 × 270,532,608 B | **PASS** 270,532,608 B, 1 VMA |
| G-copy | anon RSS growth ≤ 0.25 × lists | **PASS** **+0 B** (anon RSS 471,040 B before and after search) |
| G-stream-uapi | record STREAMING mprotect | **recorded** EINVAL; not a kill |

CERTIFY: YES. VERDICT: **declaration site is live.**
`void_streaming_ivf=false`.

Geometry: `nlist=128`, `dim=256`, `nb=262144`, `nprobe=32`, `nq=48`,
`k=10`. Codebook 131,072 B (WB heap). Lists file
`/tmp/ivf_list_dom_full/lists.bin`. Search did **not** materialize the
lists into anonymous RSS.

The silicon CAT costume remains codebook-dominated (`list_dom_ratio=
0.0078` at `nlist=8192`, `nb=nlist×4`). This outcome does not license
that campaign.

## What this licenses

A later gem5 campaign may tag **this mapping** (SE m5op, then FS
`mprotect` on a custom kernel that accepts `PROT_STREAMING`). Each of
those is a new prereg. Do not start them on mos181 while r6b is in
flight. Official STREAMING application bench remains the hash join.

## What this does not show

H2. Neighbour R. Tenant QPS vs CAT. A silicon STREAMING IVF cell. The
unrun `IVF_FLAT_SILICON_PREREG` CAT sweep. r5 join tuples/s. DuckDB
+104.5%.

## Addendum — not an E5 STREAMING IVF sentence

Keep IVF out of E5 as a STREAMING family. This outcome only retracts
“IVF lists cannot be a VMA the search actually walks, and the walk is
a codebook scan.” It does not retract “no STREAMING arm in IVF on
silicon.”
