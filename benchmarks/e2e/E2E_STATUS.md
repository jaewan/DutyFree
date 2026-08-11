# E2E status

Current candidate: GAPBS PageRank with a DuckDB scan streamer. The
private-L2/runtime gate passes, but its common `-g 22` selection is withdrawn
pending a pre-registered per-host CMT shared-LLC occupancy gate.

| bar | status |
|---|---|
| magnitude | unmeasured |
| reproducibility | private-L2/runtime gate passes; LLC occupancy gate pending |
| recovery | unmeasured |
| frontier | preregistered; unmeasured |

See `gapbs/GAPBS_SIZING_OUTCOME.md` and the separately committed
`gapbs/GAPBS_DUCKDB_CORUN_PREREGISTRATION.md`.
