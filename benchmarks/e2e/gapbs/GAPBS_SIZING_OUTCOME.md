# Outcome: GAPBS cross-vendor sizing gate

Dated 2026-08-11. This standalone gate ran before any co-run arm.

## Result

PageRank at Kronecker scale 22 is the common co-run victim:

| host | CPU/node | PageRank median trial time | CoV | decision |
|---|---|---:|---:|---|
| `mos181` | CPU 32 / node 0 | 2.748790 s | 0.109% | pass |
| `moscxl` | CPU 8 / node 0 | 2.140120 s | 1.387% | pass |

The `-g 22` graph is far beyond either private L2 (2 MiB Intel, 1 MiB AMD),
has stable repeated timings, and supplies a multi-second victim window on both
vendors. The later co-run campaign is therefore fixed to `pr -g 22 -n 4 -r 1
-l`, one pinned OpenMP thread; its first trial is warm-up.

## Other observations

At scale 24, PageRank remains stable but is much longer: 15.541270 s on Intel
and 11.492170 s on AMD. BFS and CC are shorter at scale 22 and were not chosen.
All valid records, commands, GAPBS commit, and live `numastat` samples are in
`artifacts/sizing_gate_mos181.jsonl` and `artifacts/sizing_gate_moscxl.jsonl`.

The scale-25 BFS endpoint completed (1.780870 s Intel; 1.553070 s AMD). The
scale-25 PageRank/CC endpoints were terminated after the selection rule had
already passed, to release the pinned cores for the co-run campaign. Their
interrupted records remain in the JSONL and are listed as invalid by the
summary; no result is inferred from them. An accidental detached retry created
additional valid BFS scale-20/22 records on Intel; they are retained as raw
provenance but are not used for the PageRank selection.

## Predictions

The private-L2 and stable-timing predictions held. The expected relative
latency shape did not select the victim: PageRank, rather than BFS or CC,
provided the required multi-second repeated-work window. No co-run tax,
recovery, or frontier result is claimed by this gate.
