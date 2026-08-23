# Design: OLTP index as the headline e2e victim

Dated 2026-08-23. Written before any code and before any measurement.

This is a **design and gate pre-registration**. The campaign pre-registration
is deliberately deferred: gates G1--G4 below decide whether this victim is
admissible at all, and freezing campaign parameters before they run would be
exactly the selection hazard §6.6 forbids.

---

## 1. Why this victim, stated as a mechanism rather than a preference

The project's own decomposition says the tax is not mostly capacity:

| gem5, finite SF at 65,536 entries | tax | victim L1 `SnpCleanInvalid` |
|---|---:|---:|
| WB aggressor, **infinite** SF (capacity only) | 1.369x | 1 |
| WB aggressor, finite SF | 2.501x | 36,800 |
| H2 (LLC-data bypass), finite SF | 2.512x | 37,109 |
| H2+H3 (also skips SF enrolment), finite SF | **1.061x** | **25** |

Capacity is 1.369x. The remainder is **back-invalidation of the victim's
private L1/L2**, and H2 alone does not touch it (2.501 -> 2.512). Independently,
A4 shows 7 threads re-reading an already-resident shared buffer at 0.3% of full
bandwidth -- essentially zero new memory traffic -- taxing the victim 1.248x
[1.236, 1.275], and **1.298x with CAT 8/8 applied**.

Two consequences follow, and they define the victim:

1. **The dominant charge lands on private caches.** So the ideal victim keeps
   its hot set in the **private L2** and re-hits it constantly, so that every
   SF-forced back-invalidation costs a full refetch.
2. **CAT partitions LLC ways and nothing else.** It does not partition the
   snoop filter, the L3 lookup port, or the miss queue. A victim of type (1) is
   therefore one that **CAT structurally cannot protect** -- which is the L5
   claim, expressed as a property of the workload instead of as an argument in
   the related-work section.

An in-memory OLTP index has exactly this shape: interior tree nodes are small,
traversed by every single operation, and reached by strictly serialized
dependent loads with almost no software work between hops.

### The admission criterion this changes

The CAT capacity-sensitivity gate used for GAPBS and HNSW admits a victim when
masking its own LLC down costs it >= 2x. That selects for **LLC-capacity-
sensitive** victims -- i.e. for the 1.369x charge, and away from the 2.501x one.
A victim whose hot set is L2-resident is invisible to LLC masking and will
**fail** that gate while being maximally exposed to the charge Streaming
uniquely removes.

HNSW is the worked example. It failed on all three hosts (1.257--1.544x). Under
the capacity reading that is a rejection. Under the mechanism above it is
evidence that its hot set is private-resident. The gate was answering a
different question than the one we care about.

**This design therefore runs the old gate as a control and predicts it will
fail** (G3), and admits on a new gate, CAT-isolated residual (G4). Changing the
project's admission criterion is a §9 structural decision and is flagged as one
in §9 below; nothing here presumes it.

---

## 2. Workload

### 2.1 Index: Masstree, single-threaded

`masstree-beta` (github.com/kohler/masstree-beta), pinned to a commit recorded
at setup time. Chosen over the alternatives for reasons, not familiarity:

| candidate | why not |
|---|---|
| **Silo** (OCC + TPC-C over Masstree) | Adds OCC validation and logging *per transaction*. That is software work between hops -- the exact dilution that made RocksDB a null (~7000 cycles/lookup, of which 32% turned out to be assertions). More "real" is not better when the added realism hides the latency we are measuring. Optional escalation only, per §7. |
| **DBx1000** | Architecture-community standard, but its default `IDX_HASH` index is a *single* hop, which destroys the dependent-chain property. `IDX_BTREE` would work; the build is simpler than Silo's. Held as fallback. |
| hand-rolled B+tree | Not defensible as "a real application" on its own. But see §2.3 -- it has a specific, legitimate role. |

**Driver: uniform-random point lookups**, not Zipfian, as the primary. Uniform
keeps the interior nodes 100% hot (every lookup traverses the root and upper
levels) while leaving the leaves cold -- which is precisely the hot-interior /
cold-leaf structure the mechanism needs. Zipfian would concentrate the leaf
working set too and make the victim more resilient. A Zipfian arm is a
secondary, reported as a locality sensitivity, never as the headline.

### 2.2 Sizing, derived rather than guessed

Masstree interior nodes are ~256 B with fanout ~15. For an interior set of
size `I` bytes the key count is roughly `N ~= 15 * (I / 256) * 15`.

### Verified topology, 2026-08-23, all three hosts

Every value below was read from `/sys` and `numactl -H` on the host, not from
the §2 table in `../E2E_SESSION_PROMPT.md`, **which is wrong** -- it records
`mos182` as having no CXL, and `mos182` has a cpuless 256 GiB node 2.

| host | CPU | private L2 | shared, per core | ways | MiB/way | node 2 | CXL near socket |
|---|---|---|---:|---:|---:|---:|---:|
| `mos181` | Xeon 8592+ (EMR), 2x64 | 2 MiB, 16-way | 320 MiB LLC | 20 | 16.0 | 258033 MB | **0** (d=14; 1->2 = 24) |
| `mos182` | Xeon 8462Y+ (SPR), 2x32 | 2 MiB, 16-way | 60 MiB LLC | 15 | 4.0 | 262144 MB | **1** (d=14; 0->2 = 24) |
| `moscxl` | EPYC 9754, 2x128 | 1 MiB, 8-way | 16 MiB CCX (8 cores) | 16 | 1.0 | 258020 MB | SLIT says *unreachable* |

Two facts here are load-bearing and both are easy to get wrong.

**The CXL socket affinity is mirrored between the Intel hosts.** `mos181` runs
on socket 0, `mos182` must run on **socket 1** (cpus 32--63, 96--127). Running
`mos182` on socket 0 puts every streamer access across UPI *and* CXL while its
LLC footprint lands in the victim's socket -- a different experiment, silently.

**Firmware distance and HMAT tables may not be cited as evidence.** `moscxl`
declares node 2 at SLIT distance **255** (unreachable) with HMAT bandwidth
5 GB/s, while this project has repeatedly measured ~24 GB/s from it. The two
Intel hosts declare node-2 read latency 150 and 100 ns respectively, which
almost certainly reflects firmware convention rather than a real 1.5x. Node-2
bandwidth and latency are **measured per host in G0** and the firmware numbers
are recorded only as the discrepancy they are.

### Sizing

| host | target interior set | approx keys | approx leaf bytes | index total |
|---|---:|---:|---:|---:|
| `mos181` | <= 1.2 MiB | ~800K | ~24 MiB | <= 32 MiB |
| `mos182` | <= 1.2 MiB | ~800K | ~24 MiB | <= 32 MiB |
| `moscxl` | <= 0.6 MiB | ~350K | ~10 MiB | <= 12 MiB |

Starting points for G1's sweep, **not the configuration.** G1 measures the
interior set directly rather than trusting this arithmetic.

The three hosts form a ladder in shared-cache size at nearly fixed private
geometry, and that is the point of running all three:

| host | private L2 | shared per core | shared / private |
|---|---:|---:|---:|
| `mos181` | 2 MiB | 320 MiB | 160x |
| `mos182` | 2 MiB | 60 MiB | 30x |
| `moscxl` | 1 MiB | 16 MiB | 16x |

**`mos181` and `mos182` have identical private L2 -- 2 MiB, 16-way -- and a
5.3x difference in LLC.** That is a controlled LLC-size sweep at constant
private-cache geometry, on one vendor, and G6 turns it into a discriminator
that does not depend on CAT working. Report all three separately; do not
average across them and do not pick the best one.

### 2.3 The role of the hand-rolled kernel: gem5, not silicon

Masstree needs C++ threads, `-mcx16` (128-bit CAS), and a non-trivial build.
Getting it into a hand-reconstructed gem5 FS disk image, statically linked, on
top of the disk-image risk already flagged in
`../hash_join/GEM5_FS_OS_CONTRACT_SESSION_PROMPT.md` T4, compounds two risks
that should not be compounded.

So: **Masstree on silicon; a shape-matched B+tree kernel in gem5.** The kernel
matches node size, fanout, depth, and key trace. It is admissible only if it
passes a validation gate on silicon first (G5): it must reproduce Masstree's
cycles-per-lookup and L2 miss-per-lookup within a stated tolerance, on the same
host and hot-set size. A kernel that fails G5 is not a stand-in and the gem5
leg reverts to the existing pointer chase, disclosed as such.

This is the standard move and it must be disclosed as one: the gem5 number is a
kernel's number, validated against the application's, not the application's.

---

## 3. Streamer: two families, reported separately

The §4.4 contribution requires the streamer's **own** end-to-end cost. But
flush-behind and NTA require a streamer whose loads we control, and DuckDB is
not that. Rather than compromise either, run both and never mix them:

**Family S -- synthetic** (`~/tmp_dutyfree_exp/bin/aggressor`,
`benchmarks/bench/aggressor/stream_wb_flushbehind`, vendored sources in
`../instrument/`). Full arm matrix. This is the mechanism leg.

**Family R -- real** (DuckDB scanning a CXL-node-2-resident Parquet table).
WB and WB+CAT only, plus DuckDB's own query wall time. This is the application
leg, and it is what makes the streamer's cost a real number instead of a
microbenchmark bandwidth ratio.

Per `E2E_SESSION_PROMPT.md` §4.4: **a missing row is fine; an unmeasured row
silently replaced by a synthetic number is not.**

All streamer memory is node 2 (CXL). All victim memory is the **local** DRAM
node of the socket both processes run on. The victim is latency-critical;
placing it on CXL would swamp every effect under study.

Placement per host, following the mirrored CXL affinity in §2.2:

| host | socket | victim mem | victim/streamer cpus | streamer mem |
|---|---:|---|---|---|
| `mos181` | 0 | node 0 | 0--63, 128--191 | node 2 |
| `mos182` | **1** | **node 1** | **32--63, 96--127** | node 2 |
| `moscxl` | 0, one CCX | node 0 | one 8-core CCX (e.g. 0--7) | node 2 |

Verify placement per repetition from `/proc/<pid>/numa_maps`; do not infer it
from the `numactl` command line, which succeeds whether or not the policy took
effect on the pages that matter.

---

## 4. Gates. Each has a falsifiable prediction fixed here, before any run.

Run in order. Do not proceed past a failed gate without a written decision.

### G0 -- Establish the platform numbers the firmware will not give you

Per host: measured node-2 read bandwidth at the streamer's thread count, and
measured node-2 vs local load-to-use latency, from the existing `aggressor` and
pointer-chase harness in `~/tmp_dutyfree_exp/bin/`. Record the firmware SLIT
and HMAT values alongside as the discrepancy they are (§2.2). Confirm resctrl
CAT and CMT are functional on the socket the campaign will actually use.

### G1 -- Hot-set residency. *Verifies the victim is the type claimed.*

Instrument Masstree to report bytes in interior nodes vs leaves. Sweep key
count. Then, victim alone, quiescent:

- interior set <= 0.6 x private L2, **and**
- L2 hit rate >= 90% over the run, **and**
- LLC references per lookup materially below L2 references per lookup.

**Prediction:** achievable at ~1M keys on `mos181`, ~500K on `moscxl`.
**If it fails** -- no key count puts interior in L2 while leaving leaves out of
it -- Masstree's node layout is wrong for this and DBx1000 `IDX_BTREE` is tried
next. Report the sweep either way.

### G2 -- Latency-boundness. *Verifies the miss is exposed, not overlapped.*

This is the gate HNSW would have failed and nobody ran: HNSW moved 8.44x the
DRAM traffic for only 1.54x the runtime, because `ef=64` supplies memory-level
parallelism that hides the latency.

Victim alone. Measure average outstanding L1D misses
(`l1d_pend_miss.pending / l1d_pend_miss.pending_cycles` on Intel; the Zen4
equivalent) and cycles per lookup.

- average outstanding misses <= ~2, **and**
- cycles/lookup consistent with `depth x memory latency`, not with `depth x LLC
  latency` divided by a parallelism factor.

**Prediction:** ~1--1.5 outstanding, because a tree descent is strictly
serialized. **If it fails**, this victim is MLP-tolerant like HNSW and will
absorb the tax; say so and stop, rather than proceeding and reporting a small
number as a vendor property.

### G3 -- Capacity sensitivity. *The old gate, run as a control.*

Victim alone, full LLC mask vs minimum mask, per the GAPBS/HNSW protocol.

**Prediction, recorded before the run: this gate FAILS, i.e. ratio < 2x, and
plausibly < 1.3x.** That is the point. An L2-resident hot set is invisible to
LLC masking. Recording the prediction here is what makes the failure evidence
for the mechanism rather than a post-hoc reinterpretation of a rejection.

**If G3 unexpectedly passes at >= 2x**, the hot set is not L2-resident after all
and G1's residency conclusion is contradicted. Resolve the contradiction before
proceeding; do not proceed on the strength of the convenient gate.

### G4 -- CAT-isolated residual. *The new gate. Admission turns on this.*

Victim + Family-S WB streamer, with CAT partitioning the two into
**non-overlapping** way sets, victim generously provisioned:

| host | victim ways | streamer ways |
|---|---:|---:|
| `mos181` | 16 of 20 | 4 of 20 |
| `moscxl` | 12 of 16 | 4 of 16 |

Verify enforcement, do not assume it: read back the schemata **and** confirm
victim CMT `llc_occupancy` is pinned near its granted share. The project has
been bitten three times by resctrl schemata that were written and not applied
(hardcoded domain 0, three scripts).

**Admit if CAT-isolated tax >= 1.5x** -- i.e. way partitioning, correctly
enforced and generously configured, recovers less than half the WB tax.

**Prediction:** it does. `mos181` is the sharper test because the whole index
fits in a 320 MiB LLC, so 16 granted ways = 256 MiB protects the leaves
outright; any residual there is almost entirely private-cache and lookup-path.

**The discriminator, stated as the design's core claim:** under CAT isolation
the victim's LLC occupancy is pinned. **If the victim's L2 miss rate still
rises with streamer intensity, the charge is not LLC capacity.** This needs no
exotic PMU event and works on both vendors. On AMD it is cleaner still, because
Zen's L3 is a victim cache and victim L2 and L3 contents are disjoint.

### G6 -- Iso-absolute capacity neutralization across the two Intel hosts

*The discriminator that does not depend on CAT enforcement being believed.*

G4 asks whether CAT saves the victim. G6 asks the harder question -- **is the
residual capacity or is it private-cache?** -- and answers it using the 5.3x
LLC difference between two hosts with identical 2 MiB 16-way private L2.

The naive version does not work and is recorded so it is not attempted: simply
comparing total tax on `mos182` against `mos181` discriminates nothing, because
a smaller LLC *and* a smaller snoop filter both make the tax larger. The two
candidate mechanisms predict the same sign.

What does work is equalising the capacity term by construction. Way
granularity happens to make this exact at integer way counts:

| host | MiB/way | victim ways | victim LLC | streamer ways | streamer LLC |
|---|---:|---:|---:|---:|---:|
| `mos181` | 16.0 | **2 of 20** | **32 MiB** | 18 | 288 MiB |
| `mos182` | 4.0 | **8 of 15** | **32 MiB** | 7 | 28 MiB |

Both victims get **the same 32 MiB in absolute bytes**, sized (§2.2) to hold
the *entire* index -- interior, leaves and values. Capacity pressure on the
victim is therefore neutralised identically on both hosts, whatever the LLC
around it is. Note this is the opposite configuration from G4's generous grant,
and deliberately so: G4 gives CAT every advantage, G6 gives both hosts the
*same* advantage.

**Prediction.** If the residual is a capacity charge, it is now near zero on
both hosts and the two agree at ~1.0x. If it is a private-cache and lookup-path
charge, it survives on both -- and should be **larger on `mos182`**, whose
snoop filter is provisioned for 32 cores and 60 MiB rather than 64 cores and
320 MiB, so each streamer line displaces a larger fraction of it.

**A directional result here is worth more than G4's magnitude**, because it
needs no assumption that resctrl did what it was told beyond a CMT readback,
and because it is a *within-vendor, within-microarchitecture-family* contrast
where the private caches are literally the same structure.

**If the two hosts disagree in a way neither mechanism predicts**, say so and
do not proceed to the campaign on the strength of the host that behaved.

`moscxl` cannot join G6: its entire 16 MiB CCX is smaller than the 32 MiB
grant, so the victim's index cannot be capacity-protected there at all. It
supplies the cross-vendor total-tax check and G4, not G6.

### G5 -- Kernel validation (gem5 prerequisite only)

The §2.3 B+tree kernel must reproduce Masstree's cycles/lookup and L2
misses/lookup within a tolerance fixed **before** the comparison is run
(proposal: 20% on both, stated here so it cannot be relaxed afterwards). Fails
-> gem5 leg uses the existing pointer chase and says so.

---

## 5. Silicon campaign

Only after G1, G2, G4 pass, and with G3's control recorded.

Hosts: `mos181`, `mos182`, `moscxl`. Victim one core; streamer 8 threads on
cores sharing the victim's L3 domain (`moscxl`: the victim's CCX). Socket,
memory node and cpu ranges per the §3 placement table -- **`mos182` runs on
socket 1**.

| arm | streamer | family | purpose |
|---|---|---|---|
| `quiescent` | none | -- | baseline, interleaved with every loaded rep |
| `WB` | `aggressor -m wb_load`, node 2 | S | the tax |
| `WB_CAT` | same, CAT-isolated per G4 | S | **the deployed alternative** |
| `FB256` | `stream_wb_flushbehind -f 256` | S | silicon emulation of the obligation |
| `NTA` | `aggressor -m wb_prefetchnta` | S | reported **with** the A5.4 disqualification attached, never as a non-allocating arm |
| `R_WB` | DuckDB scan, CXL Parquet | R | real streamer, plus its own query time |
| `R_WB_CAT` | same, CAT-isolated | R | real streamer vs the deployed alternative |

Protocol, inherited unchanged from the DuckDB campaign because it is what made
that campaign's failures legible:

- **victim-first arrival**: victim builds and completes a warm-up trial, emits a
  ready marker, streamer starts 0.1 s later.
- n = 10 valid repetitions per arm, **rep-interleaved** in a fixed seeded order,
  not blocked.
- `hostguard.assert_quiescent()` before **every arm**, not once per campaign.
- streamer settle gated on the streamer's own occupancy reaching steady state.
- rep-paired percentile bootstrap, B = 20000, resampling repetitions.
- bandwidth matched by **thread count**. The `-R` pacing throttle carries a
  known confound and is not used.
- a repetition is invalid if the streamer has zero traffic, exits before the
  victim's last measured trial, or cannot demonstrate node-2 placement.
- **Rule O: no repetition may be excluded for overlapping a burst.**

Recorded per arm: victim ops/s and p99, victim cycles/lookup, victim CMT
occupancy, victim L2 references/misses, victim LLC references/misses, streamer
MBM and self-reported bandwidth, streamer occupancy, and -- Family R -- DuckDB's
own query wall time.

### The table this produces, which is the contribution

| streamer mode | streamer's own cost | OLTP tenant tax | deployable today |
|---|---|---|---|
| WB (default) | 1.00x (best) | large | yes |
| WB + CAT | 1.00x | **still large** | yes |
| NTA | worse (bandwidth) | -- (disqualified as non-allocating) | yes |
| flush-behind | worse (flush overhead) | small | no (needs source patch) |
| **Streaming** | **1.00x** | **small** | needs the contract |

Every row but the last is silicon, today. The last is §6.

---

## 6. gem5 leg: the decomposition silicon cannot give, plus the OS proof

Silicon can show the total tax and the CAT-isolated residual. It **cannot**
size or disable the snoop filter, so it cannot separate back-invalidation from
lookup-port contention. gem5 can. That division of labour is the reason both
legs exist, and it should be stated that way in the paper rather than gem5
being presented as a weaker replication of silicon.

Config per `../hash_join/GEM5_FS_OS_CONTRACT_SESSION_PROMPT.md`: FS mode, custom
kernel, `mprotect(PROT_STREAMING)` on the stream region, CHI 8592, O3 @1.9 GHz,
L1d 48K/12, L2 2M/16, L3 5M/20 per core, DRAM 97 ns / CXL 198 ns.

Victim: the G5-validated B+tree kernel, interior set ~1 MiB (L2-resident at
L2 = 2 MiB). Stream: >= 4x total LLC, declared Streaming by the OS.

| arm | SF | H2 | H3 | isolates |
|---|---|---|---|---|
| quiescent, infinite SF | inf | -- | -- | baseline |
| quiescent, finite SF | 65,536 | -- | -- | SF costs the victim nothing alone |
| WB, **infinite** SF | inf | no | no | **capacity charge alone** |
| WB, finite SF | 65,536 | no | no | capacity + SF + lookup |
| H2, finite SF | 65,536 | yes | no | does LLC bypass alone pay? |
| H2+H3, finite SF | 65,536 | yes | yes | the full obligation |

`HNF_SF_FINITE=1 HNF_SF_SETS=4096 HNF_SF_WAYS=16`, `HNF_DMT=0` (finite SF
requires DMT off; mixing the two across rows is the defect that voided the
original `tab:h3sf`). Three randomisation seeds per row.

**A geometry note that inverts a known problem.** The FS restore geometry has
L2 = 2 MiB against a 5 MiB/core LLC -- a 40% ratio that is the diagnosed cause
of the fused hash-join null, because that victim needed `hot >> L2`. **This
victim needs `hot <= L2` by construction**, so the geometry that broke the hash
join is appropriate here. Say this explicitly in the write-up; it will otherwise
read as reusing a discredited configuration.

**Corollary to state plainly:** for an L2-resident victim, H2 alone should buy
close to nothing and H3 should buy nearly everything. That is what `tab:h3sf`
already shows (2.501 -> 2.512 -> 1.061). It makes the headline an **H3
capability claim**, which is permitted under the §3 embargo; the embargoed
quantity is the *attribution* of the 6.92x AMD CAT residual between H2 and H3,
and nothing here touches that.

### 6.1 A prediction that makes the two legs corroborate

`clflushopt` invalidates a line from every cache in the coherence domain, so
flush-behind plausibly bounds the streamer's **snoop-filter** footprint, not
only its LLC footprint. If so, silicon flush-behind is an emulation of
**H2+H3 combined**, not of H2 alone -- which would explain why flush-behind
recovers 76.3% on AMD while gem5 H2-alone recovers nothing, without either
result being wrong.

**Test:** at matched geometry, gem5 `H2+H3` recovery should track silicon
`FB256` recovery, and gem5 `H2` alone should track nothing on silicon.

**This is a hypothesis, not a finding.** If it fails, the two legs measure
different things and the paper must say so rather than presenting flush-behind
as an H2 emulation. Recorded here so the prediction cannot be fitted afterwards.

---

## 7. Optional escalation, explicitly not required

If G1--G4 pass and time remains, add **Silo TPC-C** over the same Masstree as a
second victim, reporting both transaction throughput and the index-lookup
latency component, so the OCC/logging dilution is *measured* rather than
assumed. This upgrades "a real OLTP index" to "a real OLTP engine".

It is optional because the dilution may well shrink the effect (§2.1), and
because with the ASPLOS deadline on 2026-09-09 a from-scratch Silo build is the
single largest schedule risk on this page.

---

## 8. Failure modes, each traced to something that already happened here

1. **Believing a null without checking the private L2** (§5.2 of the standing
   rules; three nulls in this project). G1 exists for this.
2. **MLP hiding the effect** -- HNSW's 8.44x traffic for 1.54x runtime. G2.
3. **resctrl written but not applied** -- hardcoded domain 0, three scripts.
   G4 reads back schemata *and* CMT occupancy.
4. **Reporting a loaded arm without its own interleaved quiescent baseline.**
5. **Tuning toward the number.** Every gate's prediction is recorded above,
   before any run. If a gate fails, report the failure; do not re-size until it
   passes (§6.6).
6. **Quoting a cross-host average.** The three hosts sit in deliberately
   different regimes (§2.2) and G6 depends on the difference. Report separately.
7. **Running `mos182` on the wrong socket.** Its CXL is near socket 1, the
   mirror of `mos181`. Socket 0 would add a UPI hop to every streamer access
   and put the streamer's LLC footprint in the victim's socket, silently.
8. **Citing SLIT or HMAT as measurement.** `moscxl` declares node 2 unreachable
   at 5 GB/s and delivers ~24 GB/s. Measure it (G0).
9. **Letting the kernel stand in silently for the application.** G5, and the
   disclosure in §2.3.

---

## 9. Decisions that are the lead's, not this document's

1. **Changing the admission criterion from capacity-sensitivity to CAT-isolated
   residual.** It reframes the existing GAPBS and HNSW gate results from
   rejections into supporting evidence, which touches what §5 says about victim
   selection. Nothing here presumes it; G3 is run as a control precisely so the
   old criterion's answer is on the record.
2. **Scope under 17 days.** Masstree + Family S + Family R on two hosts is
   already substantial. Silo (§7) is the risk.
3. **Whether this displaces the Sec5 DuckDB rewrite**, which remains unwritten
   while the paper still carries the unreproducible RocksDB 2.33x.
4. **Whether the headline may be an H3 claim**, given that an L2-resident victim
   makes H2 nearly inert by construction.
