# Gate 1: config reconciliation

Dated 2026-08-09, in progress. Deliverable per spec: one table, rows =
the five published tables, columns = producing commit / tab:gem5cfg claim
/ instantiated actual / verdict (match / text-fix / re-run).

## Tooling: `gate1_manifest.py`

Post-instantiation walk of `config.json` (never `config.ini`'s text form
or a script's stated intent) → JSON: LLC size/assoc, replacement policy
+ its actual parameters (not just class name — see the BRRIPRP/RRIPRP
lesson from Gate 0), prefetcher class+degree per level, MSHRs, HNF
controller `sf_finite` state, core count, memory-controller latencies,
cache line size — plus commit SHA, dirty-tree flag, command line, and
relevant env vars. Two type-name bugs found and fixed by checking
`config.json` directly rather than guessing gem5's internal class names
(`O3CPU` → actually `BaseO3CPU`; `CHI_HNFController` → actually
`CHI_Cache_Controller`) — the exact "verify, don't guess" discipline this
whole gate exists to enforce, applied to my own tooling before trusting
its output.

## First result (interim — one config, not yet tied to a specific
## published table's producing commit)

Ran `gate1_manifest.py` against `b4run.sh`'s `alone` config on the just-
unified `streaming` HEAD (`23f27375e9`). This is the same `COMMON` config
string shared by the `alone`/`wb`/`st` tags (only the aggressor/workload
differs), so it's informative for all three, though not yet validated
against whichever *older* commit actually produced each published number
— that's what commit archaeology (below) is for.

**LLC sizing**: exactly one `system.ruby.hnf.cntrl.cache` node, `size:
5242880` (= 5 MiB exactly), not duplicated per core. **Confirms the LLC
is genuinely shared at 5 MiB for a 2-core run on this config** — matching
the paper's `tab:gem5cfg` claim, not Eunji's "5 MiB per core / 10 MiB
total" description.

**Prefetchers**: `system.cpu0.l1d.prefetcher` is a `MultiPrefetcher`
containing `prefetchers0 = StridePrefetcher(degree=4)` and
`prefetchers1 = DCPTPrefetcher`. **This matches Eunji's "stride(4)+DCPT"
description exactly — not the paper's stated "L1/L2 stream" prefetcher.**

**This is not "paper right, Eunji wrong" or the reverse — it's a genuine
split.** LLC sizing tracks the paper's claim; prefetcher configuration
tracks Eunji's. Whatever produced the original published tables, it did
not match `tab:gem5cfg`'s prefetcher description on at least this
dimension, at least on this run's config/commit. This sharpens exactly
the question in the Eunji draft email (`EUNJI_QUESTION_DRAFT.md`) and
raises its stakes — her answer now needs to explain not just "which
config" but "why does the LLC-sizing claim and the prefetcher claim not
travel together."

**HNF `sf_finite`**: `False` for `system.ruby.hnf.cntrl`, matching the
`HNF_SF_FINITE=0` default — confirms this specific run used infinite SF,
as expected for the `alone`/`wb` baseline tags (not `h3sf`-specific).

**Memory latencies**: two `SimpleMemory` controllers, 98000 ps (98 ns,
local DRAM) and 203000 ps (203 ns, CXL) — both correctly instantiated
per the `--dram-latency`/`--cxl-latency` flags, confirming the
dual-latency-backend model is live at the memory-controller level, not
just requested on the command line.

## Streaming-path smoke-test (Gate 0 follow-up, in progress)

Per the panel's flag that Gate 0's smoke test only covered the
default/WB path, not the enforced `setstreaming` route behind the co-run
pair: running `b4run.sh <name> st 0 0` at both the pre-merge SHA
(`00fca787bd`, binary backed up at `/tmp/gem5_baseline_streaming.opt`)
and post-merge (`23f27375e9`) to diff `stats.txt` on this path
specifically. Result pending.

## Commit archaeology: done, via the paper's own `\jw{}` margin notes

Source: `~/STREAMING_Paper/ASPLOS27/Text/Sec5_Evaluation.tex`. Every
`\jw{}` note in the section was enumerated, not just grepped for the one
known pattern.

**Correction to the original task framing first**: "tab:gem5" and "the
2-core co-run pair" are almost certainly **the same experiment, not two
separate tables** — the co-run-pair prose (`\emph{Cross-core
co-runner}`) sits immediately before `\label{tab:gem5}` and describes
exactly the WB/+H2 columns the table reports. Treating them as one row
below; flag for confirmation before finalizing, but there is no second,
distinct co-run-pair table visible in this section.

| Table | Provenance found | Commit SHA | Verdict on provenance |
|---|---|---|---|
| **tab:h1bw** | "Measured 2026-07: go/no-go PASS." Date only. | **none** | **incomplete — auto re-run candidate** |
| **tab:gem5** (= co-run pair) | "Measured 2026-07 (x\_alone/x\_wb/x\_st)." Date + script-name pattern (note: `x_*`, not `b4run.sh`'s own naming — possibly an older/renamed harness). | **none** | **incomplete — auto re-run candidate** |
| **tab:h3sf** | "Measured 2026-08-03, c3 commit `0102eee441` (b4b\_\* at SF=65536)." | **`0102eee441`** | **complete** — the only fully-bound table. Carries its own honest-gap caveat already: *"Do not overclaim the 1.05x recovery without [a bandwidth-matched H2-vs-H3 control]."* |
| **tab:sens** | **No `\jw{}` note anywhere near the table** (checked the full margin-note list for the section, not just nearby text) — the note at line 557 that looked adjacent is attached to `tab:amdcat` (AMD **hardware**, not gem5), a different table entirely, easy to misattribute at a skim. | **none** | **zero provenance — most urgent re-run candidate** |
| tab:amdcat (context, not gem5, not in Gate 1's scope) | "Measured 2026-07 on broker (EPYC 9754)... n=3. Files: `~/tmp_dutyfree_exp/H3_GATE_RESULT.md`." | n/a (silicon, not gem5) | has its own honest caveat already (WC/WB not bandwidth-matched) — out of scope here |

## A genuine prose/table numeric discrepancy, located precisely

The prose citing `tab:gem5` says, in **two places** (lines 241 and 434):
*"H2 returns a co-resident victim to 1.02$\times$ from a 1.34$\times$
tax (94% recovered)... (\cref{tab:gem5})"*. But `tab:gem5`'s own 53%-LLC
row — the row this prose is describing (53% LLC is the config called out
explicitly at line 245's margin note) — reports **WB = 2.57$\times$**,
not 1.34$\times$, and **+H2 = 1.00$\times$**, not 1.02$\times$. Neither
prose number matches the table it cites.

**This is the exact "1.34 vs 2.57/2.03" anomaly the panel flagged as
already-known and already gated behind Gate 2's conditional re-run** —
now pinned to exact line numbers and confirmed as a real, in-text
citation mismatch, not a garbled paraphrase on my end. Two
possibilities, not yet distinguished: (a) the prose's 1.34x is simply
stale (an earlier run's number, never updated when the table was
refreshed) and should read 2.57x/1.00x; or (b) the prose is genuinely
describing a *different* run/config than what's in the table (e.g. a
different WSS point, or the pre-Gate-0 vs. post-Gate-0 lineage split),
and `\cref{tab:gem5}` is the wrong cross-reference. Gate 2's pre-
registered discriminating re-run (10 MiB actual vs. 5 MiB shared behind
the co-run pair) is exactly the test that disambiguates this — if the
co-run pair actually ran at a 10 MiB LLC, a 1.34x WB tax at that larger,
less-pressured cache is far more plausible than at a genuinely-shared
5 MiB one, which would explain the prose number without either being a
typo.

## tab:h3sf re-instantiation at `0102eee441` (Session A, complete for the H2+H3 row)

Ran the H2+H3 config (`HNF_SF_SETS=8192 HNF_SF_WAYS=8` → SF=65536,
`SFF=1`, `H3=1`) in an isolated worktree at the actual producing commit,
per the ruling that this is the one table eligible for faithful
historical re-instantiation. Both published numbers for this row
confirmed:

- **Tax**: 1.0526x vs the paper's claimed 1.05x. Match.
- **Back-invalidations**: the paper's "11" does **not** correspond to
  the obvious `SF_Eviction::total` counter (3572 in this run) — that
  stat fires on every finite-SF *capacity* eviction, whether or not an
  upstream sharer actually existed to invalidate. The correct match is
  `Global_Eviction::total` = **12**, a distinct CHI-cache-actions.sm
  event (`Initiate_Replacement_Evict_BackInvalidte` /
  `Local_Eviction` + "back-invalidate line in all upstream requesters",
  per the `.sm` source's own `desc=` strings) that only fires when the
  evicted SF entry actually had a live upstream copy to invalidate.
  Off by 1, well within re-run noise. **Another instance of Gate 0's
  own lesson (REPO_DISCIPLINE.md #2's corollary): don't trust the
  stat name that sounds right, trace the actual `.sm` semantics** —
  `SF_Eviction` and `Global_Eviction` sound like they could be the same
  metric and are not.

Remaining tab:h3sf rows (WB infinite-SF 1.22x, WB finite-SF 2.53x, H2
2.55x/3683-back-inval per the paper) not yet re-instantiated — only the
H2+H3 row has been tested so far. Queued behind Session B per the user's
ordering.

## Still to do

1. ~~Commit archaeology~~ **done** (see above) — 1 of 4 tables (h3sf)
   fully bound; 2 (h1bw, gem5) have a date and partial script-name but
   no commit SHA; 1 (sens) has nothing. Per the rule, h1bw/gem5/sens all
   go on the re-run list regardless of what config reconciliation shows,
   since "cannot identify the producing commit" is itself the failure
   condition, independent of whether the *current* tree's config happens
   to match.
2. **Re-run each of h1bw/gem5/sens at current `streaming` HEAD.**
   **gem5 (= co-run pair): done** — see `table-corun-v2` above and
   `GATE1_CORUN_PAIR_PREREGISTRATION.md`. h1bw and sens remain, in that
   order per Session B. **Searched for the
   `x_alone/x_wb/x_st` scripts specifically — not found** anywhere
   accessible (checked `STREAMING_Paper`, `DutyFree`, broad filesystem
   search for the name pattern). Given `b4run.sh`'s own tag values are
   exactly `alone`/`wb`/`st`, it is very likely the renamed/evolved
   successor to the `x_*` scripts, but this is inference, not proof of
   byte-identical config — a historical reconstruction of the *exact*
   original run is not possible without the actual script or a commit
   SHA. Re-runs against h1bw/gem5/sens are therefore **current-HEAD
   re-runs**, not historical reconstructions — label them as such in the
   final reconciliation table and in any paper-text update, not as
   reproductions of the original measurement.
3. **Re-instantiate tab:h3sf at its actual producing commit
   (`0102eee441`)** specifically — this is the one table where a
   faithful historical re-instantiation is possible and should be done
   before trusting its current-HEAD numbers, rather than defaulting to
   a fresh re-run.
4. **Eunji's answer** on which checkout/commit her description came
   from — sent, pending reply (`EUNJI_QUESTION_DRAFT.md`).
5. Resolve the lineage question once (2)-(4) are in: one canonical
   config becomes the base for Build B and the head-to-head.

## Reconciliation table (live)

| Table | Producing commit | tab:gem5cfg claim | Instantiated actual | Verdict |
|---|---|---|---|---|
| tab:h1bw | **unbound** (date only) | TBD | TBD | **re-run** (provenance) — next up, Session B |
| tab:gem5 (= co-run pair) | **unbound** (date + `x_*` script names only) → superseded by current-HEAD re-run, tag `table-corun-v2`, commit `a309523389` | 5 MiB shared LLC, L1/L2 stream PF, prose cites 1.34x/1.02x via `tab:gem5` | LLC: 5 MiB shared (confirmed); PF: stride(4)+DCPT (contradicts `tab:gem5cfg`'s claim, matches Eunji); WB tax **1.2189x**, H2 tax **1.0532x** at the mild-pressure (53% LLC, CXL-latency aggressor, 3.14 GB/s achieved fill) operating point — see `GATE1_CORUN_PAIR_PREREGISTRATION.md` | **superseded (`table-corun-v2`)** — 1.34-vs-2.57 anomaly closed as two operating points, not a bug; cross-reference at lines 241/434 needs fixing, not the numbers |
| tab:sens | **unbound** (no note at all) | TBD | TBD | **re-run** (provenance, most urgent after h1bw) |
| tab:h3sf | `0102eee441` | H2+H3: 1.05x tax, "11" back-invalidations (finite SF, SF=65536) | H2+H3 tax **1.0526x** (10,683,852 / 10,150,199) — matches; back-invalidation count: `Global_Eviction::total` = **12** (not the raw `SF_Eviction::total`=3572, which is finite-SF *capacity* evictions regardless of whether an upstream sharer existed to invalidate — `Global_Eviction` is the CHI-cache-actions.sm event specifically gated on "back-invalidate line in all upstream requesters", the correct match for the paper's stated metric) — matches within 1 | **match** — both published numbers for this row confirmed at the faithful producing commit |
