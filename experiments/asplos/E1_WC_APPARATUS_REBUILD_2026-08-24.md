# Item 11: the module's guards are validated — and one of them was broken

## What was done

`cxl_memtype_RECONSTRUCTED.ko` built and its three refusal paths exercised
against the live kernel on mos181. Nothing was ever mmap'd; no measurement was
taken. Item 11's "module loads, devices appear, a read succeeds" is **partially
met**: the safety logic is now proven, the mmap path is not, and §2 explains why
it cannot be on any host we currently have.

## A safety guard I wrote, asserted, and had wrong

The original check was

    if (region_intersects(base, len, IORESOURCE_SYSTEM_RAM, IORES_DESC_NONE)
        == REGION_INTERSECTS) { refuse; }

I committed that as "refuses any range intersecting System RAM" and said so in
the commit message. **It does not.** Linux's enum is
`REGION_INTERSECTS = 0, REGION_DISJOINT = 1, REGION_MIXED = 2`, and a range that
spans System RAM *and* an adjacent Reserved region returns **`REGION_MIXED`**,
which the `== REGION_INTERSECTS` test let straight through.

Demonstrated, not reasoned about: `insmod base=4096 len=4194304` — squarely
inside the first System RAM range — **loaded successfully** and registered
`/dev/cxl_wc` over `[0x1000, 0x401000)`. It was unloaded within seconds and
nothing had mapped it, but a WC alias of write-back kernel memory is an
architectural aliasing hazard, not merely a bad measurement, and the guard whose
entire job was to prevent that did not.

Fixed to require the only safe answer:

    ri = region_intersects(...);
    if (ri != REGION_DISJOINT) { refuse; }

Re-tested: `base=4096` now refuses with `region_intersects=2` (MIXED), and
`base=0x1000000000` refuses with `region_intersects=0` (INTERSECTS). Missing
parameters and misalignment refuse as before. Nothing loads.

**This is the fifth instance today of asserting a property instead of testing
it**, and the only one where the untested assertion was a safety claim. The
lesson is narrower than the earlier four: *a guard is not a guard until you have
watched it refuse the thing it exists to refuse.* Guards 1 and 2 passed on the
first try, which is exactly why guard 3 needed exercising rather than assuming
the pattern held.

## The re-measurement is a platform reconfiguration, not a module load

This changes the cost of items 11–13 and was not visible before building the
module.

`/dev/cxl_wc` must map the CXL window as a **device** with a WC attribute. On
mos181 the CXL expander is **onlined as a cpuless NUMA node** — node 2 reports
264 GB `MemTotal` across 129 memory blocks — so the kernel maps it write-back as
ordinary System RAM, and `/proc/iomem` shows **no soft-reserved window** for it.
The guard therefore refuses it, correctly.

So the original E1 apparatus required the CXL window **soft-reserved and not
onlined**. That is a different platform configuration from what these hosts run.
Consequences:

1. **Item 11 cannot be completed on mos181** without offlining 264 GB of live
   memory on a shared machine. Not attempted; out of scope.
2. **Items 12–13 cost more than "load a module" even once broker returns** — the
   CXL window has to be taken out of the NUMA configuration first, which is a
   reboot-class or memory-hotplug-class change to a shared host, and the
   published AMD WB arm reads ordinary cacheable memory *on that same node*, so
   the WB and WC arms may not be runnable in one boot configuration.
3. That is worth stating in the paper's artifact note alongside the existing
   "apparatus no longer available" disclosure: the arm needs a platform state,
   not just a driver.

## Status

| item | state |
|---|---|
| 11 | **partial** — guards validated (and one fixed); mmap path unvalidated, blocked on platform state |
| 12 | blocked on broker **and** on §2's configuration requirement |
| 13 | same |
| 14 | blocked on broker only (RocksDB needs no WC mapping) |

Broker itself: escalation exhausted — direct SSH on 9812, `ProxyJump` via c4, and
`ssh` from c4 on both 22 (refused) and 9812 (identical `kex` reset). Pings at
0.487 ms with the port open from two sources, so sshd is listening and rejecting
every handshake.
