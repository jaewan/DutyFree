# M11 pre-registration: why does M6's *narrower* mask cost F five times less?

Written 2026-08-28 as part of the red-team review, **before any M11 data
exists**.

## The contradiction

At nominally the same table (256 MiB instantiated), the same hit rate (1.0), the
same 16 threads on the same cores (32-47), on the same host:

| | mask given to F | cost to F |
|---|---|--:|
| M6 pass A | **2** of 20 ways = 32 MiB | **+7.5%** |
| M8 | **4** of 20 ways = 64 MiB | **+40%** |

The narrower mask costs five times less. That cannot both be right, and one of
the two numbers is quoted in the paper: **M6 pass A's +2.9%/+7.5% is the "price
of the shipped knob" in the rewritten contribution (2)**. If it is understated,
CAT's dominance over the label is overstated and the claim rewrite rests on a
soft number.

## Surviving differences between the two runs

| | M6 pass A | M8 |
|---|---|---|
| `--fact-bytes` | **256m** | **1g** |
| `--reps` / `--warmups` | 4 / 1 | 1 / 2 |
| resctrl helper | `setup_c 2 32-47 8` | `setup_b 4 32-47` |
| mask | 2 ways | 4 ways |

**Leading hypothesis: fact size.** A 256 MiB fact array re-read over
`--reps 4` in a 320 MiB LLC is small enough to be substantially cache-resident
across reps, so M6's "stream" may not be a one-pass stream at all. Under a narrow
mask a resident fact array is *already* excluded from most of the cache, so
restricting F costs little --- and the measured cost collapses. This is the same
class of defect that voided M1b and M2 (footprint collapse changing what the arm
measures).

## Design

One variable at a time, from M8's configuration toward M6's.

- Fixed: `--mode morsel --policy wb --fact-node 2 --hot-node 0 --hot-bytes
  268435456` (256 MiB, an exact power of two so nothing rounds), `--cpu-list
  32-47 --morsel 1m --threads 16 --hit-rate 1.0`.
- `fact` in {`256m`, `1g`}.
- `reps/warmups` in {`1/2` (M8's), `4/1` (M6's)}.
- `cat` in {`none`, `b2` (2 ways, M6's width), `b4` (4 ways, M8's width)}.
- 12 cells, n=8, 96 runs. Interleaved with a per-rep rotation, schemata and
  instantiated table captured per record, aborts on `HOT_TABLE_ROUNDED`, A6.19,
  resctrl torn down on every exit path.
- `setup_c` vs `setup_b` is **not** varied. `setup_b` gives F a mask and leaves
  everything else at the root default; `setup_c` additionally pins a complement
  group to cpu 8. With no victim running, cpu 8 is idle and its group cannot
  affect F. Holding the helper fixed at `setup_b` keeps the arms comparable to
  M8 and M10; if M11 fails to reproduce M6's number at M6's fact size and reps,
  the helper becomes the remaining suspect and gets its own run.

## Instrument check (registered, action on miss stated)

The cell `none` / `1g` / `1/2` / 256 MiB is M8's `none` 256 MiB cell at hit rate
1.0, whose median was 46.782 cyc/access. It must land within **+/-8% of that,
i.e. [43.04, 50.52]**. The window is +/-8% rather than +/-5% because M8's own
duplicated cell showed hit-rate-1.0 ratios reproducing only to 17.5% at n=8;
demanding +/-5% of a quantity with that spread would be the same mistake that
voided M7's gate.

- **On miss:** M11 is void for comparison against M6 or M8; the within-M11 matrix
  may still be reported as internally controlled.

## Registered predictions

Let C(fact, reps, mask) = 100 x (median(mask)/median(`none`) − 1), F's cost.

- **P1 (fact-size explains it).** C(256m, 4/1, b2) <= 15% **and**
  C(1g, 1/2, b4) >= 30%, i.e. both endpoints reproduce, so the contradiction is
  real and lives in the configuration rather than in a measurement error.
- **P2 (fact size is the dominant term).** At fixed reps and mask,
  C(1g, ·, ·) − C(256m, ·, ·) >= 15 percentage points for both masks.
- **P3 (mask monotonicity, at M8's fact size).** C(1g, 1/2, b2) >
  C(1g, 1/2, b4) --- a narrower mask costs *more* when the stream is a true
  one-pass 1 GiB stream. This is the sanity check that the apparatus behaves
  monotonically at all; if it fails, neither M6's nor M8's number is
  interpretable and both must be re-run before either is quoted.
- **P4.** `reps/warmups` contributes less than 8 percentage points at fixed fact
  size and mask.

P2 and P4 together would localise the whole discrepancy to fact size.

## Registered consequences

- **P1 + P2 + P3 hold** --- M6 pass A's F-cost numbers are measured on a stream
  that is partly cache-resident and **must not be quoted as the price of the
  shipped knob**. The rewritten contribution (2) is re-priced from the 1 GiB
  arms, which raises CAT's cost to F and *narrows* the margin by which CAT
  dominates the label. M6's pass B (V's harm) is unaffected --- it is a
  measurement of V, not of F.
- **P3 fails** --- both M6's and M8's F-cost numbers are withdrawn pending a
  re-run, and contribution (2) quotes no price for CAT until then.
- **P2 fails and P4 fails** --- the discrepancy is in reps/warmups, i.e. in
  warm-up state rather than footprint. Same consequence for M6's numbers, a
  different diagnosis to record.
- **Neither reproduces (P1 fails)** --- the discrepancy was a transient in one of
  the two runs. Both are re-run at n>=15 before either is quoted.

## What this cannot show

Intel EMR only, one table size, one hit rate, no victim. It prices F's own cost
and says nothing about V's protection, so it cannot overturn M6 pass B or the
neighbour finding. It also cannot distinguish "the fact array is LLC-resident"
from any other consequence of a 4x smaller stream; confirming residency directly
would need occupancy counters, which are not wired into this runner.
