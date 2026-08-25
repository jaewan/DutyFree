# The STREAMING project, explained from scratch

**For a reader with no prior knowledge of this project.** It explains the idea,
why we thought it would work, how we test things and why that way, what we
found, and where it now stands. Nothing here assumes you have read any other
document.

---

# Part 1 — The problem

## 1.1 What a cache is, and why it can be spoiled

A CPU is much faster than memory. To hide that, chips keep recently-used data in
small fast memories called **caches**. There are three levels: **L1** (tiny, per
core), **L2** (bigger, per core), and the **LLC** — last-level cache — which is
large and **shared by every core on the chip**.

Sharing is the problem. When any program reads memory, the hardware
automatically copies that data into the LLC, evicting whatever was there. A
program that reads a huge amount of data *once* and never looks at it again will
sweep the entire LLC clean, throwing out data that a *different* program was
relying on. The first program gains nothing — it wasn't going to re-read its
data. The second program is badly hurt. This is **cache pollution**.

## 1.2 Why this is getting worse: CXL

**CXL** is a new way to attach extra memory to a server, over a cable rather
than directly. It gives you a lot more memory, but it is slower to reach —
roughly 100–150 nanoseconds further away than normal memory.

That extra distance matters because of how CPUs fetch data. A CPU can only have
a limited number of memory requests outstanding at once. If each request takes
longer, and you can't have more of them in flight, your total bandwidth drops.
The fix hardware already has is **prefetching**: the chip notices you are reading
sequentially and starts fetching ahead of you, so data arrives before you ask.

Here is the bind. On x86, **the setting that turns on aggressive prefetching is
the same setting that says "put this in the cache."** They are one decision, not
two. So a program streaming a huge file from CXL must choose:

- **Write-back (WB)** — the normal setting. Fast, prefetched, *and* it pollutes
  the shared cache.
- **Write-combining (WC)** — declines to pollute, but also gives up prefetching,
  so it is slow.

You cannot have "prefetch aggressively but don't keep it."

## 1.3 What we proposed

**STREAMING**: a new *memory type*. The operating system marks a region of memory
as "immutable, read-once" using a normal system call. The hardware sees that mark
**in the page table** — the structure it already consults on every memory access —
and behaves accordingly:

- **H1**: prefetch as aggressively as write-back (so it's fast)
- **H2**: don't put those lines in the shared cache (so it doesn't pollute)
- **H3**: since the data is promised immutable, skip coherence bookkeeping too

The appeal was that this costs almost nothing to build. x86 already has a
mechanism called **PAT** that lets a page table entry select one of eight memory
types, and one slot is unused. So the proposal needs **no new architectural
state** — just a new meaning for an existing empty slot, plus two checks on the
cache fill path.

## 1.4 The five things that had to be true

We wrote the argument as a chain. All five links must hold:

| link | claim |
|---|---|
| **L1** | Someone actually wants this |
| **L2** | No existing interface can express it |
| **L3** | The harm really comes from cache *allocation*, not just from moving bytes |
| **L4** | An OS can enforce it and hardware can implement it |
| **L5** | No mechanism that already ships solves the problem |

---

# Part 2 — How we run experiments, and why that way

This matters more than usual here, because most of what follows is us catching
our own mistakes.

## 2.1 Pre-registration

Before running anything, we write down: the exact configurations ("arms"), the
number of repetitions, the metric, and — critically — **what result would prove
us wrong**, with numeric thresholds. Then we commit that document to version
control *before* the experiment runs.

**Why:** once you have seen the numbers, there are always several defensible ways
to read them, and it is very easy to pick the flattering one without noticing.
Writing the rule down first removes the choice. We also commit the analysis
script before the data exists, for the same reason.

## 2.2 Arms, controls, and falsifiers

An **arm** is one configuration. A **control** is an arm whose answer you already
know, used to check the instrument works. A **falsifier** is a pre-declared
result that would kill the hypothesis.

Example: to ask "does a streaming program hurt its neighbour?", we run the
neighbour **alone** (baseline), then **with** the streamer. If the instrument
can't detect harm even from a deliberately brutal streamer, then measuring a
gentle one tells you nothing — so the brutal case is the control, and it is
checked *first*.

## 2.3 Order balancing

If you always run arm A before arm B, anything that changes over time — chip
temperature, leftover cache contents — gets blamed on the difference between A
and B. So we rotate the order, using a **Latin square**: over 12 repetitions,
each arm appears in each position exactly 3 times.

We learned this the hard way. In one experiment a fixed order flipped the sign of
the result. Interestingly, plain random shuffling was *not* good enough: we tested
it and found it put one arm in first position zero times out of twelve.

## 2.4 Provenance

Every number in the paper must be traceable to a data file, produced by a
committed script, at a known commit. We keep a ledger of which numbers meet that
bar. Several did not, and we deleted them rather than reconstructing plausible
replacements. The rule is: **when the evidence is gone, say it is gone.**

## 2.5 The machines

| name | chip | notes |
|---|---|---|
| **mos181** | Intel Xeon 8592+ | 320 MB shared cache, 256 cores, our main host |
| **mos182** | Intel Xeon 8462Y+ | 60 MB shared cache |
| **broker** | AMD EPYC 9754 | 16 MB cache per core-cluster; **unreachable for 2 days** |

All three have CXL memory attached.

---

# Part 3 — What we found

## 3.1 The good news: the problem is real, and shipped software confirms it

**RocksDB** is a widely-used database. When it does background housekeeping
(compaction), it reads large files it will never re-read. And it already refuses
to cache them — at every level it is allowed to:

- **Its own cache**: `fill_cache = false` — read the block, use it, never insert
  it.
- **The operating system's cache**: it calls `posix_fadvise(DONTNEED)`, under a
  comment reading *"Tell the OS that we don't need this file in page cache."*
- **The hardware caches**: *no interface exists.* The data it just told two
  layers to discard is still loaded into L1, L2 and the LLC automatically, and
  there is no way to say otherwise.

We verified all of this line-by-line in the RocksDB source. This is the strongest
evidence in the project, because it is not a benchmark someone could dispute — it
is production code, shipped by default for a decade, implementing exactly our
policy at every layer it can reach and stopping at the hardware boundary.

**L1 (someone wants this) is solid.**

## 3.2 The harm is about allocation, not bytes

We ran a stream of data past a sensitive neighbour program twice: once as normal
cacheable memory, once as write-combining. **Same bytes, same wire, only the
cache behaviour changed.** The neighbour slowed by 28% in the first case and 0.3%
in the second.

That is the cleanest possible demonstration that the damage comes from *filling
the cache*, not from *using bandwidth*. **L3 holds.**

## 3.3 The bad news, part one: existing knobs already work

Intel and AMD ship cache-partitioning controls (**CAT**, and a bandwidth throttle
called **MBA**). We tested whether they already solve the problem.

They do. On Intel, CAT alone took a victim's slowdown from 1.62× to **1.00×** and
cost the streaming program 0.7%. On AMD, CAT plus MBA got 18.7× down to **1.07×**
while the streamer kept 96% of its speed.

So for the ordinary case — two separate programs — **the problem is already
solved by hardware you can buy today. L5 fails there.**

## 3.4 The case that was supposed to be ours

There is one case the existing knobs genuinely cannot express. CAT labels a
**thread**. If one thread does *both* the streaming *and* the sensitive work —
a "fused" database operator that scans data and looks things up in the same
loop — then there is only one label for two different kinds of access. You cannot
tell CAT to restrict one and not the other.

We measured this and it looked strong: restricting that thread's cache made it
**monotonically worse** — the tighter the restriction, the worse it got — and
restructuring the program so CAT *could* apply cost 36% of its throughput.

This became the paper's centrepiece.

## 3.5 Then we took it apart, and it fell over

We spent two days trying to find *where inside the chip* that harm lived, so we
could say which mechanism would remove it. Five separate investigations, each
pre-registered:

| what we tested | how | result |
|---|---|---|
| Is it shared-cache capacity? | Compare against a version whose data fits in a smaller cache | **0%** by the strict reading, at most 31% |
| Is it memory-system queueing? | Match the bandwidth using a different memory path | **≈0** |
| Is it address-translation cost? | Give the stream 2 MB pages instead of 4 KB — 512× fewer translations | **Excluded.** Page-walk work barely moved, so those walks were never the stream's |
| Is it memory-bound at all? | Intel's Top-Down analysis, which splits every cycle into memory / compute / branch categories | **15.9%** memory-bound |
| Does the stream cost anything? | Same loop, stream on vs off | **−0.8 cycles** — very slightly *negative* |

Then we found why. **The "harm" was never harm.**

The measurement compared two *different programs*. The "quiet" baseline looked up
keys that were always present in the table — a 100% hit rate. The "fused" version
looked up keys that were present only half the time, and a miss in this kind of
table costs more than a hit. On top of that, the baseline loop contained a
hardware division instruction the other did not (we confirmed this in the
disassembly).

Changing **only** the hit rate, nothing else, moved the fused program from 88.3
to **44.0** cycles — an effect *larger than the entire "tax"* we had been
reporting. At a matched hit rate the fused program is actually *faster* than the
baseline, while still streaming 256 MB from CXL.

**We withdrew the number from the paper.** The table of measurements survives —
every row of it is the same workload, so comparing them is valid — but the
headline "1.47× tax" was comparing apples to oranges.

## 3.6 One more chance: the three-party case

A reviewer proposed a rescue. Maybe the fused program's stream is free *to
itself* but still hurts a **neighbour**. Then the story becomes: to protect the
neighbour you must restrict the fused program, and that restriction lands on its
own working data — which is exactly what our table measures.

We tested it. First attempt was invalid (our own fault — we left stale processes
running, which polluted the baseline). Redone cleanly:

| situation | neighbour's cost | slowdown |
|---|--:|--:|
| alone | 78.1 | — |
| next to a dedicated 23 GB/s streamer | 164.6 | 2.11× |
| **next to the fused program** | **209–212** | **2.7×** |

So the neighbour *is* badly hurt. The premise held.

Then we removed the fused program's stream entirely — all 256 MB of it — and
measured the neighbour again:

**The neighbour's cost changed by 0.11%.**

**That turned out to be wrong, and we caught it within the hour.** The test that
removed the stream still left something else hammering the cache: when the fused
program looks up a key that *isn't* there, it has to search through the table
until it finds an empty slot, and those searches scatter across all 256 MB. So
both the stream and the failed lookups were independently overwhelming the
neighbour, and removing just one changed nothing — like turning off one of two
taps filling a sink that is already overflowing.

Re-running with the lookups made to always succeed — which collapses that second
effect — the picture reverses completely: with the stream the neighbour is 2.77×
slower, **without it, 0.99× — no harm at all.** The stream, on its own, causes the
entire problem.

One caveat, and it is the whole question now: our test removed the stream's
*data*, not just its *caching*. The proposed mechanism would still read every
byte and simply decline to keep it. So this shows the best H2 could possibly do,
not what it does do. The experiment that settles it — read all the bytes, keep
none of them — is the next thing to run.

The harm is real, but the *stream* is not causing it. What hurts the neighbour is
the fused program occupying the cache at all: its own lookup table (about 13% of
the effect) and, mostly, sixteen busy cores touching memory. A mechanism that
labels *streams* cannot help, because the thing doing the damage is the program's
own working data — which must stay cached, since the program is actively using
it.

---

# Part 4 — Where that leaves the project

## 4.1 Honest scoreboard

| link | verdict |
|---|---|
| **L1** someone wants it | **Holds, strongly.** RocksDB proves the demand in shipped code |
| **L2** no interface expresses it | **Holds.** One thread, two access kinds, one label |
| **L3** harm follows allocation | **Holds** on silicon, two vendors |
| **L4** OS + hardware can do it | **Holds.** Our Linux prototype ran inside a simulated machine |
| **L5** nothing shipped solves it | **Fails** |

## 4.2 The sentence that matters

**It has now changed. See Part 6, added 2026-08-26.** The statement below was
the position before the last three experiments, and it is superseded.

**Until 2026-08-25 we had not found a single configuration where STREAMING
uniquely helps. That has changed** — see the reversal noted above and
`M2_OUTCOME_2026-08-25.md`. The statement below describes the position as it
stood before that measurement, and the third bullet is now known to be an
artifact.

Three independent setups, all tested adversarially against our own hypothesis:

- **One thread doing both jobs**: the stream costs that thread *nothing*
  (−0.8 cycles).
- **Fused program next to a neighbour**: the stream contributes **0.11%** of a
  real 2.7× harm.
- **Two separate programs**: existing CAT/MBA already fix it at ≤4% cost.

The mechanism is cheap and buildable. There is no measured situation in which it
is the thing you need.

## 4.3 What honestly remains

A **measurement and interface paper**, and a good one:

- allocation-not-bytes, demonstrated on two vendors' silicon
- a complete map of what every shipped mechanism can and cannot express
- the finding that harm depends on a victim's **memory-level parallelism** — how
  many independent misses it can overlap — which explains why some programs are
  hurt 20× and others not at all
- a boundary map of exactly where the existing knobs work
- RocksDB's three-layer demand evidence
- and a set of clean negative results, including one — the tax that wasn't —
  that we found by refusing to let a number stand unexplained

## 4.4 What we got wrong, and how it was caught

Over two days we retracted **five** of our own findings and found a safety bug in
a kernel module we wrote. Every one was caught before publication, and every one
had the same cause: **we believed something about our own tools without checking
it end to end.**

Examples: we ran an experiment that had already been run a month earlier; we
reported a table as lacking statistics when it had 30 repetitions and confidence
intervals all along; we declared a paper claim falsified after measuring the
wrong thing entirely; and we wrote a guard meant to refuse dangerous memory
ranges that silently let one through — found only because we tested the guard
instead of trusting it.

Four of the five ran *against* our own work. That is the safer direction, but it
is the same failure, and one of them nearly deleted a claim from the paper that
turned out to be correct.

---

# Part 5 — What happens next

**Blocked on the lead, for three days now:** a note to the co-authors. Six paper
files have already changed and been published to them — including the withdrawal
of the most-quoted number — with no explanation attached. They are currently
reading the story from diffs.

**The real decision** is not which conference to target. It is whether this stays
a *mechanism* paper. The evidence says it should not.

**Cheap work still worth doing** (hours to two days each): one last check of
whether a faster stream changes the 0.11% *(running now)*; a cleaner measurement
of the stream's cost; rebuilding the centrepiece table on the current binary; and
restructuring one argument onto the two legs that can still be re-run.

**Stopped on evidence, not on cost:** the mechanism design study, the
three-party campaign, the end-to-end benchmark harness, and the search for a
database that gets hurt the way our theory predicted.


---

# Part 6 — Added 2026-08-26: the mechanism does work, and the "floor" was a red herring

Part 3 ended with a puzzle. Stopping the streaming program from *keeping* its
data in the cache removed only about a quarter of the harm to its neighbour. The
other three quarters seemed to survive no matter what we did — we called it a
"floor" and guessed it was the cost of moving bytes across the memory system,
which no cache mechanism could ever fix.

We were wrong, and the test that showed it was pre-registered with a threshold
that would have proved the guess right.

## What we did

The streaming program in our test does two things: it reads a huge file it will
never re-read (the stream), and it looks things up in its own **lookup table** —
256 MB of data it uses constantly and genuinely needs in the cache.

Our flush trick only ever removed the *stream* from the cache. It never touched
the lookup table, because the program is actively using it. So we shrank the
lookup table from 256 MB to 4 MB and ran the same test again.

## What happened

| streaming program's setup | neighbour's slowdown |
|---|--:|
| stream kept in cache, 256 MB table | 2.78× |
| stream flushed, 256 MB table | 2.32× |
| stream kept, **4 MB table** | 2.40× |
| **stream flushed, 4 MB table** | **0.99× — no harm at all** |

The floor did not shrink. **It disappeared.** With a small lookup table, flushing
the stream returns the neighbour to exactly its solo speed.

## What that means

The harm was never one thing with an unfixable part. It was two separate things:

1. **The stream sitting in the shared cache.** A page-granular memory type
   removes this — *completely*, not partly. Measured recovery: **100.5%**.
2. **The streaming program's own working data sitting in the shared cache.** No
   cache-admission mechanism should remove this, because the program needs it.

The "quarter" we measured earlier was simply the stream's share of the *total*
harm in a test where the program also happened to carry a 256 MB working set. It
was never a limit on the mechanism.

This also explains a result that had contradicted us for two days. In an earlier
experiment, a *pure* streaming program — one with no lookup table at all — was
fully neutralised by a cache-partitioning control. Of course it was: all of its
harm was stream-in-cache, and there was no second working set to leave behind.
Three separate Intel experiments now agree with one story.

## What still doesn't fit

One AMD measurement leaves a floor our Intel account says should not exist. It is
a single result on a machine that has been unreachable for three days, against
three consistent Intel results, and there is an independent reason to expect AMD
to behave differently (we established earlier that AMD's harm scales with request
*rate* while Intel's scales with cache *capacity*). We have recorded it as
unexplained rather than argued it away.

## Where this leaves the project

The mechanism does what it was designed to do, completely, on the thing it
targets. What it does *not* do is protect a neighbour from a streaming program
that also has a large working set of its own — and there, the existing
partitioning controls do help, by squeezing the whole program, at a measured
19–44% cost to that program's own performance.

So the honest picture is a genuine choice, not a failure:

| | removes | leaves | costs the streaming program | needs tuning |
|---|---|---|---|---|
| **new memory type** | the stream's cache footprint, **entirely** | the program's own working data | **nothing** | **no** |
| existing controls | the program's whole footprint | nothing | 19–44% of its own speed | yes, per chip vendor |

The new memory type is the only one of the two that can tell those apart — which
is precisely what the project set out to argue, and the first time in three days
that a measurement has supported it.
