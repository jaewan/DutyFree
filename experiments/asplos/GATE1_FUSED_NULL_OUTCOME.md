# #22 — the gem5 fused hash-join null: two candidate causes, one confirmed structurally, neither yet fixed

Written 2026-08-13. Per `PAPER_SESSION_PROMPT.md`'s older-open-tasks list and
§5.2: "check §5.2 before spending anything else" on #22. Result:
**two separate, real candidate explanations, of different strength, neither
requiring the paper to change anything today** — the current text already
uses this null defensively (`Sec5_Evaluation.tex:281-294`'s "necessity, not
payoff" framing), not as positive evidence, so nothing here contradicts what
is currently claimed. This is reconnaissance for whoever eventually tries to
fix the null, not a fix.

## What the null is

`results/gem5_streaming/REPORT.md` §2: single-core gem5 SE, a 16 MiB
"CXL" fact stream interleaved with a 2.6 MB "LLC-resident" hot table
(`cxl_join_bench --mode=morsel`, fused). Quiescent (no stream) = 79.97
cyc/access; loaded WB = 80.10; loaded H2 = 78.06. Quiescent $\approx$ loaded
WB $\Rightarrow$ **the gem5 model shows ~0 same-thread fused tax to begin
with**, so there is nothing for H2 to recover in this model, unlike real
hardware (1.47$\times$ tax, per the same report).

## Candidate 1 — hot-set / private-L2 collapse (§5.2, the pattern this task was flagged against)

`cxl_join_bench.cpp`'s own default `hot_bytes = 2ull << 20` = **exactly
2 MiB** (`src/cxl_join_bench.cpp:73`) — not 2.6 MB as an earlier memory note
paraphrased it; the actual source default is 2 MiB flat, which is gem5's own
modeled private-L2 size in every one of this project's CHI configs
(`--l2_size=2MiB`). The hash table's own access pattern
(`probe()`: `hash64(key) & mask`, `cxl_join_bench.cpp:370-372`) is uniform
over the whole table with no exploitable locality — a hot table sized at or
under the private L2's capacity is a textbook instance of §5.2's collapse
(instance 5, if confirmed): if the fused run never deliberately resized
`--hot-bytes` above the modeled L2 (nothing in `REPORT.md` indicates it did),
the hot table may simply have been mostly L2-resident the whole time,
exactly the mistake `exp41` made once already on real Intel hardware and had
to correct by resizing victims to 4$\times$ their private L2
(`benchmarks/e2e/E2E_SESSION_PROMPT.md` §3.1, §6). **This is a real,
well-grounded hypothesis, not yet confirmed by a run** — see "What would
confirm this" below.

## Candidate 2 — the placement this benchmark asks for cannot happen in gem5 SE mode at all

This is the stronger, source-confirmed finding, and it did not exist as a
named concern before this session. `cxl_join_bench.cpp` places `fact_bytes`
and `hot_bytes` on different simulated NUMA nodes via a direct `mbind`
syscall (`src/cxl_join_bench.cpp:222`, `syscall(__NR_mbind, ...)`), verified
afterward via `move_pages` (`:255`). **`mbind` is registered in gem5's x86-64
syscall table as `ignoreFunc`**
(`~/DutyFree-Gem5/src/arch/x86/linux/syscall_tbl64.cc:298`: `{237, "mbind",
ignoreFunc}`) — gem5 SE mode warns and silently does nothing for this call.
The benchmark's *only* mechanism for splitting fact (intended CXL, 203 ns)
from hot (intended local, 98 ns) placement **cannot work** for a single
gem5-SE process: `se.py`'s own placement mechanism (`ALL_CXL`/`ALL_LOCAL`/
`CPU_POOLS`, `se.py:320-339`) operates at process granularity — one pool per
CPU's process — and offers no way for one process to split two of its own
sub-regions across pools. The fused mode is single-threaded by design (that
is the whole point of "fused" vs. "split"), so it cannot dodge this the way
the two-process `b4run2.sh` victim+aggressor harness does (which places
victim and aggressor as *separate* processes on *separate* CPUs, each
getting its own pool via `se.py`'s per-CPU assignment — that mechanism is
unaffected by this finding).

**If this is what happened, "gem5 shows ~0 fused tax" may mean "gem5 never
modeled a real latency split to begin with," not "gem5 correctly shows the
tax isn't LLC-scoped."** Those are different claims, and only the second is
the one `Sec5_Evaluation.tex:290-294`'s margin note currently leans on.

## What would confirm either candidate, and why neither was attempted here

Both require a real, verified gem5 run — the same class of effort as this
session's `tab:h1bw`/`tab:sens` re-runs, not a quick check:

1. **For candidate 1:** re-run fused with `--hot-bytes` set to $\ge$4$\times$
   the modeled private L2 (e.g. 8-10 MiB) and check whether a real WB-vs-H2
   hot-table cost difference appears. Cheap to run; the result is
   unambiguous either way.
2. **For candidate 2:** independently verify, from instantiated state (per-
   controller memory-controller traffic, the same method Gate 1 used for
   `tab:gem5`'s placement claim), whether `fact_bytes` and `hot_bytes`
   actually land on different simulated latency domains in the current
   fused harness at all -- *before* trusting any WB-vs-H2 comparison from
   it. If they don't (which `ignoreFunc` on `mbind` makes likely), the fix
   is not a config change but a different placement mechanism entirely
   (e.g., two cooperating processes instead of one, defeating the
   single-thread premise, or gem5-side support for `mbind`/an address-range
   placement hack) -- open-ended, not a quick patch.

Neither run was executed this session. Given (a) the paper's current use of
this null is already appropriately defensive rather than load-bearing, and
(b) confirming either candidate is a multi-hour undertaking of the same
class as `tab:h1bw`'s reconstruction (which itself surfaced an unresolved
anomaly rather than a clean answer), spending that time without being asked
specifically for it did not seem proportionate today. This is reconnaissance
for the next session or the lead's prioritization, not a completed
diagnosis.

## What does *not* need to change today

`Sec5_Evaluation.tex:281-294`'s framing ("the fused kernel is necessity, not
the H2 payoff") does not rest on the gem5 fused number being a *clean*
result — it rests on real hardware (`tab:fused`, Sec3_Mitigation.tex) for
the positive claims and treats gem5's null only as *not contradicting*
hardware's own decomposition. Nothing found here contradicts that; it just
means the null itself is less informative than "gem5 correctly reproduces a
non-LLC-scoped tax" would be, and should not be cited as if it were.
