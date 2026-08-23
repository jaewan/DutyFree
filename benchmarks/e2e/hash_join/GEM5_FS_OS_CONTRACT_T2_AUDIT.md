# T2 audit: interrupted 4-CPU DirTax STREAMING sweep

Dated 2026-08-23. This is an execution audit, not an experimental result.

The original 15-arm script starts every O3+Ruby simulation concurrently and
returns immediately. In this execution environment that launch pattern first
lost its children when the invoking command ended; after retaining its parent
shell, it ran for approximately five hours. Six arms completed, while nine
still had zero-byte `stats.txt` files. The nine were stopped with `SIGINT` in
accordance with the session prompt's 90-minute zero-stat tripwire.

Completed artifacts are in `gem5/logs/intel_8592_4cpu_dirtax_streaming/`:

| WSS | completed arms |
|---:|---|
| 10% | alone, WB, Streaming |
| 25% | alone only |
| 53% | alone only |
| 75% | alone only |
| 100% | none |

At 10%, the three completed runtimes are all 1.000× at the printed precision.
This is not evidence for or against H2: the predicted tax is at larger WSS.
The aggregate `DataArrayWriteOnFill::total` counter is also not a valid H2
counter by itself because it combines private and shared cache controllers.

No conclusion about tax, H2, H3, or the OS contract follows from these partial
artifacts. The next authorized measurement is a bounded, serial matched trio
at 53%, executed by
`gem5/scripts/intel_8592_4cpu_dirtax_streaming_supervised.sh`. That runner
uses the exact frozen command-line geometry, records provenance per arm, and
sends `SIGINT` after 5,400 seconds if an arm still has zero-byte stats.
