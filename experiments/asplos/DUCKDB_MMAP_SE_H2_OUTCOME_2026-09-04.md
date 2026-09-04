# Outcome — DuckDB mmap-probe SE H2 kill-gate, 2026-09-04

**Verdict: VOID on the smoke gate. The engine-boot smoke aborted, so the full
geometry was never licensed and no arm ran. Zero of the nine registered arms
exist. `P1`–`P4` are unevaluated, not failed.**

**This is not a STREAMING negative and must not be read as one.** The
pre-registration says so in advance and in terms: "a failed smoke is **VOID**
(engine not SE-viable), not a STREAMING negative."

Pre-registration: `DUCKDB_MMAP_SE_H2_PREREG_2026-09-02.md`, frozen at commit
`bff2622`; apparatus deviation declared in its Addendum 1 at commit `f375599`
(07:26:25), **61 seconds before the smoke run's own launch banner (07:27:26)
and 34 m 23 s before the run produced its only result**. Launcher:
`run_duckdb_mmap_se.sh` (unmodified, committed at `765a1e7`). Analyzer:
`analyze_duckdb_mmap_se.py` (unmodified). Host mos181. No JSONL was written:
`data/gem5/duckdb_mmap_se_h2.jsonl` does not exist and `data/gem5/` was not
created.

Project-local date is **2026-09-04**; the host clock is KST and reads
2026-09-05. All host timestamps below are as the artifacts carry them.

---

## 1. What happened

One smoke cell was launched, as registered: `MODE=smoke`, which is
`--preset gem5-smoke` (`N=1024`, `P=8192`), arm `h2`, seed 1. It ran for
**33 m 22 s** of wall time (launch 07:27:26, exit 08:00:48 host clock) and
reached **35.42 ms** of simulated time before aborting with a gem5 `panic` and
exit code **134** (`DONE_134` = 128 + SIGABRT):

```
build_Intel_8592/mem/ruby/protocol/CHI/Cache_Controller.cc:1946:
panic: Runtime Error at CHI-cache-actions.sm:159:
STREAMING request is not a load/fetch for machine system.cpu1.l1d.
Program aborted at tick 35423497878
```

`stats.txt` is 0 bytes — the run never reached a stats dump — so there are no
counters, no `streamingHnfFillBypasses`, no `query_seconds` and no
`cyc_per_load` from this campaign at all.

### This is a deliberate protocol guard, not a crash

`CHI-cache-actions.sm:151-160`, in the sequencer-request path
(`AllocateTBE_SeqRequest`, which the backtrace confirms), reads:

```
      // STREAMING is a read-epoch capability.  Do not let a malformed PTE
      // transition, an aliasing bug, or a future privileged path turn a
      // tagged store/atomic into an H2/H3 coherence-bypass transaction.
      // Linux rejects PROT_WRITE|PROT_STREAMING, but the protocol must remain
      // safe independently of that OS invariant.
      if (in_msg.isStreamingSet() &&
          (in_msg.Type != RubyRequestType:LD) &&
          (in_msg.Type != RubyRequestType:IFETCH)) {
        error("STREAMING request is not a load/fetch");
      }
```

So the protocol fired exactly as designed. A **store** carrying
`STREAMING_BIT` arrived at the tenant CPU's L1D, and the model refuses to
define coherence-bypass semantics for it. `H2_BYPASS_COLLAPSE_2026-09-03.md`
§3 already recorded this site as "load/ifetch only; a tagged store is a hard
`error()`"; this campaign is the first to reach it.

### Why a store could carry the bit at all

The SE m5op path has no write protection anywhere in it. Tracing the three
hops:

| hop | source | behaviour |
|---|---|---|
| m5op `0x55` | `pseudo_inst.cc:624-664` `setstreaming()` | sets `EmulationPageTable::Streaming` on every page-table entry in the page-aligned range, then flushes all TLBs |
| translation | `arch/x86/tlb.cc:511` | sets `Request::STREAMING_BIT` on **any** request translating through such a page — loads and stores alike |
| protocol | `CHI-cache-actions.sm:156-159` | hard `error()` if such a request is not `LD`/`IFETCH` |

Under a full-system kernel the first hop cannot arise for a writable mapping,
because Linux rejects `PROT_WRITE|PROT_STREAMING` — which is precisely what the
source comment says the protocol must not rely on. In SE there is no such
check: `mmap_probe.cpp:241-247` maps the probe `PROT_READ|PROT_WRITE`, fills
it, and then marks it STREAMING while it is still writable. Any subsequent
store into those pages is a hard error by construction.

### Where the store came from: bounded, not identified

Two facts bound it. The tenant prints `JOIN_MEASURE_BEGIN` to `stderr` with
`std::endl` immediately after the m5op and immediately before
`gem5_reset_stats_now()`, and **that line is absent from the log**. Guest
`stderr` does reach these logs in this harness — r5's `/tmp/r5/*.log` carry
`JOIN_MEASURE_BEGIN`, `JOIN_MEASURE_END` and `JOIN_M5_EXIT` from the identical
launcher — so its absence is evidence, not silence.

The failing store therefore landed **after `gem5_set_streaming()` and before
the measured join began**, in the window containing
`register_mmap_probe(con)` and `parse_smaps()` (`mmap_probe.cpp:389-418`). The
measured query never started.

**Which store it was is not determined and is not claimed.** Localising it
needs either a `PseudoInst`/`TLB` debug-flag run or a faulting-address dump,
i.e. a new run. The pre-registration forbids debugging into a different
experiment and none was made.

### The apparatus is not at fault, and this is checkable

r5's `h2` arm used the **same** m5op declaration (`--policy stream`), the same
victim invocation (`2650 12000000`), the same one-slice 7680 KiB HNF and the
same launcher shape, and completed cleanly: `/tmp/r5/h2_s1.log` carries all
three markers and `DONE_0`. The difference between that run and this one is
the tenant. `cxl_join_bench` never writes its fact stream after marking it;
something on DuckDB's path into the probe VMA does.

---

## 2. Verdict against each registered gate, by name

| gate | verdict | evidence |
|---|---|---|
| **G-lock** | **PASS** | No process matching `atomic_2cpu_w8_fs_e2e_r6b_16g_join` at launch; launcher did not exit 2, it started and ran. Re-verified clean after exit. |
| **G0** (realized geometry) | **PARTIAL — machine half PASS, tenant half UNEVALUATED** | `l3_size_bytes=7864320` read from the smoke cell's own `config.ini`. The tenant assertions (`n=104856`, `probe=1048576`, `table_bytes=4194240`, `probe_bytes=8388608`, `keys=mod`, table/LLC) cannot be evaluated: the smoke is deliberately the wrong geometry (`N=1024`, `P=8192`) and no full arm ran. See §3 for a realized-vs-registered discrepancy G0 does **not** catch. |
| **P_complete** | **UNEVALUATED** | No arm. The smoke cell itself reached neither `JOIN_MEASURE_END` nor `JOIN_M5_EXIT`, emitted no JSON and produced an empty `stats.txt`. |
| **P_match** | **UNEVALUATED** | No `wb` and no `h2` arm to compare. |
| **P1** (H2 engagement) | **UNEVALUATED — not a miss** | `streamingHnfFillBypasses` was never sampled; the run aborted before any stats dump. This is *not* the registered `P1` VOID condition (`h2` bypasses == 0 with the run otherwise complete). It is an earlier and different failure: the run did not produce the counter at all. |
| **P2** (contention) | **UNEVALUATED** | No `cyc_per_load` for any arm. |
| **P3** (protection) | **UNEVALUATED** | R is undefined; no `qui`, `wb` or `h2` means. |
| **P4** (tenant) | **UNEVALUATED** | No `query_seconds` for any arm. |

The registered analyzer was run against the registered output path and refused,
fail-closed, as it should:

```
$ python3 experiments/asplos/analyze_duckdb_mmap_se.py data/gem5/duckdb_mmap_se_h2.jsonl
===== VERDICT =====
FAIL: no archive; no STREAMING DuckDB claim licensed
```

exit 1. No archive was fabricated to make it run.

---

## 3. Realized configuration versus registered

Read from the smoke cell's own `config.ini`
(`experiments/asplos/artifacts/duckdb_mmap_se_h2_smoke/h2_s1.config.ini`),
**never from the launcher's flags** — this is the F9 discipline and it earns
its keep twice below.

| knob | registered / requested | realized | |
|---|---|---|---|
| LLC size field | `--l3_size=7680KiB` | `size=7864320` | matches G0 |
| LLC assoc | 20 | `assoc=20` | ok |
| LLC slices | 1 | 1 HNF | ok |
| HNF TBEs | — | `number_of_TBEs=32` | one-slice pool; see §6 |
| L1D | 48 KiB / 12 | `49152` / `12` | ok |
| L1I | 32 KiB / 8 | `32768` / `8` | ok |
| L2 | 2 MiB / 16 | `2097152` / `16` | ok |
| line size | — | `cache_line_size=64` | ok |
| SF | infinite | `sf_finite=false` | ok |
| H3 | 0 | `enable_H3_streaming_bypass=false` | ok |
| DRAM latency | 98 ns | `latency=98000` ps, `latency_var=0` | ok |
| CXL latency | 203 ns | `latency=203000` ps, `latency_var=0` | ok |
| CXL pool range | 128 GiB | `137438953472:274877906944` | ok |
| memory bandwidth | `SimpleMemory` class default | **`bandwidth=2.000000` ticks/byte** | **quantised — see below** |

### Two realized-versus-requested findings, both of the F9 class

**1. `SimpleMemory.bandwidth` is quantised, as expected, and is disclosed here
rather than cited as configuration.** Both controllers realize
`bandwidth=2.000000` ticks/byte, i.e. exactly 500 GB/s, against the
512 GiB/s-class default that converts to 1.818989 — a −9.05% error.
`a5f366456e`'s `abs()` guard makes this visible, and the smoke log carries the
six `rounding error > tolerance` warnings it produces. **Those warnings are
expected and are not a gate failure**, exactly as the deviation addendum
declared in advance. They are also how `cb290444` can be told from `cfd37207`
from a console log alone, and they are present, which independently confirms
the declared binary ran.

**2. The LLC's reachable capacity is 5 MiB, not the 7.5 MiB the registration's
`table/LLC = 0.5333` is computed against.** This is derived from source, not
measured, and is labelled as such — but the derivation is exact:

- `CacheMemory.cc:111`: `m_cache_num_sets = (7864320 / 20) / 64 = 6144`.
- `CacheMemory.cc:113`: `m_cache_num_set_bits = floorLog2(6144) = 12`.
- `CacheMemory.cc:195-200`: `addressToCacheSet()` selects **12** index bits, so
  only **4096** of the 6144 allocated sets are ever addressed.
- Reachable capacity = 4096 × 20 × 64 = **5,242,880 B = 5.00 MiB**, i.e. 66.7%
  of the configured 7,864,320 B.

This is the `[F9.4]` power-of-two set-quantization defect class, at a cell that
does not appear on that class's repo-wide affected list — that list was last
enumerated in `W8.1_M5OP_IS_SE_ONLY_2026-08-24.md` as "W7 A1, and the 8-way and
12-way rows of `tab:sens`", before r5 introduced the 7680 KiB HNF on
2026-09-01. It is **not** shared with `H1BW_SINGLECORE_OUTCOME_2026-09-04.md`,
which requests a clean `5MiB` (4096 sets exactly) and is unaffected.

Consequences, stated precisely:

- **`G0` would have passed anyway, and that is the problem.** `G0` tests
  `l3_size_bytes == 7864320` and a ratio band computed against that same
  number, both from `config.ini`'s `size=` field. That field is the requested
  size faithfully recorded; it is not the reachable capacity. A gate written
  to catch requested-for-realized substitution reads a configured value here.
- **Realized `table/LLC` is 4,194,240 / 5,242,880 = 0.800**, not 0.5333.
  Realized `probe/LLC` is 1.600, not 1.067.
- **The campaign's qualitative premise survives, and strengthens.** The table
  is a large fraction of the LLC (80% rather than 53%) and the probe is larger
  than the LLC (1.6× rather than 1.07×). Nothing about the design intent
  breaks; the *number* 0.5333 is wrong as a statement about realized capacity.
- **This is inherited from r5's machine, not introduced here.** The
  registration adopts LLC 7680 KiB explicitly as "r5 machine".
  `COMPLETE_JOIN_OUTCOME_2026-09-01.md` records "HNF 7680KiB (realized
  7,864,320)", which is the same requested-for-realized reading. Handed back in
  §7; not applied to any document this campaign does not own.

Because no arm ran, **no result depends on either finding here.** They are
recorded so that whoever relaunches this campaign does not inherit them silently.

---

## 4. What the numbers are

There are none.

For completeness, and because the brief asks for them explicitly:

| quantity | value |
|---|---|
| `streamingHnfFillBypasses`, all nine arms | **not sampled** — no arm ran; the one smoke cell aborted before any stats dump and its `stats.txt` is 0 bytes |
| `query_seconds` mean, `wb` / `h2` | **none** — no arm ran |
| `cyc_per_load` mean, `qui` / `wb` / `h2` | **none** — no arm ran |
| rows/s, chrono versus `cycles`-derived | **not applicable** — the registration's ≤8% agreement rule and its labelling requirement had nothing to arbitrate |

The only numbers this campaign produced are the ones in §1 and §3: one exit
code, one simulated tick count, one wall time, and a realized machine
configuration.

---

## 5. Why this is VOID and not a negative

The distinction is the single most load-bearing thing in the pre-registration
and it is honoured here without qualification.

A STREAMING negative would be a statement of the form "H2 engaged on the
DuckDB mmap probe and did not move the neighbour or the tenant". That statement
requires `P1` to hold — the m5op reaching the HNF and bypasses being counted —
and then `P3 ≤ 0`. **Neither condition was tested.** The mechanism was never
given the chance to engage or not engage: the model refused the workload before
the measured query started.

Nor is this the registered `P1` VOID condition, which contemplates a completed
run with zero bypasses. It is a strictly earlier failure — a hard protocol
error with no counters at all — and calling it a `P1` miss would overstate how
far the experiment got.

What the smoke *was* registered to test is "whether DuckDB syscalls survive
SE". On that narrow question the evidence is genuinely encouraging and the
campaign still fails: DuckDB's dynamic loader ran, its allocator ran,
`set_robust_list`, `rseq`, `mprotect`, `madvise`, `rt_sigaction` and
`rt_sigprocmask` were all ignored by SE without incident, the engine created
table `b`, mapped and filled the probe, and executed the m5op. **No syscall
killed it.** The registration's VOID label — "engine not SE-viable" — is
therefore the right verdict but the wrong diagnosis, and the outcome is
recorded under the label the registration fixed in advance rather than under a
better one invented afterwards.

**The obvious next question is deliberately not answered here.** Whether a
`wb` or `qui` smoke completes — which would separate "DuckDB cannot run in this
SE machine" from "DuckDB cannot run on a STREAMING-marked writable mapping" —
was **not** run. The brief and the registration both forbid debugging into a
different experiment, and the registered smoke is the `h2` arm. That
separation, and any decision about a read-only or `mprotect`-paired marking
path, belongs to a fresh registration. See §7.

---

## 6. What this outcome does not license

- **No STREAMING-DuckDB sentence of any kind**, in the paper or anywhere else.
  `P1`–`P4` are unevaluated. The registration already withheld an E5 sentence
  unless all four pass *and* a later FS campaign exists; here none was even
  measured.
- **No STREAMING negative.** See §5.
- **No claim that DuckDB is not SE-viable**, despite that being the
  registration's own label for this verdict. The evidence in §5 points the
  other way and the question is open.
- **No r5 comparison**, on the two independent grounds now on record: the
  tenant's unit changed (registration), and the simulator binary changed
  (Addendum 1). r5's runs are cited in §1 only as evidence that the *apparatus*
  works, which is an apparatus claim and not a measurement comparison.
- **No CAT sweep, no flush-behind arm, no overlay on the silicon DuckDB
  +104.5% cell, no comparison of `query_seconds` to r5 tuples/s.** None was
  run, none is written, and the registration's "Do not" list is intact.
- **No conclusion about the one-slice HNF regime.** The realized
  `number_of_TBEs=32` is the same 32-entry pool that inverted the arm ordering
  in `H1BW_SLICE_BRACKET_OUTCOME_2026-09-04.md`; had the arms run, that would
  have been a live confound requiring its own treatment. It is noted, not
  resolved.
- **Nothing about the `[F9.4]` finding in §3 licenses revising a published
  number.** It is source-derived, it is handed back, and no result here rests
  on it.

---

## 7. Handbacks — not applied here

`A1_PROVENANCE_LEDGER_2026-08-28.md` and `INDEX.md` are **not edited by this
campaign**. Proposed wording for central routing:

### `A1_PROVENANCE_LEDGER_2026-08-28.md`, `F9.4` affected-cell list

> **`F9.4`, addition 2026-09-04.** The r5 HNF geometry
> (`--l3_size=7680KiB --l3_assoc=20`, 64 B lines) is a fourth affected cell and
> is not on the list last enumerated in `W8.1_M5OP_IS_SE_ONLY_2026-08-24.md`
> ("W7 A1, and the 8-way and 12-way rows of `tab:sens`"), which predates r5.
> 7,864,320 B / 20 / 64 = 6,144 sets; `CacheMemory.cc:113` takes
> `floorLog2(6144) = 12`, and `addressToCacheSet()` indexes with 12 bits, so
> **4,096 of 6,144 sets are reachable and the LLC simulates as 5.00 MiB**, 66.7%
> of the configured size. Affects every campaign adopting the r5 machine:
> `COMPLETE_JOIN_*` (r5), `FS_COMPLETE_JOIN_PREREG_2026-09-02.md`,
> `FB_ORACLE_PREREG_2026-09-03.md` and
> `DUCKDB_MMAP_SE_H2_PREREG_2026-09-02.md`. Their `table/LLC = 0.5333` is a
> ratio against a configured size; realized is **0.800**. Derived from source
> and arithmetic, **not measured** — no run emits a set count, and
> `DUCKDB_MMAP_SE_H2_OUTCOME_2026-09-04.md` §3 states the derivation in full.
> `H1BW_SINGLECORE_*` is unaffected (requests `5MiB`, 4,096 sets exactly).

### `COMPLETE_JOIN_OUTCOME_2026-09-01.md` line 21

Its "HNF 7680KiB (realized 7,864,320)" reports the configured size as the
realized one. Proposed addendum wording for that document's owner:

> `7,864,320` is the configured LLC size and is correctly read back from
> `config.ini`. The **reachable** capacity is 5.00 MiB — see `F9.4` and
> `DUCKDB_MMAP_SE_H2_OUTCOME_2026-09-04.md` §3. No r5 result is retracted; the
> table/LLC ratio 0.5333 should be read as 0.800 against reachable capacity.

### `INDEX.md` rows

> `DUCKDB_MMAP_SE_H2_OUTCOME_2026-09-04.md` — **VOID on the smoke gate.** The
> `gem5-smoke` cell aborted at 35.42 ms simulated with
> `panic: STREAMING request is not a load/fetch` — the deliberate guard at
> `CHI-cache-actions.sm:159` — so the full geometry was never licensed and
> **none of the nine arms ran**. `G-lock` PASS; `G0`'s machine half PASS, its
> tenant half unevaluated; `P_complete`, `P_match`, `P1`–`P4` **unevaluated,
> not failed**. Explicitly **not a STREAMING negative**, per the
> registration's own VOID-versus-negative rule. Cause: in SE the m5op marks
> page-table entries and `arch/x86/tlb.cc:511` stamps `STREAMING_BIT` on stores
> as well as loads, with no Linux `PROT_WRITE|PROT_STREAMING` rejection to
> prevent it; DuckDB stores into the still-writable probe VMA before the
> measured join begins. r5's `h2` arm with the same m5op on the same machine
> completes, so the apparatus is sound and the tenant is the difference. Also
> records the r5 HNF as a fourth `F9.4` cell: reachable LLC 5.00 MiB, realized
> table/LLC **0.800** not 0.5333.

### A registration decision for the campaign's owner, not taken here

Three mutually exclusive continuations exist and each needs a fresh
pre-registration; **none was started.**

1. **A `wb`/`qui` smoke** to separate "DuckDB is not SE-viable" from "DuckDB
   cannot run on a STREAMING-marked writable mapping". Cheap (~35 min) and
   answers the registered smoke question the `h2` smoke could not reach.
2. **Mark the probe read-only before the m5op** (`mprotect(PROT_READ)` after
   fill, then `SET_STREAMING`), which reproduces the invariant Linux enforces
   and which the protocol comment says the model must not depend on. This is a
   tenant change and changes what the campaign measures.
3. **Extend the protocol to define store semantics under STREAMING.** This is
   a model change with paper consequences and is far outside a kill-gate.

Option 1 is the only one that is a continuation rather than a new experiment,
and even it needs the owner's sign-off because the registered smoke was `h2`.

---

## 8. Provenance and hygiene

- **Apparatus.** `gem5.opt` `cb2904444d5c5c4d31d9d8f07295209283d29e294ef1d885d789442d98e7bbe0`
  (mtime 2026-09-04 12:51:05, `git describe` `build-cb290444-1-gfa27f665db`),
  **not** the registered `cfd37207…`; declared in advance in the
  pre-registration's Addendum 1, committed `f375599`. Tenant
  `mmap_probe.gem5` `2139aa85efb386692b14c561df27eeb6ac257d89c9acb5b6c60aa8dc636fd84b`
  and victim `1f6214b8cadb451371665e73a08ee584f5a3efb062b8ced0f9cef6fb08f6a7fd`,
  both exactly as registered. All three hashes are recorded by the launcher in
  the run log itself, not asserted here.
- **Ordering is witnessed by git, not attested.** The addendum commit
  `f375599` is timestamped **07:26:25**, the smoke cell's own launch banner
  **07:27:26** and its abort **08:00:48**. So the declaration precedes the
  launch by **61 seconds** and the result by **34 m 23 s**. The margin is thin
  and is stated as measured rather than rounded up, because the precedence
  claim is the whole point of committing first and this project has already
  been caught once reporting a "before launch" ordering that was not one
  (`H1BW_SINGLECORE_PREREG_2026-09-04.md` Addendum 1). `F16` applies as usual.
- **`gem5/src/` was not modified and `gem5.opt` was not rebuilt.** The gem5
  submodule's working tree is clean; the run wrote only into `gem5/logs/`,
  which that submodule gitignores.
- **Nothing was written under `gem5/logs/fs_restore_chi/`.** The cell landed in
  `gem5/logs/se_duckdb_mmap_h2_smoke/`, as the registered launcher specifies.
- **Artifacts.** Because the gem5 submodule ignores `logs/`, the two
  load-bearing files are preserved in
  `experiments/asplos/artifacts/duckdb_mmap_se_h2_smoke/` with a `SHA256SUMS`:
  `h2_s1.log` (`fc2df210…`) and `h2_s1.config.ini` (`66fee954…`). The
  originals remain in place.
- **No archive.** `data/gem5/duckdb_mmap_se_h2.jsonl` was not written and
  `data/gem5/` was not created, per `A6.19` — archiving is licensed only after
  9/9, and 0/9 completed.
- **Two dependencies are deliberately left uncommitted, as their owners'
  state**, following the precedent in `H1BW_SINGLECORE_OUTCOME_2026-09-04.md`
  §7 finding 4. `experiments/lib/archive_gem5_runs.py` carries an uncommitted
  extension parsing this campaign's tenant JSON, which the registration's
  analysis plan names; it is a shared file whose same diff also carries
  `join_mtuples_per_s` / `fact_bytes_bind` fields belonging to the r5
  complete-join campaign, it was uncommitted before this campaign began, and it
  was **never run** here because there was no completed arm. The tenant tree
  `benchmarks/e2e/duckdb_mmap_probe/` is untracked for the same reason. This
  campaign's dependency on both is pinned by the tenant binary's sha256 rather
  than by committing another worker's in-flight work.
- **Runtime.** One cell, 33 m 22 s wall, ~1.3 MB of artifacts. The nine-arm
  budget was not spent.
- **The `G-lock` self-match trap fired once, on the diagnostic and not on the
  launcher.** A shell command containing the literal string `gem5.opt` inside
  an `echo` was matched by its own `grep` of a process snapshot, reporting a
  simulator that did not exist. This is the same mechanism the brief warned
  about for `pgrep -f` and `r6b`. The fix used thereafter, and worth adopting:
  write the `ps` snapshot in one command and search it in a **separate** one,
  so the searching process's command line is not in the file it searches.
  `G-lock` itself never fired: the launcher started, which it does not do when
  the lock is held.

---

## 9. One line for anyone drafting from this

A paper may say **nothing** on this evidence about STREAMING and DuckDB — not
that it helps, not that it does not, not that the engine is or is not viable
under SE. The campaign registered a kill-gate, the gate closed before the
measurement, and the only publishable content is that it closed and why.
