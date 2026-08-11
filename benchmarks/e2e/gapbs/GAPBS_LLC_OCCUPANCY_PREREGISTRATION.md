# Pre-registration: GAPBS PageRank shared-LLC occupancy gate

Dated 2026-08-11. This corrects the earlier private-L2-only sizing gate before
the first co-run arm.

## Objective

Measure, rather than infer from RSS, the quiescent shared-LLC occupancy of
PageRank's reusable `outgoing_contrib` state. The per-host co-run scale is the
smallest scale in `g21` through `g25` whose measured CMT occupancy is 40–60%
of the local shared LLC while PageRank has a >=2 s repeated-work window.

## Configuration

One pinned PageRank process runs at a time, with `OMP_NUM_THREADS=1` and the
existing CPU/node mapping: Intel CPU 32/node 0 and AMD CPU 8/node 0. Each
point is `pr -g SCALE -n 4 -r 1 -l`; the first trial is warm-up. The runner
creates a distinct resctrl monitoring group, attaches the live PID after the
`Graph has` marker, records `llc_occupancy`, `mbm_local_bytes`, and
`mbm_total_bytes` from the CPU's L3 domain after every subsequent trial, then
records the group and task state at teardown.

## Predictions and decision rule

`outgoing_contrib` is 4 * 2^scale bytes: 8 MiB at g21, 16 MiB at g22, 64 MiB
at g24, and 128 MiB at g25. The anticipated selected scales are g25 on Intel
(about 40% of its 320 MiB LLC) and g21 on AMD (about 50% of its 16 MiB CCX L3),
but **observed CMT occupancy**, not this arithmetic, decides.

A point is invalid if CMT cannot be attached/read, its allocation is not local
to the requested node, or its measured trials have CoV >5%. If no point lands
in 40–60%, report the sweep and select no co-run configuration. No streamer or
aggressor is started in this gate.
