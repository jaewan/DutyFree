# Outcome: silicon hash-join e2e clean re-run

Date: 2026-09-04.
Pre-registration: `SILICON_E2E_RERUN_PREREG_2026-09-04.md`, commit
**`afdeb8f8f15594d325dda97aac58463f18cb804f`**, authored 2026-09-05T11:39:58+09:00.
G-pred waiver: `SILICON_E2E_RERUN_GPRED_WAIVER_2026-09-04.md`, commit
**`d709bf7e0c44924ee1680d97630e8a2ed3a023ae`**, authored 2026-09-06T01:25:18+09:00,
restored with an addendum at `34f478a`.

## Verdict: MEASURED — admitted by every gate, and it FAILS D1 and D2

105 records, all `status=ok`, all nine registered admission gates **PASS**,
**G-exact PASSES** — every one of the 100 tenant records reports `matches`
exactly **536,870,912**, deficit **0**. The corrected tenant computes the join
it reports. That was the point of the exercise and it is settled.

**And the registered predictions do not hold.**

> ## THE DELTA IS NOT NEGLIGIBLE. D1 AND D2 FAIL.
>
> The three **flush-behind arms** move enormously: tenant cost changes by
> **−26.0, −26.2 and −26.4 pp** against a D2 limit of 1.0 pp, and protection by
> **+12.2, +13.6 and +16.1 pp** against D1 limits of 3.8, 3.8 and 2.0 pp.
> Three CAT arms also break D1 — `cat06` at **−10.2 pp** against a 3.4 pp
> limit, `cat10` at +3.8 against 3.7, `cat12` at +3.7 against 2.4.
>
> **The pre-registration's central claim is refuted, not confirmed.** It said
> the corruption was arm-identical and would therefore cancel in the ratio
> coordinates, and that "no published figure moves". For the 15 CAT arms and
> `nta` that is true. **For the three `fb` points, which panel (b) of
> `fig:frontier` plots, it is false.** They move from
> `(46.2 %, −5.9 %)`, `(44.5 %, −6.3 %)`, `(31.8 %, −6.1 %)` to
> `(58.3 %, −31.9 %)`, `(58.1 %, −32.5 %)`, `(47.9 %, −32.5 %)`.
>
> Per the registration's own D1–D4 clause, this is reported prominently rather
> than in a footnote, **every silicon e2e flush-behind number is open pending
> diagnosis**, and it is explicitly *not* relabelled as a correction.

What is *not* in doubt: the apparatus reproduces (**D4 PASS**, all three
absolute medians within 0.45 %), and the CAT frontier has no common-mode shift
(**D3 PASS**, mean signed +0.138 pp protection / −0.191 pp cost over 15 arms).
So this is not a broken host or a drifted rig. It is a specific, large,
reproducible difference between the two tenants, confined to one code path.

| registered gate | verdict | note |
| --- | --- | --- |
| **G-pred** (predecessor clean) | **WAIVED** | condition FAILED (105 records, 104 `ok`); waived by the campaign owner at `d709bf7`. **Not** `PASS` |
| **G-exact** | **PASS** | all 100 tenant records `matches` = 536,870,912, deficit 0 |
| G-shape | PASS | 105 records, 21 arms × 5 reps |
| G-status | PASS | every record `status=ok` |
| G-host | PASS | `mos182` |
| **G-tenant** | PASS | `sha_join` = `a677c52d…` on all 105; `sha_victim` = `026e357a…` |
| G-geometry | PASS | fact 8,589,934,592, hot 33,554,432, `hit_rate` 1.0, no `HOT_TABLE_ROUNDED` |
| G-pages | PASS | `huge2m=true` on every tenant record |
| G-window | PASS | every tenant record brackets `JOIN_MEASURE_BEGIN/END` |
| G-runner | PASS | mask/clos/live/size/fb/nta/mask-held/idle all pass on all 105 |
| **G-clean** | PASS | all three manifests `sha256sum -c` OK after the campaign |
| **Positive control** | PASS | deficit exactly 0 at two sizes and on the hugepage path |
| **D1** per-arm protection | **FAIL** | `fb1m` +16.15, `fb256k` +13.56, `fb64k` +12.18, `cat06` −10.22, `cat10` +3.76, `cat12` +3.65 |
| **D2** per-arm tenant cost | **FAIL** | `fb1m` −26.39, `fb256k` −26.17, `fb64k` −26.01, all against a 1.0 pp limit |
| **D3** common mode (CAT) | PASS | mean signed +0.138 pp / −0.191 pp |
| **D4** absolute reproduction | PASS | `qui` +0.01 %, `wb` victim −0.45 %, `wb` tuples/s +0.29 % |

Analyzer exit status 1 (`VOID`-equivalent on the delta), verdict line:
`*** MATERIAL SHIFT *** the mechanism is NOT understood`.

## The material shift, localised

The registration required a failure to be reported loudly; it also permits
diagnosis. The diagnosis below **narrows** the finding without explaining it,
and the distinction is kept explicit.

### It is the binary, not the host, and it is confined to flush-behind

Matched pair on the idle host after the campaign, 1 GiB fact, `--huge2m`,
tenant cpu 4, `hit_rate` 1.0, everything else identical, both binaries run
read-only from where they already sit:

| binary | `--flush-distance 0` | `--flush-distance 65536` | flush-behind cost |
| --- | --- | --- | --- |
| **`a677c52d…`** (HEAD, clean) | 42.78 Mt/s | **30.25 Mt/s** | **−29.3 %** |
| **`75e0af94…`** (the 105 published records) | 42.58 Mt/s | **40.44 Mt/s** | **−5.0 %** |

The **plain join path is identical between the two binaries** — 42.78 vs 42.58,
a 0.5 % difference — while the flush-behind path differs by a factor of 1.34.
Deficits in the same runs confirm binary identity: 0 for the clean tenant,
262,144 = 1 GiB/4096 for the defective one.

At the campaign's own 8 GiB geometry the same thing appears as flush-behind
costing **−31.9/−32.5/−32.5 %** of `wb` in the clean dataset against
**−5.9/−6.3/−6.1 %** in the corrupted one, with `wb` itself reproducing to
+0.29 %.

### It is not mediated by the corrupted keys

The obvious hypothesis — that 1/256 wrong keys change probe behaviour — is
**refuted**. Sweeping `hit_rate`, where at 0.0 both binaries return
`matches=0` and the key corruption is irrelevant by construction:

| `hit_rate` | clean, flush cost | defective, flush cost |
| --- | --- | --- |
| 1.0 | −29.2 % | −5.3 % |
| 0.5 | −28.4 % | −9.7 % |
| **0.0** | **−24.5 %** | **−10.5 %** |

The gap survives at `hit_rate` 0.0. Whatever it is, it is not the wrong keys.

### It is not the flush distance, and not codegen

Sweeping `--flush-distance` over 16, 64, 4096, 65536 and 1048576 B — a
4-order-of-magnitude range in how far behind the cursor the line is — the clean
tenant sits at **30.24–30.34** Mt/s and the defective one at **40.30–40.59**
Mt/s at *every* distance. The ratio is flat at ≈1.33; nothing depends on the
distance, so this is not an off-by-one in the `i >= begin + flush_ents` guard
and the defective binary is not simply under-flushing.

Nor is it instruction emission. `objdump` of both binaries:

| | `clflushopt` | `clflush` | `sfence` | `prefetchnta` |
| --- | --- | --- | --- | --- |
| `a677c52d…` | 1 | 0 | 2 | 17 |
| `75e0af94…` | 1 | 0 | 2 | 17 |

And the source of `join_range_flushbehind` is **functionally identical** between
`HEAD`'s `b843d465…` and the defective binary's own source, c4's uncommitted
`e8d10458…`: the only change is an added `policy == "fbo"` branch, and the
`fb*` arms run `--policy wb`, so they take the unchanged `else if` whose guard
and body are byte-for-byte the same.

### What is therefore *not* established

The cause. Two binaries, differing by a 675-line source delta, agree to 0.5 %
on the plain join and differ by 33 % on flush-behind, with identical flush
instructions, identical flush addresses, and no dependence on hit rate or flush
distance. **That is not explained here, and it should not be treated as
explained.** The remaining suspects live in the parts of the delta this campaign
did not isolate — most obviously the removal of the seven post-`fill_fact`
`prefault_region()` calls, which changed what last touched the 8 GiB fact array
before the join and hence its cache and page state at join entry, but that is a
*hypothesis with a sign problem*: a stray dirty line per 4 KiB page should make
the **defective** binary's flushes more expensive, not less, which is the
opposite of what is measured.

The falsifiable next experiment, which this campaign did not run because it
would require a third tenant that is in no commit: build from `HEAD` with a
post-`fill_fact` prefault re-enabled and see whether flush-behind cost returns
to ≈5 %. Until something like that is done, the flush-behind numbers on this
apparatus — in **both** datasets — are open.

## What moves in the paper, and what does not

Stated precisely, because "no published figure moves" was the registered claim
and it is now only partly true. `make_eval_frontiers.py:86-99` reads
`data/silicon_e2e_hashjoin.jsonl` and plots, in panel (b), 15 CAT points, 3
`fb` points and the `nta` point.

| published point | corrupted | clean | moves? |
| --- | --- | --- | --- |
| 15 CAT points | — | — | **No.** max \|Δ protection\| 10.2 pp at `cat06`, mean signed +0.14 pp; every tenant cost within 0.6 pp |
| `nta` | (15.31 %, +2.95 %) | (14.33 %, +2.83 %) | **No.** −0.98 pp / −0.12 pp, inside its 4.03 pp envelope |
| **`fb64k`** | (46.15 %, −5.88 %) | **(58.33 %, −31.89 %)** | **YES, materially** |
| **`fb256k`** | (44.52 %, −6.31 %) | **(58.08 %, −32.48 %)** | **YES, materially** |
| **`fb1m`** | (31.76 %, −6.12 %) | **(47.91 %, −32.51 %)** | **YES, materially** |

The annotated headline of panel (b) — *"91.4 % recovery costs 42 %"*, which is
`cat01` — is **unchanged**: `cat01` goes from (91.39 %, −42.02 %) to
(91.35 %, −42.04 %), a 0.05 pp and 0.02 pp move. The paper's CAT argument, and
the cross-mechanism comparison against IVF-Flat at matched protection, rest on
`cat01` and the CAT sweep and are **not** disturbed by this.

What is disturbed is the *flush-behind* story: in the corrupted data
flush-behind looks like a cheap mechanism buying moderate protection
(≈45 % recovery for ≈6 % tenant cost); in the clean data it buys more
protection at far higher cost (≈58 % for ≈32 %), which puts it much closer to
the CAT frontier instead of below it. Any claim that flush-behind is the
cheap option is **not supported by the corrected tenant** and must be
re-examined by whoever owns that claim. This outcome does not edit those
claims; it reports the measurement and hands the wording back.

**`cat06` deserves its own line.** Its −10.22 pp protection delta is the single
largest CAT deviation and exceeds its 3.42 pp limit by 3×. It is not part of
the flush-behind story, D3 shows it is scatter rather than common mode, and its
tenant cost is fine (−0.12 pp). `cat06`'s corrupted protection (44.12 %) sits
oddly high between `cat05` (54.27) and `cat07` (35.85) — a non-monotonicity in
the corrupted data that the clean data removes (52.74 → 33.89 → 35.06). The
clean sweep is the better-behaved of the two, but D1 is a two-sided test and it
fired, so it is recorded as a failure, not argued away.

## G-exact: PASS

The gate the original registration could not have written, and the reason the
campaign exists.

| | |
| --- | --- |
| required `matches` | `fact_bytes / sizeof(Fact) × reps` = 8,589,934,592 / 16 × 1 = **536,870,912** |
| observed, all 100 tenant records | **536,870,912** |
| deficit | **0** |
| corrupted dataset, all 100 tenant records | 534,773,760, deficit 2,097,152 = `fact_bytes/4096` |
| `qui` records | `matches` null by construction, as required |

Checked in-flight as registered: the **first `wb` record**, ts
2026-09-06T01:44:07, reported `matches` 536,870,912 within the first minute,
before the run was allowed to continue.

## Frontier, paper coordinates

`q(qui)` = 73.4100, `w(wb)` = 167.1160, `tw(wb)` = 42.2007, reproducing
`make_eval_frontiers.py:91-98` exactly.

    arm       protection %  tenant cost %      arm       protection %  tenant cost %
    wb                0.00           0.00      cat06            33.89         -25.30
    nta              14.33           2.83      cat07            35.06         -21.42
    fb64k            58.33         -31.89      cat08            27.37         -17.69
    fb256k           58.08         -32.48      cat09            21.59         -13.93
    fb1m             47.91         -32.51      cat10            13.96         -10.44
    cat01            91.35         -42.04      cat11             5.60          -7.68
    cat02            82.17         -38.85      cat12             0.81          -4.89
    cat03            73.27         -35.81      cat13            -3.89          -2.70
    cat04            64.12         -32.50      cat14            -4.11          -1.01
    cat05            52.74         -28.99      cat15             0.13          -0.12

## Arm-by-arm delta against the corrupted dataset

Clean minus corrupted, percentage points. `env` is the frozen `ENVELOPE_P95`
for that arm; D1's limit is `max(2.0, 2×env)`, D2's is `max(1.0, 2×env)`.
**Bold** rows break a registered threshold.

    arm       prot clean  prot corr    dprot    env  cost clean  cost corr    dcost    env
    wb              0.00       0.00   +0.000   0.00        0.00       0.00   +0.000   0.00
    nta            14.33      15.31   -0.977   4.03        2.83       2.95   -0.115   0.15
  **fb64k          58.33      46.15  +12.178   1.92      -31.89      -5.88  -26.009   0.14**
  **fb256k         58.08      44.52  +13.560   1.88      -32.48      -6.31  -26.173   0.13**
  **fb1m           47.91      31.76  +16.148   0.46      -32.51      -6.12  -26.388   0.43**
    cat01          91.35      91.39   -0.048   0.05      -42.04     -42.02   -0.017   0.09
    cat02          82.17      82.32   -0.147   0.13      -38.85     -38.85   +0.005   0.08
    cat03          73.27      73.87   -0.593   0.66      -35.81     -35.86   +0.048   0.09
    cat04          64.12      64.21   -0.097   0.93      -32.50     -32.56   +0.062   0.10
    cat05          52.74      54.27   -1.529   1.13      -28.99     -28.99   +0.004   0.13
  **cat06          33.89      44.12  -10.223   1.71      -25.30     -25.18   -0.124   0.18**
    cat07          35.06      35.85   -0.793   3.75      -21.42     -21.35   -0.070   0.19
    cat08          27.37      27.55   -0.179   9.28      -17.69     -17.43   -0.259   0.12
    cat09          21.59      18.16   +3.426   3.11      -13.93     -13.59   -0.338   0.12
  **cat10          13.96      10.20   +3.763   1.87      -10.44     -10.17   -0.267   0.42**
    cat11           5.60       3.33   +2.277   4.54       -7.68      -7.10   -0.583   0.17
  **cat12           0.81      -2.85   +3.653   1.22       -4.89      -4.41   -0.481   0.16**
    cat13          -3.89      -5.20   +1.311   2.93       -2.70      -2.31   -0.389   0.13
    cat14          -4.11      -5.41   +1.295   1.28       -1.01      -0.72   -0.291   0.20
    cat15           0.13       0.17   -0.039   3.14       -0.12       0.05   -0.166   0.70

    max |dprot| 16.148 pp, max |dcost| 26.388 pp

D4, the absolute check: `qui` victim 73.4100 vs 73.4055 (**+0.01 %**), `wb`
victim 167.116 vs 167.875 (**−0.45 %**), `wb` tuples/s 42.2007 vs 42.0792
(**+0.29 %**) — all inside ±3 %. The rig is the same rig.

## Positive control: PASS

Registered as pre-flight, not a result. Run after the registration commit and
after IVF had exited, so it can affect neither. `--mode single --hit-rate 1.0
--reps 1 --warmups 0 --hot-bytes 33554432 --fact-node 0 --hot-node 0
--cpu-list 4 --policy wb`.

| tenant | fact_bytes | rows | `matches` | deficit | verdict |
| --- | --- | --- | --- | --- | --- |
| **`a677c52d…` (HEAD)** | 268,435,456 | 16,777,216 | **16,777,216** | **0** | EXACT |
| **`a677c52d…` (HEAD)** | 1,073,741,824 | 67,108,864 | **67,108,864** | **0** | EXACT |
| **`a677c52d…` (HEAD)**, `--huge2m` | 1,073,741,824 | 67,108,864 | **67,108,864** | **0** | EXACT |
| `75e0af94…` (defective) | 268,435,456 | 16,777,216 | 16,711,680 | 65,536 | = fact/4096 |
| `75e0af94…` (defective) | 1,073,741,824 | 67,108,864 | 66,846,720 | 262,144 | = fact/4096 |

The last two rows are a **negative** control the registration did not
explicitly require; they are reported as a diagnostic, not as a registered
result. They matter because they turn the diagnosis into a matched-pair
experiment: at identical geometry, the defective binary reproduces a deficit of
exactly `fact_bytes/4096` on demand across a 4× size range, and the HEAD
binary's deficit is exactly zero — including on the `MAP_HUGETLB` path the
campaign actually uses. Reproduced again post-campaign in the flush-behind
diagnostic above.

Two honest scope notes.

- **This does not prove the `hit_rate` saturation fix was ever live here.**
  As the registration said in advance, c4 has AVX-512, where `vcvttsd2usi`
  saturates and the pre-fix conversion was already correct. The 0.390625 %
  deficit on the published dataset is attributable to the `prefault_region`
  defect alone. The control passes both fixes at once; it isolates only the
  first.
- **The tenant's own `correct` field could not have caught this.** Every row
  above, defective ones included, reports `"correct":true`, because `ok` is
  `!c.check || …` and `--check` is off in this mode. That is precisely why
  G-exact is an external, arithmetic assertion rather than a reading of the
  artifact's self-report.

## Tenant and harness provenance

| | |
| --- | --- |
| source | `benchmarks/e2e/hash_join/src/cxl_join_bench.cpp` at `HEAD` |
| source sha256 | `b843d46595873e14708b2fe585f3a1ca75a3a4f89f5c4bc920391415bf6c7263` |
| fix commit | `abccb31`, verified an ancestor of `HEAD` |
| build | `make BUILD=/home/domin/sil_e2e_rerun/build native`, on c4, g++ 11.4.0, `-O3 -march=native`, no warnings |
| **tenant sha256** | **`a677c52d05b75091057b5d9477fca99fef56e2087605457cfaf8f2b908a98431`** |
| victim | `026e357ae21a99717cae3ebf4ed05fa2cd146bda4f110afe4a2f7b829ef2db50`, reused not rebuilt, identical to all 105 original records |
| **runner** | `run_hashjoin.py` **`a4ce56a99db78a412ef6c2921f913670fdaf2a813833414476ca757a58989079`** at `HEAD` `563ec54` |
| `gates.py` | `0e63ebdeae826f5f11e008596d540ccaf173e9b23d754db1091b9887cf303013`, unchanged from registration |

**The tenant was not rebuilt** and did not need to be: `563ec54` touches only
the two runners, and `git log 785c66d..HEAD -- src/cxl_join_bench.cpp` is empty,
so `HEAD`'s tenant source is still the `b843d465…` the binary was built from.
Its digest was re-verified on c4 before the campaign and again after.

**Registered harness deviation.** The registration froze `run_hashjoin.py` at
`fd815c6c…`. The campaign ran `a4ce56a9…`, that file at `HEAD`, because
`fd815c6c…` is the runner whose unconditional `finally: teardown()` cost the
predecessor a record. The deviation is recorded in the waiver's §A4 and bounded
there: the diff is a `_CLOS_OWNED` flag, its assignment in `setup_tenant()`,
and a guard on the outermost `finally`, so **on the campaign's own path the two
runners are behaviourally identical** — a campaign calls `setup_tenant()`, the
flag is `True`, and the exit teardown runs exactly as registered.

The harness tree `/home/domin/sil_e2e_rerun/head_tree/` was re-created as
`git archive 563ec54 -- <102 tracked paths>`, so what executed corresponds to a
commit rather than an edited working tree; `diff -rq` against the tree the
tenant was built from (retained as `head_tree.pre563ec54/`) is empty.

The build used a `git archive` of `HEAD` because **c4's checkout is not a copy
of `HEAD`**: it sits at `33eaf07` (an ancestor, predating both `abccb31` and
`563ec54`) and carries *uncommitted* modifications to both
`benchmarks/e2e/hash_join/Makefile` and `src/cxl_join_bench.cpp`, the latter
hashing `e8d10458…` and matching no commit. Nothing in c4's checkout was
read-modified or written; it is still at `33eaf07` with exactly those two files
modified. The uncommitted `Makefile`'s only difference from `HEAD` is the
absence of a `gem5-window` target — the `native` rule the tenant is built by is
identical, which is what let the flush-behind diagnosis above rule out build
flags.

Worth recording for `F13`: `build/cxl_join_bench` **on c4** *is* `75e0af94…`,
the binary all 105 published records name. The A1 ledger notes that
`75e0af94…` "is not on this host" — true of mos181, whose copy is
`75813707…`; the bytes are on **c4**. That is a strict improvement in
provenance and is offered as a correction for whoever owns that ledger (see
hand-back below).

## Precedence

Registration precedes every statistic, and the evidence is in git, not a
directory mtime:

- prereg + analyzer committed `afdeb8f`, 2026-09-05T11:39:58+09:00, containing
  only those two files (825 insertions, nothing else touched, nothing staged).
- The **G-pred waiver** was committed `d709bf7`, 2026-09-06T01:25:18+09:00.
  The measured campaign's first record is ts **2026-09-06T01:44:07** — 19
  minutes later. Every statistic in this document postdates both instruments.
- The tenant was built at 11:31 — before the prereg commit — but a build emits
  no statistic; the first `matches` of any kind, the positive control's, was
  produced at ~16:45, five hours after the commit.
- The frozen `ENVELOPE_P95` table and the D1–D4 thresholds were committed in
  `afdeb8f` **before** the 4K/hugepage cross-check was ever computed, and the
  analyzer was **not** edited after the data existed — which matters
  particularly here, because the thresholds that fired are the frozen ones.

## How the campaign was actually run, including one destroyed attempt

Two things departed from the resume plan and are recorded rather than tidied.

**1. Two workers were dispatched to this task and collided on c4.** The full
timeline, reconstructed from `sudo` records, is in the waiver's §A2. In brief:
another worker committed the waiver at 01:25:18, grew node 0, and launched the
campaign at 01:28:05; this worker's own CLOS fix-reproduction at 01:28:16 and
01:28:38 landed inside that run's `wb` and `nta` arms; this worker stopped it at
11 records, tore down the `clos_b` that `SIGTERM` left orphaned at `L3:0=003f`,
and preserved its output unanalysed at
`/home/domin/sil_e2e_rerun/out/VOIDED_2026-09-06_precedence_and_clos_contamination/`.
Damage to it was undetectable (its `wb`/`nta` rep1 sit within 0.42 % and 2.13 %
of the corrupted medians) but it stops at 11 of 105 records and cannot be
certified, so it is void. The operational rule this yields: **an idle check
authorises only the action taken immediately after it.** The measured campaign
was launched after the host was re-verified clean, and `auth.log` shows no
foreign `resctrl_clos.sh` or hugepage `sudo` call inside its 01:44–02:23 window.

**2. `run_silicon_e2e.sh` cannot launch this campaign, in the repo either.**
Resume step 3's command fails immediately. The wrapper computes

    ROOT=$(cd "$(dirname "$0")/../../.." && pwd)

but the script lives at `experiments/asplos/run_silicon_e2e.sh`, two levels
below the root, so `../../..` overshoots by one: from the staged tree it
resolves to `/home/domin/sil_e2e_rerun` and from the real checkout to
`/home/domin`, and it then tries to exec `$ROOT/experiments/asplos/silicon_e2e/run_hashjoin.py`,
which does not exist. It exits before touching CAT, hugepages or the tenant, so
the failed launch was harmless. The campaign was therefore run by invoking the
runner directly with the arguments the wrapper would have passed — which is also
how the other worker's attempt and, by implication, the original 105-record
campaign must have been launched:

    cd /home/domin/sil_e2e_rerun/head_tree
    python3 experiments/asplos/silicon_e2e/run_hashjoin.py \
      --join /home/domin/sil_e2e_rerun/build/cxl_join_bench \
      --victim /home/domin/DutyFree/benchmarks/bench/victim/pointer_chase \
      --out /home/domin/sil_e2e_rerun/out/silicon_e2e_hashjoin_clean.jsonl --huge2m

A one-line fix (`../..`) is proposed in the hand-back rather than applied, for
the same reason the runner fix was not applied by the previous worker: the file
is shared with published campaigns.

Timing: 105 records, 2026-09-06T01:44:07 → 02:23:01, all `ok`.
Output: `/home/domin/sil_e2e_rerun/out/silicon_e2e_hashjoin_clean.jsonl`,
sha256 `40f15aeaa896cce74cf494a4e9c2077f0badc86ddc2fcf2b6cdf5df7e53b67d5`,
**outside the repository**. No `data/*.jsonl` was written or modified.

## The 4K sibling: recommendation — still do not re-run, but its `fb` arms are now suspect too

`data/silicon_e2e_hashjoin_4k.jsonl` carries the same defect: same `sha_join`
`75e0af94…`, same `matches` 534,773,760, same 2,097,152 deficit, differing only
in `huge2m=false`.

**Recommendation: leave it in place, annotate its provenance, and do not
re-run it.** Reasons, in order of weight.

1. **It feeds no figure.** `make_eval_frontiers.py` reads only the hugepage
   dataset. The 4K file supports one negative claim in
   `SILICON_E2E_OUTCOME_2026-09-01.md` — "TLB was not the mechanism. Every
   verdict agrees" — and that claim is a corrupted-vs-corrupted comparison,
   which is *internally valid* precisely because the defect is identical on
   both sides.
2. **Re-running it would destroy evidence currently in use.** A1 uses this
   dataset as *independent confirmation of the corruption mechanism*: the
   1/256 rate is identical at 4K and 2 MiB pages, "which is exactly what a
   hardcoded 4096 B stride in `prefault_region` predicts and what a
   fault-driven mechanism would not." That argument needs the defective 4K
   data to keep existing. Retention, not replacement, is the right handling.
3. **A test pins its headline.** `tests/test_silicon_e2e.py`
   (`TestSiliconE2E4kArchive`) asserts 105 records, all `ok`, all
   `huge2m is False`. Any re-run must write a *new* file.

**What has changed since that recommendation was first written**, and it must be
recorded: the deferral was justified partly on the expectation that D1–D4 would
pass and the answer would transfer. **D1 and D2 did not pass.** The 4K
dataset's three `fb` arms were produced by the same defective binary and are
therefore suspect in exactly the same way and by the same magnitude. That does
*not* change the recommendation — the reasons above are about what the file is
*used for*, and the corruption-rate argument in A1 needs the file unchanged —
but any future use of the 4K file's **flush-behind** numbers must carry the same
"open pending diagnosis" caveat as the hugepage ones. Its CAT and `nta` numbers
are unaffected by this finding.

If it is later re-run: it needs explicit authorisation, must write a *new* file
rather than touch the existing one, and — for fidelity to the original
condition — should run with node 0's pool at its as-found 1024 pages, which is
where it now is.

Also in scope and needing no action: `data/silicon_e2e_calib_v4.jsonl`
(12 records, same `sha_join`) is apparatus, already documented as such.

## Nothing pre-existing changed

`sha256sum -c` passes on all three manifests, taken before the build and
re-verified after the campaign and after the post-campaign diagnostics:

- **c4** (3 entries): `benchmarks/e2e/hash_join/build/cxl_join_bench` =
  `75e0af94…` **OK**, `pointer_chase` **OK**, `ivf_flat_bench` **OK**. The
  defective binary was *executed* read-only by the diagnostics above; its bytes
  are unchanged.
- **mos181** (14 entries): every binary under `benchmarks/e2e/hash_join/build`
  including `cxl_join_bench.gem5` = `cac9e27a…` **OK**, plus `pointer_chase`
  **OK**.
- **datasets** (2 entries): `silicon_e2e_hashjoin.jsonl` **OK**,
  `silicon_e2e_hashjoin_4k.jsonl` **OK**.

c4 is left as found: node 0 restored to **1024** × 2 MiB from the 8192 the
campaign needed, node 2 at 35488 untouched, **no** CLOS groups, root schemata
`L3:0=7fff;1=7fff`, `cpus_list` `[0-127]`, no tenant or victim processes.
c4's checkout is still `33eaf07` with the same two files modified.
`/home/domin/ivf_run/` was read and never written — its JSONL is still
105 records, sha256 `a2d794bd…`, mtime 2026-09-05T16:35:28.
`gem5/`, `/home/domin/STREAMING_Paper/`, `A1_PROVENANCE_LEDGER_2026-08-28.md`
and `INDEX.md` were not touched.

## Hand-back: proposed wording for docs this worker does not own

Not applied — `A1_PROVENANCE_LEDGER_2026-08-28.md` and `INDEX.md` are held by
another worker.

**For A1 / `INDEX.md`, the headline result — supersedes the earlier
"not yet measured" wording:**

> The 105-record clean re-run is **measured** (`silicon_e2e_hashjoin_clean.jsonl`,
> sha256 `40f15aea…`, 2026-09-06, outside the repo). The corrected tenant
> `a677c52d…` computes the join exactly — `matches` = 536,870,912, deficit 0, on
> all 100 tenant records — so **G-exact passes** and the artifact's arithmetic
> defect is closed. But the registered delta predictions **D1 and D2 FAIL**: the
> three flush-behind arms move by ≈26 pp in tenant cost and 12–16 pp in
> protection, so the claim that the corruption "cancels in the ratio
> coordinates" holds for the 15 CAT arms and `nta` and **fails for the three
> `fb` points that `fig:frontier`(b) plots**. Flush-behind numbers from
> `75e0af94…` — in the hugepage *and* 4K datasets — are **open pending
> diagnosis**. The CAT sweep, including the annotated `cat01` headline
> (91.4 % recovery for 42 % cost), is unchanged to within 0.05 pp.

**For A1, correcting the location of `75e0af94…`:**

> `75e0af94…` **is on disk, on c4**: it is
> `benchmarks/e2e/hash_join/build/cxl_join_bench` in c4's checkout (verified
> 2026-09-04, re-verified 2026-09-06). The earlier note that it "is not on this
> host" was true of mos181, whose copy is `75813707…`. Silicon's `F13` position
> is therefore better than `cac9e27a…`'s: digest recorded 105 times *and* bytes
> present. The bytes are still not *reproducible* — c4's `src/cxl_join_bench.cpp`
> is an uncommitted working-tree state, sha256 `e8d10458…`, matching no commit —
> so the dataset remains non-regenerable and is retained rather than replaced.
> That non-reproducibility is now load-bearing rather than cosmetic: the
> flush-behind discrepancy above is a difference between `75e0af94…` and `HEAD`
> that cannot be bisected, because the source of one side is in no commit.

**For `IVF_FLAT_SILICON_OUTCOME_2026-09-04.md`, naming the "foreign process":**

> The process that deleted `clos_b` during `cat05`/rep2 (ts 11:40:02) is
> identified: a concurrent `run_hashjoin.py --self-test-only` from the
> silicon-e2e re-run worker, whose module-level `finally: teardown()` fires on
> every exit path including that early return. Reproduced on the idle host
> afterwards, and again on 2026-09-06 as a matched pair against the fix. It was
> not a stray campaign and not a host fault, so it carries no implication for
> the other 104 records, each of which verified its mask before and after.
> Apologies for the lost rep.

**Proposed runner fix — now applied, for the record:**

> Superseded. `563ec54` guards the outermost `finally` on a `_CLOS_OWNED` flag
> set only in `setup_tenant()`, in both `run_hashjoin.py` and `run_ivf.py`. Note
> its honest limit, recorded in the waiver's §2: the six *in-campaign*
> `teardown()` calls remain unconditional, so `run_one`'s `else` branch still
> clears any `clos_b` present at the start of every `qui`/`wb`/`nta`/`fb*` arm.
> The early-exit hazard is closed; concurrent campaigns on one host are still
> unsafe.

**For whoever owns `experiments/asplos/run_silicon_e2e.sh` — a one-line fix:**

> `ROOT=$(cd "$(dirname "$0")/../../.." && pwd)` overshoots by one level: the
> script sits two levels below the repo root, so `ROOT` resolves to the repo's
> *parent* and the `exec` of `$ROOT/experiments/asplos/silicon_e2e/run_hashjoin.py`
> fails with `No such file or directory`. It should be `../..`. The wrapper is
> therefore dead code today — every campaign that has run, including the original
> 105-record silicon e2e, must have invoked `run_hashjoin.py` directly — so
> fixing it changes no result, but leaving it broken means the documented resume
> command does not work.

**For whoever owns the flush-behind claims:** see "What moves in the paper" and
"The material shift, localised" above. The specific ask: do not cite
flush-behind's tenant cost from either `75e0af94…` dataset without the caveat,
and decide whether the falsifiable prefault experiment is worth running.

---

# §C. The cause, found: a non-hoisted string compare in the flush-behind loop

Addendum from the other worker dispatched to this task (see "How the campaign
was actually run"). It closes the question the section above leaves open, and
corrects one of its conclusions. Everything above stands except the single
clause noted below; the gate verdicts, the frontier, the delta table and
`cat06` are unaffected.

## C1. What `abccb31` did to the loop

`abccb31` added the `--policy fbo` oracle arm **inside**
`join_range_flushbehind`'s per-element loop:

```cpp
for (size_t i = begin; i < end; ++i) {
    /* probe, matches, sum */
    if (policy == "fbo") {              // <-- added by abccb31
      /* one m5op per 4 KiB */
    } else if (((i + 1) % ents_per_line) == 0 && i >= begin + flush_ents) {
      _mm_clflushopt(...);
      if (++batch >= 64) { _mm_sfence(); batch = 0; }
    }
}
```

`policy` is a `const std::string &`, and **the comparison is not hoisted out
of the loop.** `_mm_clflushopt` carries memory side effects, so the compiler
cannot prove the string's heap buffer is unmodified across an iteration and
must re-evaluate the predicate every time. The `fb*` arms run `--policy wb`,
so they take the unchanged `else if` — as the section above correctly says —
but they now pay for *asking* on every row.

## C2. Correction: the instruction census cannot see this, and it is codegen

The section above concludes "**nor is it instruction emission**" on the
strength of a census — 1 `clflushopt`, 0 `clflush`, 2 `sfence`,
17 `prefetchnta` in both binaries. That census is correct and reproduces here.
It is also the wrong instrument: the difference is not a *flush* instruction,
and it is not a change in the *count* of anything the census enumerates. It is
an added **`call`** in the loop body, which a per-opcode census of flush
primitives cannot detect. Looking at the loop itself:

```
measured tenant a677c52d…, join_range_flushbehind, the hot loop:
    9419: jne  9400                       <- probe loop back-edge
    941b: mov  %r14,%rsi
    941e: mov  %r13,%rdi
    9421: call 36f0 <std::__cxx11::basic_string::compare(char const*)@plt>   ***
    9426: mov  %eax,%r8d
    942d: test %r8d,%r8d
    9430: je   9460
    9432: test $0x3,%al                   <- the flush-test guard
    9436: cmp  %rbp,0x30(%rsp)
    9442: clflushopt (%rsi,%rbx,1)
    9454: sfence
    9460: add  $0x10,%rbx
    946d: jmp  9388                       <- outer loop back-edge

defective tenant 75e0af94…, same function, same place:
    9149: jne  9130                       <- probe loop back-edge
    914b: lea  0x1(%r13),%rax             <- straight to the guard: NO call
    914f: test $0x3,%al
    9153: cmp  %r13,0x28(%rsp)
    915f: clflushopt (%rcx,%r15,1)
    9172: sfence
    9180: add  $0x10,%r15
    918c: jmp  90b0                       <- outer loop back-edge
```

The measured tenant executes an out-of-line PLT call to
`std::string::compare(char const*)` **once per fact row — 536,870,912 times per
arm** — where the defective tenant does three ALU operations. So the honest
form of that clause is: *the flush instructions are identical, and the
regression is nonetheless in the generated code, one level away from what the
census counted.*

## C3. It quantitatively accounts for the gap, using the measurements above

From the matched pair at 1 GiB in "It is the binary, not the host", converted
to time per tuple:

| binary | `fd=0` | `fd=64 KiB` | **flush-behind adds** |
| --- | --- | --- | --- |
| `a677c52d…` (clean) | 42.78 Mt/s = 23.376 ns | 30.25 Mt/s = 33.058 ns | **9.682 ns/tuple** |
| `75e0af94…` (defective) | 42.58 Mt/s = 23.486 ns | 40.44 Mt/s = 24.728 ns | **1.242 ns/tuple** |

The defective binary's flush-behind costs **1.24 ns/tuple**, which is the real
cost of the flushing: `ents_per_line` is `64/sizeof(Fact)` = 4, so that is one
`clflushopt` per 4 tuples, ≈5.0 ns per flush, plus a batched `sfence` every 64.
The clean binary's flush-behind costs **9.68 ns/tuple** — the *same* flushing
plus **≈8.44 ns/tuple of something else**, present only on this path.

At the 8462Y+'s 2.8–3.8 GHz that is **≈24–32 cycles per tuple**, which is the
right size for a PLT-dispatched `std::string::compare`: an indirect call, a
`strlen` over the literal, a `memcmp`, a return, and a conditional branch that
cannot resolve until the call does. Four independent facts follow, and all four
are what the sections above measured:

1. **No dependence on flush distance.** The added cost is per *tuple*, not per
   flush, so it is invariant as the distance sweeps 16 B → 1 MiB. That is
   exactly the reported flat 30.24–30.34 vs 40.30–40.59 Mt/s and flat ≈1.33
   ratio.
2. **No dependence on `hit_rate`.** The predicate is evaluated before the flush
   guard and independently of the probe result, so the gap survives at
   `hit_rate` 0.0 — as reported, −24.5 % vs −10.5 %.
3. **The plain join path is untouched.** `join_range` never received the
   branch, so `fd=0` agrees to 0.5 % (42.78 vs 42.58) and `wb` reproduces to
   +0.29 %.
4. **The blast radius is exactly the three `fb*` arms.** Verified across all
   105 records: `fb64k`/`fb256k`/`fb1m` carry `flush_distance` 65536/262144/
   1048576 with `join_path=flushbehind`; `wb`, `nta` and all fifteen `cat*`
   arms carry `flush_distance=0` with `join_path=join_range`. Only the `fb*`
   arms enter the function that changed.

The "sign problem" hypothesis — re-enabled post-`fill_fact` `prefault_region`
calls changing the fact array's cache state — is not needed, and its sign
problem was the correct reason to distrust it. **The third tenant that "is in
no commit" does not need to be built.** The falsifiable experiment that
remains is cheaper: hoist the predicate (§C4), rebuild from `HEAD`, and
flush-behind cost should fall from ≈29 % to ≈5 % at the matched-pair geometry.

## C4. The fix, and what it means for the numbers

Hoist the predicate, which is loop-invariant by construction:

```cpp
const bool oracle = (policy == "fbo");     // once, before the loop
for (size_t i = begin; i < end; ++i) {
    ...
    if (oracle) { /* one m5op per 4 KiB */ }
    else if (((i + 1) % ents_per_line) == 0 && i >= begin + flush_ents) { ... }
}
```

One line. It restores the defective binary's inner loop while keeping the
`fbo` arm, and needs only the three `fb*` arms re-measured — the fifteen `cat*`
arms, `nta`, `wb` and `qui` never enter this function and do not need
re-running. `run_morsel`'s call site into the same function (`HEAD` line 2728)
passes the same `policy` into the same loop and gets the same benefit.

This **narrows** the conclusion above rather than overturning it. Still true:
neither dataset's `fb*` tenant-cost numbers are publishable, and `fig:frontier`
panel (b)'s three flush-behind points are open. Now also true, and it was not
before: **the reason is known, it is a software overhead in the measuring
tenant rather than anything about flush-behind or about CXL, the corrupted
dataset's ≈5–6 % is the closer estimate of flush-behind's true tenant cost of
the two, and the fix is one line rather than a research question.** Neither
dataset should be published for these three points regardless: the defective
one mis-joins, and the clean one measures a string comparison.

## C5. `cat06` is bimodal in the clean run, which is why its median moved

A small addition to "`cat06` deserves its own line", which reads the
non-monotonicity in the corrupted data. The clean run's `cat06` reps are
**bimodal**, and that is the more direct explanation of the −10.22 pp:

```
  arm     clean victim cyc/load, 5 reps                  median   corrupted median
  cat05   121.77 117.69 118.18 116.75 115.25           117.691   116.603
  cat06   135.85 123.93 137.17 123.61 135.36           135.356   126.198
  cat07   135.96 133.02 134.26 132.94 149.84           134.261   134.003
```

Two clusters, ≈123.8 and ≈136.1, split 2–3. The median therefore lands in the
upper cluster; a 3–2 split the other way would have moved it ≈12 cyc/load,
about 10 pp of protection — the whole observed delta. The corrupted `cat06` is
unimodal at ≈126, between the clean clusters, which is why it looked
"oddly high" from that side. So the registered 3.42 pp envelope, bootstrapped
from a unimodal spread, **understates `cat06`'s variance**; it could not have
anticipated bimodality. This is a limitation of the envelope, not a defect in
either dataset, and D1 still fired and is still recorded as a failure. If any
claim ever rests on 6 ways, `cat06` needs more reps; none does.
