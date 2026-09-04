# Agent brief: application-level e2e benchmarks for the STREAMING contract

You are working on the evaluation of an ASPLOS'27 submission.  This brief gives
you the context, the one invariant you must not violate, the apparatus that is
already staged, and the failure modes this project has already paid for.  It
deliberately does **not** prescribe your workload choices, sizing, or schedule.
Decide those, write them down before you measure, and iterate.

---

## 1. The objective, in one sentence

Produce **application-unit** measurements (queries/s, tokens/s, tuples/s, p99
latency) showing what it costs *today's shipping mechanisms* to protect a
latency-sensitive neighbour from a workload that streams immutable data --
across two or three genuinely different application domains.

## 2. Why this is the gap that matters

The paper proposes STREAMING: an OS-declared, page-granular x86 memory type
(PAT slot 6) for immutable read-only streams.  The OS side is enforced and
proven.  The hardware side (H2: never insert clean STREAMING lines in the shared
LLC) is implemented in gem5.  **Correction, 2026-09-01:** "demonstrated
end-to-end through `mprotect(PROT_STREAMING)` in full system" is true of
**mechanism engagement** (r12 gate PASS: slot-6 PTEs, 261,838 walker
translations, 118,260 HNF bypasses vs 0 in both controls).  It is **not** an
application-performance result.  `STATE_2026-08-30.md` said the path was
unconnected; that file is superseded by `STATE_2026-09-01.md`.

Everything measured so far reports **architectural** metrics -- IPC, cycles per
load, LLC bypass counts.  A reviewer's fair objection is: *"Intel CAT already
partitions the LLC.  Show me an application that cares."*  Nobody has.  Closing
that is your job.

A second, sharper finding you are helping to substantiate: **capacity
partitioning appears to be aimed at the wrong resource.**  On EPYC 9754 a way
mask restores 91.4% of the victim's L3 residency and the victim is *still 9.2x
slower*; aiming the mask changes nothing (65.1 / 65.3 / 65.1%).  In simulation,
protection is **non-monotone** in mask width -- it peaks at 8 of 20 ways and
*falls* at narrower masks, because way-starvation raises the tenant's miss
traffic more than its occupancy costs.  If that non-monotonicity reproduces on
silicon in application units, it is a strong, checkable, counter-intuitive
result independent of whether STREAMING is ever built.

## 3. The ONE design invariant

> **Every workload must contain, inside a single process, both an immutable
> stream AND a co-resident working set that benefits from cache.**

This is not a stylistic preference.  Against a *pure* stream, STREAMING and way
partitioning are equivalent -- already measured at 0.55% (model) and 0.7%
(silicon).  The entire argument is that CAT is **requestor-scoped**: it cannot
separate a stream from a working set that share a requestor ID, so protecting
the neighbour necessarily starves the tenant's own reuse.  STREAMING is
**object-scoped** and can.

A workload without co-resident reuse cannot show this and is wasted effort.
Check every candidate against this invariant before writing code.

## 4. Candidate workload families -- you choose, and justify

Ranked by how naturally they satisfy §3.  Pick **two or three**, prefer domain
diversity over depth, and say why you rejected the others.

- **LSM compaction (RocksDB / LevelDB).**  SSTables are *immutable by
  definition* and read exactly once during compaction -- the cleanest possible
  instance of the contract.  Co-resident set: the block cache and index/filter
  blocks serving concurrent reads.  Strongest fit; a real engine exists.
- **LLM decode with a KV cache.**  Past keys/values are immutable within a
  decode step and read once per token.  Co-resident set: model weights for the
  active layer.  Highly topical; note attention is usually bandwidth-bound, so
  verify the LLC actually matters at your batch/context size before committing.
- **Columnar scan / hash join (DuckDB, or the in-repo kernel).**  Fact table
  streamed once, hash table resident.  Canonical, and partially built already
  (`benchmarks/e2e/hash_join`, `--mode single`).  Lowest risk, least novelty.
- **Vector search, IVF-Flat.**  Posting lists streamed during a probe; centroids
  and the top-k heap resident.  Good fit.  Prefer IVF over HNSW: graph traversal
  is pointer-chasing, not streaming.
- **RecSys embedding lookup (DLRM).**  Weaker fit -- sparse embedding access is
  *random*, not streaming.  Only viable if you stream the training-data feed and
  keep hot embedding rows resident.  Justify carefully or skip.

## 5. What you measure, and what you cannot

**Measure, per arm:** the tenant in application units, and a co-tenant's latency
in the same window.  Arms are the mechanisms that *exist on silicon*:

| arm | mechanism |
| --- | --- |
| `wb` | baseline, no control |
| `cat<w>` | Intel CAT / resctrl, **swept across all widths** -- not two points |
| `fb<D>` | flush-behind (`CLFLUSHOPT` trailing the read pointer) |
| `nta` | `prefetchnta` / non-temporal hint |
| `wc` | write-combining pages, if you can arrange it |

**You cannot measure STREAMING.**  It does not exist in silicon.  Its number
comes from the calibrated model, and any figure combining the two must label
which platform each point came from.  Do not fake it, and do not let a reader
infer that the STREAMING point was measured on hardware.

**Sweep the full CAT range.**  This project's belief that "CAT works, it just
costs 16.7%" came from sampling exactly two widths, both of which happened to
sit inside the way-starvation region.  Two points cannot see a non-monotone
curve.

## 6. Apparatus already staged

**Host: mos182, reachable as `c4`.**  128 cores (2 x 32 x SMT2), L3 120 MiB over
2 sockets, resctrl with 15 CLOS and a **15-way** mask (`cbm_mask=7fff`), 1174 GiB
free, load 0.00, `sudo -n` works.  Pin tenant and victim to distinct physical
cores on the **same socket** (node0 = 0-31, 64-95) so you do not straddle two L3
instances.

**Do not measure on mos181** while it is running gem5 -- it currently has 14
simulator processes consuming LLC and memory bandwidth.  This project already
produced chaotic numbers once by running a diagnostic on a busy host.

**`moscxl` (`broker`)** is idle: 512 cores, AMD EPYC 9754, **32 L3 instances of
16 MiB**.  A very different cache regime, and the source of the 9.2% / 9.2x
findings.  Valuable as a *second* platform to test whether your result is
Intel-specific -- not as a substitute.  Another user is logged in there.

**Staged in `/tmp/domin_silicon_e2e/` on c4:**

    bin/cxl_join_bench   sha ff0ece4c   built native on c4
    bin/pointer_chase    sha 2bb34954   victim; needs lib/{hugepage,msr,pmu}.c and -lnuma
    scripts/resctrl_clos.sh             CLOS setup_c <ways> <scan_cpus> <probe_cpus> / teardown
    sil_e2e.sh                          runner: per-arm idle gate, mask readback, JSONL out
    cal2.jsonl                          calibration in flight

Reusable in the repo: `experiments/lib/dutyfree/resctrl.py` (schemata parsing,
integer mask comparison, `llc_occupancy`), and the runner pattern in
`benchmarks/bench/run_m12b_victim.sh`.

**Measurement floor, already established:** quiet victim 73.398 cycles/load with
0.048 spread (0.07%); tenant work deterministic (identical match counts, 0.6%
throughput spread).  Precise enough for the effects in question.

## 7. Non-negotiables

1. **Pre-register before you measure.**  A dated document stating design,
   sizing, arms, metrics, admission gates, and **falsifiable predictions with
   numeric thresholds**.  Follow `SILICON_E2E_PREREGISTRATION_2026-09-01.md`.
   If you change a threshold after seeing data, record it as a dated amendment
   that states plainly whether the change could favour the hypothesis.
2. **Gate on realized state, never on requested state.**  Read the CAT mask back
   from resctrl and compare **as integers**.  Echo realized sizes from the
   workload's own output.  A requested value reported as a fact is the single
   most repeated error in this project's history.
3. **Verify the host is idle immediately before *every* arm**, not once at the
   start.
4. **A gate that cannot fail is not a gate.**  Before trusting any check, feed it
   input that *should* fail and confirm it does.
5. **Report refutations as refutations.**  Do not reframe a failed prediction as
   a discovery.

## 8. Failure modes this project has already paid for

Read these; each cost hours.

- **`pkill`/`pgrep -f` matching its own invoking shell.**  Four occurrences.  Use
  `[p]attern`.  An idle check that matches the ssh command line containing the
  word will skip every arm and look like a busy host.
- **`CLFLUSH` is a silent no-op under gem5 Ruby/CHI** (irrelevant on silicon, but
  the *pattern* is not): a cache-control operation that appears to succeed while
  doing nothing.  Verify displacement by measurement, never by having issued the
  instruction.
- **Reading the wrong resctrl group name** returns -1 or empty, which reads as
  "unverified" and lets an unmasked run masquerade as a masked one.  The groups
  are `clos_c_scan` / `clos_c_probe`.
- **A CPU in a CTRL_MON group silently adopts that group's RMID.**  A first
  attempt at occupancy measurement read 0.0 KB for every masked arm and would
  have supported a dramatic wrong conclusion.
- **Power-of-two quantization.**  Five instances.  Hash tables that mask rather
  than divide silently round sizes up to 2x.  Report realized, not requested.
- **Killing a producer truncates its JSON**, so a whole-document parse fails and
  every reading returns null.  Parse incrementally.
- **Measuring cost before establishing efficacy.**  "CAT costs 16.7%" was
  reasoned from for two days while a measurement showing CAT does not *work* sat
  in the same repository, unread.  Ask "does it work?" before "what does it
  cost?"

## 9. Deliverables

1. A dated pre-registration per workload family.
2. A runner per workload, emitting one JSONL record per (arm, rep) with realized
   geometry, realized mask, both metrics, and provenance hashes of every binary.
3. A fail-closed analyser that prints per-prediction PASS/FAIL and refuses to
   certify on incomplete data.
4. A dated outcome document per campaign, refutations included.
5. Archived raw JSONL under `experiments/asplos/data/`, plus a regression test
   pinning the headline numbers so drift fails in `make check` rather than in
   review.

## 10. How to work

Plan first and write the plan down; you own the details.  Prefer one workload
measured properly over three measured loosely.  Land a calibration run early --
its purpose is to surface apparatus bugs, and on this project it has never
failed to find at least one.  Check in when a prediction is refuted, when a gate
turns out unimplementable, or when a result would change the paper's framing.

**Definition of done for one workload:** a reviewer can read the outcome
document and answer, in application units, *"what does it cost today's hardware
to protect the neighbour, and is that cost monotone in the knob?"* -- and can
reproduce it from the archived data and the committed runner.
