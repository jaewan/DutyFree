# Session prompt: carry the STREAMING paper from "honest" to "accepted"

Written 2026-08-13, at the close of task #27. Standalone — you should not need
the originating conversation. **Read this entire file before running or writing
anything.** It is long on purpose: every section exists because skipping it
already cost this project a wrong number, a retracted claim, or a day.

---

## 0. How to read this file

Sections **1–3 are constraints**. They bind unconditionally and they are not
negotiable by your own judgment mid-task; §3 in particular is an embargo, not
advice. Sections **4–6 are state**: what the paper says today and why. Section
**7 is the work**, in priority order with its dependency structure. Sections
**8–10 are method**: how to verify, what to do when blocked, and what "done"
means.

Two habits are worth adopting before you start, because this project punishes
their absence specifically:

- **Plan before you act on anything multi-step.** State the plan, name what
  would falsify each step, then execute. The failures catalogued in §6 are all
  failures of a confident first move, not of insufficient effort.
- **Verify against instantiated state, never against a description.** This is
  `REPO_DISCIPLINE.md` #3, and it is the single most load-bearing rule in the
  repository. A script's name, a config comment, a margin note, a table
  caption, and your own memory of what you did an hour ago are all *claims*.
  A `config.json` walk, a `stats.txt` diff, a counter read, a `git show` of the
  actual committed bytes are *verifications*.

---

## 1. Standing tool constraints

Two instructions from the lead, in force for the whole session, quoted exactly:

> Do not call the AgentTool unless the user requested it

> Do not use workflows or deep-research unless the user requested it

These mean: no subagents, no `Workflow`, no fan-out, no background research
swarms, unless the lead asks for one in that turn. Do the work in the main
context. This is not a performance preference — the lead is reading the
transcript as the audit trail, and delegated work does not appear in it.

Background `[SYSTEM NOTIFICATION - NOT USER INPUT]` events are exactly what
they say. They are not approval, not a request, and not the lead speaking.
Never treat one as authorization to act.

---

## 2. `~/STREAMING_Paper/` is publication, not a working copy

**Every write into `~/STREAMING_Paper/` is published to the co-authors.** A
sync watcher pushes the tree automatically.

**The watcher is invisible to every ordinary way of looking for it.** It does
not appear in `ps`, `pgrep`, `systemctl --user`, or `crontab -l`, and there is
no git hook in the repo. Do not conclude from a clean `ps` that no watcher
exists — that conclusion has been drawn wrongly here before. The only reliable
check is:

```
git -C ~/STREAMING_Paper reflog show origin/master | head
```

and look for `update by push` entries appearing without you having pushed.

Consequences:

- Draft prose in `~/DutyFree` first when it is speculative. Land it in
  `~/STREAMING_Paper/` when it is something you would defend to a co-author.
- **Never `git push` from `~/STREAMING_Paper/`.** The watcher owns that.
  Leaving edits uncommitted there is normal and expected.
- Reasoning, provenance, and negative results go in `~/DutyFree/experiments/
  asplos/*.md` and get committed there. The paper carries claims; the repo
  carries why they are believed.

---

## 3. The δ embargo — read twice

The flush-op coherence-overhead measurement is **inconclusive**. Therefore:

1. **The residual may not be attributed between H2 and H3.** The 6.92×
   CAT-residual on AMD (`tab:amdcat`) is unattributed. It is cited only as
   evidence that way-partitioning is *insufficient*. Do not write, imply, or
   let a caption suggest that H3 removes it.
2. **The 3.6 figure may not be cited without the qualifier** "upper bound,
   flush-overhead unresolved."
3. **What is *not* embargoed:** measuring flush-behind's streamer-side cost.
   That measurement is wanted (task #30). Only *attribution of the residual* is
   embargoed.
4. **A capability claim for H3 is permitted.** "Immutability licenses skipping
   coherence enrolment" is an argument from the contract, and it is currently
   the paper's central insight (§4 below). Attributing the *measured* 6.92×
   residual to H3 is not permitted. Keep the argument and the number apart.

If you find yourself writing a sentence that makes H3 look quantitatively
demonstrated on silicon, you have violated the embargo. Rewrite it as a
capability the type licenses, or delete it.

---

## 4. Where the paper stands

Location: `~/STREAMING_Paper/ASPLOS27/`. Text in `Text/*.tex`.

### 4.1 The argument, in the order the paper makes it

1. A workload class — large immutable objects read as streams — asks the memory
   system for two things at once: *prefetch me aggressively*, and *do not keep
   me*.
2. CXL makes the choice unavoidable: at +100–150 ns, demand misses sustain only
   ~4–5 GB/s per core, so only stream prefetching fills the pipe, and on x86
   prefetching well and polluting the shared cache are the **same decision**.
3. The tax follows cache **allocation**, not bytes. Same byte stream, different
   host memory type: +28% victim slowdown under WB, +0.3% under WC. The
   Intel CAT/MBA double dissociation confirms it.
4. This is a **bundled-interface** problem. Enforced non-allocation ships
   (CAT/MPAM/CBQRI) but is labelled by *execution context*; every
   address-scoped mechanism that ships is *advisory* (PREFETCHNTA, Arm
   Transient, RISC-V NTL.S1). Exactly one address-scoped plane is enforced —
   architectural memory types — and its encodings bundle the two properties a
   stream must separate. Call the empty {prefetch: yes, allocate-in-shared: no}
   entry the **missing admission cell**.
5. `Streaming` fills the cell on the shipped carrier. Contract in
   `Sec4_Streaming.tex`, `tab:contract`: OS side **I0** (uniform frame memory
   type within a coherence domain), **I1** (all CPU mappings read-only for the
   epoch); hardware side **H1** (prefetchers train and issue as for WB), **H2**
   (clean Streaming lines never enter shared LLC data arrays, neither on fill
   nor as private-cache victims), **H3** (implementations may additionally skip
   coherence-directory / snoop-filter enrolment).
6. **H3 is the surplus, and it is the paper's best idea.** Coherence machinery
   exists to find, later, every copy of a line someone is about to *write*. A
   reuse predictor observes that a line was not re-*read* — a claim about
   loads — and can therefore never justify skipping a structure that tracks
   stores. Only a declaration can. The lead's own formulation, which should
   survive every future edit: **types license coherence exemptions; guesses
   cannot.**

Do not let H3 fall out of the abstract or the introduction again. It has been
dropped twice by well-intentioned length passes, and the lead has objected both
times. If you must cut, cut elsewhere.

### 4.2 What pass 4 (2026-08-12) and pass 5 (#27, 2026-08-13) did

Pass 4 answered four defects from the lead, quoted: *"abstract and introduction
are ridiculously long,"* *"no narratives... it reads like a technical report
without high level intuition,"* *"we lost one of our point H3,"* plus the
consolidated panel review. Abstract 363→316 words, Intro 1270→1124, both net of
~130 words of restored H3, contributions 5→4.

Pass 5 propagated Gate 1: the calibration claim is **withdrawn**. Nine sites
changed. Full record in `PAPER_REVISIONS_2026-08-11.md` under "Pass 5."

### 4.3 The number that changed everything in pass 5

Re-instantiated at gem5 commit `b2c6499194`, placement verified from
per-controller counters, `ITERS=3e6`, 12/12 arms clean:

| WSS (% LLC) | alone c/i | CXL aggr. | local-DRAM aggr. | published | gap |
|---|---:|---:|---:|---:|---:|
| 1280 (25%)  | 16.31 | 1.000× | 1.000× | 1.79× | −44.1% |
| 2650 (52%)  | 33.87 | 1.368× | 1.600× | 2.57× | −37.7% |
| 5120 (100%) | 62.48 | 1.960× | 2.249× | 2.82× | −20.2% |

The model reads **39% low** against the hardware point it was said to be
calibrated to. The paper now says "hardware-**anchored**," treats every
simulated magnitude as a **lower bound**, and notes that the error's direction
is conservative for every claim the model is cited for. `tab:gem5`'s 25% row is
withdrawn; its `+H2` column carries a `‡` because **no H2 arm was
re-instantiated at the WB column's commit**.

Do not quietly re-strengthen any of this. If a future run earns a stronger
claim, it earns it with a run, at a recorded commit.

---

## 5. Rules the paper's numbers live under

### 5.1 The arm-identity rule

**Every tax figure names its arm and its operating point at the point of use.**
An arm is the full tuple: aggressor placement (local-DRAM vs CXL), victim WSS
as a fraction of LLC, host, and commit or `env_manifest` id.

This rule exists because of a real defect caught in pass 5: a CXL-latency
co-run pair at 3.14 GB/s was described as "a milder point on the same pressure
curve" as `tab:gem5`'s WB column — which is a *local-DRAM* arm. Two points on
one curve, not one measurement. Mixing arms inside a sentence is the most
likely way this paper gets a number wrong without anyone noticing.

### 5.2 The hot-set ÷ private-L2 collapse

**Four instances so far.** Before believing any null result, compute the
victim's hot working set and compare it to the *private L2*, not the LLC:

- gem5 fused hash-join null (#22, still open)
- exp41's first 4 MiB Intel attempt (EMR has 2 MiB private L2; Zen 4 has 1 MiB)
- `tab:gem5`'s 25% row: 1280 KiB victim, 2 MiB private L2 → 1.000× is *correct*
- the GAPBS sizing gate one level up

A victim resident in private L2 carries no shared-cache tax, so H2 is correctly
a no-op. That is a scope boundary, not a failure — but reporting it as a
failure, or sizing an experiment into it, wastes the run.

### 5.3 The ITERS gate

`b4run.sh` hardcodes `ITERS=3e5`. A valid cycles-per-iteration number needs
`3e6`. Check it every time; it has bitten twice.

### 5.4 Host map

| Handle | Machine | Cores | Shared cache | Private L2 | Notes |
|---|---|---|---|---|---|
| `mos181` | Intel Xeon 8592+ (Emerald Rapids) | 2×64 | 320 MiB LLC, 20 ways | **2 MiB/core** | node 2 = cpuless CXL; resctrl ✔; **also the gem5 testbed** |
| `ssh broker` = `moscxl` | AMD EPYC 9754 | 2×128 | **16 MiB L3 per CCX** | **1 MiB/core** | CXL device attribution needs re-verification per host |
| `ssh c4` = `mos182` | Intel Xeon 8462Y+ | 2×32 | 60 MB LLC | | |

The private-L2 column is there because of §5.2. Use it.

### 5.5 Building the paper

```
cd ~/STREAMING_Paper/ASPLOS27
latexmk -pdf -g -interaction=nonstopmode -pretex='\let\Bbbk\relax' -usepretex main.tex
```

- `-g` is **required**: latexmk caches failures and will otherwise report a
  stale one.
- `\Bbbk already defined` is a pre-existing collision; the `-pretex` handles it.
- **latexmk exits 12 with a completely clean `main.log`.** This is a known
  pre-existing quirk, not a failure. **Judge the build by `main.log`, never by
  the exit code**: 0 lines matching `^!`, 0 `undefined`, and a PDF whose
  timestamp moved.
- Expect to run it twice; "References changed" needs a second pass to converge,
  and the page count changes when it does.
- Current state: 17 pages total, body ends p11, references p12, appendix p14.
  **The 11-page body limit is the constraint; the appendix is free.** Check the
  boundary with `pdftotext` before believing a page count means trouble.
- `\heading{}` (`Defs.tex:66`) appends its own period. Never end its argument
  with one.
- Word counts, when the lead asks about length:
  `grep -v '^\s*%' f.tex | detex | wc -w`, compared against
  `git show HEAD:ASPLOS27/Text/f.tex | grep -v '^\s*%' | detex | wc -w`.
  Measure; do not estimate. An earlier pass "shortened" the introduction into
  being 106 words *longer* and only caught it by measuring.

---

## 6. Traps this project has already fallen into

Each of these has happened. They are listed so you recognize the shape, not so
you can admire the history.

1. **Trusting a stat name that sounds right.** `SF_Eviction` and
   `Global_Eviction` sound like the same metric. They are not: the first fires
   on every finite-SF capacity eviction, the second only when a live upstream
   copy actually existed. The paper's "11 back-invalidations" matches
   `Global_Eviction`=12, not `SF_Eviction`=3572. **Trace the `.sm` semantics.**
2. **Assuming one row's documented config applies to a table's other rows.**
   `tab:h3sf`'s margin note documents SF=65536 for the H2+H3 row *only*.
   Assuming it for the two finite-SF/no-H3 rows produced a consistent +18%
   mismatch that is still unresolved. Those rows carry a caveat in the caption;
   leave it there until a run removes it.
3. **A length pass that drops the paper's best idea.** Pass 2 lengthened the
   abstract and introduction *and* dropped H3 from both. Two of the lead's four
   later complaints trace directly to it.
4. **Republishing a re-run column beside a not-re-run column.** Pass 5's
   `‡` marker exists for this. If you re-run part of a table, mark the part you
   did not re-run — or re-run it.
5. **`cmd | tee log; echo $?` reports tee's exit code, not cmd's.**
   `REPO_DISCIPLINE.md` #8, and the fix itself had to be corrected once.
   Use `PIPESTATUS[0]`, and check your indexing.
6. **Fishing for a config that reproduces a published number.** Sweeping SF
   size to hunt for a match, with no documented target, is not reconciliation.
   When provenance is gone, say it is gone.

---

## 7. The work, in priority order

Both review panels — the consolidated panel review and *"Panel Response:
Feasibility and Burden of Proof for H1+H2 and H3"* — converge on #28 and #29 as
the two long poles. They are independent; if you can only carry one to
completion, carry #28, but #29 is cheap enough that not starting it is hard to
defend.

### #28 — Predictor head-to-head (P0, longest lead time)

**Named by both panels as the single most likely rejection reason.** The paper
argues declaration beats prediction and does not yet run a predictor.

Build the head-to-head against **SHiP**, **Hawkeye**, and **Mockingjay** in the
gem5 model, at the arms `tab:gem5` now uses. What the paper needs is not "we
win": it is the *shape* of the difference — a predictor's warm-up cost, its
mispredict pollution, its inability to offer a co-runner a guarantee, and above
all that no predictor can license the H3 exemption because it reasons about
loads while coherence tracks stores (§4.1.6).

A result where a predictor matches H2 on capacity is **publishable and must be
reported**, because the H3 argument survives it intact and the paper is
stronger for having run the comparison than for having asserted it.

Note the internal scope conflict flag on #15 (Build B finite-transaction-pool
model) before choosing a base config; resolve the lineage question once and
make one canonical config the base for both #15 and #28.

### #29 — Model-check H3 (P0, cheapest insurance in the plan)

Review 2's central structural point: **H3's burden is correctness, not
benefit.** Simulation can never establish the *absence* of a race. So:

Model-check the CHI-like protocol in Murphi or TLA+ for three properties:
1. no stale read is reachable while I1 holds,
2. the epoch-exit drain restores full coherence,
3. an I1 violation with H3 off still faults via the PTE.

Then write the **soundness taxonomy**: (a) ReadOnce / no-retention — what we
actually model; (b) epoch-tagged retention, bulk-cleared at exit; (c)
DeNovo-style self-invalidation; plus (d) the retain-but-unenrolled variant we
rated unsound internally — **include it and say why it is unsound.** A taxonomy
that only lists the sound options reads as marketing.

This is what earns H3 its place on an *argument* rather than on a number the
embargo forbids us to produce.

### #30 — Elevate flush-behind to a first-class anchor

Both panels now demand this. Flush-behind on AMD recovered **76.3% of a 6.48×
tax at full prefetch bandwidth** — it is *software-emulated H2*, and it is the
strongest possible-in-hardware exhibit the project owns. It is currently buried.

Needs the `[STREAMER COST]` measurement (streamer-side cost of flush-behind),
which is **not embargoed** — see §3.3. Add the Streaming-proxy arm. This
unlocks the §4.4 end-to-end suite.

### #31 — The feasibility writing tier (no experiments; data in hand)

Four artifacts, all writing:

- **Parts list** for a minimal H2 realization: one TLB bit sourced from the
  PTE; one attribute bit on requests and on private-line metadata; prefetcher
  inheritance of the attribute; a victim-path gate. This converts "a label
  path, not an enforcement engine" from an assertion into an accounting.
- **Precedent table**: DDIO (request-type-based constrained-way allocation,
  shipped a decade), MPAM PARTID carried through the fabric, Arm
  `PRFM PLDL1/2/3STRM`, Arm shareability domains (PTE-sourced coherence
  participation), NTA / `MOVNTDQA` fill behaviour, 4 KB prefetch boundaries.
- **Evidence ladder**, mostly already measured: (1) CAT-at-1-way on Intel — the
  stream holds 32–33 GB/s with LLC capacity cut ~20×; (2) flush-behind on AMD;
  (3) NTA / `PRFM PLDL*STRM`; (4) gem5. Plus one full-system gem5 FS run as the
  OS-and-hardware-together existence proof.
- **Near-miss matrix**: POWER WIMG-I, MIPS CCAs, resctrl pseudo-locking.

**Name the honest risk rather than waiting for a reviewer to.** On Intel, part
of the MLP lives outside the core: LLC-directed streamer prefetches are tracked
at the CHA and staged in the LLC. H2 removes that staging ground, so the
bandwidth claim rests on private MSHR/superqueue depth (~32–64) or on a
dedicated non-allocating stream/fill buffer (32–64 entries per L3 domain).
Pair it with the **risk asymmetry**: H1/H2 failure modes are performance-only —
they degrade toward the demand-miss floor, never below WC, and never toward
incorrectness.

**RTL or FPGA is explicitly *not* required.** Review 2 calls it a poor use of
the remaining time versus #28 and the end-to-end results. Do not start one.

### #32 — Ranged drain + transition-storm DoS

**This item is CLOSED and its premise is withdrawn — see "Correction —
2026-09-04" at the end of this file before drafting from it.** Baseline H2
entry performs no broadcast at all and is measured in **microseconds**; the
48 ms clean survives only as a `default n` H3 oracle. The wording below is
left verbatim per `A6.19`.

The 48 ms machine-scoped IPI broadcast at epoch entry is an **unprivileged DoS
primitive** if any process can trigger it in a loop. Write the ranged-drain
relocation (entry needs no drain under H2-only semantics — both types are
coherent cacheable, so the hazard is at exit and reclaim, off the read path)
and discuss the storm. A reviewer who finds this before we do will find it in
the worst possible way.

### Older open tasks

- **#15** Build B gem5 finite-transaction-pool model — **SCOPE CONFLICT flag
  set**; needs the lead's explicit confirmation before you spend on it.
- **#22** gem5 fused hash-join null — check §5.2 before spending anything else.
- **#25** `tab:sens` re-run — **zero provenance**, no margin note at all.
- **#26** `tab:h1bw` re-run — unbound provenance (date only). #26 before #25.

Both #25 and #26 are current-HEAD re-runs, not historical reconstructions.
**Label them that way in the paper**, exactly as pass 5 labelled `tab:gem5`.

---

## 8. Verification protocol

Before any number reaches `~/STREAMING_Paper/`:

1. It has a **commit SHA** (gem5) or an `env_manifest` id (silicon). "Measured
   2026-07" is not provenance. `GATE1_RECONCILIATION.md` is the ledger.
2. Its **arm is named** per §5.1, at the point of use, not only in a caption.
3. The config was read from **instantiated state** — `config.json`, not
   `config.ini`'s text form and not the script's stated intent
   (`gate1_manifest.py` does this walk).
4. The victim hot set was checked against **private L2** (§5.2).
5. If it is a table row and its siblings were not re-run, the siblings are
   **marked** (§6.4).
6. The claim in the prose and the number in the table **match**. Pass 5 found a
   1.34× in prose citing a 2.57× table row.

Add the reasoning to `PAPER_REVISIONS_2026-08-11.md` (or a new dated file if it
is a new campaign) and **commit it in `~/DutyFree`** — `REPO_DISCIPLINE.md` #9:
provenance goes on the commit, not in a chat message or a memory note.

---

## 9. When to stop and ask the lead

You have standing authorization for measurement, code, builds, and commits to
`~/DutyFree`. Ask before:

- **Any change to the paper's evidentiary posture on page 1.** Pass 5's
  "hardware-calibrated" → "hardware-anchored" was the lead's call, correctly.
- **Spending on #15** (the scope-conflict flag).
- **Structural surgery the panels want but the lead's length complaint
  resists** — e.g. folding §2 into §1. Genuinely in tension; not yours to
  resolve.
- **Anything touching the δ embargo's edges** (§3).

These are the lead's open decisions, surfaced and unresolved. Do not resolve
them by acting:

- **The ABI/motivation mismatch.** The paper motivates with sealed SSTables and
  Parquet — which are *files* — and Ray plasma objects, which are `MAP_SHARED`.
  The current ABI rejects both. Either land sealed-memfd + fs-DAX support, or
  rewrite the taxonomy. This is the largest unresolved gap between what the
  paper says it is for and what the prototype accepts.
- Whether to obtain an Arm server.
- Whether to fold §2 into §1.

Other outstanding items, for awareness: R7 is uncommitted in
`~/STREAMING_Paper/`; a printed `\jw{[DESIGN DECISION: drop silently vs. route
to a non-allocating fill buffer]}` marker survives at `Sec4_Streaming.tex:~92`
and must not reach submission; the RocksDB 2.33× at `Sec5_Evaluation.tex:~340`
is AMD-only, 1.00× on Intel at matched geometry, with no surviving raw data;
audit item 5 (`Sec2:60`'s 9.6×) has an unrecoverable config; `tab:appplat`
still needs microcode/stepping and the AMD CXL device attribution; **the lead
must personally send `EUNJI_QUESTION_DRAFT.md`**; neither `~/DutyFree` nor
`~/DutyFree-Gem5` has been pushed.

---

## 10. What "done" looks like for any unit of work here

Not "the number came out well." A unit of work is done when:

- the claim is stated at the strength the evidence supports and **no stronger**
  — the paper's current posture is that it under-claims deliberately, and that
  posture is an asset;
- the arm, the commit, and the operating point are recoverable by someone who
  was not in the room;
- what you did **not** do is written down next to what you did;
- a negative result is reported as a result. This project has several
  load-bearing ones. `GATE1_LOCALDRAM_COLUMN_OUTCOME.md` — *"no configuration
  in the pre-registered space reproduces the published column"* — is the model
  to imitate.

The paper's credibility is currently its strongest asset with the panels. It
was bought with retractions. Spend it carefully.

---

## Correction — 2026-09-04: #32's premise is withdrawn; do not draft the DoS framing

**Why this block exists.** This file exists to be drafted from. Item #32 above
instructs a future worker to "discuss the storm" and hands them the phrase
**"unprivileged DoS primitive"** as established fact. At the kernel tip
(`linux` branch `pr4-work`, tip `ae43f80e67`) that premise is false for
baseline H2, so acting on #32 as written would inject a security claim about a
threat the proposed mechanism does not have. Per `A6.19` the item is left
verbatim above; the superseded wording is quoted here rather than deleted:

> The 48 ms machine-scoped IPI broadcast at epoch entry is an **unprivileged DoS
> primitive** if any process can trigger it in a loop.

**Replacement:**

> Baseline H2 epoch entry performs **no cache writeback and no machine-wide
> clean** — it changes only future shared-cache admission — and is measured in
> **microseconds** (72–90 µs on QEMU/KVM; see the two-family note in
> `KERNEL_TEST_AGGREGATE_OUTCOME_2026-09-03.md`). There is therefore **no DoS
> primitive in baseline H2**: a ~10⁻⁴ s operation confined to the declarer is
> not a denial-of-service vector. The ~48 ms machine-wide `WBNOINVD` survives
> only as `CONFIG_PAT_STREAMING_H3_SEAL_ORACLE` (`arch/x86/Kconfig:1848`,
> **`default n`**), whose own help text says it is "deliberately not part of
> PROT_STREAMING's baseline H2 semantics … Do not enable it for normal H2 or
> end-to-end measurements." The availability argument is a property of a
> **default-off oracle**, not of the mechanism the paper proposes.

**Sources.** `mm/mprotect.c:894-903` keeps the global clean strictly behind
`IS_ENABLED(CONFIG_PAT_STREAMING_H3_SEAL_ORACLE)` and comments that baseline
semantics "need no cache drain". Commit `888060f6a66e` removed both the
`drain_at_exit` debugfs knob and the `streaming_drain_range()` call site; that
function is still defined (`mm/streaming.c:383`) and declared (`mm/internal.h`)
with **no caller anywhere in the tree**. Entry timings: 72–90 µs across four
committed QEMU/KVM guest boots under `data/kernel/`; 124 µs in gem5 r12
(`gem5/logs/fs_restore_chi/atomic_2cpu_w8_os_contract_r12_lifecycle/system.pc.com_1.device:9`),
which is **clock-quantisation-limited** — see the two-family note.

**The paper does not need this correction, and must not be "fixed" toward it.**
Checked today across all eleven `Text/*.tex`: the strings `DoS`, `denial of
service`, `storm`, `attack`, `adversar`, `malicious` and `threat` appear
**nowhere**. The word `unprivileged` appears exactly once, at
`Appendix.tex:669`, inside a paragraph headed "Why the **optional** entry
broadcast is conservative" whose subject is stated at `Appendix.tex:660` as
"The prototype's **H3-oracle** $\sim$48~ms entry cost", which the same
paragraph calls "**not an inherent H2 cost**" and closes with "**Removing the
broadcast from H2 closes it** for the portable path." That is correct at the
tip and correctly scoped. Four other sites say the same thing independently:
`Sec5_Streaming.tex:156`, `Sec6_Implementation.tex:55`,
`Sec6_Implementation.tex:142` and `Sec6_Conclusion.tex:23`.

**So the standing instruction for #32 is: do nothing.** The mitigation shipped;
the paper already describes the post-mitigation world. `RANGED_DRAIN_DOS_WRITEUP.md`
observed in August that "the words 'DoS,' 'unprivileged,' and 'storm' appear
nowhere in `~/STREAMING_Paper/`" and treated that as a gap to fill. **Treat it
instead as the correct end state.** Writing the storm discussion into the paper
now would motivate the design with a threat the design does not have — the
"claim stated stronger than the evidence supports" failure that §10 of this
file exists to prevent.
