# Outcome: DuckDB tenant CAT on silicon (named-engine join)

Date: 2026-09-01. Judged against `DUCKDB_TENANT_CAT_PREREG_2026-09-01.md`.
Host mos182 (`c4`), Xeon Platinum 8462Y+, socket 0, L3 60 MiB / 15 ways.
**STREAMING is not measured. nta and flush-behind are not arms.**

Tenant: DuckDB **v1.1.3** `19864453f7` (sha `f1aa00effc5d`), chain8 many-to-many
join, N=838864, P=10,000,000, R(N)=33,554,560 B, R/LLC=0.5333. Victim:
`pointer_chase` sha `026e357ae21a` (same binary as silicon hash-join e2e).
Tenant CPU 4 / victim CPU 6. 90/90 records `status=ok`. Medians of 5 reps.

Data: `experiments/asplos/data/duckdb_tenant_cat.jsonl`.
Analyzer: `experiments/asplos/analyze_duckdb_tenant_cat.py`.

This is **not** `DUCKDB_JOIN_CORUN_OUTCOME` (DuckDB was the victim of a
streamer). Do not share a table with that campaign.

## Verdicts

| id | prediction | verdict |
|---|---|---|
| K1 | `wb` degrades victim ≥ 1.30× over quiet | **PASS** 1.456× (106.880 / 73.406) |
| K2 | `cat01` query seconds exceed `wb` and `cat15` by ≥ 5% | **PASS** +104.49% vs wb, +104.61% vs cat15 |
| K3 | best-protection CAT costs tenant ≥ 10% query seconds vs `wb` | **PASS** cat01 **+104.49%** (0.8350 s → 1.7075 s) |

CERTIFY: YES. VERDICT: **SUCCESS**. E5 may retract “we make no named-application
claim” for **this operator in DuckDB** only. STREAMING remains model-only on
the hash-join kernel. nta/FB stay priced on `cxl_join_bench`.

## What it costs to protect the neighbour

Quiet victim 73.406 cycles/load (sd 0.005) — the 73.4 floor reproduced.
Unprotected co-run (`wb`) 106.880 (sd 0.705), tenant 0.8350 s (sd 0.0031).
`cat15` matches `wb` (0.8345 s / 107.562 cyc): full-mask CLOS is not a
second mechanism.

Protection \(R = (v_{wb}-v)/(v_{wb}-v_{qui})\). Tenant cost
\((t/t_{wb})-1\).

| arm | victim cyc/load | R | query s | tenant cost |
|---|---:|---:|---:|---:|
| qui | 73.406 | — | — | — |
| wb | 106.880 | 0 | 0.8350 | 0 |
| cat01 | 88.334 | **55.4%** | 1.7075 | **+104.5%** |
| cat02 | 100.239 | 19.8% | 1.5990 | +91.5% |
| cat04 | 120.970 | −42.1% | 1.4070 | +68.5% |
| cat08 | 141.983 | −104.9% | 1.0385 | +24.4% |
| cat15 | 107.562 | −2.0% | 0.8345 | −0.06% |
| wb_joinuniq | 226.746 | — | 0.1000 | — |

Best protection is **cat01**, not an intermediate width. Wider masks make the
victim *slower than unprotected `wb`* (negative R from cat03 onward): more
ways let the probe scan occupy more LLC. Occupancy tracks the mask (cat01
3.75 MiB → cat15 27.72 MiB; wb 28.09 MiB). G-cat-occ holds: cat01 CMT < wb
CMT.

joinuniq at the same N/P is 0.1000 s vs chain8 0.8350 s (rel_diff 88%). The
duplicate chain is the query-time mechanism; that diagnostic does not void
K1–K3.

## What this does not show

STREAMING itself. nta/FB on a DuckDB scan. A named-application claim for
any other operator. IVF. The 70-arm victim campaign.

## Addendum 1 — coupling, not STREAMING e2e

Do not discard this dataset because it lacks PAT slot 6. CAT enforcing
coupling — one PID, table and probe starved together, **+104.5% query
seconds for 55.4% R** — is the positive control for the paper’s central
claim. STREAMING’s claimed move is to name only the stream. Keep a
paragraph. Do not title the cell STREAMING e2e. Do not overlay r5 H2.

