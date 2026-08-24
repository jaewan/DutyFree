# Code audit of today's T2/T3 apparatus: what the results can and cannot carry

Asked before reporting further: is the code I wrote today correct enough to
trust the numbers? I re-derived every figure with a script sharing no code with
my analyzers, diffed the new arm against its parent, and read the runners for
failure modes. **Six defects in my own code, one error in my own outcome
document, and one defect in the paper that this audit surfaced.**

## What verified sound

| check | result |
|---|---|
| T2 bandwidth independently re-derived as `total_bytes/elapsed_sec` rather than trusting `avg_bw_gbps` | agrees to ≤2e-3 GB/s (JSON `%.3f` rounding); 2 GB region in all 30 cells; sweep counts consistent with the rates |
| Timing boundary | `clock_gettime(t0)` is taken **after** `mmap` + `memset`, so allocation and fault-in are excluded; the deadline is checked **after** a full sweep, so no partial sweep is over-counted |
| `stream_wc_nopf` vs `stream_wc`, full diff of executable content | only the MSR scaffolding and label/JSON-tag strings differ; the load loop is md5-identical, so prefetcher state is the sole variable |
| MSR handling | `msr_pf_disable` read-back-verifies, the caller `exit(1)`s on failure, `atexit` is registered before `pin_to_cpu`; restore observed in practice (`0x0` on mos181 after the run) |
| T3 guard 1 | 128 node-2 hugetlb pages consumed in all five A_2m reps, 0 in all others — measured externally, so independent of the binary's silent fallback |
| Host validity, all three hosts | cpu8 on node0, memory bound local, governor `performance` |
| AMD failures | loud (`exit 1`) for all three MSR-dependent arms; no silent no-op |

## Defects in my own code

**D1 — arm order was fixed, not randomized.** Both runners interleave arms in a
constant sequence, so `Q_4k` is always position 1 and `Q_2m` always position 3.
A position effect (thermal, residual cache/TLB state) therefore cannot be
separated from run-to-run variance. This is the most consequential defect.
*Impact:* **T2 unaffected** — its effects are 25–83% against CoV ≤1.31%, and no
position effect of that size is plausible. **T3's `R` is compromised**; see D1'.

**D2 — the T3 runner discarded stderr.** It extracted the perf counters from the
stderr file and then `rm -f`'d it. That threw away every in-band diagnostic the
binary emitted, including `HOT_TABLE_ROUNDED` — which is exactly how I failed to
notice in real time that the hot table was 256 MiB rather than the 169.6 MiB
requested. Stderr should have been archived, not parsed and deleted.

**D3 — latent F12 in the hugepage guard.** `hp_used=$(( ${hp_before:-0} -
${hp_min:-0} ))`: if the sysfs read fails, `hp_before` is the string `NA`, bash
arithmetic evaluates it as 0, and `hp_used` becomes 0 — which reads as *"the
hugepages did not take"*, indistinguishable from a genuine negative. It did not
fire here (values were correctly 0 and 128), but it is precisely the failure mode
the guard exists to prevent.

**D4 — `t2_analyze.py`'s falsifier message overstates its own scope.** It prints
"FIRED: A/C < 2.0 on **ALL** hosts" while evaluating only the hosts loaded. With
one host it would print the full-set verdict. No wrong claim was published — I
withheld the verdict until all three landed and said so — but the code is
misleading and a later reader would be misled.

**D5 — "±" values are population sd, not sample sd.** Sample sd is ~11% larger at
n=5. This follows the project's existing convention (`w7_analyze.py` uses
`pstdev`) and changes no verdict, but it was never labelled. Both are now printed
by `t3_analyze.py`.

**D6 — T3's analysis was an uncommitted inline heredoc.** The discipline enforced
all day — analyzer committed before or with the data — was broken on the last
item. The numbers are reproducible (independently re-derived, exact agreement)
but the computation was not pinned. Fixed: `t3_analyze.py` is now committed, and
its docstring records that it postdates the run.

## Error in my own T3 outcome document

`T3_HUGEPAGE_OUTCOME_2026-08-24.md` says the hot table is "~170 MB … on ~43,500
4 KiB pages". Both figures describe the **requested** size. `table_capacity()`
rounds entries up to a power of two: 177,838,489 / 16 = 11,114,905 → 16,777,216
entries × 16 B = **268,435,456 B = 256 MiB = 65,536 pages**, a **1.509×**
inflation. The direction of the conclusion is unchanged — a *larger* victim
footprint makes the victim-side walk explanation stronger, not weaker — but the
numbers were wrong and are corrected by addendum.

## The defect this audit surfaced in the paper

**F9's second instance, on silicon, unfixed.** `GATE1_FUSED_NULL_CORRECTION_
2026-08-15.md` already found this class in a gem5 arm — *"the arm recorded as
'10 MiB' was 16 MiB … a §5.1 arm-identity defect: the requested size was
recorded, the instantiated size was not"* — and fixed it at the source by adding
the `HOT_TABLE_ROUNDED` warning at `fef3e5e`. **The lesson was never applied to
the silicon panel.** `run_confirmatory_panel.py` passes `HOT_BYTES = 177838489`,
the clos_split runs predate the warning (2026-07-29), so it never fired, and:

| | requested | instantiated |
|---|--:|--:|
| hot table | 169.6 MiB | **256 MiB** |
| % of the 8592+'s 320 MiB LLC | **53.0%** | **80.0%** |
| 4 KiB pages | 43,417 | 65,536 |

`Sec3_Mitigation.tex:48` describes this workload as *"a pre-built open hash table
of about 170~MB (53\% of LLC)"*. **It is 256 MiB and 80% of LLC.** So
`tab:fused` — the paper's strongest exhibit — states the wrong operating point,
and the same figure governs the fused tax, the CAT sweep, and the split arms.

Checked and **not** affected: `Sec2_DirectoryTax.tex:96` and
`Sec5_Evaluation.tex:201` describe the *pointer-chase* victim, and
`pointer_chase.c:171` rounds WSS only up to a 2 MiB boundary — no power-of-two
inflation. Those "170 MB / 53%" claims are sound.

Direction matters for how this is reported: 80% is a **harder** operating point
than 53%, so the measured tax was obtained under more LLC pressure than claimed.
The tax is not flattered by an easy point — if anything a true 53% would show
less. But the arm identity is misstated, which is a §5.1 violation on the
exhibit we were about to promote to Figure 1.

## What today's conclusions can still carry

**T2 — fully intact.** A/C = 1.252/1.289/1.283 against a claimed 3.76, on three
hosts and two vendors, with CoV ≤1.31%. Independently re-derived. No defect above
can move a ratio of 1.27 to ≥2.0. The falsifier verdict stands, as do R4 (C≡D),
R6 (C′/C ≈ 0.69, published WC bandwidth overestimates WC) and R7 (prefetch ≈6%
of WB stream bandwidth on local DRAM).

**T3 — headline intact, `R` withdrawn as a point estimate.**

- **Withdrawn:** `R = −0.088` as a number. Its denominator is a bimodal variable
  sampled n=5 per condition under a fixed arm order (D1). The *verdict* it
  produced (R ≤ 0.10 → stream-side TLB excluded) is not in doubt, but the value
  should not be quoted.
- **Stands, and independent of D1:** the fact array's pages went 65,536 → 128
  (512×, verified by 128 consumed hugetlb pages), and the stream's apparent walk
  contribution fell **1.8%** against an arithmetic prediction of ~99.8%.
  That is a measured-vs-predicted contrast, not a between-arm timing difference,
  so arm order and thermal drift cannot produce it. **The load-induced page walks
  are the victim's, not the stream's.**
- **Stands, and strengthened:** because `run_hot_probe()` never calls
  `alloc_bytes()`, `--huge2m` is a **no-op** for the Q arm — `Q_4k` and `Q_2m`
  are the same execution. Their pooled 10 samples are therefore a direct variance
  estimate of one configuration: range 55.46–64.48, **16.3% spread**, 4 low
  (~55.6) / 6 high (~63.2). `tab:fused`'s published quiescent **61.71 is one
  sample from that distribution**, and it is the denominator of the 1.4737× tax.
  A position effect cannot explain the *within-condition* spread, only its split
  between the two Q labels.

## Consequent additions to the hygiene list

1. `Sec3_Mitigation.tex:48` — 170 MB / 53% → **256 MiB / 80%**, and audit every
   other use of `HOT_BYTES`-derived sizes.
2. `tab:fused` needs n and CoV, and its quiescent cell is bimodal.
3. Both runners want randomized arm order before any further use.
4. D2/D3 fixes before the runners are reused.
