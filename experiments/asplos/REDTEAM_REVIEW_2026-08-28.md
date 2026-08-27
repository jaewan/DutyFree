# Red-team review: a fresh reading of the paper and the repo

Requested 2026-08-28: step back, re-read the paper with fresh eyes, review the
repo, and assess whether the measurements and interpretations were done
correctly. Everything below was checked against artifacts or re-measured; where
I re-ran something the pre-registration predates the data. Findings are ordered
by severity, and **the first four are mine, introduced or left standing in the
last four days.**

Severity key: **S1** blocks submission. **S2** internal contradiction a reviewer
will find. **S3** overreach in an interpretation we published.

---

## S1-1. The gem5 bound points the wrong way, in five places

The paper says, in five live locations, that the gem5 model **bounds the benefit
from below**:

| file | text |
|---|---|
| `Abstract.tex:37` | "under-predicts the hardware tax it is nearest and therefore bounds the benefit from below" |
| `Sec1_Introduction.tex:143` | "gem5 model bounds the benefit from below" |
| `Sec5_Evaluation.tex:75` | "a hardware-anchored gem5 model bounds its benefit from below" |
| `Sec5_Evaluation.tex:193` | "The gap is conservative, so the WB column bounds the effect from below" |
| `Sec5_Evaluation.tex:587` | "is therefore a lower bound supplied by a model" |

The stated inference is: the model under-predicts the *tax*, therefore it
under-predicts the *benefit*.

**That inference is invalid, and our own commit says so.**
`GEM5_TRANSPORT_CHECK_2026-08-26.md:67` (committed two days ago) reads: *"every
gem5 recovery figure in the paper is an upper bound on what silicon would show.
H2's 90.9% is the clearest example."*

The reason is structural. gem5 uses `SimpleMemory` with `latency_var = 0`, so it
reproduces a bandwidth ceiling but **no congestion latency**. The component it
omits is therefore precisely the component STREAMING **cannot fix**. Omitting
the unfixable part inflates the fixable fraction:

| | fractional recovery | absolute tax removed |
|---|--:|--:|
| gem5 (tax 0.600; H2 removes 90.9%) | **90.9%** | 0.545 |
| silicon (tax 1.610; residency is 27% per M3b) | **<= 27%** | 0.435 |
| **gem5 overstates by** | **3.4x** | **1.25x** |

gem5 predicts the victim returns to 1.06x; the silicon decomposition predicts
2.18x. **The model is an upper bound on both measures.**

This matters more than any other finding because "bounds the benefit from below"
is the epistemic licence for the whole gem5 half of the paper --- contribution
(4) leans on it explicitly. As written, a reader concludes silicon would show
*at least* what gem5 shows. The truth is at most, and by a factor of three.

**Fix:** reverse the direction in all five places, and state the reason
(the omitted component is the unfixable one). The honest framing is available and
is not fatal: gem5 establishes that non-allocation *does not collapse bandwidth*
--- the half that could have failed --- and bounds the capacity benefit **from
above**, with M3b's 27% as the silicon-side ceiling.

## S1-2. The abstract asserts a claim §2 has already withdrawn

`Abstract.tex`: *"holding the byte stream fixed and changing only the host memory
type moves a co-runner's slowdown from large to nil."*

§2 withdrew exactly this on 2026-08-24. The arms are matched by **thread count**,
not rate; WC cannot reach WB's rate on this hardware. §2 now says so and reports
WC moving 26% fewer bytes. The abstract still claims the stream was held fixed.

**Fix:** the abstract must inherit §2's correction. The dissociation survives
--- 26% fewer bytes cannot produce a 28% -> 0.3% collapse --- and reads stronger
stated honestly, which is the argument §2 already makes.

## S1-3. `tab:amdcat`'s WC row is not rate-matched, and the gap is 43%

Recomputed from `experiments/phase1/e1_residual_decomp/e1gate_raw_n12.jsonl`
(the artifact the ledger names as the verified replacement):

| arm | n | victim slowdown | aggressor BW (self) |
|---|--:|--:|--:|
| quiescent | 12 | 1.000 | --- |
| write-back | 12 | 19.886 | **24.13 GB/s** |
| WB + CAT 8/8 | 12 | 7.225 | 24.08 GB/s |
| write-combining | 12 | 0.989 | **13.84 GB/s** |

**The WC arm moves 57.3% of WB's bytes --- a 43% rate cut, nowhere disclosed.**
The CAT arm *is* at full bandwidth (99.8%), so "9.87x residual at full aggressor
bandwidth" is sound. But the row that anchors "non-allocation removes the tax"
is confounded by rate, and `tab:catmba` shows on Intel that rate reduction alone
moves the victim (2.03x -> 1.46x at 8.7 GB/s). This is the same defect class as
E1's withdrawn "identical traffic" --- **we made that correction in §2 and never
applied it to this table.**

**Fix:** disclose the rate gap in the caption, and state that the WC row bounds
the non-allocation effect from above because it also cuts the rate. The paper
cannot claim 100% removal is attributable to non-allocation from this artifact.

## S1-4. The published "53% removed" pairs two different runs

| pairing | WB | CAT | removed |
|---|--:|--:|--:|
| within `n12` (2026-08-06) | 19.886x | 7.225x | **67.0%** |
| within `n6` rerun (2026-08-08) | 20.545x | 9.867x | **54.6%** |
| **paper: `n12` WB with `n6` CAT** | 19.886x | 9.867x | **53.1%** |

The published figure is a cross-run pairing, and it is **the least favourable to
CAT of the three** --- i.e. the error runs in our favour. The caption discloses
the CAT arm's instability but not that the two numbers in the subtraction come
from different runs.

**Also: the `n6` rerun's WC arm is void.** Its aggressor moved
`agg_mbm_bw = 0.0108 GB/s` --- no traffic at all --- while reporting 1.006x
victim slowdown. That is "the aggressor never ran," not "non-allocation removes
the tax." The published WC row comes from `n12` and so is not itself the void
arm, but the CAT number the paper now leads with comes from the same file, and
this is the second time in the project that an arm has silently not run
(M1's positive control was the first).

**Fix:** report a within-run pairing, say which, and quarantine the `n6` WC arm.

---

## S2-5. The superseded E1 absolutes survive in five live places

§2 was corrected to **12.4 / 3.2 GB/s** ($n{=}12$) with a full note. The old
**15.8 / 4.2 GB/s** is still live in: `Sec1:35`, `Sec3_5:33`, `Sec5:81`,
`Sec5:171`, `Appendix:499`. The paper currently states both values for the same
measured quantity. The *ratio* is unaffected (3.88 vs 3.76), so only the
absolutes need changing.

## S2-6. `169.6 MiB` regression --- mine, from 2026-08-26 (**fixed today**)

The appendix says, correctly and since 08-24: the requested 177,838,489 B is
rounded up to an instantiated **256 MiB**, and *"we report the instantiated size
throughout."* My 08-26 edits then wrote "169.6 MiB" into Sec1 once and Sec3 four
times --- reverting to the requested size and contradicting the appendix on the
same page. Corrected today to 256 MiB, and §3 now states the 4x table-to-mask
ratio explicitly.

## S2-7. M8 ran a duplicated cell and reported it as two

`--hot-bytes 177838489` and `268435456` **both instantiate 256 MiB**. M8's
"169.6 MiB" and "256 MiB" rows are the same configuration. So M8 measured **six**
distinct table sizes, not seven, and `M8_OUTCOME` presents them as seven. Third
appearance of the F9 power-of-two family. M7/M8/M9 all discarded stderr and so
could not have caught it from their own data; M10's runner now aborts on
`HOTM_TABLE_ROUNDED` and records the instantiated size per run.

**The silver lining is real:** the duplicate is an unplanned replicate at
identical configuration, and it prices our own precision:

| hit rate | R (cell A) | R (cell B) | spread |
|--:|--:|--:|--:|
| 0.5 | 1.3612 | 1.3663 | **0.4%** |
| 1.0 | 1.1954 | 1.4046 | **17.5%** |

So M8's hr-1.0 ratios carry ~18% run-to-run spread at n=8 and should never have
been quoted to three digits, and the P1 "miss" at hr 1.0 was **noise between two
identical configurations**. My "threshold too tight on a noisy cell" call was
right, for a reason I could have proven and did not.

---

## S3-8. "No quantitative result in the label's favour" is underpowered, not null

Published yesterday in the cover note and in `M9_OUTCOME`: the label's residency
benefit at full LLC is "+1.05 / -0.56 cyc/access, not distinguishable from zero,"
supporting "the Intel side of the paper now has no quantitative result in the
label's favour."

The estimator is a difference of differences whose validity needs the proxy's
intrinsic cost to be table-independent. It is not even hit-rate-independent:

| cell (cat=none, identical 1 GiB flushed) | proxy cost |
|---|--:|
| 32 MiB table, hr 0.5 | +12.63 cyc/acc |
| 32 MiB table, hr 1.0 | +5.78 cyc/acc |

**A 6.85 cyc/access swing from a workload change involving no change in flush
work at all** --- against a signal of ~1 cyc/access. The estimator is confounded
by how much slack the table's miss profile leaves to hide flush work, and my
signal is **6.5x smaller than a confound of the same estimator**.

**Correction:** M9 cannot measure the label's benefit at full LLC. The honest
statement is "not measurable with this instrument," not "zero," and it does not
support "no quantitative result in the label's favour." That sentence must come
out of the cover note and must not enter the paper. Sec5's current wording
("about one cycle per access in either direction ... inside the run-to-run
spread") is closer but still implies a measurement; it needs to say the
instrument is too coarse.

A sound version exists: sweep flush distance as M3b did, where intrinsic cost is
held fixed while residency varies. Not run.

## S3-9. M9's "stream share is nominally negative" is a proxy artifact

M9 found R_flush > R_retain and I reported a capacity share of 117%/125% with the
stream's share "nominally negative." But the proxy is **mask-sensitive at the
large table and not at the small one**:

| cell | proxy cost under `none` | under `b4` | excess |
|---|--:|--:|--:|
| 32 MiB, hr 0.5 | +17.41% | +18.14% | +0.73 pp |
| 32 MiB, hr 1.0 | +14.82% | +14.19% | -0.63 pp |
| 256 MiB, hr 0.5 | +12.93% | +16.44% | **+3.51 pp** |
| 256 MiB, hr 1.0 | +13.53% | +19.53% | **+5.99 pp** |

The excess (3.5--6.0 pp) is the same size as the R_flush − R_retain gap
(3.8 / 6.7 pp), so the entire "penalty is larger without the stream" effect is
explained by the proxy costing more inside a narrow mask. That is the **same
artifact as M6's falsified R2** (flush cost F +18% inside a narrow mask), so it
reproduces across two experiments and is not noise.

I also tried to "correct" R_flush by dividing out that factor. **That is
algebraically circular** --- the correction returns R_retain identically --- and
proves nothing. Withdrawn.

**What survives, and it is the load-bearing part:** P1 holds without touching the
contaminated comparison. Even the *lower* of the two ratios is 1.2173 (hr 0.5)
and 1.2732 (hr 1.0), both above the registered 1.20. So *the penalty survives a
non-allocating stream* stands; only "and is nominally larger" comes out.

## S3-10. M6's "the label has no winning cell" needs one qualification

At the 256 MiB table the label leaves V at 2.28x while CAT-narrow reaches 0.99x.
But at that size V (170 MiB) plus F's **table** (256 MiB) alone exceeds the
320 MiB LLC. The harm the label fails to remove there is caused by F's *reused
table*, not by its stream --- a harm **no stream-admission label could ever
address**, and one that is not mislabelled at all.

The comparison is still fair to a tenant who only cares about V. But the
conclusion should be stated as the mechanism it is: *partitioning is the right
tool for neighbour protection because a neighbour is harmed by the tenant's total
footprint, not only by its stream.* That is more defensible than "the label has
no winning cell," and it is consistent with the two-component account already in
the paper. M6's 4 MiB dominance (CAT wins on both axes) is untouched.

## S3-11. M6 captured no per-record mask or co-runner verification

`m6b.jsonl` records only `arm`, `rep`, `pos`, `median_cyc_per_load`. No schemata,
no F liveness, no F bandwidth. `m6a.jsonl` likewise has no schemata. M7--M10 all
capture schemata per record; M6, the experiment that killed the neighbour claim,
does not.

I checked the stderr files rather than assume: F emitted `HOT_TABLE` and
`HOT_TABLE_WARMED` in both `none` and `narrow` arms, so F did build and warm its
table under the narrow mask. And V and F share L3 domain 0 (`cpu8` and `cpu32-47`
both report L3 id 0), so the geometry is sound. **M6's conclusion is not
overturned** --- but S1-4 above is precisely the failure this gap cannot exclude,
and it should be closed before anything is submitted.

## S3-11b. §3's mask-capacity mechanism was unsupported --- so I tested it, and it holds

This one I expected to overturn the paper and it did not, so it is recorded with
the same prominence as the findings that went the other way.

On 08-26 I wrote a *mechanism* into §3: the penalty appears because a four-way
mask holds 64 MiB while the table is 256 MiB. **M8 does not establish that.** It
varied table size at one mask width, and its control cells are equally explained
by 16 cores x 2 MiB = **32 MiB of aggregate private L2** --- a table that size may
simply never reach the L3. That is standing rule S5.2 turned on my own
conclusion.

M10 swept mask width against table size; its control failed on a prediction I
had mis-specified, voiding its reading (recorded in `M10_OUTCOME_2026-08-28.md`;
I did not argue the void away). M10b re-specified the control in advance and
added a fixed-table discriminator:

| table | b2 (32 MiB mask) | b4 (64 MiB) | b8 (128 MiB) |
|--:|--:|--:|--:|
| 4 MiB | 1.0122 | 0.9993 | 1.0006 |
| 8 MiB | 1.0380 | 1.0005 | 0.9983 |
| **128 MiB** | **1.5312** | **1.3978** | **1.1163** |

Control holds (all six small cells within 1.038). And at a **fixed** 128 MiB
table the penalty is strictly ordered by mask width, spread 0.415 against a
registered >= 0.15. **A fixed table penalised progressively less as the mask
widens cannot be a private-L2 effect** --- private L2 does not change when the L3
mask does.

**§3's mechanism sentence stands**, now cited to a controlled experiment rather
than a single-width sweep. It buys the mechanism only; it does not restore the
penalty as evidence for label scope, which M9 settled.

## S3-12. An unresolved contradiction between M6 pass A and M8

Same 256 MiB table, same hit rate 1.0, same 16 threads on the same cores:

| | mask | cost to F |
|---|---|--:|
| M6 pass A | **2** of 20 ways (32 MiB) | **+7.5%** |
| M8 | **4** of 20 ways (64 MiB) | **+40%** |

The *narrower* mask costs five times less. That cannot be right. The surviving
differences are `--fact-bytes` (256m vs 1g), `--reps/--warmups` (4/1 vs 1/2), and
`setup_c` vs `setup_b`. The leading candidate is fact size: M6's 256 MiB fact
re-read over `--reps 4` is small enough to be partly LLC-resident, so M6's
"stream" may not be a one-pass stream at all --- the same class of defect that
voided M1b and M2.

**This is not cosmetic.** M6 pass A's +2.9%/+7.5% is the "price of the shipped
knob" quoted in the rewritten contribution (2). Registered as M11 and M11b and
**run**; the answer is worse than the contradiction suggested.

**M6 pass A ran n=3.** And at its operating point (hit rate 1.0) this quantity has
about **+/-15% run-to-run resolution at n <= 10** --- established twice
independently: M8's duplicated cell (17.5%) and the same M11/M11b cell measured
minutes apart (16.6%). So M6's +7.5% (n=3), M11's +21.3% (n=8) and M11b's
+41.6%/+25.9% (n=10) are **one badly-conditioned quantity measured four times**,
not four results. M11 localised a real fact-size term (15--21 pp: a 256 MiB fact
array is not a one-pass stream in a 320 MiB LLC) and a smaller warm-up term
(1--14 pp), but no combination of them is quotable at this operating point.

**Both M6 pass A's and M11's F-cost figures are therefore withdrawn**, and
contribution (2) is re-priced from hit rate 0.5 --- `tab:fused`'s own operating
point, where the overlapping M10/M10b cells reproduce to **0.3--4.4%**:

| reused table | 32 MiB mask | 64 MiB mask | 128 MiB mask |
|---|--:|--:|--:|
| 32 MiB | +21% | **+2%** | **0%** |
| 128 MiB | +51% | +39% | +17% |
| 256 MiB | +41% | +37% | +28% |

The consequence for the claim is substantive and it moves **toward** the paper.
The head-to-head becomes:

- **Small reused structure:** CAT dominates on both axes --- same protection, an
  order of magnitude cheaper (2% vs the proxy's 18.7%).
- **Large reused structure:** **neither mechanism wins both axes.** CAT protects
  the neighbour and takes ~37--41% of the tenant's throughput; non-allocation
  costs the tenant nothing and leaves the neighbour at 2.28x.

So **"the label has no winning cell," my headline on 08-26, was too strong** --- it
rested on an n=3 arm. The panel's original R1 branch ("division of labour, not
sole rescue") was closer than my overshoot of it, and §5 and contribution (2) now
say so.

**One registered consequence I declined to execute.** M11b's P1 (helpers agree
within 5 pp) "failed" at 15.6 pp, and its registered consequence was to open an
investigation into `setup_c` affecting every experiment that uses it, M6 pass B
included. The difference is not established --- permutation **p = 0.443**,
bootstrap 95% CI **[-13.7, +13.9]** spanning zero --- because I had set the
threshold below the instrument's resolution. Opening that investigation and
re-auditing M6 pass B on a p=0.44 result would be precisely the error this review
exists to catch. `setup_c` is also **not** exonerated: failing to detect an effect
at +/-14 pp is not showing there is none.

## S3-13. §3.5 claims a victim we no longer have evidence for

`Sec3_5:38`: the tax "always has a victim---a neighbor core, **or the streamer's
own interleaved hot table when both classes share a thread**." After M9 there is
no hardware evidence for the second disjunct on Intel. Needs scoping to the
neighbour case, or an explicit "we do not size this."

---

## What survived the red team

- **M6's geometry.** V and F share the L3 domain; V gets an enforced complement;
  F verified from stderr to build and warm under the narrow mask.
- **No page-size confound anywhere.** All of M7--M10 ran uniform 4 KiB pages with
  no THP variation across cells --- checked, not assumed.
- **The AMD residual is *not* the `tab:fused` capacity artifact.** There the
  victim's 4 MiB fits inside its 8 MiB of ways; in `tab:fused` the 256 MiB table
  is 4x its 64 MiB mask. Different geometry, and M8/M9's capacity reasoning does
  **not** transfer to `tab:amdcat` in either direction.
- **The gem5 retrodiction's arithmetic hangs together**, which I doubted on first
  pass. gem5 captures 37% of the silicon tax (0.600/1.610) and M3b puts residency
  at 27% --- the same ballpark, consistent with "gem5 ~ residency only." The
  retrodiction is sound; only the *bound direction* drawn from it (S1-1) is wrong.
- **§3.5's structural argument** (certainty, counterparty, scope; types licence
  coherence exemptions, guesses cannot) is untouched by everything measured this
  week, and the PC-indexed-predictor concession is correctly scoped.
- **The taxonomy, the missing admission cell, and RocksDB's demand evidence.**
- **M9's headline**, on the lower of its two ratios: the fused restriction penalty
  survives a non-allocating stream.
- **§3's mask-capacity mechanism**, which I had asserted without evidence and
  which M10b establishes on a properly specified control (S3-11b).

## Overall assessment

The measurements are, with the exceptions above, done correctly and the apparatus
discipline is good --- pre-registration before data, order rotation, per-record
validation, instrument checks with stated actions on miss. Where this week went
wrong it was almost entirely in **interpretation running ahead of what the
instrument could support**, and in **corrections not propagating** from the
section where they were made to the four other places that state the same number.

**The process finding, and it is about me.** Four registered thresholds this week
were set finer than the instrument resolves: M7's P2 (missed by 0.005), M10's
apparatus control, M11's P2 (missed by 0.016 pp) and M11b's P1 (a 15.6 pp
"failure" with a CI of +/-14 pp). Three voided readings I had already done the
work for, and the fourth nearly triggered a spurious audit of M6 pass B. The
common cause is choosing round numbers near the expected effect instead of
justifying a threshold against measured reproducibility. **Pre-registration
without a power calculation is discipline theatre.** Every future registration in
this project should state the cell's measured CoV and the n required, and should
prefer hit rate 0.5 (0.3--4.4% reproducibility) over hit rate 1.0 (16--18%) for
any quantity we intend to quote.

Two of the four S1 findings (the gem5 bound direction, the abstract's withdrawn
claim) are cases where the paper contradicts a correction the project had already
made and committed. That is a process failure, not a measurement failure, and it
is the one most likely to be caught by a reviewer, because both are visible
without any access to our data.

The single most consequential item is **S1-1**. It does not kill the gem5 half
--- the bandwidth result stands and is the half that could have failed --- but it
inverts what that half is allowed to claim.
