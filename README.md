# DutyFree — STREAMING: an enforced, object-scoped cache-admission contract

Umbrella repository for the **STREAMING** memory-type contract: an OS-declared,
page-granular x86 memory type (PAT slot 6) that lets software tell hardware a
page holds an **immutable read stream**, so the shared cache can decline to admit
it.

> **Status: active research, ASPLOS'27 in preparation.** The paper lives *outside*
> this repo in `~/STREAMING_Paper`. This repo holds the implementations, the
> experiments, and — importantly — the **provenance record** of every measurement,
> including the ones that were later corrected or withdrawn.

---

## 1. The claim, in one paragraph

A streaming tenant and a latency-critical neighbour cannot currently share a
last-level cache without one of them paying. Shipped knobs (Intel CAT, AMD
way-partitioning) *can* protect the neighbour, but a way mask is indexed by
**agent**: it confines the tenant's stream and its own reused working set
together, because both belong to the same core. A page-scoped label is indexed by
**address** and can separate them. The contract is **I0/I1** on the OS side
(uniform memory type per frame; read-only epoch) and **H1/H2/H3** on the hardware
side (WB-class prefetching; never insert clean STREAMING lines in the shared LLC;
skip coherence enrolment).

**H2 is the load-bearing clause.** H1 is a precondition, H3 is a bounded
capability claim whose charge has not been demonstrated on reachable hardware.

## 2. Repository layout

```text
DutyFree/
├── linux/          [submodule] PROT_STREAMING: mprotect bit → PAT slot, writeback IPI
├── gem5/           [submodule] CHI H2/H3, Ruby way partitioning, STREAMING TLB path
├── benchmarks/     silicon microbenchmarks + e2e (hnsw, gapbs, duckdb_join, hash_join)
│   └── setup/      per-host freeze scripts; state/ captures
├── experiments/    THE RECORD — pre-registrations, outcomes, runners, analyzers
│   ├── asplos/     the current campaign (163 documents; see INDEX.md)
│   └── phase1/     earlier AMD/CCX residual work
├── results/        raw measurement archives
├── logs/           build and run logs
└── scripts/        orchestration
```

## 3. Hosts

| host | reach | part | role |
|---|---|---|---|
| **mos181** | local | Intel Xeon 8592+ (EMR), 320 MiB LLC, 20 ways | primary Intel silicon |
| **mos182** | `ssh c4` | Intel 8462Y+ (SPR), 60 MiB LLC, 15 ways | second Intel geometry |
| **moscxl** | `ssh broker` | AMD EPYC 9754 (Bergamo), 32×16 MiB L3, **16 CAT ways** | AMD + CXL |

`broker` was **rebuilt** during a 2026-08-22→30 outage: `~/DutyFree` there is no
longer a git checkout, but `~/tmp_dutyfree_exp/` **survived** and holds the
`victim`/`aggressor` binaries that produced the published AMD numbers. Use those,
not rebuilds, for anything compared against published AMD figures.

## 4. How to pick this up

**Read these four, in order.** They are the shortest path to the current state:

1. `experiments/asplos/INDEX.md` — map of the record, marking what is superseded.
2. `experiments/asplos/STATE_2026-08-30.md` — where the argument stands, what is
   open, what to do next.
3. `experiments/asplos/FUSED_INDEX_ARTIFACT_CORRECTION_2026-08-30.md` — the most
   recent correction, and a good example of how corrections are handled here.
4. `experiments/asplos/AMD_NARROWMASK_OUTCOME_2026-08-30.md` — the AMD state,
   including what is blocked and why.

### Working conventions that are not optional

These exist because violating them has cost this project real results:

- **Pre-register before running.** Thresholds *and* the action-on-miss are fixed
  in a `*_PREREG_*.md` and committed **before** the data exists. Analyzers carry
  the thresholds as constants so an edit after the fact is visible in git.
- **Report the realized configuration, not the requested one.** Sizes quantize
  (power-of-two rounding has bitten this project five times). Read the value back
  from the run's own artifact.
- **Read arm identity from `config.ini`/logs, never from the launcher's intent.**
- **A verification check that is uniform across all records** (all pass, all fail,
  all `?`) is more likely broken than the thing it tests.
- **Never `git push` from `~/STREAMING_Paper`,** and treat every write there as
  published to co-authors.
- **Do not use the `-R` pacing throttle** — known confound. Thread count is the
  honest bandwidth lever.
- **Verify the machine is idle before a diagnostic**, not after the answer
  surprises you.

## 5. Engineering conventions

```bash
make help             # all tasks
make check            # tests + lint (what CI runs); stdlib only, no install
make gem5             # build the Intel 8592 gem5 target
make state            # print where the project stands
make clean-artifacts  # build junk ONLY -- never results or records
```

- `experiments/lib/dutyfree/` — shared helpers for parsing gem5 artifacts,
  loading JSONL, robust statistics, and resctrl masks. **Use it for new
  analyzers.** Existing analyzers are deliberately *not* refactored onto it:
  they are provenance, and editing code that produced a cited number would
  change that result's basis.
- `tests/` — one regression test per failure this project actually committed.
  Add one when you find a new class of mistake; that is what the directory is
  for.
- `experiments/asplos/HARNESS_MANIFEST.md` — which runner and analyzer produced
  which result, and which apparatus is *not* in this repo.
- Paths honour `DUTYFREE_GEM5` / `DUTYFREE_W1_GEM5`, defaulting to the original
  absolute paths so historical behaviour is unchanged.

**The record is append-only.** `experiments/asplos/` is a flat, date-stamped log
whose documents cross-reference each other by filename. Do not reorganise it into
subdirectories, and do not delete superseded results — mark them and point at the
replacement. Unread or lost provenance is this project's characteristic failure
(`F10`, `F11`), not wrong measurement.

## 6. Building and running

```bash
git clone --recursive <url> && cd DutyFree

# gem5 (Ruby/CHI, Intel 8592 config)
cd gem5 && source ~/gem5-venv/bin/activate && scons build_Intel_8592/gem5.opt -j 32

# a representative campaign run (pre-registration first!)
experiments/asplos/run_h2h_fused.sh        # partitioning vs H2, one model
python3 experiments/asplos/analyze_h2h_fused.py

# silicon: freeze the host before measuring
sudo benchmarks/setup/bergamo_freeze.sh    # or emr_freeze.sh / spr_freeze.sh
```

Key gem5 environment knobs (read at run time, no rebuild):
`HNF_RP` (LLC replacement policy), `HNF_REQ_MASKS` (`node:mask` per-requestor CAT),
`HNF_SF_FINITE`, `HNF_H3`, `HNF_DMT`, `HNF_FWD_UNIQUE`, `SEQ_OUT`, `L1D_MASK`,
`L1D_RP`.

> `HNF_FWD_UNIQUE` and `SEQ_OUT` **changed defaults** after the W1 campaign.
> Pin them to `0` and `1024` to reproduce W1-era numbers.

## 7. What is currently open

See `STATE_2026-08-30.md` for detail. In brief: the §1/§5 rewrite is partially
done; H3's standing is **unknown** (not "cut", not "supported"); the AMD
non-allocation arm is **blocked** on host configuration; and the paper is 24
pages against an 11–13pp body norm.
