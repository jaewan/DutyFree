# Session prompt: close the OS→hardware loop for STREAMING in gem5 FS mode

Paste everything below the rule into a fresh session. Written 2026-08-23.
OSTA structure (Objective / Scope / Task / Acceptance), per house format
(`GEM5_FUSED_NULL_SESSION_PROMPT.md`).

Deadline context: ASPLOS Sept cycle closes **2026-09-09**. This work has 17
days of calendar and is not the only thing competing for them. Task ordering
below is cheapest-first *specifically* so that a stall at T4 costs you T1–T3's
build time and nothing else.

---

## O — Objective

**Buy one claim that no other experiment in this project can buy:**

> The OS declares an object Streaming by writing PAT slot 6 into the page
> tables via `mprotect(PROT_STREAMING)`; the hardware reads that declaration
> off the ordinary translation and skips LLC fill (H2) and snoop-filter
> enrolment (H3). No magic instruction anywhere in the loop.

Every gem5 STREAMING number this project currently owns was produced by a
**pseudo-instruction**, not by the OS. `gem5/testcase/dutyfree/aggressor.c:24`:

```c
static inline void gem5_set_streaming(void *addr, long size) {
    __asm__ volatile(".byte 0x0f, 0x04, 0x55, 0x00"   /* M5OP 0x55 */
                     : : "D"((long)addr), "S"(size) : "rax");
}
```

That validates the hardware half (H2/H3 do what the paper says) and says
nothing at all about the OS half (I0/I1). The paper claims an
*OS-declared, page-granular, enforced* contract. A reviewer who notices that
the simulator learns about Streaming through a backdoor m5op will read the
whole §4 contract as unvalidated. **FS mode with the custom kernel is the only
configuration in this repository that closes that loop.**

Secondary objective, free if the primary succeeds: an FS number that agrees
with the SE number is a cross-check on both.

---

## Verified ground truth — do not re-litigate any of this

Each line was checked against the tree on 2026-08-23. Cited so you can confirm
in one command rather than rediscovering by search.

**Both halves of the contract are implemented.**

| what | where | state |
|---|---|---|
| OS: PAT slot 6 transitions, PTE rewrite, WBNOINVD drain | `linux/mm/streaming.c` | implemented |
| OS: `PROT_STREAMING` = `0x10` | `linux/include/uapi/asm-generic/mman-common.h:14` | implemented |
| OS: `VM_STREAMING` = `VM_HIGH_ARCH_4`, cleared unless re-passed | `linux/include/linux/mm.h:362-377` | implemented |
| OS: read-only enforcement (`PROT_STREAMING\|PROT_WRITE` → `EINVAL`) | `linux/mm/mprotect.c:745-750` | implemented |
| OS: Kconfig symbol | `linux/arch/x86/Kconfig:1819` `CONFIG_PAT_STREAMING`, `depends on X86_64 && X86_PAT`, **`default n`** | implemented |
| gem5: PAT slot 6 decode from real PTEs | `gem5/src/arch/x86/pagetable_walker.cc:360-390` (PMD leaf bit 12, 4K PTE bit 7) | implemented |
| gem5: H2 + H3 predicate | `gem5/src/mem/ruby/protocol/chi/CHI-cache-funcs.sm:825-836`; param `enable_H3_streaming_bypass` at `CHI-cache.sm:146` | implemented |
| gem5: build variant | `gem5/build_opts/Intel_8592` (`RUBY=y`, `PROTOCOL="CHI"`, `NUMBER_BITS_PER_SET=256`, `USE_X86_ISA=y`) | committed |
| gem5: FS boot + checkpoint | `gem5/scripts/fs_boot_checkpoint.sh` | written |
| gem5: FS restore into O3+CHI | `gem5/scripts/fs_restore_chi_8592.sh` | written |
| gem5: SE reference sweep | `gem5/scripts/intel_8592_{4,8}cpu_dirtax_streaming.sh` | written |

**What is absent on this host, and is the entire job:**

| artifact | state |
|---|---|
| `gem5/build_Intel_8592/gem5.opt` | absent — no gem5 build here |
| `scons` | not on PATH, not importable as a Python module |
| `linux/vmlinux` | absent — submodule is source only, no `.config` |
| `~/.cache/gem5/` | **directory does not exist** — no disk image |
| any benchmark `.rcS` | absent. `gem5/configs/boot/` holds only `hack_back_ckpt{,_delay5}.rcS`, `bbench-*.rcS`, `halt.sh` |
| `gem5/logs/` | empty — no prior FS run on this machine |

**`c3` is not reachable and is not needed.** Only `broker` (moscxl) and `c4`
(mos182) are configured in `~/.ssh/config`. This host — mos181, **256 cores,
1.2 TB RAM** — is a better build and run machine than c3 plausibly was. Do not
spend time trying to reach c3.

**Submodule state:** both `gem5` and `linux` are on detached HEAD.
`gem5` = `356e7b7d0e`, `linux` = `b9f60fafda72`. Do not check out branches.
Do not `git push` from any repository in this session.

---

## S — Scope

### In scope

- Installing build tooling, building `gem5.opt`, building `vmlinux`.
- Obtaining or reconstructing the FS disk image.
- Writing the benchmark `.rcS` that does not currently exist.
- Running SE and FS arms and recording what they produce.
- Committing all of the above to `~/DutyFree`.

### Out of scope — do not touch

- **`~/STREAMING_Paper/`.** Every write there is published to the co-authors
  automatically. Do not edit, do not build, do not `git push`. Write findings
  into `~/DutyFree` and let the lead move them.
- **Any silicon campaign.** No aggressor, no DuckDB, no resctrl group, no CAT
  mask. This host runs other people's measurements; a gem5 build with `-j` is
  already antisocial enough. See "Cost and courtesy" below.
- **`cxl_join_bench.cpp` semantics.** If the workload needs a change to run
  under FS, that is a finding to report, not a change to make silently.
- **The frozen SE geometry**, except where T2 explicitly authorises a sweep.
  Apparatus is not changed mid-campaign beyond the minimum required to run at
  all.
- **DuckDB / GAPBS / HNSW under gem5.** They cannot run under O3+Ruby CHI in
  the time available and are not the target. `cxl_join_bench` is the designated
  stand-in and is already the FS image's installed workload. If you find
  yourself sizing a DuckDB run for the simulator, stop — you have drifted.

---

## T — Task

Five tasks, cheapest-first. **Each has an explicit gate. Do not start task N+1
until task N's gate has passed and you have said so in writing.** The point of
the ordering is that T4 is the one that may be impossible, and it should cost
you as little as possible to find that out.

### T1 — Build `gem5.opt`

```bash
cd ~/DutyFree/gem5
# prefer a venv or --user install; record which you used and the version
python3 -m pip install --user 'scons>=4.5'
scons defconfig build_Intel_8592 build_opts/Intel_8592
scons build_Intel_8592/gem5.opt -j 64
```

`-j 64`, not `-j 256`. See "Cost and courtesy".

One discrepancy to resolve rather than guess at: `REPO_DISCIPLINE.md` §6 writes
the seeding step as `scons defconfig build_<variant>/gem5.opt
build_opts/<variant>`, i.e. with `/gem5.opt` appended to the build directory.
Upstream gem5's `defconfig` takes a build *directory*, not a target. One of the
two is wrong. Try the form above first, and if `defconfig` rejects it, use the
§6 form — then **fix whichever document is wrong** and say so in the commit.

**Gate T1.** All three must hold, and you must show the output of each:

1. `build_Intel_8592/gem5.opt --version` runs.
2. `grep -c 'enable_H3_streaming_bypass' build_Intel_8592/mem/ruby/protocol/CHI_Cache_Controller.hh` (or wherever SLICC emitted it) is non-zero — i.e. **H3 survived the build**, it is not merely in the `.sm` source.
3. The resolved config actually matches `build_opts/Intel_8592`: `PROTOCOL="CHI"`, `NUMBER_BITS_PER_SET=256`, `USE_X86_ISA=y`. Diff `build_Intel_8592/gem5.build/*/config` against the checked-in defconfig and paste the diff, even if empty.

Per `REPO_DISCIPLINE.md` §2, a comment asserting the build is correct is a
*claim*; a config diff after a real build is a *verification*. Only the second
counts.

### T2 — Reproduce the SE streaming sweep

No kernel and no disk image are needed for this. It is the cheapest thing that
can tell you whether H2/H3 still behave at gem5 `356e7b7d0e`, and it produces
the baseline that T5's FS run must agree with.

Run **`intel_8592_4cpu_dirtax_streaming.sh`, not the 8cpu variant.** The 8cpu
script demands `--mem-size=512GiB --cxl-mem-size=256GiB` and launches 15
concurrent simulations; the 4cpu one is the same experiment at a quarter of the
cost and is sufficient to establish that the mechanism engages.

The three arms are `alone` / `with_agg` (WB) / `with_streaming` (H2 via m5op).

**Falsifiable prediction — write it down before you launch.** `with_agg` shows
a tax over `alone` at the larger WSS points, and `with_streaming` recovers a
visible share of it. If `with_agg ≈ alone`, there is **no tax to remove** and
H2 has nothing to recover — that is the *already-diagnosed* fused-null failure
mode (`GEM5_FUSED_NULL_SESSION_PROMPT.md`), not a new discovery, and it means
the geometry is wrong rather than the mechanism.

**Gate T2.** A table of the three arms across the WSS sweep, plus the H2
engagement counter (LLC fills should drop materially in `with_streaming`
relative to `with_agg`). **Never report a loaded number without its own
quiescent baseline from the same config** — omitting that is exactly what once
made a −2.5% run-noise excursion look like a result.

If the sweep shows no tax at any WSS point: **stop and report.** Do not start
tuning geometry. That is a pre-existing, documented, unresolved problem with
its own session prompt, and inheriting it here would consume the entire budget.

### T3 — Build `vmlinux` with `CONFIG_PAT_STREAMING=y`

```bash
cd ~/DutyFree/linux
make x86_64_defconfig
./scripts/config --enable PAT_STREAMING
./scripts/config --enable X86_PAT          # PAT_STREAMING depends on it
# gem5 FS needs a console and a disk it can see; add whatever the boot
# actually requires and record every option you added and why.
make olddefconfig
make -j 64 vmlinux
```

**`CONFIG_PAT_STREAMING` is `default n`.** A kernel built without it compiles,
boots, and accepts `mprotect(PROT_STREAMING)` as an ordinary no-op prot bit —
and gem5 will then correctly observe that no page is Streaming and report no
benefit. **That failure is silent and looks exactly like a negative result.**
It is the single highest-probability way for this task to produce a
confidently-wrong conclusion.

**Gate T3.** Three checks, all of them, before the kernel is used for anything:

1. `grep PAT_STREAMING .config` shows `CONFIG_PAT_STREAMING=y`.
2. `nm vmlinux | grep -i streaming` resolves symbols from `mm/streaming.c`.
3. Build and run `tools/testing/selftests/mm/streaming_reject.c` **natively on
   this host first** (it is a userspace program; the negative cases assert
   `EINVAL` and do not need the custom kernel to *pass* — but running it tells
   you the ABI constant matches). Then confirm the KUnit tests are compiled in
   (`CONFIG_PAT_STREAMING_KUNIT_TEST`) so the boot log self-checks the PTE bit
   pattern for you inside the guest.

Check `.config` in to `~/DutyFree` as a config fragment (per
`REPO_DISCIPLINE.md` §6 — a build input that lives only in one machine's
working directory is the recurring defect class in this project).

### T4 — Obtain the disk image. **This is the task that may be impossible.**

Required: `~/.cache/gem5/x86-ubuntu-18.04-img-hashjoin-v2`, described in
`fs_boot_checkpoint.sh` as an image with the workload preinstalled at
`/root/cxl_join_bench.gem5fs` and, per `fs_restore_chi_8592.sh:26`, built with
`--line-stride` support. It does not exist on this host and was constructed
elsewhere.

**Timebox this to one working session.** In order:

1. Search `broker` and `c4` for it (`ssh broker 'ls -la ~/.cache/gem5/'`). It is
   plausibly nowhere but c3.
2. If absent: reconstruct. Take a stock gem5 x86-ubuntu image, mount it, build
   `cxl_join_bench` statically (`make gem5` in
   `benchmarks/e2e/hash_join/`, per `gem5_handoff.md`), install it at
   `/root/cxl_join_bench.gem5fs`. A reconstructed image is **not** the v2 image
   and must be named differently and disclosed as reconstructed — do not
   quietly reuse the v2 name.
3. If reconstruction stalls past the timebox: **stop, and report to the lead
   with the SE result from T2 in hand.** Do not push into T5.

**Gate T4.** The image boots to a shell under `fs_boot_checkpoint.sh` on
AtomicSimpleCPU and `/root/cxl_join_bench.gem5fs --help` runs inside the guest.

Note the script's own warning, which has bitten before: *do not launch restores
until the boot process has EXITED* — `m5.cpt` is still being written after the
checkpoint directory appears, and racing it yields a parse error that looks
like a corrupt checkpoint.

### T5 — The FS run that is the actual objective

Three things must be built or written first, none of which exist:

**(a) A benchmark `.rcS`.** `gem5/configs/boot/` contains no benchmark script.
Write one. It must, inside the guest: `m5 resetstats`, run `cxl_join_bench`
with the fact region declared via `mprotect(PROT_STREAMING)`, `m5 dumpstats`,
`m5 exit`.

**(b) The `PROT_STREAMING` call site in the workload.** `cxl_join_bench`
currently has no Streaming path — the SE arms got their declaration from the
m5op. Adding one `mprotect(fact_base, fact_len, PROT_READ|PROT_STREAMING)`
after the fact region is populated is in scope. **Ordering is part of the
contract, not an implementation detail**: populate the region with writes
*first*, declare it Streaming *second*, then read it read-only. The same
ordering constraint is spelled out at `gem5/testcase/dutyfree/aggressor.c:15-17`
and enforced by the kernel, which rejects `PROT_STREAMING|PROT_WRITE`
(`linux/mm/mprotect.c:745-750`). Check the `mprotect` return value and abort
loudly on failure — a silently-ignored `EINVAL` reproduces the T3 failure mode.

**(c) Three arms, at one geometry.** `WB` (no `mprotect`), `H2`
(`mprotect`, `enable_H3_streaming_bypass=False`), `H2+H3` (`mprotect`,
`enable_H3_streaming_bypass=True`), plus a **quiescent baseline from the same
config**.

Then:

```bash
cd ~/DutyFree/gem5
scripts/fs_boot_checkpoint.sh 2                       # 2 CPUs, not 8
scripts/fs_restore_chi_8592.sh atomic_2cpu_cxl_hj fs_streaming_wb  wb.rcS
scripts/fs_restore_chi_8592.sh atomic_2cpu_cxl_hj fs_streaming_h2  h2.rcS
scripts/fs_restore_chi_8592.sh atomic_2cpu_cxl_hj fs_streaming_h23 h23.rcS
```

**Gate T5 — the evidence that the loop closed.** The runtime numbers are
secondary. What this task exists to produce is proof that the declaration
travelled OS → PTE → TLB → CHI:

1. Guest-side: `mprotect` returned 0, and the region's PTEs carry
   PAT=1/PCD=1/PWT=0 (read `/proc/self/pagemap`, or the debugfs interface
   `mm/streaming.c` exposes).
2. gem5-side: the page-table walker classified those pages as streaming —
   instrument `pagetable_walker.cc:360-390` with a counter or a `DPRINTF` if no
   stat exists, and show a **non-zero** count in the H2 arm and **zero** in the
   WB arm. This is the single most important artifact of the entire task.
3. CHI-side: LLC fills materially lower in H2 than WB; snoop-filter
   back-invalidations materially lower in H2+H3 than H2.

Point 2 is the claim. Points 1 and 3 are its bookends. **If you can produce
point 2 and nothing else, the session was a success.**

**Expected shape of the result, so a partial recovery is not misread.** The
silicon and SE evidence both say H2 alone is nearly inert where a finite snoop
filter is in play — `H3SF_REMEASURED_2026-08-20` measures WB 2.501× → H2 2.512×
→ H2+H3 1.061×. If the FS run shows H2 ≈ WB and only H2+H3 recovering, **that
is the predicted result, not a failure.** Conversely, H2 alone recovering most
of the tax would contradict the existing gem5 result and needs explaining
before it is believed.

---

## Cost and courtesy

**The precedent that sets the tripwire.** The last gem5 attempt in this repo
(`GEM5_FUSED_NULL_OUTCOME.md`) ran three O3+Ruby arms for **1 h 11 min**, at
which point all three were still at 99.9% CPU and all three `stats.txt` were
still **zero bytes**. It was abandoned with no metrics. The intended "cheap
discriminator" was not cheap.

Therefore:

- **Tripwire.** If any single simulation reaches 90 minutes with a zero-byte
  `stats.txt`, stop it, record the wall time and the `simTicks` reached, and
  report. Do not let it run overnight hoping.
- Prefer **2 CPUs over 4, and 4 over 8**, at every step. Scale up only after a
  smaller configuration has produced a complete `stats.txt`.
- Insert `m5 resetstats` / `m5 dumpstats` around the measured region so a
  killed run still yields a partial dump.
- **This host is shared and hosts other people's silicon measurements.** Cap
  builds at `-j 64` of 256 cores, and do not launch a wide concurrent sweep
  while anything else is running. Check first; `benchmarks/e2e/lib/hostguard.py`
  run standalone (`python3 hostguard.py`) prints a survey and a verdict.

---

## Traps, each of which has already cost this project time

1. **`CONFIG_PAT_STREAMING` is `default n`.** Forgetting it yields a clean
   build, a clean boot, a successful `mprotect`, and a null result. T3's gate
   exists solely for this.
2. **A description that diverges from instantiated reality is the recurring
   failure mode here** (`REPO_DISCIPLINE.md` §3) — it has already appeared in
   resctrl schemata three times, in sysfs turbo conventions, and in perf event
   aliases. Verify every "this script does X" against what the run actually
   instantiated. `config.ini` and `stats.txt` are the authorities, not the
   script's comment header.
3. **`cmd | tee log; echo EXIT=$?` reports tee's exit code, not cmd's**
   (`REPO_DISCIPLINE.md` §8). Use `PIPESTATUS`.
4. **The restore geometry is `--l2_size=2MiB --l3_size=5MiB`** — a 40% L2:LLC
   ratio, against 0.6% on real EMR. That ratio is the diagnosed cause of the
   fused-null. It is fine for T5's purpose (proving the declaration travels),
   and it is **not** fine as the basis for a quantitative benefit claim. Say
   which of the two you are making.
5. **Do not report a loaded arm without its own quiescent baseline from the
   same config.**
6. **Do not fish.** If a number does not reproduce, say it does not reproduce.
   Hunting for the configuration that recovers a hoped-for figure is
   specifically forbidden (`§6.6`): *"When provenance is gone, say it is gone."*
7. **One logical change per commit** (`REPO_DISCIPLINE.md` §4), with provenance
   in the commit message, not only in a chat reply (§9).

---

## A — Acceptance

Done means **one** of these is established in writing, with artifacts. All four
are acceptable; the deadline makes an honest early stop worth more than a late
ambiguous result.

1. **Loop closed.** The custom kernel declares, gem5 decodes, CHI acts. A
   non-zero streaming-page count in the walker on the H2 arm and zero on WB,
   with the CHI-side effects to match. The paper gains the sentence it cannot
   currently write.
2. **Loop closed, benefit not quantifiable.** Declaration demonstrably travels
   end to end, but the geometry that is affordable to simulate yields no
   meaningful tax to recover. **This is a good outcome** — the contract claim is
   the objective; the magnitude claim is already carried by silicon and by the
   SE sweep. Report it as a capability demonstration and say plainly that the
   geometry does not support a magnitude claim.
3. **Blocked at T4.** No disk image, and reconstruction exceeded the timebox.
   Then the deliverable is T1–T3 (a working build, a working kernel, both
   committed and reproducible) plus T2's SE sweep, plus a precise statement of
   what the image would take. That is a real handoff, and it is far more than
   exists today.
4. **Refuted.** The kernel writes the PTE bits, and gem5's walker does not
   classify them. That is a genuine finding about the contract's
   implementability and is more valuable than any of the above. Report it
   immediately and do not attempt to patch around it.

### Deliverables, regardless of which branch

- A **pre-registration written before any measured run**, per house format
  (`GATE1_CORUN_PAIR_PREREGISTRATION.md`): geometry stated, falsifiable
  prediction per task, meaning of each outcome fixed in advance.
- `config_frozen.md` per `gem5_handoff.md` §8, including the L2:LLC and
  hot÷L2 ratio disclosures.
- Kernel `.config` fragment and the gem5 build config diff, both committed.
- An **outcome document** named for which acceptance branch was reached, in
  `benchmarks/e2e/hash_join/`, stating what was measured, what was not, and
  what a subsequent session would need.
- Commits to `~/DutyFree` only. **No `git push`, to any remote, at any point.**

### Escalate to the lead rather than deciding

- Anything that would change the SE reference geometry beyond T2's authorised
  sweep.
- Any change to `cxl_join_bench` semantics beyond adding the `mprotect` call.
- Spending beyond the T4 timebox.
- Any conclusion that would alter what the paper claims, as opposed to
  supporting or failing to support what it already claims.
