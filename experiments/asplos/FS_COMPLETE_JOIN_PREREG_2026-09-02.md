# FS complete-join campaign (r6b) — pre-registration

Registered 2026-09-02, before any arm of this campaign has produced a result.

## Why this campaign exists

Every wedge number now in the paper comes from `--mode single` under gem5 SE,
where the STREAMING declaration is an m5op. The objection writes itself: *a
simulator told to skip LLC fills will report skipped fills.* r12 answered half
of it — `mprotect(PROT_STREAMING)` in full system produced 261,838 tagged walks
and 118,260 HNF bypasses against 0 in both controls — but r12 ran
`--mode stream-smoke`: a truncated stream, one process, no neighbour. It proved
the counters move. It did not price anything.

This campaign runs a **complete hash join**, declared through the **real kernel
path**, against a **real LLC-resident neighbour on the other core**, and prices
it.

## What is new in the binary

`--mode fs-e2e-join` (`src/cxl_join_bench.cpp`). It borrows the process
structure of `fs-e2e-calibrate`, which exists because a fused thread cannot
show whether object-scoped admission protects a *different* execution context.
Two differences:

1. The child **joins** instead of streaming. It calls the same `join_range()`
   that `--mode single` calls. `run_single` is untouched by this change, and
   the shared kernel was verified against the SE campaign: at r5's geometry the
   native build still returns `matches = 260875` and
   `instantiated_hot_bytes = 4194304`, both exact.
2. The victim **stops when the tenant finishes** rather than running a fixed
   count, so its measured window is exactly the contended one. Under
   `--policy quiet` there is no tenant and the victim runs the full
   `--iterations` cap: that is the uncontended baseline. The SE campaign got
   the same bound by a cruder route -- its tenant called `m5_exit` after
   emitting JSON, killing the simulation mid-chase -- so the victim there could
   not record its own end. Here it can, and it reports its own load count.

The victim itself is a port of the SE campaign's
(`gem5/testcase/dutyfree/victim.c`): **32-bit elements shuffled by Sattolo's
algorithm**, a single random cycle. This matters. `fs-e2e-calibrate` uses a
constant-stride cycle, which is a materially easier victim, and the SE numbers
this campaign will be read beside were produced against the random one.
Validated natively: the contended arms retire ~1.29M victim loads against the
SE campaign's 1.31M.

The victim's window cannot be strictly contained in the tenant's — it stops
*because* the tenant finished, so it always ends one poll interval later.
Requiring containment (what `fs-e2e-calibrate` requires of its stream) would
fail every well-formed run. The registered condition is instead that the tenant
started first and the uncontended tail is ≤ 2% of the victim's window. Polling
every 1024 dereferences bounds that tail; observed natively at 0.1%.

## Geometry, and which ratios it matches

This machine's LLC is **10 MiB** (`num-l3caches = num-cpus = 2 × 5 MiB` in
`fs_restore_chi_8592.sh`). The SE complete-join campaign ran at **7.5 MiB**, so
its byte sizes are not transferable and are not used.

| | this campaign | r5 (SE) | r3 (SE) | silicon |
|---|---:|---:|---:|---:|
| LLC | 10 MiB | 7.5 MiB | 5 MiB | 60 MiB |
| table/LLC | 0.400 | 0.533 | 0.800 | 0.533 |
| victim/LLC | **0.533** | 0.345 | 0.518 | 0.533 |

The victim is sized to silicon's ratio, which r5 missed — its own audit named
that miss as the reason its victim was under-stressed and its tax fell. The
table stays at 4 MiB and so sits at 0.400: `probe()` masks rather than divides,
so the table is quantized to a power of two, and at a 10 MiB LLC no power of
two lands on 0.533. One ratio is matched and one is not; both are stated.

Fact stream 8 MiB on the CXL node, `--reps 1`, `--iterations 12000000`,
three seeds (1, 2, 3), arms `qui` / `wb` / `h2`.

## Registered gates

Enforced by `w8/fs_join_analyze.py`, fail-closed:

- rcS completed (`BENCH-EXIT 0` and `RCS-DONE`), exactly 2 stats sections.
- `status == ok`; tenant and victim placement and affinity all true.
- `tenant_covers_victim`, and uncontended tail ≤ 2%.
- `victim_capped` true **iff** the arm is `qui`; a capped contended arm means
  the tenant outlived the victim and the cyc/load is not the tax it imposed.
- **Arm identity is read off the hardware counter, not the launcher**: `h2`
  must show HNF streaming-fill bypasses > 0; `wb` and `qui` must show exactly 0.
- `wb` and `h2` at the same seed must compute the same join (`matches` equal).

## Registered predictions

- **P1 (arm identity).** `h2` bypasses > 0; `wb` and `qui` bypasses = 0.
- **P2 (the neighbour is actually stressed).** `wb` victim cyc/load exceeds
  `qui` by ≥ 10%. r5 saw +18.5%. If this fails there is no contention and
  nothing downstream means anything.
- **P3 (protection).** R(h2) = (wb − h2)/(wb − qui) > 0. Directional only:
  the magnitude is not registered, because the LLC and the victim ratio differ
  from every prior campaign and no prior number transfers.
- **P4 (the tenant does not pay).** Tenant tuples/s under `h2` ≥ under `wb`.

**Falsification.** If P1 fails the OS path did not engage and the campaign is
void — that is a broken run, not a negative result. If P1 holds and P3 fails,
the OS path engages but does not protect at this geometry: that *is* a real
negative result and the paper must report it as one.

## Known risk, and how it is bounded

`fork` + two active cores + `mprotect` has never completed in FS on this
platform. `h2-admission` reaches `mprotect` but is single-process; the only
two-process arm that ever finished (`fs-e2e-calibrate quiet`) never declares
anything; and W8.7 recorded a two-core CHI queued-spinlock livelock, which is
why the r12 mprotect arm was deliberately kept single-threaded. The campaign
driver therefore runs a small smoke arm first and refuses to launch the other
nine unless it completes.

## What this campaign does not do

It does not sweep way masks; the CAT frontier stays in the SE campaign and on
silicon. Its wedge is therefore **against an unprotected neighbour**, not
against a mask at matched protection, and must not be quoted as the latter. It
is not comparable to r5 arm-for-arm, but the reason is the machine, not lost
provenance: `experiments/asplos/run_complete_join.sh` is committed and records
r5's launch exactly (`--num-l3caches=1 --l3_size=7680KiB`, victim
`2650 12000000`, `qui` = victim + dummy), and this campaign's victim is ported
from it. What differs is the LLC -- 10 MiB here against 7.5 MiB there -- and
therefore both footprint ratios. This campaign exists to show the OS path
produces the effect at all, end to end, with no m5op in the declaration path.

---

## Addendum 1 — 2026-09-02, filed before the change it describes

Four deviations from the registration above. None of them changes a registered
prediction or a gate; P1–P4 and the fail-closed criteria stand as written.

### 1. The simulation rate in the plan was not a measurement of these arms

Two `SIGUSR1` stats dumps 45 s apart on the running smoke arm give
**26,511 simulated cycles per host-second**. The ~62,000 cyc/s figure used
when scheduling this campaign came from r12, a `stream-smoke` workload whose
memory-level parallelism is much higher, so it retires far more work per
simulated cycle. That number was an extrapolation from a different regime and
was quoted as though it were a measurement of this workload. It was not. At
the measured rate the campaign is bounded by the `qui` arms at roughly six
hours.

### 2. The nine arms were launched before the smoke arm completed

The registration says the driver runs a smoke arm first and refuses to launch
the other nine unless it completes. The nine were launched while smoke was
still running, on direct evidence that the risk the gate existed to catch is
absent: at 47 minutes both guest cores were retiring (`idleCycles` ~ 0, cpu0
at 41.4M committed instructions and 10.6M committed stores), which places
cpu0 well past `declare_streaming` — the `mprotect` executes *before* the
32 MiB scrub. Dual-core retirement past `mprotect` is the observation the
smoke gate was there to obtain, and it was obtained. Smoke was left running
and still validates the full JSON and analyzer path end to end.

### 3. `qui` only: `--iterations` 12,000,000 -> 4,000,000

`wb` and `h2` are **unchanged at 12,000,000** and were not touched.

`qui` sets only the uncontended cyc/load floor in
R = (wb - h2) / (wb - qui). After the explicit warm pass that rate does not
depend on 4M versus 12M: 4M still wraps the 1,398,100-element cycle about
three times. P2 is a 10% gap, not a precision comparison against r5 — and
this campaign is already not r5, at a different LLC and a different victim
ratio.

The contended arms keep 12M for a specific reason. `--iterations` is the
victim's **cap**, and the analyzer fails any contended arm whose
`victim_capped` is true, because a capped contended arm means the tenant
outlived the victim and the measured cyc/load is not the tax the tenant
imposed. 12M is about 9x the ~1.3M loads a contended arm is expected to
reach; 4M would be about 3x. If the join window runs longer than the 50M-cycle
estimate, a 4M cap could void an otherwise good `wb` or `h2` arm. Those arms
are not the six-hour bound, so there is nothing to buy by shortening them.

### 4. `SCRUB_BYTES` is fixed at 32 MiB x 2 on every arm, including smoke

`SCRUB_BYTES` is a compile-time constant, so the smoke arm performs the same
64 MiB of displacement writes as a full arm regardless of its much smaller
fact, table, and victim. That is why smoke ran ~50 minutes rather than the few
minutes a tripwire is supposed to cost, and it is why per-arm setup is on the
order of 1.3-2.1 hours. The gate still functioned; it was simply far more
expensive than intended.

Expected effect: wall-clock falls from about six hours to about three. No
registered prediction changes.

---

## Addendum 2 — 2026-09-02. r6b's result, its root cause, and the r6c geometry

r6b answered P1 and could not answer P3. Both outcomes are reported here, with
the diagnosis, before r6c is launched.

### What r6b established (P1, decisively)

The OS declaration path engages the hardware with no m5op anywhere:

| stage | counter | value |
|---|---|---:|
| PTEs stamped by the kernel | `mmu.dtb.walker.streamingTranslations` | 805 (smoke) |
| accesses carrying the label | `mmu.dtb.streamingAccesses` | 321,755 (smoke) |
| shared-LLC fills refused | `hnf0+hnf1.streamingHnfFillBypasses` | **130,864 / 130,635** (h2 arms) |

The 8 MiB fact stream is 131,072 lines, so **99.8% of the declared stream was
refused admission** to the shared LLC. `wb` and `qui` show exactly 0. P1 holds.

### Why P3 could not be answered: the harm was contention, not capacity

| arm | victim L2 hit rate | shared-LLC hit rate |
|---|---:|---:|
| `qui` | 66.0% | 99.16% |
| `wb` | 59.3 / 60.3% | 97.63 / 97.58% |
| `h2` | 59.4 / 61.9% | 98.20 / 98.21% |

Two facts kill the measurement. The victim served **~60-66% of its accesses
from its own private L2**, which H2 cannot reach by construction. And of the
traffic that did reach the shared LLC, **97.6% still hit under full load** --
the stream displaced barely 1.5 pp of the victim's residency. The observed
+10.27% victim tax is therefore overwhelmingly *queueing behind the stream's
131,072 fills*, not eviction. H2 stops the stream from **occupying** LLC slots;
it does not stop it from **fetching**. It structurally cannot remove a
bandwidth tax, so R measured +8.98% -- the thin capacity sliver -- against a
seed spread of 0.745 (`wb`) and 1.656 (`h2`) cyc/load. The signal is smaller
than the scatter and no number of extra seeds would recover it.

**The specific error was the victim's memory layout.** The chase was a Sattolo
permutation over 4-byte `int`s, so **16 live elements shared every 64-byte
line**. Each line was touched 16 times per traversal, inflating L2 residency far
above what a 5.33 MiB footprint implies (66% measured against ~37% predicted by
capacity). This layout was inherited verbatim from r5's `victim.c` without
checking what it does at a 2 MiB L2. Addendum 1's geometry table is therefore
misleading: the *nominal* victim/LLC was 0.533, but the footprint the L2 saw was
far smaller.

A contributing factor: this machine's LLC is 10 MiB (2 slices x 5 MiB) against
r5's 7.5 MiB single slice -- 33% more capacity, hence less eviction pressure.

### r6c: what changes

1. **The victim chase is line-granular** -- one live element per 64-byte line.
   The footprint the L2 sees now equals the footprint requested. Verified by a
   new in-binary check: Sattolo yields a single cycle, so following it exactly
   `vlines` times must return to the start; `victim_cycle_ok` is emitted and a
   false value fails the arm closed. A silently broken permutation would shrink
   the working set and look exactly like a protection result.
2. **Victim footprint 6 MiB** (98,304 lines). Predicted L2 hit ~33% against
   r6b's measured 66%; victim + 4 MiB table = 100% of the LLC, so the stream
   has something to displace. Nominal victim/LLC 0.60.
3. **`qui` cap 2,000,000** (20 full traversals -- ample for a rate), `wb`/`h2`
   unchanged at 12,000,000. Contended arms are expected near ~610K loads, so
   the headroom stays ~20x and `victim_capped` cannot bind a good arm.
4. **Every arm is pinned to a distinct physical core** with `taskset`. r6b ran
   unpinned; two of its nine arms consumed 375 min against their siblings' 286,
   and this host is 128 physical cores x 2 SMT threads, so two arms sharing one
   physical core lose ~40% -- which matches. NUMA was tested and refuted (both
   were node-local). SMT is unproven but is the only candidate of the right
   magnitude, and pinning removes it either way.

Registered predictions P1-P4 and every gate are unchanged. P1 is now expected
to reproduce rather than be discovered; P3 is the open question r6c exists to
answer, and a null remains a reportable result.

### One operational note

gem5 buffers `system.pc.com_1.device`, so console markers lag the simulation by
an unbounded amount -- two r6b arms sat at the same partial character for 20
minutes while burning 100% CPU. Console markers are not a live progress signal.
`SIGUSR1` would give a true reading but appends a stats section, and the
analyzer requires exactly two, so probing a live arm fails it closed.

---

## Addendum 3 — 2026-09-02. Addendum 2's root cause is WITHDRAWN. It was a stat-selection error.

Addendum 2 diagnosed r6b's null on P3 as follows: *"of the traffic that did reach
the shared LLC, 97.6% still hit under full load -- the stream displaced barely
1.5 pp of the victim's residency... The observed +10.27% victim tax is therefore
overwhelmingly queueing... H2 stops the stream from occupying LLC slots; it does
not stop it from fetching. It structurally cannot remove a bandwidth tax."*

**That diagnosis is wrong and is withdrawn in full.** The hit rates it rests on
were read from `m_demand_hits`/`m_demand_misses` only. This workload is
prefetch-driven *by construction* -- H1 requires the stream's prefetchers to
behave as for write-back memory -- so the demand-only columns exclude the
majority of the stream's LLC traffic. Recomputed over demand **and** prefetch,
summed across both HNF slices, from the same r6b ROI sections:

| arm | LLC miss %, demand only | LLC miss %, demand+prefetch |
|---|---:|---:|
| `qui` | 0.84 | **1.15** |
| `wb` | 2.37 | **7.19** |
| `h2` | 1.80 | **6.29** |

The stream raises the true LLC miss rate **6.25x**, not 1.5 pp. And the
mechanism is plainly acting on it -- the stream's clean-victim insertions into
the shared LLC (`inTransLatHist.WriteEvictFull.RU.UC.total`, both slices):

| arm | insertions |
|---|---:|
| `qui` | 709 |
| `wb` | **232,427** |
| `h2` | **62,819** |

**H2 removes 73% of the stream's LLC insertions and ~15% of the added misses.**
The harm in r6b was substantially capacity harm, and H2 did act on it. The
claim that H2 "structurally cannot remove" this tax was false.

This trap is already documented in this repo. `Appendix.tex:218` records
switching to demand+prefetch counters and notes that the earlier demand-only
figure "read as a cost rather than a gain". Addendum 2 repeated the mistake and
then propagated it into the r6c rcS headers as established fact.

### So why did R measure only +8.98%?

Four causes, none of them "H2 cannot help". All were found by external review
and each is verified against the r6b artifacts:

1. **The quiet baseline omits the tenant's table.** `--policy quiet` returns
   before `build_table` (`cxl_join_bench.cpp` quiet branch); the records show
   `instantiated_hot_bytes: 0`, `fact_bytes: 0`. So `(wb - qui)` conflates harm
   from the STREAMING-eligible fact stream with harm from the tenant's 4 MiB
   non-streaming table, which H2 can never remove. R has a structural ceiling
   unrelated to H2's quality, and the +10.27% tax is not stream-attributable.
2. **The victim's window is defined by the tenant's completion.** A faster
   tenant yields a shorter window, a larger fraction of which lies in the cheap
   early part of the displacement ramp -- biasing the arm hypothesised to be
   faster (`h2`) toward a lower cyc/load with zero protection. The design is
   clean only when the tenant wedge is zero, which is what r6b measured.
3. **`--reps 1` with an 8 MiB stream against a 10 MiB LLC.** 131,072 lines
   against 163,840: the stream cannot fill the shared cache even once, so
   displacement never plateaus and the reported cyc/load is the mean of a ramp
   whose truncation point is set by the tenant's runtime.
4. **Config divergence.** Neither `fs_restore_chi_8592.sh` nor
   `run_fs_e2e_gate.sh` exported any `HNF_*` variable, so r6b took
   `CHI_config_8592.py` defaults: **TreePLRURP at 20 ways**, `enable_DMT=1`,
   `fwd_unique_on_readshared=1`. Every SE number in the paper pins
   `HNF_RP=lru HNF_DMT=0 HNF_FWD_UNIQUE=0`. `Appendix.tex:345-348` states that
   TreePLRU is 2x biased at non-power-of-two associativity -- and 20 ways is
   non-power-of-two. **r6b was not the same machine as the rest of the paper.**
   Now pinned in `run_fs_joinc_campaign.sh`.

### Status of the r6c changes

The **line-granular victim stands on its own merits**: the 60-66% private-L2
hit rate measured in r6b is real, and H2 governs only the shared LLC, so that
fraction of the chase is genuinely outside its reach. But it was adopted in
Addendum 2 for a stated reason that was wrong, and that must be on the record.

**r6c is held, not launched.** Its checkpoint is built and bound, but it
carries the r6b baseline defect (1), the tenant-defined window (2), and
`--reps 1` (3). Launching it would produce a third uninterpretable R.

### Also corrected: what the bypass counter counts

`streamingHnfFillBypasses` equals `inTransLatHist.WriteEvictFull.RU.I.total`
exactly (130,888 in `h2_s1`). Because the HNF sets
`alloc_on_read{shared,unique,once}=False`, a streaming read can never register
a bypass: **every bypass event is a clean private-cache victim insertion, and
the fill clause of H2 is unreachable in this configuration.** The counter's
name and its stats.txt description ("...bypassed an LLC fill") are both wrong,
and any paper sentence reading "fills bypassed" must say victim insertions.
`Sec4` already argues the victim clause "is the whole of H2 on that
microarchitecture", so the argument survives; the wording does not.

---

## Addendum 4 — 2026-09-02. r6d: the campaign the review says is interpretable

r6c was built and its checkpoint bound, but it was **never launched**: it
carried r6b's baseline defect, r6b's tenant-defined window, and `--reps 1`.
Launching it would have produced a third uninterpretable R. r6d replaces it.
Five changes; the first two are the ones that matter.

### 1. The baseline now differs from the contended arms in exactly one thing

`--policy quiet` previously returned before `build_table` (records show
`instantiated_hot_bytes: 0`). Its victim therefore owned the LLC with 4 MiB of
headroom the contended victims never had, so `(wb - qui)` conflated harm from
the STREAMING-eligible fact stream with harm from the tenant's non-streaming
hash table -- and H2 can only ever remove the former. R had a structural
ceiling unrelated to H2's quality, and the +10.27% tax was not
stream-attributable.

The quiet tenant now builds its 4 MiB table, performs the same 64 MiB scrub as
the contended arms, and **keeps probing the table for the whole window**. The
arms differ only in whether the stream flows.

It also no longer spins on `sched_yield()`. Measured in r6b: the quiet arm
produced **3,713,197 HNF data-array writes against wb's 3,136,005** -- the
"uncontended" baseline had a syscall-thrashing neighbour that the contended
arms did not, and it was noisier than the stream under test.

### 2. The stream now saturates the LLC, and read-once is preserved

r6b/r6c streamed 8 MiB = 131,072 lines against a 163,840-line LLC = **0.80x
turnover**. The stream could not fill the shared cache even once, so
displacement rose monotonically for the entire window and the reported
cyc/load was the mean of a **ramp**, not a rate -- with the truncation point
set by the tenant's runtime.

r6d streams **32 MiB read once** = 524,288 insertions = **3.2x turnover**.

Raised through **fact size, not `--reps`**, deliberately. External review
suggested `--reps 6-8`; that reaches the same turnover but re-reads the same
object 6-8 times, giving the stream *reuse* and destroying the read-once
premise the entire contract exists to exploit. A stream with reuse would
benefit from being cached, which is the opposite of the paper's motivation.
Fact size achieves the identical insertion count with read-once intact.

Note one thing raising either knob does **not** fix: stream insertions *per
victim LLC access* is set by the two rates, not by totals, so it is unchanged
at ~0.42. What the larger object fixes is the plateau, which is the defect that
made r6b's mean uninterpretable.

### 3. The ramp is now measured rather than assumed

The victim records cyc/load in **20 equal-load buckets** across its window and
emits them as `victim_cpa_buckets`. If the last bucket differs from the mean,
the number is still a transient and must be reported as one. r6b had no way to
tell.

### 4. Windows are comparable

The quiet cap is set to 3,200,000, near the contended arms' expected load
count, rather than r6b's 4,000,000 against a contended ~790,000 -- a **4.59x**
mismatch, since a per-access mean over a 4.6x longer window weights the
post-warm transient differently and the baseline sets R's denominator. The
analyzer now fails above 2x and prints the measured spans.

### 5. The HNF configuration is pinned

Neither `fs_restore_chi_8592.sh` nor `run_fs_e2e_gate.sh` exported any `HNF_*`
variable, so r6b took `CHI_config_8592.py` defaults: **TreePLRURP at 20 ways**,
`enable_DMT=1`, `fwd_unique_on_readshared=1`. Every SE number in the paper pins
`HNF_RP=lru HNF_DMT=0 HNF_FWD_UNIQUE=0`, and `Appendix.tex:345-348` states
TreePLRU is 2x biased at non-power-of-two associativity -- 20 ways is
non-power-of-two. **r6b was not the same machine as the rest of the paper.**
Now pinned in the launcher.

### Analyzer changes (r6b's data now fails five gates it previously passed)

Run against r6b, the hardened analyzer reports: windows differ 4.59x; **P3
UNRESOLVED** (gap 0.519 < seed spread 1.656 cyc/load); **P4 REFUTED** (-0.51%
on rdtsc); plus the two incomplete arms. It previously printed
*"PASS: every gate satisfied."*

- Tenant throughput from `rdtsc`, never from `join_mtuples_per_s` -- the guest
  clock ticks at 1 ms on a ~25 ms window, and the quantised field gave the
  **opposite sign** to the counters.
- Bypass coverage must be >= 90% of the object's lines, not `> 0`.
- Cross-arm geometry compared (`victim_bytes`, `victim_lines`, `fact_bytes`,
  `hot_bytes`, `reps`); `victim_bytes` is the dominant parameter for the victim
  metric and nothing compared it before.
- `matches > 0` and `victim_cycle_ok` required.
- P2, P3 and P4 are now *asserted*, with `n` and half-range printed beside
  every mean. Previously none of the three predictions was tested by any gate.

### Predictions

P1-P4 unchanged. P3's bar is sharpened from "R > 0, directional" to **the
wb-h2 gap must exceed the observed seed spread** -- r6b's +8.98% would not
clear it. A null remains a reportable result.

---

## Addendum 5 — 2026-09-03. Mid-flight qui cap correction, and four defects deferred to r6f

External review of the running r6e campaign found one time-critical sizing error
and four defects that need a rebuild. The sizing error is corrected now, on the
`qui` arms only, by the same protocol as addendum 1 (`wb`/`h2` untouched).

### Corrected now: `qui --iterations` 3,200,000 -> 1,200,000

Addendum 4 set the quiet cap by scaling r6b's contended load count (789,504) by
4x for the 4x longer tenant window. That scaling assumed the victim's cyc/load
stayed near r6b's 62. It does not: the line-granular chase removes the 60-66%
private-L2 shielding, so cyc/load rises roughly 2.5x and the contended arms will
retire about **1.1-1.3M loads, not 3.2M**. The quiet cap is therefore 2.5-2.9x
too high, and the resulting victim windows differ by an estimated **1.6-2.4x**
against the 2.0x limit the analyzer itself enforces -- so the campaign had a
coin-flip chance of being failed by its own window-comparability gate.

1,200,000 loads is 12.2 full traversals of the 98,304-line cycle. r6d's quiet
arm showed its 20 buckets flat to 0.25% at 32 traversals, so 12 is ample for a
rate. The correction also shortens the campaign's critical path by roughly 2.5-3
hours, because the quiet arms are its bound.

### Deferred to r6f (each needs a rebuild, which would kill the running arms)

1. **`prefault_region` still mutates the FACT.** `cxl_join_bench.cpp:1644` runs
   it *after* `fill_fact` has written every byte, so it is both redundant and
   destructive: it increments the low byte of `fact[i].fk` on the first tuple of
   every page, corrupting **8,192 of 2,097,152 keys (0.39%)**. Those probes then
   miss. This is the same defect class as the victim corruption fixed in
   addendum 4 -- found on the victim, not checked on the fact. It is symmetric
   across arms at a seed, so the `matches` cross-check passes and the
   measurement is not materially moved, but the tenant is not computing the join
   it reports. Delete the line.
2. **The plateau instrumentation is inert in the arms that need it.**
   `bucket_every = c.iterations / 20`, so at `--iterations 20000000` the
   contended arms get a 1,000,000-load bucket against ~1.2M actual loads --
   **one bucket**, equal to the whole-window mean. The quiet arm gets 20. The
   ramp that addendum 4 fix #3 exists to expose is therefore visible only where
   there is no stream. Use a fixed absolute bucket size (~25,000) and 64
   buckets. No gate reads `victim_cpa_buckets` yet either.
3. **The ROI section closes after teardown.** `run_fs_e2e_join` calls
   `gem5_reset_stats_now()` but never `gem5_dump_stats_now()` -- which exists
   and is used by the h2-admission path at `:1330` with a comment stating
   exactly why it is needed. So section 1 runs to the rcS's `m5 dumpstats` and
   includes the child's 32 MiB munmap and TLB shootdowns, `waitpid`, the JSON
   write through the UART, the victim's 6 MiB munmap, and a fork+exec of
   `/sbin/m5`. That teardown is present in `wb`/`h2` and absent in `qui`, whose
   child frees nothing. P2/P3/P4 are safe -- they come from `rdtsc` brackets --
   but every insertion count and miss rate used to *explain* the result is
   contaminated asymmetrically. Fixing it requires relaxing `roi_section` from
   exactly 2 sections to 3, and re-deriving `BYPASS_COVERAGE_MIN`: with a
   32,768-line L2, the in-window ceiling for a 524,288-line stream is
   **93.75%**, only 3.75 pp above the 0.90 floor.
4. **Analyzer**: `TUPLES` is hardcoded to `8388608 // 16` (r6b's 8 MiB fact)
   while r6e streams 32 MiB -- P4's sign and magnitude survive because it is a
   ratio, but the printed tuples/cycle is 4x low. Nothing asserts realized
   geometry against intended geometry in absolute terms, and
   `instantiated_hot_bytes` is not compared across arms even though addendum 4
   fix #1 makes the quiet arm's table the thing that must now match. The P1
   arm-identity gate is guarded by `isinstance(byp, float)`, and `sum([])`
   returns int `0`, so a renamed or absent counter would silently **skip** P1
   rather than fail it.

### Recorded, not fixed

- The quiet arm is effectively **n = 1**: the victim permutation is seeded
  `std::srand(42)`, so it is byte-identical in every arm and every seed, and
  `--seed` varies only the tenant's table and fact. r6b's three quiet arms
  returned bit-identical cycle counts; r6d's agreed to 0.01%. R's denominator
  therefore carries no measured uncertainty, and the "seed spread" the P3 bar is
  compared against is entirely tenant-window noise.
- Addendum 4 fix #1's *justification* was wrong even though the fix is right.
  It compared HNF data-array write **totals** (quiet 3,713,197 vs wb 3,136,005)
  over windows of 225.0M and 49.3M cycles -- per cycle the quiet arm was
  **3.9x quieter**, and cpu0's L2 misses in that arm were 3,669, i.e. 0.098% of
  HNF accesses. The `sched_yield` spinner was invisible; the 3.71M matches the
  victim's own L2 misses. The baseline needed the tenant's table, which is fix
  #1's first argument and stands.
- The geometry sits at exactly 20.0 of 20 ways (victim 12.0/set + table
  8.0/set), the point of maximum sensitivity to replacement detail and page
  colouring. Chosen deliberately for signal; the variance consequence was not
  stated until now.

---

## Addendum 6 — 2026-09-03. Two r6f source fixes landed and quantified

Both were on addendum 5's deferred list. Applied to source only; the running
r6e arms are unaffected (they execute the binary baked into the r6e image).

### The fact prefault is gone, and the corruption is now measured, not inferred

`prefault_region(fact, ...)` ran immediately after `fill_fact` had already
written every byte of the object, so it was redundant -- and it mutates:
`q[off] = q[off] + 1` on the first byte of every page and on the last. An A/B
against the verbatim helper confirms the magnitude exactly:

| | |
|---|---:|
| tuples in a 32 MiB fact | 2,097,152 |
| keys altered by prefault | **8,192 (0.391%)** |
| pages in 32 MiB | **8,192** -- one corrupted key per page |
| expected match loss at hit_rate 0.5 | ~4,096 |

`fact[i].fk` is an `int64_t` at offset 0 of each page, so the increment lands
on the key's low byte and those probes miss. It is symmetric across arms at a
seed, so the `matches` cross-check passed and the measurement was not
materially moved -- but the tenant was not computing the join it reported. This
is the same defect class as the victim-chase corruption of addendum 4: found on
the victim, never checked on the fact. Post-fix, `matches` sits within 1.2σ of
`n/2` on 2M Bernoulli draws.

### Bucket sizing is absolute, not a fraction of the cap

`bucket_every` was `c.iterations / VBUCKETS`. But `--iterations` is a **cap**,
and a contended arm stops on `tenant_done` far below it: at `--iterations
20000000` the divisor produced a 1,000,000-load bucket against ~1.2M actual
loads, i.e. **one** bucket equal to the whole-window mean. The plateau
instrument was therefore blind in exactly the arms that ramp, and 20 buckets
wide only in the quiet arm that has no stream to ramp against.

Now `VBUCKETS = 64` at a fixed `VBUCKET_LOADS = 25000`. Verified: a 900,000-load
run emits **36** buckets and is judgeable by the plateau gate.

### Analyzer (no rebuild needed, applied now)

- Tenant throughput now derives tuples from the **realized** `fact_bytes` in
  each record. The constant was hardcoded to r6b's 8 MiB fact and would have
  printed r6e's tuples/cycle 4x low. P4 is a ratio, so its sign and magnitude
  were never affected.
- The P1 arm-identity gate **fails closed**. It was guarded by
  `isinstance(byp, float)`, and `sum([])` returns int `0`, so a renamed or
  absent counter would have silently skipped P1 rather than failing it.
- The window-comparability gate is now conditioned on plateau evidence rather
  than a bare ratio: an unequal window only biases a per-access mean if the arm
  is still ramping, and a plateaued arm reports a rate. It fails closed when an
  arm emitted too few buckets to judge -- including when the field is absent
  entirely, which the first version of this change wrongly exempted.

### Still deferred, and it needs a rebuild

`run_fs_e2e_join` never calls `gem5_dump_stats_now()`, so the ROI section closes
after the rcS's `m5 dumpstats` and includes the child's 32 MiB munmap and TLB
shootdowns, `waitpid`, the JSON write through the UART, the victim's 6 MiB
munmap, and a fork+exec of `/sbin/m5` -- present in `wb`/`h2`, absent in `qui`,
whose child frees nothing. P2/P3/P4 are safe (`rdtsc`-bracketed), but every
insertion count and miss rate used to *explain* a result is asymmetrically
contaminated. Fixing it also requires relaxing `roi_section` from exactly 2
sections to 3 and re-deriving `BYPASS_COVERAGE_MIN`, whose 0.90 floor sits only
3.75 pp under the 93.75% in-window ceiling for a 524,288-line stream against a
32,768-line L2.

---

## Addendum 7 — 2026-09-03. CAMPAIGN CLOSED AFTER r6e. No r6f, no r7.

Pre-committed in writing, before r6e's contended arms have reported.

**Decision: this is the last full-system generation.** r6e runs to completion
because it is sunk; whatever it reports becomes at most one paragraph, labelled
as a different machine. The r6f image and boot checkpoint are built and bound
and will **not** be launched.

### Why, stated plainly

The full-system campaign's only durable result is **P1** -- the OS-installed
label reaches the coherence point and changes admission, 99.8% of the declared
stream refused with both controls at exactly zero. **P1 was obtained on the
first attempt**, by the smoke arm, before any of r6b/r6c/r6d/r6e existed.

Everything after that chased a *protection* number which:

1. the calibrated model and the silicon sweep already supply, and
2. **cannot enter the same table as the +8.42% headline anyway**, because this
   machine's LLC is 10 MiB (2 slices x 5 MiB) against r5's 7.5 MiB, so the byte
   geometries do not transfer -- a fact established in addendum 3 and used
   there to justify changing the geometry, without drawing the corollary that
   it also caps the result's value to directional corroboration.

A result that cannot move the paper in either direction is not a critical path.
Six generations (r6, r7, r6b, r6c held, r6d, r6e) were spent as though it were.

### What replaces it

1. **The flush-behind oracle.** E3 states that "the paper's competitive claim
   must be made against flush-behind, not against CAT", and the appendix's
   "Platform split" concedes that the comparison exists on *neither* platform.
   The paper therefore names its own decisive comparison and admits it is
   missing -- a reviewer needs only to quote us. Plan: a `flushrange`
   pseudo-instruction beside the existing `setstreaming`, functionally
   invalidating a range in all controllers at **zero instruction and latency
   cost**, i.e. flush-behind as an *idealized oracle* -- its absolute best
   case, which errs against our own thesis. If H2 still wins against that, the
   objection is closed. Flush-behind is structurally *retroactive*: the
   neighbour's line is already evicted when the flush runs, which is the likely
   reason silicon caps it at 44.5% recovery.
2. **The restructure.** Cut H3 (its motivating table does not reproduce at its
   own documented commit, per our own margin note at `Sec5_Evaluation.tex:502`).
   Cut Sec5's superseded narrative half, which currently presents five
   different CAT costs for what reads as one experiment. Make "Enforced" in the
   title true with roughly six lines of kernel. One canonical machine-config
   table with a realized column per arm.

### The pattern this campaign should be remembered for

Six voided or compromised runs, one cause: **a verification weaker than the
thing it verified.** `cycle_ok` satisfied by a 2-element cycle because 2
divides 98,304. "PASS: every gate satisfied" while asserting none of P2, P3 or
P4. Demand-only counters on a workload that is prefetch-driven by design. A
baseline omitting the tenant's table. `prefault_region` corrupting data it ran
after -- on the victim, then again on the fact. And the 2-or-3 section
relaxation re-opening a hole the strict check had covered.

None of these crashed. Every one produced a *plausible number* that survived
reading. The remedy that worked, every time, was to **emit the quantity, not
the boolean**: `cycle_len=98304/98304` rather than `cycle_ok=1`; twenty bucket
values rather than a mean; `n` and half-range beside every average; a stats
section cross-checked against an independent rdtsc bracket.

---

## Addendum 8 — 2026-09-04. Every comparison in this document against r5's LLC is wrong by a third, and the corrected statement is cleaner than the one it replaces

Filed by the ledger/index pass, not by this campaign's worker, against
`NONPOW2_SETS_MEASURED_2026-09-04.md` (superproject `c3101b2`, gem5
`c030d776ee`). **Appended, not applied**: this is a sealed registration, so the
superseded wording is quoted in place and nothing above this line is edited, per
`A6.19`. Every figure below was re-derived rather than taken from the handback
that raised it.

**Nothing in this campaign moves.** Its own geometry is clean and was verified,
not assumed: `--num-l3caches=2 --l3_size=5MiB --l3_assoc=20` gives 4,096 sets
per slice, a power of two, so 10 MiB requested is 10 MiB realized, and the
`fs_restore_chi` run directories' own `config.ini` say so. r6b–r6e's results,
addendum 7's closure, and this registration's `victim/LLC = 0.533` and
`table/LLC = 0.400` all stand exactly as recorded.

**What is wrong is every comparison drawn against r5**, because r5's LLC was
never 7.5 MiB. gem5's Ruby `CacheMemory::init()` computes
`(size/assoc)/block` sets and then takes `floorLog2` of it for the index width,
so `--l3_size=7680KiB --l3_assoc=20` allocates **6,144** sets, indexes only
**4,096**, and realizes **5,242,880 B — 66.7% of what was configured**. This is
`[F9.4]`'s arithmetic, on record since 2026-08-23; what is new is that it is now
**measured**, `7680KiB`/20 being bit-identical to `5MiB`/20 on all 2,014
simulated quantities that a gem5 run emits. The record-keeping half is
registered as **`F18`** in `A1_PROVENANCE_LEDGER_2026-08-28.md`.

### The six places, and the one that matters most

The handback named the sentence at line 123. There are six, and the last two are
the consequential ones.

| # | where | as written | realized |
|---|---|---|---|
| 1 | line 57 | "The SE complete-join campaign ran at **7.5 MiB**" | **5.0 MiB** |
| 2 | line 62, geometry table | `LLC \| 10 MiB \| **7.5 MiB** \| 5 MiB \| 60 MiB` | r5 = **5 MiB** |
| 3 | line 63, geometry table | `table/LLC \| 0.400 \| **0.533** \| 0.800 \| 0.533` | r5 = **0.800** |
| 4 | line 64, geometry table | `victim/LLC \| 0.533 \| **0.345** \| 0.518 \| 0.533` | r5 = **0.518** |
| 5 | line 123 | "What differs is the LLC -- 10 MiB here against **7.5 MiB** there" | **10 MiB against 5 MiB — exactly 2×** |
| 6 | lines 237–238 | "10 MiB (2 slices x 5 MiB) against r5's 7.5 MiB single slice -- **33% more capacity**, hence less eviction pressure" | **100% more capacity** |

Line 642 repeats item 5's premise ("this machine's LLC is 10 MiB … against r5's
7.5 MiB, so the byte geometries do not transfer") and is corrected with it. Note
what that particular correction does **not** do: the byte geometries still do not
transfer, so addendum 3's justification for changing the geometry and addendum
7's ruling that this campaign's protection number cannot enter the same table as
the +8.42% headline both **survive unchanged**. A 2× gap is no more transferable
than a 1.33× one.

**Item 5 is a better fact than the one it replaces.** 10 MiB against 5 MiB is
**exactly 2×**, a round ratio between two power-of-two set counts, where 1.33×
was an artifact of comparing this machine's realized capacity against r5's
requested one.

**Item 6 is the one to read carefully, because it is a causal claim resting on
the wrong number.** Line 237 explains r6b's smaller effect partly by 33% more
capacity; the true figure is **100%**, so the mechanism the sentence names is
**twice as strong as stated** and the reasoning is strengthened rather than
undermined. That is the opposite of what happened to the same class of error in
r5's own outcome, where the correction *removed* an explanation
(`COMPLETE_JOIN_OUTCOME_2026-09-01.md` add. 2, item 6). Both are recorded here
so that the distinction is not lost: a void number can strengthen an argument or
destroy one, and which it does has to be checked case by case.

### The geometry table's r5 column becomes its r3 column, and the sentence under it does not survive

This is the finding that goes beyond arithmetic. Correcting items 2–4 leaves the
table reading:

| | this campaign | r5 (SE) | r3 (SE) | silicon |
|---|---:|---:|---:|---:|
| LLC | 10 MiB | **5 MiB** | 5 MiB | 60 MiB |
| table/LLC | 0.400 | **0.800** | 0.800 | 0.533 |
| victim/LLC | **0.533** | **0.518** | 0.518 | 0.533 |

**r5's column is now identical to r3's on all three rows**, which is not a
coincidence: r5 ran r3's cache geometry exactly, with the same 4 MiB table and
the same 2650 KiB victim against the same realized 5,242,880 B
(4,194,304/5,242,880 = 0.800 and 2,713,600/5,242,880 = 0.518, re-derived here).
The sentence immediately below the table therefore fails. Quoted rather than
deleted, per `A6.19`:

> The victim is sized to silicon's ratio, **which r5 missed** — its own audit
> named that miss as the reason its victim was under-stressed and its tax fell.

**The first clause survives and the second does not.** r5 did miss silicon's
victim ratio — 0.518 against 0.533 — but it missed it by 0.015 rather than by
0.188, and r5's own audit attributed its fallen tax to a *shrunken* victim ratio
that never occurred. That audit's explanation is void
(`COMPLETE_JOIN_OUTCOME_2026-09-01.md` add. 2), so it cannot be cited here in
support of anything. **This campaign's own reason for sizing the victim to
silicon's ratio is untouched** — matching silicon is a sufficient reason on its
own, and it does not need r5's miss to justify it. What is lost is a
corroborating citation, not a design decision. (The sentence quoted above is at
lines 66–67; the table it sits under is lines 60–64.)

The related claim at lines 69–70 that "at a 10 MiB LLC no power of two lands on
0.533" is about `probe()` masking the *table* to a power of two and is a
different quantization entirely. It is unaffected and correct, as is line 70's
closing "One ratio is matched and one is not; both are stated."

### What is deliberately not done

**`run_complete_join.sh` is not corrected, and must not be.** It is the committed
transcript of what r5 actually ran, and `F13`'s lesson is that a launcher's whole
value is that it reproduces its run. Changing `7680KiB` to `5MiB` there would
make it reproduce a *different* run — bit-identically, as §1 of the source record
proves, which is exactly what would make the substitution undetectable. The same
applies to this document above the line: it is what was registered, and it is
corrected by this addendum rather than by revision.
