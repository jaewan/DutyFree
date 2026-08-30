# For external auditors

A guided path through this repository. It assumes no prior contact with the
project and takes about an hour to follow.

## 0. Verify the repository works before reading anything

```bash
make check     # 13 regression tests + lint; stdlib only, no install step
python3 experiments/asplos/analyze_archives.py
```

The second command recomputes **every headline simulation number from committed
data with committed code** and checks it against the value printed in the outcome
documents. It should end with `ALL PUBLISHED VALUES REPRODUCE`. If it does not,
stop and treat every simulation claim as unverified.

## 1. Read four documents, in this order

| # | document | ~time |
|---|---|--:|
| 1 | `experiments/asplos/STATE_2026-08-30.md` | 10 min |
| 2 | `experiments/asplos/INDEX.md` | 5 min |
| 3 | `experiments/asplos/H2H_PARTITION_VS_H2_OUTCOME_2026-08-29.md` | 10 min |
| 4 | `experiments/asplos/FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` | 10 min |

(3) is the experiment that tests the project's central claim, and it **failed** on
the first attempt. (4) is a correction that reduced a headline number by 2.3x.
They are listed deliberately: read how the project handles its own negative
results before reading its positive ones.

## 2. What to be sceptical about, with our own evidence

We would rather hand you the attack surface than have you find it.

| weakness | where it is documented |
|---|---|
| The central benefit is **simulation-only**; no silicon implements STREAMING | `STATE`, "why believe the model" |
| The simulator had **five defects** found in the last week | `GEM5_TREEPLRU_NONPOW2_BIAS`, `CONFIG_FIDELITY_AUDIT`, `FUSED_INDEX_ARTIFACT_CORRECTION` |
| **Every** gem5 STREAMING number uses an SE-only pseudo-instruction, not the OS path | `W8.1`, `STATE` "the one open gap" |
| H3 has **no demonstrated benefit** on reachable hardware and costs 26% tenant IPC | `W3.4`, `W3.1`, `STATE` |
| AMD absolute magnitudes **do not reproduce** across a host rebuild (27.6x vs 19.9x) | `AMD_NARROWMASK_OUTCOME` |
| The model runs **2 cores / 5 MiB LLC**; production is 60+ cores / 300 MB | scale is answered on silicon (`E4`), not in the model |

## 3. How to check a claim end to end

Pick any number in an outcome document and trace it:

1. `experiments/asplos/HARNESS_MANIFEST.md` — maps experiment -> pre-registration
   -> runner -> analyzer -> data file.
2. The `*_PREREG_*.md` was committed **before** the data existed; check
   `git log --diff-filter=A` on it against the data file's commit date.
3. The analyzer holds its thresholds as **module constants**, so a threshold
   edited after seeing data is visible in `git log -p`.
4. `experiments/asplos/data/` holds the raw records.

## 4. Conventions that are load-bearing

Each exists because violating it cost a result. They are stated in `README.md`
§5 and enforced by tests in `tests/`.

- Pre-register thresholds **and the action-on-miss** before running.
- Report the **realized** configuration, never the requested one (sizes quantize;
  this project has five instances of getting it wrong).
- Read an arm's identity from **its own artifact**, never the launcher's intent.
- A verification result that is **uniform across every record** is more likely a
  broken checker than a finding.
- The record in `experiments/asplos/` is **append-only**. Superseded results are
  marked and kept, never deleted — the project's two worst failures were lost and
  unread provenance, not wrong measurement.

## 5. Updating the paper draft after review

The paper is a **separate repository** at `~/STREAMING_Paper`. Two rules:

- **Never `git push` from it.** Every write there is published to co-authors.
- **Rebuild and check `undef-ref: 0` after every edit.** This document silently
  drops tables when text is added — it has done so twice.

[`PAPER_DELTA.md`](PAPER_DELTA.md) is the bridge between this repo and the draft:
what has already been folded in, the **four findings that have not been**, the
structural edits recommended, and the commands to re-check both.

## 6. What is not in this repository

- **The paper** — `~/STREAMING_Paper`, deliberately separate.
- **Broker-side binaries** — the AMD `victim`/`aggressor` that produced the
  published AMD numbers live only on that host (`~/tmp_dutyfree_exp/`). The
  runners are committed under `experiments/asplos/broker/`; the binaries are not,
  and `HARNESS_MANIFEST.md` says so.
- **Full gem5 `stats.txt`** — 375 MB across 187 runs. The load-bearing fields are
  archived in `experiments/asplos/data/gem5/`; the field list is the union of
  everything the outcome documents cite.
- **Several 2026-08-29/30 analyses were inline** and are not recoverable as code.
  Their thresholds are in the pre-registrations; `analyze_archives.py` recomputes
  their results from the archive.
