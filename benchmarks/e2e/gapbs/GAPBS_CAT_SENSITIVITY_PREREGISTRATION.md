# Pre-registration: GAPBS PageRank CAT capacity-sensitivity gate

Dated 2026-08-11. This supersedes `GAPBS_LLC_OCCUPANCY_PREREGISTRATION.md`
as the co-run selection gate, before any co-run arm.

## Objective and method

Directly measure PageRank's runtime response when LLC capacity is removed. For
each host and scale g21--g25, run quiescent PageRank in a CPU-based resctrl CAT
group at the full mask and at the minimum legal contiguous way mask. The CPU's
actual L3 domain is read from sysfs; the runner writes all other domains' full
masks, reads `schemata` back, and records the exact mask and effective MiB.

## Decision rule

Select the smallest scale per host with a minimum-way median runtime at least
2x its same-scale/full-mask median, with CoV <=5% in both configurations. If
no scale passes on either host, PageRank fails the magnitude pre-gate and the
campaign moves to HNSW without building a DuckDB streamer.

Four GAPBS trials are run per invocation (first warm-up, final three measured),
with three independent invocations per scale/mask. There is no streamer or
aggressor. CMT occupancy is recorded only as a diagnostic and is explicitly
not attributed to `outgoing_contrib` or used as a selection criterion.
