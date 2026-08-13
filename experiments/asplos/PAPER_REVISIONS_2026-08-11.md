# Staged paper revisions, 2026-08-11

Drop-in replacements for `~/STREAMING_Paper/ASPLOS27/Text/`.

**Status 2026-08-11: R1–R5 applied on the user's instruction, and the autosync
watcher committed and pushed them to Overleaf as `215f031` at 15:00:42 KST.**
They are visible to co-authors. R7 (`Appendix.tex`) was applied a few minutes
later and is still uncommitted as of this writing; it will go out on the
watcher's next cycle. R6 held (unmeasured `[STREAMER COST]`).

Builds clean at 17 pages, unchanged from pre-edit, no undefined refs or
citations. (Local build needs `-pretex='\let\Bbbk\relax' -usepretex`; that
collision is pre-existing and unrelated.)

Note for future sessions: the watcher is **not** visible to `ps`, `pgrep`,
`systemctl --user`, or `crontab -l`, and there is no git hook. Do not conclude
from a process listing that it is off — it is not. Check
`git reflog show origin/master` for `update by push` entries instead; observed
pushes on 2026-08-11 at 06:59, 07:30, and 15:00, so the cadence is not a short
fixed interval. Treat any write to that tree as publication.

**R7 was found while verifying R1 and is also applied** — see below.

Each item gives the exact original text and its replacement.

Prompted by the external positioning review of 2026-08-11. Ordered by
exposure closed per word changed. R1 is a correctness fix; R2–R3 close
falsifiable claims; R4–R6 fill holes a reviewer will notice.

Nothing here invents a measurement. Where a claim needs a number we do not
have, the text says so and the gap is listed in §"Not written".

---

## R1 — Abstract overclaims what the WC arm shows

`Abstract.tex:24`. This is audit item 4 and the review's architecture-chair
item (iii), independently. §5 explicitly refuses this claim
(`Sec5_Evaluation.tex:328-330`: *"we do not yet claim \textsc{Streaming}
erases the 6.92$\times$"*), and the source comment at `Sec5_Evaluation.tex:335`
records a panel decision not to restore it. The abstract restores it anyway by
adjacency: the sentence lands immediately after the 6.92× sentence.

**Current**

```latex
A \emph{non-allocating} stream of identical bytes removes the tax outright.
```

**Replace with**

```latex
The same bytes streamed \emph{non-allocating} remove it entirely---but only as
write-combining, which caches nowhere and disables the prefetching that
justified CXL.
```

Accurate to the measured arm (WC, 0.98×, `Sec5_Evaluation.tex:318-319`), names
the arm per the arm-identity rule, and sets up R2's missing cell instead of
undercutting §5.

---

## R2 — The scope–enforcement bind is falsified by WC and UC

`Abstract.tex:29-30` and `Sec1_Introduction.tex:67-76`.

The slogan claims no shipped cache-admission label is both enforceable and
address-scoped. **WC and UC are both.** They are PAT-carried, page-scoped,
architecturally enforced, and they govern admission. A reviewer who knows x86
memory types lands this in one paragraph, and the damage is not local: the
bind is named as the paper's second thesis.

The claim that survives the counterexample is stronger and is what the paper
actually measures: the shipped enforced/address-scoped plane offers only
*bundled* points, and the cell the workload needs is empty.

### R2a — Abstract

**Current**

```latex
The gap is structural.  Enforced non-allocation already ships (CAT, MPAM,
CBQRI), but derives its label from the execution context; every address-scoped
alternative, from \texttt{PREFETCHNTA} to RISC-V's \texttt{NTL.S1}, is a hint.
\emph{A shipped cache-admission label is enforceable when it comes from the
context and address-scoped when it comes from the instruction, never both.}
```

**Replace with**

```latex
The gap is structural, and it is a gap in the memory-type table itself.
Enforced non-allocation already ships (CAT, MPAM, CBQRI) but derives its label
from the execution context; every address-scoped \emph{hint}, from
\texttt{PREFETCHNTA} to RISC-V's \texttt{NTL.S1}, is advisory.  The one
enforced, address-scoped plane that does ship---the architectural memory
types---offers only bundled points: write-back prefetches \emph{and} allocates,
while write-combining and uncacheable do neither.  \emph{The cell that
prefetches at write-back aggressiveness without allocating in the shared cache
is empty.}
```

### R2b — Introduction

**Current** (`Sec1_Introduction.tex:67-76`, from "Conversely")

```latex
Conversely, every address-scoped
mechanism is advisory: \texttt{PREFETCHNTA}, Arm's Transient attribute, and
RISC-V's \texttt{NTL.S1}---which names our exact semantics, non-reuse ``within
the capacity of the innermost shared cache''---are all hints, and
per-instruction hints cannot label the prefetcher-generated fills that dominate
a CXL stream (\S\ref{sec:controls},~\S\ref{sec:related}).  Across three
independent ISAs the same line falls in the same place: \emph{a shipped
cache-admission label is enforceable when it comes from the context and
address-scoped when it comes from the instruction, never both}.  We call this
the \textbf{scope--enforcement bind}.
```

**Replace with**

```latex
Conversely, every address-scoped mechanism that rides an \emph{instruction} is
advisory: \texttt{PREFETCHNTA}, Arm's implementation-defined Transient
attribute, and RISC-V's \texttt{NTL.S1}---which names our exact semantics,
non-reuse ``within the capacity of the innermost shared cache''---are all
hints, and per-instruction hints cannot label the prefetcher-generated fills
that dominate a CXL stream (\S\ref{sec:controls},~\S\ref{sec:related}).

One address-scoped plane \emph{is} enforced: the architectural memory types,
written by the OS into the translation and consulted by hardware on every fill.
That is the right carrier, and it is the one we build on.  But its shipped
encodings bundle the two properties a CXL stream must separate.  Write-back
prefetches and allocates; write-combining and uncacheable do neither, which is
why reaching for them to protect a co-runner costs the streamer the prefetching
that justified CXL in the first place (\S\ref{sec:controls}).  \emph{No shipped
x86 memory type prefetches at write-back aggressiveness while declining to
allocate in the shared cache.}  We call this the \textbf{missing admission
cell}: not an absence of enforcement, not an absence of address scope, but an
absence of the single combination that separating a stream from its neighbours
requires.
```

**Then the following paragraph** (`Sec1_Introduction.tex:78-88`, "It is not a
coincidence among three design processes...") argues that the page table is an
undiscovered third carrier. Under R2 that argument is no longer needed and now
reads as contradicting the text above it — memory types already live there.
Replace its opening through "...both halves of the bind, in one carrier,
already shipped." with:

```latex
The absence is an artifact of when the pathology appeared, not of
infeasibility.  The carrier question was settled long ago: the page table is a
structure the OS writes and the fill path reads, and x86 has consulted it for
memory type since the PAT was introduced.  What was frozen early is the
\emph{encoding}---eight slots, most of them assigned, and no reason to spend one
on a type that prefetches without allocating, because the workload that needs
it did not exist until memory moved across a link.  \textsc{Streaming} therefore
asks for an encoding on a shipped carrier (\S\ref{sec:contract}), not a new
enforcement engine.
```

The page-coloring sentences that close the paragraph ("Nor is the carrier
novel..." through "...enter the shared cache at all.") still follow correctly
and should be kept verbatim.

**Knock-on edits required if R2 is taken:** `\textbf{scope--enforcement bind}`
is referred to by name elsewhere. Rename every occurrence to *missing admission
cell*, and check `Sec3_Mitigation.tex:166` (`tab:checklist`, the five-axis
table) — its axes should become the two that define the cell (prefetch
preserved × allocates in shared LLC) with the rest as columns, which is the
design-space table the review asks for.

---

## R3 — Arm Outer-Non-Cacheable is prior shipping art, not a gift

`Sec5_5_RelatedWork.tex:121-124`. This is the review's most dangerous item and
I agree with it.

The paragraph's defence is *"hints ride instructions."* That defence does not
apply to Normal Inner-Write-Back / Outer-Non-Cacheable, which rides the page
and is architecturally enforced. Calling it a "gift" invites a reviewer who
knows Arm to reclassify it as prior art doing H2, and the paragraph's closing
line — *"A label the prefetcher can see has to live on the page"* — then reads
as describing something Arm already ships.

The paper is already careful to call Arm's *Transient* attribute
implementation-defined (`Sec1_Introduction.tex:68`,
`Sec5_5_RelatedWork.tex:108-109`), which is correct and should stay. Outer-NC
is the separate, harder case.

**Current**

```latex
Two are gifts: NVIDIA's teardown
call proves an epoch-drain primitive is a reasonable ask of an architecture,
and Arm's separately specified inner and outer cacheability shows ``cache
privately, skip the shared level'' is expressible as a page attribute.
```

**Replace with**

```latex
One is a gift; one is closer than that.  NVIDIA's teardown call proves an
epoch-drain primitive is a reasonable ask of an architecture.  Arm's Normal
Inner-Write-Back, Outer-Non-Cacheable attribute is not a hint at all: it is
architecturally defined, page-granular, carried in the translation, and
enforced, and on implementations that map inner to the core-private levels and
outer to the shared level it expresses much of H2 directly.  We treat it as the
closest shipped precedent rather than a distant cousin, and state what
\textsc{Streaming} adds.  (i)~Inner/outer is a \emph{cacheability} axis, not a
\emph{shareability} one: the architecture does not require the outer point to be
the shared level, and parts with a system-level cache beyond it make ``skip the
shared level'' an implementation property rather than a portable guarantee.
(ii)~Nothing in the attribute preserves prefetching.  Whether a part keeps its
prefetchers trained and issuing under outer-non-cacheable is
implementation-defined---and that is precisely H1, the half of our contract that
could have failed.  (iii)~The attribute is static configuration, not an epoch:
it carries no immutability declaration (\emph{I1}), no revocation, and no
transition protocol, so a co-runner cannot read it as a promise about the data's
lifetime.  (iv)~It is silent on coherence enrollment (\emph{H3}).  And it has no
x86 analogue, where the bundled encodings of \S\ref{sec:intro} leave the cell
empty.  A measurement of prefetch survival under outer-non-cacheable on a
shipping Neoverse part would be the strongest available portability evidence for
H2; we have not run it.
```

Verify the exact MAIR encodings and the inner/outer shareability wording
against the Arm ARM before this goes in — cite the specific section, not the
whole manual. The claim in (i) is the load-bearing one and it is the one an Arm
architect will check.

---

## R4 — Virtualization is absent, and the motivating deployment is virtualized

Zero occurrences of hypervisor, EPT, guest, or tenant VM in the entire draft. A
paper whose scenario is a shared CXL pool is describing a cloud, and a reviewer
will ask who sets the label for a tenant. Its total absence reads as not having
considered it.

**Insert as a new `\heading{}` in `Sec4_Streaming.tex` after line 138**, i.e.
directly after the PAT slot-6 discussion:

```latex
\heading{Guests} A shared pool is in practice a virtualized one, and the label
path has to survive that.  On x86 the effective memory type of a guest access
combines the guest's own \textsc{Pat} entry with the type in the extended page
tables, and an ignore-PAT bit in the \textsc{Ept} entry lets the host disregard
the guest's choice entirely: a guest that maps a page \textsc{Streaming} gets it
only if the host agrees.  We read this as a question of authority rather than a
defect in the carrier, and the answer follows the rest of the contract---the
property being declared belongs to the \emph{data}, so the declaration belongs
with whoever owns the pool.  In the deployment we expect first, the tiering or
pool-management layer sets the type and the guest need not cooperate or even
know; a guest-issued \texttt{mprotect} is then a request the host may honour.
We have not implemented the \textsc{Ept} path, and a tenant-facing interface
that lets a guest label its own pages while remaining enforceable against a
hostile one is open.
```

---

## R5 — Name the non-inclusive victim cache

One sentence, pure gain with the architecture reviewers. H2 already specifies
*"neither on fill nor as private-cache victims"* (`Sec4_Streaming.tex:26-28`),
which is exactly right for SKX-and-later Intel parts — but the draft never says
*why* the victim clause is the load-bearing one there, so it reads as
belt-and-braces rather than as the main event.

**Append to the H2 discussion at `Sec4_Streaming.tex:49-50`**, after *"...matches
what CAT enforces by hand"*:

```latex
The private-cache-victim clause is not redundant on current Intel parts: from
Skylake-SP onward the LLC is non-inclusive and fed as a victim cache, so a
one-pass stream pollutes it almost entirely through clean L2 evictions rather
than through fills.  Declining to insert clean \textsc{Streaming} victims is
therefore the whole of H2 on that microarchitecture, not a corner case of it.
```

---

## R6 — Flush-behind is a baseline, not just an instrument

It appears once in the evaluation (`Sec5_Evaluation.tex:353`) and otherwise only
in source comments. That is untenable: on stock AMD silicon with no new
hardware it recovers **76.3%** of the tax (406.25 → 144.21 cycles/access against
a 62.66 quiescent baseline; victim-first, n=12; `benchmarks/e2e/hash_join/
AMD_CROSS_PROCESS_OUTCOME.md`). A reviewer will ask why that is not the answer,
and the paper must answer before being asked.

**Insert as a new `\heading{}` in `Sec3_Mitigation.tex` after the MBA paragraph
(after line 164), before "No deployed knob passes all five axes":**

```latex
\heading{Flush-behind: the strongest deployed alternative} The sharpest
software answer needs no new hardware at all: let the streamer allocate
normally and have it flush its own lines behind the read cursor, returning
capacity to its neighbours within a bounded window.  On AMD this recovers
[RECOVERY]\% of the tax [ARM IDENTITY], which is far more than any partitioning
knob above and enough that it must be answered rather than dismissed.  Four
things separate it from a type.  It is \emph{per-core work}: every recovered
line costs the streamer instructions and issue slots on the critical path,
[STREAMER COST].  It is \emph{tuned, not declared}: the flush distance is a
window that must track link latency, prefetch depth, and consumption rate, and
a mistuned window either flushes lines still in use or returns capacity too
late to matter.  It offers the neighbour \emph{no guarantee}---nothing in the
platform prevents the streamer from simply not flushing, so a co-runner cannot
size its own working set against it, which is the entire point of a declaration.
And it \emph{cannot reach the lines that matter most}: a flush names an address
the software has already touched, while under CXL latency the resident
footprint is dominated by prefetched lines not yet consumed, which the streamer
cannot name without defeating the prefetch it depends on.  Flush-behind is
what a streamer does when the platform gives it no word for its own access
pattern.
```

**This one is not ready to apply.** Two bracketed slots need real numbers:

- `[RECOVERY]` / `[ARM IDENTITY]` — 76.3% is measured and defensible, but the
  arm identity must be spelled out inline per the project rule (AMD `broker`,
  hash-join tenant, victim-first, 256 KiB flush distance, n=12).
- `[STREAMER COST]` — **we do not have this.** It is the streamer-side
  bandwidth/throughput penalty of flush-behind, and it is the single number
  that decides whether this paragraph is convincing. It is also one arm of the
  §4.4 frontier table the e2e session is chartered to produce. Measure before
  applying R6.

Note the δ interaction: quantifying flush-behind's *streamer-side* cost is not
embargoed. What remains embargoed is attributing its *residual* between H2 and
H3, and citing 3.6 without "upper bound, flush-overhead unresolved." The
paragraph above deliberately makes no attribution.

---

## R7 — `tab:amdcat` caption attributes the residual to H3 (embargo violation)

**Applied.** Found by grepping for the R1 phrase after applying R1: the same
overclaim had a second instance at `Appendix.tex:146`, and the caption around
it carries a worse defect.

The caption asserted the residual **is** the probe-filter/fill-path. That is an
attribution between H2 and H3, which the δ embargo forbids, and which
`Sec5_Evaluation.tex:326-330` explicitly declines to make in the body — *"if
the residual is probe-filter turnover it is H3, not H2 ... which is why we do
not yet claim \textsc{Streaming} erases the 6.92$\times$."* The appendix stated
as settled the exact thing §5 says is open.

**Was**

```latex
CAT leaves a 6.92$\times$ residual at full bandwidth (the victim's working set
fits its ways, so the residual is the un-partitionable probe-filter/fill-path),
while non-allocation removes the tax outright.
```

**Now**

```latex
CAT leaves a 6.92$\times$ residual at full bandwidth.  The victim's working set
fits its ways, so the residual is not way-capacity; whether it is
probe-filter or fill-path turnover is unresolved, and if it is, removing it
is \emph{H3} rather than \emph{H2} (\S\ref{sec:eval}).  Write-combining
removes the tax, but caches nowhere and forfeits prefetching.
```

Worth noting the failure mode: the body was disciplined and the appendix
caption was not. Captions are written once and re-read rarely, and this one
had drifted to the pre-embargo claim. The other captions carrying δ-adjacent
numbers should get the same pass.

---

## Also worth doing, smaller

- **`Sec4_Streaming.tex:86`** prints a `\jw{[DESIGN DECISION: drop silently
  vs.\ route to a non-allocating fill buffer---see source comment.]}` marker
  into the PDF body. Resolve or comment it out; an unresolved design decision
  visible in the submitted text is worse than either answer.
- **Cite resctrl cache pseudo-locking** in `Sec5_5_RelatedWork.tex` as deployed
  OS-page-plane cache control. It is the closest thing to an existing OS
  interface that manipulates admission through page mappings, and omitting it
  looks like an oversight.
- **Page-coloring lineage** — the review's suggested framing (inherits plane and
  carrier; differs in *verb*, placement vs admission; differs in *economics*,
  physical indexing vs index-agnostic-after-translation) is sharper than
  `Sec5_5_RelatedWork.tex:85-88` and is worth adopting. The existing text
  already says most of it; it is a compression, not a correction, so it is
  lower priority than R1–R5.

---

## Not written, and why

- **DB-chair taxonomy demotion** (`Sec1_5_Motivation_Internal_Doc.tex`,
  `tab:workload_taxonomy`). The review is right that KV-caches are
  append-mutated and that 1–4 KiB embedding-row gathers barely train a stream
  prefetcher across rows. But the recommended survivors are *"columnar/IVF
  scans"* and *"sealed-SSTable/compaction reads"* — and those map onto the
  RocksDB and IVF instruments, whose Intel measurements are 1.00× and 1.04× at
  matched cache geometry with no surviving AMD raw data. Cutting the taxonomy
  down to the two rows we can least defend is the wrong move. This needs the
  reuse-density sweep first; the sweep decides which rows survive, not the
  other way round.
- **Bounded-private-footprint extension to H2** (architecture chair (ii)).
  Declined. Our own diagnosis of the fused null is a hot-set ÷ private-L2
  collapse — the error that has now produced four measured nulls in this
  project, most recently `tab:gem5`'s 25% row at 1.00002× against a printed
  1.79×. Re-run the fused case with correct sizing before adding a mechanism to
  the contract to explain it.
- **Anything touching the 6.92× attribution, `tab:h3sf`, or §4.2.** Embargoed
  until δ resolves.

---

## Pass 4 (2026-08-12): the lead's four defects + panel-aligned edits

Applied directly to `~/STREAMING_Paper/ASPLOS27/Text/`. Build verified: 16
pages (was 17), 0 errors, 0 undefined refs/citations.

**Defect 1 — "abstract and introduction are ridiculously long."**
Abstract 363 -> 316 words (-12%); Sec1 1270 -> 1124 (-11%). Both figures are
*net of ~130 words of new H3 content*, so the prose cut is closer to -22%.
The cuts: the WB-yes-both / WC-no-both restatement appeared in three
consecutive intro paragraphs and again in the abstract (kept once); the two
missing-admission-cell paragraphs merged; page coloring folded into the
why-now paragraph; the CXL gather-workload enumeration dropped (Sec5 owns it);
contribution (2)'s fusion/way-partitioning explication compressed. Pass 2
(R2) had *lengthened* both sections -- that is what this reverses.

**Defect 2 — "no narratives ... no high level intuition and insights."**
The intro now runs as an argument rather than a list: two requests -> CXL
forces the choice -> the tax follows allocation -> therefore a bundled
interface -> no shipped control has the right label -> the cell is empty for
historical reasons -> Streaming fills it -> and the surplus is H3. The
essayistic connective tissue the panel flagged is gone; topic sentences now
carry the claim.

**Defect 3 — "we lost H3."** Confirmed and fixed. H3 had been dropped from
BOTH the abstract and the intro in pass 2, surviving only in `tab:contract`
and Sec4's prose. Restored in both, as a *capability* claim framed the way
panel §4.1 recommends -- H2 is the claimed portable core, H3 is the contract's
unique dividend. The argument, which is also the paper's best piece of
intuition and is new text:

> Coherence machinery exists to find, later, every copy of a line that someone
> is about to write. An epoch that promises no writer exists is a promise that
> this search will never be needed. A reuse predictor infers a line will not be
> *read* again -- a claim about loads -- while the structure whose cost it would
> have to justify tracks *stores*.

**Delta embargo respected.** The 6.92x residual is cited in contribution (2)
as way-partitioning's insufficiency and is **not** attributed to H3 anywhere.
H3's page-1 presence is a capability/contract claim, which the embargo permits;
attributing the measured residual to it is what it forbids.

**Panel items also applied.** Abstract leads with the bind, not the 6.92x
(§5). "Two vendors disagree" demoted from a standalone contribution to a
clause of (1), per §4.6's "that is a characterization finding, not a
contribution" -- 5 contributions -> 4.

### Not done, and why

- **Fold §2 into §1** (panel §5). Directly opposes defect 1; folding makes §1
  longer. The lead should pick one. Cutting §2's promotional register is
  separable and still worth doing.
- **POWER WIMG-I, MIPS CCAs, resctrl pseudo-locking** as near-misses (§4.2),
  and the near-miss matrix recast of `tab:checklist`. All add length to the
  sections just cut. Staged, not applied.
- **The figures** (§5: two-charges fill-path diagram, epoch lifecycle,
  frontier plot, MSHR sweep, tax-vs-WSS). The paper is still nearly
  figure-free. This is the largest unaddressed presentation defect.
- Everything in §7's P0 list that needs an experiment: predictor head-to-head,
  ranged drain + DoS, the two end-to-end colocated pairs, the ABI/motivation
  mismatch (sealed SSTables and Parquet are *files*; the current ABI rejects
  them).

### Flag for the lead, unedited on purpose

Page 1 still says the gem5 model is **"hardware-calibrated"** (abstract, and
contribution (4)). `GATE1_LOCALDRAM_COLUMN_OUTCOME.md` found the calibration
claim does not survive: the simulated local-DRAM point at 53% WSS is 1.600x
against the 2.61x hardware point it is said to be calibrated to, 38.7% low.
Softening that phrase changes the paper's evidentiary posture on page 1, so it
is the lead's call, not an editorial fix. It is the highest-priority
outstanding number defect in the front matter.

---

## Pass 5 (2026-08-13): task #27 — Gate 1 propagated into the paper

The lead resolved the flag above: soften the calibration claim everywhere.
Nine sites, all now edited. Source of record for every number below is
`GATE1_LOCALDRAM_COLUMN_OUTCOME.md` and the reconciliation table in
`GATE1_RECONCILIATION.md`.

### The finding being propagated

Re-instantiated at gem5 commit `b2c6499194` with aggressor placement verified
from per-controller counters (not from the command line), 12/12 arms clean,
`ITERS=3e6`:

| WSS (% LLC) | alone c/i | CXL aggr. | local-DRAM aggr. | published | gap |
|---|---:|---:|---:|---:|---:|
| 1280 (25%)  | 16.31 | 1.000x | 1.000x | 1.79x | -44.1% |
| 2650 (52%)  | 33.87 | 1.368x | 1.600x | 2.57x | -37.7% |
| 5120 (100%) | 62.48 | 1.960x | 2.249x | 2.82x | -20.2% |

No configuration in the pre-registered space reproduces the published column.
The 25% row is the fourth instance of the hot-set-fits-private-L2 collapse: at
the model's 5 MiB LLC a 25%-WSS victim is 1280 KiB, resident in the 2 MiB
private L2, so there is no shared-cache tax for H2 to remove and 1.000x is the
correct answer, not a failed measurement.

### The nine edits

**`Sec5_Evaluation.tex`**
1. `\heading{Method}` (~l.58) — "one point is *validated* rather than scaled and
   reproduces hardware within 2%" was false. Now: one point is *anchored*, the
   model reads 39% low against it, magnitudes are lower bounds.
2. Calibration prose (~l.110) — rewritten. The 1.00x +H2 column certifies only
   that the policy was implemented as written; the WB arm beside it is the one
   whose fidelity is testable, and it does not pass as a calibration. States
   1.60x vs 2.61x, 39% low, direction-and-mechanism-not-magnitude.
3. Co-run pair (~l.138) — arm-identity fix. The pair was described as "a milder
   point on the same pressure curve as tab:gem5's WB column"; that column is
   now a *local-DRAM* arm while the pair is CXL-latency at 3.14 GB/s. Named as
   two points on one curve, not one measurement.
4. (~l.415) — "the comparison no machine can perform is supplied by a model
   calibrated to within 2%" -> "supplied by a model that under-predicts the
   hardware tax it is nearest, and is therefore a lower bound."
5. Section opener (l.4-6) — "hardware-calibrated" -> "hardware-anchored...
   bounds its benefit from below."

**`tab:gem5` (rows + caption)** — 25% row withdrawn to `---{\dagger}` with the
private-L2 reason stated in the caption. WB column republished at
1.60x/2.25x bound to commit `b2c6499`. `\ddagger` added to the +H2 column:
Gate 1's 12 arms were {3 WSS} x {alone, wb} x {CXL, local} — **no H2 arms were
re-instantiated at that commit**. Printing the old +H2 values beside a new WB
column without that marker would itself be the arm-identity failure Gate 1
exists to catch. The alternative — dropping the gem5 columns — would gut the
section, so explicit disclosure was chosen over both silence and deletion.

**`Abstract.tex`** (l.37) and **`Sec1_Introduction.tex`** contribution (4) —
"hardware-calibrated" -> "hardware-anchored... bounds the benefit from below,"
with the abstract carrying the under-prediction clause inline. This is the
front-matter posture change the lead signed off on.

**`Appendix.tex`** — `tab:gem5cfg`'s `\textbf{validated}: sim 2.57x, hw 2.61x`
cell -> `anchor point: sim 1.60x, hw 2.61x`; caption rewritten to say plainly
that the row was previously described as validated and what re-instantiation
found; the "Scaling / calibration" sub-header and the intro sentence's
"validated against hardware" both retermed to anchoring.

### Why the error's direction matters, and where it is stated

The model understating the WB tax understates what non-allocation removes, so
every claim the model is cited for is bounded conservatively. That sentence
appears three times (Sec5 method, Sec5 calibration prose, appendix caption)
because each is a place a reviewer may enter the argument. It is a defence of
the claim, not of the model: the model is now explicitly not calibrated.

### Build

`latexmk -pdf -g -interaction=nonstopmode -pretex='\let\Bbbk\relax' -usepretex
main.tex`. Exit 12 (the known `\Bbbk` pretex quirk), `main.log` clean: 0
errors, 0 undefined references. 17 pages total, up one from 16 — the growth is
entirely in the appendix caption. Body still ends at p11; references start p12,
appendix p14. The 11-page body limit is intact.

### Not done here

`tab:sens` (#25) and `tab:h1bw` (#26) remain unbound-provenance re-run
candidates; neither table's text was touched, because there is no Gate 1 result
to propagate for them yet. `tab:h3sf`'s two mismatched rows already carry their
own caveat from the previous pass.
