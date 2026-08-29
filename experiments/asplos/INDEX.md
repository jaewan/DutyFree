# Index of the ASPLOS campaign record

163 documents. This index exists so that someone picking the project up does not
have to read them in filename order. **Nothing here is deleted**: superseded
results are kept and marked, because the two worst failures this project has had
(`F10`, `F11`) were both *lost or unread* provenance, not wrong measurements.

## How to read a document

| suffix | meaning |
|---|---|
| `*_PREREG_*` | thresholds and action-on-miss, committed **before** the data existed |
| `*_OUTCOME_*` | the result, judged against that pre-registration |
| `*_CORRECTION_*` / `*_RETRACTION_*` | a previously published number withdrawn |
| addenda inside a file | later findings appended, never edited in place (rule A6.19) |

A document whose numbers were later invalidated carries a **`SUPERSEDED`** header
pointing at its replacement. Trust the pointer, not the filename date.

## Start here (current state, 2026-08-30)

| document | what it settles |
|---|---|
| `STATE_2026-08-30.md` | where the argument stands; what is open |
| `H2H_PARTITION_VS_H2_OUTCOME_2026-08-29.md` | partitioning vs H2 in one model — the wedge, and why a *pure* stream cannot show it |
| `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` | **supersedes the two fused documents below**; corrected wedge = 15.8–24.2% |
| `HNFRP_ROBUSTNESS_OUTCOME_2026-08-28.md` | the H2 bound under an unbiased LLC policy: 90.9% → **88.5%** |
| `HNFRP_REMAINING_CELLS_OUTCOME_2026-08-29.md` | `tab:h3sf`'s full 2×3; H3's cost 3.45% → **4.53%** |
| `AMD_NARROWMASK_OUTCOME_2026-08-30.md` | AMD: the residual survives an aimed mask; what is blocked and why |
| `BERGAMO_BACKINVAL_OUTCOME_2026-08-30.md` | the AMD harm is **L3-domain-local**, not fabric (+ addendum withdrawing the bimodality reading) |
| `GEM5_TREEPLRU_NONPOW2_BIAS_2026-08-28.md` | gem5's TreePLRU is 2× biased at non-power-of-two associativity |
| `CONFIG_FIDELITY_AUDIT_2026-08-29.md` | every geometry/default swept for silent degradation |

## Superseded — kept, do not cite

| document | superseded by | why |
|---|---|---|
| `H2H_FUSED_OUTCOME_2026-08-29.md` | `FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` | power-of-two probe stride aliased the table onto 1/8 of the cache sets |
| `FUSED_TABLESWEEP_OUTCOME_2026-08-29.md` | same | same |
| `M3B_OUTCOME_2026-08-25.md` (interpretation) | `M5_OUTCOME_2026-08-26.md` | "27% is residency" was overturned the next day |
| `REDTEAM_REVIEW_2026-08-28.md` finding S1-1 | `REDTEAM_S1-1_RETRACTION_2026-08-28.md` | self-retracted; the model is conservative, not optimistic |

## Families

- **`M*`** — the Intel mechanism series (M1–M12): occupancy, table size, isolation cost.
- **`E1`–`E4`** — the frontier: no free split, decomposition, geometry, the wedge travelling.
- **`W*`** — the gem5/SF series, including `W1` (the H2 bound) and the `W8` FS-mode work.
- **`GATE1_*`** — the co-run gates and their reconciliation.
- **`HNFRP_*`, `FUSED_*`, `H2H_*`** — the 2026-08-28→29 gem5 campaign (policy bias, the wedge, the sweeps).
- **`AMD_*`, `BERGAMO_*`, `phase1/`** — the AMD residual thread.

## Failure taxonomy referenced throughout

| tag | failure |
|---|---|
| `F9` | a figure labelled with a **requested** rather than a **realized** size (five instances) |
| `F10` | an unpinned apparatus: results whose launcher was never committed |
| `F11` | a correct artifact, committed, that nobody read back into the paper |
| `F12` | a criterion a crashed run could satisfy |
| `A6.19` | never append to a committed data file; corrections go in dated addenda |
| `S5.1` | an arm's identity comes from its own artifact, never the launcher's intent |
| `S6.6` | when provenance is gone, say it is gone |

## Runners and analyzers

`run_*.sh` launches; `analyze_*.py` judges. Analyzers hold the pre-registered
thresholds as **module constants**, not arguments, so that changing one after
seeing data is visible in git. 15 pairs currently.
