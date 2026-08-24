# Work plan: items 4–17 (session grant, 2026-08-24)

Durable so it survives context compaction. **Update the Status column in place as
each item lands, in the same commit as the work.** Item numbers are the ones used
in the 2026-08-24 "what are left items" inventory.

## Block 1 — the fused rewrite (items 4–7). One coherent paper edit.
Driven by `A4_HITRATE_FINDING_2026-08-24.md`: `run_hot_probe` probes at 100% hits
(`keys[i % keys.size()]`), `join_range` at `hit_rate` 0.5, so the published
1.47× is a workload mismatch. Matching the rate gives 88.3 → 44.0 cyc/access and
*reverses the sign* against hot-probe's 55.2.

| # | item | where | done means | Status |
|---|---|---|---|---|
| 4 | withdraw the 1.47× same-core fused tax | `Sec3_Mitigation` (table row + "60.7→89.5" sentence + "survives at a single core"), `Sec3_5`, `Appendix` | no live text asserts the tax; the withdrawal states why | **DONE** |
| 5 | re-baseline on the matched-workload result | `Sec3_Mitigation` | phase 1b's −0.795 cyc/access is the stated within-workload figure | **DONE** |
| 6 | caption the monotone table's single-workload validity | `tab:fused` caption | caption says all arms share one workload; that is what keeps it valid | **DONE** |
| 7 | disclose the hit-rate asymmetry | `app:kernel` | a reader reproducing the tax is warned | **DONE** |

## Block 2 — scoping and reconciliation (items 8–10). No machine needed.

| # | item | done means | Status |
|---|---|---|---|
| 8 | scope "prefetching well and polluting are the same decision" to far memory | the sentence names local-DRAM's ~6% (T2 B/A = 0.944/0.940) as the limit | **DONE** |
| 9 | CAT-arm instability + W5.3 any-cap MBA as ONE observation; check the CAT arm for bimodality from committed raw | a doc stating the joint finding, with the bimodality question answered from `results/clos_split/raw` | **DONE** |
| 10 | Latin square as house standard, retroactively noted | a convention note; historical fixed-order results flagged | **DONE** |

## Block 3 — broker-blocked (items 11–14). Host alive, SSH handshake resets.

| # | item | done means | Status |
|---|---|---|---|
| 11 | load + validate the reconstructed `/dev/cxl_wc` | module loaded, devices present, a read succeeds | **BLOCKED** |
| 12 | frozen-vs-rerun stability check on the WC family | E1 tax re-measured vs 1.2877/0.9996 | **BLOCKED** |
| 13 | Q4's matched-dose pair (WB 1T vs WC ~4T at ~12.5 GB/s) | a WC arm at a matched rate *with a victim* | **BLOCKED** |
| 14 | RocksDB re-earn | pre-registered, run, reported | **BLOCKED** |

Escalation attempted: direct SSH, and jump via `c4`. If both fail the block is
environmental and is recorded, not worked around.

## Block 4 — status-only (items 15–17). Cheap; close the record.

| # | item | resolution | Status |
|---|---|---|---|
| 15 | what the 31–34 cyc gap is | **closed** — it is the probe hit rate | **DONE** |
| 16 | T4 phase 2 (sub-bucket fork) | correctly **not run**; gate returned 15.9% | **DONE** |
| 17 | A4 instruction dilution | deliberately **not built**; reason registered (≈1 uop against `--no-stream`) | **DONE** |

## Rules for this session
- Paper-tree writes publish to co-authors. Never `git push` there. Record every
  paper edit in `PLAN_B_REBUILD.md`.
- Read the producing artifact end-to-end before any adverse claim (five
  retractions today, all from inferring instead of reading).
- Anything setting page-1 posture stays a `\jw{}` note for the lead.
