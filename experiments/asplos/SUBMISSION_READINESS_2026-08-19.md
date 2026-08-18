# Submission readiness: what is proven, what is left, and who owns it

Written 2026-08-19 after a fresh read of every section. Three parts: the paper
update just applied, the remaining work split by team, and the evidence matrix.

---

## Part 1 — What the paper update needed (and did not)

Two of the second-pass review's three conditions were **already met**, recorded
here so nobody re-does them:

- Sec1 contribution (4) already attributes cost to the prototype and benefit to
  the model.
- `Sec5:43` already gives the reason hardware cannot show the benefit: the
  repurposed PAT slot decodes to WB, so the prototype validates enforceability
  and transition cost only.
- `Appendix:319` already discloses that SHiP cannot attach to a Ruby cache
  without a core port, and that Hawkeye and Mockingjay are absent.

What was missing: the abstract carried the *categorical* anti-predictor argument
but not the *measured* one. Added — "a tuned reuse predictor recovers none of a
co-runner's tax; it can decline to retain a line, never to admit it." Abstract
is now 342 words against the 316 pass 4 cut it to; going lower means cutting
content the lead chose to keep.

**One update still worth making, not applied:** the conclusion asks "should the
drain be ranged or epoch-deferred?" and `Sec5` says a production ISA "wants a
bounded, ranged drain primitive." A ranged drain now exists in the prototype
(PR #3, boot-tested). The honest revision is "we implement the ranged variant;
whether reclaim-time deferral beats it is open" — but its *benefit* is
unmeasured, so the sentence cannot yet be strengthened beyond that. Deferred
until the measurement below lands.

---

## Part 2 — What is left, by team

### OS / kernel team

1. **Measure the ranged drain on real hardware.** *(highest value on this
   team's list.)* The mitigation is merged and boot-tested in QEMU; its benefit
   is unmeasured because QEMU cannot reproduce WBNOINVD cost. Needs the patched
   kernel booted on the measurement host. Deliverables: entry cost becomes O(1)
   in machine size, exit scales with object size, revised break-even. This is
   exactly the figure deleted from `Sec5` as a TBD, and it converts a disclosed
   weakness (the unprivileged 48 ms DoS) into a result.
2. **Object-scoped I0 / multi-mapper sealed memfd.** Designed
   (`REVIEWER2_RESPONSE_2026-08-19.md` Q3), unstarted. Without it Plasma's
   multi-reader case — the closest fit to the motivation — does not run. The
   hook is easy (`shmem_mmap` has inode, seals, vma; `seal_check_write` already
   refuses writable shared mappings). The work is the **object lifecycle**:
   per-mapping revocation would violate I0, so the type must persist for the
   object's life, which moves the drain to inode eviction where there is no
   mapping to walk — flush must iterate `address_space` folios, with THP and
   swap in scope. Plus a selftest.
3. **Decide fs-DAX.** Currently rejected and disclosed. Either leave it stated
   or narrow the motivation further; not a coding task.
4. **EPT / guest path.** Not implemented, disclosed in `Sec4:199`. Leave for
   this submission.

### gem5 team

1. **Variance.** No gem5 number in the paper has an interval. `SEED` is *not*
   the lever — a fixed-seed control still drifted 0.047%, the same magnitude as
   the cross-seed spread, so runs are not bit-reproducible under randomisation.
   The mechanism is **repeated identical runs**. Any magnitude the paper cites
   needs one.
2. **Sweep Q1.** The cross-core predictor result is one victim size, one stream
   size, one predictor, single runs. Sweep victim WSS across the protectable
   window (>2 MiB private L2, ≤5 MiB LLC — note `--hot-bytes` quantises to
   powers of two, so 4 MiB is the only interior point at that granularity; the
   chase victim takes KiB and is not so constrained).
3. **H2 under-enforcement.** Fill suppression is prefetch-mediated and falls
   77.3% → 57.2% as `L1_MSHR` goes 16 → 64; with prefetchers off it is
   invariant at 44.0%. The direction is conservative (the model *understates*
   H2), so nothing published is invalid, but it should be fixed or bounded.
   Localised to prefetch-filled lines not carrying the STREAMING attribute into
   their private-cache entry; the exact line needs a protocol trace.
4. **`tab:h3sf` archaeology.** Two middle rows re-instantiate ~18% high and no
   counter reproduces the 3,683 back-invalidations; the documented 65,536-entry
   SF likely does not apply to them. Either re-derive with a documented geometry
   or keep the caveat.
5. **SHiP port** (~6 call sites in core gem5) *only if* a reviewer demands a
   signature-based predictor. The structural admission argument does not need it.
6. **One full-system run** as the OS-and-hardware-together existence proof.

### End-to-end benchmark team

1. **The §4.4 frontier / Streaming-proxy arm.** #30's expensive half: real
   application streamer cost (GAPBS + DuckDB), still unmeasured. The synthetic
   aggressor's self-cost is *not* a substitute and the repo says so.
2. **RocksDB provenance.** 2.33× is AMD-only, 1.00× on Intel at matched
   geometry, with no surviving raw data. Re-run with provenance or drop the
   number.
3. **`tab:appplat`** needs microcode/stepping and the AMD CXL device
   attribution.
4. **Arm / Neoverse.** `Sec5_5:148` names a measurement of prefetch survival
   under outer-non-cacheable on a shipping Neoverse part as "the strongest
   available portability evidence for H2; we have not run it." Needs hardware —
   a lead decision, not a task.

---

## Part 3 — Evidence matrix: what must be proven to make the claims scientific

| # | Claim | Required evidence | Status |
|---|---|---|---|
| C1 | The tax follows allocation, not bytes | dissociation holding bytes fixed | **DONE, silicon.** WB +28% vs WC +0.3%; CAT/MBA double dissociation |
| C2 | Object scope is *necessary* | a case context scope cannot express | **DONE, silicon.** Fused kernel: 1.47× same-thread tax, one context label; restructuring costs 36% |
| C3 | Capacity control is *insufficient* | a residual surviving way-partitioning | **DONE, silicon.** 6.92× residual under CAT on AMD |
| C4 | The contract is enforceable | a working OS implementation | **DONE.** Linux 6.8 prototype, KUnit + kselftests, boot-tested; sealed memfd merged |
| C5 | H2 protects a co-runner | victim recovery with the stream declared | **SIMULATION ONLY.** 1.655×→1.012×. Cannot be shown on silicon: the PAT slot decodes to WB. Proxy: flush-behind recovers 76.3% on AMD |
| C6 | Prefetch survives non-allocation (H1) | bandwidth not collapsing to the WC floor | **SIMULATION.** MSHR sweep; ordering claimed, not magnitude |
| C7 | Declaration beats prediction | a predictor failing where the type succeeds | **DONE (sim) + structural.** Cross-core: predictor recovers −2.4%; admission precedes retention, so not an accuracy gap |
| C8 | H3 is *sound* | absence of a race — unprovable by simulation | **DONE, correctly.** TLA+ check of 3 properties + soundness taxonomy incl. the unsound variant |
| C9 | H3 removes pressure H2 cannot | SF-pressure separation | **PARTIAL.** `tab:h3sf`; 2 of 4 rows unresolved at +18% |
| C10 | The cost is bounded | transition cost and break-even | **PARTIAL.** 48 ms measured on silicon; mitigation implemented but **unmeasured**; break-even unfavourable at the evaluated 1 GB epochs (44% / 17%) |
| C11 | It ports across vendors | the mechanism on a second ISA | **PARTIAL.** AMD demonstrated for the tax and flush-behind; Arm unrun |
| C12 | The motivating workloads can use it | the artifact accepting the motivating carrier | **NOT DONE.** Object-scoped I0 missing; files unsupported. Disclosed, not closed |

### How to address what remains

**C5 is structural and will not close before submission.** The silicon cannot
express the benefit. The correct response is the one now in the paper: frame
gem5 as a lower bound, name flush-behind as the silicon proxy, and state the
PAT limitation where the claim is made. A reviewer who accepts that framing has
no further complaint; one who does not is really objecting that the mechanism
needs silicon, which no amount of writing fixes.

**The fixable-before-submission set, in priority order:**

1. **Intervals on every cited gem5 magnitude** (gem5 team, cheap). This is the
   most-quoted methodological objection and it is pure compute.
2. **Ranged-drain measurement on hardware** (OS team). Converts C10 from
   "disclosed weakness" to "result" and restores a deleted figure.
3. **Q1 sweep** (gem5 team). Turns the paper's best new result from one point
   into a curve, which is what a reviewer will ask for.
4. **Object-scoped I0** (OS team). Closes C12, the last place the paper promises
   something the artifact cannot do.
5. `tab:h3sf` archaeology and RocksDB provenance (both teams) — debt cleanup,
   not new claims.

Items 1–3 are compute and one machine reboot. Item 4 is days. Item 5 is
bookkeeping. Nothing on this list requires a new idea, which is the right place
to be.
