# Three §11 outstanding items resolved, one left honestly unresolved

Written 2026-08-13, continuing the same session as `PAPER_SESSION_PROMPT.md`.
All landed in `~/STREAMING_Paper/`, build verified clean (17pp stable) after
each. Not lead-only decisions — each was either a fact to verify against
instantiated state, or a caveat this project's own established rules already
mandate once the fact was known.

## 1. The `[DESIGN DECISION]` marker, `Sec4_Streaming.tex:~92` — resolved by reading the gate, not by inference

The marker asked: does a clean `Streaming` L2 victim (a) drop silently, or
(b) route to a non-allocating fill/stream buffer, and which does the gem5
model implement? The adjacent (now-removed) comment already guessed (a) from
a stale source comment. Verified directly against
`~/DutyFree-Gem5/src/mem/ruby/protocol/chi/CHI-cache-actions.sm`'s
`CheckCacheFill` (line 3505): `need_fill` is guarded by
`!(is_HN && tbe.isStreaming)`; when the gate is closed, none of the three
fill branches (write-in-place, allocate-and-write, evict-and-retry) execute —
confirming (a) by reading the actual gate. No buffer structure exists
anywhere in the current tree (`grep` for `streamBuffer`/`FillBuffer` in the
protocol directory returns nothing). Prose now states this plainly and
credits the buffer as the admitted-but-unbuilt alternative.

## 2. RocksDB 2.33× — now labelled AMD-only, with the Intel null cited

`Sec5_Evaluation.tex`'s RocksDB paragraph read as a general "real
application" confirmation. It isn't one: `~/tmp_dutyfree_exp/results/
exp41_llcgeom_intel/exp41_report.md` (read directly off this host, n=5,
rep-paired bootstrap) shows RocksDB `readrandom` at **1.00× [0.99,1.01]** on
Intel at the cache geometry matched to AMD's victim-to-L3-way ratio (1 way =
16 MiB, victim resized to 4× its private L2 so it is genuinely L3-dependent,
not a repeat of the private-L2 collapse — instance 2 of 4 on that list, per
`benchmarks/e2e/E2E_SESSION_PROMPT.md` §6). Paragraph now says AMD-specific,
not yet cross-vendor, and cites both the Intel null and the AMD run's own
missing provenance (`benchmarks/e2e/E2E_SESSION_PROMPT.md` §3.1: no
surviving raw dataset, runner, or invocation on either host). Points at
`benchmarks/e2e/E2E_STATUS.md` for the in-progress cross-vendor replacement.

**Not resolved, honestly:** `Sec2_DirectoryTax.tex:60`'s 9.6× (session
prompt's "audit item 5," "unrecoverable config"). No trace of what,
specifically, is unrecoverable about it survives anywhere in this repo
beyond the bare mention in `PAPER_SESSION_PROMPT.md:443` — `REPO_DISCIPLINE.md`
and `GATE0_TREE_UNIFICATION.md` have no matching "audit item" numbering, and
no other file names it. Rather than invent a plausible-sounding gap to
caveat against, this is left exactly as flagged: unresolved, provenance of
the original audit itself gone. Whoever ran that audit should be asked what
it found before anyone else writes a caveat for it.

## 3. `tab:appplat` — microcode/stepping/CXL device, verified per host, not assumed

This attribution had been wrong twice already (`Sec2_DirectoryTax.tex`'s own
margin note: "Samsung Type 3" for all platforms, then "Micron 6400" for the
8592+ specifically, each time by assumption). Re-verified all three hosts
directly this time:

| host | CPU | stepping | microcode | CXL device (`lspci -nn`) |
|---|---|---|---|---|
| mos181 | Xeon 8592+ | 2 | `0x210002d3` | `[1b00:c001]` Montage M88MX5891 |
| broker/moscxl | EPYC 9754 | 2 | `0xaa00215` | `[1b00:c001]` Montage M88MX5891 |
| c4/mos182 | Xeon 8462Y+ | 8 | `0x2b000661` | `[1b00:c001]` (same ID; c4's `pci.ids` is stale and doesn't resolve the name) |

All three: the **same** Montage Technology M88MX5891 CXL Memory Expander
Controller. `cxl list` on mos181 additionally gives the 8592+ node's
capacity/interleave the note specifically asked for: region0 = 256 GiB,
`interleave_ways=1`, granularity 4096 B. Broker's own capacity via
`numactl -H` (node 2: ~252 GiB, cpuless) — its `cxl` tool returned no devices
(driver not bound the same way there), so interleave ways is not probed for
that host.

This *is* a "blanket all-platforms-use-device-X" claim again — but this
time earned by three independent per-host checks, not restored from either
prior wrong assumption. Landed in both `tab:appplat` and the
`Sec2_DirectoryTax.tex` sentence that named the device, with margin notes on
both recording the verification method so a future pass doesn't have to
re-derive it from nothing, the way this pass had to.
