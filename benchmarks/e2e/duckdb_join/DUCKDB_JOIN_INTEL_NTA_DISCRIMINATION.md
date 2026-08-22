# A5.4: `PREFETCHNTA` is not a non-allocating arm on Intel either

`mos181` (Xeon 8592+, 320 MiB LLC), 2026-08-22. Implements `A5.4` of
`DUCKDB_JOIN_CORUN_PREREGISTRATION.md`, threshold fixed at 0.25 before the
measurement. Five arms x 10 repetitions at the campaign's own operating point
(chain8, N = 2M, probe 4M), `MODE=ntaintel`. 50 arms, all valid, no contention.

## The declared result: both pairs fail

| arm | GB/s | victim s | tax | victim occ | **streamer occ** | % of LLC |
|---|---:|---:|---:|---:|---:|---:|
| `quiescent` | -- | 0.6050 | 1.000 | 134.7 MiB | -- | -- |
| `WB_match_hi` | 18.72 | 0.6760 | 1.116 | 66.8 MiB | 248.1 MiB | 77.5% |
| `NTA_sat` | 17.85 | 0.6350 | 1.049 | 127.2 MiB | **139.6 MiB** | **43.6%** |
| `WB_match_lo` | 10.96 | 0.6758 | 1.118 | 64.8 MiB | 249.9 MiB | 78.1% |
| `NTA_lo` | 10.77 | 0.6168 | 1.017 | 93.9 MiB | **218.1 MiB** | **68.2%** |

Rep-paired percentile bootstrap, B = 20000, ratio taken within each declared
pair:

| pair | ratio | 95% CI | per-rep range | threshold | verdict |
|---|---:|---|---|---:|---|
| `NTA_sat` / `WB_match_hi` | **0.637** | [0.557, 0.754] | 0.494--0.813 | 0.25 | **fail** |
| `NTA_lo` / `WB_match_lo` | **0.875** | [0.852, 0.893] | 0.832--0.930 | 0.25 | **fail** |

Per A5.4, reported in the words fixed in advance:

> The Intel arms differ from the AMD ones in **degree and not in kind**. The
> de-confound contrasts *less* allocation against *more*, not allocation
> against none. Every recovery and de-confound figure in
> `DUCKDB_JOIN_CORUN_OUTCOME.md` must be relabelled on that basis.

`wb_prefetchnta` holds **43.6% and 68.2% of a 320 MiB LLC** while the victim
competes with it. Against the only reference this project has for what
non-allocating means -- AMD flush-behind at 5.5% -- that is not a
non-allocating arm, and it has been described as one throughout.

The Intel evidence that made it look like one was indirect and remains true:
the hint costs 28--41% of bandwidth on this host, and victim occupancy is far
higher under the NTA arms. Both are consistent with a hint being honoured. Both
are also consistent with a streamer that allocates and yields, which is what
this measurement shows and what Zen4c does. A4.1's claim that non-allocation
"is true on the Intel hosts" was never measured under competition, and it is
now measured and false.

## What survives, and what has to be relabelled

**The causal result survives.** At matched bandwidth, changing how much the
streamer allocates changes the victim's slowdown, with intervals excluding
zero, on a real application. Nothing here touches that.

**Its description does not.** Three specific things are now wrong:

1. "Non-allocating arm" is false for `NTA_sat` and `NTA_lo` on every host in
   this project. They are *less-allocating* arms.
2. The de-confound is a **dose-response between two allocating streamers**
   (77.5% against 43.6%, and 78.1% against 68.2%), not a contrast between
   allocation and its absence.
3. The recovery percentages -- 89.5%, 56%, 84% in
   `DUCKDB_JOIN_CORUN_OUTCOME.md` -- are recovery delivered by a
   partially-allocating streamer. They are not estimates of what full
   non-allocation would deliver.

**And no inference to full non-allocation is licensed.** The tempting reading
is that since NTA still allocates 44--68%, a true zero-allocation streamer
would do better, so the reported de-confound is conservative. That requires the
tax to be monotone in streamer occupancy, which is precisely what A5.3
disproved and what the next section disproves again on this host. The
conservative reading may be true; this project cannot assert it, and there is
no non-allocating arm on Intel to test it with.

## The de-confound replicates, one day later, with an extra monitoring group

An independent 10-repetition re-run of both declared pairs, which serves the
reproducibility bar directly:

| operating point | this run | original campaign |
|---|---|---|
| ~18 GB/s, `WB_match_hi` - `NTA_sat` | +0.069 [+0.038, +0.079] | +0.058 [+0.047, +0.071] |
| ~10.8 GB/s, `WB_match_lo` - `NTA_lo` | +0.102 [+0.094, +0.103] | +0.093 [+0.089, +0.097] |

Both intervals overlap the originals. Per-arm taxes reproduce to within 0.005
(`NTA_sat` exactly: 1.049 both times) and the quiescent arm to 0.6050 against
0.6070 s.

## Occupancy does not predict harm, now on a second vendor and inside one host

The strongest thing in either artifact. Streamer occupancy given up, against
excess tax recovered, for the three matched pairs this project has:

| pair | streamer occ | occ drop | excess tax recovered | per point |
|---|---|---:|---:|---:|
| AMD, 24.3 GB/s | 98.0% -> 86.7% | 11.3 pts | 40.3% | **3.6 %/pt** |
| Intel, ~18 GB/s | 77.5% -> 43.6% | 33.9 pts | 57.8% | **1.7 %/pt** |
| Intel, ~10.8 GB/s | 78.1% -> 68.2% | 9.9 pts | 85.6% | **8.6 %/pt** |

Normalised by excess tax, because AMD's tax is 8.175x and Intel's is 1.116x and
raw tax units are not comparable across them. The raw figures are more extreme
still: 0.2555 tax units per point on AMD against 0.0020 on Intel at 18 GB/s.

Two readings, and the second is the one that matters:

- Across vendors the exchange rate differs by 5x normalised and 128x raw. That
  could be dismissed as a microarchitecture difference.
- **Within one host, one victim, one artifact, the pair that gives up 3.4x more
  streamer occupancy recovers less tax** -- 33.9 points buying 57.8% against
  9.9 points buying 85.6%. That cannot be a vendor effect. It is an internal
  contradiction of any model in which harm follows the volume of streamer
  allocation.

This is an independent confirmation of A5.3's conclusion from a different
vendor, arrived at without the streamer-yield argument. It also sharpens what
is wrong: not that allocation is irrelevant, but that *how much* the streamer
holds is the wrong state variable.

## Three instrument defects this run exposed

**1. The settle gate accepts a slow ramp, and one arm is bimodal.**
`wait_for_streamer` returns when three consecutive occupancy samples fall
within 5%. A monotone ramp with small per-sample steps satisfies that
trivially. `WB_match_hi` consequently settles into two distinct states across
repetitions:

| state | reps | streamer occ | GB/s | victim occ | tax |
|---|---:|---:|---:|---:|---:|
| low | 3 (inv 0, 4, 8) | 170.9 MiB | 17.00 | 90.1 MiB | 1.0810 |
| high | 7 | 248.6 MiB | 18.82 | 64.8 MiB | 1.1174 |

Bandwidth is bimodal too, so this is **not** a clean natural experiment in
occupancy at fixed bandwidth and is not read as one. It is an arm
reproducibility defect that the original campaign could not have seen, because
it never sampled the streamer. It widens the ~18 GB/s interval here relative to
the campaign's. **It does not threaten the verdict**: the ratio is 0.56 in the
high state and 0.82 in the low, both far above 0.25. The gate should require a
bounded *trend*, not a bounded spread; not changed here, because changing a
pre-registered instrument mid-project needs its own amendment.

**2. My own idle estimator was invalid on Intel, and is fixed.** A5.3's
post-hoc decomposition took the victimless reading as the median of the
sampler's first and last samples. On AMD both read idle, because a 16 MiB CCX
refills in the interval between the victim exiting and the sampler stopping. On
Intel a 320 MiB LLC does not, so the last sample still reads the *competed*
level and averaging the two splits the difference between two different states.
`summarize_nta.py` now uses the first sample only. **AMD moves by <= 0.09 MiB
and nothing there changes qualitatively**: yields 1.98 and 0.13 MiB against the
2.02 and 0.21 first reported, with the idle readings now identical at 15.80 for
both arms rather than 15.84 and 15.89, which if anything sharpens the point
that a victimless sweep cannot tell the two streamers apart. The asymmetry
reads 15x rather than 10x, on non-overlapping intervals. The declared A5.3
ratio does not use this estimator at all and is untouched.
`DUCKDB_JOIN_AMD_NTA_DISCRIMINATION.md` carries the corrected table.

The fix also prints the spread of per-invocation idle readings, and on Intel it
shows that only one arm admits a trustworthy idle reading at all:

| arm | idle | competed | yield | idle spread |
|---|---:|---:|---:|---|
| `NTA_lo` | 307.3 | 218.8 | 88.6 | 306--309 |
| `NTA_sat` | 235.4 | 141.1 | 94.3 | 143--275 |
| `WB_match_hi` | 299.7 | 248.5 | 51.2 | 145--313 |
| `WB_match_lo` | 238.7 | 249.4 | **-10.8** | 185--309 |

`WB_match_lo`'s negative yield is the estimator reporting its own failure: its
first sample is often taken while the streamer is still ramping, so there is no
idle level to subtract. Only `NTA_lo` has a tight enough spread to be quoted,
and it says NTA gives up 88.6 MiB of 307 to a competing victim. The Intel
idle/competed decomposition is otherwise **not reportable**, and no argument
here rests on it.

**3. `WB_match_lo` fails section 5's bandwidth assertion at +15.1%**, against a
10% tolerance and against the campaign's own +10.5% -- the same arm, running
hotter still (median 10.96 against a declared 10.308). The arm is reproducibly
fast in co-run and this is now the second artifact to show it. **The direction
of the bias is conservative for this test**: more `wb_load` bandwidth means
more `wb_load` occupancy, which lowers the `NTA_lo / WB_match_lo` ratio and
pushes it *towards* the 0.25 threshold it failed to reach. The deviation cannot
have caused the failure. It is disclosed, not repaired by widening the
tolerance, and the tolerance has not been widened.

## Where this leaves the project

Combining A5.3 and A5.4: **no host in this project retains a demonstrated
non-allocating arm except AMD flush-behind.** That arm's own co-run results
fail the 5% CoV bar under outcome 5 and yield no verdict.

Flush-behind's status does survive, for a reason worth stating rather than
assuming: it reads 5.5% of the CCX *victimless*, and A5.3's lesson is that
victimless occupancy can only be an over-estimate of what a streamer holds
under competition -- a competitor evicts its lines faster, never slower. So
5.5% is an upper bound and flush-behind is genuinely non-allocating. The
same argument does not rescue NTA, whose victimless readings were 100% on AMD
and are now measured at 44--68% on Intel under competition.

So the project has, today, **no valid allocation-versus-none de-confound on any
host**. What it has is a dose-response between two allocating streamers on
Intel, replicated, with intervals excluding zero -- and evidence from two
vendors that the dose does not order the response. Whether that is enough to
carry L2/L3, and how L5 should be restated given `PREFETCHNTA` recovers 40--86%
of excess tax as a deployed unprivileged instruction, are **section 9 lead-only
decisions and are not taken here.**

## Provenance

- `artifacts/join_ntaintel_mos181.jsonl` -- 50 records, this measurement
- `artifacts/ntaintel_mos181.log` -- runner log
- `summarize_nta.py` -- vendor-keyed pair table, threshold 0.25 for Intel,
  B = 20000, seed 20260822. The pairing is keyed on the host read from the
  record: `WB_sat`/`NTA_sat` are a matched pair on AMD and are 24.9 against
  17.8 GB/s on Intel, so taking the AMD ratio here would commit the section 5.1
  arm-identity error inside the reducer.

Reproduce with `python3 summarize_nta.py artifacts/join_ntaintel_mos181.jsonl`.
