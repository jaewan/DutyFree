# Retraction: red-team finding S1-1 was wrong. The gem5 bound is a lower bound after all.

Written 2026-08-28 while applying M12's results to the paper. This retracts the
headline finding of `REDTEAM_REVIEW_2026-08-28.md`.

## What S1-1 claimed

That the paper's statement "the gem5 model bounds the benefit from below" was
backwards in five places, because gem5 omits congestion latency and congestion is
precisely the component non-allocation cannot remove. The arithmetic:

| | fractional recovery | absolute tax removed |
|---|--:|--:|
| gem5 (tax 0.600; H2 removes 90.9%) | 90.9% | 0.545 |
| silicon (tax 1.610; **residency is 27% per M3b**) | <= 27% | 0.435 |
| gem5 overstates by | 3.4x | 1.25x |

## Why it is wrong

**The 27% came from M3b's interpretation, which M5 overturned the following
day, and I did not check that before building on it.**

- `M3B_OUTCOME_2026-08-25.md` is titled *"~27% of the harm is residency; ~73% is
  bytes in flight and no admission-control mechanism can reach it."*
- `M5_OUTCOME_2026-08-26.md` is titled *"the 'non-residency floor' was the
  tenant's own working set. Non-allocation removes 100% of the stream's harm."*

M3b's aggressor was **the fused tenant with a 256 MiB reused table** --- not a pure
streamer, which is how I read it. M5 held everything fixed and shrank that table:

| tenant's own table | victim harm removed by non-allocation |
|---|--:|
| 4 MiB | **100.5%** |
| 128 MiB | 75% (M12 pass B; 1 GiB stream, so not on M5's stream size) |
| 256 MiB | 28.0% |

So the 73% "bytes in flight" was **the tenant's own resident data**, which is
legitimately resident and which no admission mechanism should evict. There is no
27% ceiling on what admission control can buy. I quoted a retired number as if it
were the project's position.

## What the correct comparison says

Where the configurations are matched --- a tenant whose own footprint is too small
to leave a residue --- **silicon recovers 100.5% of the victim's charge and gem5
recovers 90.9%.** The model is conservative. Combined with its 39%-low tax
against the one anchor we can check, **both magnitudes it supplies are lower
bounds**, which is what the paper said before I changed it.

## What survives from S1-1

Only the structural caveat, demoted from a finding to a caveat: `SimpleMemory`
with `latency_var = 0` genuinely cannot represent congestion latency, so **in a
configuration with a material congestion charge, gem5's recovery would be
optimistic.** We have not found such a configuration on Intel --- shrinking the
tenant's footprint drove recovery to completeness --- but we have not proved there
is none, and on AMD, whose harm E3 found to be rate-class rather than
capacity-class, we should not assume it. The paper now says exactly that.

## Damage and repair

- Five instances flipped to "upper bound" on 2026-08-28 morning. The lead had
  already reverted the abstract and the worst of the §5 passages before I noticed;
  four remained (`Sec1` contribution 4, `Sec5` opening, `Sec5`'s calibration
  passage, `Sec5`'s fused paragraph) and are now corrected to the
  configuration-matched argument with the caveat stated.
- `COVER_NOTE_2026-08-26.md` addendum 3 carries S1-1 as its headline finding and
  is **wrong**; it needs a correction appended.
- The red-team review document needs S1-1 struck and this retraction linked.

## The lesson, which is the same one as three days ago

The red-team review's own process finding was that pre-registration without a
power calculation is discipline theatre. The companion failure is this one:
**quoting a number from a committed document without checking whether a later
document superseded it.** That is F11 from the W4.3 ledger --- a correct artifact
nobody re-read --- and it is now the *third* time this week it has bitten, twice by
me: the L5/W5.3 correction on 08-28 and this one within hours of it.

The concrete rule this earns: **before any cross-document number enters an
argument, check for a later document that names the same quantity.** M3b and M5
are adjacent files in the same directory with contradictory titles. Reading only
one of them is not a subtle mistake.
