# Outcome — sourced kernel test aggregate, 2026-09-03

Replaces the unlocatable "38 assertions pass and eight skip" cited in
`Sec7_Evaluation.tex:102-107` and `Sec6_Implementation.tex:70`. That aggregate
matched no committed log; these are reproducible from the recipe below.

## Result

Two boots. The first reproduces the tree as found, plus the THP guard; the second
adds the fork errno fix, 1 GiB huge pages, and KSM.

| | run 1 | run 2 |
|---|---:|---:|
| `streaming_basic` | 10 / 0 / 0 | 10 / 0 / 0 |
| `streaming_reject` | 15 / **1** / 1 | 17 / 0 / 0 |
| `streaming_hugetlb` | 7 / 0 / 6 | 13 / 0 / 0 |
| `streaming_memfd` | 3 / 0 / 0 | 3 / 0 / 0 |
| `streaming_lifecycle` | 4 / 0 / 0 | 4 / 0 / 0 |
| **kselftest total** | **39 / 1 / 7** | **47 / 0 / 0** |
| KUnit `pat_streaming` | 10 / 0 / 0 | 10 / 0 / 0 |

(pass / fail / skip. Plan total is 47 = 10+17+13+3+4.)

**Citable figure: 47 kselftest assertions pass, none fail, none skip, alongside 10
KUnit assertions.** Run 1 is retained because the difference between the two rows
is the evidence for each fix below.

### The shipped FS-guest kernel now produces this too

Runs 1 and 2 were built in a throwaway tree. `linux/.config` has since been changed
to `CONFIG_TRANSPARENT_HUGEPAGE=y` (madvise default), `CONFIG_KSM=y` and
`CONFIG_USERFAULTFD=y`, and `linux/vmlinux` rebuilt. The shipped kernel scores
`47 / 0 / 0` kselftest and `10 / 0 / 0` KUnit in **both** THP modes:

| boot | kselftest | KUnit |
|---|---|---|
| default (`madvise`) | 47 / 0 / 0 | 10 / 0 / 0 |
| `transparent_hugepage=always` | 47 / 0 / 0 | 10 / 0 / 0 |

The `always` row matters: that is the configuration in which the khugepaged defect
would have manifested, and the kernel that ships now passes its full suite there.

- Previous kernel: `sha256 3039d245...`, backed up whole (`vmlinux`, `bzImage`,
  `.config`) to `/home/domin/kernel_backup_2026-09-03/`.
- New kernel: `sha256 4060c071...`.

THP is left at the **madvise** default rather than `always` on purpose. `always`
would silently convert every sufficiently large anonymous mapping in the guest to
2 MiB pages and change the TLB and fault behavior of every FS benchmark; `madvise`
compiles the guard in and leaves existing runs comparable. Booting with
`transparent_hugepage=always` exercises the risk path when wanted.

**One thing this changed that is worth knowing.** `alloc_bytes()` in
`cxl_join_bench.cpp:419-426` handles `--huge2m` by trying
`mmap(MAP_HUGETLB|MAP_HUGE_2MB)` and, on failure, falling back to
`madvise(MADV_HUGEPAGE)`. With THP compiled out, that fallback was a no-op, so
`--huge2m` in a guest with no hugetlb pool silently delivered 4 KiB pages — an F9
requested-vs-realized case. No committed gem5 record is affected: `"huge2m":true`
appears only in `silicon_e2e_calib_v4.jsonl` and `silicon_e2e_hashjoin.jsonl`, both
of which ran on the silicon host. Future guest runs using `--huge2m` will behave
differently from past ones.

### Relation to the paper's 38 / 8

The paper's figures sum correctly: 38 pass + 8 skip + 1 errno defect = 47, exactly
the plan total. The aggregate was structurally real and simply had no surviving
log. It is now superseded: the errno defect is fixed rather than disclosed, and
the skips were host provisioning rather than anything conditional in the type.

## The fork errno defect: found live, then fixed

Run 1 failed one assertion:

```
not ok 12 fork during STREAMING epoch was not rejected (child=-1 errno=12 status=0)
```

`errno=12` is `ENOMEM`. **The paper's description of this defect was correct, and an
earlier audit note calling it stale was wrong.** Reading `kernel/fork.c:651` alone
shows `retval = -EBUSY` and suggests the paper is out of date. The errno does not
survive the return path:

- `dup_mmap()` sets `retval = -EBUSY` and returns it.
- `dup_mm()` captures it, hits `goto free_pt`, and returns `NULL`. The function
  returns `struct mm_struct *`, so the errno is discarded.
- `copy_mm()` sees the `NULL` and substitutes `return -ENOMEM`.

The comment at `fork.c:642-645` says the check was hoisted above `__mt_dup()` so
allocation pressure could not turn the refusal into `ENOMEM`. That hoist fixed the
livelock it was written for but not the errno, which was still laundered one frame
up — unconditionally, rather than only under pressure.

**Fix:** `mm_streaming_forbids_dup()` in `kernel/fork.c`, called from `copy_mm()`
before `dup_mm()`, where an errno can still be returned. `dup_mmap()`'s check is
left in place; it now covers only the narrow race where a VMA is sealed after the
read lock is dropped, and in that race the errno degrades to `ENOMEM` without
admitting the copy.

**Evidence:** the same assertion in run 2 reads
`ok 12 fork during STREAMING epoch -> EBUSY`. Nothing else changed between the two
runs that touches this path.

## THP guard

The validation kernel in `linux/.config` has `CONFIG_TRANSPARENT_HUGEPAGE` **not
set**. Every previously reported kernel test result was produced on a build where
this failure mode cannot occur, while the paper discusses behavior under
`transparent_hugepage=always`. Both runs here enable it.

Fix: `__thp_vma_allowable_orders()` (`mm/huge_memory.c:126-129`) refuses all orders
for a VMA carrying `VM_STREAMING`, and `MADV_NOHUGEPAGE` is now permitted on
streaming VMAs (`mm/madvise.c`), since refusing it removed the owner's only
defensive call while granting no protection.

**Negative control:** with the guard deleted and the kernel rebuilt, both
assertions in `streaming_vma_allows_no_thp_order_test` fail — on the collapse path
(`in_pf=false`) and the fault path (`in_pf=true`). A sealed streaming VMA was
genuinely eligible for THP on both before the fix.

The companion case `streaming_4k_encoding_at_pmd_is_uc_minus_test` pins the reason
as arithmetic rather than prose: the 4K slot-6 encoding has bit 7 set, that bit is
PSE at a leaf, and the surviving `PCD`-only encoding is slot 2, UC-.

## Why run 1's seven skips were not real skips

Six were `streaming_hugetlb` reporting `1GB: no 1GB hugepages reserved`; gigantic
pages must be reserved on the kernel command line, not through the runtime sysfs
knob. One was `streaming_reject` case 6, `MADV_MERGEABLE unavailable`, with KSM not
enabled. Run 2 reserves four 1 GiB pages at boot and enables KSM, and all seven
convert to passes. None of them were conditional on anything in the type.

## Recipe

```
rsync -a --exclude=.git linux/ <build>/ && cd <build> && make mrproper
cp linux/.config .config
scripts/config --enable TRANSPARENT_HUGEPAGE --enable TRANSPARENT_HUGEPAGE_ALWAYS \
  --enable KUNIT --enable PAT_STREAMING --enable PAT_STREAMING_KUNIT_TEST \
  --enable HUGETLBFS --enable HUGETLB_PAGE --enable USERFAULTFD --enable KSM \
  --enable BLK_DEV_INITRD --enable DEVTMPFS --enable DEVTMPFS_MOUNT
make olddefconfig && make -j48 bzImage

# five tests built static, packed into an initramfs with busybox as /init
qemu-system-x86_64 -nodefaults -m 8192 -smp 4 -cpu host -enable-kvm \
  -kernel arch/x86/boot/bzImage -initrd initramfs.cpio.gz \
  -append 'console=ttyS0 rdinit=/init kunit.enable=1 transparent_hugepage=always \
           default_hugepagesz=2M hugepagesz=1G hugepages=4 panic=1' \
  -no-reboot -nographic -serial stdio
```

Artifacts in `experiments/asplos/data/kernel/`: `guest_boot_2026-09-03.log` (run 1),
`guest_boot_1g_2026-09-03.log` (run 2), `initramfs_init_2026-09-03.sh`.

## Caveats

- QEMU/KVM guest, not gem5 and not the silicon host. It establishes what the ABI
  does, not what the hardware does.
- Run 2's kernel carries two fixes not present in the tree that produced any
  previously reported result. It is not a re-measurement of the old kernel.
- Nothing here reruns the gem5 FS boot that produced the original KUnit `pass:8`
  line.

---

## Addendum — 2026-09-04: two measurement families for H2 transition latency, and which to cite

The logs this record owns carry a second quantity besides the assertion counts:
`streaming_lifecycle` case 4 prints `H2 transition 8MiB: enter_avg=… enter_max=…
exit_avg=…`. That quantity now exists in **two families**, and until today no
record distinguished them. Both are the same code measuring the same thing —
`GENERATIONS 8` iterations of an 8 MiB `mprotect` seal/retire pair, timed with
`clock_gettime(CLOCK_MONOTONIC_RAW)`
(`tools/testing/selftests/mm/streaming_lifecycle.c:32,56,175-178`) — so the
difference is entirely platform, not workload.

| family | platform | `enter_avg` | `enter_max` | `exit_avg` |
|---|---|---:|---:|---:|
| **A — QEMU/KVM** `guest_boot_2026-09-03.log:452` | QEMU i440FX, **KVM**, Xeon Platinum 8592+, 4 vCPU | 90 µs | 156 µs | 76 µs |
| A — `guest_boot_1g_2026-09-03.log:453` | as above | 90 µs | 168 µs | 77 µs |
| A — `guest_shipped_always_2026-09-03.log:453` | as above, `thp=always` | 87 µs | 156 µs | 81 µs |
| A — `guest_shipped_madvise_2026-09-03.log:454` | as above, `thp=madvise` | 72 µs | 85 µs | 75 µs |
| **B — gem5 FS/CHI** `…os_contract_r12_lifecycle/system.pc.com_1.device:9` | gem5 full-system, atomic, CHI, 2 CPU | 124 µs | **999 µs** | 124 µs |
| B — `…os_contract_r7_h2_lifecycle/…:9` | as above | 124 µs | **999 µs** | 124 µs |
| B — `…os_contract_r13_lifecycle/…:9` | as above | 124 µs | **999 µs** | 124 µs |
| B — `…os_validation_h2_lifecycle/…:9` | as above | 124 µs | **999 µs** | **249 µs** |

### Why they differ, checked rather than assumed

The obvious hypothesis is "gem5's timing model is slower than silicon". **That
is not what is happening, and the real reason changes how family B may be
cited.** Family B is **clock-resolution-limited**: the numbers are quantisation
artifacts, not resolved means.

The gem5 guest cannot use a fine clocksource. Its boot log
(`gem5/logs/fs_boot_ckpt/atomic_2cpu_os_validation_h2_r1_16g/system.pc.com_1.device`)
reads `tsc: Marking TSC unstable due to TSCs unsynchronized` and then
`clocksource: Switched to clocksource refined-jiffies`. At `CONFIG_HZ=1000`
(confirmed in `linux/.config`) one `refined-jiffies` tick is **999 848 ns**, so
`CLOCK_MONOTONIC_RAW` in that guest advances in ~1 ms steps. Every family-B
figure follows arithmetically:

- `enter_max` = one tick = 999 848 / 1000 = **999 µs** — identical in all four
  logs, which a genuine maximum across independent runs would not be.
- `enter_avg` = one tick over `GENERATIONS 8` = 999 848 / 8 / 1000 = **124 µs**.
- `exit_avg` = 249 µs in `os_validation` = **two** ticks over 8 = 1 999 696 / 8 /
  1000 = **249 µs**.

So the honest reading of family B is: **across 8 seal/retire pairs the guest
clock advanced by one or two ticks in total**, i.e. seven of the eight samples
returned a **0 ns delta** — each transition was *below the resolution of the
clock measuring it*. 124 µs is not a measurement of 124 µs; it is one ~1 ms tick
divided by eight. It bounds a transition at **≲ 1 ms** and says nothing finer.

Family A is genuinely resolved: `kvm-clock` (`clocksource: Switched to
clocksource kvm-clock`, TSC 1900 MHz) has nanosecond granularity, and the data
behaves accordingly — the maxima differ run to run (85, 156, 156, 168 µs) and
the means spread 72–90 µs, which is real per-sample variation rather than a
repeated constant.

### Which to cite, for what

1. **For the magnitude of baseline H2 entry — cite family A: 72–90 µs**, four
   independent boots, `data/kernel/`. It is the only resolved measurement of the
   quantity, and it runs on real silicon under KVM, so the `mprotect` path,
   page-table walk and TLB shootdown execute at hardware speed.
2. **For "the model that produced the CHI results agrees" — cite family B, with
   the limit stated.** Its value is corroborative and architectural, not
   numeric: the same kernel in the gem5 full-system CHI configuration that
   produced the paper's H2 results also completes entry in **under a
   millisecond**. Write it as "below the guest clock's ~1 ms resolution", not as
   "124 µs".
3. **Neither family measures a `WBNOINVD` broadcast, so neither is comparable to
   the ~48 ms figure.** That is a *third* platform — the 64-logical-CPU silicon
   host (`SUBMISSION_READINESS_2026-08-19.md` C10, "48 ms measured on silicon").
   The 48 ms and the µs figures are **not two measurements of one operation**:
   the oracle build issues a machine-wide clean, the baseline issues none.
   The gap is a *mechanism* change (`888060f6a66e`, `eccecc49e0ff`), and only
   secondarily a platform difference. QEMU cannot reproduce `WBNOINVD` cost at
   all — the reason `SUBMISSION_TODO_2026-08-19.md` item 2 asked for bare metal.

### Consequence for records already citing 124 µs

`STATE_2026-08-30.md`, `STATE_2026-09-01.md` (addendum 9) and commit `e9534a6`
cite the gem5 **124 µs** as the corrected baseline entry cost. **Their
conclusion is unaffected and their direction is right** — both families put
entry in microseconds, three orders of magnitude below 48 ms, so the correction
those documents make is if anything *understated*. What is imprecise is only the
figure's status: 124 µs is a quantisation-limited upper bound, and 72–90 µs is
the resolved number. A future draft quoting a single value for baseline H2 entry
should quote **72–90 µs (QEMU/KVM)** and, if it needs one number, ~90 µs as the
conservative end. Those documents are not edited here; this addendum is the
pointer. **No measurement was launched for this note** — it is arithmetic over
already-committed logs.
